import gzip
from unittest.mock import Mock, patch

from concepts.models import Item, Link
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from slurper import source_house_of_graphs, source_oeis
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


def core_sequence(number):
    return {"number": number, "keyword": "core,nonn"}


def fake_oeis_search(pages_by_sort):
    def fake_get(url, params=None, headers=None):
        page = pages_by_sort[params["sort"]].get(params["start"], [])
        return Mock(json=Mock(return_value=page))

    return fake_get


class OeisSlurperTest(TestCase):
    def test_build_item_maps_fields(self):
        item = source_oeis.OEIS_SLURPER.build_item(
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

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids", return_value=set())
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_wikidata_shell_item_gets_description_filled(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
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

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids", return_value=set())
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_non_bridged_no_name_match_is_skipped(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
    ):
        mock_parse_names.return_value = [
            ("A999999", "Some obscure sequence description.")
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        self.assertEqual(Item.objects.filter(source=Item.Source.OEIS).count(), 0)

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids", return_value=set())
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_name_eq_match_creates_item_and_link(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
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

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids", return_value=set())
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_force_bypasses_throttle(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
    ):
        SlurperRun.objects.create(
            source=Item.Source.OEIS, last_succeeded_at=timezone.now()
        )
        mock_parse_names.return_value = []

        source_oeis.OEIS_SLURPER.save_items(force=True)

        mock_fetch_names.assert_called_once()

    @patch("slurper.source_oeis.time.sleep")
    @patch("slurper.source_oeis.requests.get")
    def test_fetch_core_ids_pages_and_keeps_only_core(self, mock_get, mock_sleep):
        pages = {
            0: [
                {"number": 40, "keyword": "core,nonn,nice"},
                {"number": 123456, "keyword": "nonn,easy"},
            ],
            2: [{"number": 45, "keyword": "nonn,core,easy"}],
        }
        mock_get.side_effect = fake_oeis_search({"number": pages, "-number": pages})

        ids = source_oeis.OEIS_SLURPER.fetch_core_ids()

        self.assertEqual(ids, {"A000040", "A000045"})
        params = [c.kwargs["params"] for c in mock_get.call_args_list]
        self.assertEqual(
            [(p["sort"], p["start"]) for p in params],
            [("number", 0), ("number", 2), ("number", 3)]
            + [("-number", 0), ("-number", 2), ("-number", 3)],
        )
        self.assertEqual({p["q"] for p in params}, {"keyword:core"})

    @patch.object(source_oeis.OeisSlurper, "ANONYMOUS_SEARCH_RESULT_LIMIT", 2)
    @patch("slurper.source_oeis.time.sleep")
    @patch("slurper.source_oeis.requests.get")
    def test_fetch_core_ids_combines_lowest_and_highest(self, mock_get, mock_sleep):
        mock_get.side_effect = fake_oeis_search(
            {
                "number": {0: [core_sequence(40), core_sequence(45)]},
                "-number": {0: [core_sequence(290), core_sequence(45)]},
            }
        )

        ids = source_oeis.OEIS_SLURPER.fetch_core_ids()

        self.assertEqual(ids, {"A000040", "A000045", "A000290"})

    @patch.object(source_oeis.OeisSlurper, "ANONYMOUS_SEARCH_RESULT_LIMIT", 2)
    @patch("slurper.source_oeis.time.sleep")
    @patch("slurper.source_oeis.requests.get")
    def test_fetch_core_ids_warns_when_middle_results_missing(
        self, mock_get, mock_sleep
    ):
        mock_get.side_effect = fake_oeis_search(
            {
                "number": {0: [core_sequence(40), core_sequence(45)]},
                "-number": {0: [core_sequence(291), core_sequence(290)]},
            }
        )

        with self.assertLogs(level="WARNING"):
            source_oeis.OEIS_SLURPER.fetch_core_ids()

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids")
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_core_sequence_without_match_is_imported(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
    ):
        mock_fetch_core_ids.return_value = {"A000040"}
        mock_parse_names.return_value = [("A000040", "The prime numbers.")]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        item = Item.objects.get(source=Item.Source.OEIS, identifier="A000040")
        self.assertEqual(item.name, "The prime numbers")
        self.assertEqual(item.url, "https://oeis.org/A000040")
        self.assertFalse(Link.objects.exists())

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids")
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_core_sequence_with_name_match_gets_link(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
    ):
        nlab_item = Item.objects.create(
            source=Item.Source.NLAB,
            identifier="fibonacci-numbers",
            url="https://ncatlab.org/nlab/show/fibonacci-numbers",
            name="Fibonacci numbers",
        )
        mock_fetch_core_ids.return_value = {"A000045"}
        mock_parse_names.return_value = [
            ("A000045", "Fibonacci numbers: a(n) = a(n-1) + a(n-2).")
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        oeis_item = Item.objects.get(source=Item.Source.OEIS, identifier="A000045")
        self.assertEqual(oeis_item.name, "Fibonacci numbers")
        self.assertTrue(
            Link.objects.filter(label=Link.Label.NAME_EQ)
            .filter(source__in=[oeis_item, nlab_item])
            .filter(destination__in=[oeis_item, nlab_item])
            .exists()
        )

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids")
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_non_core_without_match_still_skipped(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
    ):
        mock_fetch_core_ids.return_value = {"A000040"}
        mock_parse_names.return_value = [
            ("A000040", "The prime numbers."),
            ("A999999", "Some obscure sequence description."),
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        identifiers = set(
            Item.objects.filter(source=Item.Source.OEIS).values_list(
                "identifier", flat=True
            )
        )
        self.assertEqual(identifiers, {"A000040"})

    @patch("slurper.source_oeis.OeisSlurper.fetch_core_ids", return_value=set())
    @patch("slurper.source_oeis.OeisSlurper.fetch_names")
    @patch("slurper.source_oeis.OeisSlurper.parse_names")
    def test_name_match_links_to_every_item_with_that_name(
        self, mock_parse_names, mock_fetch_names, mock_fetch_core_ids
    ):
        for source, identifier in [
            (Item.Source.NLAB, "catalan-numbers"),
            (Item.Source.WIKIDATA, "Q270513"),
        ]:
            Item.objects.create(
                source=source,
                identifier=identifier,
                url=f"https://example.com/{identifier}",
                name="CATALAN NUMBERS",
            )
        mock_parse_names.return_value = [
            ("A000108", "Catalan numbers: C(n) = binomial(2n,n)/(n+1).")
        ]

        source_oeis.OEIS_SLURPER.save_items(force=True)

        oeis_item = Item.objects.get(source=Item.Source.OEIS, identifier="A000108")
        self.assertEqual(
            Link.objects.filter(label=Link.Label.NAME_EQ, source=oeis_item).count(),
            2,
        )

    def test_choose_name_falls_back_to_description_only_for_core(self):
        slurper = source_oeis.OEIS_SLURPER
        self.assertIsNone(slurper.choose_name("The prime numbers.", is_core=False))
        self.assertEqual(
            slurper.choose_name("The prime numbers.", is_core=True),
            "The prime numbers",
        )
        self.assertEqual(
            slurper.choose_name("Fibonacci numbers: a(n)...", is_core=True),
            "Fibonacci numbers",
        )

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
