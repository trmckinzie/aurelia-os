---
name: roadmap-session
description: Implements one session from docs/roadmap.yaml end-to-end — reads the entry (and its dependencies), does the work, writes tests that actually check each done_when item, updates the roadmap entry, and runs the project's validators. Use when Travis asks to "do S09", "pick up the next roadmap session", or similar.
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Agent
  - Bash(.venv/bin/python tools/roadmap.py *)
  - Bash(.venv/bin/python tools/validate_vault_schema.py*)
  - Bash(.venv/bin/python -m pytest *)
  - Bash(.venv/bin/python -m pyflakes *)
  - Bash(bash verify.sh*)
  - Bash(git status*)
  - Bash(git diff*)
  - Bash(git log*)
---

# /roadmap-session — work one entry in docs/roadmap.yaml

Turns a roadmap entry into a finished, tested, documented change — the same shape every
S01...S09 session in this repo has followed by hand. Nothing here commits or pushes; that stays
gated by CLAUDE.md's "Install/change, verify, then stop" rule.

## 1. Identify the session

If Travis named one (`S09`, "the reproducibility one"), use it. Otherwise:

```
.venv/bin/python tools/roadmap.py --next
```

prints a kickoff prompt for the next unstarted session with no unmet `depends_on`, or says that
nothing is ready. When every session is done (true of S01 to S10 since 2026-10-03), the next
unit of work is a `backlog` entry or a new session that Travis adds; agree on it with him rather
than picking one. Read the chosen entry directly out of `docs/roadmap.yaml` rather than trusting
a summary — `title`, `why`, `decision` (if present and not yet `decided`, stop and ask Travis
before writing code: CLAUDE.md's decision-pending rule), `depends_on`, `tasks`, and `done_when`.

**Read every `depends_on` entry too**, not just this one. S09 built on S01; skipping that context
is how a session reinvents something an earlier one already decided.

## 2. Scope the work against the repo's own rules

Before touching anything, check `/Users/travismckinzie/dev/projects/aurelia-os/CLAUDE.md`'s "Hard
rules" — `vault/` is off-limits to modify, CI must keep `--no-sort`, voice rule for anything
user-facing, etc. A roadmap task never overrides those.

If a task would change the content model, the publication pipeline, or what the public site
renders or exposes, hand it to `garden-publication-reviewer` (Agent tool) rather than doing it
directly — see that agent's own description and `docs/ARCHITECTURE.md`'s "Privacy model". Routine
engine/template/test work can go through `generator-engine-editor` or be done directly.

## 3. Implement each task

Work the task list in `tasks`, editing engine code, templates, tests, and docs as needed. Prefer
reading the actual source over trusting the roadmap's own `why` prose — it describes the bug as
understood when the entry was written, and the real fix point is sometimes a layer removed (S09's
"deploy.py ships a dangling social preview image" turned out to be fixed in `engine/pipeline.py`
and `base.html`, not in `deploy.py` itself).

## 4. Prove `done_when`, don't just assert it

Every item in `done_when` needs an actual test behind it, not a manual check that will rot the
next time someone touches the code. If a `done_when` item describes a property existing tests
don't cover (e.g. "two builds of the same commit are byte-identical"), write the test — that is
usually itself one of the `tasks`.

Run the targeted tests as you go:

```
.venv/bin/python -m pytest tests/test_<touched_module>.py -q
.venv/bin/python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py
```

## 5. Update the roadmap entry, in the same change

In `docs/roadmap.yaml`, on this session's own entry:

- tick every `tasks[].done` you actually completed (not tasks you dropped — if you drop one,
  remove it and say why in `notes` instead of leaving it unticked forever)
- set `status: done` (or leave it short of done and say what's left, if the session didn't finish)
- set `started` / `completed` to real dates (today, almost always, for a single-sitting session)
- leave `commits: []` empty **unless** you already know the real commit hash. The squash-merge
  SHA doesn't exist until the PR actually merges, so recording it here is a follow-up change after
  that happens (`docs/roadmap.yaml`'s own convention — see how S07/S08 each got a small
  "Roadmap: record the SXX squash commit" PR after their merge). Guessing one is worse than
  leaving the field empty.

Then validate the file itself:

```
.venv/bin/python tools/roadmap.py --check
```

## 6. Run the full gate

```
bash verify.sh
```

This is the same suite CI runs on every push (pytest, pyflakes, the vault schema check,
`tools/roadmap.py --check`, a `--no-sort` build, then the Playwright/axe browser suite) — it has
to pass locally before anything goes near a PR. Fix failures and re-run rather than explaining
them away.

## 7. Stop

Leave everything in the working tree. Per CLAUDE.md: commit only when Travis asks, push only when
asked, and then only through a pull request (never a direct push to `main` — a ruleset rejects
it). Summarize what changed and what's next; don't open a PR unprompted.
