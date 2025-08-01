from django.urls import path
from . import views

app_name = 'preview'

urlpatterns = [
    path('embed/<int:repo_id>/', views.preview_embed, name='preview_embed'),
    path('api/files/<int:repo_id>/', views.repository_files_api, name='repository_files_api'),
]