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

def process_notebooklm_media(text):
    """
    Scans NotebookLM headers and converts file paths into interactive HTML media.
    Handles: Audio (mp3/wav), Video (mp4), and Images (png/jpg/webp).
    """
    
    # DEFINITION: How to handle each section
    # (Header Pattern, HTML Template, Asset Type)
    media_map = [
        {
            "header": r"#+\s*.*Audio Overview",
            "regex": r'(?:\[\[)?(assets/audio/[a-zA-Z0-9_\-\.\s]+\.(?:mp3|wav|m4a|ogg))(?:\]\])?',
            "type": "audio"
        },
        {
            "header": r"#+\s*.*Video Overview",
            "regex": r'(?:\[\[)?(assets/video/[a-zA-Z0-9_\-\.\s]+\.(?:mp4|webm))(?:\]\])?',
            "type": "video"
        },
        {
            # CATCH-ALL FOR IMAGES (Mind Map, Reports, Flashcards, etc.)
            "header": r"#+\s*.*(?:Mind Map|Reports|Flashcards|Quiz|Infographic|Slide Deck|Data Table)",
            "regex": r'(?:\[\[)?(assets/images/[a-zA-Z0-9_\-\.\s]+\.(?:png|jpg|jpeg|webp|gif))(?:\]\])?',
            "type": "image"
        }
    ]

    def render_audio(path):
        mime = "audio/mpeg"
        if path.endswith(".m4a"): mime = "audio/mp4"
        if path.endswith(".wav"): mime = "audio/wav"
        return f"""
<div class="my-6 p-4 border-l-2 border-indigo-500 bg-indigo-500/5 rounded-r-sm">
    <div class="flex items-center justify-between mb-3">
        <span class="text-[10px] font-bold font-mono text-indigo-400 uppercase tracking-widest">:: NEURAL_AUDIO_STREAM</span>
        <span class="text-[10px] font-mono text-indigo-500 animate-pulse">● LIVE_ASSET</span>
    </div>
    <audio controls class="w-full h-8 opacity-80 hover:opacity-100 transition-opacity" style="filter: hue-rotate(20deg) invert(0);">
        <source src="{path}" type="{mime}">
    </audio>
</div>"""

    def render_video(path):
        return f"""
<div class="my-6 border border-gray-800 rounded-sm overflow-hidden bg-black">
    <div class="p-2 border-b border-gray-800 bg-gray-900/50 flex items-center gap-2">
        <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
        <span class="text-[10px] font-mono text-gray-400 uppercase tracking-widest">VISUAL_FEED</span>
    </div>
    <video controls class="w-full max-h-[400px]">
        <source src="{path}" type="video/mp4">
    </video>
</div>"""

    def render_image(path):
        return f"""
<div class="my-6 group relative border border-gray-800 rounded-sm overflow-hidden bg-black/50 hover:border-indigo-500/50 transition-colors">
    <div class="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
        <a href="{path}" target="_blank" class="px-2 py-1 bg-black/80 text-[10px] font-mono text-white border border-gray-700 rounded hover:bg-indigo-600">ENLARGE</a>
    </div>
    <img src="{path}" class="w-full h-auto opacity-90 group-hover:opacity-100 transition-opacity" alt="NotebookLM Asset">
</div>"""

    # PROCESS LOOP
    # We iterate through the text multiple times, one for each media type
    # This allows us to handle multiple sections independently.
    
    processed_text = text
    
    for item in media_map:
        # 1. Find the specific Header + Content block
        pattern = f"({item['header']}\\s*\\n)([\\s\\S]*?)(?=\\n#|$)"
        
        def replacement_logic(match):
            header = match.group(1)
            content = match.group(2).strip()
            
            # 2. Check if content contains a valid file path for this type
            file_match = re.search(item['regex'], content, re.IGNORECASE)
            
            if file_match:
                path = file_match.group(1)
                html_widget = ""
                
                if item['type'] == "audio": html_widget = render_audio(path)
                elif item['type'] == "video": html_widget = render_video(path)
                elif item['type'] == "image": html_widget = render_image(path)
                
                # Replace the raw path with the widget, keep other text
                new_content = content.replace(file_match.group(0), html_widget)
                return header + new_content + "\n"
            
            return match.group(0) # No match, leave alone

        processed_text = re.sub(pattern, replacement_logic, processed_text, flags=re.IGNORECASE)

    return processed_text
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
def parse_frontmatter(content):
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}
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
            if match: meta[field] = match.group(1).strip().strip('"').strip("'").replace("{{", "").replace("}}", "")
        if "date" not in meta and "created" in meta: meta["date"] = meta["created"]
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
    if len(parts) < 3: return content
    return parts[2].strip()\
    



