import json
import time
import socket
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone
from users.models import DbClusterNode, DbReplicationLog
from whm.replication_core import (
    detect_db_engine,
    get_current_server_id,
    ensure_replication_config,
    allow_firewall_for_ip,
    remove_firewall_for_ip,
    create_replication_user,
    drop_replication_user,
    get_live_replication_telemetry,
    start_replica_link,
    pause_replica_link,
    resume_replica_link,
    promote_replica_to_primary,
    generate_pairing_token,
    parse_pairing_token
)
from users.panellogger import CpLogger

logger = CpLogger()

def get_server_ip():
    """Attempts to determine the server's public or primary IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ensure_local_node():
    """Ensures a local node entry exists in DbClusterNode."""
    local_ip = get_server_ip()
    local_node = DbClusterNode.objects.filter(is_local=True).first()
    if not local_node:
        local_node = DbClusterNode.objects.create(
            name=f"This Server ({local_ip})",
            node_role='primary',
            host=local_ip,
            mysql_port=3306,
            api_port=30,
            status='active',
            is_local=True
        )
    return local_node


def db_replication_home(request):
    """Main WHM view for Database Redundancy & Live Sync dashboard."""
    local_node = ensure_local_node()
    nodes = DbClusterNode.objects.all().order_by('-is_local', 'created_at')
    logs = DbReplicationLog.objects.all()[:25]
    telemetry = get_live_replication_telemetry()
    server_ip = get_server_ip()

    # Parse database-level selective replication settings
    try:
        selected_dbs = json.loads(local_node.selected_databases or '[]')
        if not isinstance(selected_dbs, list):
            selected_dbs = []
    except Exception:
        selected_dbs = [d.strip() for d in str(local_node.selected_databases).split(',') if d.strip()]

    databases_overview = get_local_databases_overview(selected_dbs)

    context = {
        'local_node': local_node,
        'nodes': nodes,
        'logs': logs,
        'telemetry': telemetry,
        'server_ip': server_ip,
        'selected_dbs': selected_dbs,
        'replicate_all': local_node.replicate_all,
        'databases_overview': databases_overview,
        'self_title': 'Database Redundancy & Live Sync',
    }
    return render(request, 'whm/db_replication.html', context)


@require_GET
def db_replication_status_api(request):
    """AJAX endpoint for real-time telemetry polling."""
    telemetry = get_live_replication_telemetry()
    nodes_data = []
    for node in DbClusterNode.objects.all().order_by('-is_local', 'created_at'):
        nodes_data.append({
            'id': node.id,
            'name': node.name,
            'role': node.node_role,
            'host': node.host,
            'status': node.status,
            'is_local': node.is_local,
            'replicate_all': node.replicate_all,
            'selected_databases': json.loads(node.selected_databases) if (node.selected_databases and node.selected_databases.startswith('[')) else [],
            'last_sync': node.last_sync.strftime('%Y-%m-%d %H:%M:%S') if node.last_sync else 'Never',
            'seconds_behind_master': node.seconds_behind_master,
            'last_error': node.last_error
        })

    local_node = ensure_local_node()
    try:
        selected_dbs = json.loads(local_node.selected_databases or '[]')
    except Exception:
        selected_dbs = []
    dbs_overview = get_local_databases_overview(selected_dbs)

    return JsonResponse({
        'status': 'success',
        'telemetry': telemetry,
        'nodes': nodes_data,
        'databases': dbs_overview,
        'replicate_all': local_node.replicate_all,
        'timestamp': timezone.now().strftime('%H:%M:%S')
    })


@csrf_exempt
@require_POST
def db_replication_generate_token_view(request):
    """Generates a node pairing token for the primary server."""
    local_ip = get_server_ip()
    ensure_replication_config(is_primary=True)
    token = generate_pairing_token(local_ip, panel_port=30)
    
    local_node = ensure_local_node()
    local_node.auth_token = token
    local_node.save()

    DbReplicationLog.objects.create(
        node=local_node,
        event_type='pair',
        message=f'Cluster pairing token generated for host {local_ip}'
    )

    return JsonResponse({
        'status': 'success',
        'token': token,
        'host': local_ip,
        'server_id': get_current_server_id()
    })


@csrf_exempt
@require_POST
def db_replication_pair_node(request):
    """
    Pairs this server as a replica to a primary, or adds a remote replica node record.
    Supports selective database-level replication so secondary server remains safe for other apps.
    """
    mode = request.POST.get('mode', 'token') # 'token' or 'manual'
    node_name = request.POST.get('node_name', 'Replica Node').strip()
    token_str = request.POST.get('token', '').strip()
    sync_scope = request.POST.get('sync_scope', 'selected').strip() # 'selected' or 'all'
    replicate_all = (sync_scope == 'all')

    # Parse selected databases
    dbs_raw = request.POST.get('selected_databases', '')
    selected_dbs = []
    if dbs_raw:
        try:
            selected_dbs = json.loads(dbs_raw) if dbs_raw.startswith('[') else [d.strip() for d in dbs_raw.split(',') if d.strip()]
        except Exception:
            selected_dbs = [d.strip() for d in dbs_raw.split(',') if d.strip()]
    else:
        selected_dbs = request.POST.getlist('selected_databases[]') or request.POST.getlist('selected_databases')

    if token_str or mode == 'token':
        payload, err = parse_pairing_token(token_str)
        if err:
            return JsonResponse({'status': 'error', 'message': f'Invalid token: {err}'})
        
        primary_host = payload.get('host')
        primary_port = payload.get('mysql_port', 3306)
        repl_user = request.POST.get('repl_user') or request.POST.get('user', 'olspanel_repl')
        repl_pass = request.POST.get('repl_password') or request.POST.get('password', '')
    else:
        primary_host = (request.POST.get('host') or request.POST.get('primary_host', '')).strip()
        primary_port = int(request.POST.get('port', 3306))
        repl_user = (request.POST.get('repl_user') or request.POST.get('user', 'olspanel_repl')).strip()
        repl_pass = (request.POST.get('repl_password') or request.POST.get('password', '')).strip()

    if not primary_host or not repl_user or not repl_pass:
        return JsonResponse({'status': 'error', 'message': 'Primary host, sync username, and password are required.'})

    # 1. Enable replication config locally with filters
    ensure_replication_config(
        is_primary=False,
        selected_databases=selected_dbs,
        replicate_all=replicate_all
    )

    # 2. Start replication link with selective database filtering
    success, msg = start_replica_link(
        master_host=primary_host,
        master_port=primary_port,
        repl_user=repl_user,
        repl_password=repl_pass,
        use_gtid=True,
        selected_databases=selected_dbs,
        replicate_all=replicate_all
    )

    if not success:
        return JsonResponse({'status': 'error', 'message': f'Failed to connect to Primary: {msg}'})

    # 3. Save remote primary node record
    primary_node, _ = DbClusterNode.objects.update_or_create(
        host=primary_host,
        defaults={
            'name': f"Primary ({primary_host})",
            'node_role': 'primary',
            'mysql_port': primary_port,
            'repl_user': repl_user,
            'repl_password': repl_pass,
            'status': 'active',
            'is_local': False,
            'replicate_all': replicate_all,
            'selected_databases': json.dumps(selected_dbs),
            'last_sync': timezone.now()
        }
    )

    # 4. Update local node role to replica with database filters
    local_node = ensure_local_node()
    local_node.node_role = 'replica'
    local_node.status = 'active'
    local_node.replicate_all = replicate_all
    local_node.selected_databases = json.dumps(selected_dbs)
    local_node.save()

    # 5. Create DbSyncRule entries
    for db_name in selected_dbs:
        DbSyncRule.objects.update_or_create(
            node=primary_node,
            database_name=db_name,
            defaults={'is_active': True, 'status': 'active', 'last_synced': timezone.now()}
        )

    scope_desc = "all databases" if replicate_all else f"{len(selected_dbs)} selected database(s)"
    DbReplicationLog.objects.create(
        node=primary_node,
        event_type='pair',
        message=f'Replication established with Primary {primary_host}:{primary_port} ({scope_desc}). Other local databases remain isolated and writable.'
    )

    return JsonResponse({
        'status': 'success',
        'message': f'Replica paired and synchronized successfully with Primary ({scope_desc})!'
    })


@csrf_exempt
@require_POST
def db_replication_toggle_db(request):
    """
    Toggles live replication on or off for an individual database.
    Dynamically reconfigures MySQL replication filters so other databases are untouched.
    """
    db_name = request.POST.get('database_name', '').strip()
    action = request.POST.get('action', 'toggle').strip()  # 'enable', 'disable', or 'toggle'

    if not db_name:
        return JsonResponse({'status': 'error', 'message': 'Database name is required.'})

    local_node = ensure_local_node()
    try:
        selected_dbs = json.loads(local_node.selected_databases or '[]')
        if not isinstance(selected_dbs, list):
            selected_dbs = []
    except Exception:
        selected_dbs = []

    if action == 'enable':
        if db_name not in selected_dbs:
            selected_dbs.append(db_name)
        is_synced = True
    elif action == 'disable':
        if db_name in selected_dbs:
            selected_dbs.remove(db_name)
        is_synced = False
    else:  # toggle
        if db_name in selected_dbs:
            selected_dbs.remove(db_name)
            is_synced = False
        else:
            selected_dbs.append(db_name)
            is_synced = True

    # Save to node
    local_node.selected_databases = json.dumps(selected_dbs)
    local_node.replicate_all = False  # Explicitly selective
    local_node.save()

    # Update DbSyncRule
    DbSyncRule.objects.update_or_create(
        node=local_node,
        database_name=db_name,
        defaults={'is_active': is_synced, 'status': 'active' if is_synced else 'paused'}
    )

    # Apply replication filter dynamically
    success, msg = apply_database_replication_filters(
        selected_databases=selected_dbs,
        replicate_all=False
    )

    DbReplicationLog.objects.create(
        node=local_node,
        database_name=db_name,
        event_type='filter_update',
        message=f'Database `{db_name}` replication {"enabled" if is_synced else "disabled"}. Total synced databases: {len(selected_dbs)}'
    )

    return JsonResponse({
        'status': 'success',
        'database_name': db_name,
        'is_synced': is_synced,
        'selected_count': len(selected_dbs),
        'message': f'Database `{db_name}` is now {"replicated in real time" if is_synced else "local only (not replicated)"}.'
    })


@csrf_exempt
@require_POST
def db_replication_update_db_rules(request):
    """
    Bulk updates the replication filter scope (selected databases vs all).
    """
    sync_scope = request.POST.get('sync_scope', 'selected').strip()
    replicate_all = (sync_scope == 'all')

    dbs_raw = request.POST.get('selected_databases', '')
    selected_dbs = []
    if dbs_raw:
        try:
            selected_dbs = json.loads(dbs_raw) if dbs_raw.startswith('[') else [d.strip() for d in dbs_raw.split(',') if d.strip()]
        except Exception:
            selected_dbs = [d.strip() for d in dbs_raw.split(',') if d.strip()]
    else:
        selected_dbs = request.POST.getlist('selected_databases[]') or request.POST.getlist('selected_databases')

    local_node = ensure_local_node()
    local_node.replicate_all = replicate_all
    local_node.selected_databases = json.dumps(selected_dbs)
    local_node.save()

    # Apply filters dynamically
    success, msg = apply_database_replication_filters(
        selected_databases=selected_dbs,
        replicate_all=replicate_all
    )

    DbReplicationLog.objects.create(
        node=local_node,
        event_type='filter_update',
        message=f'Replication scope updated: {"All databases" if replicate_all else f"{len(selected_dbs)} selected databases"}'
    )

    return JsonResponse({
        'status': 'success',
        'replicate_all': replicate_all,
        'selected_count': len(selected_dbs),
        'message': 'Database replication settings saved and applied.'
    })


@csrf_exempt
@require_POST
def db_replication_create_user_view(request):
    """Creates a replication user and configures firewall for a replica IP."""
    replica_ip = request.POST.get('replica_ip', '').strip()
    repl_user = (request.POST.get('repl_user') or request.POST.get('user', 'olspanel_repl')).strip()
    repl_pass = (request.POST.get('repl_password') or request.POST.get('password', '')).strip()

    if not replica_ip:
        return JsonResponse({'status': 'error', 'message': 'Replica IP address is required.'})

    # 1. Ensure binlog is enabled on primary
    ensure_replication_config(is_primary=True)

    # 2. Allow firewall port
    allow_firewall_for_ip(replica_ip)

    # 3. Create replication user
    success, res = create_replication_user(replica_ip, username=repl_user, password=repl_pass or None)
    if not success:
        return JsonResponse({'status': 'error', 'message': f'Failed to create replication user: {res}'})

    # 4. Add or update node entry for the replica
    node, _ = DbClusterNode.objects.update_or_create(
        host=replica_ip,
        defaults={
            'name': f"Replica ({replica_ip})",
            'node_role': 'replica',
            'mysql_port': 3306,
            'repl_user': res['user'],
            'repl_password': res['password'],
            'status': 'active',
            'is_local': False,
            'last_sync': timezone.now()
        }
    )

    DbReplicationLog.objects.create(
        node=node,
        event_type='pair',
        message=f'Replication credentials & firewall rule provisioned for replica {replica_ip}'
    )

    return JsonResponse({
        'status': 'success',
        'message': f'Replication user {res["user"]} provisioned for IP {replica_ip}',
        'credentials': res
    })


@csrf_exempt
@require_POST
def db_replication_action(request):

    """Handles operational cluster actions: pause, resume, promote, delete, enable_binlog."""
    action = request.POST.get('action', '').strip()
    node_id = request.POST.get('node_id')

    if action == 'pause':
        success, msg = pause_replica_link()
        if success:
            local_node = ensure_local_node()
            local_node.status = 'paused'
            local_node.save()
            DbReplicationLog.objects.create(node=local_node, event_type='pause', message='Replication paused by admin.')
            return JsonResponse({'status': 'success', 'message': 'Replication paused.'})
        return JsonResponse({'status': 'error', 'message': msg})

    elif action == 'resume':
        success, msg = resume_replica_link()
        if success:
            local_node = ensure_local_node()
            local_node.status = 'active'
            local_node.save()
            DbReplicationLog.objects.create(node=local_node, event_type='resume', message='Replication resumed by admin.')
            return JsonResponse({'status': 'success', 'message': 'Replication resumed.'})
        return JsonResponse({'status': 'error', 'message': msg})

    elif action == 'promote':
        success, msg = promote_replica_to_primary()
        if success:
            return JsonResponse({'status': 'success', 'message': 'Node successfully promoted to Primary Master! Write operations are now enabled.'})
        return JsonResponse({'status': 'error', 'message': msg})

    elif action == 'enable_binlog':
        success, msg = ensure_replication_config(is_primary=True)
        if success:
            return JsonResponse({'status': 'success', 'message': 'Binary logging & GTID enabled successfully!'})
        return JsonResponse({'status': 'error', 'message': msg})

    elif action == 'delete' and node_id:
        try:
            node = DbClusterNode.objects.get(id=node_id, is_local=False)
            remove_firewall_for_ip(node.host)
            drop_replication_user(node.host, node.repl_user)
            node_host = node.host
            node.delete()
            DbReplicationLog.objects.create(event_type='delete', message=f'Cluster node {node_host} removed.')
            return JsonResponse({'status': 'success', 'message': f'Node {node_host} disconnected and removed.'})
        except DbClusterNode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Node not found or cannot delete local node.'})

    return JsonResponse({'status': 'error', 'message': f'Unknown or unsupported action: {action}'})
