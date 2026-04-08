import logging
import time

from categorizer.wikidata_fetch_service import WikidataFetchService
from concepts.models import Item
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch missing Wikidata metadata for items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of items to fetch metadata for",
        )
        parser.add_argument(
            "--domain",
            type=str,
            default=None,
            choices=Item.Domain.values,
            help="Filter by domain: math or phys (default: all)",
        )
        parser.add_argument(
            "--no-mathworld-id",
            action="store_true",
            default=False,
            help="Count Wikidata items that have metadata but no MathWorld ID",
        )

    def _base_queryset(self, domain):
        queryset = Item.objects.filter(source=Item.Source.WIKIDATA)
        if domain:
            queryset = queryset.filter(domain=domain)
        # Only items without metadata (null or empty)
        return queryset.filter(meta__isnull=True) | queryset.filter(meta="")

    def _has_meta_no_mathworld_queryset(self, domain):
        queryset = Item.objects.filter(source=Item.Source.WIKIDATA)
        if domain:
            queryset = queryset.filter(domain=domain)
        # Has meta (not null/empty) but does not contain mathworld_id key
        return (
            queryset.exclude(meta__isnull=True)
            .exclude(meta="")
            .exclude(meta__contains='"mathworld_id"')
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        domain = options.get("domain")
        no_mathworld_id = options.get("no_mathworld_id")

        if no_mathworld_id:
            count = self._has_meta_no_mathworld_queryset(domain).count()
            self.stdout.write(
                f"Wikidata items with metadata but no MathWorld ID: {count}"
            )
            return

        total = self._base_queryset(domain).count()

        if limit:
            total = min(total, limit)

        if total == 0:
            self.stdout.write("No items without metadata found.")
            return

        self.stdout.write(f"Fetching metadata for {total} Wikidata items...")
        if domain:
            self.stdout.write(f"Domain: {domain}")
        if limit:
            self.stdout.write(f"Limit: {limit}")

        service = WikidataFetchService()
        fetched = 0
        failed = 0
        processed = 0
        page_size = 100
        start = time.perf_counter()

        while processed < total:
            remaining = total - processed
            batch_size = min(page_size, remaining)
            items = list(self._base_queryset(domain)[:batch_size])
            if not items:
                break

            page_num = processed // page_size + 1
            logger.info(
                f"[fetch-metadata] page {page_num}: "
                f"loading {len(items)} items "
                f"({processed}/{total} processed so far)"
            )

            for item in items:
                processed += 1
                logger.info(
                    f"[fetch-metadata] ({processed}/{total}) "
                    f"fetching {item.identifier} ({item.name})"
                )
                try:
                    ok = service.fetch_and_store_meta(item)
                    if ok:
                        fetched += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(
                        f"[fetch-metadata] error fetching {item.identifier}: {e}"
                    )
                    failed += 1

        elapsed = time.perf_counter() - start
        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {elapsed:.1f}s: "
                f"{fetched} fetched, {failed} failed, {total} total"
            )
        )
