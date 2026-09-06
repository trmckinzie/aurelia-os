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

from engine.pipeline import _build_search_index


# Copy that belonged to the old voice. Every one of these was on the page (or
# in the shared chrome) before the rebrand.
LEGACY_TOKENS = (
    "AURELIA OS",
    "WHAT IS AURELIA",
    "SYSTEM_READY",
    "NEURAL_LOADOUT",
    "CORTEX",
    "MOD_01",
    "OPERATOR_PROFILE",
    "TERM_v3",
    "Initiate Neural Query",
    "NODES CONNECTED",
)


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
    assert 'href="about.html" class="btn btn-primary group"' in html
    assert 'href="garden.html" class="btn btn-ghost group"' in html
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
