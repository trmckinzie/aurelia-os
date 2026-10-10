// The native dialogs (search palette, shortcut sheet, Toolkit sheet) and the
// note reader's keyboard paths: open, close, Escape, and where focus goes.
import { test, expect } from "./fixtures.mjs";
import { PAGES, PALETTE_KEY, findStudyableNoteId, gotoGarden, openNoteByCard } from "./helpers.mjs";

for (const { name, path, marker } of PAGES) {
  test(`${name}: the palette opens on Ctrl/Cmd+K, closes on Escape and returns focus`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator(marker)).toBeVisible();
    const skip = page.getByRole("link", { name: "Skip to content" });
    await skip.focus();

    const dialog = page.locator("#cmd-dialog");
    await page.keyboard.press(PALETTE_KEY);
    await expect(dialog).toBeVisible();
    await expect(page.locator("#cmd-input")).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(skip).toBeFocused();

    // The same shortcut toggles it shut as well.
    await page.keyboard.press(PALETTE_KEY);
    await expect(dialog).toBeVisible();
    await page.keyboard.press(PALETTE_KEY);
    await expect(dialog).toBeHidden();
  });
}

test("the palette searches, moves with the arrow keys and opens a result with Enter", async ({ page }) => {
  await page.goto("about.html");
  await page.keyboard.press(PALETTE_KEY);
  const input = page.locator("#cmd-input");
  await input.fill("garden");
  const options = page.locator("#cmd-results [role=option]");
  await expect(options.first()).toHaveAttribute("aria-selected", "true");
  await expect(input).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("#cmd-status")).toHaveText(/\d+ results?/);

  if ((await options.count()) > 1) {
    await page.keyboard.press("ArrowDown");
    await expect(options.nth(1)).toHaveAttribute("aria-selected", "true");
    await expect(input).toHaveAttribute("aria-activedescendant", "cmd-result-1");
    await page.keyboard.press("ArrowUp");
  }
  await expect(input).toHaveAttribute("aria-activedescendant", "cmd-result-0");
  const href = await options.first().getAttribute("href");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(href.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$"));
});

test("Escape in the palette closes only the palette, not the note reader under it", async ({ page }) => {
  await gotoGarden(page);
  const id = await findStudyableNoteId(page);
  await openNoteByCard(page, id);
  const reader = page.locator("#modal-panel");

  await page.keyboard.press(PALETTE_KEY);
  await expect(page.locator("#cmd-dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#cmd-dialog")).toBeHidden();

  await expect(reader).toHaveClass(/is-open/);
  await expect(page.locator("#modal-backdrop")).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`#${id}$`));
  await expect(reader).toBeFocused();

  // A second Escape now belongs to the reader.
  await page.keyboard.press("Escape");
  await expect(page.locator("#modal-backdrop")).toBeHidden();
});

