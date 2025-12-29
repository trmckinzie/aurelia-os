# 🛠️ Aurelia OS: Template Usage Protocols
**Role:** Data Integrity & Graph View Optimization
**Rule:** "A template filled incorrectly is a broken link in the chain."

---

## 1. T_DailyBridge (The Session Log)
*The Chronological Anchor.*

### 📝 How to Fill
1.  **File Name:** Keep the automatic date format (`YYYY-MM-DD`).
2.  **Goal:** Must be actionable (e.g., "Read ch. 1"). Do not leave this blank; it sets the intention.
3.  **Knowledge Intake:**
    * **Source Link:** Always link to the `[[Book Title]]` here. This tells the Graph View *when* you read that book.
    * **Atomic Extraction:** Do **not** write long essays here. Write bullet points.
    * **Linking:** If you encounter a new idea, wrap it in brackets `[[New Idea]]` immediately to create a "Ghost Link" (a gray node in the graph) that you can click and fill later.

### 🕸️ Graph Effect
* **Role:** The "Time Stamp."
* **Visual:** These nodes connect disparate ideas based on *when* you thought of them, revealing hidden temporal patterns.

---

## 2. T_Source (The Material)
*The Reference Node.*

### 📝 How to Fill
1.  **File Name:** Use the Title. If duplicate, append type (e.g., `Darwin's Dangerous Idea (Book)`).
2.  **YAML Tags:**
    * `type/source/book` (or article/video).
    * `status/reading` (Change to `processed` only when you have extracted all concepts).
3.  **Author Field:** Must use a WikiLink `[[Daniel Dennett]]`. This clusters all books around the author node.
4.  **Concepts Extracted:** This is the most important section. List every `[[Concept]]` you found in this source.

### 🕸️ Graph Effect
* **Role:** The "Hub" for a specific bibliography.
* **Visual:** In the graph, a Source node will look like a Star, with the Author on one side and many Concept rays shooting out the other.

---

## 3. T_Author (The Creator)
*The Person Node.*

### 📝 How to Fill
1.  **Topic Tags:** Be generous here. If Dennett covers Mind AND Biology, tag both `#topic/phil-mind` and `#topic/evolution`. This places him in the intersection of those clusters.
2.  **Key Works:** Only link to books you actually have in your vault (`[[Title]]`).
3.  **Core Concepts:** Link to the ideas they are famous for (`[[Intentional Stance]]`).

### 🕸️ Graph Effect
* **Role:** The "Cluster Center."
* **Visual:** Author nodes usually become medium-sized anchors that pull together Discipline clusters (e.g., pulling Biology towards Philosophy).

---

## 4. T_Concept (The Atom)
*The Building Block. This is 80% of your Vault.*

### 📝 How to Fill
1.  **File Name:** Keep it unique and singular (e.g., `Natural Selection`, not `Natural Selections`).
2.  **Tags:**
    * `type/concept` (Mandatory).
    * `topic/` (Pick the specific domain).
    * `status/` (Update this religiously from seed -> sapling -> evergreen).
3.  **Related Field:** Link to:
    * The **Parent Discipline** (`[[Evolutionary Theory]]`).
    * **Opposing Concepts** (`[[Skyhooks]]` vs `[[Cranes]]`).
    * **Synonyms**.
4.  **Definition:** Copy a quote or write a strict 1-sentence definition.
5.  **Key Insight:** Your *own* words. Why does this matter?

### 🕸️ Graph Effect
* **Role:** The "Connector."
* **Visual:** These are the small, dense nodes. They should be heavily interconnected. A concept with no links is a "Orphan" and will die. **Rule:** Every concept must link to at least one other note.

---

## 5. T_Discipline (The Bucket)
*The Context / Map of Content.*

### 📝 How to Fill
1.  **Definition:** Define the boundaries. What is *Philosophy of Mind*?
2.  **Core Concepts:** This is a manually curated list. Do not link *every* concept. Link only the **Pillars** of that field.
    * *Example:* For `[[Evolution]]`, link `[[Natural Selection]]`, `[[Adaptation]]`, `[[Fitness]]`.
3.  **Unresolved Questions:** Use this to drive future research.

### 🕸️ Graph Effect
* **Role:** The "Super Node."
* **Visual:** These should be the largest nodes in your graph. They act as gravity wells, holding hundreds of concept nodes in a distinct region of the screen.

---

## 6. T_Project (The Output)
*The Factory Floor.*

### 📝 How to Fill
1.  **Deadlines:** Use the `deadline:` property in YAML for Dataview tracking.
2.  **Resources:** Link to the Concepts/Sources you are using (`[[Memetics]]`, `[[Darwin's Dangerous Idea]]`).
3.  **Log:** Update the dated bullets every time you work on it.

### 🕸️ Graph Effect
* **Role:** The "Consumer."
* **Visual:** Project nodes pull from the graph but don't necessarily add to it. They look like "Satellites" orbiting the knowledge clusters they use.

---

## ⚡ Quick Graph Check Protocol
*Run this mental check once a week.*

1.  **Orphan Check:** Do I have gray nodes that aren't real notes yet? (Click them and create them).
2.  **Cluster Check:** Do my "Biology" notes look distinct from my "Business" notes? (If they are mixed, check your `#topic` tags).
3.  **Super Node Check:** Is my `[[Philosophy of Mind]]` node getting bigger? (It should be).

---