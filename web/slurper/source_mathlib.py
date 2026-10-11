"""
Slurper for Mathlib, the Lean 4 mathematical library.

Declarations are fetched from the JSON declaration index produced by doc-gen4
(served with a .bmp extension, but the content is plain JSON). Its structure is
defined by `JsonIndex` in doc-gen4's DocGen4/Output/ToJson.lean.
"""

import logging
from datetime import timedelta
from typing import Iterator, Tuple

import requests
from concepts.models import Item
from slurper.models import SlurperRun

from web.settings import MATHSWITCH_CONTACT_EMAIL


class MathlibSlurper:
    DOCS_URL = "https://leanprover-community.github.io/mathlib4_docs/"
    INDEX_URL = DOCS_URL + "declarations/declaration-data.bmp"
    MIN_INTERVAL = timedelta(days=7)
    BATCH_SIZE = 1000
    # The index also covers Lean core, Std, Batteries, Aesop, ...
    # Extend these to import more of it.
    INCLUDED_PACKAGES = frozenset({"Mathlib"})
    INCLUDED_KINDS = frozenset({"def", "structure", "class", "inductive"})

    def __init__(self, packages=None, kinds=None):
        self.source = Item.Source.MATHLIB
        self.packages = frozenset(packages or self.INCLUDED_PACKAGES)
        self.kinds = frozenset(kinds or self.INCLUDED_KINDS)

    def fetch_index(self) -> dict:
        headers = {"User-Agent": f"MathSwitch/1.0 ({MATHSWITCH_CONTACT_EMAIL})"}
        response = requests.get(self.INDEX_URL, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def package_of(info) -> str:
        # "./Mathlib/Data/Nat/Prime/Defs.html#Nat.Prime" -> "Mathlib"
        return info["docLink"].removeprefix("./").split("/", 1)[0].split(".", 1)[0]

    def is_included(self, name, info) -> bool:
        return self.package_of(info) in self.packages and info["kind"] in self.kinds

    def iter_declarations(self, index) -> Iterator[Tuple[str, dict]]:
        for name, info in index["declarations"].items():
            if self.is_included(name, info):
                yield name, info

    def declaration_to_item(self, name, info) -> Item:
        return Item(
            source=self.source,
            identifier=name,
            url=self.DOCS_URL + info["docLink"].removeprefix("./"),
            name=name,
            description=None,
            meta=info["kind"],
        )

    def save_items(self, force: bool = False):
        if not force and not SlurperRun.can_run(self.source, self.MIN_INTERVAL):
            logging.info(
                f"[{self.source.label}] skipped: ran less than "
                f"{self.MIN_INTERVAL.days} days ago (use --force to override)."
            )
            return
        before = Item.objects.filter(source=self.source).count()
        items = [
            self.declaration_to_item(name, info)
            for name, info in self.iter_declarations(self.fetch_index())
        ]
        Item.objects.bulk_create(
            items, batch_size=self.BATCH_SIZE, ignore_conflicts=True
        )
        total_saved = Item.objects.filter(source=self.source).count() - before
        SlurperRun.mark_ran(self.source)
        logging.info(
            f"[{self.source.label}] save_items finished: {total_saved} items saved."
        )


MATHLIB_SLURPER = MathlibSlurper()
