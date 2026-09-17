# CLAUDE.md

Guidance for Claude Code sessions in this repo. This file is deliberately lean: standing rules,
commands, a map, and the traps. Depth lives in `docs/` and is linked where a session needs it.

## What this is

A personal static-site generator: `build.py` turns the Obsidian vault in `vault/` into a
three-page GitHub Pages site (Lobby `index.html`, Garden `garden.html`, About `about.html`) at
https://trmckinzie.github.io/aurelia-os/ for Travis McKinzie. The Garden is an "external
cortex": atomic notes linked Zettelkasten-style, with the link graph, maturity, and backlinks
visible on the published site, plus a client-side spaced-repetition study layer. `README.md` is
the public description; `docs/ARCHITECTURE.md` is the engine walkthrough.

The site was rebranded away from "Aurelia" in 2026-09 (name collision). What remains "Aurelia"
is deliberately not branding and must stay: the GitHub repo name and Pages URL, `aurelia-*` CSS
classes and `--aurelia-*` custom properties, JS identifiers such as `aureliaReveal`, the
`aurelia_theme` localStorage key, the `AURELIA_SKIP_DROPZONE` env var, and the `20_AURELIA` vault
folder. The working domain `travisrmckinzie.com` is not yet purchased; `site.domain` in
`user_config.json` stays empty until it is (a value makes the build write `dist/CNAME`).

## Hard rules

- **`vault/` is off-limits to modify.** No session edits, deletes, or adds vault content (notes,
  folders, frontmatter) without an explicit one-time override from Travis. Reading is fine.
  Engine, templates, config, tests, and `profile.json` are fair game.
- **Don't commit or push unless asked.** Make the change, verify it, leave it in the working
  tree. Push only after confirming no divergence from `origin/main`.
- **CI must keep `--no-sort`.** `.github/workflows/deploy.yml` runs `python build.py --no-sort`
  and nothing else. Without the flag `organize_assets()` sweeps `vault/99_DROP_ZONE/` into
  `vault/assets/` and `sync_vault_assets()` publishes it with no `publish:` gate, reviewed by nobody.
- **CI runs no tests.** `pytest` and `pyflakes` only run when you run them; a red test or a new
  lint warning will not block a deploy. Run both before calling work done.
- **Voice rule for anything user-facing:** plain, professional English. No `//` separators, no
  `SNAKE_CASE` labels, no "nodes"/"neural"/"matrix"/"vault" jargon. Notes are notes; the
  collection is the Garden. `tests/test_lobby.py` and `tests/test_garden.py` pin the banned tokens.
- **Never call vault content "private."** The repo is public and all of `vault/` is committed.
  `publish:` decides what renders into `dist/`; it is not access control and never was.
- **Removed on purpose, don't reintroduce:** the Protocols/Portfolio/Transmissions/Services pages
  and their card types. `type: project|protocol|transmission` notes are skipped in `_scan_vault()`
  by design. About is data-driven from `profile.json`, not a vault note type.
- **Model routing:** Sonnet executes, Opus escalates, Fable only on Travis's explicit say-so.
  Subagents live in `.claude/agents/`; doctrine is `90_Meta/Model Routing.md` in the dev
  mono-vault that contains this repo.

## Commands

```bash
pip install -r requirements-dev.txt && npm install    # one-time setup
python build.py                                        # writes dist/ (gitignored, rebuilt from scratch)
python -m pytest tests/ -q                             # 461 tests as of 2026-09-10
python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py
python tools/validate_vault_schema.py                  # frontmatter contract; also runs under pytest
python tools/vault_health.py                           # advisory reports; never writes to the vault
python tools/roadmap.py --open                         # roadmap dashboard; writes reports/ (gitignored)
python deploy.py                                       # factory clone -> ./Aurelia_Factory_v1/ (gitignored)
```

Machine-specific notes (interpreter path, console encoding, local preview server) live in the
gitignored `CLAUDE.local.md`, which Claude Code loads alongside this file.

## Map

- `build.py` is a 15-line entrypoint; all logic is in `engine/`.
- `engine/config.py`: paths, the Jinja env (`autoescape=True`, unconditional), `THEME_CONFIG`
  (five themes, `TIMBERLINE` default), `load_user_config()`. Adding a theme is one dict entry.
- `engine/pipeline.py`: `build_all()`. `_scan_vault()` is two-pass (ids and link resolver first,
  then wikilinks, media, cards). `_build_link_graph()` computes backlinks and graph edges in one
  pass. `UNPUBLISHED_DIRS` hard-excludes `20_AURELIA` from publishing.
- `engine/content.py`: frontmatter (PyYAML), `make_id()`, `process_wikilinks()`,
  `build_link_resolver()`, the Gemini Notebook media and section passes.
- `engine/extractors.py`, `textutils.py`, `cards.py`: per-type field extraction, string helpers,
  and the single card renderer `generate_garden_card_html()` (Python f-strings, not Jinja).
- `engine/sanitize.py`: nh3 allowlist for note-authored HTML. Read its docstring before moving
  the call. It must run on the raw body, before the engine injects its own buttons and widgets.
