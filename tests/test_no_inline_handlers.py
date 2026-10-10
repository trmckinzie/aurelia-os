"""No page carries an inline event handler or style attribute (backlog B02).

The Content-Security-Policy (engine/csp.py) hashes inline <script> and
<style> blocks and allows nothing else inline, so every control names its
action in a data attribute and a delegated listener dispatches it
(assets/js/utils.js), and every style lives in a stylesheet or is set
through the CSSOM. This checks the rendered pages and the engine's own
markup, so a handler or style attribute slipped back into a template or an
f-string fails here before the policy would refuse it live.
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
STYLE_ATTR_RE = re.compile(r"""\sstyle\s*=\s*["']""")
JAVASCRIPT_URL_RE = re.compile(r"""(href|src)\s*=\s*["']\s*javascript:""", re.IGNORECASE)
_BLOCK_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)


def _markup_only(html):
    """The page without its <script> and <style> bodies, so JS source that
    builds markup strings is checked separately by the browser suite and
    `const style = ...` in it cannot match here."""
    return _BLOCK_RE.sub("", html)


def _assert_clean(html, where):
    hits = [m.group(0) for m in INLINE_HANDLER_RE.finditer(html)]
    assert hits == [], f"{where} carries inline event handlers: {hits[:5]}"
    assert JAVASCRIPT_URL_RE.search(html) is None, f"{where} carries a javascript: URL"
    styles = STYLE_ATTR_RE.findall(_markup_only(html))
    assert styles == [], f"{where} carries {len(styles)} inline style attribute(s)"


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


def test_every_page_renders_the_policy_slot_first_in_head():
    # engine/csp.py fills the token after the build; it has to precede the
    # theme boot script, or that script would run outside the policy.
    for html, where in ((render_index(), "index.html"), (render_garden(), "garden.html"), (render_about(), "about.html")):
        head = html.index("<head>")
        meta = html.index('<meta http-equiv="Content-Security-Policy" content="@@csp@@">')
        first_script = html.index("<script", head)
        assert head < meta < first_script, where


def test_a_prose_wikilink_has_no_inline_handler():
    html = process_wikilinks("See [[Some Note|the note]].")
    _assert_clean(html, "a prose wikilink")
    assert 'data-note="note-some-note"' in html
