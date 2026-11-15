/**
 * The reader's "On this page" outline.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { NODE_BY_ID } from './data.js';
import { modalContent, modalScroll } from './dom.js';

/* === ON-PAGE OUTLINE (Phase 4) =====================================
   h2/h3 headings for a normal note, or each Gemini Notebook section's
   own .gemini-note-summary text (wrap_gemini_notebook_sections in
   engine/content.py) for a gemini-notebook note -- real ones run to
   15+ sections, and note-psyc-414-1-cognitive-psychology has 20.
   Shown only once a note actually needs one (>= 4 entries); populates
   both #modal-outline (sticky sidebar, xl and up) and
   #modal-outline-mobile (collapsed <details>, below xl) with the same
   generated list, since only one of the two is ever visible at a given
   width -- see the CSS in assets/css/main.css for which. */
export function outlineEntryText(headingEl) {
    // Strips the folder-arrow glyph (▶, added by
    // wrap_gemini_notebook_sections) rather than assuming it's always
    // the very first character -- robust to whatever whitespace/markup
    // surrounds it -- and, separately, a leading emoji/pictograph
    // authors prefix a heading with by hand ("📚 Chapter 2 - Brain &
    // Cognition"). Both are visual signposts inside the note body, not
    // label text the outline strip should repeat verbatim, so both
    // branches of buildOutline() (Gemini section summaries and plain
    // h2/h3 headings) route through this one function.
    const clone = headingEl.cloneNode(true);
    clone.querySelectorAll('.folder-arrow').forEach((el) => el.remove());
    // U+FE0F (variation selector-16) and U+200D (zero-width joiner)
    // ride alongside \p{Extended_Pictographic} so a multi-codepoint
    // emoji (e.g. one joined to a modifier) is stripped whole instead
    // of leaving a stray joiner or selector behind as visible junk.
    const EMOJI_PREFIX = /^(?:[\p{Extended_Pictographic}\uFE0F\u200D])+\s*/u;
    return clone.textContent.trim().replace(EMOJI_PREFIX, '').trim();
}

export function buildOutline(noteId) {
    const sidebar = document.getElementById('modal-outline');
    const mobile = document.getElementById('modal-outline-mobile');
    if (!sidebar || !mobile) return;

    sidebar.innerHTML = '';
    mobile.innerHTML = '';
    sidebar.classList.add('hidden');
    mobile.classList.add('hidden');

    const node = NODE_BY_ID[noteId];
    const isGemini = !!node && node.type === 'gemini-notebook';
    const entries = isGemini
        ? [...modalContent.querySelectorAll('.gemini-note-summary')].map((summary) => ({
            el: summary.closest('details'),
            text: outlineEntryText(summary),
        })).filter((entry) => entry.el)
        : [...modalContent.querySelectorAll('h2, h3')].map((el) => ({ el, text: outlineEntryText(el) }));

    if (entries.length < 4) return;

    entries.forEach((entry, i) => { entry.el.id = `outline-${i + 1}`; });

    const listHtml = `<ol class="modal-outline-list">${entries.map((entry) => `
        <li><button type="button" class="modal-outline-link" data-outline-target="${entry.el.id}">${escapeHtml(entry.text)}</button></li>
    `).join('')}</ol>`;

    const actionsHtml = isGemini ? `
        <div class="modal-outline-actions">
            <button type="button" class="modal-outline-action" data-action="setAllGeminiSections" data-open="true">Expand all</button>
            <button type="button" class="modal-outline-action" data-action="setAllGeminiSections" data-open="false">Collapse all</button>
        </div>` : '';

    sidebar.innerHTML = `<p class="field-label modal-outline-heading">On this page</p>${actionsHtml}${listHtml}`;
    sidebar.classList.remove('hidden');

    mobile.innerHTML = `<summary class="modal-outline-summary field-label">On this page</summary>
        <div class="modal-outline-mobile-body">${actionsHtml}${listHtml}</div>`;
    mobile.classList.remove('hidden');
}

// "Expand all / Collapse all" in the outline's own actions row, only
// rendered for a gemini-notebook note.
export function setAllGeminiSections(open) {
    modalContent.querySelectorAll('.gemini-note-section').forEach((d) => { d.open = open; });
}

export function initOutline() {
    // Delegated on both render targets -- their contents are rebuilt on
    // every openNote(), so binding to the (stable) container once here
    // avoids re-attaching a listener per rebuild.
    ['modal-outline', 'modal-outline-mobile'].forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('click', (e) => {
            const btn = e.target.closest('.modal-outline-link');
            if (!btn) return;
            const target = document.getElementById(btn.dataset.outlineTarget);
            if (!target) return;
            // Gemini sections start collapsed except the first -- clicking
            // an entry for a collapsed one must open it before scrolling,
            // or the heading being scrolled to has zero height.
            if (target.tagName === 'DETAILS') target.open = true;
            // el.offsetTop is relative to #modal-scroll specifically (see
            // the `#modal-scroll { position: relative; }` rule in
            // assets/css/main.css and its comment) -- without that, this
            // would be relative to #modal-panel two levels up instead, and
            // overshoot every scroll by the header strip's height.
            modalScroll.scrollTo({
                top: target.offsetTop - 16,
                behavior: aureliaMotionOff() ? 'auto' : 'smooth',
            });
        });
    });
}
