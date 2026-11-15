/**
 * Study mode: the recall cover over a note's answer, the rating buttons, and
 * the "last reviewed / next due" line. Scheduling itself is window.Review
 * (assets/js/review.js); this is the page wiring around it.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { renderElaboration } from './connections.js';
import { modalContent } from './dom.js';
import { advanceReviewSession, applyDueMarkers, refreshDueState } from './review-session.js';
import { state } from './state.js';

/* === SPACED REVIEW (Phase 2) ======================================
   Recall-first reader (Study mode), the elaboration nudge, and the
   SM-2 due queue -- built on window.Review (assets/js/review.js),
   which owns the localStorage log and the scheduling math. Everything
   here is page wiring: DOM, events, and the greedy-interleave ordering
   a review session walks through. */

// --- Read / Study mode ---------------------------------------------
// localStorage key aurelia_study_mode; absent means Read mode (the
// default for a first-time visitor). Switching modes re-runs the
// recall-cover pass on whatever note is currently open.
export const STUDY_MODE_KEY = 'aurelia_study_mode';
let studyMode = false;

export function initStudy() {
    try { studyMode = localStorage.getItem(STUDY_MODE_KEY) === 'study'; } catch (e) { /* Safari private mode */ }
    setStudyModeButtons();
}

export function setStudyModeButtons() {
    document.querySelectorAll('.study-toggle-btn').forEach(btn => {
        btn.setAttribute('aria-pressed', String(studyMode));
    });
}

export function toggleStudyMode() {
    studyMode = !studyMode;
    try { localStorage.setItem(STUDY_MODE_KEY, studyMode ? 'study' : 'read'); } catch (e) { /* ignore */ }
    setStudyModeButtons();
    announce(studyMode ? 'Study mode on' : 'Read mode on');
    if (state.currentModalNoteId) applyRecallCover(state.currentModalNoteId);
}

// A note's maturity only ever lives on its card's data-maturity
// attribute (GRAPH_INDEX carries no maturity field -- see
// engine/pipeline.py._build_graph_index), so every maturity lookup in
// this section, including the v1 migration below, goes through this.
export function noteMaturity(noteId) {
    const card = document.querySelector(`.searchable-item[data-id="${CSS.escape(noteId)}"]`);
    return (card && card.dataset.maturity) || '';
}

// --- Recall cover (Study mode) --------------------------------------
// Anchors a note's "answer" element and hides it behind a cover panel
// until the reader chooses to reveal it -- practice testing instead of
// recognition. No match found -> no cover is applied, and the note is
// never blocked either way.
export const RECALL_HEADING_RE = /Definition|Core Argument|Thesis|Profile & Context/i;

export function findRecallAnchor() {
    // Concept/Source/Discipline/Author: an <h3> whose text matches the
    // pattern above, immediately followed by a <blockquote> -- the
    // extractor's actual rendered shape for these fields (see
    // engine/extractors.py and engine/cards.py). Case-insensitive: the
    // heading text convention is consistent in practice, but nothing
    // about matching it should hinge on capitalization no reader can see.
    const headings = modalContent.querySelectorAll('h3');
    for (const h of headings) {
        if (!RECALL_HEADING_RE.test(h.textContent || '')) continue;
        const sib = h.nextElementSibling;
        if (sib && sib.tagName === 'BLOCKQUOTE') return { answer: sib };
    }
    // Deep dives: the first <p> whose ONLY child node is an <em> -- the
    // dek/premise line convention documented in TPL_Deep_Dive.md's own
    // HTML-comment contract (see docs/ARCHITECTURE.md, "Content model").
    const paragraphs = modalContent.querySelectorAll('p');
    for (const p of paragraphs) {
        if (p.childNodes.length === 1 && p.firstElementChild && p.firstElementChild.tagName === 'EM') {
            return { answer: p };
        }
    }
    return null;
}

