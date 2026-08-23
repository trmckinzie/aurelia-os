# Claude Code, Demystified: How an AI Agent Actually Gets Work Done

*A ~10-minute read on what Claude Code is and how it works under the hood*

---

## Part 1: The Plain-English Preview

Before the technical detail, here's the handful of ideas that trip people up when they first hear about AI "agents" — each with an analogy that should make the mechanism click immediately.

**The agentic loop is a contractor walking your house before quoting the job.** A contractor doesn't guess at a renovation from the street — they walk through, open cabinets, check the wiring, take notes, form a plan, do a piece of the work, step back and look at it, then decide what's next. Claude Code works the same way: look around, plan, take one action, check the result, repeat. It's not one big leap from question to finished answer — it's a loop of small, checked steps.

**Tool use is Claude picking up the right instrument from a toolbox it can see the labels on.** Claude doesn't have hands. It can't directly open a file or run a command. Instead, it's handed a toolbox where every tool has a label describing what it does and what inputs it needs (read this file, run this command, search for this text). When Claude decides "I need to read that file," it doesn't do it itself — it fills out a request for the "read file" tool, someone else (the host program) actually does the reading, and hands the result back. Choosing the right tool isn't a separate decision step — it's baked into the same process by which Claude decides what word to say next.

**The context window is a whiteboard that eventually needs erasing.** Everything in a conversation — your instructions, the files read so far, the commands run and their output — gets written on a whiteboard Claude can see. The whiteboard is big, but it's not infinite. When it starts running out of room, rather than just erasing the oldest stuff and losing it, Claude Code condenses those older notes into a summary — like erasing paragraphs of detail and replacing them with a tighter recap — so the important decisions and facts survive even though the play-by-play doesn't. The task keeps going; some fine detail from early on doesn't.

**Permissions work like a supervisor who signs off on some things and not others.** A trusted contractor doesn't need your sign-off to sweep the floor or measure a room, but you'd want to be asked before they knock down a wall. Claude Code sorts its own actions the same way: reading a file or searching your codebase happens automatically; deleting files, running shell commands with side effects, or pushing code somewhere shared pauses and asks you first. And your "yes" to one risky action doesn't mean blanket approval forever — it's scoped to that specific ask.

**Subagents are like calling in a specialist who reports back a summary, not their whole notebook.** If a task has a self-contained chunk of work — say, "search the whole codebase for every place this function is used" — Claude Code can hand that off to a subagent: a separate instance with its own clean workspace and its own tools, which does the digging and comes back with a distilled answer. The main conversation's whiteboard doesn't get cluttered with all the specialist's scratch work — just the useful conclusion.

**MCP is a universal power outlet for plugging in new tools.** Historically, every new tool an AI system could use had to be wired up with custom, one-off code. The Model Context Protocol (MCP) is a standard plug shape: any tool built to that standard can be plugged into any AI application that supports the standard, the same way any lamp with a standard plug works in any outlet in the house, regardless of who manufactured either one. That's how, in some Claude Code sessions, you'll see it able to use things like email or calendar tools — those were plugged in via MCP, not custom-built into Claude Code itself.

With those six mental models in place, here's how it actually works.

---

## Part 2: The Deep Dive

### What Claude Code Is

Claude Code is Anthropic's agentic coding assistant, available as a command-line tool, an IDE extension, a desktop app, and a web app. The distinction that matters most is architectural, not cosmetic: chat-based Claude (as on claude.ai) is a text-in, text-out conversation — you ask, it answers, nothing changes in the world unless you copy-paste the result yourself. Claude Code is built around direct access to a real environment: it can read and edit files on your actual filesystem, execute shell commands, run your test suite, and interact with git — and it does so by *running a loop*, not by generating a single response. It launched as a research preview in early 2025 and reached general availability later that year.

### The Core Agent Loop

The mechanism underneath Claude Code is often described by Anthropic as *explore → plan → code → commit*, but underneath that product-level framing is a simpler, more general pattern: a **ReAct-style loop** (reason, then act), which is the same loop structure underlying tool use in Claude's API generally — Claude Code is one particular, heavily tuned application of it.

At each turn, Claude receives the full running conversation — the original request, everything read or executed so far, and every result — and does one of two things: emit a tool call, or emit a final plain-text response. If it's a tool call, the host application (Claude Code itself) executes that action in the real world, appends the result to the conversation, and hands control back to the model for the next turn. This repeats — read a file, form a hypothesis, run a search, adjust the plan, make an edit, run the tests, check the output — until the model judges the task done and returns ordinary text instead of another tool call. For long or multi-step tasks, Claude Code also exposes an explicit task-list tool (`TodoWrite`) so the model can write its plan down as a checklist rather than holding every step only in its own reasoning — useful both for tracking long tasks and for letting you see progress as it happens.

### Tool Use: How the Model Decides What to Call

A "tool," in this context, is defined to the model as a name, a natural-language description of what it does, and a schema describing what input it expects — much like a function signature with documentation attached. Claude doesn't have a separate classifier that decides "now I use the file-reader"; tool selection happens as part of the same next-token generation process that produces any other response. The model reads the available tool descriptions, reads the current state of the conversation, and generates a structured tool-call block (name plus arguments) when it judges a tool is the right next move. This has a practical consequence: how well a tool is described directly shapes whether and how correctly the model reaches for it.

Claude Code's built-in toolset generally spans file operations (read, write, targeted edits), shell execution, codebase search (content and filename search), and web fetch/search, plus a task-dispatch tool used to hand work to subagents. When there's no dependency between two actions — say, reading two unrelated files — Claude Code can batch independent tool calls together in a single turn rather than doing them one at a time, which is purely an efficiency gain and doesn't change the loop's logic.

