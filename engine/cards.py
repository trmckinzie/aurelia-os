"""The Card Factory: renders the HTML card for a single note, by type."""
import re

from markupsafe import Markup, escape

from engine.extractors import (
    extract_author_data,
    extract_concept_data,
    extract_deep_dive_data,
    extract_discipline_data,
    extract_gemini_notebook_data,
    extract_log_data,
    extract_source_data,
)
from engine.textutils import escape_attr, truncate

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

    `label` is note-derived -- it is the display half of a [[Target|Label]]
    wikilink, or a comma-separated item from a Related: line -- and lands in
    HTML text position, so it is escaped here. It was not before (audit
    finding #21's "wikilink labels reach HTML unescaped" sibling), and it has
    to be for generate_garden_card_html() to honestly return Markup.
    `target_id` needs no escaping of its own: it only ever comes from
    content.make_id(), whose output is `note-` plus [a-z0-9-], so it cannot
    carry the quote that would break out of the onclick's JS string.
    """
    label = escape(label)
    if target_id and target_id in known_ids:
        # `pill-live` adds the hover treatment (see main.css) -- a live link
        # should look reactive, not just colored, since color alone is what
        # made these look clickable when they weren't.
        return (f'<span onclick="openNote(\'{target_id}\'); event.stopPropagation()" '
                f'class="{classes} pill-live cursor-pointer">{label}</span>')
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


def _maturity_badge(slug, color):
    """Renders a 🌱/🌿/🌳 + label chip for a maturity slug (see _maturity_slug), if any.

    Templates already write status/seed, status/growing, status/evergreen
    (a Zettelkasten-style note-maturity convention) but previously only the
    Source card type surfaced it. Shared here so every card type shows it
    the same way. Silently renders nothing for notes without a maturity tag
    (e.g. status/reading, status/active) rather than showing a placeholder.

    `color` is the card type's own identity color (e.g. "border-aurelia-primary"
    for Concept) -- reusing it means no new theme colors are needed for this
    badge, and it visually ties maturity to the card's existing accent. The
    three levels differ in fill weight, not hue, echoing the seed->sapling->
    tree progression the emoji already carry: an outline, then a soft tint,
    then a solid chip (the same solid treatment the Source card's status
    badge already uses).
    """
    badge = _MATURITY_BADGES.get(slug)
    if not badge:
        return ""
    emoji, text = badge
    base = color.replace('border-', '')
    fill = {
        "seed": f"border border-{base}/50 text-{base} bg-transparent",
        "growing": f"border border-{base}/70 text-{base} bg-{base}/15",
        "evergreen": f"bg-{base} text-aurelia-inverted border border-{base} shadow-[0_0_12px_-2px_currentColor]",
    }[slug]
    return (f'<span class="field-label inline-flex items-center gap-1 px-2 py-1 '
            f'rounded-theme whitespace-nowrap {fill}" title="Maturity: {text}">'
            f'{emoji} {text}</span>')


def _connection_badge(count, color):
    """Renders a link-count chip, or nothing when a note has no connections.

    How connected a note is is arguably the most useful signal in a
    Zettelkasten -- it's what separates a load-bearing idea from an isolated
    one -- and it was already computed for the knowledge graph and the
    Lobby's hub list, but a card never surfaced it.

    Silent at zero rather than showing "0": an orphan is better communicated
    by the absence of the chip than by a number that reads like a defect.
    `color` is the card type's own identity color, the same borrowing
    _maturity_badge does, so this needs no new theme token.
    """
    if not count:
        return ""
    base = color.replace('border-', '')
    label = "link" if count == 1 else "links"
    return (f'<span class="field-label inline-flex items-center gap-1 px-2 py-1 rounded-theme '
            f'whitespace-nowrap border border-{base}/40 text-{base}/90" '
            f'title="{count} {label} to or from this note">&#9673; {count}</span>')


def generate_garden_card_html(meta, filename, note_id, body_content, full_search_text,
                              known_ids=frozenset(), connections=0, created=""):
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
    raw_title = filename.replace(".md", "").replace("_", " ")
    # Escaped for the <h3> below. escape_attr() already covered data-title,
    # but the visible heading was raw.
    title = escape(raw_title)
    maturity_slug = _maturity_slug(meta)
    # Space-joined so the client can filter with a plain
    # `dataset.tags.split(' ').includes(tag)` -- powers the Garden's
    # "Browse by Topic" cloud (topic/* tags) without a separate index.
    tags_attr = ' '.join(str(t) for t in (meta.get("tags") or []))

    # `surface` + `lift` + `bloom` are the shared depth vocabulary from
    # assets/css/main.css -- layered background, top rim-light, elevation,
    # hover lift and glow. They deliberately set no border: the type
    # identity border (border-aurelia-primary/insight/...) is applied as a
    # utility below, and a component class that also set border-color would
    # fight it -- the exact bug main.css's :where(.glass) note documents.
    #
    # `glass` is dropped here: it painted a flat translucent bg_main over
    # the card, which is what made every card the same color as the page.
    base_classes = ("searchable-item surface lift bloom relative overflow-hidden "
                    "p-5 rounded-theme border cursor-pointer flex flex-col gap-3.5 "
                    "hover:z-10 group h-full min-h-[240px]")
    # Overridden below for source/gemini-notebook: their top-badge label keeps the
    # exact color CYBER_PRIME always showed (tertiary/orange, primary/cyan)
    # even though the card's own identity color (highlight/info) differs --
    # changing it would be a visible CYBER_PRIME regression for no reason,
    # since the badge text was never derived from the card's border color.
    label_color = None

    if "daily" in note_type or "log" in note_type:
        color = "border-aurelia-tertiary"
        mission, source, cues, summary = extract_log_data(body_content)
        # Escaped after truncating, never before: escaping first and cutting
        # afterwards can slice an entity in half ("&am"). Same order at every
        # prose site below.
        #
        # These fields already pass through textutils.clean_text()/strip_html()
        # in the extractors, which is why they were assumed safe -- but that
        # strips `<[^>]+>`, i.e. only *closed* tags. An unterminated
        # `<img src=x onerror=alert(1)` survives it untouched and is then
        # completed by the very next `>` in the surrounding markup, so the
        # tag-stripper is not an output encoder and never was.
        mission = escape(mission)
        summary = escape(truncate(summary, 120))

        src_id, src_label = source
        source_html = link_pill(src_id, src_label[:40], "hover:underline decoration-dotted", known_ids)

        cues_html = render_items(
            cues,
            lambda c: link_pill(c[0], c[1], "text-[11px] font-mono px-2 py-0.5 bg-aurelia-tertiary/10 text-aurelia-tertiary border border-aurelia-tertiary/30 rounded-theme font-bold", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col gap-4 h-full">

            <div>
                <span class="field-label text-aurelia-tertiary">> MISSION_OBJ:</span>
                <p class="text-sm text-aurelia-text font-mono mt-1 border-l-2 border-aurelia-tertiary/50 pl-3 leading-relaxed line-clamp-2">
                    "{mission}"
                </p>
            </div>

            <div class="flex-grow">
                <span class="field-label text-aurelia-tertiary">> DEBRIEF:</span>
                <p class="text-sm text-aurelia-text font-sans mt-1 leading-relaxed italic line-clamp-3 opacity-90">
                    {summary if summary else "// No summary data available."}
                </p>
            </div>

            <div class="mt-auto pt-3 border-t border-aurelia-border/50 flex flex-col gap-2">
                <div class="flex justify-between items-center">
                    <span class="field-label text-aurelia-tertiary truncate w-full">SRC: {source_html}</span>
                </div>
                <div class="flex flex-wrap gap-1.5">
                    {cues_html}
                </div>
            </div>

        </div>"""
        icon = "📅"; label = "SYS_LOG"

    elif "concept" in note_type:
        color = "border-aurelia-primary"
        definition, links, tensions = extract_concept_data(body_content)
        definition = escape(truncate(definition, 160))

        links_html = render_items(
            links,
            lambda pair: link_pill(pair[0], f"→ {pair[1]}", "hover:text-aurelia-primary transition-colors border-b border-aurelia-border hover:border-aurelia-primary pb-0.5", known_ids),
            empty_html='<span class="opacity-30 text-[10px]">// NO_LINKS_DETECTED</span>',
        )
        # Built conditionally rather than via render_items' empty_html
        # placeholder: every existing Concept note has no Contrasts field
        # yet, so an always-visible "no tensions" row would add clutter to
        # every current card for a field nobody's used. tensions_block stays
        # "" (a true no-op) until a note actually fills the field in.
        tensions_block = ""
        if tensions:
            tensions_html = render_items(
                tensions,
                lambda pair: link_pill(pair[0], f"⚡ {pair[1]}", "text-[10px] font-mono px-2 py-1 border border-aurelia-tertiary/40 text-aurelia-tertiary rounded-theme hover:bg-aurelia-tertiary/10 transition-colors", known_ids),
            )
            tensions_block = f"""
            <div class="pt-2 border-t border-aurelia-border">
                <span class="field-label text-aurelia-tertiary block mb-1">CONTRASTS_WITH:</span>
                <div class="flex flex-wrap gap-1.5">
                    {tensions_html}
                </div>
            </div>"""
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-primary">
                <span class="text-[11px] font-bold font-mono text-aurelia-primary tracking-widest block mb-1">> DEFINITION:</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-medium">
                    "{definition}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="pt-3 border-t border-aurelia-border/50">
                <span class="field-label text-aurelia-primary block mb-2">NEURAL_LINKS:</span>
                <div class="flex flex-wrap gap-2 text-[11px] font-mono text-aurelia-muted">
                    {links_html}
                </div>
            </div>
            {tensions_block}
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

        argument = escape(truncate(argument, 150))

        auth_id, auth_label = author
        author_html = link_pill(auth_id, auth_label, "hover:underline decoration-dotted", known_ids)

        concepts_html = render_items(
            concepts,
            lambda pair: link_pill(pair[0], pair[1], "text-[10px] font-mono px-1.5 py-0.5 border border-aurelia-highlight/40 text-aurelia-muted rounded-theme hover:text-aurelia-highlight transition-colors", known_ids),
            empty_html='<span class="opacity-30 text-[10px] text-aurelia-muted font-mono">// NO_CONCEPTS_LINKED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-3">

            <div class="flex justify-between items-end border-b border-aurelia-highlight/30 pb-2">
                <span class="field-label text-aurelia-highlight truncate mr-2">AUTH: {author_html}</span>
                <span class="text-[10px] font-bold font-mono text-aurelia-inverted bg-aurelia-highlight px-1.5 py-0.5 rounded-theme shrink-0">{status}</span>
            </div>

            <div class="mt-1">
                <p class="text-sm text-aurelia-text font-serif leading-relaxed italic opacity-90">
                    "{argument}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="mt-auto">
                 <span class="field-label text-aurelia-highlight block mb-1">DERIVED_IDEAS:</span>
                 <div class="flex flex-wrap gap-1.5">
                    {concepts_html}
                 </div>
            </div>
        </div>"""
        icon = "📚"; label = "LIBRARY"; label_color = "text-aurelia-tertiary"

    elif "author" in note_type:
        color = "border-aurelia-secondary"
        context, works, concepts = extract_author_data(body_content)
        context = escape(truncate(context, 150))

        concepts_html = render_items(
            concepts,
            lambda pair: link_pill(pair[0], pair[1], "text-[10px] font-mono px-2 py-1 bg-aurelia-secondary text-aurelia-inverted font-bold rounded-theme border border-aurelia-secondary", known_ids),
            empty_html='<span class="text-[10px] text-aurelia-text font-mono opacity-80">// NO_SYSTEMS_DETECTED</span>',
        )
        works_html = render_items(
            works,
            lambda pair: link_pill(pair[0], pair[1], "text-[10px] font-mono px-2 py-0.5 border border-aurelia-border text-aurelia-text font-bold rounded-theme hover:border-aurelia-secondary hover:text-aurelia-secondary transition-colors", known_ids),
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-secondary">
                <span class="text-[11px] font-bold font-mono text-aurelia-secondary tracking-widest block mb-1">> BIO_MATRIX:</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-bold">
                    "{context}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="field-label text-aurelia-secondary block mb-1">CORE_SYSTEMS:</span>
                <div class="flex flex-wrap gap-1.5">
                    {concepts_html}
                </div>
            </div>

            <div class="pt-2 border-t border-aurelia-border">
                <span class="field-label text-aurelia-text block mb-1">BIBLIOGRAPHY:</span>
                <div class="flex flex-wrap gap-1.5">
                    {works_html}
                </div>
            </div>

        </div>"""
        icon = "👤"; label = "PROFILE"

    elif "discipline" in note_type:
        color = "border-aurelia-accent"
        scope, pillars, canon, tensions = extract_discipline_data(body_content)
        scope = escape(truncate(scope, 160))

        pillars_html = render_items(
            pillars,
            lambda pair: link_pill(pair[0], pair[1], "field-label px-2 py-1 bg-aurelia-accent text-aurelia-inverted rounded-theme", known_ids),
            empty_html='<span class="text-[10px] text-aurelia-muted font-mono">// FOUNDATIONS_PENDING</span>',
        )
        canon_html = render_items(
            canon,
            lambda pair: link_pill(pair[0], f"• {pair[1]}", "text-[11px] font-serif italic text-aurelia-muted hover:text-aurelia-text transition-colors truncate", known_ids),
        )
        # See the Concept card above for why this is conditional rather than
        # an empty_html placeholder: a true no-op for every existing note.
        tensions_block = ""
        if tensions:
            tensions_html = render_items(
                tensions,
                lambda pair: link_pill(pair[0], f"⚡ {pair[1]}", "text-[10px] font-mono px-2 py-1 border border-aurelia-tertiary/40 text-aurelia-tertiary rounded-theme hover:bg-aurelia-tertiary/10 transition-colors", known_ids),
            )
            tensions_block = f"""
            <div class="pt-2 border-t border-aurelia-border">
                <span class="field-label text-aurelia-tertiary block mb-1">CONTRASTS_WITH:</span>
                <div class="flex flex-wrap gap-1.5">
                    {tensions_html}
                </div>
            </div>"""
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-4 border-aurelia-accent">
                <span class="text-[11px] font-bold font-mono text-aurelia-accent tracking-widest block mb-1">:: FIELD_SCOPE</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-bold opacity-95">
                    "{scope}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="field-label text-aurelia-accent block mb-1">CORE_PILLARS:</span>
                <div class="flex flex-wrap gap-1.5">
                    {pillars_html}
                </div>
            </div>

            <div class="pt-2 border-t border-aurelia-border">
                <span class="field-label text-aurelia-text block mb-1">THE_CANON:</span>
                <div class="flex flex-col gap-1">
                    {canon_html}
                </div>
            </div>
            {tensions_block}
        </div>"""
        icon = "🧠"; label = "FIELD"

    elif "gemini-notebook" in note_type:
        color = "border-aurelia-info"
        overview, active_features = extract_gemini_notebook_data(body_content)
        overview = escape(truncate(overview, 160))

        feature_icons = {
            'audio': '🎙️', 'video': '🎥', 'mindmap': '🧠',
            'reports': '📄', 'flashcards': '🃏', 'quiz': '📝',
            'infographic': '📊', 'slides': '📽️', 'datatable': '📉',
        }

        def render_feature(f):
            return f"""
                    <div class="flex items-center gap-2 px-2 py-1 bg-aurelia-info/10 border border-aurelia-info/30 rounded-theme" title="{f.upper()}">
                        <span class="text-xs">{feature_icons.get(f, "•")}</span>
                        <span class="field-label text-aurelia-primary">{f}</span>
                    </div>
                    """

        features_html = render_items(
            active_features,
            render_feature,
            empty_html='<span class="text-[10px] text-aurelia-muted font-mono">// NO_MODULES_ONLINE</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-4 border-aurelia-info">
                <span class="text-[11px] font-bold font-mono text-aurelia-primary tracking-widest block mb-1">:: RESEARCH_SYNTHESIS</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed opacity-95">
                    "{overview}"
                </p>
            </div>

            <div class="flex-grow"></div>

            <div>
                <span class="field-label text-aurelia-muted block mb-2">AVAILABLE_DATA_STREAMS:</span>

                <div class="flex flex-wrap gap-2">
                    {features_html}
                </div>
            </div>
        </div>"""
        icon = "🧬"; label = "GEMINI NOTEBOOK"; label_color = "text-aurelia-primary"

    elif "deep-dive" in note_type or "deep_dive" in note_type:
        color = "border-aurelia-insight"
        premise, synthesis, related = extract_deep_dive_data(body_content)
        premise = escape(truncate(premise, 140))
        synthesis = escape(truncate(synthesis, 160))

        related_html = render_items(
            related,
            lambda pair: link_pill(pair[0], f"→ {pair[1]}", "hover:text-aurelia-insight transition-colors border-b border-aurelia-border hover:border-aurelia-insight pb-0.5", known_ids),
            empty_html='<span class="opacity-30 text-[10px]">// NO_LINKS_DETECTED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-4">

            <div class="relative pl-4 border-l-2 border-aurelia-insight">
                <span class="text-[11px] font-bold font-mono text-aurelia-insight tracking-widest block mb-1">> PREMISE:</span>
                <p class="text-sm text-aurelia-text font-sans leading-relaxed font-medium italic">
                    "{premise}"
                </p>
            </div>

            <div>
                <span class="field-label text-aurelia-insight block mb-1">:: SYNTHESIS</span>
                <p class="text-xs text-aurelia-muted font-sans leading-relaxed line-clamp-3">
                    {synthesis}
                </p>
            </div>

            <div class="flex-grow"></div>

            <div class="pt-3 border-t border-aurelia-border/50">
                <span class="field-label text-aurelia-insight block mb-2">SEE_ALSO:</span>
                <div class="flex flex-wrap gap-2 text-[11px] font-mono text-aurelia-muted">
                    {related_html}
                </div>
            </div>
        </div>"""
        icon = "🔎"; label = "DEEP DIVE"

    else:
        color = "border-aurelia-border"
        clean_body = re.sub(r'<[^>]+>', '', body_content)
        clean_body = re.sub(r'[*#_`\[\]]', '', clean_body)
        blurb = escape(clean_body[:200] + "...")
        card_content = f"""<div class="flex flex-col h-full"><p class="text-sm text-aurelia-muted font-sans leading-relaxed line-clamp-5">{blurb}</p></div>"""
        icon = "📄"; label = "NOTE"

    if label_color is None:
        label_color = color.replace('border-', 'text-')

    maturity_html = _maturity_badge(maturity_slug, color)

    # The type identity now reads three ways at once -- a full-height spine
    # down the left edge, the status dot, and the label -- instead of only
    # as a 1px border color. The spine is what makes a wall of cards
    # scannable by type at a glance.
    spine = color.replace('border-', 'bg-')

    connections_html = _connection_badge(connections, color)

    # data-title/-connections/-created are what the Garden's sort comparators
    # read. Title is duplicated into an attribute rather than being taken from
    # the <h3> because highlightText() rewrites that element's innerHTML during
    # search -- ordering must not depend on whether a search is active.
    # escapeHtml keeps a quote in a filename from closing the attribute.
    #
    # data-label carries the human type label the branches above already
    # computed ("LIBRARY" for source/book, "SYS_LOG" for daily-bridge, ...).
    # The note reader's header shows it, and it is emitted here rather than
    # re-derived in gardentemplate.html because it is NOT a transform of
    # note_type -- source/book -> LIBRARY and discipline -> FIELD are
    # editorial choices that live in this function's branches. A client-side
    # copy would be a second hand-maintained list of every note type, which
    # is exactly the kind of thing that silently goes stale when an eighth
    # type is added. (The reader's accent *color* needs no equivalent: the
    # template's existing graphColorFor() already maps every type to a live
    # --aurelia-* value for the graph view, so the reader reuses that.)
    #
    # data-tags and data-type are escaped for the same reason data-title is:
    # both come straight out of frontmatter, and a tag or type containing a
    # double quote closed the attribute and let the rest of the string be
    # parsed as markup on the <article> itself (audit finding #22). Escaping
    # is a no-op for every real tag -- the browser decodes entities before the
    # Garden's filter JS reads dataset.tags, so filtering is unaffected.
    #
    # Autoescape is now ON (engine/config.py, audit finding #21), so the
    # template no longer needs -- and no longer has -- a `|safe` on this
    # value. The Markup() wrapper at the bottom of this function is what
    # keeps the card raw, and it is a claim this function has to earn: every
    # note-derived value interpolated above is escaped at its own site
    # (title, the prose fields, link_pill's label) or is a literal from this
    # module (icon, label, the Tailwind class strings).
    html_card = f"""
    <article onclick="openNote('{note_id}')" data-id="{note_id}" data-type="{escape_attr(note_type)}" data-label="{escape_attr(label)}" data-maturity="{maturity_slug}" data-tags="{escape_attr(tags_attr)}" data-title="{escape_attr(raw_title)}" data-connections="{connections}" data-created="{escape_attr(created)}" class="{base_classes} {color}">
        <span aria-hidden="true" class="absolute left-0 top-0 bottom-0 w-[3px] {spine} opacity-70 group-hover:opacity-100 transition-opacity"></span>
        <span aria-hidden="true" class="bracket-mark {label_color}"></span>
        <div class="flex justify-between items-start gap-3">
            <div class="min-w-0">
                <div class="flex items-center gap-2 mb-2">
                    <span class="w-1.5 h-1.5 {spine} rounded-full shadow-[0_0_8px_currentColor] {label_color}"></span>
                    <span class="field-label {label_color}">{label}</span>
                </div>
                <h3 class="display-md text-aurelia-text group-hover:text-aurelia-text transition-colors">{title}</h3>
            </div>
            <div class="flex flex-col items-end gap-2 shrink-0">
                <div class="text-2xl opacity-40 group-hover:opacity-100 transition-opacity duration-300">{icon}</div>
                {maturity_html}
                {connections_html}
            </div>
        </div>
        <hr class="hairline">
        {card_content}
    </article>
    """
    return Markup(html_card)
