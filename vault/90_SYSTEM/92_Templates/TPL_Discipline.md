---
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - type/discipline
  - maturity/evergreen
  - status/active
  # - topic/example (add one or more)
type: discipline
maturity: evergreen
status: active
publish: false
---
<!--
Zettelkasten role: STRUCTURE note (a Map of Content). Curates a path
through a cluster of Concept/Author/Source notes rather than being an
atomic idea itself.

Discipline contract (engine/extractors.py::extract_discipline_data) -- keep
these conventions exact:
  1. A "### ... Definition ..." header followed immediately by a
     "> blockquote" line, same rule as Concept's Definition.
  2. A "### ... Core Concepts ..." header -- every wikilink anywhere in that
     section becomes a pill, up to 10.
  3. A "### ... Foundational Texts ..." header -- same, up to 10.
  4. An optional "**⚡ Contrasts With:** [[Note]], ..." line (same shape as
     Concept's, up to 6 kept) -- rival or competing fields/frameworks, not
     just related ones. Leave the placeholder as an HTML comment (not
     "[[ ]]") when unfilled.
Unresolved Questions is free-form and only shown when the note is opened.
-->
# 🧠 <% tp.file.title %>

### 🧐 Definition (The Scope)
>

---

### 🔑 Core Concepts (The Bricks)
* [[ ]]
* [[ ]]
* [[ ]]

### 📚 Foundational Texts
* [[ ]]
* [[ ]]

**⚡ Contrasts With:** <!-- optional, rival or competing fields/frameworks -->

### 🧪 Unresolved Questions
* 