"""Markdown note parsing: frontmatter, wikilinks, and Gemini Notebook media blocks."""
import csv
import os
import re

import yaml

from engine.config import VAULT_PATH, ROOT_DIR


def make_id(text):
    """Turns 'My Cool Note.md' into 'note-my-cool-note'."""
    text = text.replace(".md", "").lower()
    slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return f"note-{slug}"


# Counts notes skipped for malformed YAML frontmatter (see the except branch
# in parse_frontmatter below). The per-note console warning is easy to miss
# in build output; pipeline.py reads this via get_malformed_count() to print
# a build-log summary line instead, so a bulk vault edit that breaks YAML
# somewhere surfaces loudly rather than only as a scroll-back warning.
_malformed_count = 0

# A YAML frontmatter fence is a line that is exactly `---` (trailing spaces
# tolerated), not any occurrence of those three characters. Splitting on the
# bare substring meant a note whose frontmatter carried an em-dash-ish value
# (`title: Before---After`) had its own delimiter found mid-line: parse_frontmatter
# then handed PyYAML a truncated block and parse_body started the body
# mid-frontmatter. Anchoring to ^...$ in MULTILINE mode is the whole fix.
_FRONTMATTER_FENCE_RE = re.compile(r'(?m)^---[ \t]*$')


def get_malformed_count():
    return _malformed_count


def reset_malformed_count():
    global _malformed_count
    _malformed_count = 0


# Values that make a note publish. PyYAML already turns an unquoted `true`
# (and YAML 1.1's `yes`/`on`) into Python True, so a *string* only ever gets
# here when the author quoted it or Templater left it unfilled.
_PUBLISH_TRUE = {"true", "yes", "1"}
# Unambiguous "no". Listed separately from "unrecognized" so the warning below
# fires on `publish: maybe`, not on every unpublished note in the vault.
_PUBLISH_FALSE = {"false", "no", "0", "none", "null", ""}


def _coerce_publish(value):
    """Decides whether a frontmatter `publish:` value means publish.

    Was `bool(value)`, which is true for *any* non-empty string -- so
    `publish: "false"` published the note, the exact inversion of what the
    author wrote. The publish flag is the whole rendering gate for this site
    (see CLAUDE.md's privacy model), so it gets an allowlist, not truthiness.
    """
    if value is True or value is False:
        return value
    if value is None:
        return False

    token = str(value).strip().lower()
    if token in _PUBLISH_TRUE:
        return True
    if token in _PUBLISH_FALSE:
        return False

    print(f"   ⚠️  Unrecognized publish value {value!r} -- treating as unpublished")
    return False


def parse_frontmatter(content):
    """Parses the YAML frontmatter block of a note into a metadata dict.

    Always returns publish (bool), tags (list[str]), type, and status, defaulting
    the latter two to "unknown" so downstream routing never has to null-check them.
    """
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}
    content = content.lstrip()
    if not content.startswith("---"):
        return meta

    parts = _FRONTMATTER_FENCE_RE.split(content, maxsplit=2)
    if len(parts) < 3:
        return meta

    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        # Templater note templates often contain unfilled {{placeholder}} syntax
        # that isn't valid YAML; treat them as unpublished rather than crashing.
        global _malformed_count
        _malformed_count += 1
        print(f"   ⚠️  Skipping malformed frontmatter: {str(e).splitlines()[0]}")
        return meta

    if not isinstance(parsed, dict):
        return meta

    meta.update(parsed)
    meta["publish"] = _coerce_publish(meta.get("publish", False))

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    meta["tags"] = [str(t).strip() for t in tags]

    # Obsidian Templater placeholders (e.g. "{{date}}") that were never filled in
    # shouldn't leak into rendered pages as literal braces.
    for key, value in meta.items():
        if isinstance(value, str) and ("{{" in value or "}}" in value):
            meta[key] = value.replace("{{", "").replace("}}", "").strip()

    if "date" not in meta and "created" in meta:
        meta["date"] = meta["created"]

    return meta


def parse_body(content):
    """Returns everything after the closing frontmatter fence.

    Uses the same line-anchored fence as parse_frontmatter -- the two have to
    agree on where the frontmatter ends, or the body silently starts in the
    middle of it.
    """
    parts = _FRONTMATTER_FENCE_RE.split(content, maxsplit=2)
    if len(parts) < 3:
        return content
    return parts[2].strip()


