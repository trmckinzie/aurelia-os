import os
import re
import html

# CONFIGURATION
VAULT_PATH = "./vault"
TEMPLATE_FILE = "template.html"
OUTPUT_FILE = "garden.html"
CARD_TARGET = '<!-- CARDS_INJECTION_POINT -->'
DATA_TARGET = '<!-- DATA_INJECTION_POINT -->'

def parse_frontmatter(content):
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "status/seed"}
    
    if not content.startswith("---"): return meta
    try:
        parts = content.split("---", 2)
        if len(parts) < 3: return meta
        yaml_text = parts[1]
        
        # STRICT GATEKEEPER CHECK: Publish ONLY if "publish: true" is explicit
        if "publish: true" in yaml_text.lower():
             meta["publish"] = True
        
        meta["tags"] = re.findall(r'[\s-](type/[\w-]+|status/[\w-]+)', yaml_text)
        for tag in meta["tags"]:
            if tag.startswith("type/"): meta["type"] = tag
            if tag.startswith("status/"): meta["status"] = tag
    except: pass
    return meta

def extract_specifics(content, note_type, title):
    blurb = "..."
    extra_html = ""
    icon = "📄"
    color_class = "border-gray-800"
    type_label = "Node"
    clean_title = title.replace(".md", "")
    body_text = content.split("---", 2)[-1].strip() if "---" in content else content

    # --- TYPE MAPPING LOGIC ---
    if "type/daily-bridge" in note_type:
        icon = "📅"
        color_class = "border-l-aurelia-orange"
        type_label = "Daily_Log"
        clean_title = clean_title.replace("[[", "").replace("]]", "") 
        
        summary_match = re.search(r'\*\*📝 BRIEF SUMMARY:\*\*\s*\n>\s*(.*)', content)
        if summary_match: blurb = summary_match.group(1)[:180] + "..."
        
        concepts = re.findall(r'\*\s*\*\*Concept:\*\*\s*\[\[(.*?)\]\]', content)
        tags_html = ""
        for c in concepts[:3]: 
            c_name = c.split("|")[0] 
            tags_html += f'<span class="text-[9px] font-mono px-1.5 py-0.5 bg-aurelia-orange/10 text-aurelia-orange border border-aurelia-orange/20 rounded">{c_name}</span>'
        
        extra_html = f'<div class="mt-auto pt-4 flex items-center justify-between border-t border-gray-800/50"><div class="flex gap-2 flex-wrap">{tags_html}</div><span class="text-[9px] font-mono text-gray-600 group-hover:text-aurelia-orange">OPEN_FILE -></span></div>'

    elif "type/concept" in note_type:
        icon = "⚛️"
        color_class = "border-l-aurelia-cyan"
        type_label = "Concept_Node"
        
        def_match = re.search(r'### 💡 Definition\s*\n>\s*(.*)', content)
        if def_match: blurb = def_match.group(1)[:180] + "..."
        
        related_match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', content)
        links_html = ""
        if related_match:
            raw_links = related_match.group(1)
            links = re.findall(r'\[\[(.*?)\]\]', raw_links)
            for l in links[:3]:
                l_name = l.split("|")[0]
                links_html += f'<span class="hover:text-white transition-colors">→ {l_name}</span>'
        
        extra_html = f'<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-[9px] text-aurelia-cyan font-mono mb-2 opacity-70">LINKED_TO:</div><div class="flex gap-3 text-[10px] text-gray-500 font-mono flex-wrap">{links_html}</div></div>'

    elif "type/author" in note_type:
        icon = "👤"
        color_class = "border-l-white"
        type_label = "Author_Profile"
        
        prof_match = re.search(r'### 📝 Profile & Context\s*\n>\s*(.*)', content)
        if prof_match: blurb = prof_match.group(1)[:180] + "..."
        
        works_html = ""
        if "### 📚 Key Works" in content:
            parts = content.split("### 📚 Key Works (In Vault)")
            if len(parts) > 1:
                lines = parts[1].strip().split('\n')
                count = 0
                for line in lines:
                    if line.strip().startswith("*") and count < 2:
                        work_name = line.replace("*", "").replace("[[", "").replace("]]", "").strip()
                        works_html += f'<li class="flex items-center gap-2"><span class="text-aurelia-green">●</span> {work_name}</li>'
                        count += 1
        
        extra_html = f'<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-[9px] font-mono text-gray-500 mb-1">KEY WORKS:</div><ul class="text-[10px] font-mono text-gray-500 space-y-1">{works_html}</ul></div>'

    elif "type/source" in note_type:
        icon = "📖"
        color_class = "border-l-yellow-500"
        type_label = "Source_Text"
        
        thesis_match = re.search(r'### 💡 The Core Argument.*\s*\n>\s*(.*)', content)
        if thesis_match: blurb = thesis_match.group(1)[:180] + "..."
        
        auth_name = "UNKNOWN"
        auth_match = re.search(r'\*\*👤 Author:\*\*\s*\[\[(.*?)\]\]', content)
        if auth_match: auth_name = auth_match.group(1).upper()
        
        extra_html = f'<div class="mt-auto pt-4 flex justify-between items-center border-t border-gray-800/50"><div class="text-[9px] font-mono text-gray-500">AUTH: {auth_name}</div><span class="px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-500 text-[9px] font-mono border border-yellow-500/20">READING</span></div>'

    elif "type/discipline" in note_type:
        icon = "🧠"
        color_class = "border-l-aurelia-green"
        type_label = "Discipline"
        
        scope_match = re.search(r'### 🧐 Definition.*\s*\n>\s*(.*)', content)
        if scope_match: blurb = scope_match.group(1)[:180] + "..."
        
        bricks_html = ""
        if "### 🔑 Core Concepts" in content:
            parts = content.split("### 🔑 Core Concepts (The Bricks)")
            if len(parts) > 1:
                lines = parts[1].strip().split('\n')
                count = 0
                for line in lines:
                    if line.strip().startswith("*") and count < 3:
                        brick_name = line.replace("*", "").replace("[[", "").replace("]]", "").strip()
                        bricks_html += f'<span class="px-2 py-1 bg-white/5 rounded border border-white/5">{brick_name}</span>'
                        count += 1
        
        extra_html = f'<div class="mt-auto pt-4 border-t border-gray-800/50"><div class="text-[9px] text-aurelia-green font-mono mb-2 opacity-70">CORE_BRICKS:</div><div class="flex gap-2 text-[10px] text-gray-500 font-mono flex-wrap">{bricks_html}</div></div>'

    else:
        extra_html = '<div class="mt-auto pt-4 border-t border-gray-800/50"></div>'

    return clean_title, blurb, extra_html, body_text, icon, color_class, type_label

