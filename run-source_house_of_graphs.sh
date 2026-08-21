#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/web"
source ../venv/bin/activate
export DJANGO_SETTINGS_MODULE=web.settings

python - <<'PY'
import django

django.setup()

from slurper.source_house_of_graphs import HOG_SLURPER

HOG_SLURPER.save_items()
PY
