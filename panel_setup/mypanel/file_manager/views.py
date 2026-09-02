import os
import zipfile
import tarfile
import gzip
import shutil
from django.utils.timezone import now
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import * 
from users.server_core import *  # Import your function
from users.database import *  # Import your function
from django.db import connection
from users.function import *  # Import your function
from django.contrib.auth.hashers import make_password
from .function_file import *
from django.http import JsonResponse, FileResponse
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from urllib.parse import urlparse, unquote
from whm.decorators import * 

@login_required
def home(request):
    user_settings = UserSettings.objects.filter(userid=request.user.id).first()
    
    # Prepare settings dictionary (handle case if user_settings is None)
    settings_data = {
        'font_size': user_settings.font_size if user_settings else '14',
        'hide_hiden_file': user_settings.hide_hiden_file if user_settings else 0,
        'hide_folder_size': user_settings.hide_folder_size if user_settings else 0,
        'two_step': user_settings.two_step if user_settings else 0,
        'api': user_settings.api if user_settings else 0,
    }
    
    return render(request, 'file_manager/file_manager.html', {'my_settings': settings_data})

    
    
def get_ace_editor_mode(file_path):
    if not file_path:
        return 'text'
    file_name = os.path.basename(file_path).lower()
    
    if file_name.startswith('.'):
        name_part = file_name.lstrip('.')
        if name_part in ('env', 'ini', 'conf', 'cnf', 'properties', 'env.example', 'env.local', 'env.production'):
            return 'ini'
        elif name_part == 'htaccess':
            return 'apache_conf'
        elif name_part in ('gitignore', 'npmignore', 'dockerignore'):
            return 'ini'
            
    ext = os.path.splitext(file_name)[1].lower().lstrip('.')
    if not ext and '.' in file_name:
        ext = file_name.split('.')[-1].lower()

    mode_map = {
        'js': 'javascript',
        'mjs': 'javascript',
        'cjs': 'javascript',
        'ts': 'javascript',
        'jsx': 'javascript',
        'tsx': 'javascript',
        'json': 'json',
        'py': 'python',
        'php': 'php',
        'phtml': 'php',
        'php3': 'php',
        'php4': 'php',
        'php5': 'php',
        'php7': 'php',
        'php8': 'php',
        'html': 'html',
        'htm': 'html',
        'css': 'css',
        'scss': 'css',
        'less': 'css',
        'sql': 'sql',
        'mysql': 'mysql',
        'xml': 'xml',
        'svg': 'svg',
        'dart': 'dart',
        'java': 'java',
        'htaccess': 'apache_conf',
        'apache_conf': 'apache_conf',
        'conf': 'ini',
        'cnf': 'ini',
        'ini': 'ini',
        'env': 'ini',
        'properties': 'ini',
        'sh': 'ini',
        'bash': 'ini',
        'txt': 'text',
        'log': 'text',
        'md': 'text',
    }
    return mode_map.get(ext, 'text')


