from django.urls import path, re_path
from . import views

app_name = 'preview'

urlpatterns = [
    # Root: choose index.html (if exists) or show directory listing
    path("<int:repo_id>/", views.preview_root, name="preview_root"),
    # File/Directory handler (anything under the repo)
    re_path(r"(?P<repo_id>\d+)/(?P<path>.*)$", views.preview_serve, name="preview_serve"),

    path('redirect/<int:repo_id>/', views.redirect_to_stackblitz, name='redirect_to_stackblitz'),
    path('api/files/<int:repo_id>/', views.repository_files_api, name='repository_files_api'),
]
