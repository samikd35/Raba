## Module 3 Bootstrap Route (Backend Only) — Updated SRS (FastAPI + LangGraph)

### 0) Rationale and Design Intent

Yuba’s standard workflow accumulates validated upstream artifacts (PV/VPC/personas) that improve Module 3 outputs. However, advanced founders may want to begin directly at Module 3 without completing Modules 1–2. This feature introduces a **Module 3 bootstrap route** that creates a project from **project name + user-provided context (text and/or PDFs)**, generates **3–6 prioritized clarifying questions**, then performs **bounded web research** to **enhance (not change)** the idea and synthesize an **Enhanced Context Pack** that can substitute for upstream context. The system must **reuse the existing VPS/BMC agents** unchanged; only the context input differs.

Key constraints:

* Backend only (FastAPI).
* Use existing shared services: Auth/tenant resolution, Azure OpenAI, Search service, storage, embeddings/vector DB, credits/ledger.
* Research must include a **numbered Sources list** and inline citations like `[1]`, `[2]`.
* Enhanced context must be stored on the **VPM projects table** in a new column.
* **Credits must be deducted only once the final enhanced context is generated** (and before it becomes accessible to the user).
* Idempotency for project creation and credit debits must use Yuba’s **existing mechanism** (this SRS introduces no new idempotency concept).

---

## 1) Scope

### 1.1 In Scope (Backend)

* Single endpoint that: **creates project + accepts text/PDFs + starts LangGraph run**.
* PDF extraction, chunking, embedding; project-scoped vector storage for RAG.
* Clarifying question generation (3–6) using RAG over user-provided context.
* Persist Q&A and embed answers into the same project vector store.
* Web research enrichment using existing Search service; store sources; embed key snippets optionally.
* Generate Enhanced Context Pack (draft) with strict idea invariants and citations.
* Deduct credits **only at finalization**, using existing credit system patterns (auditable, idempotent per Yuba conventions).
* Store enhanced context JSON into the VPM projects table.
* Reuse existing Module 3 generation pipelines (VPS v1/BMC v1/etc.) with context switching only.

### 1.2 Out of Scope

* Module 1/2 generation (PV Report, full VPC flow, field research validation).
* Frontend requirements.

---

## 2) Functional Requirements

### 2.1 Single “Create + Intake” Endpoint

**FR-01** System shall expose a single endpoint to accept:

* `project_name` (required)
* `idea_text` (optional)
* `pdf_files[]` (optional)
  At least one of `idea_text` or `pdf_files[]` must be provided.

**FR-02** System shall create a new VPM project row and immediately persist raw intake (text + file storage keys) as an immutable artifact.

**FR-03** System shall set project `context_mode = "bootstrap"` and `context_status = "embedding"` and start the LangGraph workflow asynchronously.

### 2.2 PDF/Text Ingestion + Embeddings + RAG

**FR-04** System shall extract text from uploaded PDFs and chunk all intake content deterministically.
**FR-05** System shall embed chunks using the existing embedding provider and store vectors in a project-scoped namespace.
**FR-06** System shall provide a retrieval function `retrieve(project_id, query, top_k, source_filters)` used by:

* question generation
* research planning
* context synthesis
* (later) VPS v1 and BMC v1 generation through the existing agents

### 2.3 Clarifying Questions (3–6) with Priority Logic

**FR-07** System shall generate 3–6 clarifying questions after embeddings are available.
**FR-08** Questions must be derived using RAG over intake context and must follow the priority ladder:

**P0 (must-have for VPS/BMC coherence)**

1. target customer segment
2. geography / initial market scope
3. problem (pain + impact)
4. solution overview (what/how)
5. differentiation vs alternatives
6. who pays / monetization hypothesis

**P1 (improves BMC)**
7) channels / distribution
8) current alternatives / competitors
9) constraints (regulatory/ops/trust/infrastructure)

**P2 (nice-to-have)**
10) success signals
11) key partner dependencies

**FR-09** If P0 is already covered clearly, the system shall select questions from P1, then P2.
**FR-10** System shall persist questions and embed user answers into the same vector store (`source_type=qa_answer`).

### 2.4 Web Research + Enhancement (Do Not Change the Idea)

**FR-11** After Q&A, system shall generate bounded web search queries using RAG over the project context.
**FR-12** System shall use the existing Search service to fetch results and store them with structured metadata.
**FR-13** Research may only enhance with:

* competitor categories/examples
* typical pricing and channel patterns
* constraints/regulatory considerations
* common risks/mitigations
* market structure/terminology

**FR-14 (Idea invariants)** The agent must not change without explicit user edits:

* target customer segment
* geography
* core problem framing
* core solution type

### 2.5 Research Citations Requirement

**FR-15** Enhanced context must contain a dedicated `Research` section with:

* a research narrative body where claims reference sources as `[1]`, `[2]`, …
* a `Sources` list formatted as:

  * `1. Title — Publisher — URL`
  * `2. ...`
    and numbering must match citations in the body.

### 2.6 Enhanced Context Storage in VPM Projects Table

**FR-16** System shall add a JSONB column to the VPM projects table named `enhanced_context` to store:

* `draft` enhanced context (system-generated)
* `confirmed` enhanced context (user-edited later)
* `research_sources` (numbered list and metadata)
* `version`, timestamps, invariants snapshot

**FR-17** System shall set `context_status = "context_ready"` only after the enhanced context is stored successfully **and credits have been deducted successfully** (see Credits section).

### 2.7 Strict Reuse of Existing VPS/BMC Agents

**FR-18** VPS v1 and BMC v1 generation must reuse existing codepaths/agents.
**FR-19** The only difference in bootstrap route is the context source:

* Normal route: PV/VPC-derived context
* Bootstrap route: `vmp_projects.enhanced_context.confirmed` (or `draft` if confirmed not available) + project vector RAG

**FR-20** If existing agents require a normal-shaped context object, implement a lightweight adapter that maps enhanced context → expected shape, without changing agent logic.

---

## 3) Credits Requirements (Updated: Deduct Only at Final Content Generation)

### 3.1 When to Deduct

**CR-01** System shall **not** deduct credits at project creation.
**CR-02** System shall deduct credits **exactly once** when the Enhanced Context Pack is successfully generated and persisted, and **before** it becomes accessible to the user (i.e., before setting `context_status = "context_ready"`).

### 3.2 Idempotency and Auditability

**CR-03** Credit deduction must follow Yuba’s existing credit/ledger conventions for idempotency and auditability (this feature must not introduce a new idempotency mechanism).
**CR-04** Use a dedicated feature code, e.g.:

* `feature_code = "MODULE3_BOOTSTRAP_CONTEXT_GENERATION"`

### 3.3 Transactional Finalization (Expert Pattern)

**CR-05** The finalization step must be atomic:

* write `enhanced_context.draft` to `vmp_projects.enhanced_context`
* deduct credits (ledger debit using existing idempotency rules)
* set `context_status = "context_ready"`
  All in one database transaction (or equivalent two-phase with strict compensations consistent with Yuba’s current practice).

**CR-06** If credit deduction fails (insufficient balance, ledger error):

* do **not** set `context_status = "context_ready"`
* set `context_status = "payment_required"` (or existing equivalent)
* do not expose enhanced context via GET endpoints

**CR-07** Super admins bypass credit checks and debits consistently with existing system rules.

### 3.4 Optional Optimization (Allowed)

**CR-08** The system may perform a **preflight credit balance check** earlier (no debit) to avoid wasted compute, but the debit must still occur only at finalization.

---

## 4) Data Model Requirements (Backend)

### 4.1 VPM Projects Table Changes

Add:

* `enhanced_context JSONB NULL`
* `context_mode TEXT NOT NULL DEFAULT 'normal'` (values: `normal|bootstrap|hybrid`)
* `context_status TEXT NOT NULL DEFAULT 'embedding'`
  suggested states: `embedding | questions_pending | answers_received | researching | payment_required | context_ready | context_confirmed | failed`
* `context_version INT NOT NULL DEFAULT 1`

### 4.2 Vector Storage (Existing Pattern)

Store chunks with:

* `project_id`
* `source_type`: `idea_text | pdf_extract | qa_answer | web_research`
* `content`, `embedding`, `metadata` (file/page/url/source_number)

---

## 5) API Requirements (FastAPI) — Updated Endpoints

All endpoints use existing Auth + tenant/workspace resolution.

### 5.1 Create Project + Intake (Single Endpoint)

**POST** `/api/module3/bootstrap/projects`

* Multipart form:

  * `project_name` (required)
  * `idea_text` (optional)
  * `pdf_files[]` (optional)
