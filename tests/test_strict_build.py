"""Build warnings are collected in one place, and --strict fails on any of them.

Roadmap S05, Decision 6: every warning fails CI, on GitHub only. Local builds
stay forgiving; CI passes --strict. These tests cover the collector, each
failure path S05 added, and the CI wiring.
"""
import glob
import os
import subprocess
import sys

import pytest

import build
from engine import assets_pipeline, buildlog, content, pipeline
from engine.buildlog import get_warnings, reset_warnings, warn
from engine.pipeline import StrictBuildError
from engine.user_config import UserConfigError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


# --- the collector -------------------------------------------------------

def test_warn_prints_and_records(capsys):
    warn("something to fix")
    assert "⚠️  something to fix" in capsys.readouterr().out
    assert get_warnings() == ["something to fix"]


def test_reset_clears_the_record():
    warn("one")
    reset_warnings()
    assert get_warnings() == []


def test_get_warnings_returns_a_copy():
    warn("one")
    get_warnings().clear()
    assert buildlog.get_warnings() == ["one"]


def test_malformed_frontmatter_is_a_recorded_warning_naming_the_note():
    content.parse_frontmatter("---\ntitle: [unclosed\n---\nbody", source="10_GARDEN/Broken.md")
    content.reset_malformed_count()
    assert any("malformed frontmatter in 10_GARDEN/Broken.md" in w for w in get_warnings())


# --- each failure path ---------------------------------------------------

def test_every_ambiguous_alias_is_reported():
    # Only the first collision in a build used to be printed.
    notes = [
        {"note_id": "note-a", "title": "A", "aliases": ["First", "Second"]},
        {"note_id": "note-b", "title": "B", "aliases": ["First", "Second"]},
    ]
    content.build_link_resolver(notes)
    collisions = [w for w in get_warnings() if "claimed by multiple notes" in w]
    assert len(collisions) == 2
    assert "note-a, note-b" in collisions[0]


def test_unreadable_asset_warns_during_cache_busting(tmp_path, monkeypatch):
    # tmp_path holds none of the four files, so every read fails.
    monkeypatch.setattr(pipeline, "ROOT_DIR", str(tmp_path))
    pipeline._asset_version()
    warnings = get_warnings()
    assert len(warnings) == 4
    assert all("cache busting" in w for w in warnings)


def test_asset_version_is_silent_when_every_file_exists():
    pipeline._asset_version()
    assert get_warnings() == []


