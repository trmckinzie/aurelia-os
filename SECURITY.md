# Security Policy

This repository holds the static-site generator behind Travis R. McKinzie's personal site and
digital garden (single-author), a personal project with no dedicated security team and no bug
bounty program. That said, reports about the generator itself are welcome and taken seriously.

## Scope

In scope: `engine/`, `system/`, `assets/`, `build.py`, `deploy.py`, and the build/deploy pipeline
generally — e.g. XSS via unescaped vault content, injection in the build scripts, or issues with
the generated site's client-side JS.

Out of scope: the contents of `vault/` (personal notes and writing, not code) and third-party
dependencies (Jinja2, PyYAML, nh3, Tailwind, marked.js, Motion) — please report those upstream
instead. Note that a sanitizer bypass in `nh3` itself is an upstream report, but a gap in *how*
`engine/sanitize.py` configures it — an allowlist that lets through something it shouldn't — is in
scope here.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security reports. Instead, use
[GitHub's private security advisory form](https://github.com/trmckinzie/aurelia-os/security/advisories/new)
for this repository, or email trmckinzie24@gmail.com with a description of the issue and steps to
reproduce.

This is a best-effort personal project, not a commercial one — there's no guaranteed response time,
but reports will be reviewed and fixed as soon as reasonably possible.
