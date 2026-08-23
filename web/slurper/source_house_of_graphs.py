import logging

import requests
from bs4 import BeautifulSoup
from concepts.models import Item
from django.db.utils import IntegrityError
from slurper.models import SlurperRun


class HoGSlurper:
    JSON_URL = "https://houseofgraphs.org/api/invariants"

    def __init__(self):
        self.source = Item.Source.HOUSE_OF_GRAPHS
        pass

    def fetch_invariant_model_list(self):
        with requests.get(f"{self.JSON_URL}") as response:
            if not response:
                print("No response")
            else:
                data = response.json()
                invariant_model_list = data["_embedded"]["invariantModelList"]
                return invariant_model_list

    def invariant_to_item(self, invar) -> Item:
        try:
            item = Item(
                source=self.source,
                identifier=str(invar["invariantId"]),
                url=f"https://houseofgraphs.org/invariants/api/{invar['invariantId']}",
                name=invar["invariantName"],
                description=BeautifulSoup(
                    invar["definition"], "html.parser"
                ).get_text(),
            )
            return item
        except KeyError as e:
            print(f"KeyError: {e} not in invar. {invar.get('invariantId', 'unknown')}.")
            return None

    def save_items(self):
        invariant_model_list = self.fetch_invariant_model_list()

        total_saved = 0
        for invariantModel in invariant_model_list:
            invariant = invariantModel["entity"]
            item = self.invariant_to_item(invariant)
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
