"""Asset housekeeping: the drop-zone sort, the site's own assets into dist/, and the
media publish gate (a media file ships only when a published note references it)."""
import os
import shutil
import subprocess
from pathlib import Path

from engine.buildlog import warn
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
# It names the media kinds publish_referenced_media() gates below, plus the
# folders holding the site's own front-end code and images. The codebase
# already knew filtering was needed here; it was just applied on the vault
# path only.
#
# `docs` is why this is not hypothetical. assets/docs/ is the second path
# that held the author's resume in 2026-08, when an unfiltered copytree
# served it (alongside a transcript, IRB paperwork and coursework) live from
# the Pages site -- see docs/DECISIONS.md item 9. The folder still
# exists, empty. It is gitignored now as well, and both halves are needed:
# .gitignore does nothing about a file already committed, and this list does
# nothing about a file already public in the repo.
# Two halves. SITE_ASSET_DIRS hold the site's own front-end code and images
# (the headshot, the social preview) and are copied whole. REPO_MEDIA_DIRS
# hold media a note may reference, and go through the publish gate below:
# a file in them reaches dist/ only when a published note references it.
SITE_ASSET_DIRS = frozenset({"css", "js", "images"})
REPO_MEDIA_DIRS = ("audio", "video", "flashcards")
PUBLISHABLE_ASSET_DIRS = SITE_ASSET_DIRS | frozenset(REPO_MEDIA_DIRS)

# The vault's media folders, every one of them gated. `documents` is absent
# on purpose: nothing sorted there is ever published, referenced or not.
VAULT_MEDIA_DIRS = ("audio", "video", "images", "flashcards")


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
            warn(f"Drop Zone file left unsorted, unknown type: {f}")
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
            warn(f"Not published (link, or resolves outside assets/): {source}")
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
            # Stop. This used to warn and build on top of whatever survived,
            # so a file left over from an earlier build (a page since removed,
            # an asset since withheld) could ship next to the new ones, and
            # nothing in the output would say which was which.
            raise RuntimeError(
                f"Could not wipe {OUTPUT_DIR} before building (is a file in it open in another "
                f"program?): {e}"
            ) from e

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    src_assets = os.path.join(ROOT_DIR, "assets")
    dst_assets = os.path.join(OUTPUT_DIR, "assets")
    if not os.path.isdir(src_assets):
        return

    os.makedirs(dst_assets, exist_ok=True)
    assets_root = Path(src_assets).resolve()
    copied, gated, withheld = [], [], []
    for entry in sorted(os.listdir(src_assets)):
        src = os.path.join(src_assets, entry)
        # Case-folded because NTFS is case-insensitive and its casing is
        # sticky: a folder first created as `CSS/` keeps that name forever.
        # Folding an *allowlist* can only keep a legitimately-named folder
        # working -- `Docs/` still isn't `docs`, so nothing new is admitted.
        folded = entry.casefold()
        if folded in SITE_ASSET_DIRS and os.path.isdir(src) and not is_link(src):
            _copy_contained_tree(src, os.path.join(dst_assets, entry), assets_root)
            copied.append(entry)
        elif folded in REPO_MEDIA_DIRS and os.path.isdir(src) and not is_link(src):
            # Not copied here. publish_referenced_media() copies the files a
            # published note references, once the vault scan knows them.
            gated.append(entry)
        else:
            withheld.append(entry)

    print(f"   + System assets copied: {', '.join(copied) if copied else '(none)'}")
    if gated:
        print(f"   > Media folders held for the publish gate: {', '.join(gated)}")
    if withheld:
        # Named rather than silently dropped: someone who put a file here
        # expecting it on the site needs to see why it isn't.
        print(f"   > Withheld from dist/ (not a publishable asset folder): {', '.join(withheld)}")


def _media_roots():
    """The two places a note's `assets/...` reference resolves to (see
    content.resolve_asset), as (label, assets directory, gated kinds)."""
    return (
        ("vault/assets", os.path.join(VAULT_PATH, "assets"), VAULT_MEDIA_DIRS),
        ("assets", os.path.join(ROOT_DIR, "assets"), REPO_MEDIA_DIRS),
    )


