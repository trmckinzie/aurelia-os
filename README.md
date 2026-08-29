# Aurelia OS

A personal static-site generator that turns an [Obsidian](https://obsidian.md) vault into a
published digital garden — an **external cortex**: atomic notes (concepts, sources, authors,
disciplines, daily logs, NotebookLM syntheses, deep dives) linked the way a Zettelkasten links, rendered,
styled, and published as a real website with the link graph itself made visible and navigable.

**Live site:** [trmckinzie.github.io/aurelia-os](https://trmckinzie.github.io/aurelia-os/)

## What it does

- Converts Obsidian markdown notes (with YAML frontmatter and `[[wikilinks]]`) into a published,
  searchable, browsable garden — grid, tree, and force-directed knowledge-graph views.
- Only notes tagged `publish: true` are *rendered into the site*. This controls rendering, not
  access — see [Privacy model](#privacy-model) below before assuming anything in `vault/` is private.
- Real backlinks, note-maturity badges (🌱 seed / 🌿 growing / 🌳 evergreen), topic browsing, a
  command palette (⌘K), spaced-review surfacing, and a random-note discovery button.
- Four runtime-switchable themes (no rebuild required — swappable via `<html data-theme>` and a
  single CSS-variable source of truth), each with its own palette, typography, and material
  language: `CYBER_PRIME` (dark/neon), `THE_PATRIOT` (light/civic, USWDS-grounded), `THE_STOA`
  (Stoic Greco-Roman/Helvetic), and `GRIZZ` (dark, Adams State University green/black/white).
- NotebookLM export support: audio/video overviews, flashcard decks, mind maps and other synthesis
  assets are auto-detected from the export's headers and rendered as interactive widgets.
  **Note:** the media files themselves are no longer committed to this repo (see [Media](#media)),
  so the audio and image widgets currently render without their sources. Flashcard decks still
  work — those are small CSVs.

## Stack

Python + [Jinja2](https://jinja.palletsprojects.com/) for templating, [PyYAML](https://pyyaml.org/)
for real frontmatter parsing, and [Tailwind CSS](https://tailwindcss.com/) (compiled at build time
via the CLI, not the CDN). No JS framework or bundler — the client-side interactivity (search,
graph rendering, modal reader) is plain JS shipped in the page templates.

## Getting started

```bash
# One-time setup
pip install -r requirements-dev.txt   # Python deps + pytest (requirements.txt alone is enough to just build)
npm install                            # Tailwind CLI

# Build the site (writes to dist/, rebuilt from scratch every run)
python build.py

# Tests
python -m pytest tests/ -q

# Lint
python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py

# Validate every published vault note against the canonical frontmatter schema
python tools/validate_vault_schema.py

# Advisory vault-health reports: pending-atomization queue, orphaned notes,
# maturity-promotion candidates (read-only, never edits the vault)
python tools/vault_health.py
```

See [CLAUDE.md](CLAUDE.md) for the full architecture writeup — build pipeline, the wikilink/backlink
system, the theming architecture, and the reasoning behind various design decisions.

## Project structure

```
build.py               Entry point (python build.py)
engine/                 All real build logic: parsing, extraction, card rendering, theming, pipeline
system/templates/       Jinja2 templates (base + Lobby + Garden + 404)
assets/                 Tailwind input CSS, shared client JS
vault/                  The Obsidian vault itself -- source content, not source code (see License)
tests/                  pytest suite
tools/                  Standalone scripts (e.g. vault frontmatter schema validator)
deploy.py               Generates a white-labeled clone of the tooling for someone else to reuse
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
| `vault/assets/documents/` | no (not synced) | **yes** |
| Anything else in `vault/` | no | **yes** |

The same applies to the `documents` carve-out in `engine/assets_pipeline.py`: not syncing a folder
into `dist/` keeps it off the *website*, not out of the *repository*.

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

**No audio, video, or image files are committed to this repository.** `vault/assets/` holds empty
`audio/`, `images/`, and `flashcards/` directories; the only tracked assets are the Tailwind input
CSS, one shared JS file, and five small flashcard CSVs.

NotebookLM audio exports ran 64–79 MB each and had grown to ~858 MB, which pushed the published
site to 88% of GitHub Pages' 1 GB ceiling and made every clone and CI checkout pay for all of it.
They were removed from the repository and its history in 2026; `dist/` went from ~882 MB to
~5.7 MB. Media of that size belongs in object storage, linked from the notes rather than bundled
into the site — that's the intended direction, not yet built.

`engine/assets_pipeline.py` still compresses drop-zone audio over 15 MB via ffmpeg when it's
installed, which is what keeps new media from re-inflating the repo in the meantime.

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
