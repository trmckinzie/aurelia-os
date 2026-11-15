/**
 * The Garden's page script: the entry module (roadmap S13).
 *
 * garden.html loads this one file as a module; it imports the rest of
 * assets/js/garden/. Until S13 all of it was a single inline script of about
 * 2,800 lines in gardentemplate.html, which no unit test could reach. The
 * build's data now sits in the page as two JSON data blocks (data.js), and
 * the page carries no inline script of the Garden's own.
 *
 * Importing a module here runs nothing: every listener and every first
 * paint is started below, in the order the single script ran them, which
 * is what lets tests/js/ import one module and call one function.
 *
 * The page reaches this code two ways only: the action registry at the end
 * of this file (data-action / data-change / data-input, dispatched by
 * assets/js/utils.js) and the [data-note] listener in reader.js. Nothing is
 * published on window, and no markup calls a function by name.
 *
 * A module script is deferred, so this runs once the document is parsed,
 * after the classic scripts the page loads (utils.js, review.js,
 * flashcards.js, the search index, marked, Motion).
 */
import { initBanner } from './banner.js';
import { loadData } from './data.js';
import { initDom } from './dom.js';
import { initGraphResize } from './graph.js';
import { handleSearch, initGrid, setFilter } from './grid.js';
import { closeShortcutSheet, initKeyboard, openShortcutSheet } from './keyboard.js';
import { initMotion } from './motion.js';
import { initOutline, setAllGeminiSections } from './outline.js';
import { expandBacklinks } from './connections.js';
import { initReadAloud, onRateChange, onVoiceChange, toggleReading, toggleTtsSettings } from './read-aloud.js';
import { closeModal, initReader, navigateNote, openNoteFromHash, openRandomNote } from './reader.js';
import {
    applyDueMarkers,
    exportReviewProgress,
    importReviewProgress,
    refreshDueState,
    startReviewSession,
} from './review-session.js';
import { initRoving, syncRoving } from './roving.js';
import { copyNoteLink, copyViewLink } from './share.js';
import { applySort, setSort, syncSortControl, updateSortControlVisibility } from './sorting.js';
import { initStudy, noteMaturity, toggleStudyMode } from './study.js';
import { clearTopicFilter, initTopics, renderTopicCloud, toggleTopicCloud } from './topics.js';
import { restoreViewFromUrl } from './url-state.js';
import { switchView } from './views.js';

loadData();
initDom();

initBanner();
initRoving();
initOutline();
initKeyboard();
initReadAloud();
initTopics();
initGrid();
initReader();
initGraphResize();
initMotion();

// --- Review init -------------------------------------------------------
// Loads (and, on a v1 log, migrates -- see review.js's migrateV1())
// before restoreViewFromUrl() below, since that may itself need to
// recompute a due queue from ?review=1. save() persists a v1->v2
// migration immediately rather than leaving it to redo in memory on
// every future reload.
if (window.Review) {
    try {
        Review.load({ getMaturity: noteMaturity });
        Review.save();
    } catch (e) { /* localStorage unavailable -- Review already no-ops safely */ }
}
initStudy();

renderTopicCloud();
restoreViewFromUrl();
// Establishes the default order even when the URL carried no state,
// since restoreViewFromUrl() returns early with no params.
applySort();
syncSortControl();
updateSortControlVisibility();
// The grid's one tab stop. updateGrid() sets it, but on a plain visit
// (no URL state) nothing calls updateGrid() before the first keystroke,
// so every card stayed at tabindex -1 and Tab skipped the whole grid.
// Found by the browser suite (roadmap S08).
syncRoving(false);
openNoteFromHash();
// Populates the due count/"Start review" state and grid markers on
// first paint -- restoreViewFromUrl() only calls updateGrid() (which
// does this) when the URL actually carried state to restore.
refreshDueState();
applyDueMarkers();

/* === DELEGATED ACTIONS (B02) ========================================
   The toolbar, reader and sheet controls name their action in
   data-action / data-change / data-input; assets/js/utils.js dispatches
   to these. */
registerActions({
    switchView: (el) => switchView(el.dataset.view),
    setFilter: (el) => setFilter(el.dataset.filter, el),
    toggleTopicCloud: () => toggleTopicCloud(),
    openRandomNote: () => openRandomNote(),
    copyViewLink: () => copyViewLink(),
    toggleStudyMode: () => toggleStudyMode(),
    openShortcutSheet: () => openShortcutSheet(),
    closeShortcutSheet: () => closeShortcutSheet(),
    startReviewSession: () => startReviewSession(),
    exportReviewProgress: () => exportReviewProgress(),
    importReviewProgress: (el) => { importReviewProgress(el.files[0]); el.value = ''; },
    clearTopicFilter: () => clearTopicFilter(),
    copyNoteLink: () => copyNoteLink(),
    closeModal: () => closeModal(),
    toggleReading: () => toggleReading(),
    toggleTtsSettings: () => toggleTtsSettings(),
    navigateNote: (el) => navigateNote(Number(el.dataset.step)),
    setAllGeminiSections: (el) => setAllGeminiSections(el.dataset.open === 'true'),
    expandBacklinks: (el) => expandBacklinks(el),
    setSort: (el) => setSort(el.value),
    handleSearch: () => handleSearch(),
    onVoiceChange: (el) => onVoiceChange(el.value),
    onRateChange: (el) => onRateChange(el.value),
});
