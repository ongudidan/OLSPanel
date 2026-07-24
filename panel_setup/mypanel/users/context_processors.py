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

def branding(request):

    # defaults
    branding_data = {
        "brand_title": "Fortune Developers",
        "brand_image": "/media/ow.png",
        "brand_icon": "/media/logo.png",
        "brand_color": "#ef6d19",
    }

    # license check FIRST (clean exit)
    status = get_license_status(request)
    if status in ["missing", "invalid", "expired"]:
        return {"branding": branding_data}

    keys = branding_data.keys()

    qs = AppSettings.objects.filter(setting_key__in=keys)

    for item in qs:
        value = item.setting_value

        if item.setting_key == 'brand_title':
            branding_data[item.setting_key] = value if value is not None else ""
        else:
            # strict safe check (important)
            if value and str(value).strip():
                branding_data[item.setting_key] = value

    return {"branding": branding_data}