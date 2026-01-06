import os
import shutil
import json
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_NAME = "AURELIA_GENESIS_v3"
DIST_DIR = os.path.join(SOURCE_DIR, "dist_build")

# FILES TO COPY (The Structure)
INCLUDE_FILES = [
    "build.py",
    "user_config_dist.json", # We will rename this to user_config.json later
    "requirements.txt"       # If you have one, otherwise remove
]

INCLUDE_DIRS = [
    "system",
    "assets"
]

def clean_build_dir():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)
    print(f"🧹 Cleaned build directory: {DIST_DIR}")

def copy_structure():
    print("🧬 Replicating System Core...")
    
    # 1. Copy Folders (Templates, CSS, JS)
    for folder in INCLUDE_DIRS:
        src = os.path.join(SOURCE_DIR, folder)
        dst = os.path.join(DIST_DIR, folder)
        if os.path.exists(src):
            shutil.copytree(src, dst)
            print(f"   -> Cloned: {folder}/")

    # 2. Copy Root Files (Engine)
    for file in INCLUDE_FILES:
        src = os.path.join(SOURCE_DIR, file)
        if os.path.exists(src):
            shutil.copy(src, DIST_DIR)
            print(f"   -> Cloned: {file}")

def setup_identity():
    print("🆔 Injecting Factory Identity...")
    # Rename dist config to actual config
    dist_config = os.path.join(DIST_DIR, "user_config_dist.json")
    final_config = os.path.join(DIST_DIR, "user_config.json")
    
    if os.path.exists(dist_config):
        os.rename(dist_config, final_config)
        print("   -> Identity Chip Installed (user_config.json)")
    else:
        print("   ⚠️ WARNING: user_config_dist.json missing!")

def create_dummy_vault():
    print("🧠 Initializing Clean Vault...")
    vault_root = os.path.join(DIST_DIR, "vault")
    os.makedirs(vault_root)
    
    structure = {
        "00_GARDEN": "# 00_Start_Here\n\nWelcome to your Digital Garden. Add markdown files here.",
        "10_PROJECTS": "---\ntype: project\nstatus: active\nrole: Architect\n---\n# Demo Project\n\nThis is a template project.",
        "20_PROTOCOL": "---\ntype: protocol\nid: PROT_01\ntags: [demo]\n---\n# Morning Protocol\n\n- [ ] Wake up\n- [ ] Execute Code",
        "30_SERVICES": "---\ntype: service\nprice: $99\n---\n# System Architecture\n\nWe build digital brains."
    }

    for folder, content in structure.items():
        path = os.path.join(vault_root, folder)
        os.makedirs(path)
        with open(os.path.join(path, "README.md"), "w") as f:
            f.write(content)
        print(f"   -> Created: vault/{folder}")

def create_zip():
    print("📦 Compressing Asset...")
    zip_filename = f"{BUILD_NAME}_{datetime.now().strftime('%Y%m%d')}.zip"
    zip_path = os.path.join(SOURCE_DIR, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DIST_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DIST_DIR)
                zipf.write(file_path, arcname)
                
    print(f"\n✅ DEPLOYMENT COMPLETE: {zip_filename}")
    print(f"   Location: {zip_path}")
    
    # Cleanup (Optional: remove the temp folder to keep things clean)
    # shutil.rmtree(DIST_DIR)

if __name__ == "__main__":
    print("--- AURELIA REPLICATOR PROTOCOL ---")
    clean_build_dir()
    copy_structure()
    setup_identity()
    create_dummy_vault()
    create_zip()