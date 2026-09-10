"""Legacy terminal-voice tokens banned from rendered output.

The site used to be written in an "Aurelia OS terminal" register -- see
tests/test_lobby.py's module docstring for the Lobby's own history of it.
LEGACY_TOKENS is that page's (and the shared chrome's) list, moved here
verbatim so it can be shared rather than redefined.

GARDEN_LEGACY_TOKENS extends it for the Garden and the Gemini Notebook media
widgets rendered inside note bodies (engine/content.py's _render_audio,
_render_video, _render_image, _render_flashcards) -- terminal-flavored labels
the 2026-09 voice pass never reached because they live in note-body markup,
not page chrome. See tests/test_garden.py.
"""

# Copy that belonged to the old voice. Every one of these was on the page (or
# in the shared chrome) before the rebrand.
LEGACY_TOKENS = (
    "AURELIA OS",
    "WHAT IS AURELIA",
    "SYSTEM_READY",
    "NEURAL_LOADOUT",
    "CORTEX",
    "MOD_01",
    "OPERATOR_PROFILE",
    "TERM_v3",
    "Initiate Neural Query",
    "NODES CONNECTED",
)

GARDEN_LEGACY_TOKENS = LEGACY_TOKENS + (
    "Q_NODE",
    "A_DATA",
    "TAP TO DECRYPT",
    "MEMORY_BANK_LOADED",
    "NEURAL_AUDIO_STREAM",
    "VISUAL_FEED",
    "LIVE_ASSET",
    "ENLARGE",
)
