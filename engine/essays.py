"""Essays: a fourth kind of published content (docs/ESSAYS.md, roadmap S15).

An essay is a Markdown note in vault/30_ESSAYS/ (a sibling of the Garden)
plus, beside it, a reference file in CSL field names (E01.refs.yaml). The
vault walk in engine/pipeline.py never turns one into a Garden card: it
prunes this folder and sends it here instead, and a `type: essay` note found
anywhere else fails the build. The index at /essays/ and one page per essay
at /essays/<slug>/ are the first output below the top of dist/.

THE PRIVACY CHECKS FAIL EVERY BUILD, STRICT OR NOT
--------------------------------------------------
The repo is public and everything in vault/ is committed, so the boundary
is what gets committed, not what renders (docs/ARCHITECTURE.md, "Privacy
model"). The essay workflow has a private half (a Source Ledger, AI
summaries, notebook links, drafts on a reMarkable tablet) that must never
reach the folder. Each check below raises EssayError, the way a bad
user_config.json or profile.json already stops the build, and never goes
through engine/buildlog.warn(): verify.sh builds with --strict only on
GitHub, and a pushed branch is public before CI runs, so a warning would
let a local run pass with the leak in it.

  1. Field allowlist. Essay frontmatter and reference records accept only
     the fields docs/ESSAYS.md lists; any other key fails. CSL's own
     `abstract`, `annote` and `note` are therefore refused, since they are
     where a citation manager puts summaries and notes.
  2. Host denylist. Google Drive, Docs and Sheets, Gemini, NotebookLM and
     reMarkable hosts fail wherever they appear in an essay or its
     reference file, with or without a scheme in front of them.
  3. Text only. Any file in the folder other than .md and .yaml fails,
     whatever its size. The two OS metadata files .gitignore already
     refuses (.DS_Store, Thumbs.db) are the one exception, so opening the
     folder in Finder cannot fail a build.
  4. Drafts. A note in the folder without `publish: true` fails, as does a
     `type: essay` note outside it, the agent-draft folder 20_AURELIA
     included (that half lives in pipeline._scan_garden, which reads the
     raw frontmatter text so a broken YAML block cannot hide the type).
  5. Media origins (S17). Every companion URL's origin must be on
     user_config.json's `media_origins` list, the same list that feeds the
     essay pages' media-src, so nothing in the AI zone points anywhere the
     owner has not named. The YouTube episode is its own field and must be
     a YouTube address with a video id.

Citation and link problems leak nothing, so they stay build warnings: a
wikilink to a missing or unpublished Garden note warns, and --strict fails
on it in CI. So do the citation checks (S16, engine/citations.py): a
citation with no record, a record nothing cites, a key used twice, a type
the APA 7 formatter does not support. The reference file's shape (the
field allowlist, names, keys, `verified`) is the contract, and stops every
build like the frontmatter does.

The folder is read from AURELIA_ESSAYS_DIR when that is set, so the tests
and verify.sh build the fixture essay under tests/fixtures/essays/ without
anything entering the vault.

THE PARTS OF AN ESSAY PAGE THAT SAY WHO MADE WHAT (S17)
------------------------------------------------------
The disclosure note ("How this essay was made") is rendered from the
`methods` block and the reference file by disclosure(), never typed: each
sentence belongs to one fact, so a role the frontmatter does not list has
no sentence, and the source counts are of the records the reference list
shows (listed_records()), so they cannot drift from the list a reader sees. The study companion holds only players
and links built from the `companion` entries (a kind, a short label, a URL
on an allowed origin), so the one zone with AI output on the page cannot
hold prose. The YouTube episode renders as a control that loads nothing
from Google until it is pressed (essaytemplate.html).
"""
import datetime
import math
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import nh3
import yaml
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markupsafe import Markup

from engine.buildlog import warn
from engine.citations import (
    References,
    bracket_rule,
    is_key,
    narrative_rule,
    plain_citations_in_alt_text,
    render_citation,
)
from engine.config import VAULT_PATH
from engine.content import _FRONTMATTER_FENCE_RE, parse_body
from engine.paths import escapes, is_link

ESSAYS_DIR_NAME = "30_ESSAYS"
ESSAYS_DIR_ENV = "AURELIA_ESSAYS_DIR"

# Words per minute behind the reading time (docs/ESSAYS.md: words divided
# by 230, rounded up). Computed, never typed.
WORDS_PER_MINUTE = 230

# --- the data contract (docs/ESSAYS.md, "Vault layout and data contract") --

ESSAY_FIELDS = frozenset({
    "type", "id", "title", "slug", "publish", "published", "updated",
    "disciplines", "thesis", "citation_style", "methods", "companion", "youtube",
})
ESSAY_REQUIRED = ("type", "id", "title", "slug", "publish", "published",
                  "disciplines", "thesis", "citation_style", "methods")
