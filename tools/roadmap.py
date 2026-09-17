"""Engineering roadmap: validates docs/roadmap.yaml and renders it as a
progress dashboard.

docs/roadmap.yaml holds the priority-ordered work sessions for making this repo
robust -- CI/CD, tests, security settings, docs -- plus a backlog of smaller
findings. Each session lists its tasks and the checks that say it is finished,
and a session that completes roadmap work updates its own entry in the same
change. This script is the only thing that reads the file:

    python tools/roadmap.py           validate, print a summary, write the dashboard
    python tools/roadmap.py --open    the same, then open the dashboard in a browser
    python tools/roadmap.py --check   validate only; exits 1 on any problem
    python tools/roadmap.py --next    print a kickoff prompt for the next session

The dashboard is written to reports/roadmap.html (gitignored), never into
dist/. It is a maintainer's tool, not a page of the published site, whose
three-page shape is deliberate (see docs/DECISIONS.md). It is one
self-contained file with no external requests, so it opens straight from disk.

Why fail loud, and why no jsonschema: the reasoning engine/profile.py records
for profile.json applies unchanged. The file is edited by hand and by Claude
sessions, a typo must never render a dashboard that misstates how much is
done, and a small hand-written validator is easier to read and extend than a
schema document. Every error names the field it is about, e.g.
"roadmap.yaml: sessions[2].tasks[0].done: must be true or false".
"""
import argparse
import datetime
import os
import pathlib
import re
import sys
import webbrowser

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't encode
# the block characters and emoji this script prints -- same fix as build.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import yaml  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROADMAP_PATH = os.path.join(ROOT_DIR, "docs", "roadmap.yaml")
OUTPUT_PATH = os.path.join(ROOT_DIR, "reports", "roadmap.html")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "tools", "templates")

SCHEMA_VERSION = 1

STATUS_LABELS = {
    "todo": "To do",
    "in_progress": "In progress",
    "blocked": "Blocked",
    "done": "Done",
}
EFFORT_LABELS = {"S": "Small", "M": "Medium", "L": "Large"}

# 90_Meta/Model Routing.md in the dev mono-vault: Sonnet executes, Opus
# escalates, and a Fable session is only ever Travis's explicit call. A roadmap
# entry naming Fable would be pre-booking one, and `best` resolves to Fable.
MODEL_LABELS = {"sonnet": "Sonnet", "opus": "Opus"}
_FORBIDDEN_MODELS = frozenset({"fable", "best"})

BACKLOG_STATUS_LABELS = {"open": "Open", "done": "Done", "dropped": "Dropped"}

# Dashboard colours, injected into the page as CSS custom properties. They live
# here rather than in the template so tests/test_roadmap.py can hold each one to
# WCAG contrast against the surfaces it sits on, the way tests/test_theming.py
# holds THEME_CONFIG. Light borrows TIMBERLINE's paper and ink. The three status
# colours are the only coloured marks on the page and always sit beside an icon
# and a text label. They were checked as a set: every pair stays at least 8
# OKLab delta-E apart under simulated protanopia and deuteranopia, and at least
# 15 apart for full colour vision, in both schemes.
PALETTE = {
    "light": {
        "page": "#f5f2eb",
        "surface": "#fdfcf9",
        "ink": "#1a2a33",
        "ink-2": "#4d5a63",
        "hairline": "#e2dbcd",
        "track": "#e9e3d7",
        "done": "#1f8a5b",
        "active": "#2d6fc0",
        "blocked": "#c8480c",
    },
    "dark": {
        "page": "#0f161b",
        "surface": "#172229",
        "ink": "#e8edf0",
        "ink-2": "#b3bfc7",
        "hairline": "#2a3942",
        "track": "#26343d",
        "done": "#41a06f",
        "active": "#4f8fd6",
        "blocked": "#e0702f",
    },
}

