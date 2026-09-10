"""Markdown note parsing: frontmatter, wikilinks, and Gemini Notebook media blocks."""
import csv
import os
import re
from collections import defaultdict

import yaml

from engine.config import VAULT_PATH, ROOT_DIR
from engine.sanitize import sanitize_to_text


def make_id(text):
    """Turns 'My Cool Note.md' into 'note-my-cool-note'."""
    text = text.replace(".md", "").lower()
    slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return f"note-{slug}"


# Counts notes skipped for malformed YAML frontmatter (see the except branch
# in parse_frontmatter below). The per-note console warning is easy to miss
# in build output; pipeline.py reads this via get_malformed_count() to print
# a build-log summary line instead, so a bulk vault edit that breaks YAML
# somewhere surfaces loudly rather than only as a scroll-back warning.
_malformed_count = 0

# A YAML frontmatter fence is a line that is exactly `---` (trailing spaces
# tolerated), not any occurrence of those three characters. Splitting on the
# bare substring meant a note whose frontmatter carried an em-dash-ish value
# (`title: Before---After`) had its own delimiter found mid-line: parse_frontmatter
# then handed PyYAML a truncated block and parse_body started the body
# mid-frontmatter. Anchoring to ^...$ in MULTILINE mode is the whole fix.
_FRONTMATTER_FENCE_RE = re.compile(r'(?m)^---[ \t]*$')


def get_malformed_count():
    return _malformed_count


def reset_malformed_count():
    global _malformed_count
    _malformed_count = 0


# Values that make a note publish. PyYAML already turns an unquoted `true`
# (and YAML 1.1's `yes`/`on`) into Python True, so a *string* only ever gets
# here when the author quoted it or Templater left it unfilled.
_PUBLISH_TRUE = {"true", "yes", "1"}
# Unambiguous "no". Listed separately from "unrecognized" so the warning below
# fires on `publish: maybe`, not on every unpublished note in the vault.
_PUBLISH_FALSE = {"false", "no", "0", "none", "null", ""}


def _coerce_publish(value):
    """Decides whether a frontmatter `publish:` value means publish.

    Was `bool(value)`, which is true for *any* non-empty string -- so
    `publish: "false"` published the note, the exact inversion of what the
    author wrote. The publish flag is the whole rendering gate for this site
    (see CLAUDE.md's privacy model), so it gets an allowlist, not truthiness.
    """
    if value is True or value is False:
        return value
    if value is None:
        return False

    token = str(value).strip().lower()
    if token in _PUBLISH_TRUE:
        return True
    if token in _PUBLISH_FALSE:
        return False

    print(f"   ⚠️  Unrecognized publish value {value!r} -- treating as unpublished")
    return False


def parse_frontmatter(content):
    """Parses the YAML frontmatter block of a note into a metadata dict.

    Always returns publish (bool), tags (list[str]), type, and status, defaulting
    the latter two to "unknown" so downstream routing never has to null-check them.
    """
    meta = {"publish": False, "tags": [], "type": "unknown", "status": "unknown"}
    content = content.lstrip()
    if not content.startswith("---"):
        return meta

    parts = _FRONTMATTER_FENCE_RE.split(content, maxsplit=2)
    if len(parts) < 3:
        return meta

    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        # Templater note templates often contain unfilled {{placeholder}} syntax
        # that isn't valid YAML; treat them as unpublished rather than crashing.
        global _malformed_count
        _malformed_count += 1
        print(f"   ⚠️  Skipping malformed frontmatter: {str(e).splitlines()[0]}")
        return meta

    if not isinstance(parsed, dict):
        return meta

    meta.update(parsed)
    meta["publish"] = _coerce_publish(meta.get("publish", False))

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    meta["tags"] = [str(t).strip() for t in tags]

    # Obsidian Templater placeholders (e.g. "{{date}}") that were never filled in
    # shouldn't leak into rendered pages as literal braces.
    for key, value in meta.items():
        if isinstance(value, str) and ("{{" in value or "}}" in value):
            meta[key] = value.replace("{{", "").replace("}}", "").strip()

    if "date" not in meta and "created" in meta:
        meta["date"] = meta["created"]

    return meta


def parse_body(content):
    """Returns everything after the closing frontmatter fence.

    Uses the same line-anchored fence as parse_frontmatter -- the two have to
    agree on where the frontmatter ends, or the body silently starts in the
    middle of it.
    """
    parts = _FRONTMATTER_FENCE_RE.split(content, maxsplit=2)
    if len(parts) < 3:
        return content
    return parts[2].strip()


