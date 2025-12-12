install:
	pip install -r requirements.txt

install-scispacy:
	pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

start:
	python ./web/manage.py runserver

compute-concepts:
	python ./web/manage.py compute_concepts

fix-files:
	python3 -m black .
	python3 -m isort .
	python3 -m flake8 .
