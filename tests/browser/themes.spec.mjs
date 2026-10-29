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

// Theme-matched images (docs/DECISIONS.md item 49): the Lobby hero and the
// round photo show the TIMBERLINE photo in the light theme and the AI avatar
// in CYBER_PRIME, from profile.json, with only theme-vars.css choosing.
const PHOTO = "assets/images/hero-portrait-timberline.webp";
const AVATAR = "assets/images/hero-portrait-cyber-prime.webp";
const shownHero = (page) => page.locator(".hero-portrait img:visible");

test("the Lobby portrait switches with the theme in the same box", async ({ page }) => {
  await page.goto("index.html");
  await expect(shownHero(page)).toHaveCount(1);
  await expect(shownHero(page)).toHaveAttribute("src", PHOTO);
  await expect(shownHero(page)).toHaveAttribute("alt", "Travis R. McKinzie beside a river in autumn");
  const before = await page.locator(".hero-portrait").boundingBox();

  await page.locator("#theme-menu-btn").click();
  await page.locator('#theme-menu button[data-theme="cyber-prime"]').click();
  await expect(shownHero(page)).toHaveCount(1);
  await expect(shownHero(page)).toHaveAttribute("src", AVATAR);
  await expect(shownHero(page)).toHaveAttribute("alt", "A stylized AI avatar of Travis R. McKinzie");
  await expect.poll(() => shownHero(page).evaluate((img) => img.naturalWidth)).toBe(840);
  expect(await page.locator(".hero-portrait").boundingBox()).toEqual(before);

  await page.locator("#theme-menu-btn").click();
  await page.locator('#theme-menu button[data-theme="timberline"]').click();
  await expect(shownHero(page)).toHaveAttribute("src", PHOTO);
});

test("a saved dark theme paints the avatar from the first frame, never the photo", async ({ page }) => {
  // Every frame from the first one the browser renders (rAF waits on the
  // render-blocking stylesheets) records which hero image is displayed.
  await page.addInitScript(() => {
    localStorage.setItem("aurelia_theme", "cyber-prime");
    window.__heroFrames = [];
    const sample = () => {
      const shown = [...document.querySelectorAll(".hero-portrait img")]
        .filter((img) => getComputedStyle(img).display !== "none")
        .map((img) => img.getAttribute("src"));
      if (shown.length) window.__heroFrames.push(shown.join(" "));
      if (window.__heroFrames.length < 20) requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  });
  await page.goto("index.html");
  await expect.poll(() => page.evaluate(() => window.__heroFrames.length)).toBeGreaterThanOrEqual(5);
  const frames = await page.evaluate(() => window.__heroFrames);
  expect(new Set(frames)).toEqual(new Set([AVATAR]));
});

test("a theme with no image of its own shows the photo", async ({ page }) => {
  // THE_PATRIOT has no entry in profile.json's themes, as no theme but
  // CYBER_PRIME does. The menu no longer offers it, so set it directly.
  await page.goto("index.html");
  await page.evaluate(() => document.documentElement.setAttribute("data-theme", "the-patriot"));
  await expect(shownHero(page)).toHaveCount(1);
  await expect(shownHero(page)).toHaveAttribute("src", PHOTO);
});

test("opening the theme menu starts loading the hidden portrait", async ({ page }) => {
  // A visitor who never opens the menu never downloads the avatar; one who
  // does has it ready, or nearly, by the time the switch shows it.
  await page.goto("index.html");
  const avatar = page.locator(`.hero-portrait img[src="${AVATAR}"]`);
  await expect(avatar).toHaveAttribute("loading", "lazy");
  expect(await avatar.evaluate((img) => img.naturalWidth)).toBe(0);
  await page.locator("#theme-menu-btn").click();
  await expect(avatar).toHaveAttribute("loading", "eager");
  await expect.poll(() => avatar.evaluate((img) => img.naturalWidth)).toBe(840);
  await expect(avatar).toBeHidden();
});

test("the About photo switches with the theme", async ({ page }) => {
  await page.goto("about.html");
  const shown = page.locator("header img:visible");
  await expect(shown).toHaveCount(1);
  await expect(shown).toHaveAttribute("src", "assets/images/headshot.webp");
  await page.locator("#theme-menu-btn").click();
  await page.locator('#theme-menu button[data-theme="cyber-prime"]').click();
  await expect(shown).toHaveCount(1);
  await expect(shown).toHaveAttribute("src", "assets/images/headshot-cyber-prime.webp");
  await expect(shown).toHaveAttribute("alt", "A stylized AI avatar of Travis R. McKinzie");
});

test("printing About under the dark theme prints the photo, not the avatar", async ({ page }) => {
  // Print forces white paper whatever the theme (main.css @media print).
  await page.addInitScript(() => localStorage.setItem("aurelia_theme", "cyber-prime"));
  await page.goto("about.html");
  await expect(page.locator("header img:visible")).toHaveAttribute("src", "assets/images/headshot-cyber-prime.webp");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator("header img:visible")).toHaveCount(1);
  await expect(page.locator("header img:visible")).toHaveAttribute("src", "assets/images/headshot.webp");
});
