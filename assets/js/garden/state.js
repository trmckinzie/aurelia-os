/**
 * The Garden's shared, mutable page state (roadmap S13).
 *
 * One object, imported by every module that reads or writes it. An ES
 * module's exported `let` is read-only to its importers, so state that more
 * than one module writes has to live on an object; keeping all of it here
 * also makes "what can change on this page" one short list instead of a
 * search through twenty files. State that only one module touches (the
 * read-aloud queue, the graph's pan and zoom, the due-id set) stays private
 * to that module.
 *
 * No DOM access and no imports, so a unit test can import it, set a field
 * and call the function under test.
 */
export const state = {
    // Which of the three panels is showing: 'grid' | 'tree' | 'graph'.
    currentView: 'grid',

    // The three filters, all additive (see checkVisibility in grid.js).
    currentType: 'all',
    currentQuery: '',
    currentTopic: '',

    // Index of the card or tree row that carries the one tab stop
    // (roving.js).
    rovingIndex: 0,

    // sorting.js. The literal matches DEFAULT_SORT there; it is written out
    // because importing it would make this module depend on one that
    // depends on it. tests/js/sorting.test.mjs holds the two together.
    currentSort: 'connected',
    // Set once the reader picks a sort themselves, so auto-relevance never
    // overrides a deliberate choice.
    sortExplicit: false,

    // True while restoreViewFromUrl() applies several settings in a row
    // (url-state.js); updateGrid() and syncViewToUrl() no-op meanwhile.
    restoring: false,

    // The note the reader is showing, or null when it is closed.
    currentModalNoteId: null,

    // The knowledge graph's nodes, edges and layout, built on first use
    // (graph.js); null until then.
    graphState: null,

    // A review session (review-session.js). The queue shrinks as notes are
    // rated; the total is the queue's starting length, which is what lets
    // the header say "Reviewing 2 of 5".
    reviewSessionActive: false,
    reviewQueue: [],
    reviewSessionTotal: 0,
};
