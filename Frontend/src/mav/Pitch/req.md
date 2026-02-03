## Product Requirements: Pitch Deck Generator — Backend Only (FastAPI + LangGraph)

### 1) Purpose

Generate a **pitch deck content package** for an existing project by using the project’s **already embedded/chunked artifacts** (RAG) and optional **bounded web research**. The output is structured as **slide-by-slide content**, where each slide has:

* **Slide content** (headline + concise bullets), and
* A separate **short Description** that contains the **citations** and supporting context (citations must not appear inside slide bullets).

This feature is backend-only and must integrate into the existing platform and storage model.

---

### 2) Goals

* Produce a complete, stage-appropriate deck plan (must-have + conditional slides).
* Generate slide content grounded in project evidence (RAG) and web evidence when required.
* Include **Team** and **Financials** as **placeholders** when inputs are missing (no fabrication).
* Persist deck outputs with versioning and full traceability (sources, retrieval refs, web refs).
* Support repeatable generation (same inputs → deterministically similar structure).

---

### 3) Non-goals (v1)

* UI rendering, PowerPoint/PDF export, design templates, graphics generation.
* Editing workflows, collaboration comments, and slide theming.
* Re-chunking/re-embedding (assumed already done elsewhere).
* Automatic write-back to project artifacts (future phase).

---

### 4) Inputs

**Required**

* `project_id` (and platform’s tenant/workspace scoping)

**Optional (if supplied by upstream modules or user payload)**

* Deck purpose: fundraising vs demo vs partner/sales
* Stage: ideation / pre-seed / seed / growth
* Category hints: platform/SaaS, CPG, infrastructure/project-based
* Team info (names/roles/1-liners) — if not supplied, generate placeholder slide
* Traction metrics — if not supplied, omit or replace with “validation” if available
* Financial inputs (pricing assumptions, costs, forecast) — if not supplied, generate placeholder slide
* Constraints (target investor type, geography, sector)

---

### 5) Outputs

A **Deck Package (JSON)** containing:

* Deck metadata (project_id, purpose/stage/category, generation timestamp, version)
* Ordered list of slides:

  * `slide_type`
  * `title/headline`
  * `bullets[]` (slide-visible text; no citations)
  * `description` (short paragraph or bullets that includes citation markers)
  * `placeholders[]` (fields the user must fill if data is missing)
* A **Citations object** (structured) referenced by markers used inside descriptions:

  * Internal citations: artifact/chunk references + artifact version
  * Web citations: url/title/domain + evidence snippet + fetched_at
* Run trace / audit metadata:

  * retrieval ids, web queries, latency/tokens (if available)

---

### 6) Functional Requirements

#### 6.1 Deck planning (layout selection)

* The system must generate a **slide plan** based on:

  * available project artifacts
  * stage/purpose/category (if provided; otherwise infer from artifacts)
* The plan must include:

  * **must-have slides** (core narrative)
  * **conditional slides** only when data exists or can be supported via web research
* The plan must support category-specific layouts (e.g., platform vs CPG vs infrastructure) without requiring UI changes.

#### 6.2 RAG-based slide generation (project evidence)

For each slide:

* Retrieve project evidence using strict project scoping (tenant/workspace/project_id filters).
* Generate slide headline + bullets **only from grounded information**.
* Attach citation markers (e.g., [P1], [P2]) **only in the slide Description**, not in bullets.

#### 6.3 Optional bounded web research (slide-scoped)

* Web search must be invoked only when project evidence is insufficient and the slide requires external facts (market sizing, benchmarks, competitor landscape, regulatory constraints, etc.).
* Web research must return short evidence snippets and sources.
* Web citation markers (e.g., [W1]) must appear in the slide Description only.

#### 6.4 Placeholder handling (Team + Financials and other gaps)

* If team data is not available, generate a **Team placeholder slide** with fill-in fields (no invented names/credentials).
* If financial inputs are not available, generate a **Financials placeholder slide** with:

  * assumption fields (pricing, volume, costs, margins, runway)
  * a minimal “use of funds” template (optional)
* Traction must never be invented:

  * include only if present; otherwise omit or replace with “Validation to date” only if evidence exists in project artifacts.

#### 6.5 Consistency and quality checks

* After all slides are drafted, run an internal consistency pass to ensure:

  * problem/solution alignment across slides
  * same persona/target customer wording
  * consistent business model and GTM logic
  * no unsupported numeric claims
* If inconsistencies are found, the system must resolve them or flag them in the output as warnings.

#### 6.6 Persistence and versioning

* Persist each generated deck with:

  * deck JSON output
  * citations metadata
  * run trace (retrieval + web)
  * version number and timestamps
* Support retrieval of past deck versions.

---

### 7) System Requirements (LangGraph orchestration)

The agent flow must:

1. Load project context summary + available artifacts list.
2. Plan deck (slides + conditions + placeholder rules).
3. For each slide:

   * generate a slide-specific retrieval query
   * retrieve project evidence
   * decide sufficiency
   * optionally execute bounded web research
   * write slide content + description + citations
4. Run cross-slide consistency checks.
5. Persist deck output + citations + trace.

---

### 8) API Requirements (FastAPI)

Backend must provide endpoints to:

* Trigger deck generation for a `project_id` (sync or async job pattern consistent with platform).
* Fetch the generated deck package (deck + citations + metadata).
* List deck versions for a project.
* (Optional) Provide a lightweight “deck plan preview” endpoint (slides list only).

---

### 9) Security and Safety Requirements

* Enforce strict tenant/workspace/project authorization at every step.
* Treat retrieved project content and web content as untrusted data.
* Do not fabricate:

  * market numbers, traction, partnerships, customer names, financial performance, team credentials.
* Require citations for any non-trivial external factual statements (in descriptions).

---

### 10) Acceptance Criteria (Definition of Done)

* Given a project_id, the system generates a coherent slide plan and slide content grounded in project artifacts.
* Citations appear in slide **Descriptions only**, with structured citation metadata returned alongside the deck.
* Team and Financials appear as placeholders when missing; no invented facts.
* Web search triggers only when needed and produces cited evidence.
* Outputs are persisted with versioning and full traceability (retrieval/web traces).
* No cross-project leakage in retrieval or outputs.

If you want, I can also provide a compact “LangGraph node spec” (node I/O contracts + state keys) that matches this requirement while remaining naming-convention agnostic.
