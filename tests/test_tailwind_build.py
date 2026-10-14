"""Tests for engine/tailwind_build.py's generate_config() -- the theme-
independent tailwind.input.css that Tailwind v4 compiles (see that module's
docstring for why it no longer varies by theme, and docs/DECISIONS.md item
42 for the v4 migration, roadmap S12). compile_css() itself needs the real
Tailwind CLI and node_modules/, so it is exercised by `bash verify.sh`'s real
build, not here.
"""
import os
import re

from engine import tailwind_build
from engine.config import ROOT_DIR
from engine.tailwind_build import INPUT_CSS_NAME, generate_config

# Hand-written stylesheets that compile alongside the utilities: main.css
# through the generated import, each template's inline <style> through an
# @layer wrapper. See the module docstring on why they must sit *inside*
# Tailwind's utilities layer and not above it.
MAIN_CSS = os.path.join(ROOT_DIR, "assets", "css", "main.css")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system", "templates")

# v4 theme tokens are plain custom properties that utilities read with var()
# at runtime: a site-declared --text-xs replaces the `text-xs` utility's own
# value for the whole page. The site's names carry the aurelia- prefix.
_V4_THEME_NAMESPACE = re.compile(
    r"^\s*--(text|font|color|spacing|radius|shadow|inset-shadow|drop-shadow|leading|tracking|"
    r"blur|animate|ease|breakpoint|container|perspective|aspect|default)(-[a-z0-9-]+)?\s*:",
    re.M,
)


def _generate(tmp_path, monkeypatch):
    # ROOT_DIR, not OUTPUT_DIR -- the input stylesheet lives at the project
    # root (its @source and @import paths are relative to it), not in dist/.
    # Patched so the test never touches this repo's own generated file.
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path))
    config_path = generate_config()
    return config_path, open(config_path, encoding="utf-8").read()


def test_generate_config_writes_the_input_stylesheet_to_root_dir(tmp_path, monkeypatch):
    config_path, _ = _generate(tmp_path, monkeypatch)
    assert INPUT_CSS_NAME == "tailwind.input.css"
    assert config_path == str(tmp_path / INPUT_CSS_NAME)
    assert (tmp_path / INPUT_CSS_NAME).is_file()


def test_generate_config_is_css_first_v4_configuration(tmp_path, monkeypatch):
    # The v4 format: an @import of Tailwind and a @theme block, not the v3
    # tailwind.config.js (module.exports / @tailwind directives / @config).
    _, css = _generate(tmp_path, monkeypatch)
    assert '@import "tailwindcss" source(none);' in css
    assert "@theme inline {" in css
    for v3_only in ("module.exports", "@tailwind ", "@config", "<alpha-value>"):
        assert v3_only not in css


def test_generate_config_wires_every_semantic_color_to_its_css_variable(tmp_path, monkeypatch):
    _, css = _generate(tmp_path, monkeypatch)
    # A var() reference, not a baked-in hex value -- the per-theme values
    # live in theme-vars.css (engine/theming.py) and switch at runtime.
    for name, var in [
        ("aurelia-bg", "bg-main"),
        ("aurelia-primary", "primary"),
        ("aurelia-accent", "accent"),
        ("aurelia-insight", "insight"),
    ]:
        assert f"--color-{name}: rgb(var(--aurelia-{var}-rgb));" in css
    assert not re.search(r"--color-aurelia-[a-z-]+: #", css)


def test_generate_config_declares_the_non_color_tokens_the_markup_uses(tmp_path, monkeypatch):
    # rounded-theme, font-sans/mono/display, shadow-e1..e3/rim/rim-e2/rim-e3,
    # animate-scanline: each is a class in the templates or cards.py, so a
    # missing token would compile to nothing, silently.
    _, css = _generate(tmp_path, monkeypatch)
    for token in (
        "--radius-theme: var(--aurelia-radius);",
        "--font-sans: var(--aurelia-font-body), Inter, sans-serif;",
        "--font-mono: var(--aurelia-font-mono), monospace;",
        "--font-display: var(--aurelia-font-display), monospace;",
        "--shadow-e1: var(--aurelia-elevation-1);",
        "--shadow-e2: var(--aurelia-elevation-2);",
        "--shadow-e3: var(--aurelia-elevation-3);",
        "--shadow-rim: var(--aurelia-rim-light);",
        "--shadow-rim-e2: var(--aurelia-rim-light), var(--aurelia-elevation-2);",
        "--shadow-rim-e3: var(--aurelia-rim-light), var(--aurelia-elevation-3);",
        "--animate-scanline: scanline 8s linear 1 forwards;",
    ):
        assert token in css


