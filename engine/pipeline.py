"""Orchestrates the full build: scan the vault, route notes by type, render pages."""
import os
import re

from engine import cards
from engine.assets_pipeline import json_serial, organize_assets, prepare_dist, sync_vault_assets
from engine.config import (
    CURRENT_THEME,
    OUTPUT_DIR,
    PROTOCOL_PATH,
    VAULT_PATH,
    env,
    load_user_config,
)
from engine.content import make_id, parse_body, parse_frontmatter, process_notebooklm_media, process_wikilinks
from engine.extractors import extract_mission_brief
from engine.textutils import dumps_for_script_tag

try:
    import markdown
except ImportError:
    markdown = None


def _scan_vault(user_config):
    """Walks the vault, routing each published note to its garden/portfolio bucket.
    Protocols and transmissions are scanned separately (their own dedicated folders)."""
    garden_cards, portfolio_cards = [], []

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
            tags = meta.get("tags", [])
            title = filename.replace(".md", "").replace("_", " ")

            if "project" in note_type:
                project_id = f"project-{len(portfolio_cards)}"
                card_html = cards.generate_project_card(meta, {"brief": body}, title, project_id)
                portfolio_cards.append({
                    "html": card_html,
                    "body": body,
                    "id": project_id,
                    "title": title,
                    "link": f"portfolio.html#{project_id}",
                    "type": "PROJECT",
                    "tags": tags,
                    "desc": extract_mission_brief(body),
                })

            elif "protocol" in note_type or "transmission" in note_type:
                continue  # handled by their own dedicated scans below

            else:
                note_id = make_id(filename)

                raw_search = re.sub(r'[*#_`\[\]]', '', body)
                raw_search = re.sub(r'<[^>]+>', '', raw_search)
                full_search_text = raw_search.replace('\n', ' ').replace('"', "").replace("'", "").lower()

                processed_body = process_wikilinks(body)
                if "notebooklm" in note_type:
                    processed_body = process_notebooklm_media(processed_body)

                card_html = cards.generate_garden_card_html(meta, filename, note_id, processed_body, full_search_text)

                garden_cards.append({
                    "html": card_html,
                    "body": processed_body,
                    "id": note_id,
                    "title": title,
                    "link": f"garden.html#{note_id}",
                    "type": str(meta.get("type", "NOTE")).upper(),
                    "tags": tags,
                    "desc": full_search_text,
                })

    return garden_cards, portfolio_cards


def _scan_protocols():
    protocol_cards = []
    scan_path = PROTOCOL_PATH if os.path.exists(PROTOCOL_PATH) else VAULT_PATH

    for root, _, files in os.walk(scan_path):
        for filename in files:
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            meta = parse_frontmatter(content)
            if "protocol" not in meta.get("type", "") or not meta.get("publish", False):
                continue

            body = parse_body(content)
            title = filename.replace(".md", "").replace("_", " ")
            p_id = meta.get("id", "PROT_" + filename[:3].upper())
            note_id = make_id(filename)

            card_html = cards.generate_protocol_card(meta, body, title, note_id, p_id)
            protocol_cards.append({
                "html": card_html,
                "title": title,
                "desc": meta.get("description", "System Protocol"),
                "tags": meta.get("tags", []),
                "body": body,
                "id": p_id,
                "link": "protocol.html",
                "type": "PROTOCOL",
            })

    return protocol_cards


