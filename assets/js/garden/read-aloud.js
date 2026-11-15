/**
 * Read aloud: the reader's speech button and its voice and rate panel, on the
 * browser's own Web Speech API.
 *
 * Part of the Garden's page script, split into modules in roadmap S13.
 * Nothing here runs at import time; main.js calls the init functions in
 * order.
 */
import { modalContent } from './dom.js';

// --- READ ALOUD (Web Speech API) ---
// Free, no API key, no backend -- the only option that can read an
// arbitrary highlighted selection live, not just a pre-rendered whole
// note (see docs/ARCHITECTURE.md: this is a static site with
// no server to hide a cloud-TTS API key behind).
let ttsSupported = false;    // set by initReadAloud()
let ttsState = 'idle';       // 'idle' | 'speaking' | 'paused'
let ttsChunks = [];
let ttsChunkIndex = 0;
let ttsVoice = null;         // SpeechSynthesisVoice
let ttsRate = 1;

export function loadTtsPrefs() {
    try {
        return JSON.parse(localStorage.getItem('aurelia_tts_prefs') || '{}');
    } catch (e) { return {}; }
}
export function saveTtsPrefs() {
    try {
        localStorage.setItem('aurelia_tts_prefs', JSON.stringify({ voiceName: ttsVoice ? ttsVoice.name : null, rate: ttsRate }));
    } catch (e) { /* localStorage unavailable -- prefs just won't persist */ }
}

export function populateVoiceList() {
    const select = document.getElementById('tts-voice-select');
    if (!select) return;
    const voices = speechSynthesis.getVoices();
    if (voices.length === 0) return; // Chrome loads this async -- onvoiceschanged retries below
    const prefs = loadTtsPrefs();
    select.innerHTML = voices.map(v => `<option value="${escapeHtml(v.name)}">${escapeHtml(v.name)} (${escapeHtml(v.lang)})</option>`).join('');
    const match = voices.find(v => v.name === prefs.voiceName) || voices.find(v => v.lang.startsWith('en')) || voices[0];
    if (match) { select.value = match.name; ttsVoice = match; }
    ttsRate = prefs.rate || 1;
    const rateInput = document.getElementById('tts-rate-input');
    const rateLabel = document.getElementById('tts-rate-label');
    if (rateInput) rateInput.value = ttsRate;
    if (rateLabel) rateLabel.innerText = `${parseFloat(ttsRate).toFixed(1)}x`;
}

export function onVoiceChange(name) {
    const match = speechSynthesis.getVoices().find(v => v.name === name);
    if (match) { ttsVoice = match; saveTtsPrefs(); }
}
export function onRateChange(value) {
    ttsRate = parseFloat(value);
    const rateLabel = document.getElementById('tts-rate-label');
    if (rateLabel) rateLabel.innerText = `${ttsRate.toFixed(1)}x`;
    saveTtsPrefs();
}

export function toggleTtsSettings() {
    const panel = document.getElementById('tts-settings-panel');
    const open = panel.classList.toggle('hidden') === false;
    // Mirrors the panel's state onto the button, so the control reports
    // whether its popover is showing instead of looking identical either way.
    const btn = document.getElementById('btn-tts-settings');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

// Sentence-ish chunks, not one utterance for the whole note -- Chrome has
// a long-standing bug where a very long utterance can silently stop
// mid-read. This also gives pause/resume a natural granularity to work
// at without relying on the native (cross-browser flaky) pause/resume.
export function splitIntoChunks(text) {
    return text.replace(/\s+/g, ' ').trim().match(/[^.!?]+[.!?]*/g) || [];
}

// The read-aloud control is an icon button (see .reader-icon-btn), so
// state is carried by the icon plus aria-pressed/aria-label rather than
// by replacing the button's text -- the emoji-and-word label it used to
// swap in was part of what overflowed the footer on a phone.
export const TTS_ICONS = {
    idle: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072M17.657 6.343a8 8 0 010 11.314M11 5L6 9H3v6h3l5 4V5z"></path>',
    speaking: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6M14 9v6"></path><circle cx="12" cy="12" r="9" stroke-width="2"></circle>',
    paused: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 8l6 4-6 4V8z"></path><circle cx="12" cy="12" r="9" stroke-width="2"></circle>',
};
export const TTS_LABELS = { idle: 'Read this note aloud', speaking: 'Pause reading', paused: 'Resume reading' };

export function updateTtsButton() {
    const btn = document.getElementById('btn-read-aloud');
    if (!btn) return;
    btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">${TTS_ICONS[ttsState]}</svg>`;
    btn.setAttribute('aria-label', TTS_LABELS[ttsState]);
    btn.setAttribute('aria-pressed', ttsState === 'idle' ? 'false' : 'true');
}

export function speakChunk() {
    if (ttsChunkIndex >= ttsChunks.length) { stopReading(); return; }
    const utter = new SpeechSynthesisUtterance(ttsChunks[ttsChunkIndex]);
    if (ttsVoice) utter.voice = ttsVoice;
    utter.rate = ttsRate;
    utter.onend = () => { ttsChunkIndex++; if (ttsState === 'speaking') speakChunk(); };
    utter.onerror = () => { ttsChunkIndex++; if (ttsState === 'speaking') speakChunk(); };
    speechSynthesis.speak(utter);
}

export function startReading() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();
    const inModal = selectedText && modalContent.contains(selection.anchorNode);
    // .textContent, not .innerText -- .innerText reflects rendered layout
    // and would silently skip any collapsed Gemini Notebook <details>
    // section; "read the whole note" should mean all of it.
    const source = inModal ? selectedText : modalContent.textContent;
    ttsChunks = splitIntoChunks(source);
    ttsChunkIndex = 0;
    ttsState = 'speaking';
    updateTtsButton();
    speakChunk();
}

export function pauseReading() {
    // State flips before cancel() -- the resulting onend/onerror above
    // checks ttsState before auto-advancing, so this is what actually
    // stops the chunk queue rather than just skipping to the next chunk.
    ttsState = 'paused';
    speechSynthesis.cancel();
    updateTtsButton();
}

export function resumeReading() {
    ttsState = 'speaking';
    updateTtsButton();
    speakChunk();
}

export function stopReading() {
    if (!ttsSupported) return;
    speechSynthesis.cancel();
    ttsState = 'idle';
    ttsChunks = [];
    ttsChunkIndex = 0;
    updateTtsButton();
}

export function toggleReading() {
    if (!ttsSupported) return;
    if (ttsState === 'idle') startReading();
    else if (ttsState === 'speaking') pauseReading();
    else resumeReading();
}

export function initReadAloud() {
    ttsSupported = 'speechSynthesis' in window;
    // Paint the idle icon at load: the button ships empty so the icon has a
    // single source of truth here rather than one copy in the markup and
    // another in this map, which would drift the moment either changed.
    updateTtsButton();
    if (!ttsSupported) {
        const btn = document.getElementById('btn-read-aloud');
        const settingsBtn = document.getElementById('btn-tts-settings');
        if (btn) btn.classList.add('hidden');
        if (settingsBtn) settingsBtn.classList.add('hidden');
        return;
    }
    populateVoiceList();
    speechSynthesis.onvoiceschanged = populateVoiceList;
}