METHODS_FIELDS = frozenset({"drafted_on", "edited_in", "ai_roles"})
# A closed vocabulary: the disclosure note (S17) only ever says something the
# engine knows how to phrase, and "writing" can never be one.
AI_ROLES = ("source search", "source summaries", "citation audit")
COMPANION_FIELDS = frozenset({"kind", "label", "url"})
COMPANION_KINDS = frozenset({"audio", "video", "other"})
CITATION_STYLES = frozenset({"apa7", "web"})
THESIS_MAX = 200
COMPANION_LABEL_MAX = 80
METHODS_TOOL_MAX = 60

# Reference records, in CSL field names. Everything else fails -- including
# `abstract`, `annote` and `note`, on purpose (privacy check 1).
REFERENCE_FIELDS = frozenset({
    "id", "type", "author", "editor", "issued", "title", "container-title",
    "edition", "volume", "issue", "page", "publisher", "DOI", "URL",
    "version", "genre", "open_access", "verified",
})
NAME_FIELDS = frozenset({"family", "given", "literal"})

_ID_RE = re.compile(r"^E\d{2}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REFS_NAME_RE = re.compile(r"^(E\d{2})\.refs\.yaml$")

# Privacy check 2: the hosts of the private half of the workflow. Matched as
# a host or any subdomain of one, anywhere in the file text, so a bare
# `notebooklm.google.com/notebook/...` without a scheme is caught too. A
# public notebook link exposes every library-licensed PDF in it.
DENIED_HOSTS = (
    "drive.google.com",
    "drive.usercontent.google.com",
    # Where Drive and Docs serve the file bytes themselves; a "copy link" on
    # a Drive preview or an exported Doc often yields one of these.
    "googleusercontent.com",
    "docs.google.com",
    "sheets.google.com",
    "gemini.google.com",
    # Gemini's own share form is a g.co shortlink; no essay needs any g.co.
    "g.co",
    "aistudio.google.com",
    "notebooklm.google.com",
    "notebooklm.google",
    "remarkable.com",
)
# The host, or any subdomain of it, not preceded by a label character: so
# `mirror-docs.google.com` is a different host and passes, while a URL pasted
# after an ellipsis or a dot (`...docs.google.com/`) is still caught.
_DENIED_HOST_RE = re.compile(
    r"(?<![\w-])(?:[\w-]+\.)*(?:" + "|".join(re.escape(h) for h in DENIED_HOSTS) + r")(?![\w-])",
    re.IGNORECASE,
)

# Privacy check 3: the only file kinds the folder may hold, plus the OS
# metadata files .gitignore already keeps out of the repository.
TEXT_EXTENSIONS = frozenset({".md", ".yaml"})
_OS_METADATA_FILES = frozenset({".DS_Store", "Thumbs.db"})

_YOUTUBE_HOSTS = frozenset({"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"})
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
# The only player the page ever loads, and only on a reader's tap: the
# privacy-enhanced host, which sets no cookie until the video plays.
YOUTUBE_EMBED_ORIGIN = "https://www.youtube-nocookie.com"

# The study companion's kinds and what each renders as: an <audio> or a
# <video> player for media files, a plain link for anything else (exported
# flashcards, say). Never an embed of a third-party page.
PLAYER_KINDS = frozenset({"audio", "video"})

_WIKILINK_RE = re.compile(r"\[\[(.*?)\]\]")


def _wikilink_rule(state, silent):
    """markdown-it inline rule for [[Target]] and [[Target|Label]].

    An inline rule, not a regex over the rendered page: markdown-it's
    tokenizer has already set aside code spans, fenced blocks and link
    titles by the time this runs, so a wikilink quoted in code stays
    literal and one inside an attribute cannot break out of it.
    """
    src, pos = state.src, state.pos
    if src[pos:pos + 2] != "[[":
        return False
    end = src.find("]]", pos + 2)
    if end < 0 or "\n" in src[pos + 2:end]:
        return False
    if not silent:
        token = state.push("wikilink", "", 0)
        token.content = src[pos + 2:end]
    state.pos = end + 2
    return True


def _render_wikilink(self, tokens, idx, options, env):
    """One [[wikilink]] as a link to the Garden note it resolves to (the
    Garden's own resolver, so aliases and unique title suffixes work here
    too). A target that is missing or unpublished warns, so the strict CI
    build fails on it, and renders as muted text, the way the Garden dims
    its own dangling links. The label is escaped here; nothing in it is
    Markdown."""
    inner = tokens[idx].content
    if "|" in inner:
        target, label = inner.split("|", 1)
    else:
        target = label = inner
    target, label = target.strip(), escapeHtml(label.strip())
    target_id = env["resolve"](target)
    if target_id in env["known_ids"]:
        markup = (f'<a href="{env["garden_href"]}#{target_id}" class="essay-garden-link" '
                  f'data-garden-note="{target_id}">{label}</a>')
    else:
        warn(f"Essay {env['essay_id']}: [[{target}]] is not a published Garden note")
        markup = f'<span class="essay-missing-link" title="Not yet published">{label}</span>'
    return env["keep"](markup)


# CommonMark plus tables and strikethrough; no raw HTML (an essay is
# Markdown, and markdown-it escapes any tag it meets as text, so the author
# sees it), no typographer, no linkify. Rendered server-side, unlike Garden
# notes, which marked.js renders in the browser when a note opens.
_markdown = MarkdownIt("commonmark", {"html": False, "typographer": False}).enable(["table", "strikethrough"])
_markdown.inline.ruler.before("link", "wikilink", _wikilink_rule)
_markdown.add_render_rule("wikilink", _render_wikilink)
# Pandoc citations (S16, engine/citations.py): the bracketed form before the
# link rule, so [@key] is a citation and not a failed link; the narrative
# @key wherever an '@' stops markdown-it's text run.
_markdown.inline.ruler.before("link", "essay_citation", bracket_rule)
_markdown.inline.ruler.before("link", "essay_narrative_citation", narrative_rule)
_markdown.add_render_rule("essay_citation", lambda self, tokens, idx, options, env:
                          env["keep"](render_citation(tokens[idx], env["essay_references"])))
_markdown.core.ruler.after("inline", "essay_citation_alt_text", plain_citations_in_alt_text)


class EssayError(RuntimeError):
    """Raised for any problem in the Essays folder. Every message names the
    file, and the build stops whether or not --strict was passed."""


def essays_path(vault_path=None):
    """The folder the build reads essays from: AURELIA_ESSAYS_DIR when set
    (the tests and verify.sh point it at tests/fixtures/essays/), otherwise
    vault/30_ESSAYS/, found the way the Garden walk prunes it: by case-folded
    name. On this Mac a `30_essays/` opens as `30_ESSAYS`; on CI's Linux it
    does not, and a folder the walk prunes but this never reads would be a
    folder nobody checks. Two case variants side by side is an error."""
    override = os.environ.get(ESSAYS_DIR_ENV, "").strip()
    if override:
        return override
    vault = VAULT_PATH if vault_path is None else vault_path
    try:
        variants = sorted(e for e in os.listdir(vault) if e.casefold() == ESSAYS_DIR_NAME.casefold())
    except OSError:
        variants = []
    if len(variants) > 1:
        raise EssayError(f"vault/ holds more than one spelling of the Essays folder: {', '.join(variants)}")
    return os.path.join(vault, variants[0] if variants else ESSAYS_DIR_NAME)


# --- validation ----------------------------------------------------------

def _is_str(value):
    return isinstance(value, str) and value.strip() != "" and "\n" not in value and "\r" not in value


def _as_date(value):
    """A YAML date, or an ISO string, as a datetime.date; None otherwise."""
    if isinstance(value, datetime.datetime):
        return None   # a time of day is not part of the contract
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _check_url(value, field, problems):
    if not _is_str(value):
        problems.append(f"{field}: must be a URL string")
        return None
    parts = urlsplit(value.strip())
    if parts.scheme != "https" or not parts.netloc:
        problems.append(f"{field}: must be an https URL with a host")
        return None
    return parts


def youtube_id(url):
    """The video id in a YouTube address (watch?v=, youtu.be/, /embed/,
    /shorts/ or /live/), or None when there is none to find."""
    parts = urlsplit(str(url).strip())
    host = parts.netloc.lower()
    if parts.scheme != "https" or host not in _YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        candidate = parts.path.strip("/")
    elif parts.path == "/watch":
        values = [v for k, v in (pair.partition("=")[::2] for pair in parts.query.split("&")) if k == "v"]
        candidate = values[0] if len(values) == 1 else ""
    else:
        segments = parts.path.strip("/").split("/")
        candidate = segments[1] if len(segments) == 2 and segments[0] in ("embed", "shorts", "live") else ""
    return candidate if _YOUTUBE_ID_RE.match(candidate) else None


def origin_of(url):
    """'https://host' for an https URL with a plain host, else None. A URL
    with credentials or a port has no origin on the allowlist's terms."""
    parts = urlsplit(str(url).strip())
    try:
        port = parts.port
    except ValueError:   # a port that is not a number: no origin, so not allowed
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username is not None or port is not None:
        return None
    return f"https://{parts.hostname}"


def check_media_origins(raw, media_origins):
    """Privacy check 5: problems with an essay's companion URLs against the
    allowed media origins (user_config.json's `media_origins`)."""
    problems = []
    allowed = set(media_origins)
    for i, entry in enumerate(raw.get("companion") or []):
        url = entry.get("url")
        origin = origin_of(url)
        if origin not in allowed:
            listed = ", ".join(sorted(allowed)) or "none"
            problems.append(f"companion[{i}].url: {url} is not on an allowed media origin "
                            f"(user_config.json media_origins: {listed})")
    return problems


def check_denied_hosts(text):
    """The denied hosts found in `text`, in order of first appearance."""
    found = []
    for match in _DENIED_HOST_RE.finditer(text):
        host = match.group(0).lower()
        if host not in found:
            found.append(host)
    return found


def _split_frontmatter(content):
    """(raw mapping, body) for a note, or (None, content) when the note has
    no frontmatter block. Raises yaml.YAMLError on a malformed one."""
    stripped = content.lstrip()
    if not stripped.startswith("---"):
        return None, content
    parts = _FRONTMATTER_FENCE_RE.split(stripped, maxsplit=2)
    if len(parts) < 3:
        return None, content
    return yaml.safe_load(parts[1]), parse_body(content)


def check_essay_frontmatter(raw):
    """Problems with one essay's frontmatter mapping, as plain strings; an
    empty list means it meets the contract in docs/ESSAYS.md."""
    problems = []
    if not isinstance(raw, dict):
        return ["frontmatter: must be a mapping"]

    for key in raw:
        if key not in ESSAY_FIELDS:
            problems.append(f"frontmatter: unknown field '{key}' (the allowlist is in docs/ESSAYS.md)")
    for key in ESSAY_REQUIRED:
        if key not in raw:
            problems.append(f"frontmatter: missing required field '{key}'")
    if problems:
        return problems

    # Privacy check 4: a draft has no safe place in the vault. Only the
    # boolean true counts; a quoted string or a yes is not the one switch
    # the engine reads.
    if raw["publish"] is not True:
        problems.append("publish: must be true; a draft never enters the Essays folder")
    if raw["type"] != "essay":
        problems.append(f"type: expected 'essay', got {raw['type']!r}")
    if not (isinstance(raw["id"], str) and _ID_RE.match(raw["id"])):
        problems.append(f"id: must be E plus two digits, got {raw['id']!r}")
    if not _is_str(raw["title"]):
        problems.append("title: must be a non-empty single-line string")
    if not (isinstance(raw["slug"], str) and _SLUG_RE.match(raw["slug"])):
        problems.append(f"slug: must be lowercase letters, digits and single hyphens, got {raw['slug']!r}")

    published = _as_date(raw["published"])
    if published is None:
        problems.append(f"published: must be a date (YYYY-MM-DD), got {raw['published']!r}")
    if "updated" in raw:
        updated = _as_date(raw["updated"])
        if updated is None:
            problems.append(f"updated: must be a date (YYYY-MM-DD), got {raw['updated']!r}")
        elif published is not None and updated < published:
            problems.append("updated: must be on or after published")

    disciplines = raw["disciplines"]
    if not (isinstance(disciplines, list) and disciplines and all(_is_str(d) for d in disciplines)):
        problems.append("disciplines: must be a non-empty list of labels")

    thesis = raw["thesis"]
    if not _is_str(thesis):
        problems.append("thesis: must be one sentence on one line")
    elif len(thesis) > THESIS_MAX:
        problems.append(f"thesis: {len(thesis)} characters, the limit is {THESIS_MAX}")

    if raw["citation_style"] not in CITATION_STYLES:
        problems.append(f"citation_style: must be one of {sorted(CITATION_STYLES)}, got {raw['citation_style']!r}")

    methods = raw["methods"]
    if not isinstance(methods, dict):
        problems.append("methods: must be a mapping of drafted_on, edited_in and ai_roles")
    else:
        for key in methods:
            if key not in METHODS_FIELDS:
                problems.append(f"methods: unknown field '{key}'")
        for key in ("drafted_on", "edited_in"):
            if not _is_str(methods.get(key)):
                problems.append(f"methods.{key}: must be a non-empty single-line string")
            elif len(methods[key]) > METHODS_TOOL_MAX:
                # A tool's name, not a sentence: the note is built from data.
                problems.append(f"methods.{key}: {len(methods[key])} characters, the limit is {METHODS_TOOL_MAX}")
        roles = methods.get("ai_roles")
        if not isinstance(roles, list):
            problems.append("methods.ai_roles: must be a list (it may be empty)")
        else:
            for role in roles:
                if role not in AI_ROLES:
                    problems.append(f"methods.ai_roles: unknown role {role!r}; the vocabulary is {list(AI_ROLES)}")
            if len(set(map(str, roles))) != len(roles):
                problems.append("methods.ai_roles: a role is listed twice")

    if "companion" in raw:
        companion = raw["companion"]
        if not isinstance(companion, list):
            problems.append("companion: must be a list of entries")
        else:
            for i, entry in enumerate(companion):
                where = f"companion[{i}]"
                if not isinstance(entry, dict):
                    problems.append(f"{where}: must be a mapping of kind, label and url")
                    continue
                for key in entry:
                    if key not in COMPANION_FIELDS:
                        problems.append(f"{where}: unknown field '{key}'")
                for key in ("kind", "label", "url"):
                    if key not in entry:
                        problems.append(f"{where}: missing required field '{key}'")
                if entry.get("kind") not in COMPANION_KINDS:
                    problems.append(f"{where}.kind: must be one of {sorted(COMPANION_KINDS)}")
                label = entry.get("label")
                if not _is_str(label):
                    problems.append(f"{where}.label: must be a short single-line label")
                elif len(label) > COMPANION_LABEL_MAX:
                    problems.append(f"{where}.label: {len(label)} characters, the limit is {COMPANION_LABEL_MAX}")
                if "url" in entry:
                    _check_url(entry["url"], f"{where}.url", problems)

    if "youtube" in raw:
        parts = _check_url(raw["youtube"], "youtube", problems)
        if parts is not None and parts.netloc.lower() not in _YOUTUBE_HOSTS:
            problems.append(f"youtube: must be a YouTube address, got host {parts.netloc!r}")
        elif parts is not None and youtube_id(raw["youtube"]) is None:
            problems.append("youtube: no video id in the address (watch?v=, youtu.be/ or /embed/ followed by 11 characters)")

    return problems


def _check_names(value, where, problems):
    """CSL names: a list of {family, given} for a person or {literal} for a
    group. The allowlist reaches inside a name too, so nothing rides along
    in one."""
    if not isinstance(value, list) or not value:
        problems.append(f"{where}: must be a non-empty list of names")
        return
    for j, name in enumerate(value):
        at = f"{where}[{j}]"
        if not isinstance(name, dict):
            problems.append(f"{at}: must be a mapping of family and given, or literal for a group")
            continue
        for key in name:
            if key not in NAME_FIELDS:
                problems.append(f"{at}: unknown field '{key}' (a name holds family and given, or literal)")
        if "literal" in name:
            if not _is_str(name["literal"]) or len(name) > 1:
                problems.append(f"{at}: a group author is literal alone, as a single-line string")
        elif not _is_str(name.get("family")):
            problems.append(f"{at}: needs family (or literal for a group)")
        elif "given" in name and not _is_str(name["given"]):
            problems.append(f"{at}.given: must be a single-line string")


def check_reference_records(records):
    """Problems with one reference file's records (a list of CSL-field
    mappings), as plain strings. This is the record's shape -- what may be
    committed -- and stops every build; whether a record can be formatted
    is engine/citations.py's question, and only warns."""
    if not isinstance(records, list):
        return ["references: must be a list of records"]
    problems = []
    for i, record in enumerate(records):
        where = f"references[{i}]"
        if not isinstance(record, dict):
            problems.append(f"{where}: must be a mapping in CSL field names")
            continue
        for key in record:
            if key not in REFERENCE_FIELDS:
                problems.append(f"{where}: unknown field '{key}' (CSL abstract, annote and note are refused on purpose)")
        if not _is_str(record.get("id")):
            problems.append(f"{where}: missing the citation key 'id'")
        elif not is_key(record["id"]):
            problems.append(f"{where}: id {record['id']!r} is not a citation key (letters, digits and _, "
                            f"with : . / - only between them)")
        # A year when present; a record without one is left out of the
        # list with a warning (engine/citations.py), but a wrong one is the
        # record's shape.
        if "issued" in record and not (isinstance(record["issued"], int) and not isinstance(record["issued"], bool)
                                       and 1000 <= record["issued"] <= 9999):
            problems.append(f"{where}.issued: must be a four-digit year, got {record['issued']!r}")
        # Every record says whether Travis checked it against the original:
        # the disclosure note counts them (S17), so a missing answer is not
        # a quiet "no".
        if not isinstance(record.get("verified"), bool):
            problems.append(f"{where}.verified: required, true or false")
        if "open_access" in record and not isinstance(record["open_access"], bool):
            problems.append(f"{where}.open_access: must be true or false")
        for field in ("author", "editor"):
            if field in record:
                _check_names(record[field], f"{where}.{field}", problems)
    return problems


def _walk_folder(folder):
    """Every file in the Essays folder, as (relative path, full path), with
    links and anything resolving outside the folder reported as problems
    rather than read. Sorted, so a build is reproducible."""
    root = Path(folder).resolve()
    files, problems = [], []
    for dirpath, dirnames, filenames in os.walk(folder):
        kept = []
        for name in sorted(dirnames):
            full = os.path.join(dirpath, name)
            if is_link(full) or escapes(full, root):
                problems.append((os.path.relpath(full, folder), "a link, or resolves outside the Essays folder"))
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, folder).replace(os.sep, "/")
            if is_link(full) or escapes(full, root):
                problems.append((rel, "a link, or resolves outside the Essays folder"))
                continue
            files.append((rel, full))
    return files, problems


