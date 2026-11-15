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

A page reaches an ES module's imports through no template, so those get
their version here too (roadmap S13): stamp_module_imports() rewrites each
relative import in a folder of modules under assets/js/ to carry one hash of
the whole folder. Without it a returning visitor would run the new main.js
against a ten-minute-old copy of a module it imports.
"""
import hashlib
import re
from pathlib import Path

from jinja2 import pass_context

from engine.buildlog import warn

_TOKEN_RE = re.compile(r"@@asset:([A-Za-z0-9_./-]+)@@")

# A static import or re-export of a relative .js file: `from './x.js'` or a
# bare `import './x.js'`. The modules are written one import per statement
# with the specifier in quotes, which is all this has to match; a dynamic
# import() is not used and would not be versioned.
_IMPORT_RE = re.compile(r"""(\bfrom\s*|\bimport\s*)(["'])(\.{1,2}/[^"'?]+\.js)\2""")

# Where the site's own scripts are served from, under dist/.
MODULE_ROOT = "assets/js"


@pass_context
def asset_url(context, path):
    """URL of a file under the site root, versioned by a token stamped after the build."""
    root = context.get("site_root", "")
    return f"{root}{path}?v=@@asset:{path}@@"


def stamp_module_imports(dist_dir):
    """Versions the imports inside each folder of ES modules under
    dist/assets/js/ (a folder below it, such as garden/; the files directly
    in assets/js/ are classic scripts and import nothing).

    Every relative import in a folder gets the same ?v=: a hash of all of
    that folder's .js files as copied, names included. One hash for the
    folder, not one per file, for two reasons. The modules import each other
    in cycles, so there is no order in which each file's own hash could be
    known before its importers are rewritten. And a module must be imported
    under exactly one URL: two spellings of one file are two modules to the
    browser, each with its own copy of the page's state.

    The entry module's own URL is a template's asset_url(), stamped after
    this from the rewritten bytes, so it changes whenever anything in the
    folder does. Run before stamp_asset_versions() for that reason; it
    calls this itself. Returns {folder under dist/: version}."""
    dist = Path(dist_dir)
    root = dist / MODULE_ROOT
    versions = {}
    if not root.is_dir():
        return versions
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        files = sorted(folder.rglob("*.js"))
        sources = {f: f.read_text(encoding="utf-8") for f in files}
        if not any(_IMPORT_RE.search(text) for text in sources.values()):
            continue
        digest = hashlib.sha256()
        for f in files:
            digest.update(f.relative_to(folder).as_posix().encode("utf-8") + b"\0")
            digest.update(sources[f].encode("utf-8") + b"\0")
        version = digest.hexdigest()[:10]
        rel_folder = folder.relative_to(dist).as_posix()
        versions[rel_folder] = version

        for f in files:
            def stamp(match, importer=f):
                target = (importer.parent / match.group(3)).resolve()
                if folder.resolve() not in target.parents:
                    warn(f"{importer.relative_to(dist).as_posix()} imports {match.group(3)}, outside "
                         f"{rel_folder}/, which cache busting does not version")
                    return match.group(0)
                if not target.is_file():
                    warn(f"{importer.relative_to(dist).as_posix()} imports {match.group(3)}, which does not exist")
                    return match.group(0)
                return f"{match.group(1)}{match.group(2)}{match.group(3)}?v={version}{match.group(2)}"

            stamped = _IMPORT_RE.sub(stamp, sources[f])
            if stamped != sources[f]:
                f.write_text(stamped, encoding="utf-8", newline="\n")
    return versions


def stamp_asset_versions(dist_dir):
    """Replaces every @@asset:<path>@@ token in dist_dir's pages, at any
    depth, with a content hash. The token names the file's path under
    dist/, so an essay page two folders down (roadmap S15) stamps the same
    hash as the top-level pages."""
    dist = Path(dist_dir)
    # First, so a module's hash below is of the bytes it is served with.
    stamp_module_imports(dist)
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

    for page in sorted(dist.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        stamped = _TOKEN_RE.sub(version, text)
        if stamped != text:
            page.write_text(stamped, encoding="utf-8")
    return hashes
