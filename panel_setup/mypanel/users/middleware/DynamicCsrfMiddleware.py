from django.conf import settings
from urllib.parse import urlparse

class DynamicCsrfMiddleware:
    """
    Dynamically trusts the incoming Host, Origin, and Referer headers for CSRF validation.
    Allows OLSPanel to run seamlessly on any custom domain, server IP, hostname, or port globally.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(settings, 'CSRF_TRUSTED_ORIGINS') or not isinstance(settings.CSRF_TRUSTED_ORIGINS, list):
            settings.CSRF_TRUSTED_ORIGINS = []

        try:
            # 1. Dynamically trust the request host on both HTTP and HTTPS
            host = request.get_host()
            if host:
                http_origin = f"http://{host}"
                https_origin = f"https://{host}"
                if https_origin not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(https_origin)
                if http_origin not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(http_origin)

            # 2. Dynamically trust the Origin header
            origin = request.META.get('HTTP_ORIGIN')
            if origin:
                parsed = urlparse(origin)
                if parsed.scheme and parsed.netloc:
                    clean_origin = f"{parsed.scheme}://{parsed.netloc}"
                    if clean_origin not in settings.CSRF_TRUSTED_ORIGINS:
                        settings.CSRF_TRUSTED_ORIGINS.append(clean_origin)

            # 3. Dynamically trust the Referer header
            referer = request.META.get('HTTP_REFERER')
            if referer:
                parsed_ref = urlparse(referer)
                if parsed_ref.scheme and parsed_ref.netloc:
                    clean_ref = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
                    if clean_ref not in settings.CSRF_TRUSTED_ORIGINS:
                        settings.CSRF_TRUSTED_ORIGINS.append(clean_ref)
        except Exception:
            pass

        return self.get_response(request)
