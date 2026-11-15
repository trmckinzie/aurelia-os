// The page's side of spaced review: the order of a review session, the
// "next due" wording, and which notes a rating nudges the reader toward
// (assets/js/garden/review-session.js, study.js, connections.js). The
// scheduler itself is assets/js/review.js, which these do not load.
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import {
  elaborationCandidates,
  graphNeighbours,
  nudgeTypeRank,
  relatedByTopic,
  sharedTopicCount,
} from "../../assets/js/garden/connections.js";
import { setData } from "../../assets/js/garden/data.js";
import { buildInterleavedQueue } from "../../assets/js/garden/review-session.js";
import { DAY_MS, nextDuePhrase, relativeDayPhrase } from "../../assets/js/garden/study.js";
import { node, resetGarden } from "./helpers.mjs";

beforeEach(resetGarden);

// Loads `nodes` as the page's graph and returns the id -> type lookup a
// session is built with.
function graph(nodes, edges = [], backlinks = {}) {
  setData({ graph: { nodes, edges }, backlinks });
  const types = Object.fromEntries(nodes.map((n) => [n.id, n.type]));
  return (id) => types[id] || "";
}

// --- the order of a review session -------------------------------------------

test("a session keeps every due note, once each", () => {
  const typeOf = graph([node("a", "concept"), node("b", "concept"), node("c", "author"), node("d", "source")]);
  const queue = buildInterleavedQueue(["a", "b", "c", "d"], typeOf);
  assert.deepEqual([...queue].sort(), ["a", "b", "c", "d"]);
});

test("a session does not change the list it was given", () => {
  const typeOf = graph([node("a", "concept"), node("b", "author")]);
  const due = ["a", "b"];
  buildInterleavedQueue(due, typeOf);
  assert.deepEqual(due, ["a", "b"]);
});

test("notes of different types are interleaved, not run through type by type", () => {
  const typeOf = graph([
    node("c1", "concept"), node("c2", "concept"), node("c3", "concept"),
    node("a1", "author"), node("a2", "author"), node("s1", "source"),
  ]);
  const queue = buildInterleavedQueue(["c1", "c2", "c3", "a1", "a2", "s1"], typeOf);
  const types = queue.map(typeOf);
  // No type repeats while another is still available, so the three concepts
  // that were due together are never shown back to back.
  assert.deepEqual(types.slice(0, 3), ["concept", "author", "source"]);
  assert.notEqual(types[3], types[4]);
});

test("when only one type is due the session still runs through all of it", () => {
  const typeOf = graph([node("c1", "concept"), node("c2", "concept"), node("c3", "concept")]);
  assert.equal(buildInterleavedQueue(["c1", "c2", "c3"], typeOf).length, 3);
});

test("among notes of an allowed type, the one sharing fewest topics with the last note comes next", () => {
  const typeOf = graph([
    node("first", "concept", ["topic/memory", "topic/attention"]),
    node("close", "author", ["topic/memory", "topic/attention"]),
    node("far", "author", ["topic/ethics"]),
  ]);
  assert.deepEqual(buildInterleavedQueue(["first", "close", "far"], typeOf), ["first", "far", "close"]);
});

test("an empty due list is an empty session", () => {
  assert.deepEqual(buildInterleavedQueue([], () => ""), []);
});

// --- "next due" wording ----------------------------------------------------------

test("a gap in days reads as today, one day or several", () => {
  assert.equal(relativeDayPhrase(0, "ago"), "today");
  assert.equal(relativeDayPhrase(DAY_MS * 0.4, "in"), "today");
  assert.equal(relativeDayPhrase(DAY_MS, "ago"), "1 day ago");
  assert.equal(relativeDayPhrase(DAY_MS * 3, "ago"), "3 days ago");
  assert.equal(relativeDayPhrase(DAY_MS, "in"), "in 1 day");
  assert.equal(relativeDayPhrase(DAY_MS * 7, "in"), "in 7 days");
  assert.equal(relativeDayPhrase(-DAY_MS * 2, "ago"), "2 days ago", "the sign of the gap does not matter");
});

test("a note due in the past or right now is due now", () => {
  const now = 1_800_000_000_000;
  assert.equal(nextDuePhrase({ due: now - DAY_MS }, now), "next due now");
  assert.equal(nextDuePhrase({ due: now }, now), "next due now");
});

