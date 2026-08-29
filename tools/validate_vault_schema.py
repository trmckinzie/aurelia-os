"""Validates every published vault/10_GARDEN note against the canonical
per-type frontmatter schema (see CLAUDE.md's "Content model" section and the
2026 vault-standardization migration).

Run standalone:

    python tools/validate_vault_schema.py

Exits 0 with a clean report if every published note matches; exits 1 and
prints every violation otherwise. Also runnable via `pytest` -- see
tests/test_validate_vault_schema.py, which calls check_vault() directly so
CI-adjacent `pytest` runs catch schema drift even though the GitHub Actions
workflow itself only runs build.py (see CLAUDE.md).

Reused validator, not reimplemented: this imports engine.content.parse_frontmatter
rather than re-parsing YAML itself, so "does this note's frontmatter parse"
always means the same thing here as it does in the real build.
"""
import os
import sys

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode the emoji this script prints -- same fix as build.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Allow running as a standalone script (python tools/validate_vault_schema.py)
# as well as via `python -m` or pytest, both of which already have the repo
# root on sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import VAULT_PATH  # noqa: E402
from engine.content import parse_frontmatter  # noqa: E402

GARDEN = os.path.join(VAULT_PATH, "10_GARDEN")

# folder -> the `type:` value every published note in it must carry.
FOLDER_TYPE = {
    "11_Daily_Bridge": "daily-bridge",
    "12_Concepts": "concept",
    "13_Authors": "author",
    "14_Disciplines": "discipline",
    "15_Sources": "source/book",
    "16_Gemini_Notebook": "gemini-notebook",
    "17_Deep_Dives": "deep-dive",
}

VALID_MATURITY = {"seed", "growing", "evergreen"}
VALID_STATUS = {"active", "reading", "queued", "archive"}


def _tag_set(meta):
    return {str(t).strip() for t in (meta.get("tags") or [])}


def _has_topic_tag(tags):
    return any(str(t).startswith("topic/") for t in tags)


def check_note(path, folder, meta):
    """Returns a list of violation strings for one published note (empty if clean)."""
    problems = []
    expected_type = FOLDER_TYPE[folder]
    tags = _tag_set(meta)

    note_type = str(meta.get("type", "")).strip()
    if note_type != expected_type:
        problems.append(f"type: expected '{expected_type}', got '{note_type or '(missing)'}'")
    if f"type/{expected_type}" not in tags:
        problems.append(f"missing mirrored tag 'type/{expected_type}'")

    maturity = str(meta.get("maturity", "")).strip()
    if maturity not in VALID_MATURITY:
        problems.append(f"maturity: '{maturity or '(missing)'}' not one of {sorted(VALID_MATURITY)}")
    elif f"maturity/{maturity}" not in tags:
        problems.append(f"missing mirrored tag 'maturity/{maturity}'")

    status = str(meta.get("status", "")).strip()
    if status not in VALID_STATUS:
        problems.append(f"status: '{status or '(missing)'}' not one of {sorted(VALID_STATUS)}")
    elif f"status/{status}" not in tags:
        problems.append(f"missing mirrored tag 'status/{status}'")

    for t in tags:
        if t in ("topic/", "topic"):
            problems.append(f"stray empty/bare topic tag: '{t}'")

    return problems


def check_vault():
    """Walks 10_GARDEN, validates every published note.

    Returns (violations, empty_files, untagged_notes):
      violations: (relpath, [problem, ...]) for notes that fail the schema.
      empty_files: zero-byte .md paths found (reported separately -- not a
        schema violation, since an empty file is never published anyway,
        but worth surfacing as vault hygiene).
      untagged_notes: relpaths of published notes with no `topic/*` tag.
        Also informational, not a violation -- topic assignment is a
        content judgment call, not something this validator should fail a
        build over -- but worth surfacing since "Related by Topic" and the
        Garden's tag cloud (both in gardentemplate.html) are invisible to a
        note with no topic tag at all.
    """
    violations = []
    empty_files = []
    untagged_notes = []

    for folder in FOLDER_TYPE:
        folder_path = os.path.join(GARDEN, folder)
        if not os.path.isdir(folder_path):
            continue
        for fn in sorted(os.listdir(folder_path)):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(folder_path, fn)
            if os.path.getsize(path) == 0:
                empty_files.append(path)
                continue
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            meta = parse_frontmatter(content)
            if not meta.get("publish"):
                continue  # unpublished notes aren't held to the schema
            problems = check_note(path, folder, meta)
            if problems:
                violations.append((os.path.relpath(path, VAULT_PATH), problems))
            if not _has_topic_tag(_tag_set(meta)):
                untagged_notes.append(os.path.relpath(path, VAULT_PATH))

    return violations, empty_files, untagged_notes


def main():
    violations, empty_files, untagged_notes = check_vault()

    if empty_files:
        print(f"ℹ️  {len(empty_files)} zero-byte note(s) found (unpublished, not a schema violation):")
        for p in empty_files:
            print(f"     {os.path.relpath(p, VAULT_PATH)}")

    if untagged_notes:
        print(f"ℹ️  {len(untagged_notes)} published note(s) have no topic/* tag (not a schema violation, "
              f"but invisible to 'Related by Topic' and the tag cloud):")
        for p in untagged_notes:
            print(f"     {p}")

    if not violations:
        print("✅ Every published 10_GARDEN note matches the canonical schema.")
        return 0

    print(f"❌ {len(violations)} note(s) violate the canonical schema:")
    for relpath, problems in violations:
        print(f"\n  {relpath}")
        for p in problems:
            print(f"     - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
