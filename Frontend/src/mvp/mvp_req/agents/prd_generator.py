"""
PRD Generator Agent for AMRG

Generates the final PRD JSON using template-specific prompts.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAMRGAgent
from ..models.state_models import (
    ContextPack, ClarifyingQuestion, ClarifyingAnswer, ResearchResult
)
from ..models.enums import TemplateCode
from ..templates.registry import get_template_spec
from ..services.context_summarizer import get_summarized_context

logger = logging.getLogger(__name__)


class PRDGeneratorAgent(BaseAMRGAgent):
    """
    Agent for generating PRD JSON.
    
    Uses template-specific prompts to generate structured PRD output.
    Output is JSON-only, validated against template schema.
    """
    
    def get_agent_name(self) -> str:
        return "prd_generator"
    
    async def generate_prd(
        self,
        context_pack: ContextPack,
        selected_template_code: str,
        clarifying_questions: List[ClarifyingQuestion],
        clarifying_answers: List[ClarifyingAnswer],
        research_results: Optional[ResearchResult],
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Generate PRD JSON for the selected template.
        
        Args:
            context_pack: Loaded context pack
            selected_template_code: Final selected template code
            clarifying_questions: The 3 questions asked
            clarifying_answers: User's answers
            research_results: Optional web research results
            tenant_id: Tenant ID
            user_id: User ID
            project_id: Project ID
            
        Returns:
            Generated PRD JSON
        """
        logger.info(f"📝 Generating PRD for template {selected_template_code}")
        
        try:
            # Get template spec
            template_code = TemplateCode(selected_template_code)
            spec = get_template_spec(template_code)
            
            if not spec:
                raise ValueError(f"No template spec for {selected_template_code}")
            
            # Create monitoring context
            monitoring_context = self.create_monitoring_context(
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id,
                step_name=f"generate_prd_{selected_template_code.lower()}"
            )
            
            # Summarize context to fit within token limits (larger budget for PRD)
            summarized_context = get_summarized_context(context_pack, use_case="prd_generation")
            logger.info(f"   Token estimate: ~{summarized_context.token_estimate} tokens")
            
            # Select prompt template
            prompt_template = spec.prd_prompt_path
            
            # Check if template exists, fallback to generic
            try:
                prompt = self.render_prompt(prompt_template, {
                    "summarized_context": summarized_context,
                    "context_pack": context_pack,  # Keep for VPC v2 conditional check
                    "clarifying_questions": clarifying_questions,
                    "clarifying_answers": clarifying_answers,
                    "research_results": research_results,
                    "generated_at": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"Template {prompt_template} not found, using A1: {e}")
                prompt = self.render_prompt("prd_a1.j2", {
                    "summarized_context": summarized_context,
                    "context_pack": context_pack,
                    "clarifying_questions": clarifying_questions,
                    "clarifying_answers": clarifying_answers,
                    "research_results": research_results,
                    "generated_at": datetime.utcnow().isoformat()
                })
            
            # Call LLM with higher token limit for PRD (16000 to avoid truncation)
            logger.info(f"   Calling LLM with max_tokens=16000")
            prd_json = await self.call_llm_with_retry(
                prompt=prompt,
                monitoring_context=monitoring_context,
                temperature=0.2,
                max_tokens=16000,
                json_mode=True
            )
            
            # Log raw response size
            import json as json_module
            raw_json_str = json_module.dumps(prd_json)
            logger.info(f"   Raw PRD response: {len(raw_json_str)} chars, ~{len(raw_json_str)//4} tokens")
            
            # Ensure required metadata
            prd_json = self._ensure_metadata(
                prd_json, selected_template_code, spec, context_pack
            )
            
            logger.info(f"✅ PRD generated successfully")
            logger.info(f"   Template: {prd_json.get('template_code')}")
            # Support both old and new field names for logging
            must_have_count = len(prd_json.get('must_have_features', {}).get('features', []))
            if must_have_count == 0:
                must_have_count = len(prd_json.get('mvp_features', {}).get('must_haves', []))
            logger.info(f"   Features: {must_have_count} must-haves")
            workflows = prd_json.get('critical_workflows', {})
            workflow_count = len(workflows.get('workflows', [])) if isinstance(workflows, dict) else len(workflows)
            logger.info(f"   Workflows: {workflow_count}")
            
            return prd_json
            
        except Exception as e:
            logger.error(f"❌ PRD generation failed: {e}")
            raise
    
    def _ensure_metadata(
        self,
        prd_json: Dict[str, Any],
        template_code: str,
        spec: Any,
        context_pack: ContextPack
    ) -> Dict[str, Any]:
        """Ensure PRD has required metadata fields."""
        
        # Template info
        if "template_code" not in prd_json:
            prd_json["template_code"] = template_code
        
        if "template_version" not in prd_json:
            prd_json["template_version"] = spec.template_version
        
        if "schema_version" not in prd_json:
            prd_json["schema_version"] = spec.schema_version
        
        # Source artifacts
        if "source_artifacts_used" not in prd_json:
            prd_json["source_artifacts_used"] = {}
        
        artifacts_used = prd_json["source_artifacts_used"]
        artifacts_used["vps_version"] = "v2"
        artifacts_used["bmc_version"] = "v2"
        artifacts_used["critique_used"] = True
        
        # VPC v2 if available
        if context_pack.get("optional_artifacts", {}).get("vpc_v2"):
            artifacts_used["vpc_version"] = "v2"
        else:
            artifacts_used["vpc_version"] = "not_used"
        
        # Timestamp
        if "generated_at" not in prd_json:
            prd_json["generated_at"] = datetime.utcnow().isoformat()
        
        return prd_json
