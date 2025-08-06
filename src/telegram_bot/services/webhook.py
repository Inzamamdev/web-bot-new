import json
import logging
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from .bot import start_bot
from ..helpers import get_github_user

logger = logging.getLogger(__name__)

async def handle_telegram_webhook(request_body: bytes):
    """Processes the raw request body from Telegram asynchronously."""
    bot_app = None
    try:
        # Initialize bot for this request
        bot_app = await start_bot()

        # Decode and parse JSON
        try:
            data = json.loads(request_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Invalid request body: {e}, body: {request_body!r}")
            return {"status": "error", "error": "Invalid JSON or encoding"}

        logger.info(f"Incoming update: {data}")

        # Convert JSON to Telegram Update object
        update = Update.de_json(data, bot_app.bot)
       
        if not update:
            logger.error(f"Invalid Telegram update: {data}")
            return {"status": "error", "error": "Invalid Telegram update"}
       

        await bot_app.process_update(update)
        logger.info(f"Processed update ID: {update.update_id}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing Telegram update: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up bot
        if bot_app is not None:
            try:
                await bot_app.stop()
                await bot_app.shutdown()
                logger.info("Bot stopped and shut down")
            except Exception as e:
                logger.error(f"Error shutting down bot: {e}")