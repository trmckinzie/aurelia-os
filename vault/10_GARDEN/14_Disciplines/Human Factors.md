---
created: 2026-01-23
tags:
  - type/discipline
  - status/evergreen
  - topic/psychology
  - topic/ergonomics
  - topic/systems
  - topic/systems-engineering
  - topic/design
  - topic/human-factors
publish: true
---
# 🧠 Human Factors

### 🧐 Definition (The Scope)
>The scientific discipline concerned with the understanding of interactions among humans and other elements of a system. It applies theory, principles, data, and methods to design in order to optimize human well-being and overall system performance.

**The Philosophy:** "Fit the task to the human, not the human to the task." Unlike clinical psychology (which fixes the person), Human Factors fixes the _environment_. If a pilot crashes a plane because a button was confusing, Human Factors blames the button, not the pilot.

---

### 🔑 Core Concepts (The Bricks)
- **[[The Swiss Cheese Model]] (Reason's Model):** A model of accident causation. It posits that disasters (like Chernobyl or a plane crash) are rarely caused by a single failure. Instead, they occur when "holes" in multiple layers of defense (training, interface design, protocols) momentarily align, allowing a hazard to pass through.
    
- **[[Situation Awareness]] (SA):** Defined by Mica Endsley as "Perception of the elements in the environment, the comprehension of their meaning, and the projection of their status in the near future." It is the mental map of "what is happening right now." Loss of SA is the leading cause of human error in aviation and surgery.
    
- **[[Cognitive Load Theory]]:** The study of the brain's limited working memory capacity during tasks.
    
    - _Intrinsic Load:_ Difficulty of the subject itself.
        
    - _Extraneous Load:_ Difficulty caused by bad design (e.g., a confusing font).
        
    - _Germane Load:_ Effort dedicated to creating permanent schemas.
        
    - _Goal:_ Minimize Extraneous, Manage Intrinsic, Maximize Germane.
        
- **[[The Irony of Automation]]:** The paradox that as we automate more tasks (to reduce human error), the remaining tasks become _harder_ for the human. When the autopilot works 99% of the time, the pilot becomes bored and de-skilled, making them _less_ able to handle the 1% emergency when the computer fails.

### 📚 Foundational Texts
- **[[The Design of Everyday Things]]** by **Don Norman** (The bible of usability—why doors are hard to open).
    
- **[[Human Error]]** by **James Reason** (The definitive text on why smart people do dumb things).
    
- **[[Set Phasers on Stun]]** by **Steven Casey** (Case studies of design failures leading to catastrophe).
    
- **[[Designing for Situation Awareness]]** by **Mica Endsley** (How to build systems that keep humans in the loop).
### 🧪 Unresolved Questions
- The Driverless Dilemma (Vigilance): Humans are terrible at passive monitoring (vigilance decrements). How do we design semi-autonomous cars (Level 3) that require a human to "take over" instantly if the AI fails, when the human has likely zoned out?
    
- Human-AI Teaming: How do we design trust? If the AI is too confident, the human over-trusts it (Automation Bias). If the AI is too cautious, the human ignores it (Cry Wolf Effect).