import os
import json
import shutil
import time

# --- 1. CONFIGURATION ---
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR_NAME = "Aurelia_Factory_v1"
TARGET_DIR = os.path.join(SOURCE_DIR, TARGET_DIR_NAME)

# --- 2. THE "WHITE LABEL" IDENTITY ---
# Ships a Garden + Lobby product -- matches what engine/ actually builds.
FACTORY_CONFIG = {
    "system_name": "AURELIA // OS",
    "system_version": "v1.0.0 (Factory)",
    "status_message": "System_Online",
    "author": {
        "name": "[INSERT NAME]",
        "short_name": "USR",
        "role": "[INSERT ROLE]",
        "email": "user@university.edu",
        "location": "Global",
        "bio_short": "Digital Knowledge Management System.",
        "bio_long": "Aurelia OS is a local-first digital garden designed to augment biological cognition through structured data workflows."
    },
    "links": {
        "github": "https://github.com",
        "linkedin": "https://linkedin.com",
        "twitter": "https://twitter.com"
    },
    "tech_stack": [
        { "name": "Obsidian", "type": "SOFTWARE // VAULT", "desc": "Neural Core.", "icon": "💎" },
        { "name": "Zotero", "type": "RESEARCH // CITATION", "desc": "Reference Library.", "icon": "📚" },
        { "name": "Python", "type": "BACKEND // LOGIC", "desc": "Build Engine.", "icon": "🐍" }
    ]
}

def print_step(msg):
    print(f"   [+] {msg}")

def create_structure():
    print("🏗️  Constructing Architecture...")
    
    # Define the skeleton
    dirs = [
        TARGET_DIR,
        # The Vault
        f"{TARGET_DIR}/vault",
        f"{TARGET_DIR}/vault/00_LOBBY",
        f"{TARGET_DIR}/vault/10_GARDEN",
        f"{TARGET_DIR}/vault/assets",
        f"{TARGET_DIR}/vault/assets/images",
        f"{TARGET_DIR}/vault/assets/audio",
        f"{TARGET_DIR}/vault/assets/video",
        f"{TARGET_DIR}/vault/assets/flashcards",
        # The System
        f"{TARGET_DIR}/system",
        f"{TARGET_DIR}/system/templates",
        f"{TARGET_DIR}/system/templates/pages",
        # The Web Assets
        f"{TARGET_DIR}/assets",
        f"{TARGET_DIR}/assets/css",
        f"{TARGET_DIR}/assets/js",
        f"{TARGET_DIR}/assets/images"
    ]

    # Clean Slate Logic
    if os.path.exists(TARGET_DIR):
        print("   ⚠️  Target exists. wiping...")
        shutil.rmtree(TARGET_DIR)
        time.sleep(1) # Safety pause

    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    print_step(f"Skeleton created at: {TARGET_DIR_NAME}")

