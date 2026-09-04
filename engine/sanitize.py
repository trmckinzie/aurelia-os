"""Sanitizes note-authored HTML before it is published (audit finding #21).

A note's rendered body is the one thing on this site that is genuinely
note-derived HTML rather than plain text: it has to keep its formatting, so
escaping it wholesale (what autoescape does everywhere else -- see
engine/config.py) would turn every published note into a wall of literal
markup. It needs a real allowlist sanitizer instead, which is what this is.

nh3 rather than bleach: nh3 is the maintained option. bleach was formally
deprecated by Mozilla in 2023 and its README says so; nh3 is a binding to
Rust's `ammonia`, still released (0.3.7 at time of writing). Ammonia is also
allowlist-based by construction -- it parses to a DOM and re-serializes only
what it recognizes, so an unknown or malformed construct fails closed rather
than slipping through a regex.


WHY THIS RUNS BEFORE process_wikilinks(), NOT AFTER
---------------------------------------------------
The body that reaches gardentemplate.html is a *mix*: note-authored markdown
plus HTML the engine injects itself -- wikilink <button onclick="openNote(...)">
elements, <audio>/<video>/<img> media widgets, the flashcard deck's flip
handlers, the <details> section wrappers. Those carry exactly the things a
sanitizer is built to remove (event handlers, media tags nh3 does not allow),
so sanitizing the finished body would delete the site's core feature set.

Sanitizing the raw note body first, and letting the engine add its own HTML
afterwards, keeps both properties: the untrusted half is cleaned, and the
trusted half never meets the cleaner. engine/pipeline.py._scan_vault() is
where that ordering is enforced.


WHY THE UNESCAPE ON EITHER SIDE
-------------------------------
gardentemplate.html's openNote() reads the stored body back out like this:

    const txt = document.createElement("textarea");
    txt.innerHTML = rawEl.innerHTML;
    modalContent.innerHTML = marked.parse(txt.value, { breaks: true });

A <textarea> is an RCDATA element, so assigning innerHTML decodes character
references but does not parse tags -- `txt.value` is the stored text with
every HTML entity decoded. That single fact drives both calls here:

  * Trailing unescape: a sanitizer that *escaped* a payload rather than
    removing it would be undone by that decode -- `&lt;script&gt;` would come
    back as a live `<script>` on its way into marked.parse(), which does not
    sanitize (marked dropped its `sanitize` option in v5). So this must be a
    strip-based cleaner, and the trailing unescape simply puts the server on
    the same footing as the browser: what we check is what will run. It is
    also what keeps markdown intact -- nh3 escapes `>` in text to `&gt;`,
    which would otherwise break every blockquote, and with it the `>`-keyed
    extractors in engine/extractors.py.

  * Leading unescape: for the same reason, a note that literally contains
    `&lt;script&gt;` is a live script once the browser decodes it. Decoding
    first means nh3 sees that payload as the tag it is about to become, and
    removes it, instead of dutifully re-escaping it.

The pair terminates: the only `&lt;` nh3 re-introduces mark `<` characters
the HTML parser already refused to treat as a tag start (`a < b`, `3<5`), so
decoding them a second time cannot produce a tag either.
"""
import html

import nh3

# Tags whose *contents* are dropped along with the tag. Everything else that
# is not on nh3's allowlist has its tag removed but its text kept, which is
# right for prose (an unknown <foo>bar</foo> should still read "bar") and
# wrong for these two, where the text is the payload.
#
# This matches nh3's own default; it is stated explicitly because it is the
# difference between deleting a script and publishing its source as visible
# text.
_CLEAN_CONTENT_TAGS = {"script", "style"}


def sanitize_note_html(text):
    """Strips anything executable out of a note's raw markdown body.

    Uses nh3's default allowlist, which is deliberately not restated here as
    a 75-entry copy that would silently drift from the library's. What it
    admits, in the terms that matter for this site: ordinary formatting
    (headings, bold/italic, lists, blockquotes), links, images, code and
    <pre>, tables, and <details>/<summary>. What it refuses, all verified in
    tests/test_sanitize.py rather than assumed: <script> and <style> (tag and
    contents), <iframe>, <object>, <embed>, <form>, <svg>, every on* event
    handler attribute, and javascript:/data: URLs in href and src.

    Markdown is untouched: nh3 sees `## Heading`, `**bold**`, `| tables |`
    and `[[Wikilinks]]` as text, and the unescape round-trip described in
    the module docstring returns them byte-identical.
    """
    if not text:
        return text
    return html.unescape(nh3.clean(html.unescape(text),
                                   clean_content_tags=_CLEAN_CONTENT_TAGS))


def sanitize_to_text(text):
    """Strips ALL markup out of an untrusted fragment, keeping its text.

    For values that are plain text by contract and get interpolated into
    HTML the engine builds itself -- currently the question/answer cells of
    a flashcard CSV (engine/content.py's _render_flashcards).

    Why not html.escape()? Because of the same `<textarea>` round-trip the
    module docstring describes: openNote() decodes character references
    before handing the text to marked.parse(), which does not sanitize. An
    escaped `&lt;img src=x onerror=...&gt;` therefore comes back as a live
    tag on the way into innerHTML. Escaping closes the page-load sink and
    leaves the open-the-note sink wide open, so this strips, exactly as
    sanitize_note_html() does and for exactly the same reason.

    Same unescape-clean-unescape pair, same termination argument: what nh3
    re-escapes is only the `<` characters the HTML parser already refused to
    treat as a tag start (`a < b`), so decoding them once more cannot
    produce a tag.
    """
    if not text:
        return text
    return html.unescape(nh3.clean(html.unescape(text),
                                   tags=set(),
                                   clean_content_tags=_CLEAN_CONTENT_TAGS))
