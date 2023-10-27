from django.core.management.base import BaseCommand
from concepts.models import Item

class Command(BaseCommand):

    def handle(self, *args, **options):
        Item.objects.filter(source=Item.Source.WIKIDATA).delete()
