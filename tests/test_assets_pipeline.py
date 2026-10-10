import os

import pytest
from unittest.mock import patch

from engine import assets_pipeline
from engine.assets_pipeline import _compress_audio
from tests.test_paths import make_dir_link


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


def test_prepare_dist_copies_the_site_asset_folders_and_holds_media_for_the_gate(tmp_path, monkeypatch, capsys):
    _, dist = _fake_root(tmp_path, monkeypatch, {
        "css/main.css": "body{}",
        "js/utils.js": "// js",
        "images/social.jpg": "img",
        "flashcards/deck.csv": "q,a\n",
        "audio/talk.mp3": "audio",
    })

    assets_pipeline.prepare_dist()

    for rel in ("css/main.css", "js/utils.js", "images/social.jpg"):
        assert (dist / "assets" / rel).exists(), f"{rel} should be published"
    # Media waits for publish_referenced_media(), which copies only what a
    # published note references (backlog B06).
    assert not (dist / "assets" / "flashcards").exists()
    assert not (dist / "assets" / "audio").exists()
    out = capsys.readouterr().out
    assert "held for the publish gate: audio, flashcards" in out
    assert "Withheld" not in out


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


def test_prepare_dist_does_not_copy_through_a_junction_into_dist(tmp_path, monkeypatch):
    """shutil.copytree() follows a junction; dist/ is served to the internet.

    Its symlinks=True option would not have helped: a junction is not a
    symlink, so os.path.islink() is False for one. Verified against the
    unfixed code -- external.txt landed in dist/assets/images/.
    """
    root, dist = _fake_root(tmp_path, monkeypatch, {"images/real.png": "img"})
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.txt").write_text("PERSONAL", encoding="utf-8")
    make_dir_link(root / "assets" / "images" / "smuggled", outside)

    assets_pipeline.prepare_dist()

    assert (dist / "assets" / "images" / "real.png").exists()
    assert not (dist / "assets" / "images" / "smuggled").exists()
    assert not list(dist.rglob("external.txt"))


def test_prepare_dist_does_not_follow_a_junction_standing_in_for_a_whole_asset_folder(tmp_path, monkeypatch):
    root, dist = _fake_root(tmp_path, monkeypatch, {"css/main.css": "body{}"})
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.js").write_text("PERSONAL", encoding="utf-8")
    make_dir_link(root / "assets" / "js", outside)

    assets_pipeline.prepare_dist()

    assert (dist / "assets" / "css" / "main.css").exists()
    assert not list(dist.rglob("external.js"))


# --- the media publish gate (backlog B06) ----------------------------------

def _media_sandbox(tmp_path, monkeypatch, vault_files=(), repo_files=()):
    """A throwaway vault/assets and repo assets/ pair, with dist/ beside them,
    aimed at publish_referenced_media(). Returns (vault, root, dist)."""
    vault = tmp_path / "vault"
    root = tmp_path / "root"
    dist = root / "dist"
    for base, files in ((vault, vault_files), (root, repo_files)):
        for rel in files:
            path = base / "assets" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"content of {rel}", encoding="utf-8")
    monkeypatch.setattr(assets_pipeline, "VAULT_PATH", str(vault))
    monkeypatch.setattr(assets_pipeline, "ROOT_DIR", str(root))
    monkeypatch.setattr(assets_pipeline, "OUTPUT_DIR", str(dist))
    return vault, root, dist


def test_gate_publishes_a_referenced_vault_file_and_lists_the_unreferenced_one(tmp_path, monkeypatch, capsys):
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch,
                                    vault_files=("audio/used.m4a", "audio/unused.m4a", "images/chart.png"))

    published, skipped = assets_pipeline.publish_referenced_media({
        "assets/audio/used.m4a": str(vault / "assets" / "audio" / "used.m4a"),
    })

    assert (dist / "assets" / "audio" / "used.m4a").read_text(encoding="utf-8") == "content of audio/used.m4a"
    assert not (dist / "assets" / "audio" / "unused.m4a").exists()
    assert not (dist / "assets" / "images").exists()
    assert published == ["assets/audio/used.m4a"]
    assert skipped == ["vault/assets/audio/unused.m4a", "vault/assets/images/chart.png"]
    out = capsys.readouterr().out
    assert "Media published: 1 file(s)" in out
    assert "Not published, no published note references them: 2 file(s)" in out
    assert "vault/assets/audio/unused.m4a" in out


def test_gate_applies_to_the_repo_flashcard_decks_too(tmp_path, monkeypatch):
    # The five tracked decks live at the repo root. A deck no published note
    # names stays off the site.
    _, root, dist = _media_sandbox(tmp_path, monkeypatch,
                                   repo_files=("flashcards/used.csv", "flashcards/orphan.csv"))

    published, skipped = assets_pipeline.publish_referenced_media({
        "assets/flashcards/used.csv": str(root / "assets" / "flashcards" / "used.csv"),
    })

    assert (dist / "assets" / "flashcards" / "used.csv").exists()
    assert not (dist / "assets" / "flashcards" / "orphan.csv").exists()
    assert published == ["assets/flashcards/used.csv"]
    assert skipped == ["assets/flashcards/orphan.csv"]


