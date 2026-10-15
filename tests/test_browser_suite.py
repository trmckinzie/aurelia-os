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
    # Without site.domain the 404 page links under /aurelia-os/ only when
    # GITHUB_REPOSITORY names the repository (pipeline._site_root), so the
    # local build sets it the way CI does, whichever root is in force. It is
    # exported once, before both builds (the fixture one and the real one).
    script = _read("verify.sh")
    export = script.index('export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-trmckinzie/aurelia-os}"')
    assert export < script.index('build.py "${BUILD_FLAGS[@]}"')


def test_verify_sh_checks_the_essay_pages_on_a_fixture_build_then_builds_the_real_site():
    # Roadmap S15: no essay is in the vault, so the essay spec runs against
    # a build of tests/fixtures/essays/ first, with the flag that makes a
    # silent skip a failure, and the real build comes last so dist/ is the
    # site itself when the full suite runs.
    script = _read("verify.sh")
    builds = [m.start() for m in re.finditer(r'build\.py "\$\{BUILD_FLAGS\[@\]\}"', script)]
    assert len(builds) == 2
    fixture_build, real_build = builds
    line = script[script.rfind("\n", 0, fixture_build):fixture_build]
    assert 'AURELIA_ESSAYS_DIR="$ROOT/tests/fixtures/essays"' in line
    essay_spec = script.index("AURELIA_ESSAYS_FIXTURE=1 npx --no-install playwright test tests/browser/essays.spec.mjs")
    full_suite = script.index("npx --no-install playwright test\n")
    assert fixture_build < essay_spec < real_build < full_suite
    assert "AURELIA_ESSAYS_DIR" not in script[real_build - 200:real_build]


def _site_mjs_constant(name):
    match = re.search(rf'export const {name} = "([^"]*)";', _read("tests", "browser", "site.mjs"))
    assert match, f"tests/browser/site.mjs no longer exports {name}"
    return match.group(1)


def _site_domain():
    return json.loads(_read("user_config.json"))["site"].get("domain", "")


def test_browser_suite_serves_dist_from_the_root_the_build_links_from():
    # Roadmap S14: setting site.domain moves the site from /aurelia-os/ to
    # "/". BASE_PATH has to move with it, or the suite tests a layout
    # nothing serves (global-setup.mjs would stop it, but only locally).
    from engine.pipeline import _site_root
    config = json.loads(_read("user_config.json"))
    repo = _site_mjs_constant("SITE_REPOSITORY")
    assert _site_mjs_constant("BASE_PATH") == _site_root(config, {"GITHUB_REPOSITORY": repo})


def test_weekly_check_reads_the_canonical_address():
    # GitHub answers the github.io address with a redirect once a custom
    # domain is set, and the live check does not follow redirects, so the
    # weekly check has to name the address the site is really served from.
    # The deploy and redeploy checks read deploy-pages' page_url instead,
    # which follows the domain on its own.
    workflow = yaml.safe_load(_read(".github", "workflows", "weekly-check.yml"))
    step = next(s for s in workflow["jobs"]["live-check"]["steps"]
                if s.get("uses") == "./.github/actions/live-check")
    domain = _site_domain()
    expected = f"https://{domain}/" if domain else "https://trmckinzie.github.io/aurelia-os/"
    assert step["with"]["site-url"] == expected
    for name in ("deploy.yml", "redeploy.yml"):
        workflow = yaml.safe_load(_read(".github", "workflows", name))
        assert workflow["jobs"]["live-check"]["steps"][-1]["with"]["site-url"] == (
            "${{ needs.deploy.outputs.page_url }}"
        ), name


def test_a_rollback_cannot_redeploy_a_tag_from_before_the_domain():
    # Roadmap S14: a tag built before site.domain was set has no dist/CNAME
    # and a 404 page linking under /aurelia-os/. redeploy.yml must refuse it
    # after building and before anything is uploaded (docs/ROLLBACK.md).
    assert _site_domain(), "the guard only makes sense while site.domain is set"
    steps = yaml.safe_load(_read(".github", "workflows", "redeploy.yml"))["jobs"]["build"]["steps"]
    names = [s.get("name", "") for s in steps]
    build = names.index("Run Build Script")
    guard = names.index("Refuse a tag from before the custom domain")
    upload = names.index("Upload Artifact")
    assert build < guard < upload
    assert "[ ! -s dist/CNAME ]" in steps[guard]["run"]
    assert "exit 1" in steps[guard]["run"]


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
    assert needs == ["check"], "check-macos stays non-blocking (docs/DECISIONS.md item 25)"


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
