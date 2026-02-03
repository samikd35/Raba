# BMC Generation - Visual Flow Diagrams

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BMC GENERATION SYSTEM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐     │
│  │   Context    │      │     BMC      │      │   Database   │     │
│  │   Loader     │─────▶│    Agent     │─────▶│   Adapter    │     │
│  │              │      │  (9 Blocks)  │      │              │     │
│  └──────────────┘      └──────────────┘      └──────────────┘     │
│         │                      │                      │             │
│         │                      │                      │             │
│    ┌────▼────┐            ┌───▼────┐            ┌───▼────┐        │
│    │ VPS v1  │            │ OpenAI │            │  vmp_  │        │
│    │ VPC 2.0 │            │ GPT-4  │            │projects│        │
│    │Personas │            │Prompts │            │        │        │
│    │Research │            │        │            │        │        │
│    └─────────┘            └────────┘            └────────┘        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Sequential Block Generation Flow

```
START: User requests BMC generation
  │
  ├─▶ Validate Prerequisites
  │   ├─ VPS v1 exists? ✓
  │   ├─ VPC 2.0 complete? ✓
  │   ├─ Personas identified? ✓
  │   └─ Context completeness > 0.5? ✓
  │
  ├─▶ Load Base Context
  │   ├─ VPS v1 (primary input)
  │   ├─ VPC 2.0 (customer profile + value map)
  │   ├─ Personas (all identified)
  │   ├─ Field Research (hypotheses, assumptions)
  │   └─ Market Evidence (PV report, insights, analysis)
  │
  ├─▶ BLOCK 1: Customer Segments
  │   │   Input: Base Context
  │   │   Process: AI Generation
  │   │   Output: 2-4 customer segments
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 2: Value Propositions
  │   │   Input: Base Context + Block 1
  │   │   Process: AI Generation
  │   │   Output: Value props per segment
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 3: Channels
  │   │   Input: Base Context + Blocks 1-2
  │   │   Process: AI Generation
  │   │   Output: Channels per segment
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 4: Customer Relationships
  │   │   Input: Base Context + Blocks 1-3
  │   │   Process: AI Generation
  │   │   Output: Relationship strategies
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 5: Revenue Streams
  │   │   Input: Base Context + Blocks 1-4
  │   │   Process: AI Generation
  │   │   Output: Revenue models per segment
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 6: Key Resources
  │   │   Input: Base Context + Blocks 1-5
  │   │   Process: AI Generation
  │   │   Output: Required resources
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 7: Key Activities
  │   │   Input: Base Context + Blocks 1-6
  │   │   Process: AI Generation
  │   │   Output: Critical activities
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 8: Key Partnerships
  │   │   Input: Base Context + Blocks 1-7
  │   │   Process: AI Generation
  │   │   Output: Strategic partnerships
  │   └─▶ Save to DB ✓
  │
  ├─▶ BLOCK 9: Cost Structure
  │   │   Input: Base Context + ALL Blocks 1-8
  │   │   Process: AI Generation
  │   │   Output: Complete cost structure
  │   └─▶ Save to DB ✓
  │
  └─▶ Return Complete BMC ✓

END: BMC generation complete
```

---

## 3. Context Accumulation Pattern