_SESSION_ID_RE = re.compile(r"^S\d{2}$")
_BACKLOG_ID_RE = re.compile(r"^B\d{2}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REPO_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

_TOP_ALLOWED = {"schema_version", "title", "updated", "repository", "sessions", "backlog"}
_TOP_REQUIRED = {"schema_version", "title", "updated", "sessions"}

_SESSION_ALLOWED = {
    "id", "title", "status", "area", "effort", "model", "why", "decision",
    "blocker", "depends_on", "tasks", "done_when", "started", "completed",
    "commits", "notes",
}
_SESSION_REQUIRED = {"id", "title", "status", "area", "effort", "model", "why", "tasks", "done_when"}

_TASK_KEYS = {"text", "done"}

_BACKLOG_ALLOWED = {"id", "title", "area", "status", "detail", "decision"}
_BACKLOG_REQUIRED = {"id", "title", "area", "status"}


class RoadmapError(ValueError):
    """Raised for any problem loading or validating the roadmap file.

    Every message starts with "roadmap.yaml:" followed, when one is known, by a
    dotted/indexed path to the offending field -- the same shape as
    engine/profile.py's ProfileError, so a failure reads the same way in the
    terminal and in a pytest report.
    """


class _StrictLoader(yaml.SafeLoader):
    """yaml.SafeLoader, except that a mapping repeating a key is an error.

    Plain safe_load keeps the last value without a word, so a hand-edited
    session carrying two `status:` lines would quietly report whichever came
    second -- exactly the kind of silent misstatement this file must not make.
    """

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
            seen = set()
            for key_node, _value_node in node.value:
                key = self.construct_object(key_node, deep=True)
                try:
                    repeated = key in seen
                except TypeError:  # unhashable key: the base class reports it
                    break
                if repeated:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping", node.start_mark,
                        f"found duplicate key '{key}'", key_node.start_mark)
                seen.add(key)
        return super().construct_mapping(node, deep=deep)


# --- validation helpers ------------------------------------------------------

def _fail(path, msg):
    if path:
        raise RoadmapError(f"roadmap.yaml: {path}: {msg}")
    raise RoadmapError(f"roadmap.yaml: {msg}")


def _join(parent, key):
    return f"{parent}.{key}" if parent else key


def _check_mapping(value, path, allowed, required):
    if not isinstance(value, dict):
        _fail(path, "must be a set of key: value fields")
    for key in value:
        if key not in allowed:
            _fail(path, f"unknown key '{key}'")
    for key in sorted(required):
        if key not in value:
            _fail(_join(path, key), "is required")


def _check_list(value, path, max_len, min_len=0):
    if not isinstance(value, list):
        _fail(path, "must be a list")
    if len(value) < min_len:
        _fail(path, f"must have at least {min_len} item{'s' if min_len != 1 else ''}")
    if len(value) > max_len:
        _fail(path, f"must have at most {max_len} items")


def _check_str(value, path, max_len, multiline=False):
    """Non-empty text of at most max_len characters. Single-line fields may
    not contain a line break once surrounding whitespace is trimmed (YAML's `>`
    style leaves a trailing newline, which is fine)."""
    if not isinstance(value, str):
        _fail(path, "must be text")
    text = value.strip()
    if not text:
        _fail(path, "must not be empty")
    if len(text) > max_len:
        _fail(path, f"is {len(text)} characters; the limit is {max_len}")
    if not multiline and "\n" in text:
        _fail(path, "must be a single line")
    return text


def _check_enum(value, labels, path):
    if not isinstance(value, str) or value not in labels:
        _fail(path, f"must be one of: {', '.join(labels)}")
    return value


