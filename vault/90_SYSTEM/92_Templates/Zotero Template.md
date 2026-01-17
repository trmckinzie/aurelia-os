---
citekey: {{citekey}}
status: 📥 Unread
tags: [literature-note, {{itemType}}]
title: "{{title}}"
authors: {{authors}}
year: {{date | format("YYYY")}}
---

# {{title}}
**Authors:** {{authors}}
**Year:** {{date | format("YYYY")}}
**Zotero Link:** [Open in Zotero]({{zoteroSelectURI}})
**PDF:** [Open PDF]({{pdfZoteroLink}})

---
## 💡 Key Concepts & Summary
*Draft your own summary here...*

---
## 🖍️ Highlights & Annotations
{% for annotation in annotations -%}
{%- if annotation.annotatedText -%}
> {{annotation.annotatedText}} (p. {{annotation.pageLabel}})
{%- endif %}
{%- if annotation.imageRelativePath -%}
![[{{annotation.imageRelativePath}}]]
{%- endif %}
{% if annotation.comment %}
**Note:** {{annotation.comment}}
{% endif %}
{% endfor -%}