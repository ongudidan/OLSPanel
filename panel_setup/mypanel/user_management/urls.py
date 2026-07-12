from django.contrib import admin

from django.urls import path, include, re_path

from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth import views as auth_views
from users.views import *

from users.forms import LoginForm
from django.views.static import serve
from django.views.generic import RedirectView
urlpatterns = [

    path('', include('users.urls')),
    path("file_manager/", include("file_manager.urls")),
    path("whm/", include("whm.urls")),
    path("api/", include("api.urls")),
    path("admin_api/", include("admin_api.urls")),

    path('login/', CustomLoginView.as_view(redirect_authenticated_user=True, template_name='users/login.html',
                                           authentication_form=LoginForm), name='login'),

    path('logout/', user_logout, name='logout'),
    re_path(r'^3rdparty/(?P<php_file>.+)$', web_server),

    

    
    

    re_path(r'^oauth/', include('social_django.urls', namespace='social')),

]

# ---- AUTO DISCOVER MODULES ----
MODULES_DIR = os.path.join(settings.BASE_DIR, 'modules')
if os.path.isdir(MODULES_DIR):
    for module_name in os.listdir(MODULES_DIR):
        module_path = os.path.join(MODULES_DIR, module_name)
        urls_file = os.path.join(module_path, 'urls.py')
        if os.path.isdir(module_path) and os.path.isfile(urls_file):
            try:
                module_url = f"modules.{module_name}.urls"
                urlpatterns.append(
                    path(f'module/{module_name}/', include(module_url))
                )
                print(f"Loaded plugin: {module_name}")
            except Exception as e:
                print(f"Failed to load plugin {module_name}: {e}")


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
    
handler404 = 'users.views.handler404'
handler500 = 'users.views.handler500'
handler403 = 'users.views.handler403'