- `engine/paths.py`: junction/symlink containment for the vault walk.
- `engine/profile.py`: `profile.json` loader and strict validator for the About page. A missing
  file is fatal by design so the nav never differs build to build.
- `engine/theming.py` and `tailwind_build.py`: generate `theme-vars.css` and `tailwind.config.js`
  from `THEME_CONFIG`. Never hand-edit either output.
- `system/templates/`: `base.html`, `404.html`, `pages/{index,garden,about}template.html`.
- `assets/js/`: `review.js` (SM-2 study layer, localStorage only), `flashcards.js`, `utils.js`.
- `tools/`: `validate_vault_schema.py`, `vault_health.py`, `roadmap.py`.
- `docs/roadmap.yaml`: the priority-ordered engineering roadmap (sessions plus a backlog), rendered
  by `tools/roadmap.py`. A session doing roadmap work updates its own entry in the same change
  (tasks, status, dates, commits) and runs `python tools/roadmap.py --check`.
- `deploy.py`: a separate product, a white-label factory clone. Keep it in sync with `engine/`
  when the site's capabilities change; nothing tests it and it has drifted before.

Content model in brief: a note publishes only with `publish: true`; `type:` is one of `concept`,
`source/book`, `author`, `discipline`, `gemini-notebook`, `deep-dive`, or a daily log; canonical
frontmatter is `created, tags, type, maturity, status, publish` plus optional `aliases:`.
Maturity promotion is a human call (seed to growing at 2+ backlinks, growing to evergreen when
referenced from 2+ Discipline notes); nothing auto-edits it.

## Read before touching

- Links, wikilinks, card pills, backlinks: `docs/ARCHITECTURE.md`, "Link system".
- Themes, colours, contrast: `docs/ARCHITECTURE.md`, "CSS", and `tests/test_theming.py`.
- Study mode, review queue, flashcards: `docs/ARCHITECTURE.md`, "Study layer".
- Anything that changes what the public site renders or exposes: `docs/ARCHITECTURE.md`,
  "Privacy model", then hand to `garden-publication-reviewer`.
- Why something looks odd: `docs/DECISIONS.md` (dated decisions plus known gaps).
- Security history: `docs/SECURITY-AUDIT.md`. Check `git log --grep "audit #"` for the current
  state rather than trusting any list, including that one.

## Traps

Each of these cost real time once. Dates and detail are in `docs/DECISIONS.md`.

- **`make_id()` is case- and punctuation-insensitive.** `[[hippocampus]]` and `[[Hippocampus]]`
  are one target. Audit links by id, not by written form.
- **Prefer `[[Full Title|display text]]` over relying on the resolver.** The alias and title-suffix
  tiers exist, but a suffix base shared by two notes resolves to neither.
- **A dangling link is usually a deliberate placeholder**, not an error. `vault_health.py
  --report pending` is the queue. A near-match retarget is not a match; verify in the prose first.
- **Gemini cards need the pre-wrap body.** `wrap_gemini_notebook_sections()` rewrites the `#`
  headers that `extract_gemini_notebook_data()` anchors on, so `card_body` is snapshotted before
  the media and section passes. Don't collapse the two bodies; `tests/test_pipeline.py` pins it.
- **A citation URL can contain `assets/`.** The asset-reference regex needs its lookbehind, or
  live citations report as missing files.
- **Reading a CSS custom property right after switching `data-theme` in JS returns the previous
  theme's value.** Compute per-theme contrast in Python from `THEME_CONFIG`.
- **`info` fails AA as small text in the dark themes.** Sweep every theme, not just the default.
- **`clean_text()` and `strip_html()` are not encoders.** They strip closed tags only; escape at
  the sink. `sanitize.py` strips rather than escapes because `openNote()` decodes entities
  through a `<textarea>` before `marked.parse()`.
- **Flashcard Q/A go in child elements, never `data-*` attributes**, for the same `<textarea>`
  reason.
- **Motion's `cancel()` reverts to the first keyframe on the next frame.** Use `stop()` after
  writing a final value.
- **`git rev-list --objects` lists a blob once**, so a file at two paths looks like one. Use
  `git log --all --name-only` when auditing exposure.
- **Tailwind scans `dist/**/*.html`**, so classes assembled in Python are fine but classes built
  client-side after load need a `safelist` entry.
- **A parent template's top-level `{% set %}` is invisible in a child's blocks.** Child templates
  `{% set %}` `site` themselves.
- **Don't reintroduce `review_seed`.** `dueCount()` counts logged entries only, so the Lobby
  teaser needs no per-note payload.
- **Verify the built site with a real browser against a local server on `dist/`**, and add a
  query string, or the browser serves a cached `garden.html` after a rebuild.
- **Malformed frontmatter warns and exits 0 on purpose.** It is a content problem, not a broken
  build. Decide before turning it into a failure.

## Deliberately not done

Card HTML as Jinja macros (deferred), a fetch-on-click Garden to shrink the 3.6 MB `garden.html`
(tradeoff not yet discussed), any server or synced store for study progress (the site promises
no tracking), automated accessibility, Lighthouse, or visual-regression tests, and a JS test
harness. The full list with reasons is in `docs/DECISIONS.md`.
