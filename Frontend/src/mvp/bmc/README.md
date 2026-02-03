# Business Model Canvas (BMC) Generator - Documentation Index

## 📚 Documentation Overview

This folder contains the complete implementation plan for the BMC Generator, the second feature of Module 3 (MVP Development) in the Yuba platform.

---

## 📄 Documents

### 1. **BMC_IMPLEMENTATION_PLAN.md** (Main Document)
**Purpose**: Comprehensive technical implementation plan

**Contents**:
- Architecture overview
- Folder structure
- Component specifications (Agent, Service, Context Loader, Prompts)
- Database integration strategy
- API endpoints design
- Context enrichment approach
- Validation & quality assurance
- Implementation phases
- Success criteria

**Read this first** for complete technical understanding.

---

### 2. **BMC_ARCHITECTURE_SUMMARY.md** (Discussion Guide)
**Purpose**: Key architectural decisions and discussion points

**Contents**:
- Core architectural decisions explained
- 8 key discussion points requiring team input
- Implementation checklist
- Learning from VPS implementation
- Success metrics
- Critical success factors

**Use this** for team discussions and decision-making.

---

### 3. **BMC_PROMPT_STRATEGY.md** (Prompt Engineering)
**Purpose**: Detailed prompt engineering approach

**Contents**:
- Three-layer prompt architecture
- Shared system prompt
- Block-specific prompt templates
- Context formatting strategy
- Prompt engineering best practices
- Testing strategy
- Continuous improvement approach

**Reference this** when developing prompts for each BMC block.

---

### 4. **README.md** (This File)
**Purpose**: Navigation and quick reference

---

## 🎯 Quick Start Guide

### For Developers Starting Implementation:

1. **Read First**: `BMC_IMPLEMENTATION_PLAN.md` (Sections 1-3)
   - Understand the sequential generation pattern
   - Review component architecture
   - Understand folder structure

2. **Discuss**: `BMC_ARCHITECTURE_SUMMARY.md` (Discussion Points)
   - Review 8 key decisions with team
   - Resolve open questions
   - Align on approach

3. **Reference**: `BMC_PROMPT_STRATEGY.md`
   - When writing prompts
   - When defining JSON schemas
   - When formatting context

4. **Implement**: Follow phases in `BMC_IMPLEMENTATION_PLAN.md` (Section 8)
   - Phase 1: Foundation
   - Phase 2: Core Agent
   - Phase 3: Orchestration
   - Phase 4: API & Testing

---

## 🏗️ Architecture at a Glance

### 1. Single API Request - Background Processing

```
POST /bmc/generate → Background Processing (45-60s) → Complete BMC Response

VPS v1 (Required) → Load Context → Generate Block 1 (1-3 items)
                                         ↓
                                    Block 1 Context
                                         ↓
                                  Generate Block 2 (2-5 items)
                                         ↓
                                  Blocks 1-2 Context
                                         ↓
                                  Generate Block 3 (3-6 items)
                                         ↓
                                       ...
                                         ↓
                                  Blocks 1-8 Context
                                         ↓
                                  Generate Block 9 (4-8 items)
                                         ↓
                                  Complete BMC (All 9 blocks)
```

### 2. The 9 BMC Blocks with Item Ranges

**Reference**: `/Backend/src/mvp/docs/bmc.md` (Netflix & Vuba Vuba examples)

**Customer-Facing (Right Side)**:
1. Customer Segments (1-3 items) - WHO we serve
2. Value Propositions (2-5 items) - WHAT value we deliver
3. Channels (3-6 items) - HOW we reach customers
4. Customer Relationships (2-4 items) - HOW we interact
5. Revenue Streams (2-5 items) - HOW we make money

**Infrastructure (Left Side)**:
6. Key Resources (3-6 items) - WHAT we need
7. Key Activities (3-7 items) - WHAT we do
8. Key Partnerships (3-6 items) - WHO helps us

**Financial (Bottom)**:
9. Cost Structure (4-8 items) - WHAT it costs

---

## 🔑 Key Design Principles

### 1. Sequential Generation
Each block builds on previous blocks. Block 9 has ALL previous 8 blocks in context.

### 2. Evidence-Based
Every element must cite evidence source (VPS, VPC, field research, market research analysis).

### 3. VPS Alignment
BMC must be fully consistent with the generated VPS v1.

### 4. Context Reuse
Leverage existing `MVPContextLoader` from VPS implementation, including market research analysis report chunks.

### 5. Single API Request
All 9 blocks generated in one API call (~45-60s), complete BMC returned when done.

### 6. Item Count Ranges
Each block has min/max items based on Netflix & Vuba Vuba examples (see bmc.md).

### 7. Edit & Add Support
Full CRUD operations: add items, edit items, delete items, regenerate blocks.

---

## 📊 Component Overview

### BMCGenerationAgent (`agents/bmc_agent.py`)
- 9 generation methods (one per block)
- Uses **Azure OpenAI GPT-4** with structured JSON output
- Evidence tracking and cross-referencing
- Item count validation (min/max ranges)
- Temperature: 0.7
- **CRITICAL**: Azure OpenAI service (consistent with all Yuba features)

### BMCService (`services/bmc_service.py`)
- Orchestrates sequential generation in single API request
- Handles error recovery
- Progressive saving after each block
- Block-level regeneration
- Item-level CRUD operations

### BMCContextLoader (`utils/bmc_context_loader.py`)
- Extends MVPContextLoader
- Validates VPS v1 exists
- Includes market research analysis report chunks
- Formats context per block
- Adds previous blocks to context

