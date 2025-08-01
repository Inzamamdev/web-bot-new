# Repository Code Preview System

A Django-based application that integrates with GitHub repositories to fetch, store, and preview static web files (HTML, CSS, JavaScript) with Telegram bot integration.

## Features

- 🔐 **GitHub OAuth Integration** - Secure authentication with GitHub
- 📁 **Repository Management** - Fetch and store repository code states
- 🎨 **Static File Preview** - Preview HTML, CSS, and JavaScript files
- 🤖 **Telegram Bot** - Bot integration for notifications and interactions
- 🔒 **Secure Storage** - Encrypted sensitive data storage
- 📊 **File Management** - Track file changes and versions

## Tech Stack

- **Backend**: Django 5.2.4 with Django Ninja API
- **Database**: SQLite (default) / PostgreSQL (production)
- **Authentication**: GitHub OAuth + JWT
- **Bot Integration**: python-telegram-bot
- **Security**: Cryptography with Fernet encryption

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd <project-directory>
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the sample environment file and configure your settings:

```bash
cp .env.sample .env
```

Edit `.env` with your configuration:

```env
# Required: Generate a Django secret key
SECRET_KEY=your-secret-key-here

# Required: GitHub OAuth App credentials
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/github/callback

# Required: Telegram Bot Token
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Required: Generate Fernet encryption key
FERNET_KEY=your-fernet-encryption-key
```

### 3. Database Setup

```bash
cd src
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run the Application

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Configuration Guide

### GitHub OAuth Setup

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App with:
   - **Application name**: Your app name
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/api/github/callback`
3. Copy the Client ID and Client Secret to your `.env` file

### Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token to your `.env` file

### Generate Encryption Key

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Use this as your FERNET_KEY
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - GitHub OAuth login
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/auth/logout` - Logout

### Repositories
- `GET /api/repositories/` - List user repositories
- `POST /api/repositories/` - Add repository
- `GET /api/repositories/{id}/` - Get repository details
- `POST /api/repositories/{id}/sync` - Sync repository code

### Code Preview
- `GET /api/preview/{repo_id}/` - Get repository code state
- `GET /api/preview/{repo_id}/files/` - List repository files
- `GET /api/preview/{repo_id}/files/{file_id}/` - Get specific file content

## Database Models

### RepositoryCodeState
Stores the current state of a repository's code:
- Repository reference
- Commit hash and branch tracking
- Creation and update timestamps

### RepositoryFile
Stores individual files from repositories:
- File path and name
- File type (HTML, CSS, JS)
- File content and size
- Automatic file type detection

## Development

### Project Structure

```
src/
├── accounts/          # User authentication and GitHub integration
├── core/             # Core Django settings and configuration
├── preview/          # Repository code preview functionality
├── telegram_bot/     # Telegram bot integration
├── manage.py         # Django management script
└── db.sqlite3        # SQLite database (development)
```

### Running Tests

```bash
python manage.py test
```

### Code Style

The project uses Django's built-in formatting. Run the development server with:

```bash
python manage.py runserver --settings=core.settings
```

## Deployment

### Production Settings

1. Set `DEBUG=False` in production
2. Configure `ALLOWED_HOSTS` with your domain
3. Use PostgreSQL for production database
4. Set up proper CORS settings
5. Use environment variables for all secrets

### Environment Variables for Production

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
GITHUB_REDIRECT_URI=https://yourdomain.com/api/github/callback
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- All sensitive data is encrypted using Fernet encryption
- GitHub tokens are securely stored and managed
- JWT tokens are used for API authentication
- Environment variables are used for all configuration

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` folder
- Review the API documentation at `/api/docs` when running the server

---

**Note**: This application is designed for development and preview purposes. Ensure proper security measures are in place before deploying to production.