def process_wikilinks(text, resolve=None):
    """Converts [[Link]] / [[Target|Label]] to clickable modal-open buttons.

    `resolve` maps the raw target text of a wikilink to a note id -- defaults
    to plain make_id(), the historical behavior (an exact filename/title
    slug), so every caller that doesn't pass one gets byte-identical output.
    Pass a function built by build_link_resolver() to also resolve aliases
    and unique title-suffix bases (see that function's docstring).
    """
    resolve = resolve or make_id

    def replace_link(match):
        link_content = match.group(1)
        if '|' in link_content:
            target, label = link_content.split('|', 1)
        else:
            target, label = link_content, link_content

        target_id = resolve(target)
        return (f'<button onclick="openNote(\'{target_id}\')" '
                f'class="text-aurelia-primary hover:underline font-bold bg-transparent '
                f'border-none cursor-pointer p-0 inline">{label}</button>')

    return re.sub(r'\[\[(.*?)\]\]', replace_link, text)


# --- wikilink resolution (aliases, unique title-suffix bases) --------------
#
# 74% of the wikilinks written in the vault were dangling on the published
# site -- most of them not because the target note doesn't exist, but
# because the author wrote a shorter mention ([[System 1 vs System 2]]) of a
# note whose actual title carries a disambiguating suffix ("System 1 vs
# System 2 (Dual-Process Theory)"), or an alias never spelled out in the
# link text. build_link_resolver() closes that gap without touching how a
# note's own id is computed (still plain make_id() of its filename/title).

# "Base (...)" -- a trailing parenthetical, captured separately so the
# marker itself can be inspected (see _suffix_base's Gemini Notebook
# exclusion below).
_SUFFIX_PAREN_RE = re.compile(r'^(.+?)\s*\(([^()]*)\)\s*$')
# "Base: ..." -- everything after the first colon.
_SUFFIX_COLON_RE = re.compile(r'^([^:]+):\s+.+$')
# A "(Gemini Notebook)" parenthetical marks a note's *content type*, not a
# disambiguator -- see _suffix_base.
_GEMINI_NOTEBOOK_MARKER_RE = re.compile(r'^gemini notebook$', re.IGNORECASE)

# Counters in the _missing_asset_count style, read by pipeline.py to print a
# build summary line and by tools/vault_health.py to keep its own "pending"
# report's unresolved count in agreement with the real build's.
_alias_resolved_count = 0
_suffix_resolved_count = 0
# Distinct raw target slugs (make_id() of the wikilink text as written, e.g.
# "note-dopamine") that resolved via alias or suffix at least once. A single
# popular mention like [[System 1 vs System 2]] repeated 35 times is one
# entry here, not 35 -- this is what lets the build summary report "N link
# occurrences (M distinct targets)" instead of conflating the two.
_resolved_wikilink_targets = set()
# Populated by dim_dangling_links() below, not by resolve() itself: a target
# id can fail alias/suffix resolution and still turn out fine (e.g. it
# resolves to itself via plain make_id and IS a known note) -- "still
# unresolved" is properly decided where dangling links are actually detected
# against the known-ids set, which is what dim_dangling_links already does.
_unresolved_wikilink_targets = set()


def get_wikilink_resolution_counts():
    """(alias_resolved, suffix_resolved) occurrence counts since the last reset."""
    return _alias_resolved_count, _suffix_resolved_count


def get_resolved_wikilink_targets():
    """Distinct raw target slugs resolved via alias or suffix -- see
    _resolved_wikilink_targets above for why this is not the same number as
    get_wikilink_resolution_counts()'s occurrence totals."""
    return set(_resolved_wikilink_targets)


def get_unresolved_wikilink_targets():
    return set(_unresolved_wikilink_targets)


def reset_wikilink_resolution_counts():
    global _alias_resolved_count, _suffix_resolved_count
    _alias_resolved_count = 0
    _suffix_resolved_count = 0
    _resolved_wikilink_targets.clear()
    _unresolved_wikilink_targets.clear()


