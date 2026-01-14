import os
import json

# --- CONFIGURATION ---
TARGET_DIR = "Aurelia_Prof_AW"
PROF_NAME = "Prof. A.W."
PROF_ROLE = "Department Chair & Research Lead"

# --- 1. DEFINE FILE CONTENTS ---

# The Engine
BUILD_PY_CONTENT = r'''import os
import re
import json
from jinja2 import Environment, FileSystemLoader

# --- ⚡ RESTORED ENGINE BLOCK ⚡ ---

def make_id(text):
    """Turns 'My Cool Note.md' into 'note-my-cool-note'"""
    text = text.replace(".md", "").lower()
    slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return f"note-{slug}"

def process_wikilinks(text):
    """Converts [[Link]] to clickable Modal Buttons"""
    def replace_link(match):
        content = match.group(1)
        if '|' in content:
            target, label = content.split('|', 1)
        else:
            target, label = content, content
        target_id = make_id(target)
        return f'<button onclick="openNote(\'{target_id}\')" class="text-aurelia-primary hover:underline font-bold bg-transparent border-none cursor-pointer p-0 inline">{label}</button>'
    return re.sub(r'\[\[(.*?)\]\]', replace_link, text)

# --- CONFIGURATION ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system/templates")
PROTOCOL_PATH = os.path.join(ROOT_DIR, "vault", "20_PROTOCOL")
OUTPUT_DIR = ROOT_DIR

# --- THEME ENGINE ---
CURRENT_THEME = {
    "name": "CYBER_PRIME",
    "colors": {
        "bg_main": "'#0a0a0b'", "bg_layer_1": "'#121214'", "bg_layer_2": "'#18181b'",
        "text_main": "'#ffffff'", "text_muted": "'#9ca3af'", "text_inverted": "'#000000'",
        "border_main": "'#27272a'", "border_focus": "'#00f2ff'",
        "primary": "'#00f2ff'", "secondary": "'#8a2be2'", "tertiary": "'#ff8c00'", "accent": "'#39ff14'",
    },
    "font_mono": "'JetBrains Mono', 'monospace'",
    "rounded": "'2px'",
    "glass_opacity": "'0.6'"
}

print(f"🔧 CONFIG: Root={ROOT_DIR}")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- PARSERS ---
def parse_frontmatter(content):
    meta = {"publish": False, "tags": [], "type": "unknown"}
    content = content.lstrip()
    if not content.startswith("---"): return meta
    try:
        parts = content.split("---", 2)
        if len(parts) < 3: return meta
        yaml_text = parts[1]
        if re.search(r'^publish:\s*true', yaml_text, re.MULTILINE | re.IGNORECASE): meta["publish"] = True
        target_fields = ["type", "status", "role", "cover_image", "date", "icon", "created", "audio_file", "visual_loop", "series", "episode", "summary", "link_repo", "link_live"]
        for field in target_fields:
            match = re.search(rf'^{field}:\s*(.+)$', yaml_text, re.MULTILINE)
            if match: meta[field] = match.group(1).strip().strip('"').strip("'")
        
        tags = []
        inline_match = re.search(r'^tags:\s*\[(.*?)\]', yaml_text, re.MULTILINE)
        if inline_match: tags = [t.strip() for t in inline_match.group(1).split(',')]
        if not tags:
            list_matches = re.findall(r'^\s*-\s*(.+)$', yaml_text, re.MULTILINE)
            if list_matches: tags = [t.strip() for t in list_matches]
        meta["tags"] = tags
    except Exception as e: print(f"YAML Error: {e}")
    return meta

def parse_body(content):
    parts = content.split("---", 2)
    return parts[2].strip() if len(parts) > 2 else content

# --- EXTRACTORS ---
def extract_protocol_sequence(text):
    items = []
    parts = re.split(r'##\s*.*(?:Sequence|Checklist|Steps).*', text, flags=re.IGNORECASE)
    if len(parts) > 1:
        clean_section = re.split(r'\n##|\n---', parts[1])[0]
        matches = re.findall(r'-\s*\[[ x]\]\s*(.*)', clean_section)
        if not matches: matches = re.findall(r'^\s*[-*]\s+(.*)', clean_section, re.MULTILINE)
        items = [m.strip() for m in matches if m.strip()]
    return items[:6]

def extract_protocol_logic(text):
    logic_match = re.search(r'##\s*.*System Logic.*\n+>\s*(.*)', text, re.MULTILINE)
    if not logic_match: logic_match = re.search(r'>\s*(.*)', text)
    return logic_match.group(1).strip() if logic_match else "Standard operating procedure."

def extract_mission_brief(body):
    if "# 🚨 Mission Brief" in body:
        try:
            part = body.split("# 🚨 Mission Brief")[1]
            if "\n# " in part: part = part.split("\n# ")[0]
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', " ".join(part.split('\n'))).strip()
            return clean[:240] + "..." if len(clean) > 240 else clean
        except: pass
    return ""

def extract_core_logic(body):
    if "# 🛠️ Architecture" in body:
        try:
            part = body.split("# 🛠️ Architecture")[1]
            for line in part.split('\n'):
                if "**Core Logic:**" in line: return line.replace("**Core Logic:**", "").strip().replace("**", "")
        except: pass
    return ""

def extract_impact_metrics(body):
    if "# ⚡ Operational Impact" in body:
        try:
            part = body.split("# ⚡ Operational Impact")[1]
            if "\n# " in part: part = part.split("\n# ")[0]
            return [m.strip() for m in re.findall(r'[\-\*]\s*\*\*(.*?)\*\*[:\s]', part)][:4]
        except: pass
    return []

# --- CARD GENERATORS ---
def generate_project_card(meta, sections, title, note_id):
    is_active = meta.get("status") == "active"
    status_color = "bg-aurelia-accent shadow-[0_0_10px_#39ff14]" if is_active else "bg-gray-500"
    role = meta.get('role', 'Architect')
    body = sections.get('brief', '')
    mission = extract_mission_brief(body)
    logic = extract_core_logic(body)
    impacts = extract_impact_metrics(body)
    tech_stack = meta.get("tech_stack", [])
    if isinstance(tech_stack, str): tech_stack = [tech_stack]
    
    html = f"""
    <div class="searchable-item group relative flex flex-col gap-5 p-6 min-h-[520px] bg-black border-2 border-gray-800 hover:border-aurelia-secondary hover:shadow-[0_0_30px_rgba(138,43,226,0.2)] transition-all duration-300 rounded-sm cursor-pointer overflow-hidden" data-type="project" data-search="{title} {mission}" onclick="openNote('{note_id}')">
        <div class="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-gray-800 group-hover:border-aurelia-secondary transition-colors"></div>
        <div class="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-gray-800 group-hover:border-aurelia-secondary transition-colors"></div>
        <div class="flex justify-between items-start z-10">
            <div class="w-full">
                <div class="flex items-center justify-between mb-3 w-full">
                    <span class="px-2 py-1 rounded-sm text-[10px] font-bold font-mono bg-aurelia-secondary text-black border border-aurelia-secondary uppercase">{role}</span>
                    <div class="flex items-center gap-1.5 px-2 py-1 rounded border border-gray-700 bg-gray-900"><span class="w-2 h-2 {status_color} rounded-full"></span><span class="text-[10px] font-mono text-white font-bold uppercase tracking-wider">{'ONLINE' if is_active else 'ARCHIVED'}</span></div>
                </div>
                <h3 class="text-3xl font-black text-white font-sans tracking-tight leading-none group-hover:text-aurelia-secondary transition-colors uppercase">{title.replace('_', ' ')}</h3>
            </div>
        </div>
        <div class="flex flex-col gap-2 z-10"><span class="text-[10px] font-bold font-mono text-aurelia-secondary uppercase tracking-widest border-b border-gray-800 pb-1">MISSION_PARAMETER</span><p class="text-sm text-white font-sans leading-relaxed line-clamp-3 font-medium">"{mission}"</p></div>
        <div class="flex flex-col gap-2 flex-grow z-10"><span class="text-[10px] font-bold font-mono text-aurelia-secondary uppercase tracking-widest border-b border-gray-800 pb-1">SYSTEM_LOGIC</span><div class="bg-gray-900 border-l-4 border-aurelia-secondary p-3 rounded-r-sm h-full"><p class="text-xs text-gray-300 font-mono leading-relaxed italic"><span class="text-aurelia-secondary font-bold">>></span> {logic}</p></div></div>
        <div class="z-10 space-y-3"><div class="flex flex-wrap gap-1.5">{''.join([f'<span class="text-[9px] font-mono text-black bg-white px-1.5 py-0.5 rounded-sm font-bold uppercase">{t}</span>' for t in tech_stack[:4]])}</div><div class="flex flex-wrap gap-2">{''.join([f'<span class="text-[10px] font-mono text-gray-300 border border-gray-600 px-2 py-1 rounded-sm">⚡ {m}</span>' for m in impacts])}</div></div>
    </div>
    """
    return html

def generate_protocol_card(meta, body, title, note_id, p_id_override=None):
    prot_id = p_id_override if p_id_override else meta.get("id", "SYS_CMD").upper()
    sequence = extract_protocol_sequence(body)
    logic = extract_protocol_logic(body)
    is_auto = "automated" in meta.get("tags", [])
    
    html = f"""
    <div class="searchable-item group relative flex flex-col gap-0 min-h-[420px] bg-[#09090b] border border-gray-700 hover:border-aurelia-accent hover:shadow-[0_0_20px_rgba(57,255,20,0.15)] transition-all duration-200 rounded-sm cursor-pointer overflow-hidden font-mono" data-type="protocol" data-search="{title} {prot_id}" onclick="openNote('{prot_id}')">
        <div class="bg-[#18181b] border-b border-gray-700 p-4 flex justify-between items-center group-hover:bg-[#27272a] transition-colors">
            <div class="flex items-center gap-3"><div class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-aurelia-accent opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-aurelia-accent"></span></div><span class="text-xs font-bold text-white tracking-widest">{prot_id}</span></div>
            <span class="text-[10px] font-bold text-gray-400 uppercase bg-black/50 px-2 py-1 rounded border border-gray-700">{'DAEMON' if is_auto else 'MANUAL'}</span>
        </div>
        <div class="p-6 border-b border-gray-800"><h3 class="text-xl font-black text-white uppercase tracking-tight group-hover:text-aurelia-accent transition-colors leading-none">{title.replace('_', ' ')}</h3></div>
        <div class="p-6 flex flex-col gap-4 flex-grow bg-[#09090b]">
            <span class="text-[10px] font-bold text-aurelia-accent uppercase tracking-widest border-b border-gray-800 pb-2 w-full">>> EXECUTION_STEPS:</span>
            <div class="flex flex-col gap-2.5 mt-1">{''.join([f'<div class="flex items-start gap-3 group/item"><span class="text-gray-500 font-bold text-xs shrink-0 select-none group-hover:text-aurelia-accent transition-colors">0{i+1}</span><span class="text-sm text-gray-200 font-medium group-hover/item:text-white transition-colors border-l-2 border-gray-800 pl-3 leading-snug">{item}</span></div>' for i, item in enumerate(sequence)])}</div>
        </div>
        <div class="p-5 bg-[#18181b] border-t border-gray-700 mt-auto"><div class="flex items-start gap-3"><span class="text-aurelia-accent font-bold text-sm">i</span><p class="text-xs text-gray-300 font-sans leading-relaxed">{logic}</p></div></div>
        <div class="absolute inset-x-0 bottom-0 h-1 bg-aurelia-accent opacity-0 group-hover:opacity-100 transition-opacity duration-300 shadow-[0_-2px_10px_rgba(57,255,20,0.5)]"></div>
    </div>
    """
    return html

def generate_garden_card_html(meta, filename, note_id, body, search):
    # Simplified placeholder for brevity - Use your existing detailed logic here if needed
    clean_body = re.sub(r'<[^>]+>', '', body)[:200]
    return f'<article onclick="openNote(\'{note_id}\')" class="searchable-item glass p-5 border border-gray-800 cursor-pointer" data-type="NOTE" data-search="{filename}"><h3 class="text-lg font-bold text-white">{filename.replace(".md", "")}</h3><p class="text-sm text-gray-400">{clean_body}...</p></article>'

def json_serial(obj):
    from datetime import date, datetime
    if isinstance(obj, (datetime, date)): return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def build_all():
    print("\n🧬 AURELIA SYSTEM: INITIALIZING CLONE...")
    
    with open(os.path.join(ROOT_DIR, "user_config.json"), "r") as f: user_config = json.load(f)
    
    garden, projects, protocols, transmissions = [], [], [], []
    
    # SCAN
    for root, dirs, files in os.walk(VAULT_PATH):
        for f in files:
            if not f.endswith(".md"): continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file: content = file.read()
            meta = parse_frontmatter(content)
            if not meta.get("publish"): continue
            body = parse_body(content)
            note_type = meta.get("type", "note").lower()
            title = f.replace(".md", "").replace("_", " ")
            note_id = make_id(f)
            
            if "project" in note_type:
                html = generate_project_card(meta, {"brief": body}, title, f"project-{len(projects)}")
                projects.append({"html": html, "body": body, "id": f"project-{len(projects)}", "title": title})
            elif "protocol" in note_type:
                p_id = meta.get("id", "PROT_" + f[:3].upper())
                html = generate_protocol_card(meta, body, title, note_id, p_id)
                protocols.append({"html": html, "body": body, "id": p_id, "title": title, "tags": meta.get("tags")})
            elif "transmission" in note_type:
                 transmissions.append(meta) # Simplified
            else:
                 html = generate_garden_card_html(meta, f, note_id, body, "")
                 garden.append({"html": html, "body": body, "id": note_id, "title": title})

    # RENDER
    pages = [
        ("pages/indextemplate.html", "index.html", {}),
        ("pages/gardentemplate.html", "garden.html", {"cards": garden}),
        ("pages/portfoliotemplate.html", "portfolio.html", {"projects": projects}),
        ("pages/servicestemplate.html", "services.html", {}),
        ("pages/protocoltemplate.html", "protocol.html", {"protocols": protocols}),
        ("404.html", "404.html", {})
    ]
    
    if user_config.get('modules', {}).get('transmissions', {}).get('enabled'):
        pages.append(("pages/transmissionstemplate.html", "transmissions.html", {"transmissions_json": json.dumps(transmissions, default=json_serial)}))

    for t_name, out_name, ctx in pages:
        ctx.update({"theme": CURRENT_THEME, "config": user_config, "search_index": "[]"})
        try:
            html = env.get_template(t_name).render(active_page=out_name.replace(".html",""), **ctx)
            with open(os.path.join(OUTPUT_DIR, out_name), "w", encoding="utf-8") as f: f.write(html)
            print(f"   ✅ Deployed: {out_name}")
        except Exception as e: print(f"   ❌ Failed: {out_name} -> {e}")

if __name__ == "__main__":
    build_all()
'''