@login_required
def php_editor(request):
    user_settings = UserSettings.objects.filter(userid=request.user.id).first()
    
    # Prepare settings dictionary (handle case if user_settings is None)
    settings_data = {
        'font_size': user_settings.font_size if user_settings else '13',
        'hide_hiden_file': user_settings.hide_hiden_file if user_settings else 0,
        'hide_folder_size': user_settings.hide_folder_size if user_settings else 0,
        'two_step': user_settings.two_step if user_settings else 0,
        'api': user_settings.api if user_settings else 0,
    }
    
    file = request.GET.get('file')
    if not file and request.method == 'POST':
        file = request.POST.get('file') or request.GET.get('file')
    if not file:
        return redirect('/')
    username_string = request.user.username
    file = remove_home_anyname(file)
    base_dir = f'/home/{username_string}/'
    file_path = os.path.join(base_dir, file.lstrip('/'))
    file_path = ensure_user_home_prefix(file_path, username_string)
    file_path = os.path.abspath(os.path.join(base_dir, file.lstrip('/')))
    if not file_path.startswith(base_dir):
        return JsonResponse({'status': 'error', 'message': 'Access denied.'}, status=403)
    file_name = os.path.basename(file_path)
    ext = get_ace_editor_mode(file_path)

    # Handle POST request to save the file content
    if request.method == 'POST':
        new_content = request.POST.get('content')
        
        # Check if content is provided
        if new_content is None:
            return JsonResponse({'status': 'error', 'message': 'No content provided.'}, status=400)
        
        try:
            # Save the updated content with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            if file_name == '.htaccess':
                auto_restart_litespeed = int(AppSettings.objects.filter(setting_key='auto_restart_litespeed').values_list('setting_value', flat=True).first() or 0)        
                if auto_restart_litespeed == 1:
                    restart_openlitespeed()
                
            return JsonResponse({'status': 'success', 'message': 'File saved successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Error saving file: {str(e)}"}, status=500)

    # Handle GET request to display the file content
    #ext = os.path.splitext(file_path)[1].lower().lstrip('.')

           
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect('/')

    return render(request, 'file_manager/code_editor.html', {
        'ext': ext,
        'file': file_path,
        'name': os.path.basename(file),
        'base_url': base_url,
        'content': content,
        'my_settings': settings_data
    })
    



@login_required
def view(request):
    file = request.GET.get('file')
    if not file:
        return JsonResponse({'status': 'error', 'message': 'No file specified.'}, status=400)

    username_string = request.user.username
    file = remove_home_anyname(file)
    base_dir = f'/home/{username_string}/'
    file_path = os.path.abspath(os.path.join(base_dir, file.lstrip('/')))
    file_path = ensure_user_home_prefix(file_path, username_string)
    base_url = f"{request.scheme}://{request.get_host()}"

    if not file_path.startswith(base_dir) or not os.path.isfile(file_path):
        return JsonResponse({'status': 'error', 'message': 'Access denied or file not found.'}, status=403)

    # Save file content via AJAX
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        new_content = request.POST.get('content')
        has_permission, message = check_file_permission(file_path, username_string)
        if not has_permission:
            return JsonResponse({'status': 'error', 'message': message}, status=403)
        if new_content is None:
            return JsonResponse({'status': 'error', 'message': 'No content provided.'}, status=400)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return JsonResponse({'status': 'success', 'message': 'File saved.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # File extension
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if ext == 'js':
        ext = 'javascript'

    # Supported image extensions
    image_exts = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg']
    is_image = ext in image_exts

    try:
        if is_image:
            # For images, just pass the path to be used in <img src="">
            file_url = f"/file_manager/media_viewer/?path={file}"  # assumes you have a media_viewer view
            return render(request, 'file_manager/image_view.html', {
                'file_url': file_url,
                'name': os.path.basename(file),
                'ext': ext
            })
        else:
            # For text/code files
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return render(request, 'file_manager/view.html', {
                'ext': ext,
                'file': file_path,
                'base_url': base_url,
                'name': os.path.basename(file),
                'content': content
            })
    except Exception as e:
        messages.error(request, f"Error reading file: {e}")
        return redirect('/')

    

@login_required
def file_folder_list(request):
    user_settings = UserSettings.objects.filter(userid=request.user.id).first()
    folder_zise_hide = user_settings.hide_folder_size if user_settings else 0
    hiden_file = user_settings.hide_hiden_file if user_settings else 0
    directory = request.GET.get('directory', '')
    username_string = request.user.username
    base_dir = os.path.abspath(f'/home/{username_string}/')
    
    # Normalize the requested directory
    requested_path = os.path.abspath(os.path.join(base_dir, directory.strip('/')))

    # 🔒 Security check
    if not requested_path.startswith(base_dir):
        return JsonResponse({'status': 'error', 'message': 'Access denied.'}, status=403)

    if not os.path.exists(requested_path) or not os.path.isdir(requested_path):
        return JsonResponse({'status': 'error', 'message': 'Directory does not exist or is not accessible.'}, status=404)

    extension_icons = {
        'php': '/media/icon/phpcode.svg', 'html': '/media/icon/html.svg', 'txt': '/media/icon/text.svg',
        'text': '/media/icon/text.svg', 'zip': '/media/icon/zip.svg', 'tar': '/media/icon/zip.svg',
        'gz': '/media/icon/zip.svg', 'rar': '/media/icon/zip.svg', '7z': '/media/icon/zip.svg',
        'jpg': '/media/icon/image.svg', 'jpeg': '/media/icon/image.svg', 'png': '/media/icon/image.svg',
        'gif': '/media/icon/image.svg', 'bmp': '/media/icon/image.svg', 'webp': '/media/icon/image.svg',
        'tiff': '/media/icon/image.svg', 'ico': '/media/icon/image.svg', 'svg': '/media/icon/image.svg',
        'mp3': '/media/icon/audio.svg', 'wav': '/media/icon/audio.svg', 'flac': '/media/icon/audio.svg',
        'mp4': '/media/icon/video.svg', 'avi': '/media/icon/video.svg', 'mov': '/media/icon/video.svg',
        'mkv': '/media/icon/video.svg', 'webm': '/media/icon/video.svg',
    }
    default_file_icon = '/media/icon/other.svg'
    folder_icon = '/media/icon/folder-file.svg'
    public_html_icon = '/media/icon/public.svg'

    try:
        entries = []
        with os.scandir(requested_path) as it:
            for entry in it:
                if hiden_file == 1 and entry.name.startswith('.'):
                    continue
                    
                if entry.is_dir():
                    icon = public_html_icon if entry.name == 'public_html' else folder_icon
                    if folder_zise_hide==0:
                        size_display_value = size_display(get_folder_size(entry.path))
                    else:
                        size_display_value = size_display(entry.stat().st_size)
                        
                    
                    file_extension = 'folder'
                else:
                    file_extension = entry.name.split('.')[-1].lower()
                    icon = extension_icons.get(file_extension, default_file_icon)
                    size_display_value = size_display(entry.stat().st_size)

                permissions = oct(entry.stat().st_mode)[-3:]
                entries.append({
                    'name': entry.name,
                    'is_dir': entry.is_dir(),
                    'path': os.path.relpath(os.path.join(requested_path, entry.name), base_dir),
                    'size': size_display_value,
                    'modified_time': datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                    'permissions': permissions,
                    'icon': icon,
                    'extension': file_extension
                })

        entries.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return JsonResponse({'status': 'success', 'entries': entries})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Error listing directory: {str(e)}"}, status=500)
        
@login_required
def folder_list(request):
    directory = request.GET.get('directory', '')
    username_string = request.user.username
    base_dir = os.path.abspath(f'/home/{username_string}/')
    
    # Safely join and normalize
    requested_path = os.path.abspath(os.path.join(base_dir, directory))

    # 🚨 Security check: ensure user can't break out of their base folder
    if not requested_path.startswith(base_dir):
        return JsonResponse({'status': 'error', 'message': 'Access denied.'}, status=403)

    # Check if valid directory
    if not os.path.exists(requested_path) or not os.path.isdir(requested_path):
        return JsonResponse({'status': 'error', 'message': 'Directory does not exist or is not accessible.'}, status=404)

    try:
        entries = []
        with os.scandir(requested_path) as it:
            for entry in it:
                if entry.is_dir():
                    entries.append({
                        'name': entry.name,
                        'is_dir': True,
                        'path': os.path.relpath(os.path.join(requested_path, entry.name), base_dir),
                    })
        entries.sort(key=lambda x: x['name'].lower())
        return JsonResponse({'status': 'success', 'entries': entries})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Error listing directory: {str(e)}"}, status=500)
        
        
        
@login_required
def file_action(request):
    # Get parameters from the POST request
    action = request.POST.get('action', '').strip().lower()  # Convert to lowercase
    file_name = request.POST.get('file_name', '').strip()
    target_name = request.POST.get('target_name', '').strip()  # For rename, copy, move
    permissions = request.POST.get('permission', '000')
    selected_items = request.POST.getlist('selected_items[]')
    parent = request.POST.get('base', '').strip()  # For rename, copy, move
    if target_name == '/' or target_name == '':
        target_name = ''
    elif target_name.startswith('/'):
        target_name = target_name[1:]
        
    if file_name.startswith('/'):
        file_name = file_name[1:]    
        
        
    username_string = request.user.username
    base_dir = f'/home/{username_string}/'  # Default base directory
    file_path = os.path.join(base_dir, file_name)
    target_path = os.path.join(base_dir, target_name) if target_name else None
    if not target_path:
        target_path = base_dir
        
    #return JsonResponse({'status': 'error', 'message': f"File {target_path}"}, status=404)
    target_path = ensure_user_home_prefix(target_path,username_string)
     
    # Check permissions
    has_permission, message = check_file_folder_permission(base_dir, username_string)
    if not has_permission:
        return JsonResponse({'status': 'error', 'message': message}, status=403)

    if action not in ['new_file', 'new_folder'] and not os.path.exists(file_path):
        return JsonResponse({'status': 'error', 'message': 'File or folder does not exist.'}, status=404)

    try:
        # Action handling
        if action == 'rename':
            if target_path and os.path.exists(target_path):
                return JsonResponse({'status': 'error', 'message': 'Target name already exists.'}, status=400)
            os.rename(file_path, target_path)
            return JsonResponse({'status': 'success', 'message': 'Renamed successfully.'})

        elif action == 'delete':
            if selected_items:
                for file_source in selected_items:
                    
                    message = f_delete(username_string, file_source)
                    #if message.startswith("Error"):
                        #return JsonResponse({'status': 'error', 'message': file_target+' '+message})

            else: 
                message = f_delete(username_string, file_name)
                if message.startswith("Error"):
                    return JsonResponse({'status': 'error', 'message': message})
                    
            return JsonResponse({'status': 'success', 'message': 'Deleted successfully.'})
            
        elif action == 'fix-permission':
            def should_skip(path):
                return not path or os.path.abspath(path) in [f"/home/{username_string}", f"/home/{username_string}/"]
        
            
            if selected_items:
                for file_source in selected_items:
                    if should_skip(file_source_path):
                        continue  
                    file_source_path = os.path.join(base_dir, file_source)
                    set_permissions_and_ownership(file_source_path, username_string)   
                   
            else: 
                if should_skip(file_path):
                    return JsonResponse({'status': 'error', 'message': "Skipping /home/user permission change."})
                
                set_permissions_and_ownership(file_path, username_string)
                if message.startswith("Error"):
                    return JsonResponse({'status': 'error', 'message': message})
                    
            return JsonResponse({'status': 'success', 'message': f"Permission set successfully."})            
            
        elif action == 'permission':
            
            try:
                # Parse permissions (e.g., "740" -> user=7, group=4, world=0)
                user = int(permissions[0])  # First digit
                group = int(permissions[1])  # Second digit
                world = int(permissions[2])  # Third digit

                # Calculate the permission value
                permission = (user << 6) | (group << 3) | world

                # Set the permissions on the file
                os.chmod(file_path, permission)
                return JsonResponse({'status': 'success', 'message': 'Permissions set successfully.'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Failed to set permissions: {e}'+permissions})
                  
            
            
        elif action == 'new_file':
            if not is_valid_filename(os.path.basename(target_path)):
                return JsonResponse({'status': 'error', 'message': 'Invalid file name.'}, status=400)
        

            
            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                    return JsonResponse({'status': 'error', 'message': 'The folder already exists.'}, status=400)
                else:
                    return JsonResponse({'status': 'error', 'message': 'A file with the same name already exists.'}, status=400)                    
           
            # Create a new file
            with open(target_path, 'w') as f:
                f.write('')  # Create an empty file
                
              
            set_permissions_and_ownership(target_path, username_string)    
            return JsonResponse({'status': 'success', 'message': 'File created successfully.'})

        elif action == 'new_folder':
            if not is_valid_filename(os.path.basename(target_path)):
                return JsonResponse({'status': 'error', 'message': 'Invalid folder name.'}, status=400)
        

            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                    return JsonResponse({'status': 'error', 'message': 'The folder already exists.'}, status=400)
                else:
                    return JsonResponse({'status': 'error', 'message': 'A file with the same name already exists.'}, status=400)                    
            
            
            os.makedirs(target_path, exist_ok=True)
            set_permissions_and_ownership(target_path,username_string)
            return JsonResponse({'status': 'success', 'message': 'Folder created successfully.'})
            
        elif action == 'copy':
            if selected_items:
                for file_source in selected_items:
                    
                    message = f_copy(username_string, file_source, target_name)
                    #if message.startswith("Error"):
                        #return JsonResponse({'status': 'error', 'message': file_target+' '+message})

            else: 
                message = f_copy(username_string, file_name, target_name)
                if message.startswith("Error"):
                    return JsonResponse({'status': 'error', 'message': message})
            
            return JsonResponse({'status': 'success', 'message': 'Copied successfully.'})

        elif action == 'move':
            if selected_items:
                for file_source in selected_items:
                    
                    message = f_move(username_string, file_source, target_name)
                    #if message.startswith("Error"):
                        #return JsonResponse({'status': 'error', 'message': file_target+' '+message})

            else: 
                message = f_move(username_string, file_name, target_name)
                if message.startswith("Error"):
                    return JsonResponse({'status': 'error', 'message': message})
                    
            return JsonResponse({'status': 'success', 'message': 'Moved successfully.'})
            
        elif action == 'trash':
            trash_folder = os.path.join(base_dir, '.trash')
            if not os.path.exists(trash_folder):
                os.makedirs(trash_folder, exist_ok=True)
                set_permissions_and_ownership(trash_folder, username_string)
        
        
                
                    
    
            if selected_items:
                for file_source in selected_items:                    
                    message = f_move(username_string, file_source, '.trash')
                    if message.startswith("Error"):
                        return JsonResponse({'status': 'error', 'message': message})

            else: 
                message = f_move(username_string, file_name, target_name)
                if message.startswith("Error"):
                    return JsonResponse({'status': 'error', 'message': message})
                    
            return JsonResponse({'status': 'success', 'message': 'Trash successfully.'})
    

        elif action == 'unzip':
            try:
                extracted_items = []

                if file_name.endswith('.zip'):
                    with zipfile.ZipFile(file_path, 'r') as archive:
                        archive.extractall(target_path)
                        extracted_items = archive.namelist()

                elif file_name.endswith('.tar.gz') or file_name.endswith('.tgz'):
                    with tarfile.open(file_path, 'r:gz') as archive:
                        archive.extractall(target_path)
                        extracted_items = archive.getnames()
                
                elif file_name.endswith('.gz') and not file_name.endswith('.tar.gz'):
                    import gzip
                    output_file = os.path.join(
                        target_path,
                        os.path.basename(file_name[:-3])
                    )

                    with gzip.open(file_path, 'rb') as f_in:
                        with open(output_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    extracted_items = [os.path.basename(output_file)]
                
                
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Only .zip, .tar.gz and .tgz files can be extracted.'
                    }, status=400)

                # Set ownership and permissions for extracted files and directories
                for item in extracted_items:
                    extracted_path = os.path.join(target_path, item)
                    if os.path.exists(extracted_path):
                        set_permissions_and_ownership(extracted_path, username_string)

                return JsonResponse({
                    'status': 'success',
                    'message': 'Archive extracted and ownership set successfully.'
                })

            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Error during extraction: {str(e)}"
                }, status=500)
                
                
                
                
        elif action == 'compress':
            
            message = f_compress(username_string,parent, file_name, target_name, selected_items)
            #if message.startswith("Error"):
                #return JsonResponse({'status': 'error', 'message': message})
            return JsonResponse({'status': 'success', 'message': 'Compress successfully.'})
            
       

        
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Error performing action: {str(e)}"}, status=500)
        
        
@login_required
def download(request):
    try:
        # Get the file parameter and user info
        file = request.GET.get('file')
        if not file:
            return JsonResponse({'status': 'error', 'message': 'No file specified.'}, status=400)

        username_string = request.user.username

        # Sanitize and validate the file path
        file = remove_home_anyname(file)
        base_dir = f'/home/{username_string}/'
        file_path = os.path.join(base_dir, file.lstrip('/'))
        file_path = ensure_user_home_prefix(file_path, username_string)

        # Verify that the file is within the user's home directory
        if not file_path.startswith(base_dir):
            return JsonResponse({'status': 'error', 'message': 'Unauthorized access.'}, status=403)

        # Check if the file exists
        if not os.path.exists(file_path):
            return JsonResponse({'status': 'error', 'message': 'File not found.'}, status=404)

        # Open and serve the file as a download
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response

    except Exception as e:
        # Handle unexpected errors
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)
        
        
@login_required
def upload(request):
    if request.method == 'POST' and 'file' in request.FILES:
        # Get the uploaded file and other request data
        uploaded_file = request.FILES['file']  # For single file uploads
        target_name = request.POST.get('target_name', '').strip()  # For renaming, copying, moving
        user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
        disk_space_in_bytes = user_package.disk_space * 1024 * 1024
            
            

        # Ensure target_name does not start with a slash
        if target_name.startswith('/'):
            target_name = target_name[1:]

        # Define base directory and construct the target path
        username_string = request.user.username
        database_names = get_user_database_info(username_string)
        total_size = calculate_total_database_size(database_names)
        disk = get_disk_usage(f'/home/{username_string}')
        email_disk = get_disk_usage(f'/home/vmail/{username_string}')
        disk_in_bytes = human_readable_to_bytes(disk)
        email_disk_in_bytes = human_readable_to_bytes(email_disk)
        total_size_in_bytes = disk_in_bytes + total_size + email_disk_in_bytes + uploaded_file.size
        if user_package.disk_space != 0 and total_size_in_bytes > disk_space_in_bytes:
            return JsonResponse({'status': 'error','message': 'Disk quota exceeded. Please upgrade your package or free up space.'}, status=403)
        
        
       
        base_dir = f'/home/{username_string}/'
        target_path = os.path.join(base_dir, target_name) if target_name else base_dir
        target_path = ensure_user_home_prefix(target_path, username_string)

        # Check permissions
        has_permission, message = check_file_folder_permission(base_dir, username_string)
        if not has_permission:
            return JsonResponse({'status': 'error', 'message': message}, status=403)

        # Ensure target path exists
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Save the file to the target directory
        fs = FileSystemStorage(location=target_path)
        file_path = os.path.join(target_path, uploaded_file.name)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
        
        
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = os.path.join(target_path, filename)
        file_url = fs.url(filename)
        set_permissions_and_ownership(file_path, username_string)

        # Respond with success and file details
        response_data = {
            'status': 'success',
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_url': file_url
        }
        return JsonResponse(response_data, status=200)

    # Handle error if no file is uploaded
    return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)
   
    
    
@login_required
def upload_db(request, db_name):
    if request.method == 'POST' and 'file' in request.FILES:
        # Get the uploaded file and other request data
        uploaded_file = request.FILES['file']  # For single file uploads
        target_name = 'tmp'  # Temporary name for the upload folder

        # Ensure target_name does not start with a slash
        if target_name.startswith('/'):
            target_name = target_name[1:]

        # Define base directory and construct the target path
        username_string = request.user.username
        base_dir = f'/home/{username_string}/'  # Default base directory
        target_path = os.path.join(base_dir, target_name) if target_name else base_dir
        target_path = ensure_user_home_prefix(target_path, username_string)
        
        # Create the target path if it doesn't exist
        if not os.path.exists(target_path):
            os.makedirs(target_path)
            set_permissions_and_ownership(target_path, username_string)

        # Check permissions for the folder
        has_permission, message = check_file_folder_permission(base_dir, username_string)
        if not has_permission:
            return JsonResponse({'status': 'error', 'message': message}, status=403)

        # Save the file to the target directory
        filenamex, file_extension = os.path.splitext(uploaded_file.name)
        timestamp = now().strftime('%Y%m%d_%H%M%S')+''+file_extension
        fs = FileSystemStorage(location=target_path)
        filename = fs.save(timestamp, uploaded_file)
        file_path = os.path.join(target_path, filename)
        file_url = fs.url(filename)
        set_permissions_and_ownership(file_path, username_string)

        # Now that the file is uploaded, proceed with importing the database
        try:
            # You can implement the database import logic here
            import_database(username_string, file_path, db_name)

            # Respond with success and file details
            response_data = {
                'status': 'success',
                'file_name': uploaded_file.name,
                'file_size': uploaded_file.size,
                'file_url': file_url
            }
            return JsonResponse(response_data, status=200)

        except Exception as e:
            # Handle database import error
            return JsonResponse({'status': 'error', 'message': f"Error importing database: {str(e)}"}, status=500)

    # Handle error if no file is uploaded
    return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400) 


