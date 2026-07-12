from functools import wraps
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth.models import User
from users.database import *  # Import your function
from django.contrib.auth import authenticate, login, logout

def alogin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.id:
            whm = get_user_data_by_id(request.user.id).get('whm')
            if whm == 1:
                logout(request)
        # Check if the user is authenticated
        if not hasattr(request, 'admin_user') or not request.admin_user:
            return HttpResponseRedirect('/login/')
        
        # Check if the user's `whm_group` value is 1
        
        whm = get_user_data_by_id(request.admin_user.id).get('whm')
        if whm != 1:
            return redirect('/login/')  # Replace with the URL you want to redirect to
        
        return view_func(request, *args, **kwargs)
    return wrapper