test("the shortcut sheet opens with ? and its button, closes on Escape, and returns focus", async ({ page }) => {
  await gotoGarden(page);
  const sheet = page.locator("#shortcut-sheet");
  const button = page.locator("#btn-shortcuts");

  await button.click();
  await expect(sheet).toBeVisible();
  await expect(page.locator("#shortcut-sheet-title")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  await expect(button).toBeFocused();

  // From the keyboard with nothing focused, focus falls back to the button.
  await page.locator("body").click({ position: { x: 5, y: 400 } });
  await page.keyboard.press("?");
  await expect(sheet).toBeVisible();
  // The palette must not open on top of another dialog.
  await page.keyboard.press(PALETTE_KEY);
  await expect(page.locator("#cmd-dialog")).toBeHidden();
  await page.locator("#btn-shortcut-sheet-close").click();
  await expect(sheet).toBeHidden();
  await expect(button).toBeFocused();
});

test("the shortcut sheet over an open note: Escape closes the sheet and leaves the note open", async ({ page }) => {
  await gotoGarden(page);
  await openNoteByCard(page, await findStudyableNoteId(page));
  await page.keyboard.press("?");
  await expect(page.locator("#shortcut-sheet")).toBeVisible();
  // [ and ] belong to the sheet while it is open, not the reader beneath.
  const title = await page.locator("#modal-title").textContent();
  await page.keyboard.press("]");
  await page.keyboard.press("Escape");
  await expect(page.locator("#shortcut-sheet")).toBeHidden();
  await expect(page.locator("#modal-panel")).toHaveClass(/is-open/);
  await expect(page.locator("#modal-title")).toHaveText(title);
});

test("the reader: ] and [ step through notes, Tab stays inside, Escape closes", async ({ page }) => {
  await gotoGarden(page);
  const id = await findStudyableNoteId(page);
  const card = await openNoteByCard(page, id);
  const reader = page.locator("#modal-panel");
  const title = reader.locator("#modal-title");
  const first = await title.textContent();

  await page.keyboard.press("]");
  await expect(title).not.toHaveText(first);
  await expect(page).not.toHaveURL(new RegExp(`#${id}$`));
  await page.keyboard.press("[");
  await expect(title).toHaveText(first);
  await expect(page).toHaveURL(new RegExp(`#${id}$`));

  // Focus trap: however far Tab goes, focus stays in the reader.
  for (let i = 0; i < 25; i++) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.getElementById("modal-panel").contains(document.activeElement))).toBe(true);
  }
  await page.keyboard.press("Shift+Tab");
  expect(await page.evaluate(() => document.getElementById("modal-panel").contains(document.activeElement))).toBe(true);

  await page.keyboard.press("Escape");
  await expect(page.locator("#modal-backdrop")).toBeHidden();
  // Focus returns to the card's title control, the element that opened it (B19).
  await expect(card.locator(".card-open")).toBeFocused();
});

test("the Garden grid is one tab stop, arrow keys move between cards, Enter opens one", async ({ page }) => {
  await gotoGarden(page);
  const cards = page.locator("#cardGrid .searchable-item");
  // The tab stop is the card's title button, not the card (B19).
  const titles = page.locator("#cardGrid .searchable-item .card-open");
  await expect(page.locator('#cardGrid .card-open[tabindex="0"]')).toHaveCount(1);
  await expect(page.locator('#cardGrid .searchable-item[tabindex]')).toHaveCount(0);
  await titles.first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(titles.nth(1)).toBeFocused();
  await page.keyboard.press("Home");
  await expect(titles.first()).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#modal-panel")).toHaveClass(/is-open/);
  await expect(page.locator("#modal-title")).toHaveText(await cards.first().getAttribute("data-title"));
  await page.keyboard.press("Escape");
  await expect(titles.first()).toBeFocused();
});

test("a Garden card is not a button, so its pills are reachable, and a click on its body focuses its title", async ({ page }) => {
  await gotoGarden(page);
  const card = page.locator("#cardGrid .searchable-item").first();
  await expect(card).not.toHaveAttribute("role", /.+/);
  await expect(card.locator("h3 .card-open")).toHaveAttribute("type", "button");
  // Clicking the card's body, away from the title, opens the note and
  // returns focus to the title control on close.
  // The bottom padding, below the pill row: a click that hits neither the
  // title nor a pill, so only the card's own handler can open the note.
  const box = await card.boundingBox();
  await card.click({ position: { x: box.width / 2, y: box.height - 8 } });
  await expect(page.locator("#modal-panel")).toHaveClass(/is-open/);
  await page.keyboard.press("Escape");
  await expect(card.locator(".card-open")).toBeFocused();
});

test("the Lobby's Toolkit sheet opens, closes on Escape, and returns focus", async ({ page }) => {
  await page.goto("index.html");
  const more = page.locator("#readout-more");
  await more.click();
  const sheet = page.locator("#toolkit-sheet");
  await expect(sheet).toBeVisible();
  await expect(page.locator("#toolkit-sheet-title")).toBeFocused();
  await expect(page.locator("#toolkit-sheet-title")).not.toBeEmpty();
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  await expect(more).toBeFocused();
});
