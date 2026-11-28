# mathswitch

Django app that collects mathematical concepts from external sources (Wikidata,
nLab, agda-unimath, LMFDB, House of Graphs, OEIS, …), links items that describe
the same thing, and groups them into concepts shown on a web UI.

## Stack

- Python 3.12 (pyenv, `.python-version`), virtualenv in `venv/`
- Django 4.2, config via `python-decouple` from `web/.env` (copy `web/.env.example`)
- SQLite by default (`web/db.sqlite3`); Postgres when `USE_POSTGRES=True` and the
  `POSTGRES_*` vars are set (`docker compose up -d` starts one)
- Optional: scispacy (keyword extraction), HuggingFace/Ollama/OpenAI/Anthropic
  (categorizer)

## Layout

The Django project lives in `web/`; run `manage.py` from the repo root as
`python web/manage.py …` or from `web/`.

- `web/concepts/` – core models (`Item`, `Link`, `Concept`, `Domain`), views,
  templates, `compute_concepts` / `link_same` commands
- `web/slurper/` – one `source_<name>.py` per external source plus
  `import_<name>` / `clear_<name>` management commands; `SlurperRun` throttles
  slow sources (7-day interval, bypass with `--force`)
- `web/categorizer/` – LLM-based categorization of items (see its README)
- `web/web/` – settings, urls, `rebuild_db` command (clears and reimports everything)
- `experiments/` – scratch scripts, not linted, not part of the app

Data flow: `import_*` creates `Item`s (unique on `source` + `identifier`) and
`Link`s → `link_same` links items with equal names → `compute_concepts`
groups linked items (union-find) into `Concept`s.

## Commands

```bash
source venv/bin/activate          # always use the venv
make install-dev                  # dev tools + web/requirements.txt
make migrate                      # apply migrations
make create-migrations            # after any model change
make start                        # runserver
cd web && python manage.py test   # tests (what CI runs)
make fix-files                    # black + isort + flake8
```

CI (`.github/workflows/test.yml`) runs `black --check .`, `isort --check .`,
`flake8` and the Django tests. All four must pass.

## Code style

- Format with black, sort imports with isort (`profile = "black"`), max line
  length 88. Migrations, `settings.py`, `venv/` and `experiments/` are excluded.
- Keep logic out of management commands: a command parses arguments and calls
  a service/slurper (e.g. `import_oeis` → `source_oeis.OEIS_SLURPER.save_items`).
- Data access logic goes on models/querysets (`ItemQuerySet`, `LinkQuerySet`),
  external API calls go in `source_*.py` / `*_service.py`, views stay thin.
- Use `logging`, not `print`, in library code.
- New settings go through `decouple.config(...)` in `web/web/settings.py` with a
  sensible default, and get documented in `web/.env.example`.

## Adding a new source

1. Add a value to `Item.Source` and to the ordering list in `Item.Source.key()`
   in `web/concepts/models.py`, then `make create-migrations`.
2. Add `web/slurper/source_<name>.py` with a slurper class exposing
   `save_items(force=False)`.
3. Add `import_<name>.py` and `clear_<name>.py` commands, a Makefile target,
   and a step in `rebuild_db`.
4. Add tests in `web/slurper/tests.py` that mock HTTP – tests must not hit the
   network.

## Gotchas

- Never commit `web/.env`, `*.sqlite3` or `web/classifier_reports/`.
- Don't edit existing migrations; create new ones. If two branches both add a
  migration, create a merge migration (`makemigrations --merge`).
- External sources are slow and rate-limited; when testing an import manually,
  limit the number of records instead of running a full import.
- Wikidata and OEIS requests send `MATHSWITCH_CONTACT_EMAIL` (from `web/.env`)
  in the User-Agent; set it before running those imports.
