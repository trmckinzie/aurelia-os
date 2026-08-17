"""Markdown note parsing: frontmatter, wikilinks, and NotebookLM media blocks."""
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


def parse_frontmatter(content):
    """Parses the YAML frontmatter block of a note into a metadata dict.

    Always returns publish (bool), tags (list[str]), type, and status, defaulting
    the latter two to "unknown" so downstream routing never has to null-check them.
    """
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}
    content = content.lstrip()
    if not content.startswith("---"):
        return meta

    parts = content.split("---", 2)
    if len(parts) < 3:
        return meta

    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        # Templater note templates often contain unfilled {{placeholder}} syntax
        # that isn't valid YAML; treat them as unpublished rather than crashing.
        print(f"   ⚠️  Skipping malformed frontmatter: {str(e).splitlines()[0]}")
        return meta

    if not isinstance(parsed, dict):
        return meta

    meta.update(parsed)
    meta["publish"] = bool(meta.get("publish", False))

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
    parts = content.split("---", 2)
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


# --- NotebookLM media widgets ---------------------------------------------
#
# NotebookLM export notes carry a fixed set of headers (Audio Overview, Video
# Overview, Flashcards, ...) followed by a bare asset path. This scans each
# recognized header's section for a matching asset path and swaps it for the
# corresponding interactive HTML widget.

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
<div class="my-6 p-4 border-l-2 border-aurelia-info bg-aurelia-info/5 rounded-r-sm">
<div class="flex items-center justify-between mb-3">
<span class="text-[10px] font-bold font-mono text-aurelia-info uppercase tracking-widest">:: NEURAL_AUDIO_STREAM</span>
<span class="text-[10px] font-mono text-aurelia-info animate-pulse">● LIVE_ASSET</span>
</div>
<audio controls class="w-full h-8 opacity-80 hover:opacity-100 transition-opacity">
<source src="{path}" type="{mime}">
</audio>
</div>"""


def _render_video(path):
    return f"""
<div class="my-6 border border-aurelia-dim rounded-sm overflow-hidden bg-aurelia-bg">
<div class="p-2 border-b border-aurelia-dim bg-aurelia-card/50 flex items-center gap-2">
<span class="w-2 h-2 bg-aurelia-info rounded-full animate-pulse"></span>
<span class="text-[10px] font-mono text-aurelia-muted uppercase tracking-widest">VISUAL_FEED</span>
</div>
<video controls class="w-full max-h-[400px]">
<source src="{path}" type="video/mp4">
</video>
</div>"""


def _render_image(path):
    return f"""
<div class="my-6 group relative border border-aurelia-dim rounded-sm overflow-hidden bg-aurelia-bg/50 hover:border-aurelia-info/50 transition-colors">
<div class="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
<a href="{path}" target="_blank" class="px-2 py-1 bg-aurelia-bg/80 text-[10px] font-mono text-aurelia-text border border-aurelia-dim rounded hover:bg-aurelia-info hover:text-aurelia-inverted">ENLARGE</a>
</div>
<img src="{path}" class="w-full h-auto opacity-90 group-hover:opacity-100 transition-opacity" alt="NotebookLM Asset">
</div>"""


def _render_flashcards(path):
    csv_path = os.path.join(VAULT_PATH, path)
    if not os.path.exists(csv_path):
        csv_path = os.path.join(ROOT_DIR, path)
    if not os.path.exists(csv_path):
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
<div class="absolute inset-0 backface-hidden bg-aurelia-card border border-aurelia-info/30 p-4 flex flex-col items-center justify-center text-center rounded-sm group-hover:border-aurelia-info transition-colors">
<span class="text-[9px] font-mono text-aurelia-info uppercase tracking-widest absolute top-2 left-2">Q_NODE // 0{i+1}</span>
<p class="text-xs font-bold text-aurelia-text font-sans leading-relaxed">{q}</p>
<span class="text-[9px] text-aurelia-muted absolute bottom-2 animate-pulse">TAP TO DECRYPT</span>
</div>
<div class="absolute inset-0 backface-hidden rotate-y-180 bg-aurelia-info/10 border border-aurelia-info p-4 flex flex-col items-center justify-center text-center rounded-sm">
<span class="text-[9px] font-mono text-aurelia-info uppercase tracking-widest absolute top-2 left-2">A_DATA</span>
<p class="text-xs text-aurelia-text/80 font-mono leading-relaxed">{a}</p>
</div>
</div>
</div>"""
    except Exception as e:
        return f'<div class="text-aurelia-secondary font-mono text-xs">⚠️ CSV ERROR: {e}</div>'

    return f"""
<div class="my-6">
<div class="flex items-center gap-2 mb-3">
<span class="text-[10px] font-bold font-mono text-aurelia-info uppercase tracking-widest">:: MEMORY_BANK_LOADED</span>
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


def process_notebooklm_media(text):
    """Scans NotebookLM headers and converts bare asset paths into interactive
    HTML media (audio players, video, flashcard decks, enlargeable images)."""
    processed_text = text
    for item in _MEDIA_MAP:
        pattern = f"({item['header']}\\s*\\n)([\\s\\S]*?)(?=\\n#|$)"

        def replacement_logic(match, item=item):
            header = match.group(1)
            content = match.group(2).strip()
            file_match = re.search(item['regex'], content, re.IGNORECASE)
            if not file_match:
                return match.group(0)

            html_widget = _MEDIA_RENDERERS[item['type']](file_match.group(1))
            new_content = content.replace(file_match.group(0), html_widget)
            return header + new_content + "\n"

        processed_text = re.sub(pattern, replacement_logic, processed_text, flags=re.IGNORECASE)

    return processed_text
