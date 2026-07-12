from django.urls import path
from .views import *
from . import views
urlpatterns = [
    path('', home, name='api_users-home'),
    path('add_domain/', add_domain, name='api_users-domain'),
    path('domain_list/', domain_list, name='api_domain_list'),
    path('domain_issue_ssl/', domain_issue_ssl, name='api_domain_list_ssl'),
    path('db_make/', db_make, name='api_db_make'),
    path('db_user_make/<str:db>/', db_user_make, name='api_db_user_make'),
    path('database_list/', database_list, name='api_database_list'),
    path('database_exists/', database_exists, name='api_database_exists'),
    path('check_db_user/', check_db_user, name='api_check_db_user'),
    path('database_userlist/', database_userlist, name='api_database_userlist'),
    path('cronjob_list/', cronjob_list, name='api_cronjob_list'),
    path('cronjob_add/', cronjob_add, name='api_cronjob_add'),
    path('cronjob_delete/<int:line>/', cronjob_delete, name='api_cronjob_delete'), 
    path('fix_user_permission/', fix_user_permission, name='api_fix_user_permission'),

]
