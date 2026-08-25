import logging
from typing import Optional

import requests
from concepts.models import Item
from django.db.utils import IntegrityError
from django.utils.html import strip_tags
from slurper.models import SlurperRun


class HoGSlurper:
    JSON_URL = "https://houseofgraphs.org/api/invariants"
    INVARIANT_URL_PREFIX = "https://houseofgraphs.org/invariants/"

    def __init__(self):
        self.source = Item.Source.HOUSE_OF_GRAPHS

    def fetch_invariant_model_list(self):
        response = requests.get(self.JSON_URL)
        response.raise_for_status()
        return response.json()["_embedded"]["invariantModelList"]

    def invariant_to_item(self, invariant) -> Optional[Item]:
        try:
            identifier = str(invariant["invariantId"])
            return Item(
                source=self.source,
                identifier=identifier,
                url=self.INVARIANT_URL_PREFIX + identifier,
                name=invariant["invariantName"],
                description=strip_tags(invariant["definition"]),
            )
        except KeyError as missing_field:
            logging.warning(
                f"[{self.source.label}] skipped invariant "
                f"{invariant.get('invariantId', '<no id>')}: "
                f"missing field {missing_field}."
            )
            return None

    def save_items(self):
        total_saved = 0
        for invariant_model in self.fetch_invariant_model_list():
            item = self.invariant_to_item(invariant_model["entity"])
            if item is None:
                continue
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


HOG_SLURPER = HoGSlurper()
