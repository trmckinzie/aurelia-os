"""Orchestrates the full build: scan the vault, route notes by type, render pages.

Three pages are published: the Lobby (index.html), the Garden (garden.html),
and About (about.html) -- the last rendered from repo-root profile.json
rather than the vault (see engine/profile.py). Project, protocol, and
transmission notes are recognized by type but intentionally skipped --
there's no page left for them to link to.
"""
import datetime
import gzip
import os
import re
from collections import Counter
from pathlib import Path

from markupsafe import Markup

from engine import cards
from engine.assets_pipeline import organize_assets, prepare_dist, publish_referenced_media
from engine.buildlog import get_warnings, reset_warnings, warn
from engine.cachebust import stamp_asset_versions
from engine.csp import apply_csp
from engine.config import CURRENT_THEME, OUTPUT_DIR, VAULT_PATH, env
from engine.content import (
    build_link_resolver,
    dim_dangling_links,
    get_malformed_count,
    get_missing_asset_count,
    get_missing_assets,
    get_referenced_assets,
    get_resolved_wikilink_targets,
    get_unresolved_wikilink_targets,
    get_wikilink_resolution_counts,
    make_id,
    parse_body,
    parse_frontmatter,
    process_gemini_notebook_media,
    process_wikilinks,
    reset_malformed_count,
    reset_missing_asset_count,
    reset_wikilink_resolution_counts,
    wrap_gemini_notebook_sections,
)
from engine.paths import escapes
from engine.profile import load_profile, person_jsonld
from engine.sanitize import sanitize_note_html
from engine.tailwind_build import compile_css
from engine.vendor import copy_vendor_assets
from engine.textutils import dumps_for_script_tag, truncate
from engine.theming import available_themes, default_theme_slug, generate_theme_css
from engine.user_config import load_user_config


# Vault directories the build never publishes from, whatever a note's
# `publish:` flag says. The publish surface is otherwise one boolean unbounded
# by directory (see docs/ARCHITECTURE.md, "Privacy model"), so a folder whose contents are
# by definition unreviewed needs the guard here, in the build -- .gitignore
# only keeps such notes out of the repo, not off the site.
#
# 20_AURELIA: where aurelia-mcp-server's draft_note writes agent-drafted notes
# (its ARCHITECTURE.md Rule 4). Promoting a draft into 10_GARDEN is a
# deliberate human move, so an agent that emits `publish: true` in its
# frontmatter must not thereby publish itself.
UNPUBLISHED_DIRS = {"20_AURELIA"}

# Compared case-folded, because this is a *denylist* on a case-insensitive
# filesystem -- the direction where a mismatch fails open. NTFS matches
# `20_Aurelia` to `20_AURELIA` when opening the folder but reports whatever
# casing it was first created with, and that casing is sticky: nothing in
# normal use ever changes it back. So a folder created once as `20_Aurelia`
# (by a tool, a restore from backup, a hand-typed mkdir) would pass this
# prune forever, silently, and every agent draft under it would become
# publishable with no error anywhere. Folding is the whole fix.
_UNPUBLISHED_DIRS_FOLDED = frozenset(d.casefold() for d in UNPUBLISHED_DIRS)


