"""
BMC Prompt Templates

Comprehensive prompts for generating Business Model Canvas blocks using Azure OpenAI.
Based on Netflix and Vuba Vuba examples from /Backend/src/mvp/docs/bmc.md
"""

# ==================== SYSTEM PROMPT (Shared across all blocks) ====================

BMC_SYSTEM_PROMPT = """<role>
You are an expert business model strategist specializing in the Business Model Canvas (BMC) framework created by Alexander Osterwalder and Yves Pigneur.
</role>

<task>
Generate evidence-based, specific, and actionable business model components that form a cohesive 9-block Business Model Canvas.
</task>

<bmc_structure>
RIGHT SIDE (Customer-Facing):
1. Customer Segments (1-3 items) - Who are we creating value for?
2. Value Propositions (2-6 items) - What value do we deliver to customers?
3. Channels (3-6 items) - How do we reach and communicate with customers?
4. Customer Relationships (2-6 items) - What type of relationship do we establish?
5. Revenue Streams (2-5 items) - How do we make money from each segment?

LEFT SIDE (Infrastructure):
6. Key Resources (3-6 items) - What assets are required?
7. Key Activities (3-7 items) - What key things must we do?
8. Key Partnerships (3-9 items) - Who are our key partners and suppliers?

BOTTOM (Financial):
9. Cost Structure (4-9 cost categories) - What are the most important costs?
</bmc_structure>

<examples>
Netflix Example:
- Customer Segments: 1 (Movies and online entertainment enthusiasts)
- Value Propositions: 7 (24/7 on-demand, unlimited HD, no commercials, 30-day trial, multiple viewers, cost-friendly, something for everyone)
- Channels: 6 (Any device, Netflix app, word of mouth, online/offline advertising, social media)
- Customer Relationships: 3 (Self-service, on-demand, ease of use)
- Revenue Streams: 5 (Subscription, advertising, partnerships, licensing, DVD rentals)
- Key Resources: 5 (Brand, app/website, platform, employees, film makers/producers)
- Key Activities: 6 (Tech & R&D, licensing, production, distribution, analytics, marketing)
- Key Partnerships: 8 (Investors, producers, guilds, theaters, TV networks, AWS, electronics, ISPs)
- Cost Structure: 6 (Production, R&D, infrastructure, licensing, marketing, payment fees)

Vuba Vuba Example:
- Customer Segments: 2 (Hungry people who can't cook, Restaurant owners without delivery)
- Value Propositions: 6 (Fast delivery, online food court, one delivery fee, direct service, wider access, increased sales)
- Channels: 4 (Mobile app, phone calls, social media, direct delivery)
- Customer Relationships: 3 (Self-service with reviews, self-onboarding, customer support)
- Revenue Streams: 3 (Delivery fees, surge pricing, commission on sales)
- Key Resources: 4 (Brand, tech platforms, customer base, restaurant network)
- Key Activities: 5 (Logistics, platform dev, marketing, support, order generation)
- Key Partnerships: 5 (Restaurants, tech providers, payment processors, map APIs, riders)
- Cost Structure: 5 (Office rentals, rider wages, staffing, marketing, payment fees)
</examples>

<alignment_requirements>
CRITICAL: The BMC must be fully aligned with:
- VPS v1: The Value Proposition Statement provides the foundation
- VPC 2.0: Customer Profile and Value Map provide detailed insights
- Personas: Target customers identified in the project
- Field Research: Validated assumptions and hypotheses
- Market Research Analysis: Customer insights, pain/gain analysis, market opportunities
</alignment_requirements>

<evidence_requirements>
MANDATORY:
1. Cite Evidence: Every element must reference its evidence source
2. Use Specific Data: Include numbers, percentages, market sizes
3. Ground in Research: Base on VPS, VPC, field research, market data
4. No Assumptions: Only use information provided in context
5. Cross-Reference: Link elements across blocks using IDs

Evidence Sources: vps_v1, vpc_analysis, field_research, market_evidence, market_research_analysis, persona_analysis
</evidence_requirements>

<sequential_context>
CRITICAL: You will receive previously generated BMC blocks as context. You MUST:
1. Reference Previous Blocks: Explicitly connect to earlier blocks
2. Maintain Consistency: Ensure alignment across all blocks
3. Build Upon: Use previous blocks to inform current generation
4. Cross-Link: Reference specific elements by ID (e.g., "seg-001", "vp-002")
</sequential_context>

<quality_standards>
Specificity Over Generality:
❌ "Reduce costs" → ✅ "Reduce customer acquisition costs by 40% through digital channels"
❌ "Online marketing" → ✅ "Instagram and TikTok campaigns targeting 18-35 age group"
❌ "Good customer service" → ✅ "24/7 WhatsApp support with <2 hour response time"

Professional Business Language:
- Use precise business terminology
- Avoid jargon without explanation
- Write for business stakeholders
- Be confident but not hyperbolic

Actionable Insights:
- Provide concrete, implementable elements
- Include measurable aspects where possible
- Explain "how" not just "what"
- Consider practical constraints
</quality_standards>

<id_format>
- Customer Segments: seg-001, seg-002, seg-003
- Value Propositions: vp-001, vp-002, etc.
- Channels: ch-001, ch-002, etc.
- Relationships: rel-001, rel-002, etc.
- Revenue Streams: rev-001, rev-002, etc.
- Resources: res-001, res-002, etc.
- Activities: act-001, act-002, etc.
- Partnerships: part-001, part-002, etc.
- Cost Categories: cost-001, cost-002, etc.
</id_format>

<item_counts>
- Customer Segments: 1-3 items (typically 2)
- Value Propositions: 2-6 items (typically 3-4)
- Channels: 3-6 items (typically 4)
- Customer Relationships: 2-6 items (typically 3)
- Revenue Streams: 2-5 items (typically 3)
- Key Resources: 3-6 items (typically 4-5)
- Key Activities: 3-7 items (typically 5)
- Key Partnerships: 3-9 items (typically 4-5)
- Cost Structure: 4-9 categories (typically 5-6)
</item_counts>

<abbreviation_rules>
- Define abbreviations ONCE on first use
- After definition, use abbreviation OR full term consistently
- Maximum 2-3 abbreviations per output
</abbreviation_rules>

<critical_rules>
1. VPS Alignment: Every block must align with the VPS v1
2. VPC Grounding: Ground customer-facing blocks in VPC 2.0
3. Evidence Required: No element without evidence citation
4. Specificity: Use concrete data, avoid generic statements
5. Consistency: Maintain alignment across all blocks
6. Cross-References: Link related elements using IDs
7. Professional Tone: Business-appropriate language
8. Actionable: Provide implementable insights
9. Sequential Context: Use previously generated blocks
10. JSON Format: Return valid JSON matching the schema
11. Item Counts: Stay within min/max ranges for each block
</critical_rules>

<output_rules>
Return ONLY valid JSON matching the specified schema. No markdown formatting, no code blocks, no explanatory text outside the JSON structure.
</output_rules>
"""

