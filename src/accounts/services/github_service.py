import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import transaction

from ..models import *

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        self.fernet = Fernet(settings.FERNET_KEY)

    def encrypt_token(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        return self.fernet.decrypt(encrypted_token.encode()).decode()

    async def _make_request(self, access_token: str, url: str, params: dict = None, headers: dict = None) -> dict:
        """Async helper method to make GitHub API requests"""
        if headers is None:
            headers = {**self.headers, "Authorization": f"Bearer {access_token}"}
        else:
            headers = {**headers, "Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

    async def get_user_data(self, access_token: str) -> dict:
        """Fetch user data from GitHub"""
        return await self._make_request(access_token, "https://api.github.com/user")

    async def get_all_repos(self, access_token: str) -> List[dict]:
        """Fetch all repositories with pagination"""
        repos = []
        page = 1
        per_page = 100

        while True:
            try:
                batch = await self._make_request(
                    access_token,
                    "https://api.github.com/user/repos",
                    params={"page": page, "per_page": per_page, "sort": "updated"}
                )
                if not batch:
                    break

                repos.extend(batch)
                page += 1

                if len(batch) < per_page:
                    break
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch repos page {page}: {str(e)}")
                break

        return repos

    async def get_repo_branches(self, access_token: str, full_name: str) -> List[dict]:
        """Fetch branches for a repository"""
        return await self._make_request(
            access_token,
            f"https://api.github.com/repos/{full_name}/branches"
        )

    async def get_repo_topics(self, access_token: str, full_name: str) -> dict:
        """Fetch repository topics"""
        return await self._make_request(
            access_token,
            f"https://api.github.com/repos/{full_name}/topics",
            headers={"Accept": "application/vnd.github.mercy-preview+json"}
        )

    @sync_to_async
    @transaction.atomic
    def update_user_data(self, user_data: dict, access_token: str) -> User:
        """Create or update user from GitHub data"""
        encrypted_token = self.encrypt_token(access_token)

        user, created = User.objects.update_or_create(
            github_id=user_data["id"],
            defaults={
                "username": user_data["login"],
                "github_login": user_data["login"],
                "avatar": user_data.get("avatar_url"),
                "bio": user_data.get("bio"),
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "access_token": encrypted_token,
                "sso_token_expiry": datetime.now() + timedelta(days=7),
            },
        )
        return user

    @sync_to_async
    @transaction.atomic
    def update_repository(self, user: User, repos: dict) -> Repository:
        """Create or update repository"""
        """Bulk insert or update repositories with only basic info."""
        repo_ids = [r["id"] for r in repos]

    # Fetch existing repos for the user
        existing_repos = {
        r.repo_id: r for r in Repository.objects.filter(user=user, repo_id__in=repo_ids)
         }

        to_create = []
        to_update = []

        for repo in repos:
         repo_id = repo["id"]
         defaults = {
            "user": user,
            "node_id": repo["node_id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "private": repo["private"],
            "description": repo.get("description"),
            
        }

        if repo_id in existing_repos:
            # Update existing instance fields
            for field, value in defaults.items():
                setattr(existing_repos[repo_id], field, value)
            to_update.append(existing_repos[repo_id])
        else:
            to_create.append(Repository(repo_id=repo_id, **defaults))

    # Bulk create new repos
        if to_create:
         Repository.objects.bulk_create(to_create, batch_size=100)

    # Bulk update existing repos
        if to_update:
         Repository.objects.bulk_update(
            to_update,
            ["node_id", "name", "full_name", "private", "description", "updated_at"],
            batch_size=100
        )

        return len(to_create), len(to_update)

    async def update_branches(self, access_token: str, repository: Repository):
        """Update branches for a repository"""
        try:
            branches = await self.get_repo_branches(access_token, repository.full_name)
            await self._update_branches_in_db(repository, branches)
        except Exception as e:
            logger.error(f"Failed to update branches for {repository.full_name}: {str(e)}")

    @sync_to_async
    @transaction.atomic
    def _update_branches_in_db(self, repository: Repository, branches: List[dict]):
        """Sync method to update branches in database"""
        # Delete old branches not present anymore
        existing_branches = set(repository.branches.values_list("name", flat=True))
        current_branches = {branch["name"] for branch in branches}
        repository.branches.filter(
            name__in=existing_branches - current_branches
        ).delete()

        # Create or update branches
        for branch in branches:
            commit = branch.get("commit", {})
            Branch.objects.update_or_create(
                repository=repository,
                name=branch["name"],
                defaults={
                    "protected": branch.get("protected", False),
                    "last_commit_sha": commit.get("sha", ""),
                    "last_commit_url": commit.get("url", ""),
                },
            )

    @sync_to_async
    @transaction.atomic
    def _update_permissions(self, repository: Repository, permissions: dict):
        """Update repository permissions"""
        if permissions:
            RepositoryPermission.objects.update_or_create(
                repository=repository,
                defaults={
                    "admin": permissions.get("admin", False),
                    "maintain": permissions.get("maintain", False),
                    "push": permissions.get("push", False),
                    "triage": permissions.get("triage", False),
                    "pull": permissions.get("pull", True),
                },
            )

    @sync_to_async
    @transaction.atomic
    def _update_license(self, repository: Repository, license_data: Optional[dict]):
        """Update repository license"""
        if license_data:
            License.objects.update_or_create(
                repository=repository,
                defaults={
                    "key": license_data.get("key", ""),
                    "name": license_data.get("name", ""),
                    "spdx_id": license_data.get("spdx_id", ""),
                    "url": license_data.get("url"),
                    "node_id": license_data.get("node_id", ""),
                },
            )

    async def _update_topics(self, access_token: str, repository: Repository, repo_name: str):
        """Update repository topics"""
        try:
            topics_response = await self._make_request(
                access_token,
                f"https://api.github.com/repos/{repository.full_name}/topics",
                headers={"Accept": "application/vnd.github.mercy-preview+json"},
            )
            topics = topics_response.get("names", [])
            await self._update_topics_in_db(repository, topics)
        except Exception as e:
            logger.error(f"Failed to update topics for {repo_name}: {str(e)}")

    @sync_to_async
    @transaction.atomic
    def _update_topics_in_db(self, repository: Repository, topics: List[str]):
        """Sync method to update topics in database"""
        # Clear existing topics
        repository.topics.clear()

        # Add new topics
        for topic_name in topics:
            topic, _ = Topic.objects.get_or_create(name=topic_name)
            repository.topics.add(topic)