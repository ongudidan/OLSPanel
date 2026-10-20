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
