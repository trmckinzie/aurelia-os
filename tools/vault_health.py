"""Vault health reports -- pending-atomization candidates, orphaned notes,
and maturity-promotion candidates.

All three are advisory only: this script never writes to the vault (see
CLAUDE.md's "vault is off-limits" rule -- promoting a note's maturity or
writing a new atomic note is a content judgment call, not something a
script should do on its own). It reuses engine.pipeline's own scan/graph
(_scan_vault, _build_link_graph) rather than reimplementing vault-walking
logic -- both are pure functions with no side effects, the same "reused,
not reimplemented" precedent tools/validate_vault_schema.py already sets
for engine.content.parse_frontmatter.

Run standalone:

    python tools/vault_health.py                 # all three reports
    python tools/vault_health.py --report pending [--limit N]
    python tools/vault_health.py --report orphans [--types concept,discipline]
    python tools/vault_health.py --report promotion
"""
import argparse
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import VAULT_PATH  # noqa: E402
from engine.content import build_link_resolver, make_id, parse_body, parse_frontmatter  # noqa: E402
from engine.pipeline import _build_link_graph, _scan_vault  # noqa: E402

_WIKILINK_RE = re.compile(r'\[\[(.*?)\]\]')


def _garden_cards():
    """The published card list, and nothing else, from a fresh vault scan.

    _scan_vault() returns (garden_cards, backlinks, edges). Every report
    below only wants the first element, and each used to iterate the whole
    tuple as if it were the list -- which crashed the CLI on its first line
    (`TypeError: list indices must be integers`) while every test, all of
    which inject their cards, stayed green. One unpacking site, so the next
    change to _scan_vault's return shape has one place to break loudly.
    """
    garden_cards, _backlinks, _edges = _scan_vault()
    return garden_cards

# The "permanent notes" and "structure notes" in zettelkasten terms -- the
# ones meant to be densely cross-linked. Daily Log (fleeting) and
# Source/Gemini Notebook (literature) naturally have asymmetric link patterns
# (nobody links *to* a specific day; a Source is linked from its Concepts
# more than it links out) that would flood an orphan list with false
# positives if included by default.
PERMANENT_STRUCTURE_TYPES = {"concept", "discipline", "author", "deep-dive"}


