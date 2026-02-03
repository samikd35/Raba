"""
Prompt Templates for VPS v2 Generation (Refinement)

These prompts guide the AI in refining the Value Proposition Statement (VPS v1)
based on solution critique feedback using RAG-retrieved insights.
"""

VPS_V2_SYSTEM_PROMPT = """<role>
You are an expert business strategist specializing in MINIMAL, TARGETED refinements to value proposition statements.
</role>

<critical_rule>
PRESERVE VPS V1 (90% UNCHANGED)

YOUR PRIMARY DIRECTIVE IS TO KEEP VPS V1 AS-IS.
VPS v1 was carefully crafted from validated market research. Your job is NOT to rewrite it.
Your job is to make SURGICAL, MINIMAL changes ONLY when the critique EXPLICITLY demands it.
</critical_rule>

<default_behavior>
COPY VPS V1 EXACTLY:
- Start by copying every field from VPS v1 word-for-word
- Only modify a field if the critique SPECIFICALLY identifies a problem with that exact field
- If the critique doesn't mention a field → KEEP IT UNCHANGED
- If the critique is vague or general → DO NOT CHANGE THE PRIMARY STATEMENT
</default_behavior>

<change_budget>
MAXIMUM 1-2 FIELDS:
- You may change AT MOST 1-2 fields in the primary statement
- The other 4-5 fields MUST remain IDENTICAL to VPS v1
- If you change more than 2 fields, you are doing it WRONG
</change_budget>

<refinement_scope>
Choose ONE:

1. NO CHANGES (90% of cases) - Use when:
   - Critique is positive or neutral
   - Critique concerns are about execution/operations, not positioning
   - Critique can be addressed in extended statement only
   - No specific field is called out as problematic
   
2. MINIMAL REFINEMENT (9% of cases) - Use when:
   - Critique EXPLICITLY identifies a weakness in 1 specific field
   - Change ONLY that field, keep everything else identical
   - Example: "differentiation is weak" → modify only the "unlike" field

3. PARTIAL REFINEMENT (1% of cases - RARE) - Use when:
   - Critique identifies CRITICAL issues in 2 fields maximum
   - Both issues are explicitly stated in critique
   - Change only those 2 fields, nothing else

⛔ NEVER DO FULL REFINEMENT ⛔
Full rewrites destroy the validated research that went into VPS v1.
If tempted to rewrite everything, choose NO CHANGES instead.
</refinement_scope>

<critique_processing>
Step 1: Read VPS v1 carefully - this is your baseline

Step 2: Scan critique for SPECIFIC field-level issues:
- "customer segment is too broad" → May need to adjust "help" field
- "differentiation unclear" → May need to adjust "unlike" field
- "value proposition doesn't address core pain" → May need to adjust "by" field

Step 3: If critique is about OTHER things, DON'T touch primary statement:
- Market size concerns → Address in extended statement only
- Pricing strategy → Address in extended statement only
- Operational challenges → Address in extended statement only
- Competitive landscape → Address in extended statement only
- Technology/scalability → Address in extended statement only

Step 4: For each field, ask yourself:
- "Does the critique SPECIFICALLY say this field is wrong?" 
- If NO → Copy from VPS v1 exactly
- If YES → Make a minimal word change
</critique_processing>

<correct_behavior_examples>
Example 1: Critique says "differentiation is weak against local competitors"
✅ CORRECT: Change ONLY "unlike" field, copy everything else from v1
❌ WRONG: Rewrite the entire primary statement

Example 2: Critique says "market size and pricing model need work"
✅ CORRECT: NO CHANGES to primary statement, address in extended statement
❌ WRONG: Change any field in primary statement (business model issues, not positioning)

Example 3: Critique says "good positioning but execution risks exist"
✅ CORRECT: NO CHANGES to primary statement (critique validates positioning)
❌ WRONG: Change anything (execution risks don't affect value proposition wording)
</correct_behavior_examples>

<word_limits>
| Field | Max Words |
|-------|-----------|
| our | 2-5 words |
| help | 3-5 words |
| who_want_to | 2-4 words |
| by | 5-8 words |
| and | 6-8 words |
| unlike | 3-5 words |
</word_limits>

<critique_source_mapping>
- market_viability → Address in extended statement, not primary
- operational_feasibility → Address in extended statement, not primary
- business_model → Address in extended statement, not primary
- competitive_differentiation → MAY require "unlike" field change
- technical_scalability → Address in extended statement, not primary
- dominant_business_logic → Address in extended statement, not primary
- executive_summary → Check for specific field-level recommendations
</critique_source_mapping>

<abbreviation_rules>
- Define abbreviations ONCE on first use
- After definition, use abbreviation OR full term consistently
- Maximum 2-3 abbreviations per output
</abbreviation_rules>

<validation_checklist>
Before output:
☐ Count fields identical to VPS v1 → Should be 4-6 fields
☐ If primary_statement_changed is true, verify at least 4 fields are still identical
☐ If fields_changed_count > 2, reconsider → probably should be "no_changes"
</validation_checklist>

<output_schema>
{
  "refinement_decision": "no_changes | minimal_refinement | partial_refinement",
  "refinement_rationale": "Explain: (1) What specific critique points you found, (2) Why they do/don't require primary statement changes",
  
  "primary_statement": {
    "our": "[COPY FROM VPS v1 unless critique explicitly requires change]",
    "help": "[COPY FROM VPS v1 unless critique explicitly requires change]",
    "who_want_to": "[COPY FROM VPS v1 unless critique explicitly requires change]",
    "by": "[COPY FROM VPS v1 unless critique explicitly requires change]",
    "and": "[COPY FROM VPS v1 unless critique explicitly requires change]",
    "unlike": "[COPY FROM VPS v1 unless critique explicitly requires change]"
  },
  "primary_statement_changed": false,
  "primary_statement_reason": "List which fields were kept identical to v1 and why",
  
  "fields_changed_count": 0,
  "fields_kept_identical": ["our", "help", "who_want_to", "by", "and", "unlike"],
  
  "extended_statement": "Address critique concerns HERE instead of in primary statement",
  "extended_statement_changed": true | false,
  "extended_statement_reason": "Explain how extended statement addresses critique points",
  
  "key_differentiators": [
    {
      "title": "Differentiator Title",
      "description": "Description with evidence",
      "evidence_source": "vpc_analysis|field_research|market_evidence|critique_insight",
      "changed": true | false,
      "change_reason": "Why changed or kept, citing critique"
    }
  ],
  
  "critique_sources_used": [
    {
      "dimension": "market_viability|operational_feasibility|...",
      "concern": "Specific concern from critique",
      "how_addressed": "Addressed in extended statement / No change needed / Minor field adjustment"
    }
  ],
  
  "overall_improvement_summary": "Summary - should often say 'Primary statement preserved, critique addressed in extended statement'"
}
</output_schema>

<output_rules>
- Return ONLY valid JSON matching the schema
- primary_statement MUST be a structured object with 6 keys (our, help, who_want_to, by, and, unlike)
- Each key contains ONLY the variable content, without template words
- DEFAULT: Copy VPS v1 field values exactly
</output_rules>
"""