def _scan_vault():
    """Walks the vault, building a card for every published garden note.

    Two passes: the first reads every note and computes its id (but doesn't
    generate card HTML yet), so the second pass can tell each card which
    linked-note IDs actually exist and are published. Without that, a
    Related/Concepts/Key Works pill would have no way to know whether its
    target is real -- see cards.link_pill().
    """
    reset_malformed_count()
    reset_missing_asset_count()
    reset_wikilink_resolution_counts()
    pending = []

    # Resolved once, outside the walk: every note found below has to prove it
    # really lives under this directory. os.walk's followlinks=False is no
    # defense on Windows, where a junction is not a symlink -- see
    # engine/paths.py. Whatever a note's `publish:` flag says, a file outside
    # the vault was never reviewed as vault content, and this build's output
    # is a public website.
    vault_root = Path(VAULT_PATH).resolve()

    for root, dirs, files in os.walk(VAULT_PATH):
        # Prune in place so os.walk never descends -- cheaper than filtering
        # per-file, and it covers nested subfolders for free. Directories
        # that resolve outside the vault are pruned for the same reason, and
        # here rather than per-file so the walk never enters them at all.
        #
        # Sorted, not just filtered: os.walk's own directory order is
        # whatever the filesystem happens to hand back, which differs
        # between machines (and isn't even guaranteed stable on one). This
        # walk's order feeds `pending` below, which in turn decides alias/
        # title-suffix ambiguity (content.build_link_resolver -- the first
        # colliding note wins) and the referencing order of backlinks, so an
        # unsorted walk made the same vault build to different output on
        # Windows vs. CI. See tests/test_pipeline.py's byte-identical-build
        # guard (roadmap S09).
        dirs[:] = sorted(
            d for d in dirs
            if d.casefold() not in _UNPUBLISHED_DIRS_FOLDED
            and not escapes(os.path.join(root, d), vault_root)
        )

        for filename in sorted(files):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            if escapes(filepath, vault_root):
                # A file-level link that points out of the tree. The pruning
                # above cannot catch this one: os.walk lists it as a plain
                # file of the directory it sits in.
                warn(f"Refusing note that resolves outside the vault: {filepath}")
                continue

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            meta = parse_frontmatter(content, source=os.path.relpath(filepath, VAULT_PATH))
            if not meta.get("publish"):
                continue

            # Sanitize here -- before process_wikilinks() and the media/section
            # passes below, not after. Those passes inject the engine's OWN
            # HTML into the body (openNote() buttons, <audio>/<video>/<img>
            # widgets, flashcard flip handlers, <details> wrappers), which
            # carries exactly what a sanitizer removes: event handlers and
            # tags outside nh3's allowlist. Cleaning the finished body would
            # strip the site's own features; cleaning the raw note first
            # cleans the untrusted half and leaves the trusted half alone.
            # See engine/sanitize.py. Audit finding #21.
            body = sanitize_note_html(parse_body(content))
            note_type = str(meta.get("type", "unknown")).lower().strip()

            if "project" in note_type or "protocol" in note_type or "transmission" in note_type:
                continue  # no page left to route these to

            note_id = make_id(filename)
            title = filename.replace(".md", "").replace("_", " ")

            raw_search = re.sub(r'[*#_`\[\]]', '', body)
            raw_search = re.sub(r'<[^>]+>', '', raw_search)
            # Tags live in frontmatter, stripped out before `body` -- append
            # them so a search for "neuroscience" finds notes tagged
            # topic/neuroscience even if the word never appears in the prose.
            tag_text = ' '.join(str(t) for t in meta.get("tags", []))
            full_search_text = f"{raw_search} {tag_text}".replace('\n', ' ').replace('"', "").replace("'", "").lower()

            # Coerced str -> [str] the same way parse_frontmatter already
            # coerces `tags` -- an author writing a single alias unquoted as
            # `aliases: Some Alias` is valid YAML (a bare string), not a list.
            aliases = meta.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            aliases = [str(a).strip() for a in aliases if str(a).strip()]

            # Wikilink resolution (process_wikilinks + the Gemini media/
            # section passes) is deliberately NOT done here. An alias or a
            # "Base (...)" title suffix can point at a note this walk hasn't
            # reached yet, so build_link_resolver() needs every pending
            # note's id/title/aliases at once -- see the second pass below.
            pending.append({
                "meta": meta,
                "filename": filename,
                "note_id": note_id,
                "title": title,
                "note_type": note_type,
                "body": body,
                "aliases": aliases,
                "full_search_text": full_search_text,
            })

    # Second pass: now that every published note's id/title/aliases is
    # known, resolve wikilinks (aliases, unique title-suffix bases -- see
    # content.build_link_resolver) and run the Gemini Notebook media/section
    # passes, which depend on wikilink-resolved bodies for their own regex
    # scans same as before.
    resolve = build_link_resolver(pending)
    for p in pending:
        processed_body = process_wikilinks(p["body"], resolve)
        # The card reads this snapshot, not processed_body. The two Gemini
        # passes below rewrite the note's `# Header` lines into
        # <details>/<summary> chrome, and extract_gemini_notebook_data()
        # matches on a literal `#` -- so running the extractor on the wrapped
        # body silently returned nothing for both of the card's fields, i.e.
        # "Synthesis data pending." and "No Studio outputs yet" on all 15
        # published Gemini notes from the day collapsible sections shipped
        # (4ecc9d6) until this snapshot existed. The content was never
        # missing; the header the extractor anchors on was.
        #
        # It also keeps the raw `assets/...` reference lines intact, which is
        # what lets the card ask resolve_asset() whether a Studio output
        # actually exists before advertising it -- process_gemini_notebook_media
        # has by then replaced a live one with widget HTML and a purged one
        # with nothing, and neither is answerable.
        #
        # Identical to processed_body for every other note type, which run no
        # passes between here and there.
        p["card_body"] = processed_body
        if "gemini-notebook" in p["note_type"]:
            processed_body = process_gemini_notebook_media(processed_body)
            processed_body = wrap_gemini_notebook_sections(processed_body)
        p["processed_body"] = processed_body

    known_ids = {p["note_id"] for p in pending}

    # The link graph is built HERE, before card generation, because a card
    # now shows its own connection count and needs the degree at render
    # time. It used to run afterwards, on the finished cards.
    #
    # Deliberately still one scan. The obvious alternative -- a second regex
    # pass over the bodies just to count links -- is exactly what
    # _build_link_graph's docstring says was consolidated away, so this
    # reuses that function unchanged (it needs only id/title/body) and the
    # results are handed back to build_all rather than recomputed there.
    #
    # It reads processed_body, where the previous call read the dimmed body
    # (dim_dangling_links rewrites unknown-target openNote() buttons into
    # spans). That means strictly more candidate targets reach the function
    # -- which changes nothing, because it already discards any target not
    # in `known`. Verified identical: see tests/test_pipeline.py.
    link_input = [
        {"id": p["note_id"], "title": p["title"], "body": p["processed_body"]}
        for p in pending
    ]
    backlinks, edges = _build_link_graph(link_input)
    degree = _degree_from_edges(edges)

    garden_cards = []
    for p in pending:
        card_html, resolved_type = cards.generate_garden_card_html(
            p["meta"], p["filename"], p["note_id"], p["card_body"], known_ids,
            connections=degree.get(p["note_id"], 0),
            created=str(p["meta"].get("created", "")),
        )
        garden_cards.append({
            "html": card_html,
            # Marked safe here rather than inside dim_dangling_links(), which
            # is a generic string transform and cannot vouch for anything.
            # This is the end of the chain that can: the note body was
            # sanitized on the way in (see sanitize_note_html above), and
            # everything added since -- wikilink buttons, media widgets,
            # section wrappers, this dimming pass -- is HTML the engine wrote
            # itself.
            "body": Markup(dim_dangling_links(p["processed_body"], known_ids)),
            "id": p["note_id"],
            "title": p["title"],
            "link": f"garden.html#{p['note_id']}",
            # resolved_type, not p["meta"]["type"]: generate_garden_card_html()
            # returns it rather than mutating meta (S09) -- it's the type
            # this card actually rendered as, including the daily-bridge
            # filename-shape and type/* tag fallbacks, which meta's own
            # `type:` key alone does not capture.
            "type": resolved_type.upper(),
            "tags": p["meta"].get("tags", []),
            "maturity": cards._maturity_slug(p["meta"]),
            "desc": p["full_search_text"],
            "connections": degree.get(p["note_id"], 0),
        })

    return garden_cards, backlinks, edges


