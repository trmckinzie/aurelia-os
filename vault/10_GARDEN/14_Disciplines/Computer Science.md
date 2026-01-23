---
created: 2026-01-23
tags:
  - type/discipline
  - status/evergreen
  - topic/computer-science
  - topic/computation
  - topic/complexity-theory
  - topic/algorithms
  - topic/mathematics
  - topic/information-processing-theory
  - topic/cognitive-science
publish: true
---
# 🧠 Computer Science

### 🧐 Definition (The Scope)
>The study of **Computation**, **Information**, and **Automation**. It is effectively a branch of mathematics that deals with the theoretical foundations of information processing. Unlike Software Engineering (which asks "How do I build this app?"), Computer Science asks "Is this problem solvable?" and "How efficiently can it be solved?"

**The Theoretical Engine:** At its heart, it relies on the **Turing Machine**—an abstract mathematical model of a machine that manipulates symbols on a strip of tape according to a table of rules. If a problem can be solved by an algorithm, a Turing Machine can solve it.

---

### 🔑 Core Concepts (The Bricks)
- **[[Algorithms & Data Structures]]:** The fundamental tools. An **Algorithm** is a step-by-step procedure for calculations (the recipe). A **Data Structure** is a data organization, management, and storage format (the container).
    
- **[[Computational Complexity]] (Big O):** The study of the resources (Time and Space) required to solve a problem. It classifies problems based on how their difficulty scales with input size ($n$).
    
    - $O(1)$: Constant time (Instant).
        
    - $O(n)$: Linear time (Reading a book).
        
    - $O(2^n)$: Exponential time (Cracking a password by brute force).
        
- **[[Computability Theory]]:** The study of what is mathematically possible to solve. It defines the limits of computation, most famously proven by the **Halting Problem** (there are some problems that no computer can ever solve).
    
- **[[P vs NP]]:** The most famous unsolved problem in the field.
    
    - **P (Polynomial):** Problems that are fast to _solve_ (e.g., multiplication).
        
    - **NP (Nondeterministic Polynomial):** Problems that are fast to _verify_ but slow to _solve_ (e.g., Sudoku, Factoring large primes).
        
    - The question: If you can quickly verify a solution, can you also quickly find it? ($P \stackrel{?}{=} NP$).
### 📚 Foundational Texts
- **[[On Computable Numbers]]** by **Alan Turing** (The 1936 paper that invented the computer before computers existed).
    
- **[[The Art of Computer Programming]]** by **Donald Knuth** (The multi-volume bible of algorithms).
    
- **[[Introduction to the Theory of Computation]]** by **Michael Sipser** (The standard text on automata and complexity).
    
- **[[Gödel, Escher, Bach]]** by **Douglas Hofstadter** (A philosophical exploration of recursion and meaning in formal systems).

### 🧪 Unresolved Questions
* P vs NP: If P = NP, it would break all modern cryptography (which relies on factoring primes being hard) and revolutionize optimization. Most assume P $\neq$ NP, but we can't prove it._
    
- Quantum Supremacy: Can Quantum Computers (using Qubits and superposition) actually solve problems that are intractable for classical Turing Machines, or are they just faster at specific niche tasks?