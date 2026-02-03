# Business Model Canvas (BMC) Generator - Implementation Plan

## Executive Summary

This document outlines the comprehensive implementation plan for the Business Model Canvas (BMC) Generator, the second feature of Module 3 (MVP Development). The BMC agent will generate a complete 9-block business model canvas using sequential AI-powered generation, where each block builds upon the previous ones with cumulative context enrichment.

---

## 1. ARCHITECTURE OVERVIEW

### 1.1 Sequential Generation Pattern

**CRITICAL DESIGN PRINCIPLE**: Each BMC block is generated sequentially in a **SINGLE API REQUEST**. The entire process happens in the background, and the complete BMC is returned once all 9 blocks are generated.

```
Single API Request → Background Processing → Complete BMC Response

Block 1: Customer Segments (1-3 items)
  Context: VPS v1 + VPC 2.0 + PV Report + Field Research + Market Research Analysis
  
Block 2: Value Propositions (2-6 items)
  Context: Previous Context + Customer Segments (Block 1)
  
Block 3: Channels (3-6 items)
  Context: Previous Context + Blocks 1-2
  
Block 4: Customer Relationships (2-6 items)
  Context: Previous Context + Blocks 1-3
  
Block 5: Revenue Streams (2-5 items)
  Context: Previous Context + Blocks 1-4
  
Block 6: Key Resources (3-6 items)
  Context: Previous Context + Blocks 1-5
  
Block 7: Key Activities (3-7 items)
  Context: Previous Context + Blocks 1-6
  
Block 8: Key Partnerships (3-9 items)
  Context: Previous Context + Blocks 1-7
  
Block 9: Cost Structure (4-9 cost categories)
  Context: Previous Context + ALL Blocks 1-8
```

### 1.2 Item Count Ranges (Based on Netflix & Vuba Vuba Examples)

**Reference**: `/Backend/src/mvp/docs/bmc.md` (Lines 124-271)

| Block | Min Items | Max Items | Typical |
|-------|-----------|-----------|---------|
| Customer Segments | 1 | 3 | 2 |
| Value Propositions | 2 | 5 | 3-4 |
| Channels | 3 | 6 | 4 |
| Customer Relationships | 2 | 4 | 3 |
| Revenue Streams | 2 | 5 | 3 |
| Key Resources | 3 | 6 | 4-5 |
| Key Activities | 3 | 7 | 5 |
| Key Partnerships | 3 | 6 | 4-5 |
| Cost Structure | 4 | 8 | 5-6 |

### 1.3 Core Components

```
Context Loader → BMC Agent (9 Sequential Blocks) → Database Storage
     ↓                    ↓                              ↓
  VPS v1         Azure OpenAI GPT-4            vmp_projects.mvp_data
  VPC 2.0           Structured Output          (JSONB column)
  Personas          Evidence-Based
  PV Report         Item Count Ranges
  Field Research    Real-world Examples
  Market Research   (Netflix, Vuba Vuba)
  Analysis Report
```

**CRITICAL**: All AI generation uses **Azure OpenAI** service, consistent with all Yuba platform features.

---

## 2. FOLDER STRUCTURE

```
/Backend/src/mvp/bmc/
├── __init__.py
├── agents/
│   ├── __init__.py
│   └── bmc_agent.py              # Main BMC generation agent
├── prompts/
│   ├── __init__.py
│   └── bmc_prompts.py            # All 9 block prompts
├── services/
│   ├── __init__.py
│   └── bmc_service.py            # Orchestration layer
├── utils/
│   ├── __init__.py
│   └── bmc_context_loader.py     # Context loading
└── BMC_IMPLEMENTATION_PLAN.md    # This file
```

---

## 3. COMPONENT SPECIFICATIONS

### 3.1 BMC Agent (`agents/bmc_agent.py`)

**Purpose**: AI-powered agent that generates each BMC block using **Azure OpenAI** with structured output.

**Key Methods**:

```python
class BMCGenerationAgent:
    """Agent for generating Business Model Canvas blocks sequentially."""
    
    def __init__(self, ai_provider: Optional[OpenAIProvider] = None):
        """
        Initialize with Azure OpenAI GPT-4 for complex business reasoning.
        
        CRITICAL: Uses Azure OpenAI service (consistent with all Yuba features)
        - Model: Azure OpenAI GPT-4 (not GPT-4-mini)
        - Temperature: 0.7 for balanced creativity
        - Max tokens: 3000 per block
        """
        
    async def generate_customer_segments(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 1: Customer Segments (1-3 items)
        
        Examples from bmc.md:
        - Netflix: 1 segment (Movies and online entertainment enthusiasts)
        - Vuba Vuba: 2 segments (Hungry people, Restaurant owners)
        
        Output Structure:
        {
            "segments": [
                {
                    "id": "seg-001",
                    "name": "Segment Name",
                    "description": "Detailed description",
                    "characteristics": ["trait1", "trait2"],
                    "size_estimate": "Market size",
                    "priority": "high|medium|low",
                    "evidence_source": "vpc_analysis|vps_v1|field_research|market_research_analysis",
                    "persona_mapping": ["P1", "P2"]
                }
            ],
            "generation_metadata": {...}
        }
        
        CRITICAL: Generate 1-3 segments max (typically 2)
        """
        
    async def generate_value_propositions(
        self,
        context: Dict[str, Any],
        customer_segments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 2: Value Propositions (2-5 items)
        
        Examples from bmc.md:
        - Netflix: 7 value props (24/7 on-demand, unlimited HD, no commercials, etc.)
        - Vuba Vuba: 6 value props (Fast delivery, online food court, etc.)
        
        CRITICAL: Generate 2-5 value propositions (typically 3-4)
        """
        
    async def generate_channels(
        self,
        context: Dict[str, Any],
        customer_segments: Dict[str, Any],
        value_propositions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 3: Channels (3-6 items)
        
        Examples from bmc.md:
        - Netflix: 6 channels (Any device, Netflix app, word of mouth, etc.)
        - Vuba Vuba: 4 channels (Mobile app, phone calls, social media, direct delivery)
        
        CRITICAL: Generate 3-6 channels (typically 4)
        """
        
    async def generate_customer_relationships(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 4: Customer Relationships (2-4 items)
        
        Examples from bmc.md:
        - Netflix: 3 relationships (Self-service, on-demand, ease of use)
        - Vuba Vuba: 3 relationships (Self-service with reviews, self-onboarding, support)
        
        CRITICAL: Generate 2-4 relationships (typically 3)
        """
        
    async def generate_revenue_streams(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 5: Revenue Streams (2-5 items)
        
        Examples from bmc.md:
        - Netflix: 5 streams (Subscription, advertising, partnerships, licensing, DVD)
        - Vuba Vuba: 3 streams (Delivery fees, surge pricing, commission)
        
        CRITICAL: Generate 2-5 revenue streams (typically 3)
        """
        
    async def generate_key_resources(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 6: Key Resources (3-6 items)
        
        Examples from bmc.md:
        - Netflix: 5 resources (Brand, app/website, platform, employees, film makers)
        - Vuba Vuba: 4 resources (Brand, tech platforms, customer base, restaurant network)
        
        CRITICAL: Generate 3-6 resources (typically 4-5)
        """
        
    async def generate_key_activities(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 7: Key Activities (3-7 items)
        
        Examples from bmc.md:
        - Netflix: 6 activities (Tech & R&D, licensing, production, distribution, analytics, marketing)
        - Vuba Vuba: 5 activities (Logistics, platform dev, marketing, support, order generation)
        
        CRITICAL: Generate 3-7 activities (typically 5)
        """
        
    async def generate_key_partnerships(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 8: Key Partnerships (3-6 items)
        
        Examples from bmc.md:
        - Netflix: 8 partners (Investors, producers, guilds, theaters, AWS, electronics, ISPs)
        - Vuba Vuba: 5 partners (Restaurants, tech providers, payment processors, map APIs, riders)
        
        CRITICAL: Generate 3-6 partnerships (typically 4-5)
        """
        
    async def generate_cost_structure(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 9: Cost Structure (4-8 cost categories)
        
        Examples from bmc.md:
        - Netflix: 6 costs (Production, R&D, infrastructure, licensing, marketing, payment fees)
        - Vuba Vuba: 5 costs (Office rentals, rider wages, staffing, marketing, payment fees)
        
        CRITICAL: Generate 4-8 cost categories (typically 5-6)
        """
```

**Design Decisions**:
- Model: **Azure OpenAI GPT-4** (complex business reasoning required)
- Temperature: 0.7 (balanced creativity/consistency)
- Structured Output: Azure OpenAI JSON schema with strict mode
- Evidence Tracking: Every item cites evidence source
- Cross-Referencing: Use IDs to link elements
- **CRITICAL**: Use Azure OpenAI service (consistent with all Yuba features)

---

### 3.2 BMC Context Loader (`utils/bmc_context_loader.py`)

**Purpose**: Load and prepare all context data needed for BMC generation.

**Key Methods**:

```python
class BMCContextLoader:
    """Load context data for BMC generation."""
    
    def __init__(self, vpm_db_adapter, vector_adapter, mvp_db_adapter):
        """Initialize with adapters."""
        self.mvp_context_loader = MVPContextLoader(vpm_db_adapter, vector_adapter)
        self.mvp_db_adapter = mvp_db_adapter
        
    async def load_bmc_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Load all context needed for BMC generation.
        
        Returns:
        {
            "project_id": str,
            "vps_v1": {...},           # REQUIRED
            "customer_profile": {...},
            "value_map": {...},
            "personas": [...],
            "hypotheses": [...],
            "assumptions": [...],
            "pv_report_insights": [...],
            "actionable_insights": [...],
            "market_research_analysis": [...],  # CRITICAL: Multi-persona analysis chunks
            "context_completeness": float
        }
        
        CRITICAL: Market research analysis report chunks MUST be included
        in context, same as VPS implementation. This provides validated
        customer insights, pain/gain analysis, and market opportunities.
        """
        
    def format_context_for_block(
        self,
        context: Dict[str, Any],
        block_name: str,
        previous_blocks: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format context for specific BMC block.
        
        Includes:
        - Base context (VPS, VPC, personas, research)
        - Previously generated blocks (sequential context)
        """
```

**Context Strategy**:
1. Reuse `MVPContextLoader.load_vps_context()`
2. Add VPS v1 as primary input
3. Validate VPS v1 exists
4. Format block-specific context
5. Include previous blocks for sequential generation

---

### 3.3 BMC Service (`services/bmc_service.py`)

**Purpose**: Orchestration layer coordinating sequential generation of all 9 blocks.

**Key Methods**:

```python
class BMCService:
    """Service for BMC generation orchestration."""
    
    async def generate_bmc(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate complete BMC sequentially.
        
        Workflow:
        1. Validate VPS v1 exists
        2. Load context
        3. Generate Block 1 → Save
        4. Generate Block 2 (with Block 1) → Save
        5. Generate Block 3 (with Blocks 1-2) → Save
        ... Continue for all 9 blocks
        9. Return complete BMC
        """
        
    async def get_bmc(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get existing BMC."""
        
    async def update_bmc_block(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update specific block (user edits)."""
        
    async def regenerate_bmc_block(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        block_name: str
    ) -> Dict[str, Any]:
        """Regenerate specific block with AI."""
```

---

### 3.4 BMC Prompts (`prompts/bmc_prompts.py`)

**Purpose**: Comprehensive prompt templates for each BMC block.

**Structure**:

```python
# System prompt (shared across all blocks)
BMC_SYSTEM_PROMPT = """
You are an expert business model strategist specializing in BMC framework.

UNDERSTANDING BMC:
- 9 interconnected blocks
- Evidence-based generation
- VPS v1 alignment required
- VPC 2.0 integration
- Sequential context usage

CRITICAL RULES:
- Cite evidence sources
- Use specific data/numbers
- Link elements via IDs
- Maintain VPS consistency
- Ground in VPC framework
"""

# Block-specific prompts
CUSTOMER_SEGMENTS_PROMPT = """..."""
VALUE_PROPOSITIONS_PROMPT = """..."""
CHANNELS_PROMPT = """..."""
CUSTOMER_RELATIONSHIPS_PROMPT = """..."""
REVENUE_STREAMS_PROMPT = """..."""
KEY_RESOURCES_PROMPT = """..."""
KEY_ACTIVITIES_PROMPT = """..."""
KEY_PARTNERSHIPS_PROMPT = """..."""
COST_STRUCTURE_PROMPT = """..."""

# Formatting functions for each block
def format_customer_segments_prompt(context: str) -> str:
    """Format prompt for Block 1."""
    
def format_value_propositions_prompt(
    context: str, 
    customer_segments: str
) -> str:
    """Format prompt for Block 2 with Block 1 context."""
```

**Prompt Principles**:
- Structured JSON output
- Evidence requirements
- Real-world examples (Netflix, Vuba Vuba)
- Cross-referencing guidelines
- Specificity over generality

---

## 4. DATABASE INTEGRATION

### 4.1 Storage

**Table**: `vmp_projects`
**Column**: `mvp_data` (JSONB)

```json
{
  "vps_v1": {...},
  "bmc": {
    "customer_segments": {...},
    "value_propositions": {...},
    "channels": {...},
    "customer_relationships": {...},
    "revenue_streams": {...},
    "key_resources": {...},
    "key_activities": {...},
    "key_partnerships": {...},
    "cost_structure": {...},
    "generation_metadata": {
      "generated_at": "ISO timestamp",
      "model_used": "gpt-4",
      "total_time": 45.2,
      "version": "v1"
    }
  }
}
```

