from django.core.management.base import BaseCommand
from slurper import source_wikidata


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("", end="")
        n = len(source_wikidata.SLURPERS)
        for i, slurper in enumerate(source_wikidata.SLURPERS):
            print(f"\r  query {i}/{n}: {slurper.source.label}".ljust(50), end="")
            slurper.save_items()
        for i, slurper in enumerate(source_wikidata.SLURPERS):
            print(f"\r  links {i}/{n}: {slurper.source.label}".ljust(50), end="")
            slurper.save_links()
        print("\r  done.".ljust(60))
