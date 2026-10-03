// axe-core at WCAG 2.0/2.1 A and AA on every page and on every dialog and
// reader state a visitor can reach, in Read and in Study mode. Any violation
// fails the suite, and so the check job, and so the merge (roadmap S08).
//
// Every rule runs in the default theme (TIMBERLINE, what a first visit
// renders). The optional themes get axe's colour-contrast rule on each page
// at the end of this file; tests/test_theming.py sweeps their token pairs.
//
// A limit worth knowing: axe reports contrast it cannot compute as
// "incomplete", not as a violation, and only violations fail. Text over a
// gradient or beside a pseudo-element (every Garden card, the nav) is in that
// group, so for it the Python sweep is the check that counts.
import { test, expect, expectNoAxeViolations } from "./fixtures.mjs";
import { PAGES, PALETTE_KEY, findStudyableNoteId, gotoGarden, openNoteByCard, setStudyMode } from "./helpers.mjs";

for (const { name, path, marker } of PAGES) {
  test(`${name} page has no WCAG A/AA violations`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator(marker)).toBeVisible();
    await expectNoAxeViolations(page);
  });
}

test("the 404 page, two folders deep, has no WCAG A/AA violations", async ({ page, guard }) => {
  guard.expectStatus(404, "/missing/page/");
  await page.goto("missing/page/");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  await expectNoAxeViolations(page);
});

test("the search palette has no WCAG A/AA violations, empty and with results", async ({ page }) => {
  await page.goto("about.html");
  await page.keyboard.press(PALETTE_KEY);
  const dialog = page.locator("#cmd-dialog");
  await expect(dialog).toBeVisible();
  await expectNoAxeViolations(page, { include: "#cmd-dialog" });
  await page.locator("#cmd-input").fill("a");
  await expect(page.locator("#cmd-results [role=option]").first()).toBeVisible();
  await expectNoAxeViolations(page, { include: "#cmd-dialog" });
});

test("the Lobby's Toolkit sheet has no WCAG A/AA violations", async ({ page }) => {
  await page.goto("index.html");
  await page.locator("#readout-more").click();
  await expect(page.locator("#toolkit-sheet")).toBeVisible();
  await expectNoAxeViolations(page, { include: "#toolkit-sheet" });
});

test("the Garden's shortcut sheet has no WCAG A/AA violations", async ({ page }) => {
  await gotoGarden(page);
  await page.locator("#btn-shortcuts").click();
  await expect(page.locator("#shortcut-sheet")).toBeVisible();
  await expectNoAxeViolations(page, { include: "#shortcut-sheet" });
});

test("the note reader has no WCAG A/AA violations in Read mode", async ({ page }) => {
  await gotoGarden(page);
  await setStudyMode(page, false);
  await openNoteByCard(page, await findStudyableNoteId(page));
  await expectNoAxeViolations(page, { include: "#modal-panel" });
});

test("the note reader has no WCAG A/AA violations in Study mode: covered, revealed and rated", async ({ page }) => {
  await gotoGarden(page);
  await setStudyMode(page, true);
  await openNoteByCard(page, await findStudyableNoteId(page));
  const reader = page.locator("#modal-panel");

  await expect(reader.locator(".recall-cover")).toBeVisible();
  await expectNoAxeViolations(page, { include: "#modal-panel" });

  await reader.getByRole("button", { name: "Reveal" }).click();
  await expect(reader.getByRole("group", { name: "How well did you remember it?" })).toBeVisible();
  await expectNoAxeViolations(page, { include: "#modal-panel" });

  await reader.getByRole("button", { name: /Good/ }).click();
  await expect(reader.locator(".rate-confirm")).toBeVisible();
  await expectNoAxeViolations(page, { include: "#modal-panel" });
});

test("the Garden page has no WCAG A/AA violations in Study mode", async ({ page }) => {
  await gotoGarden(page);
  await setStudyMode(page, true);
  await expectNoAxeViolations(page);
});

// The theme list is read from the page (AVAILABLE_THEMES, generated from
// THEME_CONFIG), so a new theme is covered without editing this file.
for (const { name, path, marker } of PAGES) {
  test(`${name} page meets WCAG AA colour contrast in every optional theme`, async ({ page }) => {
    // Several reload + axe-scan round trips on one page (the Garden's card
    // grid makes this the heaviest test in the suite); the default 30s
    // timeout is tight enough that a slower CI runner can exceed it even
    // though nothing is actually wrong (seen in practice: 24.6s on the
    // developer's Mac, 34.9s on a GitHub-hosted runner). test.slow() triples
    // it rather than loosening the budget for the whole suite.
    test.slow();
    await page.goto(path);
    const themes = await page.evaluate(() => AVAILABLE_THEMES.map((t) => t.key));
    const fallback = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(themes.length).toBeGreaterThan(1);
    for (const theme of themes.filter((t) => t !== fallback)) {
      await page.evaluate((t) => localStorage.setItem("aurelia_theme", t), theme);
      await page.reload();
      await expect(page.locator(marker)).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      await test.step(theme, () => expectNoAxeViolations(page, { rules: ["color-contrast"] }));
    }
  });
}
