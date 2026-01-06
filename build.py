import os
import re
import json
from jinja2 import Environment, FileSystemLoader

# --- CONFIGURATION ---
# Correct pathing: Sets the Root to the folder where build.py lives
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system/templates")
PROTOCOL_PATH = os.path.join(ROOT_DIR, "vault", "20_PROTOCOL")
OUTPUT_DIR = ROOT_DIR

# --- THEME ENGINE V2.0 (SEMANTIC) ---
THEME_CONFIG = {
    # 1. CYBER_PRIME (The Original)
    "CYBER_PRIME": {
        "name": "CYBER_PRIME",
        "colors": {
            "bg_main": "'#0a0a0b'",      # Was 'dark'
            "bg_dim": "'#1e1e20'",       # Was 'dim'
            "text_main": "'#ffffff'",    # Was 'text'
            "text_dim": "'#d1d5db'",     # New: for paragraphs
            
            "primary": "'#00f2ff'",      # Was 'cyan' (Headers, Garden)
            "secondary": "'#8a2be2'",    # Was 'purple' (Portfolio, Deep Accents)
            "tertiary": "'#ff8c00'",     # Was 'orange' (Services, Alerts)
            "accent": "'#39ff14'",       # Was 'green' (Links, Buttons, Status)
        },
        "font_mono": "'JetBrains Mono', 'monospace'",
        "bg_scanline": "true"
    },
    
    # 2. THE_PATRIOT (Red/White/Blue)
    "THE_PATRIOT": {
        "name": "THE_PATRIOT",
        "colors": {
            "bg_main": "'#ffffff'",      # White Background
            "bg_dim": "'#f3f4f6'",       # Light Gray
            "text_main": "'#111827'",    # Black Text
            "text_dim": "'#374151'",     # Gray Text
            
            "primary": "'#dc2626'",      # Red (Headers)
            "secondary": "'#1e3a8a'",    # Navy Blue (Portfolio)
            "tertiary": "'#b45309'",     # Amber/Gold (Services)
            "accent": "'#2563eb'",       # Royal Blue (Links)
        },
        "font_mono": "'Inter', 'sans-serif'",
        "bg_scanline": "false"
    },
}

# ⚡ ACTIVE THEME SELECTOR ⚡
# Change to THEME_CONFIG["CYBER_PRIME"] to go back to original
CURRENT_THEME = THEME_CONFIG["CYBER_PRIME"]

print(f"🔧 CONFIG: Root={ROOT_DIR}")
print(f"🔧 CONFIG: Vault={VAULT_PATH}")
print(f"🔧 CONFIG: Templates={TEMPLATE_DIR}")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- HELPER: Frontmatter Parser ---
def parse_frontmatter(content):
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}
    
    # FIX 1: Handle leading whitespace/newlines before frontmatter
    content = content.lstrip()
    if not content.startswith("---"): return meta
    
    try:
        parts = content.split("---", 2)
        if len(parts) < 3: return meta
        yaml_text = parts[1]
        
        # Publish Check
        if re.search(r'^publish:\s*true', yaml_text, re.MULTILINE | re.IGNORECASE):
             meta["publish"] = True
        
        # Extract basic strings
        for field in ["type", "status", "role", "cover_image", "date", "icon", "created"]:
            match = re.search(rf'^{field}:\s*(.+)$', yaml_text, re.MULTILINE)
            if match: 
                meta[field] = match.group(1).strip().strip('"').strip("'").replace("{{", "").replace("}}", "")
        
        # Link Handling
        repo = re.search(r'^link_repo:\s*(.+)$', yaml_text, re.MULTILINE)
        if repo: meta["link_repo"] = repo.group(1).strip()
        live = re.search(r'^link_live:\s*(.+)$', yaml_text, re.MULTILINE)
        if live: meta["link_live"] = live.group(1).strip()

        # Date Fallback
        if "date" not in meta and "created" in meta:
            meta["date"] = meta["created"]

        # FIX 2: Universal Tag Extraction
        # Captures inline: tags: [a, b]
        # Captures list:   - a
        tags = []
        
        # A. Inline Format
        inline_match = re.search(r'^tags:\s*\[(.*?)\]', yaml_text, re.MULTILINE)
        if inline_match:
            tags = [t.strip() for t in inline_match.group(1).split(',')]
        
        # B. List Format (Regex scan for lines starting with dash inside yaml)
        # We scan the whole yaml block for lines that look like list items
        # This is safer than state-machine parsing for simple flat lists
        if not tags:
            # Find lines that are "  - something" or "- something"
            # We assume these are tags if we didn't find inline tags
            # (Limitation: This assumes tags are the only list in FM, or distinct enough)
            list_matches = re.findall(r'^\s*-\s*(.+)$', yaml_text, re.MULTILINE)
            if list_matches:
                tags = [t.strip() for t in list_matches]
                
        meta["tags"] = tags

    except Exception as e:
        print(f"YAML Error: {e}")
    return meta

