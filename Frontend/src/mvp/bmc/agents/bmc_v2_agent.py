"""
BMC v2 Refinement Agent

AI-powered agent for refining Business Model Canvas based on solution critique feedback
and alignment with refined VPS v2.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.config import get_client_config, ModelUseCase
from ..prompts.bmc_v2_prompts import BMC_V2_SYSTEM_PROMPT, format_bmc_v2_prompt

# Import AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class BMCRefinementAgent:
    """Agent for refining BMC v1 based on solution critique and VPS v2 alignment."""
    
    def __init__(self, ai_provider: Optional[OpenAIProvider] = None):
        """
        Initialize BMC refinement agent.
        
        Args:
            ai_provider: AI provider instance (creates default if None)
        
        CRITICAL: Uses centralized AI config to ensure Azure OpenAI is used
        when configured, with automatic fallback to standard OpenAI.
        """
        if ai_provider is None:
            # Use centralized config to get Azure OpenAI settings (same as market research)
            provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
            
            logger.info(f"🔧 BMC_V2_AGENT: Initializing with provider={provider_type}, model={model_name}")
            
            # Build config - gpt-5-mini doesn't support temperature
            is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
            
            config_kwargs = {
                "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
                "model_name": model_name,
                "max_tokens": 16000 if is_gpt5_model else 5000,  # gpt-5-mini needs much more tokens for 9 blocks
                "azure_endpoint": client_config.get("azure_endpoint"),
                "api_version": client_config.get("api_version"),
                "api_key": client_config.get("api_key")
            }
            
            if not is_gpt5_model:
                config_kwargs["temperature"] = 0.7
            
            config = LLMConfig(**config_kwargs)
            ai_provider = OpenAIProvider(config)
            
            logger.info(f"✅ BMC_V2_AGENT: AI provider initialized with {provider_type}")
        
        self.ai_provider = ai_provider
        logger.info(f"BMC Refinement Agent initialized with model: {ai_provider.config.model_name}")
    
    async def refine_bmc(
        self,
        bmc_v1: Dict[str, Any],
        vps_v2: Dict[str, Any],
        critique_chunks: List[Dict[str, Any]],
        context: Dict[str, Any],
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Refine BMC v1 based on critique feedback and VPS v2 alignment.
        
        Args:
            bmc_v1: Current BMC v1 data (9 blocks)
            vps_v2: Refined VPS v2 for alignment
            critique_chunks: RAG-retrieved critique chunks
            context: Minimal context (project metadata)
            creativity_level: AI creativity (0.0-1.0)
            
        Returns:
            Dictionary with refined BMC v2 and refinement metadata
            
        Raises:
            Exception: If refinement fails
        """
        try:
            project_id = context.get('project_id')
            user_id = context.get('user_id')
            tenant_id = context.get('tenant_id')
            
            logger.info(f"🚀 Refining BMC for project {project_id}")
            logger.info(f"BMC v1 blocks: {len([k for k in bmc_v1.keys() if 'generation_metadata' not in k])}")
            logger.info(f"VPS v2 provided for alignment")
            logger.info(f"Critique chunks available: {len(critique_chunks)}")
            
            # Create monitoring context
            monitoring_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                feature_id="mvp_bmc_v2_refinement",
                workflow_name="mvp_workflow",
                step_name="refine_bmc",
                environment="prod"
            )
            
            started_at = datetime.utcnow()
            
            # Build minimal formatted context
            formatted_context = f"""
PROJECT METADATA:
- Project ID: {context.get('project_id', 'N/A')}
- Tenant ID: {context.get('tenant_id', 'N/A')}

NOTE: BMC v2 refinement focuses on critique feedback and VPS v2 alignment.
All other context is already embedded in BMC v1.
"""
            
            logger.info(f"Using minimal context (no VPC/personas/research loading)")
            logger.info(f"Using {len(critique_chunks)} critique chunks for refinement")
            
            # Prepare messages
            messages = [
                {"role": "system", "content": BMC_V2_SYSTEM_PROMPT},
                {"role": "user", "content": format_bmc_v2_prompt(
                    bmc_v1=bmc_v1,
                    vps_v2=vps_v2,
                    critique_chunks=critique_chunks,
                    context=formatted_context
                )}
            ]
            
            # Use simple json_object format - BMC blocks have dynamic content
            # that can't be strictly defined with additionalProperties: false
            
            # Update temperature
            original_temp = self.ai_provider.config.temperature
            self.ai_provider.config.temperature = creativity_level
            
            logger.info(f"Calling AI with temperature: {creativity_level}")
            
            # Call AI with json_object format (BMC blocks have dynamic content)
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            # Restore temperature
            self.ai_provider.config.temperature = original_temp
            
            finished_at = datetime.utcnow()
            
            # Record AI usage
            monitoring = get_monitoring_service()
            usage = getattr(response, 'usage', {}) or {}
            actual_model = getattr(response, 'model', self.ai_provider.config.model_name)
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider="openai",
                    model_name=actual_model,
                    operation_type="responses_api",
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens')
                )
            )
            
            logger.info("✅ Received AI refinement response")
            
            # Parse response
            try:
                if not response.content:
                    raise ValueError("AI returned empty content")
                bmc_v2_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                raise ValueError(f"AI returned invalid JSON: {e}")
            
            # Build final BMC v2 structure
            refined_bmc = {
                "customer_segments": bmc_v2_data['customer_segments'],
                "value_propositions": bmc_v2_data['value_propositions'],
                "channels": bmc_v2_data['channels'],
                "customer_relationships": bmc_v2_data['customer_relationships'],
                "revenue_streams": bmc_v2_data['revenue_streams'],
                "key_resources": bmc_v2_data['key_resources'],
                "key_activities": bmc_v2_data['key_activities'],
                "key_partnerships": bmc_v2_data['key_partnerships'],
                "cost_structure": bmc_v2_data['cost_structure'],
                
                "generation_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "model_used": response.model,
                    "version": "v2",
                    "refined_from": "v1",
                    "critique_chunks_used": len(critique_chunks),
                    "vps_v2_aligned": bmc_v2_data['value_propositions'].get('vps_v2_aligned', False)
                },
                
                "refinement_metadata": {
                    "refinement_decision": bmc_v2_data['refinement_decision'],
                    "refinement_rationale": bmc_v2_data['refinement_rationale'],
                    "blocks_changed": self._count_changed_blocks(bmc_v2_data),
                    "critique_sources_used": bmc_v2_data['critique_sources_used'],
                    "vps_v2_alignment_notes": bmc_v2_data['vps_v2_alignment_notes'],
                    "overall_improvement_summary": bmc_v2_data['overall_improvement_summary']
                }
            }
            
            # Add usage info
            if response.usage:
                refined_bmc['generation_metadata']['usage'] = response.usage
            
            logger.info(f"✅ Successfully refined BMC for project {project_id}")
            logger.info(f"Refinement decision: {bmc_v2_data['refinement_decision']}")
            logger.info(f"Blocks changed: {refined_bmc['refinement_metadata']['blocks_changed']}/9")
            logger.info(f"VPS v2 aligned: {refined_bmc['generation_metadata']['vps_v2_aligned']}")
            
            return refined_bmc
            
        except Exception as e:
            finished_at = datetime.utcnow()
            
            # Record error
            monitoring = get_monitoring_service()
            actual_model = self.ai_provider.config.model_name
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider="openai",
                    model_name=actual_model,
                    operation_type="responses_api",
                    started_at=started_at,
                    finished_at=finished_at,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            logger.error(f"❌ Error refining BMC: {e}")
            raise
    
    def _count_changed_blocks(self, bmc_v2_data: Dict[str, Any]) -> int:
        """Count how many blocks were changed."""
        blocks = [
            'customer_segments', 'value_propositions', 'channels',
            'customer_relationships', 'revenue_streams', 'key_resources',
            'key_activities', 'key_partnerships', 'cost_structure'
        ]
        return sum(1 for block in blocks if bmc_v2_data.get(block, {}).get('changed', False))