def test_gate_publishes_nothing_when_nothing_is_referenced(tmp_path, monkeypatch):
    _, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("video/clip.mp4",))

    published, skipped = assets_pipeline.publish_referenced_media({})

    assert published == []
    assert skipped == ["vault/assets/video/clip.mp4"]
    assert not list((dist / "assets").rglob("*.mp4"))


def test_gate_leaves_the_sites_own_images_to_prepare_dist(tmp_path, monkeypatch):
    # A note may reference assets/images/headshot.webp, which resolve_asset()
    # finds at the repo root. That folder is copied whole by prepare_dist()
    # and is not media the gate decides about.
    _, root, dist = _media_sandbox(tmp_path, monkeypatch, repo_files=("images/headshot.webp",))

    published, skipped = assets_pipeline.publish_referenced_media({
        "assets/images/headshot.webp": str(root / "assets" / "images" / "headshot.webp"),
    })

    assert published == []
    assert skipped == []
    assert not (dist / "assets" / "images").exists()


def test_gate_refuses_a_reference_that_would_land_outside_dist_assets(tmp_path, monkeypatch, capsys):
    # resolve_asset() already refuses a traversal on the source side; the
    # gate refuses one on the destination side too, so a reference can never
    # write a file beside the pages.
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("flashcards/deck.csv",))

    published, _ = assets_pipeline.publish_referenced_media({
        "assets/flashcards/../../deck.csv": str(vault / "assets" / "flashcards" / "deck.csv"),
    })

    assert published == []
    assert not (dist / "deck.csv").exists()
    assert "would land outside dist/assets/" in capsys.readouterr().out


def test_gate_does_not_publish_a_linked_file_even_when_referenced(tmp_path, monkeypatch, capsys):
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("audio/real.mp3",))
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.mp3").write_text("PERSONAL", encoding="utf-8")
    link = vault / "assets" / "audio" / "smuggled.mp3"
    os.symlink(outside / "external.mp3", link)

    published, _ = assets_pipeline.publish_referenced_media({
        "assets/audio/smuggled.mp3": str(link),
    })

    assert published == []
    assert not list(dist.rglob("smuggled.mp3"))
    assert "Not published (link)" in capsys.readouterr().out


def test_gate_does_not_walk_a_linked_media_folder(tmp_path, monkeypatch, capsys):
    # os.path.isfile() follows links too, so the vault-side listing needs the
    # same rule as the repo-side copy: a junction standing in for a media
    # folder is refused, never followed.
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("audio/real.mp3",))
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.png").write_text("PERSONAL", encoding="utf-8")
    make_dir_link(vault / "assets" / "images", outside)

    published, skipped = assets_pipeline.publish_referenced_media({
        "assets/audio/real.mp3": str(vault / "assets" / "audio" / "real.mp3"),
    })

    assert published == ["assets/audio/real.mp3"]
    assert skipped == []
    assert not list(dist.rglob("external.png"))
    assert "Not published (link, or resolves outside vault/assets/)" in capsys.readouterr().out


def test_gate_does_not_publish_through_a_link_standing_in_for_a_media_folder(tmp_path, monkeypatch, capsys):
    # The publish-side twin of the listing test below. resolve_asset() only
    # keeps a reference inside the vault, so `vault/assets/audio` linked at
    # `vault/20_AURELIA` resolves a published note's reference to the one
    # folder the privacy model hard-excludes. The gate's containment base is
    # the literal media folder, refused when it is a link, so the file never
    # ships and the build says so.
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch)
    hidden = vault / "20_AURELIA"
    hidden.mkdir(parents=True)
    (hidden / "agent_draft.m4a").write_text("NOT FOR THE SITE", encoding="utf-8")
    (vault / "assets").mkdir()
    make_dir_link(vault / "assets" / "audio", hidden)

    published, _ = assets_pipeline.publish_referenced_media({
        "assets/audio/agent_draft.m4a": str(vault / "assets" / "audio" / "agent_draft.m4a"),
    })

    assert published == []
    assert not list(dist.rglob("agent_draft.m4a"))
    out = capsys.readouterr().out
    assert "Not published (referenced, but not in a media folder the gate publishes)" in out


def test_gate_does_not_publish_through_a_link_inside_a_media_folder(tmp_path, monkeypatch):
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("audio/real.mp3",))
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.mp3").write_text("PERSONAL", encoding="utf-8")
    make_dir_link(vault / "assets" / "audio" / "sub", outside)

    published, _ = assets_pipeline.publish_referenced_media({
        "assets/audio/sub/external.mp3": str(vault / "assets" / "audio" / "sub" / "external.mp3"),
    })

    assert published == []
    assert not list(dist.rglob("external.mp3"))


