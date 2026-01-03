import os
import re
import html

# CONFIGURATION
VAULT_PATH = "./vault"               # Where your notes live
TEMPLATE_FILE = "portfolio_template.html" # The Clean Blueprint
OUTPUT_FILE = "portfolio.html"       # The Final Site (Generated)
INJECTION_TARGET = "<!-- PORTFOLIO_CARDS_PLACEHOLDER -->"  # Injection Marker

def parse_frontmatter(content):
    """Extracts YAML frontmatter as a dictionary."""
    meta = {"publish": False, "type": "unknown", "status": "archive"}
    
    if not content.startswith("---"): return meta
    try:
        parts = content.split("---", 2)
        if len(parts) < 3: return meta
        yaml_text = parts[1]
        
        # 1. STRICT PUBLISH CHECK
        # Looks for "publish: true" (case insensitive)
        if re.search(r'^publish:\s*true', yaml_text, re.MULTILINE | re.IGNORECASE):
             meta["publish"] = True
        
        # 2. Extract Basic Fields
        for field in ["type", "status", "role", "cover_image", "date"]:
            match = re.search(rf'^{field}:\s*(.+)$', yaml_text, re.MULTILINE)
            if match: 
                clean_val = match.group(1).strip().strip('"').strip("'").replace("{{", "").replace("}}", "")
                meta[field] = clean_val

        # 3. Extract Lists (Tech Stack & Stats)
        stack_match = re.search(r'^tech_stack:\s*\[(.*?)\]', yaml_text, re.MULTILINE)
        if stack_match:
            meta["tech_stack"] = [x.strip() for x in stack_match.group(1).split(',')]
        
        # Stats Extraction
        stats_blocks = re.findall(r'-\s*"(.*?)"', yaml_text)
        if not stats_blocks: # Fallback for unquoted stats
             stats_blocks = re.findall(r'-\s*([a-zA-Z0-9_ :<>$%.]+)', yaml_text)
        
        # Heuristic: Only keep stats if we actually found a "stats:" key nearby
        if "stats:" in yaml_text and stats_blocks:
             # We take the ones likely intended as stats (simple list after stats:)
             # For robustness, we stick to the Regex that finds quoted items or explicit list items
             explicit_stats = re.findall(r'-\s*"(.*?)"', yaml_text)
             if explicit_stats: meta["stats"] = explicit_stats

        # 4. Extract Flattened Links
        links = {}
        repo = re.search(r'^link_repo:\s*"?([^"\n]+)"?', yaml_text, re.MULTILINE)
        live = re.search(r'^link_live:\s*"?([^"\n]+)"?', yaml_text, re.MULTILINE)
        demo = re.search(r'^link_demo:\s*"?([^"\n]+)"?', yaml_text, re.MULTILINE)
        
        if repo and repo.group(1).strip(): links["repo"] = repo.group(1).strip()
        if live and live.group(1).strip(): links["live"] = live.group(1).strip()
        if demo and demo.group(1).strip(): links["demo"] = demo.group(1).strip()
        
        meta["links"] = links

    except Exception as e:
        print(f"YAML Parse Error: {e}")
    return meta

def parse_body(content):
    """Splits the project note into its 3 narrative sections."""
    sections = {"brief": "Mission data unavailable.", "arch": "Architecture data unavailable.", "impact": "Impact data unavailable."}
    parts = content.split("---", 2)[-1] 
    
    try:
        if "# 🚨 Mission Brief" in parts:
            sections["brief"] = parts.split("# 🚨 Mission Brief")[1].split("# 🛠️ Architecture")[0].strip()
        
        if "# 🛠️ Architecture" in parts:
            temp = parts.split("# 🛠️ Architecture")[1]
            if "# ⚡ Operational Impact" in temp:
                sections["arch"] = temp.split("# ⚡ Operational Impact")[0].strip()
            else:
                sections["arch"] = temp.strip()

        if "# ⚡ Operational Impact" in parts:
            sections["impact"] = parts.split("# ⚡ Operational Impact")[1].strip()
            
    except Exception as e: pass
    return sections

