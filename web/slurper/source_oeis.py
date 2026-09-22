"""
Slurper for the On-Line Encyclopedia of Integer Sequences (OEIS).

Sequence names are fetched from the OEIS names.gz dump. OEIS content is
licensed under CC-BY-SA-4.0 by The On-Line Encyclopedia of Integer
Sequences, https://oeis.org/.
"""

import gzip
import logging
from datetime import timedelta
from typing import Iterator, Optional, Tuple

import requests
from concepts.models import Item, Link
from slurper.models import SlurperRun

from web.settings import WIKIPEDIA_CONTACT_EMAIL


class OeisSlurper:
    NAMES_URL = "https://oeis.org/names.gz"
    SEQUENCE_URL_PREFIX = "https://oeis.org/"
    MIN_INTERVAL = timedelta(days=7)

    def __init__(self):
        self.source = Item.Source.OEIS

    def fetch_names(self) -> bytes:
        headers = {"User-Agent": f"MathSwitch/1.0 ({WIKIPEDIA_CONTACT_EMAIL})"}
        response = requests.get(self.NAMES_URL, headers=headers)
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

    def extract_candidate_name(self, description: str) -> Optional[str]:
        if ":" not in description:
            return None
        candidate = description.split(":", 1)[0].strip()
        return candidate or None

    def save_items(self, force: bool = False):
        if not force and not SlurperRun.can_run(self.source, self.MIN_INTERVAL):
            logging.info(
                f"[{self.source.label}] skipped: ran less than "
                f"{self.MIN_INTERVAL.days} days ago (use --force to override)."
            )
            return
        total_filled = 0
        total_linked = 0
        for identifier, description in self.parse_names(self.fetch_names()):
            existing = Item.objects.filter(
                source=self.source, identifier=identifier
            ).first()
            if existing is not None:
                existing.description = description
                existing.save(update_fields=["description"])
                total_filled += 1
                continue

            candidate_name = self.extract_candidate_name(description)
            if candidate_name is None:
                continue
            matches = list(
                Item.objects.exclude(source=self.source).filter(
                    name__iexact=candidate_name
                )
            )
            if not matches:
                continue

            item = self.line_to_item(identifier, description)
            item.save()
            for match in matches:
                Link.save_new(item, match, Link.Label.NAME_EQ)
                total_linked += 1

        SlurperRun.mark_ran(self.source)
        logging.info(
            f"[{self.source.label}] save_items finished: "
            f"{total_filled} shells filled, {total_linked} NAME_EQ links created."
        )


OEIS_SLURPER = OeisSlurper()
