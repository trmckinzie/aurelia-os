"""Builds the real vault/ twice into two different output directories and
diffs them byte for byte (roadmap S09).

Before this, the vault walk didn't sort its subdirectories (only its files),
and several generated files were opened in text mode with no explicit
newline, which writes CRLF on Windows -- so the same commit, built by two
different machines (or even just read back with the drop zone sorted
differently in between), was not guaranteed to produce the same dist/.

This runs the actual build.py pipeline, which means it needs the Tailwind
CLI and the npm packages engine/vendor.py copies from (fonts, marked.js,
Motion) -- the same prerequisite `npm ci` gives every other real build. It
is skipped, rather than failing, where node_modules/ isn't installed: a
fresh checkout that hasn't run `npm ci` yet can still run the rest of the
Python suite.

OUTPUT_DIR is patched on every module that imported it directly from
engine.config (a `from X import Y` binds a separate name, so patching
engine.config.OUTPUT_DIR alone would not reach any of them) -- everything
else (VAULT_PATH, ROOT_DIR, template dir, user_config.json, profile.json)
is deliberately left pointing at the real repo, the same way CI's own build
does.
"""
import filecmp
import os

import pytest

from engine import assets_pipeline, pipeline, tailwind_build, theming, vendor
from engine.config import ROOT_DIR
from engine.pipeline import build_all

_NODE_MODULES = os.path.join(ROOT_DIR, "node_modules")
_needs_node_modules = pytest.mark.skipif(
    not os.path.isdir(_NODE_MODULES),
    reason="node_modules/ not installed -- run `npm ci` (needed for the real Tailwind/font/vendor build)",
)


def _build_into(tmp_path, monkeypatch, name):
    output_dir = str(tmp_path / name)
    for module in (pipeline, theming, tailwind_build, assets_pipeline, vendor):
        monkeypatch.setattr(module, "OUTPUT_DIR", output_dir)
    build_all(sort_dropzone=False, strict=False)
    return output_dir


def _all_files(root):
    found = []
    for dirpath, _dirs, filenames in os.walk(root):
        for name in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(found)


@_needs_node_modules
def test_two_builds_of_the_same_vault_are_byte_identical(tmp_path, monkeypatch):
    first = _build_into(tmp_path, monkeypatch, "build-a")
    second = _build_into(tmp_path, monkeypatch, "build-b")

    first_files = _all_files(first)
    second_files = _all_files(second)
    assert first_files == second_files, "the two builds produced a different set of files"
    assert first_files, "the build produced no files at all -- this guard would pass vacuously"

    mismatches = [
        relpath for relpath in first_files
        if not filecmp.cmp(os.path.join(first, relpath), os.path.join(second, relpath), shallow=False)
    ]
    assert not mismatches, f"{len(mismatches)} file(s) differ between two builds of the same commit: {mismatches[:10]}"
