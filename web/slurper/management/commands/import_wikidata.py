from django.core.management.base import BaseCommand
from slurper import source_wikidata


class Command(BaseCommand):
    def handle(self, *args, **options):
        for slurper in source_wikidata.SLURPERS:
            slurper.save_items()
        for slurper in source_wikidata.SLURPERS:
            slurper.save_links()
