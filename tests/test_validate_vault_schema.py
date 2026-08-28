"""Runs the vault schema validator (tools/validate_vault_schema.py) against
the real vault, so `pytest` catches schema drift in 10_GARDEN even though CI
itself only runs build.py (see CLAUDE.md). Also covers check_note() directly
against hand-built frontmatter, the same pattern as the other test files."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from validate_vault_schema import check_note, check_vault, _has_topic_tag  # noqa: E402


def test_real_vault_10_garden_matches_canonical_schema():
    violations, _, _ = check_vault()
    assert violations == [], (
        f"{len(violations)} note(s) violate the canonical schema -- "
        f"run `python tools/validate_vault_schema.py` for details: {violations[:3]}"
    )


def test_check_note_passes_well_formed_concept():
    meta = {
        "type": "concept", "maturity": "seed", "status": "active", "publish": True,
        "tags": ["type/concept", "maturity/seed", "status/active", "topic/neuroscience"],
    }
    assert check_note("x.md", "12_Concepts", meta) == []


def test_check_note_flags_wrong_type_for_folder():
    meta = {
        "type": "author", "maturity": "seed", "status": "active",
        "tags": ["type/author", "maturity/seed", "status/active"],
    }
    problems = check_note("x.md", "12_Concepts", meta)
    assert any("type:" in p for p in problems)


def test_check_note_flags_invalid_maturity_value():
    meta = {
        "type": "concept", "maturity": "sapling", "status": "active",
        "tags": ["type/concept", "status/active"],
    }
    problems = check_note("x.md", "12_Concepts", meta)
    assert any("maturity:" in p for p in problems)


def test_check_note_flags_key_tag_mismatch():
    # key says growing, but the mirrored tag still says seed -- the two
    # sources of truth have drifted apart.
    meta = {
        "type": "concept", "maturity": "growing", "status": "active",
        "tags": ["type/concept", "maturity/seed", "status/active"],
    }
    problems = check_note("x.md", "12_Concepts", meta)
    assert any("mirrored tag 'maturity/growing'" in p for p in problems)


def test_check_note_flags_stray_empty_topic_tag():
    meta = {
        "type": "concept", "maturity": "seed", "status": "active",
        "tags": ["type/concept", "maturity/seed", "status/active", "topic/"],
    }
    problems = check_note("x.md", "12_Concepts", meta)
    assert any("stray empty/bare topic tag" in p for p in problems)


def test_has_topic_tag_true_when_any_topic_tag_present():
    assert _has_topic_tag(["type/concept", "topic/neuroscience"]) is True


def test_has_topic_tag_false_when_no_topic_tag():
    assert _has_topic_tag(["type/concept", "maturity/seed"]) is False
