"""Roadmap S02 pinned every action to a full commit SHA, gave every job its
own least-privilege permissions, and timed out every job -- but nothing
enforced any of it going forward, so a new workflow file (or a new job in
an existing one) could quietly drift from the policy with no test to catch
it. Roadmap S06 added three more workflow files and a composite action, so
this now checks all of them, not just deploy.yml.
"""
import glob
import os
import re

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(ROOT, ".github", "workflows")
ACTION_FILES = sorted(glob.glob(os.path.join(ROOT, ".github", "actions", "*", "action.yml")))


def _workflow_files():
    return sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml")))


def _load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _iter_uses(obj):
    """Yield every `uses:` value anywhere in a parsed workflow or action file."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "uses" and isinstance(value, str):
                yield value
            else:
                yield from _iter_uses(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_uses(item)


_ALL_FILES = _workflow_files() + ACTION_FILES


@pytest.mark.parametrize("path", _ALL_FILES)
def test_every_external_action_is_pinned_to_a_full_commit_sha(path):
    # A tag can move after the fact; a SHA cannot (roadmap S02's reasoning,
    # docs/roadmap.yaml). A local action (./.github/actions/...) has
    # nothing to pin -- it's already this repo's own commit.
    for uses in _iter_uses(_load(path)):
        if uses.startswith("./"):
            continue
        assert "@" in uses, f"{path}: {uses!r} has no @ref at all"
        ref = uses.rsplit("@", 1)[1]
        assert re.fullmatch(r"[0-9a-f]{40}", ref), (
            f"{path}: {uses!r} must be pinned to a full 40-character commit SHA, not a movable tag"
        )


_USES_LINE_RE = re.compile(r'^uses:\s*(\S+)(?:\s*#\s*(.+))?$')


@pytest.mark.parametrize("path", _ALL_FILES)
def test_every_pinned_action_carries_its_version_in_a_comment(path):
    # A bare SHA tells a reader nothing about what it upgrades to. Checked
    # on the raw text, not the parsed YAML, since yaml.safe_load discards
    # comments.
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for raw_line in lines:
        m = _USES_LINE_RE.match(raw_line.strip())
        if not m:
            continue
        uses, comment = m.group(1), m.group(2)
        if uses.startswith("./") or "@" not in uses:
            continue
        assert comment, f"{path}: {uses!r} is pinned but carries no version comment"


@pytest.mark.parametrize("path", _workflow_files())
def test_default_permissions_are_empty(path):
    doc = _load(path)
    assert doc.get("permissions") == {}, (
        f"{path}: top-level `permissions` must be {{}} so every job opts in explicitly"
    )


@pytest.mark.parametrize("path", _workflow_files())
def test_every_job_declares_its_own_permissions(path):
    jobs = _load(path).get("jobs", {})
    assert jobs, f"{path}: no jobs found"
    for job_name, job in jobs.items():
        assert "permissions" in job, f"{path}: job {job_name!r} inherits permissions instead of declaring its own"


@pytest.mark.parametrize("path", _workflow_files())
def test_every_job_has_a_timeout(path):
    jobs = _load(path).get("jobs", {})
    for job_name, job in jobs.items():
        assert "timeout-minutes" in job, f"{path}: job {job_name!r} has no timeout-minutes"


_INPUT_INTERP_RE = re.compile(r'\$\{\{\s*(?:inputs|github\.event\.inputs)\.')


@pytest.mark.parametrize("path", _workflow_files())
def test_workflow_dispatch_inputs_never_reach_a_run_script_directly(path):
    # A workflow_dispatch input is free text typed into the Actions UI (or
    # `gh workflow run`). Pasting it straight into a `run:` script is the
    # classic injection path; it must go through `env:` and be referenced
    # as a shell variable instead (redeploy.yml's `tag` input is the one
    # example today). `with:` values are fine -- those go to an action's
    # own typed inputs, not a shell.
    doc = _load(path)
    for job in doc.get("jobs", {}).values():
        for step in job.get("steps", []) or []:
            run = step.get("run")
            if isinstance(run, str) and _INPUT_INTERP_RE.search(run):
                raise AssertionError(
                    f"{path}: step {step.get('name')!r} interpolates a workflow_dispatch "
                    "input directly into its run: script -- pass it through env: instead"
                )
