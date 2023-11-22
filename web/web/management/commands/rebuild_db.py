from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        call_command("clear_agda_unimath")
        call_command("clear_wikidata")
        call_command("import_wikidata")
        call_command("import_agda_unimath")
        call_command("link_same")
        call_command("compute_concepts")
