import json
import os

import pytest

from engine import pipeline
from engine.config import ROOT_DIR
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


# --- identity.photo validation -------------------------------------------
#
# validate_profile() takes no filesystem root by default, so these run
# shape-only checks the same way every test above does. Only the last three
# tests pass `root=` explicitly to exercise the resolve-then-verify existence
# check (see engine.profile._photo_file_exists).

def test_photo_optional_absent_is_valid():
    profile = minimal_profile()
    assert "photo" not in profile["identity"]
    validate_profile(profile)  # must not raise


def test_photo_requires_src_and_alt():
    profile = minimal_profile()
    profile["identity"]["photo"] = {"src": "assets/images/x.webp"}
    with pytest.raises(ProfileError, match=r"identity\.photo\.alt"):
        validate_profile(profile)

    profile = minimal_profile()
    profile["identity"]["photo"] = {"alt": "A photo"}
    with pytest.raises(ProfileError, match=r"identity\.photo\.src"):
        validate_profile(profile)


def test_photo_rejects_unknown_key():
    profile = minimal_profile()
    profile["identity"]["photo"] = {
        "src": "assets/images/x.webp", "alt": "A photo", "caption": "nope",
    }
    with pytest.raises(ProfileError, match="unknown key 'caption'"):
        validate_profile(profile)


@pytest.mark.parametrize("src", [
    "../assets/images/x.webp",
    "assets/images/../../secret.png",
    "/assets/images/x.webp",
    "assets\\images\\x.webp",
    "https://evil.example/x.webp",
    "assets/images/x.svg",
    "assets/audio/x.webp",
    "assets/images/.hidden.webp",
])
def test_photo_rejects_bad_src(src):
    profile = minimal_profile()
    profile["identity"]["photo"] = {"src": src, "alt": "A photo"}
    with pytest.raises(ProfileError, match=r"identity\.photo\.src"):
        validate_profile(profile)


def test_photo_missing_file_raises(tmp_path):
    profile = minimal_profile()
    profile["identity"]["photo"] = {"src": "assets/images/nope.webp", "alt": "A photo"}
    with pytest.raises(ProfileError, match="photo not found"):
        validate_profile(profile, root=str(tmp_path))


def test_photo_existing_file_passes(tmp_path):
    images_dir = tmp_path / "assets" / "images"
    images_dir.mkdir(parents=True)
    (images_dir / "x.webp").write_bytes(b"not a real image, existence is all that matters")

    profile = minimal_profile()
    profile["identity"]["photo"] = {"src": "assets/images/x.webp", "alt": "A photo"}
    validate_profile(profile, root=str(tmp_path))  # must not raise


def test_repo_profile_photo_exists():
    profile = load_profile()
    photo = profile["identity"].get("photo")
    assert photo, "profile.json's identity.photo should be set"
    resolved = os.path.realpath(os.path.join(ROOT_DIR, photo["src"]))
    assert os.path.isfile(resolved)


# identity.portrait shares _validate_photo with identity.photo, so these only
# pin that it is routed through the same checks under its own path.

def test_portrait_requires_alt():
    profile = minimal_profile()
    profile["identity"]["portrait"] = {"src": "assets/images/x.webp"}
    with pytest.raises(ProfileError, match=r"identity\.portrait\.alt"):
        validate_profile(profile)


def test_portrait_rejects_bad_src():
    profile = minimal_profile()
    profile["identity"]["portrait"] = {"src": "https://evil.example/x.webp", "alt": "A photo"}
    with pytest.raises(ProfileError, match=r"identity\.portrait\.src"):
        validate_profile(profile)


def test_portrait_missing_file_raises(tmp_path):
    profile = minimal_profile()
    profile["identity"]["portrait"] = {"src": "assets/images/nope.webp", "alt": "A photo"}
    with pytest.raises(ProfileError, match="photo not found"):
        validate_profile(profile, root=str(tmp_path))


# --- theme-matched images (docs/DECISIONS.md item 49) -------------------

