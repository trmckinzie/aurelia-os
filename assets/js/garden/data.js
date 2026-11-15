/**
 * The Garden's build-time data (roadmap S13).
 *
 * The page carries two JSON data blocks, written by the build and never
 * executed, so the Content-Security-Policy needs no hash for them:
 *
 *   #garden-backlinks  note_id -> [{id, title}, ...] of the notes that link
 *                      to it (engine/pipeline.py, _build_link_graph).
 *                      Powers the reader's "Referenced By" section.
 *   #garden-graph      {nodes, edges} for the knowledge-graph view: id,
 *                      title, type and tags per note, and deduped undirected
 *                      edges (engine/pipeline.py, _build_graph_index).
 *
 * loadData() reads them once, from main.js, before anything else runs. The
 * exports are live bindings, so every importer sees the loaded values; until
 * then they are empty, which is also what a unit test starts from before it
 * calls setData().
 */
export let BACKLINKS_INDEX = {};
export let GRAPH_INDEX = { nodes: [], edges: [] };

// note_id -> full lowercased body text, powering the in-page deep search
// (see checkVisibility in grid.js). Built in pipeline._build_deep_search_index
// and loaded from assets/js/search-index.js (the <script> in the page's
// head), so ~0.95 MB is cached across visits instead of re-parsed inline on
// every page load. This is also the one copy: the same text used to be
// duplicated into a data-search attribute on every grid card AND again on
// every tree row.
//
// Stays an empty object if that file failed to load, which
// checkVisibility() handles by matching on title/tags instead of returning
// nothing -- see the note there.
export let DEEP_SEARCH_INDEX = {};

// id -> {id, title, type, tags} for every published note, built once from
// GRAPH_INDEX.nodes (already loaded for the graph view) so "Related by
// Topic" doesn't need its own separate embedded index.
export let NODE_BY_ID = {};

export function setData({ backlinks, graph, searchIndex }) {
    BACKLINKS_INDEX = backlinks || {};
    GRAPH_INDEX = graph || { nodes: [], edges: [] };
    DEEP_SEARCH_INDEX = searchIndex || {};
    NODE_BY_ID = {};
    GRAPH_INDEX.nodes.forEach(n => { NODE_BY_ID[n.id] = n; });
}

function readJsonBlock(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
}

export function loadData() {
    setData({
        backlinks: readJsonBlock('garden-backlinks'),
        graph: readJsonBlock('garden-graph'),
        searchIndex: window.DEEP_SEARCH_INDEX,
    });
}
