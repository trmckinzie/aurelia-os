import os

import pytest

from engine import content as content_module
from engine.content import (
    dim_dangling_links,
    get_malformed_count,
    make_id,
    parse_body,
    parse_frontmatter,
    process_gemini_notebook_media,
    process_wikilinks,
    reset_malformed_count,
    wrap_gemini_notebook_sections,
)


# Moved to the top of the module (was previously defined mid-file, just
# above the wikilink-resolver tests it exists for) so a future second
# `setup_function` definition anywhere later in the file can't silently
# shadow/replace this one -- pytest only honors the last `setup_function`
# it sees per module, and that failure mode is invisible until a test that
# depends on the reset starts flaking.
def setup_function(_function):
    content_module.reset_wikilink_resolution_counts()


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


# --- publish: is an allowlist, not truthiness (audit #23) ------------------

@pytest.mark.parametrize("raw", ["true", "True", "TRUE", "yes", "'1'", '"true"'])
def test_publish_accepts_recognized_true_values(raw):
    assert parse_frontmatter(f"---\npublish: {raw}\n---\nbody")["publish"] is True


@pytest.mark.parametrize("raw", ["false", "False", "'false'", '"no"', "'0'", "no"])
def test_publish_rejects_recognized_false_values(raw):
    assert parse_frontmatter(f"---\npublish: {raw}\n---\nbody")["publish"] is False


def test_publish_quoted_false_string_does_not_publish():
    # The regression itself: bool("false") is True.
    content = "---\npublish: \"false\"\ntype: concept\n---\nbody"
    assert parse_frontmatter(content)["publish"] is False


def test_publish_unrecognized_value_does_not_publish_and_warns(capsys):
    content = "---\npublish: maybe later\n---\nbody"
    assert parse_frontmatter(content)["publish"] is False
    assert "Unrecognized publish value" in capsys.readouterr().out


def test_publish_recognized_false_does_not_warn(capsys):
    # Every unpublished note in the vault says `publish: false`; warning on
    # those would bury the warning that matters.
    parse_frontmatter("---\npublish: false\n---\nbody")
    assert "Unrecognized publish value" not in capsys.readouterr().out


def test_publish_missing_key_defaults_to_false_without_warning(capsys):
    assert parse_frontmatter("---\ntype: concept\n---\nbody")["publish"] is False
    assert "Unrecognized publish value" not in capsys.readouterr().out


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


# --- asset resolution is containment-checked (audit #20) -------------------

