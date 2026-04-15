#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/web"

python manage.py physics_control \
    --session "test-003-20260407"
