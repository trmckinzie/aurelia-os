/**
 * The keyboard-shortcuts sheet and the page's global key handler.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { modalBackdrop, modalContent, shortcutSheet } from './dom.js';
import { toggleReading } from './read-aloud.js';
import { closeModal, navigateNote } from './reader.js';
import { toggleStudyMode } from './study.js';

/* === KEYBOARD-SHORTCUTS SHEET (Phase 4) ============================
   showModal() gives #shortcut-sheet a free focus trap and native
   Escape handling (see the guard at the top of the global keydown
   handler below), and being a real <dialog> it also makes the rest of
   the page -- an open note reader included -- inert while it's shown,
   with no coordination needed against that reader's own markup. */
let shortcutSheetReturnFocus = null;

export function openShortcutSheet() {
    shortcutSheetReturnFocus = document.activeElement;
    shortcutSheet.showModal();
    // Not the Close button: the heading is what a screen reader should
    // announce first, matching how openNote() focuses the panel (whose
    // content) rather than a control inside it.
    const title = document.getElementById('shortcut-sheet-title');
    if (title) title.focus();
}

export function closeShortcutSheet() {
    shortcutSheet.close();
}

// Fires on every close path alike -- Esc, the Close button, or a
// programmatic .close() -- so focus returns to whatever opened the
// sheet (the toolbar button or wherever '?' was pressed) exactly once,
// regardless of how it was dismissed. The '?' key path usually leaves
// document.activeElement on <body> (nothing was focused when it was
// pressed) -- body.focus() is a silent no-op, so that case and any
// element that's gone missing since open both fall back to the
// toolbar button rather than dropping focus on the floor.
function restoreShortcutSheetFocus() {
    const target = (shortcutSheetReturnFocus
        && shortcutSheetReturnFocus !== document.body
        && typeof shortcutSheetReturnFocus.focus === 'function'
        && document.contains(shortcutSheetReturnFocus))
        ? shortcutSheetReturnFocus
        : document.getElementById('btn-shortcuts');
    if (target && typeof target.focus === 'function') target.focus();
    shortcutSheetReturnFocus = null;
}

function handleGlobalKeydown(e) {
    // While any dialog is open (the shortcut sheet, the search palette),
    // it and the browser's native Escape/focus-trap handling own all
    // keyboard input (see openShortcutSheet() below) -- nothing here
    // should also react, e.g. '[' navigating a note reader that happens
    // to be open underneath, or this handler's own Escape branch below
    // fighting the dialog's native close.
    if (document.querySelector('dialog[open]')) return;

    // '?' and '/' work anywhere on the page, not gated on the note
    // reader being open -- they're entry points into "how do I use
    // this" and "find a note", not reading controls, so they sit above
    // the modal-open guard below rather than inside it.
    if (e.key === '?' && !isTypingTarget(e)) { e.preventDefault(); openShortcutSheet(); return; }
    if (e.key === '/' && !isTypingTarget(e)) {
        // Only when the note reader isn't open: moving focus to the
        // search box behind an aria-modal dialog would break its focus
        // trap (the reader has no visible search field of its own).
        if (modalBackdrop.classList.contains('hidden')) {
            e.preventDefault();
            const input = document.getElementById('searchInput');
            if (input) input.focus();
        }
        return;
    }
    // Read/Study mode toggle -- same global reach as '?'/'/' above.
    // toggleStudyMode() already re-runs the recall-cover pass on
    // whatever note is open, so this is safe whether or not the
    // reader is currently open.
    if (e.key === 's' && !isTypingTarget(e)) { toggleStudyMode(); return; }

    // The open-check has to gate Escape too, not just the reading keys.
    // closeModal() now moves history (see its comment), and this handler
    // fires on every Escape anywhere on the page -- so dismissing the
    // command palette with a note id sitting in the URL used to run the
    // reader's close path and navigate the browser backwards. Escape
    // belongs to whatever is actually open.
    if (modalBackdrop.classList.contains('hidden')) return;
    if (e.key === 'Escape') { closeModal(); return; }
    // The reading/navigation keys below are plain letters and brackets,
    // not modified combos -- indistinguishable from ordinary typing if
    // focus happens to be in a field inside the modal (the modal has
    // none today, but Phase 2's rating keys and future controls will).
    // Escape is deliberately exempt: it's never text input, and closing
    // the reader out from under a focused field is the expected move.
    if (isTypingTarget(e)) return;
    if (e.key === ']') navigateNote(1);
    if (e.key === '[') navigateNote(-1);
    if (e.key === 'r' || e.key === 'R') toggleReading();
    // Rating shortcuts (Again/Hard/Good/Easy), only meaningful once the
    // rating row exists (after Reveal) -- see revealAnswer() below.
    // isTypingTarget above already excludes text fields; there are
    // none in this modal today, but a stray keypress while, say, a
    // search box elsewhere on the page happens to hold focus should
    // never rate a note the reader can't currently see the buttons for.
    if (['1', '2', '3', '4'].includes(e.key)) {
        const row = modalContent.querySelector('.rate-row');
        if (row) {
            const btn = row.querySelector(`button[data-grade="${e.key}"]`);
            if (btn && !btn.disabled) { e.preventDefault(); btn.click(); }
        }
    }
}

export function initKeyboard() {
    shortcutSheet.addEventListener('close', restoreShortcutSheetFocus);
    document.addEventListener('keydown', handleGlobalKeydown);
}
