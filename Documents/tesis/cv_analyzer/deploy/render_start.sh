#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
gunicorn cv_analyzer_project.wsgi:application \
  --bind 0.0.0.0:"${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