# --- 🧪 PROTOCOL EXTRACTORS (STEP-BY-STEP) --- 
def extract_protocol_sequence(text):
    """Extracts the checklist items from a Protocol"""
    items = []
    # Look for the sequence header (flexible matching)
    parts = re.split(r'##\s*.*(?:Sequence|Checklist|Steps).*', text, flags=re.IGNORECASE)
    
    if len(parts) > 1:
        section = parts[1]
        # Stop at next header
        clean_section = re.split(r'\n##|\n---', section)[0]
        
        # Regex to find: "- [ ] Task" OR "- Task" OR "1. Task"
        # We prioritize checklists
        matches = re.findall(r'-\s*\[[ x]\]\s*(.*)', clean_section)
        
        # Fallback: if no checkboxes, grab standard bullets
        if not matches:
            matches = re.findall(r'^\s*[-*]\s+(.*)', clean_section, re.MULTILINE)
            
        items = [m.strip() for m in matches if m.strip()]
        
    return items[:6] # Return top 6 steps
def extract_protocol_logic(text):
    """Extracts the logic blockquote"""
    # Look for System Logic header
    logic_match = re.search(r'##\s*.*System Logic.*\n+>\s*(.*)', text, re.MULTILINE)
    if not logic_match:
        # Fallback to just finding the blockquote if header is messy
        logic_match = re.search(r'>\s*(.*)', text)
    
    logic = logic_match.group(1).strip() if logic_match else "Logic not defined."
    return logic

# --- 🧠 GARDEN EXTRACTORS (DATA REFINERY) ---

def extract_log_data(text):
    """Parses Daily Log for GOAL, SOURCE, CONCEPTS, and SUMMARY"""
    # 1. GOAL
    goal_match = re.search(r'\*\*GOAL:\*\*\s*(.*)', text)
    goal = goal_match.group(1).strip() if goal_match else "System Check."
    # Strip buttons from goal just in case
    goal = re.sub(r'<[^>]+>', '', goal)

    # 2. SOURCE (The Fix)
    # Match the line, then strip ALL HTML tags (buttons) and brackets
    source_match = re.search(r'\*\*SOURCE:\*\*\s*(.*)', text)
    source = source_match.group(1).strip() if source_match else "Internal Log"
    
    # A. Strip HTML (Handle the <button> tags)
    source = re.sub(r'<[^>]+>', '', source)
    # B. Strip WikiLink Brackets (Handle raw [[ ]])
    source = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', source)

    # 3. CONCEPTS
    # Regex needs to handle both [[ ]] and <button> formats for robustness
    concepts = []
    # Look for bullet points with **Concept:**
    raw_concepts = re.findall(r'\*\s*\*\*Concept:\*\*\s*(.*)', text)
    for rc in raw_concepts:
        # Strip HTML and brackets to get just the text name
        clean = re.sub(r'<[^>]+>', '', rc)
        clean = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean)
        concepts.append(clean.strip())

    # 4. SUMMARY
    summary = ""
    if "**📝 BRIEF SUMMARY:**" in text:
        try:
            part = text.split("**📝 BRIEF SUMMARY:**")[1]
            bq_match = re.search(r'>\s*(.*)', part)
            if bq_match:
                summary = bq_match.group(1).strip()
                # CRITICAL: Strip tags before returning, otherwise truncation breaks layout
                summary = re.sub(r'<[^>]+>', '', summary)
                summary = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', summary)
        except: pass
    
    return goal, source, concepts[:3], summary

