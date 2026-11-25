from unittest.mock import MagicMock, patch

from categorizer.wikidata_fetch_service import WIKIDATA_API_URL, WikidataFetchService
from django.test import TestCase

ENTITY_ID = "Q2261345"
ENTITY = {
    "id": ENTITY_ID,
    "labels": {"en": {"language": "en", "value": "example concept"}},
    "descriptions": {"en": {"language": "en", "value": "example description"}},
    "claims": {
        "P4215": [{"mainsnak": {"datavalue": {"value": "example+concept"}}}],
    },
    "sitelinks": {"enwiki": {"site": "enwiki", "title": "Example concept"}},
}


class WikidataFetchServiceTest(TestCase):
    def setUp(self):
        self.service = WikidataFetchService()

    @patch("categorizer.wikidata_fetch_service.requests.get")
    def test_fetch_entity(self, mock_get):
        response = MagicMock(status_code=200)
        response.json.return_value = {"entities": {ENTITY_ID: ENTITY}}
        mock_get.return_value = response

        entity = self.service.fetch_entity(ENTITY_ID)

        self.assertEqual(entity, ENTITY)
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], WIKIDATA_API_URL)
        self.assertEqual(kwargs["params"]["action"], "wbgetentities")
        self.assertEqual(kwargs["params"]["ids"], ENTITY_ID)
