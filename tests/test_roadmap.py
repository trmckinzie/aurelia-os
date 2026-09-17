"""tools/roadmap.py: the strict validator for docs/roadmap.yaml, the progress
summary, the kickoff prompt, and the rendered dashboard.

The real roadmap file is validated here too, the same way
tests/test_validate_vault_schema.py runs the vault schema check, so a hand
edit that breaks docs/roadmap.yaml fails pytest instead of surfacing the next
time someone opens the dashboard."""
import datetime
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from roadmap import (  # noqa: E402
    PALETTE,
    RoadmapError,
    kickoff_prompt,
    load_roadmap,
    main,
    render_html,
    summarize,
    validate_roadmap,
    write_dashboard,
)

_GENERATED = datetime.datetime(2026, 9, 15, 14, 30)


def _session(sid="S01", **overrides):
    session = {
        "id": sid,
        "title": f"Session {sid}",
        "status": "todo",
        "area": "CI/CD",
        "effort": "M",
        "model": "sonnet",
        "why": "It matters.",
        "tasks": [{"text": "Do the work", "done": False}],
        "done_when": ["The work is verified"],
    }
    session.update(overrides)
    return session


def _done(sid="S01", **overrides):
    fields = {
        "status": "done",
        "tasks": [{"text": "Do the work", "done": True}],
        "started": datetime.date(2026, 9, 15),
        "completed": datetime.date(2026, 9, 16),
    }
    fields.update(overrides)
    return _session(sid, **fields)


def _roadmap(*sessions, **overrides):
    data = {
        "schema_version": 1,
        "title": "Engineering roadmap",
        "updated": datetime.date(2026, 9, 15),
        "repository": "https://github.com/trmckinzie/aurelia-os",
        "sessions": list(sessions) if sessions else [_session()],
    }
    data.update(overrides)
    return data


def _error(data):
    with pytest.raises(RoadmapError) as exc:
        validate_roadmap(data)
    return str(exc.value)


# --- the real file -------------------------------------------------------------

def test_real_roadmap_file_is_valid():
    roadmap = load_roadmap()
    assert roadmap["sessions"], "docs/roadmap.yaml should list at least one session"


# --- validation ----------------------------------------------------------------

def test_a_minimal_roadmap_is_normalized():
    roadmap = validate_roadmap(_roadmap(_session(title="  Padded title  ", why="Why.\n")))
    session = roadmap["sessions"][0]
    assert session["title"] == "Padded title"
    assert session["why"] == "Why."
    assert session["depends_on"] == [] and session["commits"] == []
    assert session["decision"] is None and session["started"] is None
    assert roadmap["backlog"] == []


def test_unknown_top_level_key_is_rejected():
    assert "unknown key 'owner'" in _error(_roadmap(owner="me"))


def test_unknown_session_key_names_its_position():
    assert "sessions[0]: unknown key 'priority'" in _error(_roadmap(_session(priority=1)))


def test_missing_required_session_field_is_named():
    session = _session()
    del session["why"]
    assert "sessions[0].why: is required" in _error(_roadmap(session))


@pytest.mark.parametrize("overrides, expected", [
    ({"id": "S1"}, "sessions[0].id: must look like S01"),
    ({"status": "finished"}, "sessions[0].status: must be one of"),
    ({"effort": "XL"}, "sessions[0].effort: must be one of"),
    ({"model": "haiku"}, "sessions[0].model: must be one of"),
    ({"title": ""}, "sessions[0].title: must not be empty"),
    ({"title": "Two\nlines"}, "sessions[0].title: must be a single line"),
    ({"tasks": []}, "sessions[0].tasks: must have at least 1 item"),
    ({"tasks": [{"text": "Work", "done": "yes"}]}, "sessions[0].tasks[0].done: must be true or false"),
    ({"tasks": [{"text": "Work"}]}, "sessions[0].tasks[0].done: is required"),
    ({"done_when": []}, "sessions[0].done_when: must have at least 1 item"),
    ({"depends_on": "S02"}, "sessions[0].depends_on: must be a list"),
    ({"commits": [1234567]}, "sessions[0].commits[0]: must be a commit hash"),
    ({"commits": ["not-a-sha"]}, "sessions[0].commits[0]: must be a commit hash"),
])
def test_invalid_session_fields_are_rejected(overrides, expected):
    assert expected in _error(_roadmap(_session(**overrides)))


