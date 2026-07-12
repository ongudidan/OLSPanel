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
    license_key = request.META.get('LICENSE_KEY')
    license_expire_raw = request.META.get('LICENSE_EXPIRE')

    if not license_key:
        return "missing"

    if not license_expire_raw:
        return "invalid"

    try:
        normalized = license_expire_raw.strip().replace('Z', '+00:00')
        expire_date = datetime.fromisoformat(normalized)

        if expire_date.tzinfo is None:
            expire_date = expire_date.replace(tzinfo=dt_timezone.utc)

        now_time = datetime.now(tz=dt_timezone.utc)

        if expire_date <= now_time:
            return "expired"

        return "active"

    except Exception:
        return "invalid"

from django.http import HttpResponse


def premium_features(*allowed_types):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

          
            whm = 0 
            if request.admin_user.id:
                whm = get_user_data_by_id(request.admin_user.id).get('whm')
            
            
            status = get_license_status(request)

            # license type handling
            license_type_raw = request.META.get("LICENSE_TYPE") or ""
            license_types = [t.strip() for t in license_type_raw.split(",") if t.strip()]

            # fallback single value
            if not license_types and license_type_raw:
                license_types = [license_type_raw]

            # 🔥 KEY RULE: EMPTY decorator = allow all types
            if allowed_types:
                type_valid = any(t in allowed_types for t in license_types)
            else:
                type_valid = True  # ✅ allow all
            if status not in ["missing", "invalid"] and not type_valid and whm == 1:
                required_types = ", ".join(allowed_types)
                messages.error(request,f"This feature requires '{required_types}' license type. "f"Your current license does not include access to this feature.")


          
                
            # block logic
            if status in ["missing", "invalid", "expired"] or not type_valid:

                if whm == 1:
                    return redirect('/whm/license/')

                return render(request, "users/premium_blocked.html", {
                    "status": status,
                    "type": license_types
                })

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator