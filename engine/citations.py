"""Essay citations and APA 7 references (roadmap S16, docs/ESSAYS.md, "Citations").

An essay cites with Pandoc's syntax and keeps its sources beside it in a
reference file of CSL records (E01.refs.yaml). This module turns the records
into an APA 7 reference list and each citation into an APA 7 in-text
citation that links to its entry:

    [@kahneman1979]                 (Kahneman & Tversky, 1979)
    [@kahneman1979, p. 263]         (Kahneman & Tversky, 1979, p. 263)
    [@kahneman1979; @thaler1980]    (Kahneman & Tversky, 1979; Thaler, 1980)
    @kahneman1979 argue that ...    Kahneman and Tversky (1979) argue that ...

WHY IN-HOUSE
------------
Checked first, as the S16 entry asks: citeproc-py 0.11.1 (maintained,
released 2026-09-01) with the official apa.csl from citeproc-py-styles
0.1.6 renders no 1979a/1979b suffixes, leaves the reference list in the
order it was given, writes "(eds.)" for "(Eds.)", and raises on a page
locator. Those are four of the rules docs/ESSAYS.md names, so the formatter
is this small module instead (docs/DECISIONS.md item 44). The records stay
CSL either way, so the choice can be reversed without touching the data.

WHAT IT COVERS
--------------
Five types: journal article, authored book, chapter in an edited book,
encyclopedia entry and preprint (CSL `article`). One to twenty authors in
full, twenty-one or more as the first nineteen, an ellipsis and the last;
group authors (CSL `literal`); same authors in the same year as 1979a and
1979b, lettered by title; DOI over URL, as an https://doi.org/ link; page
ranges with an en dash; the list ordered letter by letter on the authors,
then year, then title. It never changes a title's case: only a person knows
which words are proper nouns. Anything else -- another type, a record
missing what its type needs -- warns and is left out of the list rather
than rendered wrong.

WHAT FAILS HOW
--------------
The record *shape* (the field allowlist, name fields, the key, `verified`)
is checked by engine/essays.check_reference_records() and stops every
build, since it guards what gets committed. Citation problems leak nothing,
so they go through engine/buildlog.warn() and fail only the strict build,
like a dangling wikilink: a citation with no record, a record nothing
cites, a key used twice, a type this module does not format, or two
different works that would cite identically.
"""
import re
import unicodedata
from urllib.parse import quote

from markupsafe import Markup, escape

from engine.buildlog import warn

# The five types the first version formats (docs/ESSAYS.md). A preprint is
# CSL `article`, the type Zotero exports one as.
SUPPORTED_TYPES = ("article-journal", "book", "chapter", "entry-encyclopedia", "article")

# What each type needs beyond author, issued and title, which all need.
_REQUIRED = {
    "article-journal": ("container-title",),
    "book": ("publisher",),
    "chapter": ("container-title", "publisher"),
    "entry-encyclopedia": ("container-title",),
    "article": ("publisher",),
}

# Every field each type's entry writes. A committed field a type does not
# use warns, so nothing a reader would expect to see is dropped silently.
_COMMON_FIELDS = frozenset({"id", "type", "author", "issued", "title", "DOI", "URL", "verified", "open_access"})
_USED = {
    "article-journal": _COMMON_FIELDS | {"container-title", "volume", "issue", "page"},
    "book": _COMMON_FIELDS | {"edition", "volume", "page", "publisher"},
    "chapter": _COMMON_FIELDS | {"editor", "container-title", "edition", "volume", "page", "publisher"},
    "entry-encyclopedia": _COMMON_FIELDS | {"editor", "container-title", "edition", "version", "volume", "page", "publisher"},
    "article": _COMMON_FIELDS | {"genre", "publisher"},
}

# A citation key: Pandoc's shape, narrowed to characters that are safe in an
# HTML id and a URL fragment as they stand. Inner punctuation is allowed,
# trailing punctuation is not, so "@kahneman1979." cites kahneman1979.
KEY_PATTERN = r"[A-Za-z0-9_](?:[A-Za-z0-9_]|[:./-](?=[A-Za-z0-9_]))*"
KEY_RE = re.compile(KEY_PATTERN)
_FULL_KEY_RE = re.compile(rf"^{KEY_PATTERN}$")

