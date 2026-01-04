import os
import re
from jinja2 import Environment, FileSystemLoader

# --- CONFIGURATION ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
VAULT_PATH = os.path.join(ROOT_DIR, "vault")
TEMPLATE_DIR = os.path.join(ROOT_DIR, "system/templates")
OUTPUT_DIR = ROOT_DIR 

print(f"🔧 CONFIG: Root={ROOT_DIR}")
print(f"🔧 CONFIG: Vault={VAULT_PATH}")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# --- HELPER: Frontmatter Parser ---
def parse_frontmatter(content):
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}
    if not content.startswith("---"): return meta
    try:
        parts = content.split("---", 2)
        if len(parts) < 3: return meta
        yaml_text = parts[1]
        
        if re.search(r'^publish:\s*true', yaml_text, re.MULTILINE | re.IGNORECASE):
             meta["publish"] = True
        
        for field in ["type", "status", "role", "cover_image", "date", "icon"]:
            match = re.search(rf'^{field}:\s*(.+)$', yaml_text, re.MULTILINE)
            if match: 
                meta[field] = match.group(1).strip().strip('"').strip("'").replace("{{", "").replace("}}", "")

        tags_match = re.search(r'^tags:\s*\[(.*?)\]', yaml_text, re.MULTILINE)
        if tags_match:
            meta["tags"] = [t.strip() for t in tags_match.group(1).split(',')]
        else:
            clean_tags = []
            capture = False
            for line in yaml_text.split('\n'):
                if line.strip().startswith('tags:'):
                    capture = True
                    continue
                if capture and line.strip().startswith('-'):
                    clean_tags.append(line.strip().replace('-', '').strip())
                elif capture and ':' in line:
                    capture = False
            if clean_tags:
                meta["tags"] = clean_tags

    except Exception as e:
        print(f"YAML Error: {e}")
    return meta

def parse_body(content):
    parts = content.split("---", 2)
    if len(parts) < 3: return content
    return parts[2].strip()

# --- EXTRACTORS (SURGICALLY REPAIRED) ---

def extract_related_links(body):
    """
    Fix: Handles [[Link]] and [[Link|Alias]] correctly without leaving empty commas.
    """
    match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', body)
    if match:
        raw = match.group(1)
        # Find all [[...]] content
        links = re.findall(r'\[\[(.*?)\]\]', raw)
        # Split by pipe | to get alias if present, otherwise text
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
            # Clean bullets
            clean = line.strip().replace("*", "").replace("-", "").strip()
            # Clean wikilinks: [[Link|Alias]] -> Alias
            clean = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean)
            if clean: works.append(clean)
    return works[:3]

def extract_core_concepts(body):
    concepts = []
    capture = False
    for line in body.split('\n'):
        if "### 🔑 Core Concepts" in line or "### ⚛️ Core Concepts" in line:
            capture = True
            continue
        if capture and line.strip().startswith("###"):
            break
        if capture and (line.strip().startswith("*") or line.strip().startswith("-")):
            clean = line.strip().replace("*", "").replace("-", "").strip()
            clean = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean)
            clean = clean.replace("#", "") # Remove extra hashtags
            if clean: concepts.append(clean)
    return concepts[:4]

def extract_atomic_cues(body):
    cues = []
    for line in body.split('\n'):
        if "**Concept:**" in line:
            match = re.search(r'\[\[(.*?)\]\]', line)
            if match:
                cues.append(match.group(1).split('|')[-1])
    return cues[:4]

def extract_source_author(body):
    # Try linked author first: **👤 Author:** [[Name]]
    match = re.search(r'\*\*👤 Author:\*\*\s*\[\[(.*?)\]\]', body)
    if match: return match.group(1).split('|')[-1]
    
    # Try plain text: **👤 Author:** Name
    match_plain = re.search(r'\*\*👤 Author:\*\*\s*(.*)', body)
    if match_plain: return match_plain.group(1).strip()
    return "Unknown"

# --- GENERATOR (MATCHING OLDGARDEN.HTML EXACTLY) ---
def generate_garden_card_html(meta, filename, note_id, body_content):
    note_type = meta.get("type", "unknown").lower()
    if note_type == "unknown" and meta.get("tags"):
        for tag in meta["tags"]:
            if tag.startswith("type/"):
                note_type = tag.split("/")[1]
                break
    
    meta["type"] = note_type
    title = filename.replace(".md", "").replace("_", " ")
    
    # --- CONTENT CLEANING (THE FIX) ---
    # 1. Remove Headers (### ...)
    clean_body = re.sub(r'#{1,6}\s.*', '', body_content)
    # 2. Remove Metadata lines (**Key:** ...)
    clean_body = re.sub(r'\*\*.*?\*\*.*', '', clean_body)
    # 3. Replace [[Link|Alias]] with Alias, and [[Link]] with Link (Preserve Text!)
    clean_body = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', clean_body)
    # 4. Remove bold/italic markers
    clean_body = re.sub(r'[*_]{2,}', '', clean_body)
    # 5. Collapse whitespace
    clean_body = " ".join(clean_body.split())
    
    # Truncate to match OldGarden density (380 chars instead of 200)
    blurb = clean_body[:380].strip() + "..."
    
    # Sanitization for Data Attributes
    raw_search = f"{title} {note_type} {body_content}".lower()
    search_text = raw_search.replace('\n', ' ').replace('"', "'").replace("  ", " ")

    # SCHEMA DEFINITIONS
    if "daily" in note_type or "log" in note_type:
        color = "border-aurelia-orange"
        icon = "📅"
        label = "Daily_Log"
        cues = extract_atomic_cues(body_content)
        
        # Pill Style: Colored Background
        footer_html = '<div class="mt-auto pt-4 flex items-center justify-start border-t border-gray-800/50"><div class="flex gap-2 flex-wrap">'
        for cue in cues:
             footer_html += f'<span class="text-xs font-mono px-2 py-1 bg-aurelia-orange/10 text-aurelia-orange border border-aurelia-orange/20 rounded">{cue}</span>'
        footer_html += '</div></div>'
        
    elif "concept" in note_type:
        color = "border-aurelia-cyan"
        icon = "⚛️"
        label = "Concept_Node"
        related = extract_related_links(body_content)
        
        footer_html = '<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-xs text-aurelia-cyan font-mono mb-2 opacity-90">LINKED_TO:</div><div class="flex gap-3 text-xs text-gray-300 font-mono flex-wrap">'
        if related:
            for link in related[:2]:
                footer_html += f'<span class="hover:text-white transition-colors cursor-pointer">→ {link}</span>'
        else:
            footer_html += '<span class="opacity-50">// ROOT</span>'
        footer_html += '</div></div>'

    elif "author" in note_type:
        color = "border-white"
        icon = "👤"
        label = "Author_Profile"
        works = extract_key_works(body_content)
        
        footer_html = '<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-xs font-mono text-gray-400 mb-1">KEY WORKS:</div><ul class="text-xs font-mono text-gray-300 space-y-1">'
        for work in works:
            footer_html += f'<li class="flex items-center gap-2"><span class="text-aurelia-green">●</span> {work}</li>'
        footer_html += '</ul></div>'

    elif "source" in note_type:
        color = "border-yellow-500"
        icon = "📖"
        label = "Source_Text"
        author = extract_source_author(body_content)
        status = meta.get("status", "ARCHIVED").upper()
        
        footer_html = f'''
        <div class="mt-auto pt-4 flex justify-between items-center border-t border-gray-800/50">
            <div class="text-xs font-mono text-gray-400">AUTH: {author.upper()}</div>
            <span class="px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-500 text-xs font-mono border border-yellow-500/20">{status}</span>
        </div>
        '''

    elif "discipline" in note_type:
        color = "border-aurelia-green"
        icon = "🧠"
        label = "Discipline"
        concepts = extract_core_concepts(body_content)
        
        footer_html = '<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-xs font-mono text-gray-400 mb-1">CORE CONCEPTS:</div><ul class="text-xs font-mono text-gray-300 space-y-1">'
        for c in concepts:
            footer_html += f'<li class="flex items-center gap-2"><span class="text-aurelia-green">●</span> {c}</li>'
        footer_html += '</ul></div>'
        
    else:
        color = "border-gray-800"
        icon = "📄"
        label = "Node"
        footer_html = f'<div class="mt-auto pt-4 border-t border-gray-800/50 text-xs text-gray-500">#{note_type}</div>'

    # --- HTML ASSEMBLY ---
    # Matches OldGarden physics: hover scale 1.12, large typography
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

