"""Essays as a content type (roadmap S15, docs/ESSAYS.md).

Every done_when item of S15 has a test here or in tests/browser/essays.spec.mjs:
the index and page contents, the Garden links, no essay ever becoming a
Garden card, the live site unchanged while no essay is published, and the
privacy checks that fail a build *without* --strict, each one.

The fixture essay lives under tests/fixtures/essays/, never in the vault
(vault/30_ESSAYS does not exist yet). Every other folder these tests read
is built under pytest's tmp_path.
"""
import datetime
import math
import os
import re

import pytest
from markupsafe import Markup

import build
from engine import essays, pipeline
from engine.buildlog import get_warnings, reset_warnings
from engine.config import ROOT_DIR, env
from engine.content import make_id
from engine.essays import (
    EssayError,
    check_denied_hosts,
    check_essay_frontmatter,
    check_essays_folder,
    check_reference_records,
    essays_path,
    long_date,
    reading_minutes,
    scan_essays,
)
from tests.test_about import base_context, make_config

FIXTURE_DIR = os.path.join(ROOT_DIR, "tests", "fixtures", "essays")
FIXTURE_NOTE = os.path.join(FIXTURE_DIR, "E01 Why loss looms larger.md")

# The Garden notes the fixture essay links to. A real build resolves them
# against the vault; these tests resolve them by id so they need no vault.
GARDEN_IDS = {"note-cognitive-psychology", "note-active-recall", "note-other"}
DISCIPLINE_IDS = {"note-cognitive-psychology"}

GOOD_FRONTMATTER = """\
type: essay
id: E02
title: "A second essay"
slug: a-second-essay
publish: true
published: 2026-12-04
disciplines: [psychology]
thesis: "One sentence."
citation_style: apa7
methods:
  drafted_on: reMarkable
  edited_in: Google Docs
  ai_roles: [source search]
"""


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


def _write(folder, name, text):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _essay_note(frontmatter=GOOD_FRONTMATTER, body="A short body.\n"):
    return f"---\n{frontmatter}---\n{body}"


def _scan(folder, known_ids=GARDEN_IDS, discipline_ids=DISCIPLINE_IDS, site_root="/"):
    return scan_essays(str(folder), make_id, known_ids, discipline_ids=discipline_ids, site_root=site_root)


def _problems(folder):
    _essays, problems = check_essays_folder(str(folder))
    return [message for _rel, message in problems]


# --- the fixture essay, as the templates receive it -----------------------

def test_fixture_essay_scans_with_its_contract_fields():
    [essay] = _scan(FIXTURE_DIR)
    assert essay["id"] == "E01"
    assert essay["slug"] == "why-loss-looms-larger"
    assert essay["url"] == "essays/why-loss-looms-larger/"
    assert essay["title"] == "Why loss looms larger"
    assert essay["published"] == datetime.date(2026, 11, 20)
    assert essay["published_text"] == "Friday, 20 November 2026"
    assert essay["updated_text"] == "Sunday, 22 November 2026"
    assert essay["thesis"].startswith("Losses weigh more than equal gains")
    assert essay["citation_style"] == "apa7"
    assert essay["methods"]["ai_roles"] == ["source search", "source summaries", "citation audit"]
    # The records as written (the disclosure note counts them, S17), and
    # the APA 7 list built from them (S16, tests/test_citations.py).
    assert [r["id"] for r in essay["references"]][:2] == ["kahneman1979", "kahneman1979a"]
    assert len(essay["reference_list"]) == len(essay["references"]) == 8
    assert isinstance(essay["body_html"], Markup)


