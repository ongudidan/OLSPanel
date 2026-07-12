import configparser
from django.contrib.auth import authenticate
from django.http import JsonResponse
from functools import wraps
import os
from django.conf import settings
from users.function import *
from users.panellogger import *
from whm.models import * 

logger = CpLogger()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_api_status():
    config = configparser.ConfigParser()

    # Construct the path to conf.ini using settings.BASE_DIR
    django_root = settings.BASE_DIR
    file_path = os.path.join(django_root, 'etc', 'conf.ini')

    # Check if the file exists
    if os.path.exists(file_path):
        try:
            config.read(file_path)

            # Attempt to read the 'api_status' from the config file
            # If the section or option doesn't exist, it will raise an exception
            api_status = config.get('settings', 'api_status', fallback=None)

            if api_status is not None:
                return int(api_status)  # Ensure it's an integer and return
            else:
                return 0  # If the api_status is missing, return 0

        except (configparser.NoOptionError, configparser.NoSectionError) as e:
            # If there is an error reading the section or option, return default value 0
            return 0
    else:
        # If the file doesn't exist, return 0
        return 0
    
def api_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if get_api_status() != 1:
            return JsonResponse({'error': 'API is currently disabled'}, status=200)

        if request.method != 'POST':
            return JsonResponse({'error': 'POST method required'}, status=200)

        username = request.headers.get('username')
        apikey = request.headers.get('apikey')
        password_plain = request.headers.get('password')

        if not username or (not apikey and not password_plain):
            return JsonResponse({'error': 'Username and API key or password required'}, status=200)

        # Decide source of password
        if apikey:
            try:
                password = decode(apikey)
            except Exception:
                return JsonResponse({'error': 'Invalid API key format'}, status=200)
        else:
            password = password_plain

        user = authenticate(username=username, password=password)
        if user is None:
            ip = get_client_ip(request)
            logger.error(f"Login failed attempt in api from IP: {ip}")
            return JsonResponse({'error': 'Invalid credentials'}, status=200)

        request.user = user
        return view_func(request, *args, **kwargs)

    return _wrapped_view