# Every note link the engine renders carries its target in data-note (see
# content.process_wikilinks and cards.link_pill); this is the one pattern
# the backlinks index and the graph are built from.
_OPEN_NOTE_RE = re.compile(r'data-note="([^"]+)"')


def _build_link_graph(garden_cards):
    """Single pass over every note body extracting data-note targets, used
    to derive both the backlinks index and the knowledge-graph edges --
    these used to be two separate functions each doing their own regex scan
    and per-source dedup over the same data, which meant a build with N
    notes paid for that scan twice for no reason.

    Returns (backlinks, edges):
      backlinks: {note_id: [{id, title}, ...]} for every note with at least
        one incoming link, in referencing order. Powers the modal's
        "Referenced By" section (gardentemplate.html) -- the core
        personal-wiki feature of discovering a note from what points at it,
        not just what it points to.
      edges: [{source, target}] deduped undirected pairs, feeding the
        knowledge-graph view.
    """
    known = {c['id'] for c in garden_cards}
    id_to_title = {c['id']: c['title'] for c in garden_cards}
    backlinks = {c['id']: [] for c in garden_cards}
    edges = []
    seen_pairs = set()

    for c in garden_cards:
        targets_seen = set()
        for target_id in _OPEN_NOTE_RE.findall(c['body']):
            if target_id == c['id'] or target_id not in known or target_id in targets_seen:
                continue
            targets_seen.add(target_id)
            backlinks[target_id].append({"id": c['id'], "title": id_to_title[c['id']]})

            pair = tuple(sorted((c['id'], target_id)))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                edges.append({"source": pair[0], "target": pair[1]})

    backlinks = {note_id: refs for note_id, refs in backlinks.items() if refs}
    return backlinks, edges


def _degree_from_edges(edges):
    """{note_id: number of links touching it}, counting both endpoints.

    Shared by the Lobby's hub list and the per-card connection count, which
    otherwise derive the same number from the same edges two different ways.
    """
    degree = Counter()
    for edge in edges:
        degree[edge['source']] += 1
        degree[edge['target']] += 1
    return degree


def _build_graph_index(garden_cards, edges):
    """Builds the node/edge data for the Garden's knowledge-graph view and
    the modal's "Related by Topic" section.

    Nodes carry id/title/type/tags -- deliberately still no body text (see
    _build_search_index for the same size-conscious precedent), but tags
    are small and let the client compute topic overlap between notes
    without a second embedded index.
    """
    nodes = [{"id": c['id'], "title": c['title'], "type": c['type'].lower(), "tags": c['tags']} for c in garden_cards]
    return {"nodes": nodes, "edges": edges}


