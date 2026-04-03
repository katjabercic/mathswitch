import logging

from django.core.management.base import BaseCommand
from slurper import source_wikidata


class Command(BaseCommand):
    def handle(self, *args, **options):
        n = len(source_wikidata.SLURPERS)
        for i, slurper in enumerate(source_wikidata.SLURPERS):
            logging.info(f"=== items {i+1}/{n}: {slurper.source.label} ===")
            slurper.save_items()
        for i, slurper in enumerate(source_wikidata.SLURPERS):
            logging.info(f"=== links {i+1}/{n}: {slurper.source.label} ===")
            slurper.save_links()
        logging.info("=== import_wikidata done. ===")