export function removeRecallCover() {
    const existingCover = modalContent.querySelector('.recall-cover');
    if (existingCover) existingCover.remove();
    const existingRow = modalContent.querySelector('.rate-row');
    if (existingRow) existingRow.remove();
    modalContent.querySelectorAll('[data-recall-hidden]').forEach(el => {
        el.hidden = false;
        el.removeAttribute('data-recall-hidden');
    });
}

export function applyRecallCover(noteId) {
    // Always starts clean: called both on every openNote() and on every
    // mode toggle, and a stale cover/rate-row from whatever was on
    // screen before must never persist into the new state.
    removeRecallCover();
    if (!studyMode) return;
    const anchor = findRecallAnchor();
    if (!anchor) return;

    const cover = document.createElement('div');
    cover.className = 'recall-cover';
    cover.innerHTML = `
        <p>Try to recall it first.</p>
        <button type="button" class="rate-btn recall-reveal-btn">Reveal</button>
    `;
    anchor.answer.hidden = true;
    anchor.answer.setAttribute('data-recall-hidden', '1');
    anchor.answer.before(cover);

    const revealBtn = cover.querySelector('.recall-reveal-btn');
    const reveal = () => revealAnswer(noteId, anchor, cover);
    revealBtn.addEventListener('click', reveal);
    // Space/Enter when the Reveal button itself has focus. The global
    // keydown handler already ignores typing targets and this button
    // isn't one, so no extra guard is needed here.
    revealBtn.addEventListener('keydown', (e) => {
        if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); reveal(); }
    });
}

export const RATE_BUTTONS = [
    { grade: 1, label: 'Again', key: '1' },
    { grade: 2, label: 'Hard', key: '2' },
    { grade: 3, label: 'Good', key: '3' },
    { grade: 4, label: 'Easy', key: '4' }
];

// Builds (or rebuilds) the four Again/Hard/Good/Easy buttons inside
// `row`. Split out from revealAnswer() so "Change rating" (see
// changeRating() below) can restore the same markup without duplicating
// it -- innerHTML replacement means any previously-bound listeners are
// gone, so every call site pairs this with wireRateButtons().
export function renderRateButtons(row) {
    row.innerHTML = `
        <p class="field-label text-aurelia-muted w-full">How well did you remember it?</p>
        ${RATE_BUTTONS.map(r => `
            <button type="button" class="rate-btn" data-grade="${r.grade}">
                <span>${r.label}</span>
                <span class="rate-key" aria-hidden="true">${r.key}</span>
            </button>
        `).join('')}
    `;
}

export function wireRateButtons(row, noteId) {
    row.querySelectorAll('button[data-grade]').forEach(btn => {
        btn.addEventListener('click', () => submitRating(noteId, parseInt(btn.dataset.grade, 10), row));
    });
}

export function revealAnswer(noteId, anchor, cover) {
    anchor.answer.hidden = false;
    anchor.answer.removeAttribute('data-recall-hidden');
    cover.remove();

    const row = document.createElement('div');
    row.className = 'rate-row';
    row.setAttribute('role', 'group');
    row.setAttribute('aria-label', 'How well did you remember it?');
    renderRateButtons(row);
    anchor.answer.after(row);
    wireRateButtons(row, noteId);
    row.querySelector('button[data-grade]').focus({ preventScroll: true });
}

// Confirmation line shown in place of the rating row once a grade has
// been submitted (outside an active review session -- see
// submitRating() below). tabindex="-1" on the <p> (set here, not in
// CSS) is what lets it be focused: the button the reader just clicked
// is gone, replaced by this element, so focus has to be moved onto
// something inside the reader or it falls out to <body>.
export function showRateConfirmation(row, noteId, grade) {
    const label = (RATE_BUTTONS.find(r => r.grade === grade) || {}).label || '';
    const entry = window.Review ? Review.stateFor(noteId) : null;
    const duePhrase = entry ? nextDuePhrase(entry) : '';
    row.innerHTML = `
        <p class="rate-confirm" tabindex="-1">Rated ${label}${duePhrase ? ' · ' + duePhrase : ''}
            <button type="button" class="rate-change-btn">Change rating</button>
        </p>
    `;
    const confirmEl = row.querySelector('.rate-confirm');
    const changeBtn = row.querySelector('.rate-change-btn');
    if (changeBtn) changeBtn.addEventListener('click', () => changeRating(row, noteId));
    if (confirmEl) confirmEl.focus({ preventScroll: true });
}

// "Change rating": restores the SM-2 log entry to exactly what it was
// before the rating this row is currently confirming (see the snapshot
// taken in submitRating() below, via Review.restore() in review.js),
// then shows the four buttons again. Restoring first is what makes a
// second rate() call safe -- it runs from the same clean pre-rating
// state the first click did, rather than compounding onto the already-
// rated entry, so the SM-2 log never double-counts one recall attempt.
export function changeRating(row, noteId) {
    if (window.Review && typeof Review.restore === 'function') {
        Review.restore(noteId, row._preRatingSnapshot || null);
    }
    delete row._preRatingSnapshot;
    updateReviewedFooter(noteId);
    refreshDueState();
    applyDueMarkers();
    renderRateButtons(row);
    wireRateButtons(row, noteId);
    const firstBtn = row.querySelector('button[data-grade]');
    if (firstBtn) firstBtn.focus({ preventScroll: true });
}

export function submitRating(noteId, grade, row) {
    if (!window.Review) return;
    // Snapshot BEFORE rating -- this is the state "Change rating" (see
    // changeRating() above) restores if the reader wants a do-over. A
    // shallow copy: rate() below assigns a brand-new object into the
    // log rather than mutating this one in place, so the copy is
    // belt-and-braces rather than strictly required.
    const priorState = Review.stateFor(noteId);
    const snapshot = priorState ? Object.assign({}, priorState) : null;
    Review.rate(noteId, grade, noteMaturity(noteId));
    updateReviewedFooter(noteId);
    refreshDueState();
    applyDueMarkers();
    renderElaboration(noteId);

    if (state.reviewSessionActive) {
        advanceReviewSession(noteId);
        return;
    }
    // Not in a session: nothing to advance to. Replace the rating row
    // with a confirmation line rather than leaving it inert or removing
    // it out from under the reader (see fix #1/#2 -- this is also what
    // keeps keyboard focus inside the reader instead of falling out to
    // <body>).
    if (row) {
        row._preRatingSnapshot = snapshot;
        showRateConfirmation(row, noteId, grade);
    }
}

// --- "Last reviewed / next due" footer ------------------------------
export const DAY_MS = 24 * 60 * 60 * 1000;

export function relativeDayPhrase(deltaMs, direction) {
    const days = Math.round(Math.abs(deltaMs) / DAY_MS);
    if (days === 0) return 'today';
    return direction === 'ago' ? `${days} day${days === 1 ? '' : 's'} ago` : `in ${days} day${days === 1 ? '' : 's'}`;
}

// Shared by #modal-reviewed (updateReviewedFooter, below) and the
// post-rating confirmation line (showRateConfirmation, above) -- one
// place computing "next due", not two copies of the same date math.
export function nextDuePhrase(entry, now = Date.now()) {
    return `next due ${entry.due <= now ? 'now' : relativeDayPhrase(entry.due - now, 'in')}`;
}

export function updateReviewedFooter(noteId) {
    const el = document.getElementById('modal-reviewed');
    if (!el || !window.Review) return;
    const entry = Review.stateFor(noteId);
    if (!entry) { el.textContent = 'Never reviewed'; return; }
    const lastPhrase = relativeDayPhrase(Date.now() - entry.last, 'ago');
    el.textContent = `Last reviewed ${lastPhrase} · ${nextDuePhrase(entry)}`;
}
