// Roving focus: where the grid's one tab stop goes
// (assets/js/garden/roving.js).
import assert from "node:assert/strict";
import { test } from "node:test";

import { clampRovingIndex, columnCount, rovingIndexForKey } from "../../assets/js/garden/roving.js";

test("the index stays inside the visible items", () => {
  assert.equal(clampRovingIndex(2, 10), 2);
  assert.equal(clampRovingIndex(-1, 10), 0);
  assert.equal(clampRovingIndex(10, 10), 9);
});

test("filtering 245 cards down to 3 pulls the tab stop back onto the last one", () => {
  // Left at 180 it would point at a hidden card and Tab would skip the grid.
  assert.equal(clampRovingIndex(180, 3), 2);
});

test("with nothing visible the index is zero, ready for whatever is shown next", () => {
  assert.equal(clampRovingIndex(7, 0), 0);
});

test("left and right step one item and stop at the ends", () => {
  assert.equal(rovingIndexForKey("ArrowRight", 4, 10, 3), 5);
  assert.equal(rovingIndexForKey("ArrowLeft", 4, 10, 3), 3);
  assert.equal(rovingIndexForKey("ArrowRight", 9, 10, 3), 9);
  assert.equal(rovingIndexForKey("ArrowLeft", 0, 10, 3), 0);
});

test("up and down step one visual row at each column count", () => {
  for (const cols of [1, 2, 3]) {
    assert.equal(rovingIndexForKey("ArrowDown", 3, 12, cols), 3 + cols, `down, ${cols} columns`);
    assert.equal(rovingIndexForKey("ArrowUp", 3, 12, cols), 3 - cols, `up, ${cols} columns`);
  }
});

test("down from the last full row lands on the last item, and up from the first row on the first", () => {
  // Ten cards in three columns: the last row holds one card.
  assert.equal(rovingIndexForKey("ArrowDown", 8, 10, 3), 9);
  assert.equal(rovingIndexForKey("ArrowUp", 1, 10, 3), 0);
});

test("Home and End go to the first and last item", () => {
  assert.equal(rovingIndexForKey("Home", 6, 10, 3), 0);
  assert.equal(rovingIndexForKey("End", 6, 10, 3), 9);
  assert.equal(rovingIndexForKey("End", 0, 0, 3), 0, "End with nothing visible");
});

test("a key that does not move the tab stop returns null, so the handler leaves it to others", () => {
  for (const key of ["Enter", " ", "Tab", "a", "Escape", "PageDown"]) {
    assert.equal(rovingIndexForKey(key, 4, 10, 3), null, key);
  }
});

test("the column count is read from the computed grid template", () => {
  assert.equal(columnCount("412px 412px 412px"), 3);
  assert.equal(columnCount("  600px   600px "), 2);
  assert.equal(columnCount("375px"), 1);
  assert.equal(columnCount("none"), 1);
  assert.equal(columnCount(""), 1);
});
