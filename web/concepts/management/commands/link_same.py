from concepts.models import Item, Link
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower


class Command(BaseCommand):
    def handle(self, *args, **options):
        for name_group in (
            Item.objects.annotate(lname=Lower("name"))
            .values("lname")
            .annotate(total=Count("lname"))
            .filter(total__gte=2)
        ):
            items = Item.objects.filter(name__iexact=name_group["lname"])
            for i in range(len(items) - 1):
                for j in range(i + 1, len(items)):
                    Link.save_new(items[i], items[j], Link.Label.NAME_EQ)
