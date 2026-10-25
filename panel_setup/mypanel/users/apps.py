from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        import users.signals  # noqa
        import threading
        import sys
        import os

        # Don't run background threads during manage.py commands like migrate, makemigrations, collectstatic
        cmd_args = " ".join(sys.argv)
        if any(cmd in cmd_args for cmd in ['makemigrations', 'migrate', 'collectstatic', 'createsuperuser']):
            return

        def _ensure_package_schema():
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES LIKE 'packages'")
                    if cursor.fetchone():
                        cursor.execute("SHOW COLUMNS FROM packages LIKE 'postgresql_databases'")
                        if not cursor.fetchone():
                            cursor.execute("ALTER TABLE packages ADD COLUMN postgresql_databases INT(11) DEFAULT 0")
            except Exception:
                pass

        _ensure_package_schema()

        def _startup_repair():
            import time
            time.sleep(3)
            try:
                from users.server_core import repair_all_vhosts_and_contexts
                repair_all_vhosts_and_contexts()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Startup vhost repair failed: %s", e)

        t = threading.Thread(target=_startup_repair, daemon=True)
        t.start()
