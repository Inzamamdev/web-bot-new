from django.core.management.base import BaseCommand
from accounts.models import Repository
from preview.models import RepositoryCodeState, RepositoryFile


class Command(BaseCommand):
    help = "Create test data for preview functionality"

    def handle(self, *args, **options):
        # Create a test user first (required for Repository)
        from accounts.models import User

        test_user, user_created = User.objects.get_or_create(
            username="testuser",
            defaults={
                "github_id": 12345,
                "github_login": "testuser",
                "access_token": "test_token",
                "email": "test@example.com",
            },
        )

        if user_created:
            self.stdout.write(f"Created test user: {test_user.username}")

        # Create a test repository
        repo, created = Repository.objects.get_or_create(
            repo_id=98765,
            defaults={
                "user": test_user,
                "node_id": "test_node_id",
                "name": "test-preview-repo",
                "full_name": "testuser/test-preview-repo",
                "description": "Test repository for preview functionality",
                "url": "https://api.github.com/repos/testuser/test-preview-repo",
                "html_url": "https://github.com/testuser/test-preview-repo",
                "git_url": "git://github.com/testuser/test-preview-repo.git",
                "ssh_url": "git@github.com:testuser/test-preview-repo.git",
                "clone_url": "https://github.com/testuser/test-preview-repo.git",
                "svn_url": "https://github.com/testuser/test-preview-repo",
                "default_branch": "main",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "pushed_at": "2024-01-01T00:00:00Z",
            },
        )

        if created:
            self.stdout.write(f"Created repository: {repo.name}")
        else:
            self.stdout.write(f"Using existing repository: {repo.name}")

        # Create a branch first
        from accounts.models import Branch

        branch, branch_created = Branch.objects.get_or_create(
            repository=repo,
            name="main",
            defaults={
                "protected": False,
                "last_commit_sha": "abc123def456",
                "last_commit_url": "https://api.github.com/repos/testuser/test-preview-repo/commits/abc123def456",
            },
        )

        if branch_created:
            self.stdout.write(f"Created branch: {branch.name}")

        # Create a code state
        code_state, created = RepositoryCodeState.objects.get_or_create(
            repository=repo, commit_hash="abc123def456", defaults={"branch": branch}
        )

        if created:
            self.stdout.write(
                f"Created code state for commit: {code_state.commit_hash}"
            )
        else:
            self.stdout.write(f"Using existing code state: {code_state.commit_hash}")

        # Sample HTML content
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Preview</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <h1>Welcome to Test Preview</h1>
        <p>This is a test page for the preview functionality.</p>
        <button id="testBtn">Click Me!</button>
        <div id="output"></div>
    </div>
    <script src="script.js"></script>
</body>
</html>"""

        # Sample CSS content
        css_content = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.container {
    background: white;
    padding: 40px;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    text-align: center;
    max-width: 500px;
    width: 90%;
}

h1 {
    color: #333;
    margin-bottom: 20px;
    font-size: 2.5em;
}

p {
    color: #666;
    margin-bottom: 30px;
    font-size: 1.1em;
    line-height: 1.6;
}

#testBtn {
    background: linear-gradient(45deg, #667eea, #764ba2);
    color: white;
    border: none;
    padding: 15px 30px;
    font-size: 1.1em;
    border-radius: 25px;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

#testBtn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
}

#output {
    margin-top: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 5px;
    min-height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: #28a745;
}"""

        # Sample JavaScript content
        js_content = """document.addEventListener('DOMContentLoaded', function() {
    const button = document.getElementById('testBtn');
    const output = document.getElementById('output');
    
    let clickCount = 0;
    
    button.addEventListener('click', function() {
        clickCount++;
        
        const messages = [
            'Hello from JavaScript! 👋',
            'Button clicked ' + clickCount + ' times!',
            'Preview is working perfectly! ✨',
            'This is a live preview! 🚀',
            'Keep clicking for more messages! 🎉'
        ];
        
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];
        output.textContent = randomMessage;
        
        // Add some animation
        output.style.transform = 'scale(0.95)';
        setTimeout(() => {
            output.style.transform = 'scale(1)';
        }, 100);
    });
    
    // Initial message
    output.textContent = 'Click the button to test JavaScript functionality!';
});"""

        # Create files
        files_to_create = [
            ("index.html", "html", html_content),
            ("styles.css", "css", css_content),
            ("script.js", "js", js_content),
        ]

        for file_path, file_type, content in files_to_create:
            file_obj, created = RepositoryFile.objects.get_or_create(
                code_state=code_state,
                file_path=file_path,
                defaults={
                    "file_name": file_path,
                    "file_type": file_type,
                    "content": content,
                },
            )

            if created:
                self.stdout.write(f"Created file: {file_path}")
            else:
                self.stdout.write(f"File already exists: {file_path}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTest data created successfully!"
                f"\nRepository ID: {repo.id}"
                f"\nPreview URL: http://localhost:8000/preview/embed/{repo.id}/"
                f"\nAPI URL: http://localhost:8000/preview/api/files/{repo.id}/"
            )
        )
