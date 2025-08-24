from .models import *
import httpx
import base64
import asyncio
import logging

async def _make_request(
    access_token: str, url: str, params: dict = None, headers: dict = None
) -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    """Async helper method to make GitHub API requests"""
    if headers is None:
        headers = {**headers, "Authorization": f"Bearer {access_token}"}
    else:
        headers = {**headers, "Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()


async def get_file_content(owner, repo, path, ref, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    try:
        data = await _make_request(url=url, access_token=token)
        if data.get("encoding") == "base64":
            decoded = base64.b64decode(data["content"])
            try:
                decoded_text = decoded.decode("utf-8")
                return decoded_text, False  # not binary
            except UnicodeDecodeError:
                return None, True  # binary file
        return None, True
    except Exception as e:
        logging.error(f"Failed to fetch content for {path}: {str(e)}")
        return None, True


async def _fetch_contents(owner, repo, paths, branch_name, github_token):
    """Fetch multiple file contents in parallel"""
    tasks = [
        get_file_content(owner, repo, path, branch_name, github_token) for path in paths
    ]
    return await asyncio.gather(*tasks)


async def create_initial_snapshot(user, repo_obj, branch_obj, commit_sha, github_token):
    owner = user.github_login
    repo = repo_obj.name

    # Create initial code state
    code_state = await RepositoryCodeState.objects.acreate(
        repository=repo_obj,
        branch=branch_obj,
        commit_sha=commit_sha,
        is_initial=True,
    )

    # Get repo tree (recursive)
    tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1"
    tree_data = await _make_request(url=tree_url, access_token=github_token)

    # Collect all file paths first
    file_paths = [
        item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"
    ]

    # Fetch all contents in parallel
    contents = await _fetch_contents(
        owner, repo, file_paths, branch_obj.name, github_token
    )

    # Prepare files for bulk creation
    files_to_create = [
        RepositoryFile(
            code_state=code_state,
            path=path,
            content=content if not is_binary else None,
            is_binary=is_binary,
            change_type="added",
        )
        for path, (content, is_binary) in zip(file_paths, contents)
    ]

    # Bulk create all files
    await RepositoryFile.objects.abulk_create(files_to_create)
    return code_state


async def create_incremental_snapshot(
    user, repo_obj, branch_obj, old_sha, new_sha, github_token
):
    owner = user.github_login
    repo = repo_obj.name

    # Get changed files list
    compare_url = (
        f"https://api.github.com/repos/{owner}/{repo}/compare/{old_sha}...{new_sha}"
    )
    compare_data = await _make_request(url=compare_url, access_token=github_token)

    # Create new code state
    code_state = await RepositoryCodeState.objects.acreate(
        repository=repo_obj,
        branch=branch_obj,
        commit_sha=new_sha,
        is_initial=False,
    )

    # Separate files by type for parallel fetching
    modified_files = [
        f["filename"]
        for f in compare_data.get("files", [])
        if f["status"] in ("added", "modified")
    ]
    removed_files = [
        f["filename"] for f in compare_data.get("files", []) if f["status"] == "removed"
    ]

    # Fetch contents in parallel only for modified/added files
    contents = await _fetch_contents(
        owner, repo, modified_files, branch_obj.name, github_token
    )

    # Prepare files for bulk creation
    files_to_create = [
        RepositoryFile(
            code_state=code_state,
            path=path,
            content=content if not is_binary else None,
            is_binary=is_binary,
            change_type="modified",  # Will be updated below
        )
        for path, (content, is_binary) in zip(modified_files, contents)
    ]

    # Add removed files
    files_to_create.extend(
        RepositoryFile(
            code_state=code_state,
            path=path,
            content=None,
            is_binary=False,
            change_type="removed",
        )
        for path in removed_files
    )

    # Set correct change types (since we separated files earlier)
    file_status_map = {
        f["filename"]: f["status"] for f in compare_data.get("files", [])
    }
    for file in files_to_create:
        file.change_type = file_status_map[file.path]

    # Bulk create all files
    await RepositoryFile.objects.abulk_create(files_to_create)
    return code_state


async def update_codebase(user, repo_obj, branch_obj, commit_sha, github_token):
    code_state = await RepositoryCodeState.objects.filter(
        repository=repo_obj, branch=branch_obj
    ).afirst()
    # if code_state:
    #     await RepositoryCodeState.objects.filter(
    #         repository=repo_obj, branch=branch_obj
    #     ).adelete()

    if not code_state:
        return await create_initial_snapshot(
            user, repo_obj, branch_obj, commit_sha, github_token
        )
    if code_state.commit_sha != commit_sha:
        return await create_incremental_snapshot(
            user, repo_obj, branch_obj, code_state.commit_sha, commit_sha, github_token
        )