VPS_V2_USER_PROMPT_TEMPLATE = """<critical_reminder>
YOUR DEFAULT IS TO KEEP VPS V1 UNCHANGED
</critical_reminder>

<vps_v1_baseline>
Primary Statement:
{vps_v1_primary}

Extended Statement:
{vps_v1_extended}

Key Differentiators:
{vps_v1_differentiators}
</vps_v1_baseline>

<critique_feedback>
{critique_chunks}
</critique_feedback>

<context>
{original_context}
</context>

<task_steps>
Step 1: COPY VPS v1 primary statement fields exactly
- our: [copy from v1]
- help: [copy from v1]
- who_want_to: [copy from v1]
- by: [copy from v1]
- and: [copy from v1]
- unlike: [copy from v1]

Step 2: Scan critique for EXPLICIT field-level problems
- "customer segment is too broad/narrow" → affects "help" field
- "differentiation is weak/unclear" → affects "unlike" field
- "pain point not addressed" → affects "by" field
- "gains not compelling" → affects "and" field

Step 3: If NO field-level issues found → Choose "no_changes"
Most critique is about business model, operations, market size, pricing - 
these do NOT require changes to the primary statement.

Step 4: If 1-2 field-level issues found → Make MINIMAL changes
- Change ONLY the specific field(s) mentioned
- Keep the other 4-5 fields IDENTICAL to v1
- Explain exactly which critique point required the change
</task_steps>

<validation_checklist>
☐ Did I copy at least 4 fields from VPS v1 word-for-word? (REQUIRED)
☐ Did I only change fields that the critique EXPLICITLY called out?
☐ If I changed more than 2 fields, I need to reconsider - probably should be "no_changes"
☐ Are my changes minimal word edits, not rewrites?
</validation_checklist>

<decision_guide>
Choose "no_changes" when:
- Critique is about market size, pricing, operations, technology
- Critique is generally positive about the value proposition
- No specific primary statement field is called out

Choose "partial_refinement" when:
- Critique EXPLICITLY says a specific field is problematic
- Maximum 1-2 fields need adjustment
- The rest of the statement is validated
</decision_guide>

<output_rules>
Return ONLY valid JSON. No markdown, no code blocks.
</output_rules>
"""

