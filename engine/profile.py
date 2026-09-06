"""Loads and validates profile.json: the data source for the About page.

Why this lives outside vault/, not as a note: vault/ is off-limits to
programmatic edits (a standing instruction, see CLAUDE.md), and the About
page's content isn't a Zettelkasten note in the first place -- it's a fixed
identity record (name, roles, education, projects, links) with no maturity,
no backlinks, nothing that belongs in the note graph. Putting it in a
repo-root JSON file keeps it structured, versioned, and editable without
touching a single vault path.

Why fail loud: unlike a garden note, About is one of only three published
pages this generator produces, alongside the Lobby and the Garden (see
CLAUDE.md's "What this project is"). A build that silently fell back to an
empty or partial About page would ship a nav link to a broken or misleading
page with no warning anywhere -- and because the file lives at the repo
root rather than inside the vault-scan loop, there's no existing "N notes
skipped" counter that would ever surface the problem. A missing or invalid
profile.json is therefore fatal to the whole build, not a warning: better a
build that refuses to run than a site whose About page is silently stale,
empty, or different from one build to the next.

Why no jsonschema (or any other new dependency): this is one JSON document
with a small, fixed, hand-authored schema -- the validation rules below are
simpler to read, test, and extend than a JSON Schema document would be, and
avoid adding a dependency for a project that otherwise has none in this
part of the pipeline. See tools/validate_vault_schema.py for the same
philosophy applied to vault frontmatter.
"""
import json
import os
import re
from datetime import date
from urllib.parse import urlsplit

from engine.config import ROOT_DIR

PROFILE_FILENAME = "profile.json"
SCHEMA_VERSION = 1
ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto"})

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class ProfileError(RuntimeError):
    """Raised for any problem loading or validating profile.json.

    Every message starts with "profile.json:" so it's unmistakable in build
    output and test failures alike, followed by a dotted/indexed path to the
    offending field when one is known (e.g. "profile.json: roles[2].url: ...").
    """


# --- generic helpers ---------------------------------------------------

def _fail(path, msg):
    if path:
        raise ProfileError(f"profile.json: {path}: {msg}")
    raise ProfileError(f"profile.json: {msg}")


def _join(parent, key):
    return f"{parent}.{key}" if parent else key


def _check_object(value, path, allowed_keys, required_keys):
    """Verifies `value` is a dict, rejects any key not in allowed_keys, and
    fails if any of required_keys is missing. Does not check value types --
    callers validate each field's type/content afterward."""
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    for key in value:
        if key not in allowed_keys:
            _fail(path, f"unknown key '{key}'")
    for key in required_keys:
        if key not in value:
            _fail(_join(path, key), "is required")


def _check_list(value, path, max_len, min_len=0):
    if not isinstance(value, list) or isinstance(value, (str, bytes)):
        _fail(path, "must be an array")
    if len(value) < min_len:
        _fail(path, f"must have at least {min_len} item(s)")
    if len(value) > max_len:
        _fail(path, f"must have at most {max_len} item(s)")


def _has_forbidden_control_chars(value, multiline):
    for ch in value:
        code = ord(ch)
        if code == 0x7f:
            return True
        if code < 0x20:
            if multiline and ch in ("\n", "\t"):
                continue
            return True
    return False


def _check_str(value, path, max_len, multiline=False):
    """A required-when-present string: 1..max_len chars, no bare/whitespace-
    only value, and no control characters (multiline fields tolerate \\n/\\t).

    Every string field in this schema -- required or optional -- documents an
    explicit minimum of 1, so there is no separate "optional, may be empty"
    case to handle: a field is either absent, or present and non-empty.
    """
    if not isinstance(value, str) or isinstance(value, bool):
        _fail(path, "must be a string")
    if value.strip() == "":
        _fail(path, "must not be empty")
    if len(value) > max_len:
        _fail(path, f"exceeds maximum length of {max_len} characters")
    if _has_forbidden_control_chars(value, multiline):
        if multiline:
            _fail(path, "contains disallowed control characters")
        else:
            _fail(path, "must not contain newlines or control characters")


def _check_bool(value, path):
    if not isinstance(value, bool):
        _fail(path, "must be a boolean")


def _check_enum(value, allowed, path):
    if value not in allowed:
        _fail(path, f"must be one of {sorted(allowed)}")


