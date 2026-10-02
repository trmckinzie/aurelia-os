"""Guards for roadmap S07: the defects the audit found on the public site.

Template-level changes are pinned on rendered fixture HTML, the same way
test_lobby.py and test_garden.py do it. The self-hosting guard also builds the
vendored files into a temporary dist/ and scans them.
"""
import re
from pathlib import Path

import pytest

from engine import vendor
from engine.cachebust import stamp_asset_versions
from engine.config import ROOT_DIR
from engine.pipeline import _site_root
from tests.test_about import render_404, render_about, render_index
from tests.test_garden import render_garden

ASSETS = Path(ROOT_DIR) / "assets"


def _all_pages():
    return {
        "index": render_index(),
        "garden": render_garden(),
        "about": render_about(),
        "404": render_404(site_root="/aurelia-os/"),
    }


# --- depth-proof links ----------------------------------------------------

def test_404_links_are_absolute_to_the_site_root():
    html = render_404(site_root="/aurelia-os/")
    for page in ("index", "garden", "about"):
        assert f'href="/aurelia-os/{page}.html"' in html
    assert 'href="index.html"' not in html
    assert 'href="garden.html"' not in html
    assert 'href="about.html"' not in html
    assert 'src="/aurelia-os/assets/js/utils.js?v=' in html
    assert 'href="/aurelia-os/assets/css/main.css?v=' in html


def test_ordinary_pages_keep_relative_links():
    html = render_about()
    assert 'href="index.html"' in html
    assert 'src="assets/js/utils.js?v=' in html


def test_the_palette_anchors_result_urls_to_the_site_root():
    assert 'const SITE_ROOT = "/aurelia-os/";' in render_404(site_root="/aurelia-os/")
    assert 'const SITE_ROOT = "";' in render_about()


def test_site_root_follows_the_repository_and_the_domain():
    assert _site_root({}, {"GITHUB_REPOSITORY": "trmckinzie/aurelia-os"}) == "/aurelia-os/"
    assert _site_root({}, {}) == "/"
    assert _site_root({}, {"GITHUB_REPOSITORY": "trmckinzie/trmckinzie.github.io"}) == "/"
    custom = {"site": {"domain": "example.com"}}
    assert _site_root(custom, {"GITHUB_REPOSITORY": "trmckinzie/aurelia-os"}) == "/"


# --- cache busting --------------------------------------------------------

def test_every_local_asset_url_carries_a_version_token():
    token = re.compile(r"\?v=@@asset:([A-Za-z0-9_./-]+)@@")
    for name, html in _all_pages().items():
        refs = re.findall(r'(?:src|href)="[^"]*?(assets/[^"?]+)\?v=', html)
        assert refs, name
        for ref in refs:
            assert f"{ref}?v=@@asset:{ref}@@" in html, (name, ref)
        assert token.search(html)
    html = render_index()
    for path in ("assets/css/main.css", "assets/css/theme-vars.css", "assets/fonts/fonts.css",
                 "assets/vendor/marked.umd.js", "assets/vendor/motion.js"):
        assert f"{path}?v=@@asset:{path}@@" in html


def test_stamping_uses_the_hash_of_the_served_file(tmp_path):
    (tmp_path / "assets" / "css").mkdir(parents=True)
    css = tmp_path / "assets" / "css" / "main.css"
    css.write_text("a{}", encoding="utf-8")
    page = tmp_path / "index.html"
    page.write_text('<link href="assets/css/main.css?v=@@asset:assets/css/main.css@@">', encoding="utf-8")
    stamp_asset_versions(tmp_path)
    first = page.read_text(encoding="utf-8")
    assert "@@" not in first

    page.write_text('<link href="assets/css/main.css?v=@@asset:assets/css/main.css@@">', encoding="utf-8")
    css.write_text("a{color:red}", encoding="utf-8")
    stamp_asset_versions(tmp_path)
    assert page.read_text(encoding="utf-8") != first


# --- nav, palette, toolkit ------------------------------------------------

def test_nav_marks_only_the_current_page():
    for active, page in (("index", render_index()), ("garden", render_garden()), ("about", render_about())):
        assert page.count('aria-current="page"') == 2, "desktop and mobile nav"
        assert f'href="{active}.html" data-nav-link data-active aria-current="page"' in page
    assert 'aria-current="page"' not in render_404()


