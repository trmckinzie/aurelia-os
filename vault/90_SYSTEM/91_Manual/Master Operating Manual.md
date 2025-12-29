# 🏛️ AURELIA OS: Master Operating Manual
**Version:** 3.0
**Role:** Personal Knowledge Management & Digital Garden Architecture
**Philosophy:** "Turn Information into Intelligence."

---

## 1. Core Philosophy: The Evolutionary Engine
This system is not a static archive; it is a living ecosystem. Ideas are not "filed away"; they are "grown."

1.  **The Selector:** I am the evolutionary filter. Ideas survive only if I interact with them.
2.  **The Lifecycle:** * **🌱 Seed:** Raw capture, quick thought.
    * **🌿 Sapling:** Developing idea, connected to others.
    * **🌳 Evergreen:** Polished synthesis, ready for public display.
3.  **The Separation:**
    * **Obsidian:** The Factory (Private, messy, interconnected).
    * **Website:** The Storefront (Public, curated, rigid).

---

## 2. Directory Structure (The "Where")
*Folders define the storage location and mirror the public website.*

* 00_INBOX
* 10_LOGS
	* 11_Daily_Bridge
* 20_PROJECTS
* 30_ATLAS
	* 31_Concepts
* 40_SOURCES
	* 41_Authors
* 42_Materials
* 90_SYSTEM
	* 91_Aurelia_OS_Manual
	* 92_Templates

---

## 3. Tagging Architecture (The "What")
*Tags provide context and link disparate ideas. We use a strict 3-Tier System.*

### 🏛️ Tier 1: TYPE (The Container)
*Mandatory. Defines the structure of the note.*
* `#type/daily-bridge` → Active working sessions/logs.
* `#type/author` → People (e.g., Daniel Dennett).
* `#type/source/book` → (also `/article`, `/video`).
* `#type/concept` → **The Atom.** Specific ideas (e.g., *Intentional Stance*).
* `#type/discipline` → **The Bucket.** Broad fields (e.g., *Cognitive Science*).
* `#type/project` → Active work/outputs.

### 🧠 Tier 2: TOPIC (The Domain)
*Flexible. Defines the subject matter.*
* **Mind:** `#topic/phil-mind`, `#topic/cognitive-sci`, `#topic/self`
* **Systems:** `#topic/evolution`, `#topic/systems`, `#topic/memetics`
* **Life:** `#topic/stoicism`, `#topic/business`, `#topic/design`

### 🚦 Tier 3: STATUS (The Health)
*Mandatory. Tracks the evolutionary stage.*
* **For Ideas:** `#status/seed` → `#status/sapling` → `#status/evergreen`
* **For Sources:** `#status/to-read` → `#status/reading` → `#status/processed`
* **For Projects:** `#status/active` → `#status/archive`

---

## 4. The Template Library (The Tools)
*Located in `90_SYSTEM/92_Templates`. Always insert these using `CMD+P` -> `Insert Template`.*

| Template Name | Purpose | When to use |
| :--- | :--- | :--- |
| **T_DailyBridge** | The Session Log | Use for every "Deep Work" session. Captures reading notes and tasks. |
| **T_Source** | The Material | Create this for every Book/Article. Holds metadata and summary. |
| **T_Author** | The Creator | Create when finding a new thinker. links their works together. |
| **T_Concept** | The Atom (Brick) | Use for specific ideas (*Skyhooks*). The building blocks of the vault. |
| **T_Discipline** | The Scope (Bucket) | Use for broad fields (*Biology*). Connects many concepts together. |
| **T_Project** | The Output | Use for deliverables (*Write Essay*, *Client Website*). |

---

## 5. The Standard Workflow (The Loop)

### Phase 1: Intake (The Bridge)
1.  Open a new **DailyBridge** note.
2.  Set the Goal (e.g., "Read Chapter 1 of *Darwin's Dangerous Idea*").
3.  Take Cornell-style notes in the Bridge file.

### Phase 2: Processing (Atomization)
1.  Review the DailyBridge notes.
2.  Extract **Authors** into `T_Author` notes.
3.  Extract **Concepts** into `T_Concept` notes.
4.  Link them back to the **Source** (`T_Source`).
5.  *Result:* The DailyBridge becomes a connector; the knowledge now lives in the Atoms.

### Phase 3: Gardening (Evolution)
1.  **Seed:** A concept note is created with just a definition.
2.  **Sapling:** Later, you add a "Key Insight" or link it to a different author. Change tag to `#status/sapling`.
3.  **Evergreen:** The note is fully written, referenced, and stands alone. Change tag to `#status/evergreen` and move folder to `20_MUSEUM`.

### Phase 4: Assembly (Synthesis)
1.  Go to a **Discipline** note (e.g., *Evolutionary Theory*).
2.  Link your new Evergreen concepts into the "Core Concepts" list.
3.  This builds the "Map" of that field.

---

## 6. Maintenance Protocols
* **Inbox Zero:** At the end of every DailyBridge session, move new files from `00_INBOX` to their respective folders.
* **Tag Audit:** Ensure every file has at least a **Type** and a **Status**.
* **Backup:** Weekly backup of the Vault to external drive or GitHub.

---
*End of Manual. System Nominal.*