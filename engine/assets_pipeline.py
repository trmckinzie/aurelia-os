"""Asset housekeeping: drop-zone sorting and vault/system asset syncing into dist/."""
import os
import shutil
import subprocess
from datetime import date, datetime

from engine.config import OUTPUT_DIR, ROOT_DIR, VAULT_PATH

# NotebookLM audio exports run 30-80MB+ each and go straight into git, which
# never shrinks on its own. Rather than rewriting existing history (risky,
# needs a force-push), new audio above this size gets compressed on the way
# out of the drop zone -- capping growth going forward without touching what's
# already committed. 64k mono is a standard podcast/spoken-word target and
# typically cuts these files by 50-70%; NotebookLM's two-host dialogue exports
# don't rely on stereo separation, so mono isn't a perceptible loss here.
_AUDIO_COMPRESS_THRESHOLD_BYTES = 15 * 1024 * 1024
_AUDIO_TARGET_BITRATE = "64k"

# Codec is set explicitly per extension rather than left to ffmpeg's
# output-extension guessing, which defaults to uncompressed PCM for .wav --
# silently producing a *larger* "compressed" file. Formats not listed here
# just skip compression and get copied as-is (see _compress_audio).
_AUDIO_CODEC_ARGS = {
    ".m4a": ["-c:a", "aac"],
    ".mp3": ["-c:a", "libmp3lame"],
}


def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def _compress_audio(src_path, dest_path, ext):
    """Re-encodes src_path to a smaller mono file at dest_path.

    Returns True if dest_path now holds a valid, smaller compressed file.
    Returns False (leaving dest_path untouched) if the format isn't one we
    know how to safely compress, ffmpeg isn't installed, or the encode
    failed or didn't actually save space -- callers fall back to a plain
    copy/move in that case, so this is always safe to attempt.
    """
    codec_args = _AUDIO_CODEC_ARGS.get(ext)
    if codec_args is None:
        return False

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", src_path, "-ac", "1", "-b:a", _AUDIO_TARGET_BITRATE, *codec_args, dest_path],
            capture_output=True, text=True, timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    if result.returncode != 0 or not os.path.exists(dest_path):
        return False

    if os.path.getsize(dest_path) >= os.path.getsize(src_path):
        os.remove(dest_path)  # didn't help; let the caller fall back to a plain copy
        return False

    return True


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

        if target_folder == "audio" and os.path.getsize(src_path) > _AUDIO_COMPRESS_THRESHOLD_BYTES:
            original_mb = os.path.getsize(src_path) / 1_048_576
            if _compress_audio(src_path, dest_path, ext):
                os.remove(src_path)
                saved_mb = original_mb - os.path.getsize(dest_path) / 1_048_576
                print(f"   + [COMPRESSED] {f} -> assets/audio/ ({original_mb:.0f}MB -> saved {saved_mb:.0f}MB)")
                moved_count += 1
                continue
            print(f"   ! [NOTE] {f} ({original_mb:.0f}MB) copied uncompressed -- "
                  f"install ffmpeg for automatic compression of large audio.")

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
