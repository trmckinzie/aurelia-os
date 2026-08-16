"""The Card Factory: renders the HTML card for a single note, by type."""
import re

from engine.extractors import (
    extract_author_data,
    extract_concept_data,
    extract_discipline_data,
    extract_log_data,
    extract_notebooklm_data,
    extract_source_data,
)
from engine.textutils import truncate

_MATURITY_BADGES = {
    "seed": ("🌱", "Seed"),
    "growing": ("🌿", "Growing"),
    "evergreen": ("🌳", "Evergreen"),
}


def render_items(items, render_item, empty_html=""):
    """Joins rendered items, or falls back to empty_html when the list is empty.

    Replaces the repeated `''.join([f'...' for x in items]) + ('' if items else
    '<empty state markup>')` pattern that recurred across every card type.
    """
    if not items:
        return empty_html
    return ''.join(render_item(i) for i in items)


def link_pill(target_id, label, classes, known_ids):
    """Renders one linked-item pill.

    A real openNote() button when target_id is a published note; dimmed,
    non-interactive text when it *was* a wikilink but the target isn't
    published (yet); plain text when it was never a link at all (e.g. the
    comma-separated fallback for un-linked "Related:" items). The UI should
    never look clickable unless it actually is -- `classes` (each card
    type's own pill styling) should not include its own cursor-* class,
    since this owns that.
    """
    if target_id and target_id in known_ids:
        return (f'<span onclick="openNote(\'{target_id}\'); event.stopPropagation()" '
                f'class="{classes} cursor-pointer">{label}</span>')
    if target_id:
        return f'<span class="{classes} opacity-40 grayscale cursor-default" title="Not yet published">{label}</span>'
    return f'<span class="{classes} cursor-default">{label}</span>'


def _maturity_slug(tags):
    """Returns 'seed'/'growing'/'evergreen' from a status/<maturity> tag, or ''.

    Exposed separately from the badge HTML (see _maturity_badge) so the
    client-side review-queue JS in gardentemplate.html can read a note's
    maturity via a data-maturity attribute without re-parsing rendered HTML.
    """
    for tag in tags or []:
        if not str(tag).startswith("status/"):
            continue
        slug = str(tag).split("/", 1)[1].lower()
        if slug in _MATURITY_BADGES:
            return slug
    return ""


def _maturity_badge(slug):
    """Renders a 🌱/🌿/🌳 badge for a maturity slug (see _maturity_slug), if any.

    Templates already write status/seed, status/growing, status/evergreen
    (a Zettelkasten-style note-maturity convention) but previously only the
    Source card type surfaced it. Shared here so every card type shows it
    the same way. Silently renders nothing for notes without a maturity tag
    (e.g. status/reading, status/active) rather than showing a placeholder.
    """
    badge = _MATURITY_BADGES.get(slug)
    if not badge:
        return ""
    emoji, text = badge
    return f'<span class="text-[10px] opacity-70" title="{text}">{emoji}</span>'


