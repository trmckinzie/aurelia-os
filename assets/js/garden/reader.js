/**
 * The note reader: opening and closing a note, its header, next/previous,
 * the URL hash and browser history, and the focus trap. openNote() is where
 * every note link on the page ends up, through the one [data-note] listener
 * in initReader().
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { renderBacklinks, renderRelatedByTopic } from './connections.js';
import { NODE_BY_ID } from './data.js';
import { modalBackdrop, modalContent, modalPanel, modalProgress, modalScroll } from './dom.js';
import { graphColorFor, graphTypeColors } from './graph.js';
import { getVisibleNoteIds } from './grid.js';
import { buildOutline } from './outline.js';
import { stopReading } from './read-aloud.js';
import { endReviewSession, updateSessionProgress } from './review-session.js';
import { state } from './state.js';
import { applyRecallCover, updateReviewedFooter } from './study.js';

// The element focus returns to when the reader closes. Without this,
// dismissing the dialog dropped focus onto <body> and a keyboard user
// restarted from the top of the page every time.
let modalReturnFocus = null;
/* closeModal() hides the backdrop on a 260ms timer (it has to outlast the
   exit transition). Reopening inside that window used to let the stale
   timer fire *after* the new note had already been shown, re-adding
   `hidden` and leaving the reader invisible with the page still scroll-
   locked. Back/Forward through the reading trail lands well inside 260ms,
   so this went from unlikely to routine. openNote() cancels the pending
   hide instead of racing it. */
let modalHideTimer = null;

/* Fills the reader's header from the card element's data-* attributes.

   All of it -- type, label, title, maturity, connection count -- is
   already on the <article> for the Garden's sort comparators and filter
   sweep (see engine/cards.py), so the reader needs no new build-time
   data. The title matters most: 15 gemini-notebook notes carry no <h1>
   in their body at all, and they are the longest notes in the vault, so
   before this they opened with no title shown anywhere.

   The accent is set as a CSS custom property, not a Tailwind class.
   tailwind_build.py scans the rendered HTML under dist, so a utility
   class assembled here at runtime would never be compiled and would
   silently render with no colour -- the same trap documented for the
   graph canvas, whose graphColorFor() map this reuses rather than
   duplicating. (Writing that scan path as a glob here would close this
   comment early on its star-slash -- it broke both this file and
   main.css once each.) */
export function applyNoteChrome(noteId) {
    const card = document.querySelector(`.searchable-item[data-id="${CSS.escape(noteId)}"]`);
    const node = NODE_BY_ID[noteId];
    const type = (card && card.dataset.type) || (node && node.type) || '';
    const title = (card && card.dataset.title) || (node && node.title) || '';

    const accent = graphColorFor(type, graphTypeColors(getComputedStyle(document.documentElement)),
                                 'var(--aurelia-primary)');
    modalPanel.style.setProperty('--note-accent', accent);

    const titleEl = document.getElementById('modal-title');
    if (titleEl) titleEl.textContent = title;
    const typeEl = document.getElementById('modal-type');
    // data-label is the human label cards.py already chose for this type
    // ("SOURCE", "DAILY LOG"); it is not derivable from the type slug, so
    // the fallback is the slug itself rather than a second lookup table.
    if (typeEl) typeEl.textContent = (card && card.dataset.label) || type.toUpperCase();

    const maturityEl = document.getElementById('modal-maturity');
    if (maturityEl) {
        const m = card && card.dataset.maturity;
        maturityEl.textContent = m ? `${MATURITY_EMOJI[m] || ''} ${m}`.trim() : '';
    }
    const connEl = document.getElementById('modal-connections');
    if (connEl) {
        const n = parseInt((card && card.dataset.connections) || '0', 10);
        connEl.textContent = n > 0 ? `◉ ${n} ${n === 1 ? 'LINK' : 'LINKS'}` : '';
    }
    updateSessionProgress();
}
export const MATURITY_EMOJI = { seed: '🌱', growing: '🌿', evergreen: '🌳' };

