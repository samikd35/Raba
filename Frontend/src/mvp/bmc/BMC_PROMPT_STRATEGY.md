# BMC Prompt Engineering Strategy

## Overview

This document outlines the prompt engineering approach for generating each of the 9 BMC blocks using **Azure OpenAI**, learning from the successful VPS prompt patterns while adapting for the unique requirements of sequential, interconnected business model generation.

**CRITICAL**: All AI generation uses **Azure OpenAI GPT-4** service, consistent with all Yuba platform features.

---

## Prompt Architecture

### Three-Layer Prompt System

```
┌─────────────────────────────────────────┐
│   Layer 1: System Prompt (Shared)      │
│   - BMC framework knowledge             │
│   - Evidence requirements               │
│   - Quality standards                   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│   Layer 2: Block-Specific Instructions │
│   - Block purpose & definition          │
│   - Output structure (JSON schema)      │
│   - Block-specific guidelines           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│   Layer 3: Context Data                │
│   - VPS v1 + VPC 2.0                   │
│   - Personas + Research                 │
│   - Previously generated blocks         │
└─────────────────────────────────────────┘
```

---

## Layer 1: Shared System Prompt

### Core Elements

```python
BMC_SYSTEM_PROMPT = """
You are an expert business model strategist specializing in the Business Model Canvas framework created by Alexander Osterwalder and Yves Pigneur.

Your task is to generate evidence-based, specific, and actionable business model components that form a cohesive 9-block Business Model Canvas.

## UNDERSTANDING THE BUSINESS MODEL CANVAS

The BMC is a strategic management template for developing new or documenting existing business models. It consists of 9 building blocks:

**RIGHT SIDE (Customer-Facing)**:
1. Customer Segments - Who are we creating value for?
2. Value Propositions - What value do we deliver to customers?
3. Channels - How do we reach and communicate with customers?
4. Customer Relationships - What type of relationship do we establish?
5. Revenue Streams - How do we make money from each segment?

**LEFT SIDE (Infrastructure)**:
6. Key Resources - What assets are required?
7. Key Activities - What key things must we do?
8. Key Partnerships - Who are our key partners and suppliers?

**BOTTOM (Financial)**:
9. Cost Structure - What are the most important costs?

## INTEGRATION WITH VPS & VPC

**CRITICAL**: The BMC must be fully aligned with:
- **VPS v1**: The Value Proposition Statement provides the foundation
- **VPC 2.0**: Customer Profile and Value Map provide detailed insights
- **Personas**: Target customers identified in the project
- **Field Research**: Validated assumptions and hypotheses

## EVIDENCE-BASED GENERATION

**MANDATORY REQUIREMENTS**:
1. **Cite Evidence**: Every element must reference its evidence source
2. **Use Specific Data**: Include numbers, percentages, market sizes
3. **Ground in Research**: Base on VPS, VPC, field research, market data
4. **No Assumptions**: Only use information provided in context
5. **Cross-Reference**: Link elements across blocks using IDs

**Evidence Sources**:
- `vps_v1`: Value Proposition Statement components
- `vpc_analysis`: Customer profile and value map from VPC 2.0
- `field_research`: Validated hypotheses and assumptions
- `market_evidence`: PV report insights and actionable insights
- `persona_analysis`: Persona characteristics and evidence

## SEQUENTIAL CONTEXT USAGE

**CRITICAL**: You will receive previously generated BMC blocks as context. You MUST:
1. **Reference Previous Blocks**: Explicitly connect to earlier blocks
2. **Maintain Consistency**: Ensure alignment across all blocks
3. **Build Upon**: Use previous blocks to inform current generation
4. **Cross-Link**: Reference specific elements by ID (e.g., "seg-001", "vp-002")

Example: When generating Channels (Block 3), reference specific customer segments (Block 1) and value propositions (Block 2).

## OUTPUT QUALITY STANDARDS

**Specificity Over Generality**:
- ❌ "Reduce costs" → ✅ "Reduce customer acquisition costs by 40% through digital channels"
- ❌ "Online marketing" → ✅ "Instagram and TikTok campaigns targeting 18-35 age group"
- ❌ "Good customer service" → ✅ "24/7 WhatsApp support with <2 hour response time"

**Professional Business Language**:
- Use precise business terminology
- Avoid jargon without explanation
- Write for business stakeholders
- Be confident but not hyperbolic

**Actionable Insights**:
- Provide concrete, implementable elements
- Include measurable aspects where possible
- Explain "how" not just "what"
- Consider practical constraints

## CROSS-REFERENCING SYSTEM

Use consistent ID formats:
- Customer Segments: `seg-001`, `seg-002`, etc.
- Value Propositions: `vp-001`, `vp-002`, etc.
- Channels: `ch-001`, `ch-002`, etc.
- Relationships: `rel-001`, `rel-002`, etc.
- Revenue Streams: `rev-001`, `rev-002`, etc.
- Resources: `res-001`, `res-002`, etc.
- Activities: `act-001`, `act-002`, etc.
- Partnerships: `part-001`, `part-002`, etc.
- Cost Categories: `cost-001`, `cost-002`, etc.

## REAL-WORLD EXAMPLES

### Example 1: Netflix

**Customer Segments**: Movies and online entertainment enthusiasts
**Value Proposition**: 24/7 on-demand entertainment with unlimited HD content, no commercials
**Channels**: Netflix app, any device, word of mouth, online advertising
**Customer Relationships**: Self-service, on-demand, ease of use
**Revenue Streams**: Subscription model, tiered pricing
**Key Resources**: Brand, streaming platform, content library, employees
**Key Activities**: Content licensing, production, distribution, data analytics
**Key Partnerships**: Content producers, AWS, device manufacturers, ISPs
**Cost Structure**: Content production/licensing, R&D, AWS infrastructure, marketing

### Example 2: Vuba Vuba (Food Delivery)

**Customer Segments**: 
- Hungry people who don't want/can't cook
- Restaurant owners without delivery infrastructure

**Value Proposition**:
- Fast delivery, online food court with many options
- One delivery fee for multiple orders
- Wider access to consumers for restaurants

**Channels**: Mobile app, phone calls, social media, direct delivery
**Customer Relationships**: Self-service (reviews, ratings), customer support
**Revenue Streams**: Delivery fees, surge pricing, commission on sales
**Key Resources**: Brand, technology platform, customer base, restaurant network
**Key Activities**: Logistics, platform development, marketing, customer support
**Key Partnerships**: Restaurants, tech providers, payment processors, delivery riders
**Cost Structure**: Office rentals, rider wages, staffing, marketing, payment fees

## CRITICAL RULES

1. **VPS Alignment**: Every block must align with the VPS v1
2. **VPC Grounding**: Ground customer-facing blocks in VPC 2.0
3. **Evidence Required**: No element without evidence citation
4. **Specificity**: Use concrete data, avoid generic statements
5. **Consistency**: Maintain alignment across all blocks
6. **Cross-References**: Link related elements using IDs
7. **Professional Tone**: Business-appropriate language
8. **Actionable**: Provide implementable insights
9. **Sequential Context**: Use previously generated blocks
10. **JSON Format**: Return valid JSON matching the schema

OUTPUT FORMAT:
Return ONLY valid JSON matching the specified schema. Do not include markdown formatting, code blocks, or explanatory text outside the JSON structure.
"""
```

