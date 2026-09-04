"""Orchestrates the full build: scan the vault, route notes by type, render pages.

Only the Lobby (index.html) and Garden (garden.html) are published. Project,
protocol, and transmission notes are recognized by type but intentionally
skipped -- there's no page left for them to link to.
"""
import hashlib
import os
import re
from collections import Counter

from markupsafe import Markup

from engine import cards
from engine.assets_pipeline import organize_assets, prepare_dist, sync_vault_assets
from engine.config import CURRENT_THEME, OUTPUT_DIR, ROOT_DIR, VAULT_PATH, env, load_user_config
from engine.content import (
    dim_dangling_links,
    get_malformed_count,
    get_missing_asset_count,
    get_missing_assets,
    make_id,
    parse_body,
    parse_frontmatter,
    process_gemini_notebook_media,
    process_wikilinks,
    reset_malformed_count,
    reset_missing_asset_count,
    wrap_gemini_notebook_sections,
)
from engine.sanitize import sanitize_note_html
from engine.tailwind_build import compile_css
from engine.textutils import dumps_for_script_tag, truncate
from engine.theming import available_themes, default_theme_slug, generate_theme_css


# Vault directories the build never publishes from, whatever a note's
# `publish:` flag says. The publish surface is otherwise one boolean unbounded
# by directory (see CLAUDE.md's privacy model), so a folder whose contents are
# by definition unreviewed needs the guard here, in the build -- .gitignore
# only keeps such notes out of the repo, not off the site.
#
# 20_AURELIA: where aurelia-mcp-server's draft_note writes agent-drafted notes
# (its ARCHITECTURE.md Rule 4). Promoting a draft into 10_GARDEN is a
# deliberate human move, so an agent that emits `publish: true` in its
# frontmatter must not thereby publish itself.
UNPUBLISHED_DIRS = {"20_AURELIA"}


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
    pending = []

    for root, dirs, files in os.walk(VAULT_PATH):
        # Prune in place so os.walk never descends -- cheaper than filtering
        # per-file, and it covers nested subfolders for free.
        dirs[:] = [d for d in dirs if d not in UNPUBLISHED_DIRS]

        for filename in sorted(files):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            meta = parse_frontmatter(content)
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

            processed_body = process_wikilinks(body)
            if "gemini-notebook" in note_type:
                processed_body = process_gemini_notebook_media(processed_body)
                processed_body = wrap_gemini_notebook_sections(processed_body)

            pending.append({
                "meta": meta,
                "filename": filename,
                "note_id": note_id,
                "title": title,
                "processed_body": processed_body,
                "full_search_text": full_search_text,
            })

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
        card_html = cards.generate_garden_card_html(
            p["meta"], p["filename"], p["note_id"], p["processed_body"], p["full_search_text"], known_ids,
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
            "type": str(p["meta"].get("type", "NOTE")).upper(),
            "tags": p["meta"].get("tags", []),
            "maturity": cards._maturity_slug(p["meta"]),
            "desc": p["full_search_text"],
            "connections": degree.get(p["note_id"], 0),
        })

    return garden_cards, backlinks, edges


_OPEN_NOTE_RE = re.compile(r"openNote\('([^']+)'\)")


