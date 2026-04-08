#!/bin/bash
# Count Wikidata items that have metadata but no MathWorld ID
cd "$(dirname "$0")/web" || exit 1

python manage.py fetch_metadata --no-mathworld-id