---

## Layer 2: Block-Specific Prompts

### Template Structure for Each Block

```python
BLOCK_PROMPT_TEMPLATE = """
## BLOCK {number}: {name}

### Definition
{definition}

### Purpose
{purpose}

### Key Questions to Answer
{questions}

### Output Structure
{json_schema}

### Specific Guidelines
{guidelines}

### Evidence Requirements
{evidence_requirements}

### Cross-Referencing
{cross_reference_instructions}

### Examples
{examples}
"""
```

### Example: Customer Segments Prompt

```python
CUSTOMER_SEGMENTS_PROMPT = """
## BLOCK 1: CUSTOMER SEGMENTS

### Definition
Customer Segments define the different groups of people or organizations your business aims to reach and serve. Different segments have different needs, behaviors, and attributes.

### Purpose
Identify WHO you are creating value for. This is the foundation of your business model - without customers, there is no business.

### Key Questions to Answer
1. Who are our most important customers?
2. What are their key characteristics?
3. How large is each segment?
4. What is the priority of each segment?
5. Which personas map to which segments?

### Output Structure
{
  "segments": [
    {
      "id": "seg-001",
      "name": "Segment Name (concise, descriptive)",
      "description": "Detailed description of this customer segment (100-200 words)",
      "characteristics": [
        "Key characteristic 1",
        "Key characteristic 2",
        "Key characteristic 3"
      ],
      "size_estimate": "Market size or potential (with evidence)",
      "priority": "high|medium|low",
      "evidence_source": "vpc_analysis|vps_v1|field_research|market_evidence|persona_analysis",
      "persona_mapping": ["P1", "P2"]
    }
  ],
  "generation_metadata": {
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }
}

### Specific Guidelines

1. **Number of Segments**: Generate 2-4 customer segments based on the context
   - Primary segment (highest priority)
   - Secondary segments (medium/low priority)
   - Consider both direct customers and indirect beneficiaries

2. **Segment Characteristics**: Include:
   - Demographics (age, location, occupation, income level)
   - Psychographics (values, attitudes, lifestyle)
   - Behaviors (usage patterns, preferences)
   - Needs and pain points
   - Decision-making factors

3. **Size Estimation**: Provide:
   - Market size data from research
   - Growth potential
   - Addressable market percentage
   - Evidence from PV report or field research

4. **Persona Mapping**: 
   - Link each segment to relevant personas (P1, P2, etc.)
   - A segment may map to multiple personas
   - Explain the connection in the description

5. **Priority Assignment**:
   - High: Primary target, largest revenue potential
   - Medium: Secondary target, growth opportunity
   - Low: Tertiary target, future consideration

### Evidence Requirements

MANDATORY: Each segment must cite evidence from:
- VPS v1 (who the value proposition targets)
- VPC 2.0 Customer Profile (jobs, pains, gains)
- Personas (identified stakeholders)
- Field Research (validated assumptions about customers)
- Market Evidence (PV report data on market size, demographics)

Example Evidence Citations:
- "Based on VPS v1 targeting 'small-scale manufacturers' and Persona P1 evidence showing 85% face supply chain issues"
- "Market research indicates 200,000 potential customers in this segment (PV Report, Section 3.2)"
- "Field research validated that 73% of this segment prioritize cost over quality (Assumption A-002)"

### Cross-Referencing

**Links TO**: None (this is Block 1, first to be generated)

**Links FROM** (future blocks will reference):
- Value Propositions (Block 2) will link to segment IDs
- Channels (Block 3) will specify which segments use which channels
- Customer Relationships (Block 4) will define relationships per segment
- Revenue Streams (Block 5) will show revenue per segment

**ID Format**: Use `seg-001`, `seg-002`, `seg-003`, etc.

### Examples

**Example 1: B2C Food Delivery**
```json
{
  "id": "seg-001",
  "name": "Busy Urban Professionals",
  "description": "Working professionals aged 25-40 in urban areas who value convenience and time-saving. They have disposable income and prefer quality food delivered quickly. Often work long hours and don't have time to cook. Tech-savvy and comfortable with mobile apps.",
  "characteristics": [
    "Age 25-40, urban location",
    "Monthly income $2,000-$5,000",
    "Works 50+ hours per week",
    "Smartphone user, app-savvy",
    "Values convenience over cost"
  ],
  "size_estimate": "Estimated 150,000 potential customers in target cities, growing 15% annually (Market Research Report 2024)",
  "priority": "high",
  "evidence_source": "vpc_analysis",
  "persona_mapping": ["P1"]
}
```

**Example 2: B2B SaaS**
```json
{
  "id": "seg-001",
  "name": "Small Business Owners (10-50 employees)",
  "description": "Small business owners managing teams of 10-50 employees who need affordable, easy-to-use project management tools. They lack dedicated IT staff and need solutions that work out-of-the-box. Budget-conscious but willing to pay for tools that save time and improve team productivity.",
  "characteristics": [
    "Company size: 10-50 employees",
    "Annual revenue: $500K-$5M",
    "No dedicated IT department",
    "Budget: $50-$200/month for tools",
    "Decision maker: Owner or Operations Manager"
  ],
  "size_estimate": "2.5 million small businesses in target market, 35% currently use project management software (Industry Report 2024)",
  "priority": "high",
  "evidence_source": "market_evidence",
  "persona_mapping": ["P1", "P2"]
}
```

### Common Mistakes to Avoid

❌ **Too Generic**: "Young people who like technology"
✅ **Specific**: "Tech-savvy millennials (25-35) in urban areas with $50K+ income who early-adopt new apps"

❌ **No Evidence**: "There are many potential customers"
✅ **Evidence-Based**: "Market research shows 500,000 potential customers in target region (PV Report, p.23)"

❌ **No Characteristics**: "Small businesses"
✅ **Detailed**: "Small businesses with 10-50 employees, $500K-$5M revenue, no IT department, budget-conscious"

❌ **Missing Persona Link**: No persona_mapping provided
✅ **Linked**: "persona_mapping": ["P1", "P2"] with explanation in description

GENERATE CUSTOMER SEGMENTS NOW based on the provided context.
"""
```

