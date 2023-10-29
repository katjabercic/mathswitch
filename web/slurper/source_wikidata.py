import logging
from typing import Optional

import requests
from concepts.models import Item
from django.db.utils import IntegrityError


class WikidataSlurper:

    SPARQL_URL = "https://query.wikidata.org/sparql"

    def __init__(self, source, query, id_map, url_map, name_map, desc_map):
        self.source = source
        self.query = query
        self.id_map = id_map
        self.url_map = url_map
        self.name_map = name_map
        self.desc_map = desc_map
        self.raw_data = self.fetch_json()

    def fetch_json(self):
        response = requests.get(
            self.SPARQL_URL,
            params={"format": "json", "query": self.query},
        )
        return response.json()["results"]["bindings"]
    
    def json_to_item(self, item) -> Optional[Item]:
        return Item(
            source=self.source,
            identifier=self.id_map(item),
            url=self.url_map(item),
            name=self.name_map(item),
            description=self.desc_map(item)
        )

    def get_items(self):
        for json_item in self.raw_data:
            yield self.json_to_item(json_item)

    def save_items(self):
        for item in self.get_items():
            try:
                item.save()
            except IntegrityError:
                logging.log(logging.WARNING, f" Item {item.identifier} repeated.")

    def save_links(self):
        for json_item in self.raw_data:
            currentItem = Item.objects.get(source=self.source, identifier=self.id_map(json_item))
            if self.source == Item.Source.WIKIDATA:
                # nLab
                if "nlabID" in json_item:
                    nlab_id = json_item["nlabID"]["value"]
                    try:
                        linkToItem = Item.objects.get(source=Item.Source.NLAB, identifier=nlab_id)
                        currentItem.links.add(linkToItem)
                    except:
                        logging.log(logging.WARNING, f" NLab item {nlab_id} does not exist in the database.")
            else: # link back to WD items
                wd_id = json_item["item"]["value"].split("/")[-1]
                try:
                    linkToItem = Item.objects.get(source=Item.Source.WIKIDATA, identifier=wd_id)
                    currentItem.links.add(linkToItem)
                except:
                    logging.log(logging.WARNING, f" Wikidata item {wd_id} does not exist in the database.")


WD_SLURPER = WikidataSlurper(
    Item.Source.WIKIDATA, 
    """
SELECT
  DISTINCT ?item ?itemLabel ?itemDescription ?image
  ?mwID ?emID ?nlabID ?pwID
  ?art
WHERE {
  # anything part of a topic that is studied by mathmatics
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .
  OPTIONAL
  { ?item wdt:P18 ?image . }
  OPTIONAL
  { ?item wdt:P2812 ?mwID . }   # MathWorld
  OPTIONAL
  { ?item wdt:P7554 ?emID . }   # Encyclopedia of Mathematics
  OPTIONAL
  { ?item wdt:P4215 ?nlabID . } # nLab
  OPTIONAL
  { ?item wdt:P6781 ?pwID . }   # ProofWiki
  OPTIONAL
  {
    ?art rdf:type schema:Article;
      schema:isPartOf <https://en.wikipedia.org/>;
      schema:about ?item .
  }

  # except for natural numbers
  filter(?topic != wd:Q21199) .
  # except for humans
  FILTER NOT EXISTS{ ?item wdt:P31 wd:Q5 . }
  # collect the label and description
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""", 
    id_map=lambda item: item["item"]["value"].split("/")[-1],
    url_map=lambda item: item["item"]["value"],
    name_map=lambda item: item["itemLabel"]["value"] if ("itemLabel" in item) else None,
    desc_map=lambda item: item["itemDescription"]["value"] if ("itemDescription" in item) else None
    )

WD_NLAB_SLURPER = WikidataSlurper(
    Item.Source.NLAB, 
    """
SELECT
  DISTINCT ?item ?nlabID
WHERE {
  # anything that has the nLab identifier property
  ?item wdt:P4215 ?nlabID .
  # except for humans
  FILTER NOT EXISTS{ ?item wdt:P31 wd:Q5 . }
  # collect the label and description
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""", 
    id_map=lambda item: item["nlabID"]["value"],
    url_map=lambda item: "https://ncatlab.org/nlab/show/" + item["nlabID"]["value"],
    name_map=lambda item: item["nlabID"]["value"],
    desc_map=lambda _: None
    )

