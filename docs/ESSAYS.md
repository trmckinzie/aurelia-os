# Essays

Design for a fourth kind of published content: short human-written essays on psychology,
philosophy and adjacent subjects, each with a fixed disclosure note and an AI-generated study
companion. Planned 2026-10-12 from Travis's handoff of 2026-10-11; built across roadmap sessions
S15 to S18 (`docs/roadmap.yaml`), after S12 and before S13. The decisions behind it are
`docs/DECISIONS.md` item 41.

S15 is built (2026-10-14, `docs/DECISIONS.md` item 43): the content type in `engine/essays.py`,
the draft gate and privacy checks, the index and essay pages (`system/templates/pages/essaystemplate.html`
and `essaytemplate.html`), the Garden links, and the recursive security-policy and cache-busting
walks. S16 to S18 are not. Paths that do not exist yet are written plainly rather than as code, so
`tests/test_docs_paths.py` does not hold them to the file system until a session creates them;
vault/30_ESSAYS/ is one of them, since no essay is in the vault until S17 is done. The test essay
lives in `tests/fixtures/essays/`, and the build reads it through `AURELIA_ESSAYS_DIR`.

## Where essays come from

Only the last step of Travis's workflow touches this repo, but the page is shaped by all of it:

1. Kickoff: an essay id (E01, E02, ...), a Drive folder, a start date worked back from the
   publish date.
2. Explore: source search on PubMed and the open web; Travis picks the question and thesis.
3. Curate: chosen sources go to the Source Ledger (a private Google Sheet) and the essay's Gemini
   notebook.
4. Read and think: Travis verifies each AI summary against its source and writes his own notes.
5. Draft: by hand on a reMarkable tablet.
6. Edit and audit: transcribed into Google Docs and edited by hand. An AI citation audit may flag
   problems in comments; it never rewrites prose.
7. **Publish: the final essay, its reference file and its disclosure numbers go into the vault,
   and a pull request lands them.** This document is about this step.
8. Companion and podcast: Gemini Notebook makes study assets from the final essay and open-access
   sources; the essay becomes a YouTube episode.

## The privacy boundary

The repo is public, and everything committed to `vault/` is public whether or not it renders
(`docs/ARCHITECTURE.md`, "Privacy model"). So the boundary is what gets committed, not what
renders.

| Enters the repo | Never enters the repo |
|---|---|
| The final essay text | The Source Ledger, and any export of it |
| Its reference records (bibliographic fields only) | AI summaries of sources |
| The disclosure numbers and AI roles | Travis's Evaluation and Fit notes |
| Companion asset links (exported files only) | Any source PDF, above all library-licensed ones |
| The YouTube link | The reMarkable draft, and any draft at all |
| | Gemini notebook links, Google Drive and Docs links |
| | Anything about his employer, students or colleagues beyond what an essay itself says |

**An essay enters the vault only when it is final.** A draft has no safe place in the vault: a
`publish: false` note is still public in git. The build therefore fails on any note in the
Essays folder that is not marked `publish: true`, so a stray draft is caught before it merges.

**CI is a backstop, not the gate.** A pushed branch is public before it merges, so a check that
first runs in CI catches a leak after GitHub already has it. So the privacy checks below **fail
every build, strict or not**, the way a bad `user_config.json` already does, rather than going
through `engine/buildlog.py`'s `warn()`: `verify.sh` builds with `--strict` only on GitHub, and a
warning would let a local run pass. Travis runs `verify.sh` before every push (`CLAUDE.md`), and
the dev root's pre-push hook runs it too, as a warning. Whether that hook should *block* on a
failure is left open (see "Open questions"). Citation and link problems, which leak nothing, use
`warn()` like every other build warning, so `--strict` fails on them in CI.

### The privacy checks (each fails every build)