def generate_garden_card_html(meta, filename, note_id, body_content, full_search_text, known_ids=frozenset()):
    # str() guards against frontmatter values YAML infers as non-strings
    # (e.g. an unquoted "type: 2026" would parse as an int, not text).
    note_type = str(meta.get("type", "unknown")).lower()

    if (note_type == "unknown" or not note_type) and meta.get("tags"):
        for tag in meta["tags"]:
            if tag.startswith("type/"):
                note_type = tag.split("/")[1]
                break
    if re.match(r'\d{4}-\d{2}-\d{2}', filename):
        note_type = "daily-bridge"
    meta["type"] = note_type
    title = filename.replace(".md", "").replace("_", " ")
    maturity_slug = _maturity_slug(meta.get("tags"))
    maturity_html = _maturity_badge(maturity_slug)
    # Space-joined so the client can filter with a plain
    # `dataset.tags.split(' ').includes(tag)` -- powers the Garden's
    # "Browse by Topic" cloud (topic/* tags) without a separate index.
    tags_attr = ' '.join(str(t) for t in (meta.get("tags") or []))

    base_classes = ("searchable-item glass p-5 rounded-sm border border-opacity-40 "
                     "hover:border-opacity-100 cursor-pointer flex flex-col gap-3 "
                     "transition-all duration-300 hover:translate-y-[-4px] hover:shadow-2xl "
                     "hover:z-10 group h-full min-h-[240px]")

    if "daily" in note_type or "log" in note_type:
        color = "border-aurelia-tertiary"
        mission, source, cues, summary = extract_log_data(body_content)
        summary = truncate(summary, 120)

        src_id, src_label = source
        source_html = link_pill(src_id, src_label[:40], "hover:underline decoration-dotted", known_ids)

        cues_html = render_items(
            cues,
            lambda c: link_pill(c[0], c[1], "text-[10px] font-mono px-2 py-0.5 bg-aurelia-tertiary/10 text-aurelia-tertiary border border-aurelia-tertiary/30 rounded-sm font-bold", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col gap-4 h-full">

            <div>
                <span class="text-[10px] font-bold font-mono text-aurelia-tertiary tracking-widest">> MISSION_OBJ:</span>
                <p class="text-sm text-gray-100 font-mono mt-1 border-l-2 border-aurelia-tertiary/50 pl-3 leading-relaxed line-clamp-2">
                    "{mission}"
                </p>
            </div>

            <div class="flex-grow">
                <span class="text-[10px] font-bold font-mono text-aurelia-tertiary tracking-widest">> DEBRIEF:</span>
                <p class="text-sm text-white font-sans mt-1 leading-relaxed italic line-clamp-3 opacity-90">
                    {summary if summary else "// No summary data available."}
                </p>
            </div>

            <div class="mt-auto pt-3 border-t border-gray-800/50 flex flex-col gap-2">
                <div class="flex justify-between items-center">
                    <span class="text-[10px] font-bold font-mono text-aurelia-tertiary uppercase truncate w-full">SRC: {source_html}</span>
                </div>
                <div class="flex flex-wrap gap-1.5">
                    {cues_html}
                </div>
            </div>

        </div>"""
        icon = "📅"; label = "SYS_LOG"

    elif "concept" in note_type:
        color = "border-aurelia-primary"
        definition, links = extract_concept_data(body_content)
        definition = truncate(definition, 160)

        links_html = render_items(
            links,
            lambda pair: link_pill(pair[0], f"→ {pair[1]}", "hover:text-aurelia-primary transition-colors border-b border-gray-700 hover:border-aurelia-primary pb-0.5", known_ids),
            empty_html='<span class="opacity-30 text-[9px]">// NO_LINKS_DETECTED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-primary">
                <span class="text-[10px] font-bold font-mono text-aurelia-primary tracking-widest block mb-1">> DEFINITION:</span>
                <p class="text-sm text-white font-sans leading-relaxed font-medium">
                    "{definition}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="pt-3 border-t border-gray-800/50">
                <span class="text-[9px] font-bold font-mono text-aurelia-primary uppercase tracking-widest block mb-2">NEURAL_LINKS:</span>
                <div class="flex flex-wrap gap-2 text-[10px] font-mono text-gray-300">
                    {links_html}
                </div>
            </div>
        </div>"""
        icon = "⚛️"; label = "CONCEPT"

    elif "source" in note_type:
        color = "border-yellow-500"
        author, argument, concepts = extract_source_data(body_content)

        status = "ARCHIVED"
        if "reading" in str(meta.get("tags")): status = "READING"
        if "seed" in str(meta.get("tags")): status = "QUEUED"

        argument = truncate(argument, 150)

        auth_id, auth_label = author
        author_html = link_pill(auth_id, auth_label, "hover:underline decoration-dotted", known_ids)

        concepts_html = render_items(
            concepts,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-1.5 py-0.5 border border-yellow-500/40 text-gray-300 rounded-sm hover:text-yellow-500 transition-colors", known_ids),
            empty_html='<span class="opacity-30 text-[9px] text-gray-500 font-mono">// NO_CONCEPTS_LINKED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-3">

            <div class="flex justify-between items-end border-b border-yellow-500/30 pb-2">
                <span class="text-[10px] font-bold font-mono text-yellow-500 uppercase tracking-wider truncate mr-2">AUTH: {author_html}</span>
                <span class="text-[9px] font-bold font-mono text-black bg-yellow-500 px-1.5 py-0.5 rounded-sm shrink-0">{status}</span>
            </div>

            <div class="mt-1">
                <p class="text-sm text-white font-serif leading-relaxed italic opacity-90">
                    "{argument}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="mt-auto">
                 <span class="text-[9px] font-bold font-mono text-yellow-500 opacity-70 uppercase tracking-widest block mb-1">DERIVED_IDEAS:</span>
                 <div class="flex flex-wrap gap-1.5">
                    {concepts_html}
                 </div>
            </div>
        </div>"""
        icon = "📚"; label = "LIBRARY"

    elif "author" in note_type:
        color = "border-aurelia-secondary"
        context, works, concepts = extract_author_data(body_content)
        context = truncate(context, 150)

        concepts_html = render_items(
            concepts,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-2 py-1 bg-aurelia-secondary text-black font-bold rounded-sm border border-aurelia-secondary", known_ids),
            empty_html='<span class="text-[9px] text-white font-mono opacity-80">// NO_SYSTEMS_DETECTED</span>',
        )
        works_html = render_items(
            works,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-2 py-0.5 border border-gray-400 text-white font-bold rounded-sm hover:border-aurelia-secondary hover:text-aurelia-secondary transition-colors", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-secondary">
                <span class="text-[10px] font-bold font-mono text-aurelia-secondary tracking-widest block mb-1">> BIO_MATRIX:</span>
                <p class="text-sm text-white font-sans leading-relaxed font-bold">
                    "{context}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="text-[10px] font-bold font-mono text-aurelia-secondary uppercase tracking-widest block mb-1">CORE_SYSTEMS:</span>
                <div class="flex flex-wrap gap-1.5">
                    {concepts_html}
                </div>
            </div>

            <div class="pt-2 border-t border-gray-600">
                <span class="text-[9px] font-bold font-mono text-white uppercase tracking-widest block mb-1">BIBLIOGRAPHY:</span>
                <div class="flex flex-wrap gap-1.5">
                    {works_html}
                </div>
            </div>

        </div>"""
        icon = "👤"; label = "PROFILE"

    elif "discipline" in note_type:
        color = "border-aurelia-accent"
        scope, pillars, canon = extract_discipline_data(body_content)
        scope = truncate(scope, 160)

        pillars_html = render_items(
            pillars,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-2 py-1 bg-aurelia-accent text-black font-extrabold rounded-sm uppercase", known_ids),
            empty_html='<span class="text-[9px] text-gray-500 font-mono">// FOUNDATIONS_PENDING</span>',
        )
        canon_html = render_items(
            canon,
            lambda pair: link_pill(pair[0], f"• {pair[1]}", "text-[10px] font-serif italic text-gray-300 hover:text-white transition-colors truncate", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-4 border-aurelia-accent">
                <span class="text-[10px] font-bold font-mono text-aurelia-accent tracking-widest block mb-1">:: FIELD_SCOPE</span>
                <p class="text-sm text-white font-sans leading-relaxed font-bold opacity-95">
                    "{scope}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="text-[9px] font-bold font-mono text-aurelia-accent uppercase tracking-widest block mb-1">CORE_PILLARS:</span>
                <div class="flex flex-wrap gap-1.5">
                    {pillars_html}
                </div>
            </div>

            <div class="pt-2 border-t border-gray-600">
                <span class="text-[9px] font-bold font-mono text-white uppercase tracking-widest block mb-1">THE_CANON:</span>
                <div class="flex flex-col gap-1">
                    {canon_html}
                </div>
            </div>

        </div>"""
        icon = "🧠"; label = "FIELD"

    elif "notebooklm" in note_type:
        color = "border-indigo-500"
        overview, active_features = extract_notebooklm_data(body_content)
        overview = truncate(overview, 160)

        feature_icons = {
            'audio': '🎙️', 'video': '🎥', 'mindmap': '🧠',
            'reports': '📄', 'flashcards': '🃏', 'quiz': '📝',
            'infographic': '📊', 'slides': '📽️', 'datatable': '📉',
        }

        def render_feature(f):
            return f"""
                    <div class="flex items-center gap-2 px-2 py-1 bg-indigo-500/10 border border-indigo-500/30 rounded-sm" title="{f.upper()}">
                        <span class="text-xs">{feature_icons.get(f, "•")}</span>
                        <span class="text-[9px] font-mono text-indigo-300 font-bold uppercase">{f}</span>
                    </div>
                    """

        features_html = render_items(
            active_features,
            render_feature,
            empty_html='<span class="text-[9px] text-gray-600 font-mono">// NO_MODULES_ONLINE</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-4 border-indigo-500">
                <span class="text-[10px] font-bold font-mono text-indigo-400 tracking-widest block mb-1">:: RESEARCH_SYNTHESIS</span>
                <p class="text-sm text-gray-200 font-sans leading-relaxed opacity-95">
                    "{overview}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="text-[9px] font-bold font-mono text-gray-500 uppercase tracking-widest block mb-2">AVAILABLE_DATA_STREAMS:</span>

                <div class="flex flex-wrap gap-2">
                    {features_html}
                </div>
            </div>
        </div>"""
        icon = "🧬"; label = "NOTEBOOK"

    else:
        color = "border-gray-800"
        clean_body = re.sub(r'<[^>]+>', '', body_content)
        clean_body = re.sub(r'[*#_`\[\]]', '', clean_body)
        blurb = clean_body[:200] + "..."
        card_content = f"""<div class="flex flex-col h-full"><p class="text-sm text-gray-400 font-sans leading-relaxed line-clamp-5">{blurb}</p></div>"""
        icon = "📄"; label = "NOTE"

    html_card = f"""
    <article onclick="openNote('{note_id}')" data-id="{note_id}" data-type="{note_type}" data-maturity="{maturity_slug}" data-tags="{tags_attr}" data-search="{title} {note_type} {full_search_text}" class="{base_classes} {color}">
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-1.5">
                    <span class="w-1.5 h-1.5 {color.replace('border-', 'bg-')} rounded-full"></span>
                    <span class="text-[10px] font-mono {color.replace('border-', 'text-')} uppercase tracking-widest">{label}</span>
                    {maturity_html}
                </div>
                <h3 class="text-lg font-bold text-gray-200 font-mono group-hover:text-white transition-colors leading-tight">{title}</h3>
            </div>
            <div class="text-2xl opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-transform">{icon}</div>
        </div>
        <div class="w-full h-px bg-gray-800/50"></div>
        {card_content}
    </article>
    """
    return html_card
