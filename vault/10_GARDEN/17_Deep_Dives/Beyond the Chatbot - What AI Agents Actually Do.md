---
created: 2026-08-25
tags:
  - type/deep-dive
  - maturity/growing
  - status/active
type: deep-dive
maturity: growing
status: active
publish: true
---

**🔗 Related:** 

---
# Beyond the Chatbot - What AI Agents Actually Do

Picture two people trying to plan the same work trip.

The first opens a chatbot and types: "What's the best time to fly from Chicago to Lisbon in October?" It answers in a paragraph — shoulder season, decent weather, prices trend lower after the 15th. Helpful. Then it stops. It's waiting for the next question, the way a very well-read friend waits for you to ask something else.

The second person opens something different — an AI agent — and says: "Book me a flight to Lisbon for that conference next month, keep it under nine hundred dollars, and put it on my calendar." And then it goes to work. It checks the calendar for conflicts. It searches flights. It compares three options against the budget. It picks one, books it, creates the calendar event, and sends a confirmation email — then reports back: done, here's what I chose, and here's why.

Same underlying technology, roughly. Two completely different jobs. One answered a question. The other got something done. That gap — between answering and doing — is the entire story of AI agents, and it's worth understanding on its own terms, not as a rebrand of the chatbot you already know.

## What Actually Makes Something an "Agent"

The word "agent" gets used loosely, so it's worth being precise. A plain model call — a chatbot — takes an input and produces an output. One shot. Ask, answer, done. It has no ability to act in the world and no memory of what it was doing five steps ago, because there is no five steps ago.

An agent is different in three specific ways. First, it's goal-directed: you give it an outcome, not a single question — "book the flight," not "what are the options." Second, it takes actions, not just words: it can search the web, run code, call an API, edit a file, click buttons in a browser. Third, and this is the part that really separates it from a chatbot, it operates over multiple steps, deciding what to do next based on what happened after its last action.

That last point is the crux of it. A chatbot's job ends the moment it produces text. An agent's text is often just a decision about what to do next — and then it has to go check whether that decision worked. It's the difference between giving directions and actually driving the car, watching the road, and adjusting when there's construction ahead.

## The Loop That Runs Underneath

Nearly every AI agent, regardless of what it's built to do, runs on some version of the same basic loop: observe, plan, act, observe again.

It starts by looking at the current state of things — the task it was given, maybe a file, a webpage, an error message. Then it plans: given what I know right now, what's the single next action that moves me toward the goal? Then it acts — it actually does that thing, using a tool. That could be running a piece of code, doing a web search, clicking a link, sending an email. And then, critically, it observes the result. Did the code run, or throw an error? Did the search return anything useful? Did the page load the way it expected?

That observation feeds right back into the next planning step. If the code failed, the agent reads the error and tries something different. If the search came back empty, it rephrases the query. This loop — plan, act, observe, replan — can run for a few seconds or for many minutes, sometimes hundreds of cycles, chaining small decisions into something that looks, from the outside, like independent judgment.

There's one more piece worth knowing about: memory. As that loop runs, the agent needs to track what it's already tried, what it's learned, and what still needs doing — otherwise it repeats itself or contradicts its own earlier decisions. How agents keep track of that state across a long task is still one of the genuinely unsettled problems in the field. There's no single agreed-upon solution yet — just an active area everyone's iterating on. Worth knowing, because it's often where things go wrong.

## Where This Shows Up Right Now

This isn't a hypothetical framework — it's already running in a handful of concrete forms.

The clearest example is coding agents. Tools like Claude Code read through an entire codebase, plan a change that might touch several files, write the code, run it, read the error output if something breaks, and iterate until it works — the full loop, applied to software engineering. Cognition Labs' Devin, announced in March 2024, was one of the first tools marketed explicitly as an autonomous "AI software engineer" rather than a line-by-line autocomplete — though it's worth noting that its early demos drew real scrutiny from independent reviewers who found some of the showcased runs involved more manual correction than the marketing suggested. A useful reminder that in this space, "autonomous" claims deserve a second look. GitHub has pushed further in the same direction with its Copilot coding agent, which can take an assigned issue, work out a plan, and open a pull request on its own.

A second category is research agents. OpenAI's Deep Research, launched in early 2025, takes a broad question, breaks it into sub-questions, searches and reads dozens of sources, and comes back with a cited report — work that would otherwise take a person hours of tab-switching.

A third is browser and computer-use agents — tools that can see a screen and operate it the way a person would, clicking, typing, and navigating web applications that were never built with an API in mind. Anthropic introduced this capability in late 2024, and OpenAI followed with its own browser agent, since folded into a broader unified agent product.

And then there's business-process automation — agents deployed for customer support and sales workflows, like Salesforce's Agentforce. This category is also where the clearest cautionary tale lives, which brings us to the risks.

## Where It Breaks Down

The same thing that makes agents powerful — chaining many autonomous decisions together — is also where they get fragile. A chatbot that's ninety-five percent accurate on a single answer is pretty reliable. An agent making twenty sequential decisions, each ninety-five percent reliable, has its errors compound: a wrong assumption early on quietly poisons everything downstream, and by the time it surfaces, it's not one recent mistake — it's a long chain built on a bad foundation.

Klarna offers the clearest real-world lesson here. In early 2024, the company announced its AI assistant was handling the workload of roughly seven hundred support agents and resolving two-thirds of chats without a human. It made headlines as a triumph of autonomous customer service. But by 2025, Klarna's own CEO publicly acknowledged the company had leaned too hard into automation, that service quality had suffered, and that Klarna was rehiring human staff. The lesson isn't that agents don't work — it's that unmonitored autonomy at scale needs guardrails, and that early success metrics don't always hold up once the humans are actually gone.

There's also a straightforward cost problem — each step in that loop is another model call, another few seconds, another few cents, and that adds up fast on long tasks. And there's security: agents that browse the web or read untrusted documents can be manipulated by hidden instructions planted in that content, a problem — prompt injection — that the security community still considers largely unsolved. None of this is a reason to avoid agents. It's a reason to keep a human reviewing the important decisions, and to scope what an agent is allowed to do before it starts.

## Where This Is Headed

Research from METR in 2025 found that the length of task an AI agent can complete reliably has been roughly doubling every seven months or so — a snapshot, not a fixed law, but a genuine trend. What that means in practice is less dramatic than it sounds: not robots replacing jobs overnight, but the boundary of "things worth delegating instead of doing yourself" creeping steadily outward. A year ago that might have meant delegating a web search. Today it might mean delegating a whole bug fix. The skill that's going to matter most isn't writing the perfect prompt — it's learning to scope a task well enough that an agent can run with it, and knowing exactly where to draw the line and check its work before you trust the result.
