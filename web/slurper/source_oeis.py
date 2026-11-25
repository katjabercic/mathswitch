"""
Slurper for the On-Line Encyclopedia of Integer Sequences (OEIS).

Sequence names are fetched from the OEIS names.gz dump and from searches like
https://oeis.org/search?q=keyword%3Acore&fmt=json&sort=number&start=100.
From start= 0 to 100. Each request gives you 10 items, so we increase by 10.
110 does not work for anonymus users. To get around it we sort first by
sort=numbers and then sort=-umbers. This way we can get all 183 core items

OEIS content is licensed under CC-BY-SA-4.0 by The On-Line Encyclopedia
of Integer Sequences, https://oeis.org/.
"""

import gzip
import logging
import time
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Iterator, Optional

import requests
from concepts.models import Item, Link
from slurper.models import SlurperRun

from web.settings import MATHSWITCH_CONTACT_EMAIL


class OeisSlurper:
    NAMES_URL = "https://oeis.org/names.gz"
    SEARCH_URL = "https://oeis.org/search"
    SEQUENCE_URL_PREFIX = "https://oeis.org/"
    ANONYMOUS_SEARCH_RESULT_LIMIT = 100
    SECONDS_BETWEEN_SEARCH_REQUESTS = 0.5
    MAX_NAME_LENGTH = 100
    MIN_INTERVAL = timedelta(days=7)
    PROGRESS_REPORT_EVERY = 5_000

    def __init__(self):
        self.source = Item.Source.OEIS

    # Downloading

    def _get(self, url: str, params: Optional[dict] = None) -> requests.Response:
        headers = {"User-Agent": f"MathSwitch/1.0 ({MATHSWITCH_CONTACT_EMAIL})"}
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response

    def fetch_names(self) -> bytes:
        return gzip.decompress(self._get(self.NAMES_URL).content)

    def fetch_core_ids(self) -> set[str]:
        # Curently anonymus useres get a 100 items result limit.
        # There are curently (25.11.2026) 183 sequences with core keyword,
        # we get the first 100 and the last 100. TAlternative is to parse thru
        # oesisdata repository at https://github.com/oeis/oeisdata/tree/main.
        lowest_numbered = self._search_sequences("keyword:core", sort="number")
        highest_numbered = self._search_sequences("keyword:core", sort="-number")
        if self._search_missed_middle_results(lowest_numbered, highest_numbered):
            logging.warning(
                f"[{self.source.label}] more than "
                f"{2 * self.ANONYMOUS_SEARCH_RESULT_LIMIT} core sequences; "
                "some are missing."
            )
        return {
            self._a_number(sequence)
            for sequence in lowest_numbered + highest_numbered
            if self._has_keyword(sequence, "core")
        }

    def _search_sequences(self, query: str, sort: str) -> list[dict]:
        sequences = []
        while len(sequences) < self.ANONYMOUS_SEARCH_RESULT_LIMIT:
            page = self._get(
                self.SEARCH_URL,
                params={
                    "q": query,
                    "fmt": "json",
                    "sort": sort,
                    "start": len(sequences),
                },
            ).json()
            if not page:
                break
            sequences.extend(page)
            time.sleep(self.SECONDS_BETWEEN_SEARCH_REQUESTS)
        return sequences

    def _search_missed_middle_results(
        self, lowest_numbered: list[dict], highest_numbered: list[dict]
    ) -> bool:
        both_hit_limit = (
            len(lowest_numbered) >= self.ANONYMOUS_SEARCH_RESULT_LIMIT
            and len(highest_numbered) >= self.ANONYMOUS_SEARCH_RESULT_LIMIT
        )
        lowest_numbers = {sequence["number"] for sequence in lowest_numbered}
        highest_numbers = {sequence["number"] for sequence in highest_numbered}
        return both_hit_limit and lowest_numbers.isdisjoint(highest_numbers)

    def _a_number(self, sequence: dict) -> str:
        return f"A{int(sequence['number']):06d}"

    def _has_keyword(self, sequence: dict, keyword: str) -> bool:
        return keyword in (sequence.get("keyword") or "").split(",")

    # Parsing names.gz

    def parse_names(self, raw: bytes) -> Iterator[tuple[str, str]]:
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if not line or line.startswith("#"):
                continue
            identifier, _, description = line.partition(" ")
            description = description.strip()
            if identifier and description:
                yield identifier, description

    def name_before_colon(self, description: str) -> Optional[str]:
        if ":" not in description:
            return None
        return description.split(":", 1)[0].strip() or None

    def choose_name(self, description: str, is_core: bool) -> Optional[str]:
        name = self.name_before_colon(description)
        if name is None and is_core:
            name = description.rstrip(".").strip() or None
        return name[: self.MAX_NAME_LENGTH] if name else None

    def build_item(
        self, identifier: str, description: str, is_core: bool = False
    ) -> Item:
        return Item(
            source=self.source,
            identifier=identifier,
            url=self.SEQUENCE_URL_PREFIX + identifier,
            name=self.choose_name(description, is_core) or identifier,
            description=description,
        )

    # Saving

    def save_items(self, force: bool = False):
        if not force and not SlurperRun.can_run(self.source, self.MIN_INTERVAL):
            logging.info(
                f"[{self.source.label}] skipped: ran less than "
                f"{self.MIN_INTERVAL.days} days ago (use --force to override)."
            )
            return

        logging.info(f"[{self.source.label}] downloading core sequence IDs...")
        core_ids = self.fetch_core_ids()
        logging.info(f"[{self.source.label}] downloading names.gz...")
        sequences = list(self.parse_names(self.fetch_names()))

        existing_items = self._load_existing_items()
        other_items_by_name = self._load_other_sources_items_by_name()

        counts = Counter()
        for _, (identifier, description) in enumerate(sequences, start=1):
            is_core = identifier in core_ids
            existing_item = existing_items.get(identifier)
            if existing_item:
                self._update_item(existing_item, description, is_core)
                counts["updated"] += 1
                continue

            same_name_items = self._items_named(
                other_items_by_name, self.name_before_colon(description)
            )
            if is_core or same_name_items:
                new_item = self.build_item(identifier, description, is_core)
                new_item.save()
                self._link_same_name(new_item, same_name_items)
                counts["new core"] += is_core
                counts["links"] += len(same_name_items)

        SlurperRun.mark_ran(self.source)
        logging.info(
            f"[{self.source.label}] save_items finished: "
            f"{counts['updated']} existing items updated, "
            f"{counts['new core']} new core sequences, "
            f"{counts['links']} NAME_EQ links created."
        )

    def _load_existing_items(self) -> dict[str, Item]:
        return {
            item.identifier: item for item in Item.objects.filter(source=self.source)
        }

    def _load_other_sources_items_by_name(self) -> dict[str, list[Item]]:
        items_by_name = defaultdict(list)
        other_items = (
            Item.objects.exclude(source=self.source)
            .exclude(name=None)
            .only("id", "source", "identifier", "name")
        )
        for item in other_items:
            items_by_name[item.name.casefold()].append(item)
        return items_by_name

    def _items_named(
        self, items_by_name: dict[str, list[Item]], name: Optional[str]
    ) -> list[Item]:
        if name is None:
            return []
        return items_by_name.get(name.casefold(), [])

    def _update_item(self, item: Item, description: str, is_core: bool):
        item.name = self.choose_name(description, is_core) or item.name
        item.description = description
        item.save(update_fields=["name", "description"])

    def _link_same_name(self, item: Item, same_name_items: list[Item]):
        for other_item in same_name_items:
            Link.save_new(item, other_item, Link.Label.NAME_EQ)


OEIS_SLURPER = OeisSlurper()
