# aurelia-os roadmap

Done when: sessions S11 (the switcher offers two themes, light and dark), S12 (Tailwind v4 with every npm advisory cleared, due 2026-11-30) and S13 (the Garden's script split into served modules with unit tests) are done in `docs/roadmap.yaml`, with `bash verify.sh` and the live check green.

Tier: code. See `90_Meta/Dev Environment Standard.md` in the dev vault. This repo already meets it, and the standard was modelled on it.

**`docs/roadmap.yaml` is the source of truth** for sessions and the full backlog, checked by `tools/roadmap.py --check` in `verify.sh`; `python tools/roadmap.py --next` prints the kickoff prompt for the next session. This file names only the items that gate the Done line so the dev-dashboard can show progress. Close an item in the yaml first, then tick it here. The public site is the constraint: nothing private reaches `dist/`, and `vault/` is edited only with Travis's explicit go-ahead.

## Reach done (second roadmap, planned 2026-10-10)
- [ ] S11 the theme switcher offers only TIMBERLINE (light) and CYBER_PRIME (dark); the other three stay defined, not offered #next
- [ ] S12 Tailwind v4, and `npm audit` at zero advisories including dev dependencies (due 2026-11-30)
- [ ] S13 the Garden's inline script becomes served modules with a JavaScript unit-test run in `verify.sh`

## Standardize
- [x] `.python-version`, `.nvmrc`, hash-locked requirements, `package-lock.json`, `verify.sh`, CI pinned to SHAs, the `.claude/agents` pair (already in place before 2026-10-09)
- [x] `dashboard.json` with `verify`, `test`, `build --no-sort` and `preview` (2026-10-09)
- [x] README: the PowerShell and Windows venv lines removed (2026-10-09)

## Harden
- [x] `npm audit --omit=dev` is 0, and pip-audit finds nothing in `requirements.txt` (2026-10-09)
- [ ] 8 dev-only npm advisories (Playwright/Tailwind toolchain): cleared by S12, or by Dependabot's pull requests if they land first (due 2026-11-30)

## First Done line, met 2026-10-09
- [x] B04 keep every Garden note in the page and watch its size against a 1 MB threshold (2026-10-09)
- [x] B06 publish a media file only when a published note references it (2026-10-09)
- [x] B19 stop nesting buttons inside Garden cards, so screen readers reach the pills (2026-10-09)
- [x] B02 replace the inline `onclick` handlers with delegated listeners, then add a Content-Security-Policy (2026-10-09)

## Parked
- [ ] The rest of the backlog in `docs/roadmap.yaml` (B03, B10 waits on the About interview file, B13–B18, B20), plus the content work in the vault note (note-reader readability, `Contrasts With`)
