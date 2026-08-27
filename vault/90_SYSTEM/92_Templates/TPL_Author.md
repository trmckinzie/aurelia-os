---
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - type/author
  - maturity/evergreen
  - status/active
  # - topic/example (add one or more)
type: author
maturity: evergreen
status: active
publish: false
---
<!--
Author contract (engine/extractors.py::extract_author_data) -- keep these
three conventions exact:
  1. A "### ... Profile & Context ..." header followed immediately by a
     "> blockquote" line, same rule as Concept's Definition.
  2. A "### ... Key Works ..." header -- every wikilink anywhere in that
     section becomes a pill, up to 6.
  3. A "### ... Core Concepts ..." header -- same, up to 8.
-->
# 👤 <% tp.file.title %>

### 📝 Profile & Context
> 

### 📚 Key Works (In Vault)
* [[ ]]

### ⚛️ Core Concepts
* [[ ]]