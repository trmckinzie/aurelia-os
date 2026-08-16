from unittest.mock import patch

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