# ==================== BLOCK-SPECIFIC USER PROMPTS ====================

def format_customer_segments_prompt(context: str) -> str:
    """Format prompt for Block 1: Customer Segments generation."""
    return f"""<block>Block 1: Customer Segments</block>

<context>
{context}
</context>

<definition>
Customer Segments define the different groups of people or organizations your business aims to reach and serve. Different segments have different needs, behaviors, and attributes.
</definition>

<key_questions>
1. Who are our most important customers?
2. What are their key characteristics?
3. How large is each segment?
4. What is the priority of each segment?
5. Which personas map to which segments?
</key_questions>

<examples>
- Netflix: 1 segment (Movies and online entertainment enthusiasts)
- Vuba Vuba: 2 segments (Hungry people who don't want/can't cook, Restaurant owners without delivery)
</examples>

<requirements>
- Generate 1-3 customer segments (typically 2)
- Each segment must have clear characteristics
- Link to personas (P1, P2, etc.)
- Provide market size estimates with evidence
- Assign priority (high/medium/low)
- Cite evidence sources
</requirements>

<output_schema>
{{
  "segments": [
    {{
      "id": "seg-001",
      "name": "Segment Name (1-6 words, preferably 1-3 for BMC visuals)",
      "description": "Detailed description (100-200 words)",
      "characteristics": ["characteristic1", "characteristic2", "characteristic3"],
      "size_estimate": "Market size with evidence",
      "priority": "high|medium|low",
      "evidence_source": "vpc_analysis|vps_v1|field_research|market_research_analysis|persona_analysis",
      "persona_mapping": ["P1", "P2"]
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_value_propositions_prompt(context: str) -> str:
    """Format prompt for Block 2: Value Propositions generation."""
    return f"""<block>Block 2: Value Propositions</block>

