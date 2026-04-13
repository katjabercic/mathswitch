#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/web"

python manage.py evaluate_classifier \
    --tp-session "1000MW_include_mwid-20260409" \
    --obs-session "1000MW_exclude_mwid-20260409" \
    --results-session "2500_no_mwid-20260409" \
    --results-limit 1500 \
    --threshold 50 \
    --output-dir ./classifier_reports/
