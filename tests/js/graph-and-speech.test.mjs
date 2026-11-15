// The knowledge graph's arithmetic and the read-aloud text splitter
// (assets/js/garden/graph.js, read-aloud.js), and the rule that every module
// loads without a browser.
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { beforeEach, test } from "node:test";

import { setData } from "../../assets/js/garden/data.js";
import { computeGraphDegrees, graphColorFor, layoutGraph } from "../../assets/js/garden/graph.js";
import { splitIntoChunks } from "../../assets/js/garden/read-aloud.js";
import { state } from "../../assets/js/garden/state.js";
import { node, resetGarden } from "./helpers.mjs";

beforeEach(resetGarden);

test("a note's degree is the number of edges that touch it", () => {
  setData({
    graph: {
      nodes: [node("a", "concept"), node("b", "concept"), node("c", "concept"), node("alone", "concept")],
      edges: [{ source: "a", target: "b" }, { source: "a", target: "c" }],
    },
  });
  assert.deepEqual(computeGraphDegrees(), { a: 2, b: 1, c: 1, alone: 0 });
});

test("a node's colour comes from the first type key its type contains", () => {
  const colors = { concept: "cyan", source: "yellow", "daily-bridge": "orange" };
  assert.equal(graphColorFor("concept", colors, "grey"), "cyan");
  assert.equal(graphColorFor("source/book", colors, "grey"), "yellow");
  assert.equal(graphColorFor("author", colors, "grey"), "grey");
});

test("the layout gives every node a finite position and pulls linked notes together", () => {
  const ids = ["a", "b", "c", "d", "e", "f"];
  const nodes = ids.map((id, i) => {
    const angle = (i / ids.length) * Math.PI * 2;
    return { id, x: Math.cos(angle) * 200, y: Math.sin(angle) * 200 };
  });
  state.graphState = {
    nodes,
    edges: [{ source: "a", target: "d" }, { source: "missing", target: "a" }],
    byId: Object.fromEntries(nodes.map((n) => [n.id, n])),
  };
  layoutGraph(800, 600);
  for (const n of nodes) {
    assert.ok(Number.isFinite(n.x) && Number.isFinite(n.y), `${n.id} has a position`);
  }
  const distance = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);
  const [a, b, , d] = nodes;
  // a and d start opposite each other on the circle and are linked; a and b
  // start as neighbours and are not.
  assert.ok(distance(a, d) < distance(a, b), "the linked pair ends closer than an unlinked one");
});

test("the layout of an empty graph does nothing", () => {
  state.graphState = { nodes: [], edges: [], byId: {} };
  layoutGraph(800, 600);
  assert.deepEqual(state.graphState.nodes, []);
});

test("read aloud splits a note into sentences, keeping each one's punctuation", () => {
  assert.deepEqual(
    splitIntoChunks("Working memory is small.  Is it fixed?\nNo! It can be trained"),
    ["Working memory is small.", " Is it fixed?", " No!", " It can be trained"],
  );
});

test("read aloud has nothing to say for an empty note", () => {
  assert.deepEqual(splitIntoChunks("   \n  "), []);
});

test("every module but the entry loads without a document", async () => {
  // main.js starts the page, so it is the one file that needs a browser.
  // The rest must only declare: that is what lets these tests import them.
  const dir = new URL("../../assets/js/garden/", import.meta.url);
  const modules = readdirSync(dir).filter((name) => name.endsWith(".js") && name !== "main.js");
  assert.ok(modules.length >= 15, "the folder holds the Garden's modules");
  for (const name of modules) {
    await assert.doesNotReject(import(new URL(name, dir)), `${name} runs code at import time`);
  }
});
