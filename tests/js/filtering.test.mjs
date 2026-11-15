// The filter sweep's decision for one item, the graph's version of it, the
// topic cloud's counts and the view's query string
// (assets/js/garden/grid.js, topics.js, url-state.js).
import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { setData } from "../../assets/js/garden/data.js";
import { checkVisibility, clearHighlights, graphNodeMatches, highlightText } from "../../assets/js/garden/grid.js";
import { state } from "../../assets/js/garden/state.js";
import { topicCounts, topicLabel } from "../../assets/js/garden/topics.js";
import { viewQueryString } from "../../assets/js/garden/url-state.js";
import { card, node, resetGarden } from "./helpers.mjs";

beforeEach(resetGarden);
afterEach(() => { delete globalThis.escapeRegExp; });

const working = () => card({ id: "note-working-memory", title: "Working Memory", type: "concept", tags: ["topic/memory", "type/concept"] });

test("with no filter set, every item is visible", () => {
  assert.equal(checkVisibility(working()), true);
});

test("the type filter matches the card's type and nothing else", () => {
  state.currentType = "concept";
  assert.equal(checkVisibility(working()), true);
  state.currentType = "author";
  assert.equal(checkVisibility(working()), false);
});

test("the type filter matches inside a compound type, so 'source' finds a source/book note", () => {
  state.currentType = "source";
  assert.equal(checkVisibility(card({ id: "b", type: "source/book" })), true);
});

test("search reads the note's full text from the search index", () => {
  setData({ searchIndex: { "note-working-memory": "working memory holds about four chunks at once" } });
  state.currentQuery = "four chunks";
  assert.equal(checkVisibility(working()), true);
  state.currentQuery = "hippocampus";
  assert.equal(checkVisibility(working()), false);
});

test("without the search index, search still matches on the title and tags", () => {
  // The index is a separate file. If it fails to load, every query used to
  // match nothing, so search looked broken instead of merely shallower.
  state.currentQuery = "working";
  assert.equal(checkVisibility(working()), true);
  state.currentQuery = "topic/memory";
  assert.equal(checkVisibility(working()), true);
  state.currentQuery = "four chunks";
  assert.equal(checkVisibility(working()), false);
});

test("the topic filter needs the whole tag, not a prefix of it", () => {
  state.currentTopic = "topic/memory";
  assert.equal(checkVisibility(working()), true);
  state.currentTopic = "topic/mem";
  assert.equal(checkVisibility(working()), false);
});

test("the three filters are additive: one miss hides the item", () => {
  setData({ searchIndex: { "note-working-memory": "working memory" } });
  Object.assign(state, { currentType: "concept", currentQuery: "memory", currentTopic: "topic/memory" });
  assert.equal(checkVisibility(working()), true);
  for (const miss of [{ currentType: "author" }, { currentQuery: "zzz" }, { currentTopic: "topic/attention" }]) {
    Object.assign(state, { currentType: "concept", currentQuery: "memory", currentTopic: "topic/memory" }, miss);
    assert.equal(checkVisibility(working()), false, JSON.stringify(miss));
  }
});

test("a graph node matches on type, on title or tags, and on topic", () => {
  const n = node("note-working-memory", "concept", ["topic/memory"], "Working Memory");
  assert.equal(graphNodeMatches(n), true);
  state.currentQuery = "working";
  assert.equal(graphNodeMatches(n), true);
  state.currentQuery = "topic/memory";
  assert.equal(graphNodeMatches(n), true);
  state.currentQuery = "four chunks";
  assert.equal(graphNodeMatches(n), false, "graph nodes carry no body text");
  Object.assign(state, { currentQuery: "", currentType: "author" });
  assert.equal(graphNodeMatches(n), false);
  Object.assign(state, { currentType: "all", currentTopic: "topic/attention" });
  assert.equal(graphNodeMatches(n), false);
});

test("a graph node with no tags does not throw", () => {
  state.currentTopic = "topic/memory";
  assert.equal(graphNodeMatches({ id: "x", title: "X", type: "concept" }), false);
});

// --- search-match highlighting ---------------------------------------------

// One element of a card, as highlightText() uses it.
function cardWith(html) {
  const el = { dataset: {}, innerHTML: html };
  return { el, card: { querySelectorAll: () => [el] } };
}

// assets/js/utils.js is a classic script that needs a document, so the test
// supplies the one function the highlighter takes from it, written the same.
const useEscapeRegExp = () => {
  globalThis.escapeRegExp = (str) => String(str).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
};

test("highlighting wraps each match and leaves the tags around it alone", () => {
  useEscapeRegExp();
  const { el, card: c } = cardWith('Span of <button class="span">attention span</button>');
  highlightText(c, "span");
  assert.equal(el.innerHTML,
    '<span class="highlight">Span</span> of <button class="span">attention <span class="highlight">span</span></button>');
});

test("a query with regex characters is highlighted as typed, not compiled", () => {
  useEscapeRegExp();
  const { el, card: c } = cardWith("System 1 (fast) and System 2");
  highlightText(c, "system 1 (fast)");
  assert.equal(el.innerHTML, '<span class="highlight">System 1 (fast)</span> and System 2');
});

test("highlighting again starts from the original text, and clearing restores it", () => {
  useEscapeRegExp();
  const { el, card: c } = cardWith("Working memory");
  highlightText(c, "work");
  highlightText(c, "memory");
  assert.equal(el.innerHTML, 'Working <span class="highlight">memory</span>');
  clearHighlights(c);
  assert.equal(el.innerHTML, "Working memory");
});

// --- topic cloud -------------------------------------------------------------

test("the topic cloud counts topic tags only, most used first", () => {
  const nodes = [
    node("a", "concept", ["topic/memory", "type/concept", "status/seed"]),
    node("b", "concept", ["topic/memory", "topic/attention"]),
    node("c", "author", ["topic/memory"]),
    { id: "d", title: "D", type: "concept" },
  ];
  assert.deepEqual(topicCounts(nodes), [["topic/memory", 3], ["topic/attention", 1]]);
});

test("the topic cloud keeps only the limit it is given", () => {
  const nodes = Array.from({ length: 30 }, (_, i) => node(`n${i}`, "concept", [`topic/t${i}`]));
  assert.equal(topicCounts(nodes).length, 24);
  assert.equal(topicCounts(nodes, 5).length, 5);
});

test("a topic tag reads as plain words", () => {
  assert.equal(topicLabel("topic/working-memory-models"), "working memory models");
});

// --- the view as a query string ----------------------------------------------

test("the default view has no query string", () => {
  assert.equal(viewQueryString(), "");
});

test("every part of the view that differs from the default is in the query string", () => {
  Object.assign(state, {
    currentQuery: "working memory", currentType: "concept", currentTopic: "topic/memory",
    currentView: "graph", currentSort: "title", sortExplicit: true, reviewSessionActive: true,
  });
  const params = new URLSearchParams(viewQueryString());
  assert.deepEqual(Object.fromEntries(params), {
    q: "working memory", type: "concept", topic: "topic/memory", view: "graph", sort: "title", review: "1",
  });
});

test("a sort the reader did not choose is not carried in the link", () => {
  // Auto-relevance comes from the query; pinning it would stop the sort
  // adapting to the next reader's own search.
  Object.assign(state, { currentQuery: "memory", currentSort: "title", sortExplicit: false });
  assert.equal(viewQueryString(), "q=memory");
  Object.assign(state, { currentQuery: "", currentSort: "connected", sortExplicit: true });
  assert.equal(viewQueryString(), "", "an explicit choice of the default needs no parameter");
});