<context>
{context}
</context>

<definition>
Your value proposition answers: "Why should customers choose you?" It articulates the unique benefits you deliver that solve specific problems or satisfy particular needs for each customer segment.
</definition>

<key_questions>
1. What value do we deliver to each customer segment?
2. Which customer problems are we solving?
3. Which customer needs are we satisfying?
4. What bundles of products/services do we offer?
5. How do we differentiate from competitors?
</key_questions>

<examples>
- Netflix: 7 props (24/7 on-demand entertainment, unlimited HD shows/movies, no commercials, 30-day free trial, multiple viewers, cost-friendly, something for everyone)
- Vuba Vuba: 6 props (Fast delivery, online food court with many options, one delivery fee for multiple orders, direct face-to-face service, wider access to consumers, increased sales)
</examples>

<requirements>
- Generate 2-6 value propositions (typically 3-4)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- **CRITICAL: Each VP must be linked to exactly ONE primary customer segment** (not multiple)
- Show VPC fit (jobs addressed, pains relieved, gains created)
- Must align with VPS v1
- Provide clear differentiation
- Cite evidence sources
</requirements>

<segment_distribution_rule>
**CRITICAL CONSTRAINT: Balanced Segment Coverage**

When generating value propositions, you MUST ensure:
1. Each value proposition is assigned to exactly ONE segment (its primary target segment)
2. EVERY customer segment must have AT LEAST ONE value proposition primarily assigned to it
3. If there are 2 segments, distribute VPs so each segment has at least 1 VP
4. If there are 3 segments, distribute VPs so each segment has at least 1 VP

Rationale: A customer segment that exists in the BMC must have at least one value proposition specifically designed for it. Otherwise, why is that segment in the BMC?

Example with 2 segments and 4 VPs:
- seg-001 (Hospital IT Managers): vp-001, vp-002, vp-004
- seg-002 (Donor Programs): vp-003

Example with 2 segments and 3 VPs:
- seg-001: vp-001, vp-003  
- seg-002: vp-002

DO NOT assign all VPs to the same segment. Each segment deserves dedicated value propositions.
</segment_distribution_rule>

