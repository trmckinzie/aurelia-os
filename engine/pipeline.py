"""Orchestrates the full build: scan the vault, route notes by type, render pages.

Only the Lobby (index.html) and Garden (garden.html) are published. Project,
protocol, and transmission notes are recognized by type but intentionally
skipped -- there's no page left for them to link to.
"""
import os
import re

from engine import cards
from engine.assets_pipeline import organize_assets, prepare_dist, sync_vault_assets
from engine.config import CURRENT_THEME, OUTPUT_DIR, VAULT_PATH, env, load_user_config
from engine.content import make_id, parse_body, parse_frontmatter, process_notebooklm_media, process_wikilinks
from engine.tailwind_build import compile_css
from engine.textutils import dumps_for_script_tag, truncate


def _scan_vault():
    """Walks the vault, building a card for every published garden note.

    Two passes: the first reads every note and computes its id (but doesn't
    generate card HTML yet), so the second pass can tell each card which
    linked-note IDs actually exist and are published. Without that, a
    Related/Concepts/Key Works pill would have no way to know whether its
    target is real -- see cards.link_pill().
    """
    pending = []

    for root, _, files in os.walk(VAULT_PATH):
        for filename in sorted(files):
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            meta = parse_frontmatter(content)
            if not meta.get("publish"):
                continue

            body = parse_body(content)
            note_type = str(meta.get("type", "unknown")).lower().strip()

            if "project" in note_type or "protocol" in note_type or "transmission" in note_type:
                continue  # no page left to route these to

            note_id = make_id(filename)
            title = filename.replace(".md", "").replace("_", " ")

            raw_search = re.sub(r'[*#_`\[\]]', '', body)
            raw_search = re.sub(r'<[^>]+>', '', raw_search)
            full_search_text = raw_search.replace('\n', ' ').replace('"', "").replace("'", "").lower()

            processed_body = process_wikilinks(body)
            if "notebooklm" in note_type:
                processed_body = process_notebooklm_media(processed_body)

            pending.append({
                "meta": meta,
                "filename": filename,
                "note_id": note_id,
                "title": title,
                "processed_body": processed_body,
                "full_search_text": full_search_text,
            })

    known_ids = {p["note_id"] for p in pending}

    garden_cards = []
    for p in pending:
        card_html = cards.generate_garden_card_html(
            p["meta"], p["filename"], p["note_id"], p["processed_body"], p["full_search_text"], known_ids,
        )
        garden_cards.append({
            "html": card_html,
            "body": p["processed_body"],
            "id": p["note_id"],
            "title": p["title"],
            "link": f"garden.html#{p['note_id']}",
            "type": str(p["meta"].get("type", "NOTE")).upper(),
            "tags": p["meta"].get("tags", []),
            "desc": p["full_search_text"],
        })

    return garden_cards


_OPEN_NOTE_RE = re.compile(r"openNote\('([^']+)'\)")


def _build_backlinks_index(garden_cards):
    """Maps note_id -> [{id, title}, ...] for every other garden note whose
    body links to it -- the reverse of the forward wikilinks already in each
    note's rendered body. This is what powers the modal's "Referenced By"
    section (see gardentemplate.html), the core personal-wiki feature of
    being able to discover a note from what points at it, not just what it
    points to.
    """
    id_to_title = {c['id']: c['title'] for c in garden_cards}
    backlinks = {c['id']: [] for c in garden_cards}

    for c in garden_cards:
        targets_seen = set()
        for target_id in _OPEN_NOTE_RE.findall(c['body']):
            if target_id == c['id'] or target_id not in backlinks or target_id in targets_seen:
                continue
            targets_seen.add(target_id)
            backlinks[target_id].append({"id": c['id'], "title": id_to_title[c['id']]})

    return {note_id: refs for note_id, refs in backlinks.items() if refs}


def _build_graph_index(garden_cards):
    """Builds the node/edge data for the Garden's knowledge-graph view.

    Deliberately thin (id/title/type per node, deduped undirected edges) --
    unlike the modal's data-storage blob this gets embedded in every load of
    garden.html, so it skips full body text (see _build_search_index for the
    same size-conscious precedent).
    """
    known = {c['id'] for c in garden_cards}
    nodes = [{"id": c['id'], "title": c['title'], "type": c['type'].lower()} for c in garden_cards]

    edges = []
    seen_pairs = set()
    for c in garden_cards:
        targets_seen = set()
        for target_id in _OPEN_NOTE_RE.findall(c['body']):
            if target_id == c['id'] or target_id not in known or target_id in targets_seen:
                continue
            targets_seen.add(target_id)
            pair = tuple(sorted((c['id'], target_id)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            edges.append({"source": pair[0], "target": pair[1]})

    return {"nodes": nodes, "edges": edges}


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


def _render_pages(user_config, garden_cards, json_index, backlinks_json, graph_json):
    pages = [
        ("pages/indextemplate.html", "index.html", {}),
        ("pages/gardentemplate.html", "garden.html", {
            "cards": garden_cards, "backlinks_index": backlinks_json, "graph_index": graph_json,
        }),
        ("404.html", "404.html", {}),
    ]

    for template_name, output_name, context in pages:
        try:
            context["theme"] = CURRENT_THEME
            context["search_index"] = json_index
            context["config"] = user_config

            template = env.get_template(template_name)
            rendered_html = template.render(active_page=output_name.replace(".html", ""), **context)

            with open(os.path.join(OUTPUT_DIR, output_name), "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"   ✅ Deployed: {output_name}")
        except Exception as e:
            print(f"   ❌ Failed: {output_name} -> {e}")


def build_all():
    print("------------------------------------------------")
    print("💠 AURELIA OS BUILD ENGINE")
    print("------------------------------------------------")

    prepare_dist()
    organize_assets()
    sync_vault_assets()

    user_config = load_user_config()

    garden_cards = _scan_vault()
    garden_cards.sort(key=lambda x: x['title'].lower())

    print(f"   + Indexing: {len(garden_cards)} Notes")

    master_index = _build_search_index(garden_cards)
    json_index = dumps_for_script_tag(master_index)

    backlinks_json = dumps_for_script_tag(_build_backlinks_index(garden_cards))
    graph_json = dumps_for_script_tag(_build_graph_index(garden_cards))

    _render_pages(user_config, garden_cards, json_index, backlinks_json, graph_json)

    # Runs last: scans the just-rendered dist/**/*.html for utility classes,
    # including ones cards.py assembled dynamically (now literal text in the
    # output), and compiles the final CSS over the passthrough copy.
    compile_css()

    print("\n✅ SYSTEM SYNC COMPLETE.")
