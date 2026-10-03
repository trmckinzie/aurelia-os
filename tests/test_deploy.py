"""Smoke test for deploy.py (roadmap S09): the factory clone builds and
stands on its own.

deploy.py had no test at all -- a change to the engine's own contracts (an
import path, a context variable a template now needs) could break the
clone silently, and the clone's own README promises `python build.py` just
works out of the box.

Runs the clone's build.py as a *separate* Python process (not an in-process
call): the clone's engine/ is physically copied to a new path, and the
current process already has the real repo's `engine` package cached in
sys.modules with ROOT_DIR baked in at import time -- a fresh interpreter is
the only way to actually exercise the clone's own copy.

Needs the Tailwind CLI and the npm packages engine/vendor.py copies from
(same prerequisite as tests/test_reproducible_build.py); skipped, not
failed, where node_modules/ isn't installed. The clone borrows the main
checkout's node_modules/ via a symlink rather than running a second
`npm install` just for this test (the same borrowing CLAUDE.local.md
documents for verify.sh in a worktree).
"""
import os
import subprocess
import sys

import pytest

import deploy
from engine.config import ROOT_DIR

_NODE_MODULES = os.path.join(ROOT_DIR, "node_modules")
_needs_node_modules = pytest.mark.skipif(
    not os.path.isdir(_NODE_MODULES),
    reason="node_modules/ not installed -- run `npm ci`",
)


def _clone_into(tmp_path, monkeypatch):
    target = str(tmp_path / "clone")
    monkeypatch.setattr(deploy, "TARGET_DIR", target)
    deploy.main()
    return target


def test_clone_has_the_files_its_own_readme_promises(tmp_path, monkeypatch):
    target = _clone_into(tmp_path, monkeypatch)
    for relpath in (
        "build.py", "engine", "requirements.txt", "package.json",
        "user_config.json", "profile.json", "system/templates", "README.md",
        "vault/10_GARDEN/00_Demo_Concept.md",
    ):
        assert os.path.exists(os.path.join(target, relpath)), relpath


@_needs_node_modules
def test_clone_builds_with_no_dangling_social_preview_reference(tmp_path, monkeypatch):
    target = _clone_into(tmp_path, monkeypatch)

    # The clone's own tailwind_build.py/vendor.py resolve node_modules/
    # relative to their own ROOT_DIR (the clone's root, once build.py runs
    # as a subprocess there) -- borrow the main checkout's rather than a
    # second `npm install` just for this test.
    try:
        os.symlink(_NODE_MODULES, os.path.join(target, "node_modules"))
    except OSError as e:
        pytest.skip(f"could not symlink node_modules/ into the clone: {e}")

    result = subprocess.run(
        [sys.executable, "build.py", "--no-sort"],
        cwd=target, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    dist = os.path.join(target, "dist")
    for page in ("index.html", "garden.html", "about.html"):
        assert os.path.isfile(os.path.join(dist, page)), page

    # deploy.py deliberately never copies assets/images/ into the clone
    # (privacy -- see copy_frontend()'s own comment), so the clone has no
    # social-preview.jpg of its own. Before S09, base.html still
    # unconditionally emitted an <meta og:image> tag naming that
    # nonexistent file -- a social-media link that always 404s. See
    # engine/pipeline.py's has_social_preview and base.html.
    assert not os.path.exists(os.path.join(dist, "assets", "images", "social-preview.jpg"))
    with open(os.path.join(dist, "about.html"), encoding="utf-8") as f:
        about_html = f.read()
    assert "social-preview.jpg" not in about_html
    assert "og:image" not in about_html
