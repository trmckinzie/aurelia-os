from engine.pipeline import _build_graph_index, _build_link_graph, _build_lobby_context


def _card(note_id, title, body, tags=None):
    return {"id": note_id, "title": title, "body": body, "type": "CONCEPT", "tags": tags or []}


def _lobby_card(note_id, title, maturity=""):
    return {"id": note_id, "title": title, "maturity": maturity}


def test_link_graph_backlinks_maps_target_to_referencing_notes():
    cards = [
        _card("note-a", "A", "links to <button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "no links here"),
        _card("note-c", "C", "also links to <button onclick=\"openNote('note-b')\">B</button>"),
    ]
    backlinks, _ = _build_link_graph(cards)
    assert backlinks == {"note-b": [{"id": "note-a", "title": "A"}, {"id": "note-c", "title": "C"}]}


def test_link_graph_omits_notes_with_no_incoming_links():
    cards = [_card("note-a", "A", "no links"), _card("note-b", "B", "also no links")]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {}
    assert edges == []


def test_link_graph_ignores_self_links():
    cards = [_card("note-a", "A", "links to itself: <button onclick=\"openNote('note-a')\">A</button>")]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {}
    assert edges == []


def test_link_graph_ignores_links_to_unpublished_notes():
    # note-ghost isn't in the card list at all (e.g. unpublished or a
    # scrapped page type), so it can't appear as a backlink target or edge.
    cards = [_card("note-a", "A", "links to <button onclick=\"openNote('note-ghost')\">Ghost</button>")]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {}
    assert edges == []


def test_link_graph_dedupes_multiple_links_from_the_same_note():
    cards = [
        _card("note-a", "A", "mentions B twice: "
              "<button onclick=\"openNote('note-b')\">B</button> and again "
              "<button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "no links"),
    ]
    backlinks, edges = _build_link_graph(cards)
    assert backlinks == {"note-b": [{"id": "note-a", "title": "A"}]}
    assert edges == [{"source": "note-a", "target": "note-b"}]


def test_link_graph_edges_are_deduped_undirected_pairs():
    # A links to B and B links back to A -- one edge, not two.
    cards = [
        _card("note-a", "A", "<button onclick=\"openNote('note-b')\">B</button>"),
        _card("note-b", "B", "<button onclick=\"openNote('note-a')\">A</button>"),
    ]
    _, edges = _build_link_graph(cards)
    assert edges == [{"source": "note-a", "target": "note-b"}]


def test_graph_index_nodes_carry_id_title_type_tags():
    cards = [_card("note-a", "A", "", tags=["topic/x"])]
    index = _build_graph_index(cards, edges=[])
    assert index["nodes"] == [{"id": "note-a", "title": "A", "type": "concept", "tags": ["topic/x"]}]
    assert index["edges"] == []


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
