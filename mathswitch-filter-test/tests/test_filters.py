import tempfile
import unittest
from pathlib import Path

from filters import FILTERS
from filters.docstring import docstring_filter
from filters.kind import kind_filter
from filters.llm_judge import (
    build_prompt,
    judge_all,
    llm_filter,
    load_cache,
    parse_answer,
)
from filters.namespace import namespace_filter
from filters.references import references_filter
from ground_truth import parse_yaml, split_by_universe
from run_filters import apply_filters, choose_llm_names


def decl(**kw):
    base = {
        "kind": "def",
        "module": "Mathlib/Algebra/Group/Defs",
        "doc": None,
        "refs": 0,
    }
    base.update(kw)
    return base


class DocstringFilterTest(unittest.TestCase):
    def test_missing_or_short(self):
        self.assertFalse(docstring_filter("X", decl(), {}))
        self.assertFalse(docstring_filter("X", decl(doc="Convexity of sets."), {}))

    def test_restates_name(self):
        doc = "`Foo.someLongName` `someLongName` `Foo.someLongName`."
        self.assertFalse(docstring_filter("Foo.someLongName", decl(doc=doc), {}))

    def test_real_doc(self):
        doc = "A `Group` is a `Monoid` with an operation `⁻¹` satisfying `a⁻¹ * a = 1`."
        self.assertTrue(docstring_filter("Group", decl(doc=doc), {}))


class NamespaceFilterTest(unittest.TestCase):
    def test_blocked_module(self):
        self.assertFalse(
            namespace_filter("Foo", decl(module="Mathlib/Tactic/Ring/Basic"), {})
        )
        self.assertFalse(namespace_filter("Foo", decl(module="Mathlib/Util/Foo"), {}))

    def test_similar_module_name_not_blocked(self):
        self.assertTrue(namespace_filter("Foo", decl(module="Mathlib/Utility"), {}))

    def test_blocked_components(self):
        for name in [
            "Mathlib.Meta.FunProp.Foo",
            "Foo._aux",
            "Foo.proof_1",
            "Real.«term√_»",
            "X.1",
        ]:
            self.assertFalse(namespace_filter(name, decl(), {}), name)

    def test_concept(self):
        self.assertTrue(namespace_filter("Nat.Prime", decl(), {}))


class SimpleFiltersTest(unittest.TestCase):
    def test_kind(self):
        self.assertTrue(kind_filter("G", decl(kind="class"), {}))
        self.assertFalse(kind_filter("f", decl(kind="def"), {}))

    def test_references(self):
        self.assertTrue(references_filter("G", decl(refs=10), {}))
        self.assertFalse(references_filter("G", decl(refs=9), {}))


class LLMJudgeTest(unittest.TestCase):
    def test_parse_answer(self):
        self.assertEqual(parse_answer("yes,85"), {"answer": True, "confidence": 85})
        self.assertEqual(
            parse_answer("<think>hmm</think>\nno, 70"),
            {"answer": False, "confidence": 70},
        )
        self.assertEqual(
            parse_answer("Yes. It is a concept"), {"answer": True, "confidence": None}
        )
        self.assertIsNone(parse_answer("maybe"))

    def test_prompt_contains_fields(self):
        prompt = build_prompt("Nat.Prime", decl(doc="prime   numbers"))
        self.assertIn("Name: Nat.Prime", prompt)
        self.assertIn("Docstring: prime numbers", prompt)

    def test_judge_all_caches_and_resumes(self):
        decls = {"A": decl(), "B": decl(), "C": decl()}
        calls = []

        def fake(prompt):
            calls.append(prompt)
            if "Name: C" in prompt:
                raise RuntimeError("down")
            return "yes,90" if "Name: A" in prompt else "no,60"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.jsonl"
            verdicts = judge_all(["A", "B", "C"], decls, "FAKE", call=fake, path=path)
            self.assertEqual(verdicts, {"A": True, "B": False})
            self.assertEqual(len(load_cache(path)), 2)
            calls.clear()
            judge_all(["A", "B", "C"], decls, "FAKE", call=fake, path=path)
            self.assertEqual(len(calls), 1)  # only C is retried

    def test_judge_all_aborts_when_model_unreachable(self):
        def down(prompt):
            raise ConnectionError("refused")

        decls = {f"d{i}": decl() for i in range(10)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.jsonl"
            with self.assertRaises(RuntimeError):
                judge_all(list(decls), decls, "FAKE", call=down, path=path)

    def test_llm_filter_unjudged_is_none(self):
        self.assertIsNone(llm_filter("X", decl(), {"llm": {}}))
        self.assertTrue(llm_filter("X", decl(), {"llm": {"X": True}}))


class GroundTruthTest(unittest.TestCase):
    def test_overview_leaves(self):
        text = "Algebra:\n  Groups:\n    group: 'Group'\n    empty: ''\n  ring: Ring\n"
        self.assertEqual(
            parse_yaml("overview.yaml", text), {"Group": "overview", "Ring": "overview"}
        )

    def test_numbered_entries(self):
        text = (
            "Q1:\n  title: A\n  decl: foo\n"
            "Q2:\n  title: B\n  decls:\n    - bar\n    - baz\n"
            "Q3:\n  title: C\n"
        )
        self.assertEqual(
            parse_yaml("1000.yaml", text), {"foo": "Q1", "bar": "Q2", "baz": "Q2"}
        )

    def test_split_by_universe(self):
        inside, other, missing = split_by_universe(
            ["a", "b", "c"], {"a": {}}, {"a": {}, "b": {}}
        )
        self.assertEqual((inside, other, missing), (["a"], ["b"], ["c"]))


class RunFiltersTest(unittest.TestCase):
    def test_apply_filters_runs_every_filter(self):
        results = apply_filters({"Group": decl(kind="class", refs=50)}, {"llm": {}})
        self.assertEqual(set(results["Group"]), set(FILTERS))
        self.assertTrue(results["Group"]["kind"])
        self.assertIsNone(results["Group"]["llm"])

    def test_llm_sample_includes_ground_truth_and_is_deterministic(self):
        decls = {f"d{i}": decl() for i in range(100)}
        first = choose_llm_names(decls, {"d5"}, sample=10)
        self.assertEqual(first[0], "d5")
        self.assertEqual(len(first), 11)
        self.assertEqual(first, choose_llm_names(decls, {"d5"}, sample=10))


if __name__ == "__main__":
    unittest.main()
