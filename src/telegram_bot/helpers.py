from accounts.models import User

async def get_github_user(telegram_user_id: int):
    
    user = await User.objects.filter(chat_id=telegram_user_id).afirst()
    if user and user.access_token:
        return user
    return None