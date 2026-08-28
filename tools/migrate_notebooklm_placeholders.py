"""One-off migration: strips leftover TPL_NotebookLM.md placeholder lines
(e.g. "assets/video/[filename].mp4") out of already-published NotebookLM
notes.

Why: engine.extractors.extract_notebooklm_data() treats ANY non-whitespace
text under a feature header ("# Video Overview", "# Quiz", ...) as proof
that feature is active and badges it on the card. The old template shipped
every feature header pre-filled with a fake placeholder path, so anyone who
didn't delete the unused ones by hand got false "active" badges on the live
site. 14 of the 15 published NotebookLM notes were affected as of the
2026-08 template audit (see TPL_NotebookLM.md's new contract comment).

This script removes the header + placeholder line together for any feature
section whose content is *exactly* an unfilled placeholder (matched by
regex, not just "looks short") -- anything a human actually wrote, even a
single word, is left untouched. Safe to re-run; a no-op on already-clean
notes.

Usage:
    python tools/migrate_notebooklm_placeholders.py            # dry run, prints a diff
    python tools/migrate_notebooklm_placeholders.py --apply    # writes changes
"""
import argparse
import difflib
import glob
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import VAULT_PATH  # noqa: E402

NOTEBOOKLM_DIR = os.path.join(VAULT_PATH, "10_GARDEN", "16_NotebookLM")

# One regex per feature header, mirroring engine/extractors.py's `features`
# dict exactly -- if that dict ever changes, this must change with it.
FEATURE_HEADERS = [
    r'#+\s*.*Audio Overview',
    r'#+\s*.*Video Overview',
    r'#+\s*.*Mind Map',
    r'#+\s*.*Reports',
    r'#+\s*.*Flashcards',
    r'#+\s*.*Quiz',
    r'#+\s*.*Infographic',
    r'#+\s*.*Slide Deck',
    r'#+\s*.*Data Table',
]

# What an untouched template placeholder looks like -- deliberately strict
# (exact literal "[filename]") so a real path with a real filename never matches.
PLACEHOLDER_LINE = re.compile(r'^assets/[\w\-]+/\[filename\]\.\w+$')


def strip_unfilled_sections(text):
    """Removes each feature header block whose body is only a placeholder line."""
    for header_pat in FEATURE_HEADERS:
        # Match: header line, then its body up to (not including) the next
        # "#" header or end of string.
        pattern = re.compile(
            rf'(?im)^({header_pat}[^\n]*)\n((?:(?!^#).*\n?)*)'
        )

        def _maybe_strip(m):
            body = m.group(2)
            if PLACEHOLDER_LINE.match(body.strip()):
                return ''  # drop the header and its placeholder body entirely
            return m.group(0)

        text = pattern.sub(_maybe_strip, text)

    # Collapse any run of 3+ blank lines left behind by a removed section
    # down to a single blank line, so deletions don't leave visible gaps.
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='write changes (default: dry-run diff only)')
    args = parser.parse_args()

    changed = 0
    for path in sorted(glob.glob(os.path.join(NOTEBOOKLM_DIR, '*.md'))):
        original = open(path, 'r', encoding='utf-8').read()
        updated = strip_unfilled_sections(original)
        if updated == original:
            continue
        changed += 1
        rel = os.path.relpath(path, VAULT_PATH)
        print(f"\n{'='*70}\n{rel}\n{'='*70}")
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            lineterm='',
        )
        print(''.join(diff))
        if args.apply:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(updated)

    mode = "APPLIED" if args.apply else "DRY RUN (pass --apply to write)"
    print(f"\n{'='*70}\n{changed} note(s) affected. Mode: {mode}\n{'='*70}")


if __name__ == '__main__':
    main()
