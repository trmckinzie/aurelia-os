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


# --- pending resolution is wired through content.build_link_resolver -------
#
# So this report's "still dangling" count agrees with the real build's own
# "targets still unresolved" summary line for the same vault (both now go
# through the same resolver) -- see find_pending_atomization's docstring.

def test_find_pending_atomization_resolves_via_alias(tmp_path):
    # Title deliberately has no "Base (...)"/"Base: ..." shape, so only tier
    # 2 (alias) can resolve this -- isolates it from the suffix test below.
    aliased = _FRONTMATTER.replace("publish: true", 'publish: true\naliases: ["Dopamine"]')
    _write(tmp_path, "10_GARDEN/12_Concepts", "Reward Prediction Error.md", aliased + "Some body.")
    _write(tmp_path, "10_GARDEN/12_Concepts", "Other.md", _FRONTMATTER + "**Related:** [[Dopamine]]")

    pending = find_pending_atomization(
        vault_path=str(tmp_path),
        known_ids={"note-reward-prediction-error", "note-other"},
    )
    assert pending == []


def test_find_pending_atomization_without_the_alias_still_shows_pending(tmp_path):
    # Baseline for the test above: with no `aliases:` field, [[Dopamine]]
    # doesn't resolve to the real note and stays a pending target -- proves
    # the alias wiring is actually doing something, not a structural no-op.
    _write(tmp_path, "10_GARDEN/12_Concepts", "Reward Prediction Error.md", _FRONTMATTER + "Some body.")
    _write(tmp_path, "10_GARDEN/12_Concepts", "Other.md", _FRONTMATTER + "**Related:** [[Dopamine]]")

    pending = find_pending_atomization(
        vault_path=str(tmp_path),
        known_ids={"note-reward-prediction-error", "note-other"},
    )
    assert pending == [("note-dopamine", ["note-other"])]


def test_find_pending_atomization_resolves_via_unique_title_suffix(tmp_path):
    _write(tmp_path, "10_GARDEN/12_Concepts", "System 1 vs System 2 (Dual-Process Theory).md",
           _FRONTMATTER + "Some body.")
    _write(tmp_path, "10_GARDEN/12_Concepts", "Other.md",
           _FRONTMATTER + "**Related:** [[System 1 vs System 2]]")

    pending = find_pending_atomization(
        vault_path=str(tmp_path),
        known_ids={"note-system-1-vs-system-2-dual-process-theory", "note-other"},
    )
    assert pending == []


def test_pending_count_agrees_with_the_build_unresolved_count(tmp_path, monkeypatch):
    # The actual requirement: this report's count and the real build's
    # "targets still unresolved" count must agree for the same vault.
    import engine.pipeline as pipeline
    from engine.content import get_unresolved_wikilink_targets, reset_wikilink_resolution_counts

    aliased = _FRONTMATTER.replace("publish: true", 'publish: true\naliases: ["Dopamine"]')
    _write(tmp_path, "10_GARDEN/12_Concepts", "Dopamine (Reward Prediction Error).md",
           aliased + "Some body.")
    _write(tmp_path, "10_GARDEN/12_Concepts", "Other.md",
           _FRONTMATTER + "**Related:** [[Dopamine]] and [[Totally Missing]]")

    reset_wikilink_resolution_counts()
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(tmp_path))
    garden_cards, _backlinks, _edges = pipeline._scan_vault()
    known_ids = {c["id"] for c in garden_cards}
    build_unresolved = len(get_unresolved_wikilink_targets())

    pending = find_pending_atomization(vault_path=str(tmp_path), known_ids=known_ids)
    assert len(pending) == build_unresolved


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


# --- default-path guard -----------------------------------------------------
# Every report can be called with nothing injected, in which case it scans the
# vault itself. _scan_vault() returns a (cards, backlinks, edges) tuple, and
# the tool once iterated that tuple as if it were the card list: every
# injected-argument test passed while `python tools/vault_health.py` crashed
# on line one. These pin the uninjected path against the real return shape.

def _fake_scan(cards):
    return lambda: (cards, {}, [])


def test_find_pending_atomization_default_path_unpacks_scan_vault(tmp_path, monkeypatch):
    import vault_health

    monkeypatch.setattr(vault_health, "_scan_vault", _fake_scan([_card("note-a", "A", "")]))
    _write(tmp_path, "10_GARDEN/12_Concepts", "B.md", _FRONTMATTER + "**Related:** [[A]] and [[Ghost]]")

    pending = find_pending_atomization(vault_path=str(tmp_path))
    assert pending == [("note-ghost", ["note-b"])]


def test_find_orphans_default_path_unpacks_scan_vault(monkeypatch):
    import vault_health

    monkeypatch.setattr(vault_health, "_scan_vault", _fake_scan([_card("note-a", "A", "no links")]))
    assert find_orphans() == [("note-a", "A", "concept", 0)]


def test_find_promotion_candidates_default_path_unpacks_scan_vault(monkeypatch):
    import vault_health

    monkeypatch.setattr(vault_health, "_scan_vault", _fake_scan([_card("note-a", "A", "no links", maturity="seed")]))
    assert find_promotion_candidates() == {"seed_to_growing": [], "growing_to_evergreen": []}
