# Moving to another machine

What a fresh clone of this repo does **not** bring with it, and where each piece goes. Written for
the Alienware (Windows 11) to Mac mini move in October 2026, but true of any new checkout.

A clone carries everything tracked. It does not carry anything the `.gitignore` excludes, anything
in `.git/config`, or anything that lives under `~` rather than in the repo. That is the whole list
below. None of it should ever be committed; if a row involves a credential, it moves by hand and
never through git or a synced folder.

**Do not copy** `.venv/` or `node_modules/` between machines. A Windows virtual environment uses a
different layout (`Scripts\`) and different compiled wheels than a macOS one, and both are
rebuilt in a minute from the lock files.

## Rebuilt from tracked files (nothing to move)

| State | Why git skips it | On the new machine |
|---|---|---|
| `.venv/` | Not portable between operating systems | `python3 -m venv .venv`, then `.venv/bin/pip install --require-hashes -r requirements-dev.txt` |
| `node_modules/` | Build environment, restored from `package-lock.json` | `npm ci` |
| Playwright's Chromium | Lives in the user's cache (`~/Library/Caches/ms-playwright` on macOS), not the repo | `verify.sh` runs `npx playwright install chromium` itself |
| `test-results/`, `playwright-report/` | Browser-suite failure output | Appear when a browser test fails |
| `tailwind.config.js` | Generated from `THEME_CONFIG` on every build | Appears on the first `python build.py` |
| `dist/` | Build output | `python build.py` |
| `reports/` | Generated roadmap dashboard | `python tools/roadmap.py --open` |
| `.pytest_cache/`, `__pycache__/` | Caches | Appear on their own |
| `Aurelia_Factory_v1/` | Output of `python deploy.py` | Regenerate if wanted |
| `.playwright-mcp/`, `/garden-*.png`, `/*-snapshot.md` | Scratch from browser-driven checks | Do not move |

## Local state that has to be carried or recreated by hand

| State | What it is | Destination on the Mac |
|---|---|---|
| `brand/` | The TRM / Pine brand export from a design tool (`brand/readme.md`, `brand/tokens/`) that TIMBERLINE follows. Gitignored whole since pull request #6, because the repo is public. | Copy the folder by hand (AirDrop, `scp`, or a USB drive), or export it again from the design tool. Without it, `tests/test_brand.py` skips, as it does in CI, so the check that holds TIMBERLINE's colors to the brand tokens stays off until the folder is back. |
| `vault/20_AURELIA/` | Notes drafted by an agent through the `aurelia-mcp-server` `draft_note` tool. Gitignored on purpose: nothing auto-commits to the Garden, so a draft exists in one place only. Currently one draft. | Copy the folder by hand (AirDrop, `scp`, or a USB drive) to `vault/20_AURELIA/` in the Mac clone. Travis does this himself: sessions do not add to `vault/`. Drafts you no longer want can simply be left behind; git will never restore them. |
| `CLAUDE.local.md` | Per-machine session notes: interpreter path, preview command, console quirks. | Do not copy. Write a fresh one on the Mac. The Windows-only notes (bare `python` is the Store alias, `PYTHONUTF8`, the `py` launcher) do not apply there. Worth carrying over: several sessions can work in this repo at once, so run one `build.py` at a time and never stash or reset another session's work. |
| `.claude/settings.local.json` | The per-machine permission allowlist Claude Code appends to as tools are approved. Holds local paths. (Absent on the Alienware today.) | Do not copy. It rebuilds as you approve tools, or run the `fewer-permission-prompts` skill once a few sessions have accumulated. |
| `.env`, `.env.*` | Secrets, if any exist. None do at the moment. | If one appears later, move it by hand through the password manager. Never through git, Obsidian Sync or a chat. |
| `vault/.smart-env/` | Smart Connections plugin index | Rebuilt by the plugin on first open. |
| `vault/.obsidian/workspace*.json` | Obsidian's scroll position and open panes | Per device by design. Recreated. |
| `vault/.obsidian/plugins/obsidian-git/git_credentials_input*` | Credential-prompt scratch files | Never move. The plugin recreates them if it needs them. |
| `vault/.obsidian/plugins/*/` code (`main.js`, `manifest.json`, `styles.css`) | The Calendar, Dataview and Templater community plugins. Untracked since roadmap B08 (2026-10-01): Obsidian installs and updates plugin code itself. Each plugin's settings file, `data.json`, is still tracked where one exists: Calendar's and Templater's (Dataview has none). The turned-off Obsidian Git plugin is untracked whole. | On a fresh clone, open the vault and reinstall the three from Settings → Community plugins; the tracked settings are already in place. A clone that existed before B08 loses the plugin code when it pulls that change, because git removes files it stops tracking. Restore them from a commit that still had them: `git restore --source=f558fb2 --worktree -- vault/.obsidian/plugins`. |

## Wiring outside the repo

| State | Why it is not in the repo | Destination on the Mac |
|---|---|---|
| `core.hooksPath` in `.git/config` | Git neither clones nor tracks `.git/config`. An unwired clone looks normal and checks nothing on commit. | If the clone sits under the dev root (`~/dev/projects/aurelia-os`), run `bash ~/dev/.claude/githooks/install.sh` and confirm with `install.sh --check`. The relative path it sets works unchanged on both machines. |
| The worktree include in `.git/config` | Same reason. Git resolves the relative `core.hooksPath` from each worktree's own top level, so without it a session worktree under `.claude/worktrees/` runs none of the dev root's hooks, silently. | After `install.sh`, from the repo root: `git config --file .git/config 'includeIf.gitdir/i:./worktrees/.path' worktree-hooks.inc`, then `git config --file .git/worktree-hooks.inc core.hooksPath ../../../../../.claude/githooks`. The main checkout keeps its own value, so `install.sh --check` still reports it wired. |
| Claude Code auto-memory, `~/.claude/projects/<path-slug>/memory/` | Per OS user, and the folder name is derived from the checkout path, so it differs on the Mac | Copy the `.md` files across to the matching folder on the Mac once a session has created it, or start fresh. Check each note before trusting it: they are point-in-time. |
| `~/.claude/plans/floofy-mapping-dahl.md` | Machine-local plan for the study layer | Nothing to move. Its load-bearing content is now `docs/DECISIONS.md` item 18. |
| Git identity, GitHub login, the Playwright browser | Per machine and per login | Set up fresh: `git config user.name` / `user.email`, `gh auth login`, and `npx playwright install chromium` for the browser suite that `verify.sh` runs. A Playwright MCP server for hand checks is optional; if you add one, add it at project or local scope. |

## Checks after the move

```bash
bash verify.sh                    # the same suite CI runs
node tools/preview.mjs            # http://localhost:8791 serves dist/
git config --get core.hooksPath   # should print ../../.claude/githooks

# The hooks resolve from a session worktree too: silent with exit 0, not "cannot find a hook"
git worktree add --detach .claude/worktrees/hook-check
git -C .claude/worktrees/hook-check hook run pre-commit
git worktree remove .claude/worktrees/hook-check
```

A green `check-macos` job in CI before the machine arrives is the best early warning that the
first two will pass. It cannot see the hook checks, or anything in the tables above.