# APA 7: list up to twenty authors; past that, the first nineteen, an
# ellipsis and the last.
MAX_LISTED_AUTHORS = 20
_ELLIPSIS = ". . ."

_DASHES_RE = re.compile(r"(?<=\w)\s*[-‐-―]+\s*(?=\w)")
_LEADING_ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
_DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
_EDITION_WORD_RE = re.compile(r"\s*(?:ed\.?|edition)$", re.IGNORECASE)


def is_key(value):
    """True when `value` is a usable citation key."""
    return isinstance(value, str) and bool(_FULL_KEY_RE.match(value))


def anchor(key):
    """The id of a key's entry in the reference list."""
    return f"ref-{key}"


# --- small text helpers ---------------------------------------------------

def _text(value):
    return str(value).strip() if value is not None else ""


def en_dash(text):
    """Page ranges with an en dash: '263-291' -> '263–291'."""
    return _DASHES_RE.sub("–", text)


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def edition_label(value):
    """'2' or 2 -> '2nd ed.'; 'Fall 2021 Edition' -> 'Fall 2021 ed.'; a
    first edition is not mentioned (APA 7)."""
    text = _text(value)
    if not text:
        return None
    if text.isdigit():
        n = int(text)
        return None if n == 1 else f"{ordinal(n)} ed."
    return f"{_EDITION_WORD_RE.sub('', text)} ed."


def initials(given):
    """'Daniel' -> 'D.'; 'Jane A.' -> 'J. A.'; 'Jean-Paul' -> 'J.-P.';
    'J.R.R.' -> 'J. R. R.'"""
    words = [w for w in re.split(r"[\s.]+", _text(given)) if w]
    out = []
    for word in words:
        out.append("-".join(f"{part[0]}." for part in word.split("-") if part))
    return " ".join(out)


def _sort_text(text):
    """Letter by letter, as APA 7 alphabetizes: accents, case, spaces and
    punctuation ignored, so 'nothing precedes something'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if c.isalnum()).casefold()


def _title_sort(title):
    return _sort_text(_LEADING_ARTICLE_RE.sub("", title))


def _ends_sentence(text):
    return text.rstrip().endswith((".", "?", "!"))


# --- names ----------------------------------------------------------------

def _is_group(name):
    return "literal" in name


def surname(name):
    return _text(name["literal"]) if _is_group(name) else _text(name["family"])


def inverted(name):
    """A name as the reference list writes an author: 'Kahneman, D.'"""
    if _is_group(name):
        return _text(name["literal"])
    given = initials(name.get("given"))
    return f"{surname(name)}, {given}" if given else surname(name)


def direct(name):
    """A name as the reference list writes an editor: 'D. Kahneman'."""
    if _is_group(name):
        return _text(name["literal"])
    given = initials(name.get("given"))
    return f"{given} {surname(name)}" if given else surname(name)


def reference_authors(names):
    """The author element of a reference entry, without its closing period."""
    written = [inverted(n) for n in names]
    if len(written) == 1:
        return written[0]
    if len(written) == 2:
        return f"{written[0]}, & {written[1]}"
    if len(written) <= MAX_LISTED_AUTHORS:
        return ", ".join(written[:-1]) + ", & " + written[-1]
    return ", ".join(written[:MAX_LISTED_AUTHORS - 1]) + f", {_ELLIPSIS} " + written[-1]


def editors_phrase(names):
    """'J. Doe (Ed.)', 'J. Doe & R. Roe (Eds.)', 'A. A, B. B, & C. C (Eds.)'."""
    written = [direct(n) for n in names]
    if len(written) == 1:
        people = written[0]
    elif len(written) == 2:
        people = f"{written[0]} & {written[1]}"
    else:
        people = ", ".join(written[:-1]) + ", & " + written[-1]
    return f"{people} ({'Ed.' if len(written) == 1 else 'Eds.'})"


def in_text_authors(names, narrative=False):
    """'Kahneman', 'Kahneman & Tversky' (or 'and' in running text),
    'Kahneman et al.'"""
    if len(names) == 1:
        return surname(names[0])
    if len(names) == 2:
        joiner = "and" if narrative else "&"
        return f"{surname(names[0])} {joiner} {surname(names[1])}"
    return f"{surname(names[0])} et al."


def _author_identity(names):
    """Two works share authors when every name matches, in order."""
    return tuple((surname(n).casefold(), initials(n.get("given")).casefold()) for n in names)


def _author_sort(names):
    # A tuple per author, compared in order: a one-author work sorts before
    # a work that author wrote with others (APA 7), and co-authors break the
    # tie after that.
    return tuple((_sort_text(surname(n)), _sort_text(initials(n.get("given")))) for n in names)


# --- one entry ------------------------------------------------------------

def _link(record):
    """The DOI as an https://doi.org/ link, else the URL, else nothing."""
    doi = _text(record.get("DOI"))
    if doi:
        doi = _DOI_PREFIX_RE.sub("", doi)
        href = "https://doi.org/" + quote(doi, safe="/:;()._-")
        text = "https://doi.org/" + doi
    else:
        href = text = _text(record.get("URL"))
    if not href:
        return ""
    return f'<a href="{escape(href)}">{escape(text)}</a>'