1. **Field allowlist, not a denylist.** Essay frontmatter and reference records accept only the
   fields this document lists; any other key fails. An allowlist is the standard choice because a
   new private field (an export adding `annote` or `abstract`) fails by default instead of
   slipping past a list nobody updated. CSL's own `abstract`, `annote` and `note` fields are
   excluded on purpose: they are exactly where a citation manager puts summaries and notes.
2. **Host denylist.** Any URL anywhere in an essay, its reference file or its companion list
   whose host is Google Drive, Docs or Sheets, Gemini, NotebookLM or reMarkable fails. This is
   the notebook-link trap: a public notebook link exposes every library-licensed PDF in it.
3. **Text only.** Any file in the Essays folder other than `.md` and `.yaml` fails, whatever its
   size. Simpler and stricter than a size threshold, and it covers PDFs of every size.
4. **Drafts.** A note in the Essays folder without `publish: true` fails, as does a `type: essay`
   note outside that folder.
5. **Companion and media origins.** A companion or audio URL whose origin is not on the
   allowlist in `user_config.json` fails (see "Media").

## Vault layout and data contract

Essays live in their own top-level folder, a sibling of the Garden: vault/30_ESSAYS/. One essay is
two files:

- E01 Title of the essay.md, the essay itself: frontmatter plus the body as Markdown.
- E01.refs.yaml, its reference records.

Obsidian hides `.yaml` files unless Settings, Files and links, "Detect all file extensions" is on.

### Essay frontmatter

```yaml
type: essay
id: E01                       # E plus two digits; unique; matches the reference file's name
title: "Why loss looms larger"
slug: why-loss-looms-larger   # lowercase, digits, hyphens; the essay's URL; never changes once published
publish: true                 # required; the build fails without it (see Drafts above)
published: 2026-11-20
updated: 2026-11-22           # optional; on or after published
disciplines: [psychology, philosophy]
thesis: "One sentence."       # 200 characters at most
citation_style: apa7          # apa7 | web
methods:
  drafted_on: reMarkable
  edited_in: Google Docs
  ai_roles: [source search, source summaries, citation audit]
companion:                    # optional
  - kind: audio               # audio | video | other
    label: "Audio overview"   # 80 characters at most; never prose
    url: https://media.travisrmckinzie.com/e01/overview.m4a
youtube: https://www.youtube.com/watch?v=XXXXXXXXXXX   # optional
```

Changes from the handoff's starting point, and why:

- **No `status: draft | published`.** `publish:` is already the one switch the whole engine reads.
  Two switches can disagree; one cannot.
- **No `sources_total` or `sources_verified`.** Both are counted from the reference file (below),
  so the disclosure numbers cannot drift from the list a reader sees.
- **Reading time is computed** (words divided by 230, rounded up), not typed.
- **`ai_roles` is a closed vocabulary**: `source search`, `source summaries`, `citation audit`. An
  unknown role fails the build, so the disclosure only ever says something the engine knows how
  to phrase, and "writing" can never be one.
- **The companion entries carry no free text beyond a short label**, so the AI zone structurally
  cannot hold essay prose.
- `disciplines` render as plain labels, each linking to the Garden's Discipline note when one of
  that name is published.

### Reference records (E01.refs.yaml)

A list of records using CSL field names. CSL is the citation data format Zotero, Pandoc and every
citation processor read, which is why one record can produce both APA 7 and the web style, and
why a later switch of formatter does not touch the data.

```yaml
- id: kahneman1979              # the citation key used in the essay text
  type: article-journal         # article-journal | book | chapter | entry-encyclopedia | article (preprint)
  author:
    - {family: Kahneman, given: Daniel}
    - {family: Tversky, given: Amos}
  issued: 1979
  title: "Prospect theory: An analysis of decision under risk"   # stored in the case APA wants
  container-title: Econometrica
  volume: 47
  issue: 2
  page: 263-291
  DOI: 10.2307/1914185
  verified: true                # Travis checked the AI summary against the original
```

Allowed fields: `id`, `type`, `author`, `editor`, `issued`, `title`, `container-title`,
`edition`, `volume`, `issue`, `page`, `publisher`, `DOI`, `URL`, `version` (encyclopedia
editions), `genre` (preprint server), `open_access`, `verified`. Everything else fails.

