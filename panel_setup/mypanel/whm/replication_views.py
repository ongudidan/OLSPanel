import json
import time
import socket
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone
from users.models import DbClusterNode, DbReplicationLog, DbSyncRule
from whm.replication_core import (
    detect_db_engine,
    get_current_server_id,
    ensure_replication_config,
    get_local_databases_overview,
    assign_database_to_replicas,
    allow_firewall_for_ip,
    remove_firewall_for_ip,
    create_replication_user,
    drop_replication_user,
    get_live_replication_telemetry,
    parse_all_replica_channels,
    start_replica_channel,
    stop_replica_channel,
    restart_replica_channel,
    reset_replica_channel,
    start_all_replica_channels,
    stop_all_replica_channels,
    skip_replica_error,
    clone_databases_from_primary,
    get_primary_coordinates,
    get_connected_replicas_telemetry,
    kill_replica_process_thread,
    send_live_parity_test,
    verify_live_parity_feed,
    toggle_read_only,
    sync_timezone_from_primary,
    test_tcp_connectivity,
    promote_replica_to_primary,
    generate_pairing_token,
    parse_pairing_token
)
from users.panellogger import CpLogger

logger = CpLogger()

_SERVER_IP_CACHE = None
_SERVER_IP_CACHE_TIME = 0

def get_server_ip():
    """Attempts to determine the server's public or primary IP address (cached for 5 minutes)."""
    global _SERVER_IP_CACHE, _SERVER_IP_CACHE_TIME
    now = time.time()
    if _SERVER_IP_CACHE and (now - _SERVER_IP_CACHE_TIME < 300):
        return _SERVER_IP_CACHE
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        _SERVER_IP_CACHE = ip
        _SERVER_IP_CACHE_TIME = now
        return ip
    except Exception:
        return _SERVER_IP_CACHE or "127.0.0.1"


def ensure_local_node():
    """Ensures a local node entry exists in DbClusterNode."""
    local_node = DbClusterNode.objects.filter(is_local=True).first()
    if not local_node:
        local_ip = get_server_ip()
        local_node = DbClusterNode.objects.create(
            name=f"This Server ({local_ip})",
            node_role='primary',
            channel_name='default',
            host=local_ip,
            mysql_port=3306,
            api_port=30,
            status='active',
            is_local=True
        )
    return local_node


def get_replication_base_context(active_tab='databases'):
    """Collects baseline redundancy telemetry, nodes, and database mappings."""
    local_node = ensure_local_node()
    nodes = list(DbClusterNode.objects.all().order_by('-is_local', 'created_at'))
    
    # Authorized Replica Clients (Outbound Primary)
    replica_clients = [n for n in nodes if not n.is_local and n.node_role == 'replica']
    for client in replica_clients:
        try:
            client.databases_list = json.loads(client.selected_databases or '[]')
        except Exception:
            client.databases_list = [d.strip() for d in str(client.selected_databases).split(',') if d.strip()]

    # Inbound Primary Sources
    inbound_sources = [n for n in nodes if not n.is_local and n.node_role == 'primary']
    for src in inbound_sources:
        try:
            src.databases_list = json.loads(src.selected_databases or '[]')
        except Exception:
            src.databases_list = []

    telemetry = get_live_replication_telemetry()
    channels = telemetry.get('channels', [])
    connected_replicas = telemetry.get('connected_replicas', [])
    server_ip = get_server_ip()

    # Parse database-level selective replication settings
    try:
        selected_dbs = json.loads(local_node.selected_databases or '[]')
        if not isinstance(selected_dbs, list):
            selected_dbs = []
    except Exception:
        selected_dbs = [d.strip() for d in str(local_node.selected_databases).split(',') if d.strip()]

    databases_overview = get_local_databases_overview(selected_dbs, channels=channels, connected_replicas=connected_replicas)

    # Counts breakdown
    primary_dbs_count = sum(1 for d in databases_overview if d['db_role'] in ['primary_source', 'hybrid'])
    replica_dbs_count = sum(1 for d in databases_overview if d['db_role'] in ['inbound_replica', 'hybrid'])
    standalone_dbs_count = sum(1 for d in databases_overview if d['db_role'] == 'standalone')

    ctx = {
        'active_tab': active_tab,
        'local_node': local_node,
        'nodes': nodes,
        'replica_clients': replica_clients,
        'inbound_sources': inbound_sources,
        'telemetry': telemetry,
        'channels': channels,
        'connected_replicas': connected_replicas,
        'server_ip': server_ip,
        'selected_dbs': selected_dbs,
        'replicate_all': local_node.replicate_all,
        'databases_overview': databases_overview,
        'primary_dbs_count': primary_dbs_count,
        'replica_dbs_count': replica_dbs_count,
        'standalone_dbs_count': standalone_dbs_count,
        'self_title': 'Database Redundancy & Live Sync',
    }

    if active_tab == 'topology':
        ctx['logs'] = list(DbReplicationLog.objects.all()[:50])
    elif active_tab == 'parity':
        ctx['parity_feed'] = verify_live_parity_feed()

    return ctx