_DAILY_LOG_ID_RE = re.compile(r'^note-\d{4}-\d{2}-\d{2}')

# (slug, label) in the exact order and wording of the Garden's own filter
# chips (system/templates/pages/gardentemplate.html's .filter-btn row) --
# see _lobby_type_counts.
_LOBBY_TYPE_SLUGS = [
    ("concept", "Concepts"),
    ("source", "Sources"),
    ("author", "Authors"),
    ("discipline", "Disciplines"),
    ("deep-dive", "Deep dives"),
    ("gemini-notebook", "Gemini notebooks"),
    ("daily-bridge", "Daily logs"),
]


def _lobby_type_counts(garden_cards):
    """[{slug, label, count}, ...] for the Lobby's Garden card -- one entry
    per type with at least one published note, in Garden-filter order.

    Matches each card the same way the Garden's own client-side filter does
    (gardentemplate.html: `itemType.includes(currentType)`, a substring test
    against the card's data-type) rather than an exact-equality check, so a
    count here always equals what clicking through to
    garden.html?type=<slug> actually shows -- including "source" counting
    `source/book` notes and "daily-bridge" counting notes whose frontmatter
    type is literally that slug.
    """
    types_lower = [str(c.get('type', '')).lower() for c in garden_cards]
    counts = []
    for slug, label in _LOBBY_TYPE_SLUGS:
        count = sum(1 for t in types_lower if slug in t)
        if count:
            counts.append({"slug": slug, "label": label, "count": count})
    return counts


def _build_lobby_context(garden_cards, graph_index):
    """Aggregate, size-conscious stats for the Lobby's "Cortex Status" panel.

    Deliberately mirrors the size discipline of _build_search_index: no note
    bodies, just counts and a handful of hub notes.
    """
    maturity_counts = Counter(c['maturity'] for c in garden_cards if c['maturity'])

    # Hub notes: the most-connected nodes in the wikilink graph, surfaced as
    # "start here" entry points -- the personal-wiki equivalent of a Map of
    # Content, derived rather than hand-maintained.
    node_lookup = {n['id']: n for n in graph_index['nodes']}
    degree = _degree_from_edges(graph_index['edges'])
    hub_notes = [
        {"id": note_id, "title": node_lookup[note_id]['title'], "type": node_lookup[note_id]['type'], "connections": count}
        for note_id, count in degree.most_common(5)
    ]

    return {
        "total_notes": len(garden_cards),
        "maturity_counts": {
            "seed": maturity_counts.get("seed", 0),
            "growing": maturity_counts.get("growing", 0),
            "evergreen": maturity_counts.get("evergreen", 0),
        },
        "hub_notes": hub_notes,
        "type_counts": _lobby_type_counts(garden_cards),
    }


def _build_search_index(garden_cards, profile):
    master_index = [
        {"title": "Home", "url": "index.html", "type": "SYSTEM", "tags": ["home", "root"], "desc": "Start page"},
        {
            "title": "Garden",
            "url": "garden.html",
            "type": "SYSTEM",
            "tags": ["notes", "writing"],
            "desc": "Published notes: concepts, sources, authors, deep dives",
        },
        {
            "title": "About // " + profile["identity"]["name"],
            "url": "about.html",
            "type": "SYSTEM",
            "tags": ["about", "profile"],
            "desc": profile["identity"]["headline"],
        },
    ]

    for c in garden_cards:
        # c['desc'] is the note's *entire* body text (see full_search_text
        # above) -- that's needed in full for garden.html's own data-search
        # attribute (deep in-page search stays unaffected), but this
        # master_index gets embedded into every page's HTML via base.html's
        # command palette script, so duplicating full note bodies here
        # bloated every single page. Snippet only.
        master_index.append({"title": c['title'], "url": c['link'], "type": "GARDEN", "tags": c['tags'], "desc": truncate(c['desc'], 200)})

    return master_index


def _build_deep_search_index(garden_cards):
    """{note_id: full lowercased body text} for the Garden's in-page deep search.

    This used to live in a `data-search` attribute on every card -- and,
    because the tree view renders the same notes again, on every tree row
    too. That put the entire text of the vault into the HTML *twice*: 1.82 MB
    of attributes across 490 elements, 35% of garden.html, with one note's
    attribute alone running to 123,699 characters. The browser also had to
    parse all of it into the DOM.

    Emitting it once as JSON keyed by note id lets both views look a note up
    by `data-id` instead of carrying its own copy. Full-text search is
    preserved exactly -- this is deliberately the whole body, not the
    200-char snippet the command palette uses (see _build_search_index).
    """
    return {c['id']: c['desc'] for c in garden_cards}


