"""The build reports garden.html's compressed size and warns past the B04 limit.

Backlog B04, docs/DECISIONS.md item 32: every note body stays in garden.html
until the compressed page passes 1 MB. These tests cover the gauge that makes
that threshold visible on every build: the measurement, the report, and the
warning that --strict turns into a failed CI build.
"""
import os

import pytest

from engine import pipeline
from engine.buildlog import get_warnings, reset_warnings
from engine.pipeline import GARDEN_COMPRESSED_LIMIT_BYTES, compressed_size, report_page_sizes


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


def _write_dist(tmp_path, garden=b"<html>garden</html>", index=b"window.DEEP_SEARCH_INDEX = {};\n"):
    js_dir = tmp_path / "assets" / "js"
    js_dir.mkdir(parents=True)
    (tmp_path / "garden.html").write_bytes(garden)
    (js_dir / "search-index.js").write_bytes(index)
    return str(tmp_path)


def test_limit_is_one_mebibyte():
    assert GARDEN_COMPRESSED_LIMIT_BYTES == 1024 * 1024


def test_compressed_size_is_smaller_than_raw_for_repetitive_html():
    data = b"<article>same card over and over</article>" * 500
    assert compressed_size(data) < len(data) // 10


def test_compressed_size_is_deterministic():
    data = b"<p>" + os.urandom(2048) + b"</p>"
    assert compressed_size(data) == compressed_size(data)


def test_report_prints_both_files_and_returns_compressed_bytes(tmp_path, capsys):
    garden = b"<html>" + b"x" * 4096 + b"</html>"
    index = b"window.DEEP_SEARCH_INDEX = [" + b"1," * 2048 + b"];\n"
    sizes = report_page_sizes(_write_dist(tmp_path, garden, index))

    out = capsys.readouterr().out
    assert "Garden page:" in out and "-> garden.html" in out
    assert "Deep-search index:" in out and "-> assets/js/search-index.js" in out
    assert "KB compressed" in out and "KB raw" in out
    assert "Garden page limit: 1,024 KB compressed (backlog B04)" in out
    assert sizes == {
        "garden.html": compressed_size(garden),
        os.path.join("assets", "js", "search-index.js"): compressed_size(index),
    }


def test_report_does_not_warn_under_the_limit(tmp_path):
    report_page_sizes(_write_dist(tmp_path))
    assert get_warnings() == []


def test_report_warns_once_past_the_limit(tmp_path):
    # Random bytes do not compress, so 8 KB raw stays about 8 KB compressed
    # and a 4 KB limit is crossed for sure.
    garden = os.urandom(8192)
    report_page_sizes(_write_dist(tmp_path, garden=garden), limit=4096)

    warnings = get_warnings()
    assert len(warnings) == 1
    assert "garden.html" in warnings[0]
    assert "4 KB threshold" in warnings[0]
    assert "B04" in warnings[0]
    assert "separately cached file" in warnings[0]


def test_report_measures_the_default_dist_dir(tmp_path, monkeypatch):
    # build_all() calls report_page_sizes() with no argument, after the asset
    # stamp; the default must be the real OUTPUT_DIR and nothing else.
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", _write_dist(tmp_path))
    assert "garden.html" in report_page_sizes()


def test_build_all_reports_sizes_after_the_asset_stamp():
    # Order matters: the stamp rewrites the pages' asset URLs, so a report
    # taken before it measures bytes that never ship.
    import inspect
    source = inspect.getsource(pipeline.build_all)
    assert source.index("stamp_asset_versions(OUTPUT_DIR)") < source.index("report_page_sizes()")
