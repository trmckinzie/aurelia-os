# Security findings from the 2026-08 audit

Split out of `CLAUDE.md` on 2026-09-10 so that file could stay a lean entry point. `CLAUDE.md`
is the lean entry point; this file is the finding-by-finding record.

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
- **~~Client-side: topic-cloud `onclick` interpolated a raw tag, `highlightText()` built
  `new RegExp()` from unescaped search input~~ — FIXED.** `highlightText()` now uses
  `escapeRegExp()` (defined in `assets/js/utils.js`) wrapped in a try/catch (commit da3a4d4,
  2026-09-02) — the second half of this bullet used to describe a live functional bug (typing `(`
  threw and silently killed search); that no longer happens. The topic cloud has used
  `data-tag="${escapeHtml(tag)}"` plus a delegated listener rather than an inline `onclick` since
  commit 1c41247.
