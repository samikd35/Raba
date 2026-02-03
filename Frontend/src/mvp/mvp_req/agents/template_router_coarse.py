"""
Template Router Coarse Agent for AMRG

Performs initial template routing based on context analysis.
Returns top 1-3 template candidates with confidence scores.
"""

import logging
from typing import Dict, Any, List

from .base_agent import BaseAMRGAgent
from ..models.state_models import ContextPack, TemplateRoutingResult, TemplateCandidate
from ..templates.registry import get_template_spec, TemplateCode
from ..services.context_summarizer import get_summarized_context

logger = logging.getLogger(__name__)

# Confidence threshold for single-template selection
CONFIDENCE_THRESHOLD = 0.80


class TemplateRouterCoarseAgent(BaseAMRGAgent):
    """
    Agent for initial (coarse) template routing.
    
    Analyzes context pack and determines top template candidates.
    If confidence >= 0.8, returns single template.
    Otherwise, returns 2-3 candidates for clarification.
    """
    
    def get_agent_name(self) -> str:
        return "template_router_coarse"
    
    async def route(
        self,
        context_pack: ContextPack,
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> TemplateRoutingResult:
        """
        Perform coarse template routing.
        
        Args:
            context_pack: Loaded context pack
            tenant_id: Tenant ID
            user_id: User ID
            project_id: Project ID
            
        Returns:
            TemplateRoutingResult with top candidates
        """
        logger.info(f"🔀 Starting coarse template routing for project {project_id}")
        
        try:
            # Create monitoring context
            monitoring_context = self.create_monitoring_context(
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id,
                step_name="coarse_routing"
            )
            
            # Summarize context to fit within token limits
            summarized_context = get_summarized_context(context_pack, use_case="routing_coarse")
            logger.info(f"   Token estimate: ~{summarized_context.token_estimate} tokens")
            
            # Render prompt with summarized context
            prompt = self.render_prompt("routing_coarse.j2", {
                "summarized_context": summarized_context
            })
            
            # Call LLM
            response = await self.call_llm_with_retry(
                prompt=prompt,
                monitoring_context=monitoring_context,
                temperature=0.1,
                max_tokens=16000  # gpt-5-mini needs large token budget
            )
            
            # Parse and validate response
            result = self._parse_routing_response(response)
            
            logger.info(f"✅ Coarse routing complete")
            logger.info(f"   Top template: {result['top_templates'][0]['code']} (confidence: {result['top_templates'][0]['confidence']:.2f})")
            logger.info(f"   Threshold met: {result['confidence_threshold_met']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Coarse routing failed: {e}")
            # Return fallback with low confidence
            return self._create_fallback_result(str(e))
    
    def _parse_routing_response(self, response: Dict[str, Any]) -> TemplateRoutingResult:
        """Parse and validate LLM response."""
        
        # Extract top templates
        top_templates_raw = response.get("top_templates", [])
        top_templates: List[TemplateCandidate] = []
        
        for t in top_templates_raw:
            code = t.get("code", "A1")
            confidence = float(t.get("confidence", 0.5))
            
            # Validate template code
            try:
                template_code = TemplateCode(code)
                spec = get_template_spec(template_code)
                
                top_templates.append({
                    "code": code,
                    "confidence": confidence,
                    "rationale": t.get("rationale", ""),
                    "key_signals": t.get("key_signals", [])
                })
            except ValueError:
                logger.warning(f"Invalid template code: {code}, skipping")
        
        # Ensure at least one template
        if not top_templates:
            top_templates = [{
                "code": "A1",
                "confidence": 0.5,
                "rationale": "Default fallback",
                "key_signals": []
            }]
        
        # Sort by confidence
        top_templates.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Check threshold
        top_confidence = top_templates[0]["confidence"]
        confidence_threshold_met = top_confidence >= CONFIDENCE_THRESHOLD
        
        return {
            "top_templates": top_templates[:3],  # Max 3 candidates
            "confidence_threshold_met": confidence_threshold_met,
            "ambiguity_points": response.get("ambiguity_points", []),
            "routing_rationale": response.get("routing_rationale", "")
        }
    
    def _create_fallback_result(self, error: str) -> TemplateRoutingResult:
        """Create fallback result when routing fails."""
        return {
            "top_templates": [{
                "code": "A1",
                "confidence": 0.3,
                "rationale": f"Fallback due to error: {error}",
                "key_signals": []
            }],
            "confidence_threshold_met": False,
            "ambiguity_points": ["Routing failed, defaulting to A1 Software/SaaS"],
            "routing_rationale": f"Error during routing: {error}"
        }
