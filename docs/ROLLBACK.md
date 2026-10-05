# Rolling back a deploy

What a deploy tag is, how to find one, and how to redeploy it. Written for roadmap S06
(`docs/roadmap.yaml`); the mechanism behind this is in `docs/DECISIONS.md` item 28.

## What exists after a normal deploy

Every push to `main` that passes `check` and builds goes through `.github/workflows/deploy.yml`:
`build` renders the site with the commit's own SHA and commit timestamp stamped into every page
(a `<meta name="build-commit">` tag, invisible in the UI -- see `engine/pipeline.py`'s
`_build_commit_stamp`), `deploy` publishes it, `live-check` fetches the live Lobby, Garden, About
and a deliberately missing page and confirms the live site reports exactly that commit, and --
only once all of that has passed -- `release` tags the commit and publishes a GitHub release with
generated notes.

The tag name is deterministic from the commit alone: `deploy-<commit's own UTC timestamp,
YYYYMMDD-HHMMSS>-<first 7 hex characters of its SHA>`, for example `deploy-20261002-143501-2739b5f`.
Not wall-clock time, so a re-run of the same commit reaches the same tag name instead of minting a
duplicate.

**Find the deploy tags:** the repo's [Releases page](https://github.com/trmckinzie/aurelia-os/releases),
or `gh release list --repo trmckinzie/aurelia-os`. Each release's generated notes list the commits
since the previous tag, which is usually enough to tell what a given deploy actually contains
beyond its own SHA.

## Rolling back

1. Pick the tag to go back to, from the list above.
2. Run the **Redeploy a tag** workflow (`.github/workflows/redeploy.yml`):
   `gh workflow run redeploy.yml -f tag=deploy-20261002-143501-2739b5f --repo trmckinzie/aurelia-os`,
   or from the Actions tab: Redeploy a tag -> Run workflow -> paste the tag name. The tag is
   validated against a strict pattern before anything runs; the workflow fails fast on a typo
   rather than building whatever `actions/checkout` happens to resolve.
3. That workflow's own `build` job rebuilds the tagged commit's content (`--no-sort --strict`,
   same as a normal deploy), `deploy` publishes it, and `live-check` confirms the live site matches
   that commit -- the same three steps a normal deploy runs, just starting from an old commit
   instead of the tip of `main`.

**Why this doesn't run from the tag itself.** The `github-pages` environment's deployment branch
policy (Settings -> Environments -> github-pages on GitHub) only names branches -- `None`,
`gh-pages`, `main` -- never a tag pattern, so a workflow run whose own ref is a tag would be
refused at the `deploy` job regardless of what the workflow does. `redeploy.yml` is dispatched
from `main` instead (the only option a workflow with no `on: push: tags:` trigger offers); only
its `build` job's checkout switches to the requested tag, and only for the content it builds.
Checked with `gh api repos/trmckinzie/aurelia-os/environments/github-pages/deployment-branch-policies`
on 2026-10-02.

**This does not touch `main`.** A rollback redeploys old *content*; it does not revert the branch,
open a pull request, or change what the next ordinary push builds. If the bad commit needs
reverting too, that is a separate, ordinary pull request.

## Rehearsing this

The roadmap's `done_when` for S06 calls for rehearsing a rollback once and writing down what
happened -- not merely writing this page. That needs at least two deploy tags to exist (so there
is an earlier one to redeploy and a way to tell the rehearsal apart from "it happened to still be
live"), so it happens after this pull request's own deploy produces its first tag, with a second
deploy on top of it. It replaces the live site while it runs, so it is run only with Travis's
explicit go-ahead, and the outcome is recorded in the follow-up change that marks S06 done
(`docs/roadmap.yaml`), not in this file.