def parse_body(content):
    parts = content.split("---", 2)
    if len(parts) < 3: return content
    return parts[2].strip()

# --- EXTRACTORS (PROJECT SPECIFIC) ---

def extract_mission_brief(body):
    # Splits at the header, then ignores the rest of that header line (e.g. "(The Problem)")
    if "# 🚨 Mission Brief" in body:
        try:
            part = body.split("# 🚨 Mission Brief")[1]
            if "\n# " in part:
                part = part.split("\n# ")[0]
            
            # Remove the header suffix line if it exists
            lines = part.split('\n')
            clean_lines = [l for l in lines if not l.strip().startswith('(') and l.strip()]
            clean = " ".join(clean_lines)
            
            # Remove bold keys like **System Failure:**
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
            return clean[:240] + "..." if len(clean) > 240 else clean
        except Exception:
            pass
    return ""

def extract_core_logic(body):
    if "# 🛠️ Architecture" in body:
        try:
            part = body.split("# 🛠️ Architecture")[1]
            for line in part.split('\n'):
                if "**Core Logic:**" in line:
                    clean = line.replace("**Core Logic:**", "").strip()
                    clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
                    return clean
        except Exception:
            pass
    return ""

def extract_impact_metrics(body):
    metrics = []
    if "# ⚡ Operational Impact" in body:
        try:
            part = body.split("# ⚡ Operational Impact")[1]
            if "\n# " in part:
                part = part.split("\n# ")[0]
            matches = re.findall(r'[\-\*]\s*\*\*(.*?)\*\*[:\s]', part)
            metrics = [m.strip() for m in matches]
        except Exception:
            pass
    return metrics[:4]

# --- GARDEN EXTRACTORS (PRESERVED) ---
def extract_related_links(body):
    match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', body)
    if match:
        raw = match.group(1)
        links = re.findall(r'\[\[(.*?)\]\]', raw)
        clean_links = [l.split('|')[-1] for l in links]
        return clean_links
    return []

def extract_key_works(body):
    works = []
    capture = False
    for line in body.split('\n'):
        if "### 📚 Key Works" in line:
            capture = True
            continue
        if capture and line.strip().startswith("###"):
            break
        if capture and (line.strip().startswith("*") or line.strip().startswith("-")):
            clean = line.strip().replace("*", "").replace("-", "").strip()
            clean = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean)
            if clean: works.append(clean)
    return works[:3]

def extract_core_concepts(body):
    concepts = []
    header_match = re.search(r'###\s*.*(?:Core Concepts|Concepts Extracted).*', body)
    if header_match:
        try:
            start_idx = header_match.end()
            part = body[start_idx:]
            next_header = re.search(r'\n###', part)
            if next_header:
                part = part[:next_header.start()]
            links = re.findall(r'\[\[(.*?)\]\]', part)
            for l in links:
                name = l.split('|')[-1]
                if name not in concepts:
                    concepts.append(name)
        except Exception:
            pass
    return concepts[:4]

def extract_atomic_cues(body):
    cues = []
    pattern = re.compile(r'[\-\*]?\s*\*\*Concept:\*\*\s*\[\[(.*?)\]\]', re.IGNORECASE)
    for line in body.split('\n'):
        match = pattern.search(line)
        if match:
            cues.append(match.group(1).split('|')[-1])
    return cues[:3]

def extract_source_author(body):
    match = re.search(r'\*\*👤 Author:\*\*\s*\[\[(.*?)\]\]', body)
    if match: return match.group(1).split('|')[-1]
    match_plain = re.search(r'\*\*👤 Author:\*\*\s*(.*)', body)
    if match_plain: return match_plain.group(1).strip()
    return "Unknown"

def extract_brief_summary(body):
    if "**📝 BRIEF SUMMARY:**" in body:
        try:
            part = body.split("**📝 BRIEF SUMMARY:**")[1]
            summary_block = part.split("---")[0]
            clean = summary_block.replace(">", "").strip()
            return clean
        except IndexError:
            return ""
    return ""

def extract_definition(body):
    if "Definition" in body:
        try:
            # Flexible match for Definition header
            part = re.split(r'###\s*.*Definition.*', body)[1]
            lines = []
            for line in part.split('\n'):
                stripped = line.strip()
                if stripped.startswith(">"):
                    lines.append(stripped.replace(">", "").strip())
                elif stripped.startswith("#") or (lines and not stripped):
                    break
            clean_text = " ".join(lines)
            clean_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_text)
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
            return clean_text
        except Exception:
            return ""
    return ""

def extract_profile_context(body):
    if "Profile & Context" in body:
        try:
            part = re.split(r'###\s*.*Profile & Context.*', body)[1]
            lines = []
            for line in part.split('\n'):
                stripped = line.strip()
                if stripped.startswith(">"):
                    lines.append(stripped.replace(">", "").strip())
                elif stripped.startswith("#") or (lines and not stripped):
                    break
            clean_text = " ".join(lines)
            clean_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_text)
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
            return clean_text
        except Exception:
            return ""
    return ""

def extract_core_argument(body):
    if "Core Argument" in body:
        try:
            part = re.split(r'###\s*.*Core Argument.*', body)[1]
            lines = []
            for line in part.split('\n'):
                stripped = line.strip()
                if stripped.startswith(">"):
                    lines.append(stripped.replace(">", "").strip())
                elif stripped.startswith("#") or (lines and not stripped):
                    break
            clean_text = " ".join(lines)
            clean_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_text)
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
            return clean_text
        except Exception:
            return ""
    return ""

def extract_definition_scope(body):
    if "Definition (The Scope)" in body:
        try:
            part = body.split("### 🧐 Definition (The Scope)")[1]
            lines = []
            for line in part.split('\n'):
                stripped = line.strip()
                if stripped.startswith(">"):
                    lines.append(stripped.replace(">", "").strip())
                elif stripped.startswith("#") or (lines and not stripped):
                    break
            clean_text = " ".join(lines)
            clean_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_text)
            clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_text)
            return clean_text
        except Exception:
            return ""
    return ""

def extract_foundational_texts(body):
    texts = []
    capture = False
    for line in body.split('\n'):
        if "Foundational Texts" in line and "###" in line:
            capture = True
            continue
        if capture and line.strip().startswith("###"):
            break
        if capture and (line.strip().startswith("*") or line.strip().startswith("-")):
            match = re.search(r'\[\[(.*?)\]\]', line)
            if match:
                texts.append(match.group(1).split('|')[-1])
    return texts[:3]

# --- GENERATORS ---

