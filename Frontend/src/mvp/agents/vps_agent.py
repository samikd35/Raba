"""
VPS Generation Agent

AI-powered agent for generating Value Proposition Statements from VPC 2.0 data.
Uses OpenAI with structured output for consistent, high-quality results.

MIGRATED TO RESPONSES API (Dec 2025):
- Uses generate_responses() for gpt-5-mini
- Leverages reasoning.effort for grounded output
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.config import get_client_config, ModelUseCase
from ..prompts.vps_prompts import VPS_SYSTEM_PROMPT, format_vps_prompt

# Import AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class VPSGenerationAgent:
    """Agent for generating Value Proposition Statements."""
    
    def __init__(self, ai_provider: Optional[OpenAIProvider] = None):
        """
        Initialize VPS agent.
        
        Args:
            ai_provider: AI provider instance (creates default if None)
        
        CRITICAL: Uses centralized AI config to ensure Azure OpenAI is used
        when configured, with automatic fallback to standard OpenAI.
        """
        if ai_provider is None:
            # Use centralized config to get Azure OpenAI settings (same as market research)
            provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
            
            logger.info(f"🔧 VPS_AGENT: Initializing with provider={provider_type}, model={model_name}")
            
            # Build config - gpt-5-mini doesn't support temperature
            is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
            
            config_kwargs = {
                "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
                "model_name": model_name,
                "max_tokens": 16000,  # gpt-5-mini needs large token budget
                "azure_endpoint": client_config.get("azure_endpoint"),
                "api_version": client_config.get("api_version"),
                "api_key": client_config.get("api_key")
            }
            
            if not is_gpt5_model:
                config_kwargs["temperature"] = 0.7  # Balanced creativity
            
            config = LLMConfig(**config_kwargs)
            ai_provider = OpenAIProvider(config)
            
            logger.info(f"✅ VPS_AGENT: AI provider initialized with {provider_type}")
        
        self.ai_provider = ai_provider
        logger.info(f"VPS Agent initialized with model: {ai_provider.config.model_name}")
    
    async def generate_vps(
        self,
        context: Dict[str, Any],
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate Value Proposition Statement from context.
        
        Args:
            context: Context data from MVPContextLoader
            creativity_level: AI creativity (0.0-1.0), affects temperature
            
        Returns:
            Dictionary with VPS components and metadata
            
        Raises:
            Exception: If generation fails
        """
        try:
            project_id = context.get('project_id')
            user_id = context.get('user_id')
            tenant_id = context.get('tenant_id')
            
            logger.info(f"🚀 Generating VPS for project {project_id}")
            logger.info(f"Context completeness: {context.get('context_completeness', 0):.2%}")
            
            # Create monitoring context
            monitoring_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                feature_id="mvp_vps_generation",
                workflow_name="mvp_workflow",
                step_name="generate_vps",
                environment="prod"
            )
            
            started_at = datetime.utcnow()
            
            # Format context for prompt
            from ..utils.context_loader import MVPContextLoader
            loader = MVPContextLoader(None, None)
            formatted_context = loader.format_context_for_prompt(context)
            
            logger.info(f"Formatted context length: {len(formatted_context)} characters")
            
            # Prepare messages
            messages = [
                {"role": "system", "content": VPS_SYSTEM_PROMPT},
                {"role": "user", "content": format_vps_prompt(formatted_context)}
            ]
            
            # Define response schema for structured output (OpenAI strict mode requires additionalProperties: false)
            response_schema = {
                "type": "object",
                "properties": {
                    "primary_statement": {
                        "type": "object",
                        "description": "Structured value proposition with template components",
                        "properties": {
                            "our": {
                                "type": "string",
                                "description": "Products or services offered"
                            },
                            "help": {
                                "type": "string",
                                "description": "Target customer segment"
                            },
                            "who_want_to": {
                                "type": "string",
                                "description": "Jobs to be done or customer goals"
                            },
                            "by": {
                                "type": "string",
                                "description": "Pain relievers - how we reduce/remove/avoid pains"
                            },
                            "and": {
                                "type": "string",
                                "description": "Gain creators - how we enable/increase gains"
                            },
                            "unlike": {
                                "type": "string",
                                "description": "Competitive differentiation"
                            }
                        },
                        "required": ["our", "help", "who_want_to", "by", "and", "unlike"],
                        "additionalProperties": False
                    },
                    "extended_statement": {
                        "type": "string",
                        "description": "Detailed explanation with evidence (150-250 words)"
                    },
                    "key_differentiators": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Clear, specific title for the differentiator"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Detailed description with evidence and impact"
                                },
                                "evidence_source": {
                                    "type": "string",
                                    "enum": ["field_research", "vpc_analysis", "assumption_validation", "market_evidence"],
                                    "description": "Source of evidence for this differentiator"
                                }
                            },
                            "required": ["title", "description", "evidence_source"],
                            "additionalProperties": False  # Required for OpenAI strict mode
                        },
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Exactly 3 key differentiators"
                    }
                },
                "required": ["primary_statement", "extended_statement", "key_differentiators"],
                "additionalProperties": False  # Required for OpenAI strict mode
            }
            
            # Update temperature based on creativity level (only for models that support it)
            model_name_lower = self.ai_provider.config.model_name.lower()
            is_gpt5_model = "gpt-5" in model_name_lower or "o1" in model_name_lower or "o3" in model_name_lower
            
            original_temp = getattr(self.ai_provider.config, 'temperature', None)
            if not is_gpt5_model and original_temp is not None:
                self.ai_provider.config.temperature = creativity_level
                logger.info(f"Calling AI with temperature: {creativity_level}")
            else:
                logger.info(f"Calling AI (model {self.ai_provider.config.model_name} - temperature not supported)")
            
            # Call AI with structured output using Responses API
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "vps_generation",
                        "schema": response_schema,
                        "strict": True
                    }
                }
            )
            
            # Restore original temperature if it was modified
            if not is_gpt5_model and original_temp is not None:
                self.ai_provider.config.temperature = original_temp
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
            monitoring = get_monitoring_service()
            usage = getattr(response, 'usage', {}) or {}
            actual_model = getattr(response, 'model', self.ai_provider.config.model_name)
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider="openai",  # MVP uses standard OpenAI
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
            
            logger.info("✅ Received AI response")
            
            # Parse response
            try:
                if not response.content:
                    raise ValueError("AI returned empty content")
                vps_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Response content: {response.content[:500] if response.content else 'None'}")
                raise ValueError(f"AI returned invalid JSON: {e}")
            
            # Validate response structure
            self._validate_vps_data(vps_data)
            
            # Add IDs to differentiators
            for idx, diff in enumerate(vps_data['key_differentiators'], 1):
                diff['id'] = f"diff-{idx:03d}"
            
            # Build generation metadata
            generation_metadata = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": response.model,
                "context_sources": list(context.keys()),
                "evidence_count": self._count_evidence(context),
                "confidence_score": self._calculate_confidence(context),
                "context_completeness": context.get('context_completeness', 0.0),
                "creativity_level": creativity_level,
                "version": "v1"
            }
            
            # Add usage info if available
            if response.usage:
                generation_metadata['usage'] = response.usage
            
            # Build final VPS with ordered fields: persona info first
            ordered_vps = {}
            
            # 1. Persona metadata first (if present)
            if 'persona_id' in context and 'persona_name' in context:
                ordered_vps['persona_id'] = context['persona_id']
                ordered_vps['persona_name'] = context['persona_name']
                logger.info(f"✅ Added persona metadata: {context['persona_name']} ({context['persona_id']})")
            
            # 2. Then VPS content
            ordered_vps['primary_statement'] = vps_data['primary_statement']
            ordered_vps['extended_statement'] = vps_data['extended_statement']
            ordered_vps['key_differentiators'] = vps_data['key_differentiators']
            
            # 3. Finally metadata
            ordered_vps['generation_metadata'] = generation_metadata
            
            logger.info(f"✅ Successfully generated VPS for project {project_id}")
            logger.info(f"Confidence score: {ordered_vps['generation_metadata']['confidence_score']:.2f}")
            
            return ordered_vps
            
        except Exception as e:
            finished_at = datetime.utcnow()
            
            # Record error (fire-and-forget)
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
            
            logger.error(f"❌ Error generating VPS: {e}")
            raise
    
    def _validate_vps_data(self, vps_data: Dict[str, Any]) -> None:
        """
        Validate VPS data structure.
        
        Args:
            vps_data: Generated VPS data
            
        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        required_fields = ['primary_statement', 'extended_statement', 'key_differentiators']
        for field in required_fields:
            if field not in vps_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate primary statement structure
        primary_stmt = vps_data['primary_statement']
        if not isinstance(primary_stmt, dict):
            raise ValueError("Primary statement must be a structured object")
        
        required_ps_fields = ['our', 'help', 'who_want_to', 'by', 'and', 'unlike']
        for field in required_ps_fields:
            if field not in primary_stmt:
                raise ValueError(f"Primary statement missing required field: {field}")
        
        # Validate primary statement length (combined text)
        # Updated for persona-specific VPS: shorter, more concise statements
        primary_text = ' '.join(primary_stmt.values())
        primary_words = len(primary_text.split())
        if primary_words < 20 or primary_words > 80:
            logger.warning(f"Primary statement length ({primary_words} words) outside recommended range (30-60)")
        
        # Validate extended statement length
        # Updated for persona-specific VPS: more focused statements
        extended_words = len(vps_data['extended_statement'].split())
        if extended_words < 100 or extended_words > 220:
            logger.warning(f"Extended statement length ({extended_words} words) outside recommended range (120-180)")
        
        # Validate differentiators
        if len(vps_data['key_differentiators']) != 3:
            raise ValueError(f"Expected 3 differentiators, got {len(vps_data['key_differentiators'])}")
        
        for idx, diff in enumerate(vps_data['key_differentiators'], 1):
            if 'title' not in diff or 'description' not in diff or 'evidence_source' not in diff:
                raise ValueError(f"Differentiator {idx} missing required fields")
    
    def _count_evidence(self, context: Dict[str, Any]) -> int:
        """Count evidence items in context."""
        count = 0
        count += len(context.get('pv_report_insights', []))
        count += len(context.get('actionable_insights', []))
        count += len(context.get('assumptions', []))
        count += len(context.get('hypotheses', []))
        return count
    
    def _calculate_confidence(self, context: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on context completeness and quality.
        
        Args:
            context: Context data
            
        Returns:
            Confidence score (0.0-1.0)
        """
        score = 0.0
        
        # Base score from context completeness (50%)
        score += context.get('context_completeness', 0.0) * 0.5
        
        # Evidence quality (30%)
        pv_insights = context.get('pv_report_insights', [])
        high_quality_insights = sum(1 for i in pv_insights if i.get('relevance_score', 0) > 0.8)
        if pv_insights:
            evidence_quality = high_quality_insights / len(pv_insights)
            score += evidence_quality * 0.3
        
        # Field research validation (20%)
        assumptions = context.get('assumptions', [])
        if assumptions:
            score += 0.20
        
        return round(min(score, 1.0), 2)