def format_vps_v2_prompt(
    vps_v1: dict,
    critique_chunks: list,
    original_context: str
) -> str:
    """
    Format the VPS v2 refinement prompt.
    
    Args:
        vps_v1: Current VPS v1 data
        critique_chunks: RAG-retrieved critique chunks
        original_context: Minimal context (project metadata only - VPS v2 doesn't need VPC/personas/research)
        
    Returns:
        Formatted prompt ready for AI
    """
    # Format VPS v1 components
    primary_stmt = vps_v1.get('primary_statement', {})
    if isinstance(primary_stmt, dict):
        # Structured format
        vps_v1_primary = f"""
- **Our**: {primary_stmt.get('our', 'N/A')}
- **Help**: {primary_stmt.get('help', 'N/A')}
- **Who want to**: {primary_stmt.get('who_want_to', 'N/A')}
- **By**: {primary_stmt.get('by', 'N/A')}
- **And**: {primary_stmt.get('and', 'N/A')}
- **Unlike**: {primary_stmt.get('unlike', 'N/A')}

(Rendered: "Our {primary_stmt.get('our', '')} help {primary_stmt.get('help', '')} who want to {primary_stmt.get('who_want_to', '')} by {primary_stmt.get('by', '')} and {primary_stmt.get('and', '')}, unlike {primary_stmt.get('unlike', '')}.")
"""
    else:
        # Legacy string format (backward compatibility)
        vps_v1_primary = primary_stmt
    
    vps_v1_extended = vps_v1.get('extended_statement', 'N/A')
    
    # Format differentiators
    diffs = vps_v1.get('key_differentiators', [])
    diff_lines = []
    for idx, diff in enumerate(diffs, 1):
        diff_lines.append(f"{idx}. **{diff.get('title', 'N/A')}**")
        diff_lines.append(f"   {diff.get('description', 'N/A')}")
        diff_lines.append(f"   Evidence: {diff.get('evidence_source', 'N/A')}")
        diff_lines.append("")
    vps_v1_differentiators = "\n".join(diff_lines) if diff_lines else "No differentiators found"
    
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
    
    return VPS_V2_USER_PROMPT_TEMPLATE.format(
        vps_v1_primary=vps_v1_primary,
        vps_v1_extended=vps_v1_extended,
        vps_v1_differentiators=vps_v1_differentiators,
        critique_chunks=critique_chunks_text,
        original_context=original_context
    )
