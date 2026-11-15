/**
 * Roving focus: the grid and the tree as a single tab stop, walked with the
 * arrow keys.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { openNote } from './reader.js';
import { state } from './state.js';

/* === ROVING FOCUS =================================================
   Makes the grid and the tree operable from a keyboard. Both were
   walls of onclick-only elements: 245 cards, 245 tree rows and 615
   in-card pills, none of them reachable, against 25 focusable
   elements on the page that were all nav and toolbar.

   Roving rather than one tab stop per card. Every card being a tab
   stop is simpler, but Tab would then have to pass through up to 245
   of them to reach anything after the grid. Instead exactly one item
   carries tabindex="0" and the rest carry -1, so the grid is a single
   stop and the arrow keys move within it -- the same shape a native
   listbox or radio group has, and what a screen reader user expects
   from a grid of peers.

   What carries the tabindex is the item's control, rovingControl():
   a card's title button (.card-open, see engine/cards.py; the card
   itself is a plain <article> since B19, so the pills inside it are
   reachable), or the tree row itself, which has no inner control.
   Visibility is still judged on the item.

   Visibility is read from style.display, matching getVisibleNoteIds()
   and updateGrid()'s own sweep, so the walk follows the active
   filter, topic, search and sort with nothing extra to keep in sync.
   The reader's [ and ] keys use that same helper, which is why
   arrowing and next/previous cannot drift apart. */

export function rovingControl(item) {
    return item.querySelector('.card-open') || item;
}

export function rovingItems() {
    const sel = state.currentView === 'tree' ? '.searchable-tree-item' : '#cardGrid .searchable-item';
    return Array.from(document.querySelectorAll(sel)).filter(el => {
        if (el.style.display === 'none') return false;
        // A row inside a collapsed <details> is display:none only via its
        // ancestor, so check that it actually has a box.
        return el.getClientRects().length > 0;
    });
}

// Grid columns come from the computed template rather than a hardcoded 3,
// so up/down step one visual row at every breakpoint (1 / 2 / 3 columns).
export function rovingColumns() {
    const grid = document.getElementById('cardGrid');
    if (!grid || state.currentView === 'tree') return 1;
    return columnCount(getComputedStyle(grid).gridTemplateColumns);
}

// How many columns a computed grid-template-columns value describes: one
// track size per column ("412px 412px 412px"), or "none" for no grid.
export function columnCount(template) {
    if (!template || template === 'none') return 1;
    return Math.max(1, template.trim().split(/\s+/).length);
}

/* The index arithmetic, kept apart from the DOM so it can be unit-tested
   (tests/js/roving.test.mjs).

   clampRovingIndex: the index pulled back inside `count` items. Filtering
   from 245 cards down to 3 must not leave the tab stop pointing at a card
   that is now hidden. With nothing to point at it is 0.

   rovingIndexForKey: where a navigation key moves the tab stop from
   `index`, among `count` visible items laid out in `cols` columns, or null
   for a key that does not move it. Up and down step one visual row and stop
   at the first and last item; nothing wraps. */
export function clampRovingIndex(index, count) {
    if (count <= 0) return 0;
    return Math.min(count - 1, Math.max(0, index));
}

export function rovingIndexForKey(key, index, count, cols) {
    switch (key) {
        case 'ArrowRight': return clampRovingIndex(index + 1, count);
        case 'ArrowLeft':  return clampRovingIndex(index - 1, count);
        case 'ArrowDown':  return clampRovingIndex(index + cols, count);
        case 'ArrowUp':    return clampRovingIndex(index - cols, count);
        case 'Home':       return 0;
        case 'End':        return clampRovingIndex(count - 1, count);
        default:           return null;
    }
}

// Every card and tree row, visible or not. syncRoving resets across the
// whole set rather than only the visible one, because an item that gets
// filtered out -- or a row belonging to the view you just switched away
// from -- keeps whatever tabindex it last had. Clearing only what is
// currently visible leaves those stragglers at 0, and the grid ends up
// with two tab stops the moment one of them is shown again.
export function allRovingCandidates() {
    return document.querySelectorAll('#cardGrid .searchable-item, .searchable-tree-item');
}