def process_wikilinks(text):
    """Converts [[Link]] / [[Target|Label]] to clickable modal-open buttons."""
    def replace_link(match):
        link_content = match.group(1)
        if '|' in link_content:
            target, label = link_content.split('|', 1)
        else:
            target, label = link_content, link_content

        target_id = make_id(target)
        return (f'<button onclick="openNote(\'{target_id}\')" '
                f'class="text-aurelia-primary hover:underline font-bold bg-transparent '
                f'border-none cursor-pointer p-0 inline">{label}</button>')

    return re.sub(r'\[\[(.*?)\]\]', replace_link, text)


_WIKILINK_BUTTON_RE = re.compile(r'''<button\s+onclick="openNote\('([^']+)'\)"[^>]*>(.*?)</button>''')


def dim_dangling_links(html, known_ids):
    """Rewrites process_wikilinks() output so links to unpublished/nonexistent
    notes render as inert, visually muted text instead of a live-looking button --
    mirrors the live/dangling contract cards.link_pill() already applies to
    structured fields (Related, Core Concepts, ...), extended here to cover plain
    in-prose wikilinks, which link_pill() never sees since it only runs on
    extractor-parsed fields, not a note's full body.
    """
    def replace(match):
        target_id, label = match.group(1), match.group(2)
        if target_id in known_ids:
            return match.group(0)
        return f'<span class="opacity-70 grayscale cursor-default" title="Not yet published">{label}</span>'

    return _WIKILINK_BUTTON_RE.sub(replace, html)


# --- Gemini Notebook media widgets -----------------------------------------
#
# Gemini Notebook export notes carry a fixed set of headers (Audio Overview,
# Video Overview, Flashcards, ...) followed by a bare asset path. This scans
# each recognized header's section for a matching asset path and swaps it for
# the corresponding interactive HTML widget.

_MEDIA_MAP = [
    {
        "header": r"#+\s*.*Audio Overview",
        "regex": r'(?:\[\[)?(assets/audio/[a-zA-Z0-9_\-\.\s]+\.(?:mp3|wav|m4a|ogg))(?:\]\])?',
        "type": "audio",
    },
    {
        "header": r"#+\s*.*Video Overview",
        "regex": r'(?:\[\[)?(assets/video/[a-zA-Z0-9_\-\.\s]+\.(?:mp4|webm))(?:\]\])?',
        "type": "video",
    },
    {
        "header": r"#+\s*.*Flashcards",
        "regex": r'(?:\[\[)?(assets/.*?[a-zA-Z0-9_\-\.\s]+\.(?:csv))(?:\]\])?',
        "type": "flashcards",
    },
    {
        "header": r"#+\s*.*(?:Mind Map|Reports|Quiz|Infographic|Slide Deck|Data Table)",
        "regex": r'(?:\[\[)?(assets/images/[a-zA-Z0-9_\-\.\s]+\.(?:png|jpg|jpeg|webp|gif))(?:\]\])?',
        "type": "image",
    },
]


def _render_audio(path):
    mime = "audio/mpeg"
    if path.endswith(".m4a"):
        mime = "audio/mp4"
    if path.endswith(".wav"):
        mime = "audio/wav"
    return f"""
<div class="my-6 p-4 border-l-2 border-aurelia-info bg-aurelia-info/5 rounded-r-theme">
<div class="flex items-center justify-between mb-3">
<span class="field-label text-aurelia-info">:: NEURAL_AUDIO_STREAM</span>
<span class="text-[10px] font-mono text-aurelia-info animate-pulse">● LIVE_ASSET</span>
</div>
<audio controls class="w-full h-8 opacity-80 hover:opacity-100 transition-opacity">
<source src="{path}" type="{mime}">
</audio>
</div>"""


def _render_video(path):
    return f"""
<div class="my-6 border border-aurelia-border rounded-theme overflow-hidden bg-aurelia-bg">
<div class="p-2 border-b border-aurelia-border bg-aurelia-card/50 flex items-center gap-2">
<span class="w-2 h-2 bg-aurelia-info rounded-full animate-pulse"></span>
<span class="field-label text-aurelia-muted">VISUAL_FEED</span>
</div>
<video controls class="w-full max-h-[400px]">
<source src="{path}" type="video/mp4">
</video>
</div>"""


