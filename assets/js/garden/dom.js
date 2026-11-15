/**
 * The Garden's long-lived elements (roadmap S13).
 *
 * The element references are looked up once, by initDom() from main.js,
 * rather than at import time: a module that touched `document` while loading
 * could not be imported by a unit test. They are live bindings, so every
 * importer sees the elements once initDom() has run.
 *
 * announce() and isTypingTarget(), which the modules call throughout, are
 * globals from assets/js/utils.js: flashcards.js needs them too, and a
 * classic script cannot import.
 */

// The three view panels and their toolbar buttons (views.js).
export let gridView = null;
export let treeView = null;
export let graphViewEl = null;
export let btnGrid = null;
export let btnTree = null;
export let btnGraph = null;
export let viewLabel = null;

// The note reader (reader.js) and the keyboard-shortcuts sheet (keyboard.js).
export let modalBackdrop = null;
export let modalPanel = null;
export let modalContent = null;
export let modalScroll = null;
export let modalProgress = null;
export let shortcutSheet = null;

export function initDom() {
    gridView = document.getElementById('cardGrid');
    treeView = document.getElementById('treeView');
    graphViewEl = document.getElementById('graphView');
    btnGrid = document.getElementById('btn-grid');
    btnTree = document.getElementById('btn-tree');
    btnGraph = document.getElementById('btn-graph');
    viewLabel = document.getElementById('view-mode-label');
    modalBackdrop = document.getElementById('modal-backdrop');
    modalPanel = document.getElementById('modal-panel');
    modalContent = document.getElementById('modal-content');
    modalScroll = document.getElementById('modal-scroll');
    modalProgress = document.getElementById('modal-progress');
    shortcutSheet = document.getElementById('shortcut-sheet');
}
