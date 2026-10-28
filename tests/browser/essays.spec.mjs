// Essays (roadmap S15, docs/ESSAYS.md): the index at /essays/ and one page
// per essay, checked in a real browser at phone width.
//
// No essay is in the vault yet, so verify.sh runs this spec twice. First on
// a build that reads the fixture essay from tests/fixtures/essays/
// (AURELIA_ESSAYS_DIR), with AURELIA_ESSAYS_FIXTURE=1 so a build that quietly
// produced no essays fails here rather than skipping. Then on the real
// build, where the first group skips and the second holds the live site to
// "nothing a visitor sees changes": no Essays link, no empty index.
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test, expect, expectNoAxeViolations } from "./fixtures.mjs";
import { BASE_PATH } from "./site.mjs";

const DIST = fileURLToPath(new URL("../../dist/", import.meta.url));
const FIXTURE_BUILT = existsSync(DIST + "essays/index.html");
if (process.env.AURELIA_ESSAYS_FIXTURE && !FIXTURE_BUILT) {
  throw new Error("AURELIA_ESSAYS_FIXTURE is set but dist/essays/index.html is missing: build with AURELIA_ESSAYS_DIR=tests/fixtures/essays first");
}

const ESSAY_PATH = "essays/why-loss-looms-larger/";
// The second fixture essay (roadmap S18): citation_style: web, so its
// in-text citations link straight to a source instead of jumping to a
// reference-list entry, and its list is "Sources" rather than "References".
const WEB_ESSAY_PATH = "essays/attention-is-a-budget/";
const PHONE = { width: 375, height: 812 };

// The study companion's media host (user_config.json's media_origins) and
// the YouTube player (roadmap S17). Neither may be asked for anything before
// a reader presses play. The suite serves both itself, so CI never depends on
// the bucket or on Google; AURELIA_LIVE_MEDIA=1 lets the audio test fetch the
// real test file from the bucket instead.
const MEDIA_ORIGIN = "https://media.travisrmckinzie.com";
const AUDIO_URL = `${MEDIA_ORIGIN}/test/tone.wav`;
const YOUTUBE_PLAYER = "https://www.youtube-nocookie.com";
const LIVE_MEDIA = Boolean(process.env.AURELIA_LIVE_MEDIA);
const GOOGLE_HOST = /(^|\.)(youtube\.com|youtube-nocookie\.com|youtu\.be|ytimg\.com|googlevideo\.com|google\.com|gstatic\.com|doubleclick\.net)$/;

// A two-second 440 Hz tone as a 16-bit mono WAV, which every Chromium build
// plays (Playwright's has no AAC).
function toneWav(seconds = 2, rate = 8000) {
  const samples = seconds * rate;
  const buffer = Buffer.alloc(44 + samples * 2);
  buffer.write("RIFF", 0); buffer.writeUInt32LE(36 + samples * 2, 4); buffer.write("WAVE", 8);
  buffer.write("fmt ", 12); buffer.writeUInt32LE(16, 16); buffer.writeUInt16LE(1, 20); buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(rate, 24); buffer.writeUInt32LE(rate * 2, 28); buffer.writeUInt16LE(2, 32); buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36); buffer.writeUInt32LE(samples * 2, 40);
  for (let i = 0; i < samples; i++) buffer.writeInt16LE(Math.round(8000 * Math.sin((2 * Math.PI * 440 * i) / rate)), 44 + i * 2);
  return buffer;
}

async function expectNoHorizontalScroll(page) {
  const widths = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(widths.scroll, "the page must not scroll sideways at phone width").toBeLessThanOrEqual(widths.client);
}

