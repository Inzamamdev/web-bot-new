import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from ..models import *

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}

    async def _make_request(
        self, access_token: str, url: str, params: dict = None, headers: dict = None
    ) -> dict:
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
                    params={"page": page, "per_page": per_page, "sort": "updated"},
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
            access_token, f"https://api.github.com/repos/{full_name}/branches"
        )

    async def get_repo_topics(self, access_token: str, full_name: str) -> dict:
        """Fetch repository topics"""
        return await self._make_request(
            access_token,
            f"https://api.github.com/repos/{full_name}/topics",
            headers={"Accept": "application/vnd.github.mercy-preview+json"},
        )

    async def update_user_data(self, user_data: dict, access_token: str) -> User:
        """Create or update user from GitHub data"""
        

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
                "access_token": access_token,
                "sso_token_expiry": datetime.now() + timedelta(days=7),
            },
        )
        return user

    async def update_repository(self, user: User, repos: dict) -> List[Repository]:
        """Version that returns created repositories"""
        if not repos:
            return 0

        repo_ids = [r["id"] for r in repos]
        existing_ids = set(
            [
                r.repo_id
                async for r in Repository.objects.filter(
                    user=user, repo_id__in=repo_ids
                )
            ]
        )

        to_create = [
            Repository(
                repo_id=repo["id"],
                user=user,
                node_id=repo["node_id"],
                name=repo["name"],
                full_name=repo["full_name"],
                private=repo["private"],
                description=repo.get("description"),
            )
            for repo in repos
            if repo["id"] not in existing_ids
        ]

        if to_create:
            created = await Repository.objects.abulk_create(to_create, batch_size=100)
            return created
        return []

    async def update_branches(self, access_token: str, repository: Repository):
        """Update branches for a repository"""
        try:
            branches = await self.get_repo_branches(access_token, repository.full_name)
            db_branches = await self._update_branches_in_db(repository, branches)
            return db_branches
        except Exception as e:
            logger.error(f"Failed to update branches for {repository.full_name}: {str(e)}")
            return []

    @sync_to_async
    @transaction.atomic
    async def _update_branches_in_db(self, repository: Repository, branches: List[dict]):

        """Async method to update branches in database using bulk operations and return refreshed objects"""

        existing_branches_query = repository.branches.all()
        existing_branches = {
            branch.name: branch async for branch in existing_branches_query
        }
        current_branch_names = {branch["name"] for branch in branches}
        """Sync method to update branches in database"""
        # Delete old branches not present anymore
        to_delete = [
            name for name in existing_branches if name not in current_branch_names
        ]
        if to_delete:
            await repository.branches.filter(name__in=to_delete).adelete()

        # Prepare batches for bulk operations
        to_create = []
        to_update = []

        for branch in branches:
            branch_name = branch["name"]
            commit = branch.get("commit", {})
            defaults = {
                "protected": branch.get("protected", False),
                "last_commit_sha": commit.get("sha", ""),
                "last_commit_url": commit.get("url", ""),
            }

            if branch_name in existing_branches:
                # Update existing branch
                db_branch = existing_branches[branch_name]
                for field, value in defaults.items():
                    setattr(db_branch, field, value)
                to_update.append(db_branch)
            else:
                # Create new branch
                to_create.append(
                    Branch(repository=repository, name=branch_name, **defaults)
                )

        # Perform bulk operations
        if to_create:
            await Branch.objects.abulk_create(to_create)

        if to_update:
            await Branch.objects.abulk_update(
                to_update, fields=["protected", "last_commit_sha", "last_commit_url"]
            )

        # Refresh all branches from DB to get complete updated instances
        refreshed_branches = [
            branch
            async for branch in repository.branches.filter(
                name__in=current_branch_names
            )
        ]

        return refreshed_branches

    async def _update_permissions(self, repository: Repository, permissions: dict):
        """Update repository permissions using bulk operations"""
        if not permissions:
            return

        # Fetch existing permissions in bulk (usually just 1 record)
        existing_perms = [
            perm
            async for perm in RepositoryPermission.objects.filter(repository=repository)
        ]

        if existing_perms:
            # Bulk update existing records
            for perm in existing_perms:
                perm.admin = permissions.get("admin", False)
                perm.maintain = permissions.get("maintain", False)
                perm.push = permissions.get("push", False)
                perm.triage = permissions.get("triage", False)
                perm.pull = permissions.get("pull", True)

            await RepositoryPermission.objects.abulk_update(
                existing_perms, fields=["admin", "maintain", "push", "triage", "pull"]
            )
        else:
            # Bulk create new record (even if just one)
            new_perms = RepositoryPermission(
                repository=repository,
                admin=permissions.get("admin", False),
                maintain=permissions.get("maintain", False),
                push=permissions.get("push", False),
                triage=permissions.get("triage", False),
                pull=permissions.get("pull", True),
            )
            await RepositoryPermission.objects.abulk_create([new_perms])

    async def _update_license(
        self, repository: Repository, license_data: Optional[dict]
    ):
        """Alternative with bulk operations (less optimal for this case)"""
        if not license_data:
            return

        defaults = {
            "key": license_data.get("key", ""),
            "name": license_data.get("name", ""),
            "spdx_id": license_data.get("spdx_id", ""),
            "url": license_data.get("url"),
            "node_id": license_data.get("node_id", ""),
        }

        existing_licenses = [
            license_obj
            async for license_obj in License.objects.filter(repository=repository)
        ]

        if existing_licenses:
            for license_obj in existing_licenses:
                for field, value in defaults.items():
                    setattr(license_obj, field, value)
            await License.objects.abulk_update(
                existing_licenses, fields=["key", "name", "spdx_id", "url", "node_id"]
            )
        else:
            await License.objects.abulk_create(
                [License(repository=repository, **defaults)]
            )

    async def _update_topics(
        self, access_token: str, repository: Repository, repo_name: str
    ):
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

    async def _update_topics_in_db(self, repository: Repository, topics: List[str]):
        """Async method to update topics in database using bulk operations"""
        if not topics:
            await repository.topics.aclear()
            return

        # Clear existing topics
        await repository.topics.aclear()

        # Get existing topics in bulk
        existing_topics = {
            topic.name: topic async for topic in Topic.objects.filter(name__in=topics)
        }

        # Identify topics that need to be created
        topics_to_create = [name for name in topics if name not in existing_topics]

        # Bulk create missing topics
        if topics_to_create:
            new_topics = await Topic.objects.abulk_create(
                [Topic(name=name) for name in topics_to_create]
            )
            existing_topics.update({topic.name: topic for topic in new_topics})

        # Bulk add all topics to repository
        topic_objects = [existing_topics[name] for name in topics]
        await repository.topics.aadd(*topic_objects)

    async def fetch_codebase(self, repository, owner, branch, access_token):
        try:
            return await self._make_request(
                access_token,
                f"https://api.github.com/repos/{owner}/{repository}/git/trees/{branch}",
            )
        except Exception as e:
            logger.error(f"Failed to fetch codebase for {repository}: {str(e)}")
