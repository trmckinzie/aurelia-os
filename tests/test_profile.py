import json

import pytest

from engine import pipeline
from engine.profile import (
    PROFILE_FILENAME,
    ProfileError,
    load_profile,
    person_jsonld,
    validate_profile,
)
from tests.profile_fixtures import minimal_profile


# --- loading the real repo profile.json -------------------------------------

def test_repo_profile_json_validates():
    profile = load_profile()
    assert profile["identity"]["name"]
    assert profile["meta"]["updated"]


# --- structural validation ---------------------------------------------------

def test_unknown_top_level_key_raises():
    profile = minimal_profile()
    profile["extra_top_level_key"] = "nope"
    with pytest.raises(ProfileError, match="unknown key 'extra_top_level_key'"):
        validate_profile(profile)


def test_unknown_nested_key_raises():
    profile = minimal_profile()
    profile["identity"]["extra_nested_key"] = "nope"
    with pytest.raises(ProfileError, match="unknown key 'extra_nested_key'"):
        validate_profile(profile)


def _delete_identity_name(p):
    del p["identity"]["name"]


def _delete_role_title(p):
    del p["roles"][0]["title"]


def _delete_meta_updated(p):
    del p["meta"]["updated"]


@pytest.mark.parametrize("mutate,expected_path", [
    (_delete_identity_name, "identity.name"),
    (_delete_role_title, "roles[0].title"),
    (_delete_meta_updated, "meta.updated"),
])
def test_missing_required_key_raises(mutate, expected_path):
    profile = minimal_profile()
    mutate(profile)
    with pytest.raises(ProfileError, match=expected_path.replace("[", r"\[").replace("]", r"\]")):
        validate_profile(profile)


def test_wrong_schema_version_raises():
    profile = minimal_profile()
    profile["schema_version"] = 2
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_bool_schema_version_raises():
    profile = minimal_profile()
    profile["schema_version"] = True
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_missing_file_raises(tmp_path):
    missing = tmp_path / PROFILE_FILENAME
    with pytest.raises(ProfileError, match="profile.json"):
        load_profile(path=str(missing))


def test_malformed_json_raises(tmp_path):
    bad = tmp_path / PROFILE_FILENAME
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ProfileError, match="profile.json"):
        load_profile(path=str(bad))


# --- URL validation -----------------------------------------------------

@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "data:text/html,x",
    "//evil.example",
    "example.com",
    "JAVASCRIPT:alert(1)",
    "http://",     # empty netloc
    "mailto:",     # no '@'
])
def test_rejects_url_scheme(url):
    profile = minimal_profile()
    profile["links"][0]["url"] = url
    with pytest.raises(ProfileError):
        validate_profile(profile)


@pytest.mark.parametrize("url,kind", [
    ("http://example.com", "site"),
    ("https://example.com/path?q=1", "site"),
    ("mailto:someone@example.com", "email"),
    ("HTTPS://EXAMPLE.COM/", "site"),
])
def test_accepts_url(url, kind):
    profile = minimal_profile()
    profile["links"][0]["url"] = url
    profile["links"][0]["kind"] = kind
    validate_profile(profile)  # must not raise


# --- string validation ---------------------------------------------------

def test_rejects_over_length_string():
    profile = minimal_profile()
    profile["identity"]["name"] = "a" * 81  # max is 80
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_non_string_type():
    profile = minimal_profile()
    profile["identity"]["name"] = 12345
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_control_characters_in_url():
    profile = minimal_profile()
    profile["links"][0]["url"] = "https://example.com/\x07path"
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_newline_in_single_line_field():
    profile = minimal_profile()
    profile["identity"]["location"] = "Line one\nLine two"
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_unknown_project_status():
    profile = minimal_profile()
    profile["projects"][0]["status"] = "on-hold"
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_unknown_link_kind():
    profile = minimal_profile()
    profile["links"][0]["kind"] = "carrier-pigeon"
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_bad_updated_date():
    profile = minimal_profile()
    profile["meta"]["updated"] = "2026-13-45"
    with pytest.raises(ProfileError):
        validate_profile(profile)


def test_rejects_empty_skills_items():
    profile = minimal_profile()
    profile["skills"][0]["items"] = []
    with pytest.raises(ProfileError):
        validate_profile(profile)


# --- person_jsonld -----------------------------------------------------

def test_person_jsonld_sameas_excludes_mailto():
    profile = minimal_profile()
    profile["links"] = [
        {"label": "GitHub", "url": "https://github.com/example", "kind": "code"},
        {"label": "Email", "url": "mailto:someone@example.com", "kind": "email"},
    ]
    ld = person_jsonld(profile)
    assert ld["sameAs"] == ["https://github.com/example"]


def test_person_jsonld_worksfor_only_primary_roles():
    profile = minimal_profile()
    profile["roles"] = [
        {"org": "Primary Org", "title": "Lead", "period": "now", "description": "d", "primary": True},
        {"org": "Side Org", "title": "Advisor", "period": "now", "description": "d", "primary": False},
    ]
    ld = person_jsonld(profile)
    assert ld["worksFor"] == [{"@type": "Organization", "name": "Primary Org"}]


# --- pipeline wiring -----------------------------------------------------

def test_search_index_contains_an_about_entry():
    index = pipeline._build_search_index([], minimal_profile())
    about_entries = [e for e in index if e["url"] == "about.html"]
    assert len(about_entries) == 1
    assert about_entries[0]["type"] == "SYSTEM"
    assert "about" in about_entries[0]["tags"]


def test_build_fails_when_profile_is_invalid(monkeypatch):
    monkeypatch.setattr(pipeline, "prepare_dist", lambda: None)
    monkeypatch.setattr(pipeline, "organize_assets", lambda: None)
    monkeypatch.setattr(pipeline, "sync_vault_assets", lambda: None)

    def _raise():
        raise ProfileError("profile.json: forced failure for test")

    monkeypatch.setattr(pipeline, "load_profile", _raise)

    with pytest.raises(ProfileError):
        pipeline.build_all(sort_dropzone=False)


# --- CNAME writing -----------------------------------------------------

def test_cname_written_for_valid_domain(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", str(tmp_path))
    pipeline._write_cname({"site": {"domain": "example.com"}})
    assert (tmp_path / "CNAME").read_text(encoding="utf-8") == "example.com\n"


def test_cname_absent_when_domain_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", str(tmp_path))
    pipeline._write_cname({"site": {"domain": ""}})
    assert not (tmp_path / "CNAME").exists()

    # Also fine when "site" is missing entirely.
    pipeline._write_cname({})
    assert not (tmp_path / "CNAME").exists()


@pytest.mark.parametrize("domain", [
    "https://x.com",
    "x.com/",
    "-bad.com",
    "localhost",
    "a..b",
    "x.com:80",
    "EXAMPLE.COM",
])
def test_cname_rejects_invalid_domain(tmp_path, monkeypatch, domain):
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", str(tmp_path))
    with pytest.raises(RuntimeError):
        pipeline._write_cname({"site": {"domain": domain}})
    assert not (tmp_path / "CNAME").exists()


def test_json_module_sanity():
    # profile.json must at least be loadable as plain JSON independent of
    # our own validator, as a sanity check that the fixture above didn't
    # drift from valid JSON syntax.
    json.loads(json.dumps(minimal_profile()))
