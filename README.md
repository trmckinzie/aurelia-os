# Aurelia OS

A personal static-site generator that turns an [Obsidian](https://obsidian.md) vault into a
published digital garden — an **external cortex**: atomic notes (concepts, sources, authors,
disciplines, daily logs, NotebookLM syntheses) linked the way a Zettelkasten links, rendered,
styled, and published as a real website with the link graph itself made visible and navigable.

**Live site:** [trmckinzie.github.io/aurelia-os](https://trmckinzie.github.io/aurelia-os/)

## What it does

- Converts Obsidian markdown notes (with YAML frontmatter and `[[wikilinks]]`) into a published,
  searchable, browsable garden — grid, tree, and force-directed knowledge-graph views.
- Only notes tagged `publish: true` go live; everything else stays private in the vault.
- Real backlinks, note-maturity badges (🌱 seed / 🌿 growing / 🌳 evergreen), topic browsing, a
  command palette (⌘K), spaced-review surfacing, and a random-note discovery button.
- Four runtime-switchable themes (no rebuild required — swappable via `<html data-theme>` and a
  single CSS-variable source of truth), each with its own palette, typography, and material
  language: `CYBER_PRIME` (dark/neon), `THE_PATRIOT` (light/civic, USWDS-grounded), `THE_STOA`
  (Stoic Greco-Roman/Helvetic), and `GRIZZ` (dark, Adams State University green/black/white).
- NotebookLM export support: audio/video overviews, flashcard decks, and other synthesis assets
  are auto-detected and rendered as interactive widgets.

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
python -m pyflakes engine/*.py build.py deploy.py tests/*.py
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
deploy.py               Generates a white-labeled clone of the tooling for someone else to reuse
```

## License

The generator code (`engine/`, `system/`, `assets/`, `build.py`, `deploy.py`, `tests/`, and other
project tooling) is licensed under the [MIT License](LICENSE) — reuse, fork, and adapt it freely.

The contents of `vault/` are the author's personal notes, journal entries, and original writing.
They are **not** covered by that license, remain all rights reserved, and are not licensed for
reuse or republication. See the scope note at the bottom of [LICENSE](LICENSE) for the exact
carve-out.

## Security

This is a personal project with no formal support channel, but see [SECURITY.md](SECURITY.md) if
you find a security issue in the generator itself.
