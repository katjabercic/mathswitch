from concepts.models import Concept
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        Concept.objects.all().delete()
