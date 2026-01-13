---
created: 2026-01-13
tags:
  - type/discipline
  - status/evergreen
  - topic/evolution
  - topic/systems
  - topic/game-theory
  - topic/economics
  - topic/strategy
  - topic/evolutionary-biology
publish: true
---
# 🧠 Game Theory

### 🧐 Definition (The Scope)
>The study of mathematical models of strategic interaction among rational decision-makers. It analyzes situations (Games) where the outcome for each participant depends not only on their own actions but on the actions of others. Originally developed to model economic competition, it is now the universal language for understanding conflict and cooperation in biology, politics, computer science, and war. Its central assumption is **Rationality**: that agents will always act to maximize their own expected payoff.

>Examples of Game-Theory from [[The Selfish Gene]] by [[Richard Dawkins]]. 
>- Hawk, Dove, Retaliator, Prober-Retaliator, Bully - See Ch 5 on Aggression and stability for more info on these strategies and how they interact

---

### 🔑 Core Concepts (The Bricks)
- **[[Nash Equilibrium]]:** The "stable state" of a game. A set of strategies is in Nash Equilibrium if no player has an incentive to deviate from their chosen strategy after considering an opponent's choice. In other words, "I'm doing the best I can, given what you are doing."
- **[[The Prisoner's Dilemma]]:** The canonical example of why two rational individuals might not cooperate, even if it appears that it is in their best interest to do so. It demonstrates the tension between **Individual Rationality** (defecting protects me) and **Collective Rationality** (cooperating helps us both).
- **[[Zero-Sum vs. Non-Zero-Sum]]:**
    
    - **Zero-Sum:** One player's gain is exactly the other player's loss (e.g., Poker, Chess).
    - **Non-Zero-Sum:** The total pie can grow or shrink based on cooperation (e.g., Trade, Marriage, Nuclear War).

- **[[Schelling Point]] (Focal Point):** A solution that people tend to use in the absence of communication because it seems natural, special, or relevant to them (e.g., meeting at Grand Central Station at noon if you lose your friend in NYC).

### 🏆 Famous Strategies (The Axelrod Tournaments)

> In the 1980s, political scientist **Robert Axelrod** hosted a computer tournament where various algorithms played the **Iterated Prisoner's Dilemma** against each other thousands of times. The results revolutionized our understanding of evolutionary altruism.

- **[[Tit for Tat]]:** The simplest and most successful strategy, submitted by Anatol Rapoport.
    
    1. **Start by Cooperating.**
        
    2. **Then, copy exactly what your opponent did on the previous move.**
        
    
    - _Why it won:_ It is **Nice** (never strikes first), **Provocable** (retaliates immediately if defected against), **Forgiving** (returns to cooperation if the opponent does), and **Clear** (easy to understand).
        
- **[[Grim Trigger]]:** A ruthless strategy. It cooperates until the opponent defects _once_, then it defects forever.
    
    - _Flaw:_ It is too unforgiving; a single noise/error leads to an endless death spiral of mutual defection.
        
- **[[Pavlov]] (Win-Stay, Lose-Shift):** If you received a high payoff on the last round (Reward or Temptation), keep the same move. If you received a low payoff (Sucker or Punishment), switch moves. It exploits "suckers" (who always cooperate) but can correct errors better than Grim Trigger.
    
- **[[Generous Tit for Tat]]:** Similar to Tit for Tat, but occasionally (e.g., 10% of the time) cooperates even after the opponent defects. This breaks the "death spirals" caused by accidental errors in communication.
### 📚 Foundational Texts
- **[[Theory of Games and Economic Behavior]]** by **John von Neumann & Oskar Morgenstern** (The text that invented the field).
- **[[The Evolution of Cooperation]]** by **Robert Axelrod** (The empirical study of the tournaments).
- **[[The Strategy of Conflict]]** by **Thomas Schelling** (Applying game theory to the Cold War and nuclear deterrence).
- **[[A Beautiful Mind]]** (Sylvia Nasar's biography of John Nash, covering the mathematics of equilibrium).
### 🧪 Unresolved Questions
- The Alignment Problem: How do we design game-theoretic incentives for AGI so that its Nash Equilibrium aligns with human survival?
- Bounded Rationality: Standard Game Theory assumes "perfect" calculation. How do we model real-world players who are irrational, emotional, or computationally limited?