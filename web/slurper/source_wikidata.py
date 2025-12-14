import logging
import time
import urllib.parse

import requests
from concepts.models import Item
from django.db.utils import IntegrityError
from slurper.wd_raw_item import WD_OTHER_SOURCES, BaseWdRawItem

# Wikipedia API contact email (required by Wikipedia API guidelines)
# Set to None to disable Wikipedia article fetching
WIKIPEDIA_CONTACT_EMAIL = None
_missing_email_logged = False

# Wikidata entities to exclude from queries
KNOWN_EXCLUDED_CATEGORIES = [
    # Natural numbers
    "wd:Q21199",
    # positive integers
    "wd:Q28920044",
    # countries
    "wd:Q6256",
    # philosophical concepts
    "wd:Q714737",
]


def _load_excluded_categories_from_results():
    """
    Load Wikidata identifiers of items that have been categorized as "no"
    with confidence > 49%, to be excluded from future queries.

    Returns a list of Wikidata entity IDs in the format ["wd:Q12345", ...].
    """
    try:
        from concepts.models import CategorizerResult
        from django.db.models import Avg

        excluded_items = (
            CategorizerResult.objects.filter(
                result_answer=False, result_confidence__gt=49
            )
            .values("item__identifier", "item__source")
            .annotate(avg_confidence=Avg("result_confidence"))
            .filter(avg_confidence__gt=49, item__source=Item.Source.WIKIDATA)
            .distinct()
        )

        categories = [f"wd:{item['item__identifier']}" for item in excluded_items]

        if categories:
            logging.log(
                logging.INFO,
                f"Loaded {len(categories)} excluded categories "
                f"from categorizer results",
            )

        return categories
    except Exception as e:
        logging.log(
            logging.DEBUG, f"Could not load excluded categories from results: {e}"
        )
        return []


RESULT_EXCLUDED_CATEGORIES = _load_excluded_categories_from_results()

EXCLUDED_CATEGORIES = KNOWN_EXCLUDED_CATEGORIES + RESULT_EXCLUDED_CATEGORIES


# These are added to every query:
#   - Optional image: Fetches image if available
#   - Optional Wikipedia link: Gets English Wikipedia article
#   - Excludes natural numbers (FILTER NOT EXISTS)
#   - Excludes humans (FILTER NOT EXISTS)
#   - Label service: Automatically fetches English labels and descriptions
#
#   The class fetches mathematical concepts from Wikidata while
#   filtering out unwanted items like people and natural numbers.


class WikidataSlurper:
    SPARQL_URL = "https://query.wikidata.org/sparql"

    SPARQL_QUERY_OPTIONS = (
        """
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
    VALUES ?excludedType { """
        + " ".join(EXCLUDED_CATEGORIES)
        + """ }
    ?item wdt:P31 ?excludedType .
  }
  # except for humans
  FILTER NOT EXISTS{ ?item wdt:P31 wd:Q5 . }
  # collect the label and description
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""
    )

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
            + " ".join([f"?{src['json_key']}" for src in WD_OTHER_SOURCES.values()])
            + """
"""
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

    def fetch_article(self, json_item, index=None, total=None):
        global _missing_email_logged

        # Check if contact email is configured
        if WIKIPEDIA_CONTACT_EMAIL is None:
            if not _missing_email_logged:
                logging.log(
                    logging.WARNING,
                    "WIKIPEDIA_CONTACT_EMAIL is not set. "
                    "Wikipedia article fetching is disabled. "
                    "Please set WIKIPEDIA_CONTACT_EMAIL at the top of "
                    "source_wikidata.py to enable article fetching.",
                )
                _missing_email_logged = True
            return None

        wp_url = json_item["wp_en"]["value"]
        # Decode URL-encoded characters (e.g., %E2%80%93 becomes –)
        article_title = urllib.parse.unquote(wp_url.split("/wiki/")[-1])

        if index is not None and total is not None:
            logging.log(
                logging.INFO,
                f"Fetching Wikipedia article [{index}/{total}]: {article_title}",
            )
        else:
            logging.log(
                logging.INFO,
                f"Fetching Wikipedia article: {article_title}",
            )
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
            "User-Agent": f"MathSwitch/1.0 ({WIKIPEDIA_CONTACT_EMAIL})",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1  # Start with 1 second
        success = False
        for attempt in range(max_retries):
            try:
                # Rate limiting: delay between requests (100 req/s max)
                time.sleep(0.01)

                # Timeout: (connect_timeout, read_timeout) in seconds
                response = requests.get(
                    api_url, params=params, headers=headers, timeout=(5, 30)
                )

                # Handle rate limiting
                if response.status_code in (429, 403):
                    if attempt < max_retries - 1:
                        logging.log(
                            logging.WARNING,
                            f"Rate limited for {article_title}, retrying in "
                            f"{retry_delay}s (attempt {attempt + 1}/{max_retries})",
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logging.log(
                            logging.ERROR,
                            f"Failed to fetch {article_title} after "
                            f"{max_retries} attempts (rate limited). Skipping article.",
                        )
                        break

                response.raise_for_status()

                if not response.text:
                    logging.log(
                        logging.WARNING,
                        f"Empty response for Wikipedia article: "
                        f"{article_title}. Skipping article.",
                    )
                    break

                data = response.json()
                pages = data.get("query", {}).get("pages", {})

                # Get the first (and only) page
                for page_id, page_data in pages.items():
                    if "extract" in page_data:
                        success = True
                        return page_data["extract"]

                # Success, break retry loop
                break

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logging.log(
                        logging.WARNING,
                        f"Request failed for {article_title}: "
                        f"{e}, retrying in {retry_delay}s",
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logging.log(
                        logging.ERROR,
                        f"Failed to fetch {article_title}"
                        f" after {max_retries} attempts: {e}. Skipping article.",
                    )
        if not success and "wp_en" in json_item:
            logging.log(
                logging.INFO,
                f"Article {article_title} will have null value (fetch failed or empty)",
            )

        return None

    def get_items(self):
        for json_item in self.raw_data:
            raw_item = BaseWdRawItem.raw_item(self.source, json_item)
            yield raw_item.to_item()
            if self.source != Item.Source.WIKIDATA:
                raw_item_wd = raw_item.switch_source_to(Item.Source.WIKIDATA)
                if not raw_item_wd.item_exists():
                    yield raw_item_wd.to_item()
            if raw_item.has_source(Item.Source.WIKIPEDIA_EN):
                # Fetch Wikipedia article if available
                if "wp_en" in json_item and "article_text" not in json_item:
                    article_text = self.fetch_article(json_item)
                    if article_text is not None:
                        json_item["article_text"] = {"value": article_text}

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
