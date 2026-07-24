from django.shortcuts import render
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
                show_block = False
                block_type_label = ""
                expires_label = ""
                
                if blocked_entry.block_type == "TEMP":
                    if blocked_entry.temp_block_expires and blocked_entry.temp_block_expires > timezone.now():
                        show_block = True
                        block_type_label = "Temporary Block"
                        remaining = blocked_entry.temp_block_expires - timezone.now()
                        minutes = int(remaining.total_seconds() // 60)
                        seconds = int(remaining.total_seconds() % 60)
                        expires_label = f"{minutes}m {seconds}s"
                elif blocked_entry.block_type == "PERM":
                    show_block = True
                    block_type_label = "Permanent Block"
                    expires_label = "Indefinite"
                
                if show_block:
                    response = render(request, "users/blocked.html", {
                        "ip": ip,
                        "block_type": block_type_label,
                        "expires_in": expires_label
                    })
                    response.status_code = 403
                    return response
                    
        return self.get_response(request)
