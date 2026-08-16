import os
import json
import shutil
import time

# --- 1. CONFIGURATION ---
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR_NAME = "Aurelia_Factory_v1"
TARGET_DIR = os.path.join(SOURCE_DIR, TARGET_DIR_NAME)

# --- 2. THE "WHITE LABEL" IDENTITY ---
# This config allows the client to toggle modules easily.
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
    ],
    "modules": {
        "garden": { "enabled": True, "desc": "The main knowledge graph." },
        "projects": { "enabled": True, "desc": "Active work dossiers." },
        "protocols": { "enabled": True, "desc": "Standard Operating Procedures." },
        "notebooklm": { "enabled": True, "desc": "AI Research Synthesis." },
        "transmissions": { "enabled": False, "desc": "Podcast/Video feed." }
    }
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
        f"{TARGET_DIR}/vault/20_PROTOCOL",
        f"{TARGET_DIR}/vault/30_PROJECTS",
        f"{TARGET_DIR}/vault/40_TRANSMISSIONS",
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

    # --- A. DEMO PROJECT ---
    project_md = """---
type: project
publish: true
status: active
role: Lead Researcher
tech_stack: [Python, AI, Data]
---
# 🚨 Mission Brief
**Objective:** This is a sample project card. Use this to track active research grants, book drafts, or software builds.

# 🛠️ Architecture
**Core Logic:** The 'Project' card type is designed for high-level overviews.
- **Status Indicators:** Change 'status: active' to 'archived' in the YAML to change the visual indicator.
- **Tech Stack:** The tags in the YAML appear as chips on the card.

# ⚡ Operational Impact
- **Efficiency:** Centralized tracking.
- **Visibility:** Public-facing portfolio ready.
"""
    with open(os.path.join(TARGET_DIR, "vault", "30_PROJECTS", "00_Demo_Project.md"), "w", encoding="utf-8") as f:
        f.write(project_md)

    # --- B. DEMO PROTOCOL ---
    protocol_md = """---
type: protocol
publish: true
id: PROT_001
tags: [system, onboarding]
---
# ⚙️ SYSTEM_ONBOARDING
## 📋 The Sequence
- [ ] Install VS Code and Python.
- [ ] Open 'user_config.json' and update your Bio.
- [ ] Drop your personal photo into 'assets/images/'.
- [ ] Run 'python build.py' to deploy the site.

## 🧠 System Logic
> Protocols are 'Standard Operating Procedures'. Use them to document repeatable workflows (e.g., Grading Process, Grant Submission).
"""
    with open(os.path.join(TARGET_DIR, "vault", "20_PROTOCOL", "00_Onboarding.md"), "w", encoding="utf-8") as f:
        f.write(protocol_md)

    # --- C. DEMO NOTEBOOKLM (With Flashcards & References) ---
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

## 🧩 Modules
- **Projects:** Place `.md` files in `vault/30_PROJECTS`.
- **Protocols:** Place `.md` files in `vault/20_PROTOCOL`.
- **NotebookLM:** Use the `type: notebooklm` frontmatter (see demo).
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