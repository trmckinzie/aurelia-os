/**
 * The view's state in the query string, so a filtered view can be linked,
 * bookmarked and restored.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { setFilter, updateGrid } from './grid.js';
import { buildInterleavedQueue } from './review-session.js';
import { DEFAULT_SORT, SORTS } from './sorting.js';
import { state } from './state.js';
import { renderTopicCloud, updateTopicActiveLabel } from './topics.js';
import { switchView } from './views.js';

/* === SHAREABLE VIEW STATE ==========================================
   Filter, search, topic and view mode live in the query string, so a
   particular slice of the Garden -- "concepts about memory, as a graph"
   -- can be linked, bookmarked, or reopened where you left it. None of
   that state survived a reload before; it existed only in memory.

   Query string for the view, hash for the open note. They are
   deliberately separate: the hash already means "open this note"
   (openNoteFromHash above), so ?q=memory#note-working-memory restores a
   filtered view *and* reopens the note, and neither feature has to know
   about the other.

   replaceState, not pushState. Search runs on every keystroke, so
   pushState would add a history entry per character and bury the page
   you arrived from under a dozen near-identical URLs. The tradeoff is
   that Back leaves the Garden rather than undoing the last filter --
   which is what it did before this change too, so nothing regresses.

   `state.restoring` suppresses updateGrid() while state is being applied:
   each setter normally triggers a full pass over 245 cards, and restore
   calls several in a row. One pass at the end is enough. */

// The view as a query string ("" for the default view, with no leading "?").
export function viewQueryString() {
    const params = new URLSearchParams();
    if (state.currentQuery) params.set('q', state.currentQuery);
    if (state.currentType && state.currentType !== 'all') params.set('type', state.currentType);
    if (state.currentTopic) params.set('topic', state.currentTopic);
    if (state.currentView && state.currentView !== 'grid') params.set('view', state.currentView);
    // Only an explicit choice is worth carrying: auto-relevance is
    // derived from the query, so recording it would pin the sort for
    // whoever opens the link and stop it adapting to their search.
    if (state.sortExplicit && state.currentSort !== DEFAULT_SORT) params.set('sort', state.currentSort);
    // A review session is in-memory state, not localStorage (see
    // startReviewSession()) -- this is the only record of "a session
    // was active" that survives a reload, and restoreViewFromUrl()
    // recomputes the actual queue fresh from the log rather than
    // trying to restore its exact order.
    if (state.reviewSessionActive) params.set('review', '1');

    return params.toString();
}

export function syncViewToUrl() {
    if (state.restoring) return;
    const qs = viewQueryString();
    // Keep the hash: it may be holding an open note.
    history.replaceState(null, '', (qs ? '?' + qs : location.pathname) + location.hash);
}

export function restoreViewFromUrl() {
    const params = new URLSearchParams(location.search);
    if (![...params.keys()].length) return;

    state.restoring = true;
    try {
        const view = params.get('view');
        if (view === 'tree' || view === 'graph') switchView(view);

        const type = params.get('type');
        if (type) {
            // Only honour a type that actually has a filter button --
            // a hand-edited or stale ?type= would otherwise leave the
            // grid empty with every button showing inactive.
            const btn = document.querySelector(`.filter-btn[data-filter="${CSS.escape(type)}"]`);
            if (btn) setFilter(type, btn);
        }

        const topic = params.get('topic');
        if (topic) {
            state.currentTopic = topic;
            renderTopicCloud();
            updateTopicActiveLabel();
            // Reveal the cloud, otherwise the active topic is filtering
            // the grid from a panel the reader can't see.
            const cloud = document.getElementById('topic-cloud');
            if (cloud) cloud.classList.remove('hidden');
            // Opened without going through toggleTopicCloud(), so the
            // button's state has to be brought along by hand or it
            // reports "collapsed" over an open panel.
            const topicsBtn = document.getElementById('btn-topics');
            if (topicsBtn) {
                topicsBtn.setAttribute('aria-expanded', 'true');
                topicsBtn.classList.add('text-aurelia-accent');
            }
        }

        const sort = params.get('sort');
        if (sort && SORTS.includes(sort)) {
            state.currentSort = sort;
            state.sortExplicit = true;
        }

        const q = params.get('q');
        if (q) {
            const input = document.getElementById('searchInput');
            if (input) input.value = q;
            state.currentQuery = q.toLowerCase().trim();
        }

        // A review session never persists its queue -- reloading with
        // ?review=1 recomputes it fresh from the log (see "Review queue
        // and sessions" in docs/ARCHITECTURE.md), rather than
        // trying to restore exact queue order across a reload. Doesn't
        // force-navigate: if the URL also carries a note hash (the
        // normal case mid-session), openNoteFromHash() opens it
        // separately once init finishes.
        if (window.Review && params.get('review') === '1') {
            state.reviewSessionActive = true;
            const allIds = Array.from(document.querySelectorAll('.searchable-item')).map(el => el.dataset.id);
            state.reviewQueue = buildInterleavedQueue(Review.dueIds(allIds));
            state.reviewSessionTotal = state.reviewQueue.length;
        }
    } finally {
        state.restoring = false;
    }
    updateGrid();
}