def extract_concept_data(text):
    """Parses Concept for Definition block and Related links"""
    
    # 1. DEFINITION
    # Look for the blockquote > specifically under a Definition header
    def_match = re.search(r'###\s*.*Definition.*\n+>\s*(.*)', text, re.MULTILINE)
    if not def_match:
        # Fallback: Just find the first blockquote in the file
        def_match = re.search(r'>\s*(.*)', text)
    
    definition = def_match.group(1).strip() if def_match else "Definition unavailable."
    
    # Sanitize: Remove HTML tags (buttons) and WikiLink brackets
    definition = re.sub(r'<[^>]+>', '', definition)
    definition = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', definition)

    # 2. RELATED LINKS
    # Find the line starting with **🔗 Related:**
    related_match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', text)
    clean_links = []
    
    if related_match:
        raw = related_match.group(1)
        # A. Strip HTML buttons produced by the wiki-linker
        clean_text = re.sub(r'<[^>]+>', '', raw)
        # B. Strip remaining brackets [[ ]]
        clean_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_text)
        
        # Split by comma and clean up whitespace
        items = clean_text.split(',')
        clean_links = [i.strip() for i in items if i.strip()]

    return definition, clean_links[:4]

def extract_source_data(text):
    """Parses Source for Author, Core Argument, and Derived Concepts"""
    
    # 1. AUTHOR
    # Matches: **Author:** <button...>Name</button>  OR  **Author:** Name
    auth_match = re.search(r'\*\*.*Author:\*\*\s*(.*)', text)
    author = "UNKNOWN"
    if auth_match:
        raw = auth_match.group(1)
        # Strip the button tags to get just the name
        clean_text = re.sub(r'<[^>]+>', '', raw) 
        # Clean brackets just in case
        clean_text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_text)
        author = clean_text.strip().upper()

    # 2. CORE ARGUMENT
    arg_match = re.search(r'###\s*.*(?:Core Argument|Thesis).*\n+>\s*(.*)', text, re.MULTILINE)
    if not arg_match:
        arg_match = re.search(r'>\s*(.*)', text)
    
    argument = arg_match.group(1).strip() if arg_match else "No core argument extracted."
    # Strip buttons so the argument is plain text
    argument = re.sub(r'<[^>]+>', '', argument)
    
    # 3. DERIVED CONCEPTS (The Fix)
    concepts = []
    # Split by the header
    parts = re.split(r'###\s*.*Concepts Extracted.*', text, flags=re.IGNORECASE)
    
    if len(parts) > 1:
        section_content = parts[1]
        # Stop at next header or horizontal rule
        clean_section = re.split(r'\n###|\n---', section_content)[0]
        
        # ⚡ CRITICAL FIX: Hunt for <button> tags, NOT [[ ]] brackets
        # Because process_wikilinks() runs before this function.
        # Regex matches: <button ...>Label</button>
        links = re.findall(r'<button[^>]*>(.*?)</button>', clean_section)
        
        # Safety Fallback: If no buttons found, check for raw brackets (just in case)
        if not links:
            links = re.findall(r'\[\[(.*?)\]\]', clean_section)
            links = [l.split('|')[1] if '|' in l else l for l in links]
            
        concepts = links

    return author, argument, concepts[:5]

def extract_author_data(text):
    """Parses Author Profile for Context, Key Works, and Core Concepts"""
    
    # 1. PROFILE CONTEXT
    context_match = re.search(r'###\s*.*Profile & Context.*\n+>\s*(.*)', text, re.MULTILINE)
    if not context_match:
        context_match = re.search(r'>\s*(.*)', text)
    
    context = context_match.group(1).strip() if context_match else "Profile data unavailable."
    context = re.sub(r'<[^>]+>', '', context)
    context = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', context)

    # 2. KEY WORKS
    works = []
    work_parts = re.split(r'###\s*.*Key Works.*', text, flags=re.IGNORECASE)
    if len(work_parts) > 1:
        section = work_parts[1]
        clean_section = re.split(r'\n###|\n---', section)[0]
        links = re.findall(r'<button[^>]*>(.*?)</button>', clean_section)
        if not links: links = re.findall(r'\[\[(.*?)\]\]', clean_section)
        works = [l.split('|')[1] if '|' in l else l for l in links]

    # 3. CORE CONCEPTS
    concepts = []
    concept_parts = re.split(r'###\s*.*Core Concepts.*', text, flags=re.IGNORECASE)
    if len(concept_parts) > 1:
        section = concept_parts[1]
        clean_section = re.split(r'\n###|\n---', section)[0]
        links = re.findall(r'<button[^>]*>(.*?)</button>', clean_section)
        if not links: links = re.findall(r'\[\[(.*?)\]\]', clean_section)
        concepts = [l.split('|')[1] if '|' in l else l for l in links]

    return context, works[:4], concepts[:4]