def _render_image(path):
    return f"""
<div class="my-6 group relative border border-aurelia-border rounded-theme overflow-hidden bg-aurelia-bg/50 hover:border-aurelia-info/50 transition-colors">
<div class="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
<a href="{path}" target="_blank" class="px-2 py-1 bg-aurelia-bg/80 text-[10px] font-mono text-aurelia-text border border-aurelia-border rounded-theme hover:bg-aurelia-info hover:text-aurelia-inverted">ENLARGE</a>
</div>
<img src="{path}" class="w-full h-auto opacity-90 group-hover:opacity-100 transition-opacity" alt="Gemini Notebook Asset">
</div>"""


# Counts media widgets skipped because the file they point at is gone (see
# resolve_asset / process_gemini_notebook_media). pipeline.py reads this to
# print a build summary -- a silent skip is just a different flavour of the
# invisible failure this whole change is meant to remove.
_missing_asset_count = 0
_missing_assets = []


def get_missing_asset_count():
    return _missing_asset_count


def get_missing_assets():
    return list(_missing_assets)


def reset_missing_asset_count():
    global _missing_asset_count
    _missing_asset_count = 0
    _missing_assets.clear()


def resolve_asset(path):
    """Returns the on-disk path for a vault-relative asset ref, or None.

    Note bodies reference media as `assets/audio/x.m4a`, which lives at
    `vault/assets/audio/x.m4a` and is copied to `dist/assets/` by
    assets_pipeline.sync_vault_assets(). The ROOT_DIR fallback is kept from
    the original flashcard resolver, which supported decks committed at the
    repo root rather than in the vault.
    """
    for base in (VAULT_PATH, ROOT_DIR):
        candidate = os.path.join(base, path)
        if os.path.exists(candidate):
            return candidate
    return None


def _note_missing_asset(path):
    global _missing_asset_count
    _missing_asset_count += 1
    if path not in _missing_assets:
        _missing_assets.append(path)


def _render_flashcards(path):
    csv_path = resolve_asset(path)
    if csv_path is None:
        return f'<div class="text-aurelia-secondary font-mono text-xs">⚠️ CSV NOT FOUND: {path}</div>'

    cards_html = ""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        for i, row in enumerate(rows):
            if len(row) < 2:
                continue
            q, a = row[0], row[1]
            cards_html += f"""
<div class="snap-center shrink-0 w-64 h-40 relative group perspective-1000 cursor-pointer" onclick="this.querySelector('.inner-card').classList.toggle('rotate-y-180')">
<div class="inner-card w-full h-full relative preserve-3d transition-transform duration-500 shadow-lg">
<div class="absolute inset-0 backface-hidden bg-aurelia-card border border-aurelia-info/30 p-4 flex flex-col items-center justify-center text-center rounded-theme group-hover:border-aurelia-info transition-colors">
<span class="field-label text-aurelia-info absolute top-2 left-2">Q_NODE // 0{i+1}</span>
<p class="text-xs font-bold text-aurelia-text font-sans leading-relaxed">{q}</p>
<span class="text-[9px] text-aurelia-muted absolute bottom-2 animate-pulse">TAP TO DECRYPT</span>
</div>
<div class="absolute inset-0 backface-hidden rotate-y-180 bg-aurelia-info/10 border border-aurelia-info p-4 flex flex-col items-center justify-center text-center rounded-theme">
<span class="field-label text-aurelia-info absolute top-2 left-2">A_DATA</span>
<p class="text-xs text-aurelia-text/80 font-mono leading-relaxed">{a}</p>
</div>
</div>
</div>"""
    except Exception as e:
        return f'<div class="text-aurelia-secondary font-mono text-xs">⚠️ CSV ERROR: {e}</div>'

    return f"""
<div class="my-6">
<div class="flex items-center gap-2 mb-3">
<span class="field-label text-aurelia-info">:: MEMORY_BANK_LOADED</span>
<div class="h-px bg-aurelia-info/30 flex-grow"></div>
</div>
<div class="flex gap-4 overflow-x-auto pb-6 pt-2 px-1 snap-x no-scrollbar">
{cards_html}
</div>
</div>"""


