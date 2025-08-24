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
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_states",
        help_text="Branch associated with this code state",
    )
    commit_sha = models.CharField(max_length=40, db_index=True, null=True)
    is_initial = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        unique_together = ("repository", "branch", "commit_sha")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Code state for {self.repository.name} ({self.commit_sha[:8]})"


class RepositoryFile(models.Model):
    code_state = models.ForeignKey(
        RepositoryCodeState,
        on_delete=models.CASCADE,
        related_name="files",
        help_text="The code state this file belongs to",
    )
    path = models.CharField(max_length=500)
    file_type = models.CharField(
        max_length=10,
        choices=[("html", "HTML"), ("css", "CSS"), ("js", "JavaScript")],
        null=True, # Allow null for files without these types
        blank=True
    )
    size_bytes = models.PositiveIntegerField(default=0)
    content = models.TextField(null=True, blank=True)
    is_binary = models.BooleanField(default=False)
    change_type = models.CharField(
        max_length=20,
        choices=[
            ("added", "Added"),
            ("modified", "Modified"),
            ("removed", "Removed"),
            ("unchanged", "Unchanged"),
        ],
        default="unchanged",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["path"]),
        ]
        unique_together = ("code_state", "path")

    def __str__(self):
        return f"{self.path} ({self.file_type})"

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
        return self.path.split(".")[-1].lower() if "." in self.path else ""