/* `history` controls how this open participates in browser history:
     'push'    -- a deliberate jump to a new note (a card, a backlink,
                  the palette). Adds an entry, so Back returns to where
                  you came from.
     'replace' -- lateral movement inside one reading session ([ and ]).
                  Stepping through 30 notes must not bury the Garden
                  under 30 entries, which is the same objection the
                  comment on syncViewToUrl() raises about per-keystroke
                  pushState.
     'none'    -- the router is reacting to a history event that already
                  happened; writing again would fight the browser. */
export function openNote(noteId, history_ = 'push') {
    const rawEl = document.getElementById(noteId);
    if (!rawEl) return;
    if (modalHideTimer) { clearTimeout(modalHideTimer); modalHideTimer = null; }
    const wasOpen = !modalBackdrop.classList.contains('hidden');
    if (!wasOpen) modalReturnFocus = document.activeElement;
    stopReading();
    const txt = document.createElement("textarea");
    txt.innerHTML = rawEl.innerHTML;
    modalContent.innerHTML = marked.parse(txt.value, { breaks: true });
    // Study mode only (applyRecallCover no-ops in Read mode). Placed
    // right after the note body is parsed in, before backlinks/related,
    // so the cover panel sits directly over the answer element it's
    // covering rather than after content inserted later.
    applyRecallCover(noteId);
    // On-page outline (Phase 4) -- headings/Gemini sections are part of
    // the static parsed body above, so this can run before backlinks/
    // related/flashcards, none of which add h2/h3 or .gemini-note-
    // section elements of their own.
    buildOutline(noteId);
    renderBacklinks(noteId);
    renderRelatedByTopic(noteId);
    // Upgrades any flashcard deck(s) this note's body just rendered
    // (see assets/js/flashcards.js) into an interactive widget. Has to
    // run on every open, not just once at page load: the body itself
    // -- decks included -- is only ever parsed in here, on demand.
    if (typeof window.upgradeFlashcardDecks === 'function') upgradeFlashcardDecks(modalContent);
    // The elaboration nudge only appears after a rating (see
    // submitRating() below) -- clear any previous note's nudge here so
    // it never lingers on a note that hasn't been rated yet.
    const elaborateEl = document.getElementById('modal-elaborate');
    if (elaborateEl) elaborateEl.innerHTML = '';
    modalScroll.scrollTop = 0;
    modalProgress.style.width = '0%';

    state.currentModalNoteId = noteId;
    applyNoteChrome(noteId);
    writeNoteToUrl(noteId, history_);
    // NODE_BY_ID is built from GRAPH_INDEX.nodes (every published note),
    // so this is a fallback for defensiveness only, not an expected path.
    announce((NODE_BY_ID[noteId] && NODE_BY_ID[noteId].title) || noteId);
    const wordCount = (modalContent.innerText || '').trim().split(/\s+/).filter(Boolean).length;
    const minutes = Math.max(1, Math.round(wordCount / 200));
    const readtimeEl = document.getElementById('modal-readtime');
    if (readtimeEl) readtimeEl.innerText = `~${minutes} min read · ${wordCount} words`;
    updateReviewedFooter(noteId);

    modalBackdrop.classList.remove('hidden');
    modalPanel.classList.remove('is-closing');
    // One frame's delay so the browser registers the closed state
    // before the open state, otherwise there is nothing to transition
    // from and the panel simply appears.
    setTimeout(() => { modalBackdrop.classList.remove('opacity-0'); modalPanel.classList.add('is-open'); }, 10);
    document.body.style.overflow = 'hidden';
    // Focus the panel itself rather than the first control: the dialog
    // is for reading, so the caret belongs at the top of the document,
    // and Escape/[/] all listen on document anyway.
    if (!wasOpen) modalPanel.focus({ preventScroll: true });
}

