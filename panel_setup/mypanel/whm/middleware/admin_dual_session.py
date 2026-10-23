# whm/middleware/admin_dual_session.py
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from users.database import get_user_data_by_id

class SeparateAdminSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add admin session to request
        self.setup_admin_session(request)
        response = self.get_response(request)
        return self.handle_admin_session_response(request, response)

    def setup_admin_session(self, request):
        """Set up completely separate admin session"""
        admin_cookie_name = getattr(settings, 'ADMIN_SESSION_COOKIE_NAME', 'session_admin')
        admin_session_key = request.COOKIES.get(admin_cookie_name)
        
        # Create separate admin session store
        request.admin_session = SessionStore(admin_session_key)
        
        # Load admin user from admin session
        admin_user_id = request.admin_session.get('_auth_user_id')
        if admin_user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                request.admin_user = User.objects.get(id=admin_user_id)
            except User.DoesNotExist:
                request.admin_user = None
                request.admin_session.flush()
        else:
            request.admin_user = None

        # Fallback 1: If admin_user is authenticated via admin session, but request.user is not authenticated,
        # set request.user = request.admin_user
        if request.admin_user and hasattr(request, 'user') and not request.user.is_authenticated:
            request.user = request.admin_user

        # Track impersonated client user (if request.user is an authenticated client distinct from admin_user)
        request.impersonated_user = None
        if request.admin_user and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.id != request.admin_user.id:
                request.impersonated_user = request.user

        # WHM & Admin Scope: If navigating inside /whm/ or under an explicit admin scope (e.g. ?scope=admin),
        # always bind request.user to request.admin_user so administrative interfaces execute with full admin context
        # and are never polluted by a client session opened in another tab.
        if request.admin_user and (request.path.startswith('/whm/') or request.GET.get('scope') == 'admin'):
            request.user = request.admin_user

        # Fallback 2: If standard request.user is authenticated and is admin (whm=1 or superuser/staff),
        # but request.admin_user is not set (e.g. session_admin cookie missing/expired),
        # automatically populate request.admin_user and sync the admin session
        if not request.admin_user and hasattr(request, 'user') and request.user.is_authenticated:
            is_whm_admin = False
            if getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False):
                is_whm_admin = True
            else:
                user_data = get_user_data_by_id(request.user.id)
                if user_data and user_data.get('whm') == 1:
                    is_whm_admin = True
            
            if is_whm_admin:
                request.admin_user = request.user
                if hasattr(request, 'admin_session'):
                    request.admin_session['_auth_user_id'] = str(request.user.id)
                    request.admin_session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
                    request.admin_session.modified = True

    def handle_admin_session_response(self, request, response):
        """Handle admin session cookie"""
        admin_cookie_name = getattr(settings, 'ADMIN_SESSION_COOKIE_NAME', 'session_admin')
        
        if hasattr(request, 'admin_session'):
            if request.admin_session.modified:
                if request.admin_session._session:
                    request.admin_session.save()
                    response.set_cookie(
                        admin_cookie_name,
                        request.admin_session.session_key,
                        max_age=getattr(settings, 'ADMIN_SESSION_COOKIE_AGE', settings.SESSION_COOKIE_AGE),
                        path=getattr(settings, 'SESSION_COOKIE_PATH', '/'),
                        domain=getattr(settings, 'SESSION_COOKIE_DOMAIN', None),
                        secure=getattr(settings, 'ADMIN_SESSION_COOKIE_SECURE', settings.SESSION_COOKIE_SECURE),
                        httponly=getattr(settings, 'ADMIN_SESSION_COOKIE_HTTPONLY', settings.SESSION_COOKIE_HTTPONLY),
                        samesite=getattr(settings, 'ADMIN_SESSION_COOKIE_SAMESITE', settings.SESSION_COOKIE_SAMESITE),
                    )
                else:
                    response.delete_cookie(
                        admin_cookie_name,
                        path=getattr(settings, 'SESSION_COOKIE_PATH', '/'),
                        domain=getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
                    )
        
        return response