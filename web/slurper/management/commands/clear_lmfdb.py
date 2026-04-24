import logging
import sys
from datetime import timedelta

from concepts.models import Item
from django.core.management.base import BaseCommand
from slurper.models import SlurperRun

MIN_INTERVAL = timedelta(days=7)


class Command(BaseCommand):
    help = "Delete all LMFDB items. Guarded by a 7-day throttle; use --force to override."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Clear even if the LMFDB slurper ran within the last 7 days.",
        )

    def handle(self, *args, force=False, **options):
        source = Item.Source.LMFDB
        if not force and not SlurperRun.can_run(source, MIN_INTERVAL):
            if sys.stdin.isatty():
                answer = input(
                    f"LMFDB slurper ran within the last {MIN_INTERVAL.days} days. "
                    f"Clear anyway? [y/N] "
                ).strip().lower()
                if answer not in ("y", "yes"):
                    logging.info(f"[{source.label}] clear cancelled.")
                    return
            else:
                logging.info(
                    f"[{source.label}] clear skipped: ran less than "
                    f"{MIN_INTERVAL.days} days ago (use --force to override)."
                )
                return
        deleted, _ = Item.objects.filter(source=source).delete()
        logging.info(f"[{source.label}] cleared {deleted} items.")
