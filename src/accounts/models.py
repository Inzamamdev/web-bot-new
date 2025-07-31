from django.db import models
from django.contrib.auth.models import AbstractUser
from encrypted_model_fields.fields import EncryptedCharField

class User(AbstractUser,models.Model):
    github_id = models.BigIntegerField(unique=True, blank=True, null=True)
    chat_id = models.BigIntegerField(null=True, blank=True) 
    github_login = models.CharField(max_length=255)
    avatar = models.URLField(blank=True, null=True)
    access_token = EncryptedCharField(max_length=255)
    sso_token_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    bio = models.TextField(null=True, blank=True)
    public_repos = models.IntegerField(default=0)
    selected_repo = models.ForeignKey("Repository",  # Referencing Repository as a string
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="selected_by"
    )
    followers = models.IntegerField(default=0)
    following = models.IntegerField(default=0)
    
    def __str__(self):
        return self.github_login

class Repository(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repositories')
    repo_id = models.BigIntegerField()
    node_id = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    private = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    fork = models.BooleanField(default=False)
    url = models.URLField()
    html_url = models.URLField()
    git_url = models.URLField()
    ssh_url = models.URLField()
    clone_url = models.URLField()
    svn_url = models.URLField()
    homepage = models.URLField(null=True, blank=True)
    size = models.BigIntegerField(default=0)
    stargazers_count = models.IntegerField(default=0)
    watchers_count = models.IntegerField(default=0)
    language = models.CharField(max_length=100, null=True, blank=True)
    has_issues = models.BooleanField(default=True)
    has_projects = models.BooleanField(default=True)
    has_downloads = models.BooleanField(default=True)
    has_wiki = models.BooleanField(default=True)
    has_pages = models.BooleanField(default=False)
    has_discussions = models.BooleanField(default=False)
    forks_count = models.IntegerField(default=0)
    mirror_url = models.URLField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    disabled = models.BooleanField(default=False)
    open_issues_count = models.IntegerField(default=0)
    allow_forking = models.BooleanField(default=True)
    is_template = models.BooleanField(default=False)
    web_commit_signoff_required = models.BooleanField(default=False)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    default_branch = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'repo_id')  # Prevents duplicates per user
        verbose_name_plural = "Repositories"
        ordering = ['-pushed_at']
    
    def __str__(self):
        return self.full_name

class Branch(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    protected = models.BooleanField(default=False)
    last_commit_sha = models.CharField(max_length=40)
    last_commit_url = models.URLField()
    
    class Meta:
        verbose_name_plural = "Branches"
        unique_together = ('repository', 'name')
    
    def __str__(self):
        return f"{self.repository.name}/{self.name}"

class License(models.Model):
    repository = models.OneToOneField(Repository, on_delete=models.CASCADE, related_name='license')
    key = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    spdx_id = models.CharField(max_length=100)
    url = models.URLField(null=True, blank=True)
    node_id = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.name} ({self.repository.name})"

class RepositoryPermission(models.Model):
    repository = models.OneToOneField(Repository, on_delete=models.CASCADE, related_name='permissions')
    admin = models.BooleanField(default=False)
    maintain = models.BooleanField(default=False)
    push = models.BooleanField(default=False)
    triage = models.BooleanField(default=False)
    pull = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Permissions for {self.repository.name}"

class Topic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    repositories = models.ManyToManyField(Repository, related_name='topics')
    
    def __str__(self):
        return self.name
    
class OAuthState(models.Model):
    state = models.CharField(max_length=48, unique=True)
    telegram_id = models.CharField(max_length=32, null=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"OAuthState (expires: {self.expires_at})"