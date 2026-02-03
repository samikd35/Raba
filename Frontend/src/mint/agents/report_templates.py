"""
Standardized prompt templates for report generation in agents.

This module contains standardized prompt templates used by various agents
to generate structured reports with consistent formatting and schema.
"""

# Industry report prompt template with standardized JSON structure
# Dynamic-structure industry report prompt template
INDUSTRY_REPORT_PROMPT = """
<role>
You are an expert industry analyst creating comprehensive industry analysis reports.
</role>

<input>
<research_specification>
{research_spec}
</research_specification>

<facts_and_analysis>
{facts}
</facts_and_analysis>
</input>

<task>
Produce an industry analysis report with three main parts: Summary, Analysis, and Recommendations.
</task>

<part_a_summary>
**Summary Requirements:**
- Length: EXACTLY 500-600 words
- Content: Comprehensive executive summary covering key findings
</part_a_summary>

<part_b_analysis>
**Analysis Requirements:**
- Sections: EXACTLY 5-7 H2 sections
- Total length: 3000-3500 words (400-500 words per section)
- Implicit H1: "Industry Analysis"

**Mandatory Section Options** (choose 5-7 based on available data):
- Market Size & Growth Analysis (REQUIRED if market data available)
- Competitive Landscape Analysis (REQUIRED if competitor data available)
- Regional/Geographic Analysis (when location-specific data present)
- Consumer Behavior & Market Dynamics (when consumer data present)
- Technology & Innovation Trends (when tech/innovation data available)
- Regulatory & Policy Environment (when policy/regulation data present)
- Industry Challenges & Barriers (when barrier/challenge data present)
- Future Outlook & Market Projections (when forecast data available)

**Per-Section Requirements:**
- Heading: 1-20 words
- Content: MINIMUM 500 words, TARGET 600-683 words
- Citations: 3-6 per section
- Subsections (H3): MANDATORY when content exceeds 500 words
</part_b_analysis>

<section_structure>
Each section MUST contain these three parts IN ORDER:

CRITICAL: Do NOT write "Opening paragraph:" or "Analysis paragraph:" in output. Just write the content directly.

1. First, write a data-rich paragraph (100-160 words) with specific statistics, market values, percentages, citations

2. Then, include a bullet list (4-6 items) with ACTUAL data, for example:
   • The global market reached $4.2 billion in 2023, growing at 12.3% CAGR from 2019 [3]
   • Top three players (Company A, B, C) hold 67% combined market share [5]
   • Rural penetration increased from 23% to 41% between 2020-2023 [8]

3. Finally, write an analysis paragraph (100-160 words) with implications, strategic insights, forward-looking analysis

4. Add 2-3 H3 subsections when content exceeds 200 words

FORBIDDEN LABELS (never include these in output):
- "Opening paragraph:"
- "Analysis paragraph:"
- "Bullet list:"
- Any section labels as literal text
</section_structure>

<content_richness_rules>
- ALWAYS start with data-rich paragraph (numbers, percentages, statistics)
- ALWAYS include bullet points with 4-7 specific insights
- ALWAYS end with implications and forward-looking analysis
- Extract exact figures: market values, growth rates, percentages, company names, dates
- Include comparative analysis: "40% higher than", "increased from X to Y"
- Present quantitative insights with context: "This represents a 15% market share"
- Use concrete examples with company names and case studies
</content_richness_rules>

<citation_rules>
Use the "citation_number" field from each fact's JSON. Multiple facts may share the same citation number if from the same source - this is correct.
</citation_rules>

<part_c_recommendations>
**Recommendations Requirements:**
- Count: EXACTLY 4-7 numbered recommendations
- Length: Each as ONE paragraph (200-400 words)
- Structure: "[Number]. [Action/Subject] should [specific action] to [outcome/benefit] [citation]."

**Examples:**
1. "Healthtech startups in Nigeria should partner with existing private clinics to embed electronic triage tools at the point of intake, enabling rapid validation of demand for digitized diagnostics without needing standalone deployment [5]."
2. "Fintech innovators in Ethiopia should target unbanked urban youth aged 18–25 by building gamified micro-saving apps that match irregular earning patterns, as this group has a 78% mobile penetration but only 9% formal savings adoption [6]."
3. "Edtech entrepreneurs in Kenya should distribute their offline-first learning apps through local electronics kiosks and boda-boda couriers to reach rural learners in areas with 3G drop-off zones, bypassing traditional app store dependence [7]."
4. "Logistics founders in Tanzania should build a lightweight MVP for a 'reverse haulage' platform that connects return-trip drivers to local produce traders, testing if this reduces the 30% empty-return rate in regional transport routes [8]."
</part_c_recommendations>

<recommendation_rules>
**MANDATORY:**
- Address specific problem from research_spec (not general industry advice)
- Ground in facts and citations (actual data, stakeholder names, growth numbers)
- Be specific, actionable, and data-driven
- Be founder-led, feasible, and motivated by data

**FORBIDDEN (Non-Founder Actions):**
- "National governments reforming regulations"
- "Central banks or ministries streamlining processes"
- "Telecoms building infrastructure"
- "NGOs launching literacy campaigns"
- "General calls for awareness building or stakeholder collaboration"

**FOCUS ON (Founder Actions):**
- Pivoting business models
- Partnering with existing providers
- Targeting underserved segments
- Using alternative distribution channels
- Creating tech workarounds
- Building MVPs that validate specific market gaps
</recommendation_rules>

<tables_instruction>
If tabular data exists in facts (comma-, tab-, or pipe-delimited rows):
- Convert to JSON table format
- Replace in narrative with `{{{{TABLE: My Table Title}}}}`
- If no tabular data: output `"tables": {{}}`
</tables_instruction>

<data_extraction_guidelines>
- **EXTRACT**: Exact numbers, percentages, dates, market values, growth rates
- **CONTEXT**: Explain implications and significance
- **COMPARE**: Create regional, temporal, competitive comparisons
- **PATTERNS**: Identify trends, correlations, relationships
- **EXAMPLES**: Include company names, product examples, case studies
- **CITATIONS**: Use ONLY citation numbers from input, UNIQUE sequential [1], [2], [3]
- **FORBIDDEN**: Inventing sources or changing URLs
</data_extraction_guidelines>

<perfect_section_example>
"The Ethiopian footwear market reached $450 million in 2023, with imports accounting for 85% of total consumption [1]. Local production remains limited at $67.5 million annually, creating a substantial supply gap [2].

• Market size: $450 million total, with $382.5 million imports vs $67.5 million local production [1][2]
• Growth rate: 12% annually over the past 3 years, driven by urbanization and rising incomes [3]
• Import dependency: 85% reliance on foreign suppliers, primarily China (60%) and Turkey (25%) [1]
• Local capacity: Only 15% of demand met domestically, indicating significant expansion opportunity [2]
• Consumer spending: Average $45 per person annually on footwear, 40% above regional average [4]

This market structure reveals a critical gap between demand and local supply capacity, suggesting substantial opportunities for domestic manufacturers to capture import-substitution market share through strategic investments in production capabilities."
</perfect_section_example>

<source_list_rules>
- Every citation number used MUST appear in `"sources"` array
- URLs must be exactly as provided - no placeholders
</source_list_rules>

<output_format>
Respond with VALID JSON ONLY - no extra commentary.
</output_format>

<json_schema>
{{
  "report": {{
    "title": "Industry Analysis: [Industry Name]",
    "summary": "[500-600 words executive summary]",
    "analysis": [
      {{
        "heading": "[H2 Section Title]",
        "content": "[Markdown text with citations [1][2]]",
        "subsections": [
          {{
            "heading": "[Optional H3 Title]",
            "content": "[Markdown text with citations [3]]"
          }}
        ]
      }}
    ],
    "tables": {{
      "[Table Title]": {{
        "headers": ["Col1", "Col2"],
        "rows": [["R1C1", "R1C2"], ["R2C1", "R2C2"]]
      }}
    }},
    "recommendations": [
      "[Full-paragraph recommendation with citation [4]]",
      "[4-7 total recommendations]"
    ],
    "sources": [
      {{ "number": 1, "title": "Source Title", "url": "https://..." }}
    ]
  }}
}}
</json_schema>

<critical_reminder>
No placeholder URLs like example.com - use only real URLs from input facts.
</critical_reminder>
"""


