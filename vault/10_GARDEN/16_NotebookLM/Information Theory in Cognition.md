---
type: notebooklm
publish: true
status: active
tags:
  - topic/research
  - source/notebooklm
  - topic/information-processing-theory
  - topic/cognitive-science
created: 2026-01-16
cover_image: ""
---
---

# 📚 Lit Review Overview
> **Report: Information Theoretic Principles in Cognitive Systems**

**Part 1: Mathematical Concepts**

This section outlines the foundational mathematical frameworks and quantification methods derived from information theory and thermodynamics that serve as the basis for understanding complex systems.

**1. Information Entropy and Surprisal**

• **Definition:** In the framework established by Claude Shannon, information is defined not by semantic meaning, but by the reduction of uncertainty. The fundamental unit is the **bit** (binary digit), which represents the resolution of uncertainty between two equally likely alternatives.

• **Entropy (**H**):** Entropy quantifies the average uncertainty or "disorder" of a random variable. It is the average amount of information produced by a stochastic source. Mathematically, for a discrete random variable X, entropy is defined as H(X)=−∑P(xi​)log2​P(xi​).

• **Surprisal:** Also known as self-information, this is the negative log-probability of a specific outcome (I(x)=−logP(x)). Highly probable events have low surprisal (low information content), while rare events carry high surprisal.

• **Psychological Entropy:** In cognitive contexts, entropy is viewed as a measure of the unavailability of a system’s energy to do work, or more broadly, a measure of disorder that biological systems must minimize to maintain homeostasis.

**2. Channel Capacity and Bandwidth**

• **Definition:** Derived from the noisy-channel coding theorem, channel capacity is the upper bound on the rate at which information can be reliably transmitted over a communication channel with an arbitrarily small error probability.

• **Throughput Constraints:** Any information processing system—biological or artificial—has a finite bandwidth. If the input rate exceeds this capacity, transmission errors occur, or information is lost.

**3. Signal-to-Noise Ratio (SNR)**

• **Definition:** SNR is the dimensionless ratio of signal power to noise power. It quantifies the fidelity of signal transmission.

• **Measurement:** In neural contexts, SNR determines the discriminability of a stimulus. It is mathematically related to mutual information; Shannon derived that the information capacity (I) of a continuous channel with Gaussian noise is I=∫log2​(1+SNR(f))df.

• **Detection Theory:** SNR is directly linked to d′ (discriminability) in psychophysics. A higher SNR implies a greater separation between the signal distribution and the noise distribution, reducing false positives and misses.

**4. The Free Energy Principle (Variational Free Energy)**

• **Core Principle:** This is a mathematical formulation of how adaptive systems resist the natural tendency toward disorder (entropy). It asserts that physical systems minimize a quantity known as **variational free energy**.

• **Mathematical Formulation:** Variational free energy is an information-theoretic upper bound on surprise (surprisal). It is defined as the difference between the internal model's predictions (recognition density) and the true posterior density of external causes.

• **Components:** Free energy can be decomposed into **complexity** (the divergence between posterior beliefs and prior beliefs) minus **accuracy** (the surprise of sensations expected under the model). Minimizing free energy is mathematically equivalent to maximizing Bayesian model evidence.

**5. Redundancy**

• **Definition:** Redundancy measures the fractional difference between the entropy of an ensemble and its maximum possible value. It represents the "wasted space" or predictability in a message.

• **Calculation:** For a language like English, redundancy is roughly 50%, meaning half the characters can be removed, and the message remains reconstructable due to sequential constraints (e.g., "q" is almost always followed by "u").

**6. Network Motifs**

• **Definition:** Motifs are statistically significant, recurring sub-graphs or patterns of interconnections (e.g., 3-node loops) within a larger network.

• **Function:** These are considered the basic building blocks or "meta operators" of complex networks. The distribution of specific Motif topologies (e.g., feed-forward vs. recurrent loops) defines the functional capabilities of the network, such as temporal processing vs. spatial processing.

--------------------------------------------------------------------------------

**Part 2: Biological Application**

This section details how the mathematical concepts above are implemented in biological neural networks, cognitive architecture, and behavior.

**1. The "10 Bits/s" Paradox and Behavioral Throughput**

• **The Paradox:** There is a massive discrepancy between the information capacity of the peripheral nervous system and the information throughput of conscious behavior. The sensory periphery (e.g., the retina) gathers data at approximately 109 bits/s (Gigabits), yet human behavioral throughput (e.g., typing, speaking, playing chess) saturates at approximately **10 to 50 bits/s**.

• **The Sifting Number:** The ratio between sensory input and behavioral output is approximately 108. This implies the brain acts as a massive filter, discarding millions of bits to extract the few relevant bits needed for action.

• **Dimensionality Reduction:** The "Outer Brain" (sensory-motor) handles high-dimensional, high-rate signals, while the "Inner Brain" (cognitive/decision-making) operates on a low-dimensional manifold, processing slow variables like rules and values.

