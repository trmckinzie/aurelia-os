"""Regex extractors that pull structured card data out of a garden note's markdown body.

Each garden note type follows its own loose convention of emoji headers and
blockquotes (NotebookLM export format, daily-log templates, ...), so these
stay per-type rather than a single generic parser. The repeated pieces --
stripping rendered wikilink buttons, walking to the next header, pulling out
linked note titles -- are factored into engine.textutils.
"""
import re

from engine.textutils import (
    clean_text,
    extract_link_labels,
    first_blockquote_after,
    section_after_header,
    strip_html,
)


# --- Garden extractors -------------------------------------------------

def extract_log_data(text):
    """Parses Daily Log for GOAL, SOURCE, CONCEPTS, and SUMMARY."""
    goal_match = re.search(r'\*\*GOAL:\*\*\s*(.*)', text)
    goal = strip_html(goal_match.group(1)).strip() if goal_match else "System Check."

    source_match = re.search(r'\*\*SOURCE:\*\*\s*(.*)', text)
    source = clean_text(source_match.group(1)).strip() if source_match else "Internal Log"

    concepts = []
    for rc in re.findall(r'\*\s*\*\*Concept:\*\*\s*(.*)', text):
        concepts.append(clean_text(rc).strip())

    summary = ""
    if "**📝 BRIEF SUMMARY:**" in text:
        part = text.split("**📝 BRIEF SUMMARY:**")[1]
        bq_match = re.search(r'>\s*(.*)', part)
        if bq_match:
            summary = clean_text(bq_match.group(1)).strip()

    return goal, source, concepts[:3], summary


def extract_concept_data(text):
    """Parses Concept for Definition block and Related links."""
    definition = first_blockquote_after(text, r'###\s*.*Definition.*')
    definition = clean_text(definition).strip() if definition else "Definition unavailable."

    related_match = re.search(r'\*\*🔗 Related:\*\*\s*(.*)', text)
    clean_links = []
    if related_match:
        items = clean_text(related_match.group(1)).split(',')
        clean_links = [i.strip() for i in items if i.strip()]

    return definition, clean_links[:4]


def extract_source_data(text):
    """Parses Source for Author, Core Argument, and Derived Concepts."""
    auth_match = re.search(r'\*\*.*Author:\*\*\s*(.*)', text)
    author = clean_text(auth_match.group(1)).strip().upper() if auth_match else "UNKNOWN"

    argument = first_blockquote_after(text, r'###\s*.*(?:Core Argument|Thesis).*')
    argument = strip_html(argument).strip() if argument else "No core argument extracted."

    section = section_after_header(text, r'###\s*.*Concepts Extracted.*')
    concepts = extract_link_labels(section) if section else []

    return author, argument, concepts[:5]


def extract_author_data(text):
    """Parses Author Profile for Context, Key Works, and Core Concepts."""
    context = first_blockquote_after(text, r'###\s*.*Profile & Context.*')
    context = clean_text(context).strip() if context else "Profile data unavailable."

    works_section = section_after_header(text, r'###\s*.*Key Works.*')
    works = extract_link_labels(works_section) if works_section else []

    concepts_section = section_after_header(text, r'###\s*.*Core Concepts.*')
    concepts = extract_link_labels(concepts_section) if concepts_section else []

    return context, works[:4], concepts[:4]


def extract_discipline_data(text):
    """Parses Discipline for Scope, Core Concepts, and Foundational Texts."""
    scope = first_blockquote_after(text, r'###\s*.*Definition.*')
    scope = clean_text(scope).strip() if scope else "Scope defined in parent node."

    pillars_section = section_after_header(text, r'###\s*.*Core Concepts.*')
    pillars = extract_link_labels(pillars_section) if pillars_section else []

    canon_section = section_after_header(text, r'###\s*.*Foundational Texts.*')
    canon = extract_link_labels(canon_section) if canon_section else []

    return scope, pillars[:4], canon[:3]


def extract_notebooklm_data(text):
    """Parses NotebookLM Note for Overview and Active Studio Features."""
    overview_match = re.search(r'#\s*.*Lit Review Overview.*\n([\s\S]*?)(?=\n#|$)', text)
    raw_overview = overview_match.group(1).strip() if overview_match else "Synthesis data pending."
    clean_overview = clean_text(raw_overview).replace('>', '').strip()

    features = {
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

    active_features = []
    for key, pattern in features.items():
        if not re.search(pattern, text, re.IGNORECASE):
            continue
        section_match = re.search(f"{pattern}.*\\n([\\s\\S]*?)(?=\\n#|$)", text, re.IGNORECASE)
        if section_match and section_match.group(1).strip():
            active_features.append(key)

    return clean_overview, active_features