def test_generate_config_never_reintroduces_the_retired_aliases(tmp_path, monkeypatch):
    # aurelia-cyan/dim/dark/orange/green/purple were pre-semantic aliases
    # pointing at the same variables as a semantic name -- removed once
    # every call site moved to the semantic one (see the module docstring).
    _, css = _generate(tmp_path, monkeypatch)
    for retired in ("aurelia-cyan", "aurelia-dim", "aurelia-dark",
                    "aurelia-orange", "aurelia-green", "aurelia-purple"):
        assert f"--color-{retired}" not in css


def test_generate_config_scans_only_the_rendered_dist_output(tmp_path, monkeypatch):
    # Not the Python/Jinja source -- cards.py assembles some class names
    # dynamically, and only the rendered HTML in dist/ has them as literal
    # text Tailwind's scanner can see. v4's default source detection skips
    # gitignored paths, and dist/ is one, so the default walk is turned off
    # and the pages are named explicitly (see the module docstring).
    _, css = _generate(tmp_path, monkeypatch)
    assert "source(none)" in css
    assert '@source "./dist/**/*.html";' in css


def test_generate_config_imports_main_css_into_the_utilities_layer_last(tmp_path, monkeypatch):
    # Unlayered, main.css would beat every utility regardless of specificity
    # (cascade layers lose to unlayered rules); in the utilities layer, after
    # Tailwind's own, the ordinary cascade applies, as it did on v3 (see the
    # module docstring).
    _, css = _generate(tmp_path, monkeypatch)
    main_import = '@import "./assets/css/main.css" layer(utilities);'
    assert main_import in css
    assert css.rstrip().endswith(main_import)
    assert css.index('@import "tailwindcss"') < css.index("@theme inline") < css.index(main_import)


def test_generate_config_writes_lf_line_endings(tmp_path, monkeypatch):
    # Reproducibility (roadmap S09): text mode would otherwise write CRLF
    # on Windows for the same commit CI builds with LF.
    config_path, _ = _generate(tmp_path, monkeypatch)
    raw = open(config_path, "rb").read()
    assert b"\r\n" not in raw


def test_generate_config_is_byte_identical_across_runs(tmp_path, monkeypatch):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, first = _generate(tmp_path / "a", monkeypatch)
    _, second = _generate(tmp_path / "b", monkeypatch)
    assert first == second


def _template_style_blocks():
    for dirpath, _, names in os.walk(TEMPLATE_DIR):
        for name in names:
            if not name.endswith(".html"):
                continue
            html = open(os.path.join(dirpath, name), encoding="utf-8").read()
            for body in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S):
                yield name, body


def test_every_inline_style_block_is_wrapped_in_the_utilities_layer():
    # Left unlayered, a template's own <style> would beat every utility on
    # the page regardless of specificity: the Garden's `details > summary`
    # border did exactly that on the first v4 build (DECISIONS item 42).
    blocks = list(_template_style_blocks())
    assert blocks, "expected at least one inline <style> block in the templates"
    for name, body in blocks:
        stripped = re.sub(r"/\*.*?\*/", "", body, flags=re.S).strip()
        assert stripped.startswith("@layer utilities {"), name
        assert stripped.endswith("}"), name


def test_site_css_declares_no_variable_in_tailwinds_theme_namespace():
    offenders = []
    for name, css in [("main.css", open(MAIN_CSS, encoding="utf-8").read())] + [
        (n, b) for n, b in _template_style_blocks()
    ]:
        offenders += [f"{name}: {m.group(0).strip()}" for m in _V4_THEME_NAMESPACE.finditer(css)]
    assert offenders == [], offenders
