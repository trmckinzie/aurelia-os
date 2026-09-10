"""Regex extractors that pull structured card data out of a garden note's markdown body.

Each garden note type follows its own loose convention of emoji headers and
blockquotes (Gemini Notebook export format, daily-log templates, ...), so these
stay per-type rather than a single generic parser. The repeated pieces --
stripping rendered wikilink buttons, walking to the next header, pulling out
linked note titles -- are factored into engine.textutils.
"""
import re

from engine.content import resolve_asset
from engine.textutils import (
    clean_text,
    extract_links,
    first_blockquote_after,
    section_after_header,
    strip_html,
)


# --- Garden extractors -------------------------------------------------

_CONTRASTS_RE = re.compile(r'\*\*⚡ Contrasts With:\*\*\s*(.*)')


def _extract_contrasts(text, cap):
    """Parses an optional "**⚡ Contrasts With:**" line -- the tension/
    friction counterpart to a note's "Related" links (which are always
    symmetric agreement/association). Same parsing shape as Related: prefer
    wikilinks, fall back to plain comma-separated labels.

    New field (2026-08); capped at 6 pending real usage data -- unlike
    Related's audit-derived 12/10 caps above, there's no existing vault
    content yet to survey a realistic maximum from.
    """
    match = _CONTRASTS_RE.search(text)
    if not match:
        return []
    raw_line = match.group(1)
    tensions = extract_links(raw_line)
    if not tensions:
        items = clean_text(raw_line).split(',')
        tensions = [(None, i.strip()) for i in items if i.strip()]
    return tensions[:cap]

def extract_log_data(text):
    """Parses Daily Log for GOAL, SOURCE, CONCEPTS, and SUMMARY.

    SOURCE and each CONCEPT are returned as (target_id, label) pairs --
    target_id is None if that field wasn't actually a wikilink.
    """
    goal_match = re.search(r'\*\*GOAL:\*\*\s*(.*)', text)
    goal = strip_html(goal_match.group(1)).strip() if goal_match else "System Check."

    source_match = re.search(r'\*\*SOURCE:\*\*\s*(.*)', text)
    if source_match:
        source_links = extract_links(source_match.group(1))
        source = source_links[0] if source_links else (None, clean_text(source_match.group(1)).strip())
    else:
        source = (None, "Internal Log")

    concepts = []
    for rc in re.findall(r'\*\s*\*\*Concept:\*\*\s*(.*)', text):
        rc_links = extract_links(rc)
        if rc_links:
            concepts.append(rc_links[0])
        else:
            label = clean_text(rc).strip()
            if label:
                concepts.append((None, label))

    summary = ""
    if "**📝 BRIEF SUMMARY:**" in text:
        part = text.split("**📝 BRIEF SUMMARY:**")[1]
        bq_match = re.search(r'>\s*(.*)', part)
        if bq_match:
            summary = clean_text(bq_match.group(1)).strip()

    return goal, source, concepts[:3], summary


def extract_concept_data(text):
    """Parses Concept for Definition block and Related links (as (target_id,
    label) pairs; falls back to plain comma-separated labels with target_id=
    None if the Related line has no wikilinks in it at all)."""
    definition = first_blockquote_after(text, r'###\s*.*Definition.*')
    definition = clean_text(definition).strip() if definition else "Definition unavailable."

    related_match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', text)
    links = []
    if related_match:
        raw_line = related_match.group(1)
        links = extract_links(raw_line)
        if not links:
            items = clean_text(raw_line).split(',')
            links = [(None, i.strip()) for i in items if i.strip()]

    # Cap raised from 4 -> 12 (2026-08 audit): a survey of the 122 published
    # Concept notes found an average of 6 Related links and a max of 12, so
    # the old cap of 4 was silently dropping content from nearly every card
    # on the live site, not just guarding against a rare outlier.
    return definition, links[:12], _extract_contrasts(text, 6)


def extract_source_data(text):
    """Parses Source for Author, Core Argument, and Derived Concepts.

    Author and each Concept are (target_id, label) pairs.
    """
    auth_match = re.search(r'\*\*.*Author:\*\*\s*(.*)', text)
    if auth_match:
        auth_links = extract_links(auth_match.group(1))
        target_id, label = auth_links[0] if auth_links else (None, clean_text(auth_match.group(1)).strip())
        author = (target_id, label.upper())
    else:
        author = (None, "UNKNOWN")

    argument = first_blockquote_after(text, r'###\s*.*(?:Core Argument|Thesis).*')
    argument = strip_html(argument).strip() if argument else "No core argument extracted."

    section = section_after_header(text, r'###\s*.*Concepts Extracted.*')
    concepts = extract_links(section) if section else []

    # Cap raised from 5 -> 12 (2026-08 audit): 6 of the 15 published Source
    # notes exceeded the old cap (max observed: 12).
    return author, argument, concepts[:12]