def _build_link_graph(garden_cards):
    """Single pass over every note body extracting openNote() targets, used
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


def _build_lobby_context(garden_cards, graph_index):
    """Aggregate, size-conscious stats for the Lobby's "Cortex Status" panel.

    Deliberately mirrors the size discipline of _build_search_index: no note
    bodies, just counts, a handful of hub notes, and an id/title/maturity
    triple per note (the "review_seed" the client needs to compute its own
    spaced-review teaser from the same localStorage log the Garden uses --
    that log only exists in the browser, so this can't be precomputed here).
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

    log_ids = sorted((c['id'] for c in garden_cards if _DAILY_LOG_ID_RE.match(c['id'])), reverse=True)
    latest_log_date = log_ids[0].replace('note-', '', 1) if log_ids else None

    review_seed = [{"id": c['id'], "title": c['title'], "maturity": c['maturity']} for c in garden_cards]

    return {
        "total_notes": len(garden_cards),
        "maturity_counts": {
            "seed": maturity_counts.get("seed", 0),
            "growing": maturity_counts.get("growing", 0),
            "evergreen": maturity_counts.get("evergreen", 0),
        },
        "hub_notes": hub_notes,
        "latest_log_date": latest_log_date,
        "review_seed": review_seed,
    }


def _build_search_index(garden_cards):
    master_index = [
        {"title": "Home // Mission Control", "url": "index.html", "type": "SYSTEM", "tags": ["home", "root"], "desc": "Main Hub"},
        {"title": "The Garden // Input", "url": "garden.html", "type": "SYSTEM", "tags": ["notes", "writing"], "desc": "Digital Garden"},
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


def _asset_version():
    """A short content hash of the CSS/JS the pages link to, appended to
    those URLs as ?v= so a deploy can't leave a visitor on stale assets.

    This is not a nicety. The pages and their assets are cached
    independently, and neither GitHub Pages nor a plain static server sends
    Cache-Control for them -- so a browser applies *heuristic* freshness and
    may serve a cached utils.js without revalidating at all. A visitor who
    returns after a deploy then gets new HTML calling functions that only
    exist in the new JS, against the old file. Hit exactly that during
    development: new markup calling aureliaReveal() against a cached
    utils.js from before that function existed, which failed silently and
    made an entrance animation look like it worked when it had never run.

    Hashing content rather than using a timestamp means the URL only
    changes when the file actually changes, so unrelated rebuilds don't
    needlessly bust every visitor's cache.
    """
    digest = hashlib.sha256()
    for rel in ("assets/css/main.css", "assets/js/utils.js"):
        path = os.path.join(ROOT_DIR, rel)
        try:
            with open(path, "rb") as f:
                digest.update(f.read())
        except OSError:
            # A missing source file is the asset pipeline's problem to
            # report, not this function's -- fold the path in so the
            # version still changes if it reappears.
            digest.update(rel.encode("utf-8"))
    return digest.hexdigest()[:10]


def _write_deep_search_index(deep_search_json):
    """Writes the deep-search index to its own JS file rather than inlining it.

    At ~0.95 MB it is the single largest thing on the Garden page after the
    note bodies. Inline, it is re-downloaded and re-parsed on every visit and
    inflates the HTML the browser must parse before rendering anything. As a
    separate file it is cached across visits (and versioned by the ?v= hash,
    so a rebuild still invalidates it -- see _asset_version).

    Returns (bytes_written, content_hash). The hash is its OWN, not
    _asset_version(): that one covers main.css/utils.js, which do not change
    when the vault does. Versioning this file by that hash would let a
    visitor keep a cached index from before a note was added or edited --
    the same stale-asset failure ?v= exists to prevent, just moved.
    """
    js_dir = os.path.join(OUTPUT_DIR, "assets", "js")
    os.makedirs(js_dir, exist_ok=True)
    path = os.path.join(js_dir, "search-index.js")
    payload = f"window.DEEP_SEARCH_INDEX = {deep_search_json};\n"
    encoded = payload.encode("utf-8")
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload)
    return len(encoded), hashlib.sha256(encoded).hexdigest()[:10]


def _render_pages(user_config, garden_cards, json_index, backlinks_json, graph_json, lobby_stats, review_seed_json, deep_search_json):
    index_bytes, search_index_version = _write_deep_search_index(deep_search_json)
    print(f"   + Deep-search index: {index_bytes / 1024:.0f} KB -> assets/js/search-index.js (cached separately)")

    pages = [
        ("pages/indextemplate.html", "index.html", {"stats": lobby_stats, "review_seed": review_seed_json}),
        ("pages/gardentemplate.html", "garden.html", {
            "cards": garden_cards, "backlinks_index": backlinks_json, "graph_index": graph_json,
            "search_index_version": search_index_version,
        }),
        ("404.html", "404.html", {}),
    ]

    asset_version = _asset_version()

    for template_name, output_name, context in pages:
        try:
            context["theme"] = CURRENT_THEME
            context["theme_key"] = default_theme_slug()
            context["available_themes_json"] = dumps_for_script_tag(available_themes())
            context["search_index"] = json_index
            context["config"] = user_config
            context["asset_version"] = asset_version

            template = env.get_template(template_name)
            rendered_html = template.render(active_page=output_name.replace(".html", ""), **context)

            with open(os.path.join(OUTPUT_DIR, output_name), "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"   ✅ Deployed: {output_name}")
        except Exception as e:
            print(f"   ❌ Failed: {output_name} -> {e}")


# Values of AURELIA_SKIP_DROPZONE that mean "no, actually do sort". Anything
# else non-empty means skip -- `AURELIA_SKIP_DROPZONE=1` is the common form.
_ENV_FALSE = {"", "0", "false", "no", "off"}


def skip_dropzone_env():
    """True if the environment asks the build not to touch the drop zone."""
    return os.environ.get("AURELIA_SKIP_DROPZONE", "").strip().lower() not in _ENV_FALSE


def build_all(sort_dropzone=None):
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
    """
    if sort_dropzone is None:
        sort_dropzone = not skip_dropzone_env()

    print("------------------------------------------------")
    print("💠 AURELIA OS BUILD ENGINE")
    print("------------------------------------------------")

    prepare_dist()
    if sort_dropzone:
        organize_assets()
    else:
        print("\n⏭️  Drop Zone sort skipped -- vault/ will not be modified")
    sync_vault_assets()

    user_config = load_user_config()

    garden_cards, backlinks, edges = _scan_vault()
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
        print(f"   ⚠️  {missing_assets} media widget(s) skipped -- {len(unique)} asset file(s) missing")
        for path in unique[:3]:
            print(f"        - {path}")
        if len(unique) > 3:
            print(f"        ... and {len(unique) - 3} more")

    master_index = _build_search_index(garden_cards)
    json_index = dumps_for_script_tag(master_index)

    deep_search_json = dumps_for_script_tag(_build_deep_search_index(garden_cards))

    backlinks_json = dumps_for_script_tag(backlinks)
    graph_index = _build_graph_index(garden_cards, edges)
    graph_json = dumps_for_script_tag(graph_index)

    lobby_stats = _build_lobby_context(garden_cards, graph_index)
    review_seed_json = dumps_for_script_tag(lobby_stats.pop("review_seed"))

    _render_pages(user_config, garden_cards, json_index, backlinks_json, graph_json, lobby_stats, review_seed_json, deep_search_json)

    # Every theme in THEME_CONFIG, not just the default -- lets the nav's
    # switcher change themes at runtime with a pure CSS swap, no rebuild.
    generate_theme_css()
    print("   + Theme variables generated for all themes.")

    # Runs last: scans the just-rendered dist/**/*.html for utility classes,
    # including ones cards.py assembled dynamically (now literal text in the
    # output), and compiles the final CSS over the passthrough copy.
    compile_css()

    print("\n✅ SYSTEM SYNC COMPLETE.")
