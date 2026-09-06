"""Rendering guards for the About / profile page and the shared chrome it added.

These drive the Jinja templates directly (engine.config.env), the same way
tests/test_output_escaping.py does, rather than going through the build. That
keeps them independent of engine/pipeline.py's page list: the template contract
is what is being asserted, and it can be asserted before -- or after -- the
pipeline learns to render it.

The profile fixture below is deliberately local to this file and not imported
from the profile-validation tests. It is a *rendering* fixture: it exists to
carry hostile strings and to be stripped down to "every optional key absent",
which is not what a validation fixture is for. Sharing one would couple two
suites that want to move in opposite directions.
"""
import json
import re

import pytest
from markupsafe import Markup

from engine.config import CURRENT_THEME, env
from engine.textutils import dumps_for_script_tag
from engine.theming import available_themes, default_theme_slug


# --- fixtures ---------------------------------------------------------------

def make_profile(**overrides):
    """A minimal but complete profile, matching the contract in profile.json:
    every optional key present, so a test can remove one and see what breaks."""
    profile = {
        "schema_version": 1,
        "identity": {
            "name": "Ada Lovelace",
            "headline": "Analyst & Metaphysician",
            "location": "London, UK",
            "pronouns": "she/her",
            "summary": "Notes on the Analytical Engine, and what a machine can be said to originate.",
        },
        "roles": [
            {
                "org": "Analytical Society",
                "title": "Collaborator",
                "period": "1842 — 1843",
                "description": "Translated and annotated Menabrea's memoir.",
                "url": "https://example.org/society",
                "primary": True,
            },
            {
                "org": "Independent",
                "title": "Correspondent",
                "period": "1833 — 1852",
                "description": "Correspondence on mathematics and mechanism.",
                "primary": False,
            },
        ],
        "education": [
            {
                "institution": "Private tuition",
                "credential": "Mathematics",
                "period": "1829 — 1835",
                "detail": "Under Augustus De Morgan.",
                "url": "https://example.org/tuition",
            },
        ],
        "skills": [
            {"group": "Mathematics", "items": ["Analysis", "Algorithms"]},
            {"group": "Writing", "items": ["Technical notes"]},
        ],
        "projects": [
            {
                "name": "Note G",
                "description": "The first published algorithm intended for a machine.",
                "url": "https://example.org/note-g",
                "tags": ["Algorithms", "Bernoulli"],
                "status": "active",
            },
            {
                "name": "Engine correspondence",
                "description": "Letters on the engine's capabilities.",
                "tags": [],
                "status": "archived",
            },
        ],
        "links": [
            {"label": "Email", "url": "mailto:ada@example.org", "kind": "email"},
            {"label": "Code", "url": "https://example.org/code", "kind": "code"},
        ],
        "meta": {
            "updated": "2026-09-05",
            "availability": "Open to correspondence.",
        },
    }
    profile.update(overrides)
    return profile


def make_config(site=None, include_site=True):
    config = {
        "system_name": "AURELIA // OS",
        "system_version": "v3.2.0",
        "status_message": "Developing_Aurelia_OS",
        "author": {
            "name": "Ada Lovelace",
            "short_name": "A.L.",
            "role": "Analyst",
            "email": "ada@example.org",
            "location": "London, UK",
            "bio_short": "Analysis, mechanism, and notation.",
            "bio_long": "Longer bio.",
        },
        "links": {"github": "https://example.org/code"},
        "tech_stack": [],
    }
    if include_site:
        config["site"] = site if site is not None else {
            "name": "Ada Lovelace",
            "nav_label": "AL",
            "tagline": "Analysis and mechanism.",
            "domain": "",
        }
    return config


def base_context(**overrides):
    """Every variable base.html dereferences, plus the About page's own."""
    context = {
        "config": make_config(),
        "theme": CURRENT_THEME,
        "theme_key": default_theme_slug(),
        "available_themes_json": dumps_for_script_tag(available_themes()),
        "search_index": Markup("[]"),
        "asset_version": "test",
        "active_page": "about",
        "profile": make_profile(),
        "person_jsonld": dumps_for_script_tag({
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "Ada Lovelace",
        }),
    }
    context.update(overrides)
    return context


def render_about(**overrides):
    return env.get_template("pages/abouttemplate.html").render(**base_context(**overrides))


def main_of(html):
    """Just the About page's own <main> region.

    Several assertions below are about what this *page* is allowed to contain,
    and the shared chrome from base.html would otherwise answer for it -- the
    nav's active link carries .text-shadow-cyan, and the theme-switcher script
    emits a literal `border-black/10` swatch outline. Neither is this page's
    doing, and neither should be able to fail (or to pass) a rule about it.
    """
    start = html.index("<main ")
    return html[start:html.index("</main>", start)]


