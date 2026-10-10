from engine.cards import _connection_badge, generate_garden_card_html, link_pill, render_items


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
    assert "type=\"button\" data-note=\"note-a\"" in html
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
    html, _ = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body text")
    assert "Some Concept" in html
    assert "CONCEPT" in html
    # The card opens through its data-id (grid delegation) and its title
    # button; no inline handler names the note (B02).
    assert 'data-id="note-some-concept"' in html
    assert "openNote(" not in html


def test_concept_card_related_link_is_clickable_when_target_known():
    body = '### Definition\n> A thing.\n\n**🔗 Related:** <button type="button" data-note="note-other">Other</button>'
    html, _ = generate_garden_card_html(
        {"type": "concept", "tags": []}, "Thing.md", "note-thing", body,
        known_ids={"note-thing", "note-other"},
    )
    assert "type=\"button\" data-note=\"note-other\"" in html


def test_concept_card_related_link_is_dimmed_when_target_unpublished():
    body = '### Definition\n> A thing.\n\n**🔗 Related:** <button type="button" data-note="note-unpublished">Ghost</button>'
    html, _ = generate_garden_card_html(
        {"type": "concept", "tags": []}, "Thing.md", "note-thing", body,
        known_ids={"note-thing"},  # note-unpublished is NOT in the known set
    )
    assert "openNote('note-unpublished')" not in html
    assert "Not yet published" in html


def test_maturity_badge_shown_for_maturity_key():
    meta = {"type": "concept", "maturity": "evergreen", "tags": []}
    html, _ = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body")
    assert "🌳" in html


def test_maturity_badge_shows_text_label_and_scales_fill_with_level():
    # The badge should be readable from the label alone, not just the emoji,
    # and its visual weight (outline -> tint -> solid) should track the
    # seed -> growing -> evergreen progression using the card's own identity
    # color rather than a new theme color.
    seed_html, _ = generate_garden_card_html(
        {"type": "concept", "maturity": "seed", "tags": []}, "A.md", "note-a", "body")
    growing_html, _ = generate_garden_card_html(
        {"type": "concept", "maturity": "growing", "tags": []}, "B.md", "note-b", "body")
    evergreen_html, _ = generate_garden_card_html(
        {"type": "concept", "maturity": "evergreen", "tags": []}, "C.md", "note-c", "body")

    assert "Seed" in seed_html and "bg-aurelia-primary/15" not in seed_html
    assert "Growing" in growing_html and "bg-aurelia-primary/15" in growing_html
    assert "Evergreen" in evergreen_html and "bg-aurelia-primary text-aurelia-inverted" in evergreen_html


def test_maturity_badge_shown_for_maturity_tag_fallback():
    # No `maturity:` key -- falls back to a maturity/* tag, same precedence
    # pattern as `type` resolution (key wins, tag is the fallback for notes
    # edited without it).
    meta = {"type": "concept", "tags": ["maturity/growing"]}
    html, _ = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body")
    assert "🌿" in html


def test_maturity_badge_ignores_status_tag():
    # status/* is the separate lifecycle axis now (active/reading/queued/
    # archive) -- it must NOT be read as a maturity signal, even though it
    # used to be, back when the two axes shared one tag namespace.
    meta = {"type": "concept", "tags": ["status/evergreen"]}
    html, _ = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body")
    assert "🌱" not in html and "🌿" not in html and "🌳" not in html


def test_maturity_badge_absent_without_maturity_signal():
    meta = {"type": "concept", "tags": ["topic/foo"]}
    html, _ = generate_garden_card_html(meta, "Some Concept.md", "note-some-concept", "body")
    assert "🌱" not in html and "🌿" not in html and "🌳" not in html


def test_source_card_status_badge_reads_status_key():
    meta = {"type": "source", "status": "reading", "tags": []}
    html, _ = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body")
    assert ">READING<" in html


def test_source_card_status_badge_falls_back_to_status_tag():
    # No `status:` key -- falls back to a status/* tag, same precedence
    # pattern as maturity resolution.
    meta = {"type": "source", "tags": ["status/queued"]}
    html, _ = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body")
    assert ">QUEUED<" in html


def test_source_card_status_badge_defaults_to_archived():
    meta = {"type": "source", "tags": []}
    html, _ = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body")
    assert ">ARCHIVED<" in html


