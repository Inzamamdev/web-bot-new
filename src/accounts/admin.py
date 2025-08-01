from django.contrib import admin
from .models import User, OAuthState, Repository

# Register your models here.
admin.site.register(User)
admin.site.register(OAuthState)
admin.site.register(Repository)