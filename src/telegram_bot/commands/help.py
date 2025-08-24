from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def help_command(update, context):
    """Show detailed help information"""
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
    
    # Create quick action buttons
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
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )