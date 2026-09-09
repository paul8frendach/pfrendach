#!/bin/bash
# One-shot first deploy on PythonAnywhere.
#
# Run from a Bash console:   bash ~/paulfrendach/deploy/bootstrap.sh
#
# Safe to run twice: the virtualenv, the migrations and collectstatic are all
# idempotent, and it refuses to overwrite an existing .env.
set -euo pipefail

PROJECT=~/paulfrendach
VENV=~/.virtualenvs/paulfrendach
PYTHON=/usr/bin/python3.12

echo "==> Python"
"$PYTHON" -V

echo "==> Virtualenv"
if [ ! -d "$VENV" ]; then
  "$PYTHON" -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$PROJECT/requirements.txt"
echo "    $("$VENV/bin/python" -c 'import django; print("Django", django.get_version())')"

echo "==> Environment"
if [ -f "$PROJECT/.env" ]; then
  echo "    .env already exists - leaving it alone."
else
  cp "$PROJECT/deploy/env.production.example" "$PROJECT/.env"
  echo "    .env written from the example. EDIT IT before reloading:"
  echo "    DJANGO_SECRET_KEY and LAB_API_KEY are both REPLACE_ME."
fi

cd "$PROJECT"

echo "==> Database"
# SQLite lives beside the code. Back it up before every migrate - cheap, and
# the one thing that cannot be rebuilt from the repo.
if [ -f db.sqlite3 ]; then
  cp db.sqlite3 "db-$(date +%F-%H%M).sqlite3"
  echo "    backed up existing database"
fi
"$VENV/bin/python" manage.py migrate --noinput

echo "==> Static files"
"$VENV/bin/python" manage.py collectstatic --noinput | tail -1

echo "==> Seed the house (idempotent)"
# Worlds, site config and the chrome's tab rail come from the database. Without
# this the three tabs do not exist and every page renders an empty nav.
"$VENV/bin/python" manage.py seed_house

echo
echo "==> Checks"
"$VENV/bin/python" manage.py check --deploy 2>&1 | tail -8

cat <<'DONE'

-------------------------------------------------------------------
Bootstrap finished.

EDIT ~/paulfrendach/.env FIRST if it was just created - the secret key
and the LAB key are placeholders, and the app refuses to start without
a real secret key.

Then, on the Web tab:

  1. WSGI configuration file -> replace ALL of it with the contents of
     ~/paulfrendach/deploy/pythonanywhere_wsgi.py

  2. Virtualenv  ->  /home/pfrendach8/.virtualenvs/paulfrendach
     Source code ->  /home/pfrendach8/paulfrendach

     Static files:
       /static/   ->  /home/pfrendach8/paulfrendach/staticfiles
       /media/    ->  /home/pfrendach8/paulfrendach/media

  3. Press Reload.

Admin login, if you want one:
  ~/.virtualenvs/paulfrendach/bin/python ~/paulfrendach/manage.py createsuperuser
-------------------------------------------------------------------
DONE