def _suffix_base(title):
    """Returns the 'Base' of a 'Base (...)' or 'Base: ...' title, else None.

    "(Gemini Notebook)" is excluded from the parenthetical case: it marks a
    note as a Gemini Notebook literature note (a different content type),
    not a disambiguating suffix of some other note's title. Without this
    exclusion, [[Neuroanatomy]] could silently resolve to "Neuroanatomy
    (Gemini Notebook)" whenever an unpublished Concept note shared the base
    title "Neuroanatomy" -- a semantically wrong match, since the literature
    note isn't a disambiguation of the concept, it's an unrelated note that
    happens to share a name. A title with a genuine non-marker parenthetical
    still resolves normally.
    """
    match = _SUFFIX_PAREN_RE.match(title)
    if match:
        base, marker = match.group(1).strip(), match.group(2).strip()
        if not _GEMINI_NOTEBOOK_MARKER_RE.match(marker):
            return base
    match = _SUFFIX_COLON_RE.match(title)
    if match:
        return match.group(1).strip()
    return None


def build_link_resolver(notes):
    """Builds resolve(target_text) -> note_id from three tiers, an earlier
    tier never overwritten by a later one:

      1. Exact: make_id(target_text) is itself a known note id (i.e. the
         wikilink text matches some note's title/filename exactly). Handled
         directly in resolve() against known_ids -- needs no lookup table.
      2. Alias: a note's frontmatter `aliases:` list (coerced str -> [str],
         same as `tags` in parse_frontmatter). An alias slug claimed by more
         than one note is ambiguous and dropped, with a single warning.
      3. Unique title-suffix base: for titles shaped "Base (...)" or
         "Base: ...", make_id(Base) resolves to that note only when exactly
         one published note shares that base.

    `notes`: iterable of dicts with "note_id", "title", and optionally
    "aliases" (a list of alias strings). Extra keys are ignored, so the
    pipeline's own pending-note dicts can be passed directly.
    """
    known_ids = {n["note_id"] for n in notes}

    alias_candidates = defaultdict(set)
    for n in notes:
        aliases = n.get("aliases") or []
        # `aliases: Some Alias` is valid YAML (a bare string), not a list --
        # coerce the same way parse_frontmatter does for tags (content.py's
        # own precedent). pipeline.py already does this before building its
        # note dicts, but build_link_resolver() shouldn't assume every
        # caller does; a bare string here would otherwise iterate character
        # by character.
        if isinstance(aliases, str):
            aliases = [aliases]
        for alias in aliases:
            alias_candidates[make_id(str(alias))].add(n["note_id"])

    alias_map = {}
    warned_alias_collision = False
    for alias_id, note_ids in alias_candidates.items():
        if alias_id in known_ids:
            # A real note's own title always wins -- resolve() checks
            # known_ids before ever consulting alias_map, so this alias
            # would never be reached anyway. Not registering it keeps the
            # map itself an honest record of what it actually decides.
            continue
        if len(note_ids) > 1:
            if not warned_alias_collision:
                print(f"   ⚠️  Alias '{alias_id}' is claimed by multiple notes -- dropping it")
                warned_alias_collision = True
            continue
        alias_map[alias_id] = next(iter(note_ids))

    suffix_candidates = defaultdict(set)
    for n in notes:
        base = _suffix_base(n["title"])
        if base:
            suffix_candidates[make_id(base)].add(n["note_id"])

    suffix_map = {
        base_id: next(iter(note_ids))
        for base_id, note_ids in suffix_candidates.items()
        if len(note_ids) == 1 and base_id not in known_ids and base_id not in alias_map
    }

    def resolve(target_text):
        global _alias_resolved_count, _suffix_resolved_count
        target_id = make_id(target_text)
        if target_id in known_ids:
            return target_id
        if target_id in alias_map:
            _alias_resolved_count += 1
            _resolved_wikilink_targets.add(target_id)
            return alias_map[target_id]
        if target_id in suffix_map:
            _suffix_resolved_count += 1
            _resolved_wikilink_targets.add(target_id)
            return suffix_map[target_id]
        return target_id

    return resolve


_WIKILINK_BUTTON_RE = re.compile(r'''<button\s+onclick="openNote\('([^']+)'\)"[^>]*>(.*?)</button>''')


