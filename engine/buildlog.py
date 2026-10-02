"""One place every build warning goes through, so --strict can count them.

Before this module each warning was a bare print() scattered across the
engine, and a build that printed ten of them still exited 0 -- so CI, which
only looks at the exit code, deployed whatever came out. warn() still prints
the same line, and also records it; build_all() reads the record at the end,
prints a summary, and under --strict (CI) turns any warning into a failure.

Local builds stay forgiving on purpose (docs/roadmap.yaml, S05, Decision 6):
a half-finished note should not stop Travis previewing the rest of the site,
but it must not reach the live one.

A warning is something the build skipped or worked around that a human
should fix. Progress lines and expected, deliberate omissions (an
unpublished note, a dangling wikilink placeholder) are not warnings and stay
plain print() calls.
"""

_warnings = []


def warn(message):
    """Prints a build warning and records it for the end-of-build summary."""
    _warnings.append(message)
    print(f"   ⚠️  {message}")


def get_warnings():
    return list(_warnings)


def reset_warnings():
    _warnings.clear()