def test_build_stops_when_dist_cannot_be_wiped(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    monkeypatch.setattr(assets_pipeline, "OUTPUT_DIR", str(dist))

    def _locked(path, *args, **kwargs):
        raise PermissionError("file in use")

    monkeypatch.setattr(assets_pipeline.shutil, "rmtree", _locked)
    with pytest.raises(RuntimeError, match="Could not wipe"):
        assets_pipeline.prepare_dist()


# --- strict mode in build_all() -----------------------------------------

def _stub_build(monkeypatch, warning=None):
    """Runs build_all() end to end with every step that writes stubbed out.
    `warning`, if given, is raised by the vault scan the way a real note
    with broken frontmatter would."""
    monkeypatch.setattr(pipeline, "prepare_dist", lambda: None)
    monkeypatch.setattr(pipeline, "_write_cname", lambda cfg: None)
    monkeypatch.setattr(pipeline, "sync_vault_assets", lambda: None)
    monkeypatch.setattr(pipeline, "_render_pages", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "generate_theme_css", lambda: None)
    monkeypatch.setattr(pipeline, "compile_css", lambda: None)

    def _scan():
        if warning:
            warn(warning)
        return [], {}, []

    monkeypatch.setattr(pipeline, "_scan_vault", _scan)


def test_strict_build_fails_on_a_warning(monkeypatch):
    _stub_build(monkeypatch, warning="Skipping malformed frontmatter: test")
    with pytest.raises(StrictBuildError, match="1 build warning"):
        pipeline.build_all(sort_dropzone=False, strict=True)


def test_default_build_stays_forgiving(monkeypatch, capsys):
    _stub_build(monkeypatch, warning="Skipping malformed frontmatter: test")
    pipeline.build_all(sort_dropzone=False)
    out = capsys.readouterr().out
    assert "1 build warning(s)" in out
    assert "SYSTEM SYNC COMPLETE" in out


def test_strict_build_passes_with_no_warnings(monkeypatch):
    _stub_build(monkeypatch)
    pipeline.build_all(sort_dropzone=False, strict=True)


def test_warnings_from_an_earlier_build_do_not_carry_over(monkeypatch):
    warn("left over from a previous run in the same process")
    _stub_build(monkeypatch)
    pipeline.build_all(sort_dropzone=False, strict=True)


# --- roadmap S06: the CI commit stamp -------------------------------------

def test_build_all_forwards_the_commit_stamp_from_the_environment(monkeypatch):
    """build_all() reads AURELIA_BUILD_COMMIT(_TIME) and hands both straight
    to _render_pages -- see engine/pipeline.py's _build_commit_stamp."""
    captured = {}
    _stub_build(monkeypatch)
    monkeypatch.setattr(pipeline, "_render_pages", lambda *a, **k: captured.update(k))
    monkeypatch.setenv("AURELIA_BUILD_COMMIT", "abc123")
    monkeypatch.setenv("AURELIA_BUILD_COMMIT_TIME", "2026-10-02T08:59:00-06:00")

    pipeline.build_all(sort_dropzone=False)

    assert captured["build_commit"] == "abc123"
    assert captured["build_commit_time"] == "2026-10-02T08:59:00-06:00"


def test_build_all_stamps_nothing_without_the_environment(monkeypatch):
    """A local build matches dist/ output from before the stamp existed."""
    captured = {}
    _stub_build(monkeypatch)
    monkeypatch.setattr(pipeline, "_render_pages", lambda *a, **k: captured.update(k))
    monkeypatch.delenv("AURELIA_BUILD_COMMIT", raising=False)
    monkeypatch.delenv("AURELIA_BUILD_COMMIT_TIME", raising=False)

    pipeline.build_all(sort_dropzone=False)

    assert captured["build_commit"] is None
    assert captured["build_commit_time"] is None


# --- the command line ----------------------------------------------------

def test_cli_strict_flag():
    assert build.parse_args([]).strict is False
    assert build.parse_args(["--strict"]).strict is True


@pytest.mark.parametrize("error", [
    StrictBuildError("2 build warning(s) under --strict"),
    UserConfigError("user_config.json: author: missing required key 'name'"),
])
def test_cli_exits_one_with_the_message(monkeypatch, capsys, error):
    def _fail(**kwargs):
        raise error

    monkeypatch.setattr(build, "build_all", _fail)
    assert build.main(["--no-sort", "--strict"]) == 1
    assert str(error) in capsys.readouterr().err


def test_cli_passes_strict_through(monkeypatch):
    seen = {}
    monkeypatch.setattr(build, "build_all", lambda **kw: seen.update(kw))
    assert build.main(["--no-sort", "--strict"]) == 0
    assert seen == {"sort_dropzone": False, "strict": True}


# --- CI wiring -----------------------------------------------------------

def test_ci_deploy_build_is_strict():
    # Every workflow that invokes build.py, not just deploy.yml --
    # redeploy.yml and weekly-check.yml (roadmap S06) build too, and a
    # guard pinned to one filename stops protecting a build the moment a
    # second one is added beside it.
    workflows = sorted(glob.glob(os.path.join(ROOT, ".github", "workflows", "*.yml")))
    assert workflows, "no workflow files found"

    checked_any = False
    for workflow in workflows:
        with open(workflow, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if "build.py" in ln and "#" not in ln]
        for line in lines:
            checked_any = True
            assert "--strict" in line, f"{workflow}: CI build must pass --strict: {line}"
    assert checked_any, "no build.py invocation found in any workflow"


def _verify_build_flags(env_value):
    """Runs verify.sh's flag logic with GITHUB_ACTIONS set to env_value,
    without running the suite itself."""
    with open(os.path.join(ROOT, "verify.sh"), encoding="utf-8") as f:
        script = f.read()
    start = script.index("BUILD_FLAGS=(")
    end = script.index("fi\n", start) + 3
    snippet = script[start:end] + 'echo "${BUILD_FLAGS[*]}"\n'
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    if env_value is not None:
        env["GITHUB_ACTIONS"] = env_value
    result = subprocess.run(["bash", "-c", snippet], env=env, capture_output=True,
                            text=True, check=True)
    return result.stdout.strip()


# On Windows `bash` may be WSL's, which does not inherit GITHUB_ACTIONS.
# Both CI runners are ubuntu and macOS, where these run.
_needs_posix_bash = pytest.mark.skipif(sys.platform == "win32", reason="POSIX bash only")


@_needs_posix_bash
def test_verify_sh_is_strict_on_github_actions():
    assert _verify_build_flags("true") == "--no-sort --strict"


@_needs_posix_bash
def test_verify_sh_is_forgiving_locally():
    assert _verify_build_flags(None) == "--no-sort"
