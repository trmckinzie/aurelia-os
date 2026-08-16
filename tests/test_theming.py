from engine.theming import _hex_to_rgba, available_themes, default_theme_slug, theme_slug


def test_theme_slug_converts_key_to_kebab_case():
    assert theme_slug("CYBER_PRIME") == "cyber-prime"
    assert theme_slug("THE_PATRIOT") == "the-patriot"


def test_hex_to_rgba_converts_correctly():
    assert _hex_to_rgba("#0a0a0b", "0.6") == "rgba(10, 10, 11, 0.6)"


def test_hex_to_rgba_handles_hex_without_hash():
    assert _hex_to_rgba("ffffff", "1") == "rgba(255, 255, 255, 1)"


def test_default_theme_slug_matches_current_theme():
    # CURRENT_THEME is THEME_CONFIG["CYBER_PRIME"] as of this writing --
    # this test cares that the lookup is *correct* (finds whichever theme
    # CURRENT_THEME actually points to), not that it's hardcoded to one value.
    from engine.config import CURRENT_THEME, THEME_CONFIG
    expected_key = next(k for k, v in THEME_CONFIG.items() if v is CURRENT_THEME)
    assert default_theme_slug() == theme_slug(expected_key)


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
