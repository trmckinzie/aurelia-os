"""Rendering guards for the Lobby (index.html) after the voice rebrand.

The Lobby used to be written in an "Aurelia OS terminal" register -- a
manifesto modal, an OPERATOR_PROFILE bio modal, MOD_01/SYSTEM_READY labels.
The design system survived that pass; the copy did not. These tests pin the
result, because the failure mode is silent: a stray in-joke reads as a bug
only to a human looking at the page.

The render helpers and fixtures live in tests/test_about.py, which stood them
up first for the About page and the shared chrome. Importing rather than
duplicating them keeps one definition of "every variable base.html needs".
"""
import re

from tests.test_about import (
    make_config,
    make_profile,
    render_404,
    render_index,
)
from tests.test_garden import make_card
from tests.voice_fixtures import LEGACY_TOKENS

from engine.pipeline import _build_search_index
from engine.textutils import dumps_for_script_tag


def test_lobby_renders_profile_card_from_profile():
    # The card is fed by profile.json (passed to the Lobby's context in
    # engine/pipeline.py._render_pages), not by user_config.json -- so a
    # regression that drops `profile` from that context fails here rather
    # than silently rendering a card with empty text.
    html = render_index()
    assert "01 / Profile" in html
    assert "Ada Lovelace" in html
    assert "Analyst &amp; Metaphysician" in html
    # A primary role, and only the primary ones.
    assert "Collaborator" in html
    assert "Analytical Society" in html
    assert "Correspondent" not in html


def test_lobby_profile_card_links_to_the_about_page():
    html = render_index()
    assert re.search(r'<a href="about\.html"[^>]*class="group surface', html)


def test_lobby_omits_the_profile_card_when_no_profile_is_supplied():
    # The Garden and status cards are the Lobby's own; only the profile card
    # depends on a context key the page did not always receive.
    html = render_index(profile=None)
    assert "01 / Profile" not in html
    assert "02 / Notes" in html
    assert "03 / At a glance" in html


def test_lobby_has_no_legacy_terminal_copy():
    lobby = render_index()
    not_found = render_404()
    for token in LEGACY_TOKENS:
        assert token not in lobby, f"{token} still on the Lobby"
        assert token not in not_found, f"{token} still on the 404 page"


def test_lobby_has_no_modal_leftovers():
    # The manifesto and operator-bio modals were deleted outright; about.html
    # replaces both. A leftover onclick with no function behind it throws in
    # the console and does nothing visible, which is easy to miss.
    html = render_index()
    for token in ("openManifesto", "closeManifesto", "manifesto-backdrop",
                  "openAbout", "closeAbout", "about-backdrop"):
        assert token not in html, f"{token} survived the modal removal"


def test_lobby_hero_shows_the_site_name_without_the_scramble():
    html = render_index()
    assert "Ada Lovelace" in html
    # The letter-scramble hover went with the terminal voice; the static
    # gradient treatment stayed, under a new class.
    assert "decrypt-effect" not in html
    assert "data-value=" not in html
    assert "hero-name" in html


def test_lobby_ctas_point_at_about_and_garden():
    html = render_index()
    # w-full sm:w-auto justify-center (H2) make the three CTAs stack full-width
    # on phones instead of wrapping into a ragged, mixed-width row.
    assert 'href="about.html" class="btn btn-primary group w-full sm:w-auto justify-center"' in html
    assert 'href="garden.html" class="btn btn-ghost group w-full sm:w-auto justify-center"' in html
    assert "Browse the notes" in html
    assert "toggleCmd()" in html


def test_lobby_carousel_buttons_have_accessible_names():
    # The visible "Previous"/"Next" labels are hidden below md and only fade
    # in on hover, so the aria-label is the only name a screen reader or a
    # touch user ever gets.
    html = render_index()
    assert 'aria-label="Previous item"' in html
    assert 'aria-label="Next item"' in html


def test_lobby_readout_is_seeded_server_side_from_the_first_tech_item():
    # Without JS the readout panel used to sit on a "SYSTEM_READY" stub; it
    # now renders the first toolkit entry, which is also what updateReadout()
    # produces on init.
    config = make_config()
    config["tech_stack"] = [
        {"name": "Obsidian", "type": "SOFTWARE / KNOWLEDGE",
         "desc": "Local-first Markdown vault.", "icon": "X"},
    ]
    html = render_index(config=config)
    assert "Obsidian" in html
    assert "Local-first Markdown vault." in html
    # No trailing "//" on the swapped-in title either.
    assert 'activeTech.name + " //"' not in html


def test_lobby_renders_headshot_when_present():
    profile = make_profile()
    profile["identity"] = dict(profile["identity"])
    profile["identity"]["photo"] = {"src": "assets/images/headshot.webp", "alt": "Ada Lovelace, portrait"}
    html = render_index(profile=profile)
    header = html[html.index("<header"):html.index("</header>")]
    assert '<img src="assets/images/headshot.webp" alt="Ada Lovelace, portrait"' in header
    assert 'width="650" height="650"' in header


def test_lobby_without_photo_has_no_hero_img():
    html = render_index()
    header = html[html.index("<header"):html.index("</header>")]
    assert "<img" not in header


def test_lobby_profile_card_shows_location_and_skill_group_chips():
    # H1: fills the dead space between the headline and the roles line with
    # real profile data instead of leaving it blank at desktop widths.
    html = render_index()
    card = html[html.index("01 / Profile"):html.index("</a>", html.index("01 / Profile"))]
    assert "London, UK" in card
    assert "Mathematics" in card
    assert "Writing" in card


