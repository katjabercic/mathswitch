import json

from categorizer.wikidata_fetch_service import WikidataFetchService
from django.test import TestCase


class WikidataFetchServiceTest(TestCase):
    """
    Live test against the Wikidata API.
    Run with: python manage.py test categorizer.tests.WikidataFetchServiceTest
    """

    def setUp(self):
        self.service = WikidataFetchService()

    def test_fetch_entity_q2261345(self):
        """Fetch Q2261345 and print the response for inspection."""
        entity_id = "Q2261345"
        entity = self.service.fetch_entity(entity_id)

        self.assertIsNotNone(entity, "Expected entity data, got None")

        # Basic structure
        self.assertIn("labels", entity)
        self.assertIn("descriptions", entity)
        self.assertIn("claims", entity)
        self.assertIn("sitelinks", entity)

        # Print for inspection
        print(f"\n{'=' * 60}")
        print(f"Entity: {entity_id}")
        print(f"{'=' * 60}")

        label = entity["labels"].get("en", {}).get("value")
        print(f"Label: {label}")

        description = entity["descriptions"].get("en", {}).get("value")
        print(f"Description: {description}")

        print(f"\nClaims ({len(entity['claims'])} properties):")
        for prop_id, claims in entity["claims"].items():
            values = []
            for claim in claims:
                mainsnak = claim.get("mainsnak", {})
                datavalue = mainsnak.get("datavalue", {})
                values.append(datavalue.get("value", "N/A"))
            print(f"  {prop_id}: {values}")

        print(f"\nSitelinks ({len(entity['sitelinks'])} wikis):")
        for site, link in entity["sitelinks"].items():
            print(f"  {site}: {link['title']}")

        print(f"\n{'=' * 60}")
        print(f"Full JSON:\n{json.dumps(entity, indent=2)[:3000]}")
