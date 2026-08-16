from engine.pipeline import _build_backlinks_index, _build_lobby_context


def _card(note_id, title, body):
    return {"id": note_id, "title": title, "body": body}


def _lobby_card(note_id, title, maturity=""):
    return {"id": note_id, "title": title, "maturity": maturity}


def test_backlinks_index_maps_target_to_referencing_notes():
    cards = [
        _card("note-a", "A", "links to <button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "no links here"),
        _card("note-c", "C", "also links to <button onclick=\"openNote('note-b')\">B</button>"),
    ]
    index = _build_backlinks_index(cards)
    assert index == {"note-b": [{"id": "note-a", "title": "A"}, {"id": "note-c", "title": "C"}]}


def test_backlinks_index_omits_notes_with_no_incoming_links():
    cards = [_card("note-a", "A", "no links"), _card("note-b", "B", "also no links")]
    assert _build_backlinks_index(cards) == {}


def test_backlinks_index_ignores_self_links():
    cards = [_card("note-a", "A", "links to itself: <button onclick=\"openNote('note-a')\">A</button>")]
    assert _build_backlinks_index(cards) == {}


def test_backlinks_index_ignores_links_to_unpublished_notes():
    # note-ghost isn't in the card list at all (e.g. unpublished or a
    # scrapped page type), so it can't appear as a backlink target.
    cards = [_card("note-a", "A", "links to <button onclick=\"openNote('note-ghost')\">Ghost</button>")]
    assert _build_backlinks_index(cards) == {}


def test_backlinks_index_dedupes_multiple_links_from_the_same_note():
    cards = [
        _card("note-a", "A", "mentions B twice: "
              "<button onclick=\"openNote('note-b')\">B</button> and again "
              "<button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "no links"),
    ]
    index = _build_backlinks_index(cards)
    assert index == {"note-b": [{"id": "note-a", "title": "A"}]}


def test_lobby_context_counts_notes_and_maturity():
    cards = [
        _lobby_card("note-a", "A", "seed"),
        _lobby_card("note-b", "B", "seed"),
        _lobby_card("note-c", "C", "evergreen"),
        _lobby_card("note-d", "D", ""),  # no maturity tag at all
    ]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["total_notes"] == 4
    assert stats["maturity_counts"] == {"seed": 2, "growing": 0, "evergreen": 1}


def test_lobby_context_ranks_hub_notes_by_connection_count():
    cards = [_lobby_card("note-a", "A"), _lobby_card("note-b", "B"), _lobby_card("note-c", "C")]
    graph_index = {
        "nodes": [
            {"id": "note-a", "title": "A", "type": "concept"},
            {"id": "note-b", "title": "B", "type": "source"},
            {"id": "note-c", "title": "C", "type": "concept"},
        ],
        "edges": [{"source": "note-a", "target": "note-b"}, {"source": "note-a", "target": "note-c"}],
    }
    stats = _build_lobby_context(cards, graph_index)
    assert stats["hub_notes"][0] == {"id": "note-a", "title": "A", "type": "concept", "connections": 2}


def test_lobby_context_finds_latest_daily_log_date():
    cards = [
        _lobby_card("note-2025-01-01", "2025-01-01"),
        _lobby_card("note-2025-12-31", "2025-12-31"),
        _lobby_card("note-some-concept", "Some Concept"),  # not a daily log
    ]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["latest_log_date"] == "2025-12-31"


def test_lobby_context_latest_log_date_is_none_without_daily_logs():
    cards = [_lobby_card("note-some-concept", "Some Concept")]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["latest_log_date"] is None


def test_lobby_context_review_seed_carries_id_title_maturity():
    cards = [_lobby_card("note-a", "A", "seed")]
    graph_index = {"nodes": [], "edges": []}
    stats = _build_lobby_context(cards, graph_index)
    assert stats["review_seed"] == [{"id": "note-a", "title": "A", "maturity": "seed"}]
