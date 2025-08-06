from urllib.parse import urlencode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from django.conf import settings
from accounts.models import Repository
from ..helpers import get_github_user

async def current_repo_command(update, context):
    telegram_user_id = update.effective_user.id
    db_user = await get_github_user(telegram_user_id)
      # Check if user has a selected repository
    if not db_user.selected_repo_id:
        await update.message.reply_text("You haven't selected a repository yet. Use /selectRepo to choose one.")
        return

    # Fetch selected repository
    repo = await Repository.objects.filter(id=db_user.selected_repo_id).afirst()
    if not repo:
        await update.message.reply_text("The selected repository was not found. Please select again using /selectRepo.")
        return

    # Send repo details
    message = (
        f"*Current Repository:*\n"
        f"📦 {repo.full_name}\n"
    )
    await update.message.reply_text(message, parse_mode="Markdown")
