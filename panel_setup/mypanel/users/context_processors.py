import requests
from .plugin import * 
from users.models import AppSettings
from users.function import * 

def dynamic_plugins(request):
    """Make plugin lists available globally (e.g., sidebar)"""
    # Optional parameter example (softaculous)
    softaculous = True

    return {
        'software_plugin': get_software_plugins_list(softaculous),
        'domain_plugin': get_domain_plugins_list(),
        'file_plugin': get_file_plugins_list(),
        'security_plugin': get_security_plugins_list(),
        'database_plugin': get_database_plugins_list(),
        'email_plugin': get_email_plugins_list(),
        'advance_plugin': get_advance_plugins_list(),
    }

def hex_to_rgb(hex_code, default="239, 109, 25"):
    try:
        if not hex_code:
            return default
        h = str(hex_code).strip()
        if h.startswith("rgb"):
            inner = h[h.find("(")+1:h.find(")")].split(",")
            if len(inner) >= 3:
                return f"{int(inner[0].strip())}, {int(inner[1].strip())}, {int(inner[2].strip())}"
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join([c * 2 for c in h])
        if len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return f"{r}, {g}, {b}"
    except Exception:
        pass
    return default

def get_installed_version():
    try:
        from django.conf import settings
        import os
        version_file = os.path.join(settings.BASE_DIR, 'etc', 'version')
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                ver = f.read().strip()
                if ver:
                    return ver
        return getattr(settings, 'VERSION', '')
    except Exception:
        return ''

def branding(request):

    # defaults
    branding_data = {
        "brand_title": "Fortune Developers",
        "brand_image": "/media/ow.png",
        "brand_icon": "/media/logo.png",
        "brand_color": "#ef6d19",
        "brand_color_rgb": "239, 109, 25",
        "button_primary_color": "#9e6de0",
        "button_secondary_color": "#fd5190",
        "panel_version": get_installed_version(),
    }

    keys = ["brand_title", "brand_image", "brand_icon", "brand_color", "button_primary_color", "button_secondary_color"]

    qs = AppSettings.objects.filter(setting_key__in=keys)

    for item in qs:
        value = item.setting_value

        if item.setting_key == 'brand_title':
            branding_data[item.setting_key] = value if value is not None else ""
        else:
            # strict safe check (important)
            if value and str(value).strip():
                branding_data[item.setting_key] = value

    branding_data["brand_color_rgb"] = hex_to_rgb(branding_data.get("brand_color", "#ef6d19"))
    branding_data["panel_version"] = get_installed_version()
    return {"branding": branding_data, "panel_version": branding_data["panel_version"]}