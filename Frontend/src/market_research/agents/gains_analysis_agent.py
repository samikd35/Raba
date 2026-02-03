"""
Gains Analysis Agent for benefits and value proposition validation.

Analyzes research data to validate expected benefits, gains, and value propositions
mentioned in assumptions against actual customer feedback and desired outcomes.
"""

import logging
from typing import Dict, Any, List

from .base_analysis_agent import BaseAnalysisAgent
from ..models.analysis_models import AnalysisContext

logger = logging.getLogger(__name__)


class GainsAnalysisAgent(BaseAnalysisAgent):
    """Agent specialized in analyzing gains and benefits from market research data."""
    
    def _get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "gains_benefits"
    
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        """
        Create gains-specific analysis prompt for AI service.
        
        Args:
            context: Analysis context with assumption, persona, and research data
            
        Returns:
            List of chat messages for AI service
        """
        assumption_text = context.assumption.get("text", "")
        persona_name = context.persona.get("name", "Unknown Persona")
        
        # Extract relevant research content with balanced data representation
        research_content = self._format_research_content_balanced(context.research_data, "gains")
        
        # CRITICAL DEBUG: Log what research data the AI is receiving
        logger.info(f"🔍 RESEARCH DATA DEBUG: Total research chunks = {len(context.research_data)}")
        logger.info(f"🔍 RESEARCH DATA DEBUG: Research content length = {len(research_content)} characters")
        logger.info(f"🔍 RESEARCH DATA DEBUG: Research content preview = {research_content[:500]}...")
        if len(context.research_data) > 0:
            first_chunk = context.research_data[0]
            logger.info(f"🔍 RESEARCH DATA DEBUG: First chunk keys = {list(first_chunk.keys())}")
            logger.info(f"🔍 RESEARCH DATA DEBUG: First chunk similarity = {first_chunk.get('similarity_score', 'N/A')}")
        
        # Get expected gains from customer profile for comparison
        expected_gains = self._extract_expected_gains(context.project_context, persona_name)
        
        system_prompt = """<role>
You are a market research analyst summarizing customer gains and desired benefits for a specific persona.
</role>

<task>
Analyze research evidence to validate or invalidate the assumed benefits/gains. Produce a structured JSON analysis.
</task>

<evidence_rules>
- Quote participants verbatim with identifiers (e.g. "Interview 1 – Teacher")
- Convert repeated mentions into counts: "4 of 6 interviewees" NOT invented percentages
- If quantitative figures are missing, describe qualitatively and note the gap
- Highlight disagreements or trade-offs between personas
- NEVER fabricate references or statistics not in the context
</evidence_rules>

<tone>
Neutral, research-driven. No marketing language.
</tone>

<output_rules>
Return ONLY valid JSON matching the schema provided.
</output_rules>"""

        user_prompt = f"""
<assumption>
{assumption_text}
</assumption>

<persona>{persona_name}</persona>

<expected_gains>
{self._extract_expected_gains(context.project_context, persona_name)}
</expected_gains>

<research_material>
{research_content}
</research_material>

<instructions>
1. Use only the research above - do not reference sources that are not present
2. Attribute quotes using natural descriptors; NEVER fabricate CSV-style citations
3. Identify concrete benefits, success outcomes, or emotional gains that appear repeatedly
4. Convert repeated mentions into counts: "4 of 5 interviewees"
5. Note where participants disagree or express unmet needs
6. Explain when evidence is qualitative-only or willingness-to-pay data is missing
</instructions>

<output_schema>
{{
    "claim": "One-sentence summary of the most important gain/benefit validated, using counts if possible",
    "accuracy_level": "high|medium|low",
    "supporting_evidence": [
        "Quote or data point with explanation"
    ],
    "debunking_evidence": [
        "Evidence that contradicts or limits the benefit, if any"
    ],
    "statistical_data": {{
        "sample_size": "e.g. '5 interviewees; no survey data'",
        "benefit_signals": ["e.g. '4/5 interviewees emphasised X'"],
        "value_indicators": ["Optional notes on willingness to pay or perceived value"],
        "data_gaps": "Mention missing quantitative inputs or uncertainties"
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
        """Return JSON schema for gains analysis output validation."""
        return {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "Main claim about gains/benefits validation"
                },
                "accuracy_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the analysis"
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence supporting the expected benefits"
                },
                "debunking_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence contradicting the expected benefits"
                },
                "statistical_data": {
                    "type": "object",
                    "properties": {
                        "sample_size": {"type": "string"},
                        "benefit_signals": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "value_indicators": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "data_gaps": {"type": "string"}
                    },
                    "description": "Transparent summary of benefit evidence and limitations"
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
    
    
    def _highlight_benefit_keywords(self, content: str) -> str:
        """
        Highlight benefit-related keywords in content for better analysis.
        
        Args:
            content: Raw content string
            
        Returns:
            Content with benefit keywords highlighted
        """
        import re
        
        # Benefit-related keywords to highlight
        benefit_patterns = [
            # Positive outcomes
            (r'\b(benefit|advantage|gain|improvement|better|faster|easier|cheaper)\b', '[BENEFIT: {}]'),
            # Value indicators
            (r'\b(value|worth|important|priority|essential|critical|valuable)\b', '[VALUE: {}]'),
            # Success indicators
            (r'\b(success|achieve|accomplish|reach|attain|goal|target)\b', '[SUCCESS: {}]'),
            # Efficiency indicators
            (r'\b(save|reduce|increase|improve|optimize|streamline|efficient)\b', '[EFFICIENCY: {}]'),
            # Satisfaction indicators
            (r'\b(satisfied|happy|pleased|love|enjoy|appreciate|prefer)\b', '[SATISFACTION: {}]')
        ]
        
        highlighted = content
        for pattern, replacement in benefit_patterns:
            highlighted = re.sub(
                pattern, 
                lambda m: replacement.format(m.group()),
                highlighted, 
                flags=re.IGNORECASE
            )
        
        return highlighted
    
    def _extract_expected_gains(self, project_context: Dict[str, Any], persona_name: str) -> str:
        """
        Extract expected gains from customer profile for comparison.
        
        Args:
            project_context: Full project context
            persona_name: Name of target persona
            
        Returns:
            Formatted string of expected gains
        """
        try:
            # Look for customer profiles in project context
            customer_profiles = project_context.get("customer_profiles", [])
            
            # Find matching persona profile
            target_profile = None
            for profile in customer_profiles:
                if profile.get("persona_name") == persona_name:
                    target_profile = profile
                    break
            
            if not target_profile:
                return "No customer profile found for this persona."
            
            # Extract gains from profile
            gains = target_profile.get("gains", [])
            
            if not gains:
                return "No gains defined in customer profile."
            
            # Format gains
            formatted_gains = []
            for i, gain in enumerate(gains, 1):
                if isinstance(gain, dict):
                    gain_text = gain.get("description", str(gain))
                else:
                    gain_text = str(gain)
                formatted_gains.append(f"{i}. {gain_text}")
            
            return "\n".join(formatted_gains)
            
        except Exception as e:
            logger.warning(f"Error extracting expected gains: {str(e)}")
            return "Unable to extract expected gains from customer profile."
