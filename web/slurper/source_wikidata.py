import logging
from typing import Optional

import requests
from concepts.models import Item
from django.db.utils import IntegrityError

API_URL = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"

PROPERTY = {
    "IMAGE": "P18",
    "MATHWORLD_ID": "P2812",
    "ENCYCLOPEDIA_OF_OF_MATHEMATICS_ID": "P7554",
    "NLAB_ID": "P4215",
    "PROOFWIKI_ID": "P6781",
}

MATH_QUERY = """
SELECT
  DISTINCT ?item ?itemLabel ?itemDescription ?image
  ?mwID ?emID ?nlabID ?pwID
  ?art
WHERE {
  # anything part of a topic that is studied by mathmatics!
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
  # TODO filter out humans
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_json(query):
    response = requests.get(
        SPARQL_URL,
        params={"format": "json", "query": query},
    )
    return response.json()["results"]["bindings"]


def json_to_item(item) -> Optional[Item]:
    url = item["item"]["value"]
    identifier = url.split("/")[-1]
    name = item["itemLabel"]["value"] if ("itemLabel" in item) else None
    description = (
        item["itemDescription"]["value"] if ("itemDescription" in item) else None
    )
    return Item(
        source=Item.Source.WIKIDATA,
        identifier=identifier,
        url=url,
        name=name,
        description=description,
    )


def fetch_items(query):
    json = fetch_json(query)
    for json_item in json:
        yield json_to_item(json_item)


def save_items(query):
    for item in fetch_items(query):
        try:
            item.save()
        except IntegrityError:
            logging.log(logging.WARNING, f"Item {item.identifier} repeated.")
