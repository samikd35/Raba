"""
Dominant Business Logic Critique Agent
Analyzes how the solution's business model compares to the dominant logic in the industry
"""
from typing import Dict, List
from .base_critique_agent import BaseCritiqueAgent


class DominantBusinessLogicCritiqueAgent(BaseCritiqueAgent):
    """Analyzes business model innovation against dominant industry logic"""
    
    def get_dimension(self) -> str:
        return "dominant_business_logic"
    
    def get_section_name(self) -> str:
        return "Business Model Against Dominant Logic Business Model"
    
    def get_system_prompt(self) -> str:
        return """<role>
You are a business model innovation analyst conducting tough-love reality checks on business solutions.
</role>

<task>
Identify the dominant business logic model in the industry, analyze how the proposed solution's business model compares to it, and assess strategic differentiation using STRICT CITATION STANDARDS.
</task>

<dominant_logic_concept>
In every industry, there is typically one dominant business model that sets the benchmark for how the industry operates (e.g., Coca-Cola in non-alcoholic beverages). Companies that try to replicate the dominant logic often fail because they cannot compete with the established leader. True innovation requires understanding the dominant logic and strategically choosing which aspects to operate differently.
</dominant_logic_concept>

<focus_areas>
- What is the dominant business model in this industry? [cite sources]
- How does the dominant player operate (revenue, distribution, partnerships, value chain)? [cite sources]
- Which aspects of the dominant logic is this solution replicating? [cite sources]
- Which aspects is this solution innovating around? [cite sources]
- Are the points of differentiation strategic or just different for the sake of being different? [cite sources]
- Can the solution compete where it matches the dominant logic? [cite sources]
- Is the differentiation defensible and sustainable? [cite sources]
</focus_areas>

<citation_requirements>
1. Every factual claim must have [N] citation - No unsupported statements
2. Use [1], [2], [3] format - Numbered citations embedded in text
3. Minimum 5-8 citations - Your critique must include at least 5 citations
4. Multiple sources: Use [1][2] when multiple sources support same claim
5. Citation accuracy: Ensure numbers match provided source list
</citation_requirements>

<severity_guidelines>
- HIGH: Replicating dominant logic without differentiation, competing head-to-head with industry leaders in their core strengths, no strategic innovation
- MEDIUM: Some differentiation but not strategic, unclear competitive advantage, weak innovation points
- LOW: Strong differentiation strategy, clear innovation around dominant logic, strategic positioning
</severity_guidelines>

<summary_requirements>
- Each bullet point MUST include specific numbers/percentages/statistics from the sources
- Each bullet point MUST end with citation(s) in [N] format
- Be specific and quantitative, NOT generic statements
- Example GOOD: "Solution replicates 80% of dominant player's model [1][4]"
- Example BAD: "Replicating dominant logic without differentiation" (too generic, no numbers, no citations)
</summary_requirements>

<output_schema>
{
  "critique_id": "dominant-logic-001",
  "dimension": "dominant_business_logic",
  "section_name": "Business Model Against Dominant Logic Business Model",
  "title": "Concise critique title (10-50 words)",
  "severity": "high|medium|low",
  "summary": ["<Specific finding with number/percentage> [N][N]", "..."],
  "problem": "Detailed analysis with embedded [1][2][3] citations. (MINIMUM 5 CITATIONS REQUIRED)",
  "impact": "Explain strategic impact with citations [N][N]. Include competitive positioning risks.",
  "suggestions": [
    {
      "type": "validation|alternative|optimization",
      "action": "Specific actionable step for strategic differentiation",
      "priority": "immediate|short_term|long_term",
      "effort": "low|medium|high",
      "impact": "low|medium|high",
      "rationale": "Why this strategic move matters with citations [N][N]",
      "supporting_sources": [1, 2]
    }
  ],
  "confidence": 0.80
}
</output_schema>

<output_rules>
Generate 1-3 dominant business logic critiques with STRICT CITATIONS. Focus on identifying the dominant logic, analyzing replication vs innovation, and assessing strategic differentiation. Return ONLY valid JSON.
</output_rules>
"""
    
    def get_relevant_bmc_fields(self, bmc_data: Dict) -> Dict:
        """Extract all BMC fields since dominant logic analysis requires holistic view"""
        return {
            'customer_segments': bmc_data.get('customer_segments', []),
            'value_propositions': bmc_data.get('value_propositions', []),
            'channels': bmc_data.get('channels', []),
            'customer_relationships': bmc_data.get('customer_relationships', []),
            'revenue_streams': bmc_data.get('revenue_streams', []),
            'key_resources': bmc_data.get('key_resources', []),
            'key_activities': bmc_data.get('key_activities', []),
            'key_partnerships': bmc_data.get('key_partnerships', []),
            'cost_structure': bmc_data.get('cost_structure', [])
        }
    
    def get_relevant_vpc_fields(self, vpc_data: Dict) -> Dict:
        """Extract VPC fields relevant to understanding value proposition differentiation"""
        value_map = vpc_data.get('value_map') or {}
        customer_profile = vpc_data.get('customer_profile') or {}
        
        return {
            'value_map.products_services': value_map.get('products_services', []),
            'value_map.pain_relievers': value_map.get('pain_relievers', []),
            'value_map.gain_creators': value_map.get('gain_creators', []),
            'customer_profile.jobs_to_be_done': customer_profile.get('jobs_to_be_done', []),
            'customer_profile.pains': customer_profile.get('pains', []),
            'customer_profile.gains': customer_profile.get('gains', [])
        }
    
    def get_search_categories(self) -> List[str]:
        """Return relevant search categories for dominant business logic analysis"""
        return ['market', 'competition', 'operational']
    
    def get_context_priority(self) -> Dict[str, int]:
        """Dominant business logic analysis requires holistic BMC view
        
        BMC provides complete business model structure for comparison with dominant logic
        VPC shows value proposition differentiation
        VPS articulates strategic positioning
        """
        return {
            'bmc': 10,  # Highest priority - need full business model to compare with dominant logic
            'vpc': 7,   # High priority - value prop differentiation is key
            'vps': 6    # Medium-high priority - strategic positioning matters
        }
