from django.shortcuts import redirect, render

def get_license_status(request):
    return "active"

class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
