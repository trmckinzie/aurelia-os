import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from vault_health import find_orphans, find_pending_atomization, find_promotion_candidates  # noqa: E402


def _card(note_id, title, body, note_type="CONCEPT", maturity=""):
    return {"id": note_id, "title": title, "body": body, "type": note_type, "maturity": maturity}


def _write(tmp_path, folder, filename, content):
    folder_path = tmp_path / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / filename).write_text(content, encoding="utf-8")


_FRONTMATTER = """---
created: 2026-01-01
tags:
  - type/concept
type: concept
maturity: seed
status: active
publish: true
---
"""


def test_find_pending_atomization_ranks_by_distinct_referrer_count(tmp_path):
    _write(tmp_path, "10_GARDEN/12_Concepts", "A.md", _FRONTMATTER + "**Related:** [[Ghost Concept]]")
    _write(tmp_path, "10_GARDEN/12_Concepts", "B.md", _FRONTMATTER + "**Related:** [[Ghost Concept]]")
    _write(tmp_path, "10_GARDEN/12_Concepts", "C.md", _FRONTMATTER + "**Related:** [[Rare Concept]]")

    pending = find_pending_atomization(vault_path=str(tmp_path), known_ids=set())
    assert pending[0] == ("note-ghost-concept", ["note-a", "note-b"])
    assert pending[1] == ("note-rare-concept", ["note-c"])


def test_find_pending_atomization_skips_blank_placeholder_links(tmp_path):
    # An unfilled "[[ ]]" placeholder (TPL_Concept.md's old Related-field
    # default) must never surface as a fake "note-" target.
    _write(tmp_path, "10_GARDEN/12_Concepts", "A.md", _FRONTMATTER + "**Related:** [[ ]]")

    pending = find_pending_atomization(vault_path=str(tmp_path), known_ids=set())
    assert pending == []


def test_find_pending_atomization_excludes_already_known_targets(tmp_path):
    _write(tmp_path, "10_GARDEN/12_Concepts", "A.md", _FRONTMATTER + "**Related:** [[Real Concept]]")

    pending = find_pending_atomization(vault_path=str(tmp_path), known_ids={"note-real-concept"})
    assert pending == []


def test_find_pending_atomization_skips_unpublished_notes(tmp_path):
    unpublished = _FRONTMATTER.replace("publish: true", "publish: false")
    _write(tmp_path, "10_GARDEN/12_Concepts", "A.md", unpublished + "**Related:** [[Ghost Concept]]")

    pending = find_pending_atomization(vault_path=str(tmp_path), known_ids=set())
    assert pending == []


def test_find_orphans_returns_notes_with_degree_at_most_one():
    cards = [
        _card("note-hub", "Hub", "<button onclick=\"openNote('note-a')\">A</button>"
              "<button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-a", "A", "no links"),
        _card("note-b", "B", "no links"),
        _card("note-isolated", "Isolated", "no links"),
    ]
    orphans = find_orphans(cards, types={"concept"})
    orphan_ids = [o[0] for o in orphans]
    assert "note-isolated" in orphan_ids
    assert "note-hub" not in orphan_ids


def test_find_orphans_respects_type_filter():
    cards = [_card("note-a", "A", "no links", note_type="AUTHOR")]
    assert find_orphans(cards, types={"concept"}) == []
    assert find_orphans(cards, types={"author"})[0][0] == "note-a"


def test_find_promotion_candidates_seed_to_growing_needs_two_backlinks():
    cards = [
        _card("note-a", "A", "<button onclick=\"openNote('note-target')\">T</button>"),
        _card("note-b", "B", "<button onclick=\"openNote('note-target')\">T</button>"),
        _card("note-target", "Target", "no links", maturity="seed"),
    ]
    candidates = find_promotion_candidates(cards)
    assert candidates["seed_to_growing"] == [("note-target", "Target", 2)]


def test_find_promotion_candidates_growing_to_evergreen_needs_two_disciplines():
    cards = [
        _card("note-d1", "Discipline One", "<button onclick=\"openNote('note-target')\">T</button>", note_type="DISCIPLINE"),
        _card("note-d2", "Discipline Two", "<button onclick=\"openNote('note-target')\">T</button>", note_type="DISCIPLINE"),
        _card("note-target", "Target", "no links", maturity="growing"),
    ]
    candidates = find_promotion_candidates(cards)
    assert candidates["growing_to_evergreen"] == [("note-target", "Target", 2)]


def test_find_promotion_candidates_ignores_evergreen_notes():
    cards = [
        _card("note-a", "A", "<button onclick=\"openNote('note-target')\">T</button>"),
        _card("note-b", "B", "<button onclick=\"openNote('note-target')\">T</button>"),
        _card("note-target", "Target", "no links", maturity="evergreen"),
    ]
    candidates = find_promotion_candidates(cards)
    assert candidates == {"seed_to_growing": [], "growing_to_evergreen": []}
