"""
Jobs-to-be-Done (JTBD) Analysis Agent for workflow and process validation.

Analyzes research data to validate jobs-to-be-done, workflows, and processes
mentioned in assumptions against actual customer behaviors and job outcomes.
"""

import logging
from typing import Dict, Any, List

from .base_analysis_agent import BaseAnalysisAgent
from ..models.analysis_models import AnalysisContext

logger = logging.getLogger(__name__)


class JTBDAnalysisAgent(BaseAnalysisAgent):
    """Agent specialized in analyzing jobs-to-be-done from market research data."""
    
    def _get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "jobs_to_be_done"
    
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        """
        Create JTBD-specific analysis prompt for AI service.
        
        Args:
            context: Analysis context with assumption, persona, and research data
            
        Returns:
            List of chat messages for AI service
        """
        assumption_text = context.assumption.get("text", "")
        persona_name = context.persona.get("name", "Unknown Persona")
        
        # Extract relevant research content with balanced data representation
        research_content = self._format_research_content_balanced(context.research_data, "jtbd")
        
        system_prompt = """<role>
You are a market research analyst mapping Jobs To Be Done (JTBD) for a single persona.
</role>

<task>
Analyze research evidence to identify and validate jobs-to-be-done. Produce a structured JSON analysis.
</task>

<evidence_rules>
- Quote participants when they describe what they're trying to accomplish
- Translate repeated patterns into counts: "4 of 6 interviewees" NOT invented percentages
- Distinguish functional jobs (tasks), emotional jobs (feelings), and desired outcomes
- Call out contradictions or missing steps - do NOT invent them
- NEVER fabricate references or statistics not in the context
</evidence_rules>

<tone>
Practical and precise. No enterprise buzzwords.
</tone>

<output_rules>
Return ONLY valid JSON matching the schema provided.
</output_rules>"""

        user_prompt = f"""
<assumption>
{assumption_text}
</assumption>

<persona>{persona_name}</persona>

<expected_jobs>
{self._extract_expected_jobs(context.project_context, persona_name)}
</expected_jobs>

<research_material>
{research_content}
</research_material>

<instructions>
1. Rely solely on the research above
2. Attribute quotes with simple identifiers (e.g. "Interview 5 – Extension Officer")
3. NEVER fabricate citations like [CSV 7]
4. Separate functional tasks, emotional motivations, and desired outcomes
5. Highlight sequence or workflow steps if the data supports it
6. Note gaps in understanding (e.g. missing trigger, missing success measure)
</instructions>

<output_schema>
{{
    "claim": "One-sentence summary of the primary job(s) validated, referencing counts where possible",
    "accuracy_level": "high|medium|low",
    "supporting_evidence": [
        "Quote or observation showing a functional job",
        "Quote or observation showing emotional or outcome jobs"
    ],
    "debunking_evidence": [
        "Evidence that contradicts or limits the assumed jobs, if any"
    ],
    "statistical_data": {{
        "sample_size": "e.g. '6 interviewees; qualitative only'",
        "functional_jobs": ["Short bullet strings describing repeated tasks or workflows"],
        "emotional_jobs": ["Short bullet strings describing emotional goals"],
        "outcome_metrics": ["Optional success criteria or measures mentioned"],
        "data_gaps": "Note any missing steps or unvalidated jobs"
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
        """Return JSON schema for JTBD analysis output validation."""
        return {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "Main claim about JTBD validation"
                },
                "accuracy_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the analysis"
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence supporting the JTBD analysis"
                },
                "debunking_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence contradicting assumed jobs or workflows"
                },
                "statistical_data": {
                    "type": "object",
                    "properties": {
                        "sample_size": {"type": "string"},
                        "functional_jobs": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "emotional_jobs": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "outcome_metrics": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "data_gaps": {"type": "string"}
                    },
                    "description": "Structured summary of functional/emotional jobs, outcomes, and gaps"
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
    
    
    def _highlight_jtbd_keywords(self, content: str) -> str:
        """
        Highlight JTBD-related keywords in content for better analysis.
        
        Args:
            content: Raw content string
            
        Returns:
            Content with JTBD keywords highlighted
        """
        import re
        
        # JTBD-related keywords to highlight
        jtbd_patterns = [
            # Functional job indicators
            (r'\b(task|job|process|workflow|step|procedure|method|approach)\b', '[FUNCTIONAL: {}]'),
            # Outcome indicators
            (r'\b(goal|outcome|result|success|complete|finish|achieve|accomplish)\b', '[OUTCOME: {}]'),
            # Emotional job indicators
            (r'\b(feel|emotion|confident|frustrated|stressed|satisfied|comfortable)\b', '[EMOTIONAL: {}]'),
            # Context indicators
            (r'\b(when|where|during|while|before|after|context|situation)\b', '[CONTEXT: {}]'),
            # Constraint indicators
            (r'\b(barrier|constraint|limitation|challenge|difficult|problem|issue)\b', '[CONSTRAINT: {}]')
        ]
        
        highlighted = content
        for pattern, replacement in jtbd_patterns:
            highlighted = re.sub(
                pattern,
                lambda m: replacement.format(m.group()),
                highlighted,
                flags=re.IGNORECASE
            )

        return highlighted

    def _extract_expected_jobs(self, project_context: Dict[str, Any], persona_name: str) -> str:
        """Extract expected jobs from the customer profile for comparison."""

        try:
            customer_profiles = project_context.get("customer_profiles", []) if isinstance(project_context, dict) else []
            target_profile = None
            for profile in customer_profiles:
                if profile.get("persona_name") == persona_name:
                    target_profile = profile
                    break

            if not target_profile:
                return "No customer profile found for this persona."

            jobs = target_profile.get("jobs_to_be_done") or target_profile.get("jobs") or []

            if not jobs:
                return "No JTBD defined in the customer profile."

            formatted = []
            for idx, job in enumerate(jobs, 1):
                if isinstance(job, dict):
                    text = job.get("description") or job.get("summary") or str(job)
                else:
                    text = str(job)
                formatted.append(f"{idx}. {text}")

            return "\n".join(formatted)

        except Exception as exc:
            logger.warning(f"Error extracting expected jobs: {exc}")
            return "Unable to extract expected jobs from customer profile."
