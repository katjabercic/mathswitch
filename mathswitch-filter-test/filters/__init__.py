"""Filter registry.

Each filter is `fn(name, decl, ctx) -> bool | None` where `decl` is the
universe entry merged with the source index entry ({kind, module, url, found,
doc, refs, wikidata}) and `ctx` holds run-wide data (e.g. LLM verdicts).
True means "this is a mathematical concept", None means "not evaluated".
"""

from filters.docstring import docstring_filter
from filters.kind import kind_filter
from filters.llm_judge import llm_filter
from filters.namespace import namespace_filter
from filters.references import references_filter

FILTERS = {
    "docstring": docstring_filter,
    "namespace": namespace_filter,
    "references": references_filter,
    "kind": kind_filter,
    "llm": llm_filter,
}

DESCRIPTIONS = {
    "docstring": "Has a non-trivial docstring in the source",
    "namespace": "Not in a Tactic/Util/Init/Meta/... module or namespace",
    "references": "Mentioned by many other source files",
    "kind": "Is a structure, class or inductive",
    "llm": "Local LLM judges name + docstring a recognisable concept",
}
