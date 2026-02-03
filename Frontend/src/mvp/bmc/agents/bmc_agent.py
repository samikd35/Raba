"""
BMC Generation Agent

AI-powered agent for generating Business Model Canvas blocks using Azure OpenAI.
Generates all 9 BMC blocks sequentially with evidence-based, structured output.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
import logging
import json
import asyncio

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mvp.bmc.prompts.bmc_prompts import (
    BMC_SYSTEM_PROMPT,
    format_customer_segments_prompt,
    format_value_propositions_prompt,
    format_channels_prompt,
    format_customer_relationships_prompt,
    format_revenue_streams_prompt,
    format_key_resources_prompt,
    format_key_activities_prompt,
    format_key_partnerships_prompt,
    format_cost_structure_prompt
)

# Import AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class BMCGenerationAgent:
    """
    Agent for generating Business Model Canvas blocks sequentially using Azure OpenAI.
    
    Each block builds upon previously generated blocks for consistency and cross-referencing.
    """
    
    def __init__(self, ai_provider: Optional[OpenAIProvider] = None):
        """
        Initialize with Azure OpenAI GPT-4 for complex business reasoning.
        
        CRITICAL: Uses centralized AI config to ensure Azure OpenAI is used
        when configured, with automatic fallback to standard OpenAI.
        - Model: Azure OpenAI GPT-4.1 (via centralized config)
        - Temperature: 0.7 for balanced creativity
        - Max tokens: 3000 per block
        """
        if ai_provider is None:
            # Use centralized config to get Azure OpenAI settings (same as market research)
            provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
            
            logger.info(f"🔧 BMC_AGENT: Initializing with provider={provider_type}, model={model_name}")
            
            # Build config - gpt-5-mini doesn't support temperature
            is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
            
            config_kwargs = {
                "provider_name": str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
                "model_name": model_name,
                "max_tokens": 18000 if is_gpt5_model else 3000,  # gpt-5-mini needs more tokens for complex structured outputs
                "azure_endpoint": client_config.get("azure_endpoint"),
                "api_version": client_config.get("api_version"),
                "api_key": client_config.get("api_key")
            }
            
            if not is_gpt5_model:
                config_kwargs["temperature"] = 0.7
            
            config = LLMConfig(**config_kwargs)
            ai_provider = OpenAIProvider(config)
            
            logger.info(f"✅ BMC_AGENT: AI provider initialized with {provider_type}")
        
        self.ai_provider = ai_provider
        logger.info(f"BMC Generation Agent initialized with model: {ai_provider.config.model_name}")
    
    async def generate_customer_segments(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 1: Customer Segments (1-3 items).
        
        Examples from bmc.md:
        - Netflix: 1 segment (Movies and online entertainment enthusiasts)
        - Vuba Vuba: 2 segments (Hungry people, Restaurant owners)
        
        Args:
            context: Full context including VPS v1, VPC 2.0, personas, research
            
        Returns:
            Customer segments data with generation metadata
            
        Raises:
            ValueError: If generation fails or output invalid
        """
        start_time = time.time()
        logger.info("🎯 Generating Block 1: Customer Segments")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_customer_segments",
            workflow_name="mvp_workflow",
            step_name="generate_customer_segments",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            # Format context for this block
            from src.mvp.bmc.utils.bmc_context_loader import BMCContextLoader
            # We'll use the context directly since it's already formatted
            
            # Build messages
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_customer_segments_prompt(
                    json.dumps(context, indent=2)
                )}
            ]
            
            # Define JSON schema for structured output
            response_schema = {
                "type": "object",
                "properties": {
                    "segments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "characteristics": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "size_estimate": {"type": "string"},
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"]
                                },
                                "evidence_source": {"type": "string"},
                                "persona_mapping": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["id", "name", "description", "characteristics", 
                                       "size_estimate", "priority", "evidence_source", "persona_mapping"],
                            "additionalProperties": False
                        },
                        "minItems": 1,
                        "maxItems": 3
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["segments", "generation_metadata"],
                "additionalProperties": False
            }
            
            # Call Azure OpenAI with structured output
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "customer_segments_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            # Parse response
            if not response.content:
                logger.error(f"AI returned empty content for customer segments. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for customer segments")
            segments_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            # Add generation metadata
            generation_time = time.time() - start_time
            segments_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            # Validate
            self._validate_customer_segments(segments_data)
            
            logger.info(f"✅ Generated {len(segments_data['segments'])} customer segments in {generation_time:.2f}s")
            
            return segments_data
            
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
            
            logger.error(f"❌ Error generating customer segments: {e}")
            raise ValueError(f"Failed to generate customer segments: {e}")
    
    async def generate_value_propositions(
        self,
        context: Dict[str, Any],
        customer_segments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 2: Value Propositions (2-6 items).
        
        Examples from bmc.md:
        - Netflix: 7 value props (24/7 on-demand, unlimited HD, no commercials, etc.)
        - Vuba Vuba: 6 value props (Fast delivery, online food court, etc.)
        
        Args:
            context: Full context including VPS v1, VPC 2.0, personas, research
            customer_segments: Generated customer segments from Block 1
            
        Returns:
            Value propositions data with generation metadata
            
        Raises:
            ValueError: If generation fails or output invalid
        """
        start_time = time.time()
        logger.info("🎯 Generating Block 2: Value Propositions")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_value_propositions",
            workflow_name="mvp_workflow",
            step_name="generate_value_propositions",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            # Add customer segments to context
            enriched_context = {
                **context,
                "customer_segments": customer_segments
            }
            
            # Build messages
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_value_propositions_prompt(
                    json.dumps(enriched_context, indent=2)
                )}
            ]
            
            # Define JSON schema
            response_schema = {
                "type": "object",
                "properties": {
                    "propositions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "segment_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                    "maxItems": 1,
                                    "description": "Exactly ONE segment ID - the primary target segment for this VP"
                                },
                                "value_statement": {"type": "string"},
                                "key_benefits": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "differentiation": {"type": "string"},
                                "evidence_source": {"type": "string"},
                                "vpc_fit": {
                                    "type": "object",
                                    "properties": {
                                        "jobs_addressed": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "pains_relieved": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "gains_created": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["jobs_addressed", "pains_relieved", "gains_created"],
                                    "additionalProperties": False
                                }
                            },
                            "required": ["id", "name", "segment_ids", "value_statement", "key_benefits",
                                       "differentiation", "evidence_source", "vpc_fit"],
                            "additionalProperties": False
                        },
                        "minItems": 2,
                        "maxItems": 6
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["propositions", "generation_metadata"],
                "additionalProperties": False
            }
            
            # Call Azure OpenAI
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "value_propositions_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            # Parse response
            if not response.content:
                logger.error(f"AI returned empty content for value propositions. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for value propositions")
            propositions_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            # Add generation metadata
            generation_time = time.time() - start_time
            propositions_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            # Validate
            self._validate_value_propositions(propositions_data, customer_segments)
            
            logger.info(f"✅ Generated {len(propositions_data['propositions'])} value propositions in {generation_time:.2f}s")
            
            return propositions_data
            
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
            
            logger.error(f"❌ Error generating value propositions: {e}")
            raise ValueError(f"Failed to generate value propositions: {e}")
    
    # ==================== VALIDATION METHODS ====================
    
    def _validate_customer_segments(self, data: Dict[str, Any]) -> None:
        """Validate customer segments data."""
        if not data.get("segments"):
            raise ValueError("No customer segments generated")
        
        segments = data["segments"]
        if len(segments) < 1 or len(segments) > 3:
            raise ValueError(f"Invalid segment count: {len(segments)} (must be 1-3)")
        
        for segment in segments:
            if not segment.get("id") or not segment.get("name"):
                raise ValueError("Segment missing required fields")
            if not segment.get("evidence_source"):
                raise ValueError(f"Segment {segment['id']} missing evidence source")
        
        logger.info("✅ Customer segments validation passed")
    
    def _validate_value_propositions(
        self,
        data: Dict[str, Any],
        customer_segments: Dict[str, Any]
    ) -> None:
        """Validate value propositions data."""
        if not data.get("propositions"):
            raise ValueError("No value propositions generated")
        
        propositions = data["propositions"]
        if len(propositions) < 2 or len(propositions) > 6:
            raise ValueError(f"Invalid proposition count: {len(propositions)} (must be 2-6)")
        
        # Get valid segment IDs
        valid_segment_ids = {seg["id"] for seg in customer_segments["segments"]}
        
        for prop in propositions:
            if not prop.get("id") or not prop.get("value_statement"):
                raise ValueError("Proposition missing required fields")
            if not prop.get("evidence_source"):
                raise ValueError(f"Proposition {prop['id']} missing evidence source")
            
            # Validate segment references
            for seg_id in prop.get("segment_ids", []):
                if seg_id not in valid_segment_ids:
                    raise ValueError(f"Proposition {prop['id']} references invalid segment {seg_id}")
        
        logger.info("✅ Value propositions validation passed")
    
    async def generate_channels(
        self,
        context: Dict[str, Any],
        customer_segments: Dict[str, Any],
        value_propositions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 3: Channels (3-6 items).
        
        Examples from bmc.md:
        - Netflix: 6 channels
        - Vuba Vuba: 4 channels
        
        Args:
            context: Full context
            customer_segments: Block 1
            value_propositions: Block 2
            
        Returns:
            Channels data with generation metadata
        """
        start_time = time.time()
        logger.info("🎯 Generating Block 3: Channels")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_channels",
            workflow_name="mvp_workflow",
            step_name="generate_channels",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {
                **context,
                "customer_segments": customer_segments,
                "value_propositions": value_propositions
            }
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_channels_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "channels": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "phases": {"type": "array", "items": {"type": "string"}},
                                "segment_ids": {"type": "array", "items": {"type": "string"}},
                                "description": {"type": "string"},
                                "cost_structure": {"type": "string"},
                                "reach_potential": {"type": "string"},
                                "evidence_source": {"type": "string"}
                            },
                            "required": ["id", "name", "type", "phases", "segment_ids", "description", 
                                       "cost_structure", "reach_potential", "evidence_source"],
                            "additionalProperties": False
                        },
                        "minItems": 3,
                        "maxItems": 6
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["channels", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "channels_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for channels. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for channels")
            channels_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            channels_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            self._validate_channels(channels_data, customer_segments)
            logger.info(f"✅ Generated {len(channels_data['channels'])} channels in {generation_time:.2f}s")
            
            return channels_data
            
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
            
            logger.error(f"❌ Error generating channels: {e}")
            raise ValueError(f"Failed to generate channels: {e}")
    
    async def generate_customer_relationships(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 4: Customer Relationships (2-6 items).
        
        Args:
            context: Full context
            previous_blocks: Blocks 1-3
            
        Returns:
            Customer relationships data
        """
        start_time = time.time()
        logger.info("🎯 Generating Block 4: Customer Relationships")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_customer_relationships",
            workflow_name="mvp_workflow",
            step_name="generate_customer_relationships",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {**context, **previous_blocks}
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_customer_relationships_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "segment_ids": {"type": "array", "items": {"type": "string"}},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "acquisition_strategy": {"type": "string"},
                                "retention_strategy": {"type": "string"},
                                "growth_strategy": {"type": "string"},
                                "evidence_source": {"type": "string"}
                            },
                            "required": ["id", "name", "segment_ids", "type", "description", "acquisition_strategy",
                                       "retention_strategy", "growth_strategy", "evidence_source"],
                            "additionalProperties": False
                        },
                        "minItems": 2,
                        "maxItems": 6
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["relationships", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "customer_relationships_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for relationships. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for relationships")
            relationships_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            relationships_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            logger.info(f"✅ Generated {len(relationships_data['relationships'])} relationships in {generation_time:.2f}s")
            
            return relationships_data
            
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
            
            logger.error(f"❌ Error generating customer relationships: {e}")
            raise ValueError(f"Failed to generate customer relationships: {e}")
    
    async def generate_revenue_streams(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate Block 5: Revenue Streams (2-5 items).
        
        Args:
            context: Full context
            previous_blocks: Blocks 1-4
            
        Returns:
            Revenue streams data
        """
        start_time = time.time()
        logger.info("🎯 Generating Block 5: Revenue Streams")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_revenue_streams",
            workflow_name="mvp_workflow",
            step_name="generate_revenue_streams",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {**context, **previous_blocks}
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_revenue_streams_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "revenue_streams": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "segment_ids": {"type": "array", "items": {"type": "string"}},
                                "pricing_mechanism": {"type": "string"},
                                "pricing_strategy": {"type": "string"},
                                "revenue_potential": {"type": "string"},
                                "evidence_source": {"type": "string"}
                            },
                            "required": ["id", "name", "type", "segment_ids", "pricing_mechanism",
                                       "pricing_strategy", "revenue_potential", "evidence_source"],
                            "additionalProperties": False
                        },
                        "minItems": 2,
                        "maxItems": 5
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["revenue_streams", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "revenue_streams_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for revenue streams. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for revenue streams")
            revenue_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            revenue_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            logger.info(f"✅ Generated {len(revenue_data['revenue_streams'])} revenue streams in {generation_time:.2f}s")
            
            return revenue_data
            
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
            
            logger.error(f"❌ Error generating revenue streams: {e}")
            raise ValueError(f"Failed to generate revenue streams: {e}")
    
    async def generate_key_resources(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Block 6: Key Resources (3-6 items)."""
        start_time = time.time()
        logger.info("🎯 Generating Block 6: Key Resources")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_key_resources",
            workflow_name="mvp_workflow",
            step_name="generate_key_resources",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {**context, **previous_blocks}
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_key_resources_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "resources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "criticality": {"type": "string"},
                                "required_for": {"type": "array", "items": {"type": "string"}},
                                "acquisition_strategy": {"type": "string"},
                                "evidence_source": {"type": "string"}
                            },
                            "required": ["id", "name", "type", "description", "criticality",
                                       "required_for", "acquisition_strategy", "evidence_source"],
                            "additionalProperties": False
                        },
                        "minItems": 3,
                        "maxItems": 6
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["resources", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "key_resources_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for key resources. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for key resources")
            resources_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            resources_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            logger.info(f"✅ Generated {len(resources_data['resources'])} key resources in {generation_time:.2f}s")
            
            return resources_data
            
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
            
            logger.error(f"❌ Error generating key resources: {e}")
            raise ValueError(f"Failed to generate key resources: {e}")
    
    async def generate_key_activities(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Block 7: Key Activities (3-7 items)."""
        start_time = time.time()
        logger.info("🎯 Generating Block 7: Key Activities")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_key_activities",
            workflow_name="mvp_workflow",
            step_name="generate_key_activities",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {**context, **previous_blocks}
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_key_activities_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "activities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "criticality": {"type": "string"},
                                "required_for": {"type": "array", "items": {"type": "string"}},
                                "resources_needed": {"type": "array", "items": {"type": "string"}},
                                "evidence_source": {"type": "string"}
                            },
                            "required": ["id", "name", "type", "description", "criticality",
                                       "required_for", "resources_needed", "evidence_source"],
                            "additionalProperties": False
                        },
                        "minItems": 3,
                        "maxItems": 7
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["activities", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "key_activities_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for key activities. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for key activities")
            activities_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            activities_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            logger.info(f"✅ Generated {len(activities_data['activities'])} key activities in {generation_time:.2f}s")
            
            return activities_data
            
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
            
            logger.error(f"❌ Error generating key activities: {e}")
            raise ValueError(f"Failed to generate key activities: {e}")
    
    async def generate_key_partnerships(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Block 8: Key Partnerships (3-9 items)."""
        start_time = time.time()
        logger.info("🎯 Generating Block 8: Key Partnerships")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_key_partnerships",
            workflow_name="mvp_workflow",
            step_name="generate_key_partnerships",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {**context, **previous_blocks}
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_key_partnerships_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "partnerships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "partner_type": {
                                    "type": "string",
                                    "enum": ["strategic_alliance", "coopetition", "joint_venture", "buyer_supplier"]
                                },
                                "partner_description": {"type": "string"},
                                "motivation": {"type": "string"},
                                "value_contribution": {"type": "string"},
                                "activities_supported": {"type": "array", "items": {"type": "string"}},
                                "resources_provided": {"type": "array", "items": {"type": "string"}},
                                "evidence_source": {"type": "string"}
                            },
                            "required": ["id", "name", "partner_type", "partner_description", "motivation",
                                       "value_contribution", "activities_supported", "resources_provided",
                                       "evidence_source"],
                            "additionalProperties": False
                        },
                        "minItems": 3,
                        "maxItems": 9
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["partnerships", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "key_partnerships_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for key partnerships. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for key partnerships")
            partnerships_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            partnerships_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            logger.info(f"✅ Generated {len(partnerships_data['partnerships'])} key partnerships in {generation_time:.2f}s")
            
            return partnerships_data
            
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
            
            logger.error(f"❌ Error generating key partnerships: {e}")
            raise ValueError(f"Failed to generate key partnerships: {e}")
    
    async def generate_cost_structure(
        self,
        context: Dict[str, Any],
        previous_blocks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Block 9: Cost Structure (4-9 cost categories)."""
        start_time = time.time()
        logger.info("🎯 Generating Block 9: Cost Structure")
        
        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=context.get('user_id'),
            tenant_id=context.get('tenant_id'),
            project_id=context.get('project_id'),
            feature_id="mvp_bmc_cost_structure",
            workflow_name="mvp_workflow",
            step_name="generate_cost_structure",
            environment="prod"
        )
        started_at = datetime.utcnow()
        
        try:
            enriched_context = {**context, **previous_blocks}
            
            messages = [
                {"role": "system", "content": BMC_SYSTEM_PROMPT},
                {"role": "user", "content": format_cost_structure_prompt(json.dumps(enriched_context, indent=2))}
            ]
            
            response_schema = {
                "type": "object",
                "properties": {
                    "cost_structure": {
                        "type": "object",
                        "properties": {
                            "model_type": {"type": "string"},
                            "cost_categories": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "description": {"type": "string"},
                                        "related_resources": {"type": "array", "items": {"type": "string"}},
                                        "related_activities": {"type": "array", "items": {"type": "string"}},
                                        "related_partnerships": {"type": "array", "items": {"type": "string"}},
                                        "cost_estimate": {"type": "string"},
                                        "optimization_potential": {"type": "string"},
                                        "evidence_source": {"type": "string"}
                                    },
                                    "required": ["id", "name", "type", "description", "related_resources",
                                               "related_activities", "related_partnerships", "cost_estimate",
                                               "optimization_potential", "evidence_source"],
                                    "additionalProperties": False
                                },
                                "minItems": 4,
                                "maxItems": 9
                            },
                            "economies_of_scale": {"type": "string"},
                            "economies_of_scope": {"type": "string"}
                        },
                        "required": ["model_type", "cost_categories", "economies_of_scale", "economies_of_scope"],
                        "additionalProperties": False
                    },
                    "generation_metadata": {
                        "type": "object",
                        "properties": {
                            "generated_at": {"type": "string"},
                            "model_used": {"type": "string"},
                            "generation_time": {"type": "number"}
                        },
                        "required": ["generated_at", "model_used", "generation_time"],
                        "additionalProperties": False
                    }
                },
                "required": ["cost_structure", "generation_metadata"],
                "additionalProperties": False
            }
            
            response = await self.ai_provider.generate_responses(
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "cost_structure_response",
                        "strict": True,
                        "schema": response_schema
                    }
                }
            )
            
            if not response.content:
                logger.error(f"AI returned empty content for cost structure. Finish reason: {response.finish_reason}, usage: {response.usage}")
                raise ValueError("AI returned empty content for cost structure")
            cost_data = json.loads(response.content)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
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
            
            generation_time = time.time() - start_time
            cost_data["generation_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.ai_provider.config.model_name,
                "generation_time": generation_time
            }
            
            logger.info(f"✅ Generated cost structure with {len(cost_data['cost_structure']['cost_categories'])} categories in {generation_time:.2f}s")
            
            return cost_data
            
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
            
            logger.error(f"❌ Error generating cost structure: {e}")
            raise ValueError(f"Failed to generate cost structure: {e}")
    
    # ==================== VALIDATION METHODS ====================
    
    def _validate_channels(
        self,
        data: Dict[str, Any],
        customer_segments: Dict[str, Any]
    ) -> None:
        """Validate channels data."""
        if not data.get("channels"):
            raise ValueError("No channels generated")
        
        channels = data["channels"]
        if len(channels) < 3 or len(channels) > 6:
            raise ValueError(f"Invalid channel count: {len(channels)} (must be 3-6)")
        
        # Get valid segment IDs
        valid_segment_ids = {seg["id"] for seg in customer_segments["segments"]}
        
        for channel in channels:
            if not channel.get("id") or not channel.get("name"):
                raise ValueError("Channel missing required fields")
            if not channel.get("evidence_source"):
                raise ValueError(f"Channel {channel['id']} missing evidence source")
            
            # Validate segment references
            for seg_id in channel.get("segment_ids", []):
                if seg_id not in valid_segment_ids:
                    raise ValueError(f"Channel {channel['id']} references invalid segment {seg_id}")
        
        logger.info("✅ Channels validation passed")
