from django.core.management.base import BaseCommand
from slurper import source_wikidata


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("importing wikidata data")
        source_wikidata.WD_SLURPER.save_items()
        source_wikidata.WD_NLAB_SLURPER.save_items()
        source_wikidata.WD_MATHWORLD_SLURPER.save_items()
        source_wikidata.WD_SLURPER.save_links()
        source_wikidata.WD_NLAB_SLURPER.save_links()
        source_wikidata.WD_MATHWORLD_SLURPER.save_links()
