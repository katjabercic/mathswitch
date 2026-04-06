#!/bin/bash
# Categorize 500 Wikidata math items, no fetch, no external IDs
cd "$(dirname "$0")/web" || exit 1

SESSION="test-002-$(date +%Y%m%d)"

python manage.py categorize \
  --limit 500 \
  --source Wd \
  --domain math \
  --session-name "$SESSION"
