# Travis R. McKinzie — personal site and digital garden

This repo (still named `aurelia-os` on GitHub, its original codename) is the generator behind
Travis R. McKinzie's professional site and working notebook: a personal static-site generator that
turns an [Obsidian](https://obsidian.md) vault into a published digital garden / working notebook —
atomic notes (concepts, sources, authors, disciplines, daily logs, Gemini Notebook syntheses, deep
dives) linked the way a Zettelkasten links, rendered, styled, and published as a real website with
the link graph itself made visible and navigable.

**Live site:** [trmckinzie.github.io/aurelia-os](https://trmckinzie.github.io/aurelia-os/)

## What it does

- Converts Obsidian markdown notes (with YAML frontmatter and `[[wikilinks]]`) into a published,
  searchable, browsable garden — grid, tree, and force-directed knowledge-graph views.
- Only notes tagged `publish: true` are *rendered into the site*. This controls rendering, not
  access — see [Privacy model](#privacy-model) below before assuming anything in `vault/` is private.
- Real backlinks, note-maturity badges (🌱 seed / 🌿 growing / 🌳 evergreen), topic browsing, a
  command palette (⌘K), a random-note discovery button, an "On this page" outline for long notes,
  and a `?` keyboard-shortcut sheet.
- A study layer grounded in the learning-science evidence (practice testing, distributed
  practice, interleaving, elaboration): an optional Study mode covers each note's definition with
  a "Try to recall it first" prompt, a four-step self-rating feeds an SM-2 spaced-repetition
  scheduler, a review queue walks the due notes interleaved across types, flashcard decks study
  one card at a time with the same scheduler, and a small "How does this connect?" nudge suggests
  neighbouring notes to relate. All progress lives in the reader's own browser (localStorage) with
  a JSON export/import to move it between devices; nothing is sent anywhere.
- Wikilinks resolve through frontmatter `aliases:` and unique parenthetical title suffixes, so
  `[[Dopamine]]` reaches `Dopamine (Reward Prediction Error)` without a rename.
- A professional About page (`about.html`) — roles, education, skills, selected work, and
  schema.org `Person` structured data — rendered from a repo-root `profile.json`. The file is
  validated strictly at build time (unknown keys, non-`http`/`https`/`mailto` URLs, over-long or
  missing fields all fail the build), and every value is escaped on output; it carries no HTML.
- A light and a dark theme in the nav's theme menu (no rebuild required — swappable via
  `<html data-theme>` and a single CSS-variable source of truth): `TIMBERLINE` (light/professional,
  the default, the TRM / Pine personal brand palette) and `CYBER_PRIME` (dark/neon). Three more
  themes, each with its own palette, typography, and material language, are built and tested but
  not offered for now: `THE_PATRIOT` (light/civic, USWDS-grounded), `THE_STOA` (Stoic
  Greco-Roman/Helvetic), and `GRIZZ` (dark, Adams State University green/black/white).
- Gemini Notebook export support: audio/video overviews, flashcard decks, mind maps and other
  synthesis assets are auto-detected from the export's headers and rendered as interactive widgets,
  with each top-level section collapsible in the note reader. **Note:** the media files themselves
  are no longer committed to this repo (see [Media](#media)); a note that still names an audio,
  video, or image file the build can't resolve has that reference dropped rather than rendered as
  a broken widget — the header and surrounding prose stay, the note just reads as text there.
  Flashcard decks still work — those are small CSVs, and each renders as a one-card study widget
  (Show answer, rate 1–4, shuffle, "due cards only").

## Stack

Python + [Jinja2](https://jinja.palletsprojects.com/) for templating, [PyYAML](https://pyyaml.org/)
for real frontmatter parsing, and [Tailwind CSS](https://tailwindcss.com/) (compiled at build time
via the CLI, not the CDN). No JS framework or bundler — the client-side interactivity is plain JS:
search, graph rendering and the modal reader ship inline in the page templates, while the study
layer (`assets/js/review.js`), the flashcard widgets (`assets/js/flashcards.js`) and a shared
escaping helper (`assets/js/utils.js`) ship as separately cached files.

## Getting started

```bash
# One-time setup. Versions live in .python-version and .nvmrc, the files CI reads too.
# Run from a virtual environment: uv venv --python 3.14 (or python3 -m venv .venv).
pip install --require-hashes -r requirements-dev.txt   # Python deps + pytest + pyflakes, hash-checked
                                                       # (requirements.txt alone is enough to just build)
npm ci                                                 # Tailwind CLI, from package-lock.json

# Build the site (writes to dist/, rebuilt from scratch every run)
python build.py

# Build without touching the vault. The Drop Zone sort is the one build step
# that WRITES to vault/ -- it moves files out of vault/99_DROP_ZONE into
# vault/assets/<kind>/ -- so a plain `python build.py` mutates the vault as a
# side effect. Skip it when the working tree must stay clean: CI, a review
# checkout, or any session under a no-vault-edits rule. dist/ is identical
# either way; the drop zone just stays unsorted.
python build.py --no-sort
AURELIA_SKIP_DROPZONE=1 python build.py     # same thing, for CI

# Tests
python -m pytest tests/ -q

# Lint
python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py

# Validate every published vault note against the canonical frontmatter schema
python tools/validate_vault_schema.py

# Advisory vault-health reports: pending-atomization queue, orphaned notes,
# maturity-promotion candidates (read-only, never edits the vault)
python tools/vault_health.py

# What CI builds: any warning (malformed frontmatter, a missing asset, an
# ambiguous alias) exits 1 instead of shipping a degraded site. A plain local
# build prints the same warnings and carries on.
python build.py --no-sort --strict

# Full check suite (pytest, pyflakes, schema, roadmap, --no-sort build, then the
# Playwright browser suite with axe accessibility checks on that build) --
# the checks CI runs, where the build also gets --strict. A pull request cannot merge, and the site cannot deploy,
# until they pass. Run before pushing.
bash verify.sh

# Serve dist/ locally at http://localhost:8791 (Node, so it is the same on every OS)
node tools/preview.mjs
```

### Setting up on macOS

The same steps work on any Mac; nothing in the repo depends on Windows. CI runs `verify.sh` on
macOS as well as Ubuntu, in the `check-macos` job.

1. Install Python 3.14 and Node 24, the versions in `.python-version` and `.nvmrc`. Homebrew
   (`brew install python@3.14`) and the python.org and nodejs.org installers all work, as does
   any version manager that reads those two files (`uv`, `pyenv`, `fnm`, `nvm`).
2. Clone the repo and create the virtual environment, always inside the repo folder:

   ```bash
   python3.14 -m venv .venv
   .venv/bin/pip install --require-hashes -r requirements-dev.txt
   npm ci
   ```

3. Run the full suite. `verify.sh` finds `.venv/bin/python` on its own, so there is nothing to
   activate:

   ```bash
   bash verify.sh
   ```

4. Preview the built site with `node tools/preview.mjs`, or start the `dist-preview` entry from
   `.claude/launch.json` in Claude Code.

VS Code needs no interpreter setting: the Python extension picks up `.venv` at the repo root.
For everything git does not carry over (local drafts, per-machine Claude Code files, the hook
wiring), see [docs/MOVING-MACHINES.md](docs/MOVING-MACHINES.md).

### Dependency locks

`requirements.in` and `requirements-dev.in` hold the direct dependencies, pinned exactly; they are
the files to edit. `requirements.txt` and `requirements-dev.txt` are generated from them with
sha256 hashes for every package on every platform, and CI installs them with `--require-hashes`, so
a package that changes upstream fails the install instead of slipping in. After changing a pin,
regenerate both (needs [uv](https://docs.astral.sh/uv/)):

```bash
uv pip compile requirements.in --universal --generate-hashes --python-version 3.14 -o requirements.txt
uv pip compile requirements-dev.in --universal --generate-hashes --python-version 3.14 -o requirements-dev.txt
```

`tests/test_requirements_lock.py` fails if the `.in` files and the locks disagree, or if a locked
package has lost its hashes. Node dependencies were already locked, by `package-lock.json`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture writeup — build pipeline,
the wikilink/backlink system, the theming architecture — and [docs/DECISIONS.md](docs/DECISIONS.md)
for the reasoning behind design decisions. [CLAUDE.md](CLAUDE.md) is the short entry point for
Claude Code sessions.

## Project structure

```
build.py               Entry point (python build.py)
engine/                 All real build logic: parsing, extraction, card rendering, theming, pipeline
profile.json            The About page's content: structured data validated at build time, not a vault note
system/templates/       Jinja2 templates (base + Lobby + Garden + About + 404)
assets/                 Tailwind input CSS; client JS (utils, study layer, flashcards); site images
vault/                  The Obsidian vault itself -- source content, not source code (see License)
tests/                  pytest suite (unit) and tests/browser/ (Playwright + axe, against a built dist/)
tools/                  Standalone scripts (vault schema validator, vault-health reports, roadmap dashboard, preview server)
docs/                   Architecture writeup, decision log, and machine-migration/rollback notes
deploy.py               Generates a white-labeled clone of the tooling for someone else to reuse
.github/workflows/      CI: check/build/deploy, a tag-based redeploy for rollback, and a weekly build + live-site check
```

## Privacy model

**This repository is public, so everything committed to `vault/` is publicly readable — including
notes marked `publish: false`.**

`publish:` is a *rendering* flag consumed by `engine/pipeline.py`. It decides what becomes a card on
the site. It is not an access control, and it never was:

| | Rendered into `dist/` | Readable on GitHub |
|---|---|---|
| `publish: true` note | yes | yes |
| `publish: false` note | no | **yes** |
| Media no published note references | no (publish gate) | **yes** |
| Anything else in `vault/` | no | **yes** |

The same applies to the media publish gate in `engine/assets_pipeline.py`: a media file reaches
`dist/` only when a published note references it, and the build lists what it left behind, but
leaving a file out of `dist/` keeps it off the *website*, not out of the *repository*.

One further caveat, learned the hard way: `publish:` and the sync carve-out both govern the
*current* build. Git keeps every past version of every committed file, so anything committed once
stays readable in history even after it is deleted — removing it for real requires rewriting
history, not a delete commit.

If you fork this or run it on your own vault, decide up front which of these you want:

1. **Public vault** (what this repo does today) — treat every file you commit as published, whatever
   its frontmatter says.
2. **Private vault, public site** — keep the vault in a private repo and have CI push only the
   built `dist/` to a separate public Pages repo. This is the only arrangement in which
   `publish: false` actually means private.

## Media

**No vault media is committed to this repository.** `vault/assets/` does not exist in the repo
at all (git tracks no empty directories); the only tracked assets are the Tailwind input CSS, three
JS files (`utils.js`, `review.js`, `flashcards.js`), five small flashcard CSVs, and two small site
images under `assets/images/` (the author headshot shown on the home and About pages, and the
social-preview card it was generated from).

Gemini Notebook audio exports ran 64–79 MB each and had grown to ~858 MB, which pushed the published
site to 88% of GitHub Pages' 1 GB ceiling and made every clone and CI checkout pay for all of it.
They were removed from the repository and its history in 2026; `dist/` went from ~882 MB to
~5.7 MB. Media of that size belongs in object storage, linked from the notes rather than bundled
into the site — that's the intended direction, not yet built.

`engine/assets_pipeline.py` still compresses drop-zone audio over 15 MB via ffmpeg when it's
installed, which is what keeps new media from re-inflating the repo in the meantime.

## Version history

This project has no version numbers and no published packages, and the live site is whatever
`main` last built. Every deploy that passes its post-deploy live check is tagged
(`deploy-<time>-<commit>`) and published as a GitHub release with generated notes: a record of
what went live, for rolling back, not a version line (see [docs/ROLLBACK.md](docs/ROLLBACK.md)).
The milestone-by-milestone history, and the reasoning
behind each change, lives in one place: the decision log in
[docs/DECISIONS.md](docs/DECISIONS.md#recent-history-why-the-code-looks-like-this). Keeping it in
one file is deliberate — two dated chronologies of the same project drift apart the moment one of
them stops getting updated, which is exactly what happened to the table this section used to
carry.

## License

The generator code (`engine/`, `system/`, `assets/`, `build.py`, `deploy.py`, `tests/`, and other
project tooling) is licensed under the [MIT License](LICENSE) — reuse, fork, and adapt it freely.

The contents of `vault/` are the author's personal notes, journal entries, and original writing.
They are **not** covered by that license, remain all rights reserved, and are not licensed for
reuse or republication. See the scope note at the bottom of [LICENSE](LICENSE) for the exact
carve-out.

Reserving rights is a statement about *reuse*, not about *visibility* — see
[Privacy model](#privacy-model). Note also that this carve-out covers only the author's own
writing; it does not, and cannot, extend a license to any third-party material that happens to
sit in the vault.

## Security

This is a personal project with no formal support channel, but see [SECURITY.md](SECURITY.md) if
you find a security issue in the generator itself.
