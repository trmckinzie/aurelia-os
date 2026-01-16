---
created: 2026-01-16
tags:
  - type/discipline
  - status/evergreen
  - topic/computer-science
  - topic/engineering
  - topic/software-engineering
  - topic/systems
  - topic/project-management
publish: true
---
# 🧠 Software Engineering

### 🧐 Definition (The Scope)
>The application of engineering principles to the design, development, maintenance, testing, and evaluation of software. It is distinct from computer science (which is the study of theory/computation) in that it is focused on practical application and reliability.

**The Hierarchy of Craft:**

- **Coding:** The act of translating logic into syntax. It is the lowest level of the stack (e.g., "I know how to write a `for` loop in Python").
    
- **Programming:** The act of solving a specific logical problem using code. It focuses on algorithms and data structures (e.g., "I wrote a script to scrape this website").
    
- **Software Engineering:** The management of programming _over time_ and _at scale_. As Google's Titus Winters defines it: _"Software Engineering is programming integrated over time."_ It involves managing complexity, team collaboration, legacy code, and trade-offs between speed and stability.

---

### 🔑 Core Concepts (The Bricks)
- **[[Software Development Life Cycle]] (SDLC):** The framework defining tasks performed at each step in the software development process. It ensures software is built systematically rather than haphazardly.
    
    - **Phases:** Requirement Analysis $\rightarrow$ Design $\rightarrow$ Implementation $\rightarrow$ Testing $\rightarrow$ Deployment $\rightarrow$ Maintenance.
        
    - **Models:** Ranges from the rigid **Waterfall Model** (step-by-step) to the iterative **Agile/Scrum** (flexible, feedback-driven).
        
- **[[Abstraction]] & [[Modularity]]:** The primary tool for managing complexity. Engineers break huge systems into smaller, independent modules (Microservices, Classes, Functions) that communicate via well-defined interfaces (APIs). This allows an engineer to change one part of the system without understanding the whole.
    
- **[[Technical Debt]]:** A metaphor coined by Ward Cunningham. It reflects the implied cost of additional rework caused by choosing an easy (limited) solution now instead of using a better approach that would take longer. Like financial debt, it accrues "interest" (making future changes harder) and must eventually be "paid down" (refactoring).
    
- **[[Testing & QA]]:** The discipline of verification.
    
    - _Unit Testing:_ Does this specific function work?
        
    - _Integration Testing:_ Do these two modules talk to each other correctly?
        
    - _System Testing:_ Does the whole product meet requirements?

### 📚 Foundational Texts
- **[[The Mythical Man-Month]]** by **Fred Brooks** (The classic text on why adding manpower to a late project makes it later).
    
- **[[Design Patterns]]** by **The Gang of Four** (Standard solutions to common problems in object-oriented design).
    
- **[[Code Complete]]** by **Steve McConnell** (The comprehensive guide to construction).
    
- **[[Software Engineering at Google]]** by **Winters et al.** (Modern definition of SE as time-dependent programming).
### 🧪 Unresolved Questions
- The "10x Engineer" Myth: Is individual productivity in software linear or exponential? And if it is exponential, how do we manage teams with such vast skill disparities?
- AI-Assisted Engineering: Will LLMs (like Copilot) reduce the need for junior engineers (Coding/Programming), creating a crisis of mentorship for future senior engineers (Architecture/System Design)?