/**
 * The due queue: grid markers and the due count, a review session's
 * interleaved order and progress, and progress export and import.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { sharedTopicCount } from './connections.js';
import { NODE_BY_ID } from './data.js';
import { modalContent } from './dom.js';
import { getVisibleNoteIds } from './grid.js';
import { openNote } from './reader.js';
import { state } from './state.js';
import { updateReviewedFooter } from './study.js';
import { syncViewToUrl } from './url-state.js';

// --- Due state (grid markers, due count, "Start review") -------------
// dueIdSet is rebuilt once per updateGrid() sweep (see its own "6. DUE
// MARKERS" step) -- never once per card. Review.dueIds() itself only
// touches localStorage on the very first call on this page (the log is
// cached in review.js's module state after that), so this is cheap on
// every subsequent keystroke.
let dueIdSet = new Set();

export function refreshDueState() {
    if (!window.Review) return;
    const allIds = Array.from(document.querySelectorAll('.searchable-item')).map(el => el.dataset.id);
    dueIdSet = new Set(Review.dueIds(allIds));

    const dueCountEl = document.getElementById('due-count');
    if (dueCountEl) dueCountEl.textContent = dueIdSet.size;

    const startBtn = document.getElementById('btn-start-review');
    if (startBtn) {
        startBtn.disabled = dueIdSet.size === 0;
        startBtn.title = dueIdSet.size === 0
            ? 'No notes are due for review yet. Rate a note in Study mode to add it to the queue.'
            : `Start a review session for ${dueIdSet.size} due note${dueIdSet.size === 1 ? '' : 's'}`;
    }
}

export function applyDueMarkers() {
    document.querySelectorAll('.searchable-item').forEach(el => {
        el.classList.toggle('is-due', dueIdSet.has(el.dataset.id));
    });
}

// --- Review session (queue, greedy interleave, auto-advance) ---------
// Snapshot of the queue's starting length, taken once when a session
// begins (startReviewSession()) or is recomputed on reload
// (restoreViewFromUrl()). state.reviewQueue itself shrinks as notes are
// rated, so this is what lets updateSessionProgress() below say
// "Reviewing 2 of 5" rather than only knowing how many are left.

// "Reviewing N of M" in the modal header strip (#modal-session, next to
// #modal-connections) -- visible only while a session is active. Called
// from applyNoteChrome() on every openNote() (so it's always current
// for whatever note is on screen) and from endReviewSession() (so it
// hides immediately when a session ends without opening a new note --
// see showSessionComplete() below).
export function updateSessionProgress() {
    const el = document.getElementById('modal-session');
    if (!el) return;
    if (!state.reviewSessionActive) {
        el.textContent = '';
        el.classList.add('hidden');
        return;
    }
    const position = state.reviewSessionTotal - state.reviewQueue.length + 1;
    el.textContent = `Reviewing ${position} of ${state.reviewSessionTotal}`;
    el.classList.remove('hidden');
}

// Replaces the rating row (and clears the elaboration nudge) with a
// visible "Session complete" line and a Back to the Garden button, once
// the last due note in a session has been rated and there's nothing
// left to advance to (see advanceReviewSession() below). Reuses
// .rate-row/.rate-confirm rather than a new component -- this is the
// same confirmation-line shape submitRating() already uses, just with
// different copy and a different action.
export function showSessionComplete(count) {
    let row = modalContent.querySelector('.rate-row');
    if (!row) {
        row = document.createElement('div');
        row.className = 'rate-row';
        modalContent.appendChild(row);
    }
    const elaborateEl = document.getElementById('modal-elaborate');
    if (elaborateEl) elaborateEl.innerHTML = '';
    row.innerHTML = `
        <p class="rate-confirm" tabindex="-1">Session complete: ${count} note${count === 1 ? '' : 's'} reviewed.
            <button type="button" class="rate-change-btn" data-action="closeModal">Back to the Garden</button>
        </p>
    `;
    const confirmEl = row.querySelector('.rate-confirm');
    if (confirmEl) confirmEl.focus({ preventScroll: true });
}

export function noteType(id) {
    const card = document.querySelector(`.searchable-item[data-id="${CSS.escape(id)}"]`);
    if (card) return (card.dataset.type || '').toLowerCase();
    const node = NODE_BY_ID[id];
    return node ? (node.type || '').toLowerCase() : '';
}

/* Greedy interleave: repeatedly pick, from the remaining due pool, a
   note whose type differs from the type of EACH of the last two notes
   shown (if such a note exists), tie-breaking among valid candidates by
   fewest shared topic/* tags with the immediately preceding note --
   falling back to the best-available candidate (same tie-break) when
   no candidate can satisfy the type constraint. Surfaces genuinely
   different material back-to-back rather than letting the queue run
   through, say, six concepts in a row just because six concepts
   happened to be due.

   `typeOf` maps a note id to its type. It defaults to noteType(), which
   reads the card; a unit test passes its own. */
