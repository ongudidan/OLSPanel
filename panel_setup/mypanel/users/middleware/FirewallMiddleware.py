from django.http import HttpResponseForbidden
from users.models import BlockedIP
from django.utils import timezone

def get_client_ip(request):
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip.strip()
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

class FirewallMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = get_client_ip(request)
        if ip:
            blocked_entry = BlockedIP.objects.filter(ip_address=ip, block_type__in=["TEMP", "PERM"]).first()
            if blocked_entry:
                if blocked_entry.block_type == "TEMP":
                    if blocked_entry.temp_block_expires and blocked_entry.temp_block_expires > timezone.now():
                        return HttpResponseForbidden("<h1>403 Forbidden</h1><p>Your IP address has been temporarily blocked by OLSPanel firewall due to too many failed attempts.</p>")
                else:
                    return HttpResponseForbidden("<h1>403 Forbidden</h1><p>Your IP address has been permanently blocked by OLSPanel firewall.</p>")
                    
        return self.get_response(request)
