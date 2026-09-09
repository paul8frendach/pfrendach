#!/bin/bash
# Build the deploy bundle on the Mac. Run: bash deploy/make-bundle.sh
#
# There is no git remote for this project, so the bundle IS the delivery
# mechanism: upload it through the PythonAnywhere Files tab and unpack it.
#
# COPYFILE_DISABLE / --no-xattrs stop macOS attaching provenance and quarantine
# attributes that GNU tar cannot read - without them every extraction on the
# server prints one warning per file and buries the output that matters.
set -euo pipefail
OUT="${1:-$HOME/Desktop/paulfrendach-deploy.tar.gz}"
cd "$HOME/Desktop"
COPYFILE_DISABLE=1 tar --no-xattrs \
  --exclude='.venv' --exclude='__pycache__' --exclude='staticfiles' \
  --exclude='db.sqlite3' --exclude='db-*.sqlite3' --exclude='.git' \
  --exclude='.DS_Store' --exclude='media' \
  --exclude='paulfrendach/.env' \
  -czf "$OUT" paulfrendach

# The local .env holds a LIVE LAB key. Excluded above, and checked here rather
# than trusted: a bundle that carries it would put a working credential in a
# file that gets emailed, uploaded and left in Downloads folders.
if tar -tzf "$OUT" | grep -qE '(^|/)paulfrendach/\.env$'; then
  echo "REFUSING: the bundle contains .env, which holds a live LAB key." >&2
  rm -f "$OUT"
  exit 1
fi
echo "no .env in the bundle - checked, not assumed"
ls -lh "$OUT"
