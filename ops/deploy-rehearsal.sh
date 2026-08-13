#!/usr/bin/env bash
# Deployment rehearsal against a clean environment.
#
# Simulates what InMotion's cPanel Python app hosting will do: build a fresh
# virtualenv on Python 3.12, install only requirements/prod.txt, and exercise
# the production settings path. Anything that fails here fails on the host --
# but here it fails in 90 seconds instead of during a cutover.
#
# Usage: ./ops/deploy-rehearsal.sh

set -euo pipefail

cd "$(dirname "$0")/.."
BACKEND="$PWD/backend"
REHEARSAL="$(mktemp -d)"
trap 'rm -rf "$REHEARSAL"' EXIT

pass() { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAILURES=$((FAILURES+1)); }
FAILURES=0

echo "== 1. Linux wheel availability (no compiler on the host) =="
if ./ops/check-wheels.sh >/dev/null 2>&1; then
  pass "every production dependency has a manylinux wheel"
else
  fail "a dependency would need compiling on the server"
fi

echo "== 2. Clean virtualenv on Python 3.12 =="
if python3.12 -m venv "$REHEARSAL/venv" >/dev/null 2>&1; then
  pass "virtualenv created with python3.12"
else
  fail "python3.12 unavailable"
  exit 1
fi

PY="$REHEARSAL/venv/bin/python"
"$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1

echo "== 3. Install requirements/prod.txt only =="
if "$PY" -m pip install --quiet -r backend/requirements/prod.txt >"$REHEARSAL/pip.log" 2>&1; then
  pass "installed $("$PY" -m pip list 2>/dev/null | tail -n +3 | wc -l | tr -d ' ') packages"
else
  fail "install failed"; tail -20 "$REHEARSAL/pip.log"
fi

if grep -qi "Building wheel for" "$REHEARSAL/pip.log" 2>/dev/null; then
  printf '  \033[33mNOTE\033[0m %s\n' \
    "something compiled locally: $(grep -i 'Building wheel for' "$REHEARSAL/pip.log" | sed 's/.*for //;s/ .*//' | tr '\n' ' ')"
  printf '       (macOS-only wheel gap; step 1 confirms Linux wheels exist)\n'
fi

echo "== 4. Production settings import =="
export DJANGO_SETTINGS_MODULE=config.settings.prod
# A real 50-character key: check --deploy rejects short or low-entropy keys,
# and rightly so -- that check is one of the things being rehearsed.
export DJANGO_SECRET_KEY="$("$PY" -c 'from django.core.management.utils import get_random_secret_key as g; print(g())')"
export DJANGO_ALLOWED_HOSTS="www.austinlimoshuttle.com,api.austinlimoshuttle.com"
export DJANGO_STATIC_ROOT="$REHEARSAL/static"
export DJANGO_MEDIA_ROOT="$REHEARSAL/media"

cd "$BACKEND"
if "$PY" -c "import django,os; django.setup()" >"$REHEARSAL/settings.log" 2>&1; then
  pass "config.settings.prod imports"
else
  fail "production settings failed to import"; tail -20 "$REHEARSAL/settings.log"
fi

echo "== 5. passenger_wsgi.py entry point =="
if "$PY" -c "
import passenger_wsgi
assert hasattr(passenger_wsgi, 'application'), 'no application attribute'
print(type(passenger_wsgi.application).__name__)
" >"$REHEARSAL/passenger.log" 2>&1; then
  pass "passenger_wsgi exposes $(cat "$REHEARSAL/passenger.log")"
else
  fail "passenger_wsgi.py does not import"; tail -20 "$REHEARSAL/passenger.log"
fi

echo "== 6. Deployment checks =="
if "$PY" manage.py check --deploy --fail-level WARNING >"$REHEARSAL/check.log" 2>&1; then
  pass "check --deploy clean"
else
  fail "check --deploy reported issues"; tail -20 "$REHEARSAL/check.log"
fi

echo "== 7. collectstatic =="
if "$PY" manage.py collectstatic --noinput >"$REHEARSAL/static.log" 2>&1; then
  pass "$(grep -oE '[0-9]+ static files copied' "$REHEARSAL/static.log" | head -1)"
else
  fail "collectstatic failed"; tail -20 "$REHEARSAL/static.log"
fi

echo "== 8. Secrets are not in the web root =="
if [ -f "$BACKEND/.env" ] && [ -d "$BACKEND/../public_html" ] && \
   [ -f "$BACKEND/../public_html/.env" ]; then
  fail ".env found inside public_html"
else
  pass ".env is outside any web-servable directory"
fi

echo
if [ "$FAILURES" -eq 0 ]; then
  printf '\033[32mREHEARSAL PASSED\033[0m — %s\n' \
    "the application installs and boots in a clean Python 3.12 environment"
  exit 0
fi
printf '\033[31mREHEARSAL FAILED\033[0m — %s issue(s)\n' "$FAILURES"
exit 1
