"""Containment checks (engine/paths.py).

The link-based tests use a real junction on Windows and a real symlink
elsewhere, because the whole point of this module is that the difference
between those two matters: os.path.islink() is False for a junction, so a
test that only ever exercised symlinks would pass against the bug.
"""
import os

import pytest

from engine.paths import escapes, is_inside, is_link
from pathlib import Path


def make_dir_link(link, target):
    """Creates a directory junction (Windows) or symlink (POSIX).

    A junction is what an attacker on Windows actually gets to plant: it
    needs no elevation and no Developer Mode, unlike a symlink.
    """
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(str(target), str(link), target_is_directory=True)


def test_is_inside_accepts_the_base_itself(tmp_path):
    base = tmp_path.resolve()
    assert is_inside(base, base)


def test_is_inside_accepts_a_nested_path(tmp_path):
    base = tmp_path.resolve()
    assert is_inside(base / "a" / "b" / "c.md", base)


def test_is_inside_rejects_a_sibling_with_the_same_prefix(tmp_path):
    # The classic string-prefix bug: "vault-backup" starts with "vault".
    base = (tmp_path / "vault").resolve()
    assert not is_inside((tmp_path / "vault-backup" / "note.md").resolve(), base)


def test_escapes_rejects_a_dot_dot_traversal(tmp_path):
    base = (tmp_path / "vault").resolve()
    base.mkdir()
    assert escapes(str(base / ".." / "outside.md"), base)


def test_escapes_accepts_a_plain_child(tmp_path):
    base = (tmp_path / "vault").resolve()
    base.mkdir()
    assert not escapes(str(base / "note.md"), base)


def test_escapes_ignores_casing(tmp_path):
    """A case-flipped path is the same path on Windows and must not read as
    an escape (nor, on a case-sensitive filesystem, as containment)."""
    base = (tmp_path / "Vault").resolve()
    base.mkdir()
    flipped = str(base).swapcase()
    assert escapes(flipped, base) is (os.name != "nt")


def test_escapes_sees_through_a_directory_link(tmp_path):
    """The finding itself: a link inside the tree pointing out of it."""
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    vault.mkdir()
    outside.mkdir()
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    make_dir_link(vault / "escape-hatch", outside)

    assert escapes(str(vault / "escape-hatch" / "secret.md"), vault.resolve())


def test_escapes_allows_a_link_that_stays_inside(tmp_path):
    vault = tmp_path / "vault"
    (vault / "real").mkdir(parents=True)
    make_dir_link(vault / "alias", vault / "real")

    assert not escapes(str(vault / "alias" / "note.md"), vault.resolve())


@pytest.mark.skipif(os.name != "nt", reason="junctions are Windows-only")
def test_is_link_detects_a_junction_that_islink_misses(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    junction = tmp_path / "junction"
    make_dir_link(junction, target)

    assert not os.path.islink(str(junction))  # the reason this module exists
    assert is_link(str(junction))


def test_is_link_is_false_for_an_ordinary_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert not is_link(str(plain))


def test_is_link_is_false_for_an_ordinary_file(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("x", encoding="utf-8")
    assert not is_link(str(plain))


def test_escapes_resolves_a_base_reached_through_a_link(tmp_path):
    """The vault itself may be synced through a junction.

    Resolving the base as well as the candidate is what keeps that case from
    reading as a whole-tree escape.
    """
    real = tmp_path / "real-vault"
    real.mkdir()
    (real / "note.md").write_text("x", encoding="utf-8")
    link = tmp_path / "vault"
    make_dir_link(link, real)

    assert not escapes(str(link / "note.md"), Path(link).resolve())
