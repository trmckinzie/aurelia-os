"""Entrypoint: turns the Obsidian vault into the static dist/ site. See engine/."""
import sys

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't encode
# the emoji used throughout the build log; force UTF-8 so `python build.py`
# doesn't crash outside a UTF-8 terminal.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from engine.pipeline import build_all

if __name__ == "__main__":
    build_all()
