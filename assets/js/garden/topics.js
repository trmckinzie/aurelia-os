/**
 * Browse by topic: the tag cloud and the topic filter.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { GRAPH_INDEX } from './data.js';
import { updateGrid } from './grid.js';
import { state } from './state.js';
import { syncViewToUrl } from './url-state.js';

// --- BROWSE BY TOPIC ---
// A tag cloud computed client-side from GRAPH_INDEX (no separate index
// needed -- tags were already added there for Related by Topic). Scoped
// to topic/* the same way, for the same reason: type/* and status/*
// tags are structural, not subject matter, and would dominate a cloud
// built from all tags.
export function toggleTopicCloud() {
    const open = !document.getElementById('topic-cloud').classList.toggle('hidden');
    const btn = document.getElementById('btn-topics');
    btn.classList.toggle('text-aurelia-accent');
    // The panel appears well below the button, so nothing links the two
    // for a screen reader without aria-expanded + aria-controls.
    btn.setAttribute('aria-expanded', String(open));
}

// The `limit` most-used topic/* tags across `nodes`, as [tag, count] pairs,
// most used first.
export function topicCounts(nodes, limit = 24) {
    const counts = {};
    nodes.forEach(n => {
        (n.tags || []).forEach(t => {
            if (t.startsWith('topic/')) counts[t] = (counts[t] || 0) + 1;
        });
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, limit);
}

// "topic/working-memory" as a reader sees it: "working memory".
export function topicLabel(tag) {
    return tag.replace('topic/', '').replace(/-/g, ' ');
}

export function renderTopicCloud() {
    const sorted = topicCounts(GRAPH_INDEX.nodes);
    const maxCount = sorted.length ? sorted[0][1] : 1;

    document.getElementById('topic-cloud-items').innerHTML = sorted.map(([tag, count]) => {
        const label = topicLabel(tag);
        const size = 10 + Math.round((count / maxCount) * 6); // 10-16px, frequency-weighted
        const active = tag === state.currentTopic;
        const activeClasses = active
            ? 'border-aurelia-accent text-aurelia-accent bg-aurelia-accent/10'
            : 'border-aurelia-border text-aurelia-muted hover:border-aurelia-accent hover:text-aurelia-accent';
        // data-tag + the delegated listener below, not an inline
        // an inline toggleTopicFilter('${tag}') handler: the tag is vault-authored
        // text being dropped into a JS string literal inside an HTML
        // attribute, so an apostrophe alone breaks the handler and a
        // crafted tag could close the string and run its own code.
        // escapeHtml covers the attribute; nothing is parsed as JS at all.
        return `<button type="button" data-tag="${escapeHtml(tag)}" class="font-mono px-2.5 py-1 rounded-theme border transition-colors ${activeClasses}" data-size="${size}">${escapeHtml(label)} <span class="opacity-50">${count}</span></button>`;
    }).join('');
    // Frequency-weighted size through the CSSOM, not a style attribute in
    // the markup string, which the Content-Security-Policy refuses.
    document.querySelectorAll('#topic-cloud-items [data-size]').forEach((b) => { b.style.fontSize = b.dataset.size + 'px'; });
}

export function initTopics() {
    // Delegated: renderTopicCloud() replaces the whole list on every toggle,
    // so a per-button listener would have to be re-attached each time.
    document.getElementById('topic-cloud-items').addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-tag]');
        if (btn) toggleTopicFilter(btn.dataset.tag);
    });
}

export function toggleTopicFilter(tag) {
    state.currentTopic = (state.currentTopic === tag) ? '' : tag;
    renderTopicCloud();
    updateTopicActiveLabel();
    updateGrid();
    syncViewToUrl();
}

export function clearTopicFilter() {
    state.currentTopic = '';
    renderTopicCloud();
    updateTopicActiveLabel();
    updateGrid();
    syncViewToUrl();
}

export function updateTopicActiveLabel() {
    const label = document.getElementById('topic-active-label');
    const name = document.getElementById('topic-active-name');
    if (state.currentTopic) {
        name.innerText = topicLabel(state.currentTopic);
        label.classList.remove('hidden');
    } else {
        label.classList.add('hidden');
    }
}