def _validate_url(value, path):
    """A URL string: <=500 chars, no control chars, an allowed scheme, and a
    scheme-appropriate non-empty target (host for http/https, an '@'-bearing
    address for mailto). Rejects javascript:, data:, schemeless/protocol-
    relative strings, and empty http(s) hosts or mailto addresses.
    """
    if not isinstance(value, str) or isinstance(value, bool):
        _fail(path, "must be a string")
    if len(value) > 500:
        _fail(path, "exceeds maximum length of 500 characters")
    if _has_forbidden_control_chars(value, multiline=False):
        _fail(path, "must not contain control characters")

    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_URL_SCHEMES:
        _fail(path, f"scheme '{parts.scheme}' not allowed (http, https, mailto)")

    if scheme in ("http", "https"):
        if not parts.netloc:
            _fail(path, "http/https url must have a non-empty host")
    elif scheme == "mailto":
        if not parts.path or "@" not in parts.path:
            _fail(path, "mailto url must have a non-empty address containing '@'")


# --- section schemas -----------------------------------------------------

_TOP_LEVEL_KEYS = {
    "schema_version", "identity", "roles", "education", "skills",
    "projects", "links", "meta",
}

_IDENTITY_ALLOWED = {"name", "headline", "location", "summary", "pronouns"}
_IDENTITY_REQUIRED = {"name", "headline", "location", "summary"}
_IDENTITY_SPECS = {
    "name": (80, False),
    "headline": (160, False),
    "location": (80, False),
    "summary": (1200, True),
    "pronouns": (30, False),
}

_ROLE_ALLOWED = {"org", "title", "period", "description", "url", "primary"}
_ROLE_REQUIRED = {"org", "title", "period", "description", "primary"}
_ROLE_SPECS = {
    "org": (100, False),
    "title": (100, False),
    "period": (40, False),
    "description": (600, True),
}

_EDU_ALLOWED = {"institution", "credential", "period", "detail", "url"}
_EDU_REQUIRED = {"institution", "credential", "period"}
_EDU_SPECS = {
    "institution": (100, False),
    "credential": (120, False),
    "period": (40, False),
    "detail": (400, True),
}

_SKILL_ALLOWED = {"group", "items"}
_SKILL_REQUIRED = {"group", "items"}

_PROJECT_ALLOWED = {"name", "description", "url", "tags", "status"}
_PROJECT_REQUIRED = {"name", "description", "tags", "status"}
_PROJECT_SPECS = {
    "name": (100, False),
    "description": (600, True),
}
_PROJECT_STATUS_ENUM = frozenset({"active", "maintained", "archived", "prototype"})

_LINK_ALLOWED = {"label", "url", "kind"}
_LINK_REQUIRED = {"label", "url", "kind"}
_LINK_KIND_ENUM = frozenset({"email", "code", "social", "writing", "site"})

_META_ALLOWED = {"updated", "availability"}
_META_REQUIRED = {"updated"}


def _validate_identity(value, path):
    _check_object(value, path, _IDENTITY_ALLOWED, _IDENTITY_REQUIRED)
    for field, (max_len, multiline) in _IDENTITY_SPECS.items():
        if field in value:
            _check_str(value[field], _join(path, field), max_len, multiline)


def _validate_roles(value, path):
    _check_list(value, path, max_len=20)
    for i, item in enumerate(value):
        item_path = f"{path}[{i}]"
        _check_object(item, item_path, _ROLE_ALLOWED, _ROLE_REQUIRED)
        for field, (max_len, multiline) in _ROLE_SPECS.items():
            if field in item:
                _check_str(item[field], _join(item_path, field), max_len, multiline)
        if "url" in item:
            _validate_url(item["url"], _join(item_path, "url"))
        if "primary" in item:
            _check_bool(item["primary"], _join(item_path, "primary"))


def _validate_education(value, path):
    _check_list(value, path, max_len=10)
    for i, item in enumerate(value):
        item_path = f"{path}[{i}]"
        _check_object(item, item_path, _EDU_ALLOWED, _EDU_REQUIRED)
        for field, (max_len, multiline) in _EDU_SPECS.items():
            if field in item:
                _check_str(item[field], _join(item_path, field), max_len, multiline)
        if "url" in item:
            _validate_url(item["url"], _join(item_path, "url"))


def _validate_skills(value, path):
    _check_list(value, path, max_len=8, min_len=1)
    for i, item in enumerate(value):
        item_path = f"{path}[{i}]"
        _check_object(item, item_path, _SKILL_ALLOWED, _SKILL_REQUIRED)
        if "group" in item:
            _check_str(item["group"], _join(item_path, "group"), 40, False)
        items_path = _join(item_path, "items")
        items_val = item.get("items")
        _check_list(items_val, items_path, max_len=20, min_len=1)
        for j, s in enumerate(items_val):
            _check_str(s, f"{items_path}[{j}]", 40, False)


