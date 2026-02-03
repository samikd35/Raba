"""
Solution Analysis Agent for current solutions validation.

Analyzes research data to identify and validate current solutions, alternatives,
and competitive landscape mentioned in assumptions.
"""

import logging
from typing import Dict, Any, List

from .base_analysis_agent import BaseAnalysisAgent
from ..models.analysis_models import AnalysisContext

logger = logging.getLogger(__name__)


class SolutionAnalysisAgent(BaseAnalysisAgent):
    """Agent specialized in analyzing current solutions and alternatives from market research data."""
    
    def _get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "current_solutions"
    
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        """
        Create solution-specific analysis prompt for AI service.
        
        Args:
            context: Analysis context with assumption, persona, and research data
            
        Returns:
            List of chat messages for AI service
        """
        assumption_text = context.assumption.get("text", "")
        persona_name = context.persona.get("name", "Unknown Persona")
        
        # Extract relevant research content with balanced data representation
        research_content = self._format_research_content_balanced(context.research_data, "solution")
        
        system_prompt = """<role>
You are a market research analyst documenting which solutions or workarounds the persona currently uses.
</role>

<task>
Analyze research evidence to identify current solutions and their effectiveness. Produce a structured JSON analysis.
</task>

<evidence_rules>
- Quote participants directly when they mention a tool, workaround, or competitor
- Identify them with natural labels (e.g. "Interview 3 – Agronomist")
- Convert repeated mentions into counts: "3 of 5 interviewees" NOT invented percentages
- Note effectiveness, frustrations, or switching behaviour exactly as described
- NEVER invent adoption percentages or product names not in the context
</evidence_rules>

<tone>
Neutral, research-report style.
</tone>

<output_rules>
Return ONLY valid JSON matching the schema provided.
</output_rules>"""

        user_prompt = f"""
<assumption>
{assumption_text}
</assumption>

<persona>{persona_name}</persona>

<expected_solutions>
{self._extract_expected_solutions(context.project_context, persona_name)}
</expected_solutions>

<research_material>
{research_content}
</research_material>

<instructions>
1. Reference only solutions, tools, and behaviours found above - do NOT invent product names or metrics
2. Attribute quotes with plain-language identifiers; NEVER create citations like [CSV 4]
3. Capture how effective each solution is, frustrations, and whether participants are seeking alternatives
4. Mention if different personas use different tools
5. Flag missing data (e.g. no evidence about pricing) in the statistical snapshot
</instructions>

<output_schema>
{{
    "claim": "One-sentence summary of the dominant solution behaviour and effectiveness, using counts if possible",
    "accuracy_level": "high|medium|low",
    "supporting_evidence": [
        "Quote or observation explaining a commonly used solution"
    ],
    "debunking_evidence": [
        "Evidence that contradicts or nuances the solution pattern, if any"
    ],
    "statistical_data": {{
        "sample_size": "e.g. '5 interviewees; no survey data'",
        "solution_mentions": ["e.g. '3/5 interviewees rely on WhatsApp farmer groups'"],
        "effectiveness_notes": ["Optional notes about satisfaction, switching, or pain points"],
        "data_gaps": "Highlight missing metrics or unknowns"
    }},
    "confidence_score": 0.0-1.0
}}
</output_schema>

Return ONLY valid JSON matching the schema.
"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Return JSON schema for solution analysis output validation."""
        return {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "Main claim about current solutions validation"
                },
                "accuracy_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the analysis"
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence supporting the solution analysis"
                },
                "debunking_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence contradicting assumed solutions"
                },
                "statistical_data": {
                    "type": "object",
                    "properties": {
                        "sample_size": {"type": "string"},
                        "solution_mentions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "effectiveness_notes": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "data_gaps": {"type": "string"}
                    },
                    "description": "Summary of observed solutions, effectiveness signals, and gaps"
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Numerical confidence score"
                }
            },
            "required": ["claim", "accuracy_level", "supporting_evidence", "confidence_score"]
        }
    
    
    def _highlight_solution_keywords(self, content: str) -> str:
        """
        Highlight solution-related keywords in content for better analysis.
        
        Args:
            content: Raw content string
            
        Returns:
            Content with solution keywords highlighted
        """
        import re
        
        # Solution-related keywords to highlight
        solution_keywords = [
            # Tools and software
            r'\b(tool|software|app|platform|system|solution|service)\b',
            # Actions indicating solution usage
            r'\b(use|using|tried|implement|switch|adopt|replace)\b',
            # Competitive terms
            r'\b(competitor|alternative|instead|versus|compared to)\b',
            # Effectiveness terms
            r'\b(works|effective|satisfied|disappointed|frustrated|helpful)\b'
        ]
        
        highlighted = content
        for pattern in solution_keywords:
            highlighted = re.sub(
                pattern,
                lambda m: f'[{m.group().upper()}]',
                highlighted,
                flags=re.IGNORECASE
            )

        return highlighted

    def _extract_expected_solutions(self, project_context: Dict[str, Any], persona_name: str) -> str:
        """Extract expected current solutions from the customer profile."""

        try:
            customer_profiles = project_context.get("customer_profiles", []) if isinstance(project_context, dict) else []
            target_profile = None
            for profile in customer_profiles:
                if profile.get("persona_name") == persona_name:
                    target_profile = profile
                    break

            if not target_profile:
                return "No customer profile found for this persona."

            solutions = target_profile.get("current_solutions") or target_profile.get("solutions") or []

            if not solutions:
                return "No expected solutions documented in the customer profile."

            formatted = []
            for idx, solution in enumerate(solutions, 1):
                if isinstance(solution, dict):
                    text = solution.get("description") or solution.get("name") or str(solution)
                else:
                    text = str(solution)
                formatted.append(f"{idx}. {text}")

            return "\n".join(formatted)

        except Exception as exc:
            logger.warning(f"Error extracting expected solutions: {exc}")
            return "Unable to extract expected solutions from customer profile."
