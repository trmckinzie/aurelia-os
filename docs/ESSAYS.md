# Essays

Design for a fourth kind of published content: short human-written essays on psychology,
philosophy and adjacent subjects, each with a fixed disclosure note and an AI-generated study
companion. Planned 2026-10-12 from Travis's handoff of 2026-10-11; built across roadmap sessions
S15 to S18 (`docs/roadmap.yaml`), after S12 and before S13. The decisions behind it are
`docs/DECISIONS.md` item 41.

S15 is built (2026-10-14, `docs/DECISIONS.md` item 43): the content type in `engine/essays.py`,
the draft gate and privacy checks, the index and essay pages (`system/templates/pages/essaystemplate.html`
and `essaytemplate.html`), the Garden links, and the recursive security-policy and cache-busting
walks. S16 is built (2026-10-15, item 44): citations and the APA 7 reference list, in
`engine/citations.py`. S17 is built (2026-10-18, item 45): the disclosure note, the study
companion, the `media_origins` allowlist and the tap-to-load episode. S18 is built (2026-10-28,
item 48): the web citation style, the Article JSON-LD, per-essay Open Graph, the Atom feed at
`engine/feed.py`, and essays in the site search. Paths that do not exist yet are written plainly
rather than as code, so `tests/test_docs_paths.py` does not hold them to the file system until a
session creates them; vault/30_ESSAYS/ is one of them, since no essay is in the vault until Travis
publishes the first. Two test essays live in `tests/fixtures/essays/` (E01, `citation_style: apa7`;
E02, `citation_style: web`), and the build reads them through `AURELIA_ESSAYS_DIR`.

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
5. **Companion and media origins.** A companion URL, of any kind, whose origin is not on the
   `media_origins` allowlist in `user_config.json` fails (see "Media"), as does a `youtube`
   address with no video id in it. With no origins configured, any companion entry fails.

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
  drafted_on: reMarkable      # a tool's name, 60 characters at most
  edited_in: Google Docs      # likewise
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
editions), `genre` (a preprint's bracketed description, "Preprint" when absent), `open_access`,
`verified`. Everything else fails. A preprint's server goes in `publisher`, as Zotero exports it.

The shape of each record is part of the contract and also fails every build (S16): `id` is a
citation key (letters, digits and `_`, with `:`, `.`, `/` and `-` allowed only between them, so
it is safe as an HTML id); `verified` is required on every record, `true` or `false`, so the
disclosure count never reads a missing answer as "no"; `open_access` is `true` or `false`; and
`author` and `editor` are lists of names, each `{family, given}` for a person or `{literal}` for
a group, with nothing else inside a name. `issued`, when present, is a four-digit year (a record
without one is left out of the list with a warning, like any record missing what its type needs).

The disclosure note counts the records: "N sources; M of N verified against the original by the
author", where M counts `verified: true`. It counts the records the reference list shows, so
the numbers match the list even on a local build that left a record out with a warning; the
strict build guarantees none is left out (see "Citations").

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
cites fails. Duplicate keys fail, as does a record of an unsupported type or one missing what its
type needs, which is left out of the list. These leak nothing, so they go through `warn()` and
fail the strict build, as a dangling wikilink does; a local preview still builds.

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
in") and footnotes. A record of an unsupported `type` is left out of the list with a warning,
so the strict build fails rather than rendering it wrong.

S16 first checked whether a maintained CSL processor renders the APA 7 style correctly for the
five types. citeproc-py 0.11.1 with the official `apa.csl` did not (no year suffixes, an
unsorted list, "(eds.)", a crash on page locators), so the formatter is the small in-house
module `engine/citations.py` (`docs/DECISIONS.md` item 44). The records are CSL either way, so
the choice can be reversed later.

**How the first version reads the syntax** (S16):

- Within one parenthetical citation, works are put in reference-list order, as APA 7 asks, and
  the same authors share one name: `[@kahneman1979; @kahneman1979a]` renders "(Kahneman &
  Tversky, 1979a, 1979b)". A prefix (`[see @key]`) keeps the order as written.
