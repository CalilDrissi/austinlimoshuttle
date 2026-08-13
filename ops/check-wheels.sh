#!/usr/bin/env bash
# Verify every production dependency installs from a pre-built Linux wheel.
#
# The InMotion shared host has no C compiler and no development headers, so a
# package that only ships an sdist will fail at deploy time -- long after it was
# added. Run this after ANY change to requirements/base.txt.
#
# Note: a package may build from source on macOS while still having a perfectly
# good manylinux wheel. Only the Linux answer matters here.

set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PY:-backend/.venv/bin/python}"
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

echo "==> resolving requirements/prod.txt for manylinux2014 / cp312"
if "$PY" -m pip download -r backend/requirements/prod.txt \
      --dest "$OUT" \
      --only-binary=:all: \
      --platform manylinux2014_x86_64 \
      --python-version 3.12 \
      --implementation cp \
      >"$OUT/.log" 2>&1; then
  echo "OK: all $(find "$OUT" -name '*.whl' | wc -l | tr -d ' ') packages available as Linux wheels"
else
  echo "FAIL: at least one dependency has no Linux wheel and would need compiling." >&2
  echo "----- pip output -----" >&2
  tail -25 "$OUT/.log" >&2
  exit 1
fi
