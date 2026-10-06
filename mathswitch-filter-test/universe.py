"""Candidate universe: the declarations every filter is evaluated on.

Uses the same package/kind rule as web/slurper/source_mathlib.py (copied here so
the experiment does not need a configured Django environment).
"""

import json

import config


def package_of(info) -> str:
    # "./Mathlib/Data/Nat/Prime/Defs.html#Nat.Prime" -> "Mathlib"
    return info["docLink"].removeprefix("./").split("/", 1)[0].split(".", 1)[0]


def module_of(info) -> str:
    # "./Mathlib/Data/Nat/Prime/Defs.html#Nat.Prime" -> "Mathlib/Data/Nat/Prime/Defs"
    return info["docLink"].removeprefix("./").split("#", 1)[0].removesuffix(".html")


def doc_url(info) -> str:
    return config.DOCS_URL + info["docLink"].removeprefix("./")


def is_candidate(info) -> bool:
    return (
        package_of(info) in config.UNIVERSE_PACKAGES
        and info["kind"] in config.UNIVERSE_KINDS
    )


def load_index(path=config.DECLARATIONS_JSON) -> dict:
    with open(path) as f:
        return json.load(f)


def load_universe(path=config.DECLARATIONS_JSON) -> dict:
    """Return {name: {"kind", "module", "url"}} for every candidate declaration."""
    declarations = load_index(path)["declarations"]
    return {
        name: {"kind": info["kind"], "module": module_of(info), "url": doc_url(info)}
        for name, info in declarations.items()
        if is_candidate(info)
    }
