"""Run every filter on the candidate universe and write data/results.json."""

import argparse
import json
import random

import config
from filters import FILTERS
from filters.llm_judge import judge_all, load_cache
from ground_truth import load_ground_truth, split_by_universe
from universe import load_index, load_universe


def load_decls():
    universe = load_universe()
    with open(config.SOURCE_INDEX_JSON) as f:
        source = json.load(f)
    decls = {
        name: dict(info, **source["declarations"][name])
        for name, info in universe.items()
    }
    return decls, source["stats"]


def choose_llm_names(decls, ground_truth_names, sample, seed=config.LLM_SEED):
    """Ground-truth names first (to measure recall), then a fixed random sample."""
    rest = sorted(set(decls) - set(ground_truth_names))
    random.Random(seed).shuffle(rest)
    return sorted(ground_truth_names) + rest[:sample]


def apply_filters(decls, ctx, filters=FILTERS):
    return {
        name: {f: fn(name, decl, ctx) for f, fn in filters.items()}
        for name, decl in decls.items()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--llm-model", default=config.LLM_TYPE, help="LLMType enum name"
    )
    parser.add_argument("--llm-sample", type=int, default=config.LLM_SAMPLE)
    parser.add_argument(
        "--llm-all", action="store_true", help="judge the whole universe"
    )
    parser.add_argument(
        "--skip-llm", action="store_true", help="only use cached verdicts"
    )
    args = parser.parse_args()

    decls, stats = load_decls()
    all_declarations = load_index()["declarations"]
    ground_truth = {}
    for set_name, names in load_ground_truth().items():
        inside, other_kind, missing = split_by_universe(names, decls, all_declarations)
        ground_truth[set_name] = {
            "inside": sorted(inside),
            "labels": {n: names[n] for n in inside},
            "other_kind": len(other_kind),
            "missing": len(missing),
            "total": len(names),
        }
    gt_names = {n for g in ground_truth.values() for n in g["inside"]}

    if args.skip_llm:
        verdicts = {
            name: row["answer"]
            for (model, name), row in load_cache().items()
            if model == args.llm_model and name in decls
        }
    else:
        llm_names = (
            list(decls)
            if args.llm_all
            else choose_llm_names(decls, gt_names, args.llm_sample)
        )
        verdicts = judge_all(llm_names, decls, args.llm_model)
    ctx = {"llm": verdicts}

    results = apply_filters(decls, ctx)
    out = {
        "stats": stats,
        "llm_model": args.llm_model,
        "ground_truth": ground_truth,
        "decls": {
            name: {
                "kind": d["kind"],
                "module": d["module"],
                "url": d["url"],
                "found": d["found"],
                "doc": (d["doc"] or "")[:400],
                "refs": d["refs"],
                "wikidata": d["wikidata"],
                "filters": results[name],
            }
            for name, d in decls.items()
        },
    }
    with open(config.RESULTS_JSON, "w") as f:
        json.dump(out, f)
    for f_name in FILTERS:
        values = [r[f_name] for r in results.values() if r[f_name] is not None]
        print(f"{f_name:>10}: keeps {sum(values):>6} / {len(values)} evaluated")
    print(f"Wrote {config.RESULTS_JSON}")


if __name__ == "__main__":
    main()
