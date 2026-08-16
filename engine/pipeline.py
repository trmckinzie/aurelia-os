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
    """Walks the vault, building a card for every published garden note."""
    garden_cards = []

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

            card_html = cards.generate_garden_card_html(meta, filename, note_id, processed_body, full_search_text)

            garden_cards.append({
                "html": card_html,
                "body": processed_body,
                "id": note_id,
                "title": title,
                "link": f"garden.html#{note_id}",
                "type": str(meta.get("type", "NOTE")).upper(),
                "tags": meta.get("tags", []),
                "desc": full_search_text,
            })

    return garden_cards


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


def _render_pages(user_config, garden_cards, json_index):
    pages = [
        ("pages/indextemplate.html", "index.html", {}),
        ("pages/gardentemplate.html", "garden.html", {"cards": garden_cards}),
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

    _render_pages(user_config, garden_cards, json_index)

    # Runs last: scans the just-rendered dist/**/*.html for utility classes,
    # including ones cards.py assembled dynamically (now literal text in the
    # output), and compiles the final CSS over the passthrough copy.
    compile_css()

    print("\n✅ SYSTEM SYNC COMPLETE.")