test.describe("with the fixture essay built", () => {
  test.skip(!FIXTURE_BUILT, "dist/ was built without essays");
  test.use({ viewport: PHONE });

  test("the index lists the essay with its title, weekday date, disciplines, thesis and reading time, and the nav shows Essays", async ({ page }) => {
    await page.goto("essays/");
    const entry = page.locator('#essay-list [data-essay-id="E01"]');
    await expect(entry.getByRole("heading", { level: 2 })).toHaveText("Why loss looms larger");
    await expect(entry.locator("time")).toHaveText("Friday, 20 November 2026");
    await expect(entry.locator("time")).toHaveAttribute("datetime", "2026-11-20");
    await expect(entry.locator(".essay-disciplines li")).toHaveText(["cognitive psychology", "philosophy"]);
    await expect(entry.locator(".essay-thesis")).toContainText("Losses weigh more than equal gains");
    await expect(entry.locator(".essay-reading-time")).toHaveText(/^\d+-minute read$/);
    // The nav's phone menu carries the Essays item, marked current.
    await page.locator("#mobile-menu-btn").click();
    const navItem = page.locator('#mobile-menu a[href$="essays/"]');
    await expect(navItem).toBeVisible();
    await expect(navItem).toHaveText("ESSAYS");
    await expect(navItem).toHaveAttribute("aria-current", "page");
    await expectNoHorizontalScroll(page);
  });

  test("the essay page shows its byline, dates and body", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Why loss looms larger");
    await expect(page.locator(".essay-byline")).toHaveText("Travis R. McKinzie");
    const dates = page.locator(".essay-dates");
    await expect(dates).toContainText("Friday, 20 November 2026");
    await expect(dates).toContainText("Updated Sunday, 22 November 2026");
    await expect(dates.locator(".essay-reading-time")).toHaveText(/^\d+-minute read$/);
    const body = page.locator(".essay-body");
    await expect(body.getByRole("heading", { level: 2, name: "The shape of the asymmetry" })).toBeVisible();
    await expect(body.locator("blockquote")).toBeVisible();
    await expect(body.locator("ul li")).toHaveCount(3);
    await expectNoHorizontalScroll(page);
  });

  // Roadmap S16: APA 7 in-text citations that jump to their entries, and a
  // reference list with a hanging indent, APA's italics and DOI links.
  test("each citation reads as APA 7 and jumps to its reference entry", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const citations = page.locator(".essay-body a.essay-citation");
    expect(await citations.count()).toBeGreaterThan(8);
    await expect(page.locator(".essay-missing-citation")).toHaveCount(0);
    await expect(citations.first()).toHaveText("Kahneman et al., 1990");
    await expect(page.locator(".essay-body a.essay-citation", { hasText: "Kahneman and Tversky (1982)" })).toHaveCount(1);
    await expect(page.locator(".essay-body a.essay-citation", { hasText: "Kahneman & Tversky, 1979b, p. 279" })).toHaveCount(1);
    await expect(page.locator(".essay-body")).toContainText("(Kahneman & Tversky, 1979b; Thaler, 1980)");
    await expect(page.locator(".essay-body")).toContainText("essays@example.com");

    // Every citation targets an entry that exists.
    const targets = await citations.evaluateAll((links) => links.map((a) => a.getAttribute("href")));
    for (const href of new Set(targets)) {
      await expect(page.locator(`.essay-reference-list li${href}`), href).toHaveCount(1);
    }

    // Following one lands on its entry, visible below the fixed nav.
    const thaler = page.locator('.essay-body a.essay-citation[href="#ref-thaler1980"]').first();
    await thaler.click();
    await expect(page).toHaveURL(/#ref-thaler1980$/);
    const entry = page.locator("#ref-thaler1980");
    await expect(entry).toBeInViewport();
    await expect(entry).toContainText("Thaler, R. H. (1980). Toward a positive theory of consumer choice.");
    const navBottom = await page.locator("nav.nav-shell").evaluate((n) => n.getBoundingClientRect().bottom);
    const entryTop = await entry.evaluate((li) => li.getBoundingClientRect().top);
    expect(entryTop, "the entry must not sit under the fixed nav").toBeGreaterThanOrEqual(navBottom);
    await expectNoHorizontalScroll(page);
  });

  test("the reference list has hanging indents, APA 7 italics and DOIs as https://doi.org/ links", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const list = page.locator(".essay-references");
    await expect(list.getByRole("heading", { level: 2 })).toHaveText("References");
    const entries = list.locator(".essay-reference-list li");
    await expect(entries).toHaveCount(8);
    await expect(entries.first()).toHaveText(/^American Psychological Association\. \(2020\)\./);

    // A hanging indent: the first line starts left of the lines after it.
    const indent = await entries.first().evaluate((li) => {
      const style = getComputedStyle(li);
      return { text: parseFloat(style.textIndent), pad: parseFloat(style.paddingLeft) };
    });
    expect(indent.text).toBeLessThan(0);
    expect(indent.pad).toBeCloseTo(-indent.text, 1);

    // Italic journal title and volume; the issue and the article title stay roman.
    const journal = page.locator("#ref-kahneman1979");
    await expect(journal.locator("i")).toHaveText(["Econometrica", "47"]);
    expect(await journal.locator("i").first().evaluate((i) => getComputedStyle(i).fontStyle)).toBe("italic");
    await expect(page.locator("#ref-kahneman2011 i")).toHaveText("Thinking, fast and slow");
    await expect(page.locator("#ref-kahneman1982 i")).toHaveText("Judgment under uncertainty: Heuristics and biases");
    await expect(page.locator("#ref-steele2020 i")).toHaveText("The Stanford encyclopedia of philosophy");

    // DOIs as links; en-dash page ranges.
    const doi = journal.locator("a");
    await expect(doi).toHaveAttribute("href", "https://doi.org/10.2307/1914185");
    await expect(doi).toHaveText("https://doi.org/10.2307/1914185");
    await expect(journal).toContainText("263–291");
    await expectNoHorizontalScroll(page);
  });

  test("a Garden link in the essay opens the right Garden note", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const link = page.locator('.essay-body a[data-garden-note="note-active-recall"]');
    await expect(link).toHaveText("active recall");
    await expect(link).toHaveAttribute("href", `${BASE_PATH}garden.html#note-active-recall`);
    await link.click();
    await expect(page).toHaveURL(new RegExp(`${BASE_PATH}garden\\.html#note-active-recall$`));
    const reader = page.locator("#modal-panel");
    await expect(reader).toHaveClass(/is-open/);
    await expect(page.locator("#modal-title")).toHaveText("Active Recall");
  });

  test("a discipline label links to its Garden note", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const discipline = page.locator('.essay-disciplines a[href$="#note-cognitive-psychology"]');
    await expect(discipline).toHaveText("cognitive psychology");
    await discipline.click();
    await expect(page.locator("#modal-title")).toHaveText("Cognitive Psychology");
  });

  // Roadmap S18: citation_style: web renders each citation as a link on the
  // short author-year text straight to the source, and ends with a "Sources"
  // list instead of the APA 7 reference list -- both from the same records.
  test("a web-style essay links citations straight to their sources and ends with a Sources list", async ({ page }) => {
    await page.goto(WEB_ESSAY_PATH);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Attention is a budget");

    const citations = page.locator(".essay-body a.essay-citation");
    expect(await citations.count()).toBeGreaterThan(0);
    await expect(page.locator(".essay-missing-citation")).toHaveCount(0);
    await expect(page.locator(".essay-citation-unlinked")).toHaveCount(0);

    // Straight to the source, never to a reference-list entry.
    const hrefs = await citations.evaluateAll((links) => links.map((a) => a.getAttribute("href")));
    for (const href of hrefs) expect(href.startsWith("#")).toBe(false);
    const doiCitation = page.locator('.essay-body a.essay-citation[href="https://doi.org/10.2307/1914185"]');
    await expect(doiCitation).toHaveCount(1);
    await expect(doiCitation).toHaveAttribute("rel", "noopener noreferrer");

    const list = page.locator(".essay-references");
    await expect(list.getByRole("heading", { level: 2 })).toHaveText("Sources");
    const entries = list.locator(".essay-reference-list li");
    expect(await entries.count()).toBeGreaterThan(0);
    await expect(list.locator('a[href="https://doi.org/10.2307/1914185"]')).toHaveCount(1);
    await expectNoHorizontalScroll(page);
  });

  for (const [name, path] of [["index", "essays/"], ["essay page", ESSAY_PATH], ["web-style essay page", WEB_ESSAY_PATH]]) {
    test(`the ${name} has no WCAG A/AA violations in either offered theme, at phone width and on a desktop`, async ({ page }) => {
      test.slow();
      for (const viewport of [PHONE, { width: 1440, height: 900 }]) {
        await page.setViewportSize(viewport);
        await page.goto(path);
        const themes = await page.evaluate(() => AVAILABLE_THEMES.map((t) => t.key));
        expect(themes.length).toBeGreaterThan(1);
        for (const theme of themes) {
          await page.evaluate((t) => localStorage.setItem("aurelia_theme", t), theme);
          await page.reload();
          await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
          await test.step(`${theme} at ${viewport.width}px`, () => expectNoAxeViolations(page));
          if (viewport.width === PHONE.width) await expectNoHorizontalScroll(page);
        }
      }
    });
  }

  // Roadmap S17: the disclosure note, the study companion and the episode.
  test("the disclosure note's counts match the reference list", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const note = page.locator(".essay-disclosure");
    await expect(note.getByRole("heading", { level: 2 })).toHaveText("How this essay was made");
    const entries = await page.locator(".essay-reference-list li").count();
    expect(entries).toBe(8);
    await expect(note).toHaveAttribute("data-sources", String(entries));
    const verified = Number(await note.getAttribute("data-verified"));
    expect(verified).toBe(6);
    await expect(note).toContainText(`${entries} sources; ${verified} of ${entries} verified against the original by the author.`);
    await expect(note).toContainText("AI was used for research, not writing.");
    await expectNoHorizontalScroll(page);
  });

  test("the study companion is a separate zone with its AI label, in either offered theme", async ({ page }) => {
    await page.goto(ESSAY_PATH);
    const themes = await page.evaluate(() => AVAILABLE_THEMES.map((t) => t.key));
    for (const theme of themes) {
      await page.evaluate((t) => localStorage.setItem("aurelia_theme", t), theme);
      await page.reload();
      const zone = page.locator('section.essay-companion[data-ai-generated="true"]');
      await expect(zone.getByRole("heading", { level: 2 })).toHaveText("AI-generated study companion");
      await expect(zone).toContainText("Made with Gemini Notebook from this essay and the open-access sources listed.");
      const surfaces = await page.evaluate(() => {
        const bg = (sel) => getComputedStyle(document.querySelector(sel)).backgroundColor;
        return { page: bg("body"), essay: bg(".essay-body"), disclosure: bg(".essay-disclosure"),
                 references: bg(".essay-references"), companion: bg(".essay-companion"),
                 rule: getComputedStyle(document.querySelector(".essay-companion")).borderTopWidth };
      });
      // The essay, its disclosure note and its references share the page's
      // paper; the companion alone has a surface of its own.
      for (const part of ["essay", "disclosure", "references"]) {
        expect(surfaces[part], `${theme}: ${part}`).toBe("rgba(0, 0, 0, 0)");
      }
      expect(surfaces.companion, theme).not.toBe(surfaces.page);
      expect(surfaces.companion, theme).not.toBe("rgba(0, 0, 0, 0)");
      expect(parseFloat(surfaces.rule), theme).toBeGreaterThanOrEqual(4);
      // Only players and links: an audio player and one link, from the entries.
      await expect(zone.locator("audio")).toHaveCount(1);
      await expect(zone.locator("ul > li > a")).toHaveText(["Flashcards (CSV)"]);
      await expectNoHorizontalScroll(page);
    }
  });

  test("no audio request before play, and the test audio file plays after it", async ({ page, guard }) => {
    const mediaRequests = [];
    page.on("request", (req) => { if (new URL(req.url()).origin === MEDIA_ORIGIN) mediaRequests.push(req.url()); });
    guard.expectForeign(AUDIO_URL);
    if (!LIVE_MEDIA) {
      await page.route(`${MEDIA_ORIGIN}/**`, (route) =>
        route.fulfill({ status: 200, contentType: "audio/wav", body: toneWav() }));
    }
    await page.goto(ESSAY_PATH);
    const audio = page.locator(".essay-companion audio");
    await expect(audio).toHaveAttribute("preload", "none");
    await audio.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    expect(mediaRequests, "nothing from the media host before play").toEqual([]);

    await audio.evaluate((a) => a.play());
    await expect.poll(() => audio.evaluate((a) => a.currentTime), { timeout: 15000 }).toBeGreaterThan(0);
    await audio.evaluate((a) => { a.pause(); });
    expect(mediaRequests.length).toBeGreaterThan(0);
    expect(new Set(mediaRequests)).toEqual(new Set([AUDIO_URL]));
  });

  test("the YouTube player appears only after Play episode is pressed", async ({ page, guard }) => {
    const googleRequests = [];
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (GOOGLE_HOST.test(url.hostname)) googleRequests.push(req.url());
    });
    guard.expectForeign(`${YOUTUBE_PLAYER}/embed/`);
    // A stand-in player, so the test proves when the page asks for one
    // without loading anything from Google.
    await page.route(`${YOUTUBE_PLAYER}/**`, (route) =>
      route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>Player</title><p>Player</p>" }));

    await page.goto(ESSAY_PATH);
    const listen = page.locator(".essay-listen");
    await expect(listen.getByRole("heading", { level: 2 })).toHaveText("Listen");
    await expect(listen).toContainText("Nothing loads from YouTube until you press Play episode.");
    await expect(listen.locator("iframe")).toHaveCount(0);
    await page.evaluate(() => document.fonts.ready);
    expect(googleRequests, "nothing from Google before the tap").toEqual([]);

    await listen.getByRole("button", { name: "Play episode" }).click();
    const frame = listen.locator("iframe");
    await expect(frame).toBeVisible();
    await expect(frame).toHaveAttribute("src", `${YOUTUBE_PLAYER}/embed/XXXXXXXXXXX?autoplay=1`);
    await expect(frame).toHaveAttribute("title", "Episode: Why loss looms larger");
    await expect(frame).toBeFocused();
    await expect(page.frameLocator(".essay-listen iframe").locator("p")).toHaveText("Player");
    expect(googleRequests).toEqual([`${YOUTUBE_PLAYER}/embed/XXXXXXXXXXX?autoplay=1`]);
    await expectNoHorizontalScroll(page);
  });

  test("every essay page carries a filled Content-Security-Policy and loads only the site's own files", async ({ page, guard }) => {
    for (const path of ["essays/", ESSAY_PATH]) {
      await page.goto(path);
      const policy = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute("content");
      expect(policy, path).toMatch(/script-src 'self' 'sha256-/);
      expect(policy, path).toMatch(/style-src 'self' 'sha256-/);
      expect(policy, path).not.toContain("@@csp@@");
      const stylesheet = await page.locator('link[href*="assets/css/main.css"]').getAttribute("href");
      expect(stylesheet, path).toMatch(/^\/.*main\.css\?v=[0-9a-f]{10}$/);
      await page.evaluate(() => document.fonts.ready);
    }
    expect(guard.foreign).toEqual([]);
  });
});

test.describe("without any essay published (the live site today)", () => {
  test.skip(FIXTURE_BUILT, "dist/ carries the fixture essay");

  test("no page shows an Essays link and /essays/ is the 404 page", async ({ page, guard }) => {
    for (const path of ["index.html", "garden.html", "about.html"]) {
      await page.goto(path);
      expect(await page.locator('a[href$="essays/"]').count(), path).toBe(0);
      expect(await page.getByText("ESSAYS", { exact: true }).count(), path).toBe(0);
    }
    guard.expectStatus(404, "/essays/");
    const response = await page.goto("essays/");
    expect(response.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  });
});