# The Identity
CONFIG_CONTENT = json.dumps({
    "system_name": "AURELIA // ACADEMIC",
    "system_version": "v1.0.0",
    "status_message": "System_Online",
    "author": {
        "name": PROF_NAME,
        "short_name": "A.W.",
        "role": PROF_ROLE,
        "email": "contact@university.edu",
        "location": "Campus Research Wing",
        "bio_short": "Bridging Academic Rigor with Digital Systems.",
        "bio_long": "I specialize in [Field of Study]. This digital garden serves as a repository for my research, methodologies, and active projects."
    },
    "links": { "github": "#", "linkedin": "#", "twitter": "#" },
    "tech_stack": [
        { "name": "Zotero", "type": "RESEARCH // ARCHIVE", "desc": "Citation Management.", "icon": "📚" },
        { "name": "Obsidian", "type": "SOFTWARE // VAULT", "desc": "Knowledge Base.", "icon": "💎" },
        { "name": "Python", "type": "BACKEND // LOGIC", "desc": "Data Analysis.", "icon": "🐍" }
    ],
    "modules": {
        "garden": { "enabled": True },
        "projects": { "enabled": True },
        "protocols": { "enabled": True },
        "services": { "enabled": False },
        "transmissions": { "enabled": False }
    }
}, indent=4)