def extract_author_data(text):
    """Parses Author Profile for Context, Key Works, and Core Concepts.

    Key Works and Core Concepts are lists of (target_id, label) pairs.
    """
    context = first_blockquote_after(text, r'###\s*.*Profile & Context.*')
    context = clean_text(context).strip() if context else "Profile data unavailable."

    works_section = section_after_header(text, r'###\s*.*Key Works.*')
    works = extract_links(works_section) if works_section else []

    concepts_section = section_after_header(text, r'###\s*.*Core Concepts.*')
    concepts = extract_links(concepts_section) if concepts_section else []

    # Caps raised from 4/4 -> 6/8 (2026-08 audit): observed max across the 16
    # published Author notes was 5 Key Works and 7 Core Concepts.
    return context, works[:6], concepts[:8]


def extract_discipline_data(text):
    """Parses Discipline for Scope, Core Concepts, and Foundational Texts.

    Core Concepts and Foundational Texts are lists of (target_id, label) pairs.
    """
    scope = first_blockquote_after(text, r'###\s*.*Definition.*')
    scope = clean_text(scope).strip() if scope else "Scope defined in parent node."

    pillars_section = section_after_header(text, r'###\s*.*Core Concepts.*')
    pillars = extract_links(pillars_section) if pillars_section else []

    canon_section = section_after_header(text, r'###\s*.*Foundational Texts.*')
    canon = extract_links(canon_section) if canon_section else []

    # Caps raised from 4/3 -> 10/10 (2026-08 audit): observed max across the
    # 19 published Discipline notes was 9 Core Concepts and 10 Foundational
    # Texts -- every single note exceeded the old Foundational Texts cap of 3.
    return scope, pillars[:10], canon[:10], _extract_contrasts(text, 6)


_GEMINI_FEATURES = {
    'audio': r'#+\s*.*Audio Overview',
    'video': r'#+\s*.*Video Overview',
    'mindmap': r'#+\s*.*Mind Map',
    'reports': r'#+\s*.*Reports',
    'flashcards': r'#+\s*.*Flashcards',
    'quiz': r'#+\s*.*Quiz',
    'infographic': r'#+\s*.*Infographic',
    'slides': r'#+\s*.*Slide Deck',
    'datatable': r'#+\s*.*Data Table',
}

# The two scaffold headers every note carries, plus the nine Studio outputs
# above -- what's left is the author's own material (chapter breakdowns, study
# guides, presenter notes), which is what the card's section count is about.
_GEMINI_SCAFFOLD_RE = re.compile(
    r'Lit Review Overview|Sources|Audio Overview|Video Overview|Mind Map'
    r'|Reports|Flashcards|Quiz|Infographic|Slide Deck|Data Table',
    re.IGNORECASE,
)

_ASSET_REF_RE = re.compile(r'assets/[A-Za-z0-9_./\- ]+\.[A-Za-z0-9]{2,5}')

# A Templater placeholder the author never filled in -- the template writes
# its prompts as a whole-string bracket ("[Paste the Executive Summary or Core
# Thesis here.]", "[Zotero Data Placeholder]"), so the brackets are the
# convention to detect rather than any one wording.
_UNFILLED_RE = re.compile(r'^\[[^\]]*\]$')


def _strip_emphasis(text):
    """Removes markdown emphasis markers, which clean_text() leaves behind.

    Real overviews arrive wrapped in them ("**Report: Information Theoretic
    Principles in Cognitive Systems**") or carrying them inline, and a card
    renders the result as plain text, so the asterisks would just show. The
    `_x_` rule is word-boundary-guarded so it can't eat a snake_case
    identifier or a filename.
    """
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*\n]+)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'\1', text)
    return text