def _build_commit_stamp():
    """(commit, commit_time) from the environment, or (None, None).

    Set by CI (.github/workflows/deploy.yml and redeploy.yml) from the
    commit actually being built -- AURELIA_BUILD_COMMIT is its full SHA,
    AURELIA_BUILD_COMMIT_TIME is that commit's own committer timestamp
    (`git show -s --format=%cI` -- the committer date, not the author date,
    which is what CI actually sets this from), never the wall-clock time the
    runner happened to build at. Two CI runs of the same commit therefore
    stamp identical values, which is what keeps this compatible with S09's
    byte-identical-build goal. A local `python build.py` sets neither, so
    dist/ is unchanged from before this existed -- see docs/DECISIONS.md
    item 28.
    """
    commit = os.environ.get("AURELIA_BUILD_COMMIT", "").strip()
    commit_time = os.environ.get("AURELIA_BUILD_COMMIT_TIME", "").strip()
    if not commit or not commit_time:
        return None, None
    return commit, commit_time


def _site_root(user_config, environ=None):
    """The path the site is served from, for the 404 page's absolute links.

    "/" on a custom domain and on a user/organisation site (<name>.github.io);
    "/<repo>/" on a project site, which is where this one lives. CI knows the
    repository through GITHUB_REPOSITORY; a local build has none and previews
    at "/".
    """
    environ = os.environ if environ is None else environ
    site = user_config.get("site") if isinstance(user_config, dict) else None
    if isinstance(site, dict) and site.get("domain"):
        return "/"
    repo = environ.get("GITHUB_REPOSITORY", "").strip().split("/", 1)
    if len(repo) == 2 and repo[1] and not repo[1].lower().endswith(".github.io"):
        return f"/{repo[1]}/"
    return "/"


def _write_deep_search_index(deep_search_json):
    """Writes the deep-search index to its own JS file rather than inlining it.

    At ~0.95 MB it is the single largest thing on the Garden page after the
    note bodies. Inline, it is re-downloaded and re-parsed on every visit and
    inflates the HTML the browser must parse before rendering anything. As a
    separate file it is cached across visits (and versioned by the ?v= hash
    of its own content, see engine/cachebust.py, so a rebuild that changes a
    note still invalidates it).

    Returns the number of bytes written.
    """
    js_dir = os.path.join(OUTPUT_DIR, "assets", "js")
    os.makedirs(js_dir, exist_ok=True)
    path = os.path.join(js_dir, "search-index.js")
    payload = f"window.DEEP_SEARCH_INDEX = {deep_search_json};\n"
    encoded = payload.encode("utf-8")
    # newline="\n": text mode otherwise translates '\n' to the platform
    # line ending, which is CRLF on Windows -- the same commit would then
    # build to different bytes there than on CI's Linux runner (roadmap S09).
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(payload)
    return len(encoded)


# Backlog B04 (docs/DECISIONS.md item 32, decided 2026-10-01): garden.html
# carries every note body so a note opens with no network request, and that
# stays so until the page's compressed size passes 1 MB. The build measures
# the page the way a visitor receives it, after the asset-version stamp, and
# goes through warn() past the limit so CI's --strict build fails and forces
# the revisit rather than letting the page grow unnoticed. The limit is
# 1 MiB, which is what "1 MB" meant when the 580 KB figure was recorded.
GARDEN_COMPRESSED_LIMIT_BYTES = 1024 * 1024

# What report_page_sizes() measures, as (label, path under dist/). The index
# is listed too so the two numbers that decide B04's trade-off sit on
# adjacent lines of every build log.
_SIZED_OUTPUTS = (
    ("Garden page", "garden.html"),
    ("Deep-search index", os.path.join("assets", "js", "search-index.js")),
)


def compressed_size(data):
    """Bytes gzip produces for `data` at level 6, the level GitHub Pages and
    most CDNs serve with; close enough to what a visitor downloads to decide
    the B04 threshold on, and deterministic (mtime=0) so a build log diff
    shows a real change in the page and not the clock."""
    return len(gzip.compress(data, compresslevel=6, mtime=0))


