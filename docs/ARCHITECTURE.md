# Architecture

Split out of `CLAUDE.md` on 2026-09-10 so that file could stay a lean entry point. `CLAUDE.md`
is the lean entry point; this file is the engine walkthrough.


### Build pipeline (`build.py` → `engine/`)

`build.py` at the repo root is a ~15-line entrypoint (`from engine.pipeline import build_all`). All
real logic lives in `engine/`:

- **`config.py`** — paths (`VAULT_PATH`, `TEMPLATE_DIR`, `OUTPUT_DIR`), the Jinja2 `env`, the theme
  system (`THEME_CONFIG`, five presets in switcher order: **`TIMBERLINE` light/professional, the
  default since 2026-09**, then `CYBER_PRIME` dark/neon, `THE_PATRIOT` light/civic, `THE_STOA`
  Stoic/Helvetic, `GRIZZ` dark/collegiate), and `load_user_config()` (reads `user_config.json`).
  `CURRENT_THEME` selects the *default* only — every theme is shipped and switchable at runtime
  (see `theming.py`). Adding a theme means adding a dict entry here and nothing else: the CSS
  generator, the Tailwind config, and the switcher UI all derive from these keys. Only `colors` is
  mandatory; the optional keys (each with a default in `theming.py` that reproduces the historical
  hard-coded value) are `font_mono`, `font_display`, `font_body`, `font_reader_heading`,
  `display_weight`/`display_tracking`/`display_leading`, `label_weight`, `halo` (text-glow
  strength; `0%` turns every neon halo off), `rounded`, the glass/scanline keys, the depth-system
  keys, and `cursor_default`/`cursor_interactive` (`auto`/`pointer` opts out of the SVG cursors).
  TIMBERLINE is the reference for a theme that uses all of them.

  `env` is built with **`autoescape=True`** (audit #21 — it used to take Jinja's default of off,
  so every `{{ }}` emitted raw). It is unconditional rather than `select_autoescape()`, so a
  future non-HTML template has to opt out deliberately instead of inheriting "unescaped" from a
  filename extension. Nothing in the templates carries `|safe` any more: the two producers that
  legitimately emit raw output return `markupsafe.Markup` instead — see `cards.py` and
  `textutils.dumps_for_script_tag()` — and note-authored HTML goes through `sanitize.py`.
- **`paths.py`** — added 2026-09-04 (commit b2d2885): `is_inside`/`escapes`/`is_link`, the
  containment checks used to answer "does this path actually land inside the directory I think I'm
  reading?" for both the vault scan (`pipeline._scan_vault()`) and the asset pipeline. It exists
  specifically to catch a Windows directory junction (`mklink /J`), which `os.path.islink()` does
  not detect and `os.walk`/`shutil.copytree` will happily follow or copy through — a way to publish
  arbitrary local files on a static site generator if one were planted under `vault/` or `assets/`.
