---
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - type/concept
  - maturity/seed
  - status/active
  # - topic/example (add one or more)
type: concept
maturity: seed
status: active
publish: false
---
<!--
Zettelkasten role: PERMANENT / ATOMIC note. One idea, in your own words,
densely linked -- the thing a literature note (Source/NotebookLM) or
fleeting note (Daily Log) eventually gets distilled into.

Concept contract (engine/extractors.py::extract_concept_data) -- keep these
conventions exact and the card renders correctly:
  1. "**🔗 Related:** [[Note One]], [[Note Two]], ..." on one line. Up to 12
     wikilinks are kept as clickable pills (raise the cap in extractors.py,
     not here, if you ever need more). Plain comma-separated text with no
     [[brackets]] at all still shows, just not clickable.
  2. A "### ... Definition ..." header followed immediately by a
     "> blockquote" line -- the header text just needs "Definition" in it
     somewhere, but the blockquote must come right after with no blank
     paragraph in between.
  3. An optional "**⚡ Contrasts With:** [[Note]], ..." line, same shape as
     Related but for tension/friction instead of agreement -- notes that
     complicate, compete with, or push back on this one. Up to 6 kept.
     Leave the placeholder below as an HTML comment (not "[[ ]]") when
     unfilled, so an empty field never becomes a fake wikilink target.
Key Insight is free-form prose/bullets and isn't parsed structurally, only
shown in the note body when opened.
-->
# ⚛️ <% tp.file.title %>

**🔗 Related:** [[ ]]

**⚡ Contrasts With:** <!-- optional, notes that complicate or push back on this one -->

---

### 💡 Definition
> 

### 📝 Key Insight
* 

---

