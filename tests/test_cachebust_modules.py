"""Cache busting for the imports inside a folder of ES modules (roadmap S13).

The Garden's script is modules under assets/js/garden/. A template versions
the entry module's URL with asset_url(); nothing versions what that module
imports unless engine/cachebust.stamp_module_imports() does, and GitHub
Pages lets a browser reuse a script for ten minutes. These tests hold the
three things that have to be true: every import in the folder carries the
same version, that version and the entry module's own hash both change when
any file in the folder does, and one module is never imported under two
spellings.
"""
import re

import pytest

from engine.buildlog import get_warnings, reset_warnings
from engine.cachebust import stamp_asset_versions, stamp_module_imports

PAGE = '<script type="module" src="assets/js/garden/main.js?v=@@asset:assets/js/garden/main.js@@"></script>'


@pytest.fixture(autouse=True)
def _clean_warnings():
    reset_warnings()
    yield
    reset_warnings()


def _site(tmp_path, **overrides):
    """A dist/ with a three-module folder (a cycle between two of them, as
    the real modules have) and one classic script beside it."""
    folder = tmp_path / "assets" / "js" / "garden"
    folder.mkdir(parents=True)
    files = {
        "main.js": "import { a } from './a.js';\nimport {\n    b,\n} from './b.js';\na(); b();\n",
        "a.js": "import { b } from './b.js';\nexport function a() { return b; }\n",
        "b.js": 'import { a } from "./a.js";\nexport function b() { return a; }\n',
    }
    files.update(overrides)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    (tmp_path / "assets" / "js" / "utils.js").write_text("// not a module: import './nothing.js' in a comment\n", encoding="utf-8")
    (tmp_path / "garden.html").write_text(PAGE, encoding="utf-8")
    return folder


def _versions(folder):
    found = set()
    for path in folder.glob("*.js"):
        found.update(re.findall(r"\.js\?v=([0-9a-f]+)", path.read_text(encoding="utf-8")))
    return found


def test_every_import_in_the_folder_gets_one_version(tmp_path):
    folder = _site(tmp_path)
    versions = stamp_module_imports(tmp_path)
    assert list(versions) == ["assets/js/garden"]
    assert _versions(folder) == {versions["assets/js/garden"]}
    main = (folder / "main.js").read_text(encoding="utf-8")
    v = versions["assets/js/garden"]
    assert f"import {{ a }} from './a.js?v={v}';" in main
    # A wrapped import list, and a double-quoted specifier, are stamped too.
    assert f"}} from './b.js?v={v}';" in main
    assert f'from "./a.js?v={v}";' in (folder / "b.js").read_text(encoding="utf-8")
    assert get_warnings() == []


def test_no_unversioned_import_is_left(tmp_path):
    folder = _site(tmp_path)
    stamp_module_imports(tmp_path)
    for path in folder.glob("*.js"):
        assert not re.search(r"""\.js['"]""", path.read_text(encoding="utf-8")), path.name


def test_classic_scripts_beside_the_folder_are_left_alone(tmp_path):
    _site(tmp_path)
    before = (tmp_path / "assets" / "js" / "utils.js").read_bytes()
    stamp_module_imports(tmp_path)
    assert (tmp_path / "assets" / "js" / "utils.js").read_bytes() == before


def test_stamping_twice_changes_nothing(tmp_path):
    folder = _site(tmp_path)
    stamp_module_imports(tmp_path)
    once = {p.name: p.read_bytes() for p in folder.glob("*.js")}
    stamp_module_imports(tmp_path)
    assert {p.name: p.read_bytes() for p in folder.glob("*.js")} == once


def test_a_change_to_any_module_changes_the_entry_url(tmp_path):
    """The page's ?v= is the entry module's hash. A module the entry only
    imports must still change it, or a visitor inside the cache window keeps
    the old copy of that module behind an unchanged URL."""
    _site(tmp_path / "one")
    _site(tmp_path / "two", **{"b.js": 'import { a } from "./a.js";\nexport function b() { return 2; }\n'})
    first = stamp_asset_versions(tmp_path / "one")["assets/js/garden/main.js"]
    second = stamp_asset_versions(tmp_path / "two")["assets/js/garden/main.js"]
    assert first != second
    page = (tmp_path / "two" / "garden.html").read_text(encoding="utf-8")
    assert f"assets/js/garden/main.js?v={second}" in page


def test_the_same_modules_always_get_the_same_version(tmp_path):
    _site(tmp_path / "one")
    _site(tmp_path / "two")
    assert stamp_module_imports(tmp_path / "one") == stamp_module_imports(tmp_path / "two")


def test_an_import_that_leaves_the_folder_warns_and_is_not_stamped(tmp_path):
    folder = _site(tmp_path, **{"a.js": "import '../utils.js';\nimport { b } from './b.js';\nexport function a() { return b; }\n"})
    stamp_module_imports(tmp_path)
    assert "import '../utils.js';" in (folder / "a.js").read_text(encoding="utf-8")
    warnings = get_warnings()
    assert len(warnings) == 1 and "outside assets/js/garden/" in warnings[0]


def test_an_import_of_a_missing_module_warns(tmp_path):
    _site(tmp_path, **{"a.js": "import { c } from './c.js';\nexport function a() { return c; }\n"})
    stamp_module_imports(tmp_path)
    warnings = get_warnings()
    assert len(warnings) == 1 and "./c.js, which does not exist" in warnings[0]


def test_a_site_with_no_scripts_folder_is_fine(tmp_path):
    assert stamp_module_imports(tmp_path) == {}
