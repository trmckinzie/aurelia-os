/**
 * AURELIA // FLASHCARD DECK WIDGET (window.upgradeFlashcardDecks)
 *
 * Upgrades every `<ol class="deck" data-deck="...">` list (see
 * engine/content.py's _render_flashcards) into an interactive one-card-at-
 * a-time study widget: reveal, SM-2 rating via window.Review's deck-bucket
 * API (assets/js/review.js's rateCard/cardState/isCardDue), shuffle, and a
 * "due cards only" filter. The no-JS list itself is left in the DOM (just
 * `hidden`), so a reader with JS off -- or a browser that never runs this
 * file -- still gets sensible, readable Q/A pairs.
 *
 * Decks live inside a note's body, which gardentemplate.html's openNote()
 * renders on demand (marked.parse() on every open, not just once at page
 * load) -- so upgradeFlashcardDecks() has to be called after EVERY
 * openNote(), not only here at load time. This file only registers a
 * DOMContentLoaded call for the page-load case (a no-op today: no deck
 * lives outside the note-reader modal); openNote() itself calls
 * upgradeFlashcardDecks(modalContent) directly -- see gardentemplate.html.
 *
 * Each upgraded deck is marked `data-upgraded` so re-opening the same note
 * (history back/forward, or a second openNote() call) never double-builds
 * its widget.
 *
 * Keyboard scope is deliberately narrow: the one custom keydown listener
 * per widget lives on the widget element itself, not document, and it
 * only ever handles the 1-4 rating shortcuts (after Reveal). Space/Enter
 * on "Show answer" is native <button> activation (plus an explicit
 * preventDefault()-guarded keydown mirroring the note reader's recall-
 * cover Reveal button in gardentemplate.html, so the synthetic click a
 * browser fires for Space/Enter never doubles up with it) -- nothing here
 * intercepts Space at the container level, so it can never fight the
 * modal's own scroll or another control's native activation (Shuffle,
 * the nav arrows, the due-only checkbox).
 */
