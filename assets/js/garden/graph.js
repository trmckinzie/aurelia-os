/**
 * The knowledge-graph view: a force-directed layout drawn to a canvas, and
 * the ranked list that stands in for it on a small screen.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { GRAPH_INDEX } from './data.js';
import { el } from './dom.js';
import { graphNodeMatches } from './grid.js';
import { openNote } from './reader.js';
import { state } from './state.js';

// --- KNOWLEDGE GRAPH VIEW ---
// A lightweight force-directed layout (Fruchterman-Reingold-style),
// computed once client-side from GRAPH_INDEX and rendered to a single
// canvas. Exists to make the note graph -- what links to what -- an
// actual explorable picture, not just something you infer one modal
// click at a time.
let graphPan = { x: 0, y: 0, scale: 1, dragging: false, lastX: 0, lastY: 0 };
// The canvas's CSS size. Kept separately from canvas.width/height, which
// are the device-pixel backing store (see initGraph) and would be wrong
// to mix with pointer coordinates.
let graphSize = { width: 0, height: 0 };

// Reads live --aurelia-* values rather than hardcoded hex -- same
// reasoning as the primary/text reads in drawGraph() below: a fixed
// color map would render CYBER_PRIME's neon palette on every theme
// regardless of which one is actually active.
export function graphTypeColors(rootStyle) {
    const v = (name, fallback) => (rootStyle.getPropertyValue(name).trim() || fallback);
    return {
        concept: v('--aurelia-primary', '#00f2ff'),
        'daily-bridge': v('--aurelia-tertiary', '#ff8c00'),
        log: v('--aurelia-tertiary', '#ff8c00'),
        source: v('--aurelia-highlight', '#facc15'),
        author: v('--aurelia-secondary', '#8a2be2'),
        discipline: v('--aurelia-accent', '#39ff14'),
        'gemini-notebook': v('--aurelia-info', '#818cf8'),
        'deep-dive': v('--aurelia-insight', '#ff2d78'),
    };
}
export function graphColorFor(type, typeColors, fallback) {
    for (const key in typeColors) if (type.includes(key)) return typeColors[key];
    return fallback;
}

// Shared by initGraph()'s canvas path and renderGraphList() below --
// both need every node's degree, and computing it is O(nodes+edges)
// either way, so there's no reason for the list path to wait on
// state.graphState (which also carries the force-directed layout, the
// expensive part this function deliberately skips in list mode).
export function computeGraphDegrees() {
    const degree = {};
    GRAPH_INDEX.nodes.forEach(n => degree[n.id] = 0);
    GRAPH_INDEX.edges.forEach(e => {
        degree[e.source] = (degree[e.source] || 0) + 1;
        degree[e.target] = (degree[e.target] || 0) + 1;
    });
    return degree;
}

export function isGraphListMode() {
    return window.innerWidth < 768;
}

// Small-screen fallback for the knowledge graph (Phase 4): drag-to-pan
// and scroll-to-zoom don't work well below 768px, and the graph used
// to just render illegibly small there. Lists the top 30 notes by
// degree, filtered through the same graphNodeMatches() the canvas's
// own dimming uses, so it honors the active type filter/search too.
// Makes the graph's content reachable on a phone for the first time --
// not a substitute for the graph's actual shape.
export function renderGraphList() {
    const container = document.getElementById('graph-list-items');
    const empty = document.getElementById('graph-list-empty');
    if (!container) return;
    const degree = computeGraphDegrees();
    const matches = GRAPH_INDEX.nodes
        .filter(graphNodeMatches)
        .sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0))
        .slice(0, 30);

    if (empty) empty.classList.toggle('hidden', matches.length > 0);
    // Elements, not an HTML string: the ids and titles come from the page's
    // data blocks (dom.js, el()).
    container.replaceChildren(...matches.map((n) => {
        const d = degree[n.id] || 0;
        return el('li', {}, [
            el('button', { className: 'graph-list-row', dataset: { note: n.id }, attrs: { type: 'button' } }, [
                el('span', { className: 'graph-list-title', text: n.title }),
                el('span', { className: 'graph-list-degree', text: `◉ ${d} ${d === 1 ? 'LINK' : 'LINKS'}` }),
            ]),
        ]);
    }));
}

// Only announces the list-mode switch on an actual transition into it
// (see initGraph() below) -- initGraph() also re-runs on every resize
// while the graph view is active, and re-announcing on each of those
// while already in list mode would spam a screen reader for no reason.
let lastGraphListMode = null;

export function initGraph() {
    const canvas = document.getElementById('graph-canvas');
    const wrap = document.getElementById('graph-canvas-wrap');
    const list = document.getElementById('graph-list');
    if (!canvas || !wrap) return;

    // The pan/zoom hint describes the canvas; in list mode it would be
    // instructing the reader to drag a list.
    const hint = document.getElementById('graph-hint');
    if (isGraphListMode()) {
        wrap.classList.add('hidden');
        if (list) list.classList.remove('hidden');
        if (hint) hint.classList.add('hidden');
        renderGraphList();
        if (lastGraphListMode !== true) announce('Graph view, shown as a list on small screens');
        lastGraphListMode = true;
        return;
    }
    if (list) list.classList.add('hidden');
    if (hint) hint.classList.remove('hidden');
    wrap.classList.remove('hidden');
    lastGraphListMode = false;

    /* Backing store in device pixels, drawing surface in CSS pixels --
       same reasoning as the neural canvas above.

       graphSize exists because of the trap in doing this: drawGraph()
       and graphNodeAt() both used to read canvas.width/canvas.height for
       the centre point, and graphNodeAt() mixes that with
       `e.clientX - rect.left`, which is CSS pixels. Scale the backing
       store without touching them and the graph renders sharper while
       hit-testing silently goes wrong -- clicking a node opens a
       different note, with no error anywhere. Both now read graphSize. */
    const width = wrap.clientWidth, height = wrap.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    canvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
    graphSize = { width, height };

    if (!state.graphState) {
        const degree = {};
        GRAPH_INDEX.nodes.forEach(n => degree[n.id] = 0);
        GRAPH_INDEX.edges.forEach(e => { degree[e.source] = (degree[e.source] || 0) + 1; degree[e.target] = (degree[e.target] || 0) + 1; });

        const nodes = GRAPH_INDEX.nodes.map((n, i) => {
            const angle = (i / Math.max(GRAPH_INDEX.nodes.length, 1)) * Math.PI * 2;
            return Object.assign({}, n, { degree: degree[n.id] || 0, x: Math.cos(angle) * 200, y: Math.sin(angle) * 200 });
        });
        state.graphState = { nodes, edges: GRAPH_INDEX.edges, byId: {}, laidOut: false };
        nodes.forEach(n => state.graphState.byId[n.id] = n);
    }

    if (!state.graphState.laidOut && state.graphState.nodes.length > 0) {
        layoutGraph(width, height);
        state.graphState.laidOut = true;
    }

    bindGraphInteractions(canvas);
    drawGraph();
}

