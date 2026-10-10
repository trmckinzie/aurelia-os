// The theme menu (roadmap S11): one light and one dark choice on every page,
// a saved choice that persists, and a saved choice the menu no longer offers
// (one of the experimental themes) giving way to the default. The `guard`
// fixture (fixtures.mjs) fails any test here on a console error.
import { test, expect } from "./fixtures.mjs";
import { PAGES } from "./helpers.mjs";

const OFFERED = [
  { key: "timberline", label: "Timberline", mode: "Light theme" },
  { key: "cyber-prime", label: "Cyber Prime", mode: "Dark theme" },
];

for (const { name, path, marker } of PAGES) {
  test(`${name} theme menu offers exactly a light and a dark theme`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator(marker)).toBeVisible();
    await page.locator("#theme-menu-btn").click();
    const buttons = page.locator('#theme-menu button[data-action="setTheme"]');
    await expect(buttons).toHaveCount(OFFERED.length);
    for (const [i, t] of OFFERED.entries()) {
      await expect(buttons.nth(i)).toHaveAttribute("data-theme", t.key);
      await expect(buttons.nth(i)).toContainText(t.label);
      await expect(buttons.nth(i)).toContainText(t.mode);
    }
    // The mobile menu is built from the same list.
    const mobile = page.locator('#mobile-theme-menu button[data-action="setTheme"]');
    await expect(mobile).toHaveCount(OFFERED.length);
    for (const [i, t] of OFFERED.entries()) {
      await expect(mobile.nth(i)).toHaveAttribute("data-theme", t.key);
      await expect(mobile.nth(i)).toContainText(t.mode);
    }
  });
}

test("choosing the dark theme applies it and survives a reload", async ({ page }) => {
  await page.goto("index.html");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "timberline");
  await page.locator("#theme-menu-btn").click();
  await page.locator('#theme-menu button[data-theme="cyber-prime"]').click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "cyber-prime");
  expect(await page.evaluate(() => localStorage.getItem("aurelia_theme"))).toBe("cyber-prime");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "cyber-prime");
  await page.locator("#theme-menu-btn").click();
  await expect(page.locator('#theme-menu button[data-theme="cyber-prime"]')).toContainText("✓");
});

for (const stale of ["the-patriot", "the-stoa", "grizz", "no-such-theme"]) {
  test(`a saved theme the menu no longer offers (${stale}) falls back to the default`, async ({ page }) => {
    await page.goto("index.html");
    await page.evaluate((t) => localStorage.setItem("aurelia_theme", t), stale);
    await page.reload();
    await expect(page.locator("#lobby-total-notes")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "timberline");
    // The default's variables are what the page is painted with, not an
    // unlisted theme's block and not nothing.
    const bg = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--aurelia-bg-main").trim());
    expect(bg).toBe("#f5f2eb");
    await page.locator("#theme-menu-btn").click();
    await expect(page.locator('#theme-menu button[data-theme="timberline"]')).toContainText("✓");
  });
}