# --- 2. SETUP FUNCTION ---
def setup_structure():
    print(f"🚀 INITIATING CLONE SEQUENCE FOR: {PROF_NAME}")
    
    # Create Directories
    dirs = [
        TARGET_DIR,
        f"{TARGET_DIR}/vault",
        f"{TARGET_DIR}/vault/00_LOBBY",
        f"{TARGET_DIR}/vault/10_GARDEN",
        f"{TARGET_DIR}/vault/20_PROTOCOL",
        f"{TARGET_DIR}/vault/30_PROJECTS",
        f"{TARGET_DIR}/vault/40_TRANSMISSIONS",
        f"{TARGET_DIR}/system",
        f"{TARGET_DIR}/system/templates",
        f"{TARGET_DIR}/system/templates/pages",
        f"{TARGET_DIR}/assets",
        f"{TARGET_DIR}/assets/css",
        f"{TARGET_DIR}/assets/images",
        f"{TARGET_DIR}/assets/js"
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"   + Created: {d}")

    # Write Config & Build Script (These were already fine, but included for completeness)
    with open(f"{TARGET_DIR}/build.py", "w", encoding="utf-8") as f: f.write(BUILD_PY_CONTENT)
    with open(f"{TARGET_DIR}/user_config.json", "w", encoding="utf-8") as f: f.write(CONFIG_CONTENT)
    
    # --- THE FIX IS HERE: ADD encoding="utf-8" ---
    
    # Create Dummy Content to Verify Build
    with open(f"{TARGET_DIR}/vault/30_PROJECTS/Grant_Proposal_2026.md", "w", encoding="utf-8") as f:
        f.write("---\ntype: project\npublish: true\nstatus: active\nrole: Principal Investigator\n---\n# 🚨 Mission Brief\n**Objective:** Secure funding for next-gen research.\n# 🛠️ Architecture\n**Core Logic:** Leveraging interdisciplinary approaches.")
    
    with open(f"{TARGET_DIR}/vault/20_PROTOCOL/01_Literature_Review.md", "w", encoding="utf-8") as f:
        f.write("---\ntype: protocol\npublish: true\nid: PROT_LIT\n---\n# ⚙️ 01_LITERATURE_REVIEW\n## 📋 The Sequence\n- [ ] Search Zotero\n- [ ] Export Citation\n- [ ] Synthesize in Obsidian\n## 🧠 System Logic\n> Consistency is key to academic integrity.")

    print("\n✅ CLONE COMPLETE.")
    print(f"📂 Location: ./{TARGET_DIR}")
    print("👉 ACTION: Copy your 'base.html' and template HTML files into 'system/templates/pages/' manually (or add them to this script strings).")
    print("👉 ACTION: Copy your 'assets' folder contents to the new directory.")

if __name__ == "__main__":
    setup_structure()