def _with_variant(field, variant, key="CYBER_PRIME"):
    profile = minimal_profile()
    profile["identity"][field] = {"src": "assets/images/a.webp", "alt": "A photo",
                                  "themes": {key: variant}}
    return profile


@pytest.mark.parametrize("field", ["photo", "portrait"])
def test_theme_variant_validates(field):
    validate_profile(_with_variant(field, {"src": "assets/images/b.webp", "alt": "An avatar"}))


@pytest.mark.parametrize("field", ["photo", "portrait"])
def test_theme_variant_requires_alt(field):
    # Every image a theme can show is on the published page, so each one
    # needs its own alt text; it never inherits the default's.
    profile = _with_variant(field, {"src": "assets/images/b.webp"})
    with pytest.raises(ProfileError, match=rf"identity\.{field}\.themes\.CYBER_PRIME\.alt"):
        validate_profile(profile)


def test_theme_variant_rejects_an_unknown_theme():
    profile = _with_variant("portrait", {"src": "assets/images/b.webp", "alt": "An avatar"},
                            key="cyber-prime")
    with pytest.raises(ProfileError, match=r"identity\.portrait\.themes: unknown key 'cyber-prime'"):
        validate_profile(profile)


def test_theme_variant_rejects_bad_src():
    profile = _with_variant("portrait", {"src": "https://evil.example/b.webp", "alt": "An avatar"})
    with pytest.raises(ProfileError, match=r"identity\.portrait\.themes\.CYBER_PRIME\.src"):
        validate_profile(profile)


def test_theme_variant_cannot_nest_themes():
    profile = _with_variant("portrait", {"src": "assets/images/b.webp", "alt": "An avatar",
                                         "themes": {}})
    with pytest.raises(ProfileError, match=r"themes\.CYBER_PRIME: unknown key 'themes'"):
        validate_profile(profile)


def test_theme_variant_missing_file_raises(tmp_path):
    images = tmp_path / "assets" / "images"
    images.mkdir(parents=True)
    (images / "a.webp").write_bytes(b"")
    profile = _with_variant("portrait", {"src": "assets/images/nope.webp", "alt": "An avatar"})
    with pytest.raises(ProfileError, match=r"themes\.CYBER_PRIME\.src: photo not found"):
        validate_profile(profile, root=str(tmp_path))


def test_repo_profile_matches_its_images_to_the_two_offered_themes():
    # The handoff of 2026-10-28: TIMBERLINE shows the photo, CYBER_PRIME the
    # AI avatar, on the Lobby hero and the round photo alike; every other
    # theme falls back to the photo. load_profile() has already proven each
    # file exists.
    identity = load_profile()["identity"]
    assert identity["portrait"]["src"] == "assets/images/hero-portrait-timberline.webp"
    assert identity["portrait"]["themes"]["CYBER_PRIME"]["src"] == "assets/images/hero-portrait-cyber-prime.webp"
    assert identity["photo"]["themes"]["CYBER_PRIME"]["src"] == "assets/images/headshot-cyber-prime.webp"
    for field in ("photo", "portrait"):
        assert list(identity[field]["themes"]) == ["CYBER_PRIME"]
        assert "AI avatar" in identity[field]["themes"]["CYBER_PRIME"]["alt"]
        assert "avatar" not in identity[field]["alt"]


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


def test_person_jsonld_carries_the_site_url_only_when_given():
    # Roadmap S14: the schema.org Person names the custom domain, and claims
    # no address at all without one.
    assert "url" not in person_jsonld(minimal_profile())
    ld = person_jsonld(minimal_profile(), "https://example.com/")
    assert ld["url"] == "https://example.com/"


def test_site_url_follows_site_domain():
    assert pipeline._site_url({"site": {"domain": "example.com"}}) == "https://example.com/"
    assert pipeline._site_url({"site": {"domain": ""}}) is None
    assert pipeline._site_url({}) is None


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
    monkeypatch.setattr(pipeline, "publish_referenced_media", lambda referenced: None)

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
