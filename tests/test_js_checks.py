"""The JavaScript lint and unit tests are part of the check suite (roadmap S13).

The Garden's script is modules under assets/js/garden/ with unit tests under
tests/js/. Neither is Python, so pytest cannot run them; what it can do is
hold the wiring that makes them count: verify.sh runs both, before the
build, and CI runs verify.sh (tests/test_browser_suite.py holds that half).
Without this a later edit to verify.sh could drop the step and every other
check would stay green.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ROOT / "assets" / "js" / "garden"
JS_TESTS = ROOT / "tests" / "js"


def _read(*parts):
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_verify_sh_lints_and_unit_tests_the_modules_before_the_build():
    script = _read("verify.sh")
    lint = script.index("\nnpx --no-install eslint\n")
    unit = script.index('\nnode --test "tests/js/*.test.mjs"\n')
    first_build = script.index('build.py "${BUILD_FLAGS[@]}"')
    assert lint < unit < first_build
    assert script.index("verify.sh: all checks passed") > unit


def test_eslint_is_an_exact_pinned_dev_dependency():
    package = json.loads(_read("package.json"))
    for name in ("eslint", "@eslint/js"):
        version = package["devDependencies"][name]
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"{name} is not pinned exactly: {version}"
        assert name not in package.get("dependencies", {})
    lock = json.loads(_read("package-lock.json"))
    assert lock["packages"]["node_modules/eslint"]["version"] == package["devDependencies"]["eslint"]


def test_the_package_is_esm_so_node_reads_the_modules_as_the_browser_does():
    # Without "type": "module" Node guesses each .js file's format, warns,
    # and reparses it; the browser has no such doubt about a module script.
    assert json.loads(_read("package.json"))["type"] == "module"


def test_the_lint_covers_the_modules_and_their_tests_and_nothing_else():
    config = _read("eslint.config.mjs")
    assert 'files: ["assets/js/garden/**/*.js"]' in config
    assert '"tests/js/**/*.mjs"' in config
    # A bare `eslint` must not walk into the Obsidian plugins under vault/
    # or the built copies under dist/.
    assert '"**/*.js", "!assets/js/garden/**/*.js"' in config
    for rule in ("no-undef", "no-unused-vars"):
        assert rule in config
    assert "...js.configs.recommended.rules" in config, "a rules block must extend the recommended set, not replace it"


def test_the_unit_tests_cover_the_logic_the_roadmap_names():
    # Roadmap S13's done_when: tests for at least the sorting, filtering and
    # roving-focus logic.
    names = {p.name for p in JS_TESTS.glob("*.test.mjs")}
    assert {"sorting.test.mjs", "filtering.test.mjs", "roving.test.mjs"} <= names
    for name in names:
        source = _read("tests", "js", name)
        assert 'from "node:test"' in source, f"{name} is not a node:test file"
        assert "assets/js/garden/" in source, f"{name} tests nothing from the modules"


def test_every_module_a_unit_test_imports_exists():
    for path in JS_TESTS.glob("*.mjs"):
        for name in re.findall(r"assets/js/garden/([a-z-]+\.js)", path.read_text(encoding="utf-8")):
            assert (MODULES / name).is_file(), f"{path.name} imports {name}, which does not exist"
