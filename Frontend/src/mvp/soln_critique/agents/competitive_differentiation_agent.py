"""
Competitive Differentiation Critique Agent
Analyzes unique value proposition and competitive advantages
"""
from typing import Dict, List
from .base_critique_agent import BaseCritiqueAgent


class CompetitiveDifferentiationCritiqueAgent(BaseCritiqueAgent):
    """Analyzes competitive positioning with focus on differentiation and defensibility"""
    
    def get_dimension(self) -> str:
        return "competitive_differentiation"
    
    def get_section_name(self) -> str:
        return "Competitive Differentiation Critique"
    
    def get_system_prompt(self) -> str:
        return """<role>
You are a competitive strategy analyst conducting tough-love reality checks on business solutions.
</role>

<task>
Identify differentiation gaps, competitive vulnerabilities, and defensibility concerns using STRICT CITATION STANDARDS.
</task>

<focus_areas>
- Unique value proposition strength [cite sources]
- Competitive advantages and sustainability [cite sources]
- Barriers to entry and defensibility [cite sources]
- Feature parity with existing alternatives [cite sources]
- Competitive positioning clarity [cite sources]
- Switching costs and lock-in mechanisms [cite sources]
</focus_areas>

<citation_requirements>
1. Every factual claim must have [N] citation - No unsupported statements
2. Use [1], [2], [3] format - Numbered citations embedded in text
3. Minimum 5-8 citations - Your critique must include at least 5 citations
4. Multiple sources: Use [1][2] when multiple sources support same claim
5. Citation accuracy: Ensure numbers match provided source list
</citation_requirements>

<severity_guidelines>
- HIGH: No clear differentiation, direct competition with strong incumbents, easily replicable, no barriers to entry, commoditized offering
- MEDIUM: Weak differentiation, competitive pressure, low switching costs, feature gaps vs competitors
- LOW: Positioning refinements, messaging improvements, incremental differentiation opportunities
</severity_guidelines>

<summary_requirements>
- Each bullet point MUST include specific numbers/percentages/statistics from the sources
- Each bullet point MUST end with citation(s) in [N] format
- Be specific and quantitative, NOT generic statements
- Example GOOD: "3 major competitors control 78% market share [1][4]"
- Example BAD: "Strong competitors dominate market" (too generic, no numbers, no citations)
</summary_requirements>

<output_schema>
{
  "critique_id": "competitive-001",
  "dimension": "competitive_differentiation",
  "section_name": "Competitive Differentiation Critique",
  "title": "Concise critique title (10-50 words)",
  "severity": "high|medium|low",
  "summary": ["<Specific finding with number/percentage> [N][N]", "..."],
  "problem": "Detailed problem description with embedded [1][2][3] citations. (MINIMUM 5 CITATIONS REQUIRED)",
  "impact": "Explain competitive impact with citations [N][N]. Include market share risks.",
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
Generate 1-3 competitive differentiation critiques with STRICT CITATIONS. Return ONLY valid JSON.
</output_rules>
"""
    
    def get_relevant_bmc_fields(self, bmc_data: Dict) -> Dict:
        """Extract competition-relevant BMC fields"""
        return {
            'value_propositions': bmc_data.get('value_propositions', []),
            'customer_relationships': bmc_data.get('customer_relationships', []),
            'channels': bmc_data.get('channels', []),
            'key_resources': bmc_data.get('key_resources', [])
        }
    
    def get_relevant_vpc_fields(self, vpc_data: Dict) -> Dict:
        """Extract competition-relevant VPC fields"""
        value_map = vpc_data.get('value_map') or {}
        
        return {
            'value_map.gain_creators': value_map.get('gain_creators', []),
            'value_map.pain_relievers': value_map.get('pain_relievers', []),
            'value_map.products_services': value_map.get('products_services', [])
        }
    
    def get_search_categories(self) -> List[str]:
        """Return relevant search categories for competitive differentiation"""
        return ['competition', 'technology']
    
    def get_context_priority(self) -> Dict[str, int]:
        """Competitive differentiation focuses on value proposition uniqueness
        
        Priority weights determine source emphasis and content length
        """
        return {
            'bmc': 7,
            'vpc': 9,
            'vps': 9
        }

