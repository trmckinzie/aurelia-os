// Every page loads with its stylesheet, scripts and fonts, and logs no error.
// The `guard` fixture (fixtures.mjs) fails any test here on a console error,
// a page error, a failed or 4xx request, or a request to another origin.
import { test, expect } from "./fixtures.mjs";
import { BASE_PATH } from "./site.mjs";
import { PAGES, PALETTE_KEY, findStudyableNoteId, gotoGarden, openNoteByCard } from "./helpers.mjs";

// What a page needs from its own assets/ to work, checked in the page itself:
// the compiled stylesheet applied (a theme variable resolves and the nav is
// fixed), the vendored scripts ran, and at least one web font loaded with
// none failing.
async function expectAssetsLoaded(page) {
  const state = await page.evaluate(async () => {
    await document.fonts.ready;
    const fonts = [...document.fonts];
    return {
      themeVar: getComputedStyle(document.documentElement).getPropertyValue("--aurelia-bg-main").trim(),
      navPosition: getComputedStyle(document.querySelector("nav.nav-shell")).position,
      marked: typeof window.marked?.parse,
      motion: typeof window.Motion?.animate,
      utils: typeof window.escapeHtml,
      fontsLoaded: fonts.filter((f) => f.status === "loaded").length,
      fontsFailed: fonts.filter((f) => f.status === "error").map((f) => `${f.family} ${f.weight}`),
    };
  });
  expect(state.themeVar, "theme-vars.css applied").not.toBe("");
  expect(state.navPosition, "main.css applied").toBe("fixed");
  expect(state.marked, "marked.js loaded").toBe("function");
  expect(state.motion, "Motion loaded").toBe("function");
  expect(state.utils, "utils.js loaded").toBe("function");
  expect(state.fontsLoaded, "at least one web font loaded").toBeGreaterThan(0);
  expect(state.fontsFailed, "fonts that failed to load").toEqual([]);
}

for (const { name, path, marker } of PAGES) {
  test(`${name} loads its styles, scripts and fonts without errors`, async ({ page }) => {
    const css = [];
    page.on("response", (res) => {
      if (/\/assets\/(css|fonts)\/[^?]+\.css/.test(res.url())) css.push(`${res.status()} ${new URL(res.url()).pathname}`);
    });
    const response = await page.goto(path);
    expect(response.status()).toBe(200);
    await expect(page.locator(marker)).toBeVisible();
    await expectAssetsLoaded(page);
    expect(css.sort()).toEqual([
      `200 ${BASE_PATH}assets/css/main.css`,
      `200 ${BASE_PATH}assets/css/theme-vars.css`,
      `200 ${BASE_PATH}assets/fonts/fonts.css`,
    ]);
  });
}

test("the Garden's own scripts load", async ({ page }) => {
  await page.goto("garden.html");
  await expect(page.locator("#cardGrid .searchable-item").first()).toBeVisible();
  const types = await page.evaluate(() => ({
    review: typeof window.Review?.rate,
    flashcards: typeof window.upgradeFlashcardDecks,
  }));
  expect(types).toEqual({ review: "function", flashcards: "function" });
});

test("a missing page two folders deep serves the 404 page, styled, with working links", async ({ page, guard }) => {
  guard.expectStatus(404, "/a/b/");
  const response = await page.goto("a/b/");
  expect(response.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  await expectAssetsLoaded(page);

  // Absolute links (docs/DECISIONS.md item 29): from /aurelia-os/a/b/ a
  // relative "index.html" would point at /aurelia-os/a/b/index.html.
  await page.getByRole("link", { name: "Back to home" }).click();
  await expect(page).toHaveURL(`${BASE_PATH}index.html`);
  await expect(page.locator("#lobby-total-notes")).toBeVisible();
});

test("the search palette on a deep 404 page links to real pages", async ({ page, guard }) => {
  guard.expectStatus(404, "/a/b/");
  await page.goto("a/b/");
  await page.keyboard.press(PALETTE_KEY);
  await expect(page.locator("#cmd-dialog")).toBeVisible();
  await page.locator("#cmd-input").fill("garden");
  const first = page.locator("#cmd-results [role=option]").first();
  await expect(first).toHaveAttribute("href", new RegExp(`^${BASE_PATH}`));
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`${BASE_PATH}(garden|index)\\.html`));
});

test("the site root without its trailing slash redirects, like GitHub Pages", async ({ page }) => {
  const response = await page.goto(BASE_PATH.slice(0, -1));
  expect(response.status()).toBe(200);
  await expect(page).toHaveURL(BASE_PATH);
  await expect(page.locator("#lobby-total-notes")).toBeVisible();
});


// Backlog B02: a Content-Security-Policy without 'unsafe-inline' refuses
// inline handlers, so none may exist -- in the served markup or in anything
// a script builds later (theme menu, backlinks, graph rows). The Python
// guard (tests/test_no_inline_handlers.py) reads the templates; this reads
// the live DOM, reader open included.
const INLINE_HANDLERS = "[onclick],[onchange],[oninput],[onkeydown],[onkeyup],[onmouseenter],[onmouseover],[onsubmit],[onload],[onerror]";

test("every page carries a Content-Security-Policy with hashes and nothing unsafe", async ({ page }) => {
  for (const { name, path } of PAGES) {
    await page.goto(path);
    const policy = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content");
    expect(policy, name).toContain("default-src 'self'");
    expect(policy, name).toMatch(/script-src 'self' 'sha256-/);
    expect(policy, name).toMatch(/style-src 'self'/);
    expect(policy, name).not.toContain("unsafe");
    expect(policy, name).toContain("object-src 'none'");
  }
  // The guard fixture fails this test on any console error, and a policy
  // violation is reported as one, so reaching here with the theme menu and a
  // note open means every inline block was hashed and nothing was refused.
  await gotoGarden(page);
  await page.locator("#theme-menu-btn").click();
  await openNoteByCard(page, await findStudyableNoteId(page));
});

test("no page carries an inline event handler, in the markup or in what its scripts build", async ({ page }) => {
  for (const { name, path } of PAGES) {
    await page.goto(path);
    expect(await page.locator(INLINE_HANDLERS).count(), name).toBe(0);
  }
  await gotoGarden(page);
  await page.locator("#theme-menu-btn").click();
  await expect(page.locator('#theme-menu button[data-action="setTheme"]').first()).toBeVisible();
  await openNoteByCard(page, await findStudyableNoteId(page));
  await expect(page.locator("#modal-panel [data-note]").first()).toBeVisible();
  expect(await page.locator(INLINE_HANDLERS).count(), "Garden with the theme menu and a note open").toBe(0);
});