/* Re-applies tabindex after anything that changes what is visible or in
   what order. Clamps the index: filtering from 245 cards down to 3 must
   not leave the tab stop pointing at a card that is now hidden, which
   would silently make the grid unreachable by Tab entirely. */
export function syncRoving(focusActive) {
    allRovingCandidates().forEach(el => { rovingControl(el).tabIndex = -1; });
    const items = rovingItems();
    state.rovingIndex = clampRovingIndex(state.rovingIndex, items.length);
    if (items.length === 0) return;
    rovingControl(items[state.rovingIndex]).tabIndex = 0;
    if (focusActive) {
        rovingControl(items[state.rovingIndex]).focus({ preventScroll: true });
        // The item, not the control: scroll-margin-top (main.css) is on
        // the card so it clears the two sticky bars.
        items[state.rovingIndex].scrollIntoView({ block: 'nearest' });
    }
}

export function rovingKeydown(e) {
    // A Gemini card's topic chip is a real <button> inside the card, so
    // closest() below would find the card and Enter/Space would open the
    // note instead of applying the filter. Let the chip handle its own
    // activation (a native button click fires on both keys).
    if (e.target.closest('button.card-topic')) return;
    const item = e.target.closest('.searchable-item, .searchable-tree-item');
    if (!item) return;
    const next = rovingIndexForKey(e.key, state.rovingIndex, rovingItems().length, rovingColumns());
    if (next !== null) {
        e.preventDefault();
        state.rovingIndex = next;
        syncRoving(true);
        return;
    }
    if (e.key === 'Enter' || e.key === ' ') {
        // A card's title is a real <button>: both keys fire its
        // click natively, which bubbles to the card's handler, so
        // opening it here too would open the note twice.
        if (e.target.closest('.card-open')) return;
        // A tree row is the control itself. Space scrolls the page
        // by default; a role="button" must not.
        e.preventDefault();
        if (item.dataset.id) openNote(item.dataset.id);
    }
}

export function initRoving() {
    ['cardGrid', 'treeView'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('keydown', rovingKeydown);
        // A click anywhere on a card focuses its title control first. The
        // card is a plain <article> and not focusable, so without this a
        // pointer click would leave focus wherever it was, and the reader,
        // which records document.activeElement when it opens, would return
        // focus there instead of to the card on close. Capture phase so it
        // runs before the card's own onclick opens the note. A topic chip is
        // left alone: it filters rather than opens, and keeps its own focus.
        el.addEventListener('click', (e) => {
            if (e.target.closest('button.card-topic')) return;
            const item = e.target.closest('.searchable-item, .searchable-tree-item');
            if (!item) return;
            const control = rovingControl(item);
            if (control !== document.activeElement) control.focus({ preventScroll: true });
        }, true);
        // Focus landing on a card or row (from that click, or from the
        // reader returning it) keeps the arrow keys continuing from there
        // instead of jumping back to the old index.
        el.addEventListener('focusin', (e) => {
            const item = e.target.closest('.searchable-item, .searchable-tree-item');
            if (!item) return;
            const idx = rovingItems().indexOf(item);
            if (idx !== -1 && idx !== state.rovingIndex) {
                state.rovingIndex = idx;
                syncRoving(false);
            }
        });
    });

    /* The filter toolbar is sticky under the nav, so a focused card scrolled
       to the viewport top lands underneath it. main.css turns this into
       scroll-margin-top; it is published from here because the toolbar's
       height is content- and breakpoint-dependent (90px wide, 135px at
       375px) rather than a fixed token like --nav-h. */
    (function publishToolbarHeight() {
        const bar = document.querySelector('.nav-anchored');
        if (!bar) return;
        const write = () => document.documentElement.style.setProperty(
            '--toolbar-h', bar.getBoundingClientRect().height + 'px');
        write();
        if (window.ResizeObserver) new ResizeObserver(write).observe(bar);
        else window.addEventListener('resize', write);
    })();
}