def _check_date(value, path):
    """None, or a calendar date. YAML reads an unquoted 2026-09-15 as a date
    and a quoted one as text; both are accepted and returned as a date."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        _fail(path, "must be a date like 2026-09-15, without a time")
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and _DATE_RE.match(value.strip()):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            pass
    _fail(path, "must be a date like 2026-09-15")


def _optional_text(raw, key, path, max_len):
    if raw.get(key) is None:
        return None
    return _check_str(raw[key], _join(path, key), max_len, multiline=True)


def _duplicates(ids):
    return sorted({i for i in ids if ids.count(i) > 1})


def _find_cycle(sessions):
    """One dependency cycle as a list of ids that ends where it started
    (["S01", "S02", "S01"]), or None when the dependencies form no loop."""
    depends_on = {s["id"]: s["depends_on"] for s in sessions}
    state = {}
    stack = []

    def visit(node):
        state[node] = "visiting"
        stack.append(node)
        for dep in depends_on[node]:
            if state.get(dep) == "visiting":
                return stack[stack.index(dep):] + [dep]
            if dep not in state:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        state[node] = "visited"
        return None

    for session in sessions:
        if session["id"] not in state:
            found = visit(session["id"])
            if found:
                return found
    return None


# --- validation ----------------------------------------------------------------

def _validate_session(raw, path):
    _check_mapping(raw, path, _SESSION_ALLOWED, _SESSION_REQUIRED)
    if not isinstance(raw["id"], str) or not _SESSION_ID_RE.match(raw["id"]):
        _fail(_join(path, "id"), "must look like S01")

    model = raw["model"]
    if isinstance(model, str) and model.strip().lower() in _FORBIDDEN_MODELS:
        _fail(_join(path, "model"),
              "a roadmap entry never pre-books Fable: Sonnet executes, Opus escalates, and a "
              "Fable session is Travis's explicit call (90_Meta/Model Routing.md)")

    session = {
        "id": raw["id"],
        "title": _check_str(raw["title"], _join(path, "title"), 120),
        "status": _check_enum(raw["status"], STATUS_LABELS, _join(path, "status")),
        "area": _check_str(raw["area"], _join(path, "area"), 40),
        "effort": _check_enum(raw["effort"], EFFORT_LABELS, _join(path, "effort")),
        "model": _check_enum(model, MODEL_LABELS, _join(path, "model")),
        "why": _check_str(raw["why"], _join(path, "why"), 1200, multiline=True),
        "decision": _optional_text(raw, "decision", path, 600),
        "blocker": _optional_text(raw, "blocker", path, 400),
        "notes": _optional_text(raw, "notes", path, 1200),
    }

    _check_list(raw["tasks"], _join(path, "tasks"), max_len=30, min_len=1)
    session["tasks"] = []
    for i, task in enumerate(raw["tasks"]):
        task_path = f"{path}.tasks[{i}]"
        _check_mapping(task, task_path, _TASK_KEYS, _TASK_KEYS)
        text = _check_str(task["text"], f"{task_path}.text", 300)
        if not isinstance(task["done"], bool):
            _fail(f"{task_path}.done", "must be true or false")
        session["tasks"].append({"text": text, "done": task["done"]})

    _check_list(raw["done_when"], _join(path, "done_when"), max_len=15, min_len=1)
    session["done_when"] = [
        _check_str(item, f"{path}.done_when[{i}]", 300) for i, item in enumerate(raw["done_when"])
    ]

    depends_on = raw.get("depends_on")
    depends_on = [] if depends_on is None else depends_on
    _check_list(depends_on, _join(path, "depends_on"), max_len=10)
    for i, dep in enumerate(depends_on):
        if not isinstance(dep, str) or not _SESSION_ID_RE.match(dep):
            _fail(f"{path}.depends_on[{i}]", "must be a session id like S01")
    if _duplicates(depends_on):
        _fail(_join(path, "depends_on"), "lists the same session twice")
    session["depends_on"] = list(depends_on)

    commits = raw.get("commits")
    commits = [] if commits is None else commits
    _check_list(commits, _join(path, "commits"), max_len=50)
    for i, sha in enumerate(commits):
        if not isinstance(sha, str) or not _COMMIT_RE.match(sha):
            _fail(f"{path}.commits[{i}]",
                  "must be a commit hash: 7 to 40 lowercase hex characters, in quotes if it is all digits")
    session["commits"] = list(commits)

    started = _check_date(raw.get("started"), _join(path, "started"))
    completed = _check_date(raw.get("completed"), _join(path, "completed"))
    status = session["status"]
    open_tasks = sum(1 for task in session["tasks"] if not task["done"])
    if status == "done":
        if completed is None:
            _fail(_join(path, "completed"), "is required once status is done")
        if open_tasks:
            _fail(_join(path, "status"),
                  f"is done but {open_tasks} task{'s are' if open_tasks != 1 else ' is'} not ticked; "
                  "tick them, or remove a dropped task and say why in notes")
    elif completed is not None:
        _fail(_join(path, "completed"), f"is set but status is {status}")
    if status == "in_progress" and started is None:
        _fail(_join(path, "started"), "is required once status is in_progress")
    if status == "todo" and started is not None:
        _fail(_join(path, "started"), "is set but status is todo; use in_progress")
    if started is not None and completed is not None and completed < started:
        _fail(_join(path, "completed"), "is earlier than started")
    if status == "blocked" and session["blocker"] is None:
        _fail(_join(path, "blocker"), "is required when status is blocked: say what it is waiting on")
    if status != "blocked" and session["blocker"] is not None:
        _fail(_join(path, "blocker"), f"is only for blocked sessions; this one is {status}")
    session["started"] = started
    session["completed"] = completed
    return session


def _validate_backlog_item(raw, path):
    _check_mapping(raw, path, _BACKLOG_ALLOWED, _BACKLOG_REQUIRED)
    if not isinstance(raw["id"], str) or not _BACKLOG_ID_RE.match(raw["id"]):
        _fail(_join(path, "id"), "must look like B01")
    return {
        "id": raw["id"],
        "title": _check_str(raw["title"], _join(path, "title"), 160),
        "area": _check_str(raw["area"], _join(path, "area"), 40),
        "status": _check_enum(raw["status"], BACKLOG_STATUS_LABELS, _join(path, "status")),
        "detail": _optional_text(raw, "detail", path, 800),
        "decision": _optional_text(raw, "decision", path, 600),
    }


def validate_roadmap(data):
    """Validates a parsed roadmap and returns a normalized copy: text trimmed,
    dates as datetime.date, optional fields present as None or []. Raises
    RoadmapError on the first problem found."""
    _check_mapping(data, "", _TOP_ALLOWED, _TOP_REQUIRED)
    version = data["schema_version"]
    if isinstance(version, bool) or version != SCHEMA_VERSION:
        _fail("schema_version", f"must be {SCHEMA_VERSION}")

    title = _check_str(data["title"], "title", 80)
    updated = _check_date(data["updated"], "updated")
    if updated is None:
        _fail("updated", "must be a date like 2026-09-15")
    repository = data.get("repository")
    if repository is not None and (not isinstance(repository, str) or not _REPO_URL_RE.match(repository)):
        _fail("repository", "must be a GitHub repository URL like https://github.com/owner/name")

    _check_list(data["sessions"], "sessions", max_len=30, min_len=1)
    sessions = [_validate_session(raw, f"sessions[{i}]") for i, raw in enumerate(data["sessions"])]
    repeated = _duplicates([s["id"] for s in sessions])
    if repeated:
        _fail("sessions", f"duplicate session id(s): {', '.join(repeated)}")
    known = {s["id"] for s in sessions}
    for i, session in enumerate(sessions):
        for dep in session["depends_on"]:
            if dep == session["id"]:
                _fail(f"sessions[{i}].depends_on", "a session cannot depend on itself")
            if dep not in known:
                _fail(f"sessions[{i}].depends_on", f"'{dep}' is not a session in this file")
    cycle = _find_cycle(sessions)
    if cycle:
        _fail("sessions", f"dependency cycle: {' -> '.join(cycle)}")

    backlog_raw = data.get("backlog")
    backlog_raw = [] if backlog_raw is None else backlog_raw
    _check_list(backlog_raw, "backlog", max_len=100)
    backlog = [_validate_backlog_item(raw, f"backlog[{i}]") for i, raw in enumerate(backlog_raw)]
    repeated = _duplicates([b["id"] for b in backlog])
    if repeated:
        _fail("backlog", f"duplicate backlog id(s): {', '.join(repeated)}")

    return {
        "schema_version": version,
        "title": title,
        "updated": updated,
        "repository": repository,
        "sessions": sessions,
        "backlog": backlog,
    }


def load_roadmap(path=ROADMAP_PATH):
    """Reads, parses and validates a roadmap file; returns the normalized roadmap."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        _fail("", f"file not found at {path}")
    try:
        data = yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"line {mark.line + 1}, column {mark.column + 1}" if mark else "position unknown"
        _fail("", f"is not valid YAML ({where}): {getattr(exc, 'problem', None) or exc}")
    if data is None:
        _fail("", "is empty")
    return validate_roadmap(data)