def test_reading_time_is_words_over_230_rounded_up():
    with open(FIXTURE_NOTE, encoding="utf-8") as f:
        body = f.read().split("---\n", 2)[2]
    words = len(re.findall(r"\S+", re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", body)))
    [essay] = _scan(FIXTURE_DIR)
    assert essay["reading_minutes"] == math.ceil(words / 230)
    assert reading_minutes(" ".join(["word"] * 230)) == 1
    assert reading_minutes(" ".join(["word"] * 231)) == 2
    assert reading_minutes("") == 1


def test_long_date_carries_the_weekday():
    assert long_date(datetime.date(2026, 11, 20)) == "Friday, 20 November 2026"
    assert long_date(datetime.date(2026, 3, 1)) == "Sunday, 1 March 2026"


def test_discipline_labels_link_to_a_published_discipline_note_only():
    [essay] = _scan(FIXTURE_DIR)
    assert essay["disciplines"] == [
        {"label": "cognitive psychology", "href": "/garden.html#note-cognitive-psychology"},
        {"label": "philosophy", "href": None},
    ]


def test_body_renders_markdown_with_garden_links():
    [essay] = _scan(FIXTURE_DIR)
    html = str(essay["body_html"])
    assert "<h2>The shape of the asymmetry</h2>" in html
    assert "<blockquote>" in html and "<ul>" in html
    assert ('<a href="/garden.html#note-cognitive-psychology" class="essay-garden-link" '
            'data-garden-note="note-cognitive-psychology">Cognitive Psychology</a>') in html
    assert 'data-garden-note="note-active-recall">active recall</a>' in html
    assert "[[" not in html
    assert get_warnings() == []


def test_garden_links_follow_the_site_root():
    [essay] = _scan(FIXTURE_DIR, site_root="/aurelia-os/")
    assert 'href="/aurelia-os/garden.html#note-active-recall"' in str(essay["body_html"])
    assert essay["disciplines"][0]["href"] == "/aurelia-os/garden.html#note-cognitive-psychology"


def test_a_wikilink_to_a_missing_or_unpublished_note_warns(tmp_path):
    _write(tmp_path, "E02 Second.md", _essay_note(body="See [[Nowhere]] and [[Other|the other]].\n"))
    [essay] = _scan(tmp_path, known_ids={"note-other"})
    html = str(essay["body_html"])
    assert '<span class="essay-missing-link" title="Not yet published">Nowhere</span>' in html
    assert 'data-garden-note="note-other">the other</a>' in html
    assert get_warnings() == ["Essay E02: [[Nowhere]] is not a published Garden note"]


def test_raw_html_in_an_essay_renders_as_text_never_as_markup(tmp_path):
    # Raw HTML is off in markdown-it, so a tag typed into an essay is shown
    # to the author as text rather than trusted; nh3 then cleans the
    # rendered page as a second gate.
    _write(tmp_path, "E02 Second.md", _essay_note(
        body="Text <script>alert(1)</script> and <b onclick=\"x()\">bold</b> here.\n"))
    [essay] = _scan(tmp_path)
    html = str(essay["body_html"])
    assert "<script" not in html and "<b" not in html
    assert "&lt;script&gt;" in html and "&lt;b onclick=" in html
    assert "<b onclick" not in html


def test_autolinks_and_doi_links_survive_rendering(tmp_path):
    # The Garden's nh3 pass reads Markdown as HTML and would delete an
    # angle-bracket autolink outright; essays render first, so it is a link.
    _write(tmp_path, "E02 Second.md", _essay_note(
        body="See <https://doi.org/10.2307/1914185> and [the paper](https://example.org/p) and [bad](javascript:alert(1)).\n"))
    [essay] = _scan(tmp_path)
    html = str(essay["body_html"])
    # nh3 adds rel="noopener noreferrer" to every outbound link.
    assert re.search(r'<a href="https://doi\.org/10\.2307/1914185"[^>]*>https://doi\.org/10\.2307/1914185</a>', html)
    assert re.search(r'<a href="https://example\.org/p"[^>]*>the paper</a>', html)
    assert "href=\"javascript" not in html   # refused by markdown-it; the text stays literal


def test_a_wikilink_in_code_or_a_link_title_stays_literal(tmp_path):
    _write(tmp_path, "E02 Second.md", _essay_note(
        body="Write `[[Other]]` in Obsidian.\n\n```\n[[Nowhere]]\n```\n\n"
             "[text](https://example.org \"[[Other|x]]\") and a real [[Other|link]].\n"))
    [essay] = _scan(tmp_path, known_ids={"note-other"})
    html = str(essay["body_html"])
    assert "<code>[[Other]]</code>" in html
    assert "[[Nowhere]]" in html
    assert 'title="[[Other|x]]"' in html
    assert html.count("essay-garden-link") == 1 and ">link</a>" in html
    assert get_warnings() == []


def test_an_aligned_table_carries_no_inline_style_attribute(tmp_path):
    _write(tmp_path, "E02 Second.md", _essay_note(body="| a | b |\n|:--|--:|\n| 1 | 2 |\n"))
    [essay] = _scan(tmp_path)
    html = str(essay["body_html"])
    assert "<table>" in html and "style=" not in html


def test_essays_are_ordered_newest_first(tmp_path):
    _write(tmp_path, "E02 Older.md", _essay_note(GOOD_FRONTMATTER.replace("2026-12-04", "2026-01-05")))
    _write(tmp_path, "E03 Newer.md", _essay_note(
        GOOD_FRONTMATTER.replace("E02", "E03").replace("a-second-essay", "newer").replace("2026-12-04", "2026-06-01")))
    assert [e["id"] for e in _scan(tmp_path)] == ["E03", "E02"]


def test_an_absent_folder_is_no_essays(tmp_path):
    assert _scan(tmp_path / "missing") == []
    assert check_essays_folder(str(tmp_path / "missing")) == ([], [])


def test_essays_path_reads_the_environment_override(monkeypatch):
    monkeypatch.delenv(essays.ESSAYS_DIR_ENV, raising=False)
    assert essays_path("/v") == os.path.join("/v", "30_ESSAYS")
    monkeypatch.setenv(essays.ESSAYS_DIR_ENV, "/elsewhere")
    assert essays_path("/v") == "/elsewhere"


# --- the privacy checks (each fails every build, strict or not) ----------

def test_a_draft_in_the_essays_folder_fails(tmp_path):
    _write(tmp_path, "E02 Draft.md", _essay_note(GOOD_FRONTMATTER.replace("publish: true", "publish: false")))
    assert any("a draft never enters the Essays folder" in p for p in _problems(tmp_path))
    with pytest.raises(EssayError, match="draft"):
        _scan(tmp_path)


def test_a_note_without_a_publish_flag_or_quoting_it_fails(tmp_path):
    _write(tmp_path, "E02 No flag.md", _essay_note(GOOD_FRONTMATTER.replace("publish: true\n", "")))
    assert any("missing required field 'publish'" in p for p in _problems(tmp_path))
    _write(tmp_path, "E02 No flag.md", _essay_note(GOOD_FRONTMATTER.replace("publish: true", 'publish: "true"')))
    assert any("publish: must be true" in p for p in _problems(tmp_path))


@pytest.mark.parametrize("extra", ["status: draft", "sources_total: 14", "abstract: a summary", "notes: private"])
def test_an_unknown_frontmatter_field_fails(tmp_path, extra):
    _write(tmp_path, "E02 Extra.md", _essay_note(GOOD_FRONTMATTER + extra + "\n"))
    problems = _problems(tmp_path)
    assert any("unknown field" in p for p in problems), problems
    with pytest.raises(EssayError, match="unknown field"):
        _scan(tmp_path)


@pytest.mark.parametrize("url", [
    "https://notebooklm.google.com/notebook/abc123",
    "https://notebooklm.google/notebook/abc123",
    "https://drive.google.com/file/d/xyz/view",
    "https://docs.google.com/document/d/xyz/edit",
    "https://docs.google.com/spreadsheets/d/xyz",
    "https://sheets.google.com/x",
    "https://gemini.google.com/app/abc",
    "https://my.remarkable.com/connect",
    "https://drive.usercontent.google.com/download?id=1",
    "https://docs.googleusercontent.com/download/x",
    "https://lh3.googleusercontent.com/d/1abc",
    "https://g.co/gemini/share/abcdef",
    "https://aistudio.google.com/prompts/x",
    "notebooklm.google.com/notebook/abc123",   # no scheme: still a leak
    "see ...docs.google.com/document/d/abc",   # pasted after an ellipsis
])
def test_a_private_workflow_link_anywhere_in_an_essay_fails(tmp_path, url):
    _write(tmp_path, "E02 Link.md", _essay_note(body=f"Sources: {url}\n"))
    problems = _problems(tmp_path)
    assert any("must never enter the repository" in p for p in problems), problems
    with pytest.raises(EssayError, match="must never enter the repository"):
        _scan(tmp_path)


def test_a_private_link_in_frontmatter_or_the_reference_file_fails(tmp_path):
    _write(tmp_path, "E02 Link.md", _essay_note(
        GOOD_FRONTMATTER + "companion:\n  - kind: audio\n    label: Overview\n    url: https://drive.google.com/file/d/1/view\n"))
    # Whole messages, not substring checks, so the assertion cannot be read
    # as URL sanitisation by a scanner (CodeQL flagged the `host in p` form).
    denied = "names a host that must never enter the repository: "
    assert denied + "drive.google.com" in _problems(tmp_path)
    _write(tmp_path, "E02 Link.md", _essay_note())
    _write(tmp_path, "E02.refs.yaml", "- id: k\n  type: book\n  URL: https://gemini.google.com/share/1\n")
    assert denied + "gemini.google.com" in _problems(tmp_path)


def test_ordinary_hosts_and_the_word_remarkable_pass():
    assert check_denied_hosts("Drafted on a reMarkable tablet; see https://doi.org/10.1 and https://www.google.com/") == []
    assert check_denied_hosts("https://mirror-docs.google.com/ is another host") == []
    assert check_denied_hosts("https://docs.google.com/x") == ["docs.google.com"]


@pytest.mark.parametrize("name", ["Kahneman 1979.pdf", "diagram.png", "Source Ledger.csv", "notes.txt", "nested/paper.PDF"])
def test_any_file_other_than_md_and_yaml_in_the_folder_fails(tmp_path, name):
    _write(tmp_path, "E02 Second.md", _essay_note())
    _write(tmp_path, name, "not an essay")
    problems = _problems(tmp_path)
    assert any("only .md and .yaml" in p for p in problems), problems
    with pytest.raises(EssayError, match="only .md and .yaml"):
        _scan(tmp_path)


def test_an_essay_or_reference_file_in_a_subfolder_fails(tmp_path):
    _write(tmp_path, "archive/E02 Sub.md", _essay_note())
    _write(tmp_path, "archive/E02.refs.yaml", "[]\n")
    problems = _problems(tmp_path)
    assert len([p for p in problems if "not in a subfolder" in p]) == 2


def test_a_linked_essays_folder_fails(tmp_path):
    outside = tmp_path / "outside"
    _write(outside, "E02 Sub.md", _essay_note())
    link = tmp_path / "essays"
    os.symlink(outside, link, target_is_directory=True)
    assert any("is a link" in p for p in _problems(link))
    with pytest.raises(EssayError, match="is a link"):
        _scan(link)


def test_essays_path_finds_a_case_variant_of_the_folder_and_refuses_two(tmp_path, monkeypatch):
    monkeypatch.delenv(essays.ESSAYS_DIR_ENV, raising=False)
    (tmp_path / "30_essays").mkdir()
    assert essays_path(str(tmp_path)) == os.path.join(str(tmp_path), "30_essays")
    try:
        (tmp_path / "30_Essays").mkdir()
    except FileExistsError:
        pytest.skip("case-insensitive filesystem")
    with pytest.raises(EssayError, match="more than one spelling"):
        essays_path(str(tmp_path))


def test_os_metadata_files_do_not_fail_the_folder(tmp_path):
    _write(tmp_path, "E02 Second.md", _essay_note())
    _write(tmp_path, ".DS_Store", "")
    assert _problems(tmp_path) == []
    assert len(_scan(tmp_path)) == 1


@pytest.mark.parametrize("field", ["abstract", "annote", "note"])
def test_a_reference_record_with_a_summary_field_fails(tmp_path, field):
    _write(tmp_path, "E02 Second.md", _essay_note())
    _write(tmp_path, "E02.refs.yaml", f"- id: kahneman1979\n  type: article-journal\n  {field}: AI summary of the paper\n")
    problems = _problems(tmp_path)
    assert any(f"unknown field '{field}'" in p for p in problems), problems
    with pytest.raises(EssayError, match=field):
        _scan(tmp_path)
    assert check_reference_records([{"id": "k", field: "x"}]) != []
    assert check_reference_records([{"id": "k", "type": "book", "title": "T", "DOI": "10.1/x", "verified": True}]) == []


def test_a_reference_file_must_belong_to_an_essay_beside_it(tmp_path):
    _write(tmp_path, "E02 Second.md", _essay_note())
    _write(tmp_path, "E09.refs.yaml", "[]\n")
    assert any("no essay with id E09" in p for p in _problems(tmp_path))
    _write(tmp_path, "export.yaml", "[]\n")
    assert any("must be an essay's reference file" in p for p in _problems(tmp_path))


def test_the_reference_file_is_read_when_present(tmp_path):
    _write(tmp_path, "E02 Second.md", _essay_note())
    _write(tmp_path, "E02.refs.yaml", "- id: kahneman1979\n  type: article-journal\n  verified: true\n")
    [essay] = _scan(tmp_path)
    assert essay["references"] == [{"id": "kahneman1979", "type": "article-journal", "verified": True}]


# --- the rest of the contract ---------------------------------------------

def test_the_fixture_frontmatter_meets_the_contract():
    with open(FIXTURE_NOTE, encoding="utf-8") as f:
        raw, _body = essays._split_frontmatter(f.read())
    assert check_essay_frontmatter(raw) == []


@pytest.mark.parametrize("change, message", [
    (("id: E02", "id: 2"), "id: must be E plus two digits"),
    (("slug: a-second-essay", "slug: A Second Essay"), "slug: must be lowercase"),
    (("published: 2026-12-04", "published: soon"), "published: must be a date"),
    (("citation_style: apa7", "citation_style: mla"), "citation_style: must be one of"),
    (("ai_roles: [source search]", "ai_roles: [writing]"), "unknown role 'writing'"),
    (("ai_roles: [source search]", "ai_roles: [source search, source search]"), "listed twice"),
    (("disciplines: [psychology]", "disciplines: []"), "disciplines: must be a non-empty list"),
    (("type: essay", "type: concept"), "type: expected 'essay'"),
    (("  edited_in: Google Docs\n", ""), "methods.edited_in"),
])
def test_contract_violations_are_named(change, message):
    old, new = change
    raw, _ = essays._split_frontmatter(_essay_note(GOOD_FRONTMATTER.replace(old, new)))
    problems = check_essay_frontmatter(raw)
    assert any(message in p for p in problems), problems


def test_updated_must_follow_published_and_the_thesis_is_bounded():
    raw, _ = essays._split_frontmatter(_essay_note(GOOD_FRONTMATTER + "updated: 2026-12-01\n"))
    assert any("updated: must be on or after published" in p for p in check_essay_frontmatter(raw))
    raw, _ = essays._split_frontmatter(_essay_note(GOOD_FRONTMATTER.replace('"One sentence."', '"' + "x" * 201 + '"')))
    assert any("the limit is 200" in p for p in check_essay_frontmatter(raw))


def test_companion_and_youtube_are_checked():
    raw, _ = essays._split_frontmatter(_essay_note(
        GOOD_FRONTMATTER + "companion:\n  - kind: podcast\n    label: Overview\n    url: http://media.example.com/a.m4a\n"
        "youtube: https://vimeo.com/1\n"))
    problems = check_essay_frontmatter(raw)
    assert any("companion[0].kind" in p for p in problems)
    assert any("companion[0].url: must be an https URL" in p for p in problems)
    assert any("youtube: must be a YouTube address" in p for p in problems)
    raw, _ = essays._split_frontmatter(_essay_note(
        GOOD_FRONTMATTER + "companion:\n  - kind: audio\n    label: Audio overview\n    url: https://media.example.com/a.m4a\n"
        "youtube: https://www.youtube.com/watch?v=XXXXXXXXXXX\n"))
    assert check_essay_frontmatter(raw) == []


def test_duplicate_ids_and_slugs_fail(tmp_path):
    _write(tmp_path, "E02 One.md", _essay_note())
    _write(tmp_path, "E02 Two.md", _essay_note(GOOD_FRONTMATTER.replace("a-second-essay", "two")))
    assert any("id E02 is already used" in p for p in _problems(tmp_path))
    _write(tmp_path, "E02 Two.md", _essay_note(GOOD_FRONTMATTER.replace("E02", "E03")))
    assert any("slug 'a-second-essay' is already used" in p for p in _problems(tmp_path))


def test_malformed_or_missing_frontmatter_fails(tmp_path):
    _write(tmp_path, "E02 Broken.md", "---\ntitle: [unclosed\n---\nbody\n")
    assert any("malformed frontmatter" in p for p in _problems(tmp_path))
    _write(tmp_path, "E02 Broken.md", "Just prose, no frontmatter.\n")
    assert any("no frontmatter" in p for p in _problems(tmp_path))


# --- the vault walk: essays are never Garden cards -----------------------

def _vault_note(vault, relpath, frontmatter, body="Body.\n"):
    return _write(vault, relpath, f"---\n{frontmatter}\n---\n{body}")


@pytest.mark.parametrize("folder", ["30_ESSAYS", "30_Essays", "30_essays"])
def test_the_essays_folder_never_yields_a_garden_card(tmp_path, monkeypatch, folder):
    vault = tmp_path / "vault"
    _vault_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _write(vault, f"{folder}/E01 An essay.md", _essay_note())
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    garden_cards, _, _ = pipeline._scan_vault()
    assert [c["title"] for c in garden_cards] == ["Real Note"]
    assert "note-e01-an-essay" not in {c["id"] for c in garden_cards}


@pytest.mark.parametrize("publish", ["true", "false"])
def test_an_essay_outside_the_essays_folder_fails_the_build(tmp_path, monkeypatch, publish):
    vault = tmp_path / "vault"
    _vault_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _vault_note(vault, "10_GARDEN/12_Concepts/E01 Stray.md", f"publish: {publish}\ntype: essay")
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    with pytest.raises(EssayError, match="outside 30_ESSAYS"):
        pipeline._scan_vault()


@pytest.mark.parametrize("folder", ["20_AURELIA", "20_Aurelia", "20_AURELIA/nested"])
def test_an_essay_in_the_pruned_agent_draft_folder_still_fails_the_build(tmp_path, monkeypatch, folder):
    # 20_AURELIA is pruned from publishing, not from the privacy checks: a
    # draft parked there is still committed to a public repo.
    vault = tmp_path / "vault"
    _vault_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _vault_note(vault, f"{folder}/E02 Draft.md", "publish: false\ntype: essay",
                body="https://docs.google.com/document/d/LEAK\n")
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    with pytest.raises(EssayError, match="outside 30_ESSAYS"):
        pipeline._scan_vault()


def test_a_broken_frontmatter_block_cannot_hide_an_essay_outside_the_folder(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    _vault_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    _vault_note(vault, "00_Inbox/E02 Broken.md", "title: [unclosed\ntype: essay\npublish: true")
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    with pytest.raises(EssayError, match="outside 30_ESSAYS"):
        pipeline._scan_vault()


def test_scan_garden_hands_back_the_resolver_and_known_ids(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    _vault_note(vault, "10_GARDEN/Dopamine (Reward).md", 'publish: true\ntype: concept\naliases: ["Dopamine"]')
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    scan = pipeline._scan_garden()
    assert scan.known_ids == {"note-dopamine-reward"}
    assert scan.resolve("Dopamine") == "note-dopamine-reward"


# --- a build without --strict stops on each privacy problem ---------------

def _stub_build(monkeypatch, tmp_path, essays_dir):
    """build_all() with every step that writes stubbed out, a one-note vault
    and the Essays folder under test. The scan itself is real."""
    vault = tmp_path / "vault"
    _vault_note(vault, "10_GARDEN/Real Note.md", "publish: true\ntype: concept")
    monkeypatch.setattr(pipeline, "VAULT_PATH", str(vault))
    monkeypatch.setenv(essays.ESSAYS_DIR_ENV, str(essays_dir))
    for name in ("prepare_dist", "copy_vendor_assets", "generate_theme_css", "compile_css"):
        monkeypatch.setattr(pipeline, name, lambda: None)
    monkeypatch.setattr(pipeline, "_write_cname", lambda cfg: None)
    monkeypatch.setattr(pipeline, "publish_referenced_media", lambda referenced: None)
    monkeypatch.setattr(pipeline, "_render_pages", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "stamp_asset_versions", lambda dist: {})
    monkeypatch.setattr(pipeline, "apply_csp", lambda dist: {})
    monkeypatch.setattr(pipeline, "report_page_sizes", lambda: {})


@pytest.mark.parametrize("name, text, message", [
    ("E02 Draft.md", _essay_note(GOOD_FRONTMATTER.replace("publish: true", "publish: false")), "draft"),
    ("E02 Extra.md", _essay_note(GOOD_FRONTMATTER + "status: draft\n"), "unknown field 'status'"),
    ("E02 Link.md", _essay_note(body="https://notebooklm.google.com/notebook/1\n"), "notebooklm.google.com"),
    ("Kahneman 1979.pdf", "%PDF-1.4 not really", "only .md and .yaml"),
    ("E03.refs.yaml", "- id: k\n  abstract: summary\n", "unknown field 'abstract'"),
])
def test_a_build_without_strict_fails_on_a_privacy_problem(tmp_path, monkeypatch, name, text, message):
    folder = tmp_path / "essays"
    _write(folder, "E03 Fine.md", _essay_note(GOOD_FRONTMATTER.replace("E02", "E03").replace("a-second-essay", "fine")))
    _write(folder, name, text)
    _stub_build(monkeypatch, tmp_path, folder)
    with pytest.raises(EssayError, match=re.escape(message)):
        pipeline.build_all(sort_dropzone=False, strict=False)


def test_a_build_without_strict_passes_a_clean_essays_folder(tmp_path, monkeypatch):
    folder = tmp_path / "essays"
    _write(folder, "E02 Fine.md", _essay_note())
    _stub_build(monkeypatch, tmp_path, folder)
    captured = {}
    monkeypatch.setattr(pipeline, "_render_pages", lambda *a, **k: captured.update(k))
    pipeline.build_all(sort_dropzone=False, strict=False)
    assert [e["id"] for e in captured["essays"]] == ["E02"]


# --- citations: a strict build stops, a local one warns (S16) -------------

_ONE_RECORD = """\
- id: thaler1980
  type: article-journal
  author:
    - {family: Thaler, given: Richard H.}
  issued: 1980
  title: Toward a positive theory of consumer choice
  container-title: Journal of Economic Behavior & Organization
  volume: 1
  page: 39-60
  verified: true
"""


@pytest.mark.parametrize("body, message", [
    ("Loss looms larger [@thaler1980; @kahneman1979].\n", "cites 'kahneman1979', which has no record in E02.refs.yaml"),
    ("A body that cites nothing.\n", "reference 'thaler1980' in E02.refs.yaml is cited nowhere in the essay"),
])
def test_a_citation_problem_fails_the_strict_build_and_only_warns_without_it(tmp_path, monkeypatch, body, message):
    folder = tmp_path / "essays"
    _write(folder, "E02 Cited.md", _essay_note(body=body))
    _write(folder, "E02.refs.yaml", _ONE_RECORD)
    _stub_build(monkeypatch, tmp_path, folder)
    with pytest.raises(pipeline.StrictBuildError):
        pipeline.build_all(sort_dropzone=False, strict=True)
    assert any(message in w for w in get_warnings()), get_warnings()

    reset_warnings()
    pipeline.build_all(sort_dropzone=False, strict=False)    # a local preview still builds
    assert any(message in w for w in get_warnings())


def test_a_fully_cited_essay_passes_the_strict_build(tmp_path, monkeypatch):
    folder = tmp_path / "essays"
    _write(folder, "E02 Cited.md", _essay_note(body="As @thaler1980 argued [@thaler1980, p. 44].\n"))
    _write(folder, "E02.refs.yaml", _ONE_RECORD)
    _stub_build(monkeypatch, tmp_path, folder)
    pipeline.build_all(sort_dropzone=False, strict=True)
    assert get_warnings() == []


def test_a_reference_record_without_verified_fails_every_build(tmp_path, monkeypatch):
    folder = tmp_path / "essays"
    _write(folder, "E02 Cited.md", _essay_note(body="[@thaler1980]\n"))
    _write(folder, "E02.refs.yaml", _ONE_RECORD.replace("  verified: true\n", ""))
    _stub_build(monkeypatch, tmp_path, folder)
    with pytest.raises(EssayError, match=r"verified: required"):
        pipeline.build_all(sort_dropzone=False, strict=False)


def test_the_cli_reports_an_essay_error_as_a_failed_build(monkeypatch, capsys):
    def _fail(**kwargs):
        raise EssayError("Essays folder x: 1 problem(s)")

    monkeypatch.setattr(build, "build_all", _fail)
    assert build.main(["--no-sort"]) == 1
    assert "BUILD FAILED: Essays folder x" in capsys.readouterr().err


# --- the pages ------------------------------------------------------------

def _config():
    return {"site": {"name": "Site", "nav_label": "S", "domain": "example.com"}}


def test_essay_pages_exist_only_once_an_essay_is_published():
    assert pipeline._essay_pages(_config(), []) == []
    [essay] = _scan(FIXTURE_DIR)
    pages = pipeline._essay_pages(_config(), [essay])
    assert [(t, p.replace(os.sep, "/")) for t, p, _c in pages] == [
        ("pages/essaystemplate.html", "essays/index.html"),
        ("pages/essaytemplate.html", "essays/why-loss-looms-larger/index.html"),
    ]
    for _t, _p, context in pages:
        assert context["site_root"] == "/"
        assert context["active_page"] == "essays"
    assert pages[0][2]["page_path"] == "essays/"
    assert pages[1][2]["page_path"] == "essays/why-loss-looms-larger/"


def _render(template, **overrides):
    context = base_context(**{"essays_published": True, "site_root": "/", "page_path": None, **overrides})
    return env.get_template(template).render(**context)


def render_essays_index(**overrides):
    return _render("pages/essaystemplate.html", active_page="essays", essays=_scan(FIXTURE_DIR),
                   page_title="Essays", page_path="essays/", **overrides)


def render_essay_page(**overrides):
    [essay] = _scan(FIXTURE_DIR)
    return _render("pages/essaytemplate.html", active_page="essays", essay=essay,
                   page_title=essay["title"], page_path=essay["url"], **overrides)


def test_the_index_lists_title_weekday_date_disciplines_thesis_and_reading_time():
    html = render_essays_index()
    assert 'href="/essays/why-loss-looms-larger/">Why loss looms larger</a>' in html
    assert '<time datetime="2026-11-20">Friday, 20 November 2026</time>' in html
    assert "cognitive psychology" in html and "philosophy" in html
    assert "Losses weigh more than equal gains" in html
    assert re.search(r"\d+-minute read", html)
    assert 'aria-current="page"' in html and 'href="/essays/"' in html


def test_the_essay_page_shows_byline_dates_disciplines_and_body():
    config = make_config()
    config["site"] = {"name": "Site", "nav_label": "S", "domain": "example.org"}
    html = render_essay_page(config=config)
    assert '<h1 id="essay-title" class="display-lg text-aurelia-text mb-5">Why loss looms larger</h1>' in html
    assert '<p class="essay-byline text-base text-aurelia-text">Ada Lovelace</p>' in html
    assert "Friday, 20 November 2026" in html
    assert "Updated <time datetime=\"2026-11-22\">Sunday, 22 November 2026</time>" in html
    assert 'href="/garden.html#note-cognitive-psychology"' in html
    assert "<h2>The shape of the asymmetry</h2>" in html
    assert "<title>Why loss looms larger — " in html
    # S16: the citations link into an APA 7 reference list.
    assert '<h2 id="essay-references-title">References</h2>' in html
    assert ('(<a href="#ref-kahneman1979" class="essay-citation">Kahneman &amp; Tversky, 1979b</a>; '
            '<a href="#ref-thaler1980" class="essay-citation">Thaler, 1980</a>)') in html
    assert '<a href="#ref-kahneman1990" class="essay-citation">Kahneman et al. (1990)</a>' in html
    assert "essays@example.com" in html and "essay-missing-citation" not in html.split("</style>")[-1]
    entries = re.findall(r'<li id="(ref-[^"]+)">', html)
    assert entries == ["ref-apa2020", "ref-kahneman2011", "ref-kahneman1990", "ref-kahneman1979a",
                       "ref-kahneman1979", "ref-kahneman1982", "ref-steele2020", "ref-thaler1980"]
    for target in set(re.findall(r'href="#(ref-[^"]+)"', html)):
        assert target in entries
    assert '<link rel="canonical" href="https://example.org/essays/why-loss-looms-larger/">' in html


def test_the_essays_link_appears_only_once_an_essay_is_published():
    from tests.test_about import render_about
    without = render_about()                          # the live site today
    assert "essays/" not in without and "ESSAYS" not in without and ">Essays<" not in without
    with_essays = render_about(essays_published=True)
    assert with_essays.count('href="essays/"') == 3   # desktop nav, mobile menu, footer
    assert ">ESSAYS</a>" in with_essays and ">Essays</a>" in with_essays


def test_the_essay_page_has_no_inline_handlers_or_styles():
    from tests.test_no_inline_handlers import _assert_clean
    _assert_clean(render_essays_index(), "essays/index.html")
    _assert_clean(render_essay_page(), "essays/<slug>/index.html")


# --- a real build with the fixture essay ----------------------------------

_NODE_MODULES = os.path.join(ROOT_DIR, "node_modules")
_needs_node_modules = pytest.mark.skipif(
    not os.path.isdir(_NODE_MODULES), reason="node_modules/ not installed -- run `npm ci`")


def _build(tmp_path, monkeypatch, essays_dir, name):
    from engine import assets_pipeline, tailwind_build, theming, vendor
    output_dir = str(tmp_path / name)
    for module in (pipeline, theming, tailwind_build, assets_pipeline, vendor):
        monkeypatch.setattr(module, "OUTPUT_DIR", output_dir)
    monkeypatch.setenv(essays.ESSAYS_DIR_ENV, essays_dir)
    monkeypatch.setenv("GITHUB_REPOSITORY", "trmckinzie/aurelia-os")
    pipeline.build_all(sort_dropzone=False, strict=True)
    return output_dir


def _read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


@_needs_node_modules
def test_the_fixture_build_publishes_the_essay_pages_and_no_card(tmp_path, monkeypatch):
    dist = _build(tmp_path, monkeypatch, FIXTURE_DIR, "with-essays")
    index = _read(dist, "essays", "index.html")
    page = _read(dist, "essays", "why-loss-looms-larger", "index.html")
    lobby = _read(dist, "index.html")
    garden = _read(dist, "garden.html")

    assert "Why loss looms larger" in index and "Friday, 20 November 2026" in index
    assert 'href="/garden.html#note-active-recall"' in page
    assert 'class="essay-citation"' in page and '<li id="ref-kahneman1979">' in page

    # Never a Garden card, however the essay is typed.
    assert "note-why-loss-looms-larger" not in garden
    assert "Why loss looms larger" not in garden
    # The top-level pages link relatively, as they always have.
    assert "ESSAYS" in lobby and 'href="essays/"' in lobby

    # A filled policy with hashes, the same cache-busted URLs as the top
    # level, and nothing left unstamped two folders down.
    for html in (index, page):
        assert "@@csp@@" not in html and "@@asset:" not in html
        assert re.search(r"script-src 'self' 'sha256-", html)
        assert re.search(r"style-src 'self' 'sha256-", html)
    main_css = re.search(r"/assets/css/main\.css\?v=([0-9a-f]{10})", page).group(1)
    assert f"assets/css/main.css?v={main_css}" in lobby


@_needs_node_modules
def test_a_build_without_essays_changes_nothing_a_visitor_sees(tmp_path, monkeypatch):
    empty = tmp_path / "no-essays"
    empty.mkdir()
    dist = _build(tmp_path, monkeypatch, str(empty), "without-essays")
    assert not os.path.exists(os.path.join(dist, "essays"))
    for page in ("index.html", "garden.html", "about.html", "404.html"):
        html = _read(dist, page)
        assert "essays/" not in html, page
        assert "ESSAYS" not in html, page