def generate_card(meta, sections, title):
    # 1. Status Logic
    status_colors = {
        "active": "bg-aurelia-green shadow-[0_0_10px_#39ff14]",
        "building": "bg-aurelia-orange shadow-[0_0_10px_#ff8c00]",
        "archive": "bg-gray-500",
        "offline": "bg-red-500 shadow-[0_0_10px_red]"
    }
    status_dot = status_colors.get(meta.get("status", "archive").lower(), "bg-gray-500")
    
    # 2. Tech Stack
    stack_html = ""
    if "tech_stack" in meta:
        for tech in meta["tech_stack"]:
            if tech:
                stack_html += f'<span class="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-[10px] font-mono text-gray-300 hover:border-aurelia-cyan transition-colors cursor-default">{tech}</span>'

    # 3. Stats HUD
    stats_html = ""
    if "stats" in meta:
        for stat in meta["stats"]:
            if ":" in stat:
                label, val = stat.split(":", 1)
                stats_html += f'''
                <div class="flex flex-col items-end">
                    <span class="text-[9px] text-gray-500 uppercase tracking-wider">{label}</span>
                    <span class="text-sm font-mono text-aurelia-cyan">{val}</span>
                </div>
                '''

    # 4. Links
    links_html = ""
    links = meta.get("links", {})
    if links.get("live"):
        links_html += f'<a href="{links["live"]}" target="_blank" class="flex items-center gap-2 text-xs font-mono text-aurelia-green hover:text-white transition-colors group/link"><div class="w-1.5 h-1.5 bg-aurelia-green rounded-full group-hover/link:animate-ping"></div>LIVE_UPLINK -></a>'
    if links.get("repo"):
        links_html += f'<a href="{links["repo"]}" target="_blank" class="flex items-center gap-2 text-xs font-mono text-gray-500 hover:text-white transition-colors">SOURCE_CODE</a>'

    # 5. Content Preview (Clean)
    brief_preview = sections['brief'][:240].replace('**', '').replace('*', '') + "..."

    # CARD HTML
    html = f"""
    <div class="border border-aurelia-dim bg-black/40 p-6 rounded relative group hover:border-aurelia-cyan/50 transition-all duration-300 flex flex-col h-full">
        <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-3">
                <div class="w-2 h-2 rounded-full {status_dot} animate-pulse"></div>
                <div>
                    <h3 class="text-lg font-bold text-white font-mono tracking-tight">{title.replace('_', ' ').replace('.md', '')}</h3>
                    <p class="text-[10px] text-gray-500 font-mono mt-1 uppercase tracking-wider">{meta.get('role', 'Architect')}</p>
                </div>
            </div>
            <div class="flex gap-6 text-right">
                {stats_html}
            </div>
        </div>

        <div class="flex flex-wrap gap-2 mb-6">
            {stack_html}
        </div>

        <div class="text-sm text-gray-400 font-sans leading-relaxed mb-6 flex-grow">
            <span class="text-aurelia-dim font-bold">>> MISSION_BRIEF: </span>
            {brief_preview}
        </div>

        <div class="flex justify-between items-center border-t border-gray-800 pt-4 mt-auto">
            <div class="flex gap-4">
                {links_html}
            </div>
            <button class="text-[9px] font-mono text-aurelia-cyan/60 hover:text-aurelia-cyan transition-colors uppercase tracking-widest border border-transparent hover:border-aurelia-cyan/30 px-2 py-1 rounded">
                Read_Full_Dossier [+]
            </button>
        </div>
    </div>
    """
    return html

def build_portfolio():
    print("\n🔄 AURELIA SYSTEM: Initializing Portfolio Build...")
    
    # 1. VERIFY TEMPLATE
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ CRITICAL: {TEMPLATE_FILE} missing. Please create it from portfolio.html.")
        return

    # 2. READ TEMPLATE (CLEAN SLATE)
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    cards_html = ""
    count = 0

    # 3. COMPILE CARDS
    for root, dirs, files in os.walk(VAULT_PATH):
        for filename in sorted(files):
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                meta = parse_frontmatter(content)
                
                # FILTER: Must be 'project' AND 'publish: true'
                if meta.get("type") == "project" and meta.get("publish") is True:
                    print(f"   + Compiling: {filename}")
                    sections = parse_body(content)
                    cards_html += generate_card(meta, sections, filename)
                    count += 1

    # 4. INJECT AND WRITE TO OUTPUT
    if INJECTION_TARGET in html_content:
        # Simple Replacement - No accumulation risk
        new_html = html_content.replace(INJECTION_TARGET, cards_html)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"✅ SUCCESS: Generated {OUTPUT_FILE} with {count} active projects.")
    else:
        print(f"❌ ERROR: Injection target '{INJECTION_TARGET}' not found in {TEMPLATE_FILE}")

if __name__ == "__main__":
    build_portfolio()