def dim_dangling_links(html, known_ids):
    """Rewrites process_wikilinks() output so links to unpublished/nonexistent
    notes render as inert, visually muted text instead of a live-looking button --
    mirrors the live/dangling contract cards.link_pill() already applies to
    structured fields (Related, Core Concepts, ...), extended here to cover plain
    in-prose wikilinks, which link_pill() never sees since it only runs on
    extractor-parsed fields, not a note's full body.

    Also the one place that records a target as genuinely unresolved (see
    _unresolved_wikilink_targets above) -- this is where "does this link's
    target actually exist" is decided, alias/suffix resolution included,
    since resolve() itself has already run by the time this sees the body.
    """
    def replace(match):
        target_id, label = match.group(1), match.group(2)
        if target_id in known_ids:
            return match.group(0)
        if target_id != "note-":
            # "note-" is what an unfilled "[[ ]]" placeholder slugifies to
            # (make_id("") == "note-") -- some published Concept notes still
            # carry this from TPL_Concept.md's old Related-field default. It
            # isn't a real dangling link to a concept that doesn't exist yet,
            # so it shouldn't inflate the "still unresolved" count -- the
            # same placeholder tools/vault_health.py's find_pending_atomization
            # already skips via its own blank-target_text guard, which is
            # what this count is meant to agree with (see build_all()).
            _unresolved_wikilink_targets.add(target_id)
        return f'<span class="opacity-70 grayscale cursor-default" title="Not yet published">{label}</span>'

    return _WIKILINK_BUTTON_RE.sub(replace, html)


# --- Gemini Notebook media widgets -----------------------------------------
#
# Gemini Notebook export notes carry a fixed set of headers (Audio Overview,
# Video Overview, Flashcards, ...) followed by a bare asset path. This scans
# each recognized header's section for a matching asset path and swaps it for
# the corresponding interactive HTML widget.

_MEDIA_MAP = [
    {
        "header": r"#+\s*.*Audio Overview",
        "regex": r'(?:\[\[)?(assets/audio/[a-zA-Z0-9_\-\.\s]+\.(?:mp3|wav|m4a|ogg))(?:\]\])?',
        "type": "audio",
    },
    {
        "header": r"#+\s*.*Video Overview",
        "regex": r'(?:\[\[)?(assets/video/[a-zA-Z0-9_\-\.\s]+\.(?:mp4|webm))(?:\]\])?',
        "type": "video",
    },
    {
        "header": r"#+\s*.*Flashcards",
        # Bounded to assets/flashcards/ like the three matchers around it.
        # This used to be `assets/.*?`, and `.` matches `/` -- so a note could
        # name a .csv anywhere reachable from the build machine and have its
        # contents embedded in a published page (audit finding #20). The regex
        # is the first of two gates; resolve_asset() below is the real one.
        "regex": r'(?:\[\[)?(assets/flashcards/[a-zA-Z0-9_\-\.\s]+\.csv)(?:\]\])?',
        "type": "flashcards",
    },
    {
        "header": r"#+\s*.*(?:Mind Map|Reports|Quiz|Infographic|Slide Deck|Data Table)",
        "regex": r'(?:\[\[)?(assets/images/[a-zA-Z0-9_\-\.\s]+\.(?:png|jpg|jpeg|webp|gif))(?:\]\])?',
        "type": "image",
    },
]


def _render_audio(path):
    mime = "audio/mpeg"
    if path.endswith(".m4a"):
        mime = "audio/mp4"
    if path.endswith(".wav"):
        mime = "audio/wav"
    return f"""
<div class="my-6 p-4 border-l-2 border-aurelia-info bg-aurelia-info/5 rounded-r-theme">
<div class="flex items-center justify-between mb-3">
<span class="field-label text-aurelia-info">Audio overview</span>
</div>
<audio controls class="w-full h-8 opacity-80 hover:opacity-100 transition-opacity">
<source src="{path}" type="{mime}">
</audio>
</div>"""


def _render_video(path):
    return f"""
<div class="my-6 border border-aurelia-border rounded-theme overflow-hidden bg-aurelia-bg">
<div class="p-2 border-b border-aurelia-border bg-aurelia-card/50 flex items-center gap-2">
<span class="w-2 h-2 bg-aurelia-info rounded-full animate-pulse"></span>
<span class="field-label text-aurelia-muted">Video overview</span>
</div>
<video controls class="w-full max-h-[400px]">
<source src="{path}" type="video/mp4">
</video>
</div>"""


def _render_image(path):
    return f"""
<div class="my-6 group relative border border-aurelia-border rounded-theme overflow-hidden bg-aurelia-bg/50 hover:border-aurelia-info/50 transition-colors">
<div class="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
<a href="{path}" target="_blank" class="px-2 py-1 bg-aurelia-bg/80 text-[10px] font-mono text-aurelia-text border border-aurelia-border rounded-theme hover:bg-aurelia-info hover:text-aurelia-inverted">Open full size</a>
</div>
<img src="{path}" class="w-full h-auto opacity-90 group-hover:opacity-100 transition-opacity" alt="Gemini Notebook Asset">
</div>"""


