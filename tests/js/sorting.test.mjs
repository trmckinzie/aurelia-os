// Sort order and relevance ranking (assets/js/garden/sorting.js).
import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import {
  DEFAULT_SORT,
  SORTS,
  comparatorFor,
  effectiveSort,
  relevanceScore,
} from "../../assets/js/garden/sorting.js";
import { state } from "../../assets/js/garden/state.js";
import { card, resetGarden, titles } from "./helpers.mjs";

beforeEach(resetGarden);
afterEach(() => {
  delete globalThis.window;
  delete globalThis.Review;
});

const sorted = (cards, mode, q = "") => titles([...cards].sort(comparatorFor(mode, q)));

test("the state's starting sort is the default sort", () => {
  // state.js writes the literal because it cannot import sorting.js.
  assert.equal(state.currentSort, DEFAULT_SORT);
  assert.ok(SORTS.includes(DEFAULT_SORT));
});

test("typing a query implies relevance until the reader picks a sort", () => {
  assert.equal(effectiveSort(), "connected");
  state.currentQuery = "memory";
  assert.equal(effectiveSort(), "relevance");
  state.currentSort = "title";
  state.sortExplicit = true;
  assert.equal(effectiveSort(), "title");
});

test("relevance ranks an exact title over a prefix, a substring, a tag and a body match", () => {
  const q = "memory";
  const exact = relevanceScore(card({ id: "a", title: "Memory" }), q);
  const prefix = relevanceScore(card({ id: "b", title: "Memory Palace" }), q);
  const inside = relevanceScore(card({ id: "c", title: "Working Memory" }), q);
  const tagged = relevanceScore(card({ id: "d", title: "Chunking", tags: ["topic/memory"] }), q);
  const body = relevanceScore(card({ id: "e", title: "Attention" }), q);
  assert.deepEqual([exact, prefix, inside, tagged, body], [100, 80, 60, 40, 20]);
});

test("the title comparison ignores case", () => {
  assert.equal(relevanceScore(card({ id: "a", title: "MEMORY" }), "memory"), 100);
});

test("connections nudge a score by at most ten points, so they break ties and no more", () => {
  const q = "memory";
  const popularBody = relevanceScore(card({ id: "a", title: "Attention", connections: 500 }), q);
  const loneTitle = relevanceScore(card({ id: "b", title: "Working Memory", connections: 0 }), q);
  assert.equal(popularBody, 30);
  assert.ok(loneTitle > popularBody);
});

test("a search puts the note titled for the query first, whatever its neighbours' link counts", () => {
  // The bug this ordering fixed: "Working Memory" at position 76 of 76.
  const cards = [
    card({ id: "a", title: "Attention", connections: 40 }),
    card({ id: "b", title: "Working Memory", connections: 3 }),
    card({ id: "c", title: "Encoding", tags: ["topic/memory"], connections: 12 }),
  ];
  assert.deepEqual(sorted(cards, "relevance", "memory"), ["Working Memory", "Encoding", "Attention"]);
});

test("most connected first, then by title", () => {
  const cards = [
    card({ id: "a", title: "Zeta", connections: 2 }),
    card({ id: "b", title: "Alpha", connections: 2 }),
    card({ id: "c", title: "Mid", connections: 9 }),
    card({ id: "d", title: "None" }),
  ];
  assert.deepEqual(sorted(cards, "connected"), ["Mid", "Alpha", "Zeta", "None"]);
});

test("an unknown sort falls back to most connected", () => {
  const cards = [card({ id: "a", title: "A", connections: 1 }), card({ id: "b", title: "B", connections: 5 })];
  assert.deepEqual(sorted(cards, "no-such-sort"), ["B", "A"]);
});

test("newest first by ISO date, with an undated note last", () => {
  const cards = [
    card({ id: "a", title: "Old", created: "2025-01-09" }),
    card({ id: "b", title: "Undated" }),
    card({ id: "c", title: "New", created: "2026-10-02" }),
    card({ id: "d", title: "Also new", created: "2026-10-02" }),
  ];
  assert.deepEqual(sorted(cards, "recent"), ["Also new", "New", "Old", "Undated"]);
});

test("maturity runs evergreen, growing, seed, then unmarked, with connections breaking ties", () => {
  const cards = [
    card({ id: "a", title: "Seed", maturity: "seed" }),
    card({ id: "b", title: "Unmarked" }),
    card({ id: "c", title: "Evergreen quiet", maturity: "evergreen", connections: 1 }),
    card({ id: "d", title: "Growing", maturity: "growing" }),
    card({ id: "e", title: "Evergreen busy", maturity: "evergreen", connections: 8 }),
  ];
  assert.deepEqual(sorted(cards, "maturity"), ["Evergreen busy", "Evergreen quiet", "Growing", "Seed", "Unmarked"]);
});

test("title order is alphabetical without regard to case", () => {
  const cards = [card({ id: "a", title: "beta" }), card({ id: "b", title: "Alpha" }), card({ id: "c", title: "Gamma" })];
  assert.deepEqual(sorted(cards, "title"), ["Alpha", "beta", "Gamma"]);
});

test("due first puts the soonest due date first and a never-reviewed note last", () => {
  const due = { soon: { due: 1000 }, later: { due: 9000 } };
  globalThis.Review = { stateFor: (id) => due[id] || null };
  globalThis.window = { Review: globalThis.Review };
  const cards = [
    card({ id: "never", title: "Never reviewed" }),
    card({ id: "later", title: "Later" }),
    card({ id: "soon", title: "Soon" }),
  ];
  assert.deepEqual(sorted(cards, "due"), ["Soon", "Later", "Never reviewed"]);
});

test("due first without the review engine leaves the notes in title order", () => {
  globalThis.window = {};
  const cards = [card({ id: "b", title: "B" }), card({ id: "a", title: "A" })];
  assert.deepEqual(sorted(cards, "due"), ["A", "B"]);
});
