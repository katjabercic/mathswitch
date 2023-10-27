# import logging
# from typing import Optional

# import requests
# from concepts.models import Item
# from django.db.utils import IntegrityError

SPARQL_URL = "https://query.wikidata.org/sparql"

NLAB_WD_QUERY = """
SELECT
  DISTINCT ?item ?nlabID
WHERE {
  # anything part of a topic that is studied by mathmatics!
  ?item wdt:P4215 ?nlabID .
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .

  # except for natural numbers
  filter(?topic != wd:Q21199) .
  # and except for humans
  FILTER NOT EXISTS{ ?item wdt:P31 wd:Q5 . }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""