- Pandoc's other forms work too: a locator without the comma (`[@key p. 12]`), a suppressed
  author (`[-@key]` renders "(1979)"), and a narrative locator (`@key [p. 12]` renders
  "Kahneman and Tversky (1979, p. 12)"). A page range written with "p." becomes "pp.", and every
  range takes an en dash.
- `\@` writes a literal at sign. A word-initial `@name` that is no key in the reference file
  renders as written but warns, so a misspelled narrative citation fails the strict build; an
  email address or a URL path (`example.com/@name`) is never read as one. A citation inside a
  code span or link text stays literal, and `![@key]` is an image.
- Any bracket that opens with `@` is read as a citation, so `[@media screen]` warns as one with
  no record; write `[\@media screen]`.
- A field a record's type does not show (an `edition` on a journal article, a `page` on a
  preprint) warns rather than being dropped silently.
- Every work is linked to its entry; a citation with no record renders as written, muted, and
  warns.
- Two different works that would cite the same way ("Lee et al., 2023" twice) warn instead of
  rendering ambiguously: APA 7 adds author names to tell them apart, which the first version
  does not. Neither does it abbreviate a group author on second use.

**Web style** (`citation_style: web`, built S18), from the same records: each citation renders as
a link on the short author-year text, straight to the source's DOI or URL (DOI preferred, as an
`https://doi.org/` link, same as APA 7), and the essay ends with a short "Sources" list (title,
authors, year, link) in place of the APA reference list. The record-shape checks, the missing-
record and uncited-record warnings, and the two-works-that-would-cite-alike warning are the same
checks the APA 7 style uses, since they are about the citations and the records, not about either
style's text. A record with neither a DOI nor a URL has nothing to link to: its citations render
as plain text, muted, and `engine/citations.py` warns once per record (not per citation), so the
strict build fails on it the way an unsupported type does. `engine/essays.py`'s
`References(..., style=essay["citation_style"])` is the one switch between the two; which list an
essay gets is otherwise invisible to the rest of the pipeline.

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
   > Docs. AI was used for research, not writing. An AI assistant searched for sources and drafted
   > short summaries of them; I checked each summary against the original and wrote every evaluation
   > myself. An AI citation audit checked that each citation supports its claim and matches the
   > reference list; it flagged problems and changed no prose. 14 sources; 14 of 14 verified
   > against the original by the author.

   Sentences drop out with their roles: no citation audit in `ai_roles`, no audit sentence. The
   note names no AI vendor. With no AI role it says "No AI was used in researching or writing
   it.", except on an essay with a study companion, where that sentence is left out because it
   would sit directly above the AI-generated zone.
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
- **Exported assets only.** The companion links exported files on an allowed media origin (an
  audio overview, a video file, exported flashcards), never a notebook. A video on YouTube is the
  essay's `youtube` episode, not a companion entry (`docs/DECISIONS.md` item 45).
- **What renders (S17).** An `audio` entry is an `<audio controls preload="none">`, a `video`
  entry a `<video controls preload="none">`, and an `other` entry a plain link, each under its
  label. Only an essay page with a player widens its policy's `media-src`, and only one with an
  episode gains the `frame-src`; the rest of the site keeps both closed. The fixture essay's
  audio entry points at `test/tone.wav` on the media host: the browser suite serves its own copy
  there, and `AURELIA_LIVE_MEDIA=1` makes it use the real one from the bucket.

The footer says "No analytics or tracking." That stays true through S15 to S18: the site's own
pages still track nothing, and the YouTube player loads only on a reader's tap, with a note beside
the control saying so. Basic analytics, and a footer that matches whatever is then true, are
backlog item B21, decided separately.

## Metadata

Built S18, `docs/DECISIONS.md` item 48:

| | Every other page | An essay page |
|---|---|---|
| Open Graph | `og:type` website; title and description from `base.html`'s blocks; one site-wide preview image | `og:type` article (`{% block og_type %}`); title and description are the essay's own title and thesis; `article:published_time` and `article:modified_time` (the latter falling back to `published` with no `updated`). The preview image stays site-wide. |
| `og:url` and canonical URL | From `site.domain` plus the page's path | The essay's own URL (`essays/<slug>/`), the same path the canonical link already used since S15. |
| Structured data | Person on About only (`engine/profile.py`'s `person_jsonld()`) | An Article (`engine/essays.article_jsonld()`): headline, author (the same Person dict, not a hand-duplicated copy), `datePublished`/`dateModified`, its own URL as `url`/`mainEntityOfPage`, and one `citation` entry per reference the page's list actually shows -- a ScholarlyArticle for a journal article or a preprint, else a CreativeWork (`engine/citations.citation_jsonld()`). |
| Feed | None | Every page links `/essays/feed.xml` once it exists (`<link rel="alternate" type="application/atom+xml">`, `base.html`). |
| Search | Garden notes and the three system pages | Essays join the same index, opening their own URL rather than the Garden's note reader. |

The feed itself, `engine/feed.py`: Atom over RSS because its one specification requires the ids
and update dates a reader needs, and every feed reader supports it. One entry per published
essay, newest first; each entry's id and links are the essay's own absolute URL -- permanent by
the same contract as the URL itself (see "Pages and URLs"), not a `tag:` URI (`docs/DECISIONS.md`
item 48 records the choice). An entry's content is the full rendered essay plus "How this essay
was made" and the reference list (or the web style's Sources list) -- never the study companion or
the YouTube episode, the one place AI output appears. Relative links the essay carries (a Garden
wikilink, an in-text citation's own `#ref-<key>` anchor) are rewritten absolute, since a feed entry
has no notion of the page it came from. Built with `xml.etree.ElementTree`, never string
concatenation. The feed needs `site.domain` configured (its ids must be absolute); without one
`engine/pipeline.py` warns and writes neither the file nor the link, which never happens on the
real site since a domain is already configured (roadmap S14).

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

Since S16 the first test essay (E01, `citation_style: apa7`) cites eight real sources in every
form, and since S17 it carries a companion and an episode. Since S18 a second test essay (E02,
`citation_style: web`, `tests/fixtures/essays/E02 Attention is a budget.md`) exercises the web
style end to end. With S17 done, Travis may publish the first real essay. The Essays nav item
and index appear only once one essay is published, so S15 to S18 change nothing a visitor sees.
Each session's acceptance was checked on phone-width (375-pixel) screenshots of a build that
includes the test essays, attached to its pull request; the first real essay, published by
Travis whenever he chooses to, is the check on the live site.

## Test plan

All of it in `verify.sh`, so CI and a local run agree. The test essays live under `tests/fixtures/`,
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
- **Web style (S18, `tests/test_citations.py`):** a citation links to the record's DOI or URL, not
  to a reference-list entry; a record with neither renders unlinked and warns once; the Sources
  list is title/authors/year/link; the missing-record, uncited-record and ambiguous-citation
  warnings are the same ones the APA 7 style raises.
- **Article JSON-LD and per-essay Open Graph (S18, `tests/test_essays.py`):** the Article parses
  with `@type: Article`, reuses the About page's own Person as its author, and cites the page's
  own reference list; `og:type` is article only on an essay page and website everywhere else;
  `article:published_time`/`article:modified_time` and `og:url` read from the essay's own dates
  and URL.
- **The Atom feed (S18, `tests/test_feed.py`):** parses, and carries every element Atom requires
  (feed: id, title, updated, author; entry: id, title, updated); lists the fixture essays, newest
  first; an entry's content is the essay plus its disclosure note and references, never the
  companion or the episode; a relative link in that content comes out absolute. Built and linked
  only with at least one essay published (`tests/test_essays.py`'s real-build tests), both ways.
- **Search (S18, `tests/test_essays.py`):** an essay is an entry in the site's search index,
  opening its own URL rather than the Garden's note reader; the Garden's own entries are unchanged.
- **Browser (S15 to S18):** both pages pass axe at WCAG A/AA in both offered themes, now including
  a web-style essay page; no horizontal scroll at a 375-pixel phone width; the companion zone
  carries its label; no request to YouTube before the tap and one after it; no audio request
  before play; a web-style essay's citations link straight to their sources and its list reads
  "Sources".

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