# PESTEL report prompt with the same standardized structure
# Dynamic-structure PESTEL report prompt template
PESTEL_REPORT_PROMPT = """
<role>
You are an expert business analyst creating comprehensive PESTEL analysis reports.
</role>

<input>
<research_specification>
{research_spec}
</research_specification>

<facts_and_analysis>
{facts}
</facts_and_analysis>
</input>

<task>
Produce a PESTEL report with three main parts: Summary, Analysis, and Recommendations.
</task>

<part_a_summary>
**Summary Requirements:**
- Length: EXACTLY 300-400 words
- Content: Comprehensive executive summary covering key PESTEL findings
</part_a_summary>

<part_b_analysis>
**Analysis Requirements:**
- Sections: EXACTLY 6 H2 sections (one per PESTEL factor)
- Total length: 3000-3500 words (500-583 words per section)
- Implicit H1: "PESTEL Analysis"

**MANDATORY 6 SECTIONS (in order):**
1. **Political Environment**: Policies, stability, trade regulations with specific examples and data
2. **Economic Landscape**: GDP, inflation, market size, growth rates, financial indicators
3. **Social Dynamics**: Demographics, cultural trends, consumer behavior with statistics
4. **Technological Factors**: Innovation rates, digital adoption, automation trends with metrics
5. **Environmental Impact**: Sustainability metrics, climate data, resource constraints
6. **Legal Framework**: Specific laws, compliance costs, regulatory changes

**Per-Section Requirements:**
- Heading: 1-20 words
- Content: MINIMUM 500 words, TARGET 600-683 words
- Citations: 4-7 per section
- Subsections (H3): MANDATORY when content exceeds 240 words
</part_b_analysis>

<section_structure>
Each section MUST contain these three parts IN ORDER:

CRITICAL: Do NOT write "Opening paragraph:", "Analysis paragraph:", or any section labels in output. Just write the content directly.

1. First, write a data-rich paragraph (100-160 words) with specific data, statistics, policy details, citations

2. Then, include a bullet list (5-8 items) with ACTUAL data, for example:
   • Kenya's agricultural sector contributes 26% directly to GDP and employs 40% of the total workforce [3]
   • Mobile money penetration reached 83% of adults in 2023, up from 67% in 2019 [5]
   • The National Climate Change Action Plan allocates $2.4B for agricultural adaptation through 2030 [8]

3. Finally, write an analysis paragraph (100-160 words) with implications, cause-and-effect, forward-looking analysis

4. Add 2-3 H3 subsections when content exceeds 500 words

FORBIDDEN LABELS (never include these in output):
- "Opening paragraph:"
- "Analysis paragraph:"
- "Strategic analysis paragraph:"
- "Bullet list:"
- Any section labels as literal text
</section_structure>

<content_richness_rules>
- ALWAYS start with data-rich paragraph (policy details, economic indicators, demographic data)
- ALWAYS include bullet points with 5-8 specific insights with exact numbers
- ALWAYS end with implications and strategic analysis
- Extract exact figures: GDP data, policy dates, demographic percentages, regulatory costs
- Include quantitative analysis: percentages, growth rates, market values
- Present comparative insights: "25% higher than regional average"
- Highlight cause-and-effect relationships with evidence
- Use concrete examples: organization names, policy titles, case studies
</content_richness_rules>

<citation_rules>
Use the "citation_number" field from each fact's JSON. Multiple facts may share the same citation number if from the same source - this is correct.
</citation_rules>

<part_c_recommendations>
**Recommendations Requirements:**
- Count: EXACTLY 4-7 numbered recommendations
- Length: Each as ONE paragraph (300-400 words)
- Structure: "[Number]. [Action/Subject] should [specific action] to [outcome/benefit] [citation]."

**Examples:**
1. "Insurtech startups in Ghana should partner with pharmacy chains to bundle affordable accident coverage at checkout, leveraging existing trust in local health networks rather than investing in costly agent networks [3]."
2. "Founders in the mobility sector in Rwanda should focus on peri-urban women commuters, who face 2x higher daily wait times and have 40% less access to app-based ride options compared to men in city centers [1]."
3. "Retail tech startups in Côte d'Ivoire should pilot SMS-based inventory alerts through informal market wholesalers to bypass smartphone limitations among street vendors, a group that constitutes over 60% of micro-retailers [2]."
4. "Agri-data startups in Senegal should launch a no-code dashboard MVP for weather and crop predictions and test its usability with co-ops in the Kaolack region, where farming groups lack real-time advisory tools but have strong WhatsApp adoption [7]."
</part_c_recommendations>

<recommendation_rules>
**MANDATORY:**
- Address specific problem from research_spec (not general industry advice)
- Ground in facts and citations (actual data, stakeholder names, growth numbers)
- Be specific, actionable, and data-driven
- Be founder-led, feasible, and motivated by data
- Each paragraph must include at least one citation [n]

**FORBIDDEN (Non-Founder Actions):**
- "National governments reforming regulations"
- "Central banks or ministries streamlining processes"
- "Telecoms building infrastructure"
- "NGOs launching literacy campaigns"
- "General calls for awareness building or stakeholder collaboration"

**FOCUS ON (Founder Actions):**
- Pivoting business models
- Partnering with existing providers
- Targeting underserved segments
- Using alternative distribution channels
- Creating tech workarounds
- Building MVPs that validate specific market gaps
</recommendation_rules>

<recommendation_lenses>
Craft recommendations by interrogating through these lenses:
1. **Emerging Problems & Desirability**: Top 2-3 unmet problems, existing alternatives, distribution gaps
2. **Next-Stage Research**: Data gaps, areas for deeper investigation, status quo beneficiaries
3. **Key Stakeholders & Institutions**: Government/regulatory bodies pivotal to solving the problem
4. **Emerging Key Insights**: Affected customer segments, barriers (affordability, accessibility, awareness, etc.), enabling/hindering policies
5. **Leverage Points**: Underserved segments, enabling factors, distribution opportunities
</recommendation_lenses>

<tables_instruction>
If tabular data exists in facts (comma-, tab-, or pipe-delimited rows):
- Convert to JSON table format
- Replace in narrative with `{{{{TABLE: My Table Title}}}}`
- If no tabular data: output `"tables": {{}}`
</tables_instruction>

<data_extraction_guidelines>
- **EXTRACT**: Exact numbers, percentages, dates, policy details, economic indicators
- **CONTEXT**: Explain implications for industry/market
- **RELATIONSHIPS**: Show how PESTEL factors interact and influence each other
- **IMPACTS**: How each factor affects business operations, market dynamics, opportunities
- **EXAMPLES**: Specific regulations, policies, companies, events from facts
- **CITATIONS**: Use ONLY citation numbers from input, UNIQUE sequential [1], [2], [3]
- **FORBIDDEN**: Inventing sources or changing URLs
</data_extraction_guidelines>

<source_list_rules>
- Every citation number used MUST appear in `"sources"` array
- URLs must match input exactly - no placeholders
</source_list_rules>

<output_format>
Respond with VALID JSON ONLY - no extra commentary.
</output_format>

<json_schema>
{{
  "report": {{
    "title": "PESTEL Analysis: [Industry/Market Name]",
    "summary": "[300-400 words executive summary]",
    "analysis": [
      {{
        "heading": "[H2 Section Title]",
        "content": "[Markdown text with citations [1][2]]",
        "subsections": [
          {{
            "heading": "[Optional H3 Title]",
            "content": "[Markdown text with citations [3]]"
          }}
        ]
      }}
    ],
    "tables": {{
      "[Table Title]": {{
        "headers": ["Col1", "Col2"],
        "rows": [["R1C1", "R1C2"], ["R2C1", "R2C2"]]
      }}
    }},
    "recommendations": [
      "[Full-paragraph recommendation with citation [4]]",
      "[4-7 total recommendations]"
    ],
    "sources": [
      {{ "number": 1, "title": "Source Title", "url": "https://..." }}
    ]
  }}
}}
</json_schema>

<critical_reminder>
No placeholder URLs like example.com - use only real URLs from input facts.
</critical_reminder>
"""
