#!/bin/bash
# Fetch missing Wikidata metadata for all items, processing in pages of 100
cd "$(dirname "$0")/web" || exit 1

python manage.py fetch_metadata
