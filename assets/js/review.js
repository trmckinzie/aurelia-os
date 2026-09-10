/**
 * AURELIA // REVIEW ENGINE (window.Review)
 *
 * Pure data/logic module: an SM-2-style spaced-repetition scheduler plus the
 * localStorage log it reads and writes. No DOM work happens at load time --
 * this file is safe to load early (see gardentemplate.html/indextemplate.html
 * head_extra), and every function that touches the page (the recall cover,
 * the due-count teaser, the rating buttons) lives elsewhere and calls into
 * this module rather than the other way around.
 *
 * localStorage key: "aurelia_review_log" -- the SAME key the 2026-09-07
 * spaced-review feature used (see that commit), kept on purpose so a
 * visitor's real review history survives the rebuild. The SHAPE is new
 * (v2, see below); v1 data (a flat {noteId: millis} map, no `version` key)
 * is migrated lazily on read rather than eagerly on every page load -- see
 * load() and migrateV1() below.
 *
 *   {
 *     version: 2,
 *     notes: { "note-id": { last, due, interval, ease, reps, lapses } },
 *     decks: { "assets/flashcards/x.csv": { "12": { ...same shape } } }
 *   }
 *
 * `notes` is keyed by note id and is what Phase 2 (the recall-cover / due-
 * queue feature on the Garden) reads or writes through the public API
 * below. `decks` is keyed by deck asset path, then by card index, and is
 * written by Phase 3's assets/js/flashcards.js through rateCard()/
 * cardState()/isCardDue() -- the deck-bucket equivalents of rate()/
 * stateFor()/isDue(), sharing the same _computeNextState scheduling core.
 * Both buckets are carried through intact by save()/export()/import().
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'aurelia_review_log';
    var ONE_DAY_MS = 24 * 60 * 60 * 1000;

    // Seed interval (in days) for a note's FIRST successful rep, keyed by
    // its maturity (seed/growing/evergreen -- see engine/cards.py's
    // _maturity_badge). A less-developed note is reviewed sooner: a seed is
    // raw capture, most likely to be forgotten or to need rewriting, while
    // an evergreen note has already proven durable.
    var SEED_INTERVAL_DAYS = { seed: 1, growing: 3, evergreen: 7 };
    var DEFAULT_SEED_INTERVAL_DAYS = SEED_INTERVAL_DAYS.seed;

    var DEFAULT_EASE = 2.5;
    var MIN_EASE = 1.3;

    // Grade (1-4, what the rating buttons show as Again/Hard/Good/Easy) to
    // SM-2's own 0-5 quality scale. SM-2 only really distinguishes "failed"
    // (q < 3) from three shades of "recalled it" (q 3/4/5); collapsing the
    // reader-facing four-point scale onto that range is the standard
    // adaptation (used by Anki and most SM-2 implementations), not a
    // simplification specific to this build.
    var GRADE_TO_QUALITY = { 1: 0, 2: 3, 3: 4, 4: 5 };

    // --- localStorage plumbing ----------------------------------------
    // Every read/write is wrapped: Safari private-mode throws on *any*
    // localStorage access (not just when the quota is exceeded), and a
    // throw here must never break the reader it's called from.

    function emptyLog() {
        return { version: 2, notes: {}, decks: {} };
    }

    function readRaw() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    function writeRaw(log) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(log));
            return true;
        } catch (e) {
            // Quota exceeded, private-mode throw, or JSON that somehow
            // failed to stringify -- the caller already has the log in
            // memory for this session, so a failed persist degrades to
            // "this rating won't survive a reload" rather than a crash.
            return false;
        }
    }

    // True for the pre-2026-09 shape: a flat object mapping note id to a
    // raw millisecond timestamp, with no `version`/`notes`/`decks` keys at
    // all (those are new in v2, so their absence is what marks a v1 blob).
    function looksLikeV1(parsed) {
        return !!parsed && typeof parsed === 'object' && !Array.isArray(parsed) &&
            parsed.version === undefined && parsed.notes === undefined && parsed.decks === undefined;
    }

    // Turns a v1 { noteId: millis } map into a v2 log. `getMaturity(id)`
    // looks up the note's seed/growing/evergreen maturity (read from its
    // card's data-maturity attribute -- only the Garden page has that DOM
    // context, which is why migration is opt-in via this callback rather
    // than automatic). A note whose maturity can't be determined falls back
    // to the seed interval, the most conservative (soonest-due) choice.
    function migrateV1(parsed, getMaturity) {
        var log = emptyLog();
        Object.keys(parsed).forEach(function (id) {
            var last = parsed[id];
            if (typeof last !== 'number' || !isFinite(last)) return;
            var maturity = getMaturity ? getMaturity(id) : null;
            var intervalDays = SEED_INTERVAL_DAYS[maturity] || DEFAULT_SEED_INTERVAL_DAYS;
            log.notes[id] = {
                last: last,
                interval: intervalDays,
                due: last + intervalDays * ONE_DAY_MS,
                ease: DEFAULT_EASE,
                reps: 1,
                lapses: 0
            };
        });
        return log;
    }

    // In-memory cache, populated by the first load() this page makes and
    // kept current by every rate()/import() call after that. Avoids
    // re-parsing localStorage (and, on the Garden, re-running migration) on
    // every single stateFor()/isDue() check inside a due-marker sweep over
    // 245 cards.
    var _log = null;

    /**
     * Reads the log from localStorage, migrating a v1 blob if `options.
     * getMaturity` is given. Always returns a valid v2-shaped object, never
     * null/undefined, so callers never have to null-check the result.
     *
     * `options.getMaturity(noteId) -> 'seed'|'growing'|'evergreen'|falsy`
     * When omitted (the Lobby's read-only due-count reader has no note DOM
     * to read maturity from), a v1 blob is left un-migrated and treated as
     * empty -- its entries genuinely cannot be interpreted as "due" without
     * a maturity to seed an interval from, and guessing would be worse than
     * showing nothing. The Garden always passes getMaturity, migrates on
     * first load, and should call save() right after so the migration is
     * persisted rather than redone (in memory only) on every reload.
     */
    function load(options) {
        var opts = options || {};
        var parsed = readRaw();

        if (!parsed || typeof parsed !== 'object') {
            _log = emptyLog();
            return _log;
        }

        if (parsed.version === 2) {
            // Tolerate a v2 blob missing one of the two buckets (an export
            // taken before `decks` existed, or a hand-edited import) rather
            // than letting later code throw on a missing property.
            _log = {
                version: 2,
                notes: (parsed.notes && typeof parsed.notes === 'object') ? parsed.notes : {},
                decks: (parsed.decks && typeof parsed.decks === 'object') ? parsed.decks : {}
            };
            return _log;
        }

        if (looksLikeV1(parsed) && typeof opts.getMaturity === 'function') {
            _log = migrateV1(parsed, opts.getMaturity);
            return _log;
        }

        // Either a v1 blob with no migration context, or something that
        // matches neither shape (corrupted/foreign data) -- either way,
        // nothing here can be safely read as review state.
        _log = emptyLog();
        return _log;
    }

    // Returns the cached log, loading with no migration context if nothing
    // has called load() yet on this page. Every read-only public function
    // below goes through this rather than calling load() directly, so a
    // page that never calls load() explicitly (there isn't one today, but
    // nothing requires it) still works.
    function ensureLoaded() {
        if (!_log) load();
        return _log;
    }

    /** Persists `log` (or the current in-memory log if omitted). */
    function save(log) {
        var toWrite = log || ensureLoaded();
        _log = toWrite;
        return writeRaw(toWrite);
    }

    // --- SM-2 scheduling -------------------------------------------------
    //
    //   ease  = max(1.3, ease + 0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    //     Standard SM-2 ease update. A perfect answer (q=5) adds 0.1; a
    //     bare pass (q=3) subtracts a little; anything below the recall
    //     threshold (q<3, "Again") subtracts more. The 1.3 floor keeps a
    //     hard note's interval from shrinking to nothing rep after rep.
    //
    //   On a lapse (q<3, i.e. grade 1/"Again"):
    //     interval = 1 day, lapses += 1, reps reset to 0.
    //     SM-2's own convention: a failed recall restarts the interval
    //     ladder (seed -> 6 days -> interval*ease) from the top rather than
    //     merely stepping back one rung, since a failure means the item
    //     wasn't actually in long-term memory yet, and the seed/growing/
    //     evergreen-scaled first interval is the right place to restart it.
    //     lapses is a pure counter and is NOT reset -- it's the note's
    //     lifetime "how many times has this been forgotten" record.
    //
    //   Else (q>=3, a pass):
    //     reps increments. The interval ladder:
    //       reps was 0 (this is the first successful rep) -> seed by
    //         maturity (seed 1d / growing 3d / evergreen 7d).
    //       reps was 1 (second successful rep)             -> 6 days flat,
    //         the standard SM-2 second-interval constant.
    //       otherwise                                       -> round(interval * ease).
    //
    //   last = now, due = last + interval * ONE_DAY_MS.

    function _computeNextState(prev, grade, maturity, now) {
        var q = GRADE_TO_QUALITY[grade];
        if (q === undefined) {
            throw new Error('Review: invalid grade ' + grade + ' (expected 1-4)');
        }
        now = typeof now === 'number' ? now : Date.now();

        var prevEase = (prev && typeof prev.ease === 'number') ? prev.ease : DEFAULT_EASE;
        var prevReps = (prev && typeof prev.reps === 'number') ? prev.reps : 0;
        var prevLapses = (prev && typeof prev.lapses === 'number') ? prev.lapses : 0;
        var prevInterval = (prev && typeof prev.interval === 'number') ? prev.interval : 0;

        var ease = Math.max(MIN_EASE, prevEase + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02));

        var interval, reps, lapses;
        if (q < 3) {
            interval = 1;
            reps = 0;
            lapses = prevLapses + 1;
        } else {
            reps = prevReps + 1;
            lapses = prevLapses;
            if (prevReps === 0) {
                interval = SEED_INTERVAL_DAYS[maturity] || DEFAULT_SEED_INTERVAL_DAYS;
            } else if (prevReps === 1) {
                interval = 6;
            } else {
                interval = Math.round(prevInterval * ease);
            }
        }

        return {
            last: now,
            due: now + interval * ONE_DAY_MS,
            interval: interval,
            ease: ease,
            reps: reps,
            lapses: lapses
        };
    }

    // --- notes-bucket public API ------------------------------------------

    /**
     * Rates note `id` (grade 1-4), updates its entry in the notes bucket,
     * persists, and returns the new state. `maturity` (seed/growing/
     * evergreen) only matters the first time a note is successfully rated
     * (it seeds the initial interval) -- pass the note's current
     * data-maturity regardless, since a lapsed-then-recovered note re-seeds
     * from it too (see _computeNextState's lapse branch).
     */
    function rate(id, grade, maturity) {
        var log = ensureLoaded();
        var next = _computeNextState(log.notes[id] || null, grade, maturity);
        log.notes[id] = next;
        save(log);
        return next;
    }

    /** The raw stored state for note `id`, or null if it's never been rated. */
    function stateFor(id) {
        var log = ensureLoaded();
        return log.notes[id] || null;
    }

    /**
     * Writes `snapshot` (a state object previously returned by stateFor(),
     * or null) back into the notes bucket for `id`, then persists. Exists
     * for the reader's "Change rating" control (gardentemplate.html): it
     * snapshots stateFor(id) *before* calling rate(), and if the reader
     * asks to change their answer, restores that snapshot here first --
     * putting the log back exactly where it was before the original
     * rate() call ran, so a second rate() call is a clean first attempt
     * rather than a second entry compounding onto the first. `snapshot ===
     * null` means the note had no prior entry at all, so restoring removes
     * it from the log entirely rather than writing a null placeholder.
     */
    function restore(id, snapshot) {
        var log = ensureLoaded();
        if (snapshot) {
            log.notes[id] = snapshot;
        } else {
            delete log.notes[id];
        }
        save(log);
        return snapshot || null;
    }

    /** True only for a note that has been rated before AND is now due. */
    function isDue(id) {
        var state = stateFor(id);
        return !!state && typeof state.due === 'number' && state.due <= Date.now();
    }

    function _bucketDueCount(bucket) {
        var now = Date.now();
        var count = 0;
        Object.keys(bucket).forEach(function (key) {
            var entry = bucket[key];
            if (entry && typeof entry.due === 'number' && entry.due <= now) count++;
        });
        return count;
    }

    /**
     * Counts due notes directly from the log -- deliberately does NOT take
     * a candidate id list, so callers (in particular the Lobby teaser) need
     * no per-note payload from the server to compute this; it only ever
     * looks at what's already in the log.
     */
    function dueCount() {
        return _bucketDueCount(ensureLoaded().notes);
    }

    /** Filters `candidateIds` down to the ones that are due, in order. */
    function dueIds(candidateIds) {
        return (candidateIds || []).filter(isDue);
    }

    // --- decks-bucket public API ------------------------------------------
    //
    // Phase 3 (flashcards.js): same SM-2 math as the notes bucket above
    // (_computeNextState), addressed by (deckKey, index) instead of a note
    // id. deckKey is the deck's `data-deck` asset path (e.g.
    // "assets/flashcards/x.csv"); index is the card's position within that
    // deck, coerced to a string since it becomes an object key under
    // log.decks[deckKey]. Always seeded at the 1-day interval: maturity is
    // a note-level concept (seed/growing/evergreen come from a note's
    // frontmatter, and a flashcard has none), so these pass `null` for
    // `maturity` to _computeNextState, which falls through to
    // DEFAULT_SEED_INTERVAL_DAYS -- SEED_INTERVAL_DAYS.seed, i.e. 1 day.

    function _deckBucket(log, deckKey) {
        return log.decks[deckKey] || (log.decks[deckKey] = {});
    }

    /**
     * Rates card `index` of deck `deckKey` (grade 1-4), updates its entry,
     * persists, and returns the new state -- the deck-bucket equivalent of
     * rate() above.
     */
    function rateCard(deckKey, index, grade) {
        var log = ensureLoaded();
        var bucket = _deckBucket(log, deckKey);
        var key = String(index);
        var next = _computeNextState(bucket[key] || null, grade, null);
        bucket[key] = next;
        save(log);
        return next;
    }

    /** The raw stored state for card `index` of deck `deckKey`, or null if it's never been rated. */
    function cardState(deckKey, index) {
        var log = ensureLoaded();
        var bucket = log.decks[deckKey];
        return (bucket && bucket[String(index)]) || null;
    }

    /** True only for a card that has been rated before AND is now due. */
    function isCardDue(deckKey, index) {
        var state = cardState(deckKey, index);
        return !!state && typeof state.due === 'number' && state.due <= Date.now();
    }

    // --- export / import ---------------------------------------------------

    /**
     * Returns the full log as a plain object (not a JSON string -- the
     * caller decides whether that becomes a Blob download, as the Garden's
     * Progress panel does, or something else). A shallow-ish copy, so the
     * caller mutating the result can't corrupt the in-memory cache.
     */
    function exportLog() {
        var log = ensureLoaded();
        return {
            version: 2,
            notes: Object.assign({}, log.notes),
            decks: Object.keys(log.decks).reduce(function (acc, key) {
                acc[key] = Object.assign({}, log.decks[key]);
                return acc;
            }, {})
        };
    }

    function _mergeBucket(target, incoming) {
        if (!incoming) return 0;
        var merged = 0;
        Object.keys(incoming).forEach(function (key) {
            var entry = incoming[key];
            if (!entry || typeof entry.last !== 'number') return;
            var existing = target[key];
            // Per-key merge rule: keep whichever side was reviewed more
            // recently. This is what makes import safe to run repeatedly
            // (re-importing the same file, or importing an older export
            // after newer local activity) without ever losing progress.
            if (!existing || entry.last > existing.last) {
                target[key] = entry;
                merged++;
            }
        });
        return merged;
    }

    /**
     * Merges an imported log into the current one. Returns
     * { ok: true, merged: <count> } on success, or
     * { ok: false, error: <message> } if `data` isn't a recognized v2 log
     * -- the caller (the Progress panel's Import control) is expected to
     * show `error` rather than silently no-op.
     */
    function importLog(data) {
        if (!data || typeof data !== 'object' || data.version !== 2) {
            return { ok: false, error: 'Not a recognized progress file (expected version 2).' };
        }
        var log = ensureLoaded();
        var merged = _mergeBucket(log.notes, data.notes);

        var decks = data.decks || {};
        Object.keys(decks).forEach(function (deckKey) {
            log.decks[deckKey] = log.decks[deckKey] || {};
            merged += _mergeBucket(log.decks[deckKey], decks[deckKey]);
        });

        save(log);
        return { ok: true, merged: merged };
    }

    window.Review = {
        load: load,
        save: save,
        rate: rate,
        restore: restore,
        stateFor: stateFor,
        isDue: isDue,
        dueCount: dueCount,
        dueIds: dueIds,
        rateCard: rateCard,
        cardState: cardState,
        isCardDue: isCardDue,
        export: exportLog,
        import: importLog
    };
})();
