from django.urls import path
from .views import *
from . import views

urlpatterns = [
    path('', home, name='file_manager_home'),
    path('php_editor/', php_editor, name='php_editor'),
    path('view/', view, name='view'),
    path('file_action/', file_action, name='file_action'),
    path('file_folder_list/', file_folder_list, name='file_folder_list'),
    path('folder_list/', folder_list, name='folder_list'),
    path('download/', download, name='download'),
    path('upload/', upload, name='upload'),
    path('upload_db/<str:db_name>/', upload_db, name='upload_db'),
    path('export_db/<str:db_name>/', export_db, name='export_db'),
    path('upload_from_url/', upload_from_url, name='upload_from_url'),
    path('media_viewer/', media_viewer, name='media_viewer'),
    path('upload_from_url_bk/', upload_from_url_bk, name='upload_from_url_bk'),
    path('upload_bk/', upload_bk, name='upload_bk'),
    path("file_setting/", update_user_settings, name="file_setting"),

   
]
