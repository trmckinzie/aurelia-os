"""Containment checks for paths the build reads from disk.

Two steps of the publish path have to answer the same question -- "does this
path actually land inside the directory I think I am reading?" -- and they
must answer it identically: pipeline._scan_vault() (is this .md file really
inside vault/?) and assets_pipeline (is this asset really inside assets/?).
A second, subtly different copy of the check is a silent hole, so the answer
lives here once.

The threat this exists for is a directory junction, not a symlink. On
Windows os.path.islink() reports only IO_REPARSE_TAG_SYMLINK, while
`mklink /J` creates IO_REPARSE_TAG_MOUNT_POINT -- so islink() is False for a
junction, os.walk(followlinks=False) descends it anyway, and shutil.copytree
copies straight through it. Creating one needs no elevation, unlike a
symlink. For a static site generator whose output is published to the
internet, a junction planted anywhere under vault/ or assets/ is a way to
publish arbitrary local files.

Comparison is on Path objects, never strings. PurePath.__eq__ is
case-insensitive on Windows, so a startswith-style string test would be
bypassable by casing alone (`c:\\dev\\...` vs `C:\\dev\\...`), and resolve()
has already expanded 8.3 short names (`PROGRA~1`), which such a test would
also miss. Both were verified against file_sorter's equivalent check, which
this mirrors deliberately -- same bug class, same shape of fix.

engine/content.py has its own `_is_within` for a different question (does a
note's *relative* asset reference stay under the root it is joined to --
audit #20). It is realpath-based and normcase-guarded, so it is sound; it is
not folded in here because it takes an unresolved base and a string it must
not resolve twice.
"""
import os
from pathlib import Path


def is_inside(resolved, base_resolved):
    """True if an already-resolved path is base_resolved or below it.

    Both arguments must already have been through resolve().
    """
    return resolved == base_resolved or base_resolved in resolved.parents


def escapes(path, base_resolved):
    """True if `path` does not resolve to somewhere inside base_resolved.

    resolve() follows symlinks and junctions, which is the point: containment
    has to be judged on where a path actually lands on disk, not on the
    literal string. absolute() would let a path pass merely by pointing at a
    junction planted inside the base whose real target is outside it -- which
    is the whole attack.

    resolve() is non-strict, so a path that does not exist yet still resolves
    (with `..` segments collapsed) rather than raising.
    """
    try:
        resolved = Path(path).resolve()
    except OSError:
        # A component that cannot be resolved (permissions, a broken reparse
        # point) is treated as escaping -- fail closed, not open.
        return True
    return not is_inside(resolved, base_resolved)


def is_link(path):
    """True if `path` is a symlink or a Windows directory junction.

    os.path.islink() alone is not that test (see the module docstring).
    os.path.isjunction() is Python 3.12+, which covers both this project's
    floor and CI's pinned 3.12; on an older interpreter this degrades to the
    symlink-only answer and `escapes()` remains the real backstop.
    """
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is None:
        return False
    try:
        return bool(isjunction(path))
    except OSError:
        return True
