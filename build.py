import os
import re
import json
from jinja2 import Environment, FileSystemLoader

# --- ⚡ RESTORED ENGINE BLOCK ⚡ ---

def make_id(text):
    """Turns 'My Cool Note.md' into 'note-my-cool-note'"""
    # Remove file extension and lowercase
    text = text.replace(".md", "").lower()
    # Replace non-alphanumeric chars (spaces, underscores) with dashes
    slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return f"note-{slug}"

def process_wikilinks(text):
    """Converts [[Link]] to clickable Modal Buttons"""
    def replace_link(match):
        content = match.group(1)
        # Handle Piped Links: [[Target|Label]]
        if '|' in content:
            target, label = content.split('|', 1)
        else:
            target, label = content, content
            
        target_id = make_id(target)
        # Returns a button that triggers the existing openNote() JS function
        return f'<button onclick="openNote(\'{target_id}\')" class="text-aurelia-primary hover:underline font-bold bg-transparent border-none cursor-pointer p-0 inline">{label}</button>'

    return re.sub(r'\[\[(.*?)\]\]', replace_link, text)

# -----------------------------------

# --- CONFIGURATION ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# ... (Rest of file continues)
VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system/templates")
PROTOCOL_PATH = os.path.join(ROOT_DIR, "vault", "20_PROTOCOL")
OUTPUT_DIR = ROOT_DIR

