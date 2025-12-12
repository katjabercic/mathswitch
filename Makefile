install:
	pip install -r requirements.txt

start:
	python ./web/manage.py runserver

compute-concepts:
	python ./web/manage.py compute_concepts
