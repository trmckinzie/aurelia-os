"""Rendering guards for the Garden (garden.html) after the voice sweep.

Built the same way tests/test_about.py stands up the About page: driving the
Jinja template directly via engine.config.env rather than through the build,
so these assert the template's own contract independent of engine/pipeline.py
-- the pattern tests/test_output_escaping.py and tests/test_pipeline.py
already lean on. base_context()/make_config() are imported from
tests/test_about.py rather than reinvented, per that file's own docstring
("every variable base.html needs").
"""
from pathlib import Path

from markupsafe import Markup

from engine import content
from engine.config import env
from engine.textutils import dumps_for_script_tag

from tests.test_about import base_context
from tests.voice_fixtures import GARDEN_LEGACY_TOKENS

GARDEN_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "system" / "templates" / "pages" / "gardentemplate.html"
)

MAIN_CSS_PATH = (
    Path(__file__).resolve().parent.parent
    / "assets" / "css" / "main.css"
)


def make_card(note_id="note-a", title="A", note_type="CONCEPT", tags=None,
              maturity="seed", connections=0, body="<p>Body.</p>", html=None):
    """One fixture card, matching the dict engine/pipeline.py's _scan_vault()
    builds (garden_cards.append(...), ~L188-206): html/body/id/title/type/
    tags/maturity/connections/link, plus desc (the search snippet)."""
    tags = tags if tags is not None else []
    if html is None:
        html = Markup(f'<article data-id="{note_id}">{title}</article>')
    return {
        "html": html,
        "body": Markup(body),
        "id": note_id,
        "title": title,
        "link": f"garden.html#{note_id}",
        "type": note_type,
        "tags": tags,
        "maturity": maturity,
        "desc": title.lower(),
        "connections": connections,
    }


def render_garden(**overrides):
    """Renders gardentemplate.html with a small, complete fixture context.

    cards/backlinks_index/graph_index/search_index_version/page_title are
    what engine/pipeline.py's _render_pages() hands the template beyond the
    shared base_context() chrome (see its `pages` list, ~L474-477).
    backlinks_index/graph_index go through dumps_for_script_tag the same way
    the real build's backlinks_json/graph_json do -- the template embeds them
    raw into a <script> block (`const GRAPH_INDEX = {{ graph_index }};`), not
    through a JSON-parsing filter.
    """
    context = base_context(
        active_page="garden",
        cards=[
            make_card("note-a", "A", "CONCEPT", maturity="seed"),
            make_card("note-b", "B", "SOURCE", maturity="growing"),
            make_card("note-c", "C", "AUTHOR", maturity="evergreen"),
        ],
        backlinks_index=dumps_for_script_tag({}),
        graph_index=dumps_for_script_tag({"nodes": [], "edges": []}),
        search_index_version="test",
        page_title="The Garden",
    )
    context.update(overrides)
    return env.get_template("pages/gardentemplate.html").render(**context)


def test_garden_renders_no_legacy_tokens():
    # This ban runs on fixture-rendered HTML only, never on a real build:
    # real note bodies legitimately contain words like "cortex" (the site's
    # own "external cortex" framing -- see CLAUDE.md), so pinning this
    # against tools/build.py's actual output would be a false positive
    # waiting to happen. Fixture card bodies/html here are the engine's own
    # chrome and markup, not vault content.
    html = render_garden()
    for token in GARDEN_LEGACY_TOKENS:
        assert token not in html, f"{token!r} should not appear on the Garden"


