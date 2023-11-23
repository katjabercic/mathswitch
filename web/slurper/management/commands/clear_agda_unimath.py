from concepts.models import Item
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("clearing agda-unimath data")
        Item.objects.filter(source=Item.Source.AGDA_UNIMATH).delete()
