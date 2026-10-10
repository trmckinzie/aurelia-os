from engine.textutils import (
    clean_text,
    dumps_for_script_tag,
    escape_attr,
    extract_links,
    first_blockquote_after,
    section_after_header,
    strip_html,
    strip_wikilinks,
    truncate,
)


def test_strip_html_removes_tags_keeps_text():
    assert strip_html('<button class="x" onclick="y()">Label</button>') == "Label"


def test_strip_wikilinks_plain():
    assert strip_wikilinks("See [[Some Note]] for detail") == "See Some Note for detail"


def test_strip_wikilinks_piped():
    assert strip_wikilinks("[[Target|Display Label]]") == "Display Label"


def test_clean_text_handles_rendered_button_wikilink():
    rendered = '<button type="button" data-note="x" class="c">The Selfish Gene</button>'
    assert clean_text(rendered) == "The Selfish Gene"


def test_truncate_short_text_unchanged():
    assert truncate("short", 100) == "short"


def test_truncate_long_text_gets_ellipsis():
    result = truncate("a" * 200, 10)
    assert result == "a" * 10 + "..."


def test_truncate_handles_none():
    assert truncate(None, 10) == ""


def test_extract_links_prefers_rendered_buttons_and_keeps_target_id():
    section = '<button type="button" data-note="note-a">Alpha</button> <button type="button" data-note="note-b">Beta</button>'
    assert extract_links(section) == [("note-a", "Alpha"), ("note-b", "Beta")]


def test_extract_links_falls_back_to_raw_brackets_deriving_id_via_make_id():
    section = "[[Alpha]] and [[Target Note|Beta]]"
    assert extract_links(section) == [("note-alpha", "Alpha"), ("note-target-note", "Beta")]


def test_extract_links_returns_empty_list_when_no_links_present():
    assert extract_links("just plain text, no links here") == []


def test_section_after_header_stops_at_next_header():
    text = "## Core Concepts\n- one\n- two\n### Next Section\nignored"
    section = section_after_header(text, r'##\s*.*Core Concepts.*')
    assert "one" in section and "Next Section" not in section


def test_section_after_header_missing_returns_none():
    assert section_after_header("no headers here", r'##\s*.*Missing.*') is None


def test_first_blockquote_after_header():
    text = "### Definition\n> The real definition\nmore text"
    assert first_blockquote_after(text, r'###\s*.*Definition.*') == "The real definition"


def test_first_blockquote_after_falls_back_to_any_blockquote():
    text = "no matching header\n> fallback quote"
    assert first_blockquote_after(text, r'###\s*.*Missing.*') == "fallback quote"


def test_first_blockquote_after_returns_none_when_absent():
    assert first_blockquote_after("nothing here", r'###\s*.*Missing.*') is None


def test_dumps_for_script_tag_escapes_script_close_tag():
    payload = {"title": "</script><script>alert(1)</script>"}
    dumped = dumps_for_script_tag(payload)
    assert "</script>" not in dumped
    assert "<\\/script>" in dumped


# --- escape_attr() (engine/cards.py's double-quoted HTML attributes) ---

def test_escape_attr_escapes_a_double_quote_that_would_close_the_attribute():
    # The exact audit #22 proof-of-concept: an unescaped quote in a
    # vault-derived value closes the attribute early, and everything after
    # it on the <article> is parsed as live markup.
    out = escape_attr('concept" onmouseover="alert(1)')
    assert out == 'concept&quot; onmouseover=&quot;alert(1)'
    assert '"' not in out


def test_escape_attr_escapes_angle_brackets():
    out = escape_attr("a<b>c")
    assert out == "a&lt;b&gt;c"
    assert "<" not in out and ">" not in out


def test_escape_attr_escapes_ampersand():
    assert escape_attr("Newell & Simon") == "Newell &amp; Simon"


def test_escape_attr_escapes_ampersand_before_the_other_entities():
    # & has to go first: escaping the others first and & last would
    # double-escape their own entities (&quot; -> &amp;quot;).
    assert escape_attr('<"&">') == "&lt;&quot;&amp;&quot;&gt;"


def test_escape_attr_is_idempotent_on_plain_text():
    assert escape_attr("topic/neuroscience") == "topic/neuroscience"


def test_escape_attr_coerces_non_string_values():
    # Frontmatter values YAML infers as non-strings (an int connection
    # count, a bare `created:` date) reach this the same way a string does.
    assert escape_attr(32) == "32"
    assert escape_attr(None) == "None"
