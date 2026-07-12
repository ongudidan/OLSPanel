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
    
    
def admin_user_context(request):
    return {
        'admin_user': getattr(request, 'admin_user', None),
        'is_admin': bool(getattr(request, 'admin_user', None))
    }