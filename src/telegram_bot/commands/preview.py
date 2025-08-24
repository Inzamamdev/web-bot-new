from telegram import Update
from telegram.ext import CallbackContext
from accounts.models import User
from django.conf import settings

from asgiref.sync import sync_to_async

async def preview(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    try:
        # Run ORM call in a thread
        user = await User.objects.select_related("selected_repo").filter(chat_id=telegram_id).afirst() #prefetch_related("selected_repo")
        repo = user.selected_repo
        branch = user.current_branch

        if not repo or not branch:
            await update.message.reply_text(
                "No repository or branch selected. Use /select_repo and /select_branch first."
            )
            return

        preview_url = f"{settings.SERVER_URL}preview/{repo.id}/"
        msg = (
            f"🔎 *Preview for your current selection:*\n"
            f"*Repository:* `{repo.name}`\n"
            f"*Branch:* `{branch}`\n"
            f"*Preview URL:* [Open Preview]({preview_url})"
        )
        await update.message.reply_markdown(msg)

    except User.DoesNotExist:
        await update.message.reply_text("User not found. Please login first.")
