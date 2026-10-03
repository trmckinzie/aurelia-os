#!/usr/bin/env bash
# Full local check suite, in the order that fails fastest and cheapest first.
# Run before pushing; the pre-push hook in .claude/githooks also runs this
# automatically (warn-only) if it finds this file.
#
# Bare `python` resolves to the Microsoft Store alias on the Alienware and
# fails, so this script prefers a project venv over $PATH. A worktree under
# .claude/worktrees/ has no venv of its own and borrows the main checkout's.
# CI has neither, so it falls through to python3/python there.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# The main checkout is the parent of git's common directory: $ROOT itself in
# the main checkout and in CI, somewhere else in a linked worktree.
MAIN="$ROOT"
common="$(git rev-parse --git-common-dir 2>/dev/null || true)"
if [ -n "$common" ]; then
  MAIN="$(cd "$common/.." 2>/dev/null && pwd || echo "$ROOT")"
fi

if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif [ -x "$MAIN/.venv/Scripts/python.exe" ]; then
  PYTHON="$MAIN/.venv/Scripts/python.exe"
elif [ -x "$MAIN/.venv/bin/python" ]; then
  PYTHON="$MAIN/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  PYTHON="python"
fi

# The dev root's git hooks, its secret check among them, are wired through a
# relative core.hooksPath that git resolves from each worktree's own top level,
# so from the wrong depth they silently never run. Warn at the start and again
# at exit, never fail: CI sets no hooksPath, and this must not block a run.
hooks="$(git config --type=path --get core.hooksPath 2>/dev/null || true)"
if [ -n "$hooks" ]; then
  case "$hooks" in
    /*|[A-Za-z]:*) hooks_dir="$hooks" ;;
    *) hooks_dir="$ROOT/$hooks" ;;
  esac
  if [ ! -f "$hooks_dir/pre-commit" ]; then
    HOOKS_WARNING="WARNING: git hooks do not resolve from this worktree (core.hooksPath is $hooks), so commits made here skip the secret check. See docs/MOVING-MACHINES.md."
    echo "$HOOKS_WARNING" >&2
    trap 'echo "$HOOKS_WARNING" >&2' EXIT
  fi
fi

echo "== pytest =="
"$PYTHON" -m pytest tests/ -q

echo "== pyflakes =="
"$PYTHON" -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py

echo "== vault schema =="
"$PYTHON" tools/validate_vault_schema.py

echo "== roadmap =="
"$PYTHON" tools/roadmap.py --check

# --strict only on GitHub Actions (roadmap S05, Decision 6): there any build
# warning fails the check job and so blocks the merge and the deploy. A local
# run stays forgiving, so a half-finished note never stops a preview.
BUILD_FLAGS=(--no-sort)
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  BUILD_FLAGS+=(--strict)
fi
echo "== build (${BUILD_FLAGS[*]}) =="
# GITHUB_REPOSITORY decides the 404 page's absolute links (engine/pipeline.py
# _site_root()). CI sets it; locally it defaults to this repository, so the
# dist/ built here is the one GitHub Pages serves under /aurelia-os/ and the
# browser suite below tests the same thing locally as in CI.
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-trmckinzie/aurelia-os}" "$PYTHON" build.py "${BUILD_FLAGS[@]}"

# Browser suite (roadmap S08, docs/DECISIONS.md item 27): Playwright drives
# Chromium against the dist/ just built, served under /aurelia-os/, and runs
# axe at WCAG A/AA. Blocking, like everything above. It never builds, so it
# cannot race this script's build. The install is a no-op once the pinned
# Playwright's Chromium is present; CI installs it with --with-deps first.
echo "== browser suite (Playwright, axe) =="
npx --no-install playwright install chromium
npx --no-install playwright test

echo "verify.sh: all checks passed"
