"""
BMC v2 Refinement Prompts

Guides AI in refining Business Model Canvas v1 based on solution critique feedback
and alignment with the refined VPS v2.
"""

import logging

logger = logging.getLogger(__name__)

BMC_V2_SYSTEM_PROMPT = """<role>
You are an expert business strategist specializing in refining Business Model Canvases based on solution critique feedback and value proposition alignment.
</role>

<task>
Analyze the existing BMC v1 against the solution critique report and the refined VPS v2, then determine what refinements are needed to strengthen the business model.
</task>

<inputs>
You will receive:
1. BMC v1: The current 9-block Business Model Canvas (baseline to refine)
2. VPS v2: The refined Value Proposition Statement (must align with Value Propositions block)
3. Solution Critique: RAG-retrieved critique chunks highlighting business model concerns
4. Minimal Context: Project metadata only

IMPORTANT: BMC v1 was generated using comprehensive context. For BMC v2 refinement, you ONLY need:
- The BMC v1 (what to refine)
- The VPS v2 (alignment reference for Value Propositions block)
- The critique feedback (what to improve based on)
</inputs>

<decision_process>
1. Analyze Critique Feedback by Block:
   - Customer Segments: Market sizing issues, segment clarity, targeting concerns
   - Value Propositions: Alignment with VPS v2, differentiation gaps, value clarity
   - Channels: Distribution feasibility, reach concerns, cost-effectiveness
   - Customer Relationships: Acquisition/retention strategy gaps, scalability issues
   - Revenue Streams: Pricing concerns, monetization model viability, unit economics
   - Key Resources: Resource availability, capability gaps, infrastructure needs
   - Key Activities: Operational complexity, execution feasibility, prioritization
   - Key Partnerships: Partnership viability, ecosystem gaps, dependency risks
   - Cost Structure: Cost drivers, margin concerns, scalability of costs

2. Ensure VPS v2 Alignment:
   - Value Propositions block MUST align with VPS v2
   - If VPS v2 changed customer segment focus, update Customer Segments
   - If VPS v2 changed pain relievers/gain creators, update Value Propositions accordingly

3. Determine Refinement Scope Per Block:
   a) NO CHANGES: Block is well-aligned and validated
   b) PARTIAL REFINEMENT: Update 1-3 items within the block
   c) FULL REFINEMENT: Revise most/all items in the block

4. Generate Refinements with Evidence:
   - Every change must cite the critique source or VPS v2 alignment
   - Reference specific critique dimensions
   - Include critique quotes or VPS v2 alignment rationale
   - Explain WHY each change addresses the concern
</decision_process>

<refinement_guidelines>
Critique-Driven Changes:
- "revenue model unclear" → Clarify Revenue Streams block
- "operational complexity high" → Simplify Key Activities
- "customer segment too broad" → Narrow Customer Segments
- "partnership dependencies risky" → Address in Key Partnerships
- "cost structure unsustainable" → Optimize Cost Structure

VPS v2 Alignment:
- If VPS v2 changed customer segment description → Update Customer Segments
- If VPS v2 changed value proposition emphasis → Update Value Propositions
- If VPS v2 added/removed differentiators → Reflect in Value Propositions

Evidence Requirements:
- Cite critique source: [Business Model], [Operational Feasibility], [Market Viability]
- Quote specific concerns: "The critique notes: '[quote]'"
- Explain resolution: "To address this, we now..."
- For VPS v2 alignment: "Updated to align with refined VPS v2: '[VPS v2 quote]'"
</refinement_guidelines>

<critical_alignment_rule>
The Value Propositions block must be consistent with VPS v2. If VPS v2's primary statement changed:
- Update Value Propositions items to match
- Ensure pain_relievers and gain_creators align
- Reference VPS v2 as evidence source
</critical_alignment_rule>

<segment_distribution_rule>
**CRITICAL CONSTRAINT: Balanced Segment Coverage**

When refining value propositions, you MUST ensure:
1. Each value proposition is assigned to exactly ONE segment (its primary target segment)
2. EVERY customer segment must have AT LEAST ONE value proposition primarily assigned to it
3. segment_ids array must contain exactly ONE segment ID per value proposition

Rationale: A customer segment that exists in the BMC must have at least one value proposition specifically designed for it. If a segment has no VPs, it shouldn't exist in the BMC.

Example with 2 segments and 4 VPs:
- seg-001 (Hospital IT Managers): vp-001, vp-002, vp-004
- seg-002 (Donor Programs): vp-003

DO NOT assign all VPs to the same segment. Each segment deserves dedicated value propositions.
</segment_distribution_rule>

<abbreviation_rules>
- Define abbreviations ONCE on first use
- After definition, use abbreviation OR full term consistently
- Maximum 2-3 abbreviations per output
</abbreviation_rules>

<output_schema>
{
  "refinement_decision": "no_changes | partial_refinement | full_refinement",
  "refinement_rationale": "Overall explanation of refinement approach",
  
  "customer_segments": {
    "segments": [
      {"id": "seg-001", "name": "Segment Name", "description": "...", "characteristics": [...], "size_estimate": "...", "priority": "high|medium|low"}
    ],
    "changed": true | false,
    "change_reason": "Why changed or kept, citing critique/VPS v2"
  },
  
  "value_propositions": {
    "propositions": [
      {"id": "vp-001", "name": "Proposition Name", "value_statement": "...", "key_benefits": [...], "segment_ids": ["seg-001"]}
    ],
    "changed": true | false,
    "change_reason": "Must explain VPS v2 alignment",
    "vps_v2_aligned": true | false
  },
  
  "channels": {
    "channels": [
      {"id": "ch-001", "name": "Channel Name", "type": "direct|indirect|digital|physical", "description": "...", "segment_ids": ["seg-001"]}
    ],
    "changed": true | false,
    "change_reason": "..."
  },
  
  "customer_relationships": {
    "relationships": [
      {"id": "rel-001", "name": "Relationship Type", "description": "...", "segment_ids": ["seg-001"]}
    ],
    "changed": true | false,
    "change_reason": "..."
  },
  
  "revenue_streams": {
    "revenue_streams": [
      {"id": "rev-001", "name": "Revenue Stream Name", "pricing_strategy": "...", "segment_ids": ["seg-001"]}
    ],
    "changed": true | false,
    "change_reason": "..."
  },
  
  "key_resources": {
    "resources": [
      {"id": "res-001", "name": "Resource Name", "type": "physical|intellectual|human|financial", "description": "..."}
    ],
    "changed": true | false,
    "change_reason": "..."
  },
  
  "key_activities": {
    "activities": [
      {"id": "act-001", "name": "Activity Name", "category": "production|problem_solving|platform|other", "description": "..."}
    ],
    "changed": true | false,
    "change_reason": "..."
  },
  
  "key_partnerships": {
    "partnerships": [
      {"id": "part-001", "name": "Partner Name", "type": "strategic|coopetition|joint_venture|buyer_supplier", "value_contribution": "..."}
    ],
    "changed": true | false,
    "change_reason": "..."
  },
  
  "cost_structure": {
    "cost_structure": {
      "type": "cost_driven | value_driven",
      "cost_categories": [
        {"id": "cost-001", "name": "Cost Category Name", "type": "fixed|variable", "description": "...", "percentage_estimate": "..."}
      ]
    },
    "changed": true | false,
    "change_reason": "..."
  },
  
  "critique_sources_used": [
    {
      "dimension": "business_model|operational_feasibility|...",
      "concern": "Specific concern from critique",
      "blocks_affected": ["customer_segments", "revenue_streams"],
      "how_addressed": "How the refinement addresses this"
    }
  ],
  
  "vps_v2_alignment_notes": "How BMC v2 now aligns with refined VPS v2",
  
  "overall_improvement_summary": "High-level summary of BMC improvements"
}
</output_schema>

<output_rules>
- Return ONLY valid JSON matching the schema
- Follow the same block structures as v1
- Keep item counts within recommended ranges
- Use evidence-based language
- Ensure internal consistency across blocks
</output_rules>
"""