def extract_discipline_data(text):
    """Parses Discipline for Scope, Core Concepts, and Foundational Texts"""
    
    # 1. THE SCOPE (Definition)
    # Match header like "### ｧDefinition" then the blockquote
    def_match = re.search(r'###\s*.*Definition.*\n+>\s*(.*)', text, re.MULTILINE)
    if not def_match:
        def_match = re.search(r'>\s*(.*)', text)
    
    scope = def_match.group(1).strip() if def_match else "Scope defined in parent node."
    scope = re.sub(r'<[^>]+>', '', scope)
    scope = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', scope)

    # 2. CORE PILLARS (Concepts)
    pillars = []
    # Split by "Core Concepts" header
    concept_parts = re.split(r'###\s*.*Core Concepts.*', text, flags=re.IGNORECASE)
    if len(concept_parts) > 1:
        section = concept_parts[1]
        clean_section = re.split(r'\n###|\n---', section)[0]
        # Find links
        links = re.findall(r'<button[^>]*>(.*?)</button>', clean_section)
        if not links: links = re.findall(r'\[\[(.*?)\]\]', clean_section)
        pillars = [l.split('|')[1] if '|' in l else l for l in links]

    # 3. THE CANON (Foundational Texts)
    canon = []
    text_parts = re.split(r'###\s*.*Foundational Texts.*', text, flags=re.IGNORECASE)
    if len(text_parts) > 1:
        section = text_parts[1]
        clean_section = re.split(r'\n###|\n---', section)[0]
        links = re.findall(r'<button[^>]*>(.*?)</button>', clean_section)
        if not links: links = re.findall(r'\[\[(.*?)\]\]', clean_section)
        canon = [l.split('|')[1] if '|' in l else l for l in links]

    return scope, pillars[:4], canon[:3]

def extract_notebooklm_data(text):
    """Parses NotebookLM Note for Overview and Active Studio Features"""
    data = {}
    
    # 1. GET OVERVIEW
    # Grab text between "Lit Review Overview" and the next header
    overview_match = re.search(r'#\s*.*Lit Review Overview.*\n([\s\S]*?)(?=\n#|$)', text)
    raw_overview = overview_match.group(1).strip() if overview_match else "Synthesis data pending."
    
    # Clean up formatting for the card face
    clean_overview = re.sub(r'<[^>]+>', '', raw_overview)
    clean_overview = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_overview)
    clean_overview = clean_overview.replace('>', '').strip()
    
    # 2. CHECK ACTIVE FEATURES
    # We define the regex for each header. If content exists below it, the feature is "Active".
    features = {
        'audio': r'#+\s*.*Audio Overview',
        'video': r'#+\s*.*Video Overview',
        'mindmap': r'#+\s*.*Mind Map',
        'reports': r'#+\s*.*Reports',
        'flashcards': r'#+\s*.*Flashcards',
        'quiz': r'#+\s*.*Quiz',
        'infographic': r'#+\s*.*Infographic',
        'slides': r'#+\s*.*Slide Deck',
        'datatable': r'#+\s*.*Data Table'
    }
    
    active_features = []
    for key, pattern in features.items():
        # Check if header exists
        if re.search(pattern, text, re.IGNORECASE):
            # Capture content between this header and the NEXT header (or end of file)
            section_match = re.search(f"{pattern}.*\\n([\\s\\S]*?)(?=\\n#|$)", text, re.IGNORECASE)
            # If the capture group contains non-whitespace characters, it's active
            if section_match and section_match.group(1).strip():
                active_features.append(key)
                
    return clean_overview, active_features

# --- 🚀 PROJECT EXTRACTORS (RESTORED) ---

def extract_mission_brief(body):
    if "# 🚨 Mission Brief" in body:
        try:
            part = body.split("# 🚨 Mission Brief")[1]
            if "\n# " in part: part = part.split("\n# ")[0]
            lines = part.split('\n')
            clean_lines = [l for l in lines if not l.strip().startswith('(') and l.strip()]
            clean = " ".join(clean_lines)
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
            return clean[:240] + "..." if len(clean) > 240 else clean
        except Exception: pass
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
        except Exception: pass
    return ""

def extract_impact_metrics(body):
    metrics = []
    if "# ⚡ Operational Impact" in body:
        try:
            part = body.split("# ⚡ Operational Impact")[1]
            if "\n# " in part: part = part.split("\n# ")[0]
            matches = re.findall(r'[\-\*]\s*\*\*(.*?)\*\*[:\s]', part)
            metrics = [m.strip() for m in matches]
        except Exception: pass
    return metrics[:4]

