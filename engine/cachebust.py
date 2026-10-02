"""Cache busting by the hash of the file actually served.

GitHub Pages sends `Cache-Control: max-age=600` with an etag, so a browser
may reuse a cached script or stylesheet for ten minutes without asking. A
visitor who returns just after a deploy then gets new HTML calling functions
that only exist in the new JS, against the old file: a failure that is
silent and looks like the feature not working. So every local asset URL
carries ?v=<hash of that file's content>.

The hash cannot be computed while the pages render: main.css is compiled
from the rendered HTML, so its final bytes do not exist yet. Templates
therefore write asset_url('assets/css/main.css'), which emits a placeholder
token, and stamp_asset_versions() replaces each token with the hash of the
file in dist/ once everything, including the CSS compile, is finished. The
hash is of the served bytes, so it changes exactly when the file does.
"""
import hashlib
import re
from pathlib import Path

from jinja2 import pass_context

from engine.buildlog import warn

_TOKEN_RE = re.compile(r"@@asset:([A-Za-z0-9_./-]+)@@")


@pass_context
def asset_url(context, path):
    """URL of a file under the site root, versioned by a token stamped after the build."""
    root = context.get("site_root", "")
    return f"{root}{path}?v=@@asset:{path}@@"


def stamp_asset_versions(dist_dir):
    """Replaces every @@asset:<path>@@ token in dist_dir's pages with a content hash."""
    dist = Path(dist_dir)
    hashes = {}

    def version(match):
        rel = match.group(1)
        if rel not in hashes:
            try:
                hashes[rel] = hashlib.sha256((dist / rel).read_bytes()).hexdigest()[:10]
            except OSError as e:
                warn(f"Could not read {rel} for cache busting: {e}")
                hashes[rel] = "missing"
        return hashes[rel]

    for page in sorted(dist.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        stamped = _TOKEN_RE.sub(version, text)
        if stamped != text:
            page.write_text(stamped, encoding="utf-8")
    return hashes
