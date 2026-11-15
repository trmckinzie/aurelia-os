/**
 * Copying a link: the toolbar's Share View chip and the reader's copy-link
 * button.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { state } from './state.js';

/* Copies `text`, resolving to whether it worked. Two mechanisms, because
   the modern one is refused more often than you'd expect:
   navigator.clipboard needs a secure context (file:// and plain http on
   a LAN address don't qualify) and can also be denied outright by
   permissions policy even on https. The legacy execCommand path works
   in several of those cases, so it's a real fallback rather than a
   formality.

   Shared by the toolbar's Share View chip and the reader's copy-link
   button: same two failure modes, so the same two mechanisms, written
   once. Feedback is left to the caller, since a text chip and a 34px
   icon button can't report success the same way. */
export function writeToClipboard(text) {
    const legacyCopy = () => {
        try {
            const ta = document.createElement('textarea');
            ta.value = text;
            // Keep it off-screen but focusable; display:none can't be selected.
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.top = '-1000px';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(ta);
            return ok;
        } catch (e) {
            return false;
        }
    };
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text).then(() => true, () => legacyCopy());
    }
    return Promise.resolve(legacyCopy());
}

// The button's markup is stashed rather than its text: the label used to
// be restored with textContent, which turned the icon + label spans into
// one text node -- with an emoji that merely flattened the markup, but the
// icon is an inline SVG now and textContent would delete it outright, so
// the first copy left a permanently blank button.
let shareButtonMarkup = null;
export function copyViewLink() {
    const btn = document.getElementById('btn-share');
    const done = (msg) => {
        if (!btn) return;
        if (shareButtonMarkup === null) shareButtonMarkup = btn.innerHTML;
        btn.textContent = msg;
        setTimeout(() => { btn.innerHTML = shareButtonMarkup; }, 1600);
    };
    // If both paths fail the URL is still in the address bar, so say
    // what to do rather than reporting a failure the reader can't act on.
    writeToClipboard(location.href).then(ok => done(ok ? 'Copied' : 'Copy from the address bar'));
}

// Copies a link to the note being read -- which only became a real link
// once openNote() started writing the hash. Shares writeToClipboard()
// with the toolbar's Share View chip rather than reimplementing its
// fallback, but reports the result as an icon swap, since this control
// is a 34px square with no room for a text label.
export const COPY_ICON = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 010 5.656l-3 3a4 4 0 01-5.656-5.656l1.5-1.5M10.172 13.828a4 4 0 010-5.656l3-3a4 4 0 015.656 5.656l-1.5 1.5"></path>';
export const OK_ICON = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>';
export const FAIL_ICON = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"></path>';

export function copyNoteLink() {
    if (!state.currentModalNoteId) return;
    const btn = document.getElementById('btn-copy-note');
    const paint = (path, label) => {
        if (!btn) return;
        btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`;
        btn.setAttribute('title', label);
    };
    writeToClipboard(location.href).then(ok => {
        // If the copy was refused the URL is still in the address bar,
        // so the tooltip says what to do instead of only reporting failure.
        paint(ok ? OK_ICON : FAIL_ICON, ok ? 'Link copied' : 'Copy failed — press ⌘C to copy the address bar');
        setTimeout(() => paint(COPY_ICON, 'Copy link to this note'), 1600);
    });
}
