import os
from unittest.mock import patch

from engine import assets_pipeline
from engine.assets_pipeline import _compress_audio


def _write(path, size_bytes):
    path.write_bytes(b"\0" * size_bytes)


def test_compress_audio_skips_unsupported_extension(tmp_path):
    src = tmp_path / "clip.wav"
    _write(src, 1000)
    dest = tmp_path / "out.wav"

    with patch("shutil.which") as which:
        assert _compress_audio(str(src), str(dest), ".wav") is False
        which.assert_not_called()  # shouldn't even check for ffmpeg


def test_compress_audio_returns_false_when_ffmpeg_missing(tmp_path):
    src = tmp_path / "clip.m4a"
    _write(src, 1000)
    dest = tmp_path / "out.m4a"

    with patch("shutil.which", return_value=None):
        assert _compress_audio(str(src), str(dest), ".m4a") is False
    assert not dest.exists()


def test_compress_audio_returns_false_on_ffmpeg_failure(tmp_path):
    src = tmp_path / "clip.m4a"
    _write(src, 1000)
    dest = tmp_path / "out.m4a"

    fake_result = type("R", (), {"returncode": 1})()
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("subprocess.run", return_value=fake_result):
        assert _compress_audio(str(src), str(dest), ".m4a") is False


def test_compress_audio_success_shrinks_file(tmp_path):
    src = tmp_path / "clip.m4a"
    _write(src, 10_000)
    dest = tmp_path / "out.m4a"

    def fake_run(cmd, **kwargs):
        # Simulate ffmpeg actually writing a smaller output file.
        _write(dest, 4_000)
        return type("R", (), {"returncode": 0})()

    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("subprocess.run", side_effect=fake_run):
        assert _compress_audio(str(src), str(dest), ".m4a") is True
    assert dest.exists()
    assert dest.stat().st_size < src.stat().st_size


def test_compress_audio_discards_result_if_not_actually_smaller(tmp_path):
    src = tmp_path / "clip.m4a"
    _write(src, 1_000)
    dest = tmp_path / "out.m4a"

    def fake_run(cmd, **kwargs):
        # Simulate a pathological case where re-encoding grew the file.
        _write(dest, 2_000)
        return type("R", (), {"returncode": 0})()

    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("subprocess.run", side_effect=fake_run):
        assert _compress_audio(str(src), str(dest), ".m4a") is False
    assert not dest.exists()  # cleaned up, caller falls back to a plain copy


# --- prepare_dist publishes an allowlist, not the whole assets/ tree -------
#
# Every test below builds its own repo root under pytest's tmp_path and
# points engine.assets_pipeline's ROOT_DIR/OUTPUT_DIR at it. The real
# assets/, dist/ and vault/ are never read or written.

def _fake_root(tmp_path, monkeypatch, entries):
    """Builds tmp_path/root/assets/<entries> and aims prepare_dist() at it.

    `entries` maps a path relative to assets/ to its file content.
    Returns (root, dist).
    """
    root = tmp_path / "root"
    dist = root / "dist"
    for rel, text in entries.items():
        path = root / "assets" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(assets_pipeline, "ROOT_DIR", str(root))
    monkeypatch.setattr(assets_pipeline, "OUTPUT_DIR", str(dist))
    return root, dist


def test_prepare_dist_copies_the_allowlisted_asset_folders(tmp_path, monkeypatch):
    _, dist = _fake_root(tmp_path, monkeypatch, {
        "css/main.css": "body{}",
        "js/utils.js": "// js",
        "images/social.jpg": "img",
        "flashcards/deck.csv": "q,a\n",
    })

    assets_pipeline.prepare_dist()

    for rel in ("css/main.css", "js/utils.js", "images/social.jpg", "flashcards/deck.csv"):
        assert (dist / "assets" / rel).exists(), f"{rel} should be published"


def test_prepare_dist_does_not_publish_assets_docs(tmp_path, monkeypatch):
    # The 2026-08 incident, as a test: assets/docs/ held the author's resume
    # and the unfiltered copytree served it from the Pages site.
    _, dist = _fake_root(tmp_path, monkeypatch, {
        "css/main.css": "body{}",
        "docs/resume.pdf": "PERSONAL",
    })

    assets_pipeline.prepare_dist()

    assert (dist / "assets" / "css" / "main.css").exists()
    assert not (dist / "assets" / "docs").exists()


def test_prepare_dist_withholds_an_asset_folder_nobody_allowlisted(tmp_path, monkeypatch):
    # An allowlist, not a docs/ special case: a folder added later is
    # withheld until someone adds it to PUBLISHABLE_ASSET_DIRS on purpose.
    _, dist = _fake_root(tmp_path, monkeypatch, {"scratch/notes.txt": "private"})

    assets_pipeline.prepare_dist()

    assert not (dist / "assets" / "scratch").exists()


def test_prepare_dist_withholds_a_loose_file_at_the_top_of_assets(tmp_path, monkeypatch):
    _, dist = _fake_root(tmp_path, monkeypatch, {"stray-resume.pdf": "PERSONAL"})

    assets_pipeline.prepare_dist()

    assert not (dist / "assets" / "stray-resume.pdf").exists()


def test_prepare_dist_still_publishes_a_case_variant_of_an_allowlisted_folder(tmp_path, monkeypatch):
    # NTFS casing is sticky, so `CSS/` created once stays `CSS/`. Folding an
    # allowlist is safe in the direction that matters: it can only keep a
    # real folder working, never admit `Docs/`.
    _, dist = _fake_root(tmp_path, monkeypatch, {
        "CSS/main.css": "body{}",
        "Docs/resume.pdf": "PERSONAL",
    })

    assets_pipeline.prepare_dist()

    assert (dist / "assets" / "CSS" / "main.css").exists()
    assert not (dist / "assets" / "Docs").exists()


def test_assets_docs_is_also_gitignored():
    """The build-side allowlist is only half the fix.

    prepare_dist() keeps assets/docs/ off the website; .gitignore keeps it
    out of the repo, which is public and therefore published in its own
    right. Losing either half re-opens the 2026-08 exposure, so the ignore
    entry is asserted rather than trusted.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".gitignore"), encoding="utf-8") as f:
        assert "/assets/docs/" in f.read()
