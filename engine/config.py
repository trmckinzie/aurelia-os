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
            "highlight": "#eab308",     # Yellow (Source/Library card identity)
            "info": "#6366f1",          # Indigo (NotebookLM/Research card identity)
            "insight": "#ff2d78",       # Magenta/Rose (Deep Dive card identity)
        },
        "font_mono": "'JetBrains Mono', monospace",
        "rounded": "2px",              # Sharp corners
        "glass_opacity": "0.6",        # Heavy glass
        # Defaults (no override needed): borderless dark-glass cards, the
        # neon horizontal-sweep scanline. See engine/theming.py fallbacks.
    },

    # 2. THE_PATRIOT (Light / Americana). Palette grounded in the U.S. Web
    # Design System (USWDS) -- the federal government's own design system,
    # built and accessibility-tested (Section 508 / WCAG AA) specifically
    # for red/white/blue/gold civic sites. Every color below is a real
    # USWDS token value, not an eyeballed approximation:
    #   ink (text_main), base-dark (text_muted), primary-dark (primary),
    #   primary (accent), secondary-dark (secondary), gold-50 (tertiary),
    #   gold-5/10/30 (backgrounds/border).
    # USWDS's own accessibility docs are explicit that body text should be
    # near-black ("ink"), not a tinted color -- a navy or sepia tint on the
    # *reading* text is exactly the kind of choice that looks thematic but
    # quietly costs contrast. The blue/red/gold identity still comes
    # through clearly via headings, links, borders, and badges.
    "THE_PATRIOT": {
        "label": "The Patriot",
        "description": "Light / Americana",
        "colors": {
            # Base Layer -- warm gold-tinted parchment (USWDS gold-5/10),
            # not neutral gray, but light enough to stay well above AA
            # contrast for every text color below.
            "bg_main": "#f5f0e6",       # USWDS gold-5 -- warm parchment
            "bg_layer_1": "#ffffff",    # Pure White (Cards) -- crisp paper-on-desk
            "bg_layer_2": "#f1e5cd",    # USWDS gold-10 -- hover/modal surface

            # Typography -- near-black ink, not tinted, for maximum
            # readability (see note above).
            "text_main": "#1b1b1b",     # USWDS ink
            "text_muted": "#565c65",    # USWDS base-dark
            "text_inverted": "#ffffff", # White text (for solid buttons)

            # Structure -- a warm gold hairline (USWDS gold-30, chosen dark
            # enough to stay clearly visible as a border, not just a tint).
            "border_main": "#c7a97b",   # USWDS gold-30
            "border_focus": "#005ea2",  # USWDS primary blue (keyboard focus ring)

            # Roles -- USWDS's own theme tokens for exactly these jobs.
            "primary": "#1a4480",       # USWDS primary-dark (Headings, Key Data)
            "secondary": "#b50909",     # USWDS secondary-dark (Alerts, Emphasis)
            "tertiary": "#6b5947",      # USWDS gold-60 -- a full grade past gold-50's AA
                                        # floor, since it's used as small badge/label text
            "accent": "#005ea2",        # USWDS primary -- the standard gov-site link blue
            "highlight": "#8a6416",     # Antique brass/gold (Source/Library card identity) --
                                        # distinct from tertiary's grayer gold-60, dark enough
                                        # for AA text contrast on the parchment background.
            "info": "#2f4b6b",          # Deep navy-slate (NotebookLM/Research card identity) --
                                        # stays in the blue family but reads as its own hue
                                        # next to primary/accent.
            "insight": "#265c35",       # Deep civic green (Deep Dive card identity) -- hand-picked
                                        # in the palette's spirit (a fourth USWDS-family hue, forest
                                        # rather than gold/blue/red) and hand-darkened for AA text
                                        # contrast on parchment; not a cited USWDS token like the
                                        # other six, since none was confirmed at exactly this grade.
        },
        "font_mono": "'Courier Prime', 'Courier New', monospace",  # Typewriter -- founding-document feel
        "rounded": "8px",              # Softer corners
        "glass_opacity": "0.97",       # Solid paper look (less glass)
        # A "dossier card" look instead of CYBER_PRIME's borderless glass --
        # opaque parchment-white with a gold hairline and a soft navy-tinted
        # shadow (rather than flat black, to stay in the blue family).
        "glass_border": "1px solid #c7a97b",
        "glass_shadow": "0 4px 10px -2px rgba(26, 68, 128, 0.12)",
        # Faint gold hairlines -- a paper-texture read instead of a neon
        # sweep-highlight or flat gray grid.
        "scanline_bg": (
            "repeating-linear-gradient(0deg, transparent, transparent 1px, "
            "#c7a97b 1px, #c7a97b 2px)"
        ),
        "scanline_opacity": "0.2",
    },

    # 3. THE_STOA (Light / Stoic Greco-Roman + Swiss). Named for the Stoa
    # Poikile, the painted colonnade in Athens where Zeno of Citium taught --
    # a word that's simultaneously the origin of "Stoic" and a piece of
    # classical architecture (a repeating colonnade reads a lot like a
    # Helvetica grid). The palette is grounded in real pigments/materials of
    # Greco-Roman antiquity rather than eyeballed "ancient-looking" colors:
    # Carrara marble (backgrounds), oxidized bronze statuary (primary),
    # Pompeian/Herculaneum fresco red (secondary), laurel-leaf olive
    # (tertiary), Tyrian imperial purple -- reserved for emperors and senators
    # (accent), gold leaf (highlight), and lapis lazuli pigment (info). The
    # typographic voice is the other half of the brief: Helvetica Neue itself
    # (or its universal system fallback, Arial -- both ship on effectively
    # every OS, so this needs no webfont load), in place of every other
    # theme's monospace "terminal" voice -- cold, rational, grid-precise
    # Swiss lettering standing in for a colonnade's own discipline.
    #
    # 2026-08 contrast pass: the original backgrounds (bg_main #f3f1ea,
    # bg_layer_1 #fbfaf6) sat at 0.88-0.96 relative luminance -- within a
    # hair of paper-white, and bg_layer_1 (the note-reader/code-block
    # surface, i.e. what gets stared at longest) was literally the single
    # brightest color in the theme, lighter than bg_main itself. Every role
    # color did clear its documented >=4.5:1 AA floor against bg_main -- but
    # one pairing (text_muted on bg_layer_2, the blockquote text/background)
    # was still an undetected 4.24:1 AA *failure*, and even the passing
    # pairs landed body text at 15-16.5:1, well past AAA and into
    # eye-straining territory for sustained reading. All three backgrounds
    # were darkened/warmed a notch (still clearly the lightest of the four
    # themes), text_main and text_muted were softened off pure ink-black
    # accordingly, and border_main was darkened slightly for better
    # card/table separation -- landing body text at a still-generous
    # ~9.7-12.3:1 depending on surface, and closing the text_muted/
    # bg_layer_2 gap to 4.76:1. The seven role/identity colors below were
    # re-verified against both new backgrounds and needed no change (all
    # stay >=5:1).
    "THE_STOA": {
        "label": "The Stoa",
        "description": "Stoic / Helvetic",
        "colors": {
            # Base Layer -- Carrara marble, not neutral gray: a warm,
            # faintly stone-toned surface, pulled back from paper-white so
            # the full-height note-reader panel (bg_main) and card/code
            # surface (bg_layer_1, previously the brightest color in the
            # theme) don't read as glare.
            "bg_main": "#e9e4d5",       # Marble -- quarried stone, not paper
            "bg_layer_1": "#f2eee2",    # Polished marble (Cards) -- lightest surface, no longer near-white
            "bg_layer_2": "#dcd5c2",    # Deeper stone (Hovers / Modals)

            # Typography -- dark warm charcoal rather than literal ink-black:
            # keeps the "carved inscription" read without the harshness of
            # pure black on the marble tones above. text_muted was darkened
            # a notch past its prior value to clear an AA failure against
            # bg_layer_2 (blockquotes) that the original hex missed.
            "text_main": "#2e2a22",     # Carved-inscription charcoal
            "text_muted": "#5f594a",    # Weathered stone gray
            "text_inverted": "#ffffff", # White text (for solid buttons)

            # Structure -- a limestone hairline, darkened slightly for
            # clearer card/table separation; the focus ring borrows the
            # accent purple so it reads as unmistakably "select this," not
            # just another structural line.
            "border_main": "#a3987b",   # Limestone
            "border_focus": "#5b3a6b",  # Tyrian purple (keyboard focus ring)

            # Roles -- real antiquity pigments/materials, each hand-darkened
            # for AA text contrast on the marble background.
            "primary": "#6b5228",       # Oxidized bronze (Headings, Key Data)
            "secondary": "#8a3324",     # Pompeian red (Alerts, Emphasis)
            "tertiary": "#5b6b3f",      # Laurel olive (Commerce, Alerts)
            "accent": "#5b3a6b",        # Tyrian imperial purple (Success, Terminal)
            "highlight": "#7a5f1a",     # Gold leaf (Source/Library card identity)
            "info": "#3d5266",          # Lapis lazuli (NotebookLM/Research card identity)
            "insight": "#1f6b5c",       # Verdigris (Deep Dive card identity) -- the blue-green
                                        # patina that forms on oxidized bronze, the same real
                                        # antiquity material primary already draws on
        },
        "font_mono": "'Helvetica Neue', Helvetica, Arial, sans-serif",  # Swiss grid, not typewriter
        "rounded": "1px",              # Almost square -- architectural, not soft
        "glass_opacity": "0.96",       # Solid marble-slab look (like Patriot, unlike CYBER_PRIME's glass)
        # An engraved-tablet look: opaque stone with a limestone hairline
        # and a warm, low, neutral shadow (not colored/glowing) -- marble
        # doesn't glow.
        "glass_border": "1px solid #c7c2b0",
        "glass_shadow": "0 4px 12px -2px rgba(45, 42, 32, 0.14)",
        # Fluted-column lines rather than a neon sweep or paper hairlines --
        # wider-spaced than THE_PATRIOT's texture so the two light themes
        # don't read as the same surface at a glance.
        "scanline_bg": (
            "repeating-linear-gradient(0deg, transparent, transparent 3px, "
            "#c7c2b0 3px, #c7c2b0 4px)"
        ),
        "scanline_opacity": "0.15",
    },

    # 4. GRIZZ (Dark / Collegiate). Adams State University's official
    # Grizzlies colors are just two: green (Pantone 3435 C / #00452A) and
    # white -- confirmed via teamcolorcodes.com and brandcolorcode.com.
    # #00452A itself is print-dark: at ~0.044 relative luminance it manages
    # only ~1.8:1 against a near-black background, nowhere near AA's 4.5:1,
    # because it was never meant to sit on black -- it's a color for print
    # and jerseys, not on-dark UI text. Rather than use it directly and fail
    # the brief's own "extremely readable" requirement, the true brand hex
    # is kept as a decorative anchor (glass_shadow's tint) while every role
    # that doubles as text/link color is a brighter on-dark tint of the same
    # hue, hand-verified >=4.5:1 against bg_main. True to the brief's
    # four-color limit (green, black, white, grey) -- no hue outside that
    # family appears anywhere; card types are told apart by shade/saturation
    # within green and grey rather than by switching hue, the way a team's
    # own gear stays on-brand while still varying (jersey green vs. away
    # white vs. helmet steel).
    #
    # REVISION: the first pass used a near-black (#0a0d0a) just three RGB
    # units off CYBER_PRIME's own (#0a0a0b) -- imperceptible side by side --
    # and reused CYBER_PRIME's own glowing-glass-on-black mechanic (0.6-ish
    # opacity cards, a soft radial sweep-highlight), just recolored. Two dark
    # themes sharing an identical ground plane and the same glow-on-glass
    # visual language will always read as "the same theme, different accent"
    # no matter how carefully the accent hexes differ -- confirmed correct
    # in isolation (contrast, cascade, font-loading all checked out) but the
    # wrong fix, since the actual complaint was that it didn't *feel*
    # distinct. This pass changes the structural language, not just the
    # palette: a genuinely dark forest-green ground plane (not a
    # near-invisible tint), solid opaque panels instead of translucent glass
    # (a jersey/scoreboard panel, not a neon terminal), and a diagonal
    # stripe texture (goal-line paint) in place of the soft glow-sweep every
    # other theme uses.
    "GRIZZ": {
        "label": "Grizz",
        "description": "Dark / Collegiate",
        "colors": {
            # Base Layer -- a genuinely dark FOREST green-black, not a
            # near-neutral near-black: each layer step gets visibly richer
            # as surfaces come closer to the reader (cards, modals), like
            # standing further under stadium lights. Still dark-mode-dark
            # (bg_main's relative luminance is ~0.008, in the same
            # near-black band as every other dark UI) but unmistakably
            # green rather than neutral charcoal.
            "bg_main": "#031a0d",       # Deep forest-black
            "bg_layer_1": "#082414",    # Richer forest (Cards)
            "bg_layer_2": "#0f331d",    # Deepest forest (Hovers / Modals)

            # Typography -- literal white and black, the two non-green
            # brand colors, at maximum contrast against each other and the
            # near-black background.
            "text_main": "#ffffff",     # White text
            "text_muted": "#9aa39d",    # Steel-sage gray -- muted but still
                                        # a comfortable 7:1, since "extremely
                                        # readable" was explicit in the brief
            "text_inverted": "#000000", # Black text (for buttons on bright bgs)

            # Structure -- a genuinely visible forest-steel hairline (not a
            # near-invisible charcoal-on-charcoal line like CYBER_PRIME's
            # deliberately borderless look) -- GRIZZ cards are meant to read
            # as bordered panels, not floating glass. Focus ring borrows the
            # brightest green so it's unmistakable.
            "border_main": "#2f4536",   # Forest-steel border
            "border_focus": "#4ade80",  # Bright kelly green (keyboard focus ring)

            # Roles -- three greens at different intensities (a true
            # grass/kelly "Grizzly Green," a deeper "Pine" for emphasis, and
            # the brightest "Kelly" for success/terminal) plus three grays
            # (a warm Silver, a cool Gunmetal, and Sage -- a green-gray
            # hybrid) so every card type is still visually distinct without
            # ever leaving the green/black/white/grey family. Primary is a
            # true grass green (hue ~132) rather than the first pass's
            # sea-green (hue ~152), which read closer to CYBER_PRIME's own
            # cyan than a team green should.
            "primary": "#22b04c",       # Grizzly Green (Headings, Key Data)
            "secondary": "#1f9a55",     # Deep Pine (Alerts, Emphasis)
            "tertiary": "#b7bab4",      # Silver (Commerce, Alerts)
            "accent": "#4ade80",        # Bright Kelly (Success, Terminal)
            "highlight": "#8a9089",     # Gunmetal (Source/Library card identity)
            "info": "#7c9484",          # Sage (NotebookLM/Research card identity)
            "insight": "#3fae82",       # Teal-spruce (Deep Dive card identity) -- a fourth green,
                                        # shifted bluer (hue ~160) than primary/secondary/accent's
                                        # yellow-greens (hue ~132-152) so it reads as distinct while
                                        # staying inside the brief's green/black/white/grey family
        },
        "font_mono": "'Oswald', 'Arial Narrow', sans-serif",  # Condensed collegiate/scoreboard voice
        "rounded": "6px",              # Clean, structured -- a jersey number plate, not a terminal or a tablet
        "glass_opacity": "0.92",       # Solid panel -- a painted jersey surface, not translucent glass
        "glass_border": "1px solid #2f4536",
        # The one place the *true* brand hex (#00452A) appears directly --
        # a wide, visible shadow tinted with the real Pantone 3435 C rather
        # than a generic black, so cards read as "green-lit" even before
        # you notice any green text.
        "glass_shadow": "0 6px 24px -4px rgba(0, 69, 42, 0.5)",
        # Diagonal stripe texture -- goal-line/end-zone paint -- instead of
        # every other theme's soft radial glow-sweep. Same moving band
        # (main.css's shared .scanline mechanic), completely different
        # material: a structured stripe passing through, not a glow.
        "scanline_bg": (
            "repeating-linear-gradient(135deg, transparent, transparent 8px, "
            "rgba(34, 176, 76, 0.4) 8px, rgba(34, 176, 76, 0.4) 16px)"
        ),
        "scanline_opacity": "0.15",
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