# --- 🏭 THE CARD FACTORY (VISUAL COMPONENT ENGINE) ---

def generate_garden_card_html(meta, filename, note_id, body_content, full_search_text):
    note_type = meta.get("type", "unknown").lower()
    
    # 1. Type ID Logic
    if (note_type == "unknown" or not note_type) and meta.get("tags"):
        for tag in meta["tags"]:
            if tag.startswith("type/"): note_type = tag.split("/")[1]; break
    if re.match(r'\d{4}-\d{2}-\d{2}', filename): note_type = "daily-bridge"
    meta["type"] = note_type
    title = filename.replace(".md", "").replace("_", " ")

    # 2. Base Component Shell
    base_classes = "searchable-item glass p-5 rounded-sm border border-opacity-40 hover:border-opacity-100 cursor-pointer flex flex-col gap-3 transition-all duration-300 hover:translate-y-[-4px] hover:shadow-2xl hover:z-10 group h-full min-h-[240px]"
    
    # --- CARD TYPE: DAILY LOG ---
    if "daily" in note_type or "log" in note_type:
        color = "border-aurelia-tertiary"
        mission, source, cues, summary = extract_log_data(body_content)
        
        # Truncate summary
        if len(summary) > 120: summary = summary[:120] + "..."

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
                    {''.join([f'<span class="text-[10px] font-mono px-2 py-0.5 bg-aurelia-tertiary/10 text-aurelia-tertiary border border-aurelia-tertiary/30 rounded-sm font-bold">{c}</span>' for c in cues])}
                </div>
            </div>

        </div>"""
        icon = "📅"; label = "SYS_LOG"

    # --- CARD TYPE: CONCEPT NODE ---
    elif "concept" in note_type:
        color = "border-aurelia-primary" # Cyan
        definition, links = extract_concept_data(body_content)
        
        # Truncate definition slightly longer than logs to ensure clarity
        if len(definition) > 160: definition = definition[:160] + "..."

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
                    {''.join([f'<span class="hover:text-aurelia-primary transition-colors cursor-pointer border-b border-gray-700 hover:border-aurelia-primary pb-0.5">→ {l}</span>' for l in links])}
                    {'' if links else '<span class="opacity-30 text-[9px]">// NO_LINKS_DETECTED</span>'}
                </div>
            </div>
        </div>"""
        icon = "⚛️"; label = "CONCEPT"

   # --- CARD TYPE: SOURCE TEXT ---
    elif "source" in note_type:
        color = "border-yellow-500" # Gold
        author, argument, concepts = extract_source_data(body_content)
        
        # Status Logic
        status = "ARCHIVED"
        if "reading" in str(meta.get("tags")): status = "READING"
        if "seed" in str(meta.get("tags")): status = "QUEUED"
        
        if len(argument) > 150: argument = argument[:150] + "..."

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
                    {''.join([f'<span class="text-[9px] font-mono px-1.5 py-0.5 border border-yellow-500/40 text-gray-300 rounded-sm hover:text-yellow-500 transition-colors cursor-default">{c}</span>' for c in concepts])}
                    {'' if concepts else '<span class="opacity-30 text-[9px] text-gray-500 font-mono">// NO_CONCEPTS_LINKED</span>'}
                 </div>
            </div>
        </div>"""
        icon = "📚"; label = "LIBRARY"

    # --- CARD TYPE: AUTHOR PROFILE ---
    elif "author" in note_type:
        color = "border-aurelia-secondary" # Purple/Pink
        context, works, concepts = extract_author_data(body_content)
        
        if len(context) > 150: context = context[:150] + "..."

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
                    {''.join([f'<span class="text-[9px] font-mono px-2 py-1 bg-aurelia-secondary text-black font-bold rounded-sm border border-aurelia-secondary">{c}</span>' for c in concepts])}
                    {'' if concepts else '<span class="text-[9px] text-white font-mono opacity-80">// NO_SYSTEMS_DETECTED</span>'}
                </div>
            </div>
            
            <div class="pt-2 border-t border-gray-600">
                <span class="text-[9px] font-bold font-mono text-white uppercase tracking-widest block mb-1">BIBLIOGRAPHY:</span>
                <div class="flex flex-wrap gap-1.5">
                    {''.join([f'<span class="text-[9px] font-mono px-2 py-0.5 border border-gray-400 text-white font-bold rounded-sm hover:border-aurelia-secondary hover:text-aurelia-secondary transition-colors cursor-default">{w}</span>' for w in works])}
                </div>
            </div>

        </div>"""
        icon = "👤"; label = "PROFILE"

    # --- CARD TYPE: DISCIPLINE ---
    elif "discipline" in note_type:
        color = "border-aurelia-accent" # Unique Accent Color
        scope, pillars, canon = extract_discipline_data(body_content)
        
        if len(scope) > 160: scope = scope[:160] + "..."

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
                    {''.join([f'<span class="text-[9px] font-mono px-2 py-1 bg-aurelia-accent text-black font-extrabold rounded-sm uppercase">{p}</span>' for p in pillars])}
                    {'' if pillars else '<span class="text-[9px] text-gray-500 font-mono">// FOUNDATIONS_PENDING</span>'}
                </div>
            </div>
            
            <div class="pt-2 border-t border-gray-600">
                <span class="text-[9px] font-bold font-mono text-white uppercase tracking-widest block mb-1">THE_CANON:</span>
                <div class="flex flex-col gap-1">
                    {''.join([f'<span class="text-[10px] font-serif italic text-gray-300 hover:text-white transition-colors truncate">• {t}</span>' for t in canon])}
                </div>
            </div>

        </div>"""
        icon = "🧠"; label = "FIELD"

# --- CARD TYPE: NOTEBOOKLM (AI SYNTHESIS) ---
    elif "notebooklm" in note_type:
        color = "border-indigo-500" # AI/Synthesis Color
        overview, active_features = extract_notebooklm_data(body_content)
        
        if len(overview) > 160: overview = overview[:160] + "..."
        
        # Icon Mapping
        feature_icons = {
            'audio': '🎙️', 'video': '🎥', 'mindmap': '🧠', 
            'reports': '📄', 'flashcards': '🃏', 'quiz': '📝',
            'infographic': '📊', 'slides': '📽️', 'datatable': '📉'
        }

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
                    {''.join([f'''
                    <div class="flex items-center gap-2 px-2 py-1 bg-indigo-500/10 border border-indigo-500/30 rounded-sm" title="{f.upper()}">
                        <span class="text-xs">{feature_icons.get(f, "•")}</span>
                        <span class="text-[9px] font-mono text-indigo-300 font-bold uppercase">{f}</span>
                    </div>
                    ''' for f in active_features])}
                    
                    {'' if active_features else '<span class="text-[9px] text-gray-600 font-mono">// NO_MODULES_ONLINE</span>'}
                </div>
            </div>
        </div>"""
        icon = "🧬"; label = "NOTEBOOK"

    # --- DEFAULT CARD ---
    else:
        color = "border-gray-800"
        clean_body = re.sub(r'<[^>]+>', '', body_content) 
        clean_body = re.sub(r'[*#_`\[\]]', '', clean_body)
        blurb = clean_body[:200] + "..."
        card_content = f"""<div class="flex flex-col h-full"><p class="text-sm text-gray-400 font-sans leading-relaxed line-clamp-5">{blurb}</p></div>"""
        icon = "📄"; label = "NOTE"

    # 3. Assemble Final HTML
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
    
    # Extract Tech Stack from YAML (Safe Fallback)
    tech_stack = meta.get("tech_stack", [])
    if isinstance(tech_stack, str): tech_stack = [tech_stack] # Handle single item
    
    live_link = meta.get('link_live')
    
    # 3. Build Action Buttons
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

    # 4. Search Meta
    search_text = f"{title} project {mission} {logic}".lower().replace('\n', ' ').replace('"', "'")

    # 5. GENERATE HTML (High Contrast "Dossier" Design)
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
                {''.join([f'<span class="text-[9px] font-mono text-black bg-white px-1.5 py-0.5 rounded-sm font-bold uppercase">{t}</span>' for t in tech_stack[:4]])}
             </div>
             
             <div class="flex flex-wrap gap-2">
                {''.join([f'<span class="text-[10px] font-mono text-gray-300 border border-gray-600 px-2 py-1 rounded-sm">⚡ {m}</span>' for m in impacts])}
             </div>
        </div>

        {action_buttons}
    </div>
    """
    return html

# --- CARD TYPE: PROTOCOL ---
def generate_protocol_card(meta, body, title, note_id, p_id_override=None):
    # 1. EXTRACT DATA
    # Use the override ID if provided (ensures match with build_all loop), else fallback to metadata
    prot_id = p_id_override if p_id_override else meta.get("id", "SYS_CMD").upper()
    sequence = extract_protocol_sequence(body)
    logic = extract_protocol_logic(body)
    
    # 2. STATUS INDICATOR
    is_auto = "automated" in meta.get("tags", [])
    status_text = "DAEMON" if is_auto else "MANUAL"
    
    # 3. SEARCH META
    search_text = f"{title} {prot_id} {' '.join(sequence)}".lower()

    # 4. GENERATE HTML (High-Vis HUD Design)
    # CRITICAL FIX: onclick uses 'prot_id' (PROT_01) instead of 'note_id' (note-slug)
    # This ensures it matches the 'store-{{ p.id }}' in the HTML template.
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
                {''.join([f'''
                <div class="flex items-start gap-3 group/item">
                    <span class="text-gray-500 font-bold text-xs shrink-0 select-none group-hover:text-aurelia-accent transition-colors">0{i+1}</span>
                    <span class="text-sm text-gray-200 font-medium group-hover/item:text-white transition-colors border-l-2 border-gray-800 pl-3 leading-snug">
                        {item}
                    </span>
                </div>
                ''' for i, item in enumerate(sequence)])}
                {'' if sequence else '<span class="text-sm text-gray-500 italic">// NO_STEPS_DETECTED</span>'}
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

# --- HELPER: DATE SERIALIZER FOR TRANSMISSIONS ---
from datetime import date, datetime
def json_serial(obj):
    if isinstance(obj, (datetime, date)): return obj.isoformat()
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
    transmissions_data = []

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
                # Normalize type
                note_type = meta.get("type", "unknown").lower().strip()
                tags = meta.get("tags", []) 
                title = filename.replace(".md", "").replace("_", " ")
                
                # --- ROUTING SWITCH (The "Traffic Cop") ---
                
                # ROUTE A: PROJECTS -> Portfolio
                if "project" in note_type:
                    project_id = f"project-{len(portfolio_cards)}"
                    sections = {"brief": body}
                    # Generate the High-Contrast Dossier HTML
                    card_html = generate_project_card(meta, sections, title, project_id)
                    
                    portfolio_cards.append({
                        "html": card_html, 
                        "body": body, 
                        "id": project_id,
                        "title": title,
                        "link": f"portfolio.html#{project_id}", 
                        "type": "PROJECT",
                        "tags": tags,
                        "desc": extract_mission_brief(body)
                    })

                # ROUTE B: PROTOCOLS -> Ignore here (Handled in Step 3 for dedicated folder scan)
                elif "protocol" in note_type:
                    continue 

                # ROUTE C: TRANSMISSIONS -> Ignore here (Handled in Step 4)
                elif "transmission" in note_type:
                    continue 

                # ROUTE D: GARDEN NOTES -> Garden
                else:
                    note_id = make_id(filename)
                    
                    # ⚡ DEEP SEARCH GENERATION ⚡
                    raw_search = body
                    raw_search = re.sub(r'[*#_`\[\]]', '', raw_search)
                    raw_search = re.sub(r'<[^>]+>', '', raw_search)
                    full_search_text = raw_search.replace('\n', ' ').replace('"', "").replace("'", "").lower()
                    
                    # 1. Standard Link Processing
                    processed_body = process_wikilinks(body)
                    
                    # 2. SPECIAL: NotebookLM Media Processing (Audio/Video/Images)
                    if "notebooklm" in note_type:
                        processed_body = process_notebooklm_media(processed_body)
                    
                    # Generate the Specific Card Type HTML
                    card_html = generate_garden_card_html(meta, filename, note_id, processed_body, full_search_text)
                    
                    garden_cards.append({
                        "html": card_html, 
                        "body": processed_body, # Now contains the <audio> player HTML
                        "id": note_id,
                        "title": title,
                        "link": f"garden.html#{note_id}", 
                        "type": meta.get("type", "NOTE").upper(), 
                        "tags": tags,
                        "desc": full_search_text
                    })

    # 3. SCAN PROTOCOLS (Dedicated Scanner)
    scan_path = PROTOCOL_PATH if os.path.exists(PROTOCOL_PATH) else VAULT_PATH

    for root, dirs, files in os.walk(scan_path):
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                meta = parse_frontmatter(content)
                if "protocol" not in meta.get("type", ""): continue
                if not meta.get("publish", False): continue
                
                body = parse_body(content)
                title = filename.replace(".md", "").replace("_", " ")
                
                # CALCULATE CONSISTENT ID
                p_id = meta.get("id", "PROT_" + filename[:3].upper())
                note_id = make_id(filename)

                # PASS p_id TO GENERATOR
                card_html = generate_protocol_card(meta, body, title, note_id, p_id)
                
                protocol_cards.append({
                    "html": card_html,
                    "title": title,
                    "desc": meta.get("description", "System Protocol"),
                    "tags": meta.get("tags", []),
                    "body": body,
                    "id": p_id,  # This ID matches the onclick='p_id' above
                    "link": "protocol.html", 
                    "type": "PROTOCOL"
                })
    # 4. SCAN TRANSMISSIONS
    if user_config.get('modules', {}).get('transmissions', {}).get('enabled', False):
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
                    
                    if 'series' not in t_meta: t_meta['series'] = 'Uncategorized'
                    if 'title' not in t_meta: t_meta['title'] = filename.replace(".md", "")
                    try: t_meta['episode'] = int(t_meta.get('episode', 999))
                    except: t_meta['episode'] = 999
                    
                    try:
                        import markdown
                        t_meta['content'] = markdown.markdown(t_body, extensions=['fenced_code', 'tables']) 
                    except ImportError:
                        t_meta['content'] = t_body 
                        
                    t_meta['tags'] = t_meta.get("tags", [])
                    transmissions_data.append(t_meta)

    # ⚡ SORTING ENGINE ⚡
    garden_cards.sort(key=lambda x: x['title'].lower())
    portfolio_cards.sort(key=lambda x: x['title'].lower())
    protocol_cards.sort(key=lambda x: x['title'].lower())
    transmissions_data.sort(key=lambda x: (x['series'], x['episode']))

    print(f"   + Indexing: {len(garden_cards)} Notes, {len(portfolio_cards)} Projects, {len(protocol_cards)} Protocols, {len(transmissions_data)} Transmissions")
    
    # 5. BUILD MASTER SEARCH INDEX
    master_index = []
    
    # System Pages
    master_index.append({"title": "Home // Mission Control", "url": "index.html", "type": "SYSTEM", "tags": ["home", "root"], "desc": "Main Hub"})
    master_index.append({"title": "The Garden // Input", "url": "garden.html", "type": "SYSTEM", "tags": ["notes", "writing"], "desc": "Digital Garden"})
    master_index.append({"title": "Protocols // Logic", "url": "protocol.html", "type": "SYSTEM", "tags": ["sop", "routines"], "desc": "Operating Procedures"})
    master_index.append({"title": "Portfolio // Output", "url": "portfolio.html", "type": "SYSTEM", "tags": ["work", "jobs"], "desc": "Case Studies"})
    if transmissions_data:
        master_index.append({"title": "Transmissions // Signal", "url": "transmissions.html", "type": "SYSTEM", "tags": ["podcast", "audio"], "desc": "Neural Uplink"})
    
    # Content Indexing
    for c in garden_cards: 
        master_index.append({"title": c['title'], "url": c['link'], "type": "GARDEN", "tags": c['tags'], "desc": c['desc']})
    for p in portfolio_cards: 
        master_index.append({"title": p['title'], "url": p['link'], "type": "PROJECT", "tags": p['tags'], "desc": p['desc']})
    for prot in protocol_cards: 
        master_index.append({"title": prot['title'], "url": prot['link'], "type": "PROTOCOL", "tags": prot['tags'], "desc": prot['desc']})
    for trans in transmissions_data:
        master_index.append({"title": trans['title'], "url": "transmissions.html", "type": "TRANSMISSION", "tags": trans['tags'], "desc": f"Series: {trans['series']} // Ep {trans['episode']}"})

    # Serialize Data
    json_index = json.dumps(master_index)
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

    if user_config.get('modules', {}).get('transmissions', {}).get('enabled', False):
         pages.append(("pages/transmissionstemplate.html", "transmissions.html", {"transmissions_json": transmissions_json}))

    # RENDER LOOP
    for template_name, output_name, context in pages:
        try:
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

# --- THIS IS THE CRITICAL PART: UN-INDENTED! ---
if __name__ == "__main__":
    build_all()