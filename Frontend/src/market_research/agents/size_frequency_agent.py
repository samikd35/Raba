"""
Size Frequency Analysis Agent for problem magnitude validation.

Analyzes research data to validate the size, scale, and frequency of problems
mentioned in assumptions using quantitative and qualitative indicators.
"""

import logging
from typing import Dict, Any, List

from .base_analysis_agent import BaseAnalysisAgent
from ..models.analysis_models import AnalysisContext

logger = logging.getLogger(__name__)


class SizeFrequencyAgent(BaseAnalysisAgent):
    """Agent specialized in analyzing problem size and frequency from market research data."""
    
    def _get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "size_frequency"
    
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        """
        Create size/frequency-specific analysis prompt for AI service.
        
        Args:
            context: Analysis context with assumption, persona, and research data
            
        Returns:
            List of chat messages for AI service
        """
        assumption_text = context.assumption.get("text", "")
        persona_name = context.persona.get("name", "Unknown Persona")
        
        # Extract relevant research content with balanced data representation
        research_content = self._format_research_content_balanced(context.research_data, "size_frequency")
        
        system_prompt = """<role>
You are a market research analyst estimating problem size and frequency for a specific persona.
</role>

<task>
Analyze research evidence to estimate problem size and frequency. Produce a structured JSON analysis.
</task>

<critical_counting_rule>
When using qualitative interview data, calculate percentages based on FILE COUNT, NOT segment/chunk count:
- Each interview FILE = ONE participant/interviewee
- Multiple segments from same file = SAME participant = count as 1
- Example: "60% (3/5 files)" NOT "7% (3/41 segments)"
</critical_counting_rule>

<evidence_rules>
- Quote participants or reference survey stats only when explicitly present
- Convert repeated mentions into transparent counts: "3 of 5 interviewees"
- If survey percentages are unavailable, describe qualitatively and flag the data gap
- Note contradictory accounts and regional or persona differences
- NEVER invent numbers or statistics not in the context
</evidence_rules>

<tone>
Factual and practical.
</tone>

<output_rules>
Return ONLY valid JSON matching the schema provided.
</output_rules>"""

        user_prompt = f"""
<assumption>
{assumption_text}
</assumption>

<persona>{persona_name}</persona>

<expected_size_signals>
{self._extract_expected_size_signals(context.project_context, persona_name)}
</expected_size_signals>

<research_material>
{research_content}
</research_material>

<instructions>
1. Use the research above as your only evidence - do NOT reference data sources not present
2. Quote interviewees or cite survey metrics using plain language (e.g. "Interview 4", "Survey result")
3. NEVER output fabricated markers like [CSV 2]
4. CRITICAL: Calculate percentages based on FILE COUNT, NOT segment/chunk count
   - Count unique files that mention a theme, not total mentions across all segments
   - Example: "3 of 5 interview files (60%)" NOT "17 of 41 segments (4.5%)"
5. Translate qualitative patterns into counts or cadence statements
6. Be explicit when data is missing or inconsistent
7. Mention persona or context differences if the evidence suggests variation
</instructions>

<output_schema>
{{
    "claim": "One-sentence statement about how common or severe the problem is, based on available data",
    "accuracy_level": "high|medium|low",
    "supporting_evidence": [
        "Concrete quote or metric with explanation"
    ],
    "debunking_evidence": [
        "Evidence that contradicts or limits the problem size, if any"
    ],
    "statistical_data": {{
        "sample_size": "e.g. '5 interviewees; no survey data' or '38 survey responses'",
        "frequency_signals": ["e.g. '4/6 interviewees described daily disruptions'"],
        "intensity_notes": ["Optional notes about severity or magnitude"],
        "data_gaps": "Mention missing metrics or confidence limits"
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
        """Return JSON schema for size/frequency analysis output validation."""
        return {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "Main claim about problem size/frequency validation"
                },
                "accuracy_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the analysis"
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence supporting the size/frequency claims"
                },
                "debunking_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence contradicting the size/frequency claims"
                },
                "statistical_data": {
                    "type": "object",
                    "properties": {
                        "sample_size": {"type": "string"},
                        "frequency_signals": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "intensity_notes": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "data_gaps": {"type": "string"}
                    },
                    "description": "Transparent summary of sample size, recurrence signals, and known limitations"
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


    def _highlight_numerical_data(self, content: str) -> str:
        """
        Highlight numerical data in content for better analysis.
        
        Args:
            content: Raw content string
            
        Returns:
            Content with numerical indicators highlighted
        """
        import re
        
        # Use a single regex with named groups to avoid overlapping matches
        # Order matters - more specific patterns first
        pattern = r'(?P<percentage>\b\d+%)|(?P<cost>\$\d+(?:,\d{3})*(?:\.\d{2})?)|(?P<time>\b\d+\s+(?:hours?|days?|weeks?|months?|years?))|(?P<number>\b\d+(?:,\d{3})*)'
        
        def replace_match(match):
            if match.group('percentage'):
                return f'[PERCENTAGE: {match.group("percentage")}]'
            elif match.group('cost'):
                return f'[COST: {match.group("cost")}]'
            elif match.group('time'):
                return f'[TIME: {match.group("time")}]'
            elif match.group('number'):
                return f'[NUMBER: {match.group("number")}]'
            return match.group(0)
        
        highlighted = re.sub(pattern, replace_match, content, flags=re.IGNORECASE)
        return highlighted

    def _extract_expected_size_signals(self, project_context: Dict[str, Any], persona_name: str) -> str:
        """Extract expected size/frequency cues from the customer profile."""

        try:
            customer_profiles = project_context.get("customer_profiles", []) if isinstance(project_context, dict) else []
            target_profile = None
            for profile in customer_profiles:
                if profile.get("persona_name") == persona_name:
                    target_profile = profile
                    break

            if not target_profile:
                return "No baseline size/frequency expectations recorded for this persona."

            candidate_keys = [
                "size_frequency", "size_signals", "frequency_signals", "market_size",
                "problem_scale", "frequency", "metrics"
            ]

            collected: List[str] = []
            for key in candidate_keys:
                value = target_profile.get(key)
                if not value:
                    continue
                if isinstance(value, list):
                    for item in value:
                        collected.append(str(item))
                elif isinstance(value, dict):
                    for sub_value in value.values():
                        collected.append(str(sub_value))
                else:
                    collected.append(str(value))

            if not collected:
                return "Customer profile does not include size/frequency expectations."

            formatted = []
            for idx, item in enumerate(collected, 1):
                formatted.append(f"{idx}. {item}")
            return "\n".join(formatted)

        except Exception as exc:
            logger.warning(f"Error extracting expected size signals: {exc}")
            return "Unable to extract expected size/frequency expectations from customer profile."