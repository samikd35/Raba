"""
Template Router Final Agent for AMRG

Performs final template selection after receiving user answers.
Locks in a single template for PRD generation.
"""

import logging
from typing import Dict, Any, List

from .base_agent import BaseAMRGAgent
from ..models.state_models import (
    ContextPack, TemplateRoutingResult, 
    ClarifyingQuestion, ClarifyingAnswer
)
from ..templates.registry import get_template_spec, TemplateCode
from ..services.context_summarizer import get_summarized_context

logger = logging.getLogger(__name__)


class TemplateRouterFinalAgent(BaseAMRGAgent):
    """
    Agent for final template routing.
    
    Uses context pack + user answers to select the final template.
    This decision is deterministic and cannot be changed.
    """
    
    def get_agent_name(self) -> str:
        return "template_router_final"
    
    async def route(
        self,
        context_pack: ContextPack,
        coarse_routing: TemplateRoutingResult,
        clarifying_questions: List[ClarifyingQuestion],
        clarifying_answers: List[ClarifyingAnswer],
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Perform final template routing.
        
        Args:
            context_pack: Loaded context pack
            coarse_routing: Result from coarse routing
            clarifying_questions: The 3 questions asked
            clarifying_answers: User's answers
            tenant_id: Tenant ID
            user_id: User ID
            project_id: Project ID
            
        Returns:
            Dict with selected_template_code, final_confidence, rationale
        """
        logger.info(f"🎯 Starting final template routing for project {project_id}")
        
        try:
            # Create monitoring context
            monitoring_context = self.create_monitoring_context(
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id,
                step_name="final_routing"
            )
            
            # Summarize context to fit within token limits
            summarized_context = get_summarized_context(context_pack, use_case="routing_final")
            logger.info(f"   Token estimate: ~{summarized_context.token_estimate} tokens")
            
            # Render prompt with summarized context
            prompt = self.render_prompt("routing_final.j2", {
                "summarized_context": summarized_context,
                "coarse_routing": coarse_routing,
                "clarifying_questions": clarifying_questions,
                "clarifying_answers": clarifying_answers
            })
            
            # Call LLM
            response = await self.call_llm_with_retry(
                prompt=prompt,
                monitoring_context=monitoring_context,
                temperature=0.1,
                max_tokens=16000  # gpt-5-mini needs large token budget
            )
            
            # Parse and validate response
            result = self._parse_final_response(response, coarse_routing)
            
            logger.info(f"✅ Final routing complete")
            logger.info(f"   Selected template: {result['selected_template_code']}")
            logger.info(f"   Confidence: {result['final_confidence']:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Final routing failed: {e}")
            # Return top template from coarse routing as fallback
            return self._create_fallback_result(coarse_routing, str(e))
    
    def _parse_final_response(
        self,
        response: Dict[str, Any],
        coarse_routing: TemplateRoutingResult
    ) -> Dict[str, Any]:
        """Parse and validate final routing response."""
        
        selected_code = response.get("selected_template_code", "A1")
        
        # Validate template code
        try:
            template_code = TemplateCode(selected_code)
            spec = get_template_spec(template_code)
            if not spec:
                raise ValueError(f"No spec for {selected_code}")
        except ValueError:
            logger.warning(f"Invalid template code: {selected_code}, using top from coarse")
            selected_code = coarse_routing["top_templates"][0]["code"]
        
        return {
            "selected_template_code": selected_code,
            "final_confidence": float(response.get("final_confidence", 0.85)),
            "final_rationale": response.get("final_rationale", ""),
            "key_deciding_factors": response.get("key_deciding_factors", []),
            "template_fit_summary": response.get("template_fit_summary", "")
        }
    
    def _create_fallback_result(
        self,
        coarse_routing: TemplateRoutingResult,
        error: str
    ) -> Dict[str, Any]:
        """Create fallback result using coarse routing top choice."""
        top_template = coarse_routing["top_templates"][0]
        
        return {
            "selected_template_code": top_template["code"],
            "final_confidence": top_template["confidence"],
            "final_rationale": f"Fallback to coarse routing due to error: {error}",
            "key_deciding_factors": top_template.get("key_signals", []),
            "template_fit_summary": top_template.get("rationale", "")
        }