export function buildInterleavedQueue(dueIdList, typeOf = noteType) {
    const pool = dueIdList.slice();
    const ordered = [];
    let lastTwoTypes = [];
    let previous = null;

    while (pool.length) {
        let candidates = pool.filter(id => !lastTwoTypes.includes(typeOf(id)));
        if (candidates.length === 0) candidates = pool.slice();

        candidates.sort((a, b) => {
            const sharedA = previous ? sharedTopicCount(previous, a) : 0;
            const sharedB = previous ? sharedTopicCount(previous, b) : 0;
            return sharedA - sharedB;
        });

        const chosen = candidates[0];
        ordered.push(chosen);
        pool.splice(pool.indexOf(chosen), 1);
        lastTwoTypes = [typeOf(chosen), lastTwoTypes[0]].filter(Boolean).slice(0, 2);
        previous = chosen;
    }
    return ordered;
}

export function startReviewSession() {
    if (!window.Review) return;
    const visible = getVisibleNoteIds();
    const candidates = visible.length
        ? visible
        : Array.from(document.querySelectorAll('.searchable-item')).map(el => el.dataset.id);
    const due = Review.dueIds(candidates);
    if (due.length === 0) return;
    state.reviewQueue = buildInterleavedQueue(due);
    state.reviewSessionTotal = state.reviewQueue.length;
    state.reviewSessionActive = true;
    syncViewToUrl();
    openNote(state.reviewQueue[0], 'push');
}

export function endReviewSession() {
    if (!state.reviewSessionActive) return;
    state.reviewSessionActive = false;
    state.reviewQueue = [];
    syncViewToUrl();
    updateSessionProgress();
}

// Called after a rating is submitted, when a session is active: drops
// the just-rated note from the queue and opens the next one.
// 'replace' mirrors navigateNote's own reasoning (see its comment
// above) -- stepping through an entire session stays ONE history
// entry, not one per note.
export function advanceReviewSession(justRatedId) {
    state.reviewQueue = state.reviewQueue.filter(id => id !== justRatedId);
    if (state.reviewQueue.length === 0) {
        const reviewedCount = state.reviewSessionTotal;
        endReviewSession();
        showSessionComplete(reviewedCount);
        announce('Review session complete');
        return;
    }
    openNote(state.reviewQueue[0], 'replace');
    // openNote() only moves focus into the panel when the modal was
    // previously closed (see its own comment) -- here it's already
    // open, so focus has to be moved explicitly or a keyboard user is
    // left on the just-removed rating button (about to be detached)
    // with nowhere to land but <body>. One frame so the new note's
    // recall cover (built by applyRecallCover, called from openNote)
    // exists to focus into.
    requestAnimationFrame(() => {
        const revealBtn = modalContent.querySelector('.recall-reveal-btn');
        if (revealBtn) revealBtn.focus({ preventScroll: true });
    });
}

// --- Progress panel (export / import) ---------------------------------
export function exportReviewProgress() {
    if (!window.Review) return;
    const blob = new Blob([JSON.stringify(Review.export(), null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `garden-progress-${today}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function importReviewProgress(file) {
    const resultEl = document.getElementById('progress-panel-result');
    if (!file || !window.Review) return;
    const reader = new FileReader();
    reader.onload = () => {
        let data;
        try {
            data = JSON.parse(reader.result);
        } catch (e) {
            if (resultEl) resultEl.textContent = 'That file is not valid JSON.';
            return;
        }
        const result = Review.import(data);
        if (!result.ok) {
            if (resultEl) resultEl.textContent = result.error;
            return;
        }
        if (resultEl) {
            resultEl.textContent = `Imported — kept whichever review was more recent for each note (${result.merged} updated).`;
        }
        refreshDueState();
        applyDueMarkers();
        if (state.currentModalNoteId) updateReviewedFooter(state.currentModalNoteId);
    };
    reader.onerror = () => { if (resultEl) resultEl.textContent = 'Could not read that file.'; };
    reader.readAsText(file);
}
