from django.core.management.base import BaseCommand
from slurper import source_lmfdb


class Command(BaseCommand):
    def handle(self, *args, **options):
        source_lmfdb.LMFDB_SLURPER.save_items()