def _asset_sandbox(tmp_path, monkeypatch):
    """Points resolve_asset() at a throwaway vault/repo pair under tmp_path.

    The real vault is never touched by these tests -- every path below is
    created inside tmp_path.
    """
    vault = tmp_path / "vault"
    (vault / "assets" / "flashcards").mkdir(parents=True)
    (vault / "assets" / "flashcards" / "deck.csv").write_text("q,a\n", encoding="utf-8")
    (vault / "assets" / "flashcards" / "unit-1").mkdir()
    (vault / "assets" / "flashcards" / "unit-1" / "nested.csv").write_text(
        "q,a\n", encoding="utf-8")

    # The thing a traversal would be reaching for: outside both bases.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secrets.csv").write_text("user,password\n", encoding="utf-8")

    monkeypatch.setattr(content_module, "VAULT_PATH", str(vault))
    monkeypatch.setattr(content_module, "ROOT_DIR", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir()
    return vault, outside


def test_resolve_asset_returns_a_legitimate_asset(tmp_path, monkeypatch):
    vault, _ = _asset_sandbox(tmp_path, monkeypatch)
    resolved = content_module.resolve_asset("assets/flashcards/deck.csv")
    assert resolved is not None
    assert os.path.samefile(resolved, vault / "assets" / "flashcards" / "deck.csv")


def test_resolve_asset_allows_a_nested_subdirectory(tmp_path, monkeypatch):
    # Containment must not mean "one level deep only".
    vault, _ = _asset_sandbox(tmp_path, monkeypatch)
    resolved = content_module.resolve_asset("assets/flashcards/unit-1/nested.csv")
    assert resolved is not None
    assert os.path.samefile(
        resolved, vault / "assets" / "flashcards" / "unit-1" / "nested.csv")


def test_resolve_asset_refuses_a_dotdot_escape(tmp_path, monkeypatch, capsys):
    _, outside = _asset_sandbox(tmp_path, monkeypatch)
    escape = "assets/flashcards/../../../outside/secrets.csv"
    # Sanity: the file it is reaching for really does exist, so a None result
    # is the containment check and not just a missing file.
    assert (outside / "secrets.csv").exists()
    assert content_module.resolve_asset(escape) is None
    assert "Refusing out-of-tree asset reference" in capsys.readouterr().out


def test_resolve_asset_refuses_an_absolute_path(tmp_path, monkeypatch):
    # os.path.join(base, "/etc/passwd") silently discards base.
    _, outside = _asset_sandbox(tmp_path, monkeypatch)
    assert content_module.resolve_asset(str(outside / "secrets.csv")) is None


def test_flashcard_regex_no_longer_matches_a_traversal_path():
    # The regex is the outer gate: `assets/.*?` let `.` match `/`, so any
    # .csv on the build machine was addressable. Now bounded to
    # assets/flashcards/ like the audio/video/image matchers.
    body = "# Flashcards\nassets/../../../etc/secrets.csv\n"
    out = process_gemini_notebook_media(body)
    assert "secrets.csv" in out          # left as inert prose
    assert "<div" not in out             # no widget rendered
    assert "deck-wrap" not in out        # ... and no deck embedded


# --- flashcard CSV cells are markup, not decoration ------------------------
#
# _render_flashcards() builds HTML *after* sanitize_note_html() has run on
# the note body, so nothing else ever cleans these cells: whatever the CSV
# says went into the published page verbatim.

def _deck(tmp_path, monkeypatch, *rows):
    deck = tmp_path / "assets" / "flashcards"
    deck.mkdir(parents=True)
    (deck / "deck.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(content_module, "VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(content_module, "ROOT_DIR", str(tmp_path))
    return content_module._render_flashcards("assets/flashcards/deck.csv")


def test_flashcard_cells_keep_their_text(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, "What is a Zettel?,An atomic note")
    assert "What is a Zettel?" in out
    assert "An atomic note" in out


def test_flashcard_cell_cannot_inject_a_tag(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, '"<img src=x onerror=alert(1)>","answer"')
    assert "onerror" not in out
    assert "<img" not in out


def test_flashcard_answer_cell_cannot_inject_a_script(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, '"question","<script>alert(1)</script>"')
    assert "<script" not in out
    assert "alert(1)" not in out  # clean_content_tags drops the payload, not just the tag


def test_flashcard_cell_cannot_break_out_of_the_card_markup(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, '"</p></div><div onclick=steal()>pwned","a"')
    assert "onclick=steal()" not in out
    assert "<div onclick" not in out


def test_flashcard_cell_escaped_payload_is_stripped_not_reflected(tmp_path, monkeypatch):
    """The reason this strips instead of escaping.

    openNote() assigns the stored body to a <textarea>'s innerHTML, which
    decodes character references, and hands the result to marked.parse(),
    which does not sanitize. So a cell containing a *pre-escaped* payload
    would come back as a live tag if we merely re-escaped it -- and a cell
    we escaped ourselves would too.
    """
    out = _deck(tmp_path, monkeypatch, '"&lt;img src=x onerror=alert(1)&gt;","a"')
    assert "onerror" not in out
    assert "&lt;img" not in out


def test_flashcard_missing_file_message_cannot_inject(tmp_path, monkeypatch):
    monkeypatch.setattr(content_module, "VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(content_module, "ROOT_DIR", str(tmp_path))
    out = content_module._render_flashcards("assets/flashcards/<img src=x onerror=alert(1)>.csv")
    assert "onerror" not in out
    assert "<img" not in out


# --- voice sweep (Phase 1b): direct-call assertions on the media renderers -
#
# These are pure functions -- straight f-string builders, no I/O beyond
# _render_flashcards' file read -- so they're asserted directly rather than
# through a rendered card or page. tests/test_garden.py separately guards
# the same renderers' output against the full GARDEN_LEGACY_TOKENS list from
# inside a rendered page; these pin the exact replacement wording.

def test_render_audio_uses_plain_english_label_and_drops_the_live_asset_pulse():
    out = content_module._render_audio("assets/audio/x.mp3")
    assert "Audio overview" in out
    assert "NEURAL_AUDIO_STREAM" not in out
    assert "LIVE_ASSET" not in out


def test_render_video_uses_plain_english_label():
    out = content_module._render_video("assets/video/x.mp4")
    assert "Video overview" in out
    assert "VISUAL_FEED" not in out


def test_render_image_uses_plain_english_label():
    out = content_module._render_image("assets/images/x.png")
    assert "Open full size" in out
    assert "ENLARGE" not in out


def test_render_flashcards_wrapper_uses_plain_english_label(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, "Q,A")
    assert "Flashcards" in out
    assert "MEMORY_BANK_LOADED" not in out


def test_render_flashcards_per_card_labels_are_plain_english(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, "What is a Zettel?,An atomic note")
    assert "Q_NODE" not in out
    assert "A_DATA" not in out
    assert "TAP TO DECRYPT" not in out


# --- markup shape (Phase 3: semantic list, not the old 3D-flip strip) ------

def test_render_flashcards_emits_the_semantic_deck_markup(tmp_path, monkeypatch):
    out = _deck(tmp_path, monkeypatch, "What is a Zettel?,An atomic note")
    assert '<div class="deck-wrap">' in out
    assert '<p class="field-label">Flashcards</p>' in out
    assert '<ol class="deck" data-deck="assets/flashcards/deck.csv">' in out
    assert '<li class="deck-card">' in out
    assert '<p class="deck-q">What is a Zettel?</p>' in out
    assert '<p class="deck-a">An atomic note</p>' in out
    # The old 3D-flip strip is gone entirely, not just relabeled.
    assert "snap-center" not in out
    assert "inner-card" not in out
    assert "rotate-y-180" not in out
    assert "onclick" not in out


def test_render_flashcards_data_deck_equals_the_asset_path(tmp_path, monkeypatch):
    # data-deck is what assets/js/flashcards.js addresses a deck's SM-2 log
    # entries by (window.Review's decks bucket is keyed by this same
    # string) -- it must be the path exactly as written in the note, not a
    # resolved filesystem path.
    out = _deck(tmp_path, monkeypatch, "Q,A")
    assert 'data-deck="assets/flashcards/deck.csv"' in out


def test_render_flashcards_rows_with_fewer_than_two_columns_are_skipped(tmp_path, monkeypatch):
    out = _deck(
        tmp_path, monkeypatch,
        "only-one-column",
        "Real question,Real answer",
        "",
    )
    assert out.count('<li class="deck-card">') == 1
    assert "only-one-column" not in out
    assert "Real question" in out
    assert "Real answer" in out


def test_render_flashcards_missing_file_message_is_plain_english(tmp_path, monkeypatch):
    monkeypatch.setattr(content_module, "VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(content_module, "ROOT_DIR", str(tmp_path))
    out = content_module._render_flashcards("assets/flashcards/missing.csv")
    assert "Flashcard file not found:" in out
    assert "CSV NOT FOUND" not in out


def test_render_flashcards_read_error_message_is_plain_english(tmp_path, monkeypatch):
    # A file that exists (so resolve_asset() succeeds) but isn't valid UTF-8
    # makes the open()/read() inside the try block raise, exercising the
    # "CSV ERROR" branch without needing to fake a permissions failure.
    deck = tmp_path / "assets" / "flashcards"
    deck.mkdir(parents=True)
    (deck / "deck.csv").write_bytes(b"\xff\xfe\x00\x01")
    monkeypatch.setattr(content_module, "VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(content_module, "ROOT_DIR", str(tmp_path))
    out = content_module._render_flashcards("assets/flashcards/deck.csv")
    assert "Flashcard file could not be read:" in out
    assert "CSV ERROR" not in out


# --- wikilink resolver (Phase 1d) -------------------------------------------

def _note(note_id, title, aliases=None):
    return {"note_id": note_id, "title": title, "aliases": aliases or []}


def test_resolver_exact_title_beats_an_alias_claiming_the_same_slug():
    notes = [
        _note("note-real-title", "Real Title"),
        _note("note-other", "Other", aliases=["Real Title"]),
    ]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Real Title") == "note-real-title"
    alias_resolved, _ = content_module.get_wikilink_resolution_counts()
    assert alias_resolved == 0


def test_resolver_resolves_via_alias():
    # The real vault case (CLAUDE.md's vault-edit item 2): note_id has to be
    # make_id() of the FULL title (as a real filename-derived id would be),
    # not a short id that happens to collide with make_id("Dopamine") --
    # otherwise this exercises tier 1 (exact) by accident instead of tier 2.
    # The title also happens to be suffix-shaped ("Base (...)"), so this
    # incidentally proves tier 2 (alias) is checked before tier 3 (suffix).
    notes = [_note("note-dopamine-reward-prediction-error",
                    "Dopamine (Reward Prediction Error)", aliases=["Dopamine"])]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Dopamine") == "note-dopamine-reward-prediction-error"
    alias_resolved, suffix_resolved = content_module.get_wikilink_resolution_counts()
    assert alias_resolved == 1
    assert suffix_resolved == 0


def test_resolver_resolves_via_unique_paren_suffix():
    notes = [_note("note-x", "System 1 vs System 2 (Dual-Process Theory)")]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("System 1 vs System 2") == "note-x"
    _, suffix_resolved = content_module.get_wikilink_resolution_counts()
    assert suffix_resolved == 1


def test_resolver_resolves_via_unique_colon_suffix():
    notes = [_note("note-x", "Evolutionary Psychology: A Primer")]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Evolutionary Psychology") == "note-x"


def test_resolver_ambiguous_suffix_base_resolves_to_neither():
    # Two notes share the base "Cortisol" -- neither should win by guessing.
    notes = [
        _note("note-a", "Cortisol (Hormone)"),
        _note("note-b", "Cortisol (Stress Response)"),
    ]
    resolve = content_module.build_link_resolver(notes)
    # Falls through to plain make_id(), same as no resolver at all --
    # neither known note, so it stays a dangling target.
    assert resolve("Cortisol") == content_module.make_id("Cortisol")
    assert resolve("Cortisol") not in {"note-a", "note-b"}


def test_resolver_does_not_treat_gemini_notebook_marker_as_a_suffix():
    # "(Gemini Notebook)" marks a content type, not a disambiguating suffix --
    # a wikilink to the bare base title must NOT silently resolve to the
    # literature note, even when it's the only note sharing that base.
    notes = [_note("note-neuroanatomy-gemini-notebook", "Neuroanatomy (Gemini Notebook)")]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Neuroanatomy") == content_module.make_id("Neuroanatomy")
    assert resolve("Neuroanatomy") != "note-neuroanatomy-gemini-notebook"


def test_resolver_gemini_notebook_marker_exclusion_is_case_insensitive():
    notes = [_note("note-x", "Neuroanatomy (gemini notebook)")]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Neuroanatomy") != "note-x"


def test_resolver_a_genuine_parenthetical_still_resolves_normally():
    # Sanity check that the exclusion is specific to the Gemini Notebook
    # marker and doesn't break ordinary disambiguating suffixes.
    notes = [_note("note-x", "Cortisol (Hormone)")]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Cortisol") == "note-x"


def test_resolver_coerces_a_bare_string_aliases_value():
    # aliases: "Dopamine" is valid YAML (a bare string), not a list --
    # build_link_resolver() must not assume every caller already coerced it
    # (pipeline.py does, but the resolver shouldn't depend on that).
    notes = [{"note_id": "note-dopamine", "title": "Dopamine (Reward Prediction Error)",
              "aliases": "Dopamine"}]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Dopamine") == "note-dopamine"


def test_resolver_alias_colliding_with_a_real_title_loses():
    # "Ghost" is both a real note's own title AND an alias some other note
    # claims -- the real title wins (tier 1), so the alias is never reached.
    notes = [
        _note("note-ghost", "Ghost"),
        _note("note-other", "Other", aliases=["Ghost"]),
    ]
    resolve = content_module.build_link_resolver(notes)
    assert resolve("Ghost") == "note-ghost"


def test_resolver_alias_collision_between_two_notes_drops_the_key(capsys):
    notes = [
        _note("note-a", "A", aliases=["Shared Alias"]),
        _note("note-b", "B", aliases=["Shared Alias"]),
    ]
    resolve = content_module.build_link_resolver(notes)
    target = resolve("Shared Alias")
    assert target not in ("note-a", "note-b")
    assert "claimed by multiple notes" in capsys.readouterr().out


def test_process_wikilinks_with_no_resolver_is_unchanged():
    text = "See [[Some Note]] and [[Target|Label]]"
    assert process_wikilinks(text) == process_wikilinks(text, resolve=None)
    assert "openNote('note-some-note')" in process_wikilinks(text)


def test_process_wikilinks_uses_the_given_resolver():
    notes = [_note("note-dopamine", "Dopamine (Reward Prediction Error)", aliases=["Dopamine"])]
    resolve = content_module.build_link_resolver(notes)
    html = process_wikilinks("See [[Dopamine]] for detail", resolve=resolve)
    assert "openNote('note-dopamine')" in html


def test_dim_dangling_links_records_unresolved_targets():
    content_module.reset_wikilink_resolution_counts()
    html = process_wikilinks("See [[Ghost Note]] for detail")
    content_module.dim_dangling_links(html, known_ids=set())
    assert "note-ghost-note" in content_module.get_unresolved_wikilink_targets()


def test_dim_dangling_links_does_not_count_an_unfilled_placeholder():
    # An unfilled "[[ ]]" wikilink (TPL_Concept.md's old Related-field
    # default) slugifies to the phantom id "note-", which isn't a genuine
    # dangling link to a concept that doesn't exist yet -- it shouldn't
    # inflate the "still unresolved" count, so the build's own count agrees
    # with tools/vault_health.py's find_pending_atomization(), which already
    # skips this exact case via its own blank-target_text guard.
    content_module.reset_wikilink_resolution_counts()
    html = process_wikilinks("Related: [[ ]]")
    content_module.dim_dangling_links(html, known_ids=set())
    assert content_module.get_unresolved_wikilink_targets() == set()


def test_dim_dangling_links_does_not_record_resolved_targets():
    content_module.reset_wikilink_resolution_counts()
    html = process_wikilinks("See [[Some Note]] for detail")
    content_module.dim_dangling_links(html, known_ids={"note-some-note"})
    assert content_module.get_unresolved_wikilink_targets() == set()


def test_get_resolved_wikilink_targets_counts_distinct_targets_not_occurrences():
    # A popular alias mention repeated several times is one distinct target,
    # not one per occurrence -- this is what lets the build summary report
    # "N link occurrences (M distinct targets)" as two different numbers.
    # note_id deliberately differs from make_id("Dopamine") (same reasoning
    # as test_resolver_resolves_via_alias above) so this exercises the alias
    # tier rather than the exact-match tier.
    notes = [_note("note-dopamine-reward-prediction-error",
                    "Dopamine (Reward Prediction Error)", aliases=["Dopamine"])]
    resolve = content_module.build_link_resolver(notes)
    resolve("Dopamine")
    resolve("Dopamine")
    resolve("Dopamine")
    alias_resolved, _ = content_module.get_wikilink_resolution_counts()
    assert alias_resolved == 3
    # The distinct-target set records the raw target slug as written
    # ("note-dopamine", from make_id("Dopamine")), not the resolved note id.
    assert content_module.get_resolved_wikilink_targets() == {"note-dopamine"}


def test_reset_wikilink_resolution_counts_clears_everything():
    notes = [_note("note-a", "A", aliases=["Alt"])]
    resolve = content_module.build_link_resolver(notes)
    resolve("Alt")
    html = process_wikilinks("See [[Ghost]] for detail")
    content_module.dim_dangling_links(html, known_ids=set())
    content_module.reset_wikilink_resolution_counts()
    assert content_module.get_wikilink_resolution_counts() == (0, 0)
    assert content_module.get_resolved_wikilink_targets() == set()
    assert content_module.get_unresolved_wikilink_targets() == set()
