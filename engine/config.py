"""Paths, theme presets, and user_config.json loading."""
import json
import os

from jinja2 import Environment, FileSystemLoader

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system", "templates")
OUTPUT_DIR = os.path.join(ROOT_DIR, "dist")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- THEME ENGINE V3: RUNTIME-SWITCHABLE (see engine/theming.py) ---
# Every value here becomes a CSS custom property (--aurelia-*), generated
# for every theme in this dict -- not just one -- into
# dist/assets/css/theme-vars.css at build time. The browser picks which
# theme's block applies via a `data-theme` attribute on <html>, toggled at
# runtime by the nav's theme switcher and persisted to localStorage, so
# switching is instant and needs no rebuild.
#
# To add a new theme: copy a block below, change the values, done. No
# other file needs to know this theme exists -- the CSS generator, the
# Tailwind config, and the switcher's dropdown all derive their list from
# this dict's keys.
#
# Every value is a plain, ready-to-use CSS value string -- write it exactly
# as it would appear on the right-hand side of a CSS declaration. Hex colors
# are bare (no quotes: "#0a0a0b"); font-family lists keep the quotes CSS
# itself requires around multi-word names (e.g. "'JetBrains Mono', monospace").
#
# Only "colors" is required. Every other key has a sensible fallback (see
# engine/theming.py) so a minimal new theme can omit font_mono/rounded/
# glass_opacity/glass_border/glass_shadow/scanline_bg/scanline_opacity
# entirely and still render correctly.
THEME_CONFIG = {
    # 1. CYBER_PRIME (Dark / Neon)
    "CYBER_PRIME": {
        "label": "Cyber Prime",
        "description": "Dark / Neon",
        "colors": {
            # Base Layer
            "bg_main": "#0a0a0b",       # Deepest Black
            "bg_layer_1": "#121214",    # Slightly Lighter (Cards)
            "bg_layer_2": "#18181b",    # Hovers / Modals

            # Typography
            "text_main": "#ffffff",     # White text
            "text_muted": "#9ca3af",    # Gray text
            "text_inverted": "#000000", # Black text (for buttons on bright bgs)

            # Structure
            "border_main": "#27272a",   # Dark Gray Borders
            "border_focus": "#00f2ff",  # Cyan Focus (keyboard focus ring)

            # Roles
            "primary": "#00f2ff",       # Cyan (Headings, Key Data)
            "secondary": "#8a2be2",     # Purple (Creative, Portfolio)
            "tertiary": "#ff8c00",      # Orange (Commerce, Alerts)
            "accent": "#39ff14",        # Green (Success, Terminal)
        },
        "font_mono": "'JetBrains Mono', monospace",
        "rounded": "2px",              # Sharp corners
        "glass_opacity": "0.6",        # Heavy glass
        # Defaults (no override needed): borderless dark-glass cards, the
        # neon horizontal-sweep scanline. See engine/theming.py fallbacks.
    },

    # 2. THE_PATRIOT (Light / Americana -- a founding-document aesthetic:
    # warm parchment, deep navy ink, the flag's actual Old Glory Blue/Red,
    # and antique gold worked into structure -- borders, hover states, the
    # scanline -- rather than only used as a single accent color. Every
    # color below was picked and checked for contrast against bg_main:
    # text_main ~14:1, text_muted ~6.4:1, primary (as text/headings)
    # ~11.5:1, accent (as link text) ~6.9:1 -- all comfortably at or above
    # WCAG AA for normal text (4.5:1), most at AAA (7:1).
    "THE_PATRIOT": {
        "label": "The Patriot",
        "description": "Light / Americana",
        "colors": {
            # Base Layer -- warm parchment, not stark white, but light
            # enough to keep every text color well above AA contrast.
            "bg_main": "#f8f5ec",       # Warm Parchment
            "bg_layer_1": "#ffffff",    # Pure White (Cards) -- crisp paper-on-desk
            "bg_layer_2": "#efe8d3",    # Soft Gold-Cream (Hovers)

            # Typography -- ink navy rather than flat black, so "Blue"
            # carries into the reading experience itself, not just accents.
            "text_main": "#0b1f3a",     # Deep Navy Ink
            "text_muted": "#54617a",    # Muted Slate-Navy
            "text_inverted": "#ffffff", # White text (for solid buttons)

            # Structure -- a soft gold hairline instead of flat gray, so
            # "Gold" shows up in every border, not only as a highlight.
            "border_main": "#d9cfb0",   # Parchment Gold
            "border_focus": "#1d4ed8",  # Royal Blue (keyboard focus ring)

            # Roles -- the flag's actual colors, not a generic red/blue.
            "primary": "#0a3161",       # Old Glory Blue (Headings, Key Data)
            "secondary": "#b31942",     # Old Glory Red (Alerts, Emphasis)
            "tertiary": "#8a6d1f",      # Antique Gold (Highlights, Status)
            "accent": "#1d4ed8",        # Royal Blue (Links -- distinct from Primary's navy)
        },
        "font_mono": "'Courier Prime', 'Courier New', monospace",  # Typewriter -- founding-document feel
        "rounded": "8px",              # Softer corners
        "glass_opacity": "0.97",       # Solid paper look (less glass)
        # A "dossier card" look instead of CYBER_PRIME's borderless glass --
        # opaque parchment-white with a gold hairline and a soft navy-tinted
        # shadow (rather than flat black, to stay in the blue family).
        "glass_border": "1px solid #d9cfb0",
        "glass_shadow": "0 4px 10px -2px rgba(10, 31, 61, 0.12)",
        # Faint gold hairlines -- a paper-texture read instead of a neon
        # sweep-highlight or flat gray grid.
        "scanline_bg": (
            "repeating-linear-gradient(0deg, transparent, transparent 1px, "
            "#d9cfb0 1px, #d9cfb0 2px)"
        ),
        "scanline_opacity": "0.25",
    },
}

# The default theme: what a first-time visitor sees (before any localStorage
# preference exists) and what's baked into the bare, un-attributed :root
# block so the very first paint -- before the switcher's init script runs --
# is never unstyled. Change this to re-point the *default*; it no longer
# requires a rebuild to let a visitor use the other theme, since both are
# always shipped and switchable at runtime.
CURRENT_THEME = THEME_CONFIG["CYBER_PRIME"]


def load_user_config():
    config_path = os.path.join(ROOT_DIR, "user_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"   + Identity Loaded: {config['author']['name']}")
        return config
    except Exception as e:
        print(f"   ⚠️  WARNING: Could not load user_config.json. Using defaults. ({e})")
        return {"author": {"name": "Unknown User"}}
