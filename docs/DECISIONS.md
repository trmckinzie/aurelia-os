# Decisions and history

Split out of `CLAUDE.md` on 2026-09-10 so that file could stay a lean entry point. `CLAUDE.md`
is the lean entry point; this file is the record of why things are the way they are.

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
   weren't (see docs/ARCHITECTURE.md, "Link system") — fixed at the extractor level. Added backlinks, uniform
   maturity badges, and a random-note discovery button.
8. **Vault frontmatter standardization.** `status/growing` was used zero times anywhere in the
   vault (maturity and lifecycle status shared one tag namespace, and most notes had no maturity
   signal at all), 16_NotebookLM had four incompatible filename schemes, one published daily log
   sat outside `10_GARDEN` entirely, and a Source card's status badge was derived by
   substring-matching `str(tags)`. Every `10_GARDEN` note was migrated to the canonical schema
   described in docs/ARCHITECTURE.md, "Content model" (frontmatter rewritten via targeted line replacement, not a
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
    in whole rather than filled in piecemeal — see docs/ARCHITECTURE.md, "Content model" for how its extractor and
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
    under docs/ARCHITECTURE.md, "Content model" came out of this pass. Raised extractor link/related-item caps at
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
    documented under docs/ARCHITECTURE.md, "Content model".
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
    copy were the next two passes (see the intro above and item 16).
16. **`TIMBERLINE` theme, de-branding, and the Garden/card voice pass (2026-09-05/06).** A fifth
    theme became the default: a light, editorial "Helvetica + Times" register — Cormorant Garamond
    display type with Times New Roman as the declared fallback, system Helvetica for body text and
    tracked-caps labels, ivory paper, hairlines instead of shadows, no scanline/grid/halo/custom
    cursor. Its colors are derived from Rocky Mountain Automation AI's live brand tokens (deep
    indigo `#24214c` primary, rust `#7a2a0a`, sand tints; the signal orange `#f04800` fails AA as
    text on paper at 3.4:1, so text roles use a darkened `#b93700` and the true orange appears
    nowhere — the sand tint is the decorative light source instead). Every text role was
    contrast-checked against all three surfaces (tightest pairing 4.63:1); `tests/test_theming.py`
    now enforces that with its own WCAG implementation. Expressing the register required making
    six more things theme-driven that had been hard-coded for CYBER_PRIME: body font, display
    weight/tracking/leading, label weight, and the glow-halo strength (`--aurelia-halo`, consumed
    by `.text-shadow-cyan` and the Lobby's drop-shadows via `calc(var(--aurelia-halo) * k)` so the
    other themes are byte-identical at the 50% default), plus a `font_reader_heading` token for
    headings inside the note reader. In the same pass the user-facing "Aurelia" branding was
    removed everywhere it was branding (see the intro), the Garden chrome and card labels were
    rewritten to plain English, and a Lobby bug was fixed on the way: the maturity bar animated to
    0% and stayed there because Motion's `cancel()` reverts an element to its *first* keyframe on
    the next frame, and the settle handler (which runs twice) called it after writing the real
    width — it uses `stop()` now. The Garden's filter strip clipping at narrow viewports is
    pre-existing and untouched.
17. **Vault wikilink cleanup (2026-09-09).** A read-only audit of the whole link graph found 983
    dangling link occurrences across 680 distinct targets — but most of the biggest offenders were
    not missing notes at all, they were **short forms of notes that already existed** under a
    parenthetical title. `[[System 1 vs System 2]]` (35 occurrences), `[[System 2]]` (13) and
    `[[System 1]]` (1) all meant `System 1 vs System 2 (Dual-Process Theory)`; `[[Dopamine]]` (11)
    meant `Dopamine (Reward Prediction Error)`; and so on for 15 more targets. 92 links were
    rewritten to `[[Full Title|original display text]]`, so nothing a reader sees changed. Seven
    notes were added for targets whose absence was self-evident — the three Authors already named
    on Source notes in the vault (Max Bennett, James Clear, William Golding), the three key texts
    cited from their own Authors' notes (*Thinking, Fast and Slow*, *How the Mind Works*,
    *The Adapted Mind*), and `Cortisol`, which at 18 inbound links across 12 notes was the single
    most-linked missing note. Four notes that were linked-to but `publish: false` were published;
    three dead media embeds (assets purged in item 9) and one accidentally-bracketed word were
    removed. Net: 983 → 853 dangling occurrences, 680 → 651 targets.

    Two findings from that pass are worth keeping, because both are traps:

    - **A near-match is not a match.** An automated matcher proposed five retargets that were all
      wrong and would each have destroyed a real distinction: `[[The Cognitive Neuroscience]]` is
      Gazzaniga's *handbook* sitting in a Key Texts list, not the Discipline note;
      `[[Blank Slate]]` is the *concept*, which `EPM.md` deliberately links beside
      `[[The Blank Slate]]` (the Pinker book) in one sentence; `[[Perceptrons]]` is Minsky &
      Papert, not `Perception`; `[[Waking Up App]]` is the meditation app, not the Harris book.
      Verify a proposed retarget in its surrounding prose before applying it in bulk.
    - **`make_id()` is case- and punctuation-insensitive**, so `[[hippocampus]]` and
      `[[Hippocampus]]` are one target, not two gaps. Lowercase mid-sentence links are usually
      legitimate placeholders for unwritten notes rather than typos.

    This pass is also why item 18's resolver reports **0 alias/suffix hits** against the current
    vault: the links it was built to catch had already been rewritten to full titles the day
    before. The resolver's value there is prospective, for links written from now on — the two
    mechanisms are complementary, not redundant.

