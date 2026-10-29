import os

from engine import theming
from engine.theming import (
    _hex_to_rgba,
    _variables_for,
    available_theme_slugs,
    available_themes,
    default_theme_slug,
    generate_theme_css,
    is_switchable,
    theme_images,
    theme_mode,
    theme_slug,
)

# Every theme THEME_CONFIG holds, offered or not. Roadmap S11 narrowed the
# menu to two of them and deliberately deleted none: the experimental three
# stay built and contrast-checked (backlog B20 returns them to the menu).
ALL_THEME_KEYS = ["TIMBERLINE", "CYBER_PRIME", "THE_PATRIOT", "THE_STOA", "GRIZZ"]


def test_theme_slug_converts_key_to_kebab_case():
    assert theme_slug("CYBER_PRIME") == "cyber-prime"
    assert theme_slug("THE_PATRIOT") == "the-patriot"


def test_hex_to_rgba_converts_correctly():
    assert _hex_to_rgba("#0a0a0b", "0.6") == "rgba(10, 10, 11, 0.6)"


def test_hex_to_rgba_handles_hex_without_hash():
    assert _hex_to_rgba("ffffff", "1") == "rgba(255, 255, 255, 1)"


def test_default_theme_slug_matches_current_theme():
    # CURRENT_THEME is THEME_CONFIG["TIMBERLINE"] as of this writing --
    # this test cares that the lookup is *correct* (finds whichever theme
    # CURRENT_THEME actually points to), not that it's hardcoded to one value.
    from engine.config import CURRENT_THEME, THEME_CONFIG
    expected_key = next(k for k, v in THEME_CONFIG.items() if v is CURRENT_THEME)
    assert default_theme_slug() == theme_slug(expected_key)


def test_timberline_is_current_theme_and_default_slug():
    # TIMBERLINE became the default with the 2026-09 rebrand -- pin the
    # concrete value (unlike the generic lookup test above) so a future
    # accidental revert back to CYBER_PRIME as default is caught here.
    from engine.config import CURRENT_THEME, THEME_CONFIG
    assert CURRENT_THEME is THEME_CONFIG["TIMBERLINE"]
    assert default_theme_slug() == "timberline"


def test_timberline_is_first_in_theme_config_and_available_themes():
    from engine.config import THEME_CONFIG
    assert next(iter(THEME_CONFIG)) == "TIMBERLINE"
    themes = available_themes()
    assert themes[0]["key"] == "timberline"


def test_timberline_cursor_overrides_do_not_leak_to_other_themes():
    # TIMBERLINE opts out of the custom SVG arrow/reticle cursors in favor
    # of plain browser cursors -- a professional theme, not a HUD. Confirm
    # the override is theme-scoped: CYBER_PRIME must still get its
    # generated data-URI SVG cursors, not "auto"/"pointer" leaking across.
    from engine.config import THEME_CONFIG

    timberline_vars = _variables_for(THEME_CONFIG["TIMBERLINE"])
    assert timberline_vars["--aurelia-cursor-default"] == "auto"
    assert timberline_vars["--aurelia-cursor-interactive"] == "pointer"

    cyber_prime_vars = _variables_for(THEME_CONFIG["CYBER_PRIME"])
    assert cyber_prime_vars["--aurelia-cursor-default"].startswith('url("data:image/svg+xml,')
    assert cyber_prime_vars["--aurelia-cursor-default"].endswith(", auto")
    assert cyber_prime_vars["--aurelia-cursor-interactive"].startswith('url("data:image/svg+xml,')
    assert cyber_prime_vars["--aurelia-cursor-interactive"].endswith("12 12, pointer")


