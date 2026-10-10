# aurelia-os roadmap

Done when: backlog items B02 (delegated listeners, then a Content-Security-Policy), B19 (screen readers reach the Garden pills), B04 (every Garden note stays in the page, watched against a 1 MB threshold) and B06 (publish a media file only when a published note references it) are closed in `docs/roadmap.yaml`, with `bash verify.sh` and the live check green.

Tier: code. See `90_Meta/Dev Environment Standard.md` in the dev vault. This repo already meets it, and the standard was modelled on it.

**`docs/roadmap.yaml` is the source of truth** for sessions and the full backlog, checked by `tools/roadmap.py --check` in `verify.sh`. This file names only the items that gate the Done line (chosen 2026-10-09) so the dev-dashboard can show progress. Close an item in the yaml first, then tick it here. The public site is the constraint: nothing private reaches `dist/`, and `vault/` is edited only with Travis's explicit go-ahead.

## Standardize
- [x] `.python-version`, `.nvmrc`, hash-locked requirements, `package-lock.json`, `verify.sh`, CI pinned to SHAs, the `.claude/agents` pair (already in place before 2026-10-09)
- [x] `dashboard.json` with `verify`, `test`, `build --no-sort` and `preview` (2026-10-09)
- [x] README: the PowerShell and Windows venv lines removed (2026-10-09)

## Harden
- [x] `npm audit --omit=dev` is 0, and pip-audit finds nothing in `requirements.txt` (2026-10-09)
- [ ] 8 dev-only npm advisories (Playwright/Tailwind toolchain): let Dependabot's PRs land, or review them with the B07 Tailwind upgrade (due 2026-11-30)

## Reach done
- [ ] B02 replace the inline `onclick` handlers with delegated listeners, then add a Content-Security-Policy #next
- [ ] B19 stop nesting buttons inside Garden cards, so screen readers reach the pills
- [x] B04 keep every Garden note in the page and watch its size against a 1 MB threshold (2026-10-09)
- [ ] B06 publish a media file only when a published note references it

## Parked
- [ ] The rest of the backlog in `docs/roadmap.yaml` (B01, B03, B07, B10, B13–B18), plus the content work in the vault note (note-reader readability, `Contrasts With`)
