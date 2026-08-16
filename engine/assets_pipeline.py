"""Asset housekeeping: drop-zone sorting and vault/system asset syncing into dist/."""
import os
import shutil
from datetime import date, datetime

from engine.config import OUTPUT_DIR, ROOT_DIR, VAULT_PATH


def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def organize_assets():
    """Scans vault/99_DROP_ZONE and moves files to their correct assets/ subfolder
    based on file extension."""
    print("\n🧹 SYSTEM CLEANUP: Scanning Drop Zone...")

    drop_zone = os.path.join(VAULT_PATH, "99_DROP_ZONE")
    assets_root = os.path.join(VAULT_PATH, "assets")

    destinations = {
        "images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"],
        "audio": [".mp3", ".wav", ".m4a", ".ogg"],
        "video": [".mp4", ".mov", ".webm"],
        "flashcards": [".csv"],
        "documents": [".pdf", ".txt"],
    }

    if not os.path.exists(drop_zone):
        os.makedirs(drop_zone)
        print("   + Created 99_DROP_ZONE")
        return

    files = [f for f in os.listdir(drop_zone) if os.path.isfile(os.path.join(drop_zone, f))]
    if not files:
        print("   > Drop Zone empty. No assets to sort.")
        return

    moved_count = 0
    for f in files:
        _, ext = os.path.splitext(f)
        ext = ext.lower()

        target_folder = next((folder for folder, exts in destinations.items() if ext in exts), None)
        if not target_folder:
            print(f"   ! [SKIPPED] Unknown type: {f}")
            continue

        src_path = os.path.join(drop_zone, f)
        dest_dir = os.path.join(assets_root, target_folder)
        dest_path = os.path.join(dest_dir, f)

        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(src_path, dest_path)
        print(f"   + [MOVED] {f} -> assets/{target_folder}/")
        moved_count += 1

    print(f"   > Organization Complete. Sorted {moved_count} files.")


def prepare_dist():
    """Creates the clean dist folder and copies system assets (CSS/JS/images)."""
    print(f"\n📦 INITIALIZING BUILD TARGET: {OUTPUT_DIR}...")

    # Safety interlock: refuse to run if OUTPUT_DIR was ever misconfigured to the
    # project root, since prepare_dist() wipes it before rebuilding.
    if os.path.abspath(OUTPUT_DIR) == os.path.abspath(ROOT_DIR):
        print("\n🛑 EMERGENCY STOP: OUTPUT_DIR is pointing to the Root Directory.")
        print("   Fix 'OUTPUT_DIR' in engine/config.py to be a subfolder (e.g. 'dist').")
        raise SystemExit(1)

    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR)
        except OSError as e:
            print(f"   ⚠️  Warning: Could not fully wipe dist folder (File in use?): {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    src_assets = os.path.join(ROOT_DIR, "assets")
    dst_assets = os.path.join(OUTPUT_DIR, "assets")
    if os.path.exists(src_assets):
        shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)
        print("   + System assets copied.")


def sync_vault_assets():
    """Copies media from vault/assets into dist/assets."""
    print("\n🔄 SYNCING ASSETS: Vault -> Dist...")
    source_root = os.path.join(VAULT_PATH, "assets")
    public_root = os.path.join(OUTPUT_DIR, "assets")

    if not os.path.exists(source_root):
        return

    for folder in ["audio", "video", "images", "flashcards"]:
        src = os.path.join(source_root, folder)
        dst = os.path.join(public_root, folder)
        os.makedirs(dst, exist_ok=True)

        if os.path.exists(src):
            for f in os.listdir(src):
                s_file = os.path.join(src, f)
                if os.path.isfile(s_file):
                    shutil.copy2(s_file, os.path.join(dst, f))

    print("   + Assets synced.")
