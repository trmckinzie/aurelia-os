// Page-level helpers shared by the specs. Selectors are the ones the page
// scripts themselves use (system/templates/), so a test breaks when the
// behaviour moves, not when a class name is restyled.
import { expect } from "./fixtures.mjs";

export const PAGES = [
  { name: "Lobby", path: "index.html", marker: "#lobby-total-notes" },
  { name: "Garden", path: "garden.html", marker: "#filter-controls" },
  { name: "About", path: "about.html", marker: "#about-summary-heading" },
];

// A note whose body has a Definition heading followed by a blockquote, the
// shape Study mode covers (findRecallAnchor() in gardentemplate.html). Chosen
// at run time from the built page, so a vault edit cannot strand the test on
// a note that no longer exists.
export async function findStudyableNoteId(page) {
  return (await findStudyableNoteIds(page, 1))[0];
}

export async function findStudyableNoteIds(page, count) {
  const ids = await page.evaluate((count) => {
    const re = /Definition|Core Argument|Thesis|Profile & Context/i;
    const found = [];
    for (const card of document.querySelectorAll('#cardGrid .searchable-item[data-type="concept"]')) {
      if (found.length >= count) break;
      const raw = document.getElementById(card.dataset.id);
      if (!raw) continue;
      const txt = document.createElement("textarea");
      txt.innerHTML = raw.innerHTML;
      const html = window.marked.parse(txt.value, { breaks: true });
      const doc = new DOMParser().parseFromString(html, "text/html");
      const studyable = [...doc.querySelectorAll("h3")].some(
        (h) => re.test(h.textContent || "") && h.nextElementSibling?.tagName === "BLOCKQUOTE",
      );
      if (studyable) found.push(card.dataset.id);
    }
    return found;
  }, count);
  expect(ids.length, `fewer than ${count} concept notes with a Definition blockquote to study`).toBe(count);
  return ids;
}

export async function gotoGarden(page) {
  await page.goto("garden.html");
  await expect(page.locator("#cardGrid .searchable-item").first()).toBeVisible();
}

// Opens a note by clicking its card, the way a visitor does.
export async function openNoteByCard(page, noteId) {
  const card = page.locator(`#cardGrid .searchable-item[data-id="${noteId}"]`);
  await card.scrollIntoViewIfNeeded();
  await card.click();
  await expect(page.locator("#modal-panel")).toHaveClass(/is-open/);
  await expect(page.locator("#modal-panel")).toBeFocused();
  return card;
}

export async function setStudyMode(page, on) {
  const btn = page.locator("#btn-study-mode");
  if ((await btn.getAttribute("aria-pressed")) !== String(on)) await btn.click();
  await expect(btn).toHaveAttribute("aria-pressed", String(on));
}

// Ctrl+K on Linux and Windows, Cmd+K on macOS; the page accepts either.
export const PALETTE_KEY = "ControlOrMeta+k";