- **`content.py`** — markdown-level parsing: `parse_frontmatter()` (real YAML via PyYAML, not regex),
  `parse_body()`, `make_id()` (filename → slug), `process_wikilinks(text, resolve=None)`
  (`[[Target]]` / `[[Target|Label]]` → `<button onclick="openNote('id')">Label</button>`; with no
  resolver the target is plain `make_id(text)`, the historical behaviour),
  `build_link_resolver(notes)` (added 2026-09-10: three tiers, an earlier one never overwritten —
  exact `make_id(title)`, any entry in the note's frontmatter `aliases:`, and a *unique*
  title-suffix base so `[[Dopamine]]` reaches `Dopamine (Reward Prediction Error)`; a base shared
  by two notes resolves to neither, and a `(Gemini Notebook)` suffix is excluded because it marks
  a source type, not a disambiguation), and
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

  **No vault media is committed.** `vault/assets/` does not exist at all any more (git tracks no
  empty directories, so the placeholders an earlier revision of this file described are gone);
  the only tracked assets are `assets/css`, `assets/js`, five
  flashcard CSVs at the **repo root** in `assets/flashcards/` — which is why `resolve_asset()`'s
  ROOT_DIR fallback is load-bearing rather than vestigial — and two site images in
  `assets/images/` added 2026-09-07 — `headshot.webp`
  (650×650, 43 KB, no EXIF/XMP; referenced by `profile.json`'s optional `identity.photo` and
  validated by `engine/profile.py` as a real file under `assets/images/`) and
  `social-preview.jpg` (1200×630, the `og:image`, generated from the headshot with ffmpeg on
  TIMBERLINE's paper color). All Gemini Notebook audio and mind-map images were removed from the repo *and its
  history* in 2026 (see docs/DECISIONS.md item 9). The 16 references were deleted from the 9 notes
  that named them in commit 370e8eb (2026-09-10), and the build now prints no media warning; if the
  warning ever returns it means a note names an asset that is not in `vault/assets/` or repo-root
  `assets/`.

  **Nothing renders as a dead player.** An earlier revision of this file said those widgets do,
  and that was already false when written: `process_gemini_notebook_media()` checks
  `resolve_asset()` and drops the bare path instead of emitting a widget, then
  `wrap_gemini_notebook_sections()` drops the section it just emptied. Verified against the built
  page — `dist/garden.html` contains **zero** `<audio>` tags and **zero** `<img src="assets/...">`.
  A reader sees the note as prose with the section simply absent; the build warning is how the
  *owner* hears about it. The
  compression path above still works and is
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
  `vault/`, reads and sanitizes every published garden note, and computes its `note_id`, building
  the full `known_ids` set and the link resolver; pass two runs `process_wikilinks()` with that
  resolver (it used to run per note inside pass one, before `known_ids` existed), the Gemini
  media/section passes, and then `cards.generate_garden_card_html()` for each note, so card-face
  links know whether their targets actually exist before rendering. `build_all()` prints a
  `Wikilinks:` summary line (occurrences and distinct targets resolved via alias or suffix, plus
  the still-unresolved count), and that unresolved count agrees with
  `tools/vault_health.py --report pending` by construction — both go through the same resolver.
  `_build_link_graph()` scans every note's rendered body for `openNote('id')` occurrences once
  and returns both the backlinks index (note_id → list of notes that link to it, powering the
  modal's "Referenced By" section) and the knowledge-graph edges/degree counts — its own docstring
  notes these were originally two separate functions, each doing its own scan over the same data,
  consolidated into one pass. `_build_search_index()` builds the command-palette JSON (title/type/
  tags/short-snippet only, **not** full note bodies — this was a deliberate size fix, see
  docs/DECISIONS.md item 5). `_render_pages()` renders `index.html`, `garden.html`, `about.html`,
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
2. `content.process_wikilinks()` converts it to `<button onclick="openNote('note-target-note')">Label</button>` — this happens *before* extraction. The id comes from the build's link resolver (exact title, then `aliases:`, then a unique `Base (…)` title suffix — see `content.py` above), so an alias is a legitimate fix for a dangling link on the site as well as in Obsidian.
3. Extractors call `textutils.extract_links()` on the relevant section, which regex-matches that
   button form (or, for text that was never run through `process_wikilinks`, falls back to raw
   `[[brackets]]` and derives the id itself). Every extractor field that represents a linked item
   returns `(target_id, label)`, never a bare label.
4. `cards.link_pill()` decides, per pill, whether `target_id` is in the build's `known_ids` set
   (computed in pipeline.py's first pass) and renders accordingly (live button / dimmed dangling
   link / plain text).
5. Separately, `pipeline._build_link_graph()` scans every note's *fully rendered* body (which
   already contains real `openNote()` calls from step 2, whether from structured fields or plain
   inline prose mentions) to build the reverse graph, embedded as `BACKLINKS_INDEX` in
   `gardentemplate.html` and rendered by `renderBacklinks()` when a note's modal opens.

If you add a new garden note type or a new linked-item field, follow this same pattern rather than
extracting plain label strings — that's the bug this session's "make card-face links real" work
fixed (pills that looked clickable but weren't, because the extractor threw away the target id).

Three things to know before editing links in bulk (all learned in item 17's cleanup):

- **`make_id()` lowercases and collapses punctuation.** `[[hippocampus]]`, `[[Hippocampus]]` and
  `[[HIPPOCAMPUS]]` are one target, not three. When auditing, count by id, not by written form —
  otherwise case variants read as separate gaps and a "fix" to one leaves its siblings behind.
- **Prefer `[[Full Title|display text]]` over relying on the resolver.** The alias and title-suffix
  tiers exist so a short mention still lands, but the piped full title is unambiguous, survives a
  note gaining a second parenthetical sibling (which makes the suffix tier resolve to *neither*),
  and reads identically to the reader. The vault was normalized to this form in item 17.
- **A dangling link is usually deliberate.** Most of the ~850 unresolved targets are placeholders
  for notes not yet written — that is how a zettelkasten accumulates. Don't "fix" them by
  unlinking; `tools/vault_health.py --report pending` is the queue, not an error list.

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

`indextemplate.html`'s Toolkit carousel reads two more per-entry `tech_stack` fields,
`what_it_is` and `how_i_use_it`, to fill a native `<dialog>` detail window (`#toolkit-sheet`)
opened by a card click or the "More about" button, and skips any entry marked `draft: true`;
see docs/DECISIONS.md item 20.

`base.html`'s inline `<script>` embeds `SYSTEM_INDEX` (the command-palette JSON) via
`dumps_for_script_tag`, safe against a note title containing a literal `</script`.
`gardentemplate.html` additionally embeds `BACKLINKS_INDEX`.

### Study layer (`assets/js/review.js`, `assets/js/flashcards.js`) — added 2026-09-10

The Garden is a study tool as well as a browsing surface, on the strength of the learning-science
evidence (practice testing and distributed practice rate highest in Dunlosky et al. 2013;
interleaving, elaborative interrogation and self-explanation moderate). Everything below is
client-side, framework-free, and keeps its state in **localStorage only** — the site is static and
has no analytics, so a learner's progress never leaves their browser except through the Progress
panel's export/import (JSON, merged per note by the higher `last` timestamp).

- **`review.js`** exposes `window.Review`: an SM-2 scheduler (ratings Again/Hard/Good/Easy → quality
  0/3/4/5; `ease = max(1.3, ease + 0.1 − (5−q)(0.08 + (5−q)·0.02))`; a lapse resets the interval to
  1 day; first success seeds the interval from `data-maturity` — seed 1 d, growing 3 d, evergreen
  7 d; second success 6 d; then `round(interval × ease)`). State lives under the `aurelia_review_log`
  key the removed 2026-08 feature deliberately left behind, as
  `{version: 2, notes: {id: {last, due, interval, ease, reps, lapses}}, decks: {csvPath: {index: …}}}`;
  a v1 `{id: millis}` log is migrated lazily on the Garden. `dueCount()` counts only logged entries
  with `due <= now`, which is why the Lobby teaser (`#lobby-review-teaser`) needs no per-note
  payload in `index.html` — do not reintroduce `review_seed`.
- **Read / Study mode** (`aurelia_study_mode`; absent → Read, because the public audience is a
  recruiter, not the author). In Study mode `applyRecallCover()` runs right after `marked.parse()`
  in `openNote()` and hides the note's "answer" block — the blockquote after the Definition /
  Core Argument / Scope / Profile heading, or a Deep Dive's italic premise line — behind a
  "Try to recall it first" cover; Reveal shows it and the four-button rating row, whose result
  collapses into "Rated Good · next due in 3 days" with a Change rating link that re-rates from a
  snapshot rather than double-counting. The cover is client-side on purpose: it must be removable
  at runtime, it adds nothing to `#data-storage`, and it needs no `sanitize.py` change.
- **Elaboration nudge** (`renderElaboration()`, `#modal-elaborate`): after a rating, two or three
  linked neighbours chosen for *difference* (another permanent type first, then fewest shared
  `topic/*` tags; daily logs and Gemini notebooks excluded) under "How does this connect?".
  Nothing is stored.
- **Review queue and sessions**: "Due today: N" and Start review beside the note count; a session
  is greedily interleaved (the next note must differ in type from the last two shown), walks via
  `openNote(next, 'replace')` so `history.length` never grows, moves focus to each Reveal button,
  shows "Reviewing 2 of 5" in the reader header, and ends on a visible completion line. `?review=1`
  deep-links a session; a reload recomputes the queue from the log. Cards carry a due marker, the
  sort menu has "Due first", and the reader footer's `#modal-reviewed` slot says when a note was
  last reviewed and when it is next due.
- **`flashcards.js`** upgrades every `<ol class="deck" data-deck="assets/flashcards/x.csv">` that
  `content._render_flashcards()` now emits (Q/A as child elements, never `data-*` attributes —
  `openNote()`'s `<textarea>` decode would turn an escaped quote live) into a one-card widget:
  Show answer, 1–4 rating through `Review.rateCard()`, "12 of 80", Shuffle, prev/next, and a
  per-deck "Study due cards only" preference (`aurelia_deck_prefs`). It runs after every
  `openNote()`, not just at load, because decks live inside note bodies rendered on demand. With
  no JS the list still reads as plain Q/A pairs.
- **Navigation aids**: an "On this page" outline (`#modal-outline`, sticky at `xl:`, a collapsed
  `<details>` below) for notes with four or more headings, with Expand all / Collapse all for
  Gemini sections; a `?` shortcut sheet (native `<dialog>`, so Escape and the focus trap are free
  and cannot fight the reader's hand-rolled trap); `/` focuses search, `s` toggles Study mode; and
  under 768 px the graph view renders `#graph-list`, the 30 most connected notes, instead of the
  canvas. `#a11y-status` is the live region every view switch and note open announces through.

There is no JS test harness: `tests/test_garden.py` pins the wiring (scripts loaded with `?v=`,
elements and options present, no legacy voice tokens), and the behaviour is verified with
Playwright against a local `http.server` on `dist/` — see the Verification section of the plan
that landed this work, and note that a browser will happily serve a cached `garden.html` after a
rebuild unless you add a query string.

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
The same holds for `draft: true` on a `user_config.json` `tech_stack` entry: it keeps the entry
off the Lobby, not out of the repository.

Two consequences worth holding onto when working here:

- Don't describe anything in the vault as "private" in code comments, docs, or commit messages.
  Earlier revisions of this file and README.md did, and it was wrong.
- `_scan_vault()` walks the vault with exactly one hard-coded exclusion: `engine/pipeline.py`'s
  `UNPUBLISHED_DIRS = {"20_AURELIA"}`, added 2026-09-01/04 (commits cc078a3, b7d102d) so
  agent-drafted notes under that folder can never publish, regardless of their `publish:` value.
  The comparison is case-folded (`_UNPUBLISHED_DIRS_FOLDED`) deliberately: this is a denylist on a
  case-insensitive filesystem, and NTFS matches `20_Aurelia` to `20_AURELIA` when opening the
  folder while keeping whatever casing it was first created with — an unfolded comparison would
  let a folder recreated with different casing slip past the prune silently. Every other folder is
  still unrestricted, so a stray `publish: true` anywhere else — `80_COURSES`, `99_DROP_ZONE`, a
  plugin's bundled markdown — still publishes that note to the live site. The publish surface is
  one boolean plus this single denylisted folder, otherwise unbounded by directory.

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
`tools/validate_vault_schema.py` (also runs under `pytest`) for the enforced contract. An optional
`aliases:` list (Obsidian's own key) is honoured by the build's link resolver since 2026-09-10; the
validator does not reject unknown keys, so it passes. Two axes that
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


## `deploy.py` — a second, separate product

`deploy.py` is unrelated to building *this* site. Running it clones the codebase into
`./Aurelia_Factory_v1/` (gitignored, not committed) — a white-labeled, `[INSERT NAME]`-style
template meant to be handed to someone else as a starting point for their own instance. It copies
`build.py`, `engine/`, `system/templates/`, `assets/{css,js}` (not images, for privacy), writes a
generic `user_config.json`, and generates two demo notes (a Concept and a Gemini Notebook example)
plus a README. Keep it in sync with `engine/`'s actual capabilities when you change what the site can do —
its `FACTORY_CONFIG` and generated README have drifted out of sync with reality before (see
docs/DECISIONS.md item 4) and it's easy for that to happen again silently, since nothing tests it
automatically.
