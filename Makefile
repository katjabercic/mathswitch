VENV_DIR := venv

prepare-venv:
	@command -v pyenv >/dev/null 2>&1 || { echo "pyenv not installed"; exit 1; }
	pyenv install -s
	python -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	@echo "In order to use venv python, please run 'source venv/bin/activate', then install dependencies by running \
	'make install-dev'."

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

import-wikidata:
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

create-migrations:
	python ./web/manage.py makemigrations

migrate:
	python ./web/manage.py migrate

import-lmfdb:
	python ./web/manage.py import_lmfdb

import-house-of-graphs:
	python ./web/manage.py import_house_of_graphs

import-oeis:
	python ./web/manage.py import_oeis

# Docker (full app stack: postgres + gunicorn + nginx)
# Build without torch / the scispaCy model with e.g. `make docker-build WITH_TORCH=false`.

DOCKER_COMPOSE := docker compose --profile app

docker-build:
	WITH_TORCH=$(or $(WITH_TORCH),true) WITH_SCISPACY_MODEL=$(or $(WITH_SCISPACY_MODEL),true) $(DOCKER_COMPOSE) build

docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-logs:
	$(DOCKER_COMPOSE) logs -f

docker-createsuperuser:
	$(DOCKER_COMPOSE) exec web python manage.py createsuperuser

docker-rebuild-db:
	$(DOCKER_COMPOSE) exec web python manage.py rebuild_db
