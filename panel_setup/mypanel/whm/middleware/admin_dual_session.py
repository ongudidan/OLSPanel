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
                if hasattr(request, 'user') and not request.user.is_authenticated:
                    request.user = request.admin_user
            except User.DoesNotExist:
                request.admin_user = None
                request.admin_session.flush()
        else:
            request.admin_user = None

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