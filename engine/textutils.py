"""Shared text-sanitization helpers used across the extractor and card layers.

Markdown note bodies pass through process_wikilinks() before extraction, which
turns [[Wikilinks]] into <button>Label</button> elements. Extractors therefore
need to recognize both the rendered <button> form and, as a fallback, raw
[[brackets]] for text that was never run through that pass.
"""
import json
import re

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WIKILINK_RE = re.compile(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]')
_BUTTON_ID_RE = re.compile(r'''<button\s+onclick="openNote\('([^']+)'\)"[^>]*>(.*?)</button>''')


def strip_html(text):
    """Removes HTML tags (e.g. rendered <button> wikilinks), keeping their text."""
    return _HTML_TAG_RE.sub('', text)


def strip_wikilinks(text):
    """Collapses raw [[Target]] / [[Target|Label]] wikilinks down to their label."""
    return _WIKILINK_RE.sub(r'\1', text)


def clean_text(text):
    """Strips both rendered <button> wikilinks and raw [[wikilinks]] to plain text."""
    return strip_wikilinks(strip_html(text))


def truncate(text, limit):
    text = text or ""
    return text[:limit] + "..." if len(text) > limit else text


def extract_links(section_text):
    """Pulls linked items out of a section as (target_id, label) pairs: rendered
    <button onclick="openNote('id')">Label</button> wikilinks first, falling
    back to raw [[Target]] / [[Target|Label]] brackets (pre-process_wikilinks
    text, target_id derived via make_id) if none were found.

    target_id is preserved (rather than just the display label, which is all
    the older extract_link_labels returned) so callers can render these as
    real openNote() links instead of inert styled text.
    """
    pairs = _BUTTON_ID_RE.findall(section_text)
    if pairs:
        return [(target_id, label) for target_id, label in pairs]

    raw = re.findall(r'\[\[(.*?)\]\]', section_text)
    if not raw:
        return []

    from engine.content import make_id  # local import: content.py doesn't import textutils, so no cycle
    result = []
    for item in raw:
        target, label = item.split('|', 1) if '|' in item else (item, item)
        result.append((make_id(target.strip()), label.strip()))
    return result


def section_after_header(text, header_pattern, stop_pattern=r'\n###|\n---'):
    """Returns the text block following a markdown header matching header_pattern,
    up to the next header/hr (per stop_pattern), or None if the header isn't found."""
    parts = re.split(header_pattern, text, flags=re.IGNORECASE)
    if len(parts) < 2:
        return None
    return re.split(stop_pattern, parts[1])[0]


def dumps_for_script_tag(obj, **kwargs):
    """json.dumps(), but safe to inline inside a <script> block.

    A literal "</script" substring inside a JSON string value (e.g. a note
    title someone pastes from the web) would otherwise close the surrounding
    <script> tag early and let the rest of the page be parsed as HTML.
    """
    return json.dumps(obj, **kwargs).replace('</', '<\\/')


def escape_attr(value):
    """Escapes a value for interpolation into a double-quoted HTML attribute.

    Sibling of dumps_for_script_tag above: same idea, different sink. Card
    attributes are built by f-string interpolation in cards.py, so a value
    containing a double quote closes the attribute early and everything after
    it is parsed as markup -- which is how a stray character in a note title
    turns into a live event handler on the card.

    Vault-derived values reaching HTML attributes unescaped is a known open
    finding in this codebase (see CLAUDE.md's security notes). This does not
    close that finding, but it does mean the attributes added here aren't new
    instances of it.
    """
    return (str(value)
            .replace('&', '&amp;')
            .replace('"', '&quot;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def first_blockquote_after(text, header_pattern):
    """Finds the blockquote directly under a header matching header_pattern,
    falling back to the first blockquote anywhere in the text."""
    match = re.search(rf'{header_pattern}\n+>\s*(.*)', text, re.MULTILINE)
    if not match:
        match = re.search(r'>\s*(.*)', text)
    return match.group(1).strip() if match else None