# --- content ----------------------------------------------------------------

def test_about_renders_identity_and_every_section_heading():
    html = render_about()
    assert "Ada Lovelace" in html
    assert "Analyst &amp; Metaphysician" in html
    assert "London, UK" in html
    assert "she/her" in html
    assert "Open to correspondence." in html
    for heading in ("Summary", "Skills", "Experience", "Education", "Selected Work"):
        assert f">{heading}</h2>" in html, f"missing <h2> for {heading}"
    # Items, not just the section shells.
    assert "Collaborator" in html
    assert "Note G" in html
    assert "Analytical Engine" in html
    assert 'datetime="2026-09-05"' in html


def test_about_renders_a_primary_and_a_non_primary_role_rule():
    # `primary` is the only visual weight difference between roles, so a
    # regression that ignores the flag would otherwise be invisible here.
    html = render_about()
    assert "border-l-2 pl-6 border-aurelia-primary" in html
    assert "border-l-2 pl-6 border-aurelia-border" in html


def test_about_maps_project_status_to_a_theme_role_color():
    html = render_about()
    assert "text-aurelia-primary bg-aurelia-primary/10" in html   # active
    assert "text-aurelia-muted bg-aurelia-muted/10" in html       # archived


# --- escaping ---------------------------------------------------------------

def test_about_escapes_a_script_in_the_headline():
    profile = make_profile()
    profile["identity"]["headline"] = "<script>alert(1)</script>"
    html = render_about(profile=profile)
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_about_escapes_hostile_project_name_and_org():
    # Both an HTML-text position (the project name, the org label) and an
    # attribute position (the <title>, which carries the headline) are
    # covered, since autoescape being off would break both at once.
    profile = make_profile()
    profile["projects"][0]["name"] = '" onmouseover="alert(1)" x="<img src=x onerror=1>'
    profile["roles"][0]["org"] = '<img src=x onerror=alert(1)>'
    profile["identity"]["headline"] = 'He said "hi" <img src=x onerror=1>'
    html = render_about(profile=profile)
    assert "<img" not in html
    # The payload survives as inert text; what must not survive is the quote
    # that would close the surrounding attribute and start a new one.
    assert '" onmouseover="' not in html
    assert "&lt;img src=x onerror=1&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    # The quote that would have closed the title attribute is encoded.
    assert 'He said "hi"' not in html
    assert "He said &#34;hi&#34;" in html


def test_every_offsite_anchor_has_noopener():
    html = render_about()
    anchors = re.findall(r'<a\b[^>]*href="(?:https?:|mailto:)[^>]*>', html)
    assert anchors, "expected outbound anchors on the profile page"
    for anchor in anchors:
        assert 'rel="noopener noreferrer"' in anchor, anchor
        # rel is the guard precisely because nothing here opens a new tab.
        assert "target=" not in anchor, anchor


def test_about_jsonld_script_present_and_parses():
    html = render_about()
    match = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert match, "no ld+json block emitted"
    payload = json.loads(match.group(1))
    assert payload["@type"] == "Person"
    # Emitted as Markup, so it must not have been entity-escaped on the way in.
    assert "&#34;" not in match.group(1)


# --- structure / accessibility ---------------------------------------------

def test_about_has_exactly_one_h1():
    html = render_about()
    assert len(re.findall(r"<h1\b", html)) == 1


def test_about_heading_levels_do_not_skip():
    html = render_about()
    levels = [int(m) for m in re.findall(r"<h([1-6])\b", html)]
    assert levels[0] == 1
    for previous, current in zip(levels, levels[1:]):
        assert current - previous <= 1, f"heading jumps h{previous} -> h{current}"


def test_about_sections_are_labelled_by_a_real_heading_id():
    html = render_about()
    labelled = re.findall(r'<section aria-labelledby="([^"]+)"', html)
    assert labelled, "sections should be labelled"
    for target in labelled:
        assert f'id="{target}"' in html, f"aria-labelledby={target} points at nothing"


def test_about_uses_no_raw_tailwind_palette_colors():
    # The whole palette is semantic (aurelia-*); a raw Tailwind color would
    # be theme-blind and go unreadable on at least one of the four themes.
    html = main_of(render_about())
    banned = re.compile(
        r"\b(?:text|bg|border|decoration|from|to|via|ring|fill|stroke)-"
        r"(?:white|black|gray|grey|slate|zinc|neutral|stone|red|orange|amber|"
        r"yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|"
        r"fuchsia|pink|rose)\b")
    assert not banned.findall(html)