### Context Management: Limits and Compaction

Claude models operate over a context window measured in tokens — a hard ceiling on how much conversation, file content, and tool output can be "in view" at once. That ceiling is large by conversational standards but still finite, and a long coding session — reading many files, running many commands — can approach it.

Rather than simply truncating and losing the oldest material once the limit nears, Claude Code performs **automatic compaction**: earlier turns are summarized into a condensed form that tries to preserve the key facts, decisions, and current state, freeing up room for the session to keep going. This is a deliberate design choice: the task can continue uninterrupted, but compaction is *summarization*, not archival — meaning fine-grained detail from early in a long session can be lost even while the overall thread of the work survives. Users can also trigger this manually rather than waiting for it to happen automatically, when they know a natural checkpoint has been reached.

### Permissions and Risk-Tiered Confirmation

Claude Code's permission system doesn't treat every action alike. Read-only, reversible, low-risk actions — reading a file, searching the repo, listing directory contents — are typically auto-allowed, since there's little to lose if the model reads the wrong file. Actions that are destructive, hard to reverse, or that touch shared/external state — deleting files, force-pushing to a git remote, running arbitrary shell commands, sending a message someone else will see — pause the loop and require the user's explicit confirmation before proceeding.

This isn't a one-time unlock: approving a risky action once doesn't grant blanket future approval for similar actions. Authorization is scoped to what was actually asked and confirmed, not extended indefinitely — which is precisely how a careful human supervisor would treat sign-off in the physical-world analogy above. These rules are configurable — projects can maintain allow/deny lists for specific tools or commands in a settings file — and can be extended further through hooks (below), which let a team enforce policy that goes beyond the model's own judgment.

### Extensibility: Subagents, Hooks, Slash Commands, and MCP

Four mechanisms let Claude Code be extended or customized beyond its defaults:

- **Subagents** let Claude Code delegate a self-contained piece of work to a separate agent instance with its own isolated context window and its own defined subset of tools. This is useful for parallelizing work or for scoping a big, noisy search (like "find every usage of this pattern across the codebase") without filling up the main conversation's context with all the intermediate digging — only the distilled result comes back. Subagents are typically configured as markdown files with YAML frontmatter specifying their name, description, allowed tools, and model.

- **Hooks** are shell commands that fire automatically at defined points in the loop's lifecycle — before or after a tool call, or when the user submits a new prompt, for instance. They let a team bolt on custom policy, logging, or hard blocks that don't depend on the model choosing to comply — feedback from a hook is treated as coming from the user, not as a suggestion the model can weigh against its own judgment.

- **Slash commands** are user-defined shortcuts — markdown files invoked as `/command-name` — that inject a pre-written prompt or instruction set into the conversation on demand, useful for repeatable workflows a team wants to standardize (a code-review checklist, a release-prep routine, and so on).

- **MCP (Model Context Protocol)** is an open, standardized protocol Anthropic introduced for connecting AI applications to external tools and data sources. Before MCP, hooking a new external system (an email client, a database, an internal API) into an AI assistant meant bespoke integration code for every pairing. MCP defines a common client-server interface instead: any tool built as an MCP server can be plugged into any MCP-compliant host application, the way any standard plug fits any standard outlet, regardless of who made either end. This is how Claude Code gains access to entirely new categories of capability — like external calendars, communication tools, or internal company systems — without those capabilities being hard-coded into the product itself.

### Memory and Persistence Across Sessions

Claude Code's native, built-in persistence mechanism is **CLAUDE.md**: a project-level (and optionally user-level) markdown file that's automatically loaded into context at the start of a session, typically used for team-shared conventions, coding standards, and repo-specific instructions the model should always know about. Beyond that, Claude Code supports resuming a prior session's conversation history — but that's continuity of the transcript, not a separate semantic "memory" layer that independently profiles a user or project over time.

It's worth being precise here: a persistent memory system that actively builds up a profile of a user's preferences, ongoing projects, and past feedback across unrelated sessions is not, as of this writing, a documented core Claude Code product feature. Where it exists, it's typically a custom pattern built *on top of* Claude Code's existing primitives — usually CLAUDE.md instructions directing the model to read and write its own memory files using the same file tools it uses for everything else. It's a demonstration of what the extensibility model makes possible, not a separate built-in system.

---

## Part 3: The Plain-English Summary

If you remember one thing from each part of this report, make it these:

The **agent loop** is Claude working the way a careful contractor would — look, plan, act, check, repeat — rather than answering everything in one guess. **Tool use** means Claude never touches your computer directly; it fills out a request for the right labeled tool, and the surrounding program is what actually does the work and hands the result back. The **context window** is a whiteboard with finite space — when it fills up, older detail gets condensed into a summary rather than lost outright, so the work can keep going even if some fine texture from earlier doesn't survive. **Permissions** work like a supervisor who lets routine, reversible actions happen on their own but wants to sign off on anything destructive or hard to undo — and that sign-off doesn't carry over automatically to the next risky thing. **Subagents** are specialists you call in for a self-contained chunk of work who report back a clean answer instead of their whole notebook of scratch work. And **MCP** is the universal outlet that lets new tools — calendars, email, internal systems, anything else — get plugged into Claude Code without custom wiring for each one.

Put together, none of this is mysterious once you see the shape of it: a loop, a toolbox, a whiteboard with a summarizing habit, a supervisor's sign-off, the option to call in help, and a universal plug for new capabilities. That's the whole architecture — everything else is detail on top of those six ideas.