test("a note due later says in how many days", () => {
  const now = 1_800_000_000_000;
  assert.equal(nextDuePhrase({ due: now + DAY_MS * 3 }, now), "next due in 3 days");
  assert.equal(nextDuePhrase({ due: now + DAY_MS }, now), "next due in 1 day");
});

// --- what a note connects to -----------------------------------------------------

test("shared topics count topic tags only", () => {
  graph([
    node("a", "concept", ["topic/memory", "topic/attention", "type/concept"]),
    node("b", "concept", ["topic/memory", "type/concept", "status/seed"]),
  ]);
  assert.equal(sharedTopicCount("a", "b"), 1);
  assert.equal(sharedTopicCount("a", "missing"), 0);
});

test("a note's graph neighbours are the other end of each of its edges", () => {
  graph([node("a", "concept"), node("b", "concept"), node("c", "concept")],
    [{ source: "a", target: "b" }, { source: "c", target: "a" }, { source: "b", target: "c" }]);
  assert.deepEqual([...graphNeighbours("a")].sort(), ["b", "c"]);
});

test("the type preference runs discipline, author, source, deep dive, concept, then anything else", () => {
  const ranks = ["discipline", "author", "source", "deep-dive", "concept", "unheard-of"].map(nudgeTypeRank);
  assert.deepEqual(ranks, [0, 1, 2, 3, 4, 5]);
});

test("related by topic ranks by shared topics and leaves out daily logs and notebooks", () => {
  graph([
    node("me", "concept", ["topic/memory", "topic/attention"]),
    node("log", "daily-bridge", ["topic/memory", "topic/attention"], "2026-02-12"),
    node("notebook", "gemini-notebook", ["topic/memory", "topic/attention"], "PSYC 414"),
    node("both", "concept", ["topic/memory", "topic/attention"], "Both"),
    node("one", "author", ["topic/memory"], "One"),
    node("none", "concept", ["topic/ethics"], "None"),
  ]);
  assert.deepEqual(relatedByTopic("me").map((r) => [r.node.id, r.shared]), [["both", 2], ["one", 1]]);
});

test("related by topic brings daily logs back when fewer than two other notes qualify", () => {
  graph([
    node("me", "concept", ["topic/memory"]),
    node("log", "daily-bridge", ["topic/memory"], "2026-02-12"),
    node("one", "author", ["topic/memory"], "One"),
  ]);
  assert.deepEqual(relatedByTopic("me").map((r) => r.node.id), ["one", "log"]);
});

test("related by topic is empty for a note with no topic tags, and shows five at most", () => {
  graph([node("me", "concept", ["type/concept"]), node("x", "concept", ["type/concept"])]);
  assert.deepEqual(relatedByTopic("me"), []);
  graph([node("me", "concept", ["topic/t"]), ...Array.from({ length: 8 }, (_, i) => node(`n${i}`, "concept", ["topic/t"]))]);
  assert.equal(relatedByTopic("me").length, 5);
});

test("the elaboration nudge draws on backlinks and graph neighbours, different types first", () => {
  graph(
    [
      node("me", "concept", ["topic/memory"]),
      node("same", "concept", ["topic/ethics"], "Same type"),
      node("author", "author", ["topic/memory"], "An author"),
      node("discipline", "discipline", [], "A discipline"),
      node("log", "daily-bridge", [], "2026-02-12"),
      node("unlinked", "source", [], "Not connected"),
    ],
    [{ source: "me", target: "same" }, { source: "discipline", target: "me" }, { source: "me", target: "log" }],
    { me: [{ id: "author", title: "An author" }, { id: "me", title: "Itself" }] },
  );
  // A discipline before an author (the type preference), the same-type
  // concept last, the daily log and the unconnected note never.
  assert.deepEqual(elaborationCandidates("me").map((r) => r.node.id), ["discipline", "author", "same"]);
});

test("the elaboration nudge offers three notes at most, and none for a note with no connections", () => {
  graph(
    [node("me", "concept"), ...Array.from({ length: 6 }, (_, i) => node(`a${i}`, "author"))],
    Array.from({ length: 6 }, (_, i) => ({ source: "me", target: `a${i}` })),
  );
  assert.equal(elaborationCandidates("me").length, 3);
  graph([node("alone", "concept")]);
  assert.deepEqual(elaborationCandidates("alone"), []);
});
