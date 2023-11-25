from concepts.models import Item
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("compute singletons")
        # all items that do not appear in an edge are components
        singletons = Item.objects.filter(
            incoming_items__isnull=True, outgoing_items__isnull=True
        )
        singletons.create_singleton_concepts()

        print("compute non-singletons")
        # now deal with those that do not have a concept yet
        nonsingletons = Item.objects.filter(
            Q(incoming_items__isnull=False) | Q(outgoing_items__isnull=False)
        ).distinct()
        nonsingletons.create_concepts()