BMC_V2_USER_PROMPT_TEMPLATE = """<task>
Refine the Business Model Canvas based on solution critique feedback and VPS v2 alignment.
</task>

<bmc_v1>
Customer Segments:
{bmc_v1_customer_segments}

Value Propositions:
{bmc_v1_value_propositions}

Channels:
{bmc_v1_channels}

Customer Relationships:
{bmc_v1_customer_relationships}

Revenue Streams:
{bmc_v1_revenue_streams}

Key Resources:
{bmc_v1_key_resources}

Key Activities:
{bmc_v1_key_activities}

Key Partnerships:
{bmc_v1_key_partnerships}

Cost Structure:
{bmc_v1_cost_structure}
</bmc_v1>

<vps_v2_alignment_reference>
Primary Statement:
{vps_v2_primary}

Key Differentiators:
{vps_v2_differentiators}
</vps_v2_alignment_reference>

<critique_feedback>
{critique_chunks}
</critique_feedback>

<context>
{context}
</context>

<task_steps>
1. Analyze the solution critique against BMC v1, block by block
2. Ensure Value Propositions block aligns with VPS v2
3. Decide refinement scope per block (no_changes, partial, or full)
4. Generate BMC v2 with changes grounded in critique feedback and VPS v2 alignment
5. Cite specific critique sources for every change
6. Preserve what works well in v1
</task_steps>

<critical_requirements>
- Every change must have a reason citing the critique or VPS v2 alignment
- Value Propositions MUST align with VPS v2
- Use the same BMC block formats as v1
- Maintain evidence-based approach
</critical_requirements>

<output_rules>
Return ONLY valid JSON matching the schema. No markdown, no code blocks.
</output_rules>
"""