def report_page_sizes(output_dir=None, limit=GARDEN_COMPRESSED_LIMIT_BYTES):
    """Prints the raw and compressed size of garden.html and the deep-search
    index, and warns when the compressed Garden page passes `limit`.

    Returns {path: compressed_bytes} so a test (or a future dashboard) can
    read the numbers without parsing the log. Run after stamp_asset_versions()
    so the bytes measured are the bytes served.
    """
    output_dir = OUTPUT_DIR if output_dir is None else output_dir
    sizes = {}
    for label, rel_path in _SIZED_OUTPUTS:
        with open(os.path.join(output_dir, rel_path), "rb") as f:
            data = f.read()
        compressed = compressed_size(data)
        sizes[rel_path] = compressed
        print(f"   + {label}: {compressed / 1024:,.0f} KB compressed, {len(data) / 1024:,.0f} KB raw"
              f" -> {rel_path.replace(os.sep, '/')}")
    garden = sizes["garden.html"]
    print(f"   + Garden page limit: {limit / 1024:,.0f} KB compressed (backlog B04)")
    if garden > limit:
        warn(f"garden.html is {garden / 1024:,.0f} KB compressed, past the {limit / 1024:,.0f} KB "
             "threshold decided 2026-10-01 (docs/DECISIONS.md item 32, backlog B04). The first "
             "step is to move the note bodies into one separately cached file, the way the "
             "deep-search index already is.")
    return sizes


def _render_pages(user_config, garden_cards, json_index, backlinks_json, graph_json, lobby_stats, deep_search_json, profile,
                   build_commit=None, build_commit_time=None, has_social_preview=True):
    # Its size is reported with garden.html's by report_page_sizes(), once
    # the build has finished writing both.
    _write_deep_search_index(deep_search_json)

    pages = [
        # `profile` also goes to the Lobby: its first module card is a short
        # profile summary that links through to about.html, read from the
        # same profile.json rather than duplicated into user_config.json.
        #
        # page_title feeds base.html's default {% block title %}: None means
        # "use the site name (plus tagline)" -- the Lobby and About both set
        # their own {% block title %} anyway (see indextemplate.html /
        # abouttemplate.html), so it's explicit here mainly for symmetry with
        # the Garden, which relies on this value alone since it has no title
        # block of its own.
        ("pages/indextemplate.html", "index.html", {
            "stats": lobby_stats, "profile": profile, "page_title": None,
        }),
        ("pages/gardentemplate.html", "garden.html", {
            "cards": garden_cards, "backlinks_index": backlinks_json, "graph_index": graph_json,
            "page_title": "The Garden",
        }),
        ("pages/abouttemplate.html", "about.html", {
            "profile": profile, "person_jsonld": dumps_for_script_tag(person_jsonld(profile)),
            "page_title": None,
        }),
        # The only page a visitor can load from any depth (a missing URL two
        # folders down still gets this file), so it alone links by absolute
        # path -- see _site_root().
        ("404.html", "404.html", {"page_title": None, "site_root": _site_root(user_config)}),
    ]

    # The build's own run date, not each page's render timestamp -- a footer
    # copyright year that could differ page-to-page on the same deploy would
    # look like a bug, not a feature.
    build_year = datetime.date.today().year

    for template_name, output_name, context in pages:
        try:
            context["theme"] = CURRENT_THEME
            context["theme_key"] = default_theme_slug()
            context["available_themes_json"] = dumps_for_script_tag(available_themes())
            context["search_index"] = json_index
            context["config"] = user_config
            context.setdefault("site_root", "")
            context["build_year"] = build_year
            context["build_commit"] = build_commit
            context["build_commit_time"] = build_commit_time
            context["has_social_preview"] = has_social_preview

            template = env.get_template(template_name)
            rendered_html = template.render(active_page=output_name.replace(".html", ""), **context)

            # newline="\n": same reproducibility concern as
            # _write_deep_search_index -- text mode would otherwise write
            # CRLF on Windows and LF on CI for an identical commit.
            with open(os.path.join(OUTPUT_DIR, output_name), "w", encoding="utf-8", newline="\n") as f:
                f.write(rendered_html)
            print(f"   ✅ Deployed: {output_name}")
        except Exception as e:
            # Fail the build. This used to print and continue, which meant
            # `python build.py` exited 0 with a page missing or half-written
            # -- and CI, which only runs the build, deployed that dist/ to
            # the live site under a green check. A template typo has already
            # been swallowed here once mid-session, with the build reporting
            # success.
            #
            # Raising on the first failure is deliberate: the remaining
            # pages are not worth rendering into a dist/ that must not ship,
            # and a partial site is the outcome being prevented. The message
            # is re-stated on the exception rather than left only in the
            # printed line, so it survives into CI's failure summary.
            print(f"   ❌ Failed: {output_name} -> {e}")
            raise RuntimeError(f"Render failed for {output_name}: {e}") from e


# A hostname label: starts and ends with a letter/digit, 1-63 chars, only
# letters/digits/hyphens in between. Deliberately lowercase-only -- GitHub
# Pages' own CNAME file is case-insensitive in practice, but accepting mixed
# case here would mean either silently lowercasing a value the user typed
# (surprising) or writing a CNAME that doesn't byte-for-byte match what they
# configured at their registrar (confusing to debug). Rejecting uppercase and
# telling the user to fix user_config.json is simpler than either.
_HOSTNAME_LABEL_RE = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$')