def _validate_projects(value, path):
    _check_list(value, path, max_len=12)
    for i, item in enumerate(value):
        item_path = f"{path}[{i}]"
        _check_object(item, item_path, _PROJECT_ALLOWED, _PROJECT_REQUIRED)
        for field, (max_len, multiline) in _PROJECT_SPECS.items():
            if field in item:
                _check_str(item[field], _join(item_path, field), max_len, multiline)
        if "url" in item:
            _validate_url(item["url"], _join(item_path, "url"))
        tags_path = _join(item_path, "tags")
        tags_val = item.get("tags")
        _check_list(tags_val, tags_path, max_len=8, min_len=0)
        for j, t in enumerate(tags_val):
            _check_str(t, f"{tags_path}[{j}]", 30, False)
        if "status" in item:
            _check_enum(item["status"], _PROJECT_STATUS_ENUM, _join(item_path, "status"))


def _validate_links(value, path):
    _check_list(value, path, max_len=10)
    for i, item in enumerate(value):
        item_path = f"{path}[{i}]"
        _check_object(item, item_path, _LINK_ALLOWED, _LINK_REQUIRED)
        if "label" in item:
            _check_str(item["label"], _join(item_path, "label"), 40, False)
        if "url" in item:
            _validate_url(item["url"], _join(item_path, "url"))
        if "kind" in item:
            _check_enum(item["kind"], _LINK_KIND_ENUM, _join(item_path, "kind"))


def _validate_meta(value, path):
    _check_object(value, path, _META_ALLOWED, _META_REQUIRED)
    if "updated" in value:
        updated_path = _join(path, "updated")
        updated = value["updated"]
        _check_str(updated, updated_path, 10, False)
        if not _DATE_RE.match(updated):
            _fail(updated_path, "must match YYYY-MM-DD")
        else:
            try:
                date.fromisoformat(updated)
            except ValueError as e:
                _fail(updated_path, f"is not a valid calendar date ({e})")
    if "availability" in value:
        _check_str(value["availability"], _join(path, "availability"), 160, False)


def _validate_schema_version(value, path):
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(path, "must be an integer")
    if value != SCHEMA_VERSION:
        _fail(path, f"must equal {SCHEMA_VERSION}")


def validate_profile(data):
    """Validates `data` against profile.json's schema, hand-written (see
    module docstring for why no jsonschema). Rejects unknown keys at every
    depth and never coerces types -- a bool or int where a string is
    expected is an error, not a silent cast.

    Raises ProfileError with a path-qualified message on the first problem
    found. Returns `data` unchanged on success.
    """
    _check_object(data, "", _TOP_LEVEL_KEYS, _TOP_LEVEL_KEYS)

    _validate_schema_version(data["schema_version"], "schema_version")
    _validate_identity(data["identity"], "identity")
    _validate_roles(data["roles"], "roles")
    _validate_education(data["education"], "education")
    _validate_skills(data["skills"], "skills")
    _validate_projects(data["projects"], "projects")
    _validate_links(data["links"], "links")
    _validate_meta(data["meta"], "meta")

    return data


def load_profile(path=None):
    """Reads, parses, and validates profile.json. Fatal by design (see
    module docstring): a missing file, unreadable file, invalid JSON, or a
    schema violation all raise ProfileError rather than falling back to a
    default -- a conditionally-present About page would make the site's nav
    differ from one build to the next depending on whether the file happened
    to be there.
    """
    if path is None:
        path = os.path.join(ROOT_DIR, PROFILE_FILENAME)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raise ProfileError(f"profile.json: no file found at {path}") from None
    except OSError as e:
        raise ProfileError(f"profile.json: could not read {path}: {e}") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProfileError(f"profile.json: invalid JSON in {path}: {e}") from e

    return validate_profile(data)


def person_jsonld(profile):
    """Builds a schema.org Person JSON-LD object from a validated profile
    dict. Returns a plain dict -- no HTML, no Markup, no Jinja -- callers
    serialize it with textutils.dumps_for_script_tag(), the sink that knows
    how to embed JSON safely inside a <script> tag.
    """
    identity = profile["identity"]

    same_as = [
        link["url"] for link in profile.get("links", [])
        if urlsplit(link["url"]).scheme.lower() in ("http", "https")
    ]

    works_for = [
        {"@type": "Organization", "name": role["org"]}
        for role in profile.get("roles", [])
        if role.get("primary")
    ]

    alumni_of = []
    seen_institutions = set()
    for edu in profile.get("education", []):
        institution = edu["institution"]
        if institution not in seen_institutions:
            seen_institutions.add(institution)
            alumni_of.append({"@type": "EducationalOrganization", "name": institution})

    return {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": identity["name"],
        "jobTitle": identity["headline"],
        "description": identity["summary"],
        "address": {"@type": "PostalAddress", "addressLocality": identity["location"]},
        "sameAs": same_as,
        "worksFor": works_for,
        "alumniOf": alumni_of,
    }
