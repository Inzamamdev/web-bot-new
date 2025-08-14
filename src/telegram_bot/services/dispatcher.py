from telegram.ext import CommandHandler, CallbackQueryHandler
from ..commands.start import start_command
from ..commands.login import login_command
from ..commands.logout import logout_command
from ..commands.select_repo import select_repo_command, select_repo_callback, select_branch_callback
from ..commands.current_repo import current_repo_command


def register_commands(app):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(CommandHandler("selectrepo", select_repo_command))
    app.add_handler(CommandHandler("currentrepo", current_repo_command))
    app.add_handler(CallbackQueryHandler(select_repo_callback, pattern="^select_repo:"))
    app.add_handler(CallbackQueryHandler(select_branch_callback, pattern="^select_branch:"))
    