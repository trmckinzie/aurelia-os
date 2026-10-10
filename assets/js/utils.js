/**
 * AURELIA // SHARED CLIENT UTILITIES
 * Loaded early in <head> (see base.html) so it's available to every page's
 * own inline scripts regardless of block ordering.
 */

// Vault note titles/tags/references end up interpolated into innerHTML
// strings in a few places (command palette, note modal backlinks/related
// lists). Escape them first so a stray "<" in a note can't be read as a tag.
function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

/**
 * Escapes a string for literal use inside a RegExp.
 *
 * The Garden's search highlighter builds `new RegExp()` from whatever is
 * typed into the search box. Without this, an ordinary query containing a
 * regex metacharacter -- `System 1 (fast)`, `arrays[0]`, `a+b` -- throws a
 * SyntaxError. That is not a cosmetic failure: the highlighter runs inside
 * updateGrid()'s per-card loop, so the throw aborts filtering partway and
 * leaves the grid showing a stale set of cards under a count that no longer
 * matches them.
 */
function escapeRegExp(str) {
    return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * True when entrance animations should be skipped entirely: the user asked
 * for reduced motion, or the Motion library isn't available (CDN blocked,
 * offline, blocker extension). Callers should render their normal static
 * state in that case -- never a hidden one.
 */
function aureliaMotionOff() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches || !window.Motion;
}

/**
 * Runs a fade/slide entrance on `el` that CANNOT strand it invisible.
 *
 * The hazard this exists for: an entrance built as `opacity: [0, 1]` makes
 * the animation the only thing that ever makes the element visible. If the
 * frame loop stalls -- a tab opened in the background, a restored session,
 * an embedded view that isn't compositing -- a WAAPI animation freezes
 * mid-flight and the element stays at whatever opacity it had reached,
 * sometimes 0, permanently. Observed directly: animations reporting
 * playState "running" with a currentTime frozen at ~70ms while
 * document.visibilityState still claimed "visible", so `document.hidden`
 * is not a usable guard either.
 *
 * setTimeout keeps firing when requestAnimationFrame does not, so it is the
 * reliable way to guarantee the end state. The animation stays a pure
 * flourish: if any part of it fails, the element simply appears.
 */
function aureliaReveal(el, options) {
    const opts = options || {};
    if (aureliaMotionOff()) return;

    const anim = window.Motion.animate(el,
        { opacity: [0, 1], transform: ['translateY(' + (opts.y || 16) + 'px)', 'translateY(0px)'] },
        { duration: opts.duration || 0.45, delay: opts.delay || 0, easing: 'ease-out' });

    const settle = function () {
        try { anim.cancel(); } catch (e) { /* already finished */ }
        el.style.opacity = '';
        el.style.transform = '';
    };
    if (anim && anim.finished) anim.finished.then(settle).catch(settle);
    // Safety net, deliberately longer than duration + delay.
    setTimeout(settle, ((opts.duration || 0.45) + (opts.delay || 0)) * 1000 + 700);
}


/* === DELEGATED ACTIONS (backlog B02) ====================================
   No page carries an inline event handler (onclick="..." and friends): a
   Content-Security-Policy without 'unsafe-inline' refuses them, and they
   also mean note-derived text would have to be interpolated into JS source
   to be acted on. Instead an element names its action in a data attribute
   and one listener per event type, here on the document, dispatches to a
   function the page registered:

       <button data-action="setFilter" data-filter="concept">
       <select data-change="setSort">      <input data-input="handleSearch">

       registerActions({ setFilter: (el) => setFilter(el.dataset.filter, el) });

   The handler receives the element (so it can read its other data-*
   attributes, value or files) and the event. Pages register their maps at
   the end of their own script; an action nobody registered is ignored, not
   an error, so a page can carry markup for a feature it does not load.
   Elements that open a note use data-note instead (gardentemplate.html
   handles it, since only the Garden has notes to open). */
var AURELIA_ACTIONS = Object.create(null);

function registerActions(map) {
    Object.assign(AURELIA_ACTIONS, map);
}

function dispatchAction(attribute, event) {
    var el = event.target.closest('[' + attribute + ']');
    if (!el) return;
    var handler = AURELIA_ACTIONS[el.getAttribute(attribute)];
    if (handler) handler(el, event);
}

document.addEventListener('click', function (e) { dispatchAction('data-action', e); });
document.addEventListener('change', function (e) { dispatchAction('data-change', e); });
document.addEventListener('input', function (e) { dispatchAction('data-input', e); });
