"""Copies the web fonts, marked.js and Motion from node_modules/ into dist/.

The site serves everything itself (docs/DECISIONS.md item 29): no page asks
another server for a script, stylesheet or font, which is what keeps the
footer's "No analytics or tracking." true. The packages are pinned in
package.json / package-lock.json, so Dependabot's npm group keeps them
current and a bump is a reviewable diff rather than an edit to a CDN URL and
an SRI hash.

Written into dist/assets/:
  fonts/fonts.css       one @font-face per subset and weight, woff2 only
  fonts/files/*.woff2   only the files fonts.css names
  fonts/licenses/       each family's licence (SIL OFL), shipped with the fonts
  vendor/               marked.umd.js, motion.js and their MIT licences

The families and weights below are exactly what base.html used to request
from Google Fonts. fonts.css is generated from fontsource's own per-weight
CSS (every subset, with its unicode-range), so a browser downloads only the
subsets a page's text needs, as it did before.
"""
import hashlib
import re
import shutil
from pathlib import Path

from engine.buildlog import warn
from engine.config import OUTPUT_DIR, ROOT_DIR

# (npm package, family, fontsource stylesheet names). Keep in step with the
# families the themes in engine/config.py name.
FONT_FACES = (
    ("inter", "Inter", ("400", "500", "600", "700", "800")),
    ("cormorant-garamond", "Cormorant Garamond", ("500", "600", "700", "500-italic")),
    ("jetbrains-mono", "JetBrains Mono", ("400", "500", "600", "700", "800")),
    ("oswald", "Oswald", ("400", "500", "700")),
    ("courier-prime", "Courier Prime", ("400", "700")),
)

# (source under node_modules/, name in dist/assets/vendor/)
VENDOR_SCRIPTS = (
    ("marked/lib/marked.umd.js", "marked.umd.js"),
    ("motion/dist/motion.js", "motion.js"),
)
VENDOR_LICENSES = (
    ("marked/LICENSE", "LICENSE-marked.txt"),
    ("motion/LICENSE.md", "LICENSE-motion.txt"),
)

_SRC_RE = re.compile(
    r"src:\s*url\(\./files/([^)]+\.woff2)\)\s*format\('woff2'\),\s*"
    r"url\(\./files/[^)]+\.woff\)\s*format\('woff'\);"
)
_SOURCE_MAP_RE = re.compile(rb"\n?//# sourceMappingURL=\S+\s*$")


def _node_modules():
    modules = Path(ROOT_DIR) / "node_modules"
    if not modules.is_dir():
        raise RuntimeError("node_modules/ is missing; run `npm ci` before building (fonts, marked.js and Motion are copied from it)")
    return modules


def _short_hash(data):
    return hashlib.sha256(data).hexdigest()[:10]


def _copy_fonts(modules, assets_dir):
    fonts_dir = assets_dir / "fonts"
    files_dir = fonts_dir / "files"
    licenses_dir = fonts_dir / "licenses"
    files_dir.mkdir(parents=True, exist_ok=True)
    licenses_dir.mkdir(parents=True, exist_ok=True)

    css_parts = []
    for package, family, weights in FONT_FACES:
        package_dir = modules / "@fontsource" / package
        for weight in weights:
            css_path = package_dir / f"{weight}.css"
            try:
                css = css_path.read_text(encoding="utf-8")
            except OSError as e:
                raise RuntimeError(f"Could not read {family} {weight} from {css_path}: {e}") from e

            def rewrite(match, package_dir=package_dir):
                name = match.group(1)
                source = package_dir / "files" / name
                try:
                    data = source.read_bytes()
                except OSError as e:
                    raise RuntimeError(f"{source} is missing: {e}") from e
                shutil.copyfile(source, files_dir / name)
                # The font's own content hash on its URL: the file name alone
                # does not change when a package bump changes its glyphs.
                return f"src: url(files/{name}?v={_short_hash(data)}) format('woff2');"

            css, replaced = _SRC_RE.subn(rewrite, css)
            if not replaced or ".woff)" in css:
                warn(f"{family} {weight}: unexpected @font-face layout in {css_path}; fonts.css may be incomplete")
            css_parts.append(css.strip())

        licence = package_dir / "LICENSE"
        try:
            shutil.copyfile(licence, licenses_dir / f"{package}-LICENSE.txt")
        except OSError as e:
            raise RuntimeError(f"{family}'s licence file is missing ({licence}); the fonts must ship with it: {e}") from e

    (fonts_dir / "fonts.css").write_text("\n\n".join(css_parts) + "\n", encoding="utf-8")


def _copy_vendor(modules, assets_dir):
    vendor_dir = assets_dir / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)
    for source, name in VENDOR_SCRIPTS:
        try:
            data = (modules / source).read_bytes()
        except OSError as e:
            raise RuntimeError(f"Could not read {source} from node_modules/: {e}") from e
        # A trailing source-map comment would make a browser with devtools
        # open request a .map file the site does not ship.
        data = _SOURCE_MAP_RE.sub(b"\n", data)
        (vendor_dir / name).write_bytes(data)
    for source, name in VENDOR_LICENSES:
        try:
            shutil.copyfile(modules / source, vendor_dir / name)
        except OSError as e:
            raise RuntimeError(f"Could not read {source} from node_modules/: {e}") from e


def copy_vendor_assets():
    modules = _node_modules()
    assets_dir = Path(OUTPUT_DIR) / "assets"
    _copy_fonts(modules, assets_dir)
    _copy_vendor(modules, assets_dir)
    print("   + Fonts, marked.js and Motion copied from node_modules/ (served from the site itself)")
