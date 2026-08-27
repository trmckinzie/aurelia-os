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
Concept contract (engine/extractors.py::extract_concept_data) -- keep these
two conventions exact and the card renders correctly:
  1. "**🔗 Related:** [[Note One]], [[Note Two]], ..." on one line. Up to 12
     wikilinks are kept as clickable pills (raise the cap in extractors.py,
     not here, if you ever need more). Plain comma-separated text with no
     [[brackets]] at all still shows, just not clickable.
  2. A "### ... Definition ..." header followed immediately by a
     "> blockquote" line -- the header text just needs "Definition" in it
     somewhere, but the blockquote must come right after with no blank
     paragraph in between.
Key Insight is free-form prose/bullets and isn't parsed structurally, only
shown in the note body when opened.
-->
# ⚛️ <% tp.file.title %>

**🔗 Related:** [[ ]]

---

### 💡 Definition
> 

### 📝 Key Insight
* 

---