def _is_valid_domain(value):
    """True if `value` is a bare lowercase ASCII hostname suitable for a
    GitHub Pages CNAME file: no scheme, no path, no port, at least two
    labels, each label 1-63 chars of [a-z0-9-] not starting/ending with '-',
    total length <=253.
    """
    if not isinstance(value, str) or not value:
        return False
    if len(value) > 253:
        return False
    # A scheme, path, or port means this is a URL, not a bare hostname --
    # GitHub Pages' CNAME file wants the hostname alone.
    if "://" in value or "/" in value or ":" in value:
        return False
    labels = value.split(".")
    if len(labels) < 2:
        return False
    return all(_HOSTNAME_LABEL_RE.match(label) for label in labels)


def _write_cname(user_config):
    """Writes dist/CNAME for a custom domain, read from user_config.json's
    optional site.domain -- the file GitHub Pages reads to serve the site
    from that domain instead of the default *.github.io one.

    site.domain absent or "" means no custom domain: writes nothing. Since
    this runs right after prepare_dist() (which wipes and recreates
    OUTPUT_DIR from scratch), there is never a stale CNAME left over from an
    earlier build with a domain configured.

    A non-empty domain that fails validation raises RuntimeError naming the
    value -- a malformed CNAME is silently ignored by GitHub Pages, which
    would look like "the custom domain just doesn't work" with no error
    anywhere, so this fails the build loudly instead.
    """
    site = user_config.get("site") if isinstance(user_config, dict) else None
    domain = site.get("domain") if isinstance(site, dict) else None
    domain = domain or ""

    if not isinstance(domain, str):
        raise RuntimeError(f"user_config.json: site.domain must be a string, got {domain!r}")
    if domain == "":
        return

    if not _is_valid_domain(domain):
        raise RuntimeError(
            f"user_config.json: site.domain {domain!r} is not a valid custom domain "
            "(expected a bare lowercase hostname, e.g. 'example.com', with no scheme/path/port)"
        )

    with open(os.path.join(OUTPUT_DIR, "CNAME"), "w", encoding="utf-8", newline="\n") as f:
        f.write(domain + "\n")
    print(f"   + Custom domain: {domain} -> dist/CNAME")


class StrictBuildError(RuntimeError):
    """The build finished but printed warnings, and strict mode was on."""


# Values of AURELIA_SKIP_DROPZONE that mean "no, actually do sort". Anything
# else non-empty means skip -- `AURELIA_SKIP_DROPZONE=1` is the common form.
_ENV_FALSE = {"", "0", "false", "no", "off"}


def skip_dropzone_env():
    """True if the environment asks the build not to touch the drop zone."""
    return os.environ.get("AURELIA_SKIP_DROPZONE", "").strip().lower() not in _ENV_FALSE