def generate_garden_card_html(meta, filename, note_id, body_content):
    note_type = meta.get("type", "unknown").lower()
    
    # 1. Fallback: Check Tags for "type/..."
    if (note_type == "unknown" or not note_type) and meta.get("tags"):
        for tag in meta["tags"]:
            if tag.startswith("type/"):
                note_type = tag.split("/")[1]
                break
    
    # 2. FAIL-SAFE: Filename Date Check (YYYY-MM-DD)
    # If the filename looks like a date, it IS a daily log. Period.
    if re.match(r'\d{4}-\d{2}-\d{2}', filename):
        note_type = "daily-bridge"

    meta["type"] = note_type
    title = filename.replace(".md", "").replace("_", " ")
    
    # ... (Rest of function continues below) ...
    
    clean_body = re.sub(r'#{1,6}\s.*', '', body_content)
    clean_body = re.sub(r'\*\*.*?\*\*.*', '', clean_body)
    clean_body = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_body)
    clean_body = re.sub(r'[*_]{2,}', '', clean_body)
    clean_body = " ".join(clean_body.split())
    blurb = clean_body[:380].strip() + "..."
    
    raw_search = f"{title} {note_type} {body_content}".lower()
    search_text = raw_search.replace('\n', ' ').replace('"', "'").replace("  ", " ")

    if "daily" in note_type or "log" in note_type or "bridge" in note_type:
        color = "border-aurelia-tertiary"
        icon = "📅"
        label = "Daily_Log"
        summary = extract_brief_summary(body_content)
        blurb = summary if summary else blurb
        cues = extract_atomic_cues(body_content)
        footer_html = '<div class="mt-auto pt-4 flex items-center justify-start border-t border-gray-800/50"><div class="flex gap-2 flex-wrap">'
        for cue in cues:
             footer_html += f'<span class="text-xs font-mono px-2 py-1 bg-aurelia-tertiary/10 text-aurelia-tertiary border border-aurelia-tertiary/20 rounded">{cue}</span>'
        footer_html += '</div></div>'
        
    elif "concept" in note_type:
        color = "border-aurelia-primary"
        icon = "⚛️"
        label = "Concept_Node"
        defin = extract_definition(body_content)
        blurb = defin if defin else blurb
        related = extract_related_links(body_content)[:3]
        footer_html = '<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-xs text-aurelia-primary font-mono mb-2 opacity-90">LINKED_TO:</div><div class="flex gap-3 text-xs text-gray-300 font-mono flex-wrap">'
        if related:
            for link in related:
                footer_html += f'<span class="hover:text-white transition-colors cursor-pointer">→ {link}</span>'
        else:
            footer_html += '<span class="opacity-50">// ROOT</span>'
        footer_html += '</div></div>'

    elif "author" in note_type:
        color = "border-white"
        icon = "👤"
        label = "Author_Profile"
        prof = extract_profile_context(body_content)
        blurb = prof if prof else blurb
        works = extract_key_works(body_content)
        concepts = extract_core_concepts(body_content)[:3]
        footer_html = '<div class="mt-auto pt-4 border-t border-gray-800/50 flex flex-col gap-3">'
        if works:
            footer_html += '<div><div class="text-[10px] font-mono text-gray-500 mb-1 uppercase tracking-wider">KEY WORKS:</div><ul class="text-[10px] font-mono text-gray-300 space-y-1">'
            for work in works:
                footer_html += f'<li class="flex items-center gap-2"><span class="text-aurelia-accent">●</span> {work}</li>'
            footer_html += '</ul></div>'
        if concepts:
            footer_html += '<div><div class="text-[10px] font-mono text-gray-500 mb-1 uppercase tracking-wider">CONCEPTS:</div><div class="flex flex-wrap gap-2">'
            for c in concepts:
                footer_html += f'<span class="text-[10px] font-mono border border-gray-700 px-1.5 py-0.5 rounded text-gray-400 hover:text-white transition-colors cursor-pointer">{c}</span>'
            footer_html += '</div></div>'
        footer_html += '</div>'

    elif "source" in note_type:
        color = "border-yellow-500"
        icon = "📖"
        label = "Source_Text"
        arg = extract_core_argument(body_content)
        blurb = arg if arg else blurb
        author = extract_source_author(body_content)
        status = meta.get("status", "UNKNOWN").upper()
        if meta.get("tags"):
            for tag in meta["tags"]:
                if "reading" in tag: status = "READING"
                if "archive" in tag: status = "ARCHIVE"
        concepts = extract_core_concepts(body_content)[:3]
        footer_html = f'''
        <div class="mt-auto pt-4 border-t border-gray-800/50 flex flex-col gap-3">
            <div class="flex justify-between items-center">
                <div class="text-xs font-mono text-gray-400">AUTH: {author.upper()}</div>
                <span class="px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-500 text-xs font-mono border border-yellow-500/20">{status}</span>
            </div>
        '''
        if concepts:
             footer_html += '<div class="flex flex-wrap gap-2">'
             for c in concepts:
                 footer_html += f'<span class="text-[10px] font-mono border border-gray-700 px-1.5 py-0.5 rounded text-gray-400 hover:text-white transition-colors cursor-pointer">{c}</span>'
             footer_html += '</div>'
        footer_html += '</div>'

    elif "discipline" in note_type:
        color = "border-aurelia-accent"
        icon = "🧠"
        label = "Discipline"
        defin = extract_definition_scope(body_content)
        blurb = defin if defin else blurb
        concepts = extract_core_concepts(body_content)[:3]
        texts = extract_foundational_texts(body_content)
        footer_html = '<div class="mt-auto pt-4 border-t border-gray-800/50 grid grid-cols-2 gap-4">'
        footer_html += '<div><div class="text-[10px] font-mono text-gray-500 mb-1 uppercase tracking-wider">CONCEPTS:</div><ul class="text-[10px] font-mono text-gray-300 space-y-1">'
        for c in concepts:
            footer_html += f'<li class="flex items-center gap-1 overflow-hidden truncate"><span class="text-aurelia-accent">●</span> {c}</li>'
        footer_html += '</ul></div>'
        footer_html += '<div><div class="text-[10px] font-mono text-gray-500 mb-1 uppercase tracking-wider">TEXTS:</div><ul class="text-[10px] font-mono text-gray-300 space-y-1">'
        for t in texts:
            footer_html += f'<li class="flex items-center gap-1 overflow-hidden truncate"><span class="text-aurelia-accent">●</span> {t}</li>'
        footer_html += '</ul></div></div>'
        
    else:
        color = "border-gray-800"
        icon = "📄"
        label = "Node"
        footer_html = f'<div class="mt-auto pt-4 border-t border-gray-800/50 text-xs text-gray-500">#{note_type}</div>'

    html_card = f"""
    <article 
        onclick="openNote('{note_id}')" 
        data-type="{note_type}"
        data-search="{search_text}"
        class="searchable-item glass p-6 rounded-sm border-2 {color} border-opacity-60 hover:border-opacity-100 cursor-pointer flex flex-col gap-4 transition-all duration-300 hover:scale-[1.12] hover:z-10 group min-h-[320px]">
        
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-2">
                    <span class="w-1.5 h-1.5 {color.replace('border-', 'bg-')} rounded-full"></span>
                    <span class="text-[16px] font-mono {color.replace('border-', 'text-')} uppercase tracking-widest">{label}</span>
                </div>
                <h3 class="text-4xl font-bold text-white font-mono group-hover:text-white transition-colors leading-tight">{title}</h3>
            </div>
            <div class="text-5xl filter drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] transition-transform group-hover:scale-110">{icon}</div>
        </div>

        <div class="w-full h-px bg-gray-800/50"></div>

        <p class="text-lg text-gray-100 leading-relaxed font-normal line-clamp-5">
            {blurb}
        </p>
        
        {footer_html}
    </article>
    """
    return html_card

