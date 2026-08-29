---
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - type/gemini-notebook
  - maturity/growing
  - status/active
  - topic/research
  - source/gemini-notebook
type: gemini-notebook
maturity: growing
status: active
publish: false
---
<!--
Zettelkasten role: LITERATURE note. A synthesis pulled from source material,
not your own atomic thinking yet -- ideas worth keeping still belong in
their own Concept notes, same as a Source note's Concepts Extracted.

Gemini Notebook contract (engine/extractors.py::extract_gemini_notebook_data)
-- keep these exact:
  1. A "# ... Lit Review Overview ..." header -- everything until the next
     "#" header becomes the card's overview text.
  2. Each "# <emoji> <Feature Name>" header below is checked independently:
     if there is ANY non-whitespace text under it (before the next header),
     that feature shows an "active" badge on the card. DELETE the entire
     header + line for any feature you didn't generate -- do not leave a
     placeholder path in place, since a literal unfilled path still counts
     as "content" and falsely badges a feature you don't actually have.

  Trimmed (2026-08) to the 3 outputs actually used in practice -- Audio
  Overview, Mind Map, Flashcards. The engine still recognizes Video Overview,
  Reports, Quiz, Infographic, Slide Deck, and Data Table headers too (see
  extract_gemini_notebook_data/_MEDIA_MAP in engine/content.py) if you ever
  export one of those; just add a matching "# <emoji> <Header>" section by
  hand.

  3. Every "#"-level header in this note -- including any freeform ones you
     add below (chapter breakdowns, a study guide, exam prep, etc.) -- is
     rendered as its own collapsible section on the site (see
     wrap_gemini_notebook_sections in engine/content.py). The first section
     opens by default; the rest start collapsed. So it's fine, and expected,
     to paste in extra "# 📚 <Chapter/Section Title>" headers beyond the ones
     below -- they'll show up as additional collapsible blocks in the reader.
-->
# 📚 Lit Review Overview
> [Paste the Executive Summary or Core Thesis here.]

# 🎙️ Audio Overview
assets/audio/[filename].wav

# 🧠 Mind Map
assets/images/[filename].png

# 🃏 Flashcards
assets/flashcards/[filename].csv

# 📚 Sources
> [Zotero Data Placeholder]
