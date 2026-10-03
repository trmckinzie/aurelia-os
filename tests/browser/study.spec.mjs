// The reader and the study layer, end to end: open a note, switch to Study
// mode, reveal the covered answer, rate it, and watch the review log and the
// due queue respond (docs/ARCHITECTURE.md, "Study layer"). Progress lives in
// localStorage only, and every test starts with an empty browser profile.
import { test, expect } from "./fixtures.mjs";
import { findStudyableNoteId, findStudyableNoteIds, gotoGarden, openNoteByCard, setStudyMode } from "./helpers.mjs";

const LOG_KEY = "aurelia_review_log";
const DAY_MS = 24 * 60 * 60 * 1000;

const readLog = (page) => page.evaluate((key) => JSON.parse(localStorage.getItem(key) || "null"), LOG_KEY);

test("Read mode opens a note with nothing covered, and closing returns focus to its card", async ({ page }) => {
  await gotoGarden(page);
  await setStudyMode(page, false);
  const id = await findStudyableNoteId(page);
  const card = await openNoteByCard(page, id);
  const reader = page.locator("#modal-panel");

  await expect(page).toHaveURL(new RegExp(`#${id}$`));
  await expect(reader.locator("#modal-title")).toHaveText(await card.getAttribute("data-title"));
  await expect(reader.locator("#modal-content blockquote").first()).toBeVisible();
  await expect(reader.locator(".recall-cover")).toHaveCount(0);
  await expect(reader.locator("#modal-reviewed")).toHaveText("Never reviewed");

  await reader.getByRole("button", { name: "Close note" }).click();
  await expect(page.locator("#modal-backdrop")).toBeHidden();
  await expect(page).not.toHaveURL(/#/);
  await expect(card).toBeFocused();
});

test("Study mode covers the answer, reveals it, records a rating and can undo it", async ({ page }) => {
  await gotoGarden(page);
  await expect(page.locator("#due-count")).toHaveText("0");
  await expect(page.locator("#btn-start-review")).toBeDisabled();

  await setStudyMode(page, true);
  const id = await findStudyableNoteId(page);
  await openNoteByCard(page, id);
  const reader = page.locator("#modal-panel");

  const answer = reader.locator("blockquote[data-recall-hidden]");
  await expect(answer).toBeHidden();
  await expect(reader.locator(".recall-cover")).toContainText("Try to recall it first.");

  await reader.getByRole("button", { name: "Reveal" }).click();
  await expect(reader.locator(".recall-cover")).toHaveCount(0);
  await expect(reader.locator("#modal-content blockquote").first()).toBeVisible();
  const rateRow = reader.getByRole("group", { name: "How well did you remember it?" });
  await expect(rateRow.getByRole("button")).toHaveCount(4);
  await expect(rateRow.getByRole("button", { name: /Again/ })).toBeFocused();

  // The 3 key rates Good, as the shortcut sheet says.
  await page.keyboard.press("3");
  await expect(reader.locator(".rate-confirm")).toContainText(/Rated Good · next due in \d+ days?/);
  await expect(reader.locator(".rate-confirm")).toBeFocused();
  await expect(reader.locator("#modal-reviewed")).toContainText(/Last reviewed today · next due in \d+ days?/);

  const entry = (await readLog(page)).notes[id];
  expect(entry).toMatchObject({ reps: 1, lapses: 0 });
  expect(entry.due).toBeGreaterThan(Date.now());
  // Rated, but not due until tomorrow at the earliest: the queue is unchanged.
  await expect(page.locator("#due-count")).toHaveText("0");

  // Change rating restores the log to before the rating, not a second rating.
  await reader.getByRole("button", { name: "Change rating" }).click();
  await expect(rateRow.getByRole("button")).toHaveCount(4);
  expect((await readLog(page)).notes[id]).toBeUndefined();
  await expect(reader.locator("#modal-reviewed")).toHaveText("Never reviewed");
});

test("Study mode can be toggled with the s key while a note is open", async ({ page }) => {
  await gotoGarden(page);
  await openNoteByCard(page, await findStudyableNoteId(page));
  const reader = page.locator("#modal-panel");
  await expect(reader.locator(".recall-cover")).toHaveCount(0);
  await page.keyboard.press("s");
  await expect(page.locator("#btn-study-mode")).toHaveAttribute("aria-pressed", "true");
  await expect(reader.locator(".recall-cover")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("aurelia_study_mode"))).toBe("study");
  await page.keyboard.press("s");
  await expect(reader.locator(".recall-cover")).toHaveCount(0);
});

test("a review session walks the due queue, rating each note, and empties it", async ({ page }) => {
  await gotoGarden(page);
  const ids = await findStudyableNoteIds(page, 2);
  // Two notes rated a week ago and due yesterday: the shape Review.rate()
  // writes (assets/js/review.js), seeded so the queue has something in it.
  await page.evaluate(({ key, ids, day }) => {
    const now = Date.now();
    const notes = {};
    for (const id of ids) notes[id] = { last: now - 7 * day, due: now - day, interval: 6, ease: 2.5, reps: 2, lapses: 0 };
    localStorage.setItem(key, JSON.stringify({ version: 2, notes, decks: {} }));
    localStorage.setItem("aurelia_study_mode", "study");
  }, { key: LOG_KEY, ids, day: DAY_MS });
  await page.reload();

  await expect(page.locator("#due-count")).toHaveText("2");
  for (const id of ids) await expect(page.locator(`#cardGrid .searchable-item[data-id="${id}"]`)).toHaveClass(/is-due/);
  const start = page.locator("#btn-start-review");
  await expect(start).toBeEnabled();
  await start.click();

  const reader = page.locator("#modal-panel");
  await expect(reader).toHaveClass(/is-open/);
  await expect(page).toHaveURL(/review=1/);

  for (const position of [1, 2]) {
    await expect(reader.locator("#modal-session")).toHaveText(`Reviewing ${position} of 2`);
    const reveal = reader.getByRole("button", { name: "Reveal" });
    await expect(reveal).toBeVisible();
    await reveal.click();
    await reader.getByRole("button", { name: /Easy/ }).click();
    await expect(page.locator("#due-count")).toHaveText(String(2 - position));
  }

  await expect(reader.locator(".rate-confirm")).toContainText("Session complete: 2 notes reviewed.");
  await expect(reader.locator("#modal-session")).toBeHidden();
  await expect(start).toBeDisabled();
  const log = await readLog(page);
  for (const id of ids) {
    expect(log.notes[id].reps).toBe(3);
    expect(log.notes[id].due).toBeGreaterThan(Date.now());
  }

  await reader.getByRole("button", { name: "Back to the Garden" }).click();
  await expect(page.locator("#modal-backdrop")).toBeHidden();
  await expect(page).not.toHaveURL(/review=1/);
  for (const id of ids) await expect(page.locator(`#cardGrid .searchable-item[data-id="${id}"]`)).not.toHaveClass(/is-due/);
});

test("the Lobby shows the due count from the same review log", async ({ page }) => {
  await page.goto("index.html");
  await expect(page.locator("#lobby-review-teaser")).toBeHidden();
  await page.evaluate((key) => {
    const now = Date.now();
    localStorage.setItem(key, JSON.stringify({
      version: 2,
      notes: { "note-anything": { last: now - 2e9, due: now - 1e6, interval: 3, ease: 2.5, reps: 1, lapses: 0 } },
      decks: {},
    }));
  }, LOG_KEY);
  await page.reload();
  await expect(page.locator("#lobby-review-teaser")).toBeVisible();
  await expect(page.locator("#lobby-review-count")).toHaveText("1");
});