```
BLOCK 1: Customer Segments
┌─────────────────────────────────┐
│ Base Context:                   │
│ - VPS v1                        │
│ - VPC 2.0                       │
│ - Personas                      │
│ - Field Research                │
│ - Market Evidence               │
└─────────────────────────────────┘
         │
         ▼
    [Generate]
         │
         ▼
┌─────────────────────────────────┐
│ Output: Customer Segments       │
│ - seg-001: Primary Segment      │
│ - seg-002: Secondary Segment    │
└─────────────────────────────────┘

═══════════════════════════════════

BLOCK 2: Value Propositions
┌─────────────────────────────────┐
│ Base Context:                   │
│ - VPS v1                        │
│ - VPC 2.0                       │
│ - Personas                      │
│ - Field Research                │
│ - Market Evidence               │
│                                 │
│ + BLOCK 1:                      │
│   - seg-001: Primary Segment    │
│   - seg-002: Secondary Segment  │
└─────────────────────────────────┘
         │
         ▼
    [Generate]
         │
         ▼
┌─────────────────────────────────┐
│ Output: Value Propositions      │
│ - vp-001 → seg-001              │
│ - vp-002 → seg-002              │
└─────────────────────────────────┘

═══════════════════════════════════

BLOCK 3: Channels
┌─────────────────────────────────┐
│ Base Context                    │
│                                 │
│ + BLOCK 1: Customer Segments    │
│ + BLOCK 2: Value Propositions   │
└─────────────────────────────────┘
         │
         ▼
    [Generate]
         │
         ▼
┌─────────────────────────────────┐
│ Output: Channels                │
│ - ch-001 → seg-001, vp-001      │
└─────────────────────────────────┘

... Pattern continues for all 9 blocks ...

═══════════════════════════════════

BLOCK 9: Cost Structure
┌─────────────────────────────────┐
│ Base Context                    │
│                                 │
│ + BLOCK 1: Customer Segments    │
│ + BLOCK 2: Value Propositions   │
│ + BLOCK 3: Channels             │
│ + BLOCK 4: Customer Relations   │
│ + BLOCK 5: Revenue Streams      │
│ + BLOCK 6: Key Resources        │
│ + BLOCK 7: Key Activities       │
│ + BLOCK 8: Key Partnerships     │
└─────────────────────────────────┘
         │
         ▼
    [Generate]
         │
         ▼
┌─────────────────────────────────┐
│ Output: Cost Structure          │
│ - Costs driven by ALL blocks    │
└─────────────────────────────────┘
```

---

## 4. Cross-Referencing System

```
┌──────────────────────────────────────────────────────────────┐
│                    BMC CROSS-REFERENCES                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Customer Segments (Block 1)                                 │
│  ┌─────────────────────┐                                     │
│  │ seg-001, seg-002    │                                     │
│  └─────────────────────┘                                     │
│           │                                                   │
│           ├──────────────────────────────┐                   │
│           │                              │                   │
│           ▼                              ▼                   │
│  Value Propositions (Block 2)    Channels (Block 3)         │
│  ┌─────────────────────┐         ┌─────────────────────┐   │
│  │ vp-001 → seg-001    │         │ ch-001 → seg-001    │   │
│  │ vp-002 → seg-002    │         │ ch-002 → seg-002    │   │
│  └─────────────────────┘         └─────────────────────┘   │
│           │                              │                   │
│           └──────────────┬───────────────┘                   │
│                          │                                   │
│                          ▼                                   │
│           Customer Relationships (Block 4)                   │
│           ┌─────────────────────┐                           │
│           │ rel-001 → seg-001   │                           │
│           │ rel-002 → seg-002   │                           │
│           └─────────────────────┘                           │
│                          │                                   │
│                          ▼                                   │
│              Revenue Streams (Block 5)                       │
│              ┌─────────────────────┐                        │
│              │ rev-001 → seg-001   │                        │
│              │ rev-002 → seg-002   │                        │
│              └─────────────────────┘                        │
│                          │                                   │
│           ┌──────────────┴──────────────┐                   │
│           │                             │                   │
│           ▼                             ▼                   │
│  Key Resources (Block 6)    Key Activities (Block 7)       │
│  ┌─────────────────────┐    ┌─────────────────────┐       │
│  │ res-001 → vp-001    │    │ act-001 → vp-001    │       │
│  │ res-002 → ch-001    │    │ act-002 → ch-001    │       │
│  └─────────────────────┘    └─────────────────────┘       │
│           │                             │                   │
│           └──────────────┬──────────────┘                   │
│                          │                                   │
│                          ▼                                   │
│              Key Partnerships (Block 8)                      │
│              ┌─────────────────────┐                        │
│              │ part-001 → res-001  │                        │
│              │ part-002 → act-001  │                        │
│              └─────────────────────┘                        │
│                          │                                   │
│                          ▼                                   │
│               Cost Structure (Block 9)                       │
│               ┌─────────────────────┐                       │
│               │ cost-001 → res-001  │                       │
│               │ cost-002 → act-001  │                       │
│               │ cost-003 → part-001 │                       │
│               └─────────────────────┘                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Data Flow Through System

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA FLOW DIAGRAM                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  API Request                                                 │
│  POST /projects/{id}/bmc/generate                           │
│       │                                                       │
│       ▼                                                       │
│  ┌─────────────────────┐                                    │
│  │   BMC Service       │                                    │
│  │  (Orchestration)    │                                    │
│  └─────────────────────┘                                    │
│       │                                                       │
│       ├─▶ 1. Validate Prerequisites                         │
│       │      │                                               │
│       │      └─▶ MVP DB Adapter                             │
│       │             └─▶ Check VPS v1 exists                 │
│       │                                                       │
│       ├─▶ 2. Load Context                                   │
│       │      │                                               │
│       │      └─▶ BMC Context Loader                         │
│       │             ├─▶ VPM DB Adapter (VPC, Personas)      │
│       │             ├─▶ MVP DB Adapter (VPS v1)             │
│       │             └─▶ Vector Adapter (Market Evidence)    │
│       │                                                       │
│       ├─▶ 3. Generate Block 1                               │
│       │      │                                               │
│       │      └─▶ BMC Agent                                  │
│       │             ├─▶ Format Context                      │
│       │             ├─▶ Build Prompt                        │
│       │             ├─▶ Call OpenAI API                     │
│       │             ├─▶ Parse JSON Response                 │
│       │             └─▶ Validate Output                     │
│       │                    │                                 │
│       │                    └─▶ MVP DB Adapter (Save)        │
│       │                                                       │
│       ├─▶ 4. Generate Block 2 (with Block 1 context)       │
│       │      └─▶ [Same flow as Block 1]                     │
│       │                                                       │
│       ├─▶ 5-9. Generate Remaining Blocks                    │
│       │      └─▶ [Same flow, cumulative context]            │
│       │                                                       │
│       └─▶ 10. Return Complete BMC                           │
│              │                                               │
│              └─▶ API Response                               │
│                     │                                         │
│                     └─▶ Frontend                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Error Handling & Recovery

```
┌─────────────────────────────────────────────────────────────┐
│                   ERROR HANDLING FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Generate Block N                                            │
│       │                                                       │
│       ├─▶ Success? ─────────────────────┐                   │
│       │      │                           │                   │
│       │      YES                         NO                  │
│       │      │                           │                   │
│       │      ▼                           ▼                   │
│       │  Save Block N              Log Error                │
│       │      │                           │                   │
│       │      ▼                           ▼                   │
│       │  Continue to              Retry? (3 attempts)       │
│       │  Block N+1                      │                   │
│       │                           ┌─────┴─────┐             │
│       │                           │           │             │
│       │                          YES          NO            │
│       │                           │           │             │
│       │                           ▼           ▼             │
│       │                    Retry Block N   Save Partial    │
│       │                           │         BMC (Blocks    │
│       │                           │         1 to N-1)      │
│       │                           │              │         │
│       │                           └──────────────┘         │
│       │                                  │                  │
│       │                                  ▼                  │
│       │                          Return Error +            │
│       │                          Partial Results           │
│       │                                                     │
│       └─────────────────────────────────────────────────── │
│                                                               │
│  User Options After Partial Failure:                        │
│  1. Retry failed block                                      │
│  2. Manually edit and continue                              │
│  3. Regenerate from failed block                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Database Storage Structure

```
┌─────────────────────────────────────────────────────────────┐
│                  DATABASE STORAGE SCHEMA                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Table: vmp_projects                                         │
│  Column: mvp_data (JSONB)                                    │
│                                                               │
│  {                                                           │
│    "vps_v1": {                                              │
│      "primary_statement": "...",                            │
│      "extended_statement": "...",                           │
│      "key_differentiators": [...]                           │
│    },                                                        │
│                                                               │
│    "bmc": {                                                 │
│      "customer_segments": {                                 │
│        "segments": [                                        │
│          {                                                  │
│            "id": "seg-001",                                 │
│            "name": "...",                                   │
│            "description": "...",                            │
│            "characteristics": [...],                        │
│            "size_estimate": "...",                          │
│            "priority": "high",                              │
│            "evidence_source": "vpc_analysis",               │
│            "persona_mapping": ["P1"]                        │
│          }                                                  │
│        ],                                                   │
│        "generation_metadata": {...}                         │
│      },                                                      │
│                                                               │
│      "value_propositions": {...},                          │
│      "channels": {...},                                     │
│      "customer_relationships": {...},                       │
│      "revenue_streams": {...},                             │
│      "key_resources": {...},                               │
│      "key_activities": {...},                              │
│      "key_partnerships": {...},                            │
│      "cost_structure": {...},                              │
│                                                               │
│      "generation_metadata": {                               │
│        "generated_at": "2025-01-15T10:30:00Z",             │
│        "model_used": "gpt-4",                               │
│        "total_generation_time": 52.3,                       │
│        "context_completeness": 0.85,                        │
│        "version": "v1",                                     │
│        "block_generation_times": {                          │
│          "customer_segments": 5.2,                          │
│          "value_propositions": 6.1,                         │
│          "channels": 5.8,                                   │
│          ...                                                │
│        }                                                     │
│      }                                                       │
│    }                                                         │
│  }                                                           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. API Endpoint Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      API ENDPOINTS                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Generate BMC                                             │
│     POST /projects/{project_id}/bmc/generate                │
│     ┌─────────────────────────────────────┐                │
│     │ Request:                             │                │
│     │ {                                    │                │
│     │   "creativity_level": 0.7            │                │
│     │ }                                    │                │
│     └─────────────────────────────────────┘                │
│                    │                                         │
│                    ▼                                         │
│     ┌─────────────────────────────────────┐                │
│     │ Response:                            │                │
│     │ {                                    │                │
│     │   "bmc": {                           │                │
│     │     "customer_segments": {...},      │                │
│     │     ...all 9 blocks...               │                │
│     │   },                                 │                │
│     │   "project_id": "...",               │                │
│     │   "message": "BMC generated"         │                │
│     │ }                                    │                │
│     └─────────────────────────────────────┘                │
│                                                               │
│  2. Get BMC                                                  │
│     GET /projects/{project_id}/bmc                          │
│     └─▶ Returns existing BMC or 404                         │
│                                                               │
│  3. Update Block                                             │
│     PUT /projects/{project_id}/bmc/blocks/{block_name}      │
│     └─▶ Manual user edits                                   │
│                                                               │
│  4. Regenerate Block                                         │
│     POST /projects/{project_id}/bmc/blocks/{block_name}/    │
│          regenerate                                          │
│     └─▶ AI regeneration of specific block                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Complete BMC Canvas Visualization

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BUSINESS MODEL CANVAS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┬──────────────┬─────────────┬──────────────────────┐  │
│  │ Key          │ Key          │ Value       │ Customer             │  │
│  │ Partnerships │ Activities   │ Propositions│ Relationships        │  │
│  │              │              │             │                      │  │
│  │ Block 8      │ Block 7      │ Block 2     │ Block 4              │  │
│  │              │              │             │                      │  │
│  │ Who helps us │ What we do   │ What value  │ How we interact      │  │
│  │              │              │ we deliver  │                      │  │
│  │              ├──────────────┤             ├──────────────────────┤  │
│  │              │ Key          │             │ Channels             │  │
│  │              │ Resources    │             │                      │  │
│  │              │              │             │ Block 3              │  │
│  │              │ Block 6      │             │                      │  │
│  │              │              │             │ How we reach         │  │
│  │              │ What we need │             │ customers            │  │
│  ├──────────────┴──────────────┴─────────────┴──────────────────────┤  │
│  │                                                                    │  │
│  │                           Cost Structure                           │  │
│  │                                                                    │  │
│  │                              Block 9                               │  │
│  │                                                                    │  │
│  │                          What it costs                             │  │
│  └────────────────────────────────────────────────────────────────────┤
│                                                                           │
│                         Customer Segments (Block 1)                      │
│                                                                           │
│                            Who we serve                                  │
│                                                                           │
│                         Revenue Streams (Block 5)                        │
│                                                                           │
│                         How we make money                                │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**These visual diagrams provide a clear understanding of the BMC generation system architecture, data flow, and implementation approach!** 📊
