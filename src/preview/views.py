# src/preview/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from .models import RepositoryCodeState, RepositoryFile
import json
import os, tempfile
import mimetypes
from django.utils._os import safe_join

import re
import base64
from typing import Tuple, Dict

# -----------------------
# HTML/CSS rewrite helpers
# -----------------------

# Rewrite attributes like src="/foo.js" or href="/bar.css" to /preview/<repo_id>/foo.js
_HTML_ABS_ATTR = re.compile(
    r'(?P<attr>\s(?:src|href)=)(?P<q>["\'])/(?P<rest>[^"\']+)(?P=q)',
    re.IGNORECASE
)

def _rewrite_html_urls(html: str, prefix: str) -> str:
    """
    Rewrites <... src="/foo"> to <... src="/preview/<repo_id>/foo">.
    prefix should be something like "/preview/123" (no trailing slash).
    Leaves protocol-relative //... and absolute URLs intact.
    """
    def repl(m):
        rest = m.group('rest')
        # If rest starts with '/', it's likely protocol-relative (//...) -> skip rewriting.
        # (The regex consumed only one leading '/', so protocol-relative will start with '/')
        if rest.startswith('/'):
            return m.group(0)
        return f'{m.group("attr")}{m.group("q")}{prefix}/{rest}{m.group("q")}'
    return _HTML_ABS_ATTR.sub(repl, html)

# Rewrite CSS url('/foo.png') -> url('/preview/<repo_id>/foo.png')
_CSS_URL_ABS = re.compile(r'url\(\s*(?P<q>[\'"]?)/(?P<rest>[^)\'"]+)(?P=q)\s*\)', re.IGNORECASE)

def _rewrite_css_urls(css: str, prefix: str) -> str:
    def repl(m):
        q = m.group('q') or ''
        rest = m.group('rest')
        # If rest starts with '/', it's protocol-relative (//...) -> skip
        if rest.startswith('/'):
            return m.group(0)
        return f'url({q}{prefix}/{rest}{q})'
    return _CSS_URL_ABS.sub(repl, css)

# -----------------------
# Existing StackBlitz redirect view (unchanged)
# -----------------------
@csrf_exempt
def redirect_to_stackblitz(request, repo_id):
    """
    Renders a page that redirects the user to StackBlitz using SDK.
    """
    try:
        code_state = RepositoryCodeState.objects.filter(
            repository_id=repo_id
        ).order_by('-created_at').first()
        
        if not code_state:
            return render(request, 'preview/error.html', {
                'error': 'No code state found for this repository.'
            })

        
        files = code_state.files.all()
        
        files_data = {}
        for file in files:
            # if file.path.endswith('.json'): continue
            files_data[file.path] = file.content
        
        if not files_data:
            files_data['index.html'] = '<h1>No files found.</h1>'

        context = {
            'files_data': json.dumps(files_data),
            'repo_name': code_state.repository.name,
        }

        print(files_data.keys())
        
        # 🌟 This view renders a template, which will contain the JS for redirection.
        return render(request, 'preview/redirect_to_stackblitz.html', context)
        
    except Exception as e:
        return render(request, 'preview/error.html', {
            'error': f'Error preparing redirect to StackBlitz: {str(e)}'
        })


# -----------------------
# Helper: fetch files from DB for latest or specific state
# -----------------------
def fetch_files_from_db(repo_id) -> Tuple[RepositoryCodeState, Dict[str, Dict]]:
    """
    Fetch all files for the latest code state of a repo.
    Returns (code_state, files) where files is a dict:
      { "path/in/repo": { "content": str_or_bytes, "is_binary": bool } }
    """
    code_state = RepositoryCodeState.objects.filter(
        repository_id=repo_id
    ).order_by('-created_at').first()

    if not code_state:
        return None, {}

    files: Dict[str, Dict] = {}
    for f in code_state.files.all():
        files[f.path] = {
            "content": f.content or "",
            "is_binary": getattr(f, "is_binary", False),
        }
    
    # small debug log - remove or replace with proper logger if you want
    print(f"[preview] fetched {len(files)} files for repo_id={repo_id}, state_id={code_state.id}")

    return code_state, files