def db_replication_databases_view(request):
    """View 1: All Databases Matrix & Per-DB Replica / Master Assignment."""
    context = get_replication_base_context(active_tab='databases')
    return render(request, 'whm/db_replication/databases.html', context)


def db_replication_clients_view(request):
    """View 2: Allowed Replica Clients (IP Authorizations & Assigned DBs)."""
    context = get_replication_base_context(active_tab='clients')
    return render(request, 'whm/db_replication/clients.html', context)


def db_replication_channels_view(request):
    """View 3: Inbound Multi-Source Replication Channels."""
    context = get_replication_base_context(active_tab='channels')
    return render(request, 'whm/db_replication/channels.html', context)


def db_replication_parity_view(request):
    """View 4: Real-time Parity Verification Feed & Heartbeat Stream."""
    context = get_replication_base_context(active_tab='parity')
    return render(request, 'whm/db_replication/parity.html', context)


def db_replication_topology_view(request):
    """View 5: Cluster Topology, Server Nodes & Event Audit Log."""
    context = get_replication_base_context(active_tab='topology')
    return render(request, 'whm/db_replication/topology.html', context)


def db_replication_home(request):
    """Default entry point for Database Replication - forwards to Databases Matrix."""
    return db_replication_databases_view(request)


@require_GET
def db_replication_status_api(request):
    """AJAX endpoint for real-time telemetry polling across all channels and connected replicas."""
    telemetry = get_live_replication_telemetry()
    channels = telemetry.get('channels', [])
    connected_replicas = telemetry.get('connected_replicas', [])
    
    nodes_data = []
    for node in DbClusterNode.objects.all().order_by('-is_local', 'created_at'):
        nodes_data.append({
            'id': node.id,
            'name': node.name,
            'role': node.node_role,
            'channel_name': node.channel_name,
            'host': node.host,
            'status': node.status,
            'is_local': node.is_local,
            'replicate_all': node.replicate_all,
            'selected_databases': json.loads(node.selected_databases) if (node.selected_databases and node.selected_databases.startswith('[')) else [],
            'rewrite_rules': json.loads(node.rewrite_rules) if (node.rewrite_rules and node.rewrite_rules.startswith('{')) else {},
            'last_sync': node.last_sync.strftime('%Y-%m-%d %H:%M:%S') if node.last_sync else 'Never',
            'seconds_behind_master': node.seconds_behind_master,
            'last_error': node.last_error
        })

    local_node = ensure_local_node()
    try:
        selected_dbs = json.loads(local_node.selected_databases or '[]')
    except Exception:
        selected_dbs = []
    dbs_overview = get_local_databases_overview(selected_dbs, channels=channels, connected_replicas=connected_replicas)
    parity_feed = verify_live_parity_feed()

    return JsonResponse({
        'status': 'success',
        'telemetry': telemetry,
        'channels': channels,
        'connected_replicas': connected_replicas,
        'nodes': nodes_data,
        'databases': dbs_overview,
        'parity_feed': parity_feed,
        'replicate_all': local_node.replicate_all,
        'read_only': telemetry.get('read_only', False),
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
        message=f'Cluster pairing key generated for host {local_ip}'
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
    Pairs this server as a replica to a primary, or adds an additional multi-source replication channel.
    Supports online baseline data cloning, database renaming / rewrites, and timezone sync.
    """
    mode = request.POST.get('mode', 'token')
    channel_name = request.POST.get('channel_name', '').strip()
    sync_scope = request.POST.get('sync_scope', 'selected').strip()
    replicate_all = (sync_scope == 'all')
    clone_strategy = request.POST.get('clone_strategy', 'clone').strip() # 'clone', 'coordinates', or 'gtid'

    token_str = request.POST.get('token', '').strip()
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
        primary_port = int(request.POST.get('port', 3306) or 3306)
        repl_user = (request.POST.get('repl_user') or request.POST.get('user', 'olspanel_repl')).strip()
        repl_pass = (request.POST.get('repl_password') or request.POST.get('password', '')).strip()

    if not primary_host or not repl_user or not repl_pass:
        return JsonResponse({'status': 'error', 'message': 'Primary host, sync username, and password are required.'})

    # Auto-generate channel name if multi-source
    existing_channels = parse_all_replica_channels()
    if not channel_name:
        if len(existing_channels) == 0:
            channel_name = 'default'
        else:
            channel_name = f"source_{len(existing_channels) + 1}"

    # Parse selected databases and rewrite mappings
    dbs_raw = request.POST.get('selected_databases', '')
    selected_dbs = []
    rewrite_rules = {}
    db_pairs = []

    if dbs_raw:
        try:
            parsed = json.loads(dbs_raw) if dbs_raw.startswith('[') else [d.strip() for d in dbs_raw.split(',') if d.strip()]
            for item in parsed:
                if isinstance(item, str) and ("->" in item or ":" in item):
                    delim = "->" if "->" in item else ":"
                    src, tgt = item.split(delim, 1)
                    src, tgt = src.strip(), tgt.strip()
                    rewrite_rules[src] = tgt
                    selected_dbs.append(tgt)
                    db_pairs.append((src, tgt))
                else:
                    d_clean = str(item).strip()
                    if d_clean:
                        selected_dbs.append(d_clean)
                        db_pairs.append((d_clean, d_clean))
        except Exception:
            pass

    if not db_pairs:
        post_dbs = request.POST.getlist('selected_databases[]') or request.POST.getlist('selected_databases')
        for d in post_dbs:
            d_clean = str(d).strip()
            if d_clean:
                selected_dbs.append(d_clean)
                db_pairs.append((d_clean, d_clean))

    # Pre-flight reachability & auth test
    reachable, reach_msg = test_tcp_connectivity(primary_host, primary_port)
    if not reachable:
        return JsonResponse({'status': 'error', 'message': f'Cannot reach Primary server ({primary_host}:{primary_port}): {reach_msg}. Check firewall.'})

    # 1. Update config file locally with filters & read_only mode
    ensure_replication_config(
        is_primary=False,
        selected_databases=selected_dbs,
        rewrite_rules=rewrite_rules,
        replicate_all=replicate_all,
        read_only=True
    )

    # 2. Timezone sync
    sync_timezone_from_primary(primary_host, primary_port, repl_user, repl_pass)

    master_log_file = ""
    master_log_pos = ""

    # 3. Initial Baseline Snapshot Clone (if requested)
    if clone_strategy == 'clone' and db_pairs:
        success, clone_msg = clone_databases_from_primary(
            master_host=primary_host,
            master_port=primary_port,
            repl_user=repl_user,
            repl_password=repl_pass,
            db_pairs=db_pairs,
            channel_name=channel_name
        )
        if not success:
            return JsonResponse({'status': 'error', 'message': f'Baseline clone failed: {clone_msg}'})
    elif clone_strategy == 'coordinates':
        master_log_file, master_log_pos = get_primary_coordinates(primary_host, primary_port, repl_user, repl_pass)

    # 4. Configure and start replication stream
    success, start_msg = start_replica_channel(
        channel_name=channel_name,
        master_host=primary_host,
        master_port=primary_port,
        repl_user=repl_user,
        repl_password=repl_pass,
        master_log_file=master_log_file,
        master_log_pos=master_log_pos,
        use_gtid=(clone_strategy != 'coordinates')
    )

    if not success:
        return JsonResponse({'status': 'error', 'message': f'Failed to start replication stream: {start_msg}'})

    # 5. Save remote node record
    primary_node, _ = DbClusterNode.objects.update_or_create(
        host=primary_host,
        channel_name=channel_name,
        defaults={
            'name': f"Primary [{channel_name}] ({primary_host})",
            'node_role': 'primary',
            'mysql_port': primary_port,
            'repl_user': repl_user,
            'repl_password': repl_pass,
            'status': 'active',
            'is_local': False,
            'replicate_all': replicate_all,
            'selected_databases': json.dumps(selected_dbs),
            'rewrite_rules': json.dumps(rewrite_rules),
            'auto_cloned': (clone_strategy == 'clone'),
            'last_sync': timezone.now()
        }
    )

    # 6. Update local node role
    local_node = ensure_local_node()
    local_node.node_role = 'replica'
    local_node.status = 'active'
    local_node.replicate_all = replicate_all
    local_node.selected_databases = json.dumps(selected_dbs)
    local_node.rewrite_rules = json.dumps(rewrite_rules)
    local_node.save()

    # 7. Create DbSyncRule entries
    for p in db_pairs:
        src, tgt = p[0], p[1]
        DbSyncRule.objects.update_or_create(
            node=primary_node,
            database_name=src,
            defaults={
                'channel_name': channel_name,
                'target_database_name': tgt,
                'is_active': True,
                'status': 'active',
                'last_synced': timezone.now()
            }
        )

    DbReplicationLog.objects.create(
        node=primary_node,
        event_type='pair',
        message=f"Replication channel '{channel_name}' streaming from {primary_host}:{primary_port} (Databases: {', '.join(selected_dbs) if selected_dbs else 'All'})."
    )

    return JsonResponse({
        'status': 'success',
        'channel_name': channel_name,
        'message': f"Replication channel '{channel_name}' linked and streaming live from {primary_host}!"
    })


@csrf_exempt
@require_POST
def db_replication_resync(request):
    """
    Re-clones and synchronizes a specific replication channel or database with a fresh snapshot.
    """
    channel_name = request.POST.get('channel_name', 'default').strip()
    node_id = request.POST.get('node_id')

    node = None
    if node_id:
        node = DbClusterNode.objects.filter(id=node_id).first()
    if not node:
        node = DbClusterNode.objects.filter(channel_name=channel_name, is_local=False).first()
    if not node:
        node = DbClusterNode.objects.filter(is_local=False).first()

    if not node:
        return JsonResponse({'status': 'error', 'message': 'Replication source node not found.'})

    try:
        selected_dbs = json.loads(node.selected_databases or '[]')
    except Exception:
        selected_dbs = []

    try:
        rewrite_rules = json.loads(node.rewrite_rules or '{}')
    except Exception:
        rewrite_rules = {}

    db_pairs = []
    if rewrite_rules:
        for s, t in rewrite_rules.items():
            db_pairs.append((s, t))
    elif selected_dbs:
        for d in selected_dbs:
            db_pairs.append((d, d))
    else:
        # Clone all local databases
        all_dbs = get_local_databases_overview()
        for d in all_dbs:
            db_pairs.append((d['name'], d['name']))

    stop_replica_channel(channel_name)

    success, msg = clone_databases_from_primary(
        master_host=node.host,
        master_port=node.mysql_port,
        repl_user=node.repl_user,
        repl_password=node.repl_password,
        db_pairs=db_pairs,
        channel_name=channel_name
    )

    if not success:
        return JsonResponse({'status': 'error', 'message': f'Re-sync failed: {msg}'})

    restart_replica_channel(channel_name)

    DbReplicationLog.objects.create(
        node=node,
        event_type='sync',
        message=f"Fresh baseline re-sync completed for channel '{channel_name}' ({len(db_pairs)} database(s))."
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Databases successfully re-synced and streaming live on channel '{channel_name}'!"
    })


@csrf_exempt
@require_POST
def db_replication_skip_error(request):
    """Bypasses a blocking SQL error on a specific replication channel or across all channels."""
    channel_name = request.POST.get('channel_name', '').strip()
    success, msg = skip_replica_error(channel_name=channel_name or None)
    if success:
        local_node = ensure_local_node()
        DbReplicationLog.objects.create(
            node=local_node,
            event_type='error_skip',
            message=f"Bypassed 1 SQL statement on channel '{channel_name or 'all'}' and resumed stream."
        )
        return JsonResponse({'status': 'success', 'message': msg})
    return JsonResponse({'status': 'error', 'message': msg})


@csrf_exempt
@require_POST
def db_replication_parity_test(request):
    """Executes or reads a live parity write verification test."""
    action = request.POST.get('action', 'send').strip()
    target_db = request.POST.get('target_db', '').strip()

    if action == 'send':
        success, msg = send_live_parity_test(target_db=target_db)
        if success:
            local_node = ensure_local_node()
            DbReplicationLog.objects.create(
                node=local_node,
                event_type='parity_test',
                message=msg
            )
            return JsonResponse({'status': 'success', 'message': msg})
        return JsonResponse({'status': 'error', 'message': msg})
    else:
        feed = verify_live_parity_feed(target_db=target_db)
        return JsonResponse({'status': 'success', 'feed': feed})


@csrf_exempt
@require_POST
def db_replication_toggle_readonly(request):
    """Toggles read_only safeguard mode."""
    enable = request.POST.get('enable', 'true').lower() in ['1', 'true', 'yes', 'on']
    success, msg = toggle_read_only(enable)
    if success:
        local_node = ensure_local_node()
        DbReplicationLog.objects.create(
            node=local_node,
            event_type='readonly_toggle',
            message=msg
        )
        return JsonResponse({'status': 'success', 'message': msg, 'read_only': enable})
    return JsonResponse({'status': 'error', 'message': msg})


@csrf_exempt
@require_POST
def db_replication_channel_action(request):
    """Handles operational channel actions: start, stop, restart, reset."""
    action = request.POST.get('action', '').strip()
    channel_name = request.POST.get('channel_name', 'default').strip()

    if action == 'start':
        success, msg = (start_all_replica_channels() if channel_name == 'all' else start_replica_channel(channel_name))
    elif action == 'stop':
        success, msg = (stop_all_replica_channels() if channel_name == 'all' else stop_replica_channel(channel_name))
    elif action == 'restart':
        success, msg = restart_replica_channel(channel_name)
    elif action == 'reset':
        success, msg = reset_replica_channel(channel_name)
        if success:
            DbClusterNode.objects.filter(channel_name=channel_name, is_local=False).delete()
    else:
        return JsonResponse({'status': 'error', 'message': f'Unsupported channel action: {action}'})

    if success:
        local_node = ensure_local_node()
        DbReplicationLog.objects.create(
            node=local_node,
            event_type='channel_action',
            message=f"Channel '{channel_name}' action '{action}' executed."
        )
        return JsonResponse({'status': 'success', 'message': msg})
    return JsonResponse({'status': 'error', 'message': msg})


@csrf_exempt
@require_POST
def db_replication_kill_thread(request):
    """Kills a replica binlog dump streaming process thread on Primary."""
    thread_id = request.POST.get('thread_id', '').strip()
    if not thread_id:
        return JsonResponse({'status': 'error', 'message': 'Thread ID is required.'})

    success, msg = kill_replica_process_thread(thread_id)
    if success:
        local_node = ensure_local_node()
        DbReplicationLog.objects.create(
            node=local_node,
            event_type='kill_thread',
            message=f"Terminated streaming process thread #{thread_id}."
        )
        return JsonResponse({'status': 'success', 'message': msg})
    return JsonResponse({'status': 'error', 'message': msg})


@csrf_exempt
@require_POST
def db_replication_test_connection(request):
    """Tests TCP connection reachability to a remote MySQL host & port."""
    host = request.POST.get('host', '').strip()
    port = int(request.POST.get('port', 3306) or 3306)
    if not host:
        return JsonResponse({'status': 'error', 'message': 'Host IP is required.'})

    reachable, msg = test_tcp_connectivity(host, port)
    return JsonResponse({
        'status': 'success' if reachable else 'error',
        'reachable': reachable,
        'message': msg
    })


@csrf_exempt
@require_POST
def db_replication_toggle_db(request):
    """Toggles live replication on or off for an individual database."""
    db_name = request.POST.get('database_name') or request.POST.get('db_name', '')
    if not db_name and request.body:
        try:
            body_data = json.loads(request.body.decode('utf-8'))
            db_name = body_data.get('database_name') or body_data.get('db_name', '')
        except Exception:
            pass
    db_name = str(db_name).strip()
    action = request.POST.get('action', 'toggle').strip()

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
    else:
        if db_name in selected_dbs:
            selected_dbs.remove(db_name)
            is_synced = False
        else:
            selected_dbs.append(db_name)
            is_synced = True

    local_node.selected_databases = json.dumps(selected_dbs)
    local_node.replicate_all = False
    local_node.save()

    DbSyncRule.objects.update_or_create(
        node=local_node,
        database_name=db_name,
        defaults={'is_active': is_synced, 'status': 'active' if is_synced else 'paused'}
    )

    ensure_replication_config(
        is_primary=(local_node.node_role == 'primary'),
        selected_databases=selected_dbs,
        replicate_all=False
    )

    DbReplicationLog.objects.create(
        node=local_node,
        database_name=db_name,
        event_type='filter_update',
        message=f"Database `{db_name}` replication {'enabled' if is_synced else 'disabled'}. Total synced: {len(selected_dbs)}"
    )

    return JsonResponse({
        'status': 'success',
        'database_name': db_name,
        'is_synced': is_synced,
        'selected_count': len(selected_dbs),
        'message': f"Database `{db_name}` is now {'replicated in real time' if is_synced else 'local only (not replicated)'}."
    })


@csrf_exempt
@require_POST
def db_replication_update_db_rules(request):
    """Bulk updates replication filter scope (selected databases vs all)."""
    try:
        sync_scope = request.POST.get('sync_scope', 'selected').strip()
        replicate_all = (sync_scope == 'all')

        local_node = ensure_local_node()
        local_node.replicate_all = replicate_all

        dbs_raw = request.POST.get('selected_databases', '')
        selected_dbs = []
        if dbs_raw:
            try:
                selected_dbs = json.loads(dbs_raw) if dbs_raw.startswith('[') else [d.strip() for d in dbs_raw.split(',') if d.strip()]
            except Exception:
                selected_dbs = [d.strip() for d in dbs_raw.split(',') if d.strip()]
        else:
            post_list = request.POST.getlist('selected_databases[]') or request.POST.getlist('selected_databases')
            if post_list:
                selected_dbs = post_list
            else:
                selected_dbs = json.loads(local_node.selected_databases or '[]')

        local_node.selected_databases = json.dumps(selected_dbs)
        local_node.save()

        ensure_replication_config(
            is_primary=(local_node.node_role == 'primary'),
            selected_databases=selected_dbs,
            replicate_all=replicate_all
        )

        DbReplicationLog.objects.create(
            node=local_node,
            event_type='filter_update',
            message=f"Replication scope updated: {'All databases' if replicate_all else f'{len(selected_dbs)} selected databases'}"
        )

        return JsonResponse({
            'status': 'success',
            'replicate_all': replicate_all,
            'selected_count': len(selected_dbs),
            'message': 'Database replication settings saved and applied.'
        })
    except Exception as e:
        logger.error(f"Error in db_replication_update_db_rules: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@require_POST
def db_replication_save_replica_client(request):
    """
    Creates or updates an Authorized Replica Client IP with granular assigned databases,
    sync credentials, and UFW firewall rule.
    """
    node_id = request.POST.get('node_id')
    replica_ip = (request.POST.get('replica_ip') or request.POST.get('host', '')).strip()
    name = (request.POST.get('name') or request.POST.get('label', '')).strip()
    repl_user = (request.POST.get('repl_user') or request.POST.get('user', 'olspanel_repl')).strip()
    repl_pass = (request.POST.get('repl_password') or request.POST.get('password', '')).strip()
    sync_scope = request.POST.get('sync_scope', 'selected').strip()
    replicate_all = (sync_scope == 'all' or request.POST.get('replicate_all') in ['true', '1', True])

    if not replica_ip:
        return JsonResponse({'status': 'error', 'message': 'Replica IP address is required.'})

    if not name:
        name = f"Replica Server ({replica_ip})"

    # Parse assigned databases
    dbs_raw = request.POST.get('selected_databases', '')
    selected_dbs = []
    if dbs_raw:
        try:
            selected_dbs = json.loads(dbs_raw) if dbs_raw.startswith('[') else [d.strip() for d in dbs_raw.split(',') if d.strip()]
        except Exception:
            selected_dbs = [d.strip() for d in dbs_raw.split(',') if d.strip()]
    else:
        post_list = request.POST.getlist('selected_databases[]') or request.POST.getlist('selected_databases')
        if post_list:
            selected_dbs = post_list

    # 1. Ensure replication binary logging is on
    ensure_replication_config(is_primary=True)

    # 2. Allow Firewall port 3306 for this IP
    allow_firewall_for_ip(replica_ip)

    # 3. Create or update MySQL replication user
    success, res = create_replication_user(replica_ip, username=repl_user, password=repl_pass or None)
    if not success:
        return JsonResponse({'status': 'error', 'message': f'Failed to configure replication user: {res}'})

    # 4. Save to DbClusterNode
    if node_id and str(node_id).isdigit():
        node = DbClusterNode.objects.filter(id=node_id, is_local=False).first()
        if node:
            # If IP changed, remove old firewall rule & user
            if node.host != replica_ip:
                remove_firewall_for_ip(node.host)
                drop_replication_user(node.host, node.repl_user)

            node.name = name
            node.host = replica_ip
            node.repl_user = res['user']
            node.repl_password = res['password']
            node.selected_databases = json.dumps(selected_dbs)
            node.replicate_all = replicate_all
            node.save()
        else:
            node = DbClusterNode.objects.create(
                name=name,
                node_role='replica',
                channel_name='default',
                host=replica_ip,
                mysql_port=3306,
                repl_user=res['user'],
                repl_password=res['password'],
                selected_databases=json.dumps(selected_dbs),
                replicate_all=replicate_all,
                status='active',
                is_local=False,
                last_sync=timezone.now()
            )
    else:
        node, _ = DbClusterNode.objects.update_or_create(
            host=replica_ip,
            defaults={
                'name': name,
                'node_role': 'replica',
                'channel_name': 'default',
                'mysql_port': 3306,
                'repl_user': res['user'],
                'repl_password': res['password'],
                'selected_databases': json.dumps(selected_dbs),
                'replicate_all': replicate_all,
                'status': 'active',
                'is_local': False,
                'last_sync': timezone.now()
            }
        )

    # 5. Update DbSyncRule records
    DbSyncRule.objects.filter(node=node).delete()
    for db_name in selected_dbs:
        DbSyncRule.objects.create(
            node=node,
            database_name=db_name,
            is_active=True,
            status='active'
        )

    DbReplicationLog.objects.create(
        node=node,
        event_type='pair',
        message=f"Replica Client `{name}` ({replica_ip}) saved with {len(selected_dbs)} assigned database(s)."
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Replica IP {replica_ip} authorized and configured with {len(selected_dbs)} database(s).",
        'node_id': node.id,
        'credentials': res
    })


@csrf_exempt
@require_POST
def db_replication_delete_replica_client(request):
    """Revokes an Authorized Replica Client IP, closes firewall rule, and drops MySQL user."""
    node_id = request.POST.get('node_id')
    replica_ip = request.POST.get('replica_ip', '').strip()

    node = None
    if node_id and str(node_id).isdigit():
        node = DbClusterNode.objects.filter(id=node_id, is_local=False).first()
    elif replica_ip:
        node = DbClusterNode.objects.filter(host=replica_ip, is_local=False).first()

    if not node:
        return JsonResponse({'status': 'error', 'message': 'Replica client node not found.'})

    host_ip = node.host
    node_name = node.name
    repl_user = node.repl_user

    # Remove firewall & user
    remove_firewall_for_ip(host_ip)
    drop_replication_user(host_ip, repl_user)
    
    DbSyncRule.objects.filter(node=node).delete()
    node.delete()

    DbReplicationLog.objects.create(
        event_type='delete',
        message=f"Replica Client `{node_name}` ({host_ip}) revoked and removed."
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Replica client {host_ip} revoked and firewall access closed."
    })


@require_GET
def db_replication_get_node_details(request, node_id):
    """Fetches full configuration details for a cluster node to pre-fill edit modals."""
    try:
        node = DbClusterNode.objects.get(id=node_id)
        try:
            dbs = json.loads(node.selected_databases or '[]')
        except Exception:
            dbs = [d.strip() for d in str(node.selected_databases).split(',') if d.strip()]

        try:
            rewrite = json.loads(node.rewrite_rules or '{}')
        except Exception:
            rewrite = {}

        return JsonResponse({
            'status': 'success',
            'node': {
                'id': node.id,
                'name': node.name,
                'host': node.host,
                'node_role': node.node_role,
                'channel_name': node.channel_name,
                'mysql_port': node.mysql_port,
                'repl_user': node.repl_user,
                'repl_password': node.repl_password,
                'replicate_all': node.replicate_all,
                'selected_databases': dbs,
                'rewrite_rules': rewrite,
                'status': node.status,
                'is_local': node.is_local
            }
        })
    except DbClusterNode.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Node not found.'}, status=404)


@csrf_exempt
@require_POST
def db_replication_assign_db_replicas(request):
    """
    Directly assigns or unassigns Allowed Replica Client IPs for a specific Primary database,
    and supports inline authorizing single or multiple brand new Replica IPs in the same step.
    """
    db_name = request.POST.get('database_name', '').strip()
    node_ids_raw = request.POST.get('replica_node_ids', '[]')
    new_ip_raw = request.POST.get('new_replica_ip', '').strip()
    new_name = request.POST.get('new_replica_name', '').strip()
    new_user = request.POST.get('new_repl_user', 'olspanel_repl').strip() or 'olspanel_repl'
    new_pass = request.POST.get('new_repl_password', '').strip()

    if not db_name:
        return JsonResponse({'status': 'error', 'message': 'Database name is required.'})

    try:
        node_ids = json.loads(node_ids_raw) if node_ids_raw.startswith('[') else [n.strip() for n in node_ids_raw.split(',') if n.strip()]
    except Exception:
        node_ids = request.POST.getlist('replica_node_ids[]') or request.POST.getlist('replica_node_ids')

    node_ids = [int(nid) for nid in node_ids if str(nid).isdigit()]

    # If new IP(s) are being authorized inline right from this modal:
    created_nodes_info = []
    if new_ip_raw:
        ensure_replication_config(is_primary=True)
        # Parse potential comma/space/semicolon separated list of IPs
        raw_ips = [ip.strip() for ip in re.split(r'[,;\s]+', new_ip_raw) if ip.strip()]
        for ip in raw_ips:
            allow_firewall_for_ip(ip)
            success, res = create_replication_user(ip, username=new_user, password=new_pass or None)
            if not success:
                return JsonResponse({'status': 'error', 'message': f'Failed to configure replication user for {ip}: {res}'})
            
            node_label = new_name if len(raw_ips) == 1 and new_name else f"Replica Server ({ip})"
            node, _ = DbClusterNode.objects.update_or_create(
                host=ip,
                defaults={
                    'name': node_label,
                    'node_role': 'replica',
                    'channel_name': 'default',
                    'mysql_port': 3306,
                    'repl_user': res['user'],
                    'repl_password': res['password'],
                    'selected_databases': json.dumps([db_name]),
                    'replicate_all': False,
                    'status': 'active',
                    'is_local': False,
                    'last_sync': timezone.now()
                }
            )
            if node.id not in node_ids:
                node_ids.append(node.id)

            created_nodes_info.append({
                'id': node.id,
                'host': ip,
                'name': node_label,
                'user': res['user'],
                'password': res['password'],
                'port': 3306
            })

            DbReplicationLog.objects.create(
                node=node,
                event_type='pair',
                message=f"Replica Client `{node_label}` ({ip}) authorized & assigned to database `{db_name}`."
            )

    # Sync assignments across all nodes
    success, msg = assign_database_to_replicas(db_name, node_ids)
    if success:
        out_msg = f"Replication settings for database `{db_name}` saved successfully."
        if created_nodes_info:
            out_msg += f" {len(created_nodes_info)} replica server(s) authorized & UFW firewall opened."
        return JsonResponse({
            'status': 'success',
            'message': out_msg,
            'database_name': db_name,
            'created_nodes': created_nodes_info
        })
    return JsonResponse({'status': 'error', 'message': msg})


@csrf_exempt
@require_POST
def db_replication_edit_inbound_channel(request):
    """
    Edits an existing Inbound Multi-Source Replication Channel
    (updates Primary Server IP, port, credentials, channel name, databases filter).
    """
    node_id = request.POST.get('node_id')
    old_channel = request.POST.get('old_channel_name', '').strip()
    channel_name = request.POST.get('channel_name', '').strip() or old_channel or 'default'
    primary_host = request.POST.get('primary_host', '').strip()
    primary_port = int(request.POST.get('primary_port', 3306) or 3306)
    repl_user = request.POST.get('repl_user', 'olspanel_repl').strip()
    repl_pass = request.POST.get('repl_password', '').strip()
    sync_scope = request.POST.get('sync_scope', 'selected').strip()
    replicate_all = (sync_scope == 'all')

    if not primary_host or not repl_user or not repl_pass:
        return JsonResponse({'status': 'error', 'message': 'Primary host, username, and password are required.'})

    # Parse databases
    dbs_raw = request.POST.get('selected_databases', '')
    selected_dbs = []
    rewrite_rules = {}
    if dbs_raw:
        try:
            parsed = json.loads(dbs_raw) if dbs_raw.startswith('[') else [d.strip() for d in dbs_raw.split(',') if d.strip()]
            for item in parsed:
                if isinstance(item, str) and ("->" in item or ":" in item):
                    delim = "->" if "->" in item else ":"
                    src, tgt = item.split(delim, 1)
                    src, tgt = src.strip(), tgt.strip()
                    rewrite_rules[src] = tgt
                    selected_dbs.append(tgt)
                else:
                    selected_dbs.append(str(item).strip())
        except Exception:
            pass

    # If channel name changed, stop and reset old channel
    if old_channel and old_channel != channel_name:
        reset_replica_channel(old_channel)

    # Reconfigure MySQL channel
    success, msg = start_replica_channel(
        channel_name=channel_name,
        master_host=primary_host,
        master_port=primary_port,
        repl_user=repl_user,
        repl_password=repl_pass,
        use_gtid=True
    )

    if not success:
        return JsonResponse({'status': 'error', 'message': f'Failed to update channel: {msg}'})

    # Update or create node record
    node = None
    if node_id and str(node_id).isdigit():
        node = DbClusterNode.objects.filter(id=node_id).first()

    if not node:
        node = DbClusterNode.objects.filter(channel_name=channel_name, node_role='primary').first()

    if node:
        node.name = f"Primary Source ({primary_host})"
        node.host = primary_host
        node.mysql_port = primary_port
        node.repl_user = repl_user
        node.repl_password = repl_pass
        node.channel_name = channel_name
        node.selected_databases = json.dumps(selected_dbs)
        node.rewrite_rules = json.dumps(rewrite_rules)
        node.replicate_all = replicate_all
        node.status = 'active'
        node.save()
    else:
        node = DbClusterNode.objects.create(
            name=f"Primary Source ({primary_host})",
            node_role='primary',
            channel_name=channel_name,
            host=primary_host,
            mysql_port=primary_port,
            repl_user=repl_user,
            repl_password=repl_pass,
            selected_databases=json.dumps(selected_dbs),
            rewrite_rules=json.dumps(rewrite_rules),
            replicate_all=replicate_all,
            status='active',
            is_local=False
        )

    DbReplicationLog.objects.create(
        node=node,
        event_type='sync',
        message=f"Inbound stream channel `{channel_name}` updated to Primary {primary_host}:{primary_port}"
    )

    return JsonResponse({
        'status': 'success',
        'message': f"Inbound replication stream `{channel_name}` updated and connected.",
        'channel_name': channel_name
    })


@csrf_exempt
@require_POST
def db_replication_create_user_view(request):
    """Creates a replication user and opens firewall for a replica IP (legacy endpoint compatibility)."""
    return db_replication_save_replica_client(request)


@csrf_exempt
@require_POST
def db_replication_action(request):
    """Handles general cluster actions: promote, delete."""
    action = request.POST.get('action', '').strip()
    node_id = request.POST.get('node_id')

    if action == 'promote':
        success, msg = promote_replica_to_primary()
        if success:
            return JsonResponse({'status': 'success', 'message': msg})
        return JsonResponse({'status': 'error', 'message': msg})

    elif action == 'delete' and node_id:
        try:
            node = DbClusterNode.objects.get(id=node_id, is_local=False)
            remove_firewall_for_ip(node.host)
            drop_replication_user(node.host, node.repl_user)
            node_host = node.host
            node.delete()
            DbReplicationLog.objects.create(event_type='delete', message=f"Cluster node {node_host} removed.")
            return JsonResponse({'status': 'success', 'message': f"Node {node_host} disconnected and removed."})
        except DbClusterNode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Node not found or cannot delete local node.'})

    return JsonResponse({'status': 'error', 'message': f'Unknown or unsupported action: {action}'})

