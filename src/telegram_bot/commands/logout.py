from accounts.models import User
import logging
from ..helpers import get_github_user

logger = logging.getLogger(__name__)

async def logout_command(update, context):
     """Handle /logout command from Telegram"""
     tg_id = str(update.effective_user.id)
     user = await get_github_user(tg_id)
     if not user:
            await update.message.reply_text("❌ No GitHub account linked to this Telegram ID. Please log in first.")
            logger.warning(f"No user found for Telegram ID {tg_id}")
            return
   
     try:
        # Clear access token and sso_token_expiry
        user.access_token = ""
        user.sso_token_expiry = None 
        await user.asave()

        logger.info(f"User {user.github_login} (tg_id: {tg_id}) logged out successfully")
        await update.message.reply_text("✅ You have successfully logged out from GitHub.")

     except Exception as e:
        logger.error(f"Logout failed for Telegram ID {tg_id}: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ An unexpected error occurred while logging out. Please try again.")
