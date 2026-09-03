from engine.content import (
    dim_dangling_links,
    get_malformed_count,
    make_id,
    parse_body,
    parse_frontmatter,
    process_wikilinks,
    reset_malformed_count,
    wrap_gemini_notebook_sections,
)


def test_make_id_slugifies_filename():
    assert make_id("My Cool Note.md") == "note-my-cool-note"


def test_make_id_strips_non_alnum():
    assert make_id("2026-03-07.md") == "note-2026-03-07"


def test_parse_frontmatter_no_frontmatter_returns_defaults():
    meta = parse_frontmatter("# Just a heading\nbody text")
    assert meta == {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}


def test_parse_frontmatter_basic_fields():
    content = """---
publish: true
type: project
status: active
role: Lead Researcher
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["publish"] is True
    assert meta["type"] == "project"
    assert meta["status"] == "active"
    assert meta["role"] == "Lead Researcher"


def test_parse_frontmatter_block_list_tags():
    content = """---
publish: true
tags:
  - topic/one
  - topic/two
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["tags"] == ["topic/one", "topic/two"]


def test_parse_frontmatter_inline_list_tags():
    content = """---
publish: true
tags: [alpha, beta]
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["tags"] == ["alpha", "beta"]


def test_parse_frontmatter_does_not_leak_other_list_fields_into_tags():
    # Regression test: the old regex parser fell back to grabbing *any*
    # "- item" line in the whole frontmatter block when tags looked empty,
    # which bled unrelated list fields (like tech_stack) into tags.
    content = """---
publish: true
tags:
  - topic/one
tech_stack:
  - Python
  - Zotero
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["tags"] == ["topic/one"]
    assert meta["tech_stack"] == ["Python", "Zotero"]


def test_parse_frontmatter_date_falls_back_to_created():
    # Quoted so YAML keeps it a string, isolating the fallback logic from
    # YAML's own date-typing behavior (covered separately below).
    content = """---
publish: true
created: "2026-01-01"
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["date"] == "2026-01-01"


def test_parse_frontmatter_unquoted_date_parses_as_date_object():
    # YAML infers unquoted ISO dates as datetime.date, not str. This is
    # intentional PyYAML behavior; callers that need a string must str() it
    # themselves (see the str() guards in cards.py/pipeline.py).
    import datetime

    content = """---
publish: true
created: 2026-01-01
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["date"] == datetime.date(2026, 1, 1)


def test_parse_frontmatter_strips_unfilled_templater_braces():
    content = """---
publish: true
date: "{{date}}"
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["date"] == "date"


def test_parse_frontmatter_malformed_yaml_falls_back_to_defaults():
    # e.g. a Templater export template with unquoted {{placeholder}} syntax
    content = """---
