import logging

import requests
from concepts.models import Item
from django.db.utils import IntegrityError
from slurper.wd_raw_item import WD_OTHER_SOURCES, BaseWdRawItem


# Wikidata entities to exclude from queries (natural numbers and positive integers)
# TODO SST: Ask Katja: whether to add all found
#   1. Should I put all found? Most likely yes
#   2. Use categorization results to exclude them in further uses
KNOWN_EXCLUDED_CATEGORIES = ["wd:Q21199", "wd:Q28920044"]


# These are added to every query:
#   - Optional image: Fetches image if available
#   - Optional Wikipedia link: Gets English Wikipedia article
#   - Excludes natural numbers (FILTER NOT EXISTS)
#   - Excludes humans (FILTER NOT EXISTS)
#   - Label service: Automatically fetches English labels and descriptions
#
#   The class fetches mathematical concepts from Wikidata while filtering out unwanted items like people and natural numbers.

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
  OPTIONAL
  { ?item skos:altLabel ?itemAltLabel . FILTER (lang(?itemAltLabel) = "en") }
  # except for natural numbers and positive integers
  FILTER NOT EXISTS {
    VALUES ?excludedType { """ + " ".join(KNOWN_EXCLUDED_CATEGORIES) + """ }
    ?item wdt:P31 ?excludedType .
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
  (GROUP_CONCAT(DISTINCT ?itemAltLabel; separator=", ") AS ?aliases)
 """
            + self._sparql_source_vars_select()
            + """
WHERE {
"""
            + query
            + self._sparql_source_vars_triples()
            + self.SPARQL_QUERY_OPTIONS
            + """
GROUP BY ?item ?itemLabel ?itemDescription ?image ?wp_en """
            + " ".join(
                [f"?{src['json_key']}" for src in WD_OTHER_SOURCES.values()]
            )
            + """
"""
            + (f"LIMIT {limit}" if limit is not None else "")
        )
        self.raw_data = self.fetch_json()
        self.article_text = self.fetch_articles()


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

    def fetch_articles(self):
        """Fetch Wikipedia article text for items with wp_en links."""
        article_texts = {}

        for json_item in self.raw_data:
            # Only fetch if Wikipedia link exists
            if "wp_en" not in json_item:
                continue

            wp_url = json_item["wp_en"]["value"]
            article_title = wp_url.split("/wiki/")[-1]

            api_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "titles": article_title,
                "prop": "extracts",
                "explaintext": True,
                "exsectionformat": "plain",
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }

            try:
                response = requests.get(api_url, params=params, headers=headers)
                response.raise_for_status()

                if not response.text:
                    logging.log(
                        logging.WARNING,
                        f"Empty response for Wikipedia article: {article_title}",
                    )
                    continue

                data = response.json()
                pages = data.get("query", {}).get("pages", {})

                # Get the first (and only) page
                for page_id, page_data in pages.items():
                    if "extract" in page_data:
                        # Use Wikidata ID as key
                        wd_id = json_item["item"]["value"]
                        article_texts[wd_id] = page_data["extract"]
                        break
            except Exception as e:
                logging.log(
                    logging.WARNING,
                    f"Failed to fetch Wikipedia article for {article_title}: {e}",
                )

        return article_texts

    def get_items(self):
        for json_item in self.raw_data:
            wd_id = json_item["item"]["value"]
            if wd_id in self.article_text:
                json_item["article_text"] = {"value": self.article_text[wd_id]}

            raw_item = BaseWdRawItem.raw_item(self.source, json_item)
            yield raw_item.to_item()
            if self.source != Item.Source.WIKIDATA:
                raw_item_wd = raw_item.switch_source_to(Item.Source.WIKIDATA)
                if not raw_item_wd.item_exists():
                    yield raw_item_wd.to_item()
            if raw_item.has_source(Item.Source.WIKIPEDIA_EN):
                raw_item_wp_en = raw_item.switch_source_to(Item.Source.WIKIPEDIA_EN)
                if not raw_item_wp_en.item_exists():
                    yield raw_item_wp_en.to_item()

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
            BaseWdRawItem.raw_item(self.source, json_item).save_links()


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
  ?area wdt:P31 wd:Q1936384 .
""",
        """
  # concepts of areas of mathematics
  ?item p:P31 ?of .
  ?of ps:P31 wd:Q151885 .
  ?of pq:P642/p:P31/ps:P31 wd:Q1936384 .
""",
    ]
]

SLURPERS += [
    WikidataSlurper(
        source,
        f"\n  ?item {property['wd_property']} ?{property['json_key']} .\n",
    )
    for source, property in WD_OTHER_SOURCES.items()
]
