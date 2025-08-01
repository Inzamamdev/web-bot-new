import logging
import secrets
from datetime import datetime, timedelta
import asyncio
import time

import httpx
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse
from ninja_extra import api_controller, route
from ninja_jwt.authentication import AsyncJWTAuth

from .models import OAuthState, Repository, Branch
from .schemas import *
from .services.github_service import GitHubService
from telegram_bot.utils import notify_user
from telegram import Bot
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

logger = logging.getLogger(__name__)
github_service = GitHubService()


@api_controller("/auth/github", tags=["GitHub Auth"], auth=None)
class GitHubAuthController:
    @route.get(
        "/login", response={302: None, 400: ErrorResponse}, url_name="github_login"
    )
    async def login(self, request):
        """Initiate GitHub OAuth flow"""
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_REDIRECT_URI:
            return 400, {"detail": "GitHub OAuth not configured", "code": 400}
        
        tg_id = request.GET.get("tg_id")  # ✅ Extract Telegram user ID
        if not tg_id:
         return 400, {"detail": "Missing tg_id in query params", "code": 400}

        scope = "repo,user"
        state = secrets.token_urlsafe(32)

        await OAuthState.objects.acreate(
            state=state, telegram_id=tg_id, expires_at=datetime.now() + timedelta(minutes=10)
        )

        auth_url = (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={settings.GITHUB_CLIENT_ID}&"
            f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
            f"scope={scope}&state={state}"
        )
        return redirect(auth_url)

    @route.get(
        "/callback",
        response={
            200: dict,
            400: ErrorResponse,
            401: ErrorResponse,
            500: ErrorResponse,
        },
    )
    async def callback(self, request):
        """GitHub OAuth callback handler"""
        try:
            state = request.GET.get("state")
            if (
                not state
                or not await OAuthState.objects.filter(
                    state=state, expires_at__gt=datetime.now()
                ).aexists()
            ):
                return 401, {"detail": "Invalid state parameter", "code": 401}

            code = request.GET.get("code")
            if not code:
                return 400, {"detail": "Authorization code missing", "code": 400}
            
             # Get stored state with Telegram ID
            state_obj = await OAuthState.objects.aget(state=state)
            tg_id = state_obj.telegram_id


             # Clean up
            await OAuthState.objects.filter(state=state).adelete()

            # Exchange code for access token
            token_data = {
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            }

            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data=token_data,
                    timeout=10,
                )
                token_response.raise_for_status()
                token_json = token_response.json()

            access_token = token_json.get("access_token")
            if not access_token:
                return 400, {"detail": "Failed to obtain access token", "code": 400}

            start_time = time.perf_counter()

        # Step 1: Get user + repos
            t1 = time.perf_counter()
            logger.info("Access token used: %s", access_token)
            user_data = github_service.get_user_data(access_token)
            repos_task = github_service.get_all_repos(access_token)
            user_data, repos = await asyncio.gather(user_data, repos_task)
            logger.info(f"Fetched user + repos in {time.perf_counter() - t1:.2f}s")

        # Update user
            t2 = time.perf_counter()
            user = await github_service.update_user_data(user_data, access_token)
            user.chat_id = tg_id
            await user.asave(update_fields=["chat_id"])
            logger.info(f"Updated user in {time.perf_counter() - t2:.2f}s")
            
            t3 = time.perf_counter()
            created_count = await github_service.update_repository(user, repos)

            logger.info(f"Repositories synced: {created_count} created")

            logger.info(f"Processed all {len(repos)} repos in {time.perf_counter() - t3:.2f}s")

        # Step 5: Total time
            logger.info(f"TOTAL callback time: {time.perf_counter() - start_time:.2f}s")
            await notify_user(tg_id, "✅ Your repositories have been synced!")
                
            return HttpResponse(
    "<h2>✅ GitHub login successful!</h2>"
    "<p>You can return to Telegram now. Your repositories have been synced.</p>"
)
        
        
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}", exc_info=True)
            return 500, {"detail": "Authentication failed", "code": 500}

    @route.get("/repositories/{user_id}", response=List[RepositorySchema])
    async def list_repositories(self, request, user_id):
        """List all repositories for the authenticated user"""
        repos = []
        async for repo in Repository.objects.filter(user_id=user_id).prefetch_related(
            "branches"
        ):
            branches = []
            async for branch in repo.branches.all():
                branches.append(
                    {
                        "name": branch.name,
                        "protected": branch.protected,
                        "last_commit_sha": branch.last_commit_sha,
                        "last_commit_url": branch.last_commit_url,
                    }
                )

            repos.append(
                {
                    "id": repo.repo_id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "private": repo.private,
                    "description": repo.description,
                    "html_url": repo.html_url,
                    "language": repo.language,
                    "stargazers_count": repo.stargazers_count,
                    "forks_count": repo.forks_count,
                    "open_issues_count": repo.open_issues_count,
                    "branches": branches,
                }
            )

        return repos

    @route.get(
        "/repositories/{int:repo_id}/branches",
        response=List[BranchSchema],
        auth=AsyncJWTAuth(),
    )
    async def get_repo_branches(self, request, repo_id: int):
        """Get branches for a specific repository"""
        repo = await Repository.objects.aget(repo_id=repo_id, user=request.user)
        branches = []
        async for branch in repo.branches.all():
            branches.append(
                {
                    "name": branch.name,
                    "protected": branch.protected,
                    "last_commit_sha": branch.last_commit_sha,
                    "last_commit_url": branch.last_commit_url,
                }
            )
        return branches

    @route.get(
        "/repositories/{int:repo_id}/branches/{str:branch_name}",
        response=BranchSchema,
        auth=AsyncJWTAuth(),
    )
    async def get_branch(self, request, repo_id: int, branch_name: str):
        """Get details for a specific branch"""
        branch = await Branch.objects.aget(
            repository__repo_id=repo_id, repository__user=request.user, name=branch_name
        )
        return {
            "name": branch.name,
            "protected": branch.protected,
            "last_commit_sha": branch.last_commit_sha,
            "last_commit_url": branch.last_commit_url,
        }
