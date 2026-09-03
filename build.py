"""Entrypoint: turns the Obsidian vault into the static dist/ site. See engine/."""
import argparse
import sys

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't encode
# the emoji used throughout the build log; force UTF-8 so `python build.py`
# doesn't crash outside a UTF-8 terminal.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from engine.pipeline import build_all


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Build the Aurelia OS site into dist/.",
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        help=("Skip the Drop Zone sort. That step is the only part of the build "
              "that writes to vault/ (it moves files out of vault/99_DROP_ZONE "
              "into vault/assets/), so this makes the build read-only against "
              "the vault. Equivalent to AURELIA_SKIP_DROPZONE=1."),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    # None, not True, when the flag is absent -- that lets AURELIA_SKIP_DROPZONE
    # decide. An explicit --no-sort always wins.
    build_all(sort_dropzone=False if args.no_sort else None)