def copy_engine():
    print("⚙️  Cloning Logic Core...")

    # 1. Build Entrypoint + Engine Package (The Brain)
    shutil.copy(os.path.join(SOURCE_DIR, "build.py"), os.path.join(TARGET_DIR, "build.py"))
    shutil.copytree(
        os.path.join(SOURCE_DIR, "engine"),
        os.path.join(TARGET_DIR, "engine"),
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    print_step("build.py + engine/ installed.")

    # 2. Dependency manifests (build.py needs both a Python and a Node
    # toolchain -- Node compiles the Tailwind CSS, see engine/tailwind_build.py)
    shutil.copy(os.path.join(SOURCE_DIR, "requirements.txt"), os.path.join(TARGET_DIR, "requirements.txt"))
    shutil.copy(os.path.join(SOURCE_DIR, "package.json"), os.path.join(TARGET_DIR, "package.json"))
    lockfile = os.path.join(SOURCE_DIR, "package-lock.json")
    if os.path.exists(lockfile):
        shutil.copy(lockfile, os.path.join(TARGET_DIR, "package-lock.json"))
    print_step("requirements.txt + package.json installed.")

    # 3. Config (The Soul)
    with open(os.path.join(TARGET_DIR, "user_config.json"), "w", encoding="utf-8") as f:
        json.dump(FACTORY_CONFIG, f, indent=4)
    print_step("Clean user_config.json generated.")

def copy_frontend():
    print("🎨  Migrating UI/UX Assets...")
    
    # 1. Templates (HTML)
    # We copy the 'system/templates' folder recursively
    src_templates = os.path.join(SOURCE_DIR, "system/templates")
    dst_templates = os.path.join(TARGET_DIR, "system/templates")
    
    if os.path.exists(src_templates):
        # Remove empty dir created in step 1 to allow copytree
        shutil.rmtree(dst_templates) 
        shutil.copytree(src_templates, dst_templates)
        print_step("HTML Templates migrated.")
    else:
        print("   ❌ CRITICAL: 'system/templates' not found in source!")

    # 2. CSS & JS (Styles & Scripts)
    # We copy content, but NOT images (privacy)
    for asset_type in ["css", "js"]:
        src = os.path.join(SOURCE_DIR, f"assets/{asset_type}")
        dst = os.path.join(TARGET_DIR, f"assets/{asset_type}")
        if os.path.exists(src):
            shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print_step(f"Assets/{asset_type} migrated.")

def generate_blueprints():
    print("📝  Generating Blueprint Data...")

    # --- A. DEMO CONCEPT (the simplest garden note type -- a good first example) ---
    concept_md = """---
type: concept
publish: true
tags: [onboarding]
---
### Definition
> This is a sample Concept note. Use this note type for definitions, ideas, or
> terms you want to build a personal glossary of.

**🔗 Related:** Digital Garden, Zettelkasten

Change `type:` in the frontmatter to switch note types: `concept`, `source`,
`author`, `discipline`, `notebooklm` (see the NotebookLM demo below), or
`deep-dive` all render as different card layouts on the Garden page automatically.
"""
    with open(os.path.join(TARGET_DIR, "vault", "10_GARDEN", "00_Demo_Concept.md"), "w", encoding="utf-8") as f:
        f.write(concept_md)

    # --- B. DEMO NOTEBOOKLM (With Flashcards & References) ---
    # First, create the CSV
    csv_data = "Question,Answer\nWhat is NotebookLM?,An AI research assistant by Google.\nHow does Aurelia handle it?,It renders a dedicated dashboard with audio and flashcards.\nWhere do references go?,Paste Zotero APA citations in the Sources section."
    with open(os.path.join(TARGET_DIR, "vault", "assets", "flashcards", "demo_deck.csv"), "w", encoding="utf-8") as f:
        f.write(csv_data)

    notebook_md = """---
type: notebooklm
publish: true
status: active
tags: [research, AI]
created: 2026-01-01
---
# 📚 Lit Review Overview
> **This is a NotebookLM Card.** It is designed to house deep research. It supports Audio Overviews, Flashcard Decks (via CSV), and Mind Maps.

# 🎙️ Audio Overview
assets/audio/placeholder.mp3
*(Add an .mp3 file to vault/assets/audio to activate this player)*

# 🧠 Mind Map
assets/images/placeholder.png

# 🃏 Flashcards
assets/flashcards/demo_deck.csv

# 📚 Sources
> **References**
> - Aurelia Systems. (2026). *The Architecture of Digital Memory*.
> - Google Research. (2024). *NotebookLM Technical Report*.
"""
    with open(os.path.join(TARGET_DIR, "vault", "10_GARDEN", "NotebookLM_Demo.md"), "w", encoding="utf-8") as f:
        f.write(notebook_md)

    print_step("Blueprint Notes created.")

def create_readme():
    readme_text = """# AURELIA // OS [FACTORY EDITION]

## ✅ Prerequisites
- Python 3.10+
- Node.js 18+ (used to compile the site's Tailwind CSS)
- ffmpeg (optional) -- if installed, large audio files dropped into
  `vault/99_DROP_ZONE` get auto-compressed before publishing. Without it,
  they're just copied as-is.

## 🚀 Quick Start
1. **Install dependencies (once):**
   ```
   pip install -r requirements.txt
   npm install
   ```
2. **Configure:** Open `user_config.json` and add your Name, Role, and Bio.
3. **Build:** Open a terminal and run `python build.py`.
4. **View:** Open `dist/index.html` in your browser.

## 📂 Folder Structure
- `vault/`: Your Obsidian Notes go here.
- `system/`: The HTML templates (Do not touch unless customizing).
- `assets/`: CSS, JS, and Images.
- `engine/`: The build logic (Do not touch unless customizing).
- `dist/`: Generated output -- this is what you publish/deploy. Rebuilt
  from scratch every time you run `python build.py`; don't edit it by hand.

## 🧩 Product
This edition ships two pages: the Lobby (`index.html`) and the Garden
(`garden.html`), your knowledge base. Every published note in `vault/`
becomes a card there. Set `type:` in a note's frontmatter to choose its card
layout:
- **concept** -- definitions, ideas, terms (see demo)
- **source** -- books, articles, papers you're drawing on
- **author** -- profiles of people whose work you cite
- **discipline** -- fields of study
- **notebooklm** -- Google NotebookLM exports, with Audio Overview, Flashcard
  (CSV), and Mind Map support (see demo)
- **deep-dive** -- long-form explainers pasted in whole rather than filled in
  piecemeal; the card pulls a premise line and a summary excerpt automatically
- anything else (or no `type:` at all) renders as a plain note card

A note only appears on the site once its frontmatter has `publish: true`.
"""
    with open(os.path.join(TARGET_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_text)

def main():
    print("\n💠 INITIATING AURELIA FACTORY DEPLOYMENT 💠")
    print("==========================================")
    
    create_structure()
    copy_engine()
    copy_frontend()
    generate_blueprints()
    create_readme()
    
    print("==========================================")
    print("✅  CLONE COMPLETE.")
    print(f"📦  Product ready at: ./{TARGET_DIR_NAME}")
    print("👉  NEXT STEP: Zip this folder and send to client.")

if __name__ == "__main__":
    main()