### 4.2 Adapter Methods

Extend `src/mvp/adapters/database_adapter.py`:

```python
def save_bmc(project_id, tenant_id, bmc_data, user_id) -> bool
def get_bmc(project_id, tenant_id) -> Optional[Dict]
def update_bmc_block(project_id, tenant_id, block_name, data, user_id) -> bool
def save_bmc_progress(project_id, tenant_id, partial_bmc) -> bool
```

---

## 5. API ENDPOINTS

Extend `src/mvp/api/endpoints.py`:

```python
# ==================== GENERATION ====================

@router.post("/projects/{project_id}/bmc/generate")
async def generate_bmc(
    project_id: str,
    creativity_level: float = 0.7,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate complete BMC in SINGLE API REQUEST.
    
    Process:
    - Runs in background
    - Generates all 9 blocks sequentially
    - Returns complete BMC when done
    
    Prerequisites:
    - VPS v1 must exist
    - VPC 2.0 must be completed
    - Personas must be identified
    
    Response Time: ~45-60 seconds (all 9 blocks)
    
    Returns:
    {
        "bmc": {
            "customer_segments": {...},      # 1-3 items
            "value_propositions": {...},     # 2-5 items
            "channels": {...},               # 3-6 items
            "customer_relationships": {...}, # 2-4 items
            "revenue_streams": {...},        # 2-5 items
            "key_resources": {...},          # 3-6 items
            "key_activities": {...},         # 3-7 items
            "key_partnerships": {...},       # 3-6 items
            "cost_structure": {...},         # 4-8 items
            "generation_metadata": {...}
        },
        "project_id": "...",
        "message": "BMC generated successfully"
    }
    """

# ==================== RETRIEVAL ====================

@router.get("/projects/{project_id}/bmc")
async def get_bmc(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get existing BMC for a project.
    
    Returns:
    - Complete BMC if exists
    - 404 if not generated yet
    """

# ==================== EDITING ====================

@router.put("/projects/{project_id}/bmc/blocks/{block_name}")
async def update_bmc_block(
    project_id: str,
    block_name: str,
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Update specific BMC block (manual user edits).
    
    Block names:
    - customer_segments
    - value_propositions
    - channels
    - customer_relationships
    - revenue_streams
    - key_resources
    - key_activities
    - key_partnerships
    - cost_structure
    
    Request body:
    {
        "segments": [...],  # For customer_segments
        "propositions": [...],  # For value_propositions
        # ... etc for other blocks
    }
    
    OR wrapped format:
    {
        "data": {
            "segments": [...]
        }
    }
    """

@router.post("/projects/{project_id}/bmc/blocks/{block_name}/items")
async def add_bmc_block_item(
    project_id: str,
    block_name: str,
    item: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Add new item to specific BMC block.
    
    Example for customer_segments:
    {
        "name": "New Segment",
        "description": "...",
        "characteristics": [...],
        "size_estimate": "...",
        "priority": "medium",
        "evidence_source": "field_research",
        "persona_mapping": ["P1"]
    }
    
    System will:
    - Validate item count doesn't exceed max
    - Assign sequential ID (e.g., seg-004)
    - Add to existing block
    - Return updated block
    """

@router.delete("/projects/{project_id}/bmc/blocks/{block_name}/items/{item_id}")
async def delete_bmc_block_item(
    project_id: str,
    block_name: str,
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete specific item from BMC block.
    
    Validates:
    - Item exists
    - Minimum count not violated (e.g., can't delete last customer segment)
    
    Returns updated block after deletion.
    """

@router.put("/projects/{project_id}/bmc/blocks/{block_name}/items/{item_id}")
async def edit_bmc_block_item(
    project_id: str,
    block_name: str,
    item_id: str,
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Edit specific item within BMC block.
    
    Allows partial updates (only changed fields).
    
    Example:
    {
        "name": "Updated Segment Name",
        "priority": "high"
    }
    """

# ==================== REGENERATION ====================

@router.post("/projects/{project_id}/bmc/blocks/{block_name}/regenerate")
async def regenerate_bmc_block(
    project_id: str,
    block_name: str,
    creativity_level: float = 0.7,
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate specific BMC block using AI.
    
    Uses current context + all previous blocks.
    Replaces entire block with new AI-generated content.
    
    Use cases:
    - User wants different options
    - Context has changed (new research)
    - User wants to try different creativity level
    """
```

---

## 6. CONTEXT ENRICHMENT

### 6.1 Base Context (All Blocks)