---

## Layer 3: Context Formatting

### Context Structure for Each Block

```markdown
# PROJECT CONTEXT

## Project: {project_name}
**Description**: {project_description}

---

# VALUE PROPOSITION STATEMENT (VPS v1) - PRIMARY INPUT

## Primary Statement
{vps_primary_statement}

## Extended Statement
{vps_extended_statement}

## Key Differentiators
1. **{diff1_title}**: {diff1_description}
2. **{diff2_title}**: {diff2_description}
3. **{diff3_title}**: {diff3_description}

---

# VALUE PROPOSITION CANVAS (VPC 2.0)

## Customer Profile (Right Side)

### Jobs-to-be-Done
{formatted_jtbd_list}

### Pains
{formatted_pains_list}

### Gains
{formatted_gains_list}

## Value Map (Left Side)

### Products & Services
{formatted_products_list}

### Pain Relievers
{formatted_relievers_list}

### Gain Creators
{formatted_creators_list}

---

# PERSONAS

{formatted_personas}

---

# FIELD RESEARCH

## Validated Hypotheses
{formatted_hypotheses}

## Tested Assumptions
{formatted_assumptions}

---

# MARKET EVIDENCE

## PV Report Insights
{formatted_pv_insights}

## Actionable Insights
{formatted_actionable_insights}

## Market Research Analysis
{formatted_analysis_chunks}

---

# PREVIOUSLY GENERATED BMC BLOCKS

{formatted_previous_blocks}

---

GENERATE {block_name} NOW based on this context.
```

