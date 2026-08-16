"""The Card Factory: renders the HTML card for a single note, by type."""
import re

from engine.extractors import (
    extract_author_data,
    extract_concept_data,
    extract_core_logic,
    extract_discipline_data,
    extract_impact_metrics,
    extract_log_data,
    extract_mission_brief,
    extract_notebooklm_data,
    extract_protocol_logic,
    extract_protocol_sequence,
    extract_source_data,
)
from engine.textutils import truncate


def render_items(items, render_item, empty_html=""):
    """Joins rendered items, or falls back to empty_html when the list is empty.

    Replaces the repeated `''.join([f'...' for x in items]) + ('' if items else
    '<empty state markup>')` pattern that recurred across every card type.
    """
    if not items:
        return empty_html
    return ''.join(render_item(i) for i in items)


def generate_garden_card_html(meta, filename, note_id, body_content, full_search_text):
    note_type = meta.get("type", "unknown").lower()

    if (note_type == "unknown" or not note_type) and meta.get("tags"):
        for tag in meta["tags"]:
            if tag.startswith("type/"):
                note_type = tag.split("/")[1]
                break
    if re.match(r'\d{4}-\d{2}-\d{2}', filename):
        note_type = "daily-bridge"
    meta["type"] = note_type
    title = filename.replace(".md", "").replace("_", " ")

    base_classes = ("searchable-item glass p-5 rounded-sm border border-opacity-40 "
                     "hover:border-opacity-100 cursor-pointer flex flex-col gap-3 "
                     "transition-all duration-300 hover:translate-y-[-4px] hover:shadow-2xl "
                     "hover:z-10 group h-full min-h-[240px]")

    if "daily" in note_type or "log" in note_type:
        color = "border-aurelia-tertiary"
        mission, source, cues, summary = extract_log_data(body_content)
        summary = truncate(summary, 120)

        cues_html = render_items(
            cues,
            lambda c: f'<span class="text-[10px] font-mono px-2 py-0.5 bg-aurelia-tertiary/10 text-aurelia-tertiary border border-aurelia-tertiary/30 rounded-sm font-bold">{c}</span>',
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
                    <span class="text-[10px] font-bold font-mono text-aurelia-tertiary uppercase truncate w-full">SRC: {source[:40]}</span>
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
            lambda l: f'<span class="hover:text-aurelia-primary transition-colors cursor-pointer border-b border-gray-700 hover:border-aurelia-primary pb-0.5">→ {l}</span>',
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

        concepts_html = render_items(
            concepts,
            lambda c: f'<span class="text-[9px] font-mono px-1.5 py-0.5 border border-yellow-500/40 text-gray-300 rounded-sm hover:text-yellow-500 transition-colors cursor-default">{c}</span>',
            empty_html='<span class="opacity-30 text-[9px] text-gray-500 font-mono">// NO_CONCEPTS_LINKED</span>',
        )
        card_content = f"""
        <div class="flex flex-col h-full gap-3">

            <div class="flex justify-between items-end border-b border-yellow-500/30 pb-2">
                <span class="text-[10px] font-bold font-mono text-yellow-500 uppercase tracking-wider truncate mr-2">AUTH: {author}</span>
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
            lambda c: f'<span class="text-[9px] font-mono px-2 py-1 bg-aurelia-secondary text-black font-bold rounded-sm border border-aurelia-secondary">{c}</span>',
            empty_html='<span class="text-[9px] text-white font-mono opacity-80">// NO_SYSTEMS_DETECTED</span>',
        )
        works_html = render_items(
            works,
            lambda w: f'<span class="text-[9px] font-mono px-2 py-0.5 border border-gray-400 text-white font-bold rounded-sm hover:border-aurelia-secondary hover:text-aurelia-secondary transition-colors cursor-default">{w}</span>',
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
            lambda p: f'<span class="text-[9px] font-mono px-2 py-1 bg-aurelia-accent text-black font-extrabold rounded-sm uppercase">{p}</span>',
            empty_html='<span class="text-[9px] text-gray-500 font-mono">// FOUNDATIONS_PENDING</span>',
        )
        canon_html = render_items(
            canon,
            lambda t: f'<span class="text-[10px] font-serif italic text-gray-300 hover:text-white transition-colors truncate">• {t}</span>',
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
    <article onclick="openNote('{note_id}')" data-type="{note_type}" data-search="{title} {note_type} {full_search_text}" class="{base_classes} {color}">
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-1.5">
                    <span class="w-1.5 h-1.5 {color.replace('border-', 'bg-')} rounded-full"></span>
                    <span class="text-[10px] font-mono {color.replace('border-', 'text-')} uppercase tracking-widest">{label}</span>
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


def generate_project_card(meta, sections, title, note_id):
    is_active = meta.get("status") == "active"
    status_color = "bg-aurelia-accent shadow-[0_0_10px_#39ff14]" if is_active else "bg-gray-500"
    status_text = "ONLINE" if is_active else "ARCHIVED"

    role = meta.get('role', 'Architect')
    body = sections.get('brief', '')

    mission = extract_mission_brief(body)
    logic = extract_core_logic(body)
    impacts = extract_impact_metrics(body)

    tech_stack = meta.get("tech_stack", [])
    if isinstance(tech_stack, str):
        tech_stack = [tech_stack]

    live_link = meta.get('link_live')

    action_buttons = '<div class="flex items-center gap-3 mt-auto pt-4 border-t border-gray-700">'
    if live_link:
        action_buttons += f'''
        <a href="{live_link}" target="_blank" onclick="event.stopPropagation()"
           class="flex items-center gap-2 px-3 py-2 text-[10px] font-mono font-bold text-black bg-aurelia-secondary hover:bg-white transition-colors rounded-sm uppercase tracking-wider">
            🚀 LAUNCH_SYSTEM
        </a>
        '''
    action_buttons += f'''
    <button onclick="openNote('{note_id}'); event.stopPropagation()"
            class="ml-auto flex items-center gap-2 px-3 py-2 text-[10px] font-mono text-white border border-gray-500 hover:border-aurelia-text hover:text-aurelia-text hover:bg-white/5 transition-all rounded-sm uppercase tracking-wider">
        <span>ACCESS_DOSSIER</span>
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
    </button>
    </div>
    '''

    search_text = f"{title} project {mission} {logic}".lower().replace('\n', ' ').replace('"', "'")

    tech_html = render_items(
        tech_stack[:4],
        lambda t: f'<span class="text-[9px] font-mono text-black bg-white px-1.5 py-0.5 rounded-sm font-bold uppercase">{t}</span>',
    )
    impacts_html = render_items(
        impacts,
        lambda m: f'<span class="text-[10px] font-mono text-gray-300 border border-gray-600 px-2 py-1 rounded-sm">⚡ {m}</span>',
    )

    html = f"""
    <div class="searchable-item group relative flex flex-col gap-5 p-6 min-h-[520px]
                bg-black border-2 border-gray-800
                hover:border-aurelia-secondary hover:shadow-[0_0_30px_rgba(138,43,226,0.2)]
                transition-all duration-300 rounded-sm cursor-pointer overflow-hidden"
         data-type="project"
         data-search="{search_text}"
         onclick="openNote('{note_id}')">

        <div class="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-gray-800 group-hover:border-aurelia-secondary transition-colors"></div>
        <div class="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-gray-800 group-hover:border-aurelia-secondary transition-colors"></div>

        <div class="flex justify-between items-start z-10">
            <div class="w-full">
                <div class="flex items-center justify-between mb-3 w-full">
                    <span class="px-2 py-1 rounded-sm text-[10px] font-bold font-mono bg-aurelia-secondary text-black border border-aurelia-secondary uppercase">
                        {role}
                    </span>
                    <div class="flex items-center gap-1.5 px-2 py-1 rounded border border-gray-700 bg-gray-900">
                        <span class="w-2 h-2 {status_color} rounded-full"></span>
                        <span class="text-[10px] font-mono text-white font-bold uppercase tracking-wider">{status_text}</span>
                    </div>
                </div>
                <h3 class="text-3xl font-black text-white font-sans tracking-tight leading-none group-hover:text-aurelia-secondary transition-colors uppercase">
                    {title.replace('_', ' ').replace('.md', '')}
                </h3>
            </div>
        </div>

        <div class="flex flex-col gap-2 z-10">
            <span class="text-[10px] font-bold font-mono text-aurelia-secondary uppercase tracking-widest border-b border-gray-800 pb-1">MISSION_PARAMETER</span>
            <p class="text-sm text-white font-sans leading-relaxed line-clamp-3 font-medium">
                "{mission}"
            </p>
        </div>

        <div class="flex flex-col gap-2 flex-grow z-10">
            <span class="text-[10px] font-bold font-mono text-aurelia-secondary uppercase tracking-widest border-b border-gray-800 pb-1">SYSTEM_LOGIC</span>
            <div class="bg-gray-900 border-l-4 border-aurelia-secondary p-3 rounded-r-sm h-full">
                <p class="text-xs text-gray-300 font-mono leading-relaxed italic">
                    <span class="text-aurelia-secondary font-bold">>></span> {logic if logic else "Classified / Internal Logic Only."}
                </p>
            </div>
        </div>

        <div class="z-10 space-y-3">
             <div class="flex flex-wrap gap-1.5">
                {tech_html}
             </div>

             <div class="flex flex-wrap gap-2">
                {impacts_html}
             </div>
        </div>

        {action_buttons}
    </div>
    """
    return html


def generate_protocol_card(meta, body, title, note_id, p_id_override=None):
    prot_id = p_id_override if p_id_override else meta.get("id", "SYS_CMD").upper()
    sequence = extract_protocol_sequence(body)
    logic = extract_protocol_logic(body)

    is_auto = "automated" in meta.get("tags", [])
    status_text = "DAEMON" if is_auto else "MANUAL"

    search_text = f"{title} {prot_id} {' '.join(sequence)}".lower()

    def render_step(item_with_index):
        i, item = item_with_index
        return f"""
                <div class="flex items-start gap-3 group/item">
                    <span class="text-gray-500 font-bold text-xs shrink-0 select-none group-hover:text-aurelia-accent transition-colors">0{i+1}</span>
                    <span class="text-sm text-gray-200 font-medium group-hover/item:text-white transition-colors border-l-2 border-gray-800 pl-3 leading-snug">
                        {item}
                    </span>
                </div>
                """

    steps_html = render_items(
        list(enumerate(sequence)),
        render_step,
        empty_html='<span class="text-sm text-gray-500 italic">// NO_STEPS_DETECTED</span>',
    )

    html = f"""
    <div class="searchable-item group relative flex flex-col gap-0 min-h-[420px]
                bg-[#09090b] border border-gray-700
                hover:border-aurelia-accent hover:shadow-[0_0_20px_rgba(57,255,20,0.15)]
                transition-all duration-200 rounded-sm cursor-pointer overflow-hidden font-mono"
         data-type="protocol"
         data-search="{search_text}"
         onclick="openNote('{prot_id}')">

        <div class="bg-[#18181b] border-b border-gray-700 p-4 flex justify-between items-center group-hover:bg-[#27272a] transition-colors">
            <div class="flex items-center gap-3">
                <div class="relative flex h-2 w-2">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-aurelia-accent opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-aurelia-accent"></span>
                </div>
                <span class="text-xs font-bold text-white tracking-widest">{prot_id}</span>
            </div>
            <span class="text-[10px] font-bold text-gray-400 uppercase bg-black/50 px-2 py-1 rounded border border-gray-700">{status_text}</span>
        </div>

        <div class="p-6 border-b border-gray-800">
            <h3 class="text-xl font-black text-white uppercase tracking-tight group-hover:text-aurelia-accent transition-colors leading-none">
                {title.replace('_', ' ').replace('.md', '')}
            </h3>
        </div>

        <div class="p-6 flex flex-col gap-4 flex-grow bg-[#09090b]">
            <span class="text-[10px] font-bold text-aurelia-accent uppercase tracking-widest border-b border-gray-800 pb-2 w-full">
                >> EXECUTION_STEPS:
            </span>

            <div class="flex flex-col gap-2.5 mt-1">
                {steps_html}
            </div>
        </div>

        <div class="p-5 bg-[#18181b] border-t border-gray-700 mt-auto">
            <div class="flex items-start gap-3">
                <span class="text-aurelia-accent font-bold text-sm">i</span>
                <p class="text-xs text-gray-300 font-sans leading-relaxed">
                    {logic if logic else "Standard operating procedure."}
                </p>
            </div>
        </div>

        <div class="absolute inset-x-0 bottom-0 h-1 bg-aurelia-accent opacity-0 group-hover:opacity-100 transition-opacity duration-300 shadow-[0_-2px_10px_rgba(57,255,20,0.5)]"></div>
    </div>
    """
    return html
