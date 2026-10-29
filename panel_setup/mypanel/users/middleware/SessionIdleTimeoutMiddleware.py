import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import JsonResponse

class SessionIdleTimeoutMiddleware:
    """
    Automatically logs out users after an idle inactivity period (default 2 hours).
    Excludes automated background polling endpoints (system status, metrics, SPA prefetching)
    so open dashboard tabs do not keep sessions alive indefinitely.
    Applies to sessions where 'Remember Me' was NOT checked.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_authenticated = (hasattr(request, 'user') and request.user.is_authenticated) or \
                           (getattr(request, 'admin_user', None) and getattr(request.admin_user, 'is_authenticated', False))

        if is_authenticated:
            # Endpoints that poll automatically in the background
            BACKGROUND_POLL_PREFIXES = (
                '/whm/system_status/',
                '/api/db_replication/status/',
            )
            path = request.path_info
            is_background_poll = (
                any(path.startswith(prefix) for prefix in BACKGROUND_POLL_PREFIXES) or
                request.headers.get('X-SPA-Prefetch') == 'true' or
                (request.GET.get('json') == '1' and 'status' in path)
            )

            # Check if remember_me was selected during login
            remember_me = request.session.get('remember_me', False)
            if hasattr(request, 'admin_session'):
                remember_me = remember_me or request.admin_session.get('remember_me', False)

            # If "Remember Me" is not checked, enforce idle timeout
            if not remember_me:
                idle_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 7200)  # 2 hours default
                now = time.time()
                last_activity = request.session.get('last_activity')
                if not last_activity and hasattr(request, 'admin_session'):
                    last_activity = request.admin_session.get('last_activity')

                if last_activity and (now - float(last_activity) > idle_timeout):
                    # Inactivity timeout exceeded: flush sessions
                    logout(request)
                    if hasattr(request, 'admin_session'):
                        request.admin_session.flush()
                    request.session.flush()

                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('X-SPA-Request') == 'true':
                        return JsonResponse({
                            'status': 'expired',
                            'message': 'Session expired due to inactivity. Please log in again.',
                            'redirect': '/login/?session_expired=1'
                        }, status=401)
                    return redirect('/login/?session_expired=1')

                # Update activity timestamp only on user actions/navigation, not pollers
                if not is_background_poll:
                    request.session['last_activity'] = now
                    if hasattr(request, 'admin_session'):
                        request.admin_session['last_activity'] = now

        response = self.get_response(request)
        return response