# -----------------------
# Helper: create (or reuse) per-state temp directory and materialize files
# -----------------------
def get_or_create_tempdir_for_project(code_state: RepositoryCodeState, files: Dict[str, Dict]) -> str:
    """
    Creates a temp dir that is unique for this code_state and writes the files into it.
    We use both repository id and code_state id in the directory name to avoid collisions
    and to ensure updates create a fresh directory (so file additions/removals are visible).
    """
    # base temp folder (system temp)
    base_temp_dir = os.path.join(tempfile.gettempdir(), "repo_previews")
    os.makedirs(base_temp_dir, exist_ok=True)

    # unique folder per repo + code_state
    repo_id = code_state.repository_id if hasattr(code_state, "repository_id") else getattr(code_state, "repository").id
    snapshot_dirname = f"{repo_id}_{code_state.id}"
    project_dir = os.path.join(base_temp_dir, snapshot_dirname)

    # Always (re)create the directory for the snapshot to avoid stale files.
    if os.path.exists(project_dir):
        # Remove old snapshot directory and recreate - this ensures file deletions are reflected
        try:
            # os.remove or shutil.rmtree
            import shutil
            shutil.rmtree(project_dir)
        except Exception:
            pass

    os.makedirs(project_dir, exist_ok=True)

    # Materialize files
    for path, info in files.items():
        # normalize path and prevent absolute paths
        safe_path = path.lstrip("/\\")
        target_path = os.path.join(project_dir, safe_path)
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        content = info.get("content", "")
        is_binary = bool(info.get("is_binary", False))

        try:
            if is_binary:
                # try to decode base64 first (common for storing binaries in text fields)
                try:
                    # If content is already bytes-like, skip decoding
                    if isinstance(content, bytes):
                        data = content
                    else:
                        data = base64.b64decode(content)
                except Exception:
                    # fallback: write the raw string as latin-1 bytes
                    data = (content or "").encode("latin-1")
                with open(target_path, "wb") as fh:
                    fh.write(data)
            else:
                # text mode
                with open(target_path, "w", encoding="utf-8", errors="replace") as fh:
                    fh.write(content or "")
        except Exception as e:
            # fail-safe: write as binary if text write errors
            try:
                with open(target_path, "wb") as fh:
                    if isinstance(content, str):
                        fh.write(content.encode("utf-8", errors="replace"))
                    else:
                        fh.write(content)
            except Exception:
                # last resort: skip file but print debug
                print(f"[preview] failed to write {target_path}: {e}")

    return project_dir


