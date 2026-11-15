// Shared by the unit tests in this folder (roadmap S13).
//
// The Garden's modules read a card through its data-* attributes and its
// style.display, so a plain object with those two properties stands in for
// the <article> without a DOM. Nothing here imports a browser.
import { setData } from "../../assets/js/garden/data.js";
import { state } from "../../assets/js/garden/state.js";

// A card as engine/cards.py renders it: every value is a string, as a
// data-* attribute always is, and tags are space-separated.
export function card({ id, title = id, type = "concept", tags = [], connections = 0, created = "", maturity = "" }) {
  return {
    dataset: { id, title, type, tags: tags.join(" "), connections: String(connections), created, maturity },
    style: { display: "" },
    // checkVisibility() falls back to the card's visible title when the
    // search index has no entry for it.
    querySelector: (selector) => (selector === "h3" ? { textContent: title } : null),
  };
}

// A graph node as engine/pipeline.py's _build_graph_index writes it.
export function node(id, type, tags = [], title = id) {
  return { id, title, type, tags };
}

// Every field of the shared state back to what a fresh page load has, and
// the build data emptied, so one test cannot leak into the next.
export function resetGarden() {
  Object.assign(state, {
    currentView: "grid",
    currentType: "all",
    currentQuery: "",
    currentTopic: "",
    rovingIndex: 0,
    currentSort: "connected",
    sortExplicit: false,
    restoring: false,
    currentModalNoteId: null,
    graphState: null,
    reviewSessionActive: false,
    reviewQueue: [],
    reviewSessionTotal: 0,
  });
  setData({});
}

export const titles = (cards) => cards.map((c) => c.dataset.title);