18. **Garden as a study tool (2026-09-10).** Four phases, each browser-verified before the next:
    (1) a rendered-`garden.html` voice test (`tests/voice_fixtures.py`, `tests/test_garden.py`) and
    plain-English widget labels (`Audio overview`, `Flashcards`, …) replacing `NEURAL_AUDIO_STREAM`
    / `Q_NODE` / `TAP TO DECRYPT`; the wikilink resolver (`content.build_link_resolver`) and the
    two-pass restructure of `_scan_vault` it required, after a survey found 668 of 901 distinct
    wikilink targets dangling on the site — most of them short mentions of notes whose titles
    carry a parenthetical; the dead `full_search_text` card parameter removed; `isTypingTarget()`
    and the `#a11y-status` live region. (2) The study layer in `review.js` and the reader
    (recall-first cover, ratings, elaboration nudge, review queue and interleaved sessions, Read /
    Study mode, Lobby teaser, Progress export/import). (3) Flashcard decks rebuilt as semantic
    lists upgraded by `flashcards.js`. (4) The outline, the `?` shortcut sheet, and the phone graph
    list. Under a one-time override four vault notes were edited mechanically: `aliases:` on the
    two parenthetical-title concepts the resolver was built for, and two dead flashcard-CSV
    references removed. A literal NUL byte that had sat inside `applySort()`'s memo key since the
    graph landed was replaced with a space and a test now forbids control bytes in the template.
    The full design rationale is in the plan that drove the work
    (on the Alienware; not in this repo).
19. **Gemini Notebook card repair (2026-09-10).** Both of that card's fields had rendered nothing
    since item 14 landed collapsible sections in `4ecc9d6`: `wrap_gemini_notebook_sections()`
    rewrites a note's `# Header` lines into `<details>`/`<summary>`, `extract_gemini_notebook_data()`
    anchors on a literal `#`, and `_scan_vault` ran the wrap *before* card generation — so all 15
    published notes read `"Synthesis data pending."` and `No Studio outputs yet` for a month while
    13 of them had a real overview sitting unused. Both fields fall back silently, which is why
    nothing failed and no test caught it. The fix is a `card_body` snapshot taken after
    `process_wikilinks()` but before the media and section passes; the reader still gets the
    wrapped body. **Don't collapse those two bodies back together** — `tests/test_pipeline.py`
    pins both halves, and the pipeline comment explains why the card also needs the raw
    `assets/...` lines.

    What the card says changed with it: Overview is now the blockquote under the header (a real
    section *is* the whole report, 20k–38k chars, so the old whole-section read truncated to a
    fragment of paragraph one), an unfilled Templater stub renders as "Overview not written yet"
    rather than implying a pending process, and a "what's inside" strip plus a `topic/*` chip row
    fill the card — Gemini is the only published type with no link field of its own, averaging
    under one outbound wikilink per note. The chips' `#cardGrid` listener **captures**; the card
    is an `<article onclick="openNote(...)">` whose inline handler otherwise wins the bubble and
    opens the note on top of the filter.

    Three traps worth keeping, each of which cost real time here:

    - **A citation URL can contain `assets/`.** These notes cite sources by URL and several of
      those carry the segment themselves (`https://assets.csom.umn.edu/assets/166364.pdf`), so an
      unanchored pattern reports live citations as missing files. `_ASSET_REF_RE` needs its
      lookbehind.
    - **`info` fails AA as small text in the dark themes** (3.97:1 CYBER_PRIME, 4.25:1 GRIZZ),
      while `tests/test_theming.py`'s original sweep only checked TIMBERLINE — an accent-coloured
      13px label ships a real failure with the suite green. A second test now covers
      `text_main`/`text_muted` across every theme.
    - **Reading a colour right after switching `data-theme` in JS returns the *previous* theme's
      value**, even after forcing layout, while `body`'s background updates immediately — so a
      loop over themes silently pairs each new background with the old text colour and produces
      confident nonsense. Compute per-theme contrast in Python from `THEME_CONFIG`; use the
      browser only for a spot-check after a real reload.

    In the same pass the false claim that purged media "render as dead players" was removed from
    this file (it was already untrue: `process_gemini_notebook_media()` drops the path and the
    section wrapper drops the emptied section — the built page has zero `<audio>` tags), and under
    a one-time override the 16 now-pointless media references were deleted from the 9 notes that
    named them, which is what silenced the standing `⚠️ 16 media widget(s) skipped` build warning.
    A Studio output now requires a resolving asset in all nine cases, replacing an "any content
    counts" fallback that promoted a section whose only remaining text was a citation URL.
