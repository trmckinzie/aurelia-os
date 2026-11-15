/**
 * Sort order and relevance ranking for the card grid.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { updateGrid } from './grid.js';
import { state } from './state.js';
import { syncViewToUrl } from './url-state.js';

// HELPER: Centralized Logic (The Brain)
/* === SORTING & RELEVANCE RANKING =================================
   The Garden could be sliced four ways and then returned results in no
   order at all -- card order was filesystem order. Searching "memory"
   put the note actually titled "Working Memory" (the most-linked note
   in the vault) at position 76 of 76.

   Reordering moves real DOM nodes rather than setting CSS `order`.
   getVisibleNoteIds() reads querySelectorAll order and feeds the
   modal's [ / ] navigation and openRandomNote(); CSS `order` changes
   only visual position, so "next note" would silently disagree with
   what the reader sees. Moving nodes keeps them in step -- and makes
   prev/next follow the active sort for free. */
export const SORTS = ['relevance', 'connected', 'recent', 'maturity', 'title', 'due'];
export const DEFAULT_SORT = 'connected';
// Set once the reader picks a sort themselves, so auto-relevance below
// never overrides a deliberate choice.

// Relevance is implied by typing, but only until the reader says
// otherwise.
export function effectiveSort() {
    if (state.currentQuery && !state.sortExplicit) return 'relevance';
    return state.currentSort;
}

export const MATURITY_RANK = { evergreen: 3, growing: 2, seed: 1 };

export function cardTitle(el) { return (el.dataset.title || '').toLowerCase(); }
export function cardConnections(el) { return parseInt(el.dataset.connections, 10) || 0; }

/* A card only reaches scoring if it already matched the query
   somewhere, so a body match is the floor rather than a zero. The
   connection nudge is small on purpose: it should break ties between
   comparable matches, not let a popular note outrank an exact title. */
export function relevanceScore(el, q) {
    const title = cardTitle(el);
    const tags = (el.dataset.tags || '').toLowerCase();
    let score = 20;
    if (title === q) score = 100;
    else if (title.startsWith(q)) score = 80;
    else if (title.includes(q)) score = 60;
    else if (tags.includes(q)) score = 40;
    return score + Math.min(cardConnections(el), 20) * 0.5;
}

export function comparatorFor(mode, q) {
    const byTitle = (a, b) => cardTitle(a).localeCompare(cardTitle(b));
    switch (mode) {
        case 'relevance':
            return (a, b) => relevanceScore(b, q) - relevanceScore(a, q)
                          || cardConnections(b) - cardConnections(a)
                          || byTitle(a, b);
        case 'recent':
            // Descending string compare works because dates are ISO
            // (YYYY-MM-DD); verified present on all 245 published notes.
            return (a, b) => (b.dataset.created || '').localeCompare(a.dataset.created || '')
                          || byTitle(a, b);
        case 'maturity':
            return (a, b) => (MATURITY_RANK[b.dataset.maturity] || 0) - (MATURITY_RANK[a.dataset.maturity] || 0)
                          || cardConnections(b) - cardConnections(a)
                          || byTitle(a, b);
        case 'title':
            return byTitle;
        case 'due':
            // Ascending due date -- soonest due first. A note with no
            // review entry sorts last (Infinity), not first: "never
            // reviewed" isn't "most urgent," it's simply unranked.
            return (a, b) => dueSortValue(a) - dueSortValue(b) || byTitle(a, b);
        case 'connected':
        default:
            return (a, b) => cardConnections(b) - cardConnections(a) || byTitle(a, b);
    }
}

// Only meaningful once review.js has loaded and the log has been read
// (see the REVIEW INIT block near the end of this script) -- both are
// guaranteed by the time a reader could actually select "Due first"
// from the sort control.
export function dueSortValue(el) {
    const entry = window.Review ? Review.stateFor(el.dataset.id) : null;
    return (entry && typeof entry.due === 'number') ? entry.due : Infinity;
}

// Reordering 245 nodes is only worth doing when the order could
// actually have changed. Filtering by type or topic changes which cards
// are visible, not their relative order, so a filter click shouldn't
// pay for a re-append.
let lastSortKey = null;

export function applySort(force) {
    const grid = document.getElementById('cardGrid');
    if (!grid) return;
    const mode = effectiveSort();
    const q = state.currentQuery;
    const key = mode + ' ' + (mode === 'relevance' ? q : '');
    if (!force && key === lastSortKey) return;
    lastSortKey = key;

    const cards = Array.from(grid.querySelectorAll('.searchable-item'));
    cards.sort(comparatorFor(mode, q));
    // One reflow instead of 245: detach into a fragment, re-append once.
    const frag = document.createDocumentFragment();
    cards.forEach(c => frag.appendChild(c));
    grid.appendChild(frag);
}

export function setSort(mode) {
    if (!SORTS.includes(mode)) return;
    state.currentSort = mode;
    state.sortExplicit = true;
    applySort(true);
    updateGrid();
    syncViewToUrl();
}

// The tree is a type-grouped directory and the graph is spatial;
// neither has a meaningful linear order, so the control only applies to
// the grid.
export function updateSortControlVisibility() {
    const wrap = document.getElementById('sort-control');
    if (wrap) wrap.classList.toggle('hidden', state.currentView !== 'grid');
}

export function syncSortControl() {
    const sel = document.getElementById('sort-select');
    if (sel) sel.value = effectiveSort();
}
