"""Runs the vault schema validator (tools/validate_vault_schema.py) against
the real vault, so `pytest` catches schema drift in 10_GARDEN even though CI
itself only runs build.py (see CLAUDE.md). Also covers check_note() directly
against hand-built frontmatter, the same pattern as the other test files."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from validate_vault_schema import check_essays, check_note, check_vault, _has_topic_tag  # noqa: E402


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


# --- the Essays section (roadmap S15) --------------------------------------

def test_real_vault_essays_folder_passes_or_is_absent():
    count, problems = check_essays()
    assert problems == [], problems
    assert count >= 0


def test_check_essays_reports_a_draft_and_a_stray_file(tmp_path):
    (tmp_path / "E01 Draft.md").write_text(
        "---\ntype: essay\nid: E01\ntitle: T\nslug: t\npublish: false\npublished: 2026-01-01\n"
        "disciplines: [x]\nthesis: s\ncitation_style: apa7\nmethods: {drafted_on: a, edited_in: b, ai_roles: []}\n---\nbody\n",
        encoding="utf-8")
    (tmp_path / "paper.pdf").write_text("x", encoding="utf-8")
    count, problems = check_essays(str(tmp_path))
    assert count == 0
    messages = [m for _rel, m in problems]
    assert any("draft" in m for m in messages)
    assert any("only .md and .yaml" in m for m in messages)


def test_check_essays_passes_the_fixture_essay():
    fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "essays")
    assert check_essays(fixture) == (1, [])
