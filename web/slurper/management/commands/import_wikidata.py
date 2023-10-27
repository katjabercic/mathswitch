from django.core.management.base import BaseCommand
from slurper import wikidata


class Command(BaseCommand):

    def handle(self, *args, **options):
        wikidata.save_items(wikidata.MATH_QUERY)
