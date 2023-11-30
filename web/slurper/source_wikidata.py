import logging
from typing import Optional

import requests
from concepts.models import Item, Link
from django.db.utils import IntegrityError

WD_OTHER_SOURCE = {
    Item.Source.NLAB: {
        "wd_property": "wdt:P4215",
        "json_key": "nlabID",
    },
    Item.Source.MATHWORLD: {
        "wd_property": "wdt:P2812",
        "json_key": "mwID",
    },
    Item.Source.PROOF_WIKI: {
        "wd_property": "wdt:P6781",
        "json_key": "pwID",
    },
    Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS: {
        "wd_property": "wdt:P7554",
        "json_key": "eomID",
    },
}


class BaseWikidataRawItem:
    def __init__(self, source, json_item):
        self.source = source
        self.raw = json_item

    def identifier(self):
        pass

    def url(self):
        pass

    def name(self):
        pass

    def description(self):
        pass

    def to_item(self) -> Optional[Item]:
        return Item(
            source=self.source,
            identifier=self.identifier(),
            url=self.url(),
            name=self.name(),
            description=self.description(),
        )

    @staticmethod
    def get_raw_item(source, json_item):
        match source:
            case Item.Source.WIKIDATA:
                return WdRawItem(json_item)
            case Item.Source.NLAB:
                return nLabRawItem(json_item)
            case Item.Source.MATHWORLD:
                return MWRawItem(json_item)
            case Item.Source.PROOF_WIKI:
                return PWRawItem(json_item)
            case Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS:
                return EoMRawItem(json_item)


class WdRawItem(BaseWikidataRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.WIKIDATA, json_item)

    def identifier(self):
        id = self.raw["item"]["value"].split("/")[-1]
        if id is None:
            print("raw:\n", self.raw)
        return id

    def url(self):
        return self.raw["item"]["value"]

    def name(self):
        if "itemLabel" in self.raw:
            return self.raw["itemLabel"]["value"]
        else:
            return None

    def description(self):
        if "itemDescription" in self.raw:
            return self.raw["itemDescription"]["value"]
        else:
            None


class OtherWdRawItem(BaseWikidataRawItem):
    def __init__(self, source, json_item):
        super().__init__(source, json_item)
        self.json_key = WD_OTHER_SOURCE[self.source]["json_key"]

    def identifier(self):
        return self.raw[self.json_key]["value"]

    def name(self):
        return self.identifier()

    def description(self):
        return None


class nLabRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.NLAB, json_item)

    def url(self):
        return "https://ncatlab.org/nlab/show/" + self.identifier()


class MWRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.MATHWORLD, json_item)

    def url(self):
        return "https://mathworld.wolfram.com/" + self.identifier() + ".html"


class PWRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.PROOF_WIKI, json_item)

    def url(self):
        return "https://proofwiki.org/wiki/" + self.identifier()


class EoMRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS, json_item)

    def url(self):
        return "https://encyclopediaofmath.org/wiki/" + self.identifier()


class WikidataSlurper:
    SPARQL_URL = "https://query.wikidata.org/sparql"

    SPARQL_QUERY_OPTIONS = """
  OPTIONAL
  { ?item wdt:P18 ?image . }
  OPTIONAL
  {
    ?art rdf:type schema:Article;
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

    def __init__(self, source, query):
        self.source = source
        self.query = (
            """
SELECT
  DISTINCT ?item ?itemLabel ?itemDescription ?image ?art
 """
            + self._sparql_source_vars_select()
            + """
WHERE {
"""
            + query
            + self._sparql_source_vars_triples()
            + self.SPARQL_QUERY_OPTIONS
        )
        self.raw_data = self.fetch_json()

    def _sparql_source_vars_select(self):
        def to_var(source_dict):
            return " ?" + source_dict["json_key"]

        return " ".join(map(to_var, WD_OTHER_SOURCE.values()))

    def _sparql_source_vars_triples(self):
        def to_triple(source_dict):
            source_var_triple = "  OPTIONAL\n  { ?item "
            source_var_triple += source_dict["wd_property"]
            source_var_triple += " ?" + source_dict["json_key"]
            source_var_triple += " . }"
            return source_var_triple

        return "\n".join(map(to_triple, WD_OTHER_SOURCE.values()))

    def fetch_json(self):
        response = requests.get(
            self.SPARQL_URL,
            params={"format": "json", "query": self.query},
        )
        return response.json()["results"]["bindings"]

    def get_items(self):
        for json_item in self.raw_data:
            yield BaseWikidataRawItem.get_raw_item(self.source, json_item).to_item()
            if self.source != Item.Source.WIKIDATA:
                wd_json_item = WdRawItem(json_item)
                if not Item.objects.filter(
                    source=Item.Source.WIKIDATA, identifier=wd_json_item.identifier()
                ).exists():
                    yield wd_json_item.to_item()

    def save_items(self):
        for item in self.get_items():
            try:
                item.save()
            except IntegrityError:
                logging.log(logging.INFO, f" Link from {item.identifier} repeated.")

    def save_links(self):
        def save_link(current_item, source, source_id):
            try:
                destinationItem = Item.objects.get(source=source, identifier=source_id)
                Link.save_new(current_item, destinationItem, Link.Label.WIKIDATA)
            except Item.DoesNotExist:
                logging.log(
                    logging.WARNING,
                    f" Item {source_id} {source} does not exist in the database.",
                )

        for json_item in self.raw_data:
            identifier = BaseWikidataRawItem.get_raw_item(
                self.source, json_item
            ).identifier()
            current_item = Item.objects.get(source=self.source, identifier=identifier)
            if self.source == Item.Source.WIKIDATA:
                for source in [Item.Source.NLAB, Item.Source.MATHWORLD]:
                    source_key = WD_OTHER_SOURCE[source]["json_key"]
                    if source_key in json_item:
                        source_id = json_item[source_key]["value"]
                        save_link(current_item, source, source_id)
            else:  # link back to WD items
                wd_id = WdRawItem(json_item).identifier()
                save_link(current_item, Item.Source.WIKIDATA, wd_id)


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
    for source, source_property in WD_OTHER_SOURCE.items()
]