@pytest.mark.parametrize("model", ["fable", "Fable", "best"])
def test_a_session_never_pre_books_fable(model):
    message = _error(_roadmap(_session(model=model)))
    assert "sessions[0].model" in message and "Model Routing" in message


@pytest.mark.parametrize("version", [2, True, "1"])
def test_schema_version_must_be_1(version):
    assert "schema_version: must be 1" in _error(_roadmap(schema_version=version))


def test_repository_must_be_a_github_url():
    assert "repository: must be a GitHub repository URL" in _error(_roadmap(repository="javascript:alert(1)"))


def test_duplicate_session_ids_are_rejected():
    assert "duplicate session id(s): S01" in _error(_roadmap(_session("S01"), _session("S01")))


def test_a_dependency_on_an_unknown_session_is_rejected():
    message = _error(_roadmap(_session("S01", depends_on=["S09"])))
    assert "sessions[0].depends_on: 'S09' is not a session in this file" in message


def test_a_session_cannot_depend_on_itself():
    assert "cannot depend on itself" in _error(_roadmap(_session("S01", depends_on=["S01"])))


def test_dependency_cycles_are_rejected():
    message = _error(_roadmap(_session("S01", depends_on=["S02"]), _session("S02", depends_on=["S01"])))
    assert "dependency cycle: S01 -> S02 -> S01" in message


def test_done_needs_a_completed_date():
    assert "sessions[0].completed: is required once status is done" in _error(_roadmap(_done(completed=None)))


def test_done_needs_every_task_ticked():
    session = _done(tasks=[{"text": "A", "done": True}, {"text": "B", "done": False}])
    assert "sessions[0].status: is done but 1 task is not ticked" in _error(_roadmap(session))


def test_a_completed_date_is_only_for_done_sessions():
    session = _session(status="in_progress", started=datetime.date(2026, 9, 15),
                       completed=datetime.date(2026, 9, 16))
    assert "sessions[0].completed: is set but status is in_progress" in _error(_roadmap(session))


def test_in_progress_needs_a_started_date():
    message = _error(_roadmap(_session(status="in_progress")))
    assert "sessions[0].started: is required once status is in_progress" in message


def test_todo_cannot_have_a_started_date():
    message = _error(_roadmap(_session(started=datetime.date(2026, 9, 15))))
    assert "sessions[0].started: is set but status is todo" in message


def test_completed_cannot_precede_started():
    session = _done(started=datetime.date(2026, 9, 16), completed=datetime.date(2026, 9, 15))
    assert "sessions[0].completed: is earlier than started" in _error(_roadmap(session))


def test_blocked_needs_a_blocker():
    message = _error(_roadmap(_session(status="blocked")))
    assert "sessions[0].blocker: is required when status is blocked" in message


def test_a_blocker_is_only_for_blocked_sessions():
    message = _error(_roadmap(_session(blocker="Waiting on a reply")))
    assert "sessions[0].blocker: is only for blocked sessions" in message


def test_quoted_dates_are_accepted_like_unquoted_ones():
    roadmap = validate_roadmap(_roadmap(_done(started="2026-09-15", completed="2026-09-16"), updated="2026-09-15"))
    assert roadmap["sessions"][0]["completed"] == datetime.date(2026, 9, 16)
    assert roadmap["updated"] == datetime.date(2026, 9, 15)


@pytest.mark.parametrize("value", ["15/09/2026", "2026-9-15", datetime.datetime(2026, 9, 15, 10, 0)])
def test_malformed_dates_are_rejected(value):
    assert "updated: must be a date like 2026-09-15" in _error(_roadmap(updated=value))


def test_backlog_items_are_validated():
    item = {"id": "B01", "title": "Tidy up", "area": "Docs", "status": "open"}
    assert "backlog[0].id: must look like B01" in _error(_roadmap(backlog=[dict(item, id="X1")]))
    assert "backlog[0].status: must be one of" in _error(_roadmap(backlog=[dict(item, status="later")]))
    assert "duplicate backlog id(s): B01" in _error(_roadmap(backlog=[item, dict(item)]))


