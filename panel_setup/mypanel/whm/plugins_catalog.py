"""
OLSPanel Official Plugin Catalog Definition
Defines the local, self-hosted marketplace plugins and categories.
Eliminates all runtime external dependencies on upstream servers.
"""

DEFAULT_CATEGORIES = [
    {"id": 1, "name": "Database", "slug": "database"},
    {"id": 2, "name": "Terminal", "slug": "terminal"},
    {"id": 3, "name": "Migration & Backup", "slug": "migration-backup"},
    {"id": 4, "name": "Development", "slug": "development"},
    {"id": 5, "name": "Security", "slug": "security"},
    {"id": 6, "name": "OpenLiteSpeed", "slug": "openlitespeed"},
]

DEFAULT_PLUGINS = [
    {
        "id": 2,
        "slug": "postgresql",
        "category_id": 1,
        "category": "Database",
        "name": "PostgreSQL",
        "description": "PostgreSQL relational database server and phpPgAdmin management interface.",
        "path": "plugin/postgresql.conf",
        "url": "https://github.com/ongudidan/olspanel-plugin-postgresql/releases/latest/download/postgresql.zip",
        "type": "free",
        "date": "2025-03-19",
        "pre_build_path": "",
        "image": "/media/icon/postgresql.svg",
    },
    {
        "id": 1,
        "slug": "mongodb",
        "category_id": 1,
        "category": "Database",
        "name": "MongoDB",
        "description": "MongoDB document-oriented database server and phpMyMongo management interface.",
        "path": "/usr/bin/mongosh",
        "url": "https://ongudidan.github.io/OLSPanel/extra/install_mongodb.sh",
        "type": "free",
        "date": "2025-02-05",
        "pre_build_path": "phpmymongos/",
        "image": "/media/icon/mongodb.svg",
    },
    {
        "id": 4,
        "slug": "terminal",
        "category_id": 2,
        "category": "Terminal",
        "name": "SSH Web Terminal",
        "description": "Interactive in-browser bash/ssh terminal streaming console output directly in OLSPanel.",
        "path": "plugin/terminal.conf",
        "url": "https://github.com/ongudidan/olspanel-plugin-terminal/releases/latest/download/terminal.zip",
        "type": "free",
        "date": "2026-02-02",
        "pre_build_path": "",
        "image": "/media/icon/terminal.svg",
    },
    {
        "id": 7,
        "slug": "replicator",
        "category_id": 3,
        "category": "Migration & Backup",
        "name": "Server Replicator",
        "description": "Duplicate or migrate websites, users, SSL certificates, and databases between OLSPanel servers over SSH.",
        "path": "plugin/replicator.conf",
        "url": "https://github.com/ongudidan/olspanel-plugin-replicator/releases/latest/download/replicator.zip",
        "type": "free",
        "date": "2026-04-10",
        "pre_build_path": "",
        "image": "/media/icon/replicator.svg",
    },
    {
        "id": 8,
        "slug": "git_deploy",
        "category_id": 4,
        "category": "Development",
        "name": "Git Auto Deploy",
        "description": "Automated Git repository synchronization, webhook triggers, and automated branch deployment.",
        "path": "plugin/git_deploy.conf",
        "url": "https://github.com/ongudidan/olspanel-plugin-git-deploy/releases/latest/download/git_deploy.zip",
        "type": "free",
        "date": "2026-05-01",
        "pre_build_path": "",
        "image": "/media/icon/git_deploy.svg",
    },
    {
        "id": 9,
        "slug": "pm2",
        "category_id": 4,
        "category": "Development",
        "name": "Node.js PM2 Manager",
        "description": "Production process management, port mapping, proxy contexts, environment variables, and log streamer for Node.js apps.",
        "path": "plugin/pm2.conf",
        "url": "https://github.com/ongudidan/olspanel-plugin-pm2/releases/latest/download/pm2.zip",
        "type": "free",
        "date": "2026-05-15",
        "pre_build_path": "",
        "image": "/media/icon/pm2.svg",
    },
    {
        "id": 3,
        "slug": "imunifyav",
        "category_id": 5,
        "category": "Security",
        "name": "ImunifyAV (Antivirus)",
        "description": "Antivirus scanner and malware detection for web hosting environments.",
        "path": "/usr/bin/imunify-antivirus",
        "url": "https://ongudidan.github.io/OLSPanel/extra/imunifyfav.sh",
        "type": "free",
        "date": "2025-11-11",
        "pre_build_path": "imunifyfav_whm/",
        "image": "/media/icon/imunifyfav.png",
    },
    {
        "id": 5,
        "slug": "htaccess_compat",
        "category_id": 6,
        "category": "OpenLiteSpeed",
        "name": ".htaccess Module",
        "description": "Apache .htaccess rewrite rules compatibility module for OpenLiteSpeed.",
        "path": "modules/htaccess_compat/",
        "url": "https://ongudidan.github.io/OLSPanel/extra/module_installer/install_modules_htaccess_compat.sh",
        "type": "free",
        "date": "2026-08-25",
        "pre_build_path": "",
        "image": "/media/icon/extension.svg",
    },
    {
        "id": 6,
        "slug": "lscache_owner",
        "category_id": 6,
        "category": "OpenLiteSpeed",
        "name": "LSCache Owner",
        "description": "Permissions and file ownership manager for OpenLiteSpeed cache.",
        "path": "modules/lscache_owner/",
        "url": "https://ongudidan.github.io/OLSPanel/extra/module_installer/lscache_owner_module_installer.sh",
        "type": "free",
        "date": "2026-08-25",
        "pre_build_path": "",
        "image": "/media/icon/extension.svg",
    },
]

def get_plugins_catalog():
    """Return a deep copy of all registered plugins."""
    import copy
    return copy.deepcopy(DEFAULT_PLUGINS)

def get_plugin_by_id(plugin_id):
    """Find plugin by numeric id, slug, or name."""
    if plugin_id is None:
        return None
    target = str(plugin_id).strip().lower()
    for p in DEFAULT_PLUGINS:
        if str(p.get("id")) == target:
            import copy
            return copy.deepcopy(p)
        if str(p.get("slug", "")).lower() == target:
            import copy
            return copy.deepcopy(p)
        if str(p.get("name", "")).lower() == target:
            import copy
            return copy.deepcopy(p)
    return None

def get_categories_catalog():
    """Return categories list with accurate plugin counts."""
    import copy
    cats = copy.deepcopy(DEFAULT_CATEGORIES)
    plugins = DEFAULT_PLUGINS
    for cat in cats:
        count = sum(1 for p in plugins if p.get("category_id") == cat.get("id"))
        cat["plugin_count"] = count
    return cats
