import logging
from .services.bot import start_bot  # Updated import path


logger = logging.getLogger(__name__)

async def notify_user(tg_id: int, message: str):
    """Send a message to a Telegram user."""
    bot_app = None
    try:
        bot_app = await start_bot()
        await bot_app.bot.send_message(chat_id=tg_id, text=message)
        logger.info(f"Sent message to {tg_id}: {message}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {tg_id}: {str(e)}")
        raise
    finally:
        if bot_app is not None:
            try:
                await bot_app.stop()
                await bot_app.shutdown()
                logger.info("Bot stopped and shut down")
            except Exception as e:
                logger.error(f"Error shutting down bot: {e}")





async def get_github_user(telegram_user_id: int):
    from accounts.models import User
    user = await User.objects.filter(chat_id=telegram_user_id).afirst()
    if user and user.access_token:
        return user
    return None