def _relative_luminance(hex_color):
    """WCAG 2.x relative luminance -- deliberately independent of
    theming._lum(), which uses the cheaper ITU-R BT.601 weighting for
    picking a *lit-gradient* direction, not for a real contrast-ratio
    check. This is the sRGB-linearized formula the WCAG contrast formula
    actually specifies."""
    hex_color = hex_color.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        c = int(hex_color[i:i + 2], 16) / 255
        c = c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        channels.append(c)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a, hex_b):
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def test_timberline_text_roles_meet_aa_contrast_on_every_background():
    # Every text-bearing role must clear WCAG AA's 4.5:1 floor against all
    # three of TIMBERLINE's surfaces (bg_main, bg_layer_1, bg_layer_2) --
    # this is the regression guard for the TRM / Pine repaint (see
    # docs/DECISIONS.md item 27): pine, pine-deep, steel, and brick must each
    # clear AA as text on every surface, same as the palette they replaced.
    # The tightest pairing is highlight on bg_layer_2 at 4.71:1.
    from engine.config import THEME_CONFIG

    colors = THEME_CONFIG["TIMBERLINE"]["colors"]
    backgrounds = ["bg_main", "bg_layer_1", "bg_layer_2"]
    text_roles = [
        "text_main", "text_muted", "primary", "secondary",
        "tertiary", "accent", "highlight", "info", "insight",
    ]
    for role in text_roles:
        for bg in backgrounds:
            ratio = _contrast_ratio(colors[role], colors[bg])
            assert ratio >= 4.5, (
                f"TIMBERLINE {role} ({colors[role]}) on {bg} ({colors[bg]}) "
                f"is only {ratio:.2f}:1, below WCAG AA's 4.5:1 floor"
            )


def test_default_type_register_keys_reproduce_former_hardcoded_values():
    # display_weight/display_tracking/display_leading/label_weight/halo/
    # font_body are all new, optional keys -- a theme that doesn't set them
    # (CYBER_PRIME, and every theme besides TIMBERLINE) must render exactly
    # what main.css/tailwind_build.py used to hard-code, so this refactor
    # is a no-op for every existing theme.
    from engine.config import THEME_CONFIG

    variables = _variables_for(THEME_CONFIG["CYBER_PRIME"])
    assert variables["--aurelia-display-weight"] == "800"
    assert variables["--aurelia-display-tracking"] == "-0.03em"
    assert variables["--aurelia-display-leading"] == "0.95"
    assert variables["--aurelia-label-weight"] == "700"
    assert variables["--aurelia-halo"] == "50%"
    assert variables["--aurelia-font-body"] == "'Inter', sans-serif"


def test_timberline_overrides_the_type_register_keys():
    # TIMBERLINE's editorial brief (serif display, grotesque body/labels,
    # halo off) depends on these six keys actually reaching the CSS
    # variables rather than falling back to the CYBER_PRIME-shaped defaults
    # above.
    from engine.config import THEME_CONFIG

    variables = _variables_for(THEME_CONFIG["TIMBERLINE"])
    assert variables["--aurelia-font-display"] == "'Cormorant Garamond', 'Times New Roman', Times, serif"
    assert variables["--aurelia-font-body"] == "'Helvetica Neue', Helvetica, Arial, sans-serif"
    assert variables["--aurelia-display-weight"] == "600"
    assert variables["--aurelia-display-tracking"] == "-0.005em"
    assert variables["--aurelia-display-leading"] == "1.02"
    assert variables["--aurelia-label-weight"] == "600"
    assert variables["--aurelia-halo"] == "0%"


def test_theme_config_still_holds_all_five_themes():
    from engine.config import THEME_CONFIG
    assert list(THEME_CONFIG) == ALL_THEME_KEYS


def test_every_theme_declares_its_switchable_flag():
    # The key is optional (an omitted one is offered), but each theme here
    # states it, so the menu's contents can be read straight off config.py.
    from engine.config import THEME_CONFIG
    for key, theme in THEME_CONFIG.items():
        assert isinstance(theme.get("switchable"), bool), f"{key} has no explicit switchable flag"
    assert is_switchable({"colors": {}}) is True


