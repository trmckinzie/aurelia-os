"""Guards for roadmap S08: the browser suite and its accessibility gate.

The suite itself is JavaScript (tests/browser/, run by Playwright). What this
module pins is the wiring around it, which can disappear without any browser
test noticing: verify.sh running it after the build, the CI jobs installing
Chromium and keeping failure artifacts, the dev-only dependencies, and the
accessibility exceptions each pointing at an open backlog entry.
"""
import json
import os
import re
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _steps(job):
    workflow = yaml.safe_load(_read(".github", "workflows", "deploy.yml"))
    return workflow["jobs"][job]["steps"]


# --- verify.sh ------------------------------------------------------------

def test_verify_sh_runs_the_browser_suite_after_the_build():
    script = _read("verify.sh")
    build = script.index('build.py "${BUILD_FLAGS[@]}"')
    install = script.index("playwright install chromium")
    run = script.index("playwright test")
    assert build < install < run, "the browser suite must run after the build it tests"
    assert script.index("verify.sh: all checks passed") > run


def test_verify_sh_builds_for_the_project_site_prefix():
    # The suite serves dist/ under /aurelia-os/; the 404 page only links
    # there when GITHUB_REPOSITORY names the repository (pipeline._site_root).
    script = _read("verify.sh")
    line = next(ln for ln in script.splitlines() if 'build.py "${BUILD_FLAGS[@]}"' in ln)
    assert 'GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-trmckinzie/aurelia-os}"' in line


# --- CI -------------------------------------------------------------------

def _step_index(steps, needle, key="run"):
    for i, step in enumerate(steps):
        if needle in str(step.get(key, "")):
            return i
    raise AssertionError(f"no step whose {key} contains {needle!r}")


def test_both_check_jobs_install_chromium_then_run_verify_and_keep_failures():
    for job in ("check", "check-macos"):
        steps = _steps(job)
        install = _step_index(steps, "playwright install --with-deps chromium")
        verify = _step_index(steps, "bash verify.sh")
        upload = _step_index(steps, "actions/upload-artifact@", key="uses")
        assert install < verify < upload, job
        artifact = steps[upload]
        assert artifact.get("if") == "failure()", job
        assert "test-results/" in artifact["with"]["path"], job
        assert "playwright-report/" in artifact["with"]["path"], job


def test_only_the_ubuntu_check_gates_the_deploy():
    workflow = yaml.safe_load(_read(".github", "workflows", "deploy.yml"))
    needs = workflow["jobs"]["build"]["needs"]
    needs = [needs] if isinstance(needs, str) else needs
    assert needs == ["check"], "check-macos stays non-blocking (docs/DECISIONS.md item 22)"


# --- dependencies and output ------------------------------------------------

def test_playwright_and_axe_are_exact_pinned_dev_dependencies():
    package = json.loads(_read("package.json"))
    dev = package.get("devDependencies", {})
    for name in ("@playwright/test", "@axe-core/playwright"):
        assert re.fullmatch(r"\d+\.\d+\.\d+", dev.get(name, "")), f"{name} must be pinned to an exact version"
        assert name not in package.get("dependencies", {}), f"{name} is a dev tool"
    lock = json.loads(_read("package-lock.json"))
    for name in ("@playwright/test", "@axe-core/playwright"):
        assert lock["packages"][f"node_modules/{name}"].get("dev") is True


def test_nothing_from_the_test_tools_is_copied_into_the_site():
    vendor = _read("engine", "vendor.py").lower()
    assert "playwright" not in vendor and "axe" not in vendor


def test_browser_suite_output_is_ignored():
    for path in ("test-results/x.png", "playwright-report/index.html"):
        result = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT)
        assert result.returncode == 0, f"{path} must be gitignored"


# --- the accessibility gate -------------------------------------------------

def test_axe_runs_wcag_a_and_aa():
    fixtures = _read("tests", "browser", "fixtures.mjs")
    tags = re.search(r"WCAG_TAGS = \[([^\]]*)\]", fixtures).group(1)
    for tag in ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa"):
        assert f'"{tag}"' in tags


def test_every_axe_exception_names_an_open_backlog_entry():
    fixtures = _read("tests", "browser", "fixtures.mjs")
    block = fixtures[fixtures.index("AXE_EXCEPTIONS = ["):fixtures.index("];", fixtures.index("AXE_EXCEPTIONS = ["))]
    backlog = {b["id"]: b for b in yaml.safe_load(_read("docs", "roadmap.yaml"))["backlog"]}
    entries = re.findall(r'rule: "([^"]+)",\s*selector: \'([^\']+)\',\s*backlog: "(B\d+)"', block)
    assert len(entries) == block.count("rule:"), "every exception needs a rule, one selector and a backlog id"
    for rule, selector, backlog_id in entries:
        assert backlog_id in backlog, f"{rule} on {selector}: {backlog_id} is not in docs/roadmap.yaml"
        assert backlog[backlog_id]["status"] == "open", f"{backlog_id} is closed; remove the {rule} exception"
