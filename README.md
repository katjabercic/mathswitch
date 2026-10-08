# mathswitch

Infrastructure for relaying and exchanging mathematical concepts.

For a demonstration of a page with at least one link, see for example `{baseurl}/concept/Schwartz%20space/`.

## Notes on installation and usage

To prepare pyenv (`venv`) make sure to have `pyenv` installed, then run
```bash
make prepare-venv
source venv/bin/activate
```

By default, the Mathswitch uses sqlite3 database, in order to use postgresql there is
a provided `.env.example` config and Docker compose to run the database:
```bash
docker compose up -d
```

Dependencies are split into groups in [pyproject.toml](pyproject.toml) (`[dependency-groups]`, PEP 735),
so that you only install what you need. Installing a group needs pip >= 25.1 (`make prepare-venv` upgrades pip).

| Group | What it is for | Install |
|---|---|---|
| `prod` | bare minimum to run the web app | `make install-prod` |
| `slurper` | populating the database (`import_*` commands, spaCy keywords, LMFDB) | `make install-slurper` |
| `categorizer` | LLM categorizer with local models (torch, transformers, ...) and classifier evaluation | `make install-categorizer` |
| `categorizer-paid` | optional OpenAI / Anthropic clients for the categorizer | `make install-categorizer-paid` |
| `dev` | linters, formatters and test dependencies | `make install-dev` |

`make install-all` installs everything except the paid APIs. You can also install groups directly,
e.g. `pip install --group prod --group slurper`, or with uv: `uv sync --group slurper`.

To install the web app, run:

```bash
make prepare-web # Which does the necessary steps for env, db, superuser
# OR
make install-prod
```

Prepare an environment:
```bash
cp web/.env.example web/.env
```

Next, to create a database, run:

```bash
python web/manage.py migrate
```

In order to use the administrative interface, you need to create an admin user:

```bash
python web/manage.py createsuperuser
```

Finally, populate the database.
  * In order to fetch wikipedia articles and extract keywords from them, install the slurper
    dependencies (this also downloads the scispacy model):
    ```bash
    make install-slurper
    ```
    then configure your email `MATHSWITCH_CONTACT_EMAIL` in [.env](web/.env)
    * This is needed
  * Then run the database population (make sure your db is cleared)

 To populate the database run

```bash
python web/manage.py import_wikidata
# OR
make populate-db
```



If you ever want to repopulate the database, you can clear it using

```bash
python web/manage.py clear_wikidata
```

### To run the categorizer
The categorizer is setup to work with several models, divided into free and paid.
All of them are run locally, so expect some performance hits. The models are downloaded when the categorizer is
ran initially, and by default the free models are used.

Install its dependencies first:
```bash
make install-categorizer
```
If you don't need a GPU, the CPU-only torch wheels are much smaller. Install them before the group:
```bash
pip install torch~=2.9.0 --index-url https://download.pytorch.org/whl/cpu
```

The database needs to be filled in before running it, so:
```bash
make populate-db
```
then
```bash
make categorize
```

There are some known existing issues that have some inline fixes, such as `gpt2` getting stuck
and returning the same prompt, then few times `---\n\n\n---`.

For more details see [categorizer readme](web/categorizer/README.md).

## Notes for developers

