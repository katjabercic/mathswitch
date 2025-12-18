# mathswitch

Infrastructure for relaying and exchanging mathematical concepts.

For a demonstration of a page with at least one link, see for example `{baseurl}/concept/Schwartz%20space/`.

## Notes on installation and usage

To prepare pyenv (`venv`) make sure to have `pyenv` installed, then run
```bash
make prepare-env
source venv/bin/activate
```

By default, the Mathswitch uses sqlite3 database, in order to use postgresql there is
a provided `.env.example` config and Docker compose to run the database:
```bash
docker compose up -d
```

To install all the necessary Python packages, run:

```bash
make prepare-web # Which does the necessary steps for env, db, superuser
# OR
pip install -r web/requirements.txt
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

Finally, to populate the database, run

```bash
python web/manage.py import_wikidata
# OR
make populate-db
```

  * In order to fetch wikipedia articles and extract keywords from them:
    ```bash
    make install-scispacy
    ```
    then configure your email `WIKIPEDIA_CONTACT_EMAIL` in [source_wikidata.py](web/slurper/source_wikidata.py)
    * This is needed
  * Then run the database population (make sure your db is cleared)



If you ever want to repopulate the database, you can clear it using

```bash
python web/manage.py clear_wikidata
```

### To run the categorizer
The categorizer is setup to work with several models, divided into free and paid.
All of them are run locally, so expect some performance hits. The models are downloaded when the categorizer is
ran initially, and by default the free models are used.

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

In order to contribute, install [Black](https://github.com/psf/black) and [isort](https://pycqa.github.io/isort/) autoformatters and [Flake8](https://flake8.pycqa.org/) linter.
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

## Instructions for Katja to update the live version
```bash
sudo systemctl stop mathswitch
cd mathswitch
git pull
source venv/bin/activate
cd web
./manage.py rebuild_db
sudo systemctl start mathswitch
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
