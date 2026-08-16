# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Aurelia OS is a personal static-site generator: it turns an Obsidian vault (`vault/`) into a
published GitHub Pages site (`https://trmckinzie.github.io/aurelia-os/`) for Travis McKinzie. The
stated purpose is an **"external cortex"** — a personal wiki/digital garden where atomic notes
(concepts, sources, authors, disciplines, daily logs, NotebookLM syntheses) link to each other the
way a Zettelkasten does, captured in Obsidian and then rendered, styled, and published as a real
website. The design goal is not just "notes on the web" — it's making the *graph* (what links to
what, note maturity, discoverability) actually visible and navigable in the published site, not
just inside Obsidian.

The **only two published pages are the Lobby (`index.html`) and the Garden (`garden.html`)**.
Protocols/Portfolio/Transmissions/Services pages, and their card types, project types, and
extractors, were deliberately removed (see "Recent history" below) — don't reintroduce them without
being asked.

## Commands

```bash
# One-time setup
pip install -r requirements-dev.txt   # Python deps + pytest (requirements.txt alone is enough to just build)
npm install                            # Tailwind CLI

# Build the site (writes to dist/, gitignored, rebuilt from scratch every run)
python build.py

# Tests
python -m pytest tests/ -q             # full suite (60 tests as of this writing)
python -m pytest tests/test_cards.py -v            # one file
python -m pytest tests/test_cards.py::test_link_pill_renders_clickable_button_for_known_target -v  # one test

# Lint (no linter config beyond this; pyflakes catches unused imports/names)
python -m pyflakes engine/*.py build.py deploy.py tests/*.py

# Factory clone (see "deploy.py" below) -- generates ./Aurelia_Factory_v1/, not committed
python deploy.py
```

On Windows, `build.py`'s own `print()` calls use emoji; if you ever invoke engine code directly via
`python -c "..."` instead of through `build.py`, you may need `PYTHONUTF8=1` in the environment,
since `build.py` itself reconfigures stdout to UTF-8 but a bare one-off script won't.

**CI (`.github/workflows/deploy.yml`) only runs `python build.py`** — it does not run `pytest` or
`pyflakes`. Both exist and are used during development, but a broken test or a new lint warning
will not fail the build or block a deploy. Run them manually before committing.

## Architecture

### Build pipeline (`build.py` → `engine/`)

`build.py` at the repo root is a ~15-line entrypoint (`from engine.pipeline import build_all`). All
real logic lives in `engine/`:

- **`config.py`** — paths (`VAULT_PATH`, `TEMPLATE_DIR`, `OUTPUT_DIR`), the Jinja2 `env`, the theme
  system (`THEME_CONFIG` dict with `CYBER_PRIME` dark/neon and `THE_PATRIOT` light/academic presets;
  `CURRENT_THEME` is hardcoded to `CYBER_PRIME` — there's no runtime theme switch), and
  `load_user_config()` (reads `user_config.json`).
- **`content.py`** — markdown-level parsing: `parse_frontmatter()` (real YAML via PyYAML, not regex),
  `parse_body()`, `make_id()` (filename → slug), `process_wikilinks()` (`[[Target]]` /
  `[[Target|Label]]` → `<button onclick="openNote('id')">Label</button>`), and
  `process_notebooklm_media()` (converts NotebookLM export headers like `# Audio Overview` into
  embedded `<audio>`/`<video>`/flashcard-CSV widgets).
- **`extractors.py`** — regex extractors that pull structured data out of a garden note's body per
  type (`extract_log_data`, `extract_concept_data`, `extract_source_data`, `extract_author_data`,
  `extract_discipline_data`, `extract_notebooklm_data`). These depend on emoji-prefixed markdown
  headers matching loosely (e.g. `r'###\s*.*Definition.*'` matches regardless of exact emoji), but
  **exact-string fields** (like `**🔗 Related:**`) are fragile — change the literal text in a
  template and extraction silently returns nothing for that field. Every extractor that returns
  linked items returns `(target_id, label)` tuples, not bare strings (see "Link system" below).
- **`textutils.py`** — shared string helpers used by extractors and cards: `strip_html`,
  `strip_wikilinks`, `clean_text`, `truncate`, `extract_links` (the core link-extraction helper —
  prefers rendered `<button onclick="openNote('id')">` form, falls back to deriving an id from raw
  `[[brackets]]` via `make_id`), `section_after_header`, `first_blockquote_after`,
  `dumps_for_script_tag` (JSON-dumps but escapes `</script` so embedded JSON can't break out of its
  `<script>` tag).
- **`cards.py`** — `generate_garden_card_html()` is the single card-rendering function; it branches
  on note type (daily-log, concept, source, author, discipline, notebooklm, default) and calls the
  matching extractor. `link_pill()` renders one linked-item pill: a real `openNote()` button if the
  target note id is in the `known_ids` set passed in, dimmed non-interactive text (with a "Not yet
  published" tooltip) if it was a wikilink to something that doesn't exist/isn't published, or plain
  text if it was never a link at all. `_maturity_badge()` renders a 🌱/🌿/🌳 badge from a
  `status/seed|growing|evergreen` tag, shown uniformly across every card type.
- **`assets_pipeline.py`** — `organize_assets()` (sorts `vault/99_DROP_ZONE` into
  `vault/assets/{images,audio,video,flashcards,documents}` by extension; audio over 15MB gets
  auto-compressed via ffmpeg if it's installed, otherwise copied as-is with a warning — a
  deliberate choice to cap git growth going forward without rewriting history, see "Recent history"
  item 6), `prepare_dist()` (wipes and recreates `dist/`), `sync_vault_assets()` (copies
  `vault/assets/{audio,video,images,flashcards}` into `dist/assets/` — note `documents` is
  deliberately *not* synced, so anything sorted there stays private).
- **`tailwind_build.py`** — generates `tailwind.config.js` (gitignored) from `THEME_CONFIG` and runs
  the Tailwind CLI. Runs **last**, after pages are rendered, scanning `dist/**/*.html` rather than
  the Python/Jinja source — this matters because `cards.py` builds some class names dynamically
  (e.g. `color.replace('border-', 'bg-')`), and those are only literal, scannable text once they're
  in the rendered HTML. There's no `safelist` currently (a prior one existed only for a client-side
  JS `text-*` → `bg-*` class derivation in the now-deleted protocol page; removed once confirmed
  unused). If a future template assembles Tailwind class names in the browser after page load
  (rather than server-side in Python, which the `dist/**/*.html` scan already covers), those classes
  will need a `safelist` entry added back — the content scanner can't see anything that only exists
  once client-side JS runs.
- **`pipeline.py`** — orchestrates everything. `_scan_vault()` is **two-pass**: pass one walks
  `vault/`, reads every published garden note, and computes its `note_id`, building the full
  `known_ids` set; pass two calls `cards.generate_garden_card_html()` for each note with that set
  now available, so card-face links know whether their targets actually exist before rendering.
  `_build_backlinks_index()` scans every note's rendered body for `openNote('id')` occurrences and
  inverts the graph (note_id → list of notes that link to it) — this is what powers the modal's
  "Referenced By" section. `_build_search_index()` builds the command-palette JSON (title/type/
  tags/short-snippet only, **not** full note bodies — this was a deliberate size fix, see "Recent
  history" item 5). `_render_pages()` renders `index.html`, `garden.html`, `404.html` and nothing
  else.

### Link system (the "personal wiki" part)

This is the mechanism most likely to need touching if you're asked to change how notes link to each
other. The flow for one wikilink, end to end:

1. Author writes `[[Target Note]]` or `[[Target Note|Custom Label]]` in a vault note.
2. `content.process_wikilinks()` converts it to `<button onclick="openNote('note-target-note')">Label</button>` — this happens *before* extraction.
3. Extractors call `textutils.extract_links()` on the relevant section, which regex-matches that
   button form (or, for text that was never run through `process_wikilinks`, falls back to raw
   `[[brackets]]` and derives the id itself). Every extractor field that represents a linked item
   returns `(target_id, label)`, never a bare label.
4. `cards.link_pill()` decides, per pill, whether `target_id` is in the build's `known_ids` set
   (computed in pipeline.py's first pass) and renders accordingly (live button / dimmed dangling
   link / plain text).
5. Separately, `pipeline._build_backlinks_index()` scans every note's *fully rendered* body (which
   already contains real `openNote()` calls from step 2, whether from structured fields or plain
   inline prose mentions) to build the reverse graph, embedded as `BACKLINKS_INDEX` in
   `gardentemplate.html` and rendered by `renderBacklinks()` when a note's modal opens.

If you add a new garden note type or a new linked-item field, follow this same pattern rather than
extracting plain label strings — that's the bug this session's "make card-face links real" work
fixed (pills that looked clickable but weren't, because the extractor threw away the target id).

### Templates (`system/templates/`)

Only four template files exist: `base.html` (nav, footer, command palette, theme CSS block, loads
`marked.js` via CDN pinned with an SRI hash, loads `assets/js/utils.js` for the shared
`escapeHtml()`), `404.html`, `pages/indextemplate.html` (Lobby), `pages/gardentemplate.html`
(Garden — the note-modal system, search/filter, tree view, and now backlinks + random-note live
here). Both page templates `{% extends "base.html" %}`.

`base.html`'s inline `<script>` embeds `SYSTEM_INDEX` (the command-palette JSON) via
`dumps_for_script_tag`, safe against a note title containing a literal `</script`.
`gardentemplate.html` additionally embeds `BACKLINKS_INDEX`.

### CSS

`assets/css/main.css` is the Tailwind input file (`@tailwind base/components/utilities` +
hand-written CSS: cursor SVGs, the `@keyframes scanline` atmosphere effect, the `.scanline` baseline
rule shared across every page). It is **not** loaded from a CDN — Tailwind compiles it at build
time (see `tailwind_build.py` above). The color palette (`aurelia-bg`, `aurelia-primary`,
`aurelia-secondary`, etc., plus legacy aliases `aurelia-cyan`/`aurelia-orange`/`aurelia-green`/
`aurelia-purple`/`aurelia-dim`/`aurelia-dark` mapped onto the semantic ones) is generated into
`tailwind.config.js` from `THEME_CONFIG`, so **theme colors have exactly one source of truth**:
`engine/config.py`. Don't hand-edit `tailwind.config.js` — it's regenerated and gitignored.

### Content model (vault conventions)

Garden note types are set via YAML frontmatter `type:` (or a `type/xxx` tag as fallback) and a note
only publishes with `publish: true`. Types: `concept`, `source`, `author`, `discipline`,
`notebooklm`, daily logs (detected by a `YYYY-MM-DD`-shaped filename, or `type: daily-bridge`/`log`),
and anything else falls through to a generic card. Templater templates for each type live in
`vault/90_SYSTEM/92_Templates/`. Notes are also tagged `status/seed|growing|evergreen` (maturity,
shown as a badge) and various `status/reading|active|archive` states (type-specific, e.g. Source
cards show READING/QUEUED/ARCHIVED).

`type: project`, `type: protocol`, and `type: transmission` notes are recognized and explicitly
skipped in `_scan_vault()` — the templates/card generators for them were deleted, not just disabled.

**The vault is off-limits to modify.** Every session working on this repo has operated under an
explicit standing instruction not to edit, delete, or add vault content (notes, folders) — treat
that as still in force unless the user says otherwise. Non-vault code changes (engine/, templates,
config) are fair game.

## Recent history (why the code looks like this)

This codebase went through a large refactor across several sessions, in roughly this order — worth
knowing so you don't "fix" something that was a deliberate decision:

1. **`build.py` → `engine/` package split.** Was a single 1,409-line file. Also replaced regex
   frontmatter parsing with real YAML (PyYAML), which fixed several latent bugs: project
   `tech_stack` chips were always empty, protocol IDs from frontmatter were silently ignored, tags
   were being polluted with unrelated list-field items.
2. **Security/robustness pass.** SRI-pinned `marked.js`, escaped JSON-in-`<script>`, HTML-escaped
   vault-derived text before `innerHTML` insertion, least-privilege CI permissions, added the first
   test suite (previously zero coverage), `str()`-guarded frontmatter values PyYAML could infer as
   non-strings (e.g. an unquoted date).
3. **Tailwind CDN → compiled build.** The Play CDN script (`cdn.tailwindcss.com`) is explicitly
   documented by Tailwind as unsuitable for production. Migrated to the Tailwind CLI wired into
   `build.py`. In the process, found and fixed several color classes (`aurelia-cyan`, `aurelia-dim`,
   etc.) that had never actually been defined in any config and were silently rendering with no
   color at all.
4. **Pages scrapped: kept only Lobby + Garden.** Protocols/Portfolio/Transmissions/Services were
   removed at the user's request — templates deleted, scanning/rendering code removed, nav and
   homepage links removed, search index entries removed, `deploy.py`'s factory product updated to
   match (it used to promise features the stripped-down engine could no longer deliver).
5. **Search index payload trimmed.** The command-palette JSON embedded in every page was including
   each garden note's *entire body text*, making `index.html` ~1MB (95% of it that one JSON blob).
   Garden entries in the index now carry a 200-char snippet; `garden.html`'s own in-page deep search
   is unaffected since it uses a separate `data-search` HTML attribute per card, not this index.
6. **Audio growth capped going forward.** `assets/audio/` (NotebookLM exports) was ~714MB and
   growing; rewriting git history to fix it was explicitly ruled out as too risky. Instead,
   `organize_assets()` now compresses large (>15MB) audio via ffmpeg on its way out of the drop
   zone, before it's ever committed — optional (falls back to a plain copy if ffmpeg isn't
   installed), never blocks the build.
7. **"Make the personal wiki actually work" pass.** Card-face link pills looked clickable but
   weren't (see "Link system" above) — fixed at the extractor level. Added backlinks, uniform
   maturity badges, and a random-note discovery button.

## Known gaps / deliberately not done

- **Card HTML is still built via Python f-strings**, not Jinja2 macros, even though Jinja is the
  templating engine for everything else. This was considered and explicitly deferred as
  higher-risk-for-the-reward while there were 3 separate card-generator functions; now that only
  `generate_garden_card_html()` remains, it may be worth reconsidering, but hasn't been done.
- **Card body vocabulary isn't unified.** Each note type has its own field labels for the same
  conceptual slot (`> DEFINITION:` vs `AUTH:` vs `:: FIELD_SCOPE` vs `> BIO_MATRIX:`) — discussed,
  not yet standardized.
- **`vault/90_SYSTEM/92_Templates/TPL_Synthesis_Note.md`** is a richer note-taking template (a
  "Crane not Skyhook" mechanistic Input/Processing/Logic/Output framework) with no YAML frontmatter
  at all, so notes written from it never publish and there's no card type that could render its
  structure even if they did. One real note exists using it
  (`vault/10_GARDEN/17_Gemini_Synthesis/Lit Review Pipeline.md`) and has never appeared on the site.
- **A raw-Tailwind-class → semantic `aurelia-*` migration is incomplete.** A one-off script
  (`refactor.py`) describing this exact mapping (`text-white` → `text-aurelia-text`, `bg-black` →
  `bg-aurelia-bg`, etc.) was found and deleted as dead code (it was never runnable and unreferenced
  anywhere) — but the migration it described was never finished, so both styles still coexist in
  templates and generated HTML.
- **`garden.html` is large** (~5MB) because every note's full body is embedded inline for the
  instant-open modal (no network request needed). Known, not addressed — fixing it means trading
  instant-open for a fetch-on-click UX, which wasn't chosen without discussing the tradeoff first.
- No automated accessibility, performance (Lighthouse), or visual-regression testing.

## `deploy.py` — a second, separate product

`deploy.py` is unrelated to building *this* site. Running it clones the codebase into
`./Aurelia_Factory_v1/` (gitignored, not committed) — a white-labeled, `[INSERT NAME]`-style
template meant to be handed to someone else as a starting point for their own instance. It copies
`build.py`, `engine/`, `system/templates/`, `assets/{css,js}` (not images, for privacy), writes a
generic `user_config.json`, and generates two demo notes (a Concept and a NotebookLM example) plus a
README. Keep it in sync with `engine/`'s actual capabilities when you change what the site can do —
its `FACTORY_CONFIG` and generated README have drifted out of sync with reality before (see "Recent
history" item 4) and it's easy for that to happen again silently, since nothing tests it
automatically.