# --- THEME ENGINE V2.1 (FULL SEMANTIC) ---
THEME_CONFIG = {
    # 1. CYBER_PRIME (Dark / Neon)
    "CYBER_PRIME": {
        "name": "CYBER_PRIME",
        "colors": {
            # Base Layer
            "bg_main": "'#0a0a0b'",       # Deepest Black
            "bg_layer_1": "'#121214'",    # Slightly Lighter (Cards)
            "bg_layer_2": "'#18181b'",    # Hovers / Modals
            
            # Typography
            "text_main": "'#ffffff'",     # White text
            "text_muted": "'#9ca3af'",    # Gray text
            "text_inverted": "'#000000'", # Black text (for buttons on bright bgs)

            # Structure
            "border_main": "'#27272a'",   # Dark Gray Borders
            "border_focus": "'#00f2ff'",  # Cyan Focus
            
            # Roles
            "primary": "'#00f2ff'",       # Cyan (Headings, Key Data)
            "secondary": "'#8a2be2'",     # Purple (Creative, Portfolio)
            "tertiary": "'#ff8c00'",      # Orange (Commerce, Alerts)
            "accent": "'#39ff14'",        # Green (Success, Terminal)
        },
        "font_mono": "'JetBrains Mono', 'monospace'",
        "rounded": "'2px'",               # Sharp corners
        "glass_opacity": "'0.6'"          # Heavy glass
    },
    
    # 2. THE_PATRIOT (Light / Academic / CIA Dossier Style)
    "THE_PATRIOT": {
        "name": "THE_PATRIOT",
        "colors": {
            # Base Layer
            "bg_main": "'#fdfbf7'",       # Warm Paper White
            "bg_layer_1": "'#ffffff'",    # Pure White (Cards)
            "bg_layer_2": "'#f3f4f6'",    # Light Gray (Hovers)
            
            # Typography
            "text_main": "'#111827'",     # Deep Black/Blue (Ink)
            "text_muted": "'#4b5563'",    # Gray
            "text_inverted": "'#ffffff'", # White text (for solid buttons)

            # Structure
            "border_main": "'#e5e7eb'",   # Light Gray Borders
            "border_focus": "'#1d4ed8'",  # Navy Focus
            
            # Roles
            "primary": "'#1e3a8a'",       # Navy Blue (Headings - Authority)
            "secondary": "'#dc2626'",     # Crimson Red (Alerts - Action)
            "tertiary": "'#b45309'",      # Amber/Gold (Highlights)
            "accent": "'#2563eb'",        # Royal Blue (Links)
        },
        "font_mono": "'Courier Prime', 'Courier New', monospace", # Typewriter style
        "rounded": "'8px'",               # Softer corners
        "glass_opacity": "'0.95'"         # Solid paper look (less glass)
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
        
        # [UPDATED] Extract basic strings - Added audio_file, visual_loop, series, episode, summary
        target_fields = [
            "type", "status", "role", "cover_image", "date", "icon", "created", 
            "audio_file", "visual_loop", "series", "episode", "summary", "link_repo", "link_live"
        ]
        
        for field in target_fields:
            # Regex captures "key: value"
            match = re.search(rf'^{field}:\s*(.+)$', yaml_text, re.MULTILINE)
            if match: 
                # Clean up quotes and template tags
                meta[field] = match.group(1).strip().strip('"').strip("'").replace("{{", "").replace("}}", "")
        
        # Date Fallback
        if "date" not in meta and "created" in meta:
            meta["date"] = meta["created"]

        # FIX 2: Universal Tag Extraction
        tags = []
        
        # A. Inline Format
        inline_match = re.search(r'^tags:\s*\[(.*?)\]', yaml_text, re.MULTILINE)
        if inline_match:
            tags = [t.strip() for t in inline_match.group(1).split(',')]
        
        # B. List Format
        if not tags:
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

def generate_garden_card_html(meta, filename, note_id, body_content, full_search_text):
    note_type = meta.get("type", "unknown").lower()
    
    # 1. TYPE IDENTIFICATION LOGIC
    if (note_type == "unknown" or not note_type) and meta.get("tags"):
        for tag in meta["tags"]:
            if tag.startswith("type/"):
                note_type = tag.split("/")[1]; break
    
    if re.match(r'\d{4}-\d{2}-\d{2}', filename): note_type = "daily-bridge"
    meta["type"] = note_type
    title = filename.replace(".md", "").replace("_", " ")

    # 2. VISUAL CLEANING (The Blurb)
    # Strip HTML tags (like our new buttons) and Markdown for the preview text
    clean_body = re.sub(r'<[^>]+>', '', body_content) 
    clean_body = re.sub(r'[*#_`\[\]]', '', clean_body)
    clean_body = " ".join(clean_body.split())
    blurb = clean_body[:280].strip() + "..."

    # 3. STYLE & DATA MAPPING
    # Default State
    color = "border-gray-800"
    icon = "📄"
    label = "NODE"
    footer_content = f'<div class="text-xs text-gray-600 font-mono">#{note_type}</div>'

    # Specific States
    if "daily" in note_type or "log" in note_type:
        color = "border-aurelia-tertiary"
        icon = "📅"
        label = "LOG"
        cues = extract_atomic_cues(body_content)
        footer_content = '<div class="flex gap-2 flex-wrap">' + "".join([f'<span class="text-[10px] font-mono px-1.5 py-0.5 bg-aurelia-tertiary/10 text-aurelia-tertiary rounded border border-aurelia-tertiary/20">{c}</span>' for c in cues]) + '</div>'

    elif "concept" in note_type:
        color = "border-aurelia-primary"
        icon = "⚛️"
        label = "CONCEPT"
        defin = extract_definition(body_content)
        blurb = defin if defin else blurb
        footer_content = '<div class="text-[10px] text-aurelia-primary font-mono opacity-80">:: SYSTEM_CONCEPT</div>'

    elif "source" in note_type:
        color = "border-yellow-500"
        icon = "📖"
        label = "SOURCE"
        author = extract_source_author(body_content)
        footer_content = f'<div class="flex justify-between items-center w-full"><span class="text-[10px] font-mono text-gray-500">AUTH: {author.upper()}</span><span class="text-[10px] text-yellow-500 border border-yellow-500/30 px-1 rounded">REF</span></div>'

    elif "project" in note_type:
        color = "border-purple-500"
        icon = "🚀"
        label = "PROJECT"

    # 4. THE MASTER COMPONENT (Unified HTML Structure)
    # Key Fix: 'h-full', 'flex-col', and 'flex-grow' on the paragraph ensure alignment.
    html_card = f"""
    <article 
        onclick="openNote('{note_id}')" 
        data-type="{note_type}"
        data-search="{title} {note_type} {full_search_text}"
        class="searchable-item glass p-5 rounded-sm border {color} border-opacity-40 hover:border-opacity-100 cursor-pointer flex flex-col gap-4 transition-all duration-300 hover:translate-y-[-4px] hover:shadow-2xl hover:z-10 group h-full min-h-[240px]">
        
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-1.5">
                    <span class="w-1.5 h-1.5 {color.replace('border-', 'bg-')} rounded-full"></span>
                    <span class="text-[10px] font-mono {color.replace('border-', 'text-')} uppercase tracking-widest">{label}</span>
                </div>
                <h3 class="text-lg font-bold text-gray-200 font-mono group-hover:text-aurelia-text transition-colors leading-tight">{title}</h3>
            </div>
            <div class="text-2xl opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-transform">{icon}</div>
        </div>

        <div class="w-full h-px bg-gray-800/50"></div>

        <p class="text-sm text-gray-400 leading-relaxed font-sans line-clamp-4 flex-grow">
            {blurb}
        </p>
        
        <div class="mt-auto pt-3 border-t border-gray-800/50 flex items-center">
            {footer_content}
        </div>
    </article>
    """
    return html_card

    # UPDATE THE HTML CARD BLOCK
    html_card = f"""
    <article 
        onclick="openNote('{note_id}')" 
        data-type="{note_type}"
        data-search="{title} {note_type} {full_search_text}" 
        class="searchable-item glass p-6 rounded-sm border-2 {color} border-opacity-60 hover:border-opacity-100 cursor-pointer flex flex-col gap-4 transition-all duration-300 hover:scale-[1.02] hover:-translate-y-1 hover:shadow-2xl hover:z-10 group h-full min-h-[220px]">
        
        <div class="flex justify-between items-start">
            <div>
                <div class="flex items-center gap-2 mb-1">
                    <span class="w-1.5 h-1.5 {color.replace('border-', 'bg-')} rounded-full"></span>
                    <span class="text-[10px] font-mono {color.replace('border-', 'text-')} uppercase tracking-widest">{label}</span>
                </div>
                <h3 class="text-xl font-bold text-gray-200 font-mono group-hover:text-aurelia-text transition-colors leading-tight">{title}</h3>
            </div>
            <div class="text-2xl opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-all">{icon}</div>
        </div>

        <div class="w-full h-px bg-gray-800/30"></div>

        <p class="text-sm text-gray-400 leading-relaxed font-sans line-clamp-4 flex-grow">
            {blurb}
        </p>
        
        {footer_html}
    </article>
    """
    return html_card

def generate_project_card(meta, sections, title, note_id):
    # 1. Status Logic
    is_active = meta.get("status") == "active"
    status_color = "bg-aurelia-accent shadow-[0_0_10px_#39ff14]" if is_active else "bg-gray-500"
    status_text = "ONLINE" if is_active else "ARCHIVED"
    
    role = meta.get('role', 'Architect')
    body = sections.get('brief', '')
    
    # 2. Extract Data
    mission = extract_mission_brief(body)
    logic = extract_core_logic(body)
    impacts = extract_impact_metrics(body)
    live_link = meta.get('link_live')
    
    # 3. Build Action Buttons
    action_buttons = '<div class="flex items-center gap-3 mt-auto pt-4 border-t border-gray-800">'
    if live_link:
        action_buttons += f'''
        <a href="{live_link}" target="_blank" onclick="event.stopPropagation()" 
           class="flex items-center gap-2 px-3 py-2 text-[10px] font-mono font-bold text-black bg-aurelia-secondary hover:bg-white transition-colors rounded-sm uppercase tracking-wider">
           🚀 LAUNCH_SYSTEM
        </a>
        '''
    action_buttons += f'''
    <button onclick="openNote('{note_id}'); event.stopPropagation()" 
            class="ml-auto flex items-center gap-2 px-3 py-2 text-[10px] font-mono text-gray-400 border border-gray-700 hover:border-aurelia-text hover:text-aurelia-text transition-all rounded-sm uppercase tracking-wider">
        <span>ACCESS_DATA</span>
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
    </button>
    </div>
    '''

    # 4. Search Meta
    search_text = f"{title} project {mission} {logic}".lower().replace('\n', ' ').replace('"', "'")

    # 5. GENERATE HTML (The "Terminal Block" Design)
    html = f"""
    <div class="searchable-item group relative flex flex-col gap-5 p-6 min-h-[480px]
                bg-[#0a0a0b]/80 backdrop-blur-md border border-gray-800 
                hover:border-aurelia-secondary/50 hover:shadow-[0_0_30px_rgba(138,43,226,0.15)] 
                transition-all duration-300 rounded-sm cursor-pointer overflow-hidden"
         data-type="project" 
         data-search="{search_text}"
         onclick="openNote('{note_id}')">
        
        <div class="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-aurelia-secondary/20 group-hover:border-aurelia-secondary transition-colors"></div>
        <div class="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-aurelia-secondary/20 group-hover:border-aurelia-secondary transition-colors"></div>

        <div class="flex justify-between items-start z-10">
            <div>
                <div class="flex items-center gap-2 mb-3">
                    <span class="px-2 py-0.5 rounded text-[9px] font-bold font-mono bg-aurelia-secondary/10 text-aurelia-secondary border border-aurelia-secondary/20 uppercase">
                        {role}
                    </span>
                    <div class="flex items-center gap-1.5 px-2 py-0.5 rounded border border-gray-800 bg-black/50">
                        <span class="w-1.5 h-1.5 {status_color} rounded-full"></span>
                        <span class="text-[9px] font-mono text-gray-400 uppercase tracking-wider">{status_text}</span>
                    </div>
                </div>
                <h3 class="text-2xl font-bold text-gray-100 font-sans tracking-tight leading-none group-hover:text-aurelia-secondary transition-colors">
                    {title.replace('_', ' ').replace('.md', '')}
                </h3>
            </div>
        </div>

        <div class="flex flex-col gap-2 z-10">
            <span class="text-[10px] font-mono text-gray-500 uppercase tracking-widest">MISSION_PARAMETER</span>
            <p class="text-sm text-gray-300 font-sans leading-relaxed line-clamp-3">
                {mission}
            </p>
        </div>

        <div class="flex flex-col gap-2 flex-grow z-10">
            <span class="text-[10px] font-mono text-gray-500 uppercase tracking-widest">SYSTEM_LOGIC</span>
            <div class="bg-black/60 border-l-2 border-aurelia-secondary p-3 rounded-r-sm h-full">
                <p class="text-xs text-aurelia-muted font-mono leading-relaxed italic opacity-90">
                    <span class="text-aurelia-secondary opacity-50">>></span> {logic}
                </p>
            </div>
        </div>

        <div class="flex flex-wrap gap-2 z-10">
            { "".join([f'<span class="text-[10px] font-mono text-gray-400 bg-gray-900 border border-gray-800 px-2 py-1 rounded-sm">{m}</span>' for m in impacts]) }
        </div>

        {action_buttons}
    </div>
    """
    return html

# --- NEW HELPER: DATE SERIALIZER FOR TRANSMISSIONS ---
from datetime import date, datetime
def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

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

    # 1. LOAD DATA CONTAINERS
    garden_cards = []
    portfolio_cards = []
    protocol_cards = []
    transmissions_data = [] # <--- NEW: Transmissions Container

    # 2. SCAN VAULT (The Main Router)
    for root, dirs, files in os.walk(VAULT_PATH):
        for filename in sorted(files):
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                meta = parse_frontmatter(content)
                if not meta.get("publish"): continue 

                body = parse_body(content)
                # Normalize type to ensure matching works
                note_type = meta.get("type", "unknown").lower().strip()
                tags = meta.get("tags", []) 
                
                # --- ROUTING SWITCH (The "Traffic Cop") ---
                
                # ROUTE A: PROJECTS -> Portfolio
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
                        "tags": tags,
                        "desc": extract_mission_brief(body)
                    })

                # ROUTE B: PROTOCOLS -> Ignore (Handled in Step 3)
                elif "protocol" in note_type:
                    continue 

                # ROUTE C: TRANSMISSIONS -> Ignore (Handled in Step 4)
                elif "transmission" in note_type:
                    continue # Skips adding to Garden, handled by separate loader below

                # ROUTE D: GARDEN NOTES -> Garden
                else:
                    note_id = make_id(filename)
                    
                    # ⚡ DEEP SEARCH GENERATION ⚡
                    # 1. Get raw body
                    raw_search = body
                    # 2. Strip Markdown & HTML tags (so we don't search "<button>" or "##")
                    raw_search = re.sub(r'[*#_`\[\]]', '', raw_search)
                    raw_search = re.sub(r'<[^>]+>', '', raw_search)
                    # 3. Flatten (remove newlines/quotes) for the data attribute
                    full_search_text = raw_search.replace('\n', ' ').replace('"', "").replace("'", "").lower()
                    
                    # Process Links for the VISIBLE body
                    processed_body = process_wikilinks(body)
                    
                    # Pass the 'full_search_text' as the new 5th argument
                    card_html = generate_garden_card_html(meta, filename, note_id, processed_body, full_search_text)
                    
                    garden_cards.append({
                        "html": card_html, 
                        "body": processed_body, 
                        "id": note_id,
                        "title": filename.replace(".md", "").replace("_", " "),
                        "link": f"garden.html#{note_id}", 
                        "type": meta.get("type", "NOTE").upper(), 
                        "tags": tags,
                        "desc": full_search_text # Use full text for tree search too
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
                    "link": f"protocol.html", 
                    "type": "PROTOCOL"
                })

    # 4. SCAN TRANSMISSIONS (UPDATED FOR 40_TRANSMISSIONS)
    # Checks config first
    if user_config.get('modules', {}).get('transmissions', {}).get('enabled', False):
        # 1. Target the new folder structure
        transmissions_dir = os.path.join(VAULT_PATH, "40_TRANSMISSIONS")

        if os.path.exists(transmissions_dir):
            print(f"   + Processing Transmissions from: {transmissions_dir}")
            for filename in os.listdir(transmissions_dir):
                if filename.endswith(".md"):
                    filepath = os.path.join(transmissions_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        t_content = f.read()
                    
                    t_meta = parse_frontmatter(t_content)
                    t_body = parse_body(t_content)
                    
                    # Metadata Safety Checks
                    if 'series' not in t_meta: t_meta['series'] = 'Uncategorized'
                    if 'title' not in t_meta: t_meta['title'] = filename.replace(".md", "")
                    
                    # Ensure episode is integer for safe sorting
                    try:
                        t_meta['episode'] = int(t_meta.get('episode', 999))
                    except:
                        t_meta['episode'] = 999
                    
                    # Markdown Parsing
                    try:
                        import markdown
                        # Enable extensions if you need tables or code fencing
                        t_meta['content'] = markdown.markdown(t_body, extensions=['fenced_code', 'tables']) 
                    except ImportError:
                        t_meta['content'] = t_body 
                        
                    t_meta['tags'] = t_meta.get("tags", [])
                    
                    transmissions_data.append(t_meta)
        else:
            print(f"   ⚠️ WARNING: Transmissions enabled but '40_TRANSMISSIONS' folder not found in {VAULT_PATH}")

    # ⚡ SORTING ENGINE ⚡
    
    # 1. Garden Cards (A-Z)
    garden_cards.sort(key=lambda x: x['title'].lower())
    
    # 2. Portfolio Cards (A-Z)
    portfolio_cards.sort(key=lambda x: x['title'].lower())

    # 3. Protocol Cards (A-Z)
    protocol_cards.sort(key=lambda x: x['title'].lower())

    # 4. Transmissions (Series, then Episode)
    transmissions_data.sort(key=lambda x: (x['series'], x['episode']))

    print(f"   + Indexing: {len(garden_cards)} Notes, {len(portfolio_cards)} Projects, {len(protocol_cards)} Protocols, {len(transmissions_data)} Transmissions")
    
    # 5. BUILD MASTER SEARCH INDEX
    master_index = []
    
    # Add System Pages
    master_index.append({"title": "Home // Mission Control", "url": "index.html", "type": "SYSTEM", "tags": ["home", "root"], "desc": "Main Hub"})
    master_index.append({"title": "The Garden // Input", "url": "garden.html", "type": "SYSTEM", "tags": ["notes", "writing"], "desc": "Digital Garden"})
    master_index.append({"title": "Protocols // Logic", "url": "protocol.html", "type": "SYSTEM", "tags": ["sop", "routines"], "desc": "Operating Procedures"})
    master_index.append({"title": "Portfolio // Output", "url": "portfolio.html", "type": "SYSTEM", "tags": ["work", "jobs"], "desc": "Case Studies"})
    
    if transmissions_data:
        master_index.append({"title": "Transmissions // Signal", "url": "transmissions.html", "type": "SYSTEM", "tags": ["podcast", "audio"], "desc": "Neural Uplink"})
    
    # Add Content
    for c in garden_cards: 
        master_index.append({"title": c['title'], "url": c['link'], "type": "GARDEN", "tags": c['tags'], "desc": c['desc']})
        
    for p in portfolio_cards: 
        master_index.append({"title": p['title'], "url": p['link'], "type": "PROJECT", "tags": p['tags'], "desc": p['desc']})
        
    for prot in protocol_cards: 
        master_index.append({"title": prot['title'], "url": prot['link'], "type": "PROTOCOL", "tags": prot['tags'], "desc": prot['desc']})

    for trans in transmissions_data:
        master_index.append({
            "title": trans['title'], 
            "url": "transmissions.html", # All eps live on one SPA page
            "type": "TRANSMISSION", 
            "tags": trans['tags'], 
            "desc": f"Series: {trans['series']} // Ep {trans['episode']}"
        })

    # Serialize Index
    json_index = json.dumps(master_index)
    
    # Serialize Transmissions (Custom Date Handler)
    transmissions_json = json.dumps(transmissions_data, default=json_serial)

    # 6. RENDER PAGES
    pages = [
        ("pages/indextemplate.html", "index.html", {}),
        ("pages/gardentemplate.html", "garden.html", {"cards": garden_cards}),
        ("pages/portfoliotemplate.html", "portfolio.html", {"projects": portfolio_cards}),
        ("pages/servicestemplate.html", "services.html", {}),
        ("pages/protocoltemplate.html", "protocol.html", {"protocols": protocol_cards}), 
        ("404.html", "404.html", {}),
    ]

    # CHECK CONFIG, NOT DATA
    # We use the config flag to decide whether to build the page
    if user_config.get('modules', {}).get('transmissions', {}).get('enabled', False):
         pages.append(("pages/transmissionstemplate.html", "transmissions.html", {"transmissions_json": transmissions_json}))

    # RENDER LOOP
    for template_name, output_name, context in pages:
        try:
            # INJECT GLOBAL DATA
            context["theme"] = CURRENT_THEME 
            context["search_index"] = json_index
            context["config"] = user_config 
            
            template = env.get_template(template_name)
            rendered_html = template.render(active_page=output_name.replace(".html", ""), **context)
            
            with open(os.path.join(OUTPUT_DIR, output_name), "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"   ✅ Deployed: {output_name}")
        except Exception as e:
            print(f"   ❌ Failed: {output_name} -> {e}")

    print("\n✅ SYSTEM SYNC COMPLETE.")

if __name__ == "__main__":
    build_all()