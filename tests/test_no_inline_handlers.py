"""No page carries an inline event handler (backlog B02).

A Content-Security-Policy without 'unsafe-inline' refuses onclick="..." and
its siblings, so every control names its action in a data attribute and a
delegated listener dispatches it (assets/js/utils.js). This checks the
rendered pages and the engine's own markup, so a handler slipped back into a
template or an f-string fails here before the policy would refuse it live.
"""
import re

from markupsafe import Markup

from engine.cards import generate_garden_card_html, link_pill
from engine.content import process_wikilinks

from tests.test_about import render_about
from tests.test_garden import render_garden
from tests.test_lobby import render_index

# An attribute, not a word: `on` + letters, `=`, then a quote. The JS source
# inside the pages talks about events ("addEventListener('click'") without
# ever matching this.
INLINE_HANDLER_RE = re.compile(r"""\son[a-z]+\s*=\s*["']""")
JAVASCRIPT_URL_RE = re.compile(r"""(href|src)\s*=\s*["']\s*javascript:""", re.IGNORECASE)


def _assert_clean(html, where):
    hits = [m.group(0) for m in INLINE_HANDLER_RE.finditer(html)]
    assert hits == [], f"{where} carries inline event handlers: {hits[:5]}"
    assert JAVASCRIPT_URL_RE.search(html) is None, f"{where} carries a javascript: URL"


def test_the_lobby_has_no_inline_handlers():
    _assert_clean(render_index(), "index.html")


def test_the_garden_has_no_inline_handlers():
    _assert_clean(render_garden(), "garden.html")


def test_the_about_page_has_no_inline_handlers():
    _assert_clean(render_about(), "about.html")


def test_a_card_and_its_pills_have_no_inline_handlers():
    meta = {"type": "concept", "tags": ["topic/memory"], "maturity": "seed"}
    body = Markup('**🔗 Related:** <button type="button" data-note="note-b">B</button>')
    html, _ = generate_garden_card_html(meta, "A.md", "note-a", body, known_ids={"note-a", "note-b"})
    _assert_clean(str(html), "a concept card")
    _assert_clean(link_pill("note-b", "B", "x", known_ids={"note-b"}), "a live pill")


def test_a_prose_wikilink_has_no_inline_handler():
    html = process_wikilinks("See [[Some Note|the note]].")
    _assert_clean(html, "a prose wikilink")
    assert 'data-note="note-some-note"' in html
