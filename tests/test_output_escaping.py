"""Output-encoding guards for audit finding #21 (Jinja2 autoescape was off).

Two layers are covered here:

  * the Jinja environment itself (engine/config.py) escapes by default, so a
    template author has to opt *out* rather than remember to opt in; and
  * the two producers that legitimately emit raw HTML/JSON -- cards.py and
    textutils.dumps_for_script_tag -- say so by returning Markup, and earn
    that claim by escaping the note-derived values they interpolate.

The point of the Markup half is that `|safe` scattered through templates is
unreviewable: it looks identical whether the value behind it is trustworthy or
not. A Markup return sits next to the code that built the string, where the
question "is this safe?" can actually be answered.
"""
from markupsafe import Markup

from engine.cards import generate_garden_card_html, link_pill
from engine.config import env
from engine.textutils import dumps_for_script_tag


def test_jinja_environment_autoescapes():
    # The regression guard for the whole finding. With this off, every {{ }}
    # in every template emits raw and the escaping asserted everywhere else
    # in this file is silently bypassed at the template layer.
    assert env.autoescape is True


def test_template_escapes_an_interpolated_value_by_default():
    # Proves the flag above is actually wired into rendering, not just set.
    rendered = env.from_string("<p>{{ value }}</p>").render(
        value='<script>alert(1)</script>')
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_dumps_for_script_tag_returns_markup():
    # Embedded into a <script> block by base.html/gardentemplate.html/
    # indextemplate.html with no `|safe`, so it has to carry its own
    # "already safe here" signal or autoescape would mangle the JSON.
    out = dumps_for_script_tag({"title": "a & b"})
    assert isinstance(out, Markup)
    assert env.from_string("var x = {{ payload }};").render(payload=out) == \
        'var x = {"title": "a & b"};'


def test_dumps_for_script_tag_still_breaks_up_a_closing_script_tag():
    assert "</script" not in dumps_for_script_tag({"t": "</script><img>"})


def test_generate_garden_card_html_returns_markup():
    # gardentemplate.html renders this with a bare {{ card.html }}; without
    # Markup, autoescape would emit the card as visible literal HTML.
    html = generate_garden_card_html({"type": "concept", "tags": []}, "A.md", "note-a", "b", "s")
    assert isinstance(html, Markup)


def test_card_heading_escapes_a_hostile_filename():
    # data-title was already escaped (finding #22); the visible <h3> was not.
    html = generate_garden_card_html(
        {"type": "concept", "tags": []},
        "Note <img src=x onerror=alert(1)>.md", "note-x", "b", "s")
    # The payload survives as inert text -- what matters is that the `<` is
    # encoded, so the browser never starts a tag and never runs the handler.
    assert "<img" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_link_pill_escapes_a_wikilink_label():
    # The display half of [[Target|Label]] is note-derived and lands in HTML
    # text position. It reached the page raw before this change.
    pill = link_pill("note-t", '<img src=x onerror=alert(1)>', "c", {"note-t"})
    assert "<img" not in pill
    assert "&lt;img" in pill


def test_card_prose_field_escapes_an_unterminated_tag():
    # The extractors run clean_text()/strip_html() over prose, which is why
    # these were assumed safe -- but that only strips `<[^>]+>`, i.e. tags
    # that are already closed. An unterminated `<img src=x onerror=...`
    # survives it untouched, and the next `>` in the surrounding card markup
    # closes it for the browser. So the tag-stripper is not an output
    # encoder, and the card escapes at the point of interpolation instead.
    body = "### Definition\n> <img src=x onerror=alert(1)\n"
    html = generate_garden_card_html(
        {"type": "concept", "tags": []}, "A.md", "note-a", body, "s")
    # Again: the text is allowed to survive, the tag start is not.
    assert "<img" not in html
    assert "&lt;img src=x onerror=alert(1)" in html


def test_card_prose_escaping_is_not_double_applied():
    # Escape-then-truncate would cut an entity in half; escaping a value that
    # was already escaped would show "&amp;amp;" to a reader. Neither here.
    body = "### Definition\n> Newell & Simon's symposium\n"
    html = generate_garden_card_html(
        {"type": "concept", "tags": []}, "A.md", "note-a", body, "s")
    assert "Newell &amp; Simon&#39;s symposium" in html
    assert "&amp;amp;" not in html
