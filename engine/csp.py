"""The Content-Security-Policy each built page carries (backlog B02).

GitHub Pages sends no response headers, so the policy is a <meta http-equiv>
tag, the first element in <head> (system/templates/base.html), rendered with
the placeholder token below and filled in here once the page's bytes are
final. The policy allows no inline script or style by default: every inline
<script> and <style> block gets a sha256 hash computed from its exact
contents, which is what lets the Garden keep its one large inline script
without 'unsafe-inline' and without the B01 module split. Inline event
handlers and style attributes have no hash form the policy accepts here, so
none exist (the first half of B02 removed the handlers; the second half the
style attributes), and apply_csp() warns if one comes back, which the
strict CI build turns into a failure.

A hash is of the final bytes, so apply_csp() must run after every other
rewrite of the pages -- after stamp_asset_versions() in build_all().
"""
import base64
import hashlib
import html
import re
from pathlib import Path

from engine.buildlog import warn

# What base.html renders into the meta tag's content attribute.
TOKEN = "@@csp@@"

_SCRIPT_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
_STYLE_RE = re.compile(r"<style(?P<attrs>[^>]*)>(?P<body>.*?)</style>", re.S | re.I)
_SRC_RE = re.compile(r"\ssrc\s*=", re.I)
_TYPE_RE = re.compile(r"""\stype\s*=\s*["']?([^"'\s>]+)""", re.I)
_STYLE_ATTR_RE = re.compile(r"""\sstyle\s*=\s*["']""", re.I)
_HANDLER_ATTR_RE = re.compile(r"""\son[a-z]+\s*=\s*["']""", re.I)

# Script types the browser executes, so the policy has to vouch for them.
# A data block (application/ld+json, application/json) is never executed
# and needs no hash.
_EXECUTED_TYPES = {"", "text/javascript", "application/javascript", "module"}

# The directives every page shares. Nothing on the site needs another origin
# (tests/browser/origin.spec.mjs holds it to that): fonts, scripts, styles,
# media and the search index are all served from the site itself. data: is
# for the favicon, an inline SVG data URL in base.html. No frames, plugins,
# forms or <base> anywhere, so each of those is closed outright.
STATIC_DIRECTIVES = (
    "default-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "media-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "frame-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
)


def sha256_source(text):
    """The CSP source expression for one inline block: 'sha256-<base64>' of
    the block's exact UTF-8 bytes, which is what the browser computes."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def _executed(attrs):
    if _SRC_RE.search(attrs):
        return False
    match = _TYPE_RE.search(attrs)
    return (match.group(1).strip().lower() if match else "") in _EXECUTED_TYPES


def inline_script_hashes(page_html):
    """Hashes of every inline <script> the browser would execute, in order."""
    return [sha256_source(m.group("body")) for m in _SCRIPT_RE.finditer(page_html) if _executed(m.group("attrs"))]


def style_block_hashes(page_html):
    """Hashes of every <style> block, in order."""
    return [sha256_source(m.group("body")) for m in _STYLE_RE.finditer(page_html)]


def build_policy(script_hashes, style_hashes):
    """The policy string for one page. 'self' plus that page's hashes; never
    'unsafe-inline' or 'unsafe-eval'."""
    directives = [
        STATIC_DIRECTIVES[0],
        " ".join(["script-src 'self'", *script_hashes]),
        " ".join(["style-src 'self'", *style_hashes]),
        *STATIC_DIRECTIVES[1:],
    ]
    return "; ".join(directives)


def _markup_only(page_html):
    """The page with every <script> and <style> body removed, so a scan for
    attributes cannot match JS source that merely mentions one."""
    return _STYLE_RE.sub("<style>", _SCRIPT_RE.sub("<script>", page_html))


def apply_csp(dist_dir):
    """Fills each page's policy token with hashes of that page's own inline
    blocks. Returns {page name: policy}. Warns, so --strict fails, when a
    page has no token to fill or carries an inline style attribute or event
    handler, since the policy would refuse those live and the page would
    render without them."""
    policies = {}
    for page in sorted(Path(dist_dir).glob("*.html")):
        text = page.read_text(encoding="utf-8")
        if TOKEN not in text:
            warn(f"{page.name} has no Content-Security-Policy slot (base.html's meta tag)")
            continue
        markup = _markup_only(text)
        if _STYLE_ATTR_RE.search(markup):
            warn(f"{page.name} carries an inline style attribute, which the Content-Security-Policy refuses")
        if _HANDLER_ATTR_RE.search(markup):
            warn(f"{page.name} carries an inline event handler, which the Content-Security-Policy refuses")
        policy = build_policy(inline_script_hashes(text), style_block_hashes(text))
        page.write_text(text.replace(TOKEN, html.escape(policy, quote=False)), encoding="utf-8")
        policies[page.name] = policy
    return policies
