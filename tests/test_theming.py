from engine.theming import (
    _hex_to_rgba,
    _variables_for,
    available_themes,
    default_theme_slug,
    theme_slug,
)


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
    # this is the check that catches the "true brand orange fails as text"
    # trap the theme's own config.py comment documents (secondary/tertiary
    # are hand-darkened precisely so this test passes).
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


def test_available_themes_covers_every_theme_config_entry():
    from engine.config import THEME_CONFIG
    themes = available_themes()
    assert len(themes) == len(THEME_CONFIG)
    assert {t["key"] for t in themes} == {theme_slug(k) for k in THEME_CONFIG}


def test_available_themes_entries_carry_label_and_swatch():
    themes = available_themes()
    for t in themes:
        assert t["label"]
        assert set(t["swatch"].keys()) == {"bg", "primary", "secondary", "accent"}
