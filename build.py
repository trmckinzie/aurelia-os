"""Entrypoint: turns the Obsidian vault into the static dist/ site. See engine/."""
import argparse
import sys

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't encode
# the emoji used throughout the build log; force UTF-8 so `python build.py`
# doesn't crash outside a UTF-8 terminal.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from engine.pipeline import StrictBuildError, build_all
from engine.profile import ProfileError
from engine.user_config import UserConfigError


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Build the site into dist/.",
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        help=("Skip the Drop Zone sort. That step is the only part of the build "
              "that writes to vault/ (it moves files out of vault/99_DROP_ZONE "
              "into vault/assets/), so this makes the build read-only against "
              "the vault. Equivalent to AURELIA_SKIP_DROPZONE=1."),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=("Exit non-zero if the build printed any warning (malformed "
              "frontmatter, a missing asset, an ambiguous alias, ...). CI "
              "builds with this so a degraded site cannot deploy; local "
              "builds leave it off and stay forgiving."),
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        # None, not True, when --no-sort is absent -- that lets
        # AURELIA_SKIP_DROPZONE decide. An explicit --no-sort always wins.
        build_all(sort_dropzone=False if args.no_sort else None, strict=args.strict)
    except (UserConfigError, ProfileError, StrictBuildError) as e:
        # Problems with the input, not bugs in the engine: one line naming
        # the file and field reads better than a traceback, in a terminal
        # and in CI's failure summary alike.
        print(f"\n❌ BUILD FAILED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
