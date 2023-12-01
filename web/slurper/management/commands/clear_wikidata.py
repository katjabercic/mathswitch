from concepts.models import Item
from django.core.management.base import BaseCommand
from slurper.wd_raw_item import WD_OTHER_SOURCES


class Command(BaseCommand):
    def handle(self, *args, **options):
        Item.objects.filter(source=Item.Source.WIKIDATA).delete()
        Item.objects.filter(source=Item.Source.WIKIPEDIA_EN).delete()
        for source in WD_OTHER_SOURCES:
            Item.objects.filter(source=source).delete()