def format_bmc_v2_prompt(
    bmc_v1: dict,
    vps_v2: dict,
    critique_chunks: list,
    context: str
) -> str:
    """
    Format the BMC v2 refinement prompt.
    
    Args:
        bmc_v1: Current BMC v1 data (9 blocks)
        vps_v2: Refined VPS v2 for alignment
        critique_chunks: RAG-retrieved critique chunks
        context: Minimal context (project metadata only)
        
    Returns:
        Formatted prompt ready for AI
    """
    # Format BMC v1 blocks
    def format_block_items(items):
        if not items:
            return "No items"
        lines = []
        for item in items:
            # Extract name from various possible field names
            name = (item.get('segment_name') or 
                   item.get('name') or 
                   item.get('proposition') or 
                   item.get('title') or 
                   'N/A')
            lines.append(f"  - {item.get('id', 'N/A')}: {name}")
            desc = item.get('description', '')
            if desc and len(desc) > 100:
                lines.append(f"    {desc[:100]}...")
            elif desc:
                lines.append(f"    {desc}")
        return "\n".join(lines)
    
    # BMC v1 uses different key names per block
    bmc_v1_customer_segments = format_block_items(bmc_v1.get('customer_segments', {}).get('segments', []))
    bmc_v1_value_propositions = format_block_items(bmc_v1.get('value_propositions', {}).get('propositions', []))
    bmc_v1_channels = format_block_items(bmc_v1.get('channels', {}).get('channels', []))
    bmc_v1_customer_relationships = format_block_items(bmc_v1.get('customer_relationships', {}).get('relationships', []))
    bmc_v1_revenue_streams = format_block_items(bmc_v1.get('revenue_streams', {}).get('revenue_streams', []))
    bmc_v1_key_resources = format_block_items(bmc_v1.get('key_resources', {}).get('resources', []))
    bmc_v1_key_activities = format_block_items(bmc_v1.get('key_activities', {}).get('activities', []))
    bmc_v1_key_partnerships = format_block_items(bmc_v1.get('key_partnerships', {}).get('partnerships', []))
    bmc_v1_cost_structure = format_block_items(bmc_v1.get('cost_structure', {}).get('cost_structure', {}).get('cost_categories', []))
    
    # Log BMC v1 content extraction status
    blocks_with_content = []
    blocks_empty = []
    
    if bmc_v1_customer_segments != "No items":
        blocks_with_content.append("customer_segments")
    else:
        blocks_empty.append("customer_segments")
        
    if bmc_v1_value_propositions != "No items":
        blocks_with_content.append("value_propositions")
    else:
        blocks_empty.append("value_propositions")
        
    if bmc_v1_channels != "No items":
        blocks_with_content.append("channels")
    else:
        blocks_empty.append("channels")
        
    if bmc_v1_customer_relationships != "No items":
        blocks_with_content.append("customer_relationships")
    else:
        blocks_empty.append("customer_relationships")
        
    if bmc_v1_revenue_streams != "No items":
        blocks_with_content.append("revenue_streams")
    else:
        blocks_empty.append("revenue_streams")
        
    if bmc_v1_key_resources != "No items":
        blocks_with_content.append("key_resources")
    else:
        blocks_empty.append("key_resources")
        
    if bmc_v1_key_activities != "No items":
        blocks_with_content.append("key_activities")
    else:
        blocks_empty.append("key_activities")
        
    if bmc_v1_key_partnerships != "No items":
        blocks_with_content.append("key_partnerships")
    else:
        blocks_empty.append("key_partnerships")
        
    if bmc_v1_cost_structure != "No items":
        blocks_with_content.append("cost_structure")
    else:
        blocks_empty.append("cost_structure")
    
    logger.info(f"📊 BMC v1 Content Extraction:")
    logger.info(f"   ✅ Blocks with content ({len(blocks_with_content)}/9): {', '.join(blocks_with_content)}")
    if blocks_empty:
        logger.warning(f"   ⚠️ Empty blocks ({len(blocks_empty)}/9): {', '.join(blocks_empty)}")
    else:
        logger.info(f"   🎉 All 9 blocks have content!")
    
    # Format VPS v2
    # Handle both structured (dict) and legacy (string) primary_statement formats
    primary_stmt = vps_v2.get('primary_statement', 'N/A')
    if isinstance(primary_stmt, dict):
        vps_v2_primary = " ".join([
            primary_stmt.get('our', ''),
            primary_stmt.get('help', ''),
            primary_stmt.get('who_want_to', ''),
            primary_stmt.get('by', ''),
            primary_stmt.get('and', ''),
            primary_stmt.get('unlike', '')
        ]).strip() or 'N/A'
    else:
        vps_v2_primary = primary_stmt
    
    vps_v2_diffs = vps_v2.get('key_differentiators', [])
    diff_lines = []
    for idx, diff in enumerate(vps_v2_diffs, 1):
        diff_lines.append(f"{idx}. **{diff.get('title', 'N/A')}**")
        diff_lines.append(f"   {diff.get('description', 'N/A')[:150]}...")
    vps_v2_differentiators = "\n".join(diff_lines) if diff_lines else "No differentiators"
    
    # Format critique chunks
    critique_lines = []
    for idx, chunk in enumerate(critique_chunks, 1):
        metadata = chunk.get('metadata', {})
        section = metadata.get('section', 'Unknown')
        dimension = metadata.get('dimension', 'Unknown')
        
        critique_lines.append(f"**Critique Chunk {idx}** [Dimension: {dimension}, Section: {section}]")
        critique_lines.append(chunk.get('content', 'N/A'))
        critique_lines.append("")
        critique_lines.append("---")
        critique_lines.append("")
    
    critique_chunks_text = "\n".join(critique_lines) if critique_lines else "No critique feedback available"
    
    return BMC_V2_USER_PROMPT_TEMPLATE.format(
        bmc_v1_customer_segments=bmc_v1_customer_segments,
        bmc_v1_value_propositions=bmc_v1_value_propositions,
        bmc_v1_channels=bmc_v1_channels,
        bmc_v1_customer_relationships=bmc_v1_customer_relationships,
        bmc_v1_revenue_streams=bmc_v1_revenue_streams,
        bmc_v1_key_resources=bmc_v1_key_resources,
        bmc_v1_key_activities=bmc_v1_key_activities,
        bmc_v1_key_partnerships=bmc_v1_key_partnerships,
        bmc_v1_cost_structure=bmc_v1_cost_structure,
        vps_v2_primary=vps_v2_primary,
        vps_v2_differentiators=vps_v2_differentiators,
        critique_chunks=critique_chunks_text,
        context=context
    )
