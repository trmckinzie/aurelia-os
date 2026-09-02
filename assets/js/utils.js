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
