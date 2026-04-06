#!/bin/bash
# Categorize 500 Wikidata math items, fetch entity data, include external IDs
cd "$(dirname "$0")/web" || exit 1

SESSION="test-001-$(date +%Y%m%d)"

python manage.py categorize \
  --limit 500 \
  --source Wd \
  --domain math \
  --fetch \
  --session-name "$SESSION"
