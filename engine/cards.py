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
        # grayscale neutralizes whatever hue `classes` set (so a dangling
        # link never looks like a "real," differently-colored pill); the
        # opacity floor is well above a typical disabled-state 40% because
        # that -- combined with grayscale already darkening/desaturating
        # the color -- dropped well below readable contrast on light
        # themes. 70% keeps the "this isn't clickable" signal clear
        # without the label being hard to read.
        return f'<span class="{classes} opacity-70 grayscale cursor-default" title="Not yet published">{label}</span>'
    return f'<span class="{classes} cursor-default">{label}</span>'


def _maturity_slug(meta):
    """Returns 'seed'/'growing'/'evergreen' for a note, or ''.

    Prefers the frontmatter `maturity:` key (mirroring how `type` resolution
    prefers its own key -- see generate_garden_card_html), falling back to a
    `maturity/*` tag for notes edited without the key. This used to read a
    status/<maturity> tag, back when maturity and lifecycle status shared one
    tag namespace -- they're now two separate axes (status/* is lifecycle:
    active/reading/queued/archive; maturity/* is seed/growing/evergreen), so
    a status/* tag is no longer a maturity signal at all.

    Exposed separately from the badge HTML (see _maturity_badge) so the
    client-side review-queue JS in gardentemplate.html can read a note's
    maturity via a data-maturity attribute without re-parsing rendered HTML.
    """
    slug = str(meta.get("maturity", "")).lower().strip()
    if slug in _MATURITY_BADGES:
        return slug
    for tag in meta.get("tags") or []:
        if not str(tag).startswith("maturity/"):
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
    maturity_slug = _maturity_slug(meta)
    maturity_html = _maturity_badge(maturity_slug)
    # Space-joined so the client can filter with a plain
    # `dataset.tags.split(' ').includes(tag)` -- powers the Garden's
    # "Browse by Topic" cloud (topic/* tags) without a separate index.
    tags_attr = ' '.join(str(t) for t in (meta.get("tags") or []))

    base_classes = ("searchable-item glass p-5 rounded-sm border border-opacity-40 "
                     "hover:border-opacity-100 cursor-pointer flex flex-col gap-3 "
                     "transition-all duration-300 hover:translate-y-[-4px] hover:shadow-2xl "
                     "hover:z-10 group h-full min-h-[240px]")
    # Overridden below for source/notebooklm: their top-badge label keeps the
    # exact color CYBER_PRIME always showed (tertiary/orange, primary/cyan)
    # even though the card's own identity color (highlight/info) differs --
    # changing it would be a visible CYBER_PRIME regression for no reason,
    # since the badge text was never derived from the card's border color.
    label_color = None

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
                <p class="text-sm text-aurelia-text font-mono mt-1 border-l-2 border-aurelia-tertiary/50 pl-3 leading-relaxed line-clamp-2">
                    "{mission}"
                </p>
            </div>

            <div class="flex-grow">
                <span class="text-[10px] font-bold font-mono text-aurelia-tertiary tracking-widest">> DEBRIEF:</span>
                <p class="text-sm text-aurelia-text font-sans mt-1 leading-relaxed italic line-clamp-3 opacity-90">
                    {summary if summary else "// No summary data available."}
                </p>
            </div>

            <div class="mt-auto pt-3 border-t border-aurelia-dim/50 flex flex-col gap-2">
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
            lambda pair: link_pill(pair[0], f"→ {pair[1]}", "hover:text-aurelia-primary transition-colors border-b border-aurelia-dim hover:border-aurelia-primary pb-0.5", known_ids),
            empty_html='<span class="opacity-30 text-[9px]">// NO_LINKS_DETECTED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-primary">
                <span class="text-[10px] font-bold font-mono text-aurelia-primary tracking-widest block mb-1">> DEFINITION:</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-medium">
                    "{definition}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="pt-3 border-t border-aurelia-dim/50">
                <span class="text-[9px] font-bold font-mono text-aurelia-primary uppercase tracking-widest block mb-2">NEURAL_LINKS:</span>
                <div class="flex flex-wrap gap-2 text-[10px] font-mono text-aurelia-muted">
                    {links_html}
                </div>
            </div>
        </div>"""
        icon = "⚛️"; label = "CONCEPT"

    elif "source" in note_type:
        color = "border-aurelia-highlight"
        author, argument, concepts = extract_source_data(body_content)

        # Reads the lifecycle `status:` key itself (falling back to a
        # status/* tag, same precedence as _maturity_slug/type resolution),
        # not a substring test against the tag list rendered to a string --
        # that used to key "QUEUED" off the same "seed" substring that also
        # drove maturity. The two are separate axes now: status/* is
        # lifecycle (active/reading/queued/archive), maturity/* is
        # seed/growing/evergreen (see _maturity_slug).
        status_lifecycle = str(meta.get("status", "")).lower().strip()
        if status_lifecycle not in ("reading", "queued", "archive"):
            status_lifecycle = ""
            for tag in meta.get("tags") or []:
                if str(tag).startswith("status/"):
                    status_lifecycle = str(tag).split("/", 1)[1].lower()
                    break
        status = {"reading": "READING", "queued": "QUEUED", "archive": "ARCHIVED"}.get(status_lifecycle, "ARCHIVED")

        argument = truncate(argument, 150)

        auth_id, auth_label = author
        author_html = link_pill(auth_id, auth_label, "hover:underline decoration-dotted", known_ids)

        concepts_html = render_items(
            concepts,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-1.5 py-0.5 border border-aurelia-highlight/40 text-aurelia-muted rounded-sm hover:text-aurelia-highlight transition-colors", known_ids),
            empty_html='<span class="opacity-30 text-[9px] text-aurelia-muted font-mono">// NO_CONCEPTS_LINKED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-3">

            <div class="flex justify-between items-end border-b border-aurelia-highlight/30 pb-2">
                <span class="text-[10px] font-bold font-mono text-aurelia-highlight uppercase tracking-wider truncate mr-2">AUTH: {author_html}</span>
                <span class="text-[9px] font-bold font-mono text-aurelia-inverted bg-aurelia-highlight px-1.5 py-0.5 rounded-sm shrink-0">{status}</span>
            </div>

            <div class="mt-1">
                <p class="text-sm text-aurelia-text font-serif leading-relaxed italic opacity-90">
                    "{argument}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="mt-auto">
                 <span class="text-[9px] font-bold font-mono text-aurelia-highlight uppercase tracking-widest block mb-1">DERIVED_IDEAS:</span>
                 <div class="flex flex-wrap gap-1.5">
                    {concepts_html}
                 </div>
            </div>
        </div>"""
        icon = "📚"; label = "LIBRARY"; label_color = "text-aurelia-tertiary"

    elif "author" in note_type:
        color = "border-aurelia-secondary"
        context, works, concepts = extract_author_data(body_content)
        context = truncate(context, 150)

        concepts_html = render_items(
            concepts,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-2 py-1 bg-aurelia-secondary text-aurelia-inverted font-bold rounded-sm border border-aurelia-secondary", known_ids),
            empty_html='<span class="text-[9px] text-aurelia-text font-mono opacity-80">// NO_SYSTEMS_DETECTED</span>',
        )
        works_html = render_items(
            works,
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-2 py-0.5 border border-aurelia-dim text-aurelia-text font-bold rounded-sm hover:border-aurelia-secondary hover:text-aurelia-secondary transition-colors", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-secondary">
                <span class="text-[10px] font-bold font-mono text-aurelia-secondary tracking-widest block mb-1">> BIO_MATRIX:</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-bold">
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

            <div class="pt-2 border-t border-aurelia-dim">
                <span class="text-[9px] font-bold font-mono text-aurelia-text uppercase tracking-widest block mb-1">BIBLIOGRAPHY:</span>
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
            lambda pair: link_pill(pair[0], pair[1], "text-[9px] font-mono px-2 py-1 bg-aurelia-accent text-aurelia-inverted font-extrabold rounded-sm uppercase", known_ids),
            empty_html='<span class="text-[9px] text-aurelia-muted font-mono">// FOUNDATIONS_PENDING</span>',
        )
        canon_html = render_items(
            canon,
            lambda pair: link_pill(pair[0], f"• {pair[1]}", "text-[10px] font-serif italic text-aurelia-muted hover:text-aurelia-text transition-colors truncate", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-4 border-aurelia-accent">
                <span class="text-[10px] font-bold font-mono text-aurelia-accent tracking-widest block mb-1">:: FIELD_SCOPE</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-bold opacity-95">
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

            <div class="pt-2 border-t border-aurelia-dim">
                <span class="text-[9px] font-bold font-mono text-aurelia-text uppercase tracking-widest block mb-1">THE_CANON:</span>
                <div class="flex flex-col gap-1">
                    {canon_html}
                </div>
            </div>

        </div>"""
        icon = "🧠"; label = "FIELD"

    elif "notebooklm" in note_type:
        color = "border-aurelia-info"
        overview, active_features = extract_notebooklm_data(body_content)
        overview = truncate(overview, 160)

        feature_icons = {
            'audio': '🎙️', 'video': '🎥', 'mindmap': '🧠',
            'reports': '📄', 'flashcards': '🃏', 'quiz': '📝',
            'infographic': '📊', 'slides': '📽️', 'datatable': '📉',
        }

        def render_feature(f):
            return f"""
                    <div class="flex items-center gap-2 px-2 py-1 bg-aurelia-info/10 border border-aurelia-info/30 rounded-sm" title="{f.upper()}">
                        <span class="text-xs">{feature_icons.get(f, "•")}</span>
                        <span class="text-[9px] font-mono text-aurelia-primary font-bold uppercase">{f}</span>
                    </div>
                    """

        features_html = render_items(
            active_features,
            render_feature,
            empty_html='<span class="text-[9px] text-aurelia-muted font-mono">// NO_MODULES_ONLINE</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-4 border-aurelia-info">
                <span class="text-[10px] font-bold font-mono text-aurelia-primary tracking-widest block mb-1">:: RESEARCH_SYNTHESIS</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed opacity-95">
                    "{overview}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="text-[9px] font-bold font-mono text-aurelia-muted uppercase tracking-widest block mb-2">AVAILABLE_DATA_STREAMS:</span>

                <div class="flex flex-wrap gap-2">
                    {features_html}
                </div>
            </div>
        </div>"""
        icon = "🧬"; label = "NOTEBOOK"; label_color = "text-aurelia-primary"

    else:
        color = "border-aurelia-dim"
        clean_body = re.sub(r'<[^>]+>', '', body_content)
        clean_body = re.sub(r'[*#_`\[\]]', '', clean_body)
        blurb = clean_body[:200] + "..."
        card_content = f"""<div class="flex flex-col h-full"><p class="text-sm text-aurelia-muted font-sans leading-relaxed line-clamp-5">{blurb}</p></div>"""
        icon = "📄"; label = "NOTE"

    if label_color is None:
        label_color = color.replace('border-', 'text-')

    html_card = f"""
    <article onclick="openNote('{note_id}')" data-id="{note_id}" data-type="{note_type}" data-maturity="{maturity_slug}" data-tags="{tags_attr}" data-search="{title} {note_type} {full_search_text}" class="{base_classes} {color}">
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-1.5">
                    <span class="w-1.5 h-1.5 {color.replace('border-', 'bg-')} rounded-full"></span>
                    <span class="text-[10px] font-mono {label_color} uppercase tracking-widest">{label}</span>
                    {maturity_html}
                </div>
                <h3 class="text-lg font-bold text-aurelia-text font-mono group-hover:text-aurelia-text transition-colors leading-tight">{title}</h3>
            </div>
            <div class="text-2xl opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-transform">{icon}</div>
        </div>
        <div class="w-full h-px bg-aurelia-dim/50"></div>
        {card_content}
    </article>
    """
    return html_card
