from engine.extractors import (
    extract_author_data,
    extract_concept_data,
    extract_deep_dive_data,
    extract_discipline_data,
    extract_log_data,
    extract_source_data,
)


def test_extract_concept_data_with_wikilinked_related():
    text = """
### Definition
> A concept is a unit of thought.

**🔗 Related:** <button onclick="openNote('note-idea-one')">Idea One</button>, <button onclick="openNote('note-idea-two')">Idea Two</button>
"""
    definition, links = extract_concept_data(text)
    assert definition == "A concept is a unit of thought."
    assert links == [("note-idea-one", "Idea One"), ("note-idea-two", "Idea Two")]


def test_extract_concept_data_falls_back_to_plain_related_text():
    # No wikilinks in the Related line at all -- still shown, just not clickable.
    text = """
### Definition
> A concept is a unit of thought.

**🔗 Related:** Idea One, Idea Two
"""
    definition, links = extract_concept_data(text)
    assert definition == "A concept is a unit of thought."
    assert links == [(None, "Idea One"), (None, "Idea Two")]


def test_extract_source_data_author_and_argument():
    text = """
**Author:** <button onclick="openNote('note-jordan-peterson')">Jordan Peterson</button>

### Core Argument (Thesis)
> Meaning comes from responsibility.

### Concepts Extracted
<button onclick="openNote('note-hierarchy')">Hierarchy</button>
"""
    author, argument, concepts = extract_source_data(text)
    assert author == ("note-jordan-peterson", "JORDAN PETERSON")
    assert argument == "Meaning comes from responsibility."
    assert concepts == [("note-hierarchy", "Hierarchy")]


def test_extract_source_data_missing_author_defaults_to_unknown():
    author, _, _ = extract_source_data("no author line here")
    assert author == (None, "UNKNOWN")


def test_extract_author_data_works_and_concepts():
    text = """
### Profile & Context
> A researcher.

### Key Works
<button onclick="openNote('note-book-one')">Book One</button>

### Core Concepts
<button onclick="openNote('note-idea')">Idea</button>
"""
    context, works, concepts = extract_author_data(text)
    assert context == "A researcher."
    assert works == [("note-book-one", "Book One")]
    assert concepts == [("note-idea", "Idea")]


def test_extract_discipline_data_pillars_and_canon():
    text = """
### Definition
> The scope of the field.

### Core Concepts
<button onclick="openNote('note-pillar')">Pillar</button>

### Foundational Texts
<button onclick="openNote('note-text')">The Text</button>
"""
    scope, pillars, canon = extract_discipline_data(text)
    assert scope == "The scope of the field."
    assert pillars == [("note-pillar", "Pillar")]
    assert canon == [("note-text", "The Text")]


def test_extract_log_data_source_and_concepts_are_link_aware():
    text = """
**GOAL:** Read chapter one.

**SOURCE:** <button onclick="openNote('note-the-selfish-gene')">The Selfish Gene</button>

* **Concept:** <button onclick="openNote('note-replicator')">Replicator</button>
* **Concept:** Unlinked Idea

**📝 BRIEF SUMMARY:**
> A short summary.
"""
    goal, source, concepts, summary = extract_log_data(text)
    assert goal == "Read chapter one."
    assert source == ("note-the-selfish-gene", "The Selfish Gene")
    assert concepts == [("note-replicator", "Replicator"), (None, "Unlinked Idea")]
    assert summary == "A short summary."


def test_extract_log_data_defaults_when_fields_missing():
    goal, source, concepts, summary = extract_log_data("nothing here")
    assert goal == "System Check."
    assert source == (None, "Internal Log")
    assert concepts == []
    assert summary == ""


def test_extract_deep_dive_data_with_wikilinked_related():
    # Related sits before the pasted body, matching TPL_Deep_Dive.md's
    # actual layout -- Part 3 is the last section in the document, same as
    # a real pasted-in piece, so its section correctly runs to the end.
    text = """**🔗 Related:** <button onclick="openNote('note-idea-one')">Idea One</button>, <button onclick="openNote('note-idea-two')">Idea Two</button>

---

# Some Title

*A ~5-minute read on why this matters*

---

## Part 1: The Plain-English Preview

Preview text here.

## Part 2: The Deep Dive

### First Idea
Some detail.

## Part 3: The Plain-English Summary

The **agent loop** is the core idea, explained with a `code` reference and a # stray hash.
"""
    premise, summary, related = extract_deep_dive_data(text)
    assert premise == "A ~5-minute read on why this matters"
    assert summary == "The agent loop is the core idea, explained with a code reference and a stray hash."
    assert related == [("note-idea-one", "Idea One"), ("note-idea-two", "Idea Two")]


def test_extract_deep_dive_data_ignores_bold_delimiter_for_premise():
    # A **bold** line (doubled delimiter) must not be mistaken for the
    # single-asterisk *italic* premise line -- the whole point of the
    # backreference-based regex is to tell these apart.
    text = "**This is bold, not the premise**\n\n*This is the real premise*\n"
    premise, _, _ = extract_deep_dive_data(text)
    assert premise == "This is the real premise"


def test_extract_deep_dive_data_underscore_premise_also_matches():
    text = "_An underscore-delimited premise line_\n"
    premise, _, _ = extract_deep_dive_data(text)
    assert premise == "An underscore-delimited premise line"


def test_extract_deep_dive_data_defaults_when_fields_missing():
    premise, summary, related = extract_deep_dive_data("nothing here")
    assert premise == "No premise line found."
    assert summary == "No summary section found."
    assert related == []


def test_extract_deep_dive_data_no_related_field_returns_empty_list():
    # Regression guard: the template's empty placeholder is a bracket-free
    # HTML comment specifically so an unfilled Related field parses to no
    # links at all, not a dangling link to an empty target.
    text = "*A premise*\n\n## Part 3: Summary\n\nSome summary text.\n\n**🔗 Related:** <!-- optional -->\n"
    _, _, related = extract_deep_dive_data(text)
    assert related == []
