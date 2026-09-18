#!/usr/bin/env bash
# Full local check suite, in the order that fails fastest and cheapest first.
# Run before pushing; the pre-push hook in .claude/githooks also runs this
# automatically (warn-only) if it finds this file.
#
# Bare `python` resolves to the Microsoft Store alias on the Alienware and
# fails, so this script prefers a project venv over $PATH. CI has no venv,
# so it falls through to python3/python there.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  PYTHON="python"
fi

echo "== pytest =="
"$PYTHON" -m pytest tests/ -q

echo "== pyflakes =="
"$PYTHON" -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py

echo "== vault schema =="
"$PYTHON" tools/validate_vault_schema.py

echo "== roadmap =="
"$PYTHON" tools/roadmap.py --check

echo "== build (--no-sort) =="
"$PYTHON" build.py --no-sort

echo "verify.sh: all checks passed"