def generate_project_card(meta, sections, title):
    status_dot = "bg-aurelia-green shadow-[0_0_10px_#39ff14]" if meta.get("status") == "active" else "bg-gray-500"
    stats_html = ""
    if "stats" in meta:
        for stat in meta["stats"]:
            if ":" in stat:
                l, v = stat.split(":", 1)
                stats_html += f'<div class="flex flex-col items-end"><span class="text-[9px] text-gray-500 uppercase">{l}</span><span class="text-sm font-mono text-aurelia-cyan">{v}</span></div>'
    
    # Sanitization
    brief = sections.get('brief', '')
    search_text = f"{title} project {brief}".lower().replace('\n', ' ').replace('"', "'")

    html = f"""
    <div class="searchable-item border border-aurelia-dim bg-black/40 p-6 rounded relative group hover:border-aurelia-cyan/50 transition-all duration-300 flex flex-col h-full" data-type="project" data-search="{search_text}">
        <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-3">
                <div class="w-2 h-2 rounded-full {status_dot} animate-pulse"></div>
                <div>
                    <h3 class="text-lg font-bold text-white font-mono tracking-tight">{title.replace('_', ' ').replace('.md', '')}</h3>
                    <p class="text-[10px] text-gray-500 font-mono mt-1 uppercase">{meta.get('role', 'Architect')}</p>
                </div>
            </div>
            <div class="flex gap-6 text-right">{stats_html}</div>
        </div>
        <div class="text-sm text-gray-400 font-sans leading-relaxed mb-6 flex-grow">
             {brief[:240]}...
        </div>
    </div>
    """
    return html

def build_all():
    print("\n🧬 AURELIA SYSTEM: INITIALIZING JINJA CORE...")
    garden_cards = []
    portfolio_cards = []
    
    for root, dirs, files in os.walk(VAULT_PATH):
        for filename in sorted(files):
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                meta = parse_frontmatter(content)
                if not meta.get("publish"): continue 

                note_id = f"note-{len(garden_cards)}"
                body = parse_body(content)
                note_type = meta.get("type", "unknown").lower()
                if note_type == "unknown" and meta.get("tags"):
                    for tag in meta["tags"]:
                        if tag.startswith("type/"):
                            note_type = tag.split("/")[1]
                            break
                
                if "project" in note_type:
                    sections = {"brief": body}
                    portfolio_cards.append(generate_project_card(meta, sections, filename))
                else:
                    card_html = generate_garden_card_html(meta, filename, note_id, body)
                    garden_cards.append({
                        "html": card_html,
                        "body": body,
                        "id": note_id,
                        "type": note_type,
                        "title": filename.replace(".md", "")
                    })

    print(f"   + Loaded {len(garden_cards)} Garden Nodes")
    print(f"   + Loaded {len(portfolio_cards)} Projects")

    pages = [
        ("pages/index.html", "index.html", {}),
        ("pages/garden.html", "garden.html", {"cards": garden_cards}),
        ("pages/portfolio.html", "portfolio.html", {"projects": portfolio_cards}),
        ("pages/services.html", "services.html", {}),
        ("pages/museum.html", "museum.html", {})
    ]

    for template_name, output_name, context in pages:
        try:
            template = env.get_template(template_name)
            rendered_html = template.render(**context)
            out_path = os.path.join(OUTPUT_DIR, output_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"   ✅ Deployed: {output_name}")
        except Exception as e:
            print(f"   ❌ Failed: {output_name} -> {e}")

    print("\n✅ SYSTEM SYNC COMPLETE.")

if __name__ == "__main__":
    build_all()