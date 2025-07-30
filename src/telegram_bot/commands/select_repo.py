from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from accounts.models import User, Repository
from asgiref.sync import sync_to_async
from accounts.services.github_service import GitHubService

github_service = GitHubService()
# Step 1: Command to show repo selection
async def select_repo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id

    # Check if user exists
    user = await User.objects.filter(chat_id=telegram_user_id).afirst()
    if not user:
        await update.message.reply_text("You haven't linked your GitHub account yet. Use /login to connect.")
        return

    # Fetch repos (top 10 to avoid huge keyboard)
    repos_qs = Repository.objects.filter(user=user).order_by('-updated_at')
    repos = await sync_to_async(list)(repos_qs[:10])  # limit to 10 for now

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
        branch_data = await github_service.update_branches(user.access_token,repo)
        permission = await github_service._update_permissions(repo,repo.get("permissions", {}))
        license_info = await github_service._update_license(repo,repo.get("license"))
        topics = await github_service._update_topics(user.access_token,repo,repo["name"])

        # Store the selected repo (you can add a field in User model: selected_repo = ForeignKey)
        user.selected_repo = repo
        await sync_to_async(user.save)()

        await query.edit_message_text(
            f"*{repo.full_name}* selected!\n\n"
            f"✅ Branches: `{', '.join([b['name'] for b in branch_data])}`\n"
            f"🏷 Topics: `{', '.join(topics)}`\n"
            f"📄 License: `{license_info.get('name', 'None')}`\n"
            f"🔐 Permission: `{permission.get('permission', 'Unknown')}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await query.edit_message_text(f"Repo selected, but failed to fetch extra data: {str(e)}")