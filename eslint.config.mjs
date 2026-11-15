// Lint for the Garden's client modules and their unit tests (roadmap S13).
// Run by verify.sh as `npx --no-install eslint`, which reads the files
// named below.
//
// The rule that earns its place is no-undef. The modules in assets/js/garden/
// were one 2,800-line script in which every function could see every other;
// as modules, a call into another file needs an import, and one that is
// missing fails only when that line runs in a browser. no-undef finds it
// here instead.
//
// The other scripts in assets/js/ are classic scripts that publish globals,
// and are not linted yet (docs/DECISIONS.md, known gaps).
import js from "@eslint/js";

// What a browser gives every script. Written out, not taken from the
// `globals` package, so the list is only what these modules use and a typo
// that happens to match some other browser global is still caught.
const browser = Object.fromEntries([
  "window", "document", "location", "history", "navigator", "localStorage",
  "console", "setTimeout", "clearTimeout", "requestAnimationFrame",
  "getComputedStyle", "CSS", "URL", "URLSearchParams", "Blob", "FileReader",
  "ResizeObserver", "speechSynthesis", "SpeechSynthesisUtterance",
].map((name) => [name, "readonly"]));

// What the page's classic scripts define before the modules run:
// assets/js/utils.js, assets/js/review.js, assets/js/flashcards.js, and the
// vendored marked.
const page = Object.fromEntries([
  "escapeHtml", "escapeRegExp", "aureliaMotionOff", "aureliaReveal",
  "announce", "isTypingTarget", "registerActions", "Review", "upgradeFlashcardDecks", "marked",
].map((name) => [name, "readonly"]));

export default [
  // Lint only the files named below, wherever eslint is pointed. A bare
  // `eslint` otherwise walks every .js file in the repository, the Obsidian
  // plugins under vault/ and the built copies under dist/ included.
  {
    ignores: [
      "**/*.js", "!assets/js/garden/**/*.js",
      "**/*.mjs", "**/*.cjs", "!tests/js/**/*.mjs", "!eslint.config.mjs",
    ],
  },
  {
    files: ["assets/js/garden/**/*.js"],
    ...js.configs.recommended,
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "module",
      globals: { ...browser, ...page },
    },
    rules: {
      ...js.configs.recommended.rules,
      // `catch (e) { }` around localStorage and focus calls is deliberate.
      "no-unused-vars": ["error", { caughtErrors: "none" }],
    },
  },
  {
    files: ["tests/js/**/*.mjs", "eslint.config.mjs"],
    ...js.configs.recommended,
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "module",
      globals: { globalThis: "readonly", console: "readonly", URL: "readonly", URLSearchParams: "readonly" },
    },
  },
];
