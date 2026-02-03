# BMC Implementation - Architecture Summary & Discussion Points

## 🎯 Core Architectural Decisions

### 1. **Sequential Generation with Cumulative Context**

**The Key Innovation**: Each BMC block is generated in order, with ALL previously generated blocks fed as context to the next generation.

```
Block 1: Customer Segments
  ↓ (Block 1 added to context)
Block 2: Value Propositions  
  ↓ (Blocks 1-2 added to context)
Block 3: Channels
  ↓ (Blocks 1-3 added to context)
...
Block 9: Cost Structure (has ALL 8 previous blocks in context)
```

**Why This Matters**:
- Each block can reference and build upon previous blocks
- Cost Structure (Block 9) has complete visibility of the entire business model
- Natural dependencies are respected (e.g., costs depend on resources/activities)
- Ensures consistency across all blocks

**Alternative Considered**: Parallel generation → Rejected because blocks are interdependent

---

### 2. **Context Reuse from VPS Implementation**

**Strategy**: Leverage existing `MVPContextLoader` that already loads:
- VPS v1 (primary input)
- VPC 2.0 (customer profile + value map)
- Personas
- Field research
- Market evidence (PV report, insights, analysis)

**New Addition**: `BMCContextLoader` extends this by:
- Validating VPS v1 exists (prerequisite)
- Formatting context for each specific block
- Adding previously generated blocks to context

**Why This Works**:
- No duplication of context loading logic
- Consistent data sources across MVP module
- Proven RAG patterns from VPS generation

---

### 3. **Agent Architecture Pattern**

**Following VPS Agent Pattern**:

```python
class BMCGenerationAgent:
    - Uses OpenAI GPT-4 (not mini) for complex reasoning
    - Temperature: 0.7 (balanced creativity)
    - Structured JSON output with strict schema
    - Evidence tracking for every element
    - Cross-referencing via IDs
```

**9 Generation Methods** (one per block):
- `generate_customer_segments(context)`
- `generate_value_propositions(context, customer_segments)`
- `generate_channels(context, customer_segments, value_propositions)`
- ... and so on

**Key Design Choice**: Separate method per block (not one giant method) for:
- Clear separation of concerns
- Easier testing per block
- Ability to regenerate individual blocks
- Better error isolation

---

### 4. **Database Storage Strategy**

**Location**: `vmp_projects.mvp_data` (JSONB column)

```json
{
  "vps_v1": {...},
  "bmc": {
    "customer_segments": {...},
    "value_propositions": {...},
    ...all 9 blocks...,
    "generation_metadata": {...}
  }
}
```

**Progressive Saving**: After each block generation, save progress to database
- Enables recovery if generation fails mid-way
- User can see partial results
- Reduces risk of losing work

---

### 5. **Prompt Engineering Strategy**

**Shared System Prompt** + **Block-Specific User Prompts**

**System Prompt** (all blocks):
- BMC framework explanation
- Evidence requirements
- VPS alignment rules
- Cross-referencing guidelines
- Real-world examples (Netflix, Vuba Vuba)

**User Prompts** (per block):
- Block-specific instructions
- JSON schema definition
- Context formatting
- Previous blocks integration

**Critical Elements**:
- Evidence source citation (mandatory)
- Specific data/numbers (not generic)
- Cross-references using IDs
- VPS v1 consistency checks

---

## 🤔 Key Discussion Points

### Discussion 1: Model Selection

**DECISION MADE**: Use **Azure OpenAI GPT-4** (not GPT-4-mini)

**Reasoning**:
- BMC requires complex business reasoning
- Need to synthesize 9 interconnected blocks
- Must maintain consistency across blocks
- VPS uses GPT-4-mini, but BMC is more complex
- **CRITICAL**: Must use Azure OpenAI service (consistent with all Yuba features)

**Status**: ✅ CONFIRMED - Azure OpenAI GPT-4 will be used

---

### Discussion 2: Block Granularity

**Proposal**: Generate multiple items per block (e.g., 3-5 customer segments)

**Reasoning**:
- Real businesses have multiple segments
- Provides options for user selection
- Richer, more complete BMC

**Question**: Should we:
- A) Generate fixed number (e.g., 3 segments, 5 channels)
- B) Generate variable number based on context
- C) Generate all, let user select/edit

---

### Discussion 3: Error Handling Strategy

**Scenario**: Block 5 generation fails after Blocks 1-4 succeed

**Options**:
1. **Save Progress**: Keep Blocks 1-4, allow retry of Block 5
2. **Rollback All**: Delete entire BMC, start over
3. **Hybrid**: Save progress, but mark BMC as "incomplete"

**Proposal**: Option 1 (Save Progress) with ability to regenerate any block

**Question**: Do we agree with this approach?

---

### Discussion 4: User Editing Capabilities

**Proposal**: Allow users to:
- Edit any block manually
- Regenerate any block with AI
- Keep manual edits when regenerating other blocks