The disclosure note counts the records: "N sources; M of N verified against the original by the
author", where M counts `verified: true`. The count is of cited sources, which the build
guarantees equals the reference list (see "Citations").

## Citations

The essay text cites with Pandoc's citation syntax, the standard for scholarly Markdown:

| Written | APA 7 renders |
|---|---|
| `[@kahneman1979]` | (Kahneman & Tversky, 1979) |
| `[@kahneman1979, p. 263]` | (Kahneman & Tversky, 1979, p. 263) |
| `[@kahneman1979; @thaler1980]` | (Kahneman & Tversky, 1979; Thaler, 1980) |
| `@kahneman1979 argue that...` | Kahneman and Tversky (1979) argue that... |

The text carries the key only, never the formatting; at step 7 Travis replaces each Google Docs
citation with its key. Each rendered citation links to its entry in the reference list. A bare
`@` only counts as a citation at the start of a word and only for a key the reference file
holds; an email address is left alone.

Strict checks, both directions: a citation with no matching record fails, and a record nothing
cites fails. Duplicate keys fail.

**APA 7 formatting, first version.** The engine formats from the records. Covered, each with
golden-output tests: journal article; authored book (with edition); chapter in an edited book;
encyclopedia entry (the Stanford Encyclopedia of Philosophy shape, with edition and editor);
preprint. Also: one, two, three to twenty, and twenty-one or more authors; a group author;
same-author same-year works as 1979a and 1979b; DOI preferred over URL, as `https://doi.org/`
links; page ranges with an en dash; list order by first author, then year, then title; hanging
indent; italics on journal title and volume, and on book and encyclopedia titles. The engine
never changes a title's case, since only a person knows which words are proper nouns.

