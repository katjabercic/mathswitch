#!/bin/bash
# Categorize 1000 math Wikidata items with MathWorld ID, exclude MathWorld ID from prompt
cd "$(dirname "$0")/web" || exit 1

SESSION="1000MW_exclude_mwid-$(date +%Y%m%d)"

python manage.py categorize \
  --limit 1000 \
  --source Wd \
  --domain math \
  --has-mathworld-id \
  --session-name "$SESSION"
