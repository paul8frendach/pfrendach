#!/bin/bash
# Redeploy on PythonAnywhere after uploading a new bundle.
#
#   cd ~ && tar -xzf paulfrendach-deploy.tar.gz && bash ~/paulfrendach/deploy/update.sh
#
# Differs from bootstrap.sh in the ways that matter for a SECOND deploy:
#   - never touches .env (your live config, secret key and LAB key stay put)
#   - never re-seeds (seed_house is idempotent, but re-running it on every
#     deploy would overwrite copy you have since edited in the admin)
#   - always backs the database up first
set -euo pipefail
PROJECT=~/paulfrendach
VENV=~/.virtualenvs/paulfrendach
cd "$PROJECT"

echo "==> Backing up the database"
# The one thing here that cannot be rebuilt from the bundle: worlds, projects,
# milestones, bookings and enquiries all live in this file.
if [ -f db.sqlite3 ]; then
  cp db.sqlite3 "db-$(date +%F-%H%M).sqlite3"
  echo "    db-$(date +%F-%H%M).sqlite3"
fi

echo "==> Dependencies (only if requirements changed)"
"$VENV/bin/pip" install --quiet -r requirements.txt

echo "==> Migrations"
"$VENV/bin/python" manage.py migrate --noinput

echo "==> Static files"
# Must run on every CSS change. WhiteNoise's manifest storage hashes filenames,
# so without this the templates ask for a hash that is no longer on disk and
# the page ships with no stylesheet at all.
"$VENV/bin/python" manage.py collectstatic --noinput | tail -1

# ---------------------------------------------------------------- reload
#
# PythonAnywhere reloads a web app when its WSGI file is touched, so the
# deploy can do it rather than asking somebody to remember.
#
# This is not a convenience. collectstatic writes the new stylesheets where
# nginx serves them *immediately*, while the worker keeps the old templates
# in memory - and with DEBUG off Django's cached loader pins them there until
# a reload. Between the two you have new CSS driving old markup, which is a
# state nobody should ever be able to be in.
echo "==> Reloading the web app"
# Matched by CONTENT, not by name or by taking the first file. This account
# runs other web apps - findthe90, sunset-landing, debrief - and touching one
# of those would reload somebody else's site. The right file is the one that
# points at THIS project root, and only that one.
WSGI=$(grep -l -- "$PROJECT" /var/www/*_wsgi.py 2>/dev/null | head -1)
if [ -n "$WSGI" ]; then
  touch "$WSGI"
  echo "    touched $WSGI - the worker is picking up the new code now"
  RELOADED=1
else
  echo "    NO WSGI FILE FOUND under /var/www."
  echo "    Press Reload on the Web tab before doing anything else: until you"
  echo "    do, the new stylesheets are live but the old templates are not."
  RELOADED=0
fi

echo
if [ "$RELOADED" = "1" ]; then
  echo "Done, and reloaded. Give it a couple of seconds, then hard-refresh"
  echo "the browser once (Cmd+Shift+R) to clear anything it already cached."
else
  echo "Done - but NOT live until you press Reload on the Web tab."
fi