@login_required
def export_db(request, db_name):
    # Set a temporary name for the upload folder
    target_name = 'tmp'

    # Ensure the target name does not start with a slash
    if target_name.startswith('/'):
        target_name = target_name[1:]

    # Define base directory and construct the target path
    username_string = request.user.username
    base_dir = f'/home/{username_string}/'  # Default base directory
    target_path = os.path.join(base_dir, target_name) if target_name else base_dir
    target_path = ensure_user_home_prefix(target_path, username_string)
    
    # Create the target path if it doesn't exist
    if not os.path.exists(target_path):
        os.makedirs(target_path)
        set_permissions_and_ownership(target_path, username_string)

    # Check permissions for the folder
    has_permission, message = check_file_folder_permission(base_dir, username_string)
    if not has_permission:
        return JsonResponse({'status': 'error', 'message': message}, status=403)

    # Define the file path for exporting the database
    file_path = os.path.join(target_path, f"{db_name}.sql")
    set_permissions_and_ownership(file_path, username_string)

    # Attempt to export the database
    try:
        export_database(username_string, file_path, db_name)

        # Respond with success and file details
        response_data = {
            'status': 'success',
            'file_path': file_path,
        }
        return JsonResponse(response_data, status=200)

    except Exception as e:
        # Handle database export error
        return JsonResponse({'status': 'error', 'message': f"Error exporting database: {str(e)}"}, status=500)
        
        
