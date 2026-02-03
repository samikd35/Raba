"""
Business Model Critique Agent
Analyzes revenue model, cost structure, and unit economics
"""
from typing import Dict, List
from .base_critique_agent import BaseCritiqueAgent


class BusinessModelCritiqueAgent(BaseCritiqueAgent):
    """Analyzes business model viability with focus on monetization and profitability"""
    
    def get_dimension(self) -> str:
        return "business_model"
    
    def get_section_name(self) -> str:
        return "Business Model Defensibility Critique"
    
    def get_system_prompt(self) -> str:
        return """<role>
You are a business model analyst conducting tough-love reality checks on business solutions.
</role>

<task>
Identify revenue model gaps, cost structure issues, and profitability concerns using STRICT CITATION STANDARDS.
</task>

<focus_areas>
- Revenue model clarity and realism [cite sources]
- Cost structure completeness and accuracy [cite sources]
- Profit margin viability [cite sources]
- Customer acquisition cost (CAC) vs Lifetime value (LTV) [cite sources]
- Unit economics and scalability [cite sources]
- Monetization strategy feasibility [cite sources]
</focus_areas>

<citation_requirements>
1. Every factual claim must have [N] citation - No unsupported statements
2. Use [1], [2], [3] format - Numbered citations embedded in text
3. Minimum 5-8 citations - Your critique must include at least 5 citations
4. Multiple sources: Use [1][2] when multiple sources support same claim
5. Citation accuracy: Ensure numbers match provided source list
</citation_requirements>

<severity_guidelines>
- HIGH: No clear revenue model, unrealistic pricing, unsustainable costs, broken unit economics, path to profitability unclear
- MEDIUM: Revenue model challenges, high CAC, margin concerns, pricing pressure, competitive pricing dynamics
- LOW: Revenue optimization opportunities, cost efficiency improvements, pricing refinements
</severity_guidelines>

<summary_requirements>
- Each bullet point MUST include specific numbers/percentages/dollar amounts from the sources
- Each bullet point MUST end with citation(s) in [N] format
- Be specific and quantitative, NOT generic statements
- Example GOOD: "CAC of $25 exceeds LTV of $18 by 39% [1][4]"
- Example BAD: "Unit economics are broken" (too generic, no numbers, no citations)
</summary_requirements>

<output_schema>
{
  "critique_id": "business-001",
  "dimension": "business_model",
  "section_name": "Business Model Defensibility Critique",
  "title": "Concise critique title (10-50 words)",
  "severity": "high|medium|low",
  "summary": ["<Specific finding with number/percentage> [N][N]", "..."],
  "problem": "Detailed problem description with embedded [1][2][3] citations. (MINIMUM 5 CITATIONS REQUIRED)",
  "impact": "Explain financial impact with citations [N][N]. Include revenue/cost projections.",
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
Generate 1-3 business model critiques with STRICT CITATIONS. Return ONLY valid JSON.
</output_rules>
"""
    
    def get_relevant_bmc_fields(self, bmc_data: Dict) -> Dict:
        """Extract business-model-relevant BMC fields"""
        return {
            'revenue_streams': bmc_data.get('revenue_streams', []),
            'cost_structure': bmc_data.get('cost_structure', []),
            'key_resources': bmc_data.get('key_resources', []),
            'customer_segments': bmc_data.get('customer_segments', []),
            'value_propositions': bmc_data.get('value_propositions', [])
        }
    
    def get_relevant_vpc_fields(self, vpc_data: Dict) -> Dict:
        """Extract business-model-relevant VPC fields"""
        value_map = vpc_data.get('value_map') or {}
        customer_profile = vpc_data.get('customer_profile') or {}
        
        return {
            'value_map.products_services': value_map.get('products_services', []),
            'customer_profile.pains': customer_profile.get('pains', []),
            'customer_profile.gains': customer_profile.get('gains', [])
        }
    
    def get_search_categories(self) -> List[str]:
        """Return relevant search categories for business model"""
        return ['market', 'competition']
    
    def get_context_priority(self) -> Dict[str, int]:
        """Business model analysis heavily relies on BMC
        
        BMC contains revenue_streams, cost_structure, key_resources - critical for business model critique
        VPC provides customer value context
        VPS provides solution positioning
        """
        return {
            'bmc': 10,  # Highest priority - revenue, costs, resources all in BMC
            'vpc': 6,   # Medium priority - customer value and willingness to pay
            'vps': 5    # Moderate priority - solution positioning
        }
