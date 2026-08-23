# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Aurelia OS is a personal static-site generator: it turns an Obsidian vault (`vault/`) into a
published GitHub Pages site (`https://trmckinzie.github.io/aurelia-os/`) for Travis McKinzie. The
stated purpose is an **"external cortex"** — a personal wiki/digital garden where atomic notes
(concepts, sources, authors, disciplines, daily logs, NotebookLM syntheses, deep dives) link to each other the
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
python -m pytest tests/ -q             # full suite (94 tests as of this writing)
python -m pytest tests/test_cards.py -v            # one file
python -m pytest tests/test_cards.py::test_link_pill_renders_clickable_button_for_known_target -v  # one test

# Lint (no linter config beyond this; pyflakes catches unused imports/names)
python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py

# Validate every published vault/10_GARDEN note against the canonical
# frontmatter schema (see "Content model" below) -- also runs under pytest
python tools/validate_vault_schema.py

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
  system (`THEME_CONFIG`, currently four presets: `CYBER_PRIME` dark/neon, `THE_PATRIOT`
  light/civic, `THE_STOA` Stoic/Helvetic, `GRIZZ` dark/collegiate), and `load_user_config()`
  (reads `user_config.json`). `CURRENT_THEME` selects the *default* only — every theme is shipped
  and switchable at runtime (see `theming.py`). Adding a theme means adding a dict entry here and
  nothing else: the CSS generator, the Tailwind config, and the switcher UI all derive from these
  keys.

  `env` is built as `Environment(loader=FileSystemLoader(TEMPLATE_DIR))` — **autoescape is off**
  (Jinja's default), so every `{{ }}` in every template emits raw. See "Known gaps" before
  assuming template output is escaped.
- **`content.py`** — markdown-level parsing: `parse_frontmatter()` (real YAML via PyYAML, not regex),
  `parse_body()`, `make_id()` (filename → slug), `process_wikilinks()` (`[[Target]]` /
  `[[Target|Label]]` → `<button onclick="openNote('id')">Label</button>`), and
  `process_notebooklm_media()` (converts NotebookLM export headers like `# Audio Overview` into
  embedded `<audio>`/`<video>`/flashcard-CSV widgets).
- **`extractors.py`** — regex extractors that pull structured data out of a garden note's body per
  type (`extract_log_data`, `extract_concept_data`, `extract_source_data`, `extract_author_data`,
  `extract_discipline_data`, `extract_notebooklm_data`, `extract_deep_dive_data`). These depend on emoji-prefixed markdown
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
  on note type (daily-log, concept, source, author, discipline, notebooklm, deep-dive, default) and
  calls the matching extractor. `link_pill()` renders one linked-item pill: a real `openNote()` button if the
  target note id is in the `known_ids` set passed in, dimmed non-interactive text (with a "Not yet
  published" tooltip) if it was a wikilink to something that doesn't exist/isn't published, or plain
  text if it was never a link at all. `_maturity_badge()` renders a 🌱/🌿/🌳 badge from the frontmatter
  `maturity:` key (falling back to a `maturity/*` tag — see "Content model" below), shown
  uniformly across every card type.
- **`assets_pipeline.py`** — `organize_assets()` (sorts `vault/99_DROP_ZONE` into
  `vault/assets/{images,audio,video,flashcards,documents}` by extension; audio over 15MB gets
  auto-compressed via ffmpeg if it's installed, otherwise copied as-is with a warning),
  `prepare_dist()` (wipes and recreates `dist/`), `sync_vault_assets()` (copies
  `vault/assets/{audio,video,images,flashcards}` into `dist/assets/` — `documents` is deliberately
  *not* synced, so anything sorted there stays off the **website**; it does *not* thereby become
  private, see "Privacy model" below).

  **No media is currently committed.** `vault/assets/` holds empty `audio/`, `images/`, and
  `flashcards/` directories; the only tracked assets are `assets/css`, `assets/js`, and five
  flashcard CSVs. All NotebookLM audio and mind-map images were removed from the repo *and its
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
`aurelia-secondary`, etc., plus the three surviving legacy aliases `aurelia-cyan`/`aurelia-dim`/
`aurelia-dark` mapped onto semantic ones — `aurelia-orange`/`green`/`purple` were dropped once the
Protocol/Portfolio pages went and left them with zero call sites) is split across two generated
files:

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
`notebooklm`, `deep-dive`, daily logs (detected by a `YYYY-MM-DD`-shaped filename, or
`type: daily-bridge`/`log`), and anything else falls through to a generic card. Templater templates
for each type live in `vault/90_SYSTEM/92_Templates/`.

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

### Open security findings (from the 2026-08 audit — none of these are fixed)

These are real and reproducible, confirmed by running payloads through the actual functions. The
practical risk is bounded (single-author site, content the author pastes in himself), but there is
**no output-encoding layer anywhere** in the generator — the one `escapeHtml()` in
`assets/js/utils.js` is client-side and covers roughly six of ~40 sinks.

- **Jinja2 autoescape is off** (`engine/config.py`, the `Environment(...)` call). Every `{{ }}` in
  every template emits raw. The `|safe` filters in `gardentemplate.html` were never opting out of
  anything, because nothing was being escaped to begin with. Turning it on is one line and is the
  single highest-leverage fix — but expect to audit every existing `|safe` afterwards.
- **Note bodies are injected raw into the live DOM.** `gardentemplate.html`'s `#data-storage` block
  emits `{{ card.body | safe }}` per note. `class="hidden"` is `display:none`, which stops
  *rendering*, not *parsing* — a `<script>` in a note executes at page load. `openNote()` then
  passes the same content through `marked.parse()`, which does not sanitize (the `sanitize` option
  was removed in marked v5).
- **Attribute breakout via frontmatter tags.** `cards.py` builds `data-tags`/`data-search` by raw
  f-string interpolation; a tag containing `"` closes the attribute and lands a live event handler
  on the `<article>`. Wikilink *labels* and CSV cell contents reach HTML unescaped by the same
  route. (Prose fields are safe — the extractors run `clean_text()` on those — which is exactly why
  this went unnoticed.)
- **Path traversal in the flashcard resolver.** `content.py`'s flashcards matcher uses `assets/.*?`
  where the other three media matchers use a bounded character class, so `.*?` matches `/`. Combined
  with an `os.path.join` that has no containment check, a note can name a `.csv` anywhere on the
  build machine and have its contents embedded in a published page. Fix is resolve-then-verify with
  `os.path.realpath`, not a tighter regex alone.
- **The build cannot fail.** `pipeline.py`'s `_render_pages()` catches every render exception per
  page, prints `❌`, and returns normally — so `python build.py` exits 0 and CI deploys a `dist/`
  that is silently missing a page. Same for the malformed-frontmatter counter: it warns, then exits
  0 while notes vanish from the site.
- **Client-side:** the topic-cloud `onclick` interpolates a raw tag into a JS string, and
  `highlightText()` builds `new RegExp()` from unescaped search input — the latter is a live
  functional bug today, since typing `(` throws and silently kills search.

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
