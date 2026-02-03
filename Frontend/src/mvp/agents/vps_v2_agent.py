"""
VPS v2 Refinement Agent

AI-powered agent for refining Value Proposition Statements based on solution critique feedback.
Uses RAG to dynamically retrieve relevant critique insights and intelligently decide what to update.

MIGRATED TO RESPONSES API (Dec 2025):
- Uses generate_responses() for gpt-5-mini
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.config import get_client_config, ModelUseCase
from ..prompts.vps_v2_prompts import VPS_V2_SYSTEM_PROMPT, format_vps_v2_prompt

# Import AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class VPSV2RefinementAgent:
    """Agent for refining VPS v1 based on solution critique feedback using RAG."""
    
    def __init__(self, ai_provider: Optional[OpenAIProvider] = None):
        """
        Initialize VPS v2 refinement agent.
        
        Args:
            ai_provider: AI provider instance (creates default if None)
        
        CRITICAL: Uses centralized AI config to ensure Azure OpenAI is used
        when configured, with automatic fallback to standard OpenAI.
        """
        if ai_provider is None:
            # Use centralized config to get Azure OpenAI settings (same as market research)
            provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
            
            logger.info(f"🔧 VPS_V2_AGENT: Initializing with provider={provider_type}, model={model_name}")
            
            # Build config - gpt-5-mini doesn't support temperature
            is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
            
            config_kwargs = {
                "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
                "model_name": model_name,
                "max_tokens": 3500,  # More tokens for detailed refinement
                "azure_endpoint": client_config.get("azure_endpoint"),
                "api_version": client_config.get("api_version"),
                "api_key": client_config.get("api_key")
            }
            
            if not is_gpt5_model:
                config_kwargs["temperature"] = 0.7
            
            config = LLMConfig(**config_kwargs)
            ai_provider = OpenAIProvider(config)
            
            logger.info(f"✅ VPS_V2_AGENT: AI provider initialized with {provider_type}")
        
        self.ai_provider = ai_provider
        logger.info(f"VPS v2 Refinement Agent initialized with model: {ai_provider.config.model_name}")
    
    async def refine_vps(
        self,
        vps_v1: Dict[str, Any],
        critique_chunks: List[Dict[str, Any]],
        original_context: Dict[str, Any],
        creativity_level: float = 0.7
    ) -> Dict[str, Any]:
        """
        Refine VPS v1 based on critique feedback.
        
        Args:
            vps_v1: Current VPS v1 data
            critique_chunks: RAG-retrieved critique chunks
            original_context: Original context from VPS v1 generation
            creativity_level: AI creativity (0.0-1.0)
            
        Returns:
            Dictionary with refined VPS v2 and refinement metadata
            
        Raises:
            Exception: If refinement fails
        """
        try:
            project_id = original_context.get('project_id')
            user_id = original_context.get('user_id')
            tenant_id = original_context.get('tenant_id')
            
            logger.info(f"🚀 Refining VPS for project {project_id}")
            logger.info(f"VPS v1 confidence: {vps_v1.get('generation_metadata', {}).get('confidence_score', 'N/A')}")
            logger.info(f"Critique chunks available: {len(critique_chunks)}")
            
            # Create monitoring context
            monitoring_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                feature_id="mvp_vps_v2_refinement",
                workflow_name="mvp_workflow",
                step_name="refine_vps",
                environment="prod"
            )
            
            started_at = datetime.utcnow()
            
            # Build minimal formatted context (VPS v2 only needs project metadata)
            formatted_context = f"""
PROJECT METADATA:
- Project ID: {original_context.get('project_id', 'N/A')}
- Tenant ID: {original_context.get('tenant_id', 'N/A')}