def _file_key(path):
    """(device, inode): the identity of a file or directory on disk. Two paths
    with one key are the same object, which is the question a case variant on
    macOS or NTFS (`Assets/Audio/Thing.MP3` for `assets/audio/thing.mp3`)
    needs answered, and which comparing resolved path strings gets wrong:
    realpath follows links but does not canonicalize case."""
    st = os.stat(path)
    return (st.st_dev, st.st_ino)


def _is_under(path, directory):
    """True if `path` resolves to a file whose ancestors include `directory`,
    judged by file identity rather than by string.

    The caller has already established that `directory` is a real directory
    and not a link, so its identity is its own. The path's resolved parents
    are the real directories it sits in, so a file reached through a link
    planted anywhere below `directory` resolves outside it and fails here,
    while a case variant of a real path succeeds.
    """
    try:
        want = _file_key(directory)
        return any(_file_key(parent) == want for parent in Path(path).resolve().parents)
    except OSError:
        # Fail closed: a path that cannot be stat'ed is not inside anything.
        return False


def _media_home(source, roots):
    """(label, kind) for a referenced file that sits inside a gated media
    folder reached without crossing a link; None for anything else.

    The containment base is the literal `<assets>/<kind>` directory, refused
    outright when it or the assets directory is a link. This is what the
    replaced sync_vault_assets() enforced with escapes() per file and what
    _unreferenced_media() still enforces on the listing side: a link standing
    in for a media folder points wherever whoever planted it chose, and
    dist/ is what GitHub Pages serves.
    """
    for label, assets_dir, kinds in roots:
        if not os.path.isdir(assets_dir) or is_link(assets_dir):
            continue
        for kind in kinds:
            kind_dir = os.path.join(assets_dir, kind)
            if not os.path.isdir(kind_dir) or is_link(kind_dir):
                continue
            if _is_under(source, kind_dir):
                return label, kind
    return None


def _is_site_asset(source):
    """True if a referenced file sits in one of the site's own asset folders
    (assets/{css,js,images} at the repo root), which prepare_dist() copies
    whole. A note that references the headshot, say, needs nothing from the
    gate and deserves no warning."""
    assets_dir = os.path.join(ROOT_DIR, "assets")
    if not os.path.isdir(assets_dir) or is_link(assets_dir):
        return False
    for kind in SITE_ASSET_DIRS:
        kind_dir = os.path.join(assets_dir, kind)
        if os.path.isdir(kind_dir) and not is_link(kind_dir) and _is_under(source, kind_dir):
            return True
    return False


def _walk_media_files(label, assets_dir, kind):
    """Yields (display path, on-disk path) for every regular file under
    <assets_dir>/<kind>, refusing links the way _copy_contained_tree() does.
    Dotfiles (.DS_Store, .gitkeep) are never published either, but listing
    them would only be noise."""
    kind_dir = os.path.join(assets_dir, kind)
    if not os.path.isdir(kind_dir):
        return
    assets_resolved = Path(assets_dir).resolve()
    if is_link(kind_dir) or escapes(kind_dir, assets_resolved):
        warn(f"Not published (link, or resolves outside {label}/): {kind_dir}")
        return
    for dirpath, dirnames, filenames in os.walk(kind_dir):
        for name in sorted(dirnames):
            full = os.path.join(dirpath, name)
            if is_link(full) or escapes(full, assets_resolved):
                warn(f"Not published (link, or resolves outside {label}/): {full}")
                dirnames.remove(name)
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            full = os.path.join(dirpath, name)
            if is_link(full) or escapes(full, assets_resolved):
                warn(f"Not published (link, or resolves outside {label}/): {full}")
                continue
            yield f"{label}/{os.path.relpath(full, assets_dir).replace(os.sep, '/')}", full


def _unpublished_media(roots, published_keys):
    """What the gate left behind, as two lists of display paths: the files in
    gated media folders that no published note referenced, and the files in
    every other folder under vault/assets/ (`documents`, or a kind nobody has
    named yet), which are never published whatever references them. Both are
    listed so nothing in a media folder is invisibly dropped."""
    unreferenced, never = [], []
    for label, assets_dir, kinds in roots:
        if not os.path.isdir(assets_dir) or is_link(assets_dir):
            continue
        for kind in kinds:
            for shown, full in _walk_media_files(label, assets_dir, kind):
                try:
                    key = _file_key(full)
                except OSError:
                    continue
                if key not in published_keys:
                    unreferenced.append(shown)
        if label == "assets":
            # The repo's other folders are prepare_dist()'s business: the
            # site's own are copied whole, the rest are already withheld
            # and named in its log.
            continue
        for entry in sorted(os.listdir(assets_dir)):
            folded = entry.casefold()
            if folded in kinds or entry.startswith("."):
                continue
            if os.path.isdir(os.path.join(assets_dir, entry)):
                never.extend(shown for shown, _full in _walk_media_files(label, assets_dir, entry))
    return unreferenced, never