def _italic(text):
    return f"<i>{escape(text)}</i>"


def _closing(html_so_far, plain_tail):
    """A period after an element unless it already ends a sentence."""
    return html_so_far if _ends_sentence(plain_tail) else html_so_far + "."


def _pages(page):
    page = en_dash(_text(page))
    return f"{'pp.' if chr(0x2013) in page or ',' in page else 'p.'} {page}"


def _details(record, edition_field="edition"):
    """The parenthetical after a book-like title: '(2nd ed., Vol. 3, pp. 10–20)'."""
    parts = []
    edition = edition_label(record.get(edition_field))
    if edition:
        parts.append(edition)
    if _text(record.get("volume")) and record.get("type") != "article-journal":
        parts.append(f"Vol. {_text(record['volume'])}")
    if _text(record.get("page")):
        parts.append(_pages(record["page"]))
    return f" ({escape(', '.join(parts))})" if parts else ""


def _book_title(title, details):
    """An italic title, its details, and the period that closes them."""
    if details:
        return f"{_italic(title)}{details}."
    return _closing(_italic(title), title)


def _publisher(record, authors):
    """The publisher as its own element, left out when it is the group
    author (APA 7: the author already names it)."""
    publisher = _text(record.get("publisher"))
    if not publisher:
        return ""
    if len(authors) == 1 and _is_group(authors[0]) and _sort_text(surname(authors[0])) == _sort_text(publisher):
        return ""
    return " " + _closing(str(escape(publisher)), publisher)


def format_entry(record, year_label):
    """One APA 7 reference entry as HTML (a Markup string). The record has
    passed check_record(), so every field its type needs is present."""
    kind = record["type"]
    authors = record["author"]
    title = _text(record["title"])
    who = reference_authors(authors)
    head = f"{escape(_closing(who, who))} ({escape(year_label)})."

    if kind == "article-journal":
        source = _italic(_text(record["container-title"]))
        if _text(record.get("volume")):
            source += f", {_italic(_text(record['volume']))}"
        if _text(record.get("issue")):
            source += f"({escape(_text(record['issue']))})" if _text(record.get("volume")) else f", ({escape(_text(record['issue']))})"
        if _text(record.get("page")):
            source += f", {escape(en_dash(_text(record['page'])))}"
        body = f" {escape(_closing(title, title))} {source}."
    elif kind == "book":
        body = " " + _book_title(title, _details(record)) + _publisher(record, authors)
    elif kind in ("chapter", "entry-encyclopedia"):
        edition_field = "version" if kind == "entry-encyclopedia" and _text(record.get("version")) else "edition"
        editors = record.get("editor") or []
        lead = f"In {escape(editors_phrase(editors))}, " if editors else "In "
        container = _text(record["container-title"])
        body = (f" {escape(_closing(title, title))} {lead}"
                f"{_book_title(container, _details(record, edition_field))}"
                f"{_publisher(record, authors)}")
    else:   # article: a preprint
        genre = _text(record.get("genre")) or "Preprint"
        body = f" {_italic(title)} [{escape(genre)}]." + _publisher(record, authors)

    link = _link(record)
    return Markup(head + body + (f" {link}" if link else ""))


