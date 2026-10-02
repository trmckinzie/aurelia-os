"""Loads and validates user_config.json: site identity and the Lobby's Toolkit.

Fatal by design, for the reason engine/profile.py gives for profile.json.
This loader used to catch every error, print one warning, and carry on with
{"author": {"name": "Unknown User"}} -- so a JSON typo built a Lobby titled
"Personal site" with a blank name and an empty Toolkit, exited 0, and CI
deployed it (docs/roadmap.yaml, S05). A bad file now stops the build with a
message naming the field, the same way profile.json does.

The schema is the set of keys the templates actually read (base.html,
indextemplate.html) plus the ones deploy.py's FACTORY_CONFIG writes. Unknown
keys are rejected so a misspelt key fails here instead of silently rendering
nothing. Like profile.py, this is hand-written rules rather than JSON Schema,
to keep the dependency list where it is.

What this does not check: the Toolkit copy's voice rule and length budget,
which tests/test_lobby.py enforces on the real file, and site.domain's format,
which pipeline._write_cname() validates when it writes dist/CNAME.
"""
import json
import os
from urllib.parse import urlsplit

from engine.config import ROOT_DIR

USER_CONFIG_FILENAME = "user_config.json"


class UserConfigError(RuntimeError):
    """Raised for any problem loading or validating user_config.json.

    Every message starts with "user_config.json:" and, when one is known, a
    dotted path to the field (e.g. "user_config.json: tech_stack[3].icon: ...").
    """


def _fail(path, msg):
    if path:
        raise UserConfigError(f"user_config.json: {path}: {msg}")
    raise UserConfigError(f"user_config.json: {msg}")


def _check_object(value, path, allowed, required):
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    for key in value:
        if key not in allowed:
            _fail(path, f"unknown key '{key}'")
    for key in required:
        if key not in value:
            _fail(path, f"missing required key '{key}'")


def _join(parent, key):
    return f"{parent}.{key}" if parent else key


def _check_str(value, path, max_len, multiline=False, allow_empty=False):
    if not isinstance(value, str):
        _fail(path, "must be a string")
    if not allow_empty and value.strip() == "":
        _fail(path, "must not be empty")
    if len(value) > max_len:
        _fail(path, f"exceeds maximum length of {max_len} characters")
    for ch in value:
        code = ord(ch)
        if code == 0x7f or (code < 0x20 and not (multiline and ch in "\n\t")):
            _fail(path, "must not contain newlines or control characters"
                  if not multiline else "contains disallowed control characters")


def _check_url(value, path):
    _check_str(value, path, 500)
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        _fail(path, "must be an http(s) URL with a host")


def _check_email(value, path):
    # A mailto: target in base.html's footer. Loose on purpose: one '@' with
    # something either side and no whitespace catches the typos that matter.
    _check_str(value, path, 254)
    local, sep, domain = value.partition("@")
    if not sep or not local or "." not in domain or any(c.isspace() for c in value):
        _fail(path, "must be an email address like name@example.com")


# key -> (max length, required)
_SITE_FIELDS = {"name": (120, False), "nav_label": (40, False), "tagline": (300, False)}
_AUTHOR_FIELDS = {
    "name": (120, True), "short_name": (40, False), "role": (200, True),
    "location": (120, False), "bio_short": (300, True),
}
_TOOL_FIELDS = {
    "name": (80, True), "type": (80, True), "icon": (16, True), "desc": (300, True),
    "what_it_is": (2000, False), "how_i_use_it": (2000, False),
}
_TOP_LEVEL = {
    "system_name": True, "system_version": False, "status_message": True,
    "site": False, "author": True, "links": False, "tech_stack": True,
}


def _check_fields(obj, path, fields):
    for key, (max_len, _required) in fields.items():
        if key in obj:
            _check_str(obj[key], _join(path, key), max_len)


def _validate_site(value, path):
    _check_object(value, path, set(_SITE_FIELDS) | {"domain"}, ())
    _check_fields(value, path, _SITE_FIELDS)
    if "domain" in value:
        # "" means no custom domain; _write_cname() checks a non-empty value.
        _check_str(value["domain"], _join(path, "domain"), 253, allow_empty=True)


def _validate_author(value, path):
    allowed = set(_AUTHOR_FIELDS) | {"email", "bio_long"}
    required = [k for k, (_, req) in _AUTHOR_FIELDS.items() if req]
    _check_object(value, path, allowed, required)
    _check_fields(value, path, _AUTHOR_FIELDS)
    if "email" in value:
        _check_email(value["email"], _join(path, "email"))
    if "bio_long" in value:
        _check_str(value["bio_long"], _join(path, "bio_long"), 3000, multiline=True)


def _validate_links(value, path):
    _check_object(value, path, {"github"}, ())
    if "github" in value:
        _check_url(value["github"], _join(path, "github"))


def _validate_tech_stack(value, path):
    if not isinstance(value, list):
        _fail(path, "must be an array")
    if len(value) > 100:
        _fail(path, "must have at most 100 item(s)")
    required = [k for k, (_, req) in _TOOL_FIELDS.items() if req]
    for i, tool in enumerate(value):
        item_path = f"{path}[{i}]"
        _check_object(tool, item_path, set(_TOOL_FIELDS) | {"draft"}, required)
        _check_fields(tool, item_path, _TOOL_FIELDS)
        if "draft" in tool and not isinstance(tool["draft"], bool):
            _fail(_join(item_path, "draft"), "must be a boolean")


def validate_user_config(data):
    """Returns `data` unchanged if it satisfies the schema, else raises
    UserConfigError naming the first problem found."""
    required = [k for k, req in _TOP_LEVEL.items() if req]
    _check_object(data, "", set(_TOP_LEVEL), required)
    _check_str(data["system_name"], "system_name", 120)
    if "system_version" in data:
        _check_str(data["system_version"], "system_version", 40)
    _check_str(data["status_message"], "status_message", 200)
    if "site" in data:
        _validate_site(data["site"], "site")
    _validate_author(data["author"], "author")
    if "links" in data:
        _validate_links(data["links"], "links")
    _validate_tech_stack(data["tech_stack"], "tech_stack")
    return data


def load_user_config(path=None):
    """Reads, parses, and validates user_config.json. A missing file, an
    unreadable one, invalid JSON, or a schema violation all raise
    UserConfigError; nothing falls back to defaults."""
    if path is None:
        path = os.path.join(ROOT_DIR, USER_CONFIG_FILENAME)

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raise UserConfigError(f"user_config.json: no file found at {path}") from None
    except OSError as e:
        raise UserConfigError(f"user_config.json: could not read {path}: {e}") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise UserConfigError(f"user_config.json: invalid JSON in {path}: {e}") from e

    return validate_user_config(data)
