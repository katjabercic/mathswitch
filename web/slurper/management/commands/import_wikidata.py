from django.core.management.base import BaseCommand
from slurper import source_wikidata


class Command(BaseCommand):
    def handle(self, *args, **options):
        source_wikidata.save_items(source_wikidata.MATH_QUERY)