// Moves to the next/previous note within whatever's currently visible
// (respects the active filter/search, same pool as openRandomNote) --
// supports interleaved review sessions without closing the modal.
export function navigateNote(direction) {
    if (!state.currentModalNoteId) return;
    const ids = getVisibleNoteIds();
    if (ids.length === 0) return;
    let idx = ids.indexOf(state.currentModalNoteId);
    if (idx === -1) idx = 0;
    idx = (idx + direction + ids.length) % ids.length;
    // 'replace': one reading session stays one history entry, so Back
    // still exits to wherever you entered the reader from rather than
    // replaying every note you paged past.
    openNote(ids[idx], 'replace');
}

/* closeModal(dueToHistory) -- `true` when the router is closing us in
   response to a history event that has already happened, in which case
   touching history again would fight the browser.

   Otherwise, dismissing unwinds the *whole* reading trail in one hop
   (history.go(-depth)), so ✕ and Escape always return to the Garden
   rather than stepping back one note at a time -- Back is what steps.
   If the current entry is not ours -- someone arrived directly at
   garden.html#note-x, where we pushed nothing -- only strip the hash,
   because going back there would walk off the site entirely. */
export function closeModal(dueToHistory) {
    // Ends any active review session first, so the URL loses ?review=1
    // (via endReviewSession()'s own syncViewToUrl() call) before the
    // history navigation below runs.
    if (state.reviewSessionActive) endReviewSession();
    stopReading();
    const st = window.history.state;
    const trailDepth = (st && st.aureliaNote) ? (st.aureliaDepth || 1) : 0;
    state.currentModalNoteId = null;
    modalBackdrop.classList.add('opacity-0');
    modalPanel.classList.remove('is-open');
    modalPanel.classList.add('is-closing');
    // Matches --dur-2 (220ms) plus a little slack. setTimeout rather
    // than transitionend: if the frame loop is throttled the event
    // never fires and the backdrop would stay up, blocking the page.
    // Held in modalHideTimer so a reopen inside the window can cancel it.
    if (modalHideTimer) clearTimeout(modalHideTimer);
    modalHideTimer = setTimeout(() => {
        modalBackdrop.classList.add('hidden');
        modalPanel.classList.remove('is-closing');
        modalHideTimer = null;
    }, 260);
    document.body.style.overflow = 'auto';

    if (dueToHistory !== true) {
        if (trailDepth > 0) window.history.go(-trailDepth);
        else if (location.hash) window.history.replaceState(null, '', location.pathname + location.search);
    }
    // Return focus to whatever opened the reader (usually the card), so
    // a keyboard user resumes where they left off instead of at <body>.
    if (modalReturnFocus && document.contains(modalReturnFocus)) {
        try { modalReturnFocus.focus({ preventScroll: true }); } catch (e) { /* detached */ }
    }
    modalReturnFocus = null;
}

/* === NOTE URL / HISTORY ===========================================
   The hash has always meant "open this note" -- openNoteFromHash() and
   the command palette both rely on it -- but nothing ever *wrote* it.
   The result was that the URL never named the note you were reading (so
   it could not be linked), Back did nothing, and a stale hash survived
   closing, so a reload reopened a note you had already dismissed.

   Everything funnels through one idempotent router. Idempotency is what
   makes this safe rather than clever: traversing history across a
   fragment change can fire popstate *and* hashchange, and a router that
   no-ops when the requested note is already open cannot double-handle
   them. Our own pushState/replaceState calls fire neither event, so
   they never re-enter. */
/* Each entry we push records how deep into the reading trail it is, so
   the ✕ can unwind the whole trail in one hop while Back still steps
   through it one note at a time.

   Without the depth, closing had to be a single history.back(), which
   is right when you opened one note from the grid but wrong the moment
   you follow a backlink: closing note B would reopen note A instead of
   returning you to the Garden. Depth makes "dismiss" and "go back" two
   different distances rather than forcing them to be the same one. */
export function writeNoteToUrl(noteId, mode) {
    if (mode === 'none') return;
    const url = location.pathname + location.search + '#' + noteId;
    const current = window.history.state;
    const currentDepth = (current && current.aureliaDepth) || 0;
    if (mode === 'replace') {
        // Lateral move inside one reading session: same entry, so it
        // keeps the depth it already had (1 if we arrived by deep link,
        // where nothing was pushed and there is nothing to unwind).
        window.history.replaceState(
            { aureliaNote: noteId, aureliaDepth: currentDepth || 1 }, '', url);
    } else {
        window.history.pushState(
            { aureliaNote: noteId, aureliaDepth: currentDepth + 1 }, '', url);
    }
}