def find_pending_atomization(vault_path=VAULT_PATH, known_ids=None):
    """Ranks not-yet-published wikilink targets by how many distinct
    published notes reference them -- the zettelkasten practice of letting
    demand tell you what to write next, instead of noticing one dimmed pill
    at a time on whatever card happens to carry it.

    Returns [(target_id, [referencing_note_id, ...]), ...] sorted by
    descending distinct-referrer count, then target_id.

    Deliberately re-walks the vault and regexes raw [[wikilinks]] directly,
    rather than using _build_link_graph's edges/backlinks -- those are
    built from already-rendered openNote() calls and only ever record
    *resolved* (published-to-published) links; an unresolved target is
    discarded the moment it's found (see _build_link_graph), never tracked
    anywhere. known_ids can be injected (e.g. in tests) to avoid a second
    full _scan_vault() when the caller already has one.

    Targets are resolved through content.build_link_resolver() -- the same
    alias/title-suffix resolution the real build applies via
    engine.pipeline._scan_vault() -- built fresh from every published note
    found in this walk (id/title/aliases). Without this, a note that added
    `aliases:` to close a dangling link would keep showing up here as
    "pending" even though the site itself already resolves it; this report
    exists specifically to tell Travis what's still actually dangling, so
    its count is meant to agree with the build's own "targets still
    unresolved" summary line (see build_all()) for the same vault.
    """
    if known_ids is None:
        known_ids = {c["id"] for c in _garden_cards()}

    notes = []
    for root, _, files in os.walk(vault_path):
        for filename in sorted(files):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(root, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            meta = parse_frontmatter(content)
            if not meta.get("publish"):
                continue
            note_type = str(meta.get("type", "unknown")).lower().strip()
            if "project" in note_type or "protocol" in note_type or "transmission" in note_type:
                continue

            # Coerced str -> [str] the same way pipeline._scan_vault does,
            # which is itself the same coercion parse_frontmatter already
            # applies to `tags`.
            aliases = meta.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            aliases = [str(a).strip() for a in aliases if str(a).strip()]

            notes.append({
                "note_id": make_id(filename),
                "title": filename.replace(".md", "").replace("_", " "),
                "aliases": aliases,
                "body": parse_body(content),
            })

    # Built once over every published note this walk found -- an alias or a
    # "Base (...)" suffix can point at a note discovered later in the walk,
    # same reasoning as the two-pass split in pipeline._scan_vault.
    resolve = build_link_resolver(notes)

    target_refs = defaultdict(set)
    for n in notes:
        for raw in _WIKILINK_RE.findall(n["body"]):
            target_text = raw.split("|", 1)[0].strip()
            if not target_text:
                # An unfilled "[[ ]]" placeholder (some published Concept
                # notes still carry this from TPL_Concept.md's old
                # Related-field default) -- skip before resolve() turns
                # it into a fake "note-" entry that would otherwise look
                # like a real, in-demand target.
                continue
            target_id = resolve(target_text)
            if target_id == n["note_id"]:
                continue
            target_refs[target_id].add(n["note_id"])

    dangling = {t: refs for t, refs in target_refs.items() if t not in known_ids}
    return sorted(
        ((t, sorted(refs)) for t, refs in dangling.items()),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )


def find_orphans(garden_cards=None, types=None):
    """Lists published notes of `types` (default PERMANENT_STRUCTURE_TYPES)
    whose total degree (backlinks in + resolved links out, i.e. distinct
    edge endpoints from _build_link_graph) is <= 1 -- the inverse of the
    Lobby's existing "Hub Notes" panel, which only ever surfaces the most-
    connected notes. Nothing currently surfaces the least-connected ones.

    Returns [(note_id, title, type, degree), ...] sorted by ascending
    degree, then title.
    """
    if garden_cards is None:
        garden_cards = _garden_cards()
    types = types or PERMANENT_STRUCTURE_TYPES

    _, edges = _build_link_graph(garden_cards)
    degree = Counter()
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1

    orphans = [
        (c["id"], c["title"], c["type"].lower(), degree.get(c["id"], 0))
        for c in garden_cards
        if c["type"].lower() in types and degree.get(c["id"], 0) <= 1
    ]
    return sorted(orphans, key=lambda t: (t[3], t[1].lower()))


def find_promotion_candidates(garden_cards=None):
    """Suggests (never applies) maturity promotions per the heuristic
    documented in CLAUDE.md's Content model section: seed -> growing once a
    note has >=2 backlinks; growing -> evergreen once it's referenced from
    >=2 distinct Discipline notes.

    Returns {"seed_to_growing": [(id, title, backlink_count), ...],
             "growing_to_evergreen": [(id, title, discipline_count), ...]}
    """
    if garden_cards is None:
        garden_cards = _garden_cards()

    backlinks, _ = _build_link_graph(garden_cards)
    id_to_card = {c["id"]: c for c in garden_cards}

    seed_to_growing = []
    growing_to_evergreen = []
    for c in garden_cards:
        refs = backlinks.get(c["id"], [])
        if c["maturity"] == "seed" and len(refs) >= 2:
            seed_to_growing.append((c["id"], c["title"], len(refs)))
        elif c["maturity"] == "growing":
            discipline_refs = {
                r["id"] for r in refs
                if id_to_card.get(r["id"], {}).get("type", "").lower() == "discipline"
            }
            if len(discipline_refs) >= 2:
                growing_to_evergreen.append((c["id"], c["title"], len(discipline_refs)))

    seed_to_growing.sort(key=lambda t: -t[2])
    growing_to_evergreen.sort(key=lambda t: -t[2])
    return {"seed_to_growing": seed_to_growing, "growing_to_evergreen": growing_to_evergreen}


def _print_pending(limit):
    pending = find_pending_atomization()
    print(f"\n{'='*70}\nPENDING ATOMIZATION -- unwritten concepts, ranked by demand\n{'='*70}")
    if not pending:
        print("  Nothing pending -- every wikilink target already exists.")
    for target_id, refs in pending[:limit]:
        print(f"  {target_id}  (referenced from {len(refs)} note{'s' if len(refs) != 1 else ''})")
        for ref in refs[:5]:
            print(f"       <- {ref}")
        if len(refs) > 5:
            print(f"       ... and {len(refs) - 5} more")


def _print_orphans(types):
    orphans = find_orphans(types=types)
    label = ", ".join(sorted(types)) if types else ", ".join(sorted(PERMANENT_STRUCTURE_TYPES))
    print(f"\n{'='*70}\nORPHAN / ISOLATED NOTES -- degree <= 1, among [{label}]\n{'='*70}")
    if not orphans:
        print("  None -- every note in scope has at least 2 connections.")
    for note_id, title, note_type, degree in orphans:
        print(f"  [{note_type:<10}] {title}  (degree={degree}, {note_id})")


def _print_promotion():
    candidates = find_promotion_candidates()
    print(f"\n{'='*70}\nMATURITY PROMOTION CANDIDATES (advisory -- confirm by hand)\n{'='*70}")
    print("  seed -> growing (>=2 backlinks):")
    if not candidates["seed_to_growing"]:
        print("    None.")
    for note_id, title, count in candidates["seed_to_growing"]:
        print(f"    {title}  ({count} backlinks, {note_id})")
    print("  growing -> evergreen (>=2 distinct Discipline backlinks):")
    if not candidates["growing_to_evergreen"]:
        print("    None.")
    for note_id, title, count in candidates["growing_to_evergreen"]:
        print(f"    {title}  ({count} disciplines, {note_id})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", choices=["pending", "orphans", "promotion", "all"], default="all")
    parser.add_argument("--limit", type=int, default=25, help="max entries for the pending report")
    parser.add_argument("--types", type=str, default=None, help="comma-separated types for the orphans report")
    args = parser.parse_args()

    types = {t.strip().lower() for t in args.types.split(",")} if args.types else None

    if args.report in ("pending", "all"):
        _print_pending(args.limit)
    if args.report in ("orphans", "all"):
        _print_orphans(types)
    if args.report in ("promotion", "all"):
        _print_promotion()

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