def extract_gemini_notebook_data(text):
    """Parses a Gemini Notebook note for its card.

    Returns (overview, live_features, source_count, section_count).

    `overview` is the blockquote directly under the Lit Review Overview
    header -- the note's own dek -- and "" when that is missing or is still an
    unfilled template placeholder, which the card renders as an honest empty
    state rather than implying something is still processing. Deliberately not
    the whole section, the way this used to read it: a real note's Overview
    section IS the report (20k-38k characters across the current vault), so
    truncating it to a card line yielded a fragment of paragraph one. Every
    other type's prose field is the blockquote under its header, and these
    notes follow that convention too.

    `live_features` holds only the Studio outputs a reader can actually open.
    A section that references media reaches the card only if at least one of
    those references resolves on disk: the 2026 history purge took every
    vault audio file and mind-map image with it, so 10 "Audio Overview" and 6
    "Mind Map" sections across the vault now point at nothing, and listing
    them was advertising a dead end. A section with no asset reference at all
    (a text-only Report or Quiz) still counts on having any content, which is
    the rule this function always used.

    NOTE: this reads the note body from *before*
    content.wrap_gemini_notebook_sections() rewrites `# Header` into
    <details>/<summary> -- see the card_body snapshot in pipeline._scan_vault.
    """
    raw_overview = first_blockquote_after(text, r'#\s*.*Lit Review Overview.*') or ""
    overview = _strip_emphasis(clean_text(raw_overview)).replace('>', '').strip()
    if _UNFILLED_RE.match(overview):
        overview = ""

    live_features = []
    for key, pattern in _GEMINI_FEATURES.items():
        section_match = re.search(f"{pattern}.*\\n([\\s\\S]*?)(?=\\n#|$)", text, re.IGNORECASE)
        if not section_match:
            continue
        section = section_match.group(1).strip()
        if not section:
            continue
        refs = _ASSET_REF_RE.findall(section)
        if refs and not any(resolve_asset(ref.strip()) for ref in refs):
            continue
        live_features.append(key)

    sources_section = section_after_header(text, r'#\s*.*Sources.*')
    source_count = len(re.findall(r'^\s*\d+\.\s+\S', sources_section or "", re.MULTILINE))

    section_count = sum(
        1 for header in re.findall(r'^#\s+(.+)$', text, re.MULTILINE)
        if not _GEMINI_SCAFFOLD_RE.search(header)
    )

    return overview, live_features, source_count, section_count


def extract_deep_dive_data(text):
    """Parses a Deep Dive for its italic premise line, the "Part 3" plain-
    English summary excerpt, and any manually wikilinked related notes.

    Deep Dives are pasted in whole from elsewhere (an AI chat, an essay
    draft), not filled in piecemeal the way other types are, so this only
    depends on two structural conventions the template documents: a single
    standalone *italic* line under the title (the premise -- matched via a
    backreference so `*...*` and `_..._` both work, but a `**bold**` run
    never does, since its doubled delimiter can't satisfy the single-char
    backreference), and a "Part 3" header (the plain-English summary).
    Related is (target_id, label) pairs, same as every other type's manual
    link field.
    """
    premise_match = re.search(r'^(\*|_)([^*_\n]+)\1\s*$', text, re.MULTILINE)
    premise = clean_text(premise_match.group(2)).strip() if premise_match else "No premise line found."

    summary_section = section_after_header(text, r'##\s*Part 3.*')
    # Deliberately not narrowed to the first paragraph: Part 3 often opens
    # with a short setup line ("If you remember one thing...") before the
    # actual substance, so grabbing paragraph[0] tends to surface the
    # throat-clearing instead of the summary -- the whole section, cleaned
    # and left for cards.py's truncate() to cut to size, is more reliably
    # meaningful than a "first paragraph" heuristic, and matches how every
    # other extractor in this module hands off to truncate() rather than
    # pre-trimming itself. Unlike those other extractors' single-line
    # blockquote sources, though, a multi-paragraph section carries blank
    # lines that clean_text() doesn't touch -- collapsed here rather than
    # left to reach the rendered <p> as literal double-newlines.
    if summary_section:
        # clean_text() only strips wikilinks/HTML; the other extractors
        # never needed more since a single blockquote line rarely carries
        # markdown emphasis, but a multi-paragraph prose section routinely
        # does (**bold**, `code`, ### stray headers) -- stripped the same
        # blunt way cards.py's own generic-fallback card already does.
        summary = re.sub(r'[*_`#]', '', clean_text(summary_section))
        summary = re.sub(r'\s+', ' ', summary).strip()
    else:
        summary = "No summary section found."

    related_match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', text)
    related = extract_links(related_match.group(1)) if related_match else []

    return premise, summary, related[:4]
