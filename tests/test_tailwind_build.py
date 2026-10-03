"""Tests for engine/tailwind_build.py's generate_config() -- the theme-
independent tailwind.config.js (see that module's docstring for why it no
longer varies by theme). compile_css() itself needs the real Tailwind CLI
and node_modules/, so it is exercised by `bash verify.sh`'s real build, not
here.
"""
from engine import tailwind_build
from engine.tailwind_build import generate_config


def test_generate_config_writes_to_root_dir(tmp_path, monkeypatch):
    # ROOT_DIR, not OUTPUT_DIR -- tailwind.config.js lives at the project
    # root (npx reads it from cwd), not in dist/. Patched so the test never
    # touches this repo's own tailwind.config.js.
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path))
    config_path = generate_config()

    assert config_path == str(tmp_path / "tailwind.config.js")
    assert (tmp_path / "tailwind.config.js").is_file()


def test_generate_config_wires_every_semantic_color_to_its_css_variable(tmp_path, monkeypatch):
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path))
    config_path = generate_config()
    config_js = open(config_path, encoding="utf-8").read()

    # The RGB-channel form, not a bare hex var() -- see the module
    # docstring on why a plain var(--aurelia-x) breaks the /opacity modifier.
    for name, var in [
        ("aurelia-bg", "bg-main"),
        ("aurelia-primary", "primary"),
        ("aurelia-accent", "accent"),
        ("aurelia-insight", "insight"),
    ]:
        assert f"'{name}': 'rgb(var(--aurelia-{var}-rgb) / <alpha-value>)'" in config_js


def test_generate_config_never_reintroduces_the_retired_aliases(tmp_path, monkeypatch):
    # aurelia-cyan/dim/dark/orange/green/purple were pre-semantic aliases
    # pointing at the same variables as a semantic name -- removed once
    # every call site moved to the semantic one (see the module docstring).
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path))
    config_js = open(generate_config(), encoding="utf-8").read()
    for retired in ("aurelia-cyan", "aurelia-dim", "aurelia-dark",
                    "aurelia-orange", "aurelia-green", "aurelia-purple"):
        assert f"'{retired}'" not in config_js


def test_generate_config_content_glob_scans_the_rendered_dist_output(tmp_path, monkeypatch):
    # Not the Python/Jinja source -- cards.py assembles some class names
    # dynamically, and only the rendered HTML in dist/ has them as literal
    # text Tailwind's scanner can see (see the module docstring).
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path))
    config_js = open(generate_config(), encoding="utf-8").read()
    assert 'content: ["./dist/**/*.html"]' in config_js


def test_generate_config_writes_lf_line_endings(tmp_path, monkeypatch):
    # Reproducibility (roadmap S09): text mode would otherwise write CRLF
    # on Windows for the same commit CI builds with LF.
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path))
    config_path = generate_config()
    raw = open(config_path, "rb").read()
    assert b"\r\n" not in raw


def test_generate_config_is_byte_identical_across_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path / "a"))
    (tmp_path / "a").mkdir()
    first = open(generate_config(), "rb").read()

    monkeypatch.setattr(tailwind_build, "ROOT_DIR", str(tmp_path / "b"))
    (tmp_path / "b").mkdir()
    second = open(generate_config(), "rb").read()

    assert first == second
