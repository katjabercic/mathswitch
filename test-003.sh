#!/bin/bash
# Categorize 500 Wikidata physics items
cd "$(dirname "$0")/web" || exit 1

SESSION="test-003-$(date +%Y%m%d)"

python manage.py categorize \
  --limit 500 \
  --source Wd \
  --domain phys \
  --session-name "$SESSION"
