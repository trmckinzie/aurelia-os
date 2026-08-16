from engine.extractors import extract_concept_data, extract_source_data


def test_extract_concept_data_definition_and_links():
    text = """
### Definition
> A concept is a unit of thought.

**🔗 Related:** Idea One, Idea Two
"""
    definition, links = extract_concept_data(text)
    assert definition == "A concept is a unit of thought."
    assert links == ["Idea One", "Idea Two"]


def test_extract_source_data_author_and_argument():
    text = """
**Author:** <button onclick="openNote('x')">Jordan Peterson</button>

### Core Argument (Thesis)
> Meaning comes from responsibility.

### Concepts Extracted
<button onclick="openNote('a')">Hierarchy</button>
"""
    author, argument, concepts = extract_source_data(text)
    assert author == "JORDAN PETERSON"
    assert argument == "Meaning comes from responsibility."
    assert concepts == ["Hierarchy"]
