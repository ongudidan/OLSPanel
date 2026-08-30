from functools import wraps
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from users.database import get_user_data_by_id

def alogin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        admin_user = getattr(request, 'admin_user', None)
        
        # Fallback to standard request.user if authenticated and has whm=1
        if not admin_user and hasattr(request, 'user') and request.user.is_authenticated:
            user_data = get_user_data_by_id(request.user.id)
            if user_data and user_data.get('whm') == 1:
                admin_user = request.user
                request.admin_user = admin_user

        # Check if the admin user is authenticated
        if not admin_user:
            return HttpResponseRedirect('/login/?next=' + request.path)
        
        # Verify that the user's `whm` group value is 1
        user_data = get_user_data_by_id(admin_user.id)
        if not user_data or user_data.get('whm') != 1:
            return redirect('/login/')
        
        return view_func(request, *args, **kwargs)
    return wrapper