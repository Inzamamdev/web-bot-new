import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from accounts.models import User, Repository, Branch
from accounts.services.github_service import GitHubService
from ..helpers import get_github_user
from preview.services import update_codebase

import logging
logger = logging.getLogger(__name__)
github_service = GitHubService()


async def select_repo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id

    # Check if user exists
    user = await get_github_user(telegram_user_id)
    if not user:
        await update.message.reply_text(
            "You haven't linked your GitHub account yet. Use /login to connect."
        )
        return

    repos = Repository.objects.filter(user=user).order_by("-updated_at")

    if not await repos.aexists():
        await update.message.reply_text("No repositories found for your account.")
        return

    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton(repo.full_name, callback_data=f"select_repo:{repo.id}")]
        async for repo in repos
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Select a repository to work with:", reply_markup=reply_markup
    )


# Step 2: Handle button press
async def select_repo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Retrieving repository branches...")

    data = query.data
    if not data.startswith("select_repo:"):
        logger.warning("Invalid callback data: %s", data)
        return

    repo_id = int(data.split(":")[1])

    # Fetch repo & update user preference
    repo = (
        await Repository.objects.prefetch_related("branches")
        .filter(id=repo_id)
        .afirst()
    )
    user = await User.objects.filter(chat_id=query.from_user.id).afirst()
    if not repo or not user:
        logger.error("Either user or repo not found. User: %s, Repo: %s", user, repo)
        await query.edit_message_text("Something went wrong. Please try again.")
        return

    try:
        branch_data = await github_service.update_branches(user.access_token, repo)
        url = f"https://api.github.com/repos/{repo.full_name}"
        repo_data = await github_service._make_request(user.access_token, url)
        await github_service._update_permissions(repo, repo_data.get("permissions", {}))
        user.selected_repo = repo
        await user.asave()
        repo_summary = f"Repository *{repo.full_name}* selected! The AI will now work on this repo."

        if branch_data:
            keyboard = [
                [InlineKeyboardButton(b.name, callback_data=f"select_branch:{b.id}")]
                for b in branch_data
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"{repo_summary}\n🌿 *Select a branch:*",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"{repo_summary}\n_No branches found._", parse_mode="Markdown"
            )

    except Exception as e:
        await query.edit_message_text(
            f"Repo selected, but failed to fetch extra data: {str(e)}"
        )


async def animate_loading(query, context, loading_message):
    dots = ["", ".", "..", "..."]
    i = 0
    while not context.chat_data.get("setup_done"):
        await asyncio.sleep(0.1)
        i = (i + 1) % len(dots)
        try:
            await query.edit_message_text(
                f"{loading_message}{dots[i]}", parse_mode="Markdown"
            )
        except Exception:
            break


async def select_branch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Setting up codebase...")
    branch_id = query.data.split(":")[1]
    user = (
        await User.objects.select_related("selected_repo")
        .filter(chat_id=query.from_user.id)
        .afirst()
    )
    branch = await Branch.objects.filter(id=branch_id).afirst()

    user.current_branch = branch.name
    await user.asave()

    loading_message = f"Setting up codebase for *{branch.name}*"
    await query.edit_message_text(loading_message, parse_mode="Markdown")
    # Init flag
    context.chat_data["setup_done"] = False

    # Animate the loading dots while update_codebase runs

    # Run the animation in background
    asyncio.create_task(
        animate_loading(query=query, context=context, loading_message=loading_message)
    )

    # Do the heavy work
    await update_codebase(
        user, user.selected_repo, branch, branch.last_commit_sha, user.access_token
    )

    # Mark setup done so animation stops
    context.chat_data["setup_done"] = True
    await asyncio.sleep(0)  # let animate_loading break cleanly

    # Final message
    await query.edit_message_text(
        f"🌿 Branch set to *{branch.name}*", parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id=query.from_user.id, text="Now run /preview to view your application."
    )
