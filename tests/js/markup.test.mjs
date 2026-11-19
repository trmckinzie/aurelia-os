// The reader's connection sections and the graph's list are built as
// elements, never as HTML strings, so a note id or title read from the
// page's data blocks can only ever be text or an attribute value. These
// tests pin that with a stand-in for `document` that records what was built:
// if a hostile value shows up anywhere but a text node, a data-* value or an
// attribute, the code went back to building markup from strings.
import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { renderBacklinks, renderElaboration, renderRelatedByTopic } from "../../assets/js/garden/connections.js";
import { setData } from "../../assets/js/garden/data.js";
import { el, noteButton } from "../../assets/js/garden/dom.js";
import { renderGraphList } from "../../assets/js/garden/graph.js";
import { node, resetGarden } from "./helpers.mjs";

const HOSTILE_ID = 'note-x" onclick="alert(1)';
const HOSTILE_TITLE = '<img src=x onerror=alert(1)> & "friends"';

function fakeElement(tag) {
  return {
    tag,
    className: "",
    textContent: "",
    hidden: false,
    dataset: {},
    attrs: {},
    children: [],
    classList: { toggle() {} },
    setAttribute(name, value) { this.attrs[name] = value; },
    appendChild(child) { this.children.push(child); return child; },
    replaceChildren(...kids) { this.children = kids; },
    set innerHTML(value) {
      // Only the empty string is ever allowed through here.
      assert.equal(value, "", "a section was built from an HTML string");
      this.children = [];
    },
  };
}

function fakeDocument() {
  const byId = {};
  return {
    byId,
    createElement: fakeElement,
    createTextNode: (text) => ({ text }),
    getElementById(id) {
      if (!byId[id]) byId[id] = fakeElement("div");
      return byId[id];
    },
  };
}

// Every element under `root`, depth first.
function walk(root, out = []) {
  for (const child of root.children || []) {
    out.push(child);
    walk(child, out);
  }
  return out;
}

const buttonsFor = (container) => walk(container).filter((n) => n.tag === "button" && n.dataset.note !== undefined);

beforeEach(() => {
  resetGarden();
  globalThis.document = fakeDocument();
});

afterEach(() => {
  delete globalThis.document;
});

test("el() sets text, data-* values and attributes as values, and turns strings into text nodes", () => {
  const built = el("p", { className: "c", dataset: { note: HOSTILE_ID }, attrs: { title: HOSTILE_TITLE } }, [
    "before ",
    el("span", { text: HOSTILE_TITLE }),
  ]);
  assert.equal(built.className, "c");
  assert.equal(built.dataset.note, HOSTILE_ID);
  assert.equal(built.attrs.title, HOSTILE_TITLE);
  assert.deepEqual(built.children[0], { text: "before " });
  assert.equal(built.children[1].textContent, HOSTILE_TITLE);
});

test("noteButton() is a plain button that names its note", () => {
  const button = noteButton(HOSTILE_ID, HOSTILE_TITLE, "pill", { title: "2 shared tags" });
  assert.equal(button.tag, "button");
  assert.equal(button.attrs.type, "button");
  assert.equal(button.attrs.title, "2 shared tags");
  assert.equal(button.dataset.note, HOSTILE_ID);
  assert.equal(button.textContent, HOSTILE_TITLE);
  assert.equal(button.className, "pill");
});

test("Referenced By keeps a hostile id and title as values, and hides the overflow", () => {
  const refs = [{ id: HOSTILE_ID, title: HOSTILE_TITLE }];
  for (let i = 0; i < 14; i += 1) refs.push({ id: `note-${i}`, title: `Note ${i}` });
  setData({ backlinks: { "note-a": refs }, graph: { nodes: [], edges: [] } });

  renderBacklinks("note-a");

  const container = globalThis.document.getElementById("modal-backlinks");
  const buttons = buttonsFor(container);
  assert.equal(buttons.length, 15);
  assert.equal(buttons[0].dataset.note, HOSTILE_ID);
  assert.equal(buttons[0].textContent, HOSTILE_TITLE);

  const all = walk(container);
  assert.ok(all.some((n) => n.textContent === "⟵ Referenced By (15)"));
  const rest = all.find((n) => n.attrs && n.attrs.id === "backlinks-rest");
  assert.equal(rest.hidden, true);
  assert.equal(rest.children.length, 3);
  const more = all.find((n) => n.dataset && n.dataset.action === "expandBacklinks");
  assert.equal(more.textContent, "+3 MORE");
});

test("Referenced By with nothing to show empties the section", () => {
  setData({ backlinks: {}, graph: { nodes: [], edges: [] } });
  const container = globalThis.document.getElementById("modal-backlinks");
  container.children = [fakeElement("div")];
  renderBacklinks("note-a");
  assert.equal(container.children.length, 0);
});

test("Related by Topic keeps a hostile id and title as values", () => {
  const hostile = node(HOSTILE_ID, "concept", ["topic/memory"], HOSTILE_TITLE);
  setData({ graph: { nodes: [node("note-a", "concept", ["topic/memory"]), hostile], edges: [] } });

  renderRelatedByTopic("note-a");

  const buttons = buttonsFor(globalThis.document.getElementById("modal-related"));
  assert.equal(buttons.length, 1);
  assert.equal(buttons[0].dataset.note, HOSTILE_ID);
  assert.equal(buttons[0].textContent, HOSTILE_TITLE);
  assert.equal(buttons[0].attrs.title, "1 shared tag");
});

test("the elaboration nudge keeps a hostile id and title as values", () => {
  const hostile = node(HOSTILE_ID, "discipline", [], HOSTILE_TITLE);
  setData({
    backlinks: { "note-a": [{ id: HOSTILE_ID, title: HOSTILE_TITLE }] },
    graph: { nodes: [node("note-a", "concept"), hostile], edges: [] },
  });

  renderElaboration("note-a");

  const container = globalThis.document.getElementById("modal-elaborate");
  const paragraph = walk(container).find((n) => n.tag === "p");
  assert.deepEqual(paragraph.children[0], { text: "How does this connect to " });
  assert.equal(paragraph.children[1].dataset.note, HOSTILE_ID);
  assert.equal(paragraph.children[1].textContent, HOSTILE_TITLE);
  assert.deepEqual(paragraph.children[2], { text: "?" });
});

test("the graph's list keeps a hostile id and title as values and counts links", () => {
  const hostile = node(HOSTILE_ID, "concept", [], HOSTILE_TITLE);
  setData({
    graph: { nodes: [hostile, node("note-b", "concept")], edges: [{ source: HOSTILE_ID, target: "note-b" }] },
  });

  renderGraphList();

  const container = globalThis.document.getElementById("graph-list-items");
  const rows = buttonsFor(container);
  assert.equal(rows.length, 2);
  const row = rows.find((r) => r.dataset.note === HOSTILE_ID);
  assert.equal(row.className, "graph-list-row");
  assert.equal(row.children[0].textContent, HOSTILE_TITLE);
  assert.equal(row.children[1].textContent, "◉ 1 LINK");
});