**Sources** (Reference: `/Backend/src/mvp/docs/bmc.md`):
1. **VPS v1** (primary statement, extended, differentiators) - REQUIRED
2. **VPC 2.0** (customer profile + value map)
3. **Personas** (all identified personas with evidence)
4. **Field Research** (hypotheses, assumptions, validation results)
5. **Market Evidence**:
   - PV report insights (vector search)
   - Actionable insights (vector search)
   - **Market Research Analysis Report** (vector search) - CRITICAL
     * Multi-persona analysis chunks
     * Customer insights and pain/gain analysis
     * Market opportunities and validation data
     * Same integration as VPS implementation

**Real-World Examples** (from bmc.md):
- Netflix BMC (1 segment, 7 value props, 6 channels, etc.)
- Vuba Vuba BMC (2 segments, 6 value props, 4 channels, etc.)

### 6.2 Sequential Addition

- Block 1 → Block 2: Add Customer Segments
- Block 2 → Block 3: Add Value Propositions
- Block 3 → Block 4: Add Channels
- Block 4 → Block 5: Add Customer Relationships
- Block 5 → Block 6: Add Revenue Streams
- Block 6 → Block 7: Add Key Resources
- Block 7 → Block 8: Add Key Activities
- Block 8 → Block 9: Add Key Partnerships
- Block 9: Has ALL previous 8 blocks

---

## 7. VALIDATION & QUALITY

### 7.1 Prerequisites

- ✅ VPS v1 must exist
- ✅ VPC 2.0 completed
- ✅ Personas identified
- ✅ Context completeness > 0.5

### 7.2 Output Validation

- JSON schema compliance
- Required fields present
- Evidence sources cited
- Cross-references valid
- Consistency with VPS v1

### 7.3 Error Handling

- Graceful failures per block
- Progress saving after each block
- Retry logic for API failures
- Detailed error logging

---

## 8. IMPLEMENTATION PHASES

### Phase 1: Foundation (Week 1)
- Create folder structure
- Implement BMCContextLoader
- Extend database adapter
- Write system prompt

### Phase 2: Core Agent (Week 2)
- Implement BMCGenerationAgent
- Write all 9 block prompts
- Add JSON schemas
- Test individual blocks

### Phase 3: Orchestration (Week 3)
- Implement BMCService
- Add sequential generation logic
- Implement progress saving
- Add error handling

### Phase 4: API & Testing (Week 4)
- Add API endpoints
- Integration testing
- End-to-end testing
- Documentation

---

## 9. SUCCESS CRITERIA

### 9.1 Functional
- ✅ Generates all 9 BMC blocks
- ✅ Sequential context works
- ✅ Evidence-based output
- ✅ VPS v1 alignment
- ✅ Cross-references valid

### 9.2 Quality
- ✅ Specific, not generic
- ✅ Grounded in research
- ✅ Consistent across blocks
- ✅ Professional tone
- ✅ Actionable insights

### 9.3 Technical
- ✅ < 60s total generation time
- ✅ Progress saved per block
- ✅ Error recovery works
- ✅ API responses < 5s
- ✅ Database queries optimized

---

## 10. NEXT STEPS

1. **Review & Refine**: Discuss this plan, identify gaps
2. **Prompt Engineering**: Develop detailed prompts for each block
3. **Schema Design**: Define exact JSON schemas
4. **Implementation**: Start with Phase 1
5. **Iteration**: Test and refine based on results

---

## APPENDIX: BMC BLOCK DETAILS

### Block 1: Customer Segments
- Who are we creating value for?
- Multiple segments possible
- Link to personas
- Evidence from VPC customer profile

### Block 2: Value Propositions
- What value do we deliver?
- One per customer segment
- Must align with VPS v1
- Show VPC fit (jobs/pains/gains)

### Block 3: Channels
- How do we reach customers?
- Awareness → Purchase → Delivery → After-sales
- Digital + Physical
- Segment-specific

### Block 4: Customer Relationships
- How do we interact?
- Acquisition + Retention + Growth
- Personal vs Automated
- Segment-specific

### Block 5: Revenue Streams
- How do we make money?
- Pricing mechanisms
- Revenue models
- Segment-specific

### Block 6: Key Resources
- What assets do we need?
- Physical, Intellectual, Human, Financial
- Required for value props
- Required for channels

### Block 7: Key Activities
- What must we do?
- Production, Problem-solving, Platform
- Required for value props
- Required for channels

### Block 8: Key Partnerships
- Who helps us?
- Strategic alliances, Suppliers
- Optimization, Risk reduction, Resource acquisition
- Support activities/resources

### Block 9: Cost Structure
- What are our costs?
- Fixed vs Variable
- Driven by resources/activities/partnerships
- Cost-driven vs Value-driven model