citekey: {{citekey}}
---
body
"""
    meta = parse_frontmatter(content)
    assert meta["publish"] is False
    assert meta["type"] == "unknown"


def test_malformed_frontmatter_increments_shared_counter():
    # pipeline.py reads this counter to print a build-log summary line when
    # a bulk vault edit silently drops notes for bad YAML -- see
    # get_malformed_count/reset_malformed_count in content.py.
    reset_malformed_count()
    assert get_malformed_count() == 0
    parse_frontmatter("---\ncitekey: {{citekey}}\n---\nbody")
    parse_frontmatter("---\ncitekey: {{citekey}}\n---\nbody")
    assert get_malformed_count() == 2
    reset_malformed_count()
    assert get_malformed_count() == 0


def test_well_formed_frontmatter_does_not_increment_counter():
    reset_malformed_count()
    parse_frontmatter("---\npublish: true\n---\nbody")
    assert get_malformed_count() == 0


def test_parse_body_returns_content_after_frontmatter():
    content = "---\npublish: true\n---\nActual body text"
    assert parse_body(content) == "Actual body text"


def test_parse_body_no_frontmatter_returns_whole_content():
    assert parse_body("Just body, no frontmatter") == "Just body, no frontmatter"


# --- frontmatter fence is a whole line, not a substring (audit #24) ---------

def test_parse_frontmatter_ignores_triple_dash_inside_a_value():
    content = (
        "---\n"
        "title: Before---After\n"
        "publish: true\n"
        "type: concept\n"
        "---\n"
        "Body text\n"
    )
    meta = parse_frontmatter(content)
    assert meta["title"] == "Before---After"
    assert meta["publish"] is True
    assert meta["type"] == "concept"


def test_parse_body_ignores_triple_dash_inside_a_frontmatter_value():
    content = (
        "---\n"
        "title: Before---After\n"
        "publish: true\n"
        "---\n"
        "Body text\n"
    )
    assert parse_body(content) == "Body text"


def test_parse_body_ignores_triple_dash_mid_line_in_the_body():
    content = (
        "---\n"
        "publish: true\n"
        "---\n"
        "A well---known result.\n"
    )
    assert parse_body(content) == "A well---known result."


def test_parse_body_keeps_a_horizontal_rule_in_the_body():
    content = (
        "---\n"
        "publish: true\n"
        "---\n"
        "Intro paragraph.\n"
        "\n"
        "---\n"
        "\n"
        "Section after the rule.\n"
    )
    body = parse_body(content)
    assert body.startswith("Intro paragraph.")
    assert "---" in body
    assert body.endswith("Section after the rule.")


def test_parse_frontmatter_tolerates_trailing_whitespace_on_the_fence():
    content = "---  \npublish: true\n---\t\nBody"
    meta = parse_frontmatter(content)
    assert meta["publish"] is True
    assert parse_body(content) == "Body"


def test_process_wikilinks_simple():
    html = process_wikilinks("See [[Some Note]] for detail")
    assert "openNote('note-some-note')" in html
    assert ">Some Note</button>" in html


def test_process_wikilinks_piped_label():
    html = process_wikilinks("[[Target Note|Custom Label]]")
    assert "openNote('note-target-note')" in html
    assert ">Custom Label</button>" in html


def test_dim_dangling_links_leaves_known_target_untouched():
    html = process_wikilinks("See [[Some Note]] for detail")
    result = dim_dangling_links(html, known_ids={"note-some-note"})
    assert result == html


def test_dim_dangling_links_rewrites_unknown_target():
    html = process_wikilinks("See [[Some Note]] for detail")
    result = dim_dangling_links(html, known_ids=set())
    assert "openNote(" not in result
    assert '<span class="opacity-70 grayscale cursor-default" title="Not yet published">Some Note</span>' in result


def test_dim_dangling_links_handles_mixed_known_and_unknown():
    html = process_wikilinks("[[Real Note]] and [[Ghost Note]]")
    result = dim_dangling_links(html, known_ids={"note-real-note"})
    assert "openNote('note-real-note')" in result
    assert ">Real Note</button>" in result
    assert "openNote('note-ghost-note')" not in result
    assert '<span class="opacity-70 grayscale cursor-default" title="Not yet published">Ghost Note</span>' in result


def test_wrap_gemini_notebook_sections_wraps_each_header():
    text = """# 📚 Lit Review Overview
Overview text.

# 🎙️ Audio Overview
Some audio widget HTML.

# 📚 Sources
> A citation.
"""
    result = wrap_gemini_notebook_sections(text)
    assert result.count("<details") == 3
    assert '<summary class="gemini-note-summary"><span class="folder-arrow">▶</span> 📚 Lit Review Overview</summary>' in result
    assert "Overview text." in result
    assert "Some audio widget HTML." in result
    assert "> A citation." in result


def test_wrap_gemini_notebook_sections_only_first_section_starts_open():
    text = "# First\nBody one.\n\n# Second\nBody two.\n"
    result = wrap_gemini_notebook_sections(text)
    first_details, second_details = result.split("<details", 2)[1:]
    assert first_details.startswith(" open")
    assert not second_details.startswith(" open")


def test_wrap_gemini_notebook_sections_no_headers_returns_text_unchanged():
    assert wrap_gemini_notebook_sections("Just plain text, no headers.") == "Just plain text, no headers."
