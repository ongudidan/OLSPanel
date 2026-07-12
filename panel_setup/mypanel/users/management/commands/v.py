from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Displays the current  version"

    def handle(self, *args, **kwargs):
        self.stdout.write(f"OLS Panel version: {settings.VERSION}")