# --- progress ------------------------------------------------------------------

def _percent(part, whole):
    return int(100 * part / whole + 0.5) if whole else 0


def _waiting_on(session, by_id):
    """Dependencies of `session` that are not done yet."""
    return [dep for dep in session["depends_on"] if by_id[dep]["status"] != "done"]


def summarize(roadmap):
    """Progress numbers shared by the dashboard and the terminal summary.

    `next_up` is an in-progress session when there is one -- finishing beats
    starting -- and otherwise the earliest-listed to-do session whose
    dependencies are all done. Blocked sessions are never next. It is None
    when nothing is ready.
    """
    sessions = roadmap["sessions"]
    by_id = {s["id"]: s for s in sessions}
    counts = {status: 0 for status in STATUS_LABELS}
    for session in sessions:
        counts[session["status"]] += 1
    tasks_total = sum(len(s["tasks"]) for s in sessions)
    tasks_done = sum(1 for s in sessions for task in s["tasks"] if task["done"])

    in_progress = [s for s in sessions if s["status"] == "in_progress"]
    ready = [s for s in sessions if s["status"] == "todo" and not _waiting_on(s, by_id)]
    next_up = (in_progress or ready or [None])[0]

    return {
        "total": len(sessions),
        "counts": counts,
        "done": counts["done"],
        "percent": _percent(counts["done"], len(sessions)),
        "tasks_done": tasks_done,
        "tasks_total": tasks_total,
        "tasks_percent": _percent(tasks_done, tasks_total),
        "in_progress": in_progress,
        "blocked": [s for s in sessions if s["status"] == "blocked"],
        "needs_decision": [s for s in sessions if s["decision"] and s["status"] != "done"],
        "next_up": next_up,
        "backlog_open": sum(1 for item in roadmap["backlog"] if item["status"] == "open"),
    }


