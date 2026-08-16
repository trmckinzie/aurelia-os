from engine.pipeline import _build_backlinks_index


def _card(note_id, title, body):
    return {"id": note_id, "title": title, "body": body}


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