def build_all(sort_dropzone=None, strict=False):
    """Builds the site into dist/.

    organize_assets() is the one step in this pipeline that WRITES to vault/:
    it moves files out of vault/99_DROP_ZONE into vault/assets/<kind>/. That
    makes an ordinary `python build.py` a vault mutation, which is a surprise
    for a command whose job is to produce dist/, and a problem anywhere the
    vault must stay untouched -- CI, a review checkout, an agent session under
    a no-vault-edits instruction (audit finding #26).

    sort_dropzone=False (build.py --no-sort, or AURELIA_SKIP_DROPZONE=1) skips
    it. Everything else in the pipeline only reads the vault, so the rendered
    site is identical apart from assets still sitting in the drop zone.
    Leaving it None defers to the environment variable.

    strict=True (build.py --strict, which CI passes) raises StrictBuildError
    after the build if anything called buildlog.warn(), so a degraded site
    cannot deploy. Off by default so a local build stays forgiving. Hard
    failures (a bad user_config.json or profile.json, a render error, a dist/
    that cannot be wiped) raise whatever strict says.
    """
    if sort_dropzone is None:
        sort_dropzone = not skip_dropzone_env()
    reset_warnings()

    print("------------------------------------------------")
    print("SITE BUILD ENGINE")
    print("------------------------------------------------")

    user_config = load_user_config()
    print(f"   + Identity Loaded: {user_config['author']['name']}")

    # Fatal by design (see engine/profile.py's module docstring): About is
    # one of only three published pages, so a missing/invalid profile.json
    # must abort the whole build rather than ship a broken or stale page.
    # Loaded before any vault work so a bad profile fails fast.
    profile = load_profile()
    print(f"   + Profile Loaded: {profile['identity']['name']}")

    prepare_dist()
    # Checked right after prepare_dist(), which is what actually decides
    # whether assets/images/ (and anything in it) made it into dist/ -- see
    # that function's PUBLISHABLE_ASSET_DIRS allowlist. deploy.py's factory
    # clone deliberately does not copy repo-root images into its own
    # assets/images/ (privacy: the real site's is the owner's own banner),
    # so a fresh clone has no file here and base.html's unconditional
    # <meta property="og:image"> named one anyway -- a link that always
    # 404s. has_social_preview gates that tag instead (roadmap S09).
    has_social_preview = os.path.isfile(
        os.path.join(OUTPUT_DIR, "assets", "images", "social-preview.jpg"))
    copy_vendor_assets()
    _write_cname(user_config)
    if sort_dropzone:
        organize_assets()
    else:
        print("\n⏭️  Drop Zone sort skipped -- vault/ will not be modified")

    garden_cards, backlinks, edges = _scan_vault()
    # After the scan, not before: the scan is what records which media the
    # published notes reference, and only those files are published
    # (backlog B06; assets_pipeline.publish_referenced_media).
    publish_referenced_media(get_referenced_assets())
    garden_cards.sort(key=lambda x: x['title'].lower())

    print(f"   + Indexing: {len(garden_cards)} Notes")
    malformed = get_malformed_count()
    if malformed:
        # Loud on purpose: a bulk vault edit (e.g. a frontmatter migration)
        # that breaks YAML somewhere silently drops that note from the site
        # with nothing but the per-note warning above -- easy to miss in
        # scroll-back. This line is the summary a human will actually see.
        print(f"   ⚠️  {malformed} note(s) skipped for malformed frontmatter -- see warnings above")

    missing_assets = get_missing_asset_count()
    if missing_assets:
        # Same reasoning as the counter above. These are media widgets that
        # were NOT rendered because the file a note names is gone (the 2026
        # history purge removed the Gemini Notebook audio and mind maps).
        # Skipping them is right -- an empty audio player helps nobody -- but
        # skipping them silently would just replace a visible broken control
        # with an invisible absence, so the count is surfaced here.
        unique = get_missing_assets()
        warn(f"{missing_assets} media widget(s) skipped -- {len(unique)} asset file(s) missing")
        for path in unique[:3]:
            print(f"        - {path}")
        if len(unique) > 3:
            print(f"        ... and {len(unique) - 3} more")

    # Alias/suffix resolution (see content.build_link_resolver) closes some
    # of the gap between what Travis wrote and what the site could already
    # show as a live link; this reports how much, and points at the report
    # that lists what's still dangling -- see tools/vault_health.py.
    alias_resolved, suffix_resolved = get_wikilink_resolution_counts()
    resolved_targets = get_resolved_wikilink_targets()
    unresolved_targets = get_unresolved_wikilink_targets()
    print(f"   + Wikilinks: {alias_resolved + suffix_resolved} link occurrences "
          f"({len(resolved_targets)} distinct targets) resolved via alias or title suffix; "
          f"{len(unresolved_targets)} targets still unresolved (tools/vault_health.py --report pending)")

    master_index = _build_search_index(garden_cards, profile)
    json_index = dumps_for_script_tag(master_index)

    deep_search_json = dumps_for_script_tag(_build_deep_search_index(garden_cards))

    backlinks_json = dumps_for_script_tag(backlinks)
    graph_index = _build_graph_index(garden_cards, edges)
    graph_json = dumps_for_script_tag(graph_index)

    lobby_stats = _build_lobby_context(garden_cards, graph_index)

    build_commit, build_commit_time = _build_commit_stamp()
    _render_pages(user_config, garden_cards, json_index, backlinks_json, graph_json, lobby_stats, deep_search_json, profile,
                  build_commit=build_commit, build_commit_time=build_commit_time,
                  has_social_preview=has_social_preview)

    # Every theme in THEME_CONFIG, not just the default -- lets the nav's
    # switcher change themes at runtime with a pure CSS swap, no rebuild.
    generate_theme_css()
    print("   + Theme variables generated for all themes.")

    # Runs last: scans the just-rendered dist/**/*.html for utility classes,
    # including ones cards.py assembled dynamically (now literal text in the
    # output), and compiles the final CSS over the passthrough copy.
    compile_css()

    # After the compile: main.css is only final now, and its hash (with every
    # other asset's) goes into the URLs the pages already carry as tokens.
    stamp_asset_versions(OUTPUT_DIR)

    # After the stamp and before the size report: the policy's hashes are of
    # each page's final inline blocks, and the report measures final bytes.
    apply_csp(OUTPUT_DIR)
    report_page_sizes()

    warnings = get_warnings()
    if warnings:
        print(f"\n⚠️  {len(warnings)} build warning(s):")
        for message in warnings:
            print(f"   - {message}")
        if strict:
            raise StrictBuildError(
                f"{len(warnings)} build warning(s) under --strict; fix them before deploying "
                f"(first: {warnings[0]})"
            )

    print("\n✅ SYSTEM SYNC COMPLETE.")