def test_about_uses_none_of_the_lobby_in_jokes():
    html = main_of(render_about())
    for token in ("glitch-text", "decrypt-effect", "text-shadow-cyan",
                  "OPERATOR", "NODE_", "SYSTEM_"):
        assert token not in html, f"{token} does not belong on the profile page"


def test_about_optional_fields_absent_render_cleanly():
    profile = make_profile()
    del profile["identity"]["pronouns"]
    del profile["meta"]["availability"]
    for role in profile["roles"]:
        role.pop("url", None)
    for entry in profile["education"]:
        entry.pop("url", None)
        entry.pop("detail", None)
    for project in profile["projects"]:
        project.pop("url", None)
    html = render_about(profile=profile)
    assert "Pronouns" not in html
    assert "Availability" not in html
    assert "Undefined" not in html
    assert "None" not in html
    # The orgs/institutions/projects themselves still render, just not linked.
    assert "Analytical Society" in html
    assert "Note G" in html
    assert len(re.findall(r"<h1\b", html)) == 1


# --- shared chrome ----------------------------------------------------------

def render_404(**overrides):
    context = base_context(active_page="404", **overrides)
    return env.get_template("404.html").render(**context)


def render_index(**overrides):
    context = base_context(active_page="index", **overrides)
    context.setdefault("stats", {
        "total_notes": 0,
        "latest_log_date": None,
        "maturity_counts": {"seed": 0, "growing": 0, "evergreen": 0},
        "hub_notes": [],
    })
    context.setdefault("review_seed", Markup("null"))
    return env.get_template("pages/indextemplate.html").render(**context)


def test_nav_links_to_about_on_index_garden_and_about():
    # base.html owns the nav, so proving it there proves it for every page
    # that extends it -- including the Garden, whose own context is far too
    # heavy to stand up here.
    chrome = render_404()
    assert chrome.count('href="about.html"') >= 2, "desktop + mobile nav entries"
    assert ">ABOUT</a>" in chrome

    about = render_about()
    assert 'href="about.html" data-nav-link data-active' in about

    lobby = render_index()
    assert 'href="about.html" class="btn btn-primary group"' in lobby
    assert "About me" in lobby


def test_nav_indicator_script_is_not_hardcoded_to_two_links():
    # The sliding indicator measures [data-nav-link] generically; a count
    # baked into the script would silently mis-position once About landed.
    chrome = render_404()
    assert chrome.count("data-nav-link") >= 3
    assert "querySelectorAll('[data-nav-link]')" in chrome


def test_skip_link_precedes_nav_and_main_has_id():
    html = render_about()
    skip = html.index('href="#main-content"')
    nav = html.index("<nav class=\"nav-shell")
    assert skip < nav, "skip link must be the first focusable element"
    assert 'id="main-content"' in html
    assert html.index('id="main-content"') > nav


@pytest.mark.parametrize("page", ["404.html", "pages/abouttemplate.html"])
def test_canonical_only_when_domain_set(page):
    def render(domain, active):
        config = make_config(site={
            "name": "Ada Lovelace", "nav_label": "AL",
            "tagline": "t", "domain": domain,
        })
        context = base_context(config=config, active_page=active)
        return env.get_template(page).render(**context)

    active = "404" if page == "404.html" else "about"

    assert 'rel="canonical"' not in render("", active)

    with_domain = render("example.com", active)
    assert 'rel="canonical"' in with_domain
    assert "https://example.com/" in with_domain


def test_canonical_for_the_lobby_points_at_the_site_root():
    config = make_config(site={
        "name": "Ada Lovelace", "nav_label": "AL", "tagline": "t",
        "domain": "example.com",
    })
    html = render_index(config=config)
    assert 'href="https://example.com/"' in html


def test_brand_label_comes_from_config():
    branded = render_about()
    assert "AL<span" in branded
    assert "SITE<span" not in branded

    # A config predating the `site` block (the factory clone writes one) must
    # still render -- degraded to the generic fallback brand, not to an error.
    legacy = render_about(config=make_config(include_site=False))
    assert "SITE<span" in legacy
    assert 'rel="canonical"' not in legacy


def test_description_block_feeds_both_meta_description_and_og():
    html = render_about()
    assert '<meta name="description" content="Analyst &amp; Metaphysician">' in html
    assert '<meta property="og:description" content="Analyst &amp; Metaphysician">' in html
    assert '<meta property="og:title" content="Ada Lovelace">' in html
    assert "<title>Ada Lovelace — Analyst &amp; Metaphysician</title>" in html


def test_about_does_not_rely_on_the_reveal_animation():
    # [data-reveal] starts at opacity 0 and is brought in by script. On a CV
    # page that would mean "invisible without JavaScript", and invisible in
    # print.
    assert "data-reveal" not in render_about()
