#!/bin/bash
# Categorize 2500 math Wikidata items without MathWorld ID
cd "$(dirname "$0")/web" || exit 1

SESSION="2500_no_mwid-$(date +%Y%m%d)"

python manage.py categorize \
  --limit 2500 \
  --source Wd \
  --domain math \
  --no-mathworld-id \
  --session-name "$SESSION"
