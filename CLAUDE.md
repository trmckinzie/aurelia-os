# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Aurelia OS is a personal static-site generator: it turns an Obsidian vault (`vault/`) into a
published GitHub Pages site (`https://trmckinzie.github.io/aurelia-os/`) for Travis McKinzie. The
stated purpose is an **"external cortex"** — a personal wiki/digital garden where atomic notes
(concepts, sources, authors, disciplines, daily logs, Gemini Notebook syntheses, deep dives) link to each other the
way a Zettelkasten does, captured in Obsidian and then rendered, styled, and published as a real
website. The design goal is not just "notes on the web" — it's making the *graph* (what links to
what, note maturity, discoverability) actually visible and navigable in the published site, not
just inside Obsidian.

**Three pages are published: the Lobby (`index.html`), the Garden (`garden.html`), and About
(`about.html`).** About was added 2026-09 at the user's request (see "Recent history" item 15) and
is a *data-driven* page rendered from the repo-root `profile.json` — it is not a vault note type.
The Protocols/Portfolio/Transmissions/Services pages, and their card types, project types, and
extractors, were deliberately removed (see "Recent history" below) — don't reintroduce them without
being asked. About does not bring them back: there is no `type: project` card, and nothing about
the page reads from `vault/`.

**The site is at the start of a rebrand.** The "Aurelia" name collides with an unrelated software
company, so the plan is to move the site to a personal professional domain (working name
`travisrmckinzie.com`, not yet purchased) and let the "evolutionary theory meets cognitive science"
framing give way to web design, cognitive psychology, digital ergonomics, and Travis's professional
roles. What has landed so far is the plumbing: `user_config.json` has a `site` block (`name`,
`nav_label`, `tagline`, `domain`) that `base.html` reads for the nav brand, `<title>`, and
canonical URL, and a non-empty `site.domain` makes the build write `dist/CNAME`. The Lobby's hero,
manifesto modal, and the terminal-flavored chrome copy (`SEARCH THE CORTEX`, `TOTAL_NODES`, and
so on) are **not yet rewritten** — that is the next pass. The `aurelia-*` CSS class names and
`--aurelia-*` custom properties are internal identifiers, not branding; leave them alone.

## Commands

```bash
# One-time setup
pip install -r requirements-dev.txt   # Python deps + pytest (requirements.txt alone is enough to just build)
npm install                            # Tailwind CLI

# Build the site (writes to dist/, gitignored, rebuilt from scratch every run)
python build.py

# Tests
python -m pytest tests/ -q             # full suite (229 tests as of this writing)
python -m pytest tests/test_cards.py -v            # one file
python -m pytest tests/test_cards.py::test_link_pill_renders_clickable_button_for_known_target -v  # one test

# Lint (no linter config beyond this; pyflakes catches unused imports/names)
python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py

# Validate every published vault/10_GARDEN note against the canonical
# frontmatter schema (see "Content model" below) -- also runs under pytest
python tools/validate_vault_schema.py

# Advisory vault-health reports (pending-atomization queue, orphaned notes,
# maturity-promotion candidates) -- read-only, never edits the vault; see
# "Content model" below for the promotion heuristic and tools/vault_health.py
python tools/vault_health.py

# Factory clone (see "deploy.py" below) -- generates ./Aurelia_Factory_v1/, not committed
python deploy.py
```

On Windows, `build.py`'s own `print()` calls use emoji; if you ever invoke engine code directly via
`python -c "..."` instead of through `build.py`, you may need `PYTHONUTF8=1` in the environment,
since `build.py` itself reconfigures stdout to UTF-8 but a bare one-off script won't.

**CI (`.github/workflows/deploy.yml`) only runs `python build.py --no-sort`** — it does not run
`pytest` or `pyflakes`. Both exist and are used during development, but a broken test or a new lint
warning will not fail the build or block a deploy. Run them manually before committing.

The `--no-sort` there is not optional and not cosmetic. Without it CI runs `organize_assets()`,
which moves everything under `vault/99_DROP_ZONE/` into `vault/assets/<kind>/` — and
`sync_vault_assets()` then copies those into `dist/` with **no `publish:` gate**. An unsorted file
sitting in the drop zone at push time would be published to the live site by CI, reviewed by
nobody. Keep the flag on any workflow that builds this site.

## Architecture

### Build pipeline (`build.py` → `engine/`)

`build.py` at the repo root is a ~15-line entrypoint (`from engine.pipeline import build_all`). All
real logic lives in `engine/`:

- **`config.py`** — paths (`VAULT_PATH`, `TEMPLATE_DIR`, `OUTPUT_DIR`), the Jinja2 `env`, the theme
  system (`THEME_CONFIG`, currently four presets: `CYBER_PRIME` dark/neon, `THE_PATRIOT`
  light/civic, `THE_STOA` Stoic/Helvetic, `GRIZZ` dark/collegiate), and `load_user_config()`
  (reads `user_config.json`). `CURRENT_THEME` selects the *default* only — every theme is shipped
  and switchable at runtime (see `theming.py`). Adding a theme means adding a dict entry here and
  nothing else: the CSS generator, the Tailwind config, and the switcher UI all derive from these
  keys.

  `env` is built with **`autoescape=True`** (audit #21 — it used to take Jinja's default of off,
  so every `{{ }}` emitted raw). It is unconditional rather than `select_autoescape()`, so a
  future non-HTML template has to opt out deliberately instead of inheriting "unescaped" from a
  filename extension. Nothing in the templates carries `|safe` any more: the two producers that
  legitimately emit raw output return `markupsafe.Markup` instead — see `cards.py` and
  `textutils.dumps_for_script_tag()` — and note-authored HTML goes through `sanitize.py`.
- **`content.py`** — markdown-level parsing: `parse_frontmatter()` (real YAML via PyYAML, not regex),
  `parse_body()`, `make_id()` (filename → slug), `process_wikilinks()` (`[[Target]]` /
  `[[Target|Label]]` → `<button onclick="openNote('id')">Label</button>`), and
  `process_gemini_notebook_media()` (converts Gemini Notebook export headers like `# Audio Overview`
  into embedded `<audio>`/`<video>`/flashcard-CSV widgets), and `wrap_gemini_notebook_sections()`
  (wraps each top-level `#` section of a Gemini Notebook note in a collapsible `<details>`/
  `<summary>` block for the modal reader — see "Content model" below).
- **`extractors.py`** — regex extractors that pull structured data out of a garden note's body per
  type (`extract_log_data`, `extract_concept_data`, `extract_source_data`, `extract_author_data`,
  `extract_discipline_data`, `extract_gemini_notebook_data`, `extract_deep_dive_data`). These depend on emoji-prefixed markdown
  headers matching loosely (e.g. `r'###\s*.*Definition.*'` matches regardless of exact emoji), but
  **exact-string fields** (like `**🔗 Related:**`) are fragile — change the literal text in a
  template and extraction silently returns nothing for that field. Every extractor that returns
  linked items returns `(target_id, label)` tuples, not bare strings (see "Link system" below).
- **`textutils.py`** — shared string helpers used by extractors and cards: `strip_html`,
  `strip_wikilinks`, `clean_text`, `truncate`, `extract_links` (the core link-extraction helper —
  prefers rendered `<button onclick="openNote('id')">` form, falls back to deriving an id from raw
  `[[brackets]]` via `make_id`), `section_after_header`, `first_blockquote_after`,
  `dumps_for_script_tag` (JSON-dumps but escapes `</script` so embedded JSON can't break out of its
  `<script>` tag; returns `Markup`, since a `<script>` block is exactly the sink it vouches for —
  the same JSON is *not* safe in HTML text or an attribute).

  Note that `strip_html`/`clean_text` are **not** output encoders and never were: the regex is
  `<[^>]+>`, so an unterminated `<img src=x onerror=…` passes through untouched and the next `>`
  in the surrounding markup closes it. Escape at the sink; don't rely on these.
- **`sanitize.py`** — `sanitize_note_html()`, the allowlist sanitizer (nh3) for note-authored HTML,
  applied by `pipeline._scan_vault()` to the **raw** note body. Read the module docstring before
  moving that call: it has to run before `process_wikilinks()` and the media/section passes, since
  those inject the engine's own `onclick` buttons and `<audio>`/`<img>` widgets that a sanitizer
  would strip. It also explains why the cleaner must *strip* rather than escape (`openNote()`
  decodes entities through a `<textarea>` before handing the body to `marked.parse()`).
