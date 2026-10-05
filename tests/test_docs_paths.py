"""Every repo-relative path CLAUDE.md, README.md and docs/*.md name in backticks
should actually exist, so a rename or deletion can't leave a dangling reference
behind (roadmap S10)."""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

DOC_FILES = [ROOT / "CLAUDE.md", ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md"))

# Only a path whose first segment is one of these is checked. Everything else
# in a backtick span -- a CSS class, a JS/Python expression, a GitHub Action
# name, a frontmatter value like `source/book` -- is prose, not a repo path,
# and checking it would just make this test as brittle as the docs it guards.
CHECKED_PREFIXES = (
    "engine", "system", "assets", "vault", "tests", "tools", "docs",
    ".claude", ".github", ".git",
)
CHECKED_EXACT = {
    "build.py", "deploy.py", "CLAUDE.md", "CLAUDE.local.md", "README.md",
    "LICENSE", "SECURITY.md", "verify.sh", "package.json", "package-lock.json",
    "profile.json", "user_config.json", "requirements.txt", "requirements.in",
    "requirements-dev.txt", "requirements-dev.in", ".python-version", ".nvmrc",
}

# Generated at build time (or by a tool run), gitignored, and legitimately
# absent from a fresh checkout. Named here, not skipped wholesale by
# prefix, so a *source* path under the same directory still gets checked.
ALLOWED_GENERATED = {
    "dist",
    "assets/js/search-index.js",
    "tailwind.config.js",
    "reports/roadmap.html",
    "test-results",
    "playwright-report",
    "Aurelia_Factory_v1",
    "node_modules",
}

# Named in the docs precisely because they're *not* there -- per-machine or
# per-session files that are gitignored (CLAUDE.local.md's own family), vault
# content this repo deliberately never commits (the Privacy model table in
# README.md), the dev-vault-root hooks a project CLAUDE.md points at relative
# to the vault root rather than this repo, and a file DECISIONS.md records as
# having been deleted once its one-off migration finished.
KNOWN_ABSENT = {
    ".claude/settings.local.json",
    ".claude/githooks/pre-push",
    ".claude/worktrees",
    "CLAUDE.local.md",
    "vault/99_DROP_ZONE",
    "vault/assets",
    "vault/assets/documents",
    "vault/.smart-env",
    "vault/20_AURELIA",
    "tools/migrate_notebooklm_placeholders.py",
}

PATH_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _on_disk(candidate):
    """Where a documented path lives. `.git/...` is git's own directory, which
    is ROOT/.git in the main checkout but not from a linked worktree, where
    ROOT/.git is a one-line file pointing elsewhere. Ask git for its common
    directory instead, or every concurrent session's verify.sh fails here."""
    if candidate != ".git" and not candidate.startswith(".git/"):
        return ROOT / candidate
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], cwd=ROOT, capture_output=True, text=True
    )
    common = ROOT / result.stdout.strip() if result.returncode == 0 else ROOT / ".git"
    return common / candidate[len(".git/"):] if candidate.startswith(".git/") else common


def _is_generated(candidate):
    parts = Path(candidate).parts
    return any(candidate == g or parts[0] == g.split("/")[0] for g in ALLOWED_GENERATED)


def _candidate_paths(text):
    found = set()
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for span in re.findall(r"`([^`]+)`", line):
            if "..." in span or not PATH_RE.match(span):
                continue
            first = span.split("/")[0]
            if first in CHECKED_PREFIXES or span in CHECKED_EXACT:
                found.add(span.rstrip("/"))
    return found


def _all_candidates():
    for doc in DOC_FILES:
        for candidate in _candidate_paths(doc.read_text(encoding="utf-8")):
            yield doc, candidate


@pytest.mark.parametrize("doc,candidate", list(_all_candidates()), ids=lambda v: str(v))
def test_documented_path_exists(doc, candidate):
    if _is_generated(candidate):
        pytest.skip(f"{candidate} is a generated/gitignored artifact")
    if candidate in KNOWN_ABSENT:
        pytest.skip(f"{candidate} is documented as deliberately absent")
    assert _on_disk(candidate).exists(), (
        f"{doc.relative_to(ROOT)} names `{candidate}`, which does not exist in the repo"
    )