@login_required
def upload_from_url(request):
    if request.method == 'POST':
        file_url = request.POST.get('file_url', '').strip()
        target_name = request.POST.get('target_name', '').strip()
        
        if not file_url:
            return JsonResponse({'status': 'error', 'message': 'No URL provided.'}, status=400)

        if target_name.startswith('/'):
            target_name = target_name[1:]
        
        username_string = request.user.username
        user_package = Package.objects.filter(id=get_user_data_by_id(request.user.id).get('pkg_id')).first()
        disk_space_in_bytes = user_package.disk_space * 1024 * 1024 if user_package else 0

        # Extract filename
        parsed_url = urlparse(file_url)
        filename = unquote(os.path.basename(parsed_url.path))
        if not filename:
            filename = 'downloaded_file'

       
        base_dir = f'/home/{username_string}/'
    
    
        target_path = os.path.join(base_dir, target_name) if target_name else base_dir
        target_path = ensure_user_home_prefix(target_path, username_string)

        # Permissions and directory checks
        has_permission, message = check_file_folder_permission(base_dir, username_string)
        if not has_permission:
            return JsonResponse({'status': 'error', 'message': message}, status=403)

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Disk quota calculation
        temp_file_path = os.path.join(target_path, filename)
        try:
            download_file_with_wget(file_url, temp_file_path)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

        file_size = os.path.getsize(temp_file_path)

        database_names = get_user_database_info(username_string)
        total_size = calculate_total_database_size(database_names)
        disk = get_disk_usage(f'/home/{username_string}')
        email_disk = get_disk_usage(f'/home/vmail/{username_string}')
        disk_in_bytes = human_readable_to_bytes(disk)
        email_disk_in_bytes = human_readable_to_bytes(email_disk)
        total_size_in_bytes = disk_in_bytes + total_size + email_disk_in_bytes + file_size

        if user_package and user_package.disk_space != 0 and total_size_in_bytes > disk_space_in_bytes:
            os.remove(temp_file_path)
            return JsonResponse({'status': 'error', 'message': 'Disk quota exceeded. Please upgrade your package or free up space.'}, status=403)

        set_permissions_and_ownership(temp_file_path, username_string)

        fs = FileSystemStorage(location=target_path)
        file_url_saved = fs.url(filename)

        return JsonResponse({
            'status': 'success',
            'file_name': filename,
            'file_size': file_size,
            'file_url': file_url_saved
        }, status=200)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
    
    
