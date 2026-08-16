"""Paths, theme presets, and user_config.json loading."""
import json
import os

from jinja2 import Environment, FileSystemLoader

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system", "templates")
PROTOCOL_PATH = os.path.join(VAULT_PATH, "20_PROTOCOL")
OUTPUT_DIR = os.path.join(ROOT_DIR, "dist")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- THEME ENGINE V2.1 (FULL SEMANTIC) ---
THEME_CONFIG = {
    # 1. CYBER_PRIME (Dark / Neon)
    "CYBER_PRIME": {
        "name": "CYBER_PRIME",
        "colors": {
            # Base Layer
            "bg_main": "'#0a0a0b'",       # Deepest Black
            "bg_layer_1": "'#121214'",    # Slightly Lighter (Cards)
            "bg_layer_2": "'#18181b'",    # Hovers / Modals

            # Typography
            "text_main": "'#ffffff'",     # White text
            "text_muted": "'#9ca3af'",    # Gray text
            "text_inverted": "'#000000'", # Black text (for buttons on bright bgs)

            # Structure
            "border_main": "'#27272a'",   # Dark Gray Borders
            "border_focus": "'#00f2ff'",  # Cyan Focus

            # Roles
            "primary": "'#00f2ff'",       # Cyan (Headings, Key Data)
            "secondary": "'#8a2be2'",     # Purple (Creative, Portfolio)
            "tertiary": "'#ff8c00'",      # Orange (Commerce, Alerts)
            "accent": "'#39ff14'",        # Green (Success, Terminal)
        },
        "font_mono": "'JetBrains Mono', 'monospace'",
        "rounded": "'2px'",               # Sharp corners
        "glass_opacity": "'0.6'"          # Heavy glass
    },

    # 2. THE_PATRIOT (Light / Academic / CIA Dossier Style)
    "THE_PATRIOT": {
        "name": "THE_PATRIOT",
        "colors": {
            # Base Layer
            "bg_main": "'#fdfbf7'",       # Warm Paper White
            "bg_layer_1": "'#ffffff'",    # Pure White (Cards)
            "bg_layer_2": "'#f3f4f6'",    # Light Gray (Hovers)

            # Typography
            "text_main": "'#111827'",     # Deep Black/Blue (Ink)
            "text_muted": "'#4b5563'",    # Gray
            "text_inverted": "'#ffffff'", # White text (for solid buttons)

            # Structure
            "border_main": "'#e5e7eb'",   # Light Gray Borders
            "border_focus": "'#1d4ed8'",  # Navy Focus

            # Roles
            "primary": "'#1e3a8a'",       # Navy Blue (Headings - Authority)
            "secondary": "'#dc2626'",     # Crimson Red (Alerts - Action)
            "tertiary": "'#b45309'",      # Amber/Gold (Highlights)
            "accent": "'#2563eb'",        # Royal Blue (Links)
        },
        "font_mono": "'Courier Prime', 'Courier New', monospace",  # Typewriter style
        "rounded": "'8px'",               # Softer corners
        "glass_opacity": "'0.95'"         # Solid paper look (less glass)
    },
}

# Change to THEME_CONFIG["THE_PATRIOT"] to switch themes.
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
        return {"author": {"name": "Unknown User"}, "modules": {}}
