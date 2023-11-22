import logging
from typing import Optional

import requests
from concepts.models import Item, Link
from django.db.utils import IntegrityError


class AgdaUnimathSlurper:
    JSON_URL = "https://unimath.github.io/agda-unimath/concept_index.json"
    # description at https://github.com/UniMath/agda-unimath/pull/884

    def __init__(self):
        self.source = Item.Source.AGDA_UNIMATH
        self.id_map = lambda item: item["id"]
        self.url_map = (
            lambda item: "https://unimath.github.io/agda-unimath/" + item["link"]
        )
        self.name_map = lambda item: item["name"]
        self.desc_map = lambda _: None
        self.raw_data = self.fetch_json()

    def fetch_json(self):
        response = requests.get(self.JSON_URL)
        return response.json()

    def json_to_item(self, item) -> Optional[Item]:
        return Item(
            source=self.source,
            identifier=self.id_map(item),
            url=self.url_map(item),
            name=self.name_map(item),
            description=self.desc_map(item),
        )

    def save_items(self):
        for json_item in self.raw_data:
            try:
                item = self.json_to_item(json_item)
                item.save()
                if "wikidata" in json_item:
                    wd_id = json_item["wikidata"]
                    try:
                        destinationItem = Item.objects.get(
                            source=Item.Source.WIKIDATA,
                            identifier=wd_id,
                        )
                        Link.save_new(item, destinationItem, Link.Label.AGDA_UNIMATH)
                    except Item.DoesNotExist:
                        logging.log(
                            logging.WARNING,
                            f"Item WD {wd_id} does not exist.",
                        )
                    except IntegrityError:
                        logging.log(
                            logging.WARNING,
                            f"Repeated link: AUm {item.identifier} -> WD {wd_id}.",
                        )
            except IntegrityError:
                logging.log(
                    logging.WARNING,
                    f"Item {item.identifier} is already in the database.",
                )


AU_SLURPER = AgdaUnimathSlurper()