# --- the reference file as a whole ---------------------------------------

def unused_fields(record):
    """The fields a record carries that its type's entry never writes."""
    used = _USED.get(record.get("type"), frozenset(record))
    return sorted(k for k, v in record.items() if k not in used and v is not None)


def check_record(record):
    """What stops one (shape-checked) record from being formatted, as a
    list of plain strings; empty when it can be."""
    kind = record.get("type")
    if kind not in SUPPORTED_TYPES:
        return [f"type {kind!r} is not one the APA 7 formatter supports ({', '.join(SUPPORTED_TYPES)})"]
    problems = []
    if not record.get("author"):
        problems.append("needs at least one author")
    issued = record.get("issued")
    if not (isinstance(issued, int) and not isinstance(issued, bool) and 1000 <= issued <= 9999):
        problems.append("issued must be a four-digit year")
    for field in ("title",) + _REQUIRED[kind]:
        if not _text(record.get(field)):
            problems.append(f"a {kind} needs {field}")
    url = _text(record.get("URL"))
    if url and not url.startswith(("https://", "http://")):
        problems.append("URL must start with https:// or http://")
    return problems


class References:
    """An essay's reference list, ready to cite from and to render.

    Built once per essay, before its body is rendered, because a citation's
    text depends on the whole list (1979a needs to know about 1979b).
    """

    def __init__(self, records, essay_id, refs_name):
        self.essay_id = essay_id
        self.refs_name = refs_name
        self.keys = set()        # every key in the file, formattable or not
        self.cited = set()
        self._entries = {}
        usable = []
        for record in records or []:
            key = record["id"]
            if key in self.keys:
                warn(f"Essay {essay_id}: reference key '{key}' appears more than once in {refs_name}; "
                     f"only the first is used")
                continue
            self.keys.add(key)
            problems = check_record(record)
            if problems:
                warn(f"Essay {essay_id}: reference '{key}' in {refs_name} is left out of the list: "
                     + "; ".join(problems))
                continue
            unused = unused_fields(record)
            if unused:
                warn(f"Essay {essay_id}: reference '{key}' in {refs_name} has {', '.join(unused)}, "
                     f"which an APA 7 {record['type']} entry does not show")
            usable.append(record)

        usable.sort(key=lambda r: (_author_sort(r["author"]), r["issued"], _title_sort(_text(r["title"]))))

        # Same authors, same year: a, b, c by title, in the list and in the text.
        groups = {}
        for record in usable:
            groups.setdefault((_author_identity(record["author"]), record["issued"]), []).append(record)
        year_labels = {}
        for members in groups.values():
            for i, record in enumerate(members):
                suffix = chr(ord("a") + i) if len(members) > 1 else ""
                year_labels[record["id"]] = f"{record['issued']}{suffix}"

        # Different authors that shorten to the same in-text form ("Lee et
        # al., 2023" twice): APA 7 spells out more names, which this
        # formatter does not, so it says so rather than citing ambiguously.
        seen = {}
        for record in usable:
            short = (in_text_authors(record["author"]), year_labels[record["id"]])
            if short in seen:
                warn(f"Essay {essay_id}: references '{seen[short]}' and '{record['id']}' would both cite "
                     f"as ({short[0]}, {short[1]}); APA 7 adds author names to tell them apart, "
                     f"which the formatter does not")
            else:
                seen[short] = record["id"]

        self.order = [r["id"] for r in usable]
        for record in usable:
            key = record["id"]
            self._entries[key] = {
                "key": key,
                "anchor": anchor(key),
                "authors": record["author"],
                "identity": _author_identity(record["author"]),
                "year": year_labels[key],
                "html": format_entry(record, year_labels[key]),
            }

    def __contains__(self, key):
        return key in self.keys

    def entry(self, key):
        return self._entries.get(key)

    def entries(self):
        """The reference list, in APA order, as the template renders it."""
        return [{"key": e["key"], "anchor": e["anchor"], "html": e["html"]}
                for e in (self._entries[k] for k in self.order)]

    def warn_uncited(self):
        for key in sorted(self.keys - self.cited):
            warn(f"Essay {self.essay_id}: reference '{key}' in {self.refs_name} is cited nowhere in the essay")


