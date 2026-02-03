"""
Market Viability Critique Agent
Analyzes market demand, size, and customer validation
"""
from typing import Dict, List
from .base_critique_agent import BaseCritiqueAgent


class MarketViabilityCritiqueAgent(BaseCritiqueAgent):
    """Analyzes market viability with focus on demand validation and market size"""
    
    def get_dimension(self) -> str:
        return "market_viability"
    
    def get_section_name(self) -> str:
        return "Market Viability Critique"
    
    def get_system_prompt(self) -> str:
        return """<role>
You are a market viability analyst conducting tough-love reality checks on business solutions.
</role>

<task>
Identify market demand gaps, unvalidated assumptions, and market size issues using STRICT CITATION STANDARDS.
</task>

<focus_areas>
- Is there evidence of real customer demand? [cite sources]
- Are market size claims validated? [cite sources]
- Is pricing realistic for the target market? [cite sources]
- Are customer segments clearly defined and reachable? [cite sources]
- Does the solution solve a real, validated problem? [cite sources]
</focus_areas>

<citation_requirements>
1. Every factual claim must have [N] citation - No unsupported statements
2. Use [1], [2], [3] format - Numbered citations embedded in text
3. Minimum 5-8 citations - Your critique must include at least 5 citations
4. Multiple sources: Use [1][2] when multiple sources support same claim
5. Citation accuracy: Ensure numbers match provided source list
</citation_requirements>

<severity_guidelines>
- HIGH: Unvalidated core assumptions, no demand evidence, unrealistic market size, fundamental viability concerns
- MEDIUM: Weak demand signals, questionable pricing, unclear segments, addressable market concerns
- LOW: Market education needed, minor positioning issues, optimization opportunities
</severity_guidelines>

<summary_requirements>
- Each bullet point MUST include specific numbers/percentages/statistics from the sources
- Each bullet point MUST end with citation(s) in [N] format
- Be specific and quantitative, NOT generic statements
- Example GOOD: "Only 15% of farmers willing to pay for advisory services [3][7]"
- Example BAD: "Willingness to pay is unproven" (too generic, no numbers, no citations)
</summary_requirements>

<output_schema>
{
  "critique_id": "market-001",
  "dimension": "market_viability",
  "section_name": "Market Viability Critique",
  "title": "Concise critique title (10-50 words)",
  "severity": "high|medium|low",
  "summary": ["<Specific finding with number/percentage> [N][N]", "..."],
  "problem": "Detailed problem description with embedded [1][2][3] citations. (MINIMUM 5 CITATIONS REQUIRED)",
  "impact": "Explain business impact with citations [N][N]. Include quantified risks.",
  "suggestions": [
    {
      "type": "validation|alternative|optimization",
      "action": "Specific actionable step",
      "priority": "immediate|short_term|long_term",
      "effort": "low|medium|high",
      "impact": "low|medium|high",
      "rationale": "Why this suggestion matters with citations [N][N]",
      "supporting_sources": [1, 2]
    }
  ],
  "confidence": 0.80
}
</output_schema>

<output_rules>
Generate 1-3 market viability critiques with STRICT CITATIONS. Return ONLY valid JSON.
</output_rules>
"""
    
    def get_relevant_bmc_fields(self, bmc_data: Dict) -> Dict:
        """Extract market-relevant BMC fields"""
        return {
            'customer_segments': bmc_data.get('customer_segments', []),
            'value_propositions': bmc_data.get('value_propositions', []),
            'revenue_streams': bmc_data.get('revenue_streams', []),
            'channels': bmc_data.get('channels', [])
        }
    
    def get_relevant_vpc_fields(self, vpc_data: Dict) -> Dict:
        """Extract market-relevant VPC fields"""
        customer_profile = vpc_data.get('customer_profile') or {}
        value_map = vpc_data.get('value_map') or {}
        
        return {
            'customer_profile.jobs_to_be_done': customer_profile.get('jobs_to_be_done', []),
            'customer_profile.pains': customer_profile.get('pains', []),
            'customer_profile.gains': customer_profile.get('gains', []),
            'value_map.products_services': value_map.get('products_services', []),
            'value_map.pain_relievers': value_map.get('pain_relievers', []),
            'value_map.gain_creators': value_map.get('gain_creators', [])
        }
    
    def get_search_categories(self) -> List[str]:
        """Return relevant search categories for market viability"""
        return ['market', 'competition']
    
    def get_context_priority(self) -> Dict[str, int]:
        """Market viability analysis relies heavily on VPC and customer validation
        
        VPC provides deep customer insights - jobs, pains, gains
        BMC shows customer segments and value propositions
        VPS articulates the solution being validated
        """
        return {
            'vpc': 10,  # Highest priority - customer jobs, pains, gains are critical
            'bmc': 7,   # High priority - customer segments and value props
            'vps': 8    # High priority - solution statement for validation
        }
