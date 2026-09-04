"""Asset housekeeping: drop-zone sorting and vault/system asset syncing into dist/."""
import os
import shutil
import subprocess
from pathlib import Path

from engine.config import OUTPUT_DIR, ROOT_DIR, VAULT_PATH
from engine.paths import escapes, is_link

# Gemini Notebook audio exports run 30-80MB+ each and go straight into git,
# which never shrinks on its own. Rather than rewriting existing history
# (risky, needs a force-push), new audio above this size gets compressed on
# the way out of the drop zone -- capping growth going forward without
# touching what's already committed. 64k mono is a standard podcast/
# spoken-word target and typically cuts these files by 50-70%; Gemini
# Notebook's two-host dialogue exports don't rely on stereo separation, so
# mono isn't a perceptible loss here.
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

# Repo-root assets/ subfolders that may be published. An allowlist, not a
# list of known-bad names: prepare_dist() copies into dist/, dist/ is what
# GitHub Pages serves, and a subfolder added later would otherwise be
# published by default -- silently, and at the moment CI next runs.
#
# It mirrors sync_vault_assets()'s media kinds below, plus the two folders
# holding the site's own front-end code. The codebase already knew filtering
# was needed here; it was just applied on the vault path only.
#
# `docs` is why this is not hypothetical. assets/docs/ is the second path
# that held the author's resume in 2026-08, when an unfiltered copytree
# served it (alongside a transcript, IRB paperwork and coursework) live from
# the Pages site -- see CLAUDE.md, "Recent history" item 9. The folder still
# exists, empty. It is gitignored now as well, and both halves are needed:
# .gitignore does nothing about a file already committed, and this list does
# nothing about a file already public in the repo.
PUBLISHABLE_ASSET_DIRS = frozenset({"css", "js", "images", "audio", "video", "flashcards"})


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


def _copy_contained_tree(src, dst, base_resolved):
    """Copies src/ into dst/, refusing any entry that leaves base_resolved.

    shutil.copytree() cannot be used here. It follows a directory junction
    and copies the *target's* contents into dist/, and its symlinks=True
    option is no help, because a junction is not a symlink -- os.path.islink()
    is False for one (see engine/paths.py). dist/ is what GitHub Pages
    serves, so "copy whatever this link points at" hands the decision about
    what goes on the internet to whoever planted the link.

    Links are skipped outright rather than followed-and-checked, even when
    they resolve back inside the tree: assets/ contains none, following one
    buys nothing, and a junction aimed at an ancestor would recurse until
    the path length gave out. `escapes()` stays as the backstop for anything
    is_link() cannot recognize on an older interpreter.
    """
    os.makedirs(dst, exist_ok=True)
    for entry in sorted(os.listdir(src)):
        source = os.path.join(src, entry)
        target = os.path.join(dst, entry)

        if is_link(source) or escapes(source, base_resolved):
            print(f"   ⚠️  Not published (link, or resolves outside assets/): {source}")
            continue

        if os.path.isdir(source):
            _copy_contained_tree(source, target, base_resolved)
        elif os.path.isfile(source):
            shutil.copy2(source, target)


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
    if not os.path.isdir(src_assets):
        return

    os.makedirs(dst_assets, exist_ok=True)
    assets_root = Path(src_assets).resolve()
    copied, withheld = [], []
    for entry in sorted(os.listdir(src_assets)):
        src = os.path.join(src_assets, entry)
        # Case-folded because NTFS is case-insensitive and its casing is
        # sticky: a folder first created as `CSS/` keeps that name forever.
        # Folding an *allowlist* can only keep a legitimately-named folder
        # working -- `Docs/` still isn't `docs`, so nothing new is admitted.
        if entry.casefold() in PUBLISHABLE_ASSET_DIRS and os.path.isdir(src) and not is_link(src):
            _copy_contained_tree(src, os.path.join(dst_assets, entry), assets_root)
            copied.append(entry)
        else:
            withheld.append(entry)

    print(f"   + System assets copied: {', '.join(copied) if copied else '(none)'}")
    if withheld:
        # Named rather than silently dropped: someone who put a file here
        # expecting it on the site needs to see why it isn't.
        print(f"   > Withheld from dist/ (not a publishable asset folder): {', '.join(withheld)}")


def sync_vault_assets():
    """Copies media from vault/assets into dist/assets."""
    print("\n🔄 SYNCING ASSETS: Vault -> Dist...")
    source_root = os.path.join(VAULT_PATH, "assets")
    public_root = os.path.join(OUTPUT_DIR, "assets")

    if not os.path.exists(source_root):
        return

    # Same containment rule as prepare_dist(): os.path.isfile() follows a
    # link, so without this a single symlink or junction dropped into
    # vault/assets/audio/ publishes whatever it points at.
    assets_root = Path(source_root).resolve()

    for folder in ["audio", "video", "images", "flashcards"]:
        src = os.path.join(source_root, folder)
        dst = os.path.join(public_root, folder)
        os.makedirs(dst, exist_ok=True)

        if os.path.exists(src):
            for f in sorted(os.listdir(src)):
                s_file = os.path.join(src, f)
                if is_link(s_file) or escapes(s_file, assets_root):
                    print(f"   ⚠️  Not published (link, or resolves outside vault/assets/): {s_file}")
                    continue
                if os.path.isfile(s_file):
                    shutil.copy2(s_file, os.path.join(dst, f))

    print("   + Assets synced.")
