// The path the site is served under, shared by playwright.config.mjs (where
// the test server mounts dist/) and the specs. It follows from user_config.json
// (engine/pipeline.py's _site_root()): "/" while site.domain is set, which it
// is since roadmap S14, and "/aurelia-os/" for the github.io project site
// without one. tests/test_browser_suite.py holds the two in step.
export const BASE_PATH = "/";
export const SITE_REPOSITORY = "trmckinzie/aurelia-os";
