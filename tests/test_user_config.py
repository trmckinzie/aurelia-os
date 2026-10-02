"""user_config.json is validated strictly and a bad one stops the build.

The loader used to print a warning and fall back to a stub config, so a JSON
typo built a Lobby with a blank name and an empty Toolkit, exited 0, and
deployed (docs/roadmap.yaml, S05).
"""
import copy
import json
import os

import pytest

import build
import deploy
from engine import user_config as user_config_module
from engine.config import ROOT_DIR
from engine.user_config import UserConfigError, load_user_config, validate_user_config


def _minimal():
    return {
        "system_name": "Site",
        "status_message": "Working notebook",
        "author": {"name": "A. Person", "role": "Writer", "bio_short": "Writes things."},
        "tech_stack": [{"name": "Tool", "type": "SOFTWARE / EDITOR", "icon": "🛠️", "desc": "An editor."}],
    }


def _write(tmp_path, text):
    path = tmp_path / "user_config.json"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_real_user_config_is_valid():
    load_user_config()


def test_factory_config_is_valid():
    # deploy.py writes FACTORY_CONFIG into every factory clone, and the clone
    # runs this same engine, so the clone must not fail its first build.
    validate_user_config(copy.deepcopy(deploy.FACTORY_CONFIG))


def test_minimal_config_is_valid():
    validate_user_config(_minimal())


def test_malformed_json_names_the_file_and_position(tmp_path):
    path = _write(tmp_path, '{"system_name": "Site",, }')
    with pytest.raises(UserConfigError, match=r"^user_config\.json: invalid JSON .*line 1"):
        load_user_config(path)


def test_missing_file_is_an_error(tmp_path):
    with pytest.raises(UserConfigError, match="no file found"):
        load_user_config(str(tmp_path / "absent.json"))


@pytest.mark.parametrize("mutate, message", [
    (lambda c: c.pop("author"), "missing required key 'author'"),
    (lambda c: c["author"].pop("name"), r"author: missing required key 'name'"),
    (lambda c: c.update(sytem_name="typo"), "unknown key 'sytem_name'"),
    (lambda c: c.update(system_name=""), "system_name: must not be empty"),
    (lambda c: c.update(status_message=5), "status_message: must be a string"),
    (lambda c: c["author"].update(email="not an email"), "author.email: must be an email"),
    (lambda c: c.update(links={"github": "javascript:alert(1)"}), r"links\.github: must be an http\(s\) URL"),
    (lambda c: c.update(site={"domain": 7}), r"site\.domain: must be a string"),
    (lambda c: c.update(tech_stack={}), "tech_stack: must be an array"),
    (lambda c: c["tech_stack"][0].pop("icon"), r"tech_stack\[0\]: missing required key 'icon'"),
    (lambda c: c["tech_stack"][0].update(draft="yes"), r"tech_stack\[0\]\.draft: must be a boolean"),
    (lambda c: c["tech_stack"][0].update(name="two\nlines"), r"tech_stack\[0\]\.name: must not contain newlines"),
])
def test_schema_violations_name_the_field(mutate, message):
    config = _minimal()
    mutate(config)
    with pytest.raises(UserConfigError, match=message):
        validate_user_config(config)


def test_empty_domain_means_no_custom_domain():
    config = _minimal()
    config["site"] = {"domain": ""}
    validate_user_config(config)


def test_build_exits_non_zero_on_malformed_user_config(tmp_path, monkeypatch, capsys):
    """The S05 done_when: a malformed user_config.json makes build.py exit
    non-zero with a message naming the problem. load_user_config() runs
    before anything touches dist/ or the vault, so nothing else needs
    stubbing to keep this test off the real build."""
    _write(tmp_path, '{"system_name": "Site"')
    monkeypatch.setattr(user_config_module, "ROOT_DIR", str(tmp_path))

    assert build.main(["--no-sort"]) == 1

    err = capsys.readouterr().err
    assert "BUILD FAILED" in err
    assert "user_config.json: invalid JSON" in err


def test_real_config_is_unchanged_by_validation():
    with open(os.path.join(ROOT_DIR, "user_config.json"), encoding="utf-8") as f:
        raw = json.load(f)
    assert load_user_config() == raw
