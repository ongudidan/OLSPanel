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
from users.firewall import *  # Import your function

class Command(BaseCommand):
    help = "Checks if the Django project version is up to date and creates an update file if needed"

    def handle(self, *args, **kwargs):
        try:
            if not check_csf_installed():
                run_monitor()
            
        except Exception as e:
            self.stderr.write(f"❌ Error: {e}")
