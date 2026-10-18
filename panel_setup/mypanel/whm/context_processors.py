import requests
from .plugin import * 



def dynamic_plugins(request):
    users_plugin = get_users_plugins_list()
    database_plugin = get_database_plugins_list()
    domain_plugin = get_domain_plugins_list()
    file_plugin = get_file_plugins_list()
    security_plugin = get_security_plugins_list()
    service_plugin = get_server_plugins_list()
    email_plugin = get_email_plugins_list()
    php_plugin = get_php_plugins_list()
    node_plugin = get_node_plugins_list()
    advance_plugin = get_advance_plugins_list()
    configuration_plugin = get_configuration_plugins_list()
    account_plugin = get_account_plugins_list()
    support_plugin = get_support_plugins_list()
     
    
    return {
        'w_users_plugin': users_plugin,
        'w_database_plugin': database_plugin,
        'w_domain_plugin': domain_plugin,
        'w_file_plugin': file_plugin,
        'w_security_plugin': security_plugin,
        'w_service_plugin': service_plugin,
        'w_email_plugin': email_plugin,
        'w_php_plugin': php_plugin,
        'w_node_plugin': node_plugin,
        'w_advance_plugin': advance_plugin,
        'w_configuration_plugin': configuration_plugin,
        'w_account_plugin': account_plugin,
        'w_support_plugin': support_plugin,
    }
    
    
from users.database import get_user_data_by_id

def admin_user_context(request):
    admin_user = getattr(request, 'admin_user', None)
    if not admin_user and hasattr(request, 'user') and request.user.is_authenticated:
        if getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False):
            admin_user = request.user
        else:
            u_data = get_user_data_by_id(request.user.id)
            if u_data and u_data.get('whm') == 1:
                admin_user = request.user

    is_impersonating = False
    if admin_user and hasattr(request, 'user') and request.user.is_authenticated:
        if request.user.id != admin_user.id:
            is_impersonating = True

    return {
        'admin_user': admin_user,
        'is_admin': bool(admin_user and not is_impersonating),
        'is_impersonating': is_impersonating
    }