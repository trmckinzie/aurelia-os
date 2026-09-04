"""Allowlist-sanitizer tests for note-authored HTML (audit finding #21).

Split in two: the unit half pins engine/sanitize.py's behavior directly, and
the end-to-end half builds a vault under pytest's tmp_path, runs the real
_scan_vault(), and asserts on what would actually be written into
gardentemplate.html's #data-storage block -- the sink a visitor's browser
parses at page load. The real vault/ is never read or written.
"""
import pytest

from engine import pipeline
from engine.sanitize import sanitize_note_html


# --- Unit: what the sanitizer removes ---------------------------------

@pytest.mark.parametrize("payload", [
    "<script>alert(1)</script>",
    # Entity-encoded, because openNote() decodes entities out of the stored
    # body before handing it to marked.parse() -- see engine/sanitize.py.
    # A sanitizer that only escaped would be undone by that decode.
    "&lt;script&gt;alert(1)&lt;/script&gt;",
    "<iframe src='//evil.example'></iframe>",
    "<object data='evil.swf'></object>",
    "<embed src='evil.swf'>",
    "<svg onload=alert(1)>",
    "<style>body{display:none}</style>",
])
def test_dangerous_elements_are_removed(payload):
    out = sanitize_note_html(payload)
    assert "<script" not in out
    assert "<iframe" not in out
    assert "<object" not in out
    assert "<embed" not in out
    assert "<svg" not in out
    assert "<style" not in out


def test_script_contents_are_removed_not_just_its_tags():
    # Dropping the tags but keeping the text would publish the payload as
    # visible source -- and, after the entity decode in openNote(), marked
    # would hand it straight back to the parser.
    assert "alert(1)" not in sanitize_note_html("<script>alert(1)</script>")


def test_event_handler_attributes_are_stripped():
    out = sanitize_note_html('<img src="a.png" onerror="alert(1)">')
    assert "onerror" not in out
    assert "alert(1)" not in out
    assert "<img" in out and 'src="a.png"' in out


def test_javascript_url_is_stripped_from_href():
    out = sanitize_note_html('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in out
    assert ">click</a>" in out          # the link text survives, the URL does not


def test_data_url_is_stripped_from_href_and_src():
    assert "data:" not in sanitize_note_html(
        '<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>')
    assert "data:" not in sanitize_note_html(
        '<img src="data:text/html,<script>alert(1)</script>">')


# --- Unit: what the sanitizer must NOT break --------------------------

@pytest.mark.parametrize("markdown", [
    "## A heading",
    "**bold** and *italic* and `inline code`",
    "> A blockquote line",                       # `>` must survive: the
                                                 # extractors key off it
    "| a | b |\n|---|---|\n| 1 | 2 |",
    "```python\nprint('hi')\n```",
    "- one\n- two\n",
    "[a link](https://example.com)",
    "![alt](assets/images/x.png)",
    "[[Working Memory]] and [[Target|Label]]",   # wikilinks, pre-conversion
    "Newell & Simon, and a < b, and 3<5",
])
def test_ordinary_markdown_survives_unchanged(markdown):
    # Byte-identical, not merely "close enough" -- this body is markdown that
    # marked.parse() renders client-side, and it is also what the extractors
    # in engine/extractors.py parse to build the cards.
    assert sanitize_note_html(markdown) == markdown


def test_safe_html_in_a_note_is_preserved():
    assert sanitize_note_html("<details><summary>S</summary>body</details>") == \
        "<details><summary>S</summary>body</details>"


def test_external_link_keeps_its_href():
    out = sanitize_note_html('<a href="https://example.com">ok</a>')
    assert 'href="https://example.com"' in out


def test_empty_body_is_returned_as_is():
    assert sanitize_note_html("") == ""


# --- End to end: through the real scan, into the real sink ------------

def _write_note(vault, relpath, frontmatter, body):
    path = vault / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def _body_for(tmp_path, monkeypatch, note_body):
    """Runs the real _scan_vault() over a one-note tmp_path vault and returns
    the card body that gardentemplate.html would emit into #data-storage."""
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/Hostile.md", "publish: true\ntype: concept", note_body)
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    garden_cards, _, _ = pipeline._scan_vault()
    assert len(garden_cards) == 1
    return garden_cards[0]["body"]


def test_script_in_a_note_never_reaches_the_published_body(tmp_path, monkeypatch):
    # #data-storage is display:none, which stops rendering, not parsing -- a
    # <script> there executes at page load whether or not anyone opens the
    # note. This is the finding's headline case.
    body = _body_for(tmp_path, monkeypatch,
                     "Intro text.\n\n<script>alert(1)</script>\n\nOutro text.")
    assert "<script" not in body
    assert "alert(1)" not in body
    assert "Intro text." in body and "Outro text." in body


def test_onerror_attribute_never_reaches_the_published_body(tmp_path, monkeypatch):
    body = _body_for(tmp_path, monkeypatch, '<img src="x.png" onerror="alert(1)">')
    assert "onerror" not in body
    assert "alert(1)" not in body


def test_javascript_href_never_reaches_the_published_body(tmp_path, monkeypatch):
    body = _body_for(tmp_path, monkeypatch, '<a href="javascript:alert(1)">click me</a>')
    assert "javascript:" not in body
    assert "click me" in body


def test_ordinary_formatting_still_renders_in_the_published_body(tmp_path, monkeypatch):
    note = (
        "## Heading\n\n"
        "**bold** and `code`\n\n"
        "> a blockquote\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "[a link](https://example.com)\n"
    )
    body = _body_for(tmp_path, monkeypatch, note)
    for fragment in ("## Heading", "**bold**", "`code`", "> a blockquote",
                     "| a | b |", "[a link](https://example.com)"):
        assert fragment in body


def test_engine_injected_wikilink_buttons_survive_sanitizing(tmp_path, monkeypatch):
    # The ordering guard. Wikilink buttons carry an onclick and <button> is
    # not on nh3's allowlist, so sanitizing the *finished* body instead of
    # the raw note would delete every link in the vault. If this fails, the
    # sanitize step has been moved after process_wikilinks().
    vault = tmp_path / "vault"
    _write_note(vault, "10_GARDEN/A.md", "publish: true\ntype: concept",
                "See [[B]] for more.")
    _write_note(vault, "10_GARDEN/B.md", "publish: true\ntype: concept", "Body.")
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    garden_cards, _, _ = pipeline._scan_vault()

    body = next(c["body"] for c in garden_cards if c["id"] == "note-a")
    assert "<button onclick=\"openNote('note-b')\"" in body