# --- citations in the text ------------------------------------------------

_ITEM_RE = re.compile(rf"^\s*(?:(?P<prefix>[^@;]*?)\s+)?(?P<suppress>-?)@(?P<key>{KEY_PATTERN})(?P<rest>.*)$", re.DOTALL)


def parse_bracket(inner):
    """The items of a bracketed citation ('@a, p. 3; see @b'), or None when
    the text is not one. Each item is (prefix, key, locator, suppress)."""
    items = []
    for part in inner.split(";"):
        match = _ITEM_RE.match(part)
        if not match:
            return None
        rest = match.group("rest")
        if rest and not (rest[0] == "," or rest[0].isspace()):
            return None
        prefix = " ".join((match.group("prefix") or "").split())
        locator = " ".join(rest.lstrip(" ,\t\n").split())
        items.append((prefix, match.group("key"), locator, bool(match.group("suppress"))))
    return items or None


_SINGLE_PAGE_RANGE_RE = re.compile(r"^p\.\s*(?=[^,;]*\u2013)")


def locator_text(locator):
    """A page locator as APA 7 writes it: ranges with an en dash, and
    'pp.' for a range written with 'p.'."""
    return _SINGLE_PAGE_RANGE_RE.sub("pp. ", en_dash(locator))


def _citation_link(entry, text):
    return f'<a href="#{escape(entry["anchor"])}" class="essay-citation">{escape(text)}</a>'


def _missing(raw):
    return f'<span class="essay-missing-citation">{escape(raw)}</span>'


def render_parenthetical(items, references, raw):
    """A bracketed citation as APA 7: '(Kahneman & Tversky, 1979a, 1979b;
    Thaler, 1980)', every work linked to its entry. The works are put in
    reference-list order, as APA 7 asks, unless one carries a prefix ('see'),
    which belongs where the author put it."""
    entries = []
    for prefix, key, locator, suppress in items:
        references.cited.add(key)
        entry = references.entry(key)
        if entry is None:
            if key in references:
                warn(f"Essay {references.essay_id}: {raw} cites '{key}', whose record is left out of the list")
            else:
                warn(f"Essay {references.essay_id}: {raw} cites '{key}', which has no record in {references.refs_name}")
        entries.append((prefix, entry, locator_text(locator), suppress))
    if any(entry is None for _p, entry, _l, _s in entries):
        return _missing(raw)

    if not any(prefix for prefix, *_ in entries):
        entries.sort(key=lambda item: references.order.index(item[1]["key"]))

    parts = []
    previous = None
    for prefix, entry, locator, suppress in entries:
        year = entry["year"] + (f", {locator}" if locator else "")
        # The same authors again, with nothing between: 'Kahneman & Tversky,
        # 1979a, 1979b' rather than repeating the names.
        if (previous and not prefix and not suppress and not locator
                and not previous[1] and previous[0] == entry["identity"]):
            parts[-1] += ", " + _citation_link(entry, year)
        else:
            text = year if suppress else f"{in_text_authors(entry['authors'])}, {year}"
            lead = f"{escape(prefix)} " if prefix else ""
            parts.append(lead + _citation_link(entry, text))
        previous = (entry["identity"], bool(locator) or suppress)
    return "(" + "; ".join(parts) + ")"