# Counts media widgets skipped because the file they point at is gone (see
# resolve_asset / process_gemini_notebook_media). pipeline.py reads this to
# print a build summary -- a silent skip is just a different flavour of the
# invisible failure this whole change is meant to remove.
_missing_asset_count = 0
_missing_assets = []


def get_missing_asset_count():
    return _missing_asset_count


def get_missing_assets():
    return list(_missing_assets)


def reset_missing_asset_count():
    global _missing_asset_count
    _missing_asset_count = 0
    _missing_assets.clear()


def _is_within(candidate, base):
    """True if candidate resolves to a path inside base.

    realpath first, then compare -- resolving symlinks/junctions matters on a
    vault that may be synced through one. normcase because Windows paths are
    case-insensitive and a case-flipped prefix would otherwise slip past.
    """
    real_base = os.path.realpath(base)
    real_candidate = os.path.realpath(candidate)
    return os.path.normcase(real_candidate).startswith(
        os.path.normcase(real_base) + os.sep)


def resolve_asset(path):
    """Returns the on-disk path for a vault-relative asset ref, or None.

    Note bodies reference media as `assets/audio/x.m4a`, which lives at
    `vault/assets/audio/x.m4a` and is copied to `dist/assets/` by
    assets_pipeline.sync_vault_assets(). The ROOT_DIR fallback is kept from
    the original flashcard resolver, which supported decks committed at the
    repo root rather than in the vault -- the five tracked flashcard CSVs
    actually live there, so it is load-bearing, not vestigial.

    Resolve-then-verify: the returned path must sit *under* the base it was
    joined to. A tightened regex alone is not enough, because `assets/` is a
    prefix, not a boundary -- `assets/flashcards/../../../../secrets.csv` still
    matches a bounded character class only if the class admits dots and slashes,
    and containment is what actually settles it (audit finding #20).
    """
    for base in (VAULT_PATH, ROOT_DIR):
        candidate = os.path.join(base, path)
        if not _is_within(candidate, base):
            # A note asked for something outside the asset root -- `../../.env`,
            # or an absolute path os.path.join() happily adopts. Refuse before
            # touching the filesystem, so this can't be used as an existence
            # oracle either. Audit finding #20.
            print(f"   ⚠️  Refusing out-of-tree asset reference: {path}")
            continue
        if os.path.isfile(candidate):
            return candidate
    return None


def _note_missing_asset(path):
    global _missing_asset_count
    _missing_asset_count += 1
    if path not in _missing_assets:
        _missing_assets.append(path)


def _render_flashcards(path):
    """Emits a semantic, sanitize-safe Q/A list for a flashcard deck.

    Phase 3 of the study-tool plan replaced the old 3D-flip strip (an
    all-visible horizontal scroll of tap-to-flip cards, no scoring, no
    keyboard) with a plain <ol> that reads as sensible Q/A pairs with no JS
    at all, plus a `data-deck` asset path. assets/js/flashcards.js finds
    every `.deck` at runtime and upgrades it into an interactive one-card-
    at-a-time widget (reveal, SM-2 rating, shuffle, due filter) -- see that
    file and gardentemplate.html's openNote(). Q/A text is emitted as CHILD
    ELEMENTS (`.deck-q`/`.deck-a`), never as a `data-*` attribute: openNote()
    reads a note's stored body through a <textarea> entity-decode, so an
    escaped quote in an attribute would come back live and break out of it.
    """
    csv_path = resolve_asset(path)
    if csv_path is None:
        # Same treatment as the cells: these two diagnostic branches also
        # emit into the published page.
        return ('<div class="text-aurelia-secondary font-mono text-xs">Flashcard file not found: '
                f'{sanitize_to_text(path)}</div>')

    cards_html = ""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        for row in rows:
            if len(row) < 2:
                continue
            # A CSV cell is plain text by contract, and this HTML is built
            # after sanitize_note_html() has already run on the note body
            # (pipeline._scan_vault), so nothing else ever cleans it: the
            # cells went into the published page exactly as written. They
            # reach two sinks -- the raw #data-storage block parsed at page
            # load, and marked.parse() via openNote()'s entity-decoding
            # <textarea>. Escaping only closes the first; see
            # sanitize.sanitize_to_text.
            q, a = sanitize_to_text(row[0]), sanitize_to_text(row[1])
            cards_html += f'<li class="deck-card"><p class="deck-q">{q}</p><p class="deck-a">{a}</p></li>'
    except Exception as e:
        return ('<div class="text-aurelia-secondary font-mono text-xs">Flashcard file could not be read: '
                f'{sanitize_to_text(str(e))}</div>')

    return (
        '<div class="deck-wrap">'
        '<p class="field-label">Flashcards</p>'
        f'<ol class="deck" data-deck="{path}">{cards_html}</ol>'
        '</div>'
    )


