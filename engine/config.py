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

    # 2. THE_PATRIOT (Light / Academic / CIA Dossier Style)
    "THE_PATRIOT": {
        "label": "The Patriot",
        "description": "Light / Academic",
        "colors": {
            # Base Layer
            "bg_main": "#fdfbf7",       # Warm Paper White
            "bg_layer_1": "#ffffff",    # Pure White (Cards)
            "bg_layer_2": "#f3f4f6",    # Light Gray (Hovers)

            # Typography
            "text_main": "#111827",     # Deep Black/Blue (Ink)
            "text_muted": "#4b5563",    # Gray
            "text_inverted": "#ffffff", # White text (for solid buttons)

            # Structure
            "border_main": "#e5e7eb",   # Light Gray Borders
            "border_focus": "#1d4ed8",  # Navy Focus (keyboard focus ring)

            # Roles
            "primary": "#1e3a8a",       # Navy Blue (Headings - Authority)
            "secondary": "#dc2626",     # Crimson Red (Alerts - Action)
            "tertiary": "#b45309",      # Amber/Gold (Highlights)
            "accent": "#2563eb",        # Royal Blue (Links)
        },
        "font_mono": "'Courier Prime', 'Courier New', monospace",  # Typewriter style
        "rounded": "8px",              # Softer corners
        "glass_opacity": "0.95",       # Solid paper look (less glass)
        # A "dossier card" look instead of CYBER_PRIME's borderless glass --
        # opaque white with a hairline border and a soft drop shadow.
        "glass_border": "1px solid #e5e7eb",
        "glass_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
        # Faint gray hairlines instead of a neon sweep-highlight.
        "scanline_bg": (
            "repeating-linear-gradient(0deg, transparent, transparent 1px, "
            "#e5e7eb 1px, #e5e7eb 2px)"
        ),
        "scanline_opacity": "0.3",
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
