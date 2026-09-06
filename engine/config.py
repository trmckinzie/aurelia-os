"""Paths, theme presets, and user_config.json loading."""
import json
import os

from jinja2 import Environment, FileSystemLoader

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system", "templates")
OUTPUT_DIR = os.path.join(ROOT_DIR, "dist")

# autoescape=True, not Jinja's default of False (audit finding #21). With it
# off, every {{ }} in every template emitted raw HTML, so any vault-derived
# value -- a note title, a tag, a frontmatter field -- reaching a template
# was an injection sink, and the `|safe` filters dotted around the templates
# were opting out of nothing.
#
# It is unconditional rather than select_autoescape(): every template here is
# HTML, and a future non-HTML one should have to opt out deliberately rather
# than inherit "unescaped" from a filename extension.
#
# The two things that legitimately must stay raw now say so at the point they
# are produced, which is the honest place for it:
#   - engine/cards.py's generate_garden_card_html() returns Markup
#   - engine/textutils.py's dumps_for_script_tag() returns Markup
# Note-derived HTML (a note's rendered body) is neither: it is sanitized
# through engine/sanitize.py before it is marked safe.
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

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
# entirely and still render correctly. Two more are overridable the same
# way for the same reason: cursor_default/cursor_interactive normally
# derive an SVG cursor (arrow / target-reticle) from the theme's own
# colors, but a theme aiming at plain professional UI -- see TIMBERLINE --
# can set them to the literal CSS keywords "auto"/"pointer" to opt out of
# the custom cursors entirely.
#
# Six more govern the *type register* rather than color/shape, added for
# TIMBERLINE's editorial brief and all optional with defaults that
# reproduce the previous hard-coded behavior exactly, so every other theme
# is unaffected:
#   - font_body ("--aurelia-font-body", default "'Inter', sans-serif"):
#     the body/paragraph face read by Tailwind's font-sans (see
#     tailwind_build.py). Independent of font_mono/font_display -- a theme
#     can go serif-display + grotesque-body (TIMBERLINE) without touching
#     the mono/display faces at all.
#   - display_weight / display_tracking / display_leading
#     ("--aurelia-display-weight/-tracking/-leading", defaults "800" /
#     "-0.03em" / "0.95"): the .display-xl/-lg/-md heading rules in
#     main.css. Defaults are exactly what those rules used to hard-code, so
#     a theme that omits these renders byte-for-byte identical headings to
#     before this became theme-driven.
#   - label_weight ("--aurelia-label-weight", default "700"): shared by
#     .field-label/.btn/.chip in main.css (all were hard-coded to 700).
#     Deliberately not read by .chip-static, which stays at a fixed 500
#     regardless of theme -- see that rule's own comment in main.css.
#   - halo ("--aurelia-halo", default "50%"): the color-mix() percentage
#     behind main.css's .text-shadow-cyan glow. A theme going for a flat,
#     hairline-and-paper register instead of a glowing one (TIMBERLINE)
#     sets this to "0%" to turn the halo off rather than just dimming it.
THEME_CONFIG = {
    # 1. TIMBERLINE (Light / Editorial). The default (2026-09 rebrand).
    # Palette derived from Rocky Mountain Automation AI's live brand tokens
    # (measured off rockymountainautomationai.com's own CSS): black
    # #000000, signal orange #f04800, sand #f2c898, deep indigo #24214c,
    # rust #7a2a0a, slate ink #1a2a33. The palette is unchanged from the
    # theme's first pass; what changed in this pass is the *type register*
    # sitting on top of it.
    #
    # The brief: "Helvetica + Times New Roman" -- a book-jacket or quality-
    # broadsheet register, not a HUD, and not the same "clean grotesque
    # headings" look the first pass reached for by pointing font_display at
    # the body sans. A serif display face (font_display) now carries the
    # headings and a grotesque (font_body/font_mono) carries everything
    # else -- prose, field labels, buttons, chips, even code, the same
    # trade THE_STOA already makes and documents the cost of (code blocks
    # inherit the humanist face too; accepted there for the same reason
    # here). font_display is 'Cormorant Garamond' -- the Garamond-family
    # face actually available on Google Fonts -- falling back to 'Times New
    # Roman', Times, serif: a *named*, deliberate fallback matching the
    # brief's own "Times New Roman" half, not an accidental generic-serif
    # default. This is also why every existing theme needed the six new
    # display/label/halo keys documented above added before this pass could
    # happen at all -- until now, font_body didn't exist and
    # display_weight/tracking/leading/label_weight/halo were hard-coded in
    # main.css and tailwind_build.py, so no theme (light or dark) could
    # actually depart from "heavy mono-first, glowing" without editing
    # shared CSS.
    #
    # The depth system follows the same brief: rounded is "0px" (a
    # typeset page has square corners, not app-UI curves), glass_opacity is
    # "1" (fully opaque -- paper, not glass), elevation_1 is a hairline
    # (rgba(214, 204, 186, 0.55)) rather than a shadow, and halo is "0%" --
    # the glowing text-shadow every other theme uses reads as HUD/neon, and
    # an editorial page separates elements with rules and whitespace, not
    # light. glow_primary is kept (a theme with a `primary` role still needs
    # one, since it's referenced unconditionally elsewhere), but it's
    # retuned to a soft sand-tint bloom rather than a saturated color, since
    # the brief calls the brand's sand tint "the light source" and reserves
    # true orange for emphasis text only.
    #
    # Professional first, brand-inspired second -- unchanged from the first
    # pass. The true brand orange (#f04800) is a striking accent but fails
    # AA as *text* on any of this theme's light backgrounds -- 3.39:1
    # against bg_main, nowhere near the 4.5:1 floor, because it was
    # designed to pop on black (RMAAI's own site), not to sit on paper.
    # Rather than eyeball a lighter background or quietly drop the brand
    # color, the trap is handled the same way GRIZZ handles its own
    # print-dark brand green (#00452A, ~1.8:1 on black): the true hex is
    # kept as a purely decorative anchor -- glow_primary's radial bloom is
    # the one place rgba(240, 72, 0, ...) appears -- while every role that
    # doubles as text/link color is a hand-darkened on-light tint of the
    # same hue family (secondary #b93700, tertiary #7a2a0a -- rust is
    # itself a true, unmodified brand hex and clears AA on its own at
    # 8.83:1). The backgrounds were re-tuned this pass toward a warmer,
    # more ivory paper (bg_main #f5f2eb, bg_layer_2 #eae5da -- a visibly
    # deeper sand hairline than the first pass's cooler off-white) to read
    # less like app chrome and more like stock; every text-bearing role was
    # re-verified against all three backgrounds (bg_main, bg_layer_1,
    # bg_layer_2) after that change: the tightest pairing is secondary on
    # bg_layer_2 at 4.63:1, everything else clears with more room, and body
    # text (text_main) runs comfortably past that on every surface.
    #
    # This is also why it's first in the dict (switcher order) and why
    # CURRENT_THEME points here: the "Aurelia"/terminal-neon framing is
    # being retired in favor of a professional portfolio site (see
    # CLAUDE.md's rebrand notes), and a light, quiet, CV-appropriate theme
    # is what a first-time visitor should land on now. The custom SVG
    # cursors (arrow/reticle) are switched off via cursor_default/
    # cursor_interactive below -- a "tactical HUD" cursor reads as playful
    # novelty on a résumé-adjacent page, not as polish -- which is also why
    # scanline_bg/grid_overlay are both "none" (this is the first theme
    # with no atmosphere-texture overlay at all, another explicit inverse
    # of the design each other theme opts into).
    "TIMBERLINE": {
        "label": "Timberline",
        "description": "Light / Editorial",
        "colors": {
            "bg_main": "#f5f2eb",       # ivory paper
            "bg_layer_1": "#fdfcf9",    # cards -- barely lifted off the page
            "bg_layer_2": "#eae5da",    # hovers / modals -- sand hairline territory

            "text_main": "#1a2a33",     # RMAAI's own body ink (slate)
            "text_muted": "#4d5a63",
            "text_inverted": "#ffffff",

            "border_main": "#d6ccba",   # sand hairline
            "border_focus": "#b93700",  # darkened brand orange (focus ring)

            "primary": "#24214c",       # RMAAI deep indigo (headings, key data)
            "secondary": "#b93700",     # brand orange, darkened for AA text (emphasis, CTAs)
            "tertiary": "#7a2a0a",      # RMAAI rust (true brand hex; clears AA on its own)
            "accent": "#2b5f80",        # steel blue (links/success role)
            "highlight": "#8a5a12",     # ochre, sand family darkened (Source card identity)
            "info": "#3f4a8c",          # indigo-slate (Gemini Notebook card identity)
            "insight": "#2f6b4f",       # pine green (Deep Dive card identity)
        },
        # Serif display + grotesque everything-else -- see the comment
        # above. font_mono doubles as font_body (both read Helvetica Neue),
        # the same "one humanist face carries labels, buttons, chips, *and*
        # code" trade THE_STOA documents; accepted here for the same
        # reason.
        "font_display": "'Cormorant Garamond', 'Times New Roman', Times, serif",
        # Note headings in the reader take the same serif; every other
        # theme leaves them in its body face (engine/theming.py default).
        "font_reader_heading": "'Cormorant Garamond', 'Times New Roman', Times, serif",
        "font_mono": "'Helvetica Neue', Helvetica, Arial, sans-serif",
        "font_body": "'Helvetica Neue', Helvetica, Arial, sans-serif",
        # A restrained serif register rather than the house style's heavy
        # mono-first display type: a lighter weight, barely-there negative
        # tracking (serif capitals don't need the aggressive tightening a
        # grotesque does), and slightly looser leading than the house 0.95
        # (a serif face wants a little more air between lines than a
        # condensed mono does). label_weight stays a firm 600 rather than
        # the house 700 -- Helvetica Neue at 700 in small caps reads heavy
        # next to a light serif headline; 600 keeps labels legible without
        # competing with it.
        "display_weight": "600",
        "display_tracking": "-0.005em",
        "display_leading": "1.02",
        "label_weight": "600",
        "halo": "0%",               # no glow -- hairlines and whitespace do the separating
        "rounded": "0px",           # a typeset page has square corners, not app-UI curves
        "glass_opacity": "1",       # fully opaque -- paper, not glass
        "glass_border": "1px solid #d6ccba",
        "glass_shadow": "0 0 0 0 transparent",  # no-op; see theming.py's _DEFAULTS for why not `none`
        "scanline_bg": "none",
        "scanline_opacity": "0",
        "surface_1": "linear-gradient(180deg, #fdfcf9 0%, #fbf9f4 100%)",
        "surface_2": "linear-gradient(180deg, #fdfcf9 0%, #f3efe6 100%)",
        # A hairline instead of a shadow at rest, still backed by a real
        # (if soft) shadow ladder at the deeper levels -- a book jacket
        # doesn't float, but a raised modal still needs to read as raised.
        "elevation_1": "0 0 0 1px rgba(214, 204, 186, 0.55)",
        "elevation_2": "0 12px 32px -20px rgba(26, 42, 51, 0.25)",
        "elevation_3": "0 24px 56px -28px rgba(26, 42, 51, 0.30)",
        "rim_light": "inset 0 0 0 0 transparent",  # no top-edge catch-light -- flat paper, not glass
        # The brand's sand tint is the light source here; true orange is
        # reserved for emphasis text, not ambient glow (see comment above).
        "glow_primary": "radial-gradient(circle, rgba(242, 200, 152, 0.28) 0%, transparent 70%)",
        "glow_accent": "radial-gradient(circle, rgba(43, 95, 128, 0.12) 0%, transparent 70%)",
        "grid_overlay": "none",
        "cursor_default": "auto",
        "cursor_interactive": "pointer",
    },

    # 2. CYBER_PRIME (Dark / Neon)
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
            "info": "#6366f1",          # Indigo (Gemini Notebook/Research card identity)
            "insight": "#ff2d78",       # Magenta/Rose (Deep Dive card identity)
        },
        "font_mono": "'JetBrains Mono', monospace",
        "rounded": "2px",              # Sharp corners
        "glass_opacity": "0.6",        # Heavy glass
        # Defaults (no override needed): borderless dark-glass cards, the
        # neon horizontal-sweep scanline. See engine/theming.py fallbacks.

        # --- Hand-tuned depth system -------------------------------------
        # Every key below has a working derived default in theming.py's
        # _DERIVED (so the other themes need none of this). CYBER_PRIME
        # overrides them because it's the flagship theme and the derived
        # values, while coherent, are deliberately conservative.
        #
        # The problem being solved: bg_main (#0a0a0b) is a *neutral* near-
        # black, and stacking neutral grays on it reads as flat no matter
        # how many layers there are. Every surface below is pushed a few
        # points toward blue-violet instead, so a panel separates from the
        # page by hue as well as luminance -- that's what makes the cyan
        # read as light falling on a surface rather than as a border color.
        "surface_1": "linear-gradient(160deg, #16161f 0%, #0e0e14 100%)",
        "surface_2": "linear-gradient(160deg, #1c1c28 0%, #14141c 100%)",
        # Shadow ladder. Level 3 carries a cyan bloom, which is the "light"
        # half of the system -- a pure black shadow on a black page is
        # invisible, so depth here has to come from emitted light.
        "elevation_1": "0 2px 8px -2px rgba(0,0,0,0.8)",
        "elevation_2": "0 10px 26px -8px rgba(0,0,0,0.9)",
        "elevation_3": "0 22px 48px -14px rgba(0,0,0,0.95), 0 0 40px -12px rgba(0,242,255,0.28)",
        # Slightly hotter than the derived 0.18 -- on this near-black the
        # rim is the main cue that a card has a top edge at all.
        "rim_light": "inset 0 1px 0 0 rgba(0,242,255,0.22)",
        "glow_primary": "radial-gradient(circle, rgba(0,242,255,0.40) 0%, transparent 70%)",
        "glow_accent": "radial-gradient(circle, rgba(57,255,20,0.35) 0%, transparent 70%)",
        "grid_overlay": ("linear-gradient(rgba(0,242,255,0.055) 1px, transparent 1px), "
                         "linear-gradient(90deg, rgba(0,242,255,0.055) 1px, transparent 1px)"),
    },

    # 3. THE_PATRIOT (Light / Americana). Palette grounded in the U.S. Web
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
            "info": "#2f4b6b",          # Deep navy-slate (Gemini Notebook/Research card identity) --
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

    # 4. THE_STOA (Light / Stoic Greco-Roman + Swiss). Named for the Stoa
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
            "info": "#3d5266",          # Lapis lazuli (Gemini Notebook/Research card identity)
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

    # 5. GRIZZ (Dark / Collegiate). Adams State University's official
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
            "info": "#7c9484",          # Sage (Gemini Notebook/Research card identity)
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
#
# TIMBERLINE as of the 2026-09 rebrand (was CYBER_PRIME): the site is
# moving away from the "AURELIA" terminal-neon identity toward a
# professional portfolio (see CLAUDE.md's rebrand notes), and a light,
# quiet, CV-appropriate theme is what a first-time visitor should land on
# now. CYBER_PRIME and the other three remain fully shipped and
# switchable -- this only changes the default.
CURRENT_THEME = THEME_CONFIG["TIMBERLINE"]


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