def build_garden():
    print("🔄 AURELIA SYSTEM: Building Production Grid...")
    
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ CRITICAL: {TEMPLATE_FILE} missing.")
        return

    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template_content = f.read()

    try:
        card_split_index = template_content.index(CARD_TARGET)
        data_split_index = template_content.index(DATA_TARGET)
    except ValueError:
        print("❌ ERROR: Injection targets not found in template.html")
        return

    print("   Streaming Cards...")
    
    cards_html = ""
    hidden_data_html = ""
    file_count = 0
    
    for root, dirs, files in os.walk(VAULT_PATH):
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # CHECK PUBLISH FLAG
                meta = parse_frontmatter(content)
                if not meta["publish"]: continue
                
                file_count += 1
                note_id = f"note-{file_count}"
                
                title, blurb, extra, body, icon, color, label = extract_specifics(content, meta["type"], filename)
                type_clean = meta['type'].replace('type/', '')
                search_string = f"{title} {blurb} {type_clean}".lower()
                hover_border = color.replace("border-l-", "hover:border-r-") + "/50" if "white" not in color else "hover:border-r-white/50"

# --- MODIFIED LOGIC FOR FULL BORDERS ---
                # 1. Convert "border-l-color" to just "border-color" for the full box
                full_border_color = color.replace("border-l-", "border-")
                
                # 2. Update the HTML structure
                card = f"""
                <article 
                    onclick="openNote('{note_id}')" 
                    data-type="{type_clean}"
                    data-search="{search_string}"
                    class="searchable-item glass p-6 rounded-sm border-2 {full_border_color} border-opacity-60 hover:border-opacity-100 cursor-pointer flex flex-col gap-4 transition-all duration-300 hover:scale-[1.12] hover:z-10 group min-h-[320px]">
                    
                    <div class="flex justify-between items-start">
                        <div>
                            <div class="flex items-center gap-2 mb-2">
                                <span class="w-1.5 h-1.5 {color.replace('border-l-', 'bg-')} rounded-full"></span>
                                <span class="text-[16px] font-mono {color.replace('border-l-', 'text-')} uppercase tracking-widest">{label}</span>
                            </div>
                            <h3 class="text-5xl font-bold text-white font-mono group-hover:text-white transition-colors leading-tight">{title}</h3>
                        </div>
                        <div class="text-5xl filter drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] transition-transform group-hover:scale-110">{icon}</div>
                    </div>

                    <div class="w-full h-px bg-gray-800/50"></div>

                   <p class="text-large text-gray-100 leading-relaxed font-normal line-clamp-5">
    {blurb}
</p>


                    {extra}
                </article>
                """
                cards_html += card
                safe_body = html.escape(body)
                hidden_data_html += f'<div id="{note_id}" class="hidden">{safe_body}</div>\n'

    final_html = (
        template_content[:card_split_index] + 
        cards_html + 
        template_content[card_split_index + len(CARD_TARGET):data_split_index] + 
        hidden_data_html + 
        template_content[data_split_index + len(DATA_TARGET):]
    )

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write(final_html)

    print(f"✅ SUCCESS: {OUTPUT_FILE} Generated with {file_count} nodes.")

if __name__ == "__main__":
    build_garden()