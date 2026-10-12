// Runs once before the browser suite. The suite tests dist/ and never builds
// it (see playwright.config.mjs), so a missing or wrongly built dist/ stops
// here with the fix, rather than surfacing as forty confusing test failures.
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { BASE_PATH, SITE_REPOSITORY } from "./site.mjs";

const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));
const BUILD_HINT =
  "Build it first, the way verify.sh does:\n" +
  `  GITHUB_REPOSITORY=${SITE_REPOSITORY} .venv/bin/python build.py --no-sort\n` +
  "or run everything with: bash verify.sh";

export default async function globalSetup() {
  let html;
  try {
    html = await readFile(DIST + "404.html", "utf8");
  } catch {
    throw new Error(`dist/404.html not found, so dist/ has not been built.\n${BUILD_HINT}`);
  }
  // The 404 page is the one page with absolute links (docs/DECISIONS.md
  // item 29), so it records the root the build linked from. A dist/ built
  // for another root (an older build, or site.domain emptied without
  // BASE_PATH following it) would fail every deep-link test confusingly.
  const root = /const SITE_ROOT = "([^"]*)";/.exec(html)?.[1];
  if (root !== BASE_PATH) {
    throw new Error(
      `dist/404.html was built for site root ${JSON.stringify(root)}, not ${JSON.stringify(BASE_PATH)}.\n${BUILD_HINT}`,
    );
  }
}
