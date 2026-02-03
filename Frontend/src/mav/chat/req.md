## Product Requirements: Project Chat (Module 4) — Backend Only (FastAPI + LangGraph)

### 1) Purpose

Provide a **ChatGPT-style project chat** where users can ask questions about a specific project and receive **grounded answers** using:

* **Project RAG** over the project’s stored artifacts (already chunked/embedded by project ID), and
* **Optional bounded web search** when internal project data is insufficient.

The system must support **threads, history, and memory**, and must attach **sources/citations** to answers.

---

### 2) Goals

* **Threaded conversations per project** (multiple threads per project).
* **Message history persistence** with pagination and reliable ordering.
* **Thread memory** that maintains continuity without replaying entire history (summary + pinned facts + open loops).
* **Grounded answers** with structured citations:

  * Internal (project artifact/chunk references)
  * External (web sources)
* **Routing** between:

  * RAG-only answers
  * RAG + web search answers
  * Web-only answers (if user asks something outside the project)
* **Auditability**: store retrieval references, web sources used, and model/tool metadata per assistant message.

---

### 3) Non-goals (v1)

* Frontend/UI behavior and rendering.
* Re-chunking/re-embedding logic (assumed done).
* Automated write-back edits to project artifacts (can be future phase).
* Ticket generation, workflow automation, or CRM-like task management.

---

### 4) Primary User Outcomes

* Users can create a project thread and continue conversations over days/weeks.
* Users can ask: “What did we decide about X?” and get consistent answers based on stored artifacts.
* Users can ask: “What’s the latest benchmark / regulation / competitor info?” and get a sourced answer via web research when needed.
* Users can review “Sources” per answer and trust where information came from.

---

### 5) Functional Requirements

#### 5.1 Threads and history

* Create a thread under a project.
* List threads under a project (sorted by recent activity).
* Post a user message to a thread.
* Retrieve messages in a thread with pagination (cursor/limit).
* Store assistant and tool messages in the same thread history (role-based).

#### 5.2 Thread memory (continuity layer)

Maintain thread-level state, separate from raw message history:

* **Running summary**: compact summary of the thread so far.
* **Pinned facts**: user-validated stable facts/preferences/decisions (minimal, high-signal).
* **Open loops**: unanswered questions, pending decisions, requested follow-ups.
* **Last context refs**: last-used project chunks and web sources (for traceability and debugging).

Memory update rules:

* Summary updates incrementally after each assistant response (or every N turns).
* Pinned facts only updated when user confirms or the system has high confidence (configurable).

#### 5.3 RAG answering (project-grounded)

For each user question, the system must:

* Filter retrieval strictly by `tenant/workspace/project` boundaries.
* Retrieve relevant project evidence (top-K chunks).
* Use evidence in the response.
* Emit internal citations that reference the retrieved evidence.

#### 5.4 Web search augmentation (bounded research)

If project evidence is insufficient, the system must:

* Execute bounded web research (limited results, limited fetches, timeouts).
* Extract short evidence snippets.
* Produce an answer with web citations.
* Optionally store a compact “web research note” as a project-linked record (recommended for reuse).

#### 5.5 Source attachment (citations as metadata)

Assistant responses must include:

* Clean natural language answer text.
* A structured list of citations with:

  * Internal: artifact reference + version + chunk/section reference + snippet (optional)
  * External: url + title/domain + fetched time + snippet (optional)

Citations must be generated only from retrieved evidence (no fabricated sources).

---

### 6) System Behavior Requirements

#### 6.1 Orchestration (LangGraph)

The chat run should follow this logical flow:

1. Load thread memory + recent message window (bounded).
2. Route intent: project-grounded vs needs web vs web-only vs meta.
3. Retrieve project evidence (RAG).
4. Decide if evidence is sufficient; if not, do bounded web research.
5. Synthesize answer with citations.
6. Persist assistant message + citations + tool trace.
7. Update thread memory.

#### 6.2 Context assembly (avoid prompt bloat)

When generating an answer, include only:

* Thread summary + pinned facts + open loops
* Recent message window (configurable N)
* Retrieved project evidence snippets
* Web evidence snippets (if used)

Do not load full message history into the model input.

---

### 7) Data Requirements (backend storage)

Minimum persisted entities (conceptual):

* **Thread**: project linkage, title, created/updated metadata.
* **Message**: thread linkage, role, content, timestamps, optional tool trace.
* **Thread Memory**: summary, pinned facts, open loops, last context refs.
* **Citation** (either embedded in Message record or separate table): typed references to internal evidence and web sources.

Key requirement: internal citations must include **artifact versioning** to remain auditable after project artifacts evolve.

---

### 8) API Requirements (FastAPI)

Provide endpoints to support:

* Thread lifecycle: create, list, read.
* Messaging: post message (triggers orchestration), list messages (pagination).
* Optional: read thread memory state (admin/debug) and/or export thread transcript.

The “post message” endpoint must be synchronous from the client’s perspective (single request yields assistant response), unless your platform already uses job polling—either is acceptable as long as history integrity is maintained.

---

### 9) Security and Safety Requirements

* Strict multi-tenant isolation (enforced in DB queries and retrieval filters).
* Treat retrieved project text and web content as **untrusted data**:

  * Do not allow retrieved content to override system/developer instructions.
* Tool gating:

  * Web search only when routed as necessary.
  * No write-actions to project artifacts in v1.
* Store minimal web content (snippets/evidence) rather than full pages unless required.

---

### 10) Observability and Quality Requirements

For each assistant message, store:

* Retrieval identifiers (e.g., chunk IDs + scores)
* Whether web research was used + sources list
* Latency and token usage (if available)
* User feedback hooks (thumb up/down + optional reason) if your platform supports it

---

### 11) Acceptance Criteria (Definition of Done)

* Users can create/list threads and post messages to receive answers.
* Thread message history persists correctly and is retrievable with pagination.
* Thread memory updates automatically and improves continuity across long threads.
* Answers include structured citations:

  * RAG-only questions cite internal evidence.
  * Web-augmented questions cite web sources.
* Web search triggers only when internal evidence is insufficient (router + sufficiency check).
* No cross-project or cross-tenant leakage in retrieval or thread access.
* Tool traces and citations are persisted for audit/debug.

---

### 12) Suggested v1.1 Extensions (optional)

* “Write-back” mode: propose edits to artifacts with user approval.
* Cross-thread project memory: reusable “decisions” and “research notes.”
* Re-ranking and retrieval quality tuning knobs.
* Automatic thread titles and thread clustering.

If you want, I can convert this into a **backend SRS-style spec** (entities, request/response shapes, LangGraph state schema, and step-by-step orchestration) while still staying convention-agnostic.