def test_source_card_status_badge_ignores_unrelated_tag_substrings():
    # Regression guard for the bug this replaced: a tag merely CONTAINING
    # "reading" or "seed" (e.g. a topic tag) must not flip the badge the way
    # a naive `"seed" in str(tags)` substring check used to.
    meta = {"type": "source", "tags": ["topic/reading-list", "topic/seedling"]}
    html, _ = generate_garden_card_html(meta, "A Book.md", "note-a-book", "body")
    assert ">ARCHIVED<" in html


def test_gemini_notebook_card_renders_label_type_and_color():
    body = """
# 📚 Lit Review Overview
> A synthesis of the source material.

# 🎙️ Audio Overview
assets/audio/example.m4a
"""
    meta = {"type": "gemini-notebook", "tags": []}
    html, _ = generate_garden_card_html(meta, "A Notebook.md", "note-a-notebook", body)
    assert "GEMINI NOTEBOOK" in html
    assert 'data-type="gemini-notebook"' in html
    assert "border-aurelia-info" in html


def test_deep_dive_card_renders_premise_synthesis_and_related():
    meta = {"type": "deep-dive", "maturity": "growing", "tags": []}
    body = """**🔗 Related:** <button type="button" data-note="note-idea">Idea</button>

---

# A Deep Dive

*A short premise line*

---

## Part 3: The Plain-English Summary

The synthesis text goes here.
"""
    html, _ = generate_garden_card_html(meta, "A Deep Dive.md", "note-a-deep-dive", body, known_ids={"note-idea"})
    assert 'data-type="deep-dive"' in html
    assert "DEEP DIVE" in html
    assert "border-aurelia-insight" in html
    assert "A short premise line" in html
    assert "The synthesis text goes here." in html
    assert "type=\"button\" data-note=\"note-idea\"" in html


def test_deep_dive_card_shows_no_links_placeholder_when_related_empty():
    meta = {"type": "deep-dive", "maturity": "seed", "tags": []}
    body = "*A premise*\n\n## Part 3: Summary\n\nSome text.\n"
    html, _ = generate_garden_card_html(meta, "N.md", "note-n", body)
    assert "No links yet" in html


def test_card_carries_the_attributes_the_garden_sorts_on():
    meta = {"type": "concept", "created": "2026-03-07", "tags": []}
    html, _ = generate_garden_card_html(
        meta, "Working Memory.md", "note-working-memory", "body",
        connections=32, created="2026-03-07",
    )
    assert 'data-connections="32"' in html
    assert 'data-created="2026-03-07"' in html
    # Sorting reads data-title rather than the <h3>, because highlightText()
    # rewrites that element's innerHTML while a search is active.
    assert 'data-title="Working Memory"' in html


def test_card_sort_attributes_default_when_not_supplied():
    # Every existing call site omits these; they must not render as "None".
    html, _ = generate_garden_card_html({"type": "concept", "tags": []}, "A.md", "note-a", "b")
    assert 'data-connections="0"' in html
    assert 'data-created=""' in html


def test_card_title_attribute_is_escaped():
    # A quote in a filename would otherwise close the attribute and let the
    # rest be parsed as markup.
    html, _ = generate_garden_card_html(
        {"type": "concept", "tags": []}, 'He said "hi".md', "note-x", "b")
    assert 'data-title="He said &quot;hi&quot;"' in html


def test_card_tags_attribute_is_escaped():
    # A frontmatter tag carrying a double quote closed data-tags and let
    # everything after it land on the <article> as real markup -- an event
    # handler, in the audit's proof-of-concept. Audit finding #22.
    html, _ = generate_garden_card_html(
        {"type": "concept", "tags": ['topic/one" onmouseover="alert(1)', "a<b"]},
        "A.md", "note-a", "b")
    assert 'data-tags="topic/one&quot; onmouseover=&quot;alert(1) a&lt;b"' in html
    assert 'onmouseover="alert(1)"' not in html
    assert "<b" not in html.split('class="', 1)[0]


def test_card_type_attribute_is_escaped():
    # data-type comes from frontmatter `type:` the same way data-tags comes
    # from `tags:`, so it is the same sink.
    html, _ = generate_garden_card_html(
        {"type": 'concept" onmouseover="alert(1)', "tags": []},
        "A.md", "note-a", "b")
    assert 'data-type="concept&quot; onmouseover=&quot;alert(1)"' in html
    assert 'onmouseover="alert(1)"' not in html


