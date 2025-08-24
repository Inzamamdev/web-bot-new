from telegram import Update
from telegram.ext import ContextTypes

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Unknown Command ⁉️\n\nPlease enter the right command or type /start to restart the bot."
    )
