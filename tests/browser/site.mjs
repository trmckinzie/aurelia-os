// The path GitHub Pages serves this project site under, shared by
// playwright.config.mjs (where the test server mounts dist/) and the specs.
// It follows from the repository name (engine/pipeline.py's _site_root()).
// If the site moves to a custom domain, it is served from "/" and this, the
// build step in verify.sh and global-setup.mjs change together.
export const BASE_PATH = "/aurelia-os/";
export const SITE_REPOSITORY = "trmckinzie/aurelia-os";