@login_required
def media_viewer(request):
    path = request.GET.get('path')
    if not path:
        raise Http404("No file path specified.")

    username_string = request.user.username
    base_dir = f'/home/{username_string}/'
    file_path = os.path.abspath(os.path.join(base_dir, path))

    if not file_path.startswith(base_dir) or not os.path.isfile(file_path):
        raise Http404("File not found or access denied.")

    # Infer basic content type from extension
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    return FileResponse(open(file_path, 'rb'), content_type=content_type) 
    
    
@alogin_required
def upload_from_url_bk(request):
    if request.method == 'POST':
        ALLOWED_EXTENSIONS = ['.gz', '.tar', '.zip']
        file_url = request.POST.get('file_url', '').strip()
        target_name = 'backup'
        
        if not file_url:
            return JsonResponse({'status': 'error', 'message': 'No URL provided.'}, status=400)

        if target_name.startswith('/'):
            target_name = target_name[1:]
        
        username_string = request.user.username
       
        # Extract filename
        parsed_url = urlparse(file_url)
        filename = unquote(os.path.basename(parsed_url.path))
        
        if not filename:
            filename = 'downloaded_file'
            
        _, file_extension = os.path.splitext(filename)
        if file_extension.lower() not in ALLOWED_EXTENSIONS:
            return JsonResponse({'status': 'error', 'message': f'Only {", ".join(ALLOWED_EXTENSIONS)} files are allowed.'}, status=400)


        base_dir = '/home/'
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        
    
    
        target_path = os.path.join(base_dir, target_name) if target_name else base_dir
       

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Disk quota calculation
        temp_file_path = os.path.join(target_path, filename)
        try:
            download_file_with_wget(file_url, temp_file_path)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

        file_size = os.path.getsize(temp_file_path)

        

        fs = FileSystemStorage(location=target_path)
        file_url_saved = fs.url(filename)

        return JsonResponse({
            'status': 'success',
            'file_name': filename,
            'file_size': file_size,
            'file_url': file_url_saved
        }, status=200)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
      
      