def check_essays_folder(folder, media_origins=()):
    """Reads and validates the Essays folder without rendering anything.

    Returns (essays, problems): `essays` is a list of {"rel", "raw",
    "body", "refs"} for every note that passed, and `problems` a list of
    (relative path, message) for everything that did not. Shared by
    scan_essays() (which fails the build on any problem) and
    tools/validate_vault_schema.py (which prints them).

    `media_origins` is user_config.json's allowlist; the default, none,
    means any companion entry fails, so a caller that forgets to pass it
    errs on the closed side.
    """
    if not os.path.isdir(folder):
        return [], []
    if is_link(folder):
        # The walk below checks every entry against the folder it resolves
        # to, which a linked root would pass by construction; the root gets
        # the same answer every vault directory gets (engine/paths.py).
        return [], [(".", "the Essays folder is a link, and a link decides what goes on the site")]

    files, problems = _walk_folder(folder)
    notes, refs = {}, {}

    for rel, full in files:
        name = os.path.basename(rel)
        if name in _OS_METADATA_FILES:
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in TEXT_EXTENSIONS:
            # Privacy check 3. A PDF of any size, an image, an export.
            problems.append((rel, "only .md and .yaml files may be in the Essays folder"))
            continue
        if os.path.dirname(rel):
            # Flat by contract: an essay and its reference file sit beside
            # each other at the top of the folder, and nothing else does.
            problems.append((rel, "essays and reference files sit at the top of the Essays folder, not in a subfolder"))
            continue
        with open(full, "r", encoding="utf-8") as f:
            text = f.read()
        # Privacy check 2, on the whole file: frontmatter, body or records.
        for host in check_denied_hosts(text):
            problems.append((rel, f"names a host that must never enter the repository: {host}"))
        if ext == ".yaml":
            refs[rel] = text
            continue
        notes[rel] = text

    essays, ids, slugs = [], {}, {}
    for rel, text in notes.items():
        try:
            raw, body = _split_frontmatter(text)
        except yaml.YAMLError as e:
            problems.append((rel, f"malformed frontmatter: {str(e).splitlines()[0]}"))
            continue
        if raw is None:
            problems.append((rel, "no frontmatter; an essay needs the fields in docs/ESSAYS.md"))
            continue
        # The origin check reads `companion` as the contract shapes it, so it
        # runs only once the frontmatter itself is clean; an essay with both
        # problems reports the frontmatter first.
        note_problems = check_essay_frontmatter(raw) or check_media_origins(raw, media_origins)
        if note_problems:
            problems.extend((rel, p) for p in note_problems)
            continue
        if raw["id"] in ids:
            problems.append((rel, f"id {raw['id']} is already used by {ids[raw['id']]}"))
            continue
        if raw["slug"] in slugs:
            problems.append((rel, f"slug {raw['slug']!r} is already used by {slugs[raw['slug']]}"))
            continue
        ids[raw["id"]] = rel
        slugs[raw["slug"]] = rel
        essays.append({"rel": rel, "raw": raw, "body": body, "refs": None})

    by_id = {e["raw"]["id"]: e for e in essays}
    for rel, text in refs.items():
        match = _REFS_NAME_RE.match(rel)
        if not match:
            problems.append((rel, "a .yaml file here must be an essay's reference file, named E01.refs.yaml beside it"))
            continue
        essay = by_id.get(match.group(1))
        if essay is None:
            problems.append((rel, f"no essay with id {match.group(1)} to belong to"))
            continue
        try:
            records = yaml.safe_load(text)
        except yaml.YAMLError as e:
            problems.append((rel, f"malformed YAML: {str(e).splitlines()[0]}"))
            continue
        if records is None:
            records = []
        record_problems = check_reference_records(records)
        if record_problems:
            problems.extend((rel, p) for p in record_problems)
            continue
        essay["refs"] = records

    return essays, problems


