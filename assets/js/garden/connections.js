/**
 * What a note connects to, shown in the reader: "Referenced By" (explicit
 * wikilinks), "Related by Topic" (shared topic tags), and the "How does this
 * connect?" nudge that follows a rating in Study mode.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { BACKLINKS_INDEX, GRAPH_INDEX, NODE_BY_ID } from './data.js';

export function renderBacklinks(noteId) {
    const container = document.getElementById('modal-backlinks');
    const refs = BACKLINKS_INDEX[noteId] || [];
    if (refs.length === 0) {
        container.innerHTML = '';
        return;
    }
    // The vault's most-linked note has 32 backlinks, and rendering all of
    // them flat produced an undifferentiated wall that was harder to read
    // than a truncated list plus a count. Show a first screenful, keep the
    // rest one click away.
    const VISIBLE = 12;
    const shown = refs.slice(0, VISIBLE);
    const rest = refs.slice(VISIBLE);
    // Ordinary tab stops, unlike the tabindex="-1" pills on the card faces:
    // there are at most a dozen or so here, and the reader already traps
    // focus around its own content, so they cost nothing to tab through.
    const pill = (r) => `
                <button type="button" data-note="${r.id}" class="text-[0.8125rem] font-mono px-2.5 py-1 border border-aurelia-border rounded-theme pill-live hover:border-aurelia-primary hover:text-aurelia-primary cursor-pointer transition-colors">${escapeHtml(r.title)}</button>`;
    container.innerHTML = `
        <div class="mt-6 pt-6 border-t border-aurelia-border">
            <span class="field-label text-aurelia-muted block mb-3">⟵ Referenced By (${refs.length})</span>
            <div class="flex flex-wrap gap-2">
                ${shown.map(pill).join('')}
                ${rest.length ? `<span id="backlinks-rest" hidden>${rest.map(pill).join('')}</span>` : ''}
                ${rest.length ? `<button type="button" data-action="expandBacklinks" class="text-[0.8125rem] font-mono px-2.5 py-1 border border-dashed border-aurelia-border rounded-theme text-aurelia-muted hover:text-aurelia-text hover:border-aurelia-text/50 cursor-pointer transition-colors">+${rest.length} MORE</button>` : ''}
            </div>
        </div>
    `;
}

// `hidden` rather than a display class: the pills are already in the DOM,
// so revealing them costs no re-render and keeps their openNote handlers.
export function expandBacklinks(btn) {
    const rest = document.getElementById('backlinks-rest');
    if (rest) { rest.hidden = false; rest.className = 'contents'; }
    btn.remove();
}

// relatedByTopic() ranks; renderRelatedByTopic() below draws what it returns
// ([{node, shared}, ...], at most five).
//
// Implicit connections via shared tags, as opposed to renderBacklinks'
// explicit wikilinks -- this is what makes tagging pay compound
// interest: an old note becomes newly discoverable the moment a later
// note reuses one of its tags, with no manual re-linking required.
export function relatedByTopic(noteId) {
    const current = NODE_BY_ID[noteId];
    // Only "topic/*" tags signal subject matter -- "type/*" and
    // "status/*" are structural (note type, maturity/reading state) and
    // would otherwise dominate the overlap score: type/concept and
    // status/seed alone cover roughly half the vault, which would make
    // this section mean "other concept notes" instead of "related".
    const topicTags = current ? (current.tags || []).filter(t => t.startsWith('topic/')) : [];
    if (topicTags.length === 0) return [];
    const tagSet = new Set(topicTags);

    const scoredAll = Object.values(NODE_BY_ID)
        .filter(n => n.id !== noteId)
        .map(n => ({ node: n, shared: (n.tags || []).filter(t => tagSet.has(t)).length }))
        .filter(r => r.shared > 0);

    // Same candidate policy as renderElaboration() below: daily logs and
    // Gemini Notebook dumps rack up shared topic/* tags just by being
    // course material, which used to fill this strip with five
    // 2026-02-12-style daily logs on a course note instead of anything
    // actually related. They're excluded from the ranked list and only
    // reintroduced -- merged back into the full pool, not appended -- if
    // fewer than two non-excluded candidates remain, so a thin note
    // still gets a strip instead of an empty section.
    const preferred = scoredAll.filter(r => !NUDGE_EXCLUDED_TYPES.has(r.node.type));
    const pool = preferred.length >= 2 ? preferred : scoredAll;

    return pool
        .sort((a, b) => b.shared - a.shared
            || nudgeTypeRank(a.node.type) - nudgeTypeRank(b.node.type)
            || a.node.title.localeCompare(b.node.title))
        .slice(0, 5);
}

export function renderRelatedByTopic(noteId) {
    const container = document.getElementById('modal-related');
    const related = relatedByTopic(noteId);
    if (related.length === 0) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = `
        <div class="mt-6 pt-6 border-t border-aurelia-border">
            <span class="field-label text-aurelia-accent block mb-3">✦ Related by Topic</span>
            <div class="flex flex-wrap gap-2">
                ${related.map(r => `
                <button type="button" data-note="${r.node.id}" title="${r.shared} shared tag${r.shared === 1 ? '' : 's'}" class="text-[0.8125rem] font-mono px-2.5 py-1 border border-aurelia-accent/30 rounded-theme hover:border-aurelia-accent hover:text-aurelia-accent cursor-pointer transition-colors">${escapeHtml(r.node.title)}</button>
                `).join('')}
            </div>
        </div>
    `;
}

// --- Elaboration nudge -----------------------------------------------
// Runs after a rating is submitted (see submitRating() above).
// Candidates come from this note's explicit backlinks (BACKLINKS_INDEX)
// unioned with its graph neighbours (GRAPH_INDEX.edges), ranked by
// DIFFERENCE from the current note -- a different type first, then
// fewest shared topic/* tags -- so the nudge surfaces genuinely
// different material to connect to (the interleaving principle in
// docs/DECISIONS.md item 18),
// not more of the same.
export function noteTopicTags(id) {
    const node = NODE_BY_ID[id];
    return node ? (node.tags || []).filter(t => t.startsWith('topic/')) : [];
}

export function sharedTopicCount(idA, idB) {
    const a = new Set(noteTopicTags(idA));
    return noteTopicTags(idB).filter(t => a.has(t)).length;
}

export function graphNeighbours(noteId) {
    const ids = new Set();
    (GRAPH_INDEX.edges || []).forEach(edge => {
        if (edge.source === noteId) ids.add(edge.target);
        else if (edge.target === noteId) ids.add(edge.source);
    });
    return ids;
}

// Daily logs and Gemini Notebook dumps are course material, not
// concepts -- an elaboration prompt against one ("How does this connect
// to 2026-02-12?") is useless, so these are hard-excluded regardless of
// how well they'd otherwise score. Everything else the vault publishes
// (concept/source/author/discipline/deep-dive) is fair game, ranked by
// NUDGE_TYPE_PREFERENCE below.
export const NUDGE_EXCLUDED_TYPES = new Set(['daily-bridge', 'log', 'gemini-notebook']);
// Tie-break preference among different-type candidates, most to least
// preferred. Doesn't need to be exhaustive: any type not listed here
// (there isn't one among the surviving, non-excluded types today) sorts
// after every listed one via nudgeTypeRank()'s fallback.
export const NUDGE_TYPE_PREFERENCE = ['discipline', 'author', 'source', 'deep-dive', 'concept'];

export function nudgeTypeRank(type) {
    const idx = NUDGE_TYPE_PREFERENCE.indexOf(type);
    return idx === -1 ? NUDGE_TYPE_PREFERENCE.length : idx;
}

export function elaborationCandidates(noteId) {
    const current = NODE_BY_ID[noteId];
    const ownType = current ? current.type : '';
    const currentTags = new Set(noteTopicTags(noteId));

    const candidateIds = new Set();
    (BACKLINKS_INDEX[noteId] || []).forEach(r => candidateIds.add(r.id));
    graphNeighbours(noteId).forEach(id => candidateIds.add(id));
    candidateIds.delete(noteId);

    return Array.from(candidateIds)
        .map(id => NODE_BY_ID[id])
        .filter(Boolean)
        .filter(node => !NUDGE_EXCLUDED_TYPES.has(node.type))
        .map(node => ({
            node,
            // 1 when the type differs -- sorted to the top below.
            differentType: node.type !== ownType ? 1 : 0,
            typeRank: nudgeTypeRank(node.type),
            shared: (node.tags || []).filter(t => currentTags.has(t)).length
        }))
        // Different type first; among ties, prefer discipline > author >
        // source > deep-dive > concept (NUDGE_TYPE_PREFERENCE); among
        // further ties, fewer shared topic tags first (more genuinely
        // different material). Same-type concepts are never filtered
        // out, just sorted to the bottom -- the fallback rule in
        // docs/DECISIONS.md item 18:
        // show them as a last resort rather than render nothing.
        .sort((a, b) => b.differentType - a.differentType
            || a.typeRank - b.typeRank
            || a.shared - b.shared)
        .slice(0, 3);
}

export function renderElaboration(noteId) {
    const container = document.getElementById('modal-elaborate');
    if (!container) return;
    const scored = elaborationCandidates(noteId);
    if (scored.length === 0) { container.innerHTML = ''; return; }

    container.innerHTML = `
        <div class="mt-6 pt-6 border-t border-aurelia-border">
            <span class="field-label text-aurelia-insight block mb-3">How does this connect?</span>
            <div class="flex flex-col gap-2">
                ${scored.map(r => `
                <p class="text-[0.8125rem] text-aurelia-muted">
                    How does this connect to
                    <button type="button" data-note="${r.node.id}" class="text-[0.8125rem] font-mono px-2.5 py-1 border border-aurelia-border rounded-theme pill-live hover:border-aurelia-insight hover:text-aurelia-insight cursor-pointer transition-colors">${escapeHtml(r.node.title)}</button>?
                </p>
                `).join('')}
            </div>
        </div>
    `;
}
