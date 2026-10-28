"""The Essays Atom feed (roadmap S18, docs/ESSAYS.md, "Metadata").

Atom's required elements (feed: id, title, updated, author; entry: id,
title, updated), that it lists the fixture essays, newest first, that an
entry's content is the full rendered essay plus its disclosure note and
references -- never the study companion or the YouTube episode -- and that
relative links (a Garden wikilink, an in-text citation's own anchor) come
out absolute, since a feed entry carries no notion of the page it came
from.
"""
import xml.etree.ElementTree as ET

import pytest

from engine.buildlog import reset_warnings
from engine.feed import ATOM_NS, build_atom_feed
from tests.test_essays import FIXTURE_DIR, _e01, _scan

SITE_URL = "https://example.org/"
AUTHOR = "Travis R. McKinzie"


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


def _tag(name):
    return f"{{{ATOM_NS}}}{name}"


def _feed():
    essays = _scan(FIXTURE_DIR)
    return ET.fromstring(build_atom_feed(essays, SITE_URL, AUTHOR)), essays


def _entry_by_title(root, title):
    return next(e for e in root.findall(_tag("entry")) if e.find(_tag("title")).text == title)


def test_the_feed_carries_every_atom_required_element():
    root, essays = _feed()
    assert root.tag == _tag("feed")
    assert root.find(_tag("id")).text == f"{SITE_URL}essays/feed.xml"
    assert root.find(_tag("title")).text == "Essays"
    assert root.find(_tag("updated")).text
    assert root.find(_tag("author")).find(_tag("name")).text == AUTHOR
    links = {link.get("rel"): link.get("href") for link in root.findall(_tag("link"))}
    assert links == {"self": f"{SITE_URL}essays/feed.xml", "alternate": f"{SITE_URL}essays/"}

    entries = root.findall(_tag("entry"))
    assert len(entries) == len(essays) == 2
    for entry in entries:
        assert entry.find(_tag("id")).text
        assert entry.find(_tag("title")).text
        assert entry.find(_tag("updated")).text


def test_the_feed_lists_the_fixture_essay_newest_first():
    root, essays = _feed()
    titles = [e.find(_tag("title")).text for e in root.findall(_tag("entry"))]
    assert titles == [e["title"] for e in essays]
    assert titles[0] == "Attention is a budget"   # published 2026-12-01, newest
    assert titles[1] == "Why loss looms larger"    # published 2026-11-20


def test_an_entrys_id_and_link_are_the_essays_absolute_permanent_url():
    root, _essays = _feed()
    e01 = _e01()
    entry = _entry_by_title(root, e01["title"])
    url = f"{SITE_URL}{e01['url']}"
    assert url == "https://example.org/essays/why-loss-looms-larger/"
    assert entry.find(_tag("id")).text == url
    assert entry.find(_tag("link")).attrib == {"rel": "alternate", "type": "text/html", "href": url}
    assert entry.find(_tag("published")).text == "2026-11-20T00:00:00Z"
    assert entry.find(_tag("updated")).text == "2026-11-22T00:00:00Z"
    assert entry.find(_tag("summary")).text.startswith("Losses weigh more than equal gains")


def test_an_essay_without_updated_uses_published_for_both():
    root, _essays = _feed()
    entry = _entry_by_title(root, "Attention is a budget")
    assert entry.find(_tag("published")).text == entry.find(_tag("updated")).text == "2026-12-01T00:00:00Z"


def test_content_is_the_essay_its_disclosure_and_references_never_the_companion_or_episode():
    root, _essays = _feed()
    content_el = _entry_by_title(root, "Why loss looms larger").find(_tag("content"))
    assert content_el.get("type") == "html"
    content = content_el.text

    # The essay's own body, and its disclosure note and APA 7 list.
    assert "Hand someone a coffee mug" in content
    assert "<h2>How this essay was made</h2>" in content
    assert "I wrote this essay by hand" in content
    assert "<h2>References</h2>" in content
    assert '<li id="ref-kahneman1979">' in content

    # Never the one zone with AI output, and never the episode.
    assert "essay-companion" not in content and "AI-generated study companion" not in content
    assert "essay-listen" not in content and "Play episode" not in content
    assert "youtube" not in content.lower()


def test_content_rewrites_relative_links_to_absolute():
    root, _essays = _feed()
    content = _entry_by_title(root, "Why loss looms larger").find(_tag("content")).text
    # A Garden wikilink, built from site_root ("/"), becomes the site's own
    # absolute address; an in-text citation's own "#ref-<key>" anchor
    # becomes the essay's absolute URL plus that same fragment.
    assert 'href="https://example.org/garden.html#note-active-recall"' in content
    assert 'href="https://example.org/essays/why-loss-looms-larger/#ref-kahneman1979"' in content
    assert 'href="/garden.html' not in content
    assert 'href="#' not in content
    # Already-absolute links (a DOI) are left exactly as they were.
    assert 'href="https://doi.org/10.2307/1914185"' in content


def test_the_web_style_essay_ends_with_a_sources_section_linking_straight_to_its_sources():
    root, _essays = _feed()
    content = _entry_by_title(root, "Attention is a budget").find(_tag("content")).text
    assert "<h2>Sources</h2>" in content
    assert "<h2>References</h2>" not in content
    assert 'href="https://doi.org/10.2307/1914185"' in content
    assert 'href="#ref-' not in content