- **`cards.py`** — `generate_garden_card_html()` is the single card-rendering function; it branches
  on note type (daily-log, concept, source, author, discipline, gemini-notebook, deep-dive, default) and
  calls the matching extractor. `link_pill()` renders one linked-item pill: a real `openNote()` button if the
  target note id is in the `known_ids` set passed in, dimmed non-interactive text (with a "Not yet
  published" tooltip) if it was a wikilink to something that doesn't exist/isn't published, or plain
  text if it was never a link at all. `_maturity_badge(slug, color)` renders a 🌱/🌿/🌳 + text-label
  chip from the frontmatter `maturity:` key (falling back to a `maturity/*` tag — see "Content
  model" below), shown uniformly across every card type. `color` is the calling card type's own
  identity color (e.g. `border-aurelia-primary` for Concept) — the badge reuses it rather than a
  new theme color, with fill weight (outline → soft tint → solid) tracking seed → growing →
  evergreen, so no `THEME_CONFIG` change was needed to make the badge legible at a glance.
- **`assets_pipeline.py`** — `organize_assets()` (sorts `vault/99_DROP_ZONE` into
  `vault/assets/{images,audio,video,flashcards,documents}` by extension; audio over 15MB gets
  auto-compressed via ffmpeg if it's installed, otherwise copied as-is with a warning),
  `prepare_dist()` (wipes and recreates `dist/`), `sync_vault_assets()` (copies
  `vault/assets/{audio,video,images,flashcards}` into `dist/assets/` — `documents` is deliberately
  *not* synced, so anything sorted there stays off the **website**; it does *not* thereby become
  private, see "Privacy model" below).

  **No media is currently committed.** `vault/assets/` holds empty `audio/`, `images/`, and
  `flashcards/` directories; the only tracked assets are `assets/css`, `assets/js`, and five
  flashcard CSVs. All Gemini Notebook audio and mind-map images were removed from the repo *and its
  history* in 2026 (see "Recent history" item 9), so 15 notes still reference `assets/audio/...`
  and `assets/images/...` paths that no longer resolve — those widgets render as dead players
  until media hosting is re-established off-repo. The compression path above still works and is
  what keeps new drop-zone audio from re-inflating the repo, but the intended long-term answer is
  object storage linked from the notes, not files in git.
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
- **`theming.py`** — turns `THEME_CONFIG` into `dist/assets/css/theme-vars.css`: one
  `:root[data-theme="<slug>"]` block per theme defining every `--aurelia-*` custom property, plus a
  bare `:root` block mirroring the default so the first paint isn't unstyled before the switcher's
  init script runs. Also emits `-rgb` channel twins of each color (Tailwind's opacity modifiers
  like `bg-aurelia-primary/10` need decomposable channels, not a hex string) and the per-theme
  cursor SVGs. `available_themes()` feeds the nav switcher's embedded JSON.
- **`pipeline.py`** — orchestrates everything. `_scan_vault()` is **two-pass**: pass one walks
  `vault/`, reads every published garden note, and computes its `note_id`, building the full
  `known_ids` set; pass two calls `cards.generate_garden_card_html()` for each note with that set
  now available, so card-face links know whether their targets actually exist before rendering.
  `_build_backlinks_index()` scans every note's rendered body for `openNote('id')` occurrences and
  inverts the graph (note_id → list of notes that link to it) — this is what powers the modal's
  "Referenced By" section. `_build_search_index()` builds the command-palette JSON (title/type/
  tags/short-snippet only, **not** full note bodies — this was a deliberate size fix, see "Recent
  history" item 5). `_render_pages()` renders `index.html`, `garden.html`, `about.html`,
  `404.html` and nothing else. `build_all()` loads `profile.json` (below) *before* scanning the
  vault, so a malformed profile aborts the build before any vault work; it also writes
  `dist/CNAME` when `user_config.json`'s `site.domain` is set (validated as a bare hostname).
- **`profile.py`** — the About page's data layer. `load_profile()` reads the repo-root
  `profile.json` and `validate_profile()` checks it against a hand-written schema (no `jsonschema`
  dependency, same precedent as `tools/validate_vault_schema.py`): unknown keys at any depth, a
  non-string where a string is expected, an over-long string, a bad `meta.updated` date, or a URL
  whose scheme isn't `http`/`https`/`mailto` all raise `ProfileError` (a `RuntimeError`) with a
  path-qualified message. A **missing file is fatal by design** — a conditionally present page
  would make the nav differ build to build. `person_jsonld()` returns a schema.org `Person` dict
  that the pipeline serializes with `dumps_for_script_tag()` (the correct sink for JSON in a
  `<script>`). The module emits no HTML; every profile value reaches the page through autoescaped
  `{{ }}`.

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

Only five template files exist: `base.html` (nav, footer, command palette, theme CSS block, loads
`marked.js` via CDN pinned with an SRI hash, loads `assets/js/utils.js` for the shared
`escapeHtml()`), `404.html`, `pages/indextemplate.html` (Lobby), `pages/gardentemplate.html`
(Garden — the note-modal system, search/filter, tree view, and now backlinks + random-note live
here), and `pages/abouttemplate.html` (About — a deliberately plain, CV-like page: one `<h1>`,
`aria-labelledby` sections, no terminal-flavored copy, no `data-reveal`, a `@media print` block in
`main.css` so it doubles as a printable résumé). All page templates `{% extends "base.html" %}`.
`base.html` reads `config.site` (nav brand, `<title>`, canonical URL) and carries the skip link
and the three nav entries; child templates that need `site` must `{% set %}` it themselves, since
a parent's top-level `set` is not visible inside a child's blocks.

`base.html`'s inline `<script>` embeds `SYSTEM_INDEX` (the command-palette JSON) via
`dumps_for_script_tag`, safe against a note title containing a literal `</script`.
`gardentemplate.html` additionally embeds `BACKLINKS_INDEX`.

### CSS

`assets/css/main.css` is the Tailwind input file (`@tailwind base/components/utilities` +
hand-written CSS: cursor SVGs, the `@keyframes scanline` atmosphere effect, the `.scanline` baseline
rule shared across every page). It is **not** loaded from a CDN — Tailwind compiles it at build
time (see `tailwind_build.py` above). The color palette is entirely semantic now (`aurelia-bg`,
`aurelia-primary`, `aurelia-secondary`, …): the legacy aliases `aurelia-cyan`/`aurelia-dim`/
`aurelia-dark` pointed at the *same* CSS variables as `primary`/`border`/`bg` and were removed
once all 74 call sites were migrated, so there is exactly one spelling per color. (`aurelia-orange`/
`green`/`purple` had gone earlier, when the Protocol/Portfolio pages left them with zero call
sites.) The palette is split across two generated files:

- `tailwind.config.js` (from `tailwind_build.py`) maps each utility class to
  `rgb(var(--aurelia-x-rgb) / <alpha-value>)` — **theme-independent**, only needs regenerating when
  the *set* of class names changes.
- `dist/assets/css/theme-vars.css` (from `theming.py`) holds the actual per-theme values.

So **theme colors still have exactly one source of truth** — `THEME_CONFIG` in `engine/config.py` —
but it reaches the page through those two files rather than being baked into the Tailwind config.
Don't hand-edit either; both are regenerated, and `tailwind.config.js` is gitignored.

### Privacy model (read before touching anything vault-related)

**The GitHub repo is public, and the entire `vault/` directory is committed to it.** Everything in
the vault is therefore publicly readable, *including* notes with `publish: false`.

`publish:` is a rendering flag read by `_scan_vault()` — it decides what becomes a card in `dist/`.
It is not an access control and never has been. Neither is the `documents` sync carve-out in
`assets_pipeline.py`. Both keep content off the *website*; neither keeps it out of the *repository*.

Two consequences worth holding onto when working here:

- Don't describe anything in the vault as "private" in code comments, docs, or commit messages.
  Earlier revisions of this file and README.md did, and it was wrong.
- `_scan_vault()` walks the whole vault with no folder restriction, so a stray `publish: true`
  anywhere — `80_COURSES`, `99_DROP_ZONE`, a plugin's bundled markdown — publishes that note to the
  live site. The publish surface is one boolean, unbounded by directory.

Making `publish: false` genuinely mean private requires a structural change, not a code fix: vault
in a private repo, CI pushing only built `dist/` to a separate public Pages repo.

### Content model (vault conventions)

Garden note types are set via YAML frontmatter `type:` (or a `type/xxx` tag as fallback) and a note
only publishes with `publish: true`. Types: `concept`, `source/book`, `author`, `discipline`,
`gemini-notebook`, `deep-dive`, daily logs (detected by a `YYYY-MM-DD`-shaped filename, or
`type: daily-bridge`/`log`), and anything else falls through to a generic card. Templater templates
for each type live in `vault/90_SYSTEM/92_Templates/`.

`gemini-notebook` (`10_GARDEN/16_Gemini_Notebook/`, renamed from `notebooklm` in 2026-08) is a
literature note pasted from a Gemini Notebook/NotebookLM export: a Lit Review Overview plus
whatever Studio outputs were generated (Audio Overview, Mind Map, Flashcards, and — recognized by
the extractor and media map but no longer scaffolded in the template since no real note has ever
used them — Video Overview, Reports, Quiz, Infographic, Slide Deck, Data Table). Every top-level `#`
header in the note body, including freeform ones an author adds beyond the template's scaffold
(chapter breakdowns, study guides — common in real notes), is wrapped by
`content.wrap_gemini_notebook_sections()` into its own collapsible `<details>`/`<summary>` block in
the modal reader (first section open, the rest collapsed) — real notes have run to 15+ sections, so
this is a navigation aid, not decoration. Its card identity reuses the `info` role color (no
dedicated CSS variable — `border-aurelia-info` is simply not assigned to any other card type).

`deep-dive` (`10_GARDEN/17_Deep_Dives/`, added 2026-08) is structurally unlike the other six: a Deep
Dive is pasted in whole from elsewhere (an AI chat, an essay draft) rather than filled in piecemeal,
so `extract_deep_dive_data()` (`extractors.py`) depends on only two conventions instead of a full set
of headers — a standalone `*italic*`/`_italic_` line under the title (the card's premise/dek) and a
`## Part 3` header (the plain-English summary excerpt), both documented in
`TPL_Deep_Dive.md`'s own HTML-comment contract rather than enforced by the schema validator. Its card
identity is `aurelia-insight` (magenta/rose in CYBER_PRIME), the one color role added since the
original six — see `THEME_CONFIG` in `config.py` for the per-theme values and reasoning; GRIZZ's in
particular was hand-picked rather than derived, since the theme's own brief caps it at exactly two
hues (green + grey) and a 7th shade there was already the tight end of that budget.

Every published `10_GARDEN` note follows one canonical frontmatter schema (`created, tags, type,
maturity, status, publish`), standardized across all 6 original types in a 2026 migration — see
`tools/validate_vault_schema.py` (also runs under `pytest`) for the enforced contract. Two axes that
used to share one `status/*` tag namespace (and, for maturity, were largely just absent) are now
separate: `maturity: seed|growing|evergreen` (the 🌱/🌿/🌳 badge) and `status: active|reading|
queued|archive` (lifecycle; Source cards show READING/QUEUED/ARCHIVED from this). Both keys are
mirrored as `maturity/*`/`status/*` tags (alongside the existing `type/*` tag) so Obsidian's own tag
pane, graph view, and Dataview/Bases queries stay in sync — `cards._maturity_slug()` and the Source
card's status badge both read the frontmatter key first, falling back to the tag for notes edited by
hand without it, the same precedence `type` resolution already used.

Maturity promotion is a manual, human call — nothing auto-edits a note's `maturity:` key — but as of
the 2026-08 zettelkasten audit there's a written heuristic to judge candidates by, instead of pure gut
feel: promote **seed → growing** once a note has accumulated 2+ backlinks (it's actually being used,
not just sitting there), and **growing → evergreen** once it's referenced from 2+ distinct Discipline
notes (it's load-bearing across more than one structure note, not just locally popular).
`tools/vault_health.py --report promotion` surfaces candidates against this rule using the same
backlink graph `_build_link_graph()` already computes for the knowledge-graph view — advisory only,
never applies anything.

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
   growing; rewriting git history to fix it was ruled out at the time as too risky. Instead,
   `organize_assets()` began compressing large (>15MB) audio via ffmpeg on its way out of the drop
   zone, before it's ever committed — optional (falls back to a plain copy if ffmpeg isn't
   installed), never blocks the build. *Superseded by item 9: the history rewrite was eventually
   done deliberately, and the audio is gone entirely.*
7. **"Make the personal wiki actually work" pass.** Card-face link pills looked clickable but
   weren't (see "Link system" above) — fixed at the extractor level. Added backlinks, uniform
   maturity badges, and a random-note discovery button.
8. **Vault frontmatter standardization.** `status/growing` was used zero times anywhere in the
   vault (maturity and lifecycle status shared one tag namespace, and most notes had no maturity
   signal at all), 16_NotebookLM had four incompatible filename schemes, one published daily log
   sat outside `10_GARDEN` entirely, and a Source card's status badge was derived by
   substring-matching `str(tags)`. Every `10_GARDEN` note was migrated to the canonical schema
   described in "Content model" above (frontmatter rewritten via targeted line replacement, not a
   full YAML round-trip, to keep the vault's existing formatting and diffs clean); 5 files were
   renamed/moved (with vault-wide wikilink text fixed up, since Obsidian's auto-relink only fires on
   an in-app rename); ~15 `topic/*` tags were de-typo'd/merged; and `tools/validate_vault_schema.py`
   was added to keep it from drifting again.
9. **Security/privacy audit and history purge (2026-08).** An architectural audit found that the
   documented privacy model was simply false: the repo is public, so *everything* in `vault/` was
   world-readable regardless of `publish:`. Exposed and since removed: the author's résumé (which
   an older `dist/`-committing deploy had actually **served live** from the Pages site), an
   academic transcript, IRB paperwork and unpublished capstone results, instructor assessments and
   submitted coursework, 11 textbook chapters and 3 trade ebooks (~396MB of documents in total).
   No credentials were ever exposed — that was checked across all history.

   Three `git filter-repo` passes plus deletion of a stale `gh-pages` branch (a legacy deploy
   target holding a second public copy of the vault, including Smart Connections embeddings)
   brought the repo from **1.09 GiB to 24.57 MiB** and `dist/` from **882MB to 5.7MB**, which also
   retired the looming GitHub Pages 1GB site-size ceiling. Each pass was rehearsed on a throwaway
   clone first — that rehearsal is what caught the résumé, which sat at a second path
   (`assets/docs/`) that the first path list missed. Worth internalizing: `git rev-list --objects`
   lists each blob **once** under a single name, so a file duplicated across paths looks like one
   file. Enumerate with `git log --all --name-only` instead. Recon before the rewrite confirmed no
   Wayback captures, no search indexing, and zero forks.

   The audit's *code* findings were deliberately **not** fixed in the same pass — see "Known gaps".
10. **Added the `deep-dive` type (2026-08).** A 7th garden note type for long-form explainers pasted
    in whole rather than filled in piecemeal — see "Content model" above for how its extractor and
    card differ from the other six. Required a new theme color role (`aurelia-insight`), the first
    added since the original six identity colors; every `THEME_CONFIG` entry, `theming.py`'s
    `_COLOR_KEYS`, `tailwind_build.py`'s `color_map`, and `gardentemplate.html`'s filter button/
    legend/graph-node-coloring all needed a matching addition, since nothing about the type→color
    mapping is generic — each of the previous six was hand-wired the same way. `tools/
    validate_vault_schema.py`'s `FOLDER_TYPE` picked up `"17_Deep_Dives": "deep-dive"` alongside it.
11. **Zettelkasten-improvements pass (2026-08).** Six additive suggestions for making the vault a
    better zettelkasten, implemented via a formal plan: a "Contrasts With" tension-link field on
    Concept/Discipline (`_extract_contrasts()` in `extractors.py`, rendered conditionally so it's a
    byte-identical no-op for every note without the field), `tools/vault_health.py` (pending-
    atomization, orphan, and maturity-promotion-candidate reports — advisory, never writes to the
    vault), a topic-tag-hygiene check folded into `validate_vault_schema.py`, and each Templater
    template in `92_Templates/` labeled with its zettelkasten role (fleeting/literature/permanent/
    structure/context) in its own contract comment. The maturity-promotion heuristic documented
    under "Content model" above came out of this pass. Raised extractor link/related-item caps at
    the same time after discovering nearly every card was silently truncating content far below
    actual vault usage (e.g. Concept's Related cap of 4 against notes with 8+ links).
12. **THE_STOA contrast/readability fix (2026-08).** An audit (prompted by the theme's backgrounds
    reading as eye-straining, closer to paper-white than intended) found `bg_layer_1` was literally
    the single brightest color in the theme — lighter than `bg_main` itself — driving body-text
    contrast to 15–16.5:1 (well past AAA) on the note-reader/card surfaces, the ones stared at
    longest. It also turned up a real, previously undetected AA *failure*: `text_muted` on
    `bg_layer_2` (blockquote text/background) at 4.24:1, despite the theme's own comments claiming
    every color was hand-checked. All three backgrounds, `text_main`/`text_muted`, and `border_main`
    were recalibrated (values and full before/after contrast math live in the `THE_STOA` block's own
    comments in `engine/config.py`); the seven role/identity colors needed no change. No other
    theme, and no file besides `engine/config.py`, was touched — `theming.py`/`tailwind_build.py`
    regenerate everything else from that one dict.
13. **Card maturity badge redesign + general card readability (2026-08).** The maturity badge
    (🌱/🌿/🌳) was a bare 10px emoji at 70% opacity with no visible text label — easy to miss while
    scanning the Garden grid, and the only place maturity is surfaced anywhere in the UI at all.
    `_maturity_badge()` gained a `color` parameter (see its Architecture entry above) and now
    renders an always-visible, labeled chip whose fill weight tracks maturity level, moved out of
    the cramped type-label row into its own slot under the card's icon. In the same pass: every
    9–10px field-label text size in `cards.py` was bumped up a notch, the card title went
    `text-lg` → `text-xl`, and the at-rest card border opacity went 40% → 60% so card edges (and,
    per the same audit, boundaries generally) read clearly while scanning rather than only on
    hover.
14. **`notebooklm` renamed to `gemini-notebook`, notes made collapsible (2026-08).** The product
    isn't called NotebookLM any more, so the type slug, vault folder (`16_NotebookLM` →
    `16_Gemini_Notebook`), the 3 note filenames that carried a "(NotebookLM)" suffix, every Python
    identifier (`process_notebooklm_media` → `process_gemini_notebook_media`,
    `extract_notebooklm_data` → `extract_gemini_notebook_data`), and every site-facing label
    (card badge, filter button, legend, graph node color key) were renamed to match. All 15 existing
    notes' frontmatter (`type:`, `type/*` and `source/*` tags) were migrated, and the 4 files with
    inbound wikilinks to the 3 renamed notes were fixed up (same "Obsidian doesn't auto-relink
    outside the app" caveat as item 8). `tools/migrate_notebooklm_placeholders.py`, a completed
    one-off migration from the 2026-08 template audit, was deleted rather than left to break on
    import. Separately, `TPL_Gemini_Notebook.md` was trimmed from 9 scaffolded Studio-output
    headers to the 3 ever actually used (Audio Overview, Mind Map, Flashcards) — the other 6 had
    only ever sat as unfilled placeholders (the exact bug class the template's own contract comment
    already warned about); the extractor and media-widget map still recognize all 9 if a header is
    added by hand. The actual new capability, `content.wrap_gemini_notebook_sections()`, is
    documented under "Content model" above.
15. **About page + rebrand plumbing (2026-09).** A third published page, `about.html`, as a
    professional profile and portfolio piece — the site itself is the demo. Content lives in a
    repo-root `profile.json`, **not** in `vault/` (the vault is off-limits to sessions, and a CV is
    structured data, not a note), and is validated fail-loud by `engine/profile.py` (see its
    Architecture entry for the rules and why there's no `jsonschema` dependency). The old
    Portfolio page type did not come back: no card type, no extractor, nothing read from the vault.
    Content decisions worth knowing: only repos confirmed public via the GitHub API carry links
    (private ones are described without a URL); location is state-level; the contact email is
    the one already public in `user_config.json`; side jobs and employer-internal tooling were
    left out. In the same pass `user_config.json` gained the `site` block and `base.html` was
    made brand-config-driven (nav label, title, canonical, `dist/CNAME`), the skip link and
    `<main id="main-content">` landmark were added, and the author `role`/`bio_*` strings were
    rewritten to the new positioning. The Lobby's hero/manifesto and the terminal-flavored chrome
    copy are the *next* rebrand pass, listed in the intro above.

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
  structure even if they did. The one real note that used it
  (`vault/10_GARDEN/17_Gemini_Synthesis/Lit Review Pipeline.md`) was later deleted from the vault;
  no note currently uses this template.
- **A raw-Tailwind-class → semantic `aurelia-*` migration is incomplete.** A one-off script
  (`refactor.py`) describing this exact mapping (`text-white` → `text-aurelia-text`, `bg-black` →
  `bg-aurelia-bg`, etc.) was found and deleted as dead code (it was never runnable and unreferenced
  anywhere) — but the migration it described was never finished, so both styles still coexist in
  templates and generated HTML.
- **`garden.html` is large** (~5MB) because every note's full body is embedded inline for the
  instant-open modal (no network request needed). Known, not addressed — fixing it means trading
  instant-open for a fetch-on-click UX, which wasn't chosen without discussing the tradeoff first.
- No automated accessibility, performance (Lighthouse), or visual-regression testing.

### Security findings from the 2026-08 audit

These were all real and reproducible, confirmed by running payloads through the actual functions.
Some have since been fixed; the header used to say "none of these are fixed" and went stale as they
were. **Check `git log --grep "audit #"` for the current state rather than trusting this list** —
each fix names its finding number in the commit subject.

The line that used to sit here — "there is **no output-encoding layer anywhere** in the generator"
— is no longer true. There is one now, in two halves: Jinja2 autoescape for everything that is
plain text, and `engine/sanitize.py` for the one value that is genuinely note-authored HTML. The
client-side `escapeHtml()` in `assets/js/utils.js` is still only a client-side helper, not that
layer.

- **~~Jinja2 autoescape is off~~ — FIXED (#21).** `engine/config.py` now builds the environment
  with `autoescape=True`. The two producers that legitimately emit raw output say so by returning
  `markupsafe.Markup` — `cards.generate_garden_card_html()` and
  `textutils.dumps_for_script_tag()` — rather than every template restating it with `|safe`, and
  the seven `|safe` filters that were there are gone. Turning it on also forced the sinks behind
  the card to be closed: `clean_text()`/`strip_html()` only strip *closed* tags (`<[^>]+>`), so an
  unterminated `<img src=x onerror=…` went through untouched and was completed by the next `>` in
  the card markup. The `<h3>` title, the prose fields and `link_pill()`'s wikilink label are now
  escaped at their own interpolation sites.
- **~~Note bodies are injected raw into the live DOM~~ — FIXED (#21).** `gardentemplate.html`'s
  `#data-storage` block still emits each note's body, and `class="hidden"` is still `display:none`
  (which stops *rendering*, not *parsing*), and `marked.parse()` still does not sanitize — but the
  body is now run through `engine/sanitize.py` (nh3, allowlist) at build time. Read that module
  before touching this path: it documents why it must run on the *raw* note body rather than the
  finished one (the engine injects its own `onclick` buttons and media widgets afterwards, which a
  sanitizer would eat), and why `openNote()`'s `<textarea>` round-trip means the cleaner has to
  *strip* rather than escape. One deliberate cost: HTML-looking text inside a fenced code block is
  removed, since sanitizing necessarily precedes markdown parsing.
- **Attribute breakout via frontmatter tags** — `data-tags`/`data-type` fixed under #22, and
  wikilink *labels* under #21. **~~CSV cell contents are still unescaped~~ — FIXED (publish sweep
  6/6).** `_render_flashcards()` used to interpolate `q`/`a` straight into HTML; both cells (and
  the two diagnostic branches) now go through `sanitize.sanitize_to_text()`. Note it *strips*
  rather than escapes, for the same reason `sanitize_note_html()` does: `openNote()`'s `<textarea>`
  decodes character references before `marked.parse()`, so an escaped payload comes back live —
  escaping would have closed the page-load sink and left the open-the-note sink open. Note that the
  parenthetical this bullet
  used to carry — "prose fields are safe, the extractors run `clean_text()` on those" — was wrong;
  see the autoescape entry above for why.
- **Path traversal in the flashcard resolver** — fixed under #20 (`resolve_asset()` now does
  resolve-then-verify with `os.path.realpath`, and the regex is bounded to `assets/flashcards/`).
- **~~The build cannot fail~~ — PARTLY FIXED (publish sweep 6/6).** `_render_pages()` used to catch
  every render exception per page, print `❌`, and return normally — so `python build.py` exited 0
  and CI deployed a `dist/` silently missing a page. It now re-raises as a `RuntimeError` naming the
  page, aborting before the remaining pages are written, since a half-rendered `dist/` is the thing
  being prevented. **Still true for the malformed-frontmatter counter**: it warns, then exits 0
  while those notes vanish from the site. That one is a content problem rather than a broken build,
  so it was left as a warning deliberately — decide before changing it.
- **Client-side:** the topic-cloud `onclick` interpolates a raw tag into a JS string, and
  `highlightText()` builds `new RegExp()` from unescaped search input — the latter is a live
  functional bug today, since typing `(` throws and silently kills search.

## `deploy.py` — a second, separate product

`deploy.py` is unrelated to building *this* site. Running it clones the codebase into
`./Aurelia_Factory_v1/` (gitignored, not committed) — a white-labeled, `[INSERT NAME]`-style
template meant to be handed to someone else as a starting point for their own instance. It copies
`build.py`, `engine/`, `system/templates/`, `assets/{css,js}` (not images, for privacy), writes a
generic `user_config.json`, and generates two demo notes (a Concept and a Gemini Notebook example)
plus a README. Keep it in sync with `engine/`'s actual capabilities when you change what the site can do —
its `FACTORY_CONFIG` and generated README have drifted out of sync with reality before (see "Recent
history" item 4) and it's easy for that to happen again silently, since nothing tests it
automatically.

## Model routing

Sonnet executes, Opus escalates, Fable only on Travis's explicit say-so. This repo's subagents
live in `.claude/agents/`; the doctrine they point to is `90_Meta/Model Routing.md` in the dev
mono-vault containing this repo — personal workflow config, not part of this project.