export function layoutGraph(width, height) {
    const nodes = state.graphState.nodes;
    const edges = state.graphState.edges;
    const area = width * height;
    const k = Math.sqrt(area / Math.max(nodes.length, 1)) * 0.9;
    let temperature = Math.max(width, height) / 8;
    const iterations = nodes.length > 300 ? 80 : 150;

    for (let iter = 0; iter < iterations; iter++) {
        nodes.forEach(n => { n.fx = 0; n.fy = 0; });

        for (let a = 0; a < nodes.length; a++) {
            for (let b = a + 1; b < nodes.length; b++) {
                const dx = nodes[a].x - nodes[b].x, dy = nodes[a].y - nodes[b].y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
                const force = (k * k) / dist;
                const fx = (dx / dist) * force, fy = (dy / dist) * force;
                nodes[a].fx += fx; nodes[a].fy += fy;
                nodes[b].fx -= fx; nodes[b].fy -= fy;
            }
        }

        edges.forEach(e => {
            const s = state.graphState.byId[e.source], t = state.graphState.byId[e.target];
            if (!s || !t) return;
            const dx = s.x - t.x, dy = s.y - t.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
            const force = (dist * dist) / k;
            const fx = (dx / dist) * force, fy = (dy / dist) * force;
            s.fx -= fx; s.fy -= fy;
            t.fx += fx; t.fy += fy;
        });

        nodes.forEach(n => {
            n.fx -= n.x * 0.01;
            n.fy -= n.y * 0.01;
            const disp = Math.sqrt(n.fx * n.fx + n.fy * n.fy) || 0.01;
            const clamped = Math.min(disp, temperature);
            n.x += (n.fx / disp) * clamped;
            n.y += (n.fy / disp) * clamped;
        });

        temperature *= 0.95;
    }
}

