"""Generates the runtime-switchable theme stylesheet from THEME_CONFIG.

One :root[data-theme="<slug>"] block per theme, each defining the full set
of --aurelia-* custom properties, plus a bare :root block mirroring the
default theme (CURRENT_THEME) so the very first paint -- before the nav's
theme-switcher init script runs -- already has real values instead of
flashing unstyled.

Everything that used to be baked into HTML/JS at build time (a template's
{{ theme.colors.primary }}, tailwind.config.js's literal hex, even the
custom cursor's hardcoded SVG colors) now resolves through one of these
variables instead, so switching themes at runtime is a pure CSS swap --
no rebuild, and nothing left hardcoded to one theme.
"""
import os

from engine.config import CURRENT_THEME, OUTPUT_DIR, THEME_CONFIG

_COLOR_KEYS = [
    "bg_main", "bg_layer_1", "bg_layer_2",
    "text_main", "text_muted", "text_inverted",
    "border_main", "border_focus",
    "primary", "secondary", "tertiary", "accent",
    "highlight", "info", "insight",
]

# Optional per-theme keys and what applies when a theme omits them -- see
# THEME_CONFIG's own docstring-comment for the reasoning: a new theme only
# has to define what makes it actually different.
_DEFAULTS = {
    "font_mono": "'JetBrains Mono', monospace",
    "font_body": "'Inter', sans-serif",
    "display_weight": "800",
    "display_tracking": "-0.03em",
    "display_leading": "0.95",
    "label_weight": "700",
    "halo": "50%",
    "rounded": "2px",
    "glass_opacity": "0.6",
    "glass_border": "none",
    # A no-op shadow rather than the keyword `none`, because .glass now
    # *composes* this on top of the depth system's rim-light and elevation
    # (see main.css). `none` is only legal as a box-shadow's sole value --
    # `box-shadow: <rim>, <elevation>, none` is invalid CSS and would
    # silently drop the whole declaration, taking the elevation with it.
    "glass_shadow": "0 0 0 0 transparent",
    "scanline_bg": "linear-gradient(0deg, rgba(0, 0, 0, 0) 0%, rgba(255, 255, 255, 0.02) 50%, rgba(0, 0, 0, 0) 100%)",
    "scanline_opacity": "0.1",
}

# --- DEPTH SYSTEM -------------------------------------------------------
# The surface/elevation/glow/grid tokens below are what give a theme actual
# depth instead of flat color-on-color. They are deliberately NOT in
# _COLOR_KEYS: that list is mandatory for every theme, which is why adding
# the `insight` role rippled through four theme dicts plus this file,
# tailwind_build.py, and gardentemplate.html. These are optional and
# *derived* from each theme's own palette instead -- the same approach
# _cursor_default()/_cursor_interactive() below already use.
#
# Net effect: every theme gets a coherent depth treatment for free, built
# from its own colors, and a theme that wants a hand-tuned one just sets
# the key (see CYBER_PRIME in config.py). Nothing has to be defined twice,
# and adding a 5th theme still requires nothing here.
#
# `_derived_*` functions each take the theme's `colors` dict and return a
# finished CSS value.