def _scan_transmissions(user_config):
    if not user_config.get('modules', {}).get('transmissions', {}).get('enabled', False):
        return []

    transmissions_dir = os.path.join(VAULT_PATH, "40_TRANSMISSIONS")
    if not os.path.exists(transmissions_dir):
        return []

    print(f"   + Processing Transmissions from: {transmissions_dir}")
    transmissions_data = []

    for filename in os.listdir(transmissions_dir):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(transmissions_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            t_content = f.read()

        t_meta = parse_frontmatter(t_content)
        t_body = parse_body(t_content)

        if 'series' not in t_meta:
            t_meta['series'] = 'Uncategorized'
        if 'title' not in t_meta:
            t_meta['title'] = filename.replace(".md", "")
        try:
            t_meta['episode'] = int(t_meta.get('episode', 999))
        except (TypeError, ValueError):
            t_meta['episode'] = 999

        t_meta['content'] = markdown.markdown(t_body, extensions=['fenced_code', 'tables']) if markdown else t_body
        t_meta['tags'] = t_meta.get("tags", [])
        transmissions_data.append(t_meta)

    return transmissions_data


def _build_search_index(garden_cards, portfolio_cards, protocol_cards, transmissions_data):
    master_index = [
        {"title": "Home // Mission Control", "url": "index.html", "type": "SYSTEM", "tags": ["home", "root"], "desc": "Main Hub"},
        {"title": "The Garden // Input", "url": "garden.html", "type": "SYSTEM", "tags": ["notes", "writing"], "desc": "Digital Garden"},
        {"title": "Protocols // Logic", "url": "protocol.html", "type": "SYSTEM", "tags": ["sop", "routines"], "desc": "Operating Procedures"},
        {"title": "Portfolio // Output", "url": "portfolio.html", "type": "SYSTEM", "tags": ["work", "jobs"], "desc": "Case Studies"},
    ]
    if transmissions_data:
        master_index.append({"title": "Transmissions // Signal", "url": "transmissions.html", "type": "SYSTEM", "tags": ["podcast", "audio"], "desc": "Neural Uplink"})

    for c in garden_cards:
        master_index.append({"title": c['title'], "url": c['link'], "type": "GARDEN", "tags": c['tags'], "desc": c['desc']})
    for p in portfolio_cards:
        master_index.append({"title": p['title'], "url": p['link'], "type": "PROJECT", "tags": p['tags'], "desc": p['desc']})
    for prot in protocol_cards:
        master_index.append({"title": prot['title'], "url": prot['link'], "type": "PROTOCOL", "tags": prot['tags'], "desc": prot['desc']})
    for trans in transmissions_data:
        master_index.append({"title": trans['title'], "url": "transmissions.html", "type": "TRANSMISSION", "tags": trans['tags'], "desc": f"Series: {trans['series']} // Ep {trans['episode']}"})

    return master_index


def _render_pages(user_config, garden_cards, portfolio_cards, protocol_cards, transmissions_data, json_index):
    pages = [
        ("pages/indextemplate.html", "index.html", {}),
        ("pages/gardentemplate.html", "garden.html", {"cards": garden_cards}),
        ("pages/portfoliotemplate.html", "portfolio.html", {"projects": portfolio_cards}),
        ("pages/servicestemplate.html", "services.html", {}),
        ("pages/protocoltemplate.html", "protocol.html", {"protocols": protocol_cards}),
        ("404.html", "404.html", {}),
    ]

    if user_config.get('modules', {}).get('transmissions', {}).get('enabled', False):
        transmissions_json = dumps_for_script_tag(transmissions_data, default=json_serial)
        pages.append(("pages/transmissionstemplate.html", "transmissions.html", {"transmissions_json": transmissions_json}))

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

    garden_cards, portfolio_cards = _scan_vault(user_config)
    protocol_cards = _scan_protocols()
    transmissions_data = _scan_transmissions(user_config)

    garden_cards.sort(key=lambda x: x['title'].lower())
    portfolio_cards.sort(key=lambda x: x['title'].lower())
    protocol_cards.sort(key=lambda x: x['title'].lower())
    transmissions_data.sort(key=lambda x: (x['series'], x['episode']))

    print(f"   + Indexing: {len(garden_cards)} Notes, {len(portfolio_cards)} Projects, "
          f"{len(protocol_cards)} Protocols, {len(transmissions_data)} Transmissions")

    master_index = _build_search_index(garden_cards, portfolio_cards, protocol_cards, transmissions_data)
    json_index = dumps_for_script_tag(master_index)

    _render_pages(user_config, garden_cards, portfolio_cards, protocol_cards, transmissions_data, json_index)

    print("\n✅ SYSTEM SYNC COMPLETE.")