# --- rendering -----------------------------------------------------------

# How a `methods` value reads in a sentence, where the bare name would not.
# Anything else is written as given.
_TOOL_PHRASES = {"remarkable": "a reMarkable tablet"}


def _tool_phrase(value):
    return _TOOL_PHRASES.get(value.strip().casefold(), value.strip())


def _count(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def disclosure(methods, records, has_companion=False):
    """The sentences of "How this essay was made" (docs/ESSAYS.md, "The
    essay page"), from the essay's `methods` and its reference records.

    Never hand-written, so it cannot claim more or less than the data: each
    AI role in the closed vocabulary has its own sentence and drops out
    with it, and the counts are of the records, with "verified" counting
    `verified: true` only. Returns a dict of the sentences, in order, and
    the two counts, which the page and its tests read. With no AI role the
    note says no AI was used, unless the essay has a study companion: that
    sentence would sit directly above the AI-generated zone, so it is left
    out there (Travis, 2026-10-27). The roles name no vendor, so neither
    does the note: "an AI assistant", always true whichever tool was used.
    """
    roles = set(methods["ai_roles"])
    search, summaries, audit = (r in roles for r in AI_ROLES)
    sentences = [f"I wrote this essay by hand: the first draft on {_tool_phrase(methods['drafted_on'])}, "
                 f"the revisions in {_tool_phrase(methods['edited_in'])}."]
    if search or summaries:
        sentences.append("AI was used for research, not writing.")
    elif audit:
        sentences.append("AI was used to check citations, not to write.")
    elif not has_companion:
        sentences.append("No AI was used in researching or writing it.")
    if search and summaries:
        sentences.append("An AI assistant searched for sources and drafted short summaries of them; I checked each "
                         "summary against the original and wrote every evaluation myself.")
    elif search:
        sentences.append("An AI assistant searched for sources; I read each one and wrote every evaluation myself.")
    elif summaries:
        sentences.append("An AI assistant drafted short summaries of the sources; I checked each summary against the "
                         "original and wrote every evaluation myself.")
    if audit:
        sentences.append("An AI citation audit checked that each citation supports its claim and matches the "
                         "reference list; it flagged problems and changed no prose.")
    records = records or []
    total = len(records)
    verified = sum(1 for r in records if r.get("verified") is True)
    if total:
        sentences.append(f"{_count(total, 'source')}; {verified} of {total} verified against the original "
                         f"by the author.")
    return {"sentences": sentences, "sources": total, "verified": verified}


def listed_records(records, reference_list):
    """The records the reference list actually shows, once each, in file
    order. The disclosure note counts these, not the file: a record left
    out of the list (an unsupported type, a duplicate key) only warns, so a
    local build without --strict would otherwise say "14 sources" above a
    list of 13."""
    shown = {entry["key"] for entry in reference_list}
    listed, seen = [], set()
    for record in records or []:
        key = record.get("id")
        if key in shown and key not in seen:
            seen.add(key)
            listed.append(record)
    return listed


def companion_entries(companion):
    """The study companion as the template draws it: one player or link per
    entry, built from the structured fields only (kind, label, URL)."""
    return [{"kind": entry["kind"], "label": entry["label"].strip(), "url": entry["url"].strip(),
             "player": entry["kind"] in PLAYER_KINDS}
            for entry in companion or []]


def page_policy_sources(essay, media_origins):
    """The extra Content-Security-Policy sources one essay page needs, by
    directive, for engine/csp.py: the allowed media origins when it has a
    player, and the YouTube player's host when it has an episode. A page
    with neither keeps the site-wide policy unchanged."""
    sources = {}
    if any(entry["player"] for entry in essay["companion"]):
        sources["media-src"] = list(media_origins)
    if essay["youtube_id"]:
        sources["frame-src"] = [YOUTUBE_EMBED_ORIGIN]
    return sources

def reading_minutes(body):
    """Words divided by WORDS_PER_MINUTE, rounded up, never below one."""
    plain = _WIKILINK_RE.sub(lambda m: m.group(1).split("|", 1)[-1], body)
    words = len(re.findall(r"\S+", plain))
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def long_date(value):
    """'2026-11-20' -> 'Friday, 20 November 2026'. The weekday is part of
    the contract: an essay is dated the way a journal dates an article."""
    return f"{value:%A}, {value.day} {value:%B} {value.year}"


# The placeholder each Garden link is rendered as while nh3 runs, so the
# cleaner (which allows no class or data attribute) cannot strip the
# engine's own anchors; they are put back afterwards. Letters only, so nh3
# passes it through as text.
_LINK_SLOT = "AURELIAESSAYLINK{}END"


def render_body(body, essay_id, resolve, known_ids, garden_href, references=None):
    """The essay body as HTML. Returns Markup, since this is the end of
    the chain that can vouch for it:

      1. markdown-it renders with raw HTML off, so every tag in the output
         is its own and a tag typed into the essay shows as text. Its link
         validator refuses javascript: and data: destinations. CommonMark
         autolinks (<https://doi.org/...>) render as links, which is why
         the note text is not passed through the Garden's nh3 pass first:
         that one reads Markdown as HTML and would delete them.
      2. nh3 then cleans the rendered page on its default allowlist, as a
         second gate, which also drops the `style` attribute markdown-it
         puts on an aligned table cell (the Content-Security-Policy refuses
         inline styles; engine/csp.py).
      3. The [[wikilinks]] and the citations were rendered by the inline
         rules above into numbered slots and are written back last, as the
         engine's own anchors: to garden.html#<id>, and to the reference
         list's #ref-<key>. scan_essays() always passes `references`, empty
         for an essay with no reference file, so a citation there still
         warns; only a direct call without it leaves the syntax alone.
    """
    links = []

    def keep(markup):
        links.append(markup)
        return _LINK_SLOT.format(len(links) - 1)

    env = {"resolve": resolve, "known_ids": known_ids, "garden_href": garden_href,
           "essay_id": essay_id, "keep": keep, "essay_references": references}
    rendered = _markdown.render(body, env)
    cleaned = nh3.clean(rendered)
    restored = re.sub(_LINK_SLOT.format(r"(\d+)"), lambda m: links[int(m.group(1))], cleaned)
    return Markup(restored)


def scan_essays(folder, resolve, known_ids, discipline_ids=frozenset(), site_root="/", media_origins=()):
    """Reads the Essays folder and returns the essays ready for the
    templates, newest first. Raises EssayError, naming every file and
    problem, if anything in the folder fails the contract or a privacy
    check. An absent folder is simply no essays.

    `resolve` and `known_ids` come from the Garden scan (the same resolver
    the Garden's own wikilinks use); `discipline_ids` are the published
    Discipline notes, so a discipline label can link to its note;
    `site_root` is where the site is served from, since an essay page sits
    a folder or two down and links from the root like 404.html does;
    `media_origins` is user_config.json's allowlist for companion URLs.
    """
    essays, problems = check_essays_folder(folder, media_origins)
    if problems:
        lines = [f"{rel}: {message}" for rel, message in problems]
        raise EssayError(
            f"Essays folder {folder}: {len(problems)} problem(s), and every one stops the build "
            f"whether or not --strict is on (docs/ESSAYS.md, 'The privacy checks'):\n  - "
            + "\n  - ".join(lines)
        )

    garden_href = f"{site_root}garden.html"
    published = []
    for essay in essays:
        raw, body = essay["raw"], essay["body"]
        published_on = _as_date(raw["published"])
        updated_on = _as_date(raw["updated"]) if "updated" in raw else None
        disciplines = []
        for label in raw["disciplines"]:
            target_id = resolve(label.strip())
            disciplines.append({
                "label": label.strip(),
                "href": f"{garden_href}#{target_id}" if target_id in discipline_ids else None,
            })
        references = References(essay["refs"], raw["id"], f"{raw['id']}.refs.yaml")
        body_html = render_body(body, raw["id"], resolve, known_ids, garden_href, references)
        references.warn_uncited()
        reference_list = references.entries()
        published.append({
            "id": raw["id"],
            "slug": raw["slug"],
            "title": raw["title"].strip(),
            "url": f"essays/{raw['slug']}/",
            "published": published_on,
            "published_iso": published_on.isoformat(),
            "published_text": long_date(published_on),
            "updated": updated_on,
            "updated_iso": updated_on.isoformat() if updated_on else None,
            "updated_text": long_date(updated_on) if updated_on else None,
            "disciplines": disciplines,
            "thesis": raw["thesis"].strip(),
            "citation_style": raw["citation_style"],
            "methods": {
                "drafted_on": raw["methods"]["drafted_on"].strip(),
                "edited_in": raw["methods"]["edited_in"].strip(),
                "ai_roles": list(raw["methods"]["ai_roles"]),
            },
            "companion": companion_entries(raw.get("companion")),
            "youtube": raw["youtube"].strip() if raw.get("youtube") else None,
            "youtube_id": youtube_id(raw["youtube"]) if raw.get("youtube") else None,
            "disclosure": disclosure(raw["methods"], listed_records(essay["refs"], reference_list),
                                     has_companion=bool(raw.get("companion"))),
            "reading_minutes": reading_minutes(body),
            "body_html": body_html,
            "references": essay["refs"],
            # The APA 7 list (engine/citations.py); `references` stays the
            # records as written, which `disclosure` counts.
            "reference_list": reference_list,
            "source": essay["rel"],
        })

    # Newest first; the id breaks a tie so the order is the same on every
    # machine (tests/test_reproducible_build.py).
    published.sort(key=lambda e: (e["published"], e["id"]), reverse=True)
    return published
