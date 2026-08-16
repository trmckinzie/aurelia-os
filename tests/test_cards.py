from engine.cards import generate_garden_card_html, generate_protocol_card, render_items


def test_render_items_joins_rendered_items():
    result = render_items(["a", "b"], lambda x: f"<span>{x}</span>")
    assert result == "<span>a</span><span>b</span>"


def test_render_items_empty_list_uses_fallback():
    result = render_items([], lambda x: f"<span>{x}</span>", empty_html="<em>none</em>")
    assert result == "<em>none</em>"


def test_render_items_empty_list_no_fallback_is_blank():
    assert render_items([], lambda x: x) == ""


def test_generate_garden_card_html_contains_title_and_type():
    meta = {"type": "concept", "tags": []}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body text", "search text")
    assert "Some Concept" in html
    assert "CONCEPT" in html
    assert "openNote('note-some-concept')" in html


def test_generate_protocol_card_uses_frontmatter_id_not_filename():
    meta = {"type": "protocol", "tags": []}
    body = "## Sequence\n- [ ] step one\n## System Logic\n> logic here\n"
    html = generate_protocol_card(meta, body, "01 Morning Launch", "note-01-morning-launch", p_id_override="PROT_01")
    assert "PROT_01" in html
    assert "openNote('PROT_01')" in html
