// No page asks another server for anything (docs/DECISIONS.md item 26: the
// footer says "No analytics or tracking.", and a font or script fetched from
// a CDN is a third party seeing the visit). The `guard` fixture already fails
// any test that makes such a request; this test walks every page and every
// state that loads something on demand, so the promise is checked in one
// place even if other tests change, and it also checks the recorder works.
import { test, expect } from "./fixtures.mjs";
import { PAGES, PALETTE_KEY, findStudyableNoteId, gotoGarden, openNoteByCard, setStudyMode } from "./helpers.mjs";

test("every page, dialog and reader state loads files only from the site itself", async ({ page, guard }) => {
  const seen = new Set();
  page.on("request", (req) => seen.add(new URL(req.url()).origin));

  for (const { path, marker } of PAGES) {
    await page.goto(path);
    await expect(page.locator(marker)).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await page.keyboard.press(PALETTE_KEY);
    await page.locator("#cmd-input").fill("a");
    await expect(page.locator("#cmd-results [role=option]").first()).toBeVisible();
    await page.keyboard.press("Escape");
  }

  guard.expectStatus(404, "/no/such/page/");
  await page.goto("no/such/page/");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);

  await page.goto("index.html");
  await page.locator("#readout-more").click();
  await expect(page.locator("#toolkit-sheet")).toBeVisible();
  await page.keyboard.press("Escape");

  await gotoGarden(page);
  await page.locator("#btn-shortcuts").click();
  await page.keyboard.press("Escape");
  const id = await findStudyableNoteId(page);
  await openNoteByCard(page, id);
  await page.keyboard.press("Escape");
  await setStudyMode(page, true);
  await openNoteByCard(page, id);
  await page.getByRole("button", { name: "Reveal" }).click();
  await page.getByRole("button", { name: /Good/ }).click();
  await expect(page.locator(".rate-confirm")).toBeVisible();
  for (const view of ["Tree", "Graph"]) {
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: new RegExp(view === "Tree" ? "List view" : "Knowledge graph") }).click();
    await expect(page.locator("#view-mode-label")).toHaveText(view);
  }

  expect(guard.foreign, "requests to another origin").toEqual([]);
  // The recorder saw the site's own requests, so an empty list above means
  // nothing foreign was asked for, not that nothing was recorded.
  expect([...seen].filter((o) => o.startsWith("http"))).toEqual([guard.origin]);
});