@alogin_required
def upload_bk(request):
    if request.method == 'POST' and 'file' in request.FILES:
        ALLOWED_EXTENSIONS = ['.gz', '.tar', '.zip']
        # Get the uploaded file and other request data
        uploaded_file = request.FILES['file']  # For single file uploads
        target_name = 'backup'
        filename = uploaded_file.name
        _, file_extension = os.path.splitext(filename)
        
        if file_extension.lower() not in ALLOWED_EXTENSIONS:
            return JsonResponse({'status': 'error', 'message': f'Only {", ".join(ALLOWED_EXTENSIONS)} files are allowed.'}, status=400)
   
            

        # Ensure target_name does not start with a slash
        if target_name.startswith('/'):
            target_name = target_name[1:]

        # Define base directory and construct the target path
        username_string = request.user.username
        
        
        base_dir = '/home/'
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)                    
        
        target_path = os.path.join(base_dir, target_name) if target_name else base_dir
        

        

        # Ensure target path exists
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Save the file to the target directory
        fs = FileSystemStorage(location=target_path)
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = os.path.join(target_path, filename)
        file_url = fs.url(filename)
        

        # Respond with success and file details
        response_data = {
            'status': 'success',
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_url': file_url
        }
        return JsonResponse(response_data, status=200)

    # Handle error if no file is uploaded
    return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)   


@login_required
def update_user_settings(request):
    if request.method == "POST":
        try:
              # Get or create settings for user
            settings, _ = UserSettings.objects.get_or_create(userid=request.user.id)

            if request.POST.get("font_size"):
                settings.font_size =request.POST.get("font_size")
            else:              
                settings.hide_hiden_file = 0 if request.POST.get("hide_hiden_file") != "0" else 1
                settings.hide_folder_size = 0 if request.POST.get("hide_folder_size") != "0" else 1


            # Add other fields here as needed

            settings.save()

            return JsonResponse({
                "status": "success",
                "message": "Settings updated successfully."
            })

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Error saving settings: {str(e)}"
            }, status=500)

    return JsonResponse({
        "status": "error",
        "message": "Invalid request method."
    }, status=405)    