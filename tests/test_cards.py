from engine.cards import generate_garden_card_html, link_pill, render_items


def test_render_items_joins_rendered_items():
    result = render_items(["a", "b"], lambda x: f"<span>{x}</span>")
    assert result == "<span>a</span><span>b</span>"


def test_render_items_empty_list_uses_fallback():
    result = render_items([], lambda x: f"<span>{x}</span>", empty_html="<em>none</em>")
    assert result == "<em>none</em>"


def test_render_items_empty_list_no_fallback_is_blank():
    assert render_items([], lambda x: x) == ""


def test_link_pill_renders_clickable_button_for_known_target():
    html = link_pill("note-a", "Alpha", "my-classes", known_ids={"note-a", "note-b"})
    assert "onclick=\"openNote('note-a'); event.stopPropagation()\"" in html
    assert "cursor-pointer" in html
    assert "Alpha" in html


def test_link_pill_renders_dimmed_text_for_dangling_target():
    html = link_pill("note-missing", "Ghost", "my-classes", known_ids={"note-a"})
    assert "onclick" not in html
    assert "opacity-40" in html
    assert "Not yet published" in html
    assert "Ghost" in html


def test_link_pill_renders_plain_text_when_never_a_link():
    html = link_pill(None, "Just Text", "my-classes", known_ids={"note-a"})
    assert "onclick" not in html
    assert "opacity-40" not in html  # not a broken link, just descriptive text
    assert "Just Text" in html


def test_generate_garden_card_html_contains_title_and_type():
    meta = {"type": "concept", "tags": []}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body text", "search text")
    assert "Some Concept" in html
    assert "CONCEPT" in html
    assert "openNote('note-some-concept')" in html


def test_concept_card_related_link_is_clickable_when_target_known():
    body = '### Definition\n> A thing.\n\n**🔗 Related:** <button onclick="openNote(\'note-other\')">Other</button>'
    html = generate_garden_card_html(
        {"type": "concept", "tags": []}, "Thing.md", "note-thing", body, "search",
        known_ids={"note-thing", "note-other"},
    )
    assert "onclick=\"openNote('note-other'); event.stopPropagation()\"" in html


def test_concept_card_related_link_is_dimmed_when_target_unpublished():
    body = '### Definition\n> A thing.\n\n**🔗 Related:** <button onclick="openNote(\'note-unpublished\')">Ghost</button>'
    html = generate_garden_card_html(
        {"type": "concept", "tags": []}, "Thing.md", "note-thing", body, "search",
        known_ids={"note-thing"},  # note-unpublished is NOT in the known set
    )
    assert "openNote('note-unpublished')" not in html
    assert "Not yet published" in html


def test_maturity_badge_shown_for_evergreen_status_tag():
    meta = {"type": "concept", "tags": ["status/evergreen"]}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body", "search")
    assert "🌳" in html


def test_maturity_badge_absent_without_status_tag():
    meta = {"type": "concept", "tags": ["topic/foo"]}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body", "search")
    assert "🌱" not in html and "🌿" not in html and "🌳" not in html
