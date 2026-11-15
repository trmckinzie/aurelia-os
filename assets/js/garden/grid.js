/**
 * The card grid and the tree: search, the type filter, the sweep that shows
 * and hides items (updateGrid), search-match highlighting, and the one
 * delegated click listener that opens a card or tree row.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { DEEP_SEARCH_INDEX } from './data.js';
import { drawGraph, isGraphListMode, renderGraphList } from './graph.js';
import { openNote } from './reader.js';
import { applyDueMarkers, refreshDueState } from './review-session.js';
import { syncRoving } from './roving.js';
import { applySort, syncSortControl } from './sorting.js';
import { state } from './state.js';
import { toggleTopicFilter } from './topics.js';
import { syncViewToUrl } from './url-state.js';

export function handleSearch() {
    const input = document.getElementById('searchInput');
    state.currentQuery = input.value.toLowerCase().trim();
    updateGrid();
    syncViewToUrl();
}

export function setFilter(type, btn) {
    state.currentType = type;

    // 1. Reset All Buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        // Remove generic active styles
        btn.classList.remove('active');

        // Remove color-specific active styles (Clean Sweep)
        btn.classList.remove(
            'bg-aurelia-primary/10', 'text-aurelia-primary', 'border-aurelia-primary',
            'bg-aurelia-tertiary/10', 'text-aurelia-tertiary', 'border-aurelia-tertiary',
            'bg-aurelia-secondary/10', 'text-aurelia-secondary', 'border-aurelia-secondary',
            'bg-aurelia-accent/10', 'text-aurelia-accent', 'border-aurelia-accent',
            'bg-aurelia-highlight/10', 'text-aurelia-highlight', 'border-aurelia-highlight',
            'bg-aurelia-info/10', 'text-aurelia-info', 'border-aurelia-info',
            'bg-aurelia-insight/10', 'text-aurelia-insight', 'border-aurelia-insight'
        );

        // Add inactive state
        btn.classList.add('border-aurelia-border', 'text-aurelia-muted');
        // Same reason as the view toggles: which filter is on is
        // otherwise carried entirely by colour.
        btn.setAttribute('aria-pressed', 'false');
    });

    // 2. Activate Target Button
    // btn is passed explicitly (the delegated setFilter action hands
    // over the clicked chip) -- previously read from the implicit global
    // `event` object, which
    // only worked because every call site happened to be a live click
    // and would break if setFilter were ever called programmatically.
    const target = btn;
    target.classList.remove('border-aurelia-border', 'text-aurelia-muted');
    target.classList.add('active');
    target.setAttribute('aria-pressed', 'true');

    // 3. Apply Dynamic Color Scheme
    if (type === 'daily-bridge') {
        target.classList.add('bg-aurelia-tertiary/10', 'text-aurelia-tertiary', 'border-aurelia-tertiary');
    } else if (type === 'source') {
        target.classList.add('bg-aurelia-highlight/10', 'text-aurelia-highlight', 'border-aurelia-highlight');
    } else if (type === 'author') {
        target.classList.add('bg-aurelia-secondary/10', 'text-aurelia-secondary', 'border-aurelia-secondary');
    } else if (type === 'discipline') {
        target.classList.add('bg-aurelia-accent/10', 'text-aurelia-accent', 'border-aurelia-accent');
    } else if (type === 'gemini-notebook') {
        target.classList.add('bg-aurelia-info/10', 'text-aurelia-info', 'border-aurelia-info');
    } else if (type === 'deep-dive') {
        target.classList.add('bg-aurelia-insight/10', 'text-aurelia-insight', 'border-aurelia-insight');
    } else {
        // Default (All, Concepts) -> Cyan
        target.classList.add('bg-aurelia-primary/10', 'text-aurelia-primary', 'border-aurelia-primary');
    }
    
    updateGrid();
    syncViewToUrl();
}

/* motion.js runs a step on either side of every sweep (it staggers in the
   cards a sweep newly shows). It registers a wrapper here rather than
   replacing updateGrid, which is what the single script did: an exported
   function cannot be reassigned by the module that imports it. Unset, as
   under reduced motion, the sweep runs bare. */
let gridUpdateWrapper = null;
export function setGridUpdateWrapper(wrapper) { gridUpdateWrapper = wrapper; }

export function updateGrid() {
    if (gridUpdateWrapper) gridUpdateWrapper(sweepGrid);
    else sweepGrid();
}

