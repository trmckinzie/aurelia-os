"""The Essays Atom feed (roadmap S18, docs/ESSAYS.md, "Metadata").

Atom over RSS because its one specification requires the ids and update
dates a reader needs, and every feed reader supports it (docs/ESSAYS.md).
One function, build_atom_feed(), turns the essays engine/essays.py's
scan_essays() already returns (newest first) into the feed's bytes, which
engine/pipeline.py writes to dist/essays/feed.xml -- only once at least one
essay is published, the same guard the index and the nav item already use,
so the live site never advertises an empty feed.

Built with xml.etree.ElementTree, never string concatenation, so a title or
a thesis that happens to contain "&" or "<" is escaped the way the library
escapes XML text rather than by a hand-rolled substitution.

ENTRY IDS (docs/DECISIONS.md item 48)
--------------------------------------
An Atom id must be a permanent, dereferenceable IRI. This module uses the
essay's own absolute URL -- not a `tag:` URI -- because that URL is already
permanent by contract (docs/ESSAYS.md, "Pages and URLs": "An essay's URL is
permanent once published") and it is also the address worth dereferencing
to read the piece it names, which a `tag:` URI is not. Both the feed's own
id and each entry's id are built from site_url, the same absolute address
engine/pipeline.py's _site_url() gives the Person and Article JSON-LD and
the canonical link; a build with no site.domain configured has no such
address, so engine/pipeline.py never calls this module in that case.

ENTRY CONTENT
-------------
entry_content_html() is the full rendered essay plus its disclosure note
("How this essay was made") and its reference list -- never the study
companion or the YouTube episode, the one place AI output appears on the
page and the one media a feed reader should not be asked to fetch on the
essay's behalf. Relative links the essay body and reference list carry
(a Garden wikilink to site_root + "garden.html#id", an in-text citation's
"#ref-<key>" anchor) are rewritten absolute, since a feed entry is read
with no notion of the page it came from.
"""
import xml.etree.ElementTree as ET

from markupsafe import escape

ATOM_NS = "http://www.w3.org/2005/Atom"


def _rfc3339(value):
    """A date as the midnight-UTC timestamp Atom's `updated`/`published`
    elements need; an essay carries a date, not a time of day, so every
    entry is stamped at the start of its day."""
    return f"{value.isoformat()}T00:00:00Z"


def _absolutize(html, base, essay_url):
    """Rewrites the two relative forms essay HTML carries into absolute
    addresses: a site-root path (a Garden link, built from site_root, which
    is "/" on the real site) and a same-page fragment (an in-text citation
    linking to its own reference-list entry). Anything already absolute
    (a DOI link, a web-style citation's source link) matches neither
    pattern and is left alone."""
    html = html.replace('href="#', f'href="{essay_url}#')
    html = html.replace('href="/', f'href="{base}/')
    return html


def entry_content_html(essay, site_url):
    """One entry's <content>: the rendered essay, "How this essay was
    made", and the reference list ("Sources" in the web style), each with
    every relative link made absolute. Never the companion or the episode.
    """
    base = site_url.rstrip("/")
    essay_url = f"{base}/{essay['url']}"
    parts = [_absolutize(str(essay["body_html"]), base, essay_url)]

    disclosure_text = escape(" ".join(essay["disclosure"]["sentences"]))
    parts.append(f"<section><h2>How this essay was made</h2><p>{disclosure_text}</p></section>")

    if essay["reference_list"]:
        heading = "Sources" if essay["citation_style"] == "web" else "References"
        items = "".join(
            f'<li id="{ref["anchor"]}">{_absolutize(str(ref["html"]), base, essay_url)}</li>'
            for ref in essay["reference_list"]
        )
        parts.append(f"<section><h2>{heading}</h2><ul>{items}</ul></section>")

    return "".join(parts)


def build_atom_feed(essays, site_url, author_name):
    """The feed's bytes, ready to write to dist/essays/feed.xml.

    `essays` is never empty -- engine/pipeline.py calls this only once at
    least one essay is published -- and is already newest first, the order
    scan_essays() returns. `site_url` is the site's absolute address
    ("https://host/"); `author_name` is user_config.json's author.name, the
    feed's one <author>.
    """
    feed_url = f"{site_url}essays/feed.xml"
    index_url = f"{site_url}essays/"

    # A plain `xmlns` attribute on the root, not etree's namespace-prefix
    # machinery: every element below inherits it as the default namespace on
    # serialization, which is all Atom needs, with no "ns0:" prefix noise.
    root = ET.Element("feed", {"xmlns": ATOM_NS})
    ET.SubElement(root, "id").text = feed_url
    ET.SubElement(root, "title").text = "Essays"
    ET.SubElement(root, "updated").text = _rfc3339(max(e["updated"] or e["published"] for e in essays))
    author = ET.SubElement(root, "author")
    ET.SubElement(author, "name").text = author_name
    ET.SubElement(root, "link", rel="self", type="application/atom+xml", href=feed_url)
    ET.SubElement(root, "link", rel="alternate", type="text/html", href=index_url)

    for essay in essays:
        url = f"{site_url}{essay['url']}"
        entry = ET.SubElement(root, "entry")
        ET.SubElement(entry, "id").text = url
        ET.SubElement(entry, "title").text = essay["title"]
        ET.SubElement(entry, "updated").text = _rfc3339(essay["updated"] or essay["published"])
        ET.SubElement(entry, "published").text = _rfc3339(essay["published"])
        ET.SubElement(entry, "link", rel="alternate", type="text/html", href=url)
        ET.SubElement(entry, "summary").text = essay["thesis"]
        ET.SubElement(entry, "content", type="html").text = entry_content_html(essay, site_url)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
