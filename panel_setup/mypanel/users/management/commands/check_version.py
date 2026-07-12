import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from whm.function import * 
from whm.models import *
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
from whm.models import * 
from users.models import * 
from users.server_core import *  # Import your function
from users.database import *  # Import your function
from django.db import connection
from users.function import *  # Import your function
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse, FileResponse
from django.core.files.storage import FileSystemStorage
from users.forms import *
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
import subprocess
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from users.panellogger import *
from django.contrib.auth import update_session_auth_hash

class Command(BaseCommand):
    help = "Checks if the Django project version is up to date and creates an update file if needed"

    def handle(self, *args, **kwargs):
        try:
            # URL of the version file on the web
            version_url = "https://ongudidan.github.io/FortunePanel/panel_updates/version.txt"
            auto_update_version_url = "https://ongudidan.github.io/FortunePanel/panel_updates/version.txt?live=1"
            # Get OS details from settings, with defaults
            os_name = getattr(settings, "MY_OS_NAME", "linux")
            os_version = getattr(settings, "MY_OS_VERSION", "0")
            panel_version = getattr(settings, "VERSION", "0")
            
            # Data to send in the POST request
            data = {
                "osname": os_name,
                "osversion": os_version,
                "panel": panel_version
            }

            # Fetch the latest version
            response = requests.post(version_url, data=data, timeout=10)
            response.raise_for_status()  # Raise error if request fails
            latest_version = response.text.strip()

            # Get the current version from settings.py
            current_version = getattr(settings, "VERSION", "0.0.0")

            # Django root directory
            django_root = settings.BASE_DIR

            # Path to the update file
            update_file_path = os.path.join(django_root, 'etc', 'update')

            # Compare versions
            if current_version == latest_version:
                self.stdout.write(f"✅ The project is up to date (Version: {current_version})")
                # Remove update file if it exists (no update needed)
                if os.path.exists(update_file_path):
                    os.remove(update_file_path)
                    self.stdout.write("🗑️ Removed outdated update file.")
            else:
                self.stdout.write(f"⚠️ Update available! Current: {current_version}, Latest: {latest_version}")
                # Create the update file
                os.makedirs(os.path.dirname(update_file_path), exist_ok=True)
                with open(update_file_path, "w") as update_file:
                    update_file.write(f"{latest_version}\n")
                    
                    
                response = requests.post(auto_update_version_url, data=data, timeout=10)
                response.raise_for_status()  # Raise error if request fails
                auto_latest_version = response.text.strip()            
                current_version = getattr(settings, "VERSION", "0.0.0")
                
                if version_tuple(auto_latest_version) > version_tuple(current_version):
                    auto_update = int(AppSettings.objects.filter(setting_key='auto_update').values_list('setting_value', flat=True).first() or 0)
                    if auto_update==1:
                        self.stdout.write(f"🔄 Auto update is enabled. Updating...{auto_latest_version}")
                        install_panel_update()
                        restart_openlitespeed()



                
                self.stdout.write(f"📂 Update file created at: {update_file_path}")

        except requests.RequestException as e:
            self.stderr.write(f"❌ Error fetching version info: {e}")
