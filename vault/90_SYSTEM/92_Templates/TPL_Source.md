---
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - type/source/book
  - maturity/seed
  - status/queued
  # - topic/example (add one or more)
type: source/book
maturity: seed
status: queued
publish: false
---
<!--
Source contract (engine/extractors.py::extract_source_data) -- keep these
three conventions exact:
  1. A line containing "Author:" followed by a wikilink -- label is
     upper-cased on the card. Anything wrapping the label ("**👤 Author:**")
     is fine, only the literal word "Author:" and what follows it matters.
  2. A "### ... Core Argument ..." or "... Thesis ..." header followed
     immediately by a "> blockquote" line, same rule as Concept's Definition.
  3. A "### ... Concepts Extracted ..." header -- every wikilink anywhere in
     that section (not just one line) becomes a pill, up to 12.
"Full Notes:" and everything else below is free-form and only shown when
the note is opened, not parsed.
-->
# 📖 <% tp.file.title %>

**👤 Author:** [[ ]]
 Full Notes: 

---

### 💡 The Core Argument (Thesis)
>

---

### 🧠 Concepts Extracted
* [[ ]]