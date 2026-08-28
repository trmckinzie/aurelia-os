---
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - type/notebooklm
  - maturity/growing
  - status/active
  - topic/research
  - source/notebooklm
type: notebooklm
maturity: growing
status: active
publish: false
---
<!--
Zettelkasten role: LITERATURE note. A synthesis pulled from source material,
not your own atomic thinking yet -- ideas worth keeping still belong in
their own Concept notes, same as a Source note's Concepts Extracted.

NotebookLM contract (engine/extractors.py::extract_notebooklm_data) -- keep
these exact:
  1. A "# ... Lit Review Overview ..." header -- everything until the next
     "#" header becomes the card's overview text.
  2. Each "# <emoji> <Feature Name>" header below is checked independently:
     if there is ANY non-whitespace text under it (before the next header),
     that feature shows an "active" badge on the card. DELETE the entire
     header + line for any feature you didn't generate -- do not leave a
     placeholder path in place, since a literal unfilled path still counts
     as "content" and falsely badges a feature you don't actually have.
     (This bugged 14 of the vault's 15 published NotebookLM notes before the
     2026-08 template audit: unused headers were left with fake
     "assets/.../[filename].ext" placeholder text, so their cards showed
     Video/Slides/Quiz/etc. badges for studio outputs that were never
     generated.) Only keep the headers for outputs you actually exported.
-->
# 📚 Lit Review Overview
> [Paste the Executive Summary or Core Thesis here.]

# 🎙️ Audio Overview
assets/audio/[filename].wav

# 🎥 Video Overview
assets/video/[filename].mp4

# 🧠 Mind Map
assets/images/[filename].png

# 📄 Reports
assets/images/[filename].png

# 🃏 Flashcards
assets/flashcards/[filename].csv

# 📝 Quiz
assets/images/[filename].png

# 📊 Infographic
assets/images/[filename].png

# 📽️ Slide Deck
assets/images/[filename].png

# 📉 Data Table
assets/images/[filename].png

# 📚 Sources
> [Zotero Data Placeholder]