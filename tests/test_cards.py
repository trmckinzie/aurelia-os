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
    assert "opacity-70" in html
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


def test_maturity_badge_shown_for_maturity_key():
    meta = {"type": "concept", "maturity": "evergreen", "tags": []}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body", "search")
    assert "🌳" in html


def test_maturity_badge_shows_text_label_and_scales_fill_with_level():
    # The badge should be readable from the label alone, not just the emoji,
    # and its visual weight (outline -> tint -> solid) should track the
    # seed -> growing -> evergreen progression using the card's own identity
    # color rather than a new theme color.
    seed_html = generate_garden_card_html(
        {"type": "concept", "maturity": "seed", "tags": []}, "A.md", "note-a", "body", "search")
    growing_html = generate_garden_card_html(
        {"type": "concept", "maturity": "growing", "tags": []}, "B.md", "note-b", "body", "search")
    evergreen_html = generate_garden_card_html(
        {"type": "concept", "maturity": "evergreen", "tags": []}, "C.md", "note-c", "body", "search")

    assert "Seed" in seed_html and "bg-aurelia-primary/15" not in seed_html
    assert "Growing" in growing_html and "bg-aurelia-primary/15" in growing_html
    assert "Evergreen" in evergreen_html and "bg-aurelia-primary text-aurelia-inverted" in evergreen_html


def test_maturity_badge_shown_for_maturity_tag_fallback():
    # No `maturity:` key -- falls back to a maturity/* tag, same precedence
    # pattern as `type` resolution (key wins, tag is the fallback for notes
    # edited without it).
    meta = {"type": "concept", "tags": ["maturity/growing"]}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body", "search")
    assert "🌿" in html


def test_maturity_badge_ignores_status_tag():
    # status/* is the separate lifecycle axis now (active/reading/queued/
    # archive) -- it must NOT be read as a maturity signal, even though it
    # used to be, back when the two axes shared one tag namespace.
    meta = {"type": "concept", "tags": ["status/evergreen"]}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body", "search")
    assert "🌱" not in html and "🌿" not in html and "🌳" not in html


def test_maturity_badge_absent_without_maturity_signal():
    meta = {"type": "concept", "tags": ["topic/foo"]}
    html = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body", "search")
    assert "🌱" not in html and "🌿" not in html and "🌳" not in html


def test_source_card_status_badge_reads_status_key():
    meta = {"type": "source", "status": "reading", "tags": []}
    html = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body", "search")
    assert ">READING<" in html


def test_source_card_status_badge_falls_back_to_status_tag():
    # No `status:` key -- falls back to a status/* tag, same precedence
    # pattern as maturity resolution.
    meta = {"type": "source", "tags": ["status/queued"]}
    html = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body", "search")
    assert ">QUEUED<" in html


def test_source_card_status_badge_defaults_to_archived():
    meta = {"type": "source", "tags": []}
    html = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body", "search")
    assert ">ARCHIVED<" in html


def test_source_card_status_badge_ignores_unrelated_tag_substrings():
    # Regression guard for the bug this replaced: a tag merely CONTAINING
    # "reading" or "seed" (e.g. a topic tag) must not flip the badge the way
    # a naive `"seed" in str(tags)` substring check used to.
    meta = {"type": "source", "tags": ["topic/reading-list", "topic/seedling"]}
    html = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body", "search")
    assert ">ARCHIVED<" in html


def test_gemini_notebook_card_renders_label_type_and_color():
    body = """
# 📚 Lit Review Overview
> A synthesis of the source material.

# 🎙️ Audio Overview
assets/audio/example.m4a
"""
    meta = {"type": "gemini-notebook", "tags": []}
    html = generate_garden_card_html(meta, "A Notebook.md", "note-a-notebook", body, "search")
    assert "GEMINI NOTEBOOK" in html
    assert 'data-type="gemini-notebook"' in html
    assert "border-aurelia-info" in html


def test_deep_dive_card_renders_premise_synthesis_and_related():
    meta = {"type": "deep-dive", "maturity": "growing", "tags": []}
    body = """**🔗 Related:** <button onclick="openNote('note-idea')">Idea</button>

---

# A Deep Dive

*A short premise line*

---

## Part 3: The Plain-English Summary

The synthesis text goes here.
"""
    html = generate_garden_card_html(meta, "A Deep Dive.md", "note-a-deep-dive", body, "search", known_ids={"note-idea"})
    assert 'data-type="deep-dive"' in html
    assert "DEEP DIVE" in html
    assert "border-aurelia-insight" in html
    assert "A short premise line" in html
    assert "The synthesis text goes here." in html
    assert "onclick=\"openNote('note-idea'); event.stopPropagation()\"" in html


def test_deep_dive_card_shows_no_links_placeholder_when_related_empty():
    meta = {"type": "deep-dive", "maturity": "seed", "tags": []}
    body = "*A premise*\n\n## Part 3: Summary\n\nSome text.\n"
    html = generate_garden_card_html(meta, "N.md", "note-n", body, "search")
    assert "NO_LINKS_DETECTED" in html