def test_lobby_garden_card_renders_type_counts_as_links_with_counts():
    stats = {
        "total_notes": 12,
        "latest_log_date": None,
        "maturity_counts": {"seed": 0, "growing": 0, "evergreen": 0},
        "hub_notes": [],
        "type_counts": [
            {"slug": "concept", "label": "Concepts", "count": 7},
            {"slug": "source", "label": "Sources", "count": 5},
        ],
    }
    html = render_index(stats=stats)
    assert 'href="garden.html?type=concept"' in html
    assert 'href="garden.html?type=source"' in html
    assert "Concepts" in html
    assert "Sources" in html
    # The old static, unlinked list is a fallback for when there are no
    # counts to show -- it should be gone once real ones are available.
    assert "Concepts &middot; Sources &middot; Authors" not in html
    # No nested <a> -- the card itself is a <div>; its heading carries the
    # one real link.
    assert re.search(r'<h2 class="display-lg">\s*<a href="garden\.html"', html)


def test_lobby_garden_card_falls_back_to_the_static_list_without_type_counts():
    html = render_index()  # default stats fixture carries no type_counts key
    assert "Concepts &middot; Sources &middot; Authors &middot; Disciplines &middot; Deep dives" in html
    assert 'href="garden.html?type=' not in html


def test_lobby_latest_note_date_is_human_readable_and_in_a_time_element():
    html = render_index(stats={
        "total_notes": 1, "latest_log_date": "2026-09-07",
        "maturity_counts": {"seed": 1, "growing": 0, "evergreen": 0}, "hub_notes": [],
    })
    assert '<time datetime="2026-09-07">September 7, 2026</time>' in html


def test_lobby_maturity_legend_wraps_instead_of_breaking_mid_item():
    # H3: "🌱 162 SEED" was breaking after the number on a 375px screen --
    # each item gets its own whitespace-nowrap and the row wraps between
    # items instead of splitting one.
    html = render_index()
    assert 'class="whitespace-nowrap">🌱' in html
    assert 'class="whitespace-nowrap">🌿' in html
    assert 'class="whitespace-nowrap">🌳' in html


def test_lobby_carousel_readout_stripe_opacity_is_theme_driven():
    # H4: a flat opacity-20 read as a permanently disabled panel on
    # TIMBERLINE (scanline_opacity: 0%); it now follows the same
    # --aurelia-scanline-opacity every other scanline overlay reads.
    html = render_index()
    assert 'style="opacity: var(--aurelia-scanline-opacity)"' in html
    assert "bg-[size:100%_4px] pointer-events-none opacity-20" not in html


def test_lobby_has_review_teaser_and_loads_review_js():
    html = render_index()
    assert '<div id="lobby-review-teaser"' in html
    assert '<span id="lobby-review-count">0</span>' in html
    assert 'href="garden.html?review=1"' in html
    # "hidden" by default -- shown only client-side by the teaser script
    # once Review.dueCount() says there's actually something due.
    assert 'id="lobby-review-teaser" class="hidden' in html
    assert 'src="assets/js/review.js?v=test"' in html


def test_lobby_has_no_embedded_per_note_review_payload():
    # The removed 2026-09-07 feature embedded a review_seed of 245
    # id/title/maturity triples straight into index.html; the rebuilt
    # teaser is 100% client-side (Review.dueCount(), reading only the
    # aurelia_review_log localStorage key -- see the teaser script in
    # indextemplate.html). This proves neither the literal "review_seed"
    # name nor any garden note id leaked back in anywhere -- including
    # inside the page's own SYSTEM_INDEX command-palette blob, which
    # legitimately carries every note's id in its url field (as
    # "garden.html#note-a") and would otherwise make this check pass for
    # the wrong reason.
    cards = [
        make_card("note-a", "A", "CONCEPT"),
        make_card("note-b", "B", "SOURCE"),
        make_card("note-c", "C", "AUTHOR"),
    ]
    search_index = dumps_for_script_tag(_build_search_index(cards, make_profile()))
    html = render_index(search_index=search_index)

    assert "review_seed" not in html

    # Scope the note-id check to everything OUTSIDE the SYSTEM_INDEX
    # script's own JSON blob (mirrors how base.html embeds it: `const
    # SYSTEM_INDEX = {{ search_index }};`).
    before, marker, after = html.partition("const SYSTEM_INDEX = ")
    assert marker, "SYSTEM_INDEX script tag not found in rendered Lobby HTML"
    _, _, after_blob = after.partition(";")
    outside_index = before + after_blob

    for note_id in ("note-a", "note-b", "note-c"):
        assert note_id in html, f"sanity check: {note_id} should be in the page via SYSTEM_INDEX"
        assert note_id not in outside_index, (
            f"{note_id} appears outside the search index -- a per-note review "
            "payload may have leaked into the Lobby template"
        )


def test_search_index_seed_titles_are_plain():
    seeds = {
        entry["url"]: entry
        for entry in _build_search_index([], make_profile())
    }
    assert seeds["index.html"]["title"] == "Home"
    assert seeds["index.html"]["desc"] == "Start page"
    assert seeds["garden.html"]["title"] == "Garden"
    assert "concepts" in seeds["garden.html"]["desc"]
    # About keeps its existing shape.
    assert seeds["about.html"]["title"] == "About // Ada Lovelace"
    # Types, tags and urls are untouched by the copy change.
    for entry in seeds.values():
        assert entry["type"] == "SYSTEM"
        assert entry["tags"]
