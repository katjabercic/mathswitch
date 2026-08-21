from django.core.management.base import BaseCommand
from slurper import source_house_of_graphs

class Command(BaseCommand):
    def handle(self, *args, **options):
        source_house_of_graphs.HOG_SLURPER.save_items()