def test_available_themes_offers_only_the_switchable_themes_in_config_order():
    # Roadmap S11: TIMBERLINE as the light choice and CYBER_PRIME as the dark
    # one, nothing else. The experimental three stay in THEME_CONFIG.
    from engine.config import THEME_CONFIG
    assert [t["key"] for t in available_themes()] == ["timberline", "cyber-prime"]
    assert available_theme_slugs() == ["timberline", "cyber-prime"]
    assert [k for k, t in THEME_CONFIG.items() if not is_switchable(t)] == ["THE_PATRIOT", "THE_STOA", "GRIZZ"]


def test_default_theme_is_offered_by_the_menu():
    # Otherwise the menu could never mark the theme a first-time visitor is
    # looking at, and the head script would refuse a saved copy of it.
    assert default_theme_slug() in available_theme_slugs()


def test_available_themes_entries_carry_label_mode_and_swatch():
    themes = available_themes()
    for t in themes:
        assert t["label"]
        assert t["mode"] in ("light", "dark")
        assert set(t["swatch"].keys()) == {"bg", "primary", "secondary", "accent"}
    assert [(t["label"], t["mode"]) for t in themes] == [("Timberline", "light"), ("Cyber Prime", "dark")]


def test_theme_mode_follows_the_page_background_of_every_theme():
    # Light or dark is read off bg_main rather than typed by hand, so a
    # theme cannot be labelled the wrong way round.
    from engine.config import THEME_CONFIG
    assert {k: theme_mode(t) for k, t in THEME_CONFIG.items()} == {
        "TIMBERLINE": "light", "CYBER_PRIME": "dark", "THE_PATRIOT": "light",
        "THE_STOA": "light", "GRIZZ": "dark",
    }


def test_card_text_roles_meet_aa_contrast_in_every_theme():
    """text_main and text_muted must clear AA on every surface of every theme,
    the three the menu does not offer included (roadmap S11).

    The Gemini card's topic chips and its "what's inside" strip are 13px
    text, so AA's 4.5:1 floor applies rather than the large-text exception.
    They deliberately use text_main/text_muted instead of the card's own
    `info` identity colour, which the theme sweep above only checks for
    TIMBERLINE -- `info` is 3.97:1 on CYBER_PRIME's bg_layer_2 and 4.25:1 on
    GRIZZ's, so an accent-coloured label would ship a real AA failure in both
    dark themes while the existing test stayed green. This is the guard that
    notices if either role drifts, or if a new theme is added with a weak one.
    """
    from engine.config import THEME_CONFIG

    assert list(THEME_CONFIG) == ALL_THEME_KEYS
    for theme, cfg in THEME_CONFIG.items():
        colors = cfg["colors"]
        for role in ("text_main", "text_muted"):
            for bg in ("bg_main", "bg_layer_1", "bg_layer_2"):
                ratio = _contrast_ratio(colors[role], colors[bg])
                assert ratio >= 4.5, (
                    f"{theme} {role} ({colors[role]}) on {bg} ({colors[bg]}) "
                    f"is only {ratio:.2f}:1, below WCAG AA's 4.5:1 floor"
                )


# --- generate_theme_css() -----------------------------------------------

def test_generate_theme_css_writes_a_bare_root_and_one_block_per_theme(tmp_path, monkeypatch):
    from engine.config import THEME_CONFIG

    monkeypatch.setattr(theming, "OUTPUT_DIR", str(tmp_path))
    output_path = generate_theme_css()

    assert output_path == os.path.join(str(tmp_path), "assets", "css", "theme-vars.css")
    css = open(output_path, encoding="utf-8").read()

    assert ":root {" in css
    # Every theme, the ones the menu does not offer included: the stylesheet
    # is what keeps an experimental theme buildable while it waits (B20).
    assert list(THEME_CONFIG) == ALL_THEME_KEYS
    for key in THEME_CONFIG:
        assert f':root[data-theme="{theme_slug(key)}"] {{' in css
    # Every theme's own primary color lands somewhere in its own block --
    # a cheap proxy for "the per-theme variables actually made it in", not
    # just the selector.
    for key, theme in THEME_CONFIG.items():
        assert theme["colors"]["primary"] in css