def kickoff_prompt(session):
    """A ready-to-paste opening message for the Claude Code session that will
    do `session`'s work."""
    sid = session["id"]
    lines = [
        f"Roadmap session {sid}: {session['title']}",
        "",
        f"Work in this repo (aurelia-os) and follow CLAUDE.md. The {sid} entry in docs/roadmap.yaml "
        "is the scope: its tasks are the work, and its done_when list is how we will know it is finished.",
    ]
    if session["depends_on"]:
        lines += ["", f"It builds on {', '.join(session['depends_on'])}; check those entries first."]
    if session["decision"]:
        lines += ["", f"Before changing anything, ask me to decide this: {session['decision']}"]
    lines += [
        "",
        f"Suggested model: {MODEL_LABELS[session['model']]} (90_Meta/Model Routing.md).",
        "",
        f"When you finish, update the {sid} entry in docs/roadmap.yaml in the same change: tick the tasks "
        "you completed, and set status, the started and completed dates, and the commit hashes. Then run "
        "`python tools/roadmap.py --check`. Do not commit or push unless I ask.",
    ]
    return "\n".join(lines)


def format_summary(roadmap, summary):
    """The terminal version of the dashboard's headline, a few lines long."""
    blocks = {"done": "█", "in_progress": "▓", "blocked": "▓", "todo": "░"}
    meter = "".join(blocks[s["status"]] for s in roadmap["sessions"])
    lines = [
        f"{roadmap['title']} (updated {roadmap['updated'].isoformat()})",
        f"  Sessions   {meter}  {summary['done']} of {summary['total']} done ({summary['percent']}%)",
        f"  Tasks      {summary['tasks_done']} of {summary['tasks_total']} done ({summary['tasks_percent']}%)",
    ]
    for session in summary["in_progress"]:
        lines.append(f"  In progress: {session['id']} {session['title']}")
    for session in summary["blocked"]:
        lines.append(f"  Blocked:     {session['id']} {session['title']} -- {session['blocker']}")
    next_up = summary["next_up"]
    if next_up is not None and next_up["status"] == "todo":
        lines.append(f"  Next up:     {next_up['id']} {next_up['title']} "
                     f"({MODEL_LABELS[next_up['model']]}, {EFFORT_LABELS[next_up['effort']].lower()} effort)")
    elif next_up is None and summary["done"] < summary["total"]:
        lines.append("  Next up:     nothing is ready; every remaining session is blocked or waiting on another")
    elif summary["done"] == summary["total"]:
        lines.append("  Every session is done.")
    if summary["needs_decision"]:
        lines.append("  Needs your decision: " + ", ".join(s["id"] for s in summary["needs_decision"]))
    if summary["backlog_open"]:
        lines.append(f"  Backlog:     {summary['backlog_open']} open item(s)")
    return "\n".join(lines)


# --- dashboard -----------------------------------------------------------------

def _shortdate(value):
    """datetime.date(2026, 9, 15) -> 'Sep 15, 2026'. The day is formatted by
    hand because strftime's no-leading-zero flag differs between Windows and
    POSIX (the same reason as engine/config.py's _longdate)."""
    return f"{value:%b} {value.day}, {value.year}"