def test_card_tags_attribute_unchanged_for_ordinary_tags():
    # Escaping must be a no-op for every real tag in the vault -- the Garden's
    # filter JS reads this attribute.
    html, _ = generate_garden_card_html(
        {"type": "concept", "tags": ["topic/neuroscience", "maturity/seed"]},
        "A.md", "note-a", "b")
    assert 'data-tags="topic/neuroscience maturity/seed"' in html


def test_card_carries_the_type_label_the_reader_displays():
    # The note reader's header shows the note's type using this attribute.
    # It is emitted here rather than derived client-side because the label
    # is NOT a transform of the type slug -- see the pairs below.
    for note_type, filename, expected in [
        ("concept", "A.md", "CONCEPT"),
        ("source/book", "B.md", "SOURCE"),
        ("author", "C.md", "AUTHOR"),
        ("discipline", "D.md", "DISCIPLINE"),
        ("gemini-notebook", "E.md", "GEMINI NOTEBOOK"),
        ("deep-dive", "F.md", "DEEP DIVE"),
    ]:
        html, _ = generate_garden_card_html(
            {"type": note_type, "tags": []}, filename, "note-x", "body")
        assert f'data-label="{expected}"' in html, note_type
        # The same label the card face prints, so the reader and the card
        # can never disagree about what a note is.
        assert f">{expected}</span>" in html, note_type


def test_daily_log_card_carries_its_type_label():
    # Daily logs are detected by filename shape, not by a `type:` key, so
    # they reach the label through a different branch than the six above.
    html, _ = generate_garden_card_html({"tags": []}, "2026-03-07.md", "note-2026-03-07", "body")
    assert 'data-label="DAILY LOG"' in html


def test_card_type_label_is_escaped():
    # The fallback branch's label is a constant, but the attribute is built
    # by f-string interpolation like its neighbours -- assert the escaping
    # path is wired rather than trusting that today's labels stay ASCII.
    html, _ = generate_garden_card_html({"type": "unknown-type", "tags": []}, "A.md", "note-a", "b")
    assert 'data-label="NOTE"' in html


def test_connection_badge_renders_count_and_pluralises():
    assert "2 links to or from this note" in _connection_badge(2, "border-aurelia-primary")
    assert "1 link to or from this note" in _connection_badge(1, "border-aurelia-primary")


def test_connection_badge_is_silent_at_zero():
    # An orphan reads better as an absent chip than as a "0" that looks
    # like a defect.
    assert _connection_badge(0, "border-aurelia-primary") == ""


# --- the card is an article; its title is the one control (B19) -----------

def _card_html(title="Alpha Note"):
    meta = {"type": "concept", "tags": [], "maturity": "seed"}
    html, _ = generate_garden_card_html(meta, f"{title}.md", "note-alpha", "body text", known_ids={"note-alpha"})
    return str(html)


def test_card_article_is_not_a_button():
    # A button's children are presentational, so the pills inside a
    # role=button card were unreachable to a screen reader (axe
    # nested-interactive, backlog B19).
    html = _card_html()
    article = html[html.index("<article"):html.index(">", html.index("<article"))]
    assert "role=" not in article
    assert "tabindex=" not in article
    assert "aria-label=" not in article
    # No inline handler either (B02): the grid's delegated listener opens
    # data-id.
    assert "onclick" not in article
    assert 'data-id="note-alpha"' in article


def test_card_title_is_the_one_control_that_opens_the_note():
    html = _card_html("Alpha Note")
    assert ('<h3 class="display-md text-aurelia-text group-hover:text-aurelia-text transition-colors">'
            '<button type="button" class="card-open" tabindex="-1" data-id="note-alpha">Alpha Note</button></h3>') in html
    # Exactly one control opens this note from the card face: the title.
    # The pills carry their own targets and the article its pointer handler.
    assert html.count('class="card-open"') == 1


def test_card_title_control_escapes_the_title():
    html = _card_html('Say "hi" <b>')
    button = html[html.index('class="card-open"'):html.index("</button>", html.index('class="card-open"'))]
    assert "<b>" not in button
    assert '"hi"' not in button
    assert "&lt;b&gt;" in button