---

## Prompt Engineering Best Practices

### 1. Specificity Enforcement

**Technique**: Provide examples of bad vs good outputs

```
❌ BAD: "Digital marketing"
✅ GOOD: "Instagram and TikTok influencer campaigns targeting 18-30 demographic"

❌ BAD: "Reduce costs"
✅ GOOD: "Reduce customer acquisition cost from $50 to $30 through organic social media"
```

### 2. Evidence Mandates

**Technique**: Make evidence citation a required field in JSON schema

```json
{
  "evidence_source": {
    "type": "string",
    "enum": ["vps_v1", "vpc_analysis", "field_research", "market_evidence", "persona_analysis"],
    "description": "REQUIRED: Source of evidence for this element"
  }
}
```

### 3. Cross-Reference Validation

**Technique**: Provide clear ID formats and linking instructions

```
When referencing Customer Segment "seg-001" in Value Propositions:
{
  "segment_id": "seg-001",  // Links to specific segment
  ...
}
```

### 4. Sequential Context Integration

**Technique**: Explicitly instruct how to use previous blocks

```
CRITICAL: You have access to previously generated blocks:
- Customer Segments (Block 1): Use these to determine WHO needs channels
- Value Propositions (Block 2): Use these to determine WHAT to communicate

Your Channels (Block 3) must specify:
- Which segment_ids use this channel
- How this channel delivers the value propositions
```

### 5. Quality Checkpoints

**Technique**: Include self-validation questions in prompt

```
Before finalizing your output, verify:
✓ Does each element cite evidence?
✓ Are all cross-references valid IDs?
✓ Is the output specific (not generic)?
✓ Does it align with VPS v1?
✓ Does it use data from previous blocks?
```

---

## Testing Strategy

### Prompt Testing Phases

**Phase 1: Individual Block Testing**
- Test each block prompt in isolation
- Verify JSON schema compliance
- Check evidence citation quality
- Validate specificity level

**Phase 2: Sequential Testing**
- Test Block 2 with Block 1 context
- Test Block 3 with Blocks 1-2 context
- Verify cross-references work
- Check consistency across blocks

**Phase 3: End-to-End Testing**
- Generate complete 9-block BMC
- Verify all cross-references
- Check overall consistency
- Validate VPS alignment

**Phase 4: Edge Case Testing**
- Minimal context (low completeness)
- Multi-persona projects
- Different industries
- Various business models

---

## Continuous Improvement

### Feedback Loop

```
User Feedback → Prompt Refinement → Testing → Deployment
      ↑                                            ↓
      └────────────────────────────────────────────┘
```

### Metrics to Track

1. **Evidence Citation Rate**: % of elements with evidence
2. **Specificity Score**: Manual review of generic vs specific
3. **Cross-Reference Accuracy**: % of valid cross-references
4. **VPS Alignment**: Manual review of consistency
5. **User Satisfaction**: Feedback on output quality

---

**This prompt strategy ensures high-quality, evidence-based, interconnected BMC generation!** 🎯
