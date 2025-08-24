from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .start import start_command
from .login import login_command
from .logout import logout_command
from .current_repo import current_repo_command
from .select_repo import select_repo_command

async def menu_callback(update, context):
    """Handle menu button callbacks"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Handle different callback commands
    if callback_data == "cmd_login":
        await handle_callback_command(update, context, login_command)
    elif callback_data == "cmd_logout":
        await handle_callback_command(update, context, logout_command)
    elif callback_data == "cmd_current_repo":
        await handle_callback_command(update, context, current_repo_command)
    elif callback_data == "cmd_select_repo":
        await handle_callback_command(update, context, select_repo_command)
    elif callback_data == "cmd_start":
        await handle_callback_command(update, context, start_command)
    elif callback_data == "cmd_menu":
        await handle_callback_menu(update, context)
    elif callback_data == "cmd_help":
        await show_help(update, context)

async def handle_callback_command(update, context, command_func):
    """Wrapper to handle callback queries for regular commands"""
    # Create a mock update object that has the message from callback_query
    class MockUpdate:
        def __init__(self, callback_query):
            self.message = callback_query.message
            self.effective_user = callback_query.from_user
            self.callback_query = callback_query
    
    mock_update = MockUpdate(update.callback_query)
    await command_func(mock_update, context)

async def handle_callback_menu(update, context):
    """Handle menu callback specifically"""
    query = update.callback_query
    
    menu_text = """
🤖 **Bot Menu**

Choose an option below to get started:
"""
    
    # Create inline keyboard with command buttons
    keyboard = [
        [
            InlineKeyboardButton("🔐 Login", callback_data="cmd_login"),
            InlineKeyboardButton("🚪 Logout", callback_data="cmd_logout")
        ],
        [
            InlineKeyboardButton("📁 Current Repo", callback_data="cmd_current_repo"),
            InlineKeyboardButton("🔄 Select Repo", callback_data="cmd_select_repo")
        ],
        [
            InlineKeyboardButton("🚀 Start", callback_data="cmd_start"),
            InlineKeyboardButton("📋 Menu", callback_data="cmd_menu")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="cmd_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        menu_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def show_help(update, context):
    """Show detailed help information - same as /help command"""
    help_text = """
🤖 **Bot Help & Guide**

**Getting Started:**
1️⃣ Connect your GitHub account with `/login`
2️⃣ Select a repository using `/select_repo`
3️⃣ Start managing your repositories!

**📋 Available Commands:**

**👤 Account Management:**
🔐 `/login` - Connect your GitHub account
🚪 `/logout` - Disconnect from GitHub

**📁 Repository Management:**
📂 `/current_repo` - View current repository & branch
🔄 `/select_repo` - Choose a repository to work with

**ℹ️ General Commands:**
🚀 `/start` - Start the bot and get welcome message
📋 `/menu` - Show interactive command menu
❓ `/help` - Show this help guide

**💡 Tips:**
• Use the interactive `/menu` for quick access to all commands
• Make sure to login first before using repository commands
• Commands work in both private chats and groups

**🆘 Need Support?**
If you encounter any issues, please contact our support team.
"""
    
    # Create quick action buttons - same as /help command
    keyboard = [
        [
            InlineKeyboardButton("🔐 Login Now", callback_data="cmd_login"),
            InlineKeyboardButton("📋 Show Menu", callback_data="cmd_menu")
        ],
        [
            InlineKeyboardButton("🔄 Select Repo", callback_data="cmd_select_repo"),
            InlineKeyboardButton("📂 Current Repo", callback_data="cmd_current_repo")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def menu_command(update, context):
    menu_text = """
🤖 **Bot Menu**

Choose an option below to get started:
"""
    
    # Create inline keyboard with command buttons
    keyboard = [
        [
            InlineKeyboardButton("🔐 Login", callback_data="cmd_login"),
            InlineKeyboardButton("🚪 Logout", callback_data="cmd_logout")
        ],
        [
            InlineKeyboardButton("📁 Current Repo", callback_data="cmd_current_repo"),
            InlineKeyboardButton("🔄 Select Repo", callback_data="cmd_select_repo")
        ],
        [
            InlineKeyboardButton("🚀 Start", callback_data="cmd_start"),
            InlineKeyboardButton("📋 Menu", callback_data="cmd_menu")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="cmd_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        menu_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
