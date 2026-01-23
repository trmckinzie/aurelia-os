---
created: 2026-01-23
tags:
  - type/discipline
  - status/evergreen
  - topic/
  - topic/computer-science
  - topic/cognitive-science
  - topic/machine-learning
  - topic/artificial-intelligence
publish: true
---
# 🧠 Artificial Intelligence

### 🧐 Definition (The Scope)
>The theory and development of computer systems able to perform tasks that normally require human intelligence, such as visual perception, speech recognition, decision-making, and translation.

**The Two Paradigms:**

- **Symbolic AI (GOFAI - "Good Old-Fashioned AI"):** The dominant approach from the 1950s-80s. It attempted to hard-code intelligence using logical rules and symbols (e.g., "If [Has Feathers] and [Quacks] then [Duck]"). It is akin to the **"Rider"** (System 2)—logical but brittle.
    
- **Connectionism (Machine Learning/Deep Learning):** The dominant approach today. It attempts to _learn_ intelligence from data using artificial neural networks, mimicking the brain's architecture. It is akin to the **"Elephant"** (System 1)—intuitive and robust, but opaque.

---

### 🔑 Core Concepts (The Bricks)
- **[[Machine Learning]] (ML):** A subset of AI where computers are not explicitly programmed for a task but are trained with data to learn patterns. Instead of writing code to "detect a cat," you feed the algorithm 10,000 images of cats and let it figure out the pixel patterns itself.
    
- **[[Neural Networks]] (Deep Learning):** A specific type of ML algorithm modeled after the human brain. It consists of layers of "nodes" (neurons) connected by "weights" (synapses). Data passes through the layers, and the weights are adjusted (trained) to minimize error.
    
- **[[Reinforcement Learning]] (RL):** A type of training where an agent learns to make decisions by performing actions in an environment and receiving rewards or punishments. This is pure **Behaviorism** (Skinner) applied to code.
    
- **[[The Alignment Problem]]:** The challenge of ensuring that AI systems pursue goals that match human intent. Because AI optimizes for the _objective function_ (what you told it to do), not the _intended meaning_ (what you wanted it to do), it can lead to "Paperclip Maximizer" scenarios where the AI destroys the world to achieve a trivial goal.

### 📚 Foundational Texts
- **[[Artificial Intelligence: A Modern Approach]]** by **Russell & Norvig** (The standard university textbook).
    
- **[[Perceptrons]]** by **Minsky & Papert** (The 1969 book that famously criticized neural networks and caused the first "AI Winter").
    
- **[[Learning Internal Representations by Error Propagation]]** by **Rumelhart et al.** (The 1986 paper on **Backpropagation** that resurrected neural networks).
    
- **[[Superintelligence]]** by **Nick Bostrom** (The philosophical text on existential risk and alignment).

### 🧪 Unresolved Questions
- The Black Box Problem (Explainability): Deep Learning models are effectively black boxes. We know the input and the output, but we often cannot explain _why_ the model made a specific decision. Can we trust a system we don't understand?
    
- AGI (Artificial General Intelligence): Can we scale current Deep Learning (which is "Narrow AI"—good at one thing) to achieve AGI (human-level competence across all domains), or do we need a fundamentally new paradigm (e.g., Neuro-Symbolic AI)?