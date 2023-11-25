from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("clearing data: agda-unimath")
        call_command("clear_agda_unimath")
        print("clearing data: Wikidata")
        call_command("clear_wikidata")
        print("clearing data: concepts")
        call_command("clear_concepts")
        call_command("migrate")
        print("importing data: Wikidata")
        call_command("import_wikidata")
        print("importing data: agda-unimath")
        call_command("import_agda_unimath")
        print("linking: items with the same name")
        call_command("link_same")
        print("computing concepts")
        call_command("compute_concepts")
