from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from accounts.models import User, Repository
from accounts.services.github_service import GitHubService
from ..helpers import get_github_user

github_service = GitHubService()


async def select_repo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
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

    # Extract repo_id from callback data
    data = query.data
    if not data.startswith("select_repo:"):
        return
    repo_id = int(data.split(":")[1])

    # Fetch repo & update user preference
    repo = await Repository.objects.filter(id=repo_id).afirst()
    user = await User.objects.filter(chat_id=query.from_user.id).afirst()
    if not repo or not user:
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
                [
                    InlineKeyboardButton(
                        b["name"], callback_data=f"select_branch:{b['name']}"
                    )
                ]
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


async def select_branch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    branch_name = query.data.split(":")[1]
    user = await User.objects.filter(chat_id=query.from_user.id).afirst()

    user.current_branch = branch_name
    await user.asave()

    await query.edit_message_text(
        f"🌿 Branch set to *{branch_name}*", parse_mode="Markdown"
    )
