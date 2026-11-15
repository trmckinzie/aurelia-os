/**
 * Staggered entrance for the cards. Decoration only.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { setGridUpdateWrapper } from './grid.js';

/* === MOTION: staggered card reveal ===============================
   Cards animate in as they scroll into view, and re-stagger after a
   filter or search changes what's visible -- so a filter change reads
   as the grid rebuilding itself rather than as content teleporting.

   Same two guards the Lobby uses (commit 414a16e): skipped entirely
   under prefers-reduced-motion, and a no-op if the Motion CDN didn't
   load. Cards are always rendered in their correct final state by
   cards.py, so nothing here is load-bearing for visibility -- if this
   block never runs, the grid just appears the way it does today. */
export function initMotion() {
    if (aureliaMotionOff()) return;
    const { inView } = window.Motion;

    // Tracked so a card already revealed once isn't re-animated every
    // time the filter changes -- only newly-shown cards animate.
    const revealed = new WeakSet();

    function revealCard(card, index) {
        if (revealed.has(card)) return;
        revealed.add(card);
        // aureliaReveal (assets/js/utils.js) guarantees the card ends
        // visible even if the frame loop stalls mid-animation.
        aureliaReveal(card, { y: 14, duration: 0.42, delay: Math.min(index, 12) * 0.035 });
    }

    document.querySelectorAll('.searchable-item').forEach((card) => {
        inView(card, () => {
            if (revealed.has(card)) return;
            // Index within the currently-visible run, so the stagger
            // reads left-to-right across the row being entered.
            const shown = [...document.querySelectorAll('.searchable-item')]
                .filter(c => c.style.display !== 'none');
            revealCard(card, Math.max(0, shown.indexOf(card) % 12));
        }, { amount: 0.15 });
    });

    // updateGrid() is what filter + search both funnel through; wrapping
    // it keeps this in one place instead of hooking each call site.
    setGridUpdateWrapper((sweepGrid) => {
        const wasVisible = new Set(
            [...document.querySelectorAll('.searchable-item')].filter(c => c.style.display !== 'none'));
        sweepGrid();
        const nowVisible = [...document.querySelectorAll('.searchable-item')]
            .filter(c => c.style.display !== 'none');
        nowVisible.forEach((card, i) => {
            if (!wasVisible.has(card)) revealCard(card, i);
        });
    });
}