Not in the first version: conference papers, theses, reports and grey literature, translated
or republished works, audiovisual and legal sources, datasets, secondary citations ("as cited
in") and footnotes. A record of an unsupported `type` fails the build rather than rendering
wrong.

S16 first checks whether a maintained CSL processor renders the APA 7 style correctly for the
five types (vetting it under the dev root's rule for any new dependency). If none does, the
formatter is a small in-house module. Either way the records are CSL, so the choice can be
reversed later.

**Web style** (`citation_style: web`), from the same records: each citation renders as a link on
the short author-year text, straight to the source's DOI or URL, and the essay ends with a short
Sources list (title, authors, year, link) instead of an APA reference list.

## Pages and URLs

| Page | URL | Notes |
|---|---|---|
| Essays index | /essays/ | Newest first: title, publish date with weekday, discipline labels, the thesis, reading time. A fourth nav item, "Essays". |
| An essay | /essays/(slug)/ | One page per essay. |
| Feed | /essays/feed.xml | Atom. |

Folder-style URLs (`/essays/slug/`, served from `essays/slug/index.html`) are the standard for
articles because the URL names no file format, so it survives a change of host or generator. An
essay's URL is permanent once published: feeds, links and citations of the essay depend on it.

This is the first output below the top of `dist/`, and three things assume the top level today:
`engine/csp.py` and `engine/cachebust.py` only read `dist/*.html`, so both move to a recursive
walk (an essay page missed by the first ships with an unfilled security policy); and essay pages
link from the site root, as `404.html` already does, since S14 made that root "/". The build
already writes absolute URLs from `site.domain` through `engine/pipeline.py`'s `_site_url()`.

Essays never become Garden cards: the vault walk sends `type: essay` notes to the Essays pipeline
instead of the card renderer, and a test holds that.

## The essay page, top to bottom

The line between Travis's writing and AI output has to be obvious at a glance on a phone.

1. **The essay.** Title in the display serif; byline "Travis R. McKinzie"; the publish date with
   its weekday ("Friday, 20 November 2026"), and "Updated ..." when set; discipline labels;
   reading time. The body follows the brand's reading settings (body type at a 68-character
   measure). Garden concepts written as `[[wikilinks]]` resolve through the Garden's own
   resolver (`content.build_link_resolver()`) and render as ordinary links to `/garden.html#id`;
   a link to a note that is missing or unpublished fails the strict build.
2. **How this essay was made.** Rendered from frontmatter, never hand-written, on the same paper
   surface as the essay, under a small label:

   > I wrote this essay by hand: the first draft on a reMarkable tablet, the revisions in Google
   > Docs. AI was used for research, not writing. Claude searched for sources and drafted short
   > summaries of them; I checked each summary against the original and wrote every evaluation
   > myself. An AI citation audit checked that each citation supports its claim and matches the
   > reference list; it flagged problems and changed no prose. 14 sources; 14 of 14 verified
   > against the original by the author.

   Sentences drop out with their roles: no citation audit in `ai_roles`, no audit sentence.
3. **References.** APA 7 (or the web style's Sources list).
4. **Study companion.** A visually separate zone, the one place AI output appears: an inverted
   surface (paper on the theme's darkest ink) with a heavy top rule, headed by the label
   "AI-generated study companion" and the line "Made with Gemini Notebook from this essay and the
   open-access sources listed." It holds only players and links built from the companion list.
   Colors come from theme tokens, so both offered themes get it, and the browser suite holds it to
   WCAG AA in each.
5. **Listen.** The YouTube episode, when one exists (see "Media").

Typography follows the TRM / Pine brand as the site applies it today: the display serif for
headings, the grotesque for body and labels, no ornament. It should read like a well-set journal
article.

## Media

Audio and video never enter the repo. GitHub Pages is a poor host for them (GitHub warns at 50 MB
per file and refuses 100 MB), and every byte would live in git history for good. The repo today
holds no audio or video, and never has.

- **Audio: a Cloudflare R2 bucket on media.travisrmckinzie.com**, played by a plain
  `<audio controls preload="none">`, so a phone downloads nothing until the reader presses play.
  No third party is involved. Travis creates the bucket and connects the subdomain himself (an
  account step a session does not take); uploads are a manual part of step 8. The media sits
  outside the deploy rollback.
- **Kept swappable:** the engine never assumes a host. The allowed media origins are one list in
  `user_config.json`; it feeds the security policy's `media-src` and the companion URL check.
  Moving to another host is a config edit and a re-upload, with no engine change.
- **Video: YouTube, loaded on tap.** The page shows a plain typographic "Play episode" control and
  nothing from Google loads until it is pressed; then a `youtube-nocookie.com` player replaces
  it. No YouTube thumbnail, since fetching one is itself a request to Google. The security policy
  gains `frame-src https://www.youtube-nocookie.com`, and the control registers a delegated
  `data-action` like every other control on the site (`assets/js/utils.js`).
- **Exported assets only.** The companion links exported files (an audio overview, a video on
  YouTube), never a notebook.

The footer says "No analytics or tracking." That stays true through S15 to S18: the site's own
pages still track nothing, and the YouTube player loads only on a reader's tap, with a note beside
the control saying so. Basic analytics, and a footer that matches whatever is then true, are
backlog item B21, decided separately.

## Metadata

| | Today | Essays add |
|---|---|---|
| Open Graph | Site-wide tags in `system/templates/base.html`; `og:type` website; one preview image | Per essay: `og:type` article, title, thesis as description, `article:published_time` and `article:modified_time`. The preview image stays site-wide in the first version. |
| Canonical URL | From `site.domain` | The essay's own URL. |
| Structured data | Person on About only (`engine/profile.py`) | An Article per essay: headline, author (the About page's Person), dates, and `citation` entries for each reference. |
| Feed | None | Atom at /essays/feed.xml, linked from every page's head. Atom over RSS because its one specification requires the ids and update dates a reader needs, and every feed reader supports it. Entries carry the full essay and its disclosure note, not the companion. |
| Search | Lobby search over Garden notes | Essays join the site search. |

## Garden integration

First version: one-way. Essays link out to Garden notes; the Garden does not change. Showing
essays in Garden backlinks ("Cited in E01") is backlog item B22, after S13 splits the Garden's
inline script into modules, so it is built once in testable code instead of twice.

## Sessions

| Session | Model | Effort | Builds |
|---|---|---|---|
| S15 | Opus | L | The content type, draft gate and privacy checks, the index and essay pages, Garden links, the recursive security-policy and cache-busting walk |
| S16 | Sonnet | L | Reference records, citation resolving with both strict checks, APA 7 for the five types |
| S17 | Sonnet | M | The disclosure note, the companion zone, R2 audio and the YouTube tap-to-load player |
| S18 | Sonnet | M | The web citation style, Article structured data, per-essay Open Graph, the Atom feed, search |

S15 is Opus because it changes the publish surface and the shape of the build's output, and
anything that changes what the public site renders is reviewed by `garden-publication-reviewer`
(`.claude/agents/`). The rest follow a contract this document fixes, which is Sonnet's work.

Until S16, a citation in an essay renders as its raw key; S15's test essay has none. No real
essay goes into the vault until S17 is done, so nothing ships half-rendered. The Essays nav item
and index appear only once one essay is published, so S15 to S18 change nothing a visitor sees.
Until then each session's acceptance is checked on phone-width (375-pixel) screenshots of a
build that includes the test essay, attached to its pull request; the first real essay, published
by Travis after S17, is the check on the live site.

## Test plan

All of it in `verify.sh`, so CI and a local run agree. The test essay lives under `tests/fixtures/`,
never in the vault.

- **Formatter (S16):** golden strings per source type and author-count case; a/b disambiguation;
  list order; DOI over URL; en-dash ranges; parenthetical, narrative, multi-source and page-locator
  citations; the web style from the same records; an unsupported type fails.
- **Citation resolver (S16):** unknown key fails; uncited record fails; duplicate key fails; an
  email address in the text is not a citation.
- **Build (S15):** a draft in the Essays folder fails a build without `--strict`; a `type: essay` note outside it
  fails; an essay never becomes a Garden card; essay pages carry a filled security policy and
  cache-busted URLs; a wikilink to an unpublished note fails; the build stays byte-identical on a
  rerun (`tests/test_reproducible_build.py`). A `.DS_Store` or `Thumbs.db` in the folder does
  not fail it, since `.gitignore` already keeps both out of the repository (S15's one carve-out
  from check 3).
- **Privacy (S15), each in a build without `--strict`:** an unknown frontmatter or reference field fails; `abstract`, `annote` and
  `note` fail; a Drive, Docs, Gemini, NotebookLM or reMarkable URL anywhere fails; a non-text file
  in the folder fails; a companion URL off the media allowlist fails (S17).
- **Browser (S15 to S18):** both pages pass axe at WCAG A/AA in both offered themes; no horizontal
  scroll at a 375-pixel phone width; the companion zone carries its label; no request to YouTube
  before the tap and one after it; no audio request before play.

## Out of scope for the first version

Footnotes; the citation types listed above; a per-essay social image; a table of contents; a
print stylesheet or PDF export; comments or a newsletter; a sitemap; essays in Garden backlinks
(B22); analytics (B21); `deploy.py`'s factory clone carrying Essays (S15 decides whether it
does, and records it).

## Open questions (not blocking)

- **A serif body for essays.** The brand sets body text in the grotesque. A journal-article
  feel may want a text serif, but Cormorant Garamond is a display face and reads poorly at body
  size on phones. A brand call for Travis, whenever he wants it.
- **Should the pre-push hook block on an Essays privacy failure** rather than warn? It lives in
  the dev root, not this repo, and applies to every repo there.
- **Mini Essay #1.** vault/00_Meta holds a Word-exported PDF of a May 2026 mini essay, public
  since commit 5a80d5c. It is untouched by this design; whether it becomes an essay is Travis's
  content call.
