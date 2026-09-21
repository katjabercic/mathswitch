from django.core.management.base import BaseCommand
from slurper import source_oeis


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Bypass the 7-day throttle and run anyway.",
        )

    def handle(self, *args, force=False, **options):
        source_oeis.OEIS_SLURPER.save_items(force=force)
