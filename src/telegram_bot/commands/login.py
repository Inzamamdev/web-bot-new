from urllib.parse import urlencode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from django.conf import settings
from ..helpers import get_github_user
import logging
from django.forms.models import model_to_dict
logger = logging.getLogger(__name__)

async def login_command(update, context):
    telegram_user_id = update.effective_user.id
    user = await get_github_user(telegram_user_id)

    if user:
        context.user_data["db_user"] = user
        logger.info(f"context: {context.user_data.get("db_user")}")
        await update.message.reply_text("✅ You're already connected to GitHub!")
        return
    
    
   
    live_url = settings.SERVER_URL
    params = urlencode({"tg_id": telegram_user_id})
    login_url = f"{live_url}api/auth/github/login?{params}"
   
   # Create a button
    keyboard = [
        [InlineKeyboardButton("🔗 Connect GitHub", url=login_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Click the button below to connect your GitHub account:",
        reply_markup=reply_markup
    )