In order to contribute, install [Black](https://github.com/psf/black) and [isort](https://pycqa.github.io/isort/) autoformatters and [Flake8](https://flake8.pycqa.org/) linter (together with everything needed to run the tests).
```bash
make install-dev
```

You can run all three with
```bash
make fix-files
# Or manually
isort .
black .
flake8
```

or set up a Git pre-commit hook by creating `.git/hooks/pre-commit` with the following contents:

```bash
#!/bin/bash

black . && isort . && flake8
```

Each time after you change a model, make sure to create the appropriate migrations:
```bash
python web/manage.py makemigrations
# OR
make create-migrations
```

To update the database with the new model, run:
```bash
python web/manage.py migrate
# OR
make migrate
```

## WD item JSON example

```json
{
    "item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q192276"}, 
    "art": {"type": "uri", "value": "https://en.wikipedia.org/wiki/Measure_(mathematics)"}, 
    "image": {"type": "uri", "value": "http://commons.wikimedia.org/wiki/Special:FilePath/Measure%20illustration%20%28Vector%29.svg"}, 
    "mwID": {"type": "literal", "value": "Measure"}, 
    "itemLabel": {"xml:lang": "en", "type": "literal", "value": "measure"}, 
    "itemDescription": {"xml:lang": "en", "type": "literal", "value": "function assigning numbers to some subsets of a set, which could be seen as a generalization of length, area, volume and integral"}, 
    "eomID": {"type": "literal", "value": "measure"}, 
    "pwID": {"type": "literal", "value": "Definition:Measure_(Measure_Theory)"}
}
```

## WD query examples

### Query example from the paper

```
SELECT DISTINCT
  ?item ?label ?desc ?image ?wp_en ?nlab ?mw ?pw ?eom
  (GROUP_CONCAT(DISTINCT ?alt; separator=", ") AS ?aliases)
WHERE {
  # Property path: instances of a topic
  # studied by mathematics
  ?item  wdt:P31   ?topic .
  ?topic wdt:P2579 wd:Q395 .
  # External identifiers (optional)
  OPTIONAL { ?item wdt:P4215 ?nlab . }
  OPTIONAL { ?item wdt:P2812 ?mw   . }
  OPTIONAL { ?item wdt:P6781 ?pw   . }
  OPTIONAL { ?item wdt:P7554 ?eom  . }
  # Image and Wikipedia article (optional)
  OPTIONAL { ?item wdt:P18 ?image . }
  OPTIONAL {
    ?wp_en rdf:type schema:Article ;
           schema:isPartOf
             <https://en.wikipedia.org/> ;
           schema:about ?item .
  }
  # Aliases
  OPTIONAL {
    ?item skos:altLabel ?alt .
    FILTER (lang(?alt) = "en")
  }
  # Exclusions
  FILTER NOT EXISTS {
    VALUES ?excludedType {
      wd:Q21199 wd:Q28920044
      wd:Q6256  wd:Q714737
    }
    ?item wdt:P31 ?excludedType .
  }
  FILTER NOT EXISTS { ?item wdt:P31 wd:Q5 . }
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
GROUP BY ?item ?label ?desc ?image ?wp_en ?nlab ?mw ?pw ?eom
ORDER BY ?item
LIMIT 1000 OFFSET 0
```

### Other examples

```
  ?item ?image
  ?item_EN ?item_desc_EN
  ?item_NL ?item_desc_NL
  ?item_SI ?item_desc_SI
  ?mathworldID ?encyclopediaofmathematicsID ?nlabID ?proofwikiID
WHERE {
  # anything part of a topic that is studied by mathmatics!
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .
  OPTIONAL
  { ?item wdt:P18 ?image . }
  OPTIONAL
  { ?item wdt:P2812 ?mathworldID . }
  OPTIONAL
  { ?item wdt:7554 ?encyclopediaofmathematicsID . }
  OPTIONAL
  { ?item wdt:4215 ?nlabID . }
  OPTIONAL
  { ?item wdt:6781 ?proofwikiID . }
  
  # except for natural numbers
  filter(?topic != wd:Q21199) .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en".
    ?item rdfs:label ?item_EN.
    ?item schema:description ?item_desc_EN.
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "nl".
    ?item rdfs:label ?item_NL.
    ?item schema:description ?item_desc_NL.
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "si".
    ?item rdfs:label ?item_SI.
    ?item schema:description ?item_desc_SI.
  }
}
```

```
SELECT ?art WHERE {
  # an article in the english wikipedia with a corresponding wikidata entry
  ?art rdf:type schema:Article;
       schema:isPartOf <https://en.wikipedia.org/>;
       schema:about ?entry .

  # anything part of a topic that is studied by mathmatics!
  ?entry wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .

  # except for natural numbers
  filter(?topic != wd:Q21199) .
}
```

```
SELECT ?itemLabel ?descriptionLabel ?areaLabel ?mathworld
WHERE
{
  BIND(wd:Q11518 AS ?item)
  ?item schema:description ?description.
  ?item wdt:P361 ?area.
  ?item wdt:P2812 ?mathworld.
#  wdt:P2812 wdt:1630 ?mathworld_formatter
  FILTER(LANG(?description) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
}
```