def _segment_fill(status, tasks_percent):
    """How much of a session's meter segment is filled. An in-progress or
    blocked session with nothing ticked still shows a sliver, so started work
    never reads as untouched."""
    if status == "done":
        return 100
    if status in ("in_progress", "blocked"):
        return max(tasks_percent, 8)
    return 0


def _session_view(session, index, by_id, repository, next_up):
    tasks_done = sum(1 for task in session["tasks"] if task["done"])
    tasks_total = len(session["tasks"])
    tasks_percent = _percent(tasks_done, tasks_total)
    view = dict(session)
    view.update({
        "number": index + 1,
        "status_label": STATUS_LABELS[session["status"]],
        "effort_label": EFFORT_LABELS[session["effort"]],
        "model_label": MODEL_LABELS[session["model"]],
        "tasks_done": tasks_done,
        "tasks_total": tasks_total,
        "tasks_percent": tasks_percent,
        "segment_fill": _segment_fill(session["status"], tasks_percent),
        "waiting_on": [] if session["status"] == "done" else _waiting_on(session, by_id),
        "is_next": next_up is not None and next_up["id"] == session["id"],
        "commit_links": [
            {"label": sha[:7], "url": f"{repository}/commit/{sha}" if repository else None}
            for sha in session["commits"]
        ],
    })
    return view


def render_html(roadmap, generated_at=None):
    """The dashboard as one self-contained HTML document (a str)."""
    summary = summarize(roadmap)
    next_up = summary["next_up"]
    by_id = {s["id"]: s for s in roadmap["sessions"]}
    sessions = [
        _session_view(session, i, by_id, roadmap["repository"], next_up)
        for i, session in enumerate(roadmap["sessions"])
    ]
    next_view = next((view for view in sessions if view["is_next"]), None)
    backlog = [dict(item, status_label=BACKLOG_STATUS_LABELS[item["status"]]) for item in roadmap["backlog"]]
    generated_at = generated_at or datetime.datetime.now()

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["shortdate"] = _shortdate
    return env.get_template("roadmap.html").render(
        roadmap=roadmap,
        summary=summary,
        sessions=sessions,
        next_view=next_view,
        prompt=kickoff_prompt(next_up) if next_up else None,
        backlog=backlog,
        palette=PALETTE,
        status_labels=STATUS_LABELS,
        generated=f"{_shortdate(generated_at)} at {generated_at:%H:%M}",
    )


def write_dashboard(roadmap, output_path=OUTPUT_PATH, generated_at=None):
    """Renders the dashboard to output_path, creating its folder; returns the path."""
    html = render_html(roadmap, generated_at)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return output_path


def _display_path(path):
    """Repo-relative when the path is inside the repo, otherwise absolute."""
    path = os.path.abspath(path)
    try:
        relative = os.path.relpath(path, ROOT_DIR)
    except ValueError:  # a different drive on Windows
        return path
    return path if relative.startswith("..") else relative


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate docs/roadmap.yaml and render the engineering roadmap dashboard.")
    parser.add_argument("--file", default=ROADMAP_PATH, help="roadmap file to read (default: docs/roadmap.yaml)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate only; exit 1 on any problem")
    mode.add_argument("--next", action="store_true", help="print a kickoff prompt for the next session")
    parser.add_argument("--output", default=OUTPUT_PATH,
                        help="where to write the dashboard (default: reports/roadmap.html)")
    parser.add_argument("--open", action="store_true", help="open the dashboard in the default browser")
    args = parser.parse_args(argv)

    try:
        roadmap = load_roadmap(args.file)
    except RoadmapError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    summary = summarize(roadmap)

    if args.check:
        print(f"✅ {_display_path(args.file)} is valid: {summary['total']} sessions, "
              f"{summary['tasks_total']} tasks, {len(roadmap['backlog'])} backlog items.")
        return 0

    if args.next:
        if summary["next_up"] is None:
            print("Nothing is ready to start: every remaining session is done, blocked, or waiting on another.")
        else:
            print(kickoff_prompt(summary["next_up"]))
        return 0

    path = write_dashboard(roadmap, args.output)
    print(format_summary(roadmap, summary))
    print(f"\n  Dashboard:   {_display_path(path)}")
    if args.open and not webbrowser.open(pathlib.Path(path).resolve().as_uri()):
        print("  (Could not open a browser; open the file above by hand.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
