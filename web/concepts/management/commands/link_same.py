from concepts.models import Item, Link
from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("link same")
        for name_count in (
            Item.objects.all()
            .values("name")
            .annotate(total=Count("name"))
            .filter(total__gte=2)
        ):
            items = Item.objects.filter(name=name_count["name"])
            for i in range(len(items) - 1):
                for j in range(i + 1, len(items)):
                    Link.save_new(items[i], items[j], Link.Label.NAME_EQ)