def test_gate_does_not_publish_when_the_assets_folder_itself_is_a_link(tmp_path, monkeypatch):
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch)
    outside = tmp_path / "outside"
    (outside / "audio").mkdir(parents=True)
    (outside / "audio" / "x.mp3").write_text("PERSONAL", encoding="utf-8")
    vault.mkdir(exist_ok=True)
    make_dir_link(vault / "assets", outside)

    published, unreferenced = assets_pipeline.publish_referenced_media({
        "assets/audio/x.mp3": str(vault / "assets" / "audio" / "x.mp3"),
    })

    assert published == []
    assert unreferenced == []
    assert not list(dist.rglob("x.mp3"))


def test_gate_warns_about_a_referenced_file_outside_every_media_folder(tmp_path, monkeypatch, capsys):
    # extractors._ASSET_REF_RE is broad enough to register a mention of
    # assets/documents/paper.pdf in a published note. The gate withholds it,
    # and says so rather than leaving a widget pointing at nothing.
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("documents/paper.pdf",))

    published, unreferenced = assets_pipeline.publish_referenced_media({
        "assets/documents/paper.pdf": str(vault / "assets" / "documents" / "paper.pdf"),
    })

    assert published == []
    assert not (dist / "assets" / "documents").exists()
    out = capsys.readouterr().out
    assert "Not published (referenced, but not in a media folder the gate publishes): assets/documents/paper.pdf" in out
    assert "Never published, not a media folder: 1 file(s)" in out
    assert "vault/assets/documents/paper.pdf" in out


def test_gate_lists_a_vault_folder_nobody_named_as_never_published(tmp_path, monkeypatch, capsys):
    _media_sandbox(tmp_path, monkeypatch, vault_files=("scratch/notes.txt",))

    published, unreferenced = assets_pipeline.publish_referenced_media({})

    assert (published, unreferenced) == ([], [])
    assert "vault/assets/scratch/notes.txt" in capsys.readouterr().out


def _case_insensitive(path):
    probe = path / "CaseProbe"
    probe.write_text("", encoding="utf-8")
    try:
        return (path / "caseprobe").exists()
    finally:
        probe.unlink()


def test_gate_counts_a_case_variant_reference_as_the_file_it_is(tmp_path, monkeypatch, capsys):
    # macOS and NTFS resolve `Thing.MP3` to `thing.mp3` but realpath keeps
    # the spelling the note used, so comparing path strings listed the file
    # as both published and unreferenced. Identity (device, inode) does not.
    if not _case_insensitive(tmp_path):
        pytest.skip("needs a case-insensitive filesystem")
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("audio/thing.mp3",))

    published, unreferenced = assets_pipeline.publish_referenced_media({
        "assets/audio/Thing.MP3": str(vault / "assets" / "audio" / "Thing.MP3"),
    })

    assert published == ["assets/audio/Thing.MP3"]
    assert unreferenced == []
    assert (dist / "assets" / "audio" / "Thing.MP3").exists()
    assert "Not published, no published note references them" not in capsys.readouterr().out


def test_gate_publishes_a_directory_case_variant_reference(tmp_path, monkeypatch):
    if not _case_insensitive(tmp_path):
        pytest.skip("needs a case-insensitive filesystem")
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("audio/thing.mp3",))

    published, unreferenced = assets_pipeline.publish_referenced_media({
        "Assets/Audio/thing.mp3": str(vault / "Assets" / "Audio" / "thing.mp3"),
    })

    assert published == ["Assets/Audio/thing.mp3"]
    assert unreferenced == []
    # Under the real dist/assets/ folder, which a case-insensitive host
    # serves for the URL the widget emits.
    assert (dist / "assets" / "Audio" / "thing.mp3").exists()


def test_gate_publishes_one_file_referenced_two_ways_once(tmp_path, monkeypatch, capsys):
    vault, _, dist = _media_sandbox(tmp_path, monkeypatch, vault_files=("audio/thing.mp3",))
    source = str(vault / "assets" / "audio" / "thing.mp3")

    published, unreferenced = assets_pipeline.publish_referenced_media({
        "assets/audio/thing.mp3": source,
        "assets/images/../audio/thing.mp3": source,
    })

    assert published == ["assets/audio/thing.mp3"]
    assert unreferenced == []
    assert len(list(dist.rglob("thing.mp3"))) == 1
    assert "Not published twice" in capsys.readouterr().out


def test_gate_copes_with_no_media_folders_at_all(tmp_path, monkeypatch):
    # The real vault has no vault/assets/ today, and a fresh clone may have
    # no repo media either.
    _media_sandbox(tmp_path, monkeypatch)

    assert assets_pipeline.publish_referenced_media({}) == ([], [])


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
