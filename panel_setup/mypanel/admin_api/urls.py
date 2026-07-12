from django.urls import path
from .views import *
from . import views
urlpatterns = [
    path('', home, name='api_users-home'),
    path('add_user/', add_user, name='api_add_user_api'),
    path('suspend_user/', suspend_user, name='api_suspend_user'),
    path('update_user/', update_user, name='api_update_user'),
    path('packages_list/', packages_list, name='api_packages_list'),
    path('new_package/', new_package, name='api_new_package'),
    path('issue_ssl/', issue_ssl, name='api_issue_ssl'),
    path('add_domain/', add_domain, name='api_add_domain'),
    path('database_add/', database_add, name='api_database_add'),
    path('sso_login/', sso_login, name='api_sso_login'),
   

]
