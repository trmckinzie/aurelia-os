/**
 * AURELIA // SHARED CLIENT UTILITIES
 * Loaded early in <head> (see base.html) so it's available to every page's
 * own inline scripts regardless of block ordering.
 */

// Vault note titles/tags/references end up interpolated into innerHTML
// strings in a few places (command palette, transmissions sidebar/refs
// list). Escape them first so a stray "<" in a note can't be read as a tag.
function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}
