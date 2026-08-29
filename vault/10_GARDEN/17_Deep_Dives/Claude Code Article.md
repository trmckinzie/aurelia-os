# Claude Code: An Agent That Works in Your Repo, Not in a Chat Window

Most AI coding tools are, structurally, a conversation. You describe a problem, you get back a block of code, and then you do the actual work: figuring out which files it belongs in, adapting it to conventions the model never saw, running the tests, and coming back to report what broke. The model produces text. You provide the hands, the repository, and the feedback loop.

Claude Code, Anthropic's agentic command-line tool for software engineering, inverts that arrangement. It runs in your terminal, inside your project directory, with access to the actual files on disk and the ability to execute shell commands. When you ask it to fix a failing test, it reads the relevant source, makes the edit, runs the test suite, reads the output, and — if the test still fails — tries again. The loop that you were closing by hand is the thing the tool is built around.

That difference matters most on the tasks that are tedious rather than intellectually hard: a rename that touches forty files, a dependency upgrade with a dozen small breaking changes, a bug whose reproduction is obvious but whose cause is buried three call sites deep. These are jobs where the bottleneck was never "what should the code say" but "carrying the change through the whole repo and confirming nothing else broke."

## How it works

The core loop is unglamorous and worth understanding precisely, because it explains both the tool's strengths and its failure modes.

Claude Code operates by calling tools. It reads files, searches the codebase, writes edits, and runs shell commands — builds, test runners, linters, package managers, `git`. Each result comes back into its context, and the model decides what to do next based on what actually happened rather than on what it predicted would happen. A test that fails produces real stack traces. A build that breaks produces real compiler errors. The agent reads those and revises.

This is bounded by a permission model you control. Before Claude Code takes an action that changes your system — writing a file, running a command — it asks, and you approve or deny. You can grant standing permission for categories of action (say, allow all reads and test runs, but require approval for anything that touches `git push`), or you can loosen the model further for a session where you want it to work uninterrupted. Denying a request isn't a dead end; the agent treats the refusal as information and proposes something else.

So "autonomous" is the wrong word, and it's worth being blunt about that. Claude Code is autonomous *within a boundary you set*, and the boundary is the whole safety story. Set it loose with broad permissions in a repo with no test coverage and you have an enthusiastic contributor with no feedback signal. Set it up in a repo with a fast test suite and a linter, and the verification step does real work.

## What it can actually do

**Multi-file changes.** Because it can search the repository and edit many files in one pass, refactors that span module boundaries are ordinary work rather than a special occasion. It reads before it writes, which means it adapts to the conventions already in the file instead of importing a generic style.

**Running and interpreting output.** This is the capability that most distinguishes an agent from a code generator. Claude Code doesn't just produce a patch; it runs the suite and reads the failures. When a test fails for a reason unrelated to the change — a flaky integration test, a missing environment variable — it can usually tell the difference and say so rather than thrashing.

**Git and version control.** Since shell commands are just tool calls, git operations need no special support: branching, staging, commit messages written from the actual diff, resolving a conflict by reading both sides. It can drive `gh` for pull request workflows if the CLI is installed and authenticated.

**Project memory.** Claude Code reads `CLAUDE.md` files from your project and from your user configuration, loading them into context automatically at the start of a session. This is where teams put architecture notes, build commands, house style, and the standing instructions they'd otherwise repeat every day — "this codebase uses X, never Y," "always run the linter before committing." It's the difference between onboarding the agent once and onboarding it every session.

**Subagents and hooks.** Work can be delegated to subagents with their own separate context, which keeps a long investigation from crowding out the main session's working memory. Hooks let you run your own scripts at defined points in the agent's lifecycle — before or after a tool call, at session start — so you can enforce checks, log activity, or wire in external tooling deterministically rather than by asking the model nicely.

**Surfaces beyond the terminal.** The CLI is the primary interface, but Claude Code is also available through IDE extensions for VS Code and JetBrains editors, as a desktop application, and on the web. The Claude Agent SDK — previously called the Claude Code SDK — exposes the same agent loop programmatically, so you can build your own agents on the underlying framework instead of only driving the CLI.

## Where it fits alongside other tools

The honest framing here is about design center, not superiority. GitHub Copilot began as inline completion built into the editor and has since added chat and agent capabilities. Cursor is an AI-native editor — a VS Code fork — where the assistant is woven into the editing surface itself. Both are good at what they were designed around, and both have shipped agentic features; anyone claiming Claude Code is the only tool that executes code is out of date.

What Claude Code optimizes for is the terminal-first, execution-heavy end of the spectrum: long-running tasks where the agent needs to run things, read output, and iterate without a human mediating each step, in whatever editor and toolchain you already use. If your pain is "I type the same boilerplate constantly," an autocomplete-first tool is a better fit and you'll feel the value immediately. If your pain is "this migration will take me two days of mechanical work," the agentic loop is what you want. Plenty of developers run both.

## A realistic session

Say a field is silently dropped when a record is written — it's set on the object, but absent when read back. You know the symptom; you don't know where it's lost.

You start Claude Code in the repo and describe the bug. It searches for the write path, reads the serialization layer and the schema definition, and comes back with a hypothesis: the field was added to the type but never to the column list in the insert statement. It asks to edit two files. You approve.

Then it runs the test suite. Two tests fail — one is the bug you reported, now passing, and one is a snapshot test that legitimately needs updating because the persisted shape changed. It tells you which is which and asks whether to update the snapshot. That question is the important part: it correctly declined to treat a snapshot mismatch as noise.

You approve, it re-runs, everything's green. It offers to write a commit. You ask it to also add a regression test that reads the record back after writing — it does, runs the suite again, and stages the change.

Not every session is that clean. Sometimes the first hypothesis is wrong and it spends a few minutes going down a dead end; sometimes it needs you to answer a question it can't resolve from the code. The loop tolerates both, but it doesn't eliminate your judgment about whether the fix is the right one.

## Getting started, and when not to bother

Claude Code installs from npm as `@anthropic-ai/claude-code` and runs on macOS, Linux, and Windows. Once installed, you launch it from inside a project directory and start by describing what you want. Running `/init` generates a starting `CLAUDE.md` from your codebase, which is the highest-leverage five minutes of setup available.

Access is available through paid Claude subscription plans as well as through usage-based API billing on an Anthropic account. Rates, plan tiers, and included usage change, so check anthropic.com/pricing rather than trusting a number in an article. The practical point is that agentic sessions consume more tokens than chat does, because the model is reading files and command output continuously — budget accordingly, and scope tasks rather than pointing it at an entire codebase and hoping.

It's overkill for small, well-understood edits you could make faster yourself, and it's genuinely weak in repositories with no tests and no build step, where its verification loop has nothing to verify against. It's at its best on work that is well-specified but laborious, in codebases where something — tests, types, a linter — can tell it when it's wrong.

Start with something bounded and slightly annoying: a bug with a clear reproduction, a dependency bump, a refactor you've been putting off. Watch what it does with the tests. That will tell you more about the fit than any feature list.