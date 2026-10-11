"""Ground-truth concept lists shipped with mathlib4 in docs/*.yaml.

- overview.yaml / undergrad.yaml: nested topics whose leaves are Lean names.
- 100.yaml / 1000.yaml: numbered (or Wikidata-keyed) entries with `decl` or
  `decls`; these are mostly theorems, so few fall inside the candidate universe.
"""

import config
import yaml


def _leaves(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _leaves(value)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value)
    elif isinstance(node, str) and node.strip():
        yield node.strip()


def _entry_decls(data):
    """For 100/1000.yaml: yield (key, decl name)."""
    for key, entry in (data or {}).items():
        if not isinstance(entry, dict):
            continue
        if entry.get("decl"):
            yield str(key), str(entry["decl"]).strip()
        for decl in entry.get("decls") or []:
            yield str(key), str(decl).strip()


def parse_yaml(filename, text):
    """Return {lean name: label} for one ground-truth file."""
    data = yaml.safe_load(text)
    if filename in ("100.yaml", "1000.yaml"):
        return {decl: key for key, decl in _entry_decls(data)}
    return {name: filename.removesuffix(".yaml") for name in _leaves(data)}


def load_ground_truth(docs_dir=config.MATHLIB_DIR / "docs"):
    """Return {set name: {lean name: label}} (label = entry key, e.g. a QID)."""
    sets = {}
    for filename in config.GROUND_TRUTH_FILES:
        path = docs_dir / filename
        if path.exists():
            sets[filename.removesuffix(".yaml")] = parse_yaml(
                filename, path.read_text(encoding="utf-8")
            )
    return sets


def split_by_universe(names, universe, all_declarations):
    """Split ground-truth names into (in universe, other kind, not found)."""
    inside, other_kind, missing = [], [], []
    for name in names:
        if name in universe:
            inside.append(name)
        elif name in all_declarations:
            other_kind.append(name)
        else:
            missing.append(name)
    return inside, other_kind, missing