def test_palette_is_a_labelled_native_dialog_with_a_combobox():
    html = render_about()
    assert re.search(r'<dialog id="cmd-dialog"[^>]*aria-label="[^"]+"', html)
    assert 'id="cmd-backdrop"' not in html
    assert re.search(r'<input[^>]*id="cmd-input"[^>]*role="combobox"', html)
    assert 'aria-controls="cmd-results"' in html
    assert re.search(r'id="cmd-results"[^>]*role="listbox"', html)
    assert 'id="cmd-status"' in html
    assert 'role="option"' in html and "aria-activedescendant" in html
    assert "cmdDialog.showModal()" in html
    assert "cmdReturnFocus" in html


def test_toolkit_ring_is_hidden_from_screen_readers_and_the_readout_is_announced():
    html = render_index()
    assert re.search(r'class="carousel-scene[^"]*"[^>]*aria-hidden="true"', html)
    assert re.search(r'<div aria-live="polite" aria-atomic="true"[^>]*>\s*<h3 id="readout-title"', html)
    assert "motion-safe:animate-pulse" in html


def test_carousel_turns_the_short_way():
    html = render_index()
    assert "if (diff > cardCount / 2) diff -= cardCount;" in html
    assert "else if (diff < -cardCount / 2) diff += cardCount;" in html


def test_about_page_does_not_state_a_theme_count():
    html = render_about()
    assert "four switchable themes" not in html


# --- dead code ------------------------------------------------------------

@pytest.mark.parametrize("name", [".carousel-card", ".modal-action", ".bloom-accent", ".text-shadow-white"])
def test_dead_css_stays_removed(name):
    assert name not in (ASSETS / "css" / "main.css").read_text(encoding="utf-8")


def test_dead_roving_container_stays_removed():
    html = render_garden()
    assert "rovingContainer" not in html
    for js in (ASSETS / "js").glob("*.js"):
        assert "rovingContainer" not in js.read_text(encoding="utf-8")


# --- self-hosting ---------------------------------------------------------

_EXTERNAL = re.compile(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", re.I)
_CSS_URL = re.compile(r"""url\(\s*["']?\s*(?:https?:)?//""", re.I)
_IMPORT = re.compile(r"""@import\s+(?:url\()?\s*["']?(?:https?:)?//""", re.I)


def _external_loads(html):
    """External <script src> and stylesheet/font <link href>; plain <a href> links are fine."""
    found = []
    for tag in re.findall(r"<(?:script|link)\b[^>]*>", html, re.I):
        if _EXTERNAL.search(tag):
            found.append(tag)
    return found


def test_no_page_loads_a_script_stylesheet_or_font_from_another_origin():
    for name, html in _all_pages().items():
        assert _external_loads(html) == [], name
        assert "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html, name
        assert "cdn.jsdelivr.net" not in html, name


@pytest.fixture(scope="module")
def built_vendor(tmp_path_factory):
    dist = tmp_path_factory.mktemp("dist")
    original = vendor.OUTPUT_DIR
    vendor.OUTPUT_DIR = str(dist)
    try:
        vendor.copy_vendor_assets()
    finally:
        vendor.OUTPUT_DIR = original
    return dist / "assets"


def test_vendored_fonts_reference_only_files_that_ship(built_vendor):
    css = (built_vendor / "fonts" / "fonts.css").read_text(encoding="utf-8")
    assert not _CSS_URL.search(css) and not _IMPORT.search(css)
    names = re.findall(r"url\(files/([^)?]+\.woff2)\?v=[0-9a-f]{10}\)", css)
    assert names
    for name in set(names):
        assert (built_vendor / "fonts" / "files" / name).is_file(), name
    shipped = {p.name for p in (built_vendor / "fonts" / "files").iterdir()}
    assert shipped == set(names), "no unreferenced font files"
    for _, family, _ in vendor.FONT_FACES:
        assert f"font-family: '{family}'" in css


def test_fonts_and_scripts_ship_with_their_licences(built_vendor):
    licenses = {p.name for p in (built_vendor / "fonts" / "licenses").iterdir()}
    assert licenses == {f"{package}-LICENSE.txt" for package, _, _ in vendor.FONT_FACES}
    for path in (built_vendor / "fonts" / "licenses").iterdir():
        assert path.stat().st_size > 0
    for name in ("marked.umd.js", "motion.js", "LICENSE-marked.txt", "LICENSE-motion.txt"):
        assert (built_vendor / "vendor" / name).stat().st_size > 0, name
    for name in ("marked.umd.js", "motion.js"):
        assert "sourceMappingURL" not in (built_vendor / "vendor" / name).read_text(encoding="utf-8")


def test_source_stylesheet_loads_nothing_from_another_origin():
    css = (ASSETS / "css" / "main.css").read_text(encoding="utf-8")
    assert not _CSS_URL.search(css) and not _IMPORT.search(css)
