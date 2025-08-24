# web-bot/src/preview/views.py

import json
import urllib.parse
from django.http import HttpResponse
from django.shortcuts import render

# Import your actual models
from .models import RepositoryCodeState, RepositoryFile
from accounts.models import Repository # Need to import Repository from the accounts app

@csrf_exempt
def launch_preview(request, repo_id, commit_hash):
    """
    Renders the HTML page to embed the Stackblitz preview.
    Fetches all files for a specific repository and commit hash.
    """
    try:
        # Step 1: Find the specific code state by repository ID and commit hash
        code_state = RepositoryCodeState.objects.get(
            repository__repo_id=repo_id,
            commit_hash=commit_hash
        )
        
        # Step 2: Retrieve all related files for this code state
        # The related_name 'files' is defined on the RepositoryFile model
        related_files = code_state.files.all()

        # Step 3: Build the files payload dictionary
        files_payload = {}
        for file in related_files:
            files_payload[file.file_path] = file.content
        
        # Step 4: Pass the data to the template context
        context = {
            'files_data': json.dumps(files_payload), # Pass as JSON string
            'repo_name': code_state.repository.name,
            'commit_hash': commit_hash,
        }
        
        # Pass the context to the template
        return render(request, 'preview/templates/preview_embed.html', context)
        
    except RepositoryCodeState.DoesNotExist:
        return HttpResponse("Error: Preview not found for this repository and commit.", status=404)
    except Repository.DoesNotExist:
        return HttpResponse("Error: Repository not found.", status=404)
    except Exception as e:
        # Generic error handling for unexpected issues
        return HttpResponse(f"An unexpected error occurred: {e}", status=500)