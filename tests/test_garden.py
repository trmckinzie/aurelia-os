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

# The Garden's script (roadmap S13): ES modules served from assets/js/garden/,
# no longer an inline script in the template. The tests below that pin JS
# source text read it from here.
GARDEN_MODULES_DIR = Path(__file__).resolve().parent.parent / "assets" / "js" / "garden"


def garden_module(name):
    """The source of one module in assets/js/garden/."""
    return (GARDEN_MODULES_DIR / name).read_text(encoding="utf-8")


def garden_script():
    """Every module in assets/js/garden/, concatenated in name order."""
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(GARDEN_MODULES_DIR.glob("*.js")))


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

    cards/backlinks_index/graph_index/page_title are
    what engine/pipeline.py's _render_pages() hands the template beyond the
    shared base_context() chrome (see its `pages` list, ~L474-477).
    backlinks_index/graph_index go through dumps_for_script_tag the same way
    the real build's backlinks_json/graph_json do -- the template embeds them
    raw into two JSON data blocks (#garden-backlinks, #garden-graph), not
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
    # The script builds some of the page's copy (labels, announcements). It
    # was part of the rendered page until roadmap S13 moved it into modules.
    script = garden_script()
    for token in GARDEN_LEGACY_TOKENS:
        assert token not in script, f"{token!r} should not appear in the Garden's script"


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
    # Rendered as a token; engine/cachebust.stamp_asset_versions() swaps in
    # the hash of the served file after the build.
    html = render_garden()
    assert 'src="assets/js/review.js?v=@@asset:assets/js/review.js@@"' in html


# --- Phase 3: flashcards ------------------------------------------------

def test_garden_loads_flashcards_js_with_cache_busting_version():
    # Same wiring as review.js above, so a deploy can't leave a visitor on a
    # stale copy that predates a new window.Review deck API it calls.
    html = render_garden()
    assert 'src="assets/js/flashcards.js?v=@@asset:assets/js/flashcards.js@@"' in html
    # Loaded after review.js, since it calls into window.Review at
    # interaction time (not at parse time, so load order only matters in
    # spirit -- but this pins it anyway as the documented contract).
    assert html.index('assets/js/review.js?v=') < html.index('assets/js/flashcards.js?v=')


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
    assert 'data-action="startReviewSession"' in html
    assert "disabled" in html.split('id="btn-start-review"', 1)[1].split('>', 1)[0]


def test_garden_has_due_sort_option():
    html = render_garden()
    assert '<option value="due">Due first</option>' in html


def test_garden_has_study_mode_toggle_in_toolbar_and_modal_footer():
    # Two instances (toolbar + modal footer), both carrying the shared
    # .study-toggle-btn class and toggleStudyMode() handler so they stay in
    # sync (see setStudyModeButtons() in assets/js/garden/study.js).
    html = render_garden()
    assert html.count('data-action="toggleStudyMode"') == 2
    assert 'id="btn-study-mode"' in html
    assert 'id="btn-study-mode-modal"' in html
    assert html.count("study-toggle-btn") >= 2


def test_garden_has_progress_panel_with_export_and_import():
    html = render_garden()
    assert '<details id="progress-panel"' in html
    assert 'data-action="exportReviewProgress"' in html
    assert 'data-change="importReviewProgress"' in html
    assert '<p id="progress-panel-result"' in html


def test_garden_scripts_reference_the_review_engine_public_api():
    # Wiring guard: the Garden's script actually calls into window.Review's
    # documented public functions rather than, say, a typo'd method name
    # that would only surface as a runtime TypeError in a real browser.
    # Review.restore is the punch-list #1/#2 addition ("Change rating"
    # must run rate() from a clean pre-rating state -- see changeRating()
    # in assets/js/garden/study.js and restore() in assets/js/review.js).
    script = garden_script()
    for member in ("Review.load(", "Review.save(", "Review.rate(",
                   "Review.restore(", "Review.stateFor(", "Review.dueIds(",
                   "Review.export(", "Review.import("):
        assert member in script, f"{member} not called from assets/js/garden/"


# --- Punch-list fixes (Phase 2 checkpoint) ----------------------------------

def test_garden_template_source_has_no_disallowed_control_bytes():
    # Regression guard for a stray NUL byte found in this file (present in
    # HEAD, not just the working tree -- see git log for the fix commit) at
    # ~byte offset 96159, inside a JS cache-key string
    # (`mode + '\x00' + ...` in applySort()). Checked directly against the
    # template source file, in binary, rather than through Jinja: a control
    # byte the renderer happens to pass straight through would not
    # necessarily show up any other way.
    # The script that byte sat in is now assets/js/garden/ (roadmap S13), so
    # the modules are held to the same rule.
    allowed = {0x09, 0x0A, 0x0D}  # tab, LF, CR
    for path in [GARDEN_TEMPLATE_PATH, *sorted(GARDEN_MODULES_DIR.glob("*.js"))]:
        data = path.read_bytes()
        bad = sorted({b for b in set(data) if b < 0x20 and b not in allowed})
        assert not bad, f"disallowed control bytes in {path.name}: {[hex(b) for b in bad]}"


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
    # (updateSessionProgress() in assets/js/garden/review-session.js, called from
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
    # their copy via JS template literals -- showRateConfirmation() in
    # study.js and showSessionComplete() in review-session.js -- rather than
    # server-rendered Jinja markup, so (like the Review-API wiring guard
    # above, and test_garden_has_modal_reviewed_and_modal_elaborate_elements)
    # this pins their literal source text rather than executing the JS.
    assert "Change rating" in garden_module("study.js")
    session = garden_module("review-session.js")
    assert "Session complete:" in session
    assert 'data-action="closeModal">Back to the Garden' in session


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
    assert 'data-action="openShortcutSheet"' in html
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
    # relatedByTopic() used to rank every node by shared topic/* tags
    # alone, so a course note's "Related by Topic" strip surfaced five
    # 2026-02-12-style daily logs -- they accumulate topic tags just by
    # being course material, the same bias renderElaboration() was already
    # written to avoid. It now reuses that function's candidate policy
    # (NUDGE_EXCLUDED_TYPES -- daily-bridge/log/gemini-notebook -- with a
    # fallback to the excluded types only when fewer than two ranked
    # candidates remain) rather than a second, drifting copy of it.
    # String-asserted against the module's source, the same way the
    # other Review-API/session-copy tests above pin JS source rather than
    # executing it.
    script = garden_module("connections.js")
    start = script.index("function relatedByTopic")
    end = script.index("function renderRelatedByTopic", start)
    fn = script[start:end]
    assert "NUDGE_EXCLUDED_TYPES" in fn
    assert "daily-bridge" in script  # confirms the set itself lists it


def test_garden_grid_click_handler_decides_chip_then_link_then_card():
    """One delegated click handler per container, in a fixed priority.

    A Gemini card's topic chip must filter without also opening the note it
    sits in, a pill must open its own target and not the card around it,
    and anything else on the card opens the card. Pinned as source order:
    the chip check comes first and returns, the data-note/data-action guard
    second, and the card open last. Inline handlers used to force a
    capture-phase trick here; with no inline handler on the card there is
    one listener and the order is explicit (B02).
    """
    script = garden_module("grid.js")
    start = script.index("function handleGridClick(e)")
    handler = script[start:]
    chip = handler.index("button.card-topic[data-tag]")
    guard = handler.index("closest('[data-note], [data-action]')")
    open_card = handler.index("openNote(item.dataset.id)")
    assert chip < guard < open_card
    assert "toggleTopicFilter(chip.dataset.tag)" in handler
    assert "el.addEventListener('click', handleGridClick);" in handler
    assert "}, true);" not in handler
    # The pill's half: one document listener opens whatever [data-note] names.
    reader = garden_module("reader.js")
    assert "document.addEventListener('click', openClickedNoteLink);" in reader
    link = reader[reader.index("function openClickedNoteLink(e)"):]
    assert "openNote(link.dataset.note)" in link[:link.index("\n}\n")]


def test_garden_roving_keydown_defers_to_card_topic_chips():
    # Without this guard Enter/Space on a focused chip would reach the card's
    # roving handler and open the note instead of applying the filter, since
    # closest('.searchable-item') matches from inside the card.
    script = garden_module("roving.js")
    start = script.index("function rovingKeydown")
    end = script.index("rovingIndexForKey(e.key", start)
    assert "button.card-topic" in script[start:end]


# --- roving focus lives on the card's title control (B19) ------------------

def test_garden_roving_focus_targets_the_card_title_control():
    script = garden_module("roving.js")
    start = script.index("function rovingControl(item)")
    end = script.index("/* The filter toolbar is sticky", start)
    block = script[start:end]
    assert "item.querySelector('.card-open') || item" in block
    assert "rovingControl(el).tabIndex = -1" in block
    assert "rovingControl(items[state.rovingIndex]).tabIndex = 0" in block
    assert "rovingControl(items[state.rovingIndex]).focus(" in block
    # Enter/Space on the title button activate it natively; the handler must
    # not open the note a second time.
    assert "if (e.target.closest('.card-open')) return;" in block
    # A pointer click on the card body focuses the title first, in the
    # capture phase, so the reader returns focus to the card on close.
    click = block[block.index("el.addEventListener('click'"):block.index("el.addEventListener('focusin'")]
    assert "control.focus({ preventScroll: true })" in click
    assert "}, true);" in click


# --- the script is served modules, not an inline block (roadmap S13) ---------

def test_garden_carries_no_inline_script_of_its_own():
    """garden.html executes no inline script beyond the two base.html gives
    every page. Its own code is one module script with a versioned URL."""
    from engine.csp import inline_script_hashes
    from tests.test_about import render_about

    html = render_garden()
    assert inline_script_hashes(html) == inline_script_hashes(render_about())
    assert '<script type="module" src="assets/js/garden/main.js?v=@@asset:assets/js/garden/main.js@@"></script>' in html


def test_garden_build_data_is_two_json_data_blocks():
    """The build's data reaches the script as JSON data blocks, which the
    browser never executes, read by assets/js/garden/data.js. A title holding
    "</script>" must not close the block early and must survive the parse."""
    import json
    import re

    backlinks = {"note-a": [{"id": "note-b", "title": "B </script><b>"}]}
    graph = {"nodes": [{"id": "note-a", "title": "A", "type": "concept", "tags": ["topic/x"]}], "edges": []}
    html = render_garden(backlinks_index=dumps_for_script_tag(backlinks), graph_index=dumps_for_script_tag(graph))
    blocks = dict(re.findall(r'<script type="application/json" id="(garden-[a-z]+)">(.*?)</script>', html, re.S))
    assert json.loads(blocks["garden-backlinks"]) == backlinks
    assert json.loads(blocks["garden-graph"]) == graph
    data = garden_module("data.js")
    assert "readJsonBlock('garden-backlinks')" in data and "readJsonBlock('garden-graph')" in data


def test_garden_modules_import_only_each_other():
    """Every import in assets/js/garden/ is a relative import of a file in
    that folder, one statement per source file, which is the shape
    engine/cachebust.stamp_module_imports() versions. Anything else (a bare
    package name, a URL, a path out of the folder) would be served
    unversioned or not at all."""
    import re

    names = {p.name for p in GARDEN_MODULES_DIR.glob("*.js")}
    for path in sorted(GARDEN_MODULES_DIR.glob("*.js")):
        source = path.read_text(encoding="utf-8")
        specifiers = re.findall(r"""^\s*(?:import\b[^'"]*|\}\s*from\s*)['"]([^'"]+)['"]""", source, re.M)
        for spec in specifiers:
            assert spec.startswith("./") and spec[2:] in names, f"{path.name} imports {spec!r}"
        # `Review.import(` is a method call; a dynamic import has nothing before it.
        assert not re.search(r"(?<![.\w])import\(", source), f"{path.name} uses a dynamic import, which is not versioned"


def test_garden_modules_run_nothing_at_import_time():
    """Outside main.js, a module's top level is imports, declarations and
    comments. Listeners and first paints start from main.js, in order, which
    is also what lets tests/js/ import a module without a document."""
    import re

    allowed = re.compile(r"^(import |export |function |const |let |\} from |//|/\*|\*/|\}|\)|\]|$)")
    for path in sorted(GARDEN_MODULES_DIR.glob("*.js")):
        if path.name == "main.js":
            continue
        in_comment = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if in_comment:
                in_comment = "*/" not in line
                continue
            if line.startswith("/*") and "*/" not in line:
                in_comment = True
                continue
            if line[:1] in (" ", "\t"):
                continue
            assert allowed.match(line), f"{path.name}:{number} runs at import time: {line!r}"


def test_what_a_classic_script_expects_on_window_is_not_a_module_export():
    """A classic script cannot import, so whatever one of them reads off
    `window` has to be defined by a classic script. flashcards.js guards
    announce() and isTypingTarget() with `typeof`, so when the Garden's
    script became modules and those two stopped being globals, nothing
    failed: deck announcements just stopped. Both live in utils.js now."""
    import re

    scripts_dir = GARDEN_MODULES_DIR.parent
    classic = {p.name: p.read_text(encoding="utf-8") for p in sorted(scripts_dir.glob("*.js"))}
    everything = "\n".join(classic.values())
    guarded = set()
    for source in classic.values():
        guarded.update(re.findall(r"typeof window\.(\w+)\s*[!=]==\s*'function'", source))
    assert {"announce", "isTypingTarget"} <= guarded, "flashcards.js no longer guards these; update this test"
    for name in sorted(guarded):
        defined = (re.search(rf"^function {name}\(", everything, re.M)
                   or re.search(rf"window\.{name}\s*=[^=]", everything))
        assert defined, f"a classic script expects window.{name}, which no classic script defines"
    for name in ("announce", "isTypingTarget"):
        assert not re.search(rf"export (function|const|let) {name}\b", garden_script()), (
            f"{name} is defined in a module again; flashcards.js cannot reach it there")
