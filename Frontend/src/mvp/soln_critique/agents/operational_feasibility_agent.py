"""
Operational Feasibility Critique Agent
Analyzes supply chain, regulatory compliance, and operational complexity
"""
from typing import Dict, List
from .base_critique_agent import BaseCritiqueAgent


class OperationalFeasibilityCritiqueAgent(BaseCritiqueAgent):
    """Analyzes operational feasibility with focus on execution challenges"""
    
    def get_dimension(self) -> str:
        return "operational_feasibility"
    
    def get_section_name(self) -> str:
        return "Operational Feasibility Critique"
    
    def get_system_prompt(self) -> str:
        return """<role>
You are an operational feasibility analyst conducting tough-love reality checks on business solutions.
</role>

<task>
Identify operational barriers, regulatory compliance gaps, and execution complexity issues using STRICT CITATION STANDARDS.
</task>

<focus_areas>
- Supply chain complexity and reliability [cite sources]
- Regulatory compliance requirements [cite sources]
- Licensing and legal requirements [cite sources]
- Resource availability (materials, talent, infrastructure) [cite sources]
- Infrastructure gaps and dependencies [cite sources]
- Operational cost realities [cite sources]
</focus_areas>

<citation_requirements>
1. Every factual claim must have [N] citation - No unsupported statements
2. Use [1], [2], [3] format - Numbered citations embedded in text
3. Minimum 5-8 citations - Your critique must include at least 5 citations
4. Multiple sources: Use [1][2] when multiple sources support same claim
5. Citation accuracy: Ensure numbers match provided source list
</citation_requirements>

<severity_guidelines>
- HIGH: Regulatory blockers, operational impossibility, critical resource unavailability, legal compliance failures
- MEDIUM: High operational complexity, difficult resource access, regulatory challenges, infrastructure limitations
- LOW: Minor operational inefficiencies, optimization opportunities, process improvements
</severity_guidelines>

<summary_requirements>
- Each bullet point MUST include specific numbers/percentages/statistics from the sources
- Each bullet point MUST end with citation(s) in [N] format
- Be specific and quantitative, NOT generic statements
- Example GOOD: "Regulatory approval takes 18-24 months, delaying market entry [2][5]"
- Example BAD: "Regulatory requirements are complex" (too generic, no numbers, no citations)
</summary_requirements>

<output_schema>
{
  "critique_id": "operational-001",
  "dimension": "operational_feasibility",
  "section_name": "Operational Feasibility Critique",
  "title": "Concise critique title (10-50 words)",
  "severity": "high|medium|low",
  "summary": ["<Specific finding with number/percentage> [N][N]", "..."],
  "problem": "Detailed problem description with embedded [1][2][3] citations. (MINIMUM 5 CITATIONS REQUIRED)",
  "impact": "Explain operational impact with citations [N][N]. Include cost implications.",
  "suggestions": [
    {
      "type": "validation|alternative|optimization|compliance",
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
Generate 1-3 operational feasibility critiques with STRICT CITATIONS. Return ONLY valid JSON.
</output_rules>
"""
    
    def get_relevant_bmc_fields(self, bmc_data: Dict) -> Dict:
        """Extract operations-relevant BMC fields"""
        return {
            'key_activities': bmc_data.get('key_activities', []),
            'key_resources': bmc_data.get('key_resources', []),
            'key_partnerships': bmc_data.get('key_partnerships', []),
            'cost_structure': bmc_data.get('cost_structure', [])
        }
    
    def get_relevant_vpc_fields(self, vpc_data: Dict) -> Dict:
        """Extract operations-relevant VPC fields"""
        value_map = vpc_data.get('value_map') or {}
        
        return {
            'value_map.products_services': value_map.get('products_services', []),
            'value_map.pain_relievers': value_map.get('pain_relievers', [])
        }
    
    def get_search_categories(self) -> List[str]:
        """Return relevant search categories for operational feasibility"""
        return ['regulatory', 'operational']
    
    def get_context_priority(self) -> Dict[str, int]:
        """Operational feasibility heavily relies on BMC operational blocks
        
        Priority weights determine source emphasis and content length
        """
        return {
            'bmc': 10,
            'vpc': 4,
            'vps': 6
        }

