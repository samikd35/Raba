"""
Enterprise Pain Analysis Agent for Advanced Market Intelligence.

Enterprise-grade pain point validation with advanced intelligence capabilities:
- Multi-source evidence synthesis from massive datasets (25+ PDFs, 5+ CSVs)
- Statistical significance testing for pain point prevalence
- Cross-file validation and consistency checking
- AI-enhanced pattern recognition for hidden pain correlations
- Comprehensive persona-aware pain analysis
- Real-time accuracy monitoring and bias detection
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from .base_analysis_agent import EnterpriseBaseAnalysisAgent
from ..models.analysis_models import AnalysisContext

logger = logging.getLogger(__name__)


class EnterprisePainAnalysisAgent(EnterpriseBaseAnalysisAgent):
    """Enterprise-grade pain analysis agent with advanced intelligence capabilities.
    
    Features:
    - Multi-source pain evidence synthesis from 25+ files
    - Statistical significance testing for pain prevalence
    - Cross-file pain consistency validation
    - AI-enhanced pain pattern recognition
    - Comprehensive persona-aware pain analysis
    - Advanced pain severity and frequency analysis
    """
    
    def _get_analysis_type(self) -> str:
        """Return the analysis type identifier."""
        return "pain_points"
    
    async def analyze_assumption(self, context: AnalysisContext) -> Dict[str, Any]:
        """Perform enterprise-grade pain analysis with advanced intelligence."""
        try:
            # Get enterprise data from context
            enterprise_data = context.research_data.get("enterprise_statistics", {})
            
            if enterprise_data:
                # Use enterprise analysis for massive datasets
                return await self.perform_enterprise_analysis(context, enterprise_data)
            else:
                # Fallback to standard analysis
                return await self._perform_standard_analysis(context)
                
        except Exception as e:
            logger.error(f"❌ ENTERPRISE PAIN ANALYSIS: Failed: {e}")
            # Fallback to standard analysis
            return await self._perform_standard_analysis(context)
    
    async def _perform_standard_analysis(self, context: AnalysisContext) -> Dict[str, Any]:
        """Perform standard pain analysis for backward compatibility."""
        # Create two-tier analysis prompt
        prompt_bundle = await self._create_two_tier_analysis_prompt(
            context, "pain_points", persona_id=context.persona.get("id")
        )
        
        # Generate analysis using AI service
        response = await self.ai_service_wrapper.generate_with_fallback(
            prompt_bundle["messages"],
            json_mode=True,
            max_tokens=16000,  # gpt-5-mini needs large token budget
            temperature=0.2
        )
        
        if not response or not response.get("content"):
            raise ValueError("No response from AI service")
        
        # Parse and validate response
        analysis_result = self._parse_and_validate_response(response["content"])
        
        # Add metadata
        analysis_result["analysis_metadata"] = {
            "analysis_type": "pain_points",
            "persona_id": context.persona.get("id"),
            "assumption_id": context.assumption.get("id"),
            "evidence_sources": len(context.research_data.get("chunks", [])),
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        return analysis_result
    
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        """
        Create pain-specific analysis prompt for AI service.
        
        Args:
            context: Analysis context with assumption, persona, and research data
            
        Returns:
            List of chat messages for AI service
        """
        assumption_text = context.assumption.get("text", "")
        persona_name = context.persona.get("name", "Unknown Persona")
        
        # Extract relevant research content with balanced data representation
        research_content = self._format_research_content_balanced(context.research_data, "pain")
        
        # Get expected pains from customer profile for comparison
        expected_pains = self._extract_expected_pains(context.project_context, persona_name)
        
        system_prompt = """<role>
You are a market research analyst validating customer pain points for a single persona.
</role>

<task>
Analyze research evidence to validate or invalidate the assumed pain point. Produce a structured JSON analysis.
</task>

<evidence_rules>
- Quote participants directly with identifiers (e.g. "Interview 3 – Farmer": "quote")
- Convert repeated mentions into counts: "3 of 5 interviewees" NOT invented percentages
- If no quantitative data exists, describe qualitatively and note the gap
- NEVER fabricate CSV references, file names, or statistics not in the context
- Call out disagreements or outliers explicitly
</evidence_rules>

<tone>
Practical, research-note style. No enterprise buzzwords or marketing copy.
</tone>

<output_rules>
Return ONLY valid JSON matching the schema provided.
</output_rules>"""

        user_prompt = f"""
<assumption>
{assumption_text}
</assumption>

<persona>{persona_name}</persona>

<expected_pains>
{expected_pains}
</expected_pains>

<research_material>
{research_content}
</research_material>

<instructions>
1. Identify the strongest evidence that confirms or challenges the assumption
2. Reference interview speakers or document names when quoting (e.g. "Interview 2", "Survey response")
3. NEVER invent CSV citations like [CSV 3]
4. Convert repeated mentions into counts: "3 of 5 interviewees mentioned..."
5. Highlight disagreement or missing data explicitly
6. If no numerical data exists, use "Several interviewees" or "Qualitative evidence only"
</instructions>

<output_schema>
{{
    "claim": "One-sentence finding with counts when available (e.g. '3 of 5 interviewees struggled with...')",
    "accuracy_level": "high|medium|low",
    "supporting_evidence": [
        "Interview/document reference with explanation (e.g. 'Interview 2 – Agronomist: \"quote\" (shows severity)')"
    ],
    "debunking_evidence": [
        "Evidence that contradicts or softens the pain point, if any"
    ],
    "statistical_data": {{
        "sample_size": "e.g. '5 interview participants; no survey data'",
        "mention_counts": ["e.g. '3/5 interviewees reported X'"],
        "data_gaps": "Note missing or qualitative-only evidence"
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
        """Return JSON schema for pain analysis output validation."""
        return {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "Main claim about pain point validation"
                },
                "accuracy_level": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the analysis"
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence supporting the pain point"
                },
                "debunking_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence contradicting the pain point"
                },
                "statistical_data": {
                    "type": "object",
                    "properties": {
                        "sample_size": {"type": "string"},
                        "mention_counts": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "data_gaps": {"type": "string"}
                    },
                    "description": "Transparent description of sample size, counts, and data limitations"
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
    
    
    def _extract_expected_pains(self, project_context: Dict[str, Any], persona_name: str) -> str:
        """
        Extract expected pain points from customer profile for comparison.
        
        Args:
            project_context: Full project context
            persona_name: Name of target persona
            
        Returns:
            Formatted string of expected pain points
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
            
            # Extract pain points from profile
            pains = target_profile.get("pains", [])
            
            if not pains:
                return "No pain points defined in customer profile."
            
            # Format pain points
            formatted_pains = []
            for i, pain in enumerate(pains, 1):
                if isinstance(pain, dict):
                    pain_text = pain.get("description", str(pain))
                else:
                    pain_text = str(pain)
                formatted_pains.append(f"{i}. {pain_text}")
            
            return "\n".join(formatted_pains)
            
        except Exception as e:
            logger.warning(f"Error extracting expected pains: {str(e)}")
            return "Unable to extract expected pain points from customer profile."


# Create alias for backward compatibility
PainAnalysisAgent = EnterprisePainAnalysisAgent