function sweepGrid() {
    // Suppressed while restoreViewFromUrl() applies several settings in
    // a row; it runs one pass itself once they're all in place.
    if (state.restoring) return;
    applySort();
    syncSortControl();
    let visibleCount = 0;

    // 1. FILTER GRID ITEMS
    const gridItems = document.querySelectorAll('.searchable-item');
    gridItems.forEach(item => {
        if (checkVisibility(item)) {
            item.style.display = 'flex';
            visibleCount++;
            // Additive Highlight: Only highlight if there is a query.
            //
            // Deliberately contained. Highlighting is decoration; filtering
            // is not. This call used to be able to throw (see highlightText),
            // and because it sits inside this loop the throw aborted
            // filtering partway -- later cards kept their previous
            // visibility, and node-count, the empty state, the tree folders
            // and the graph dimming below all never ran, leaving the grid
            // showing one set of cards under a count for another. The
            // escaping in highlightText fixes the known trigger; this makes
            // any *future* one degrade to "this card isn't highlighted"
            // instead of "the grid is lying". Scoped to the highlight call
            // only, so a real bug elsewhere still surfaces normally.
            if (state.currentQuery.length > 0) {
                try {
                    highlightText(item, state.currentQuery);
                } catch (e) {
                    console.error('highlightText failed for', item.dataset.id, e);
                    clearHighlights(item);
                }
            } else {
                clearHighlights(item);
            }
        } else {
            item.style.display = 'none';
            clearHighlights(item);
        }
    });

    // 2. FILTER TREE NODES
    const treeNodes = document.querySelectorAll('.searchable-tree-item');
    treeNodes.forEach(item => {
        if (checkVisibility(item)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });

    // 3. AUTO-HIDE EMPTY FOLDERS
    const treeFolders = document.querySelectorAll('.tree-folder'); 
    treeFolders.forEach(folder => {
        const children = folder.querySelectorAll('.searchable-tree-item');
        let hasVisible = false;
        children.forEach(c => { if(c.style.display !== 'none') hasVisible = true; });

        if (hasVisible) folder.style.display = 'block';
        else folder.style.display = 'none';
    });

    const counter = document.getElementById('node-count');
    if (counter) counter.innerText = visibleCount;

    const gridEmpty = document.getElementById('grid-empty');
    if (gridEmpty) gridEmpty.classList.toggle('hidden', visibleCount > 0);

    // 4. REFRESH GRAPH DIMMING/LIST (if that's the active view). Below
    // 768px (Phase 4) the graph is a ranked list instead of the canvas
    // (see initGraph()/renderGraphList() further down) -- it re-filters
    // through the same graphNodeMatches() the canvas's own dimming
    // uses, so a filter/search change is reflected in both equally.
    if (state.currentView === 'graph') {
        if (isGraphListMode()) renderGraphList();
        else if (state.graphState && state.graphState.laidOut) drawGraph();
    }

    // 5. KEEP THE KEYBOARD TAB STOP VALID
    // Everything above can hide or reorder the item currently carrying
    // tabindex="0". If that item ends up hidden, the grid stops being
    // reachable by Tab at all, so re-apply and clamp after every sweep.
    // Never steals focus -- this runs on every keystroke in the search box.
    syncRoving(false);

    // 6. DUE MARKERS (Phase 2). updateGrid() runs on every keystroke
    // over 245 cards, so the log is read ONCE per sweep (refreshDueState)
    // into a Set; each card then does a plain membership check
    // (applyDueMarkers) rather than a localStorage read of its own.
    refreshDueState();
    applyDueMarkers();
}

export function graphNodeMatches(node) {
    const typeMatch = (state.currentType === 'all') || (node.type.includes(state.currentType));
    // Graph nodes don't carry full body text (see _build_graph_index's
    // size-conscious design), so search here matches title + tags
    // rather than the full-text match the grid/tree get from
    // data-search -- narrower, but far better than title-only.
    const haystack = (node.title + ' ' + (node.tags || []).join(' ')).toLowerCase();
    const searchMatch = state.currentQuery.length === 0 || haystack.includes(state.currentQuery);
    const topicMatch = !state.currentTopic || (node.tags || []).includes(state.currentTopic);
    return typeMatch && searchMatch && topicMatch;
}

// Shared by navigateNote and openRandomNote -- both need "whatever the
// current filter/search leaves visible in the grid," previously
// re-queried and re-filtered independently in each place.
export function getVisibleNoteIds() {
    return Array.from(document.querySelectorAll('#cardGrid .searchable-item'))
        .filter(el => el.style.display !== 'none')
        .map(el => el.dataset.id);
}

export function checkVisibility(item) {
    // Full body text comes from DEEP_SEARCH_INDEX, keyed by note id.
    // It used to live in a data-search attribute on every card AND every
    // tree row -- the whole vault's text embedded twice, 1.82 MB and 35%
    // of this page. Same full-text search, one copy.
    const itemType = item.dataset.type ? item.dataset.type.toLowerCase() : '';
    const itemTags = item.dataset.tags || '';

    // Deep-search text comes from the index, keyed by note id. If that
    // file didn't load, fall back to the note's title plus its tags --
    // both already in the DOM. Without the fallback an empty index makes
    // every query match nothing, so search would look broken rather than
    // merely shallower.
    let itemSearch = DEEP_SEARCH_INDEX[item.dataset.id];
    if (itemSearch === undefined) {
        const titleEl = item.querySelector('h3') || item.querySelector('span');
        itemSearch = ((titleEl ? titleEl.textContent : '') + ' ' + itemTags).toLowerCase();
    }

    // ADDITIVE LOGIC: Must match Filter Button AND Search Bar AND Topic
    const typeMatch = (state.currentType === 'all') || (itemType.includes(state.currentType));
    const searchMatch = itemSearch.includes(state.currentQuery);
    const topicMatch = !state.currentTopic || itemTags.split(' ').includes(state.currentTopic);

    return typeMatch && searchMatch && topicMatch;
}

// --- ROBUST HIGHLIGHTING ENGINE ---
export function highlightText(card, term) {
    // Only target Visible elements (h3, p) to avoid breaking layout/icons
    const targets = card.querySelectorAll('h3, p');
    targets.forEach(element => {
        if (!element.dataset.original) element.dataset.original = element.innerHTML;
        const originalHTML = element.dataset.original;
        
        // Only highlight if the VISIBLE text actually contains the term
        if (originalHTML.toLowerCase().includes(term)) {
            // ⚡ SMART REGEX ⚡: Ignores text inside HTML tags (like <button> or class="")
            // escapeRegExp (assets/js/utils.js) is load-bearing: the term
            // comes straight from the search box, so an ordinary query
            // like "System 1 (fast)" would otherwise be compiled as a
            // pattern and throw. A reader typing a paren means a paren.
            const regex = new RegExp(`(?![^<]*>)(${escapeRegExp(term)})`, 'gi');
            element.innerHTML = originalHTML.replace(regex, '<span class="highlight">$1</span>');
        } else {
            element.innerHTML = originalHTML;
        }
    });
}

export function clearHighlights(card) {
    const targets = card.querySelectorAll('h3, p');
    targets.forEach(element => {
        if (element.dataset.original) element.innerHTML = element.dataset.original;
    });
}

/* === DELEGATED CLICKS: GRID, TREE AND NOTE LINKS (B02) ============
   No card, pill, chip or tree row carries an inline handler. One
   listener on each container decides what a click meant, in priority
   order inside a card: a Gemini card's topic chip filters (and is left
   alone by the card), a pill or prose link (data-note) opens its own
   target through the document listener below, and anything else on
   the card -- the title button's activation included -- opens the
   card's note. Delegated on the container rather than per element
   because updateGrid() re-sorts and re-parents the cards, so a
   per-element listener would not survive a sort.

   The chip also reveals the topic cloud, so the active filter is
   visible somewhere the reader can clear it; filtering with no visible
   control is how the topic deep-link handler already justifies this. */
export function handleGridClick(e) {
    const chip = e.target.closest('button.card-topic[data-tag]');
    if (chip) {
        const cloud = document.getElementById('topic-cloud');
        const topicsBtn = document.getElementById('btn-topics');
        if (cloud && cloud.classList.contains('hidden')) {
            cloud.classList.remove('hidden');
            if (topicsBtn) {
                topicsBtn.setAttribute('aria-expanded', 'true');
                topicsBtn.classList.add('text-aurelia-accent');
            }
        }
        toggleTopicFilter(chip.dataset.tag);
        return;
    }
    if (e.target.closest('[data-note], [data-action]')) return;
    const item = e.target.closest('.searchable-item, .searchable-tree-item');
    if (item && item.dataset.id) openNote(item.dataset.id);
}
export function initGrid() {
    ['cardGrid', 'treeView'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', handleGridClick);
    });
}
