import logging
from typing import Optional

import requests
from concepts.models import Item, Link
from django.db.utils import IntegrityError


class WikidataSlurper:
    SPARQL_URL = "https://query.wikidata.org/sparql"

    SPARQL_QUERY_SELECT = """
SELECT
  DISTINCT ?item ?itemLabel ?itemDescription ?image
  ?mwID ?emID ?nlabID ?pwID
  ?art
WHERE {
"""

    SPARQL_QUERY_OPTIONS = """
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
  # except for humans
  FILTER NOT EXISTS{ ?item wdt:P31 wd:Q5 . }
  # collect the label and description
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

    def __init__(self, source, query, id_map, url_map, name_map, desc_map):
        self.source = source
        self.query = self.SPARQL_QUERY_SELECT + query + self.SPARQL_QUERY_OPTIONS
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
            description=self.desc_map(item),
        )

    def get_items(self):
        for json_item in self.raw_data:
            yield self.json_to_item(json_item)

    def save_items(self):
        for item in self.get_items():
            try:
                item.save()
            except IntegrityError:
                logging.log(logging.WARNING, f" Link from {item.identifier} repeated.")

    def save_links(self):
        def source_to_key(source):
            """Map source to WD json key for that source"""
            if source == Item.Source.NLAB:
                return "nlabID"
            elif source == Item.Source.MATHWORLD:
                return "mwID"
            else:
                return None

        def save_link(current_item, source, source_id):
            try:
                destinationItem = Item.objects.get(source=source, identifier=source_id)
                Link.save_new(current_item, destinationItem, Link.Label.WIKIDATA)
            except Item.DoesNotExist:
                logging.log(
                    logging.WARNING,
                    f" {source} item {source_id} does not exist in the database.",
                )

        for json_item in self.raw_data:
            current_item = Item.objects.get(
                source=self.source, identifier=self.id_map(json_item)
            )
            if self.source == Item.Source.WIKIDATA:
                for source in [Item.Source.NLAB, Item.Source.MATHWORLD]:
                    if source_to_key(source) in json_item:
                        source_id = json_item[source_to_key(source)]["value"]
                        save_link(current_item, source, source_id)
            else:  # link back to WD items
                wd_id = json_item["item"]["value"].split("/")[-1]
                save_link(current_item, Item.Source.WIKIDATA, wd_id)


WD_SLURPER_1 = WikidataSlurper(
    Item.Source.WIKIDATA,
    """
  # anything part of a topic that is studied by mathmatics
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .
  # except for natural numbers
  filter(?topic != wd:Q21199) .
""",
    id_map=lambda item: item["item"]["value"].split("/")[-1],
    url_map=lambda item: item["item"]["value"],
    name_map=lambda item: item["itemLabel"]["value"] if ("itemLabel" in item) else None,
    desc_map=lambda item: item["itemDescription"]["value"]
    if ("itemDescription" in item)
    else None,
)

WD_SLURPER_2 = WikidataSlurper(
    Item.Source.WIKIDATA,
    """
  # concepts of areas of mathematics
  ?item p:P31 ?of.
  ?of ps:P31 wd:Q151885.
  ?of pq:P642/p:P31/ps:P31 wd:Q1936384
""",
    id_map=lambda item: item["item"]["value"].split("/")[-1],
    url_map=lambda item: item["item"]["value"],
    name_map=lambda item: item["itemLabel"]["value"] if ("itemLabel" in item) else None,
    desc_map=lambda item: item["itemDescription"]["value"]
    if ("itemDescription" in item)
    else None,
)

WD_NLAB_SLURPER = WikidataSlurper(
    Item.Source.NLAB,
    """
  # anything that has the nLab identifier property
  ?item wdt:P4215 ?nlabID .
""",
    id_map=lambda item: item["nlabID"]["value"],
    url_map=lambda item: "https://ncatlab.org/nlab/show/" + item["nlabID"]["value"],
    name_map=lambda item: item["nlabID"]["value"],
    desc_map=lambda _: None,
)

WD_MATHWORLD_SLURPER = WikidataSlurper(
    Item.Source.MATHWORLD,
    """
  # anything that has the MathWorld identifier property
  ?item wdt:P2812 ?mwID .
""",
    id_map=lambda item: item["mwID"]["value"],
    url_map=lambda item: "https://mathworld.wolfram.com/"
    + item["mwID"]["value"]
    + ".html",
    name_map=lambda item: item["mwID"]["value"],
    desc_map=lambda _: None,
)

#   ?concept wdt:P642 ?area .
#   ?area wdt:P31 wd:Q1936384 .
