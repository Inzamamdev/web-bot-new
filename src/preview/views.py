from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import RepositoryCodeState, RepositoryFile
import json


def preview_embed(request, repo_id):
    """
    Render the preview embed template for a specific repository.
    """
    try:
        # Get the latest code state for the repository
        code_state = RepositoryCodeState.objects.filter(
            repository_id=repo_id
        ).order_by('-created_at').first()
        
        if not code_state:
            return render(request, 'preview/error.html', {
                'error': 'No code state found for this repository'
            })
        
        # Get all files for this code state
        files = code_state.files.all()
        
        # Prepare files data for StackBlitz
        files_data = {}
        for file in files:
            files_data[file.file_path] = file.content
        
        # Ensure we have an index.html file
        if 'index.html' not in files_data:
            # Try to find any HTML file to use as index
            html_files = [f for f in files if f.file_type == 'html']
            if html_files:
                # Use the first HTML file as index
                first_html = html_files[0]
                files_data['index.html'] = first_html.content
        
        context = {
            'repo_name': code_state.repository.name,
            'files_data': json.dumps(files_data),
            'code_state': code_state,
        }
        
        return render(request, 'preview_embed.html', context)
        
    except Exception as e:
        return render(request, 'preview/error.html', {
            'error': f'Error loading preview: {str(e)}'
        })


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
                'file_path': file.file_path,
                'file_name': file.file_name,
                'file_type': file.file_type,
                'size_bytes': file.size_bytes,
                'content': file.content,
                'created_at': file.created_at.isoformat(),
                'updated_at': file.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'repository': code_state.repository.name,
            'commit_hash': code_state.commit_hash,
            'branch': code_state.branch_id,
            'files': files_data,
            'total_files': len(files_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def simple_preview(request, repo_id):
    """
    Render a simple preview without StackBlitz dependency.
    """
    try:
        # Get the latest code state for the repository
        code_state = RepositoryCodeState.objects.filter(
            repository_id=repo_id
        ).order_by('-created_at').first()
        
        if not code_state:
            return render(request, 'preview/error.html', {
                'error': 'No code state found for this repository'
            })
        
        # Get all files for this code state
        files = code_state.files.all()
        
        # Find HTML content for the iframe
        html_content = ""
        html_files = [f for f in files if f.file_type == 'html']
        if html_files:
            html_file = next((f for f in html_files if f.file_name == 'index.html'), html_files[0])
            html_content = html_file.content
            
            # Inject CSS and JS into HTML
            css_files = [f for f in files if f.file_type == 'css']
            js_files = [f for f in files if f.file_type == 'js']
            
            # Add CSS
            for css_file in css_files:
                if '</head>' in html_content:
                    html_content = html_content.replace('</head>', f'<style>{css_file.content}</style></head>')
                else:
                    html_content = f'<style>{css_file.content}</style>' + html_content
            
            # Add JS
            for js_file in js_files:
                if '</body>' in html_content:
                    html_content = html_content.replace('</body>', f'<script>{js_file.content}</script></body>')
                else:
                    html_content = html_content + f'<script>{js_file.content}</script>'
        
        context = {
            'repo_name': code_state.repository.name,
            'files': files,
            'html_content': html_content,
            'code_state': code_state,
        }
        
        return render(request, 'simple_preview.html', context)
        
    except Exception as e:
        return render(request, 'preview/error.html', {
            'error': f'Error loading simple preview: {str(e)}'
        })


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