**2. Working Memory Capacity and Chunking**

• **Miller’s Magical Number:** George Miller (1956) identified that immediate memory is limited to 7±2 items. However, Miller clarified that this limit applies to **chunks** (meaningful units), not bits. A human can recall 7 binary digits (low information) or 7 words (high information), indicating the brain recodes data to overcome bit-limits.

• **The "Magical Number 4":** Later research, such as that by Cowan, suggests the pure capacity limit (without rehearsal or chunking) is closer to **4 chunks**.

• **Channel Capacity in Absolute Judgment:** Unlike memory, the capacity for "absolute judgment" (distinguishing stimuli like pitch or loudness without a reference) _is_ limited by bits—specifically about 2.5 bits (roughly 6 distinct alternatives).

**3. Cognitive Load Theory and Schema Acquisition**

• **Schema Theory:** To manage the limited working memory (10 bits/s throughput), the brain stores information in long-term memory as **schemas**. Schemas are organized knowledge structures that act as a single "chunk" in working memory, effectively bypassing processing limits.

• **Redundancy Effects:**

    ◦ **Content Redundancy:** Providing the same information in multiple formats (e.g., text and audio) can increase cognitive load if the learner has to process redundant information (the "redundancy effect"). However, recent studies show content redundancy can help learning, while **modal redundancy** (ineffective combination of sensory modalities) harms it.

    ◦ **Split-Attention Effect:** Spatially separating related text and diagrams increases cognitive load because the brain must mentally integrate them. Integrating them physically reduces this load.

**4. Predictive Coding and Active Inference**

• **Minimizing Surprise:** Following the Free Energy Principle, the brain is an inference engine that constantly generates top-down predictions to explain bottom-up sensory data. The goal is to minimize **prediction error** (surprise/free energy).

• **Active Inference:** The organism minimizes surprise in two ways:

    1. **Perception:** Updating internal models to match sensory data.

    2. **Action:** Changing the environment to match internal predictions (e.g., moving a hand to confirm a tactile expectation).

• **The Dark Room Problem:** Critics argue that if organisms wanted to minimize surprise, they would seek a dark, static room. The theory resolves this by positing that agents have **prior beliefs** (models) that include exploration and movement. To a creature expecting to move and explore, a dark room is highly surprising (high entropy relative to the model), compelling the agent to leave.

• **Exploration vs. Exploitation:** Minimizing free energy naturally balances exploration (visiting new states to reduce uncertainty about the environment) and exploitation (visiting states with high expected utility/intrinsic value).

**5. Selective Attention and Signal-to-Noise Optimization**

• **Cocktail Party Effect:** This phenomenon demonstrates the brain's ability to segregate a single auditory stream (signal) from a noisy background. It relies on both bottom-up cues (spatial location, pitch) and top-down cognitive control.

• **Neural Mechanisms:** Attention acts as a filter that enhances the **Signal-to-Noise Ratio (SNR)**. It increases the synaptic efficacy of relevant neurons while suppressing irrelevant ones, effectively "gating" information.

• **Musicianship Advantage:** Musicians show enhanced neural encoding of speech-in-noise, suggesting that training can improve the brain's ability to segregate complex auditory scenes.

**6. Multisensory Integration and Spiking Neural Networks (SNNs)**

• **McGurk Effect:** This effect reveals that the brain integrates conflicting visual and auditory information (e.g., seeing "ga" but hearing "ba" results in perceiving "da"). It proves that perception is a multi-modal construction, not a passive recording.

• **Motif-Topology Application:** Spiking Neural Networks (SNNs) that utilize **Motif-topologies** (specifically 3-node loops derived from biological spatial and temporal networks) are significantly more efficient at simulating these cognitive phenomena (Cocktail Party and McGurk effects) than standard networks. Temporal tasks require denser Motif connections than spatial tasks.

**7. Visual Entropy and Mental Workload**

• **Gaze Entropy:** The spatial distribution of eye fixations (heatmap entropy) serves as a physiological marker of cognitive load.

• **Correlations:** Higher gaze entropy (more dispersed scanning) generally correlates with **higher cognitive load**, longer response times, and lower task performance in complex scenarios. However, specific task demands (e.g., temporal vs. mental demand) can alter this; high mental demand may sometimes lead to grouped (lower entropy) fixations as the user focuses intensely on specific areas.

# 🎙️ Audio Overview
assets/audio/Information_Theory_Deep_Dive.m4a

# 🎥 Video Overview
assets/video/[filename].mp4

# 🧠 Mind Map
assets/images/[filename].png

# 📄 Reports
assets/images/[filename].png

# 🃏 Flashcards
assets/images/[filename].csv

# 📝 Quiz
assets/images/[filename].png

# 📊 Infographic
assets/images/[filename].png

# 📽️ Slide Deck
assets/images/[filename].png

# 📉 Data Table
assets/images/[filename].png

# 📚 Sources
> [Zotero Data Placeholder]