_MEDIA_RENDERERS = {
    "audio": _render_audio,
    "video": _render_video,
    "image": _render_image,
    "flashcards": _render_flashcards,
}


def process_gemini_notebook_media(text):
    """Scans Gemini Notebook headers and converts bare asset paths into
    interactive HTML media (audio players, video, flashcard decks,
    enlargeable images)."""
    processed_text = text
    for item in _MEDIA_MAP:
        pattern = f"({item['header']}\\s*\\n)([\\s\\S]*?)(?=\\n#|$)"

        def replacement_logic(match, item=item):
            header = match.group(1)
            content = match.group(2).strip()
            file_match = re.search(item['regex'], content, re.IGNORECASE)
            if not file_match:
                return match.group(0)

            asset_path = file_match.group(1)

            # Don't render a player/image for a file that isn't there. The
            # 2026 history purge removed the Gemini Notebook audio and
            # mind-map assets from the repo, but the notes still name them --
            # 34 of 38 references currently resolve to nothing, so 15 notes
            # render empty audio controls and broken images. Dropping the
            # bare path leaves the header and surrounding prose intact and
            # the note simply reads as text.
            #
            # Flashcards included: that renderer's own "CSV NOT FOUND" box is
            # a build diagnostic that was being rendered to readers. The count
            # below reports it to the person who can act on it instead.
            if resolve_asset(asset_path) is None:
                _note_missing_asset(asset_path)
                new_content = content.replace(file_match.group(0), "").strip()
                return header + new_content + "\n"

            html_widget = _MEDIA_RENDERERS[item['type']](asset_path)
            new_content = content.replace(file_match.group(0), html_widget)
            return header + new_content + "\n"

        processed_text = re.sub(pattern, replacement_logic, processed_text, flags=re.IGNORECASE)

    return processed_text


_SECTION_HEADER_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)


def wrap_gemini_notebook_sections(text):
    """Wraps each top-level `# Header` section of a Gemini Notebook note in a
    collapsible <details>/<summary> block, so a long note (real ones run to
    15+ sections) can be scanned by header and expanded on demand in the
    modal reader, instead of one long scroll.

    Only the first section starts open (the Lit Review Overview, by
    convention always first) -- everything else starts collapsed.

    A blank line separates <summary>...</summary> from the section body, and
    another precedes the closing </details>: CommonMark (and marked.js, which
    renders this client-side in openNote()) treats <details>/<summary> as a
    raw-HTML block that ends at a blank line, so markdown *inside* the gap --
    bold, bullet lists, and the audio/video/flashcard widget HTML
    process_gemini_notebook_media() already injected -- still gets parsed
    normally, while the collapse/expand chrome itself is just plain HTML.
    This is the same pattern GitHub-flavored markdown uses for collapsible
    sections.
    """
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        return text

    pieces = [text[:matches[0].start()]]
    opened_one = False
    for i, match in enumerate(matches):
        header_text = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_body = text[start:end].strip()

        # Drop a section that has no body at all. This is what a header whose
        # only content was a now-missing media file collapses to (see
        # process_gemini_notebook_media): 10 "Audio Overview" and 6 "Mind Map"
        # sections currently. Keeping them would trade a visibly broken player
        # for an expandable section that opens onto nothing -- still a dead end
        # for the reader, just a quieter one. It also covers the unfilled
        # placeholder headers TPL_Gemini_Notebook's own contract warns about.
        if not section_body:
            continue

        # "First section starts open" means the first section actually
        # *rendered*, not index 0 -- if section 0 were dropped as empty, keying
        # off `i` would leave the note with every section collapsed.
        open_attr = "" if opened_one else " open"
        opened_one = True
        pieces.append(
            f'\n\n<details{open_attr} class="gemini-note-section">\n'
            f'<summary class="gemini-note-summary"><span class="folder-arrow">▶</span> {header_text}</summary>\n\n'
            f'{section_body}\n\n'
            f'</details>\n\n'
        )

    return "".join(pieces)
