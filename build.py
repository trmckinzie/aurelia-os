import os
import re
import datetime

# ==============================================================================
# ⚙️ CONFIGURATION & CONSTANTS
# ==============================================================================
VAULT_PATH = "./vault"
TEMPLATE_FILE = "template.html"
OUTPUT_FILE = "garden.html"
TARGET_MARKER = "<!--CONTENT-->"

# Visual Styles based on Status
STATUS_COLORS = {
    "status/seed": "border-gray-700 opacity-80",
    "status/sapling": "border-aurelia-cyan/50 shadow-[0_0_15px_rgba(0,242,255,0.1)]",
    "status/evergreen": "border-aurelia-green shadow-[0_0_20px_rgba(57,255,20,0.2)]",
    "status/active": "border-orange-500 shadow-[0_0_15px_rgba(255,140,0,0.2)]",
    "status/reading": "border-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.2)]"
}

TYPE_ICONS = {
    "type/author": "👤",
    "type/concept": "⚛️",
    "type/daily-bridge": "📅",
    "type/source": "📖",
    "type/discipline": "🧠",
    "type/project": "🚀"
}

# ==============================================================================
# 🧠 EXTRACTION LOGIC (The Brain)
# ==============================================================================

def parse_frontmatter(content):
    """Extracts YAML metadata (tags, publish status)."""
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "status/seed"}
    
    # Check if file starts with YAML
    if not content.startswith("---"):
        return meta
        
    try:
        # Split by the second '---'
        parts = content.split("---", 2)
        if len(parts) < 3: return meta
        
        yaml_text = parts[1]
        
        # Check Publish
        if "publish: true" in yaml_text:
            meta["publish"] = True
            
        # Extract Tags (Simple search to avoid external libraries)
        # Looks for "- type/..." or "- status/..."
        meta["tags"] = re.findall(r'[\s-](type/[\w-]+|status/[\w-]+)', yaml_text)
        
        # Determine Primary Type and Status
        for tag in meta["tags"]:
            if tag.startswith("type/"): meta["type"] = tag
            if tag.startswith("status/"): meta["status"] = tag
            
    except Exception as e:
        print(f"⚠️ YAML Parse Error: {e}")
        
    return meta

def extract_features(content, note_type, title):
    """Surgically removes specific data based on note type."""
    blurb = "Click to access neural node."
    extra_html = ""
    
    # --- LOGIC: DAILY BRIDGE ---
    if note_type == "type/daily-bridge":
        # clean title from [[Date]]
        title = title.replace('[', '').replace(']', '')
        
        # Extract Summary
        summary_match = re.search(r'\*\*📝 BRIEF SUMMARY:\*\*\s*\n>\s*(.*)', content)
        if summary_match:
            blurb = summary_match.group(1)[:150] + "..."
            
        # Extract Concepts (The Pill Tags)
        concepts = re.findall(r'\*\s*\*\*Concept:\*\*\s*\[\[(.*?)\]\]', content)
        if concepts:
            tags_html = "".join([f'<span class="text-[10px] bg-white/10 px-2 py-1 rounded text-aurelia-cyan border border-aurelia-cyan/20">{c}</span>' for c in concepts[:3]])
            extra_html = f'<div class="flex flex-wrap gap-2 mt-3">{tags_html}</div>'

    # --- LOGIC: AUTHOR ---
    elif note_type == "type/author":
        title = title.replace('👤', '').strip()
        # Extract Profile
        profile_match = re.search(r'### 📝 Profile & Context\s*\n>\s*(.*)', content)
        if profile_match:
            blurb = profile_match.group(1)[:120] + "..."

    # --- LOGIC: CONCEPT ---
    elif note_type == "type/concept":
        title = title.replace('⚛️', '').strip()
        # Extract Definition
        def_match = re.search(r'### 💡 Definition\s*\n>\s*(.*)', content)
        if def_match:
            blurb = def_match.group(1)[:120] + "..."

    # --- LOGIC: SOURCE (Book) ---
    elif "type/source" in note_type:
        title = title.replace('📖', '').strip()
        # Extract Author
        auth_match = re.search(r'\*\*👤 Author:\*\*\s*\[\[(.*?)\]\]', content)
        if auth_match:
            extra_html = f'<div class="text-xs text-aurelia-cyan mb-2">by {auth_match.group(1)}</div>'
        
        # Extract Thesis
        thesis_match = re.search(r'### 💡 The Core Argument.*\s*\n>\s*(.*)', content)
        if thesis_match:
            blurb = thesis_match.group(1)[:120] + "..."

    # --- LOGIC: DISCIPLINE ---
    elif note_type == "type/discipline":
        title = title.replace('🧠', '').strip()
        scope_match = re.search(r'### 🧐 Definition.*\s*\n>\s*(.*)', content)
        if scope_match:
            blurb = scope_match.group(1)[:120] + "..."

    return title, blurb, extra_html

# ==============================================================================
# 🚀 MAIN BUILD ENGINE
# ==============================================================================

def build_garden():
    print("🔄 AURELIA SYSTEM: Initiating Recursive Vault Scan...")
    
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ CRITICAL: {TEMPLATE_FILE} missing.")
        return

    cards_html = ""
    files_processed = 0

    # 1. RECURSIVE CRAWLER (The Upgrade)
    # os.walk goes into every subfolder automatically
    for root, dirs, files in os.walk(VAULT_PATH):
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 2. PARSE METADATA
                meta = parse_frontmatter(content)
                
                # The Gatekeeper
                if not meta["publish"]: 
                    continue
                
                files_processed += 1
                
                # 3. EXTRACT CONTENT
                raw_title = filename.replace('.md', '')
                clean_title, blurb, extra = extract_features(content, meta["type"], raw_title)
                
                # Visuals
                css_border = STATUS_COLORS.get(meta["status"], STATUS_COLORS["status/seed"])
                icon = TYPE_ICONS.get(meta["type"], "📄") # Default icon if unknown
                
                # 4. GENERATE CARD HTML
                card = f"""
                <article class="glass p-6 rounded-lg border {css_border} group relative overflow-hidden transition-all hover:scale-[1.02] hover:bg-white/5 cursor-pointer flex flex-col h-full">
                    <div class="absolute top-0 right-0 p-4 opacity-20 text-5xl font-mono group-hover:opacity-40 transition-opacity">{icon}</div>
                    
                    <div class="flex items-center gap-2 mb-4">
                        <span class="text-[10px] font-mono tracking-widest uppercase text-gray-500 border border-gray-700 px-2 rounded">{meta['type'].replace('type/', '')}</span>
                    </div>

                    <h3 class="text-xl font-bold text-white mb-2 z-10 relative">{clean_title}</h3>
                    {extra}
                    <p class="text-sm text-gray-400 leading-relaxed z-10 relative flex-grow">{blurb}</p>
                </article>
                """
                cards_html += card

    print(f"🔎 Scanned deeply. Found {files_processed} publishable notes.")

    # 5. INJECT INTO TEMPLATE
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template_content = f.read()

    if TARGET_MARKER in template_content:
        final_html = template_content.replace(TARGET_MARKER, cards_html)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(final_html)
        print(f"✅ SUCCESS: {OUTPUT_FILE} Generated. System Online.")
    else:
        print(f"❌ ERROR: Could not find target marker in {TEMPLATE_FILE}")

if __name__ == "__main__":
    build_garden()