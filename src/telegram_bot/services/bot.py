from telegram.ext import Application, CommandHandler
from .dispatcher import register_commands
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

async def build_bot():
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        app = Application.builder().token(token).build()
        await register_commands(app)
        logger.info("Bot initialized successfully")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise

async def start_bot():
    """Initialize and start the bot for processing updates."""
    try:
        app = await build_bot()
        await app.initialize()
        await app.start()
        logger.info("Bot started")
        return app
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise