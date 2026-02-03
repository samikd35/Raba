## Product Requirements: Go-To-Market (GTM) Strategy Generator — Backend Only (FastAPI + LangGraph)

### 1) Purpose

Generate a **complete GTM Strategy Pack** for an existing project by leveraging the project’s **already chunked/embedded stored artifacts** (RAG) and **optional bounded web research** when external context is required (e.g., competitor landscape, market benchmarks, regulatory notes). The GTM output must be fully generated from available project context (no placeholders).

---

### 2) Goals

* Produce a structured, actionable GTM strategy covering the **full GTM workflow** (problem → audience → insights → value prop → messaging → channels → customer success motion → metrics).
* Ground outputs primarily in the project’s stored artifacts, prioritizing the **latest versions** (v2 over v1).
* Use web search **only when needed** and always return **structured sources** for externally-derived claims.
* Persist outputs with **versioning** and traceability (retrieval and web research traces).

---

### 3) Non-Goals (v1)

* Frontend/UI design, rich formatting, PDF export.
* Re-chunking/re-embedding logic (assumed already handled).
* Interactive clarification flows (since you require no placeholders).
* Automatic write-back modifications to upstream artifacts.

---

### 4) Inputs

**Required**

* `project_id` (plus your platform’s tenant/workspace scope)

**Optional (if supplied)**

* GTM context constraints: target geography focus, launch timeline, budget band, target segment priority, deck purpose alignment (fundraising vs sales), product stage.

If optional inputs are missing, the agent must infer from existing artifacts rather than requesting user data.

---

### 5) Data Sources (Project Corpus)

The GTM agent must retrieve from the project’s stored artifacts, including (as available):

* Problem validation report
* Persona
* Customer profile v1/v2 (prefer v2)
* Hypothesis + assumptions
* Questionnaire insights
* Market research analysis
* Value map
* VPS v1/v2 (prefer v2)
* BMC v1/v2 (prefer v2)
* Solution critique
* Requirement generator output
* Pitch deck (if present; for narrative consistency)

**Precedence rule:** prefer **latest/most authoritative** (v2) artifacts; use earlier artifacts only if needed for missing detail or historical rationale.

---

### 6) Output

A **GTM Strategy Pack (JSON)** containing:

* `summary` (1–2 paragraphs)
* `steps[1..8]` (your GTM steps), each with:

  * `content`: actionable guidance (clean text)
  * `description`: short explanation + citation markers (if you use citation markers) or reference notes
  * `sources_used`: list of internal and/or external source IDs referenced by that step
* `channel_plan`: prioritized channels with rationale, funnel stage mapping, and a lightweight experiment plan
* `customer_success_motion`: recommended motion (self-serve / assisted / partner-led) + onboarding/retention approach
* `metrics_plan`: north-star metric + funnel KPIs + 30/60/90 targets
* `execution_plan_30_60_90`: milestones and weekly actions
* `sources`: structured citations metadata:

  * internal: artifact reference + version + chunk reference
  * external: url/title/domain + evidence snippet + fetched timestamp
* `run_trace`: retrieval IDs, web queries (if used), and audit metadata

---

### 7) Functional Requirements

#### 7.1 GTM planning and section generation

* The system must generate all GTM steps in a consistent order:

  1. Define the Problem
  2. Define the Audience (ICP/personas)
  3. Gather Market Insights
  4. Product Value Proposition
  5. Manifesto / Key Messaging
  6. Channel Mastery
  7. Customer Success Methodology (sales/onboarding/retention)
  8. Goals & Performance Metrics

#### 7.2 Retrieval (Project RAG)

* For each GTM step, perform **step-scoped retrieval** from the project index using strict project scoping filters.
* Retrieval must be **artifact-aware** (e.g., channels step pulls primarily from BMC v2 + research).
* Conflicts must be resolved using the precedence rule (v2 preferred).

#### 7.3 Optional bounded web research

* Web research is allowed only for steps where external context materially improves quality (typically: market insights, competition, channels, regulatory constraints).
* Web research must be bounded (limited queries/results/time) and return **structured sources**.
* Any externally-derived factual claim must be attributable to returned web sources.

#### 7.4 Consistency checks

* The final output must be internally consistent across:

  * ICP/persona ↔ value proposition ↔ messaging ↔ channels ↔ success motion ↔ metrics
* If contradictions exist in the artifacts, the agent must:

  * reconcile using latest artifacts, and
  * record a brief note in the relevant step description (without requesting user input).

#### 7.5 Persistence and versioning

* Persist each GTM output as a versioned artifact linked to the project.
* Store associated sources and run traces for audit/debug.

---

### 8) System Requirements (LangGraph orchestration)

The LangGraph workflow must:

1. Load project metadata + artifact availability.
2. For each GTM step:

   * build retrieval query → retrieve evidence → grade sufficiency
   * if needed, perform bounded web research and extract evidence
   * write step output + attach sources
3. Run a cross-step consistency checker.
4. Assemble final GTM pack + sources + trace.
5. Persist results.

---

### 9) API Requirements (FastAPI)

Provide endpoints to:

* Trigger GTM generation for a `project_id` (sync or async job pattern consistent with your platform).
* Fetch a GTM run result (latest or by version).
* List GTM versions for a project.

---

### 10) Security and Safety Requirements

* Enforce strict authorization and tenant/workspace/project isolation.
* Treat retrieved project text and web content as untrusted; do not allow it to override system/tool rules.
* Do not fabricate facts; rely on project evidence or web evidence. When evidence is weak, prefer conservative language grounded in artifacts.

---

### 11) Acceptance Criteria

* Given a valid project_id, the system returns a complete GTM Strategy Pack (all 8 steps) generated from project artifacts.
* Web search is used only when needed and all external claims are source-backed.
* Output is consistent with the project’s latest v2 artifacts (Customer Profile v2, VPS v2, BMC v2).
* Result is persisted with versioning and includes retrievable sources + run trace.
* No cross-project leakage in retrieval or output.
