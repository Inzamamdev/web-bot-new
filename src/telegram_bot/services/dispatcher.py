from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import BotCommand
from ..commands.start import start_command
from ..commands.login import login_command
from ..commands.logout import logout_command
from ..commands.select_repo import (
    select_repo_command,
    select_repo_callback,
    select_branch_callback,
)
from ..commands.unknown_command import unknown_command
from ..commands.current_repo import current_repo_command
from ..commands.menu import menu_command, menu_callback
from ..commands.help import help_command
from ..commands.preview import preview


def register_commands(app):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(CommandHandler("select_repo", select_repo_command))
    app.add_handler(CommandHandler("current_repo", current_repo_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^cmd_"))
    app.add_handler(CallbackQueryHandler(select_repo_callback, pattern="^select_repo:"))
    app.add_handler(
        CallbackQueryHandler(select_branch_callback, pattern="^select_branch:")
    )
    app.add_handler(CommandHandler("preview", preview))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))


async def set_commands(app):
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/login", description="Connect your GitHub account"),
        BotCommand(command="/logout", description="Disconnect your GitHub account"),
        BotCommand(
            command="/select_repo", description="Select a repository to work with"
        ),
        BotCommand(
            command="/current_repo",
            description="View the current repository and branch",
        ),
        BotCommand(command="/preview", description="Get a preview of your current selection"),
        BotCommand(command="/menu", description="Show all available commands"),
        BotCommand(command="/help", description="Get help and usage guide"),
    ]
    await app.bot.set_my_commands(commands)