def test_generate_theme_css_writes_lf_line_endings(tmp_path, monkeypatch):
    # Reproducibility (roadmap S09): text mode would otherwise translate
    # '\n' to the platform line ending, so the same commit would build to
    # CRLF on Windows and LF on CI.
    monkeypatch.setattr(theming, "OUTPUT_DIR", str(tmp_path))
    output_path = generate_theme_css()

    raw = open(output_path, "rb").read()
    assert b"\r\n" not in raw


def test_generate_theme_css_is_byte_identical_across_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(theming, "OUTPUT_DIR", str(tmp_path / "a"))
    first = open(generate_theme_css(), "rb").read()
    monkeypatch.setattr(theming, "OUTPUT_DIR", str(tmp_path / "b"))
    second = open(generate_theme_css(), "rb").read()
    assert first == second


# --- theme-matched images (docs/DECISIONS.md item 49) ------------------

def test_generate_theme_css_hides_images_made_for_another_theme(tmp_path, monkeypatch):
    # Every theme, offered or not, so an experimental theme stamped as the
    # build default still shows the default image and no variant.
    from engine.config import THEME_CONFIG

    monkeypatch.setattr(theming, "OUTPUT_DIR", str(tmp_path))
    css = open(generate_theme_css(), encoding="utf-8").read()
    rules = css[css.index("[data-theme-only]") - 40:]
    for key in THEME_CONFIG:
        slug = theme_slug(key)
        assert f':root[data-theme="{slug}"] [data-theme-only]:not([data-theme-only~="{slug}"])' in rules
        assert f':root[data-theme="{slug}"] [data-theme-hide~="{slug}"]' in rules
    assert rules.rstrip().endswith("{\n    display: none;\n}")


def test_theme_images_without_variants_is_the_image_alone():
    image = {"src": "assets/images/a.webp", "alt": "A photo"}
    assert theme_images(image, "timberline") == [
        {"src": "assets/images/a.webp", "alt": "A photo", "only": None, "hide": None, "current": True},
    ]


def test_theme_images_lists_the_default_then_each_variant_in_theme_order():
    image = {"src": "a.webp", "alt": "A", "themes": {
        "GRIZZ": {"src": "g.webp", "alt": "G"},
        "CYBER_PRIME": {"src": "c.webp", "alt": "C"},
    }}
    images = theme_images(image, "timberline")
    assert [i["src"] for i in images] == ["a.webp", "c.webp", "g.webp"]
    assert images[0]["hide"] == "cyber-prime grizz"
    assert [i["only"] for i in images] == [None, "cyber-prime", "grizz"]
    assert [i["alt"] for i in images] == ["A", "C", "G"]


def test_theme_images_marks_the_one_shown_under_the_build_default():
    # Only that one may load eagerly; the rest wait until a switch shows them.
    image = {"src": "a.webp", "alt": "A", "themes": {"CYBER_PRIME": {"src": "c.webp", "alt": "C"}}}
    assert [i["current"] for i in theme_images(image, "timberline")] == [True, False]
    assert [i["current"] for i in theme_images(image, "cyber-prime")] == [False, True]
    assert [i["current"] for i in theme_images(image, "grizz")] == [True, False]


def test_theme_images_is_a_template_global_without_importing_theming():
    # Registered where env is made (engine/config.py), so a renderer that
    # imports only env still has it; a fresh interpreter proves the import.
    import subprocess
    import sys
    code = ("from engine.config import env; "
            "print(env.globals['theme_images']({'src': 'a', 'alt': 'A'}, 'timberline')[0]['current'])")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert out.stdout.strip() == "True"