export function bindGraphInteractions(canvas) {
    if (canvas.dataset.bound) return;
    canvas.dataset.bound = '1';

    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 0.9;
        graphPan.scale = Math.min(4, Math.max(0.2, graphPan.scale * factor));
        drawGraph();
    }, { passive: false });

    canvas.addEventListener('mousedown', (e) => {
        graphPan.dragging = true; graphPan.lastX = e.clientX; graphPan.lastY = e.clientY;
        canvas.style.cursor = 'grabbing';
    });
    window.addEventListener('mouseup', () => { graphPan.dragging = false; canvas.style.cursor = 'grab'; });
    canvas.addEventListener('mousemove', (e) => {
        if (graphPan.dragging) {
            graphPan.x += e.clientX - graphPan.lastX;
            graphPan.y += e.clientY - graphPan.lastY;
            graphPan.lastX = e.clientX; graphPan.lastY = e.clientY;
            drawGraph();
            return;
        }
        const hit = graphNodeAt(canvas, e);
        const tooltip = document.getElementById('graph-tooltip');
        if (hit) {
            canvas.style.cursor = 'pointer';
            tooltip.classList.remove('hidden');
            tooltip.style.left = `${e.clientX - canvas.getBoundingClientRect().left + 14}px`;
            tooltip.style.top = `${e.clientY - canvas.getBoundingClientRect().top + 10}px`;
            tooltip.innerHTML = `${escapeHtml(hit.title)} <span class="opacity-50">· ${escapeHtml(hit.type)}</span>`;
        } else {
            canvas.style.cursor = 'grab';
            tooltip.classList.add('hidden');
        }
    });
    canvas.addEventListener('mouseleave', () => { document.getElementById('graph-tooltip').classList.add('hidden'); });

    canvas.addEventListener('click', (e) => {
        const hit = graphNodeAt(canvas, e);
        if (hit) openNote(hit.id);
    });
}

export function graphNodeAt(canvas, e) {
    if (!state.graphState) return null;
    const rect = canvas.getBoundingClientRect();
    // graphSize, not canvas.width/height: those are device pixels now, and
    // they are being combined with clientX/rect, which are CSS pixels.
    const cx = graphSize.width / 2 + graphPan.x, cy = graphSize.height / 2 + graphPan.y;
    const mx = (e.clientX - rect.left - cx) / graphPan.scale;
    const my = (e.clientY - rect.top - cy) / graphPan.scale;
    for (const n of state.graphState.nodes) {
        const r = 4 + Math.min(n.degree, 12);
        const dx = n.x - mx, dy = n.y - my;
        if (dx * dx + dy * dy <= (r + 4) * (r + 4)) return n;
    }
    return null;
}

export function drawGraph() {
    const canvas = document.getElementById('graph-canvas');
    const empty = document.getElementById('graph-empty');
    if (!canvas || !state.graphState) return;
    const ctx = canvas.getContext('2d');
    // CSS pixels: the context carries a devicePixelRatio transform from
    // initGraph, so all drawing below stays in the same coordinate space
    // the layout and the pointer handlers use.
    const width = graphSize.width, height = graphSize.height;
    ctx.clearRect(0, 0, width, height);

    const cx = width / 2 + graphPan.x, cy = height / 2 + graphPan.y;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(graphPan.scale, graphPan.scale);

    const visible = new Set();
    state.graphState.nodes.forEach(n => { if (graphNodeMatches(n)) visible.add(n.id); });
    if (empty) empty.classList.toggle('hidden', visible.size > 0);

    // Read live theme colors once per draw (cheap: two custom-property
    // reads, not per-edge/per-node) -- these used to be hardcoded cyan
    // edges and white labels, invisible on a light theme's background.
    const rootStyle = getComputedStyle(document.documentElement);
    const primaryRgb = (rootStyle.getPropertyValue('--aurelia-primary-rgb').trim() || '0 242 255').replace(/\s+/g, ', ');
    const textRgb = (rootStyle.getPropertyValue('--aurelia-text-main-rgb').trim() || '255 255 255').replace(/\s+/g, ', ');
    const mutedRgb = (rootStyle.getPropertyValue('--aurelia-text-muted-rgb').trim() || '107 114 128').replace(/\s+/g, ', ');
    const typeColors = graphTypeColors(rootStyle);

    ctx.lineWidth = 1 / graphPan.scale;
    state.graphState.edges.forEach(e => {
        const s = state.graphState.byId[e.source], t = state.graphState.byId[e.target];
        if (!s || !t) return;
        const active = visible.has(s.id) && visible.has(t.id);
        ctx.strokeStyle = active ? `rgba(${primaryRgb}, 0.25)` : `rgba(${mutedRgb}, 0.08)`;
        ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke();
    });

    state.graphState.nodes.forEach(n => {
        const active = visible.has(n.id);
        const r = 4 + Math.min(n.degree, 12);
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.globalAlpha = active ? 1 : 0.3;
        ctx.fillStyle = active ? graphColorFor(n.type, typeColors, `rgb(${mutedRgb})`) : `rgb(${mutedRgb})`;
        ctx.fill();
        ctx.globalAlpha = 1;

        if (active && (state.graphState.nodes.length < 60 || r > 8)) {
            ctx.font = `${11 / graphPan.scale}px 'JetBrains Mono', monospace`;
            ctx.fillStyle = `rgba(${textRgb}, 0.85)`;
            ctx.fillText(n.title, n.x + r + 4, n.y + 3);
        }
    });

    ctx.restore();
}

export function initGraphResize() {
    window.addEventListener('resize', () => { if (state.currentView === 'graph') initGraph(); });
}