(function () {
    'use strict';

    var PREFS_KEY = 'aurelia_deck_prefs';

    // --- per-deck "due only" preference, keyed by deck asset path ---------
    // Same try/catch discipline as review.js: Safari private-mode throws on
    // any localStorage access, and a throw here must never break the reader.

    function loadPrefs() {
        try {
            var raw = localStorage.getItem(PREFS_KEY);
            var parsed = raw ? JSON.parse(raw) : null;
            return (parsed && typeof parsed === 'object') ? parsed : {};
        } catch (e) {
            return {};
        }
    }

    function getDueOnlyPref(deckKey) {
        var prefs = loadPrefs();
        return !!(prefs[deckKey] && prefs[deckKey].dueOnly);
    }

    function setDueOnlyPref(deckKey, dueOnly) {
        try {
            var prefs = loadPrefs();
            prefs[deckKey] = prefs[deckKey] || {};
            prefs[deckKey].dueOnly = !!dueOnly;
            localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
        } catch (e) { /* private mode / quota -- the toggle still works this visit */ }
    }

    function shuffleInPlace(arr) {
        for (var i = arr.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1));
            var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
        }
        return arr;
    }

    // announce()/isTypingTarget() live in gardentemplate.html's own inline
    // script, which runs AFTER this file (loaded earlier in head_extra) --
    // but neither is called until a user interacts with an already-open
    // widget, by which point the page has fully parsed and both exist on
    // window. Guarded anyway, the same defensiveness review.js gives
    // `window.Review` everywhere it's used.
    function announceIfPresent(text) {
        if (typeof window.announce === 'function') window.announce(text);
    }

    function isTypingTargetSafe(e) {
        return typeof window.isTypingTarget === 'function' ? window.isTypingTarget(e) : false;
    }

    var RATE_BUTTONS = [
        { grade: 1, label: 'Again', key: '1' },
        { grade: 2, label: 'Hard', key: '2' },
        { grade: 3, label: 'Good', key: '3' },
        { grade: 4, label: 'Easy', key: '4' }
    ];

    function buildWidgetShell() {
        var el = document.createElement('div');
        el.className = 'deck-widget';
        el.innerHTML =
            '<div class="deck-widget-toolbar">' +
                '<label class="deck-due-toggle">' +
                    '<input type="checkbox" class="deck-due-checkbox">' +
                    '<span>Study due cards only</span>' +
                '</label>' +
                '<button type="button" class="rate-btn deck-shuffle-btn">Shuffle</button>' +
            '</div>' +
            '<div class="deck-widget-body"></div>' +
            '<div class="deck-widget-nav">' +
                '<button type="button" class="rate-btn deck-nav-btn" data-dir="-1" aria-label="Previous card">‹</button>' +
                '<p class="deck-progress"></p>' +
                '<button type="button" class="rate-btn deck-nav-btn" data-dir="1" aria-label="Next card">›</button>' +
            '</div>';
        return el;
    }

    function upgradeOneDeck(deckEl) {
        // Marked first, before any early return, so a deck with zero usable
        // rows (every row skipped by _render_flashcards' own <2-column
        // guard) is never re-scanned on the next upgradeFlashcardDecks() call.
        deckEl.setAttribute('data-upgraded', '1');

        var deckKey = deckEl.getAttribute('data-deck') || '';
        var cardEls = Array.prototype.slice.call(deckEl.querySelectorAll('.deck-card'));
        var cards = cardEls.map(function (li) {
            var qEl = li.querySelector('.deck-q');
            var aEl = li.querySelector('.deck-a');
            // .textContent, never innerHTML -- these come back already
            // decoded from the parsed DOM, and re-inserting them as HTML
            // anywhere below would reopen exactly the injection sink
            // engine/sanitize.py's sanitize_to_text() docstring describes.
            return { q: qEl ? qEl.textContent : '', a: aEl ? aEl.textContent : '' };
        });
        if (cards.length === 0) return;

        deckEl.hidden = true;

        var widget = buildWidgetShell();
        deckEl.parentNode.insertBefore(widget, deckEl.nextSibling);

        var body = widget.querySelector('.deck-widget-body');
        var progressEl = widget.querySelector('.deck-progress');
        var dueCheckbox = widget.querySelector('.deck-due-checkbox');
        var shuffleBtn = widget.querySelector('.deck-shuffle-btn');
        var prevBtn = widget.querySelector('.deck-nav-btn[data-dir="-1"]');
        var nextBtn = widget.querySelector('.deck-nav-btn[data-dir="1"]');

        var allIndices = cards.map(function (_, i) { return i; });

        var state = {
            order: allIndices.slice(),
            pos: 0,
            revealed: false,
            dueOnly: getDueOnlyPref(deckKey)
        };
        dueCheckbox.checked = state.dueOnly;

        // True only for a card rated before AND now due -- Review.isCardDue
        // mirrors Review.isDue for notes, so a never-studied deck has zero
        // "due" cards until its first rating (see review.js). That is what
        // makes the empty-state copy below ("Nothing due... N scheduled")
        // correct on a fresh deck, not just on one that's fully caught up.
        function dueIndices() {
            return allIndices.filter(function (i) {
                return window.Review && Review.isCardDue(deckKey, i);
            });
        }

        // Rebuilds state.order from the current dueOnly setting.
        // preserveOrder keeps whatever relative order a prior shuffle left
        // (filtered down to whichever of those indices still qualify),
        // rather than snapping back to deck order every time the filter is
        // toggled or a rating changes which cards are due.
        function recomputeOrder(preserveOrder) {
            var base = state.dueOnly ? dueIndices() : allIndices.slice();
            if (preserveOrder) {
                var kept = state.order.filter(function (i) { return base.indexOf(i) !== -1; });
                base.forEach(function (i) { if (kept.indexOf(i) === -1) kept.push(i); });
                base = kept;
            }
            state.order = base;
            state.pos = 0;
            state.revealed = false;
        }

        function currentIndex() { return state.order[state.pos]; }

        var firstRender = true;

        // Focus is deliberately NOT moved on the very first render (a cold
        // mount, e.g. right after openNote() -- forcing focus down into a
        // note's flashcard section the reader hasn't scrolled to yet would
        // be the same "steals focus out from under you" bug Phase 2's
        // reader fixes elsewhere). Every render AFTER that is the direct
        // result of a user interaction (Reveal, rate, nav, shuffle, toggle),
        // and body.innerHTML is rebuilt wholesale on each one -- so without
        // this, focus would fall out to <body> exactly the way Phase 2's
        // own "Risks" section warns auto-advance can.
        function focusAfterRender() {
            if (firstRender) { firstRender = false; return; }
            if (state.order.length === 0) {
                var studyAllBtn = body.querySelector('.deck-study-all-btn');
                if (studyAllBtn) studyAllBtn.focus({ preventScroll: true });
                return;
            }
            var target = state.revealed
                ? body.querySelector('button[data-grade]')
                : body.querySelector('.deck-reveal-btn');
            if (target) target.focus({ preventScroll: true });
        }

        function renderEmpty() {
            body.innerHTML =
                '<p class="deck-empty"></p>' +
                '<button type="button" class="rate-btn deck-study-all-btn">Study all</button>';
            body.querySelector('.deck-empty').textContent =
                'Nothing due in this deck. ' + cards.length + ' cards scheduled.';
            body.querySelector('.deck-study-all-btn').addEventListener('click', function () {
                state.dueOnly = false;
                dueCheckbox.checked = false;
                setDueOnlyPref(deckKey, false);
                recomputeOrder(false);
                render();
                announceIfPresent('Studying all ' + cards.length + ' cards.');
            });
            progressEl.textContent = '';
            prevBtn.disabled = true;
            nextBtn.disabled = true;
        }

        function renderCard() {
            var idx = currentIndex();
            var card = cards[idx];
            prevBtn.disabled = state.order.length <= 1;
            nextBtn.disabled = state.order.length <= 1;
            progressEl.textContent = (state.pos + 1) + ' of ' + state.order.length;

            if (!state.revealed) {
                body.innerHTML =
                    '<p class="deck-question"></p>' +
                    '<button type="button" class="rate-btn deck-reveal-btn">Show answer</button>';
                body.querySelector('.deck-question').textContent = card.q;
                var revealBtn = body.querySelector('.deck-reveal-btn');
                revealBtn.addEventListener('click', reveal);
                // Mirrors gardentemplate.html's recall-cover Reveal button
                // exactly: preventDefault() here stops the browser's own
                // synthetic click for Space/Enter, so reveal() runs once,
                // not twice.
                revealBtn.addEventListener('keydown', function (e) {
                    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); reveal(); }
                });
            } else {
                body.innerHTML =
                    '<p class="deck-question"></p>' +
                    '<p class="deck-answer"></p>' +
                    '<div class="rate-row" role="group" aria-label="How well did you remember it?">' +
                        '<p class="field-label text-aurelia-muted w-full">How well did you remember it?</p>' +
                        RATE_BUTTONS.map(function (r) {
                            return '<button type="button" class="rate-btn" data-grade="' + r.grade + '">' +
                                '<span>' + r.label + '</span>' +
                                '<span class="rate-key" aria-hidden="true">' + r.key + '</span>' +
                            '</button>';
                        }).join('') +
                    '</div>';
                body.querySelector('.deck-question').textContent = card.q;
                body.querySelector('.deck-answer').textContent = card.a;
                body.querySelectorAll('button[data-grade]').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        rate(parseInt(btn.getAttribute('data-grade'), 10));
                    });
                });
            }
            focusAfterRender();
        }

        function render() {
            if (state.order.length === 0) { renderEmpty(); focusAfterRender(); return; }
            renderCard();
        }

        function reveal() {
            state.revealed = true;
            render();
        }

        function go(direction) {
            if (state.order.length === 0) return;
            state.pos = (state.pos + direction + state.order.length) % state.order.length;
            state.revealed = false;
            render();
            announceIfPresent('Card ' + (state.pos + 1) + ' of ' + state.order.length);
        }

        function rate(grade) {
            if (!window.Review) return;
            var idx = currentIndex();
            Review.rateCard(deckKey, idx, grade);
            if (state.dueOnly) {
                // A fresh rating can move this card in or out of "due" --
                // rebuild the filtered set rather than just advancing pos,
                // so the progress count stays honest under the filter.
                recomputeOrder(true);
                render();
                announceIfPresent(state.order.length === 0
                    ? 'Nothing due in this deck.'
                    : 'Card 1 of ' + state.order.length);
            } else {
                go(1);
            }
        }

        dueCheckbox.addEventListener('change', function () {
            state.dueOnly = dueCheckbox.checked;
            setDueOnlyPref(deckKey, state.dueOnly);
            recomputeOrder(true);
            render();
            announceIfPresent(state.order.length === 0
                ? 'Nothing due in this deck.'
                : 'Card 1 of ' + state.order.length);
        });

        shuffleBtn.addEventListener('click', function () {
            shuffleInPlace(state.order);
            state.pos = 0;
            state.revealed = false;
            render();
            announceIfPresent('Shuffled. Card 1 of ' + state.order.length);
        });

        prevBtn.addEventListener('click', function () { go(-1); });
        nextBtn.addEventListener('click', function () { go(1); });

        // The ONLY listener scoped to the widget rather than to one button
        // -- handles just the 1-4 rating shortcuts, and only once a card is
        // revealed. Deliberately does nothing with Space/Enter (see the
        // module docstring): those stay native button activation on
        // whichever control actually has focus, so this can never hijack
        // Shuffle/the nav arrows/the due-only checkbox's own Space handling.
        widget.addEventListener('keydown', function (e) {
            if (isTypingTargetSafe(e)) return;
            if (!state.revealed) return;
            if (e.key !== '1' && e.key !== '2' && e.key !== '3' && e.key !== '4') return;
            var btn = body.querySelector('button[data-grade="' + e.key + '"]');
            if (btn && !btn.disabled) { e.preventDefault(); btn.click(); }
        });

        recomputeOrder(false);
        render();
    }

    function upgradeFlashcardDecks(root) {
        var scope = root || document;
        if (typeof scope.querySelectorAll !== 'function') return;
        var decks = scope.querySelectorAll('.deck:not([data-upgraded])');
        decks.forEach(function (deckEl) { upgradeOneDeck(deckEl); });
    }

    window.upgradeFlashcardDecks = upgradeFlashcardDecks;

    // Safety net for the page-load case -- see the module docstring for why
    // this is a no-op today (every deck lives inside a note body, rendered
    // on demand by openNote(), which calls upgradeFlashcardDecks(modalContent)
    // itself; see gardentemplate.html).
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { upgradeFlashcardDecks(document); });
    } else {
        upgradeFlashcardDecks(document);
    }
})();
