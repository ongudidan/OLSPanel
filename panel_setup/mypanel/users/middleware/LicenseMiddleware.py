from django.shortcuts import redirect, render
from django.contrib import messages
from datetime import datetime, timezone as dt_timezone


# ----------------------------
# LICENSE ROUTE CONFIG
# ----------------------------
LICENSED_ROUTES = {
    "/3rdparty/terminal/": None,
    "/whm/panel_brand": None,
    "/whm/user_limit": None,
    "/module/api/": ["basic", "pro", "enterprise"],
}


# ----------------------------
# LICENSE STATUS CHECK
# ----------------------------
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


# ----------------------------
# MIDDLEWARE
# ----------------------------
class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path
        admin_user = getattr(request, "admin_user", None)

        # skip license page
        if path.startswith("/whm/license/"):
            return self.get_response(request)

        # find required license types
        required_types = None
        for route, types in LICENSED_ROUTES.items():
            if path.startswith(route):
                required_types = types
                break

        # ----------------------------
        # NO RESTRICTION → ALLOW ALL
        # ----------------------------
        if required_types is None:
            return self.get_response(request)

        # ----------------------------
        # LICENSE STATUS
        # ----------------------------
        status = get_license_status(request)

        license_type_raw = request.META.get("LICENSE_TYPE") or ""
        license_types = [
            t.strip() for t in license_type_raw.split(",") if t.strip()
        ]

        # ----------------------------
        # TYPE CHECK (EMPTY DECORATOR RULE)
        # ----------------------------
        if required_types:
            type_valid = any(t in required_types for t in license_types)
        else:
            type_valid = True  # allow all

        # ----------------------------
        # OPTIONAL ADMIN MESSAGE
        # ----------------------------
        if status not in ["missing", "invalid"] and not type_valid and admin_user:
            messages.error(
                request,
                f"This feature requires '{', '.join(required_types)}' license type. "
                f"Your current license does not include access."
            )

        # ----------------------------
        # BLOCK LOGIC
        # ----------------------------
        if status in ["missing", "invalid", "expired"] or not type_valid:

            if admin_user:
                return redirect("/whm/license/")

            return render(request, "users/premium_blocked.html", {
                "status": status,
                "type": license_types,
                "required": required_types
            })

        

        return self.get_response(request)