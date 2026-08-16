from engine.extractors import (
    extract_concept_data,
    extract_core_logic,
    extract_impact_metrics,
    extract_mission_brief,
    extract_protocol_logic,
    extract_protocol_sequence,
    extract_source_data,
)


def test_extract_protocol_sequence_checklist():
    text = """
## Sequence
- [ ] Wake up
- [ ] Drink water
- [x] Done step
## Next
- [ ] should not appear
"""
    steps = extract_protocol_sequence(text)
    assert steps == ["Wake up", "Drink water", "Done step"]


def test_extract_protocol_sequence_caps_at_six():
    items = "\n".join(f"- [ ] step {i}" for i in range(10))
    text = f"## Sequence\n{items}\n"
    assert len(extract_protocol_sequence(text)) == 6


def test_extract_protocol_logic_found():
    text = "## System Logic\n> The core rationale here.\nmore"
    assert extract_protocol_logic(text) == "The core rationale here."


def test_extract_protocol_logic_missing_uses_default():
    assert extract_protocol_logic("no logic section at all") == "Logic not defined."


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


def test_extract_mission_brief_truncates_long_text():
    body = "# 🚨 Mission Brief\n" + ("word " * 100) + "\n# Next Section"
    brief = extract_mission_brief(body)
    assert brief.endswith("...")
    assert len(brief) <= 243


def test_extract_mission_brief_missing_section():
    assert extract_mission_brief("no mission brief here") == ""


def test_extract_core_logic_strips_bold_markers():
    body = "# 🛠️ Architecture\n**Core Logic:** **Bold** plain text\n"
    assert extract_core_logic(body) == "Bold plain text"


def test_extract_impact_metrics_caps_at_four():
    # The colon lives *inside* the bold markers (matching real note style,
    # e.g. "- **Efficiency:** Centralized tracking."), so it's part of the
    # captured label.
    body = "# ⚡ Operational Impact\n" + "\n".join(f"- **Metric {i}:** value" for i in range(6))
    metrics = extract_impact_metrics(body)
    assert len(metrics) == 4
    assert metrics[0] == "Metric 0:"
