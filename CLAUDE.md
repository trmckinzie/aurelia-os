# CLAUDE.md

Guidance for Claude Code sessions in this repo. This file is deliberately lean: standing rules,
commands, a map, and the traps. Depth lives in `docs/` and is linked where a session needs it.

## What this is

A personal static-site generator: `build.py` turns the Obsidian vault in `vault/` into a
three-page GitHub Pages site (Lobby `index.html`, Garden `garden.html`, About `about.html`) at
https://trmckinzie.github.io/aurelia-os/ for Travis McKinzie. The Garden is an "external
cortex": atomic notes linked Zettelkasten-style, with the link graph, maturity, and backlinks
visible on the published site, plus a client-side spaced-repetition study layer. `README.md` is
the public description; `docs/ARCHITECTURE.md` is the engine walkthrough.

The site was rebranded away from "Aurelia" in 2026-09 (name collision). What remains "Aurelia"
is deliberately not branding and must stay: the GitHub repo name and Pages URL, `aurelia-*` CSS
classes and `--aurelia-*` custom properties, JS identifiers such as `aureliaReveal`, the
`aurelia_theme` localStorage key, the `AURELIA_SKIP_DROPZONE` env var, and the `20_AURELIA` vault
folder. The working domain `travisrmckinzie.com` is not yet purchased; `site.domain` in
`user_config.json` stays empty until it is (a value makes the build write `dist/CNAME`).

TIMBERLINE is the TRM / Pine personal brand, documented in `brand/readme.md`. `brand/` is an
export from a design tool: nobody edits files in it directly, since changes are made in the tool
and re-exported. It is gitignored and stays local by decision, because the repo is public, so a
fresh clone (CI included) does not have it, and `tests/test_brand.py` skips without it. The
site's colors live in `THEME_CONFIG` (`engine/config.py`); `tests/test_brand.py` holds them to
`brand/tokens/` when `brand/` is present. Where the site and `brand/readme.md` differ today
(motion timings, the code font, the numbered section labels), the site stays as it is until
Travis decides otherwise. `CYBER_PRIME`, `THE_PATRIOT`, `THE_STOA`, and `GRIZZ` are optional
themes, not part of the brand.

## Hard rules

- **`vault/` is off-limits to modify.** No session edits, deletes, or adds vault content (notes,
  folders, frontmatter) without an explicit one-time override from Travis. Reading is fine.
  Engine, templates, config, tests, and `profile.json` are fair game.
