import logging
import requests
from concepts.models import Item
from django.db.utils import IntegrityError
from slurper.wd_raw_item import WD_OTHER_SOURCES, BaseWdRawItem

class WikidataSlurper:
    SPARQL_URL = "https://query.wikidata.org/sparql"

    SPARQL_QUERY_OPTIONS = """
  OPTIONAL
  { ?item wdt:P18 ?image . }
  OPTIONAL
  {
    ?wp_en rdf:type schema:Article;
      schema:isPartOf <https://en.wikipedia.org/>;
      schema:about ?item .
  }
  # except for natural numbers
  MINUS {
    ?item wdt:P31 wd:Q21199 .
  }
  # except for humans
  FILTER NOT EXISTS{ ?item wdt:P31 wd:Q5 . }
  # collect the label and description
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

    def __init__(self, source, query, limit=None):
        self.source = source
        self.query = (
            """
SELECT
  DISTINCT ?item ?itemLabel ?itemDescription ?image ?wp_en
 """
            + self._sparql_source_vars_select()
            + """
WHERE {
"""
            + query
            + self._sparql_source_vars_triples()
            + self.SPARQL_QUERY_OPTIONS
            + (f"LIMIT {limit}" if limit is not None else "")
        )
        self.raw_data = self.fetch_json()

    def _sparql_source_vars_select(self):
        def to_var(source_dict):
            return " ?" + source_dict["json_key"]

        return " ".join(map(to_var, WD_OTHER_SOURCES.values()))

    def _sparql_source_vars_triples(self):
        def to_triple(source_dict):
            source_var_triple = "  OPTIONAL\n  { ?item "
            source_var_triple += source_dict["wd_property"]
            source_var_triple += " ?" + source_dict["json_key"]
            source_var_triple += " . }"
            return source_var_triple

        return "\n".join(map(to_triple, WD_OTHER_SOURCES.values()))

    def fetch_json(self):
        response = requests.get(
            self.SPARQL_URL,
            params={"format": "json", "query": self.query},
        )
        return response.json()["results"]["bindings"]

    def get_items(self):
        for json_item in self.raw_data:
            raw_item = BaseWdRawItem.raw_item(self.source, json_item)
            yield raw_item.to_item()
            if self.source != Item.Source.WIKIDATA:
                raw_item.switch_source_to(Item.Source.WIKIDATA).yield_item_if_not_exists()
            if raw_item.has_source(Item.Source.WIKIPEDIA_EN):
                raw_item.switch_source_to(Item.Source.WIKIPEDIA_EN).yield_item_if_not_exists()

    def save_items(self):
        for item in self.get_items():
            try:
                item.save()
            except IntegrityError:
                logging.log(
                    logging.INFO,
                    f"Item {item.source} {item.identifier} is already in the database.",
                )

    def save_links(self):
        for json_item in self.raw_data:
            BaseWdRawItem.raw_item(
                self.source, json_item
            ).save_links()


SLURPERS = [
    WikidataSlurper(Item.Source.WIKIDATA, query)
    for query in [
        """
  # anything part of a topic that is studied by mathmatics
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .
""",
        """
  # concepts studied by an area of mathematics
  ?item wdt:P2579 ?area .
  ?area wdt:P31 wd:Q1936384
""",
        """
  # concepts of areas of mathematics
  ?item p:P31 ?of .
  ?of ps:P31 wd:Q151885 .
  ?of pq:P642/p:P31/ps:P31 wd:Q1936384
""",
        """
  # entities with nLab and MathWorld links
  { ?item wdt:P4215 ?nlabID . }
  UNION
  { ?item wdt:P2812 ?mwID . }
""",
    ]
]

SLURPERS += [
    WikidataSlurper(
        source, f"?item {source_property['wd_property']} ?{source_property['json_key']}"
    )
    for source, source_property in WD_OTHER_SOURCES.items()
]
