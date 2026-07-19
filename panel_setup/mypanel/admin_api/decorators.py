import configparser
from django.contrib.auth import authenticate
from django.http import JsonResponse
from functools import wraps
import os
from django.conf import settings
from users.function import *
from users.database import *  
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

    
def admin_api_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        ip = get_client_ip(request)
        get_api_status = int(AppSettings.objects.filter(setting_key='api').values_list('setting_value', flat=True).first() or 0)        
        if get_api_status != 1:
            return JsonResponse({'error': 'API is currently disabled'}, status=200)

        if request.method != 'POST':
            return JsonResponse({'error': 'POST method required'}, status=200)

        username = request.headers.get('username')
        password = request.headers.get('password')

        if not username or not password:
            return JsonResponse({'error': 'Username and password required'}, status=200)

        user = authenticate(username=username, password=password)
        

        if user is None:
            logger.error(f"Login failed attempt in api from IP: {ip}")
            try:
                from users.firewall import register_panel_failed_login
                register_panel_failed_login(ip)
            except Exception as e:
                logger.error(f"Error registering admin api failed login: {e}")
            return JsonResponse({'error': 'Invalid credentials'}, status=200)
            
        whm = get_user_data_by_id(user.id).get('whm')
        if whm != 1:
            logger.error(f"Login failed attempt in api from IP: {ip}")
            try:
                from users.firewall import register_panel_failed_login
                register_panel_failed_login(ip)
            except Exception as e:
                logger.error(f"Error registering admin api failed login: {e}")
            return JsonResponse({'error': 'Invalid credentials'}, status=200)    

        request.user = user  # Attach the user manually
        return view_func(request, *args, **kwargs)

    return _wrapped_view