- **Don't commit or push unless asked, and never push to `main`.** Make the change, verify it,
  leave it in the working tree. Shipping goes through a pull request ("Branches and pull
  requests" below); a ruleset on `main` rejects direct pushes.
- **CI must keep `--no-sort`.** Both the `check` and `build` jobs in `.github/workflows/deploy.yml`
  run `python build.py --no-sort` (with `--strict`, below). Without the flag `organize_assets()` sweeps
  `vault/99_DROP_ZONE/` into `vault/assets/` on the runner, a vault write reviewed by nobody; the
  media publish gate then keeps an unreferenced file off the site, but not out of the vault.
- **CI gates the deploy on the full check suite.** Every push to `main` and every pull request
  runs `verify.sh` (pytest, pyflakes, the vault schema check, `tools/roadmap.py --check`, a
  `--no-sort` build, then the Playwright browser suite with axe at WCAG A/AA on that build) in
  the `check` job, and on GitHub only that build adds `--strict`; `build` needs `check` and
  `deploy` needs `build`, so neither runs if `check` fails, and a pull request cannot merge until
  `check` passes. Run `bash verify.sh` locally before pushing — it's the same suite, so CI can't
  fail on something the local run missed. The dev root's pre-push hook
  (`~/dev/.claude/githooks/pre-push`, wired in through `core.hooksPath`, see
  `docs/MOVING-MACHINES.md`) also runs it, but only as a warning; CI is the real gate. A `check-macos` job runs the same suite on macOS but is deliberately neither in
  `build`'s `needs` nor required to merge, so a Mac-only failure is visible without holding up
  a deploy.
- **One Python and one Node, read from files.** `.python-version` (3.14) and `.nvmrc` (24) are the
  single source; CI's `setup-python` and `setup-node` read them, so a bump is one line. Python
  packages install with `--require-hashes` from `requirements.txt` / `requirements-dev.txt`, which
  are **generated** from `requirements.in` / `requirements-dev.in`. Edit the `.in` file, then
  regenerate (commands in README, "Dependency locks"); `tests/test_requirements_lock.py` fails on
  drift. Never hand-edit a lock file.
- **Voice rule for anything user-facing:** plain, professional English. No `//` separators, no
  `SNAKE_CASE` labels, no "nodes"/"neural"/"matrix"/"vault" jargon. Notes are notes; the
  collection is the Garden. `tests/test_lobby.py` and `tests/test_garden.py` pin the banned tokens.
- **Never call vault content "private."** The repo is public and all of `vault/` is committed.
  `publish:` decides what renders into `dist/`; it is not access control and never was.
- **Removed on purpose, don't reintroduce:** the Protocols/Portfolio/Transmissions/Services pages
  and their card types. `type: project|protocol|transmission` notes are skipped in `_scan_vault()`
  by design. About is data-driven from `profile.json`, not a vault note type.
- **Model routing:** Sonnet executes, Opus escalates, Fable only on Travis's explicit say-so.
  Subagents live in `.claude/agents/`; doctrine is `90_Meta/Model Routing.md` in the dev
  mono-vault that contains this repo.

## Commands

```bash
pip install --require-hashes -r requirements-dev.txt && npm ci   # one-time setup, inside .venv
python build.py                                        # writes dist/ (gitignored, rebuilt from scratch)
python build.py --no-sort --strict                     # what CI runs: any build warning exits 1
python -m pytest tests/ -q                             # the unit/integration suite (skips tests/browser/)
python -m pyflakes engine/*.py tools/*.py build.py deploy.py tests/*.py
python tools/validate_vault_schema.py                  # frontmatter contract; also runs under pytest
python tools/vault_health.py                           # advisory reports; never writes to the vault
python tools/roadmap.py --open                         # roadmap dashboard; writes reports/ (gitignored)
python tools/roadmap.py --check                        # validate roadmap.yaml; exits 1 on any problem
python deploy.py                                       # factory clone -> ./Aurelia_Factory_v1/ (gitignored)
npx playwright install chromium                        # one-time: the browser the suite drives
GITHUB_REPOSITORY=trmckinzie/aurelia-os python build.py --no-sort   # dist/ as Pages serves it
npx playwright test                                    # browser + axe suite (see tests/browser/) on that dist/
npx playwright test tests/browser/study.spec.mjs --headed   # one file, watching; or -g "<title>", --ui
npx playwright show-trace test-results/<test>/trace.zip     # step through a failure
bash verify.sh                                          # everything above, in CI's order; run before pushing
```

The browser suite (`tests/browser/`, `playwright.config.mjs`) tests `dist/` and never builds it,
so it cannot race a build; it serves `dist/` under `/aurelia-os/` via `tools/preview.mjs` on port
8792. An axe finding is fixed, or added to `AXE_EXCEPTIONS` in `tests/browser/fixtures.mjs` as
one rule on one selector with an open backlog id; never disable a rule. CI keeps failure
screenshots and traces as the `browser-suite-failures-<os>` artifact. `docs/DECISIONS.md` item 30.

Machine-specific notes (interpreter path, console encoding, local preview server) live in the
gitignored `CLAUDE.local.md`, which Claude Code loads alongside this file.

## Branches and pull requests

Every change reaches `main` through a pull request, note-only commits included, and merging one
deploys the site. The "Protect main" ruleset requires the `check` job, blocks force pushes and
deletion, and has no bypass, because sessions push as Travis. Reasons: `docs/DECISIONS.md` item 25.

```bash
git switch main && git pull --ff-only     # start from the current main
git switch -c s05-strict-build            # a branch named after the work
bash verify.sh                            # before every push
git push -u origin s05-strict-build
gh pr create --fill                       # the template carries the checklist
gh pr merge --squash --auto               # GitHub merges it once `check` passes
git switch main && git pull --ff-only && git branch -D s05-strict-build   # after the merge
```

- **Squash merges, one commit per pull request.** GitHub deletes the merged branch; the local one
  needs `-D` because a squash leaves it looking unmerged. The squash commit exists only after
  the merge, so a roadmap session records it in the follow-up change that marks the session done.
- **Note-only commits take the same path.** The Obsidian Git plugin in `vault/` is disabled; if it
  is ever turned back on, its pushes to `main` will be rejected.
- **Concurrent sessions each get a worktree** under `.claude/worktrees/`, where Claude Code puts
  them (gitignored; `.worktreeinclude` copies `CLAUDE.local.md` in). Run `npm ci` in a new
  worktree before `verify.sh`, which borrows the main checkout's `.venv`. The dev root's git hooks
  reach these worktrees only through a per-machine include in `.git/config`
  (`docs/MOVING-MACHINES.md`), and `verify.sh` warns when they do not. Don't commit from a
  worktree that shows the warning: a pushed branch is public before it merges.
- **Look into another worktree with `git -C <path>`, not `cd`.** The session follows a `cd`, and
  Windows will not delete a folder a shell is still in.

## Map

- `build.py` is a short entrypoint (arg parsing and error reporting only); all real logic is in
  `engine/`.
- `engine/config.py`: paths, the Jinja env (`autoescape=True`, unconditional), `THEME_CONFIG`
  (five themes, `TIMBERLINE` default). Adding a theme is one dict entry.
- `engine/user_config.py`: `user_config.json` loader and strict validator (site identity, the
  Lobby Toolkit). Like `profile.py`, any error is fatal.
- `engine/buildlog.py`: `warn()`, the one path for build warnings, which `--strict` counts.
- `engine/pipeline.py`: `build_all()`. `_scan_vault()` is two-pass (ids and link resolver first,
  then wikilinks, media, cards). `_build_link_graph()` computes backlinks and graph edges in one
  pass. `UNPUBLISHED_DIRS` hard-excludes `20_AURELIA` from publishing.
- `engine/content.py`: frontmatter (PyYAML), `make_id()`, `process_wikilinks()`,
  `build_link_resolver()`, the Gemini Notebook media and section passes.
- `engine/extractors.py`, `textutils.py`, `cards.py`: per-type field extraction, string helpers,
  and the single card renderer `generate_garden_card_html()` (Python f-strings, not Jinja).
- `engine/sanitize.py`: nh3 allowlist for note-authored HTML. Read its docstring before moving
  the call. It must run on the raw body, before the engine injects its own buttons and widgets.
- `engine/paths.py`: junction/symlink containment for the vault walk.
- `engine/profile.py`: `profile.json` loader and strict validator for the About page. A missing
  file is fatal by design so the nav never differs build to build.
- `engine/theming.py` and `tailwind_build.py`: generate `theme-vars.css` and `tailwind.config.js`
  from `THEME_CONFIG`. Never hand-edit either output.
- `engine/assets_pipeline.py`: the Drop Zone sort, the site's own assets into `dist/`, the media
  publish gate (a media file ships only when a published note references it), and ffmpeg
  compression for oversized drop-zone audio.
- `engine/cachebust.py`: hashes each served script/stylesheet's actual bytes into its URL, so a
  deploy's new files aren't masked by GitHub Pages' ten-minute cache.
- `engine/vendor.py`: copies the pinned web fonts, `marked.js`, and Motion from `node_modules/`
  into `dist/`, so the site serves everything itself.
- `system/templates/`: `base.html`, `404.html`, `pages/{index,garden,about}template.html`.
- `assets/js/`: `review.js` (SM-2 study layer, localStorage only), `flashcards.js`, `utils.js`.
  `search-index.js` is generated into this folder at build time (gitignored) — see
  `pipeline._write_deep_search_index`.
- `tools/`: `validate_vault_schema.py`, `vault_health.py`, `roadmap.py`, and `preview.mjs` (the
  Node static server behind `.claude/launch.json`'s `dist-preview`; `node tools/preview.mjs`).
- `docs/roadmap.yaml`: the priority-ordered engineering roadmap (sessions plus a backlog), rendered
  by `tools/roadmap.py`. A session doing roadmap work updates its own entry in the same change
  (tasks, status, dates, commits) and runs `python tools/roadmap.py --check`.
- `deploy.py`: a separate product, a white-label factory clone. Keep it in sync with `engine/`
  when the site's capabilities change. `tests/test_deploy.py` is only a smoke test (the clone
  builds and ships what its README promises, roadmap S09), so it has drifted before and can again.

Content model in brief: a note publishes only with `publish: true`; `type:` is one of `concept`,
`source/book`, `author`, `discipline`, `gemini-notebook`, `deep-dive`, or a daily log; canonical
frontmatter is `created, tags, type, maturity, status, publish` plus optional `aliases:`.
Maturity promotion is a human call (seed to growing at 2+ backlinks, growing to evergreen when
referenced from 2+ Discipline notes); nothing auto-edits it.

## Read before touching

- Links, wikilinks, card pills, backlinks: `docs/ARCHITECTURE.md`, "Link system".
- Themes, colours, contrast: `docs/ARCHITECTURE.md`, "CSS", `tests/test_theming.py`, and
  `brand/readme.md` for TIMBERLINE's TRM / Pine brand.
- Study mode, review queue, flashcards: `docs/ARCHITECTURE.md`, "Study layer", and the reasoning
  behind it in `docs/DECISIONS.md` item 18.
- Setting up a new machine, or what git will not carry to one: `docs/MOVING-MACHINES.md`.
- Rolling back a bad deploy, or what the post-deploy live check verifies: `docs/ROLLBACK.md`.
- Anything that changes what the public site renders or exposes: `docs/ARCHITECTURE.md`,
  "Privacy model", then hand to `garden-publication-reviewer`.
- Why something looks odd: `docs/DECISIONS.md` (dated decisions plus known gaps).
- Security history: `docs/SECURITY-AUDIT.md`. Check `git log --grep "audit #"` for the current
  state rather than trusting any list, including that one.

## Traps

Each of these cost real time once. Dates and detail are in `docs/DECISIONS.md`.

- **`make_id()` is case- and punctuation-insensitive.** `[[hippocampus]]` and `[[Hippocampus]]`
  are one target. Audit links by id, not by written form.
- **Prefer `[[Full Title|display text]]` over relying on the resolver.** The alias and title-suffix
  tiers exist, but a suffix base shared by two notes resolves to neither.
- **A dangling link is usually a deliberate placeholder**, not an error. `vault_health.py
  --report pending` is the queue. A near-match retarget is not a match; verify in the prose first.
- **Gemini cards need the pre-wrap body.** `wrap_gemini_notebook_sections()` rewrites the `#`
  headers that `extract_gemini_notebook_data()` anchors on, so `card_body` is snapshotted before
  the media and section passes. Don't collapse the two bodies; `tests/test_pipeline.py` pins it.
- **A citation URL can contain `assets/`.** The asset-reference regex needs its lookbehind, or
  live citations report as missing files.
- **Reading a CSS custom property right after switching `data-theme` in JS returns the previous
  theme's value.** Compute per-theme contrast in Python from `THEME_CONFIG`.
- **`info` fails AA as small text in the dark themes.** Sweep every theme, not just the default.
- **`clean_text()` and `strip_html()` are not encoders.** They strip closed tags only; escape at
  the sink. `sanitize.py` strips rather than escapes because `openNote()` decodes entities
  through a `<textarea>` before `marked.parse()`.
- **Flashcard Q/A go in child elements, never `data-*` attributes**, for the same `<textarea>`
  reason.
- **Motion's `cancel()` reverts to the first keyframe on the next frame.** Use `stop()` after
  writing a final value.
- **`git rev-list --objects` lists a blob once**, so a file at two paths looks like one. Use
  `git log --all --name-only` when auditing exposure.
- **Tailwind scans `dist/**/*.html`**, so classes assembled in Python are fine but classes built
  client-side after load need a `safelist` entry.
- **A parent template's top-level `{% set %}` is invisible in a child's blocks.** Child templates
  `{% set %}` `site` themselves.
- **Don't reintroduce `review_seed`.** `dueCount()` counts logged entries only, so the Lobby
  teaser needs no per-note payload.
- **Verify the built site with a real browser against a local server on `dist/`**
  (`node tools/preview.mjs` sends `no-store`; any other server needs a query string), or the
  browser serves a cached `garden.html` after a rebuild.
- **A build warning exits 0 locally and fails CI.** Malformed frontmatter, a missing asset or an
  ambiguous alias go through `engine/buildlog.warn()`; `--strict`, which only CI passes, turns any
  of them into exit 1. A new warning must use `warn()`, not `print()`, or CI never sees it. A bad
  `user_config.json` or `profile.json` fails every build, strict or not. `docs/DECISIONS.md` item 26.

## Deliberately not done

Card HTML as Jinja macros (deferred), any server or synced store for study progress (the site
promises no tracking), Lighthouse or visual-regression tests, and a unit-test harness for
`assets/js/`. Browser and accessibility tests do exist now and block the merge
(`docs/DECISIONS.md` item 30). `garden.html` keeps every note's body inline rather than fetching
a note when it opens: decided 2026-10-01, to revisit once the compressed page passes 1 MB
(`docs/roadmap.yaml`, backlog B04). The full list with reasons is in `docs/DECISIONS.md`.