def render_narrative(key, locator, references):
    """'@kahneman1979' in running text: 'Kahneman and Tversky (1979)'."""
    references.cited.add(key)
    entry = references.entry(key)
    raw = f"@{key}" + (f" [{locator}]" if locator else "")
    if entry is None:
        warn(f"Essay {references.essay_id}: {raw} cites '{key}', whose record is left out of the list")
        return _missing(raw)
    year = entry["year"] + (f", {locator_text(locator)}" if locator else "")
    return _citation_link(entry, f"{in_text_authors(entry['authors'], narrative=True)} ({year})")


# --- markdown-it inline rules ---------------------------------------------

_NARRATIVE_LOCATOR_RE = re.compile(r" ?\[([^\[\]@\n]+)\](?![(\[])")
# Characters that, just before an '@', make it part of a word, an email
# address or a URL path (https://example.com/@name), rather than the start
# of a citation.
_WORD_CHARS = frozenset("_.+-%/:=&?#~@")


def bracket_rule(state, silent):
    """[@key], [@key, p. 12], [@a; @b], [see @a] -- Pandoc's bracketed
    citation. A bracket that is not one (no key, a stray '@', a link
    `[@x](url)`) is left for markdown-it's own link rule."""
    src, pos = state.src, state.pos
    references = state.env.get("essay_references")
    if references is None or src[pos] != "[" or src[pos + 1:pos + 2] == "[":
        return False
    if src[pos - 1:pos] == "!" and pos > 0:
        return False   # ![...] is an image, whatever its alt text says
    end = src.find("]", pos + 1)
    if end < 0 or "[" in src[pos + 1:end] or src[end + 1:end + 2] in ("(", "["):
        return False
    inner = src[pos + 1:end]
    items = parse_bracket(inner)
    if items is None:
        return False
    if not silent:
        token = state.push("essay_citation", "", 0)
        token.content = src[pos:end + 1]
        token.meta = {"items": items}
    state.pos = end + 1
    return True


def narrative_rule(state, silent):
    """@key in running text, with an optional [locator] after it. Only at
    the start of a word and only for a key the reference file holds, so an
    email address is left alone; '\\@' writes a literal one.

    A word-initial @token that is no key renders as written but warns, so
    a misspelled narrative citation (@kahnman1979) fails the strict build
    instead of reaching the page as raw text. An essay that means a literal
    @name writes it as \\@name."""
    src, pos = state.src, state.pos
    references = state.env.get("essay_references")
    if references is None or src[pos] != "@" or state.linkLevel > 0:
        return False
    if pos > 0 and (src[pos - 1].isalnum() or src[pos - 1] in _WORD_CHARS):
        return False
    match = KEY_RE.match(src, pos + 1)
    if not match:
        return False
    if match.group(0) not in references:
        if not silent:
            warn(f"Essay {references.essay_id}: @{match.group(0)} reads as a citation but has no record "
                 f"in {references.refs_name}; write \\@{match.group(0)} if it is not one")
        return False
    end = match.end()
    locator = ""
    trailing = _NARRATIVE_LOCATOR_RE.match(src, end)
    if trailing:
        locator = " ".join(trailing.group(1).split())
        end = trailing.end()
    if not silent:
        token = state.push("essay_citation", "", 0)
        token.content = src[pos:end]
        token.meta = {"key": match.group(0), "locator": locator}
    state.pos = end
    return True


def render_citation(token, references):
    """An essay_citation token as HTML. Rendering, not parsing, records the
    citation and raises its warnings, so a token that never renders (one
    turned back into text by plain_citations_in_alt_text) cites nothing."""
    meta = token.meta
    if "items" in meta:
        return render_parenthetical(meta["items"], references, token.content)
    return render_narrative(meta["key"], meta["locator"], references)


def plain_citations_in_alt_text(state):
    """markdown-it core rule: an image's alt text is plain text, so a
    citation parsed inside one goes back to the text it was written as."""
    def walk(tokens):
        for token in tokens or ():
            if token.type == "image":
                for child in token.children or ():
                    if child.type == "essay_citation":
                        child.type, child.meta = "text", {}
            walk(token.children)
    walk(state.tokens)
