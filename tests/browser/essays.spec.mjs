// Essays (roadmap S15, docs/ESSAYS.md): the index at /essays/ and one page
// per essay, checked in a real browser at phone width.
//
// No essay is in the vault yet, so verify.sh runs this spec twice. First on
// a build that reads the fixture essay from tests/fixtures/essays/
// (AURELIA_ESSAYS_DIR), with AURELIA_ESSAYS_FIXTURE=1 so a build that quietly
// produced no essays fails here rather than skipping. Then on the real
// build, where the first group skips and the second holds the live site to
// "nothing a visitor sees changes": no Essays link, no empty index.
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test, expect, expectNoAxeViolations } from "./fixtures.mjs";
import { BASE_PATH } from "./site.mjs";

const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));
const FIXTURE_BUILT = existsSync(DIST + "essays/index.html");
if (process.env.AURELIA_ESSAYS_FIXTURE && !FIXTURE_BUILT) {
  throw new Error("AURELIA_ESSAYS_FIXTURE is set but dist/essays/index.html is missing: build with AURELIA_ESSAYS_DIR=tests/fixtures/essays first");
}

const ESSAY_PATH = "essays/why-loss-looms-larger/";
const PHONE = { width: 375, height: 812 };

async function expectNoHorizontalScroll(page) {
  const widths = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(widths.scroll, "the page must not scroll sideways at phone width").toBeLessThanOrEqual(widths.client);
}

test.describe("with the fixture essay built", () => {
  test.skip(!FIXTURE_BUILT, "dist/ was built without essays");
  test.use({ viewport: PHONE });

  test("the index lists the essay with its title, weekday date, disciplines, thesis and reading time, and the nav shows Essays", async ({ page }) => {
    await page.goto("essays/");
    const entry = page.locator('#essay-list [data-essay-id="E01"]');
    await expect(entry.getByRole("heading", { level: 2 })).toHaveText("Why loss looms larger");
    await expect(entry.locator("time")).toHaveText("Friday, 20 November 2026");
    await expect(entry.locator("time")).toHaveAttribute("datetime", "2026-11-20");
    await expect(entry.locator(".essay-disciplines li")).toHaveText(["cognitive psychology", "philosophy"]);
    await expect(entry.locator(".essay-thesis")).toContainText("Losses weigh more than equal gains");
    await expect(entry.locator(".essay-reading-time")).toHaveText(/^\d+-minute read$/);
    // The nav's phone menu carries the Essays item, marked current.
    await page.locator("#mobile-menu-btn").click();
    const navItem = page.locator('#mobile-menu a[href$="essays/"]');
    await expect(navItem).toBeVisible();
    await expect(navItem).toHaveText("ESSAYS");
    await expect(navItem).toHaveAttribute("aria-current", "page");
    await expectNoHorizontalScroll(page);
  });

  test("the essay page shows its byline, dates and body", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Why loss looms larger");
    await expect(page.locator(".essay-byline")).toHaveText("Travis R. McKinzie");
    const dates = page.locator(".essay-dates");
    await expect(dates).toContainText("Friday, 20 November 2026");
    await expect(dates).toContainText("Updated Sunday, 22 November 2026");
    await expect(dates.locator(".essay-reading-time")).toHaveText(/^\d+-minute read$/);
    const body = page.locator(".essay-body");
    await expect(body.getByRole("heading", { level: 2, name: "The shape of the asymmetry" })).toBeVisible();
    await expect(body.locator("blockquote")).toBeVisible();
    await expect(body.locator("ul li")).toHaveCount(3);
    await expectNoHorizontalScroll(page);
  });

  test("a Garden link in the essay opens the right Garden note", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const link = page.locator('.essay-body a[data-garden-note="note-active-recall"]');
    await expect(link).toHaveText("active recall");
    await expect(link).toHaveAttribute("href", `${BASE_PATH}garden.html#note-active-recall`);
    await link.click();
    await expect(page).toHaveURL(new RegExp(`${BASE_PATH}garden\\.html#note-active-recall$`));
    const reader = page.locator("#modal-panel");
    await expect(reader).toHaveClass(/is-open/);
    await expect(page.locator("#modal-title")).toHaveText("Active Recall");
  });

  test("a discipline label links to its Garden note", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const discipline = page.locator('.essay-disciplines a[href$="#note-cognitive-psychology"]');
    await expect(discipline).toHaveText("cognitive psychology");
    await discipline.click();
    await expect(page.locator("#modal-title")).toHaveText("Cognitive Psychology");
  });

  for (const [name, path] of [["index", "essays/"], ["essay page", ESSAY_PATH]]) {
    test(`the ${name} has no WCAG A/AA violations in either offered theme, at phone width and on a desktop`, async ({ page }) => {
      test.slow();
      for (const viewport of [PHONE, { width: 1440, height: 900 }]) {
        await page.setViewportSize(viewport);
        await page.goto(path);
        const themes = await page.evaluate(() => AVAILABLE_THEMES.map((t) => t.key));
        expect(themes.length).toBeGreaterThan(1);
        for (const theme of themes) {
          await page.evaluate((t) => localStorage.setItem("aurelia_theme", t), theme);
          await page.reload();
          await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
          await test.step(`${theme} at ${viewport.width}px`, () => expectNoAxeViolations(page));
          if (viewport.width === PHONE.width) await expectNoHorizontalScroll(page);
        }
      }
    });
  }

  test("every essay page carries a filled Content-Security-Policy and loads only the site's own files", async ({ page, guard }) => {
    for (const path of ["essays/", ESSAY_PATH]) {
      await page.goto(path);
      const policy = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content");
      expect(policy, path).toMatch(/script-src 'self' 'sha256-/);
      expect(policy, path).toMatch(/style-src 'self' 'sha256-/);
      expect(policy, path).not.toContain("@@csp@@");
      const stylesheet = await page.locator('link[href*="assets/css/main.css"]').getAttribute("href");
      expect(stylesheet, path).toMatch(/^\/.*main\.css\?v=[0-9a-f]{10}$/);
      await page.evaluate(() => document.fonts.ready);
    }
    expect(guard.foreign).toEqual([]);
  });
});

test.describe("without any essay published (the live site today)", () => {
  test.skip(FIXTURE_BUILT, "dist/ carries the fixture essay");

  test("no page shows an Essays link and /essays/ is the 404 page", async ({ page, guard }) => {
    for (const path of ["index.html", "garden.html", "about.html"]) {
      await page.goto(path);
      expect(await page.locator('a[href$="essays/"]').count(), path).toBe(0);
      expect(await page.getByText("ESSAYS", { exact: true }).count(), path).toBe(0);
    }
    guard.expectStatus(404, "/essays/");
    const response = await page.goto("essays/");
    expect(response.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  });
});
