from functools import wraps
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth.models import User
from users.database import *  # Import your function
from datetime import datetime, timezone as dt_timezone
from django.http import HttpRequest
from django.shortcuts import render

def admincheck(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/login/')        
       
        return view_func(request, *args, **kwargs)
    return wrapper
    
    
    
def loginadminoruser(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if either regular user OR admin user is authenticated
        regular_user_authenticated = request.user.is_authenticated
        admin_user_authenticated = hasattr(request, 'admin_user') and request.admin_user
        
        if not regular_user_authenticated and not admin_user_authenticated:
            return HttpResponseRedirect('/login/')
        
        return view_func(request, *args, **kwargs)
    return wrapper   


def get_license_status(request):
    return "active"

def premium_features(*allowed_types):
    def decorator(view_func):
        from functools import wraps
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