def _lum(hex_color):
    r, g, b = _hex_channels(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _lit_gradient(a, b):
    """A 160deg gradient between two surface colors with the lighter one
    always at the top, so the panel reads as lit from above on every theme.
    Ordering by luminance rather than by key matters because the layers
    invert between dark and light themes: on CYBER_PRIME layer_2 is the
    brighter of the pair, on THE_PATRIOT it's the darker one."""
    top, bottom = (a, b) if _lum(a) >= _lum(b) else (b, a)
    return f"linear-gradient(160deg, {top} 0%, {bottom} 100%)"


def _derived_surface_1(colors):
    """Card/panel surface: a subtle directional lift across the theme's two
    layer colors, so a panel reads as a lit surface rather than a flat fill."""
    return _lit_gradient(colors["bg_layer_2"], colors["bg_layer_1"])


def _derived_surface_2(colors):
    """Raised surface (modals, popovers, hovered rows) -- sits one step off
    the page background so stacked elements stay distinguishable."""
    return _lit_gradient(colors["bg_layer_2"], colors["bg_layer_2"])


def _is_dark(hex_color):
    """Relative luminance test (ITU-R BT.601 weighting, good enough for a
    light-vs-dark decision). Used to pick a shadow color: a shadow has to be
    darker than the surface it falls on, and deriving one from bg_main works
    only on dark themes -- on THE_PATRIOT that produced a parchment-colored
    'shadow' lighter than the card casting it."""
    r, g, b = _hex_channels(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


def _derived_elevation(colors, level):
    """A 3-step shadow ladder. The shadow color is always the darker end of
    the theme -- its background on a dark theme, its ink on a light one --
    so the ladder reads as depth in both. Level 3 adds a faint primary-tinted
    bloom: the 'light' half of the depth system, which is what actually
    separates a surface from a near-black page where a black shadow is
    invisible."""
    depth = {1: (4, 10, 0.30), 2: (10, 26, 0.55), 3: (22, 48, 0.75)}[level]
    y, blur, alpha = depth
    shade = colors["bg_main"] if _is_dark(colors["bg_main"]) else colors["text_main"]
    shadow = f"0 {y}px {blur}px -{max(y // 2, 2)}px {_hex_to_rgba(shade, alpha)}"
    if level == 3:
        shadow += f", 0 0 {blur}px -{blur // 3}px {_hex_to_rgba(colors['primary'], 0.35)}"
    return shadow


def _derived_rim_light(colors):
    """A 1px inset highlight along a surface's top edge -- the single
    cheapest cue that a panel is a physical object catching light. Keyed to
    the theme's primary so it reads as the theme's own light source."""
    return f"inset 0 1px 0 0 {_hex_to_rgba(colors['primary'], 0.18)}"


def _derived_glow(colors, role):
    """A radial bloom used behind hero elements and on card hover. Returns a
    full background-image value so it can be dropped straight onto a
    pseudo-element."""
    return f"radial-gradient(circle, {_hex_to_rgba(colors[role], 0.35)} 0%, transparent 70%)"


def _derived_grid_overlay(colors):
    """The HUD grid. Two hairline gradients at the theme's primary, faint
    enough to read as texture rather than as content."""
    line = _hex_to_rgba(colors["primary"], 0.05)
    return (f"linear-gradient({line} 1px, transparent 1px), "
            f"linear-gradient(90deg, {line} 1px, transparent 1px)")


_DERIVED = {
    "surface_1": _derived_surface_1,
    "surface_2": _derived_surface_2,
    "elevation_1": lambda c: _derived_elevation(c, 1),
    "elevation_2": lambda c: _derived_elevation(c, 2),
    "elevation_3": lambda c: _derived_elevation(c, 3),
    "rim_light": _derived_rim_light,
    "glow_primary": lambda c: _derived_glow(c, "primary"),
    "glow_accent": lambda c: _derived_glow(c, "accent"),
    "grid_overlay": _derived_grid_overlay,
}


def theme_slug(key):
    """'CYBER_PRIME' -> 'cyber-prime'. The data-theme attribute value and
    CSS selector suffix -- used identically in Python, generated CSS, and
    the switcher's embedded JS payload so none of them can drift apart."""
    return key.lower().replace("_", "-")


def _hex_channels(hex_color):
    hex_color = hex_color.lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _hex_to_rgba(hex_color, alpha):
    r, g, b = _hex_channels(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _hex_to_rgb_triple(hex_color):
    """'#00f2ff' -> '0 242 255' -- Tailwind's documented pattern for a
    CSS-variable-backed color that still supports the /opacity modifier
    (bg-aurelia-primary/10) is `rgb(var(--x-rgb) / <alpha-value>)`, which
    needs the channels as bare numbers, not a hex string or a pre-built
    rgb()/var() value. Without this, Tailwind can't decompose the color to
    apply an alpha and silently omits the opacity-modifier class entirely
    -- bg-aurelia-primary/10 would compile to nothing at all."""
    r, g, b = _hex_channels(hex_color)
    return f"{r} {g} {b}"


def _cursor_default(colors):
    """The default arrow cursor, filled with this theme's own bg (so it
    reads as a translucent shape against a same-toned page) and outlined
    in its primary color -- previously a CYBER_PRIME-only hardcoded SVG
    that stayed cyan-on-black regardless of the active theme."""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'>"
        f"<path d='M2 2l8.8 20.4 2.8-8.4 8.4-2.8L2 2z' fill='{colors['bg_main']}' fill-opacity='0.5' "
        f"stroke='{colors['primary']}' stroke-width='1.5' stroke-linejoin='round'/></svg>"
    ).replace("#", "%23")
    return f'url("data:image/svg+xml,{svg}"), auto'


def _cursor_interactive(colors):
    """The interactive target-reticle cursor, keyed to this theme's accent."""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'>"
        f"<circle cx='12' cy='12' r='9' fill='none' stroke='{colors['accent']}' stroke-width='1.5'/>"
        f"<circle cx='12' cy='12' r='2' fill='{colors['accent']}'/>"
        f"<path d='M12 2v4M12 18v4M2 12h4M18 12h4' stroke='{colors['accent']}' stroke-width='1.5'/></svg>"
    ).replace("#", "%23")
    return f'url("data:image/svg+xml,{svg}") 12 12, pointer'


def _variables_for(theme):
    """Builds the {css-custom-property-name: value} map for one theme."""
    colors = theme["colors"]
    variables = {f"--aurelia-{key.replace('_', '-')}": colors[key] for key in _COLOR_KEYS}
    # RGB-channel twins of the same colors, for Tailwind's opacity-modifier
    # utilities (see _hex_to_rgb_triple) -- the plain hex versions above are
    # still what direct var(--aurelia-x) references in template <style>
    # blocks use.
    for key in _COLOR_KEYS:
        variables[f"--aurelia-{key.replace('_', '-')}-rgb"] = _hex_to_rgb_triple(colors[key])

    font_mono = theme.get("font_mono", _DEFAULTS["font_mono"])
    variables["--aurelia-font-mono"] = font_mono
    # The display face defaults to the theme's own mono -- "mono-first
    # headings" is the house style, and a theme that wants an actual display
    # family (a condensed poster face, a serif) just sets font_display.
    variables["--aurelia-font-display"] = theme.get("font_display", font_mono)
    # The body/paragraph face. Independent of font_mono/font_display: the
    # house style up to TIMBERLINE hard-coded 'Inter' as the body sans
    # everywhere (base.html's <body> gets Tailwind's font-sans, which used
    # to be a literal ['Inter', 'sans-serif'] in tailwind_build.py) so every
    # theme's prose rendered in the same face regardless of its own voice.
    # Defaulting this to 'Inter' keeps that exact behavior for every theme
    # that doesn't set it -- only a theme with an actual editorial brief
    # (see TIMBERLINE in config.py) overrides it.
    variables["--aurelia-font-body"] = theme.get("font_body", _DEFAULTS["font_body"])
    # Headings *inside a note* (the Garden's .obsidian-reader). They used
    # to simply inherit the reader's body face; that stays the default so
    # no existing theme changes, but an editorial theme can point them at
    # its serif display face without dragging the site chrome's mono-first
    # .display-* headings along with it.
    variables["--aurelia-font-reader-heading"] = theme.get(
        "font_reader_heading", variables["--aurelia-font-body"])
    variables["--aurelia-radius"] = theme.get("rounded", _DEFAULTS["rounded"])

    # Display-heading type tuning (weight/tracking/leading) and the shared
    # label weight (.field-label/.btn/.chip). Defaults reproduce main.css's
    # former hard-coded values exactly (800 / -0.03em / 0.95 / 700), so every
    # existing theme renders byte-for-byte the same as before these became
    # theme-driven -- only a theme that sets them (see TIMBERLINE) departs
    # from the "heavy mono-first" house voice.
    variables["--aurelia-display-weight"] = theme.get("display_weight", _DEFAULTS["display_weight"])
    variables["--aurelia-display-tracking"] = theme.get("display_tracking", _DEFAULTS["display_tracking"])
    variables["--aurelia-display-leading"] = theme.get("display_leading", _DEFAULTS["display_leading"])
    variables["--aurelia-label-weight"] = theme.get("label_weight", _DEFAULTS["label_weight"])

    # Strength of text-shadow halos (main.css's .text-shadow-cyan) as a
    # color-mix() percentage. Defaults to the previous hard-coded 50%; a
    # theme going for a hairline/print register (TIMBERLINE) sets this to
    # "0%" to turn the glow off entirely rather than just dimming it.
    variables["--aurelia-halo"] = theme.get("halo", _DEFAULTS["halo"])

    # Depth system -- a theme's own value wins, otherwise it's derived from
    # that theme's palette (see _DERIVED above).
    for key, derive in _DERIVED.items():
        variables[f"--aurelia-{key.replace('_', '-')}"] = theme.get(key, derive(colors))
    variables["--aurelia-grid-size"] = theme.get("grid_size", "40px")

    glass_opacity = theme.get("glass_opacity", _DEFAULTS["glass_opacity"])
    variables["--aurelia-glass-bg"] = _hex_to_rgba(colors["bg_main"], glass_opacity)
    variables["--aurelia-glass-border"] = theme.get("glass_border", _DEFAULTS["glass_border"])
    variables["--aurelia-glass-shadow"] = theme.get("glass_shadow", _DEFAULTS["glass_shadow"])

    variables["--aurelia-scanline-bg"] = theme.get("scanline_bg", _DEFAULTS["scanline_bg"])
    variables["--aurelia-scanline-opacity"] = theme.get("scanline_opacity", _DEFAULTS["scanline_opacity"])

    # Theme-overridable the same way the depth-system keys above are: a
    # theme's own value wins, otherwise it's derived from that theme's
    # palette. A professional theme (see TIMBERLINE in config.py) sets
    # these to the plain CSS keywords "auto"/"pointer" to opt out of the
    # custom SVG arrow/reticle cursors entirely -- a tactical-HUD cursor
    # reads as novelty rather than polish on a CV-adjacent page.
    variables["--aurelia-cursor-default"] = theme.get("cursor_default", _cursor_default(colors))
    variables["--aurelia-cursor-interactive"] = theme.get("cursor_interactive", _cursor_interactive(colors))

    return variables


def _block(selector, variables):
    lines = "\n".join(f"    {name}: {value};" for name, value in variables.items())
    return f"{selector} {{\n{lines}\n}}"


def generate_theme_css():
    """Writes dist/assets/css/theme-vars.css: a bare :root block (the
    default theme, for pre-JS first paint) plus one :root[data-theme="x"]
    block per THEME_CONFIG entry. Returns the output path.
    """
    blocks = [
        "/* AUTO-GENERATED by engine/theming.py from engine/config.py THEME_CONFIG.",
        " * Do not edit by hand -- add or edit a theme there and rebuild instead. */",
        _block(":root", _variables_for(CURRENT_THEME)),
    ]
    for key, theme in THEME_CONFIG.items():
        blocks.append(_block(f':root[data-theme="{theme_slug(key)}"]', _variables_for(theme)))

    css_dir = os.path.join(OUTPUT_DIR, "assets", "css")
    os.makedirs(css_dir, exist_ok=True)
    output_path = os.path.join(css_dir, "theme-vars.css")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + "\n")
    return output_path


def default_theme_slug():
    """The slug for CURRENT_THEME (config.py's default-theme selection) --
    stamped onto <html data-theme="..."> at build time so the page renders
    correctly before the switcher's init script (which may override it
    from localStorage) has run."""
    for key, theme in THEME_CONFIG.items():
        if theme is CURRENT_THEME:
            return theme_slug(key)
    return theme_slug(next(iter(THEME_CONFIG)))


def available_themes():
    """[{key, label, description, colors}, ...] for the switcher UI and its
    embedded JS payload -- 'colors' is a small swatch preview, not the full
    palette, to keep that payload light."""
    return [
        {
            "key": theme_slug(key),
            "label": theme.get("label", key.replace("_", " ").title()),
            "description": theme.get("description", ""),
            "swatch": {
                "bg": theme["colors"]["bg_main"],
                "primary": theme["colors"]["primary"],
                "secondary": theme["colors"]["secondary"],
                "accent": theme["colors"]["accent"],
            },
        }
        for key, theme in THEME_CONFIG.items()
    ]