* Behavior:

  * validate at least one of idea_text/pdf_files exists
  * create VPM project (`context_mode=bootstrap`, `context_status=embedding`)
  * store files (existing storage)
  * persist raw input artifact
  * start LangGraph run (async) through question generation
* Response:

  * `{ project_id, context_status: "embedding" }`

### 5.2 Fetch Questions

**GET** `/api/module3/bootstrap/projects/{project_id}/questions`

* Response when ready:

  * `{ context_status: "questions_pending", questions: [...] }`

### 5.3 Submit Answers (Resume Graph)

**POST** `/api/module3/bootstrap/projects/{project_id}/answers`

* Body: `{ answers: [{ question_id, answer }] }`
* Behavior:

  * persist answers, embed into vectors
  * set `context_status=researching`
  * resume LangGraph to research + synthesize + finalize (including credit debit)
* Response:

  * `{ context_status: "researching" }`

### 5.4 Fetch Enhanced Context (Only If Paid/Ready)

**GET** `/api/module3/bootstrap/projects/{project_id}/enhanced-context`

* If `context_status=context_ready` or `context_confirmed`:

  * returns draft/confirmed
* If `payment_required`:

  * returns error payload: `{ code: "PAYMENT_REQUIRED", message: ... }`

### 5.5 Confirm Edited Context

**PUT** `/api/module3/bootstrap/projects/{project_id}/enhanced-context/confirm`

* Body: `{ enhanced_context: { ... } }`
* Writes `enhanced_context.confirmed`, bumps version, sets `context_status=context_confirmed`

---

## 6) LangGraph Workflow Requirements (Backend Only)

### 6.1 Graph: `Module3BootstrapGraph`

Nodes:

1. `LoadRawInputNode`
2. `PdfExtractNode`
3. `ChunkEmbedNode` (idea + PDF extracts)
4. `QuestionGenNode` (RAG + priority selection) → persist → set `questions_pending` → **interrupt**
5. `AnswersIngestNode` (resume) → embed answers
6. `ResearchPlanNode` (bounded queries)
7. `WebSearchNode` (existing Search service; store sources with `n`)
8. `EnhancedContextComposeNode` (build draft with `[n]` citations and numbered Sources)
9. `FinalizeAndChargeNode` (atomic finalize):

* write `enhanced_context.draft`
* debit credits (per existing credit system idempotency rules)
* set `context_status=context_ready`
* on failure: set `payment_required`, do not expose context

### 6.2 Error Handling

* Any node failure sets `context_status=failed` and persists an error artifact with run_id and node name.

---

## 7) Enhanced Context JSON Contract (Stored in `vmp_projects.enhanced_context`)

Minimum required structure (example shape):

```json
{
  "version": 1,
  "draft": {
    "IdeaSummary": "...",
    "CustomerSegments": ["..."],
    "Problem": { "who": "...", "what": "...", "where": "...", "why_now": "..." },
    "SolutionOverview": "...",
    "Differentiation": ["...", "..."],
    "BusinessModelSeeds": {
      "who_pays": "...",
      "pricing_hypothesis": "...",
      "channels": ["..."],
      "partners": ["..."],
      "resources": ["..."],
      "cost_drivers": ["..."]
    },
    "AlternativesAndCompetition": { "summary": "...", "categories": ["..."] },
    "ConstraintsAndRisks": ["..."],
    "Research": {
      "body": "… claim ... [1] … claim ... [2] …",
      "sources": [
        { "n": 1, "title": "...", "publisher": "...", "url": "...", "captured_at": "...", "snippet": "..." },
        { "n": 2, "title": "...", "publisher": "...", "url": "...", "captured_at": "...", "snippet": "..." }
      ]
    }
  },
  "confirmed": null,
  "metadata": {
    "context_mode": "bootstrap",
    "invariants": {
      "customer_segment": "...",
      "geography": "...",
      "core_problem": "...",
      "core_solution_type": "..."
    }
  }
}
```

---

## 8) Acceptance Criteria (Backend)

1. A bootstrap project is created via a **single endpoint** that includes project_name and text/PDF intake.
2. The system generates 3–6 prioritized questions using RAG over user-provided context.
3. After answers, the system produces enhanced context that includes a numbered `Sources` list and inline `[n]` citations.
4. **Credits are deducted exactly once** and only at finalization; enhanced context is not accessible unless debit succeeds (or user is super admin).
5. Existing VPS/BMC generation continues to use the same agents/codepaths; only the context source differs when `context_mode=bootstrap`.

---