export function syncModalToLocation() {
    const id = location.hash.slice(1);
    const isOpen = !modalBackdrop.classList.contains('hidden');
    if (id && document.getElementById(id)) {
        if (state.currentModalNoteId === id && isOpen) return;   // already showing it
        openNote(id, 'none');
    } else if (isOpen) {
        closeModal(true);
    }
}

/* Focus trap. aria-modal="true" tells assistive tech that the rest of
   the page is inert, but it does not change the browser's tab order --
   measured, 20 controls behind the backdrop stayed reachable by Tab.
   A keydown trap rather than the `inert` attribute, which would need
   the page restructured into a wrapper this markup does not have. */
function trapReaderFocus(e) {
    if (e.key !== 'Tab') return;
    const focusables = [...modalPanel.querySelectorAll(
        'a[href], button:not([disabled]), select, input, textarea, [tabindex]:not([tabindex="-1"])'
    )].filter(el => el.offsetParent !== null);
    if (focusables.length === 0) return;
    const first = focusables[0], last = focusables[focusables.length - 1];
    // The panel itself holds focus right after opening; Tab from there
    // should enter the controls rather than escape to the page behind.
    if (e.shiftKey && (document.activeElement === first || document.activeElement === modalPanel)) {
        e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
    }
}

// --- RANDOM NOTE DISCOVERY ---
// Picks from whatever's currently visible (respects active filter/search),
// so "surprise me" stays scoped to what you're actually browsing.
export function openRandomNote() {
    const ids = getVisibleNoteIds();
    if (ids.length === 0) return;
    openNote(ids[Math.floor(Math.random() * ids.length)]);
}

// --- HASH DEEP-LINKING ---
// garden.html#note-id opens that note directly on load -- what the
// command palette's results, the Random Note button's URL, and the
// Lobby's hub-note links all rely on. Re-checked on hashchange
// too, so an in-page link to a different note (e.g. a backlink pill
// that also updates the URL) keeps working the same way.
// Arriving with a hash already set: open it without writing history,
// since this entry is the one the visitor landed on. closeModal() reads
// history.state to tell this case apart -- nothing was pushed here, so
// closing strips the hash rather than calling back() and leaving the site.
export function openNoteFromHash() {
    const id = location.hash.slice(1);
    if (id && document.getElementById(id)) openNote(id, 'none');
}

// Every note link the engine or this script renders -- a prose wikilink
// in the reader, a card pill, a backlink, a related note, a graph list
// row -- is a <button data-note="id">. The id is make_id() output.
function openClickedNoteLink(e) {
    const link = e.target.closest('[data-note]');
    if (link) openNote(link.dataset.note);
}

// A click on the backdrop itself closes the reader; a click inside the
// panel bubbles up here too, which is why the target is checked rather
// than propagation stopped.
function closeOnBackdropClick(e) {
    if (e.target === modalBackdrop) closeModal();
}

export function initReader() {
    // Reading-progress bar under the reader's header.
    modalScroll.addEventListener('scroll', () => {
        const max = modalScroll.scrollHeight - modalScroll.clientHeight;
        const pct = max > 0 ? (modalScroll.scrollTop / max) * 100 : 0;
        modalProgress.style.width = `${pct}%`;
    });
    // Both listeners run the same idempotent router: traversing history
    // across a fragment change can fire popstate and hashchange together,
    // and syncModalToLocation() no-ops when the requested note is already
    // open, so the pair cannot double-handle one navigation.
    window.addEventListener('popstate', syncModalToLocation);
    window.addEventListener('hashchange', syncModalToLocation);
    modalPanel.addEventListener('keydown', trapReaderFocus);
    document.addEventListener('click', openClickedNoteLink);
    modalBackdrop.addEventListener('click', closeOnBackdropClick);
}
