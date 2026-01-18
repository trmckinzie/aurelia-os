---
type: project
publish: true
status: active
date: 2026-01-03
tags: []
cover_image: ""
role: Lead Architect
tech_stack:
  - Python
  - HTML5
  - Tailwind
  - Obsidian
link_repo: ""
link_live: https://trmckinize24-gif.github.io/aurelia-os/
link_demo: ""
stats:
  - "Latency: <50ms"
  - "Cost: $0.00"
---
# 🚨 Mission Brief (The Problem)

**System Failure:** Needed a personal website to start developing a public brand as an academic researcher and business professional with a versatile skillset and digital literacy. Also wanted to design an efficient workflow that allowed my local obsidian notes to become automatically published to a personal site that acts as headquarters for my academic and professional portfolio. 

**Resource Gap:** Traditional sites such as Wix do not allow for the kind of customization I was looking for and Obsidian publish (and equivalent options for publishing notes) was too expensive for my liking. 

**Objective:** Engineer a "Digital Garden" pipeline that automatically compiles raw markdown notes into a high-performance, cybernetic web interface without manual formatting. Create a personal multi-modal website that houses my digital garden but also reflects my competency as a budding academic, productivity expert, and digital architect. This site must be visually stunning but also highly functional. 

# 🛠️ Architecture (The Solution)

**Core Logic:** Designed a custom **Python ETL Script** (`build.py`) acting as the compiler. The site now acts as a custom PKM that balances complex functionality and UX convenience. 

* **Ingestion Module:** Scans the local Obsidian vault for notes tagged `#publish`.
* **Transformation Engine:** Parses Frontmatter metadata (Type, Status, Tags) and converts Markdown syntax to semantic HTML.
* **UI Layer:** Utilizes **Tailwind CSS** for a responsive, "Glassmorphism" aesthetic and **Vanilla JS** for high-speed, client-side filtering (no database queries required).
* **Integration:** The system is "Headless"—the content lives in Obsidian, the code lives in VS Code, and they merge only at build time. Using a plugin on Obsidian I am able to publish updated versions of the site to Github, without opening VS code or Github itself! 

# ⚡ Operational Impact (The Results)
- **Velocity:** Reduced deployment time from hours to seconds (1-click build process).
- **Performance:** Achieved perfect Lighthouse scores (100/100) due to static HTML architecture.
- **Cohesion:** Successfully merged "Portfolio" (Proof of Work) with "Garden" (Proof of Knowledge) into a single, unified Operating System. I am currently building other modules at this time. It will all function together and maintain the same aesthetic, allowing me to display a personal brand while also taking advantage of the functional utility provided by AI automation, digital gardening, and advanced synthesis across ideas and concepts. 