def generate_project_card(meta, sections, title, note_id):
    status_dot = "bg-aurelia-accent shadow-[0_0_10px_#39ff14]" if meta.get("status") == "active" else "bg-gray-500"
    role = meta.get('role', 'Architect')
    body = sections.get('brief', '')
    
    mission = extract_mission_brief(body)
    logic = extract_core_logic(body)
    impacts = extract_impact_metrics(body)
    
    live_link = meta.get('link_live')
    
    action_buttons = '<div class="flex items-center gap-3 pt-6 mt-auto border-t border-purple-500/20">'
    if live_link:
        action_buttons += f'''
        <a href="{live_link}" target="_blank" onclick="event.stopPropagation()" 
           class="group flex items-center gap-2 px-3 py-1.5 text-[10px] font-mono text-purple-300 border border-purple-500/50 hover:bg-purple-500/10 hover:text-white hover:border-purple-400 transition-all rounded uppercase tracking-wider">
           <span class="w-1.5 h-1.5 bg-green-400 rounded-full group-hover:animate-pulse"></span>
           LIVE_SYSTEM
        </a>
        '''
    action_buttons += f'''
    <button onclick="openNote('{note_id}'); event.stopPropagation()" 
            class="ml-auto flex items-center gap-2 px-3 py-1.5 text-[10px] font-mono text-gray-500 border border-gray-800 hover:border-purple-500/50 hover:text-white transition-all rounded uppercase tracking-wider group">
        <svg class="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path></svg>
        EXTRACT_DATA
    </button>
    </div>
    '''

    search_text = f"{title} project {mission} {logic}".lower().replace('\n', ' ').replace('"', "'")

    html = f"""
    <div class="searchable-item glass p-8 rounded-sm border-2 border-purple-500/20 hover:border-purple-500/60 cursor-pointer flex flex-col gap-6 transition-all duration-300 hover:scale-[1.01] hover:shadow-[0_0_30px_rgba(168,85,247,0.1)] group min-h-[450px]"
         data-type="project" 
         data-search="{search_text}"
         onclick="openNote('{note_id}')">
        
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-2">
                    <span class="w-1.5 h-1.5 {status_dot} rounded-full"></span>
                    <span class="text-[11px] font-mono text-purple-400 uppercase tracking-widest">PROJECT_NODE</span>
                </div>
                <h3 class="text-3xl font-bold text-white font-mono leading-tight group-hover:text-purple-200 transition-colors">{title.replace('_', ' ').replace('.md', '')}</h3>
                <p class="text-[10px] text-gray-500 font-mono mt-1 uppercase">ROLE: {role}</p>
            </div>
            <div class="text-4xl opacity-30 group-hover:opacity-80 transition-opacity filter drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]">🚀</div>
        </div>

        <div class="w-full h-px bg-purple-500/20"></div>

        <div class="flex flex-col gap-2">
            <span class="text-[10px] font-mono text-purple-500/70 uppercase tracking-wider">MISSION_BRIEF:</span>
            <p class="text-sm text-gray-300 font-sans leading-relaxed line-clamp-3 opacity-90">
                {mission}
            </p>
        </div>

        <div class="flex flex-col gap-2 flex-grow">
            <span class="text-[10px] font-mono text-purple-500/70 uppercase tracking-wider">CORE_LOGIC:</span>
            <p class="text-xs text-gray-400 font-mono border-l-2 border-purple-500/30 pl-3 italic">
                "{logic}"
            </p>
        </div>

        <div class="flex flex-wrap gap-2 mb-2">
            { "".join([f'<span class="text-[10px] font-mono border border-purple-500/20 bg-purple-500/5 text-purple-300 px-2 py-1 rounded">{m}</span>' for m in impacts]) }
        </div>

        {action_buttons}
    </div>
    """
    return html

