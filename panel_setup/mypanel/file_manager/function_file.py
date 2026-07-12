import os
import zipfile
import tarfile
import shutil
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
from django.http import JsonResponse, FileResponse
import subprocess


def f_copy(username_string, file_name, target_name):
    
    try:
        if target_name.startswith('/'):
            target_name = target_name[1:]

        if file_name.startswith('/'):
            file_name = file_name[1:]

        base_dir = f'/home/{username_string}/'  # Default base directory
        file_path = os.path.join(base_dir, file_name)
        target_path = os.path.join(base_dir, target_name) if target_name else None
        if not target_path:
            target_path = base_dir
        target_path = ensure_user_home_prefix(target_path, username_string)

        if not os.path.exists(file_path):
            return f"Error: Source path '{file_path}' does not exist."

        if os.path.isdir(file_path):
            target_path_with_folder = os.path.join(target_path, os.path.basename(file_path))
            shutil.copytree(file_path, target_path_with_folder, dirs_exist_ok=True)
            set_permissions_and_ownership(target_path_with_folder, username_string)
            return f"Directory copied successfully to '{target_path_with_folder}'."
        else:
            shutil.copy(file_path, target_path)
            if not target_path.endswith('/'):
                target_path += '/'

            file_name_only = os.path.basename(file_path)
            set_permissions_and_ownership(target_path + file_name_only, username_string)
            return f"File copied successfully to '{target_path}'."
    except Exception as e:
        return f"Error: {str(e)}"
        
        
        
        
def f_move(username_string, file_name, target_name):
   
    try:
        # Normalize paths
        if target_name.startswith('/'):
            target_name = target_name[1:]

        if file_name.startswith('/'):
            file_name = file_name[1:]

        base_dir = f'/home/{username_string}/'
        file_path = os.path.join(base_dir, file_name)
        target_path = os.path.join(base_dir, target_name) if target_name else None
        if not target_path:
            target_path = base_dir
        
        target_path = ensure_user_home_prefix(target_path, username_string)

        # If the target is a directory, move files inside it
        if os.path.isdir(target_path):
            # Get the basename of the file or folder being moved
            item_name = os.path.basename(file_path)
            final_target_path = os.path.join(target_path, item_name)

            # Replace the existing file if it exists
            if os.path.exists(final_target_path):
                if os.path.isfile(final_target_path):
                    os.remove(final_target_path)  # Replace file only

            # Move the file or directory into the target directory
            shutil.move(file_path, target_path)
        else:
            # If the target is not a directory, move directly
            shutil.move(file_path, target_path)

        return f"File moved successfully to '{target_path}'."
    except Exception as e:
        return f"Error: {str(e)}"  
        
        
        
def f_delete(username_string, file_name):
    """
    Delete a file or folder for a specific user.
    """
    try:
        # Normalize the file path
        if file_name.startswith('/'):
            file_name = file_name[1:]

        base_dir = f'/home/{username_string}/'
        file_path = os.path.join(base_dir, file_name)

        # Check if the path is a folder or file and delete accordingly
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)  # Recursively delete the folder
        elif os.path.isfile(file_path):
            os.remove(file_path)  # Delete the file
        else:
            return f"Error: '{file_path}' does not exist or is not a valid file/directory."

        return f"File deleted successfully: '{file_path}'."
    except Exception as e:
        return f"Error: {str(e)}"   


def f_compress(username_string, parent, file_name=None, target_name=None, selected_items=None):
    try:
        # Validate and sanitize inputs
        if not target_name:
            return JsonResponse({'status': 'error', 'message': 'Target name is required.'}, status=400)

        if isinstance(target_name, str) and target_name.startswith('/'):
            target_name = target_name[1:]

        if file_name and isinstance(file_name, str) and file_name.startswith('/'):
            file_name = file_name[1:]

        base_dir = f'/home/{username_string}/'
        source_path = os.path.join(base_dir, parent)  # Path to the source folder

        # Construct the target path and ensure it's valid
        if target_name:
            target_path = os.path.join(base_dir, target_name)
            target_path = ensure_user_home_prefix(target_path, username_string)
            if not isinstance(target_path, str):
                raise ValueError(f"Invalid target path: {target_path}")

        # Create the zip target path
        zip_target = target_path if target_path.endswith('.zip') else target_path + '.zip'

        # Check if the zip file already exists
        if os.path.exists(zip_target):
            return JsonResponse({'status': 'error', 'message': f"The zip file '{zip_target}' already exists."}, status=400)

        # Create a zip file
        with zipfile.ZipFile(zip_target, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            if selected_items:
                # Compress multiple selected files/folders
                for file_source in selected_items:
                    file_source_path = os.path.join(base_dir, file_source)

                    if not os.path.exists(file_source_path):
                        return JsonResponse({'status': 'error', 'message': f"The item '{file_source}' does not exist."}, status=404)

                    # If it's a directory, add the directory contents recursively
                    if os.path.isdir(file_source_path):
                        for folder_root, _, files in os.walk(file_source_path):
                            # Calculate the relative path based on the `source_path`
                            arcname = os.path.relpath(folder_root, source_path)  # Relative to the source directory
                            zip_ref.write(folder_root, arcname)  # Add the folder to zip
                            for file in files:
                                file_path = os.path.join(folder_root, file)
                                arcname_file = os.path.join(arcname, file)
                                zip_ref.write(file_path, arcname_file)  # Add files to zip
                    else:
                        # If it's a file, add it directly
                        arcname = os.path.relpath(file_source_path, source_path)  # Remove the `/home/username/parent/` part
                        zip_ref.write(file_source_path, arcname)  # Add the file to zip

            elif file_name:
                # Compress a single file or folder
                file_path = os.path.join(base_dir, file_name)

                if not os.path.exists(file_path):
                    return JsonResponse({'status': 'error', 'message': f"The item '{file_name}' does not exist."}, status=404)

                # If it's a directory, add the directory contents recursively
                if os.path.isdir(file_path):
                    for folder_root, _, files in os.walk(file_path):
                        arcname = os.path.relpath(folder_root, source_path)  # Strip the source_path
                        zip_ref.write(folder_root, arcname)  # Add folder to zip
                        for file in files:
                            file_path = os.path.join(folder_root, file)
                            arcname_file = os.path.join(arcname, file)
                            zip_ref.write(file_path, arcname_file)  # Add file to zip

                # If it's a file, add it directly
                else:
                    arcname = os.path.relpath(file_path, source_path)  # Remove the `/home/username/parent/` part
                    zip_ref.write(file_path, arcname)  # Add the file to zip

            else:
                return JsonResponse({'status': 'error', 'message': 'No file or selected items provided for compression.'}, status=400)

        # Set permissions and ownership for the created zip file
        set_permissions_and_ownership(zip_target, username_string)

        return JsonResponse({'status': 'success', 'message': f'File(s) compressed successfully to "{zip_target}".'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Error during compression: {str(e)}"}, status=500)
  
       
def is_valid_filename(filename):
    """Check if the filename is valid (no special or forbidden characters)."""
    return bool(re.match(r'^[^<>:"/\\|?*\x00-\x1F]+$', filename))   


def download_file_with_wget(url, output_path):
    try:
        result = subprocess.run(
            ['wget', '-q', '-O', output_path, url],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except subprocess.CalledProcessError as e:
        raise Exception(f"wget failed: {e.stderr.decode().strip()}")

