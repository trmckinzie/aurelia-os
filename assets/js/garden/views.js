/**
 * The three views of the Garden -- grid, tree and knowledge graph -- and the
 * toolbar buttons that switch between them.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { btnGraph, btnGrid, btnTree, graphViewEl, gridView, treeView, viewLabel } from './dom.js';
import { initGraph } from './graph.js';
import { syncRoving } from './roving.js';
import { updateSortControlVisibility } from './sorting.js';
import { state } from './state.js';
import { syncViewToUrl } from './url-state.js';

// --- 1. VIEW SWITCHER LOGIC (NEW) ---

export function switchView(mode) {
    const previous = state.currentView;
    state.currentView = mode;
    gridView.classList.toggle('hidden', mode !== 'grid');
    treeView.classList.toggle('hidden', mode !== 'tree');
    graphViewEl.classList.toggle('hidden', mode !== 'graph');

    // Animate the panel that just became visible. These three panels
    // previously carried `animate-fade-in-up`, a class that was never
    // defined anywhere in the project -- so switching views actually
    // had no transition at all, it just popped. aureliaReveal is used
    // rather than a bare animate() because it guarantees the panel
    // ends visible even if the frame loop stalls mid-animation (see
    // assets/js/utils.js). Skipped when re-selecting the current view,
    // which would otherwise replay the entrance for no reason.
    if (previous !== mode) {
        const shown = mode === 'grid' ? gridView : mode === 'tree' ? treeView : graphViewEl;
        if (shown) aureliaReveal(shown, { y: 10, duration: 0.34 });
    }

    [[btnGrid, 'grid'], [btnTree, 'tree'], [btnGraph, 'graph']].forEach(([btn, m]) => {
        // The tint below is the only visual cue for "this view is
        // selected"; aria-pressed is the same statement made out loud.
        btn.setAttribute('aria-pressed', String(m === mode));
        if (m === mode) {
            btn.classList.add('bg-aurelia-text/10', 'text-aurelia-primary');
            btn.classList.remove('text-aurelia-muted');
        } else {
            btn.classList.remove('bg-aurelia-text/10', 'text-aurelia-primary');
            btn.classList.add('text-aurelia-muted');
        }
    });

    viewLabel.innerText = mode === 'grid' ? "Grid" : mode === 'tree' ? "Tree" : "Graph";
    // DELETED: The lines that set filterControls.style.opacity/pointerEvents
    // Filters now remain active in every mode.

    // Matches each button's own aria-label/title (see the toolbar
    // markup) rather than viewLabel's shorter text above, so the
    // announcement and the visible label never say different things.
    if (previous !== mode) {
        announce(mode === 'grid' ? "Grid view" : mode === 'tree' ? "List view" : "Knowledge graph");
    }

    if (mode === 'graph') initGraph();
    updateSortControlVisibility();
    // The grid and the tree keep separate item lists, so the tab stop has
    // to be re-established against whichever one is now on screen. Reset
    // to the top: carrying position 180 across from the grid into a tree
    // that groups by type would land somewhere arbitrary.
    if (previous !== mode) state.rovingIndex = 0;
    syncRoving(false);
    syncViewToUrl();
}
