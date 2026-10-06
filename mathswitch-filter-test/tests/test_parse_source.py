import unittest

from parse_source import (
    additive_name,
    build_index,
    count_references,
    parse_file,
    split_code,
)

LEAN = """
/-!
# Module doc mentioning namespace Fake
-/
module

@[expose] public section

namespace Nat

/-- `Nat.Prime p` means that `p` is prime. -/
@[pp_nodot, wikidata Q49008]
def Prime (p : ℕ) := Irreducible p

-- def Commented : Nat := 0
/- def AlsoCommented : Nat := 0 -/

theorem Prime.two_le : True := trivial

namespace Inner
/-- inner doc -/
protected noncomputable def foo.{u} : Nat := 0
end Inner

/-- root doc -/
def _root_.RootThing : Nat := 0

section Foo
structure Bar where
  x : Nat
end Foo

end Nat

/-- A monoid hom. -/
@[to_additive /-- An additive monoid hom. -/]
structure MulThing where

@[to_additive (attr := simp)
  /-- multi-line additive doc -/]
class inductive Kls : Type

def outside := 1
"""


class SplitCodeTest(unittest.TestCase):
    def test_removes_comments_and_keeps_docstrings(self):
        code, docs = split_code(LEAN)
        self.assertNotIn("Commented", code)
        self.assertNotIn("Module doc", code)
        self.assertIn("`Nat.Prime p` means that `p` is prime.", docs)

    def test_nested_block_comment(self):
        code, _ = split_code("/- a /- b -/ still comment -/ def x := 1")
        self.assertNotIn("still", code)
        self.assertIn("def x", code)

    def test_strings_are_blanked(self):
        code, _ = split_code('def s := "-- not a comment /- nor this"\ndef t := 1')
        self.assertIn("def t", code)


class ParseFileTest(unittest.TestCase):
    def setUp(self):
        decls, self.code, self.namespaces = parse_file(LEAN)
        self.decls = {d["name"]: d for d in decls}

    def test_namespace_prefix(self):
        self.assertIn("Nat.Prime", self.decls)
        self.assertIn("Nat.Prime.two_le", self.decls)
        self.assertIn("Nat.Bar", self.decls)
        self.assertIn("outside", self.decls)

    def test_nested_namespace_modifiers_and_universes(self):
        self.assertEqual(self.decls["Nat.Inner.foo"]["doc"], "inner doc")

    def test_root(self):
        self.assertEqual(self.decls["RootThing"]["doc"], "root doc")

    def test_docstring_attributes_and_wikidata(self):
        prime = self.decls["Nat.Prime"]
        self.assertEqual(prime["doc"], "`Nat.Prime p` means that `p` is prime.")
        self.assertEqual(prime["wikidata"], "Q49008")
        self.assertIsNone(self.decls["Nat.Prime.two_le"]["doc"])

    def test_to_additive_doc(self):
        self.assertEqual(
            self.decls["MulThing"]["additive_doc"], "An additive monoid hom."
        )
        self.assertEqual(self.decls["Kls"]["kind"], "class inductive")
        self.assertEqual(self.decls["Kls"]["additive_doc"], "multi-line additive doc")

    def test_commented_decls_ignored(self):
        self.assertNotIn("Nat.Commented", self.decls)
        self.assertNotIn("Nat.AlsoCommented", self.decls)

    def test_namespaces(self):
        self.assertEqual(self.namespaces, {"Nat", "Nat.Inner"})


class AdditiveNameTest(unittest.TestCase):
    def test_translation(self):
        self.assertEqual(additive_name("HasProd"), "HasSum")
        self.assertEqual(additive_name("MonoidHom.mul_comp"), "AddMonoidHom.add_comp")
        self.assertEqual(additive_name("Subgroup"), "AddSubgroup")
        self.assertEqual(additive_name("Multiset.card"), "Multiset.card")


def _u(module):
    return {"kind": "def", "module": module}


class ReferencesTest(unittest.TestCase):
    universe = {"Nat.Prime": _u("A"), "Group": _u("A"), "Foo.bar": _u("A")}

    def test_full_name_open_and_namespace(self):
        files = [
            ("A", "Nat.Prime Group", set()),  # own module: not counted
            ("B", "theorem x : Nat.Prime 2", set()),
            ("C", "theorem y : Prime 2", {"Nat"}),  # via open / namespace
            ("D", "theorem z : Prime 2", set()),  # unresolved short name
            ("E", "variable [Group G] (h : bar)", set()),
        ]
        refs = count_references(files, self.universe)
        self.assertEqual(refs, {"Nat.Prime": 2, "Group": 1})

    def test_build_index(self):
        universe = {"Nat.Prime": _u("A"), "Missing": _u("A")}
        index, stats = build_index(
            universe, [("A", LEAN), ("B", "open Nat\n#check Prime")]
        )
        self.assertTrue(index["Nat.Prime"]["found"])
        self.assertEqual(index["Nat.Prime"]["refs"], 1)
        self.assertFalse(index["Missing"]["found"])
        self.assertEqual(stats["coverage"], 0.5)


if __name__ == "__main__":
    unittest.main()
