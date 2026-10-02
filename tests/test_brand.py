"""Drift guard between brand/tokens/*.css (the TRM / Pine design-tool export)
and engine/config.py's THEME_CONFIG["TIMBERLINE"].

brand/ is an export from an external design tool: nobody edits files inside
it by hand (changes are made in the tool and re-exported), and it is
gitignored whole because this repo is public (PR #6, c1c3082) -- so it stays
local and a fresh clone, including CI, does not have it. This test skips at
module level when brand/ is absent rather than failing, which is why it is
not part of the suite CI uses to gate a merge the way the other TIMBERLINE
checks in tests/test_theming.py are.

font-mono is deliberately left out of the pairs below: the brand's token is
a system monospace stack for code, but the site intentionally sets code in
Helvetica Neue (TIMBERLINE's font_mono == font_body, see engine/config.py),
the same "one humanist face carries labels, buttons, chips, and code" trade
THE_STOA documents. That is a deliberate site-vs-brand divergence, not drift
to catch.

Values are parsed out of the token files with a plain `--name: value;` regex
-- no new dependency for something this small. Hex colors compare case-
insensitively; rgba()/gradient values are compared with internal whitespace
normalized, since the two files don't always agree on spacing after a comma.
"""
import os
import re

import pytest

from engine.config import ROOT_DIR, THEME_CONFIG

BRAND_DIR = os.path.join(ROOT_DIR, "brand")
TOKENS_DIR = os.path.join(BRAND_DIR, "tokens")

if not os.path.isdir(BRAND_DIR):
    pytest.skip(
        "brand/ is gitignored and absent from this checkout (expected in CI "
        "and any fresh clone) -- nothing to compare it against",
        allow_module_level=True,
    )

_TOKEN_RE = re.compile(r"--([a-zA-Z0-9-]+)\s*:\s*(.+?)\s*;")


def _parse_tokens(filename):
    path = os.path.join(TOKENS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return {name: value.strip() for name, value in _TOKEN_RE.findall(text)}


def _normalize(value):
    """Case-fold hex colors and collapse internal whitespace, so
    'rgba(28, 38, 34, 0.25)' and 'rgba(28,38,34,0.25)' compare equal, and so
    do '#2F6B4F' and '#2f6b4f'."""
    value = re.sub(r"\s+", " ", value.strip())
    value = re.sub(r"\s*,\s*", ",", value)
    return value.lower()


_COLOR_TOKENS = _parse_tokens("colors.css")
_EFFECT_TOKENS = _parse_tokens("effects.css")
_TYPE_TOKENS = _parse_tokens("typography.css")
_SPACE_TOKENS = _parse_tokens("spacing.css")

_TIMBERLINE = THEME_CONFIG["TIMBERLINE"]
_TIMBERLINE_COLORS = _TIMBERLINE["colors"]

# (brand token source dict, brand token name, config value, pair label)
_COLOR_PAIRS = [
    (_COLOR_TOKENS, "paper", _TIMBERLINE_COLORS["bg_main"], "paper/bg_main"),
    (_COLOR_TOKENS, "paper-raised", _TIMBERLINE_COLORS["bg_layer_1"], "paper-raised/bg_layer_1"),
    (_COLOR_TOKENS, "paper-sunk", _TIMBERLINE_COLORS["bg_layer_2"], "paper-sunk/bg_layer_2"),
    (_COLOR_TOKENS, "hairline", _TIMBERLINE_COLORS["border_main"], "hairline/border_main"),
    (_COLOR_TOKENS, "ink", _TIMBERLINE_COLORS["text_main"], "ink/text_main"),
    (_COLOR_TOKENS, "ink", _TIMBERLINE_COLORS["primary"], "ink/primary"),
    (_COLOR_TOKENS, "ink-muted", _TIMBERLINE_COLORS["text_muted"], "ink-muted/text_muted"),
    (_COLOR_TOKENS, "pine", _TIMBERLINE_COLORS["secondary"], "pine/secondary"),
    (_COLOR_TOKENS, "pine", _TIMBERLINE_COLORS["accent"], "pine/accent"),
    (_COLOR_TOKENS, "pine", _TIMBERLINE_COLORS["border_focus"], "pine/border_focus"),
    (_COLOR_TOKENS, "pine-deep", _TIMBERLINE_COLORS["insight"], "pine-deep/insight"),
    (_COLOR_TOKENS, "ochre", _TIMBERLINE_COLORS["highlight"], "ochre/highlight"),
    (_COLOR_TOKENS, "steel", _TIMBERLINE_COLORS["info"], "steel/info"),
    (_COLOR_TOKENS, "brick", _TIMBERLINE_COLORS["tertiary"], "brick/tertiary"),
]

_EFFECT_PAIRS = [
    (_EFFECT_TOKENS, "elevation-1", _TIMBERLINE["elevation_1"], "elevation-1/elevation_1"),
    (_EFFECT_TOKENS, "elevation-2", _TIMBERLINE["elevation_2"], "elevation-2/elevation_2"),
    (_EFFECT_TOKENS, "elevation-3", _TIMBERLINE["elevation_3"], "elevation-3/elevation_3"),
    (_EFFECT_TOKENS, "glow-sand", _TIMBERLINE["glow_primary"], "glow-sand/glow_primary"),
    (_EFFECT_TOKENS, "glow-pine", _TIMBERLINE["glow_accent"], "glow-pine/glow_accent"),
]

_TYPE_PAIRS = [
    (_TYPE_TOKENS, "font-display", _TIMBERLINE["font_display"], "font-display/font_display"),
    (_TYPE_TOKENS, "font-body", _TIMBERLINE["font_body"], "font-body/font_body"),
    (_TYPE_TOKENS, "display-weight", _TIMBERLINE["display_weight"], "display-weight/display_weight"),
    (_TYPE_TOKENS, "display-tracking", _TIMBERLINE["display_tracking"], "display-tracking/display_tracking"),
    (_TYPE_TOKENS, "display-leading", _TIMBERLINE["display_leading"], "display-leading/display_leading"),
    (_TYPE_TOKENS, "label-weight", _TIMBERLINE["label_weight"], "label-weight/label_weight"),
]

_SPACE_PAIRS = [
    (_SPACE_TOKENS, "radius", _TIMBERLINE["rounded"], "radius/rounded"),
]

_ALL_PAIRS = _COLOR_PAIRS + _EFFECT_PAIRS + _TYPE_PAIRS + _SPACE_PAIRS


@pytest.mark.parametrize("tokens, token_name, config_value, label", _ALL_PAIRS, ids=[p[3] for p in _ALL_PAIRS])
def test_brand_token_matches_timberline_config(tokens, token_name, config_value, label):
    assert token_name in tokens, f"brand/tokens: no --{token_name} token found for {label}"
    brand_value = tokens[token_name]
    assert _normalize(brand_value) == _normalize(config_value), (
        f"{label}: brand/tokens has --{token_name}: {brand_value!r}, "
        f"THEME_CONFIG[\"TIMBERLINE\"] has {config_value!r}"
    )
