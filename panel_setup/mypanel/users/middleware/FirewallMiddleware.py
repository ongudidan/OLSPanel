from django.http import HttpResponseForbidden
from users.models import BlockedIP, AppSettings
from django.utils import timezone

def get_client_ip(request):
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip.strip()
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def render_blocked_page(ip, block_type, expires_in, brand_title, brand_image):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied - IP Blocked</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
            color: #f8fafc;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow: hidden;
        }}
        .container {{
            max-width: 500px;
            width: 100%;
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px 30px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .brand-logo {{
            max-height: 55px;
            margin-bottom: 24px;
            object-fit: contain;
        }}
        .icon-box {{
            width: 80px;
            height: 80px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            color: #ef4444;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }}
            70% {{ box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
        }}
        h1 {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ff8a8a 0%, #ef4444 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        p {{
            font-size: 16px;
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 24px;
        }}
        .info-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
            text-align: left;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        .info-label {{
            color: #64748b;
        }}
        .info-value {{
            color: #e2e8f0;
            font-family: monospace;
            font-weight: 600;
        }}
        .footer-text {{
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <img src="{brand_image}" alt="{brand_title}" class="brand-logo">
        <div class="icon-box">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width: 42px; height: 42px;">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z" />
            </svg>
        </div>
        <h1>Access Denied</h1>
        <p>Your IP address has been temporarily blocked by {brand_title} security firewall due to multiple failed login attempts.</p>
        
        <div class="info-card">
            <div class="info-row">
                <span class="info-label">Your IP Address:</span>
                <span class="info-value">{ip}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Block Type:</span>
                <span class="info-value">{block_type}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Expires In:</span>
                <span class="info-value">{expires_in}</span>
            </div>
        </div>
        
        <div class="footer-text">
            If you believe this is an error, please contact your <strong>system administrator</strong> or hosting support to request unblocking.
        </div>
    </div>
</body>
</html>"""

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
                    try:
                        brand_title = AppSettings.objects.filter(setting_key='brand_title').values_list('setting_value', flat=True).first()
                        if not brand_title or not brand_title.strip():
                            brand_title = "Fortune Developers"
                    except Exception:
                        brand_title = "Fortune Developers"

                    try:
                        brand_image = AppSettings.objects.filter(setting_key='brand_image').values_list('setting_value', flat=True).first()
                        if not brand_image or not brand_image.strip():
                            brand_image = "/media/ow.png"
                    except Exception:
                        brand_image = "/media/ow.png"
                        
                    html_content = render_blocked_page(
                        ip=ip,
                        block_type=block_type_label,
                        expires_in=expires_label,
                        brand_title=brand_title,
                        brand_image=brand_image
                    )
                    return HttpResponseForbidden(html_content)
                    
        return self.get_response(request)
