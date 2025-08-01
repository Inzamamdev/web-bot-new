from django.db import models
from accounts.models import Repository
from accounts.models import Branch

class RepositoryCodeState(models.Model):
    """
    Represents the current state of code for a specific repository.
    """

    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="code_states",
        help_text="The repository this code state belongs to",
    )
    commit_hash = models.CharField(
        max_length=40, blank=True, help_text="Git commit hash"
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_states",
        help_text="Branch associated with this code state",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        unique_together = ["repository", "commit_hash"]

    def __str__(self):
        return f"Code state for {self.repository.name} ({self.commit_hash[:8]})"


class RepositoryFile(models.Model):
    code_state = models.ForeignKey(
        RepositoryCodeState,
        on_delete=models.CASCADE,
        related_name="files",
        help_text="The code state this file belongs to",
    )
    file_path = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=[("html", "HTML"), ("css", "CSS"), ("js", "JavaScript")])
    content = models.TextField()
    size_bytes = models.PositiveIntegerField(default=0)
    
    version = models.PositiveIntegerField(default=1, help_text="Version number of the file")
    is_latest = models.BooleanField(default=True, help_text="Is this the latest version of this file")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["code_state", "file_path", "version"]
        indexes = [
            models.Index(fields=["file_type"]),
            models.Index(fields=["file_name"]),
            models.Index(fields=["file_path", "is_latest"]),
        ]

    def __str__(self):
        return f"{self.file_path} v{self.version} ({self.file_type})"

    def save(self, *args, **kwargs):
        # Auto-detect type
        if not self.file_type or self.file_type == "other":
            ext = self.get_file_extension()
            self.file_type = {
                "html": "html",
                "htm": "html",
                "css": "css",
                "js": "js",
                "jsx": "js",
            }.get(ext, "other")

        # Calculate size
        self.size_bytes = len(self.content.encode("utf-8"))

        super().save(*args, **kwargs)

    def get_file_extension(self):
        return self.file_path.split(".")[-1].lower() if "." in self.file_path else ""