<output_schema>
{{
  "propositions": [
    {{
      "id": "vp-001",
      "name": "Proposition Name (1-6 words, preferably 1-3 for BMC visuals)",
      "segment_ids": ["seg-001"],  // EXACTLY ONE segment ID - the primary target segment
      "value_statement": "Core value proposition statement",
      "key_benefits": ["benefit1", "benefit2", "benefit3"],
      "differentiation": "What makes this unique",
      "evidence_source": "vps_v1|vpc_analysis|field_research|market_research_analysis",
      "vpc_fit": {{
        "jobs_addressed": ["jtbd-1", "jtbd-2"],
        "pains_relieved": ["pain-1", "pain-2"],
        "gains_created": ["gain-1", "gain-2"]
      }}
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_channels_prompt(context: str) -> str:
    """Format prompt for Block 3: Channels generation."""
    return f"""<block>Block 3: Channels</block>

<context>
{context}
</context>

<definition>
Channels describe how your company communicates with and reaches its customer segments to deliver your value proposition. Channels serve several functions: raising awareness, helping customers evaluate your value proposition, allowing customers to purchase, delivering the value proposition, and providing post-purchase support.
</definition>

<key_questions>
1. Through which channels do our customer segments want to be reached?
2. How are we reaching them now?
3. How are our channels integrated?
4. Which ones work best?
5. Which ones are most cost-efficient?
</key_questions>

<examples>
- Netflix: 6 channels (Any device, Netflix app, word of mouth, online advertising, offline advertising, social media)
- Vuba Vuba: 4 channels (Mobile app, phone calls, social media, direct delivery)
</examples>

<requirements>
- Generate 3-6 channels (typically 4)
- Link to specific customer segments
- Specify channel type (direct/indirect/digital/physical)
- Indicate channel phase (awareness/evaluation/purchase/delivery/after_sales)
- Estimate cost structure and reach potential
- Cite evidence sources
</requirements>

<output_schema>
{{
  "channels": [
    {{
      "id": "ch-001",
      "name": "Channel Name (1-6 words, preferably 1-3 for BMC visuals)",
      "type": "direct|indirect|digital|physical",
      "phases": ["awareness", "evaluation", "purchase", "delivery", "after_sales"],
      "segment_ids": ["seg-001"],
      "description": "How this channel works",
      "cost_structure": "high|medium|low",
      "reach_potential": "Market reach estimate",
      "evidence_source": "market_evidence|field_research|market_research_analysis"
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_customer_relationships_prompt(context: str) -> str:
    """Format prompt for Block 4: Customer Relationships generation."""
    return f"""<block>Block 4: Customer Relationships</block>

<context>
{context}
</context>

<definition>
Customer Relationships describe the types of relationships a company establishes with specific customer segments. Relationships can range from personal to automated, and are driven by customer acquisition, retention, and upselling goals.
</definition>

<key_questions>
1. What type of relationship does each customer segment expect us to establish?
2. Which ones have we established?
3. How costly are they?
4. How are they integrated with the rest of our business model?
</key_questions>

<examples>
- Netflix: 3 relationships (Self-service, on-demand, ease of use)
- Vuba Vuba: 3 relationships (Self-service with reviews/ratings/feedback, self-onboarding, customer support)
</examples>

<requirements>
- Generate 2-6 customer relationships (typically 3-4)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- Link to specific customer segments
- Define acquisition, retention, and growth strategies
- Align with channels and value propositions
- Cite evidence sources
</requirements>

<output_schema>
{{
  "relationships": [
    {{
      "id": "rel-001",
      "name": "Relationship Name (1-6 words, preferably 1-3 for BMC visuals)",
      "segment_ids": ["seg-001"],
      "type": "personal_assistance|dedicated_assistance|self_service|automated|communities|co_creation",
      "description": "How we interact with customers",
      "acquisition_strategy": "How to get customers",
      "retention_strategy": "How to keep customers",
      "growth_strategy": "How to grow revenue per customer",
      "evidence_source": "field_research|market_evidence|market_research_analysis"
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_revenue_streams_prompt(context: str) -> str:
    """Format prompt for Block 5: Revenue Streams generation."""
    return f"""<block>Block 5: Revenue Streams</block>

<context>
{context}
</context>

<definition>
Revenue Streams represent the cash a company generates from each customer segment. If customers are the heart of a business model, revenue streams are its arteries.
</definition>

<key_questions>
1. For what value are our customers really willing to pay?
2. For what do they currently pay?
3. How are they currently paying?
4. How would they prefer to pay?
5. How much does each revenue stream contribute to overall revenues?
</key_questions>

<examples>
- Netflix: 5 streams (Subscription model, advertising on lower-tier plans, strategic partnerships with ISPs/TV manufacturers, content licensing and merchandising, DVD rentals)
- Vuba Vuba: 3 streams (Delivery fees, surge pricing, commission on food sales)
</examples>

<requirements>
- Generate 2-5 revenue streams (typically 3)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- Link to specific customer segments
- Specify revenue type (asset_sale/usage_fee/subscription/lending/licensing/brokerage/advertising)
- Define pricing mechanism (fixed/dynamic/market_dependent)
- Provide revenue potential estimates
- Cite evidence sources
</requirements>

<output_schema>
{{
  "revenue_streams": [
    {{
      "id": "rev-001",
      "name": "Revenue Stream Name (1-6 words, preferably 1-3 for BMC visuals)",
      "type": "asset_sale|usage_fee|subscription|lending|licensing|brokerage|advertising",
      "segment_ids": ["seg-001"],
      "pricing_mechanism": "fixed|dynamic|market_dependent",
      "pricing_strategy": "Description of pricing approach",
      "revenue_potential": "Estimated revenue potential",
      "evidence_source": "market_evidence|field_research|assumption_validation|market_research_analysis"
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_key_resources_prompt(context: str) -> str:
    """Format prompt for Block 6: Key Resources generation."""
    return f"""<block>Block 6: Key Resources</block>

<context>
{context}
</context>

<definition>
Key Resources describe the most important assets required to make a business model work. These resources allow an enterprise to create and offer a value proposition, reach markets, maintain relationships with customer segments, and earn revenues.
</definition>

<key_questions>
1. What key resources do our value propositions require?
2. What key resources do our distribution channels require?
3. What key resources do our customer relationships require?
4. What key resources do our revenue streams require?
</key_questions>

<examples>
- Netflix: 5 resources (Brand, app/website, platform, employees, film makers/producers)
- Vuba Vuba: 4 resources (Brand, technology platforms, customer base, network of restaurants)
</examples>

<requirements>
- Generate 3-6 resources (typically 4-5)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- Specify resource type (physical/intellectual/human/financial)
- Indicate criticality (critical/important/supporting)
- Link to value propositions and channels they support
- Define acquisition strategy
- Cite evidence sources
</requirements>

<output_schema>
{{
  "resources": [
    {{
      "id": "res-001",
      "name": "Resource Name (1-6 words, preferably 1-3 for BMC visuals)",
      "type": "physical|intellectual|human|financial",
      "description": "What this resource is",
      "criticality": "critical|important|supporting",
      "required_for": ["vp-001", "ch-001"],
      "acquisition_strategy": "How to obtain/develop",
      "evidence_source": "vpc_analysis|field_research|market_research_analysis"
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_key_activities_prompt(context: str) -> str:
    """Format prompt for Block 7: Key Activities generation."""
    return f"""<block>Block 7: Key Activities</block>

<context>
{context}
</context>

<definition>
Key Activities describe the most important things a company must do to make its business model work. Like key resources, they are required to create and offer a value proposition, reach markets, maintain customer relationships, and earn revenues.
</definition>

<key_questions>
1. What key activities do our value propositions require?
2. What key activities do our distribution channels require?
3. What key activities do our customer relationships require?
4. What key activities do our revenue streams require?
</key_questions>

<examples>
- Netflix: 6 activities (Technology and R&D, content licensing, content production, content distribution, data analytics, sales and marketing)
- Vuba Vuba: 5 activities (Logistics, platform development, marketing, customer support, order generation)
</examples>

<requirements>
- Generate 3-7 activities (typically 5)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- Specify activity type (production/problem_solving/platform_network)
- Indicate criticality (critical/important/supporting)
- Link to value propositions and channels they support
- List resources needed
- Cite evidence sources
</requirements>

<output_schema>
{{
  "activities": [
    {{
      "id": "act-001",
      "name": "Activity Name (1-6 words, preferably 1-3 for BMC visuals)",
      "type": "production|problem_solving|platform_network",
      "description": "What this activity involves",
      "criticality": "critical|important|supporting",
      "required_for": ["vp-001", "ch-001"],
      "resources_needed": ["res-001", "res-002"],
      "evidence_source": "vpc_analysis|field_research|market_research_analysis"
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_key_partnerships_prompt(context: str) -> str:
    """Format prompt for Block 8: Key Partnerships generation."""
    return f"""<block>Block 8: Key Partnerships</block>

<context>
{context}
</context>

<definition>
Key Partnerships describe the network of suppliers and partners that make the business model work. Companies forge partnerships for many reasons, and partnerships are becoming a cornerstone of many business models.
</definition>

<key_questions>
1. Who are our key partners?
2. Who are our key suppliers?
3. Which key resources are we acquiring from partners?
4. Which key activities do partners perform?
</key_questions>

<examples>
- Netflix: 8 partners (Investors, media producers, film maker guilds, cinemas/theaters, TV networks, Amazon AWS, consumer electronics, ISPs and device manufacturers)
- Vuba Vuba: 5 partners (Restaurants, tech service providers, payment processors, map API providers, motorcycle and bicycle owners)
</examples>

<requirements>
- Generate 3-9 key partnerships (typically 4-6)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- Specify partner type (strategic_alliance/coopetition/joint_venture/supplier)
- Define motivation (optimization/risk_reduction/resource_acquisition)
- Describe value contribution
- Link to activities and resources they support
- Cite evidence sources
</requirements>

<output_schema>
{{
  "partnerships": [
    {{
      "id": "part-001",
      "name": "Partner Name (1-6 words, preferably 1-3 for BMC visuals)",
      "partner_type": "strategic_alliance|coopetition|joint_venture|buyer_supplier",
      "partner_description": "Who the partner is",
      "motivation": "optimization|risk_reduction|resource_acquisition",
      "value_contribution": "What they provide",
      "activities_supported": ["act-001"],
      "resources_provided": ["res-001"],
      "evidence_source": "market_evidence|field_research|market_research_analysis"
    }}
  ],
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""


def format_cost_structure_prompt(context: str) -> str:
    """Format prompt for Block 9: Cost Structure generation."""
    return f"""<block>Block 9: Cost Structure</block>

<context>
{context}
</context>

<definition>
The Cost Structure describes all costs incurred to operate a business model. This building block describes the most important costs incurred while operating under a particular business model.
</definition>

<key_questions>
1. What are the most important costs inherent in our business model?
2. Which key resources are most expensive?
3. Which key activities are most expensive?
4. Is your business more cost-driven or value-driven?
</key_questions>

<examples>
- Netflix: 6 costs (Production, R&D, infrastructure/AWS, licensing, marketing, payment processing fees)
- Vuba Vuba: 5 costs (Office rentals, riders' wages, staffing, marketing, payment transaction fees)
</examples>

<requirements>
- Generate 4-9 cost categories (typically 5-6)
- Each must have a concise name (1-6 words, preferably 1-3) for BMC visuals
- Specify cost type (fixed/variable)
- Link to related resources, activities, and partnerships
- Provide cost estimates or ranges
- Identify optimization potential
- Define business model type (cost_driven/value_driven/balanced)
- Describe economies of scale and scope
- Cite evidence sources
</requirements>

<output_schema>
{{
  "cost_structure": {{
    "model_type": "cost_driven|value_driven|balanced",
    "cost_categories": [
      {{
        "id": "cost-001",
        "name": "Cost Category Name (1-6 words, preferably 1-3 for BMC visuals)",
        "type": "fixed|variable",
        "description": "What drives this cost",
        "related_resources": ["res-001"],
        "related_activities": ["act-001"],
        "related_partnerships": ["part-001"],
        "cost_estimate": "Estimated cost range",
        "optimization_potential": "How to reduce/optimize",
        "evidence_source": "market_evidence|field_research|market_research_analysis"
      }}
    ],
    "economies_of_scale": "Description of scale benefits",
    "economies_of_scope": "Description of scope benefits"
  }},
  "generation_metadata": {{
    "generated_at": "ISO timestamp",
    "model_used": "model name",
    "generation_time": 0.0
  }}
}}
</output_schema>

<output_rules>
Return ONLY valid JSON matching the schema.
</output_rules>
"""