def publish_referenced_media(referenced):
    """Copies into dist/ the media files that published notes reference, and
    lists every other file in the media folders as not published.

    `referenced` is content.get_referenced_assets(): {reference as written in
    a note: resolved on-disk path}, filled by resolve_asset() while the vault
    scan processed the published notes. This is the publish gate for media
    (backlog B06, docs/DECISIONS.md item 32). Before it, every file in
    vault/assets/{audio,video,images,flashcards} and the repo's
    assets/{audio,video,flashcards} was copied to the public site whether or
    not any note used it, so a file that merely landed in a media folder was
    published, reviewed by nobody. Now a file ships only when a published
    note names it, and the build log says what it left behind.

    Containment is checked on both ends. resolve_asset() kept the source
    inside the vault or the repo; _media_home() requires it to sit inside a
    real `<assets>/<kind>` folder reached through no link; escapes() keeps
    the destination inside dist/assets/. Files are compared by identity,
    not path string, so a case variant in a note publishes once and is
    listed once.

    Runs after the vault scan, since the scan is what fills the registry.
    Returns (published references, unreferenced files) for the tests.
    """
    print("\n🔄 PUBLISHING MEDIA: files referenced by published notes...")
    roots = _media_roots()
    dist_assets = Path(OUTPUT_DIR, "assets")
    dist_assets.mkdir(parents=True, exist_ok=True)
    dist_assets_resolved = dist_assets.resolve()

    published, published_keys = [], set()
    for ref, source in sorted(referenced.items()):
        if is_link(source):
            warn(f"Not published (link): {source}")
            continue
        if _media_home(source, roots) is None:
            if _is_site_asset(source):
                continue
            # Referenced by a published note, so the page may point at it,
            # but it is not in a media folder the gate publishes from: a
            # vault/assets/documents file, a link standing in for a media
            # folder, or a kind nobody has named. Said out loud, since the
            # alternative is a widget pointing at nothing.
            warn(f"Not published (referenced, but not in a media folder the gate publishes): {ref}")
            continue
        try:
            key = _file_key(source)
        except OSError as e:
            warn(f"Not published (unreadable): {source} ({e})")
            continue
        shown = os.path.normpath(ref).replace(os.sep, "/")
        if key in published_keys:
            # A second reference to the same file under a case variant or a
            # `..` spelling. The first copy serves it on a case-insensitive
            # host; on Linux the page would ask for a name that is not
            # there, which is a note to fix, not a file to duplicate.
            warn(f"Not published twice: {shown} is the same file as an earlier reference")
            continue
        # The reference is also the URL the widget uses, so the file goes to
        # dist/<reference>, placed under the real dist/assets/ directory by
        # its parts so a reference spelt `Assets/...` on a case-insensitive
        # host lands in the one folder the site serves. Nothing may leave
        # dist/assets/: every reference starts with that folder and holds no
        # `..`, and escapes() is the backstop, so a reference can never
        # write beside the pages.
        parts = Path(os.path.normpath(ref)).parts
        if (os.path.isabs(ref) or len(parts) < 2 or parts[0].casefold() != "assets"
                or any(part == ".." for part in parts)):
            warn(f"Not published (reference would land outside dist/assets/): {ref}")
            continue
        dest = dist_assets.joinpath(*parts[1:])
        if escapes(dest, dist_assets_resolved):
            warn(f"Not published (reference would land outside dist/assets/): {ref}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        published.append(shown)
        published_keys.add(key)

    unreferenced, never = _unpublished_media(roots, published_keys)

    print(f"   + Media published: {len(published)} file(s) referenced by published notes")
    for ref in published:
        print(f"     - {ref}")
    if unreferenced:
        print(f"   > Not published, no published note references them: {len(unreferenced)} file(s)")
        for item in unreferenced:
            print(f"     - {item}")
    if never:
        print(f"   > Never published, not a media folder: {len(never)} file(s)")
        for item in never:
            print(f"     - {item}")
    return published, unreferenced
