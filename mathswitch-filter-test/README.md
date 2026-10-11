# Mathlib concept-filter test

Most Mathlib declarations are formalization plumbing, not mathematical concepts.
This experiment runs each candidate filter from the issue **on its own** and
builds an HTML report that compares what each filter keeps or drops.

The candidate universe is the production slurper's default
(`web/slurper/source_mathlib.py`): Mathlib `def` / `structure` / `class` /
`inductive` declarations from `mathlib-declarations.json` at the repo root,
about 48k of them.

## Filters

| name | keeps a declaration if |
|---|---|
| `docstring` | its source docstring has at least `MIN_DOC_LEN` chars and does more than restate the name |
| `namespace` | it is not in a `Tactic`/`Util`/`Init`/`Meta`/... module and has no internal name component (`_aux`, `proof_1`, `«term…»`, ...) |
| `references` | at least `REF_MIN` *other* source files mention it |
| `kind` | it is a `structure`, `class` or `inductive` |
| `llm` | a local LLM says the name + docstring is a recognisable mathematical concept |

All thresholds and blocklists are in `config.py`.

## Ground truth

mathlib4 ships lists of named concepts that map to Lean names:
`docs/overview.yaml`, `undergrad.yaml`, `100.yaml` and `1000.yaml`. The report
gives each filter's recall on these lists. Most `100`/`1000` entries are
theorems, so only a few of them fall inside the universe.

## Running

From this folder, using the repo venv:

```sh
python fetch_source.py        # shallow clone of mathlib4 into data/ (~150 MB)
python parse_source.py        # docstrings + reference counts -> data/source_index.json
python run_filters.py         # all filters -> data/results.json (runs the LLM, see below)
python run_filters.py --skip-llm   # only use LLM verdicts already cached
python report.py              # -> report/index.html
python -m unittest            # tests
```

### LLM judge

This filter uses `web/categorizer/llm_service.py`. The default model is
`OLLAMA_QWEN25_7B`; choose another with `--llm-model <LLMType name>`. Before
running it:

```sh
ollama pull qwen2.5:7b && ollama serve
```

By default it judges every ground-truth concept plus a fixed random sample of
`--llm-sample 2000` other declarations. `--llm-all` judges the whole universe,
which takes many hours on a local 7B model.

Verdicts are cached in `data/llm_cache.jsonl`, so a run can be interrupted and
resumed. Pairs that involve the LLM are compared only on the judged subset.

## Known limitations of the source parser

The parser works with regexes; it does not elaborate Lean.

- About 84% of the universe is matched to a source declaration. The report
  shows this coverage.
- Unmatched names are mostly generated declarations: parent projections
  (`Foo.toBar`), structure fields, notation, and `to_additive` copies whose
  name the heuristic in `additive_name` cannot guess. They have no docstring
  here, so the `docstring` filter rejects them.
- References are code tokens resolved through the full name, or through a
  namespace the file `open`s or is inside. Dot notation (`hp.two_le`) is not
  resolved, and mentions inside docstrings are not counted.
