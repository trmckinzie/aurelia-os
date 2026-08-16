"""Shared text-sanitization helpers used across the extractor and card layers.

Markdown note bodies pass through process_wikilinks() before extraction, which
turns [[Wikilinks]] into <button>Label</button> elements. Extractors therefore
need to recognize both the rendered <button> form and, as a fallback, raw
[[brackets]] for text that was never run through that pass.
"""
import re

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WIKILINK_RE = re.compile(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]')
_BUTTON_RE = re.compile(r'<button[^>]*>(.*?)</button>')


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


def extract_link_labels(section_text):
    """Pulls linked note titles out of a section: rendered <button> wikilinks first,
    falling back to raw [[brackets]] if none were found (pre-process_wikilinks text)."""
    links = _BUTTON_RE.findall(section_text)
    if not links:
        raw = re.findall(r'\[\[(.*?)\]\]', section_text)
        links = [l.split('|')[1] if '|' in l else l for l in raw]
    return links


def section_after_header(text, header_pattern, stop_pattern=r'\n###|\n---'):
    """Returns the text block following a markdown header matching header_pattern,
    up to the next header/hr (per stop_pattern), or None if the header isn't found."""
    parts = re.split(header_pattern, text, flags=re.IGNORECASE)
    if len(parts) < 2:
        return None
    return re.split(stop_pattern, parts[1])[0]


def first_blockquote_after(text, header_pattern):
    """Finds the blockquote directly under a header matching header_pattern,
    falling back to the first blockquote anywhere in the text."""
    match = re.search(rf'{header_pattern}\n+>\s*(.*)', text, re.MULTILINE)
    if not match:
        match = re.search(r'>\s*(.*)', text)
    return match.group(1).strip() if match else None
