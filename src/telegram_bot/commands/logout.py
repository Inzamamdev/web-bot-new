from accounts.models import User
import logging


logger = logging.getLogger(__name__)
async def logout_command(update, context):
     """Handle /logout command from Telegram"""
     tg_id = str(update.effective_user.id)
     logger.info(f"context: {context.user_data.get("db_user")}")
     try:
        # Find the user associated with the Telegram ID
        user = context.user_data.get("db_user")
        # Clear access token and sso_token_expiry
        user.access_token = ""
        user.sso_token_expiry = None  # Clear to avoid naive datetime issues
        await user.asave()

        logger.info(f"User {user.github_login} (tg_id: {tg_id}) logged out successfully")
        await update.message.reply_text("✅ You have successfully logged out from GitHub.")

     except Exception as e:
        logger.error(f"Logout failed for Telegram ID {tg_id}: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ An unexpected error occurred while logging out. Please try again.")