### BMC Prompts (`prompts/bmc_prompts.py`)
- Shared system prompt with bmc.md examples
- 9 block-specific prompts with item ranges
- JSON schemas for structured output
- Netflix & Vuba Vuba real-world examples

---

## 🔌 API Endpoints

### Generation
- `POST /projects/{id}/bmc/generate` - Generate complete BMC (single request, ~45-60s)

### Retrieval
- `GET /projects/{id}/bmc` - Get existing BMC

### Block-Level Editing
- `PUT /projects/{id}/bmc/blocks/{block_name}` - Update entire block
- `POST /projects/{id}/bmc/blocks/{block_name}/regenerate` - Regenerate block with AI

### Item-Level Editing
- `POST /projects/{id}/bmc/blocks/{block_name}/items` - Add new item to block
- `PUT /projects/{id}/bmc/blocks/{block_name}/items/{item_id}` - Edit specific item
- `DELETE /projects/{id}/bmc/blocks/{block_name}/items/{item_id}` - Delete specific item

---

## 🎓 Learning from VPS Implementation

### What We're Keeping:
✅ Structured JSON output with strict schema
✅ Evidence-based generation
✅ Context loading via MVPContextLoader
✅ Clear separation: Agent → Service → API
✅ Progressive metadata tracking

### What We're Improving:
🔄 Sequential generation (VPS was single-shot)
🔄 Progressive saving (VPS saves once at end)
🔄 Block-level regeneration (VPS regenerates entire VPS)
🔄 More complex cross-referencing (9 blocks vs 3 components)

---

## ⚠️ Critical Prerequisites

Before BMC generation can start:
- ✅ VPS v1 must be generated
- ✅ VPC 2.0 must be completed
- ✅ Personas must be identified
- ✅ Context completeness > 0.5

---

## 🚀 Implementation Timeline

### Week 1: Foundation
- Create folder structure
- Implement BMCContextLoader
- Extend database adapter
- Write system prompt

### Week 2: Core Agent
- Implement BMCGenerationAgent
- Write all 9 block prompts
- Define JSON schemas
- Test individual blocks

### Week 3: Orchestration
- Implement BMCService
- Add sequential generation logic
- Implement progressive saving
- Add error handling

### Week 4: API & Testing
- Add API endpoints
- Integration testing
- End-to-end testing
- Documentation

---

## 📈 Success Metrics

### Functional:
- ✅ Generates all 9 BMC blocks
- ✅ Sequential context works
- ✅ Evidence-based output
- ✅ VPS v1 alignment
- ✅ Cross-references valid

### Quality:
- ✅ Specific, not generic
- ✅ Grounded in research
- ✅ Consistent across blocks
- ✅ Professional language
- ✅ Actionable insights

### Technical:
- ✅ Total time < 60 seconds
- ✅ Per block < 7 seconds
- ✅ Progressive saving works
- ✅ Error recovery functional
- ✅ API responses < 5 seconds

---

## 🤔 Open Questions (See Architecture Summary)

1. Model selection (GPT-4 vs GPT-4-mini)
2. Block granularity (fixed vs variable items)
3. Error handling strategy (save progress vs rollback)
4. User editing capabilities (cascade regeneration?)
5. Context window management (full vs summarized)
6. Validation approach (schema only vs AI quality checks)
7. Generation time optimization
8. Multi-persona handling (unified vs separate BMCs)

**→ Discuss these in team meeting using BMC_ARCHITECTURE_SUMMARY.md**

---

## 📞 Next Steps

1. **Team Review**: Schedule meeting to discuss architecture summary
2. **Decision Making**: Resolve 8 open questions
3. **Prompt Development**: Start writing detailed prompts
4. **Schema Definition**: Define exact JSON schemas
5. **Implementation**: Begin Phase 1 (Foundation)

---

## 🔗 Related Documentation

- **VPS Implementation**: `/Backend/src/mvp/agents/vps_agent.py`
- **VPS Prompts**: `/Backend/src/mvp/prompts/vps_prompts.py`
- **Context Loader**: `/Backend/src/mvp/utils/context_loader.py`
- **MVP Database Adapter**: `/Backend/src/mvp/adapters/database_adapter.py`
- **BMC Reference**: `/Backend/src/mvp/docs/bmc.md`

---

## 💡 Key Insights

### Why Sequential Generation?
BMC blocks are interdependent. Cost Structure (Block 9) depends on Resources (Block 6), Activities (Block 7), and Partnerships (Block 8). Sequential generation ensures each block can reference and build upon previous blocks, creating a cohesive business model.

### Why Evidence-Based?
Generic BMCs are useless. By requiring evidence citations, we ensure every element is grounded in actual research data, validated assumptions, and real market insights. This makes the BMC actionable and credible.

### Why VPS Alignment?
The VPS v1 is the strategic foundation. The BMC operationalizes that strategy. If they're misaligned, the business model won't deliver on the value proposition. Alignment is critical for coherence.

### Why Progressive Saving?
Generating 9 blocks takes 45-60 seconds. If generation fails at Block 7, we don't want to lose Blocks 1-6. Progressive saving enables recovery and lets users see partial results.

---

## 🎯 Vision

**The BMC Generator will transform validated market research and value propositions into a complete, evidence-based, actionable business model canvas that entrepreneurs can immediately use to build and scale their ventures.**

---

**Ready to build! 🚀**

For questions or clarifications, refer to the specific documentation files above.
