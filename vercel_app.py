import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Import and setup Django
import django
django.setup()

# Import the WSGI application
from core.wsgi import application

# This is what Vercel will use
app = application