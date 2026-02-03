# Yuba Module 3 — Agentic MVP Requirements Generator (AMRG)

## 1. Purpose

AMRG is a LangGraph-based, multi-agent backend service that generates a template-compliant MVP Product Requirements artifact (JSON only) for an existing Yuba project. AMRG uses only the project's stored business-definition artifacts (VPS/BMC + critique) to produce a structured MVP requirement output suitable for MVP development planning.

---

## 2. Scope

### 2.1 In Scope

- Run AMRG only for an already-created `project_id` in Yuba
- Load the required project artifacts and normalize them into a single `context_pack`
- Perform **two-stage template routing**:
  - Coarse routing before clarification (top candidates + confidence)
  - Final routing lock after clarification (deterministic selection)
- Ask exactly **three clarifying questions**, persist state, resume after answers
- Optional bounded web research (tool-based), controlled via `research_mode` (`off`/`auto`/`on`), with stored sources/notes
- Generate **JSON-only output** validated against a template-specific JSON schema
- Persist run state (interrupt/resume), version outputs, and store audit metadata

### 2.2 Out of Scope (v1.2)

- UI requirements and frontend behavior
- Markdown/PDF output
- Auto-conversion to tickets/user stories

---

## 3. Eligibility and Inputs

### 3.1 Eligibility Preconditions

AMRG must only start if:

1. `project_id` exists and is accessible under the active tenant/workspace
2. The project contains all required artifacts

**Required artifacts** (must exist in the project's stored data):

| Artifact | Description |
|----------|-------------|
| VPS v1 | Value Proposition Statement v1 |
| BMC v1 | Business Model Canvas v1 |
| Solution Critique | Solution Critique |
| VPS v2 | Value Proposition Statement v2 |
| BMC v2 | Business Model Canvas v2 |

### 3.2 Eligibility Failure Response

If any required artifact is missing, AMRG must return:

```json
{
  "error_code": "MISSING_REQUIRED_ARTIFACTS",
  "missing_artifacts": ["vps_v1", "bmc_v1", "solution_critique", "vps_v2", "bmc_v2"]
}
```

> Only include those that are missing.

### 3.3 Context Pack (Authoritative Inputs)

AMRG must load only the following from the project:

```json
{
  "project_id": "uuid",
  "tenant_id": "uuid",
  "artifacts": {
    "vps_v1": { },
    "bmc_v1": { },
    "solution_critique": { },
    "vps_v2": { },
    "bmc_v2": { }
  },
  "metadata": {
    "project_title": "string",
    "project_description": "string",
    "industry": "string | null",
    "geography": "string | null"
  }
}
```

---

## 4. Output Contract (JSON Only)

### 4.1 Primary Output

AMRG produces `prd_json` only, and it must validate against the selected template's JSON Schema.

### 4.2 Minimum Fields Required in All Template Outputs

Every `prd_json` must include:

| Field | Description |
|-------|-------------|
| `template_code` | e.g., "A1" |
| `template_version` | Version of the template used |
| `schema_version` | Version of the schema |
| `purpose` | Why this MVP exists |
| `objective` | Learning goals/outcomes |
| `scope` | Explicitly included/excluded |
| `mvp_features.must_haves[]` | Required MVP features |
| `mvp_features.nice_to_haves[]` | Deferred features |
| `critical_workflows[]` | Flows relevant to the template |
| `constraints_and_nongoals[]` | What is deliberately excluded |
| `success_signals` | Metrics + qualitative signals |
| `assumptions_and_risks[]` | Key assumptions and risks |
| `source_artifacts_used` | References to VPS/BMC versions + critique |
| `research` (optional) | Sources and extracted notes (if enabled) |

---

## 5. Template System Requirements

### 5.1 Template Codes as Stable Backend Contract

Template codes must be represented in Python as a stable Enum and used throughout:

- Run state
- Persistence tables
- Logs/metrics
- API responses

**Example (normative pattern):**

```python
from enum import Enum

class TemplateCode(str, Enum):
    A1 = "A1"  # Software / SaaS / App
    A2 = "A2"  # Digital content / Course / EdTech
    A3 = "A3"  # Platform / Marketplace
    A4 = "A4"  # Tech-enabled services
    A5 = "A5"  # Fintech
    B1 = "B1"  # Offline services
    C1 = "C1"  # CPG / FMCG
    C2 = "C2"  # Hardware / IoT
```

### 5.2 Prompt Templates Stored in Code

Each template must exist as a prompt template file in the repository (recommended `.j2` rendered by Jinja2 in Python). There is **no database template registry** and **no runtime editing UI**.

**Recommended repository structure:**

```
amrg/prompts/templates/
├── a1_prd.j2
├── a2_prd.j2
├── a3_prd.j2
├── a4_prd.j2
├── a5_prd.j2
├── b1_prd.j2
├── c1_prd.j2
├── c2_prd.j2
├── a1_questions.j2
├── a2_questions.j2
└── ...
```

### 5.3 Registry Mapping

AMRG must implement a Python registry mapping `TemplateCode` → `TemplateSpec`.

**TemplateSpec (normative fields):**

| Field | Description |
|-------|-------------|
| `code` | Template code (e.g., "A1") |
| `name` | Human-readable name |
| `prd_prompt_path` | Path to PRD prompt template |
| `questions_prompt_path` | Path to questions template |
| `schema_path` | Path to JSON schema |
| `template_version` | Template version |
| `schema_version` | Schema version |

This registry is the authoritative definition of what A1/A2/etc "are" in the codebase.

---

## 6. LangGraph Architecture Requirements (Multi-Agent)

### 6.1 Required Nodes/Phases

AMRG must implement a LangGraph state machine with at least the following nodes:

#### EligibilityGateNode
Validates project existence and required artifacts.

#### ContextLoaderNode
Loads VPS v1, BMC v1, Solution Critique, VPS v2, BMC v2 into `context_pack`.

#### Two-Stage Routing

**TypeRouterCoarseNode**
Produces coarse routing output using `context_pack`:
- `top_templates[]` (at least top 2 when confidence is not high)
- Confidence scores
- Rationale

**ClarifyingQuestionNode**
Generates exactly 3 clarifying questions derived from:
- Coarse routing candidates (`top_templates`) and uncertainty points
- Gaps/ambiguities detected from VPS/BMC + critique

> **Rule:** When coarse confidence is below a defined threshold, Question 1 must be designed to disambiguate between the top candidates.

**Interrupt/WaitForAnswers**
Persists state and stops until answers are submitted.

**AnswerNormalizationNode**
Parses answers into structured fields used by the template.

**TypeRouterFinalNode**
Re-evaluates routing using `context_pack` + the 3 answers and then:
- Sets `selected_template_code` (final, locked)
- Sets final confidence + rationale
- Resolves `TemplateSpec` from the registry for downstream steps

#### Research Control Model

**ResearchPlannerNode (Optional)**
Research usage must be governed by `research_mode`:

| Mode | Behavior |
|------|----------|
| `off` | Never use web research |
| `auto` (default) | Planner decides based on template_code + missing constraints + user answers |
| `on` | Always run bounded research |

Planner produces a bounded plan: max queries, max sources, and extraction targets.

**WebResearchLoopNode (Optional)**
Tool-calling loop that stores `sources[]` and `research_findings[]`.

#### PRDGenerationNode
Renders the template prompt (`.j2`) using `context_pack` + answers + research and calls the LLM to produce JSON only.

#### SchemaValidationNode
Validates output against template schema and deterministic constraints.

#### RepairNode (bounded loop)
Attempts up to N repairs on validation failure; otherwise returns a structured "needs input" error.

#### PersistOutputNode
Stores versioned `prd_json` plus metadata.

### 6.2 State Object (Minimum Required)

| Category | Fields |
|----------|--------|
| **Identity** | `run_id`, `tenant_id`, `project_id`, `user_id` |
| **Context** | `context_pack` |
| **Coarse Routing** | `top_templates[]`, `coarse_confidence_map`, `coarse_rationale` |
| **Clarification** | `clarifying_questions[3]`, `clarifying_answers` (structured) |
| **Final Routing** | `selected_template_code`, `final_confidence`, `final_rationale`, `template_spec_ref` |
| **Research** | `research_mode`, `research_plan` (optional), `sources[]` (optional), `research_findings[]` (optional) |
| **Output** | `prd_json`, `validation_report`, `repair_attempts` |
| **Persistence** | `thread_id`, `status` |

---

## 7. Functional Requirements (FR)

### FR-01: Project Access and Eligibility

- The system shall require an existing project
- System shall verify required artifacts exist (VPS v1, BMC v1, Solution Critique, VPS v2, BMC v2)
- System shall return a structured error if missing

### FR-02: Context Load

- System shall load only the five specified artifacts and minimal metadata

### FR-03a: Coarse Template Routing (Pre-clarification)

System shall perform coarse routing using `context_pack` and produce:
- `top_templates[]` (include at least top 2 when confidence is below threshold)
- Confidence scores and rationale

### FR-03b: Final Template Routing (Post-clarification)

System shall perform final routing after the 3 answers are collected and:
- Set `selected_template_code` (final)
- Resolve `TemplateSpec` (prompt paths + schema)
- Store final confidence and rationale

### FR-04: Exactly Three Clarifying Questions

- System shall generate exactly three questions per run
- System shall not proceed until all three are answered
- If coarse routing confidence is below the threshold, Q1 must disambiguate between the top candidates

### FR-05: Template Rendering (Prompt in Code)

- System shall render `.j2` prompt templates with strict undefined-variable behavior (fail-fast if variables are missing)
- Prompts must be versioned in source control

### FR-06: JSON-only Generation

- System shall enforce JSON-only outputs (no markdown, no prose outside JSON)
- System shall reject or repair outputs that contain non-JSON

### FR-07: Validation and Repair

- System shall validate `prd_json` against template JSON schema + deterministic checks (minimum counts, required sections)
- System shall attempt up to N repairs; if still failing, return:

```json
{
  "error_code": "PRD_VALIDATION_FAILED",
  "missing_fields": ["..."],
  "notes": "..."
}
```

### FR-08: Research Mode (off/auto/on)

System shall support `research_mode` per run:

| Mode | Behavior |
|------|----------|
| `off` | Research nodes are skipped |
| `auto` | ResearchPlannerNode decides whether to run WebResearchLoopNode |
| `on` | Research nodes must run |

- System shall bound queries/sources in all cases
- System shall store sources and extracted notes
- System shall treat web content as untrusted (cannot override system/template instructions)

### FR-09: Versioning and Auditability

System shall store each output as a new version and retain:
- Template code + versions
- Coarse routing output
- Final routing output
- Q/A
- Research metadata (if used)
- Validation reports

### FR-10: Tenancy and Access Control

- All operations must be tenant/workspace scoped

---

## 8. Data Storage Requirements (Recommended)

### `amrg_runs`

| Field | Description |
|-------|-------------|
| `id` | Primary key |
| `tenant_id` | Tenant identifier |
| `project_id` | Project identifier |
| `user_id` | User identifier |
| `status` | `created`, `awaiting_answers`, `running`, `completed`, `failed` |
| `coarse_top_templates` | JSON array of top templates |
| `coarse_confidence_map` | JSON map of confidence scores |
| `coarse_rationale` | Text rationale |
| `selected_template_code` | Final selected template |
| `final_confidence` | Final confidence score |
| `final_rationale` | Final rationale |
| `template_version` | Template version used |
| `schema_version` | Schema version used |
| `research_mode` | `off`, `auto`, or `on` |
| `thread_id` | LangGraph thread ID |
| `state_json` | Full state snapshot |
| `timestamps` | Created/updated timestamps |
| `error_fields` | Error information |

### `amrg_qna`

| Field | Description |
|-------|-------------|
| `run_id` | Foreign key to run |
| `q_index` | Question index (1..3) |
| `question_text` | Question text |
| `answer_text` | User's answer |

### `amrg_outputs`

| Field | Description |
|-------|-------------|
| `run_id` | Foreign key to run |
| `version` | Output version number |
| `prd_json` | Generated PRD JSON |
| `validation_report_json` | Validation results |
| `timestamps` | Created/updated timestamps |

### `amrg_sources` (optional)

| Field | Description |
|-------|-------------|
| `run_id` | Foreign key to run |
| `url` | Source URL |
| `title` | Source title |
| `extracted_notes` | Extracted content |

---

## 9. API Requirements (FastAPI)

### `POST /projects/{project_id}/amrg/runs`

- Validates eligibility
- Runs coarse routing
- Returns `run_id` + coarse routing output + 3 questions
- Accepts optional `research_mode` in payload (default `"auto"`)

### `POST /amrg/runs/{run_id}/answers`

- Submits answers
- Runs final routing lock
- Runs research according to `research_mode`
- Triggers PRD generation + validation + persistence

### `GET /amrg/runs/{run_id}`

- Returns status and `prd_json` when complete

### `POST /amrg/runs/{run_id}/regenerate`

- Accepts revision instructions + optional template override + `research_mode`

### `GET /projects/{project_id}/amrg/history`

- Returns output versions + metadata

---

## 10. Non-Functional Requirements (NFR)

| Category | Requirement |
|----------|-------------|
| **Reliability** | Restart-safe via persisted checkpoint state |
| **Security** | Least-privilege access; avoid unnecessary PII in logs; research injection resistance |
| **Observability** | Structured logs keyed by run/project/tenant/template; record validation failures and repair attempts; record coarse vs final routing decisions |
| **Maintainability** | Template prompt files and schemas are code-reviewed; automated tests verify schema validity per template |

---

## 11. Acceptance Criteria

A run is accepted as complete when:

1. **Clarifying Questions Phase**
   - For an eligible project, AMRG returns exactly 3 clarifying questions and persists state (`awaiting_answers`)
   - Returns coarse routing output (`top_templates` + confidence + rationale)

2. **PRD Generation Phase**
   - After answers submission, AMRG performs final routing lock
   - Produces `prd_json` that passes schema validation and deterministic constraints
   - Output includes `template_code`, `template_version`, `schema_version`
   - Output includes purpose/objective/scope, must-have vs nice-to-have features, workflows, constraints/non-goals, success signals, assumptions/risks

3. **Research Behavior**
   - `off`: No sources stored
   - `auto`: Sources stored only when the planner decides
   - `on`: Sources stored for every run
   - If research is enabled, sources and extracted notes are stored and referenced in the output's `research` field
