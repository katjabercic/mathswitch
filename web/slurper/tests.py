import gzip
from unittest.mock import Mock, patch

from concepts.models import Item, Link
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from slurper import source_house_of_graphs, source_mathlib, source_oeis
from slurper.models import SlurperRun

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


# The following tests define what "done" means for the OEIS slurper's scoping
# rewrite (only import Wikidata-known A-numbers or NAME_EQ matches, fill in
# Wikidata-bridge shell items, credit the license, set a User-Agent).


class OeisSlurperTest(TestCase):
    def test_line_to_item_maps_fields(self):
        item = source_oeis.OEIS_SLURPER.line_to_item(
            "A000045",
            "Fibonacci numbers: a(0) = 0, a(1) = 1, a(n) = a(n-1) + a(n-2).",
        )

        self.assertEqual(item.identifier, "A000045")
        self.assertEqual(item.url, "https://oeis.org/A000045")
        self.assertEqual(item.name, "Fibonacci numbers")
        self.assertEqual(
            item.description,
            "Fibonacci numbers: a(0) = 0, a(1) = 1, a(n) = a(n-1) + a(n-2).",
        )

    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_wikidata_shell_item_gets_description_filled(
        self, mock_parse_names, mock_fetch_names
    ):
        Item.objects.create(
            source=Item.Source.OEIS,
            identifier="A000045",
            url="https://oeis.org/A000045",
            name="A000045",
            description=None,
        )
        mock_parse_names.return_value = [
            (
                "A000045",
                "Fibonacci numbers: a(0) = 0, a(1) = 1, a(n) = a(n-1) + a(n-2).",
            )
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        self.assertEqual(Item.objects.filter(source=Item.Source.OEIS).count(), 1)
        item = Item.objects.get(source=Item.Source.OEIS, identifier="A000045")
        self.assertEqual(item.name, "Fibonacci numbers")
        self.assertEqual(
            item.description,
            "Fibonacci numbers: a(0) = 0, a(1) = 1, a(n) = a(n-1) + a(n-2).",
        )

    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_non_bridged_no_name_match_is_skipped(
        self, mock_parse_names, mock_fetch_names
    ):
        mock_parse_names.return_value = [
            ("A999999", "Some obscure sequence description.")
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        self.assertEqual(Item.objects.filter(source=Item.Source.OEIS).count(), 0)

    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_name_eq_match_creates_item_and_link(
        self, mock_parse_names, mock_fetch_names
    ):
        nlab_item = Item.objects.create(
            source=Item.Source.NLAB,
            identifier="fibonacci-numbers",
            url="https://ncatlab.org/nlab/show/fibonacci-numbers",
            name="Fibonacci numbers",
        )
        mock_parse_names.return_value = [
            (
                "A000045",
                "fibonacci numbers: a(0) = 0, a(1) = 1, a(n) = a(n-1) + a(n-2).",
            )
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        oeis_item = Item.objects.get(source=Item.Source.OEIS, identifier="A000045")
        self.assertTrue(
            Link.objects.filter(
                label=Link.Label.NAME_EQ, source=oeis_item, destination=nlab_item
            ).exists()
            or Link.objects.filter(
                label=Link.Label.NAME_EQ, source=nlab_item, destination=oeis_item
            ).exists()
        )

    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    def test_throttle_blocks_without_force(self, mock_fetch_names):
        SlurperRun.objects.create(
            source=Item.Source.OEIS, last_succeeded_at=timezone.now()
        )

        source_oeis.OEIS_SLURPER.save_items()

        mock_fetch_names.assert_not_called()

    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_force_bypasses_throttle(self, mock_parse_names, mock_fetch_names):
        SlurperRun.objects.create(
            source=Item.Source.OEIS, last_succeeded_at=timezone.now()
        )
        mock_parse_names.return_value = []

        source_oeis.OEIS_SLURPER.save_items(force=True)

        mock_fetch_names.assert_called_once()

    @patch("slurper.source_oeis.requests.get")
    def test_fetch_names_sets_user_agent(self, mock_get):
        mock_get.return_value = Mock(content=gzip.compress(b"A000045 test"))

        source_oeis.OEIS_SLURPER.fetch_names()

        headers = mock_get.call_args.kwargs.get("headers", {})
        self.assertIn("@", headers.get("User-Agent", ""))

    def test_module_docstring_credits_oeis(self):
        docstring = source_oeis.__doc__ or ""

        self.assertIn("CC-BY-SA-4.0", docstring)
        self.assertIn("oeis.org", docstring)


class OeisCommandsTest(TestCase):
    @patch("slurper.source_oeis.OEIS_SLURPER.save_items")
    def test_import_oeis_calls_slurper(self, mock_save_items):
        call_command("import_oeis")

        mock_save_items.assert_called_once_with(force=False)

    @patch("slurper.source_oeis.OEIS_SLURPER.save_items")
    def test_import_oeis_with_force(self, mock_save_items):
        call_command("import_oeis", "--force")

        mock_save_items.assert_called_once_with(force=True)

    def test_clear_oeis_removes_only_oeis_items(self):
        Item.objects.create(
            source=Item.Source.WIKIDATA,
            identifier="wd-1",
            url="https://example.com/wd-1",
            name="Wikidata item",
        )
        Item.objects.create(
            source=Item.Source.OEIS,
            identifier="A000045",
            url="https://oeis.org/A000045",
            name="A000045",
        )

        call_command("clear_oeis", "--force")

        self.assertTrue(Item.objects.filter(source=Item.Source.WIKIDATA).exists())
        self.assertFalse(Item.objects.filter(source=Item.Source.OEIS).exists())


MATHLIB_INDEX = {
    "declarations": {
        "Nat.Prime": {
            "docLink": "./Mathlib/Data/Nat/Prime/Defs.html#Nat.Prime",
            "kind": "def",
        },
        "Nat.Prime.two_le": {
            "docLink": "./Mathlib/Data/Nat/Prime/Defs.html#Nat.Prime.two_le",
            "kind": "theorem",
        },
        "Nat.instDecidablePrime": {
            "docLink": "./Mathlib/Data/Nat/Prime/Defs.html#Nat.instDecidablePrime",
            "kind": "instance",
        },
        "Group": {
            "docLink": "./Mathlib/Algebra/Group/Defs.html#Group",
            "kind": "class",
        },
        "List.splitAt": {
            "docLink": "./Batteries/Data/List/Basic.html#List.splitAt",
            "kind": "def",
        },
        "Nat": {
            "docLink": "./Init/Prelude.html#Nat",
            "kind": "inductive",
        },
    },
    "instances": {},
    "instancesFor": {},
    "modules": {},
}


class MathlibSlurperTest(TestCase):
    def included(self, slurper):
        return {name for name, _ in slurper.iter_declarations(MATHLIB_INDEX)}

    def test_default_filter_keeps_only_mathlib_concept_kinds(self):
        self.assertEqual(
            self.included(source_mathlib.MathlibSlurper()), {"Nat.Prime", "Group"}
        )

    def test_filter_can_be_extended_to_other_packages(self):
        slurper = source_mathlib.MathlibSlurper(packages={"Mathlib", "Batteries"})

        self.assertEqual(self.included(slurper), {"Nat.Prime", "Group", "List.splitAt"})

    def test_declaration_to_item_maps_fields(self):
        item = source_mathlib.MATHLIB_SLURPER.declaration_to_item(
            "Nat.Prime", MATHLIB_INDEX["declarations"]["Nat.Prime"]
        )

        self.assertEqual(item.source, Item.Source.MATHLIB)
        self.assertEqual(item.identifier, "Nat.Prime")
        self.assertEqual(
            item.url,
            "https://leanprover-community.github.io/mathlib4_docs/"
            "Mathlib/Data/Nat/Prime/Defs.html#Nat.Prime",
        )
        self.assertEqual(item.name, "Nat.Prime")
        self.assertEqual(item.meta, "def")

    @patch(
        "slurper.source_mathlib.MATHLIB_SLURPER.fetch_index",
        return_value=MATHLIB_INDEX,
    )
    def test_save_items_creates_items_without_duplicates(self, mock_fetch_index):
        source_mathlib.MATHLIB_SLURPER.save_items(force=True)
        source_mathlib.MATHLIB_SLURPER.save_items(force=True)

        self.assertEqual(
            set(
                Item.objects.filter(source=Item.Source.MATHLIB).values_list(
                    "identifier", flat=True
                )
            ),
            {"Nat.Prime", "Group"},
        )
        self.assertEqual(Item.objects.filter(source=Item.Source.MATHLIB).count(), 2)

    @patch("slurper.source_mathlib.MATHLIB_SLURPER.fetch_index")
    def test_throttle_blocks_without_force(self, mock_fetch_index):
        SlurperRun.objects.create(
            source=Item.Source.MATHLIB, last_succeeded_at=timezone.now()
        )

        source_mathlib.MATHLIB_SLURPER.save_items()

        mock_fetch_index.assert_not_called()

    @patch(
        "slurper.source_mathlib.MATHLIB_SLURPER.fetch_index",
        return_value=MATHLIB_INDEX,
    )
    def test_force_bypasses_throttle(self, mock_fetch_index):
        SlurperRun.objects.create(
            source=Item.Source.MATHLIB, last_succeeded_at=timezone.now()
        )

        source_mathlib.MATHLIB_SLURPER.save_items(force=True)

        mock_fetch_index.assert_called_once()


class MathlibCommandsTest(TestCase):
    @patch("slurper.source_mathlib.MATHLIB_SLURPER.save_items")
    def test_import_mathlib_calls_slurper(self, mock_save_items):
        call_command("import_mathlib")

        mock_save_items.assert_called_once_with(force=False)

    @patch("slurper.source_mathlib.MATHLIB_SLURPER.save_items")
    def test_import_mathlib_with_force(self, mock_save_items):
        call_command("import_mathlib", "--force")

        mock_save_items.assert_called_once_with(force=True)

    def test_clear_mathlib_removes_only_mathlib_items(self):
        Item.objects.create(
            source=Item.Source.WIKIDATA,
            identifier="wd-1",
            url="https://example.com/wd-1",
            name="Wikidata item",
        )
        Item.objects.create(
            source=Item.Source.MATHLIB,
            identifier="Nat.Prime",
            url="https://example.com/Nat.Prime",
            name="Nat.Prime",
        )

        call_command("clear_mathlib", "--force")

        self.assertTrue(Item.objects.filter(source=Item.Source.WIKIDATA).exists())
        self.assertFalse(Item.objects.filter(source=Item.Source.MATHLIB).exists())
