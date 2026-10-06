"""LLM judge: "is this a recognisable mathematical concept?".

Uses the local models in web/categorizer/llm_service.py (Ollama/HuggingFace).
Verdicts are computed up front by `judge_all` (cached in data/llm_cache.jsonl,
so interrupted runs resume) and looked up by `llm_filter`.
"""

import json
import logging
import sys

import config

sys.path.insert(0, str(config.WEB_DIR))

from categorizer.result_parsers import parse_categorization_result  # noqa: E402

MAX_FAILURES_BEFORE_SUCCESS = 5

PROMPT = """You are judging declarations from Mathlib, the Lean 4 mathematics library.
Many declarations are formalization plumbing (helper constructions, coercions,
instance glue, tactic internals) rather than mathematical concepts.

Question: is the declaration below a recognisable mathematical concept, i.e.
something a mathematician would name and could find in a textbook or on
Wikipedia (e.g. "prime number", "group", "measure", "Lie algebra")?

Name: {name}
Kind: {kind}
Module: {module}
Docstring: {doc}

Answer with exactly "yes,<confidence>" or "no,<confidence>" where confidence is
0-100, and nothing else."""


def build_prompt(name, decl):
    doc = " ".join((decl.get("doc") or "(none)").split())[: config.LLM_DOC_CHARS]
    return PROMPT.format(name=name, kind=decl["kind"], module=decl["module"], doc=doc)


def parse_answer(raw):
    """Parse a model answer into {"answer": bool, "confidence": int|None} or None."""
    text = raw.strip()
    if "</think>" in text:  # deepseek-r1 style reasoning
        text = text.rsplit("</think>", 1)[1].strip()
    text = text.strip("`\"' .").splitlines()[0] if text else text
    try:
        return parse_categorization_result(text)
    except ValueError:
        low = text.lower()
        if low.startswith("yes"):
            return {"answer": True, "confidence": None}
        if low.startswith("no"):
            return {"answer": False, "confidence": None}
        return None


def load_cache(path=config.LLM_CACHE):
    cache = {}
    if path.exists():
        with open(path) as f:
            for line in f:
                row = json.loads(line)
                cache[(row["model"], row["name"])] = row
    return cache


def judge_all(
    names, decls, llm_type_name=config.LLM_TYPE, call=None, path=config.LLM_CACHE
):
    """Judge every name (skipping cached ones); return {name: bool | None}.

    `call(prompt) -> str` defaults to LLMService().call_llm with `llm_type_name`.
    """
    if call is None:
        from categorizer.llm_service import LLMService, LLMType

        service = LLMService()
        llm_type = LLMType[llm_type_name]

        def call(prompt):
            return service.call_llm(llm_type, prompt)

    cache = load_cache(path)
    todo = [n for n in names if (llm_type_name, n) not in cache]
    if todo:
        print(
            f"LLM judge ({llm_type_name}): {len(todo)} to judge, "
            f"{len(names) - len(todo)} cached"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    failures = succeeded = 0
    with open(path, "a") as f:
        for i, name in enumerate(todo, 1):
            try:
                raw = call(build_prompt(name, decls[name]))
            except Exception as e:  # keep going; failed items stay unjudged
                logging.error(f"LLM call failed for {name}: {e}")
                failures += 1
                if failures == MAX_FAILURES_BEFORE_SUCCESS and not succeeded:
                    raise RuntimeError(
                        f"First {failures} LLM calls failed; is the model running?"
                    ) from e
                continue
            succeeded += 1
            parsed = parse_answer(raw)
            row = {
                "model": llm_type_name,
                "name": name,
                "raw": raw,
                "answer": parsed["answer"] if parsed else None,
                "confidence": parsed["confidence"] if parsed else None,
            }
            cache[(llm_type_name, name)] = row
            f.write(json.dumps(row) + "\n")
            f.flush()
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}")
    return {
        n: cache[(llm_type_name, n)]["answer"]
        for n in names
        if (llm_type_name, n) in cache
    }


def llm_filter(name, decl, ctx):
    return ctx.get("llm", {}).get(name)
