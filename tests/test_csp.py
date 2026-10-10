"""The Content-Security-Policy each built page carries (backlog B02).

engine/csp.py fills base.html's meta tag after the build with hashes of the
page's own inline <script> and <style> blocks. These tests cover the hash,
which blocks count, the policy's shape, the token fill and the warnings.
"""
import base64
import hashlib

import pytest

from engine import csp
from engine.buildlog import get_warnings, reset_warnings


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


def test_sha256_source_matches_what_a_browser_computes():
    body = "console.log('hi');\n"
    expected = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    assert csp.sha256_source(body) == f"'sha256-{expected}'"


def test_hashes_cover_executed_inline_scripts_only():
    page = (
        "<script>a()</script>"
        "<script src=\"x.js\"></script>"
        "<script type=\"application/ld+json\">{}</script>"
        "<script type=\"module\">b()</script>"
        "<script type='text/javascript'>c()</script>"
    )
    assert csp.inline_script_hashes(page) == [csp.sha256_source("a()"), csp.sha256_source("b()"), csp.sha256_source("c()")]


def test_hashes_are_of_the_exact_bytes_between_the_tags():
    # Whitespace is part of what the browser hashes; trimming would break it.
    assert csp.inline_script_hashes("<script>\n  a()\n</script>") == [csp.sha256_source("\n  a()\n")]


def test_style_block_hashes():
    assert csp.style_block_hashes("<style>.a{}</style><p></p><style media=\"print\">.b{}</style>") == [
        csp.sha256_source(".a{}"), csp.sha256_source(".b{}")]


def test_policy_allows_self_plus_hashes_and_nothing_inline():
    policy = csp.build_policy([csp.sha256_source("a()")], [csp.sha256_source(".a{}")])
    assert policy.startswith("default-src 'self'; ")
    assert "script-src 'self' 'sha256-" in policy
    assert "style-src 'self' 'sha256-" in policy
    assert "unsafe-inline" not in policy
    assert "unsafe-eval" not in policy
    assert "unsafe-hashes" not in policy
    for closed in ("object-src 'none'", "frame-src 'none'", "base-uri 'none'", "form-action 'none'"):
        assert closed in policy
    assert "img-src 'self' data:" in policy


def test_policy_with_no_inline_blocks_still_names_self():
    policy = csp.build_policy([], [])
    assert "script-src 'self';" in policy
    assert "style-src 'self';" in policy


def _page(tmp_path, name, body):
    (tmp_path / name).write_text(body, encoding="utf-8")


def test_apply_csp_fills_each_page_with_its_own_hashes(tmp_path):
    _page(tmp_path, "a.html", "<head><meta content=\"@@csp@@\"></head><script>a()</script>")
    _page(tmp_path, "b.html", "<head><meta content=\"@@csp@@\"></head><style>.b{}</style>")

    policies = csp.apply_csp(tmp_path)

    a = (tmp_path / "a.html").read_text(encoding="utf-8")
    b = (tmp_path / "b.html").read_text(encoding="utf-8")
    assert "@@csp@@" not in a and "@@csp@@" not in b
    assert csp.sha256_source("a()") in a and csp.sha256_source("a()") not in b
    assert csp.sha256_source(".b{}") in b and csp.sha256_source(".b{}") not in a
    assert set(policies) == {"a.html", "b.html"}
    assert get_warnings() == []


def test_apply_csp_warns_when_a_page_has_no_slot(tmp_path):
    _page(tmp_path, "stray.html", "<html><script>a()</script></html>")
    csp.apply_csp(tmp_path)
    assert any("no Content-Security-Policy slot" in w for w in get_warnings())


def test_apply_csp_warns_about_an_inline_style_attribute_or_handler(tmp_path):
    _page(tmp_path, "p.html", "<head><meta content=\"@@csp@@\"></head><div style=\"color:red\" onclick=\"x()\"></div>")
    csp.apply_csp(tmp_path)
    warnings = get_warnings()
    assert any("inline style attribute" in w for w in warnings)
    assert any("inline event handler" in w for w in warnings)


def test_apply_csp_ignores_attribute_shaped_text_inside_scripts_and_styles(tmp_path):
    _page(tmp_path, "p.html", "<head><meta content=\"@@csp@@\"></head>"
          "<script>const style = \"x\"; el.innerHTML = ' onclick=\"never\"';</script>"
          "<style>/* style = \"inside a comment\" */</style>")
    csp.apply_csp(tmp_path)
    assert get_warnings() == []
