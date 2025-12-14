prepare-web:
	pip install -r web/requirements.txt
	cp web/.env.example web/.env
	python ./web/manage.py migrate
	python ./web/manage.py createsuperuser

install-dev:
	pip install -r requirements.txt

install-scispacy:
	pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

start:
	python ./web/manage.py runserver

populate-db:
	python ./web/manage.py import_wikidata

clear-db:
	python ./web/manage.py clear_wikidata

compute-concepts:
	python ./web/manage.py compute_concepts

categorize:
	python ./web/manage.py categorize --limit 10

fix-files:
	pip install -r requirements.txt
	python3 -m black .
	python3 -m isort .
	python3 -m flake8 .