20. **Toolkit detail window (2026-09-14).** Clicking a Lobby Toolkit card, or a new "More about
    {name}" button under the readout, opens a native `<dialog>` (`#toolkit-sheet` in
    `indextemplate.html`) with a longer "What it is" / "How I use it" explanation of that tool —
    `what_it_is` and `how_i_use_it`, two new optional fields on every `user_config.json`
    `tech_stack` entry, alongside the existing `name`/`type`/`icon`/`desc`. The dialog reuses
    `.shortcut-sheet`'s surface, border, radius, width and backdrop (`main.css`) rather than a new
    floating-panel pattern, and is modeled directly on `gardentemplate.html`'s own
    `#shortcut-sheet`: `showModal()` for the focus trap and Escape handling, a stored
    `document.activeElement` restored on close. It adds one thing that sheet lacks: a
    click-outside-to-close check (`e.target === sheet` and outside
    `sheet.getBoundingClientRect()`, so dragging the dialog's own scrollbar on a short screen doesn't
    close it). It is JS-only, like the ring itself — with no JS the
    server-rendered readout panel still shows the first non-draft entry's name and `desc`, just
    with no way to open the fuller explanation.

    A third new field, `draft`, lets an entry be staged without publishing it: `indextemplate.html`
    filters `config.tech_stack` through `toolkit = ... | rejectattr('draft') | list` once, at the
    top of the template, and both the server-rendered readout seed and the carousel's own JS data
    loop read `toolkit` instead of the raw config. `draft` affects rendering only — it is not
    access control, since the repo is public and a draft entry's copy is still visible in the
    source diff, just not on the built page. It shipped immediately for a new Mac mini M6 entry,
    ahead of the machine's expected arrival.

    The copy pass that produced every `what_it_is`/`how_i_use_it` (and renamed "Alienware i7" to
    "Alienware Aurora R16", "Mac Mini M1" to "Mac mini M1", and dropped "vault" from three
    descriptions the voice rule already banned it from) followed rules worth keeping for the next
    entry: no version numbers, prices, "latest" claims, or ownership claims likely to go stale (a
    tool or framework changing hands doesn't make last month's card wrong); no employer-internal
    tooling or side jobs (item 15); no client names, pricing, or internal details for Rocky Mountain
    Automation AI, which one card mentions in passing; and software copy names no specific machine, so
    a future hardware swap only ever touches the hardware cards.


## Known gaps / deliberately not done

- **Card HTML is still built via Python f-strings**, not Jinja2 macros, even though Jinja is the
  templating engine for everything else. This was considered and explicitly deferred as
  higher-risk-for-the-reward while there were 3 separate card-generator functions; now that only
  `generate_garden_card_html()` remains, it may be worth reconsidering, but hasn't been done.
- **Card body vocabulary was unified in the 2026-09 voice pass** (`Definition:`, `Author:`,
  `Scope:`, `Bio:`, `Summary:` and so on, all rendered through `.field-label`). The *markup* is
  still per-type f-strings — see the bullet above.
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
- **`garden.html` is large** (~3.6MB as of 2026-09-10) because every note's full body is embedded
  inline for the instant-open modal (no network request needed). Known, not addressed — fixing it
  means trading instant-open for a fetch-on-click UX, which wasn't chosen without discussing the
  tradeoff first. The study layer added no per-note markup to it; `review.js` and `flashcards.js`
  ship as separately cached files.
- No automated accessibility, performance (Lighthouse), or visual-regression testing, and no JS
  test harness — the study layer's behaviour is verified by hand with Playwright (see
  docs/ARCHITECTURE.md, "Study layer").
- **Study progress is per-browser.** The scheduler state is localStorage only; the Progress panel's
  export/import is the whole sync story. A backend or a synced store was deliberately not added —
  the site has no server and promises no tracking.
- **The `Contrasts With` field is still empty across the vault**, and the elaboration nudge would
  be strictly better with it: a contrast edge is exactly the confusable pair interleaved practice
  should juxtapose. Content work, not code — `tools/vault_health.py --report promotion` lists the
  candidates.
