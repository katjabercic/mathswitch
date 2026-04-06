import json
import logging
import time

import requests
from concepts.models import Item

from web.settings import WIKIPEDIA_CONTACT_EMAIL

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

RETRY_DELAYS = [5, 10, 30]

# Wikidata property -> meta key mapping for external IDs
EXTERNAL_ID_PROPERTIES = {
    "P2812": "mathworld_id",
    "P4215": "nlab_id",
    "P6781": "proofwiki_id",
    "P7554": "eom_id",
}


class WikidataFetchService:

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_headers(self):
        return {
            "User-Agent": f"MathSwitch/1.0 ({WIKIPEDIA_CONTACT_EMAIL})",
            "Accept": "application/json",
        }

    def fetch_entity(self, entity_id):
        """
        Fetch entity data from the Wikidata API for a given Q-id.

        Returns the entity dict on success, or None on failure.
        """
        max_retries = len(RETRY_DELAYS) + 1
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    WIKIDATA_API_URL,
                    params={
                        "action": "wbgetentities",
                        "format": "json",
                        "ids": entity_id,
                        "props": "labels|descriptions|claims|sitelinks",
                        "languages": "en",
                    },
                    headers=self.get_headers(),
                    timeout=(10, 30),
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries - 1:
                        delay = RETRY_DELAYS[attempt]
                        self.logger.info(
                            f"[wikidata-fetch] retryable status "
                            f"{response.status_code}, waiting {delay}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(
                            f"[wikidata-fetch] giving up after "
                            f"{max_retries} attempts "
                            f"(status {response.status_code})"
                        )
                        return None

                response.raise_for_status()
                data = response.json()
                entities = data.get("entities", {})
                return entities.get(entity_id)

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = RETRY_DELAYS[attempt]
                    self.logger.info(
                        f"[wikidata-fetch] request failed ({e}), "
                        f"retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"[wikidata-fetch] giving up after "
                        f"{max_retries} attempts: {e}"
                    )
                    return None
        return None

    def fetch_and_store_meta(self, item):
        """
        Fetch entity data from the item's source and store it in item.meta.

        Currently only supports Wikidata (source=Wd).
        Returns True if meta was updated, False otherwise.
        """
        if item.source != Item.Source.WIKIDATA:
            self.logger.debug(
                f"[wikidata-fetch] skipping non-Wikidata item: "
                f"{item.identifier} (source={item.source})"
            )
            return False

        meta = self._parse_meta(item.meta)
        if meta.get("raw"):
            self.logger.debug(
                f"[wikidata-fetch] meta.raw already present " f"for {item.identifier}"
            )
            return False

        entity = self.fetch_entity(item.identifier)
        if entity is None:
            self.logger.warning(
                f"[wikidata-fetch] failed to fetch entity for {item.identifier}"
            )
            return False

        meta["raw"] = entity
        self._extract_external_ids(meta, entity)
        item.meta = json.dumps(meta)
        item.save(update_fields=["meta"])
        self.logger.info(f"[wikidata-fetch] stored meta for {item.identifier}")
        return True

    def _extract_external_ids(self, meta, entity):
        claims = entity.get("claims", {})
        for prop_id, meta_key in EXTERNAL_ID_PROPERTIES.items():
            if prop_id in claims:
                claim_list = claims[prop_id]
                if claim_list:
                    value = (
                        claim_list[0]
                        .get("mainsnak", {})
                        .get("datavalue", {})
                        .get("value")
                    )
                    if value:
                        meta[meta_key] = value

    def _parse_meta(self, raw):
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