# --- reading the file ------------------------------------------------------------

_VALID_YAML = """\
schema_version: 1
title: Engineering roadmap
updated: 2026-09-15
repository: https://github.com/trmckinzie/aurelia-os
sessions:
  - id: S01
    title: First
    status: done
    area: CI/CD
    effort: S
    model: sonnet
    why: Needed first.
    tasks:
      - text: One
        done: true
    done_when:
      - It works
    started: 2026-09-15
    completed: 2026-09-15
    commits: ["88973b6"]
  - id: S02
    title: Second
    status: todo
    area: Testing
    effort: M
    model: opus
    why: Needed next.
    depends_on: [S01]
    tasks:
      - text: Two
        done: false
    done_when:
      - It also works
"""


def _write(tmp_path, text, name="roadmap.yaml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_load_roadmap_reads_a_yaml_file(tmp_path):
    roadmap = load_roadmap(_write(tmp_path, _VALID_YAML))
    assert [s["id"] for s in roadmap["sessions"]] == ["S01", "S02"]
    assert roadmap["sessions"][0]["completed"] == datetime.date(2026, 9, 15)


def test_a_repeated_yaml_key_is_an_error_not_a_silent_overwrite(tmp_path):
    text = _VALID_YAML.replace("    status: todo\n", "    status: todo\n    status: done\n")
    with pytest.raises(RoadmapError, match="duplicate key 'status'"):
        load_roadmap(_write(tmp_path, text))


def test_invalid_yaml_says_where(tmp_path):
    with pytest.raises(RoadmapError, match=r"is not valid YAML \(line \d+, column \d+\)"):
        load_roadmap(_write(tmp_path, "sessions: [unclosed\n"))


def test_missing_and_empty_files_are_errors(tmp_path):
    with pytest.raises(RoadmapError, match="file not found"):
        load_roadmap(str(tmp_path / "absent.yaml"))
    with pytest.raises(RoadmapError, match="is empty"):
        load_roadmap(_write(tmp_path, "# only a comment\n"))


# --- progress --------------------------------------------------------------------

def test_summary_counts_sessions_and_tasks():
    roadmap = validate_roadmap(_roadmap(
        _done("S01"),
        _session("S02", status="in_progress", started=datetime.date(2026, 9, 16),
                 tasks=[{"text": "A", "done": True}, {"text": "B", "done": False}]),
        _session("S03", depends_on=["S02"]),
        _session("S04", status="blocked", blocker="Waiting on a decision"),
    ))
    summary = summarize(roadmap)
    assert (summary["done"], summary["total"], summary["percent"]) == (1, 4, 25)
    assert (summary["tasks_done"], summary["tasks_total"]) == (2, 5)
    assert summary["counts"] == {"todo": 1, "in_progress": 1, "blocked": 1, "done": 1}


def test_next_up_finishes_started_work_before_starting_new_work():
    roadmap = validate_roadmap(_roadmap(
        _session("S01"),
        _session("S02", status="in_progress", started=datetime.date(2026, 9, 15)),
    ))
    assert summarize(roadmap)["next_up"]["id"] == "S02"


def test_next_up_skips_sessions_waiting_on_unfinished_dependencies():
    roadmap = validate_roadmap(_roadmap(
        _session("S01", status="blocked", blocker="Needs a decision"),
        _session("S02", depends_on=["S01"]),
        _session("S03"),
    ))
    assert summarize(roadmap)["next_up"]["id"] == "S03"


def test_next_up_is_none_when_nothing_is_ready():
    roadmap = validate_roadmap(_roadmap(
        _session("S01", status="blocked", blocker="Needs a decision"),
        _session("S02", depends_on=["S01"]),
    ))
    assert summarize(roadmap)["next_up"] is None


def test_needs_decision_ignores_finished_sessions():
    roadmap = validate_roadmap(_roadmap(
        _done("S01", decision="Already decided"),
        _session("S02", decision="Should tests gate the deploy?"),
    ))
    assert [s["id"] for s in summarize(roadmap)["needs_decision"]] == ["S02"]


def test_kickoff_prompt_carries_scope_decision_and_the_update_step():
    roadmap = validate_roadmap(_roadmap(
        _session("S01", title="Gate the deploy", decision="Should tests block a deploy?", model="opus")))
    prompt = kickoff_prompt(roadmap["sessions"][0])
    assert prompt.startswith("Roadmap session S01: Gate the deploy")
    assert "Should tests block a deploy?" in prompt
    assert "Opus" in prompt
    assert "tools/roadmap.py --check" in prompt
    assert "Do not commit or push unless I ask" in prompt


# --- the dashboard -----------------------------------------------------------------

def _html(*sessions, **overrides):
    return render_html(validate_roadmap(_roadmap(*sessions, **overrides)), generated_at=_GENERATED)


def test_dashboard_has_one_meter_segment_and_one_card_per_session():
    html = _html(_done("S01"), _session("S02"), _session("S03"))
    assert html.count('data-segment="') == 3
    assert html.count('<details class="card status-') == 3
    for sid in ("S01", "S02", "S03"):
        assert f'id="{sid}"' in html


def test_dashboard_escapes_roadmap_text():
    html = _html(_session(title='<script>alert("x")</script>', why="<img src=x onerror=alert(1)>"))
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x" not in html


def test_dashboard_makes_no_external_requests():
    html = _html(_done("S01", commits=["88973b6"]))
    assert "<script src" not in html and "<link" not in html
    for url in re.findall(r'(?:src|href)="(https?://[^"]*)"', html):
        assert url.startswith("https://github.com/trmckinzie/aurelia-os/commit/"), url
    assert 'href="https://github.com/trmckinzie/aurelia-os/commit/88973b6"' in html


def test_dashboard_offers_the_next_session_and_its_prompt():
    html = _html(_done("S01"), _session("S02", title="Second session"))
    assert 'data-next="S02"' in html
    assert "Roadmap session S02: Second session" in html


def test_dashboard_says_when_every_session_is_done():
    assert "Every session is done" in _html(_done("S01"))


def test_write_dashboard_creates_the_output_folder(tmp_path):
    target = tmp_path / "nested" / "roadmap.html"
    write_dashboard(validate_roadmap(_roadmap()), str(target), generated_at=_GENERATED)
    assert target.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def _luminance(hex_color):
    channels = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_palette_meets_wcag_contrast(scheme):
    colors = PALETTE[scheme]
    for background in ("page", "surface"):
        assert _contrast(colors["ink"], colors[background]) >= 7.0, (scheme, "ink", background)
        assert _contrast(colors["ink-2"], colors[background]) >= 4.5, (scheme, "ink-2", background)
    # Status colours mark progress bars and icons, so they need the 3:1
    # non-text contrast against everything they sit on, including the track.
    for status in ("done", "active", "blocked"):
        for background in ("page", "surface", "track"):
            assert _contrast(colors[status], colors[background]) >= 3.0, (scheme, status, background)


# --- the command line ----------------------------------------------------------------

def test_check_passes_a_valid_file_and_fails_an_invalid_one(tmp_path, capsys):
    good = _write(tmp_path, _VALID_YAML, "good.yaml")
    bad = _write(tmp_path, _VALID_YAML.replace("effort: S", "effort: XL"), "bad.yaml")
    assert main(["--check", "--file", good]) == 0
    assert main(["--check", "--file", bad]) == 1
    assert "sessions[0].effort" in capsys.readouterr().err


def test_default_run_writes_the_dashboard_and_prints_a_summary(tmp_path, capsys):
    out = tmp_path / "out.html"
    assert main(["--file", _write(tmp_path, _VALID_YAML), "--output", str(out)]) == 0
    assert out.exists()
    printed = capsys.readouterr().out
    assert "1 of 2 done" in printed
    assert "Next up:" in printed and "S02 Second" in printed


def test_next_prints_the_kickoff_prompt(tmp_path, capsys):
    assert main(["--next", "--file", _write(tmp_path, _VALID_YAML)]) == 0
    assert capsys.readouterr().out.startswith("Roadmap session S02: Second")
