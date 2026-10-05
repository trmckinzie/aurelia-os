// Shared fixtures for the browser suite.
//
// Every test gets a `guard` that watches its page from the first request to
// the last, and fails the test at the end if anything below happened. Because
// it is automatic, the foreign-origin check runs in every test, with every
// dialog and reader state the tests reach, not only in the test named for it.
//   - a console error or an uncaught page error
//   - a request that failed, or a response of 400 or above, other than a
//     status a test declared it expects (the 404 page's own document)
//   - a request to any origin other than the test server's. data: and blob:
//     URLs are local, so they are allowed. This keeps the promise in
//     docs/DECISIONS.md item 29: no page asks another server for anything.
import { test as base, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

export { expect };

const LOCAL_SCHEMES = new Set(["data:", "blob:", "about:"]);

export const test = base.extend({
  guard: [
    async ({ page, baseURL }, use) => {
      const origin = new URL(baseURL).origin;
      const problems = [];
      const expected = [];
      const foreign = [];

      page.on("console", (msg) => {
        if (msg.type() !== "error") return;
        // Chrome logs every 4xx response as a console error too; one the
        // test declared (the 404 page's own document) is not a problem.
        const status = /status of (\d{3})/.exec(msg.text())?.[1];
        const where = msg.location()?.url ?? "";
        if (status && expected.some((e) => e.status === Number(status) && e.test(where))) return;
        problems.push(`console error: ${msg.text()} ${where}`.trim());
      });
      page.on("pageerror", (err) => problems.push(`page error: ${err.message}`));
      page.on("request", (req) => {
        const url = new URL(req.url());
        if (LOCAL_SCHEMES.has(url.protocol)) return;
        if (url.origin !== origin) foreign.push(req.url());
      });
      page.on("requestfailed", (req) => {
        // A navigation that a later navigation replaced is aborted by the
        // browser, not failed by the server; that is not a defect.
        const reason = req.failure()?.errorText ?? "";
        if (reason.includes("ERR_ABORTED") && req.isNavigationRequest()) return;
        problems.push(`request failed: ${req.url()} (${reason})`);
      });
      page.on("response", (res) => {
        if (res.status() < 400) return;
        const allowed = expected.some((e) => e.status === res.status() && e.test(res.url()));
        if (!allowed) problems.push(`HTTP ${res.status()}: ${res.url()}`);
      });

      await use({
        origin,
        // Declares a response status this test expects, e.g. the 404 page.
        expectStatus(status, urlMatcher) {
          expected.push({ status, test: (u) => (typeof urlMatcher === "string" ? u.includes(urlMatcher) : urlMatcher.test(u)) });
        },
        foreign,
        problems,
      });

      expect(foreign, "requests to another origin (only the site's own files may load)").toEqual([]);
      expect(problems, "console errors, page errors or failed requests").toEqual([]);
    },
    { auto: true },
  ],
});

// WCAG 2.0 and 2.1, levels A and AA: the tags the build gate enforces.
export const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

// Known violations, each one rule on one selector, with its reason and the
// docs/roadmap.yaml backlog entry that removes it. Every other element is
// still checked by that rule, and these elements by every other rule. Never
// disable a rule outright or exclude a region: add an entry here instead,
// and delete it in the change that fixes the defect.
export const AXE_EXCEPTIONS = [
  {
    rule: "nested-interactive",
    selector: '#cardGrid > article.searchable-item[role="button"]',
    backlog: "B19",
    reason:
      "A Garden card is role=button and contains the link and topic pills, which are buttons too. " +
      "A button's children are presentational, so a screen reader cannot reach the pills from the card. " +
      "Fixing it changes how every card is built and navigated, which is more than S08's scope.",
  },
];

// Runs axe on the page as it stands and fails on any violation not listed in
// AXE_EXCEPTIONS. `include` narrows the scan to an open dialog or reader, so
// a page-level issue is not counted again for every state of it.
// `rules` runs only the named rules instead of every rule with the WCAG tags
// (axe takes one or the other), so pass only rules that carry those tags.
export async function expectNoAxeViolations(page, { include, rules } = {}) {
  let builder = new AxeBuilder({ page }).withTags(WCAG_TAGS);
  if (rules) builder = builder.withRules(rules);
  if (include) builder = builder.include(include);
  const results = await builder.analyze();
  const violations = [];
  for (const v of results.violations) {
    const rules = AXE_EXCEPTIONS.filter((e) => e.rule === v.id);
    let nodes = v.nodes;
    if (rules.length) {
      // A node's target is a CSS selector path; match the element it names
      // against each exception's selector in the page itself.
      const keep = await page.evaluate(
        ({ targets, selectors }) =>
          targets.map((t) => {
            const el = t.length === 1 ? document.querySelector(t[0]) : null;
            return !(el && selectors.some((s) => el.matches(s)));
          }),
        { targets: nodes.map((n) => n.target), selectors: rules.map((e) => e.selector) },
      );
      nodes = nodes.filter((_, i) => keep[i]);
    }
    if (nodes.length) violations.push({ ...v, nodes });
  }
  const summary = violations.map((v) => ({
    rule: v.id,
    impact: v.impact,
    help: v.help,
    nodes: v.nodes.slice(0, 5).map((n) => ({ target: n.target.join(" "), summary: n.failureSummary })),
    more: Math.max(0, v.nodes.length - 5),
  }));
  expect(summary, "axe WCAG A/AA violations").toEqual([]);
}