def build_all():
    print("\n🧬 AURELIA SYSTEM: INITIALIZING JINJA CORE...")

    # --- 0. LOAD IDENTITY CHIP ---
    config_path = os.path.join(ROOT_DIR, "user_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        print(f"   + Identity Loaded: {user_config['author']['name']}")
    except Exception as e:
        print(f"   ⚠️ WARNING: Could not load user_config.json. Using defaults. ({e})")
        user_config = { "author": { "name": "Unknown User" } } # Fallback

    # ... (Rest of your existing code: garden_cards = [], etc.)
    
    # 1. LOAD DATA CONTAINERS
    garden_cards = []
    portfolio_cards = []
    protocol_cards = []

    # 2. SCAN VAULT (Garden & Portfolio)
    for root, dirs, files in os.walk(VAULT_PATH):
        for filename in sorted(files):
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                meta = parse_frontmatter(content)
                if not meta.get("publish"): continue 

                body = parse_body(content)
                note_type = meta.get("type", "unknown").lower()
                tags = meta.get("tags", [])  # <--- CAPTURE TAGS
                
                # Logic to separate Projects from Notes
                if "project" in note_type:
                    project_id = f"project-{len(portfolio_cards)}"
                    sections = {"brief": body}
                    card_html = generate_project_card(meta, sections, filename, project_id)
                    portfolio_cards.append({
                        "html": card_html, 
                        "body": body, 
                        "id": project_id,
                        "title": filename.replace(".md", "").replace("_", " "),
                        "link": f"portfolio.html#{project_id}", 
                        "type": "PROJECT",
                        "tags": tags,           # <--- SAVE TAGS
                        "desc": extract_mission_brief(body) # <--- SAVE BRIEF
                    })
                else:
                    note_id = f"note-{len(garden_cards)}"
                    card_html = generate_garden_card_html(meta, filename, note_id, body)
                    
                    # Extract a clean text blurb for searching
                    clean_text = re.sub(r'[*#_`\[\]]', '', body)[:200]
                    
                    garden_cards.append({
                        "html": card_html, 
                        "body": body, 
                        "id": note_id,
                        "title": filename.replace(".md", "").replace("_", " "),
                        "link": f"garden.html#{note_id}", 
                        "type": "NOTE",
                        "tags": tags,          # <--- SAVE TAGS
                        "desc": clean_text     # <--- SAVE PREVIEW
                    })

    # 3. SCAN PROTOCOLS
    if os.path.exists(PROTOCOL_PATH):
        for filename in os.listdir(PROTOCOL_PATH):
            if filename.endswith(".md"):
                filepath = os.path.join(PROTOCOL_PATH, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                meta = parse_frontmatter(content)
                if not meta.get("publish", False): continue
                
                # Use ID if present, else generate one
                p_id = meta.get("id", "PROT_" + filename[:3].upper())
                
                protocol_cards.append({
                    "title": meta.get("title", filename.replace(".md", "")),
                    "desc": meta.get("description", "System Protocol"),
                    "tags": meta.get("tags", []),
                    "body": content.split("---", 2)[2] if len(content.split("---", 2)) > 2 else content,
                    "id": p_id,
                    "link": f"protocol.html", # Protocols are currently in a drawer, linking to page is safest
                    "type": "PROTOCOL"
                })

    print(f"   + Indexing: {len(garden_cards)} Notes, {len(portfolio_cards)} Projects, {len(protocol_cards)} Protocols")

    # 4. BUILD MASTER SEARCH INDEX
    master_index = []
    
    # Add System Pages
    master_index.append({"title": "Home // Mission Control", "url": "index.html", "type": "SYSTEM", "tags": ["home", "root"], "desc": "Main Hub"})
    master_index.append({"title": "The Garden // Input", "url": "garden.html", "type": "SYSTEM", "tags": ["notes", "writing"], "desc": "Digital Garden"})
    master_index.append({"title": "Protocols // Logic", "url": "protocol.html", "type": "SYSTEM", "tags": ["sop", "routines"], "desc": "Operating Procedures"})
    master_index.append({"title": "Portfolio // Output", "url": "portfolio.html", "type": "SYSTEM", "tags": ["work", "jobs"], "desc": "Case Studies"})
    
    # Add Content
    for c in garden_cards: 
        master_index.append({
            "title": c['title'], 
            "url": c['link'], 
            "type": "GARDEN", 
            "tags": c['tags'],     # <--- PASS TAGS TO FRONTEND
            "desc": c['desc']      # <--- PASS DESC TO FRONTEND
        })
        
    for p in portfolio_cards: 
        master_index.append({
            "title": p['title'], 
            "url": p['link'], 
            "type": "PROJECT", 
            "tags": p['tags'], 
            "desc": p['desc']
        })
        
    for prot in protocol_cards: 
        master_index.append({
            "title": prot['title'], 
            "url": prot['link'], 
            "type": "PROTOCOL", 
            "tags": prot['tags'], 
            "desc": prot['desc']
        })
    
    # Add Content Content
    for c in garden_cards: master_index.append({"title": c['title'], "url": c['link'], "type": "GARDEN"})
    for p in portfolio_cards: master_index.append({"title": p['title'], "url": p['link'], "type": "PROJECT"})
    for prot in protocol_cards: master_index.append({"title": prot['title'], "url": prot['link'], "type": "PROTOCOL"})

    # Serialize to JSON string
    json_index = json.dumps(master_index)

    # 5. RENDER PAGES
    pages = [
        ("pages/indextemplate.html", "index.html", {}),
        ("pages/gardentemplate.html", "garden.html", {"cards": garden_cards}),
        ("pages/portfoliotemplate.html", "portfolio.html", {"projects": portfolio_cards}),
        ("pages/servicestemplate.html", "services.html", {}),
        ("pages/protocoltemplate.html", "protocol.html", {"protocols": protocol_cards}), 
        ("404.html", "404.html", {}),
    ]

    # ... inside the pages loop ...
    for template_name, output_name, context in pages:
        try:
            # INJECT DATA
            context["theme"] = CURRENT_THEME 
            context["search_index"] = json_index
            context["config"] = user_config  # <--- THIS IS THE NEW LINE
            
            template = env.get_template(template_name)
            # ... rest of render code
            rendered_html = template.render(active_page=output_name.replace(".html", ""), **context)
            
            with open(os.path.join(OUTPUT_DIR, output_name), "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"   ✅ Deployed: {output_name}")
        except Exception as e:
            print(f"   ❌ Failed: {output_name} -> {e}")

    print("\n✅ SYSTEM SYNC COMPLETE.")
 

if __name__ == "__main__":
    build_all()