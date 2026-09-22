from unittest.mock import patch

from concepts.models import Item
from django.core.management import call_command
from django.test import TestCase
from slurper import source_house_of_graphs

# Run: ./venv/bin/python ./web/manage.py test slurper.tests

CHROMATIC_NUMBER = {
    "invariantId": 4,
    "definition": (
        "The <i>chromatic number</i> of a graph <i>G</i> is the minimum number "
        "of different colors required to color the vertices of <i>G</i>."
    ),
    "keyword": "Chromatic",
    "invariantName": "Chromatic Number",
    "typeName": "i",
}


class HoGSlurperTest(TestCase):
    def test_invariant_maps_to_item(self):
        item = source_house_of_graphs.HOG_SLURPER.invariant_to_item(CHROMATIC_NUMBER)

        self.assertEqual(item.identifier, "4")
        self.assertEqual(item.url, "https://houseofgraphs.org/invariants/4")
        self.assertEqual(item.name, "Chromatic Number")
        self.assertNotIn("<", item.description)


class HouseOfGraphsCommandsTest(TestCase):
    def test_clear_house_of_graphs_removes_only_house_of_graphs_items(self):
        Item.objects.create(
            source=Item.Source.WIKIDATA,
            identifier="wd-1",
            url="https://example.com/wd-1",
            name="Wikidata item",
        )
        Item.objects.create(
            source=Item.Source.HOUSE_OF_GRAPHS,
            identifier="hog-1",
            url="https://example.com/hog-1",
            name="House of Graphs item",
        )

        call_command("clear_house_of_graphs")

        self.assertTrue(Item.objects.filter(source=Item.Source.WIKIDATA).exists())
        self.assertFalse(
            Item.objects.filter(source=Item.Source.HOUSE_OF_GRAPHS).exists()
        )

    @patch("slurper.source_house_of_graphs.HOG_SLURPER.save_items")
    def test_import_house_of_graphs_calls_slurper(self, mock_save_items):
        call_command("import_house_of_graphs")

        mock_save_items.assert_called_once_with()