**Implementation**:
- PUT endpoint for manual edits
- POST endpoint for AI regeneration
- Track which blocks are "user-edited" vs "AI-generated"

**Question**: Should regenerating Block 2 automatically regenerate Blocks 3-9 (cascade)?
- Pro: Maintains consistency
- Con: Loses user edits in later blocks

---

### Discussion 5: Context Window Management

**Challenge**: By Block 9, context includes:
- Base context (VPS, VPC, personas, research) ~5000 tokens
- Blocks 1-8 ~8000 tokens
- Total: ~13,000 tokens

**GPT-4 Context Limit**: 128K tokens (plenty of room)

**Question**: Do we need context optimization strategies, or is full context acceptable?

**Options**:
- A) Full context (all blocks verbatim)
- B) Summarized context (key points only)
- C) Selective context (only relevant blocks per generation)

---

### Discussion 6: Validation & Quality Checks

**Proposal**: Validate after each block:
- JSON schema compliance ✅
- Required fields present ✅
- Evidence sources cited ✅
- Cross-references valid ✅
- VPS v1 consistency ✅

**Question**: Should we add AI-powered quality checks?
- Example: "Does this value proposition align with VPS v1?"
- Pro: Higher quality output
- Con: Additional API calls, slower generation

---

### Discussion 7: Generation Time

**Estimate**: 
- Per block: 5-7 seconds
- Total (9 blocks): 45-63 seconds

**Question**: Is this acceptable, or do we need optimization?

**Optimization Options**:
- Reduce max_tokens per block
- Use GPT-4-mini for simpler blocks
- Parallel generation of independent blocks (risky)

---

### Discussion 8: Multi-Persona Handling

**Challenge**: Project may have 2 personas

**Options**:
1. **Unified BMC**: One BMC covering both personas (like VPS v1)
2. **Separate BMCs**: One BMC per persona
3. **Hybrid**: Shared blocks (1-5) + persona-specific blocks (6-9)

**Proposal**: Option 1 (Unified BMC) for consistency with VPS v1

**Question**: Do we agree with unified approach?

---

## 📋 Implementation Checklist

### Phase 1: Foundation
- [ ] Create folder structure
- [ ] Implement `BMCContextLoader`
- [ ] Extend database adapter (save/get/update methods)
- [ ] Write shared system prompt

### Phase 2: Agent Development
- [ ] Implement `BMCGenerationAgent` class
- [ ] Write 9 block-specific prompts
- [ ] Define JSON schemas for each block
- [ ] Test individual block generation

### Phase 3: Orchestration
- [ ] Implement `BMCService` class
- [ ] Add sequential generation logic
- [ ] Implement progressive saving
- [ ] Add error handling & recovery

### Phase 4: API & Integration
- [ ] Add API endpoints (generate, get, update, regenerate)
- [ ] Integration testing with VPS v1
- [ ] End-to-end testing
- [ ] Documentation

---

## 🎓 Learning from VPS Implementation

### What Worked Well in VPS:
✅ Structured JSON output with strict schema
✅ Evidence-based generation with source tracking
✅ Context loading via MVPContextLoader
✅ Progressive metadata tracking
✅ Clear separation: Agent → Service → API

### What to Improve for BMC:
🔄 Sequential generation (VPS was single-shot)
🔄 Progressive saving (VPS saves once at end)
🔄 Block-level regeneration (VPS regenerates entire VPS)
🔄 More complex cross-referencing (9 blocks vs 3 components)

---

## 🚀 Next Steps

1. **Review this plan** - Discuss architectural decisions
2. **Resolve discussion points** - Make final decisions on open questions
3. **Refine prompts** - Develop detailed prompts for each block
4. **Define schemas** - Create exact JSON schemas for structured output
5. **Start implementation** - Begin with Phase 1 (Foundation)

---

## 📊 Success Metrics

### Functional Success:
- ✅ Generates all 9 BMC blocks successfully
- ✅ Sequential context properly integrated
- ✅ Evidence-based, not generic
- ✅ Aligned with VPS v1
- ✅ Cross-references work correctly

### Quality Success:
- ✅ Specific, actionable insights (not generic advice)
- ✅ Grounded in research data
- ✅ Consistent across all blocks
- ✅ Professional business language
- ✅ Real-world applicability

### Technical Success:
- ✅ Total generation time < 60 seconds
- ✅ Individual block generation < 7 seconds
- ✅ Progressive saving works
- ✅ Error recovery functional
- ✅ API response times < 5 seconds

---

## 🎯 Critical Success Factors

1. **VPS v1 Quality**: BMC quality depends on VPS v1 quality (garbage in, garbage out)
2. **Context Richness**: More field research = better BMC
3. **Prompt Engineering**: Block prompts must be precise and comprehensive
4. **Sequential Logic**: Each block must properly use previous blocks
5. **Evidence Grounding**: Every element must cite real evidence

---

**Ready to discuss and refine this plan!** 🚀