_MEDIA_RENDERERS = {
    "audio": _render_audio,
    "video": _render_video,
    "image": _render_image,
    "flashcards": _render_flashcards,
}


def process_gemini_notebook_media(text):
    """Scans Gemini Notebook headers and converts bare asset paths into
    interactive HTML media (audio players, video, flashcard decks,
    enlargeable images)."""
    processed_text = text
    for item in _MEDIA_MAP:
        pattern = f"({item['header']}\\s*\\n)([\\s\\S]*?)(?=\\n#|$)"

        def replacement_logic(match, item=item):
            header = match.group(1)
            content = match.group(2).strip()
            file_match = re.search(item['regex'], content, re.IGNORECASE)
            if not file_match:
                return match.group(0)

            asset_path = file_match.group(1)

            # Don't render a player/image for a file that isn't there. The
            # 2026 history purge removed the Gemini Notebook audio and
            # mind-map assets from the repo, but the notes still name them --
            # 34 of 38 references currently resolve to nothing, so 15 notes
            # render empty audio controls and broken images. Dropping the
            # bare path leaves the header and surrounding prose intact and
            # the note simply reads as text.
            #
            # Flashcards included: that renderer's own "CSV NOT FOUND" box is
            # a build diagnostic that was being rendered to readers. The count
            # below reports it to the person who can act on it instead.
            if resolve_asset(asset_path) is None:
                _note_missing_asset(asset_path)
                new_content = content.replace(file_match.group(0), "").strip()
                return header + new_content + "\n"

            html_widget = _MEDIA_RENDERERS[item['type']](asset_path)
            new_content = content.replace(file_match.group(0), html_widget)
            return header + new_content + "\n"

        processed_text = re.sub(pattern, replacement_logic, processed_text, flags=re.IGNORECASE)

    return processed_text


_SECTION_HEADER_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)


def wrap_gemini_notebook_sections(text):
    """Wraps each top-level `# Header` section of a Gemini Notebook note in a
    collapsible <details>/<summary> block, so a long note (real ones run to
    15+ sections) can be scanned by header and expanded on demand in the
    modal reader, instead of one long scroll.

    Only the first section starts open (the Lit Review Overview, by
    convention always first) -- everything else starts collapsed.

    A blank line separates <summary>...</summary> from the section body, and
    another precedes the closing </details>: CommonMark (and marked.js, which
    renders this client-side in openNote()) treats <details>/<summary> as a
    raw-HTML block that ends at a blank line, so markdown *inside* the gap --
    bold, bullet lists, and the audio/video/flashcard widget HTML
    process_gemini_notebook_media() already injected -- still gets parsed
    normally, while the collapse/expand chrome itself is just plain HTML.
    This is the same pattern GitHub-flavored markdown uses for collapsible
    sections.
    """
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        return text

    pieces = [text[:matches[0].start()]]
    opened_one = False
    for i, match in enumerate(matches):
        header_text = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_body = text[start:end].strip()

        # Drop a section that has no body at all. This is what a header whose
        # only content was a now-missing media file collapses to (see
        # process_gemini_notebook_media): 10 "Audio Overview" and 6 "Mind Map"
        # sections currently. Keeping them would trade a visibly broken player
        # for an expandable section that opens onto nothing -- still a dead end
        # for the reader, just a quieter one. It also covers the unfilled
        # placeholder headers TPL_Gemini_Notebook's own contract warns about.
        if not section_body:
            continue

        # "First section starts open" means the first section actually
        # *rendered*, not index 0 -- if section 0 were dropped as empty, keying
        # off `i` would leave the note with every section collapsed.
        open_attr = "" if opened_one else " open"
        opened_one = True
        pieces.append(
            f'\n\n<details{open_attr} class="gemini-note-section">\n'
            f'<summary class="gemini-note-summary"><span class="folder-arrow">▶</span> {header_text}</summary>\n\n'
            f'{section_body}\n\n'
            f'</details>\n\n'
        )

    return "".join(pieces)
