import gzip
import logging
from datetime import timedelta
from typing import Iterator, Tuple

import requests
from concepts.models import Item
from django.db.utils import IntegrityError
from slurper.models import SlurperRun


class OeisSlurper:
    NAMES_URL = "https://oeis.org/names.gz"
    SEQUENCE_URL_PREFIX = "https://oeis.org/"
    MIN_INTERVAL = timedelta(days=7)

    def __init__(self):
        self.source = Item.Source.OEIS

    def fetch_names(self) -> bytes:
        response = requests.get(self.NAMES_URL)
        response.raise_for_status()
        return gzip.decompress(response.content)

    def parse_names(self, raw: bytes) -> Iterator[Tuple[str, str]]:
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if not line or line.startswith("#"):
                continue
            identifier, _, description = line.partition(" ")
            description = description.strip()
            if not identifier or not description:
                continue
            yield identifier, description

    def line_to_item(self, identifier: str, description: str) -> Item:
        return Item(
            source=self.source,
            identifier=identifier,
            url=self.SEQUENCE_URL_PREFIX + identifier,
            name=identifier,
            description=description,
        )

    def save_items(self, force: bool = False):
        if not force and not SlurperRun.can_run(self.source, self.MIN_INTERVAL):
            logging.info(
                f"[{self.source.label}] skipped: ran less than "
                f"{self.MIN_INTERVAL.days} days ago (use --force to override)."
            )
            return
        total_saved = 0
        for identifier, description in self.parse_names(self.fetch_names()):
            item = self.line_to_item(identifier, description)
            try:
                item.save()
                total_saved += 1
            except IntegrityError:
                logging.info(
                    f"Item {item.source} {item.identifier} is already in the database."
                )
        SlurperRun.mark_ran(self.source)
        logging.info(
            f"[{self.source.label}] save_items finished: {total_saved} items saved."
        )


OEIS_SLURPER = OeisSlurper()
