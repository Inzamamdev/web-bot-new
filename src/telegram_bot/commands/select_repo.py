from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from accounts.models import User, Repository
from asgiref.sync import sync_to_async
from accounts.services.github_service import GitHubService
from django.forms.models import model_to_dict
import logging
logger = logging.getLogger(__name__)
github_service = GitHubService()
# Step 1: Command to show repo selection
async def select_repo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id

    # Check if user exists
    user = await User.objects.filter(chat_id=telegram_user_id).afirst()
    if not user:
        await update.message.reply_text("You haven't linked your GitHub account yet. Use /login to connect.")
        return

   
    repos_qs = Repository.objects.filter(user=user).order_by('-updated_at')
    repos = await sync_to_async(list)(repos_qs)  

    if not repos:
        await update.message.reply_text("No repositories found for your account.")
        return

    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton(repo.name, callback_data=f"select_repo:{repo.id}")]
        for repo in repos
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Select a repository to work with:", reply_markup=reply_markup)


# Step 2: Handle button press
async def select_repo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("select_repo:"):
        logger.warning("Invalid callback data: %s", data)
        return

    repo_id = int(data.split(":")[1])
    logger.info("Received repo selection for repo_id: %d", repo_id)

    # Fetch user and repo
    user = await User.objects.filter(chat_id=query.from_user.id).afirst()
    

    repo = await Repository.objects.filter(id=repo_id).afirst()

    logger.info("User object: %s", user)
    logger.info("Repo object: %s", model_to_dict(repo))

    if not repo or not user:
        logger.error("Either user or repo not found. User: %s, Repo: %s", user, repo)
        await query.edit_message_text("Something went wrong. Please try again.")
        return

    try:
        
        logger.info("Access token used: %s", user.access_token)
        branch_data = await github_service.update_branches(user.access_token, repo)
        logger.info("Branches fetched: %s", branch_data)
        url = f"https://api.github.com/repos/{repo.full_name}"
        repo_data = await github_service._make_request(user.access_token,url,)
        logger.info("Repo Data object: %s", repo_data)
        permission = await github_service._update_permissions(repo, repo_data.get("permissions", {}))
        logger.info("Permissions fetched: %s", permission)

        license_info = await github_service._update_license(repo, repo_data.get("license"))
        logger.info("License info fetched: %s", license_info)

        topics = await github_service._update_topics(user.access_token, repo, repo["name"])
        logger.info("Topics fetched: %s", topics)

        # Save selected repo to user
        user.selected_repo = repo
        await sync_to_async(user.save)()
        logger.info("Selected repo saved to user.")

        await query.edit_message_text(
            f"*{repo.full_name}* selected!\n\n"
            f"✅ Branches: `{', '.join([b['name'] for b in branch_data])}`\n"
            f"🔐 Permission: `{permission.get('permission', 'Unknown') if permission else 'Unknown'}`\n"
            f"🏷 Topics: `{', '.join(topics) if topics else 'Unavailable'}`\n"
            f"📄 License: `{license_info.get('name', 'None') if license_info else 'None'}`\n",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.exception("Error during repo selection: %s", str(e))
        await query.edit_message_text(f"Repo selected, but failed to fetch extra data: {str(e)}")