def test_garden_media_widget_output_has_no_legacy_tokens(tmp_path, monkeypatch):
    # Phase 1b regression guard. The top-level test above can't catch a
    # regression in the Gemini Notebook media renderers themselves, since its
    # fixture card bodies never call them -- this one does, the same way a
    # real note's rendered body would after process_gemini_notebook_media().
    deck_dir = tmp_path / "assets" / "flashcards"
    deck_dir.mkdir(parents=True)
    (deck_dir / "deck.csv").write_text(
        "What is spaced practice?,Distributed review over time\n", encoding="utf-8")
    monkeypatch.setattr(content, "VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(content, "ROOT_DIR", str(tmp_path))

    widget_html = (
        content._render_audio("assets/audio/x.mp3")
        + content._render_video("assets/video/x.mp4")
        + content._render_image("assets/images/x.png")
        + content._render_flashcards("assets/flashcards/deck.csv")
    )
    html = render_garden(cards=[make_card(body=widget_html)])
    for token in GARDEN_LEGACY_TOKENS:
        assert token not in html, f"{token!r} should not appear in a rendered media widget"


def test_garden_has_a11y_status_live_region():
    # Phase 1e: a visually-hidden aria-live region beside #node-count, for
    # switchView()/openNote() announcements that don't otherwise reach a
    # screen reader (the existing live region on #node-count only ever
    # re-reads the result count).
    html = render_garden()
    assert '<div id="a11y-status"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-atomic="true"' in html
    assert 'sr-only' in html.split('id="a11y-status"', 1)[1].split('>', 1)[0]


# --- Phase 2: recall-first reader, elaboration, spaced review --------------

def test_garden_loads_review_js_with_cache_busting_version():
    # Same asset_version-based cache-busting utils.js already uses (see
    # base.html) -- NOT search-index.js's own content hash, since review.js
    # is small and static per build (see engine/pipeline.py._asset_version,
    # which now hashes it alongside main.css/utils.js).
    html = render_garden()
    assert 'src="assets/js/review.js?v=test"' in html


# --- Phase 3: flashcards ------------------------------------------------

def test_garden_loads_flashcards_js_with_cache_busting_version():
    # Same wiring as review.js above -- engine/pipeline.py._asset_version
    # now hashes assets/js/flashcards.js too, so a deploy can't leave a
    # visitor on a stale copy that predates a new window.Review deck API
    # it calls.
    html = render_garden()
    assert 'src="assets/js/flashcards.js?v=test"' in html
    # Loaded after review.js, since it calls into window.Review at
    # interaction time (not at parse time, so load order only matters in
    # spirit -- but this pins it anyway as the documented contract).
    assert html.index('review.js?v=test') < html.index('flashcards.js?v=test')


def test_garden_has_modal_reviewed_and_modal_elaborate_elements():
    html = render_garden()
    assert '<span id="modal-reviewed"' in html
    assert '<div id="modal-elaborate"' in html
    # #modal-elaborate sits after #modal-related in the modal DOM (the
    # nudge is appended after backlinks/related, not before).
    assert html.index('id="modal-related"') < html.index('id="modal-elaborate"')


def test_garden_has_due_status_and_start_review_button():
    html = render_garden()
    assert "Due today:" in html
    assert '<span id="due-count"' in html
    assert '<button type="button" id="btn-start-review"' in html
    # Disabled by default server-side; refreshDueState() (client-side)
    # enables it once the log says there's actually something due -- no
    # per-note review payload is rendered here to answer that up front.
    assert 'onclick="startReviewSession()"' in html
    assert "disabled" in html.split('id="btn-start-review"', 1)[1].split('>', 1)[0]


def test_garden_has_due_sort_option():
    html = render_garden()
    assert '<option value="due">Due first</option>' in html


def test_garden_has_study_mode_toggle_in_toolbar_and_modal_footer():
    # Two instances (toolbar + modal footer), both carrying the shared
    # .study-toggle-btn class and toggleStudyMode() handler so they stay in
    # sync (see gardentemplate.html's setStudyModeButtons()).
    html = render_garden()
    assert html.count('onclick="toggleStudyMode()"') == 2
    assert 'id="btn-study-mode"' in html
    assert 'id="btn-study-mode-modal"' in html
    assert html.count("study-toggle-btn") >= 2


def test_garden_has_progress_panel_with_export_and_import():
    html = render_garden()
    assert '<details id="progress-panel"' in html
    assert 'onclick="exportReviewProgress()"' in html
    assert 'onchange="importReviewProgress(this.files[0])' in html
    assert '<p id="progress-panel-result"' in html


def test_garden_scripts_reference_the_review_engine_public_api():
    # Wiring guard: the inline script actually calls into window.Review's
    # documented public functions rather than, say, a typo'd method name
    # that would only surface as a runtime TypeError in a real browser.
    # Review.restore is the punch-list #1/#2 addition ("Change rating"
    # must run rate() from a clean pre-rating state -- see changeRating()
    # in gardentemplate.html and restore() in assets/js/review.js).
    html = render_garden()
    for member in ("Review.load(", "Review.save(", "Review.rate(",
                   "Review.restore(", "Review.stateFor(", "Review.dueIds(",
                   "Review.export(", "Review.import("):
        assert member in html, f"{member} not called from gardentemplate.html"


# --- Punch-list fixes (Phase 2 checkpoint) ----------------------------------

def test_garden_template_source_has_no_disallowed_control_bytes():
    # Regression guard for a stray NUL byte found in this file (present in
    # HEAD, not just the working tree -- see git log for the fix commit) at
    # ~byte offset 96159, inside a JS cache-key string
    # (`mode + '\x00' + ...` in applySort()). Checked directly against the
    # template source file, in binary, rather than through Jinja: a control
    # byte the renderer happens to pass straight through would not
    # necessarily show up any other way.
    data = GARDEN_TEMPLATE_PATH.read_bytes()
    allowed = {0x09, 0x0A, 0x0D}  # tab, LF, CR
    bad = sorted({b for b in set(data) if b < 0x20 and b not in allowed})
    assert not bad, f"disallowed control bytes in gardentemplate.html: {[hex(b) for b in bad]}"


def test_garden_rendered_html_has_no_disallowed_control_chars():
    # Same guard as above, against the actual rendered output -- catches a
    # control character introduced anywhere in the render path, not just
    # ones already sitting in the template source.
    html = render_garden()
    allowed = {"\t", "\n", "\r"}
    bad = sorted({c for c in html if ord(c) < 0x20 and c not in allowed})
    assert not bad, f"disallowed control characters in rendered garden HTML: {[hex(ord(c)) for c in bad]}"


def test_garden_has_session_progress_element_hidden_by_default():
    # Fix #4: "Reviewing N of M", next to #modal-connections in the header
    # strip. Visibility and its count are entirely client-JS-driven
    # (updateSessionProgress() in gardentemplate.html, called from
    # applyNoteChrome() on every openNote()), so a static Jinja render can
    # only assert the element exists and starts hidden -- the same
    # hidden-by-default/toggled-by-class pattern #topic-active-label
    # already uses for its own conditional (not responsive-breakpoint)
    # visibility.
    html = render_garden()
    assert '<span id="modal-session" class="hidden field-label text-aurelia-muted"></span>' in html
    assert html.index('id="modal-connections"') < html.index('id="modal-session"')


def test_garden_scripts_build_session_completion_and_change_rating_markup():
    # Fix #1 ("Change rating") and fix #4 (session completion) both build
    # their copy via inline JS template literals -- showRateConfirmation()
    # and showSessionComplete() in gardentemplate.html -- rather than
    # server-rendered Jinja markup, so (like the Review-API wiring guard
    # above, and test_garden_has_modal_reviewed_and_modal_elaborate_elements)
    # this pins their literal source text rather than executing the JS.
    html = render_garden()
    assert "Session complete:" in html
    assert 'onclick="closeModal()">Back to the Garden' in html
    assert "Change rating" in html


def test_garden_start_review_tooltip_has_no_double_hyphen():
    # Fix #5: the Start-review tooltip used to read "...yet -- rate a
    # note...". Pinned as the specific fixed copy, and specifically within
    # the button's own title attribute (the actual rendered sink a
    # tooltip/screen reader shows) -- NOT as a blanket "' -- ' not
    # anywhere in the page" check: this codebase's own JS/HTML/Jinja
    # comments use " -- " pervasively as a house-style em dash (135
    # occurrences in this fixture's own rendered output, none of them
    # user-facing), and the punch list itself carves comments out of this
    # fix's scope.
    html = render_garden()
    assert "No notes are due for review yet. Rate a note in Study mode to add it to the queue." in html
    assert "No notes are due for review yet -- rate a note" not in html
    btn_start = html.index('id="btn-start-review"')
    btn_chunk = html[btn_start:html.index(">", btn_start)]
    assert " -- " not in btn_chunk


def test_garden_tree_view_has_no_terminal_glyph_prefix():
    # Fix #6: the leftover "::" decoration on every tree-view row, banned by
    # CLAUDE.md's voice rule ("No // separators, no SNAKE_CASE labels...").
    html = render_garden()
    assert 'font-mono">::</span>' not in html


# --- Phase 4: long-note navigation and remaining HCI -----------------------

def test_garden_has_modal_outline_containers():
    # buildOutline() (scripts block) populates both render targets with the
    # same generated list -- a sticky sidebar (xl and up) and a collapsed
    # <details> (below xl) -- see assets/css/main.css for which one a given
    # width actually shows. Both start empty/hidden; only a note with >= 4
    # headings gets either populated.
    html = render_garden()
    assert '<nav id="modal-outline" aria-label="On this page" class="modal-outline custom-scrollbar hidden">' in html
    assert '<details id="modal-outline-mobile" class="modal-outline-mobile hidden">' in html


def test_garden_has_shortcut_sheet_dialog_and_toolbar_button():
    html = render_garden()
    assert '<dialog id="shortcut-sheet"' in html
    assert 'onclick="openShortcutSheet()"' in html
    assert 'id="btn-shortcuts"' in html
    # aria-label, not just a title attribute -- the icon-only toolbar form
    # (everything below 2xl) has no other accessible name, same reasoning
    # every other toolbar-icon-btn in this row already follows.
    assert 'aria-label="Keyboard shortcuts"' in html


def test_garden_shortcut_sheet_lists_key_shortcuts():
    # Pinned within the sheet's own markup specifically (not just "appears
    # somewhere in the page"), since '[', ']' and '1' are common characters
    # that could otherwise match by coincidence elsewhere in the fixture.
    html = render_garden()
    start = html.index('<dialog id="shortcut-sheet"')
    end = html.index('</dialog>', start)
    sheet = html[start:end]
    for key in ("[", "]", "?", "1"):
        assert f'<span class="kbd">{key}</span>' in sheet, f"{key!r} not listed in the shortcut sheet"


def test_garden_has_graph_list_container():
    # Small-screen fallback for the knowledge graph (below 768px) -- see
    # isGraphListMode()/renderGraphList() in the scripts block.
    html = render_garden()
    assert '<div id="graph-list" class="hidden' in html
    assert '<ol id="graph-list-items"' in html
    assert '<p id="graph-list-empty"' in html


# --- Final polish pass -------------------------------------------------

def test_modal_outline_css_sets_overflow_y_for_reachability():
    # #modal-outline is position: sticky inside #modal-panel, which is
    # h-[90vh] (gardentemplate.html) rather than the full viewport. A
    # max-height budget sized off 100vh let a long (e.g. 19-entry) outline
    # run past the bottom of #modal-scroll's own visible area with no way
    # to reach the overflow -- position: sticky doesn't get clipped with a
    # scrollbar of its own, and the page behind the reader doesn't scroll.
    # Read straight from the stylesheet source (Jinja never touches this
    # file) rather than the template's own <style> block, which only
    # defines .custom-scrollbar.
    css = MAIN_CSS_PATH.read_text(encoding="utf-8")
    start = css.index(".modal-outline:not(.hidden) {")
    end = css.index("}", start)
    rule = css[start:end]
    assert "overflow-y: auto" in rule
    # Sized against the modal panel's own 90vh, not the full-viewport
    # budget that caused the overrun (the max-height declaration itself,
    # not just the explanatory comment above it, which also mentions
    # 100vh in passing).
    assert "max-height: calc(90vh" in rule


def test_related_by_topic_excludes_daily_logs_from_ranked_candidates():
    # renderRelatedByTopic() used to rank every node by shared topic/* tags
    # alone, so a course note's "Related by Topic" strip surfaced five
    # 2026-02-12-style daily logs -- they accumulate topic tags just by
    # being course material, the same bias renderElaboration() was already
    # written to avoid. It now reuses that function's candidate policy
    # (NUDGE_EXCLUDED_TYPES -- daily-bridge/log/gemini-notebook -- with a
    # fallback to the excluded types only when fewer than two ranked
    # candidates remain) rather than a second, drifting copy of it.
    # String-asserted against the rendered inline script, the same way the
    # other Review-API/session-copy tests above pin JS source rather than
    # executing it.
    html = render_garden()
    start = html.index("function renderRelatedByTopic")
    end = html.index("function closeModal", start)
    fn = html[start:end]
    assert "NUDGE_EXCLUDED_TYPES" in fn
    assert "daily-bridge" in html  # confirms the set itself lists it


def test_garden_card_topic_chip_listener_uses_the_capture_phase():
    """The chip's grid listener must capture, not bubble.

    A Gemini card is an <article onclick="openNote(...)"> and the chip sits
    inside it, so the card's inline handler runs during bubbling -- i.e.
    before a bubble-phase listener on #cardGrid. Verified in a browser: with
    bubbling the chip both filtered the Garden and opened the note on top of
    the filter. Capturing at the grid runs first, so its stopPropagation()
    actually suppresses the card. Pinned because the trailing `true` is a
    single easily-dropped token whose loss reintroduces exactly that bug.
    """
    html = render_garden()
    start = html.index("document.getElementById('cardGrid').addEventListener('click'")
    end = html.index("function toggleTopicFilter", start)
    listener = html[start:end]
    assert "button.card-topic[data-tag]" in listener
    assert "e.stopPropagation()" in listener
    assert "}, true);" in listener


def test_garden_roving_keydown_defers_to_card_topic_chips():
    # Without this guard Enter/Space on a focused chip would reach the card's
    # roving handler and open the note instead of applying the filter, since
    # closest('.searchable-item') matches from inside the card.
    html = render_garden()
    start = html.index("function rovingKeydown")
    end = html.index("case 'ArrowRight'", start)
    assert "button.card-topic" in html[start:end]