# -----------------------
# Existing repository_files_api (unchanged)
# -----------------------
def repository_files_api(request, repo_id):
    """
    API endpoint to get repository files as JSON.
    """
    try:
        code_state = RepositoryCodeState.objects.filter(
            repository_id=repo_id
        ).order_by('-created_at').first()
        
        if not code_state:
            return JsonResponse({'error': 'Repository not found'}, status=404)
        
        files = code_state.files.all()
        files_data = []
        
        for file in files:
            files_data.append({
                'id': file.id,
                'file_path': getattr(file, 'path', getattr(file, 'file_path', None)),
                'file_name': getattr(file, 'path', None),
                'file_type': file.file_type,
                'size_bytes': file.size_bytes,
                'content': file.content,
                'created_at': file.created_at.isoformat(),
                'updated_at': file.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'repository': code_state.repository.name,
            'commit_hash': getattr(code_state, 'commit_sha', getattr(code_state, 'commit_hash', None)),
            'branch': getattr(code_state, 'branch_id', None),
            'files': files_data,
            'total_files': len(files_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------
# preview index (unchanged)
# -----------------------
def preview_index(request):
    """
    Index page showing available preview options.
    """
    # Get some basic stats
    total_repos = RepositoryCodeState.objects.count()
    total_files = RepositoryFile.objects.count()
    
    context = {
        'total_repos': total_repos,
        'total_files': total_files,
    }
    
    return render(request, 'index.html', context)


# -----------------------
# preview_root and preview_serve (complete)
# -----------------------
def preview_root(request, repo_id):
    """
    Root handler for repo preview:
    - If index.html exists in snapshot, redirect to it
    - Otherwise show file browser for repo root
    """
    code_state, files = fetch_files_from_db(repo_id)
    if not code_state:
        return render(request, "preview/error.html", {
            "error": "No code state found for this repository."
        })

    temp_dir = get_or_create_tempdir_for_project(code_state, files)
    index_path = os.path.join(temp_dir, "index.html")

    if os.path.exists(index_path):
        # Redirect so URL is explicit (/preview/<repo_id>/index.html)
        return redirect("preview:preview_serve", repo_id=repo_id, path="index.html")

    # No index.html → show file browser for root
    try:
        entries = sorted(os.listdir(temp_dir))
    except Exception:
        entries = []

    return render(request, "preview/file_browser.html", {
        "files": entries,
        "repo_id": repo_id,
        "path": "",
    })


def preview_serve(request, repo_id, path=""):
    """
    Serve a file or directory under the repo's preview snapshot.
    - directories -> render file_browser for that dir
    - files -> return with proper Content-Type
      * HTML and CSS are rewritten so leading-/root-absolute links point into /preview/<repo_id>/...
    """
    code_state, files = fetch_files_from_db(repo_id)
    if not code_state:
        return HttpResponse("404 Not Found", status=404)

    temp_dir = get_or_create_tempdir_for_project(code_state, files)

    # normalize path (strip leading slash if any)
    path = (path or "").lstrip("/")

    # safe_join prevents path traversal
    try:
        target_path = safe_join(temp_dir, path)
    except Exception:
        return HttpResponse("Invalid path", status=400)

    # directory -> list
    if os.path.isdir(target_path):
        try:
            entries = sorted(os.listdir(target_path))
        except Exception:
            entries = []
        return render(request, "preview/file_browser.html", {
            "files": entries,
            "repo_id": repo_id,
            "path": path,
        })

    # file -> serve with correct mime
    if os.path.isfile(target_path):
        mime_type, _ = mimetypes.guess_type(target_path)
        if not mime_type:
            # fallback for JS in older Python/mimetypes environments
            if target_path.endswith(".js"):
                mime_type = "application/javascript"
            elif target_path.endswith(".css"):
                mime_type = "text/css"
            elif target_path.endswith(".html") or target_path.endswith(".htm"):
                mime_type = "text/html"
            else:
                mime_type = "application/octet-stream"

        # Text-like files: open as text, rewrite if needed
        text_like = mime_type.startswith("text/") or mime_type in ("application/javascript", "application/json", "image/svg+xml")
        if text_like:
            try:
                with open(target_path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except Exception:
                # fallback to binary read then decode
                with open(target_path, "rb") as fh:
                    content = fh.read().decode("utf-8", errors="replace")

            # If HTML, rewrite absolute src/href to point to preview namespace
            if mime_type == "text/html":
                prefix = f"/preview/{repo_id}"
                content = _rewrite_html_urls(content, prefix)
                # optional: inject <base href> to help relative paths if desired
                # NOTE: injecting base can alter how relative paths resolve - test before enabling
                # if '<base ' not in content.lower():
                #     content = content.replace('<head>', '<head><base href="%s/">' % prefix, 1)

                return HttpResponse(content, content_type=f"{mime_type}; charset=utf-8")

            # If CSS, rewrite url(...) absolute paths
            if mime_type == "text/css":
                prefix = f"/preview/{repo_id}"
                content = _rewrite_css_urls(content, prefix)
                return HttpResponse(content, content_type=f"{mime_type}; charset=utf-8")

            # JS / JSON / SVG text-like
            return HttpResponse(content, content_type=f"{mime_type}; charset=utf-8")

        # Binary -> stream
        try:
            return FileResponse(open(target_path, "rb"), content_type=mime_type)
        except Exception:
            return HttpResponse("Error reading file", status=500)

    return HttpResponse("404 Not Found", status=404)