NOTE: VPS v2 refinement focuses solely on the critique feedback against VPS v1.
All other context (VPC, personas, market research) is already embedded in VPS v1.
"""
            
            logger.info(f"Using minimal context (no PV report/insights/personas loading)")
            logger.info(f"Using {len(critique_chunks)} critique chunks for refinement")
            
            # Prepare messages
            messages = [
                {"role": "system", "content": VPS_V2_SYSTEM_PROMPT},
                {"role": "user", "content": format_vps_v2_prompt(
                    vps_v1=vps_v1,
                    critique_chunks=critique_chunks,
                    original_context=formatted_context
                )}
            ]
            
            # Define response schema for structured output
            # CRITICAL: Schema enforces 90% preservation of VPS v1
            response_schema = {
                "type": "object",
                "properties": {
                    "refinement_decision": {
                        "type": "string",
                        "enum": ["no_changes", "minimal_refinement", "partial_refinement"],
                        "description": "no_changes (90% of cases), minimal_refinement (1 field), partial_refinement (2 fields max)"
                    },
                    "refinement_rationale": {
                        "type": "string",
                        "description": "Explain what critique points were found and why they do/don't require primary statement changes"
                    },
                    "primary_statement": {
                        "type": "object",
                        "description": "COPY FROM VPS v1 - only modify fields explicitly required by critique",
                        "properties": {
                            "our": {
                                "type": "string",
                                "description": "COPY FROM v1 unless critique explicitly requires change"
                            },
                            "help": {
                                "type": "string",
                                "description": "COPY FROM v1 unless critique explicitly requires change"
                            },
                            "who_want_to": {
                                "type": "string",
                                "description": "COPY FROM v1 unless critique explicitly requires change"
                            },
                            "by": {
                                "type": "string",
                                "description": "COPY FROM v1 unless critique explicitly requires change"
                            },
                            "and": {
                                "type": "string",
                                "description": "COPY FROM v1 unless critique explicitly requires change"
                            },
                            "unlike": {
                                "type": "string",
                                "description": "COPY FROM v1 unless critique explicitly requires change"
                            }
                        },
                        "required": ["our", "help", "who_want_to", "by", "and", "unlike"],
                        "additionalProperties": False
                    },
                    "primary_statement_changed": {
                        "type": "boolean",
                        "description": "Should be FALSE in 90% of cases - only true if critique explicitly required field changes"
                    },
                    "primary_statement_reason": {
                        "type": "string",
                        "description": "List which fields were kept identical to v1 and why"
                    },
                    "fields_changed_count": {
                        "type": "integer",
                        "description": "Number of fields changed from v1 (0, 1, or 2 max)"
                    },
                    "fields_kept_identical": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of field names copied exactly from v1 (should be 4-6 fields)"
                    },
                    "extended_statement": {
                        "type": "string",
                        "description": "Address critique concerns HERE instead of changing primary statement"
                    },
                    "extended_statement_changed": {
                        "type": "boolean",
                        "description": "Extended statement can change to address critique without touching primary"
                    },
                    "extended_statement_reason": {
                        "type": "string",
                        "description": "How extended statement addresses critique points"
                    },
                    "key_differentiators": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "evidence_source": {
                                    "type": "string",
                                    "enum": ["vpc_analysis", "field_research", "assumption_validation", "market_evidence", "market_research_analysis", "critique_insight"]
                                },
                                "changed": {"type": "boolean"},
                                "change_reason": {"type": "string"}
                            },
                            "required": ["title", "description", "evidence_source", "changed", "change_reason"],
                            "additionalProperties": False
                        },
                        "minItems": 3,
                        "maxItems": 3
                    },
                    "critique_sources_used": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dimension": {"type": "string"},
                                "concern": {"type": "string"},
                                "how_addressed": {"type": "string"}
                            },
                            "required": ["dimension", "concern", "how_addressed"],
                            "additionalProperties": False
                        }
                    },
                    "overall_improvement_summary": {
                        "type": "string",
                        "description": "Should often say 'Primary statement preserved, critique addressed in extended statement'"
                    }
                },
                "required": [
                    "refinement_decision", "refinement_rationale",
                    "primary_statement", "primary_statement_changed", "primary_statement_reason",
                    "fields_changed_count", "fields_kept_identical",
                    "extended_statement", "extended_statement_changed", "extended_statement_reason",
                    "key_differentiators", "critique_sources_used", "overall_improvement_summary"
                ],
                "additionalProperties": False
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
                        "name": "vps_v2_refinement",
                        "schema": response_schema,
                        "strict": True
                    }
                }
            )
            
            # Restore original temperature if it was modified
            if not is_gpt5_model and original_temp is not None:
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
                vps_v2_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Response content: {response.content[:500] if response.content else 'None'}")
                raise ValueError(f"AI returned invalid JSON: {e}")
            
            # Validate response structure
            self._validate_vps_v2_data(vps_v2_data)
            
            # Add IDs to differentiators
            for idx, diff in enumerate(vps_v2_data['key_differentiators'], 1):
                diff['id'] = f"diff-{idx:03d}"
            
            # CRITICAL: Validate v1 preservation - count how many fields actually changed
            v1_primary = vps_v1.get('primary_statement', {})
            v2_primary = vps_v2_data['primary_statement']
            
            actual_changes = self._count_actual_field_changes(v1_primary, v2_primary)
            fields_preserved = 6 - actual_changes
            preservation_percentage = (fields_preserved / 6) * 100
            
            logger.info(f"📊 V1 PRESERVATION CHECK:")
            logger.info(f"   - Fields changed: {actual_changes}/6")
            logger.info(f"   - Fields preserved: {fields_preserved}/6")
            logger.info(f"   - Preservation: {preservation_percentage:.1f}%")
            
            # Warn if too many changes
            if actual_changes > 2:
                logger.warning(f"⚠️ WARNING: {actual_changes} fields changed - exceeds recommended max of 2")
                logger.warning(f"   VPS v2 may have deviated too much from v1")
            
            # Build final VPS v2 structure (same as v1 format + refinement metadata)
            refined_vps = {
                "persona_id": vps_v1.get('persona_id'),  # Preserve persona metadata
                "persona_name": vps_v1.get('persona_name'),  # Preserve persona metadata
                "primary_statement": vps_v2_data['primary_statement'],
                "extended_statement": vps_v2_data['extended_statement'],
                "key_differentiators": vps_v2_data['key_differentiators'],
                "generation_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "model_used": response.model,
                    "context_sources": list(original_context.keys()),
                    "evidence_count": self._count_evidence(original_context),
                    "confidence_score": self._calculate_refined_confidence(vps_v2_data, original_context),
                    "context_completeness": original_context.get('context_completeness', 0.0),
                    "creativity_level": creativity_level,
                    "version": "v2",
                    "refined_from": "v1",
                    "critique_chunks_used": len(critique_chunks)
                },
                "refinement_metadata": {
                    "refinement_decision": vps_v2_data['refinement_decision'],
                    "refinement_rationale": vps_v2_data['refinement_rationale'],
                    "primary_statement_changed": vps_v2_data['primary_statement_changed'],
                    "primary_statement_reason": vps_v2_data['primary_statement_reason'],
                    "extended_statement_changed": vps_v2_data['extended_statement_changed'],
                    "extended_statement_reason": vps_v2_data['extended_statement_reason'],
                    "fields_changed_count": vps_v2_data.get('fields_changed_count', actual_changes),
                    "fields_kept_identical": vps_v2_data.get('fields_kept_identical', []),
                    "actual_fields_changed": actual_changes,
                    "preservation_percentage": preservation_percentage,
                    "differentiators_changed": [
                        {
                            "id": diff['id'],
                            "title": diff['title'],
                            "changed": diff['changed'],
                            "reason": diff['change_reason']
                        }
                        for diff in vps_v2_data['key_differentiators']
                    ],
                    "critique_sources_used": vps_v2_data['critique_sources_used'],
                    "overall_improvement_summary": vps_v2_data['overall_improvement_summary'],
                    "changes_count": self._count_changes(vps_v2_data)
                }
            }
            
            # Add usage info
            if response.usage:
                refined_vps['generation_metadata']['usage'] = response.usage
            
            logger.info(f"✅ Successfully refined VPS for project {project_id}")
            logger.info(f"Refinement decision: {vps_v2_data['refinement_decision']}")
            logger.info(f"Changes count: {refined_vps['refinement_metadata']['changes_count']}")
            logger.info(f"Refined confidence score: {refined_vps['generation_metadata']['confidence_score']:.2f}")
            
            return refined_vps
            
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
            
            logger.error(f"❌ Error refining VPS: {e}")
            raise
    
    def _validate_vps_v2_data(self, vps_v2_data: Dict[str, Any]) -> None:
        """Validate VPS v2 response structure."""
        required_fields = [
            'refinement_decision', 'primary_statement', 'extended_statement',
            'key_differentiators', 'critique_sources_used'
        ]
        for field in required_fields:
            if field not in vps_v2_data:
                raise ValueError(f"Missing required field in VPS v2: {field}")
        
        # Validate primary statement structure
        primary_stmt = vps_v2_data['primary_statement']
        if not isinstance(primary_stmt, dict):
            raise ValueError("Primary statement must be a structured object")
        
        required_ps_fields = ['our', 'help', 'who_want_to', 'by', 'and', 'unlike']
        for field in required_ps_fields:
            if field not in primary_stmt:
                raise ValueError(f"Primary statement missing required field: {field}")
        
        # Validate differentiators count
        if len(vps_v2_data['key_differentiators']) != 3:
            raise ValueError(f"Expected 3 differentiators, got {len(vps_v2_data['key_differentiators'])}")
    
    def _count_evidence(self, context: Dict[str, Any]) -> int:
        """Count evidence items in context."""
        count = 0
        count += len(context.get('pv_report_insights', []))
        count += len(context.get('actionable_insights', []))
        count += len(context.get('assumptions', []))
        count += len(context.get('hypotheses', []))
        return count
    
    def _calculate_refined_confidence(self, vps_v2_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Calculate confidence score for refined VPS.
        Higher confidence if changes address critique concerns.
        """
        base_score = context.get('context_completeness', 0.0) * 0.4
        
        # Critique integration boost (30%)
        critique_sources = vps_v2_data.get('critique_sources_used', [])
        if critique_sources:
            critique_boost = min(len(critique_sources) / 5.0, 1.0) * 0.3
            base_score += critique_boost
        
        # Refinement quality (30%)
        if vps_v2_data['refinement_decision'] == 'no_changes':
            # High confidence if no changes needed (critique validated v1)
            base_score += 0.30
        elif vps_v2_data['refinement_decision'] == 'minimal_refinement':
            # High confidence for single field adjustment
            base_score += 0.28
        elif vps_v2_data['refinement_decision'] == 'partial_refinement':
            # Medium-high confidence for targeted improvements (max 2 fields)
            base_score += 0.25
        
        return round(min(base_score, 1.0), 2)
    
    def _count_changes(self, vps_v2_data: Dict[str, Any]) -> int:
        """Count how many components were changed."""
        changes = 0
        if vps_v2_data.get('primary_statement_changed'):
            changes += 1
        if vps_v2_data.get('extended_statement_changed'):
            changes += 1
        for diff in vps_v2_data.get('key_differentiators', []):
            if diff.get('changed'):
                changes += 1
        return changes
    
    def _count_actual_field_changes(self, v1_primary: Dict[str, Any], v2_primary: Dict[str, Any]) -> int:
        """
        Count how many primary statement fields actually changed between v1 and v2.
        
        This is the ACTUAL verification - compares field by field to see real differences.
        """
        if not v1_primary or not v2_primary:
            return 6  # Assume all changed if missing data
        
        fields = ['our', 'help', 'who_want_to', 'by', 'and', 'unlike']
        changes = 0
        
        for field in fields:
            v1_value = str(v1_primary.get(field, '')).strip().lower()
            v2_value = str(v2_primary.get(field, '')).strip().lower()
            
            if v1_value != v2_value:
                changes += 1
                logger.info(f"   📝 Field '{field}' changed:")
                logger.info(f"      v1: {v1_primary.get(field, 'N/A')[:50]}")
                logger.info(f"      v2: {v2_primary.get(field, 'N/A')[:50]}")
        
        return changes
