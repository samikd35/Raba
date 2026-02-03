#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Actionable Insights Service for MINT.

This module provides functionality for generating actionable insights from completed reports
using a hybrid RAG approach that LEVERAGES the existing chat infrastructure.

MIGRATED TO RESPONSES API (Dec 2025):
- Uses centralized OpenAIProvider.generate_responses() for gpt-5-mini
- Leverages reasoning.effort and text.verbosity for grounded output
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..system.core.supabase_client import get_supabase_client
from ..ai.providers import OpenAIProvider, LLMConfig
from ..services.ai.embedding_service import get_embedding_service
from ..services.storage.chunk_storage_service import get_chunk_storage_service
from ..report.report_models import ReportChunk, ReportChunkWithEmbedding
from ..system.core.azure_semaphore import azure_openai_semaphore
# Import ReportChatService dynamically to avoid circular imports
from .models import InsightGenerationResult

# Import AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

@dataclass
class UserContext:
    """User context for actionable insights generation."""
    user_id: str
    geography: Optional[str] = None
    user_type: Optional[str] = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InsightGenerationContext:
    """Context information for insight generation."""
    user_id: str
    report_id: str
    industry: Optional[str] = None
    geography: Optional[str] = None
    background: Optional[str] = None
    product_type: Optional[str] = None
    tenant_id: Optional[str] = None  # For AI usage monitoring
    project_id: Optional[str] = None  # For AI usage monitoring


class ActionableInsight(BaseModel):
    """Model for a single actionable insight."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    insight_type: str = Field(..., description="Type of insight: market_entry, product_development, risk_mitigation, competitive_advantage")
    title: str = Field(..., description="Brief title for the insight")
    content: Union[str, Dict[str, Any]] = Field(..., description="Detailed actionable content - can be string or structured sections")
    supporting_chunks: List[str] = Field(default_factory=list, description="Report chunks supporting this insight")
    confidence_score: float = Field(default=0.8, description="Confidence score for the insight")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User context used for generation")
    generation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about generation process")


class InsightGenerationResult(BaseModel):
    """Result of insight generation process."""
    success: bool
    insights: List[ActionableInsight] = Field(default_factory=list)
    total_insights: int = 0
    generation_time_seconds: float = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionableInsightsService:
    """
    Service for generating actionable insights from completed reports
    using the existing RAG infrastructure.
    """
    
    def __init__(self):
        """Initialize the actionable insights service."""
        self.supabase = get_supabase_client(use_service_role=True)
    
    async def generate_insights(self, report_id: str, user_context: InsightGenerationContext) -> InsightGenerationResult:
        """
        Generate actionable insights for a completed report.
        
        Args:
            report_id: UUID of the report to generate insights for
            user_context: User context for personalized insights
            
        Returns:
            InsightGenerationResult with generated insights
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting insight generation for report {report_id}")
            
            # 1. Validate report exists and user has access
            await self._validate_report_access(report_id, user_context.user_id)
            
            # 2. Always generate new insights (old insights will be deleted in _store_insights)
            logger.info(f"Generating new insights for report {report_id}")
            
            # 3. Update status to generating
            await self._update_insight_status(report_id, "generating")
            
            # 4. Verify report has embeddings (required for RAG)
            await self._ensure_report_embeddings(report_id)
            
            # 5. Generate comprehensive insights using structured prompt template
            insights = await self._generate_comprehensive_insights(report_id, user_context)
            
            # 6. Store insights in database
            await self._store_insights(report_id, insights, user_context)
            
            # 7. Update status to completed
            await self._update_insight_status(report_id, "completed")
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Successfully generated {len(insights)} insights for report {report_id} in {generation_time:.2f}s")
            
            return InsightGenerationResult(
                success=True,
                insights=insights,
                total_insights=len(insights),
                generation_time_seconds=generation_time,
                metadata={"source": "generated"}
            )
            
        except Exception as e:
            logger.error(f"Failed to generate insights for report {report_id}: {str(e)}")
            await self._update_insight_status(report_id, "failed")
            
            return InsightGenerationResult(
                success=False,
                error_message=str(e),
                generation_time_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _validate_report_access(self, report_id: str, user_id: str) -> None:
        """Validate that the report exists and user has access."""
        try:
            logger.info(f"Validating access for report {report_id} and user {user_id}")
            
            # Try documents table first (new approach)
            result = self.supabase.client.table("documents").select("id, created_by, source_type").eq("id", report_id).execute()
            
            if result.data:
                report = result.data[0]
                logger.info(f"Found report in documents table with source_type: {report.get('source_type')}")
                
                # Check if it's a PV report or any report type
                if report.get("created_by") != user_id:
                    raise ValueError(f"User {user_id} does not have access to report {report_id}")
                
                logger.info(f"Access validation successful for report {report_id}")
                return
            
            # Fallback to mint_reports table (old approach)
            logger.info(f"Report not found in documents table, trying mint_reports table")
            result = self.supabase.client.table("mint_reports").select("id, user_id").eq("id", report_id).execute()
            
            if not result.data:
                raise ValueError(f"Report {report_id} not found in any table")
            
            report = result.data[0]
            if report.get("user_id") != user_id:
                raise ValueError(f"User {user_id} does not have access to report {report_id}")
                
            logger.info(f"Access validation successful via mint_reports table")
                
        except Exception as e:
            logger.error(f"Report access validation failed: {str(e)}")
            raise
    
    async def _get_existing_insights(self, report_id: str, user_id: str) -> List[ActionableInsight]:
        """Check if insights already exist for this report and belong to the user."""
        try:
            logger.info(f"Checking for existing insights for report {report_id} and user {user_id}")
            
            # Try documents table approach first
            try:
                result = self.supabase.client.table("documents").select("*")\
                    .eq("source_document_id", report_id)\
                    .eq("source_type", "actionable_insights")\
                    .eq("created_by", user_id)\
                    .execute()
                
                logger.info(f"Documents table query successful, found {len(result.data) if result.data else 0} insights")
                
                if result.data:
                    insights = []
                    for row in result.data:
                        try:
                            # Parse content safely
                            content = row.get("content", "")
                            if isinstance(content, str) and content:
                                try:
                                    import json
                                    content = json.loads(content)
                                    logger.debug(f"Successfully parsed JSON content for insight {row.get('id')}")
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"Failed to parse JSON content for insight {row.get('id')}: {e}")
                                    pass
                            
                            # Extract metadata safely
                            metadata = row.get("metadata", {}) or {}
                            
                            # Debug: Log the supporting_chunks data
                            supporting_chunks_raw = metadata.get("supporting_chunks", [])
                            logger.info(f"Raw supporting_chunks type: {type(supporting_chunks_raw)}")
                            logger.info(f"Raw supporting_chunks content: {supporting_chunks_raw[:2] if supporting_chunks_raw else 'empty'}")
                            
                            # Ensure supporting_chunks is a list of strings
                            supporting_chunks = []
                            if isinstance(supporting_chunks_raw, list):
                                for chunk in supporting_chunks_raw:
                                    if isinstance(chunk, str):
                                        supporting_chunks.append(chunk)
                                    else:
                                        # Convert non-string items to strings
                                        supporting_chunks.append(str(chunk))
                            else:
                                logger.warning(f"supporting_chunks is not a list: {type(supporting_chunks_raw)}")
                                supporting_chunks = []
                            
                            logger.info(f"Processed supporting_chunks: {len(supporting_chunks)} items")
                            
                            # Create insight object
                            insight = ActionableInsight(
                                id=row.get("id", "unknown"),
                                insight_type=metadata.get("insight_type", "comprehensive_actionable_insights"),
                                title=row.get("title", "Untitled Insight"),
                                content=content if content else "No content available",
                                supporting_chunks=supporting_chunks,
                                confidence_score=float(metadata.get("confidence_score", 0.8)),
                                user_context=metadata.get("user_context", {}),
                                generation_metadata=metadata.get("generation_metadata", {})
                            )
                            insights.append(insight)
                            logger.debug(f"Successfully created insight object for {insight.id}")
                            
                        except Exception as row_error:
                            logger.error(f"Error processing insight row {row.get('id', 'unknown')}: {str(row_error)}")
                            continue
                    
                    logger.info(f"Successfully retrieved {len(insights)} insights from documents table")
                    return insights
                    
            except Exception as doc_error:
                logger.warning(f"Documents table query failed: {str(doc_error)}")
                logger.info("Falling back to report_insights table")
            
            # Fallback to report_insights table
            try:
                result = self.supabase.client.table("report_insights").select("*")\
                    .eq("report_id", report_id)\
                    .eq("user_id", user_id)\
                    .execute()
                
                logger.info(f"Report_insights table query successful, found {len(result.data) if result.data else 0} insights")
                
                insights = []
                for row in result.data:
                    insight = ActionableInsight(
                        id=row["id"],
                        insight_type=row["insight_type"],
                        title=row["title"],
                        content=row["content"],
                        supporting_chunks=row.get("supporting_chunks", []),
                        confidence_score=float(row.get("confidence_score", 0.8)),
                        user_context=row.get("user_context", {}),
                        generation_metadata=row.get("generation_metadata", {})
                    )
                    insights.append(insight)
                
                logger.info(f"Successfully retrieved {len(insights)} insights from report_insights table")
                return insights
                
            except Exception as fallback_error:
                logger.error(f"Fallback to report_insights also failed: {str(fallback_error)}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get existing insights for report {report_id} and user {user_id}: {str(e)}")
            return []
    
    async def _get_all_report_chunks(self, report_id: str) -> List[Dict[str, Any]]:
        """Retrieve ALL chunks from a report for comprehensive analysis."""
        try:
            logger.info(f"Retrieving all chunks for report {report_id}")
            
            # Get all chunks from the chunks table using doc_id (updated schema)
            result = self.supabase.client.table("chunks") \
                .select("id, doc_id, chunk_index, content, metadata") \
                .eq("doc_id", report_id) \
                .order("chunk_index") \
                .execute()
            
            if hasattr(result, "error") and result.error:
                logger.error(f"Error retrieving all chunks: {result.error}")
                return []
            
            chunks = result.data or []
            logger.info(f"Retrieved {len(chunks)} total chunks for comprehensive analysis")
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving all chunks: {e}")
            return []
    
    async def _update_insight_status(self, report_id: str, status: str) -> None:
        """Update the insight generation status for a report in documents metadata."""
        try:
            # Get current metadata
            current_report = self.supabase.client.table("documents").select("metadata").eq("id", report_id).execute()
            if current_report.data:
                current_metadata = current_report.data[0].get("metadata", {}) or {}
                
                # Update insights status in metadata
                insights_metadata = current_metadata.get("actionable_insights", {})
                insights_metadata["status"] = status
                if status == "completed":
                    insights_metadata["completed_at"] = datetime.now().isoformat()
                elif status == "generating":
                    insights_metadata["started_at"] = datetime.now().isoformat()
                
                current_metadata["actionable_insights"] = insights_metadata
                
                # Update the document
                self.supabase.client.table("documents").update({
                    "metadata": current_metadata
                }).eq("id", report_id).execute()
                
                logger.debug(f"Updated insight status for report {report_id} to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update insight status: {str(e)}")
    
    async def _ensure_report_embeddings(self, report_id: str) -> None:
        """Ensure the report has embeddings for RAG processing."""
        try:
            # Check if embeddings exist in chunks table
            result = self.supabase.client.table("chunks").select("id").eq("doc_id", report_id).limit(1).execute()
            
            if not result.data:
                logger.warning(f"No embeddings found for report {report_id}, attempting to generate embeddings now")
                
                # Attempt on-demand chunking + embedding from stored PV report content
                try:
                    # Try to load PV report content from documents table
                    doc_result = self.supabase.client.table("documents").select("content, source_type").eq("id", report_id).maybe_single().execute()
                    report_content = None
                    content_json = None
                    if doc_result.data:
                        raw_content = doc_result.data.get("content")
                        # Content may be a JSON string or a dict; normalize
                        if isinstance(raw_content, dict):
                            content_json = raw_content
                        elif isinstance(raw_content, str):
                            try:
                                content_json = json.loads(raw_content)
                            except Exception:
                                report_content = raw_content  # Treat as plain text
                        
                    if content_json is None and report_content is None:
                        logger.error("PV report content not found or empty; cannot generate embeddings on-demand")
                        raise ValueError("Report content unavailable for embedding generation")
                    
                    # Import chunking service lazily to avoid circulars
                    from ..report.report_chunking_service import ReportChunkingService
                    chunking_service = ReportChunkingService()
                    
                    vector_success = False
                    if content_json is not None and isinstance(content_json, dict):
                        vector_success = await chunking_service.process_report_from_json(
                            report_id=report_id,
                            report_json=content_json
                        )
                    else:
                        vector_success = await chunking_service.process_report(
                            report_id=report_id,
                            report_content=report_content or ""
                        )
                    
                    if not vector_success:
                        raise ValueError("On-demand embedding generation failed")
                    
                    # Re-check embeddings existence
                    recheck = self.supabase.client.table("chunks").select("id").eq("doc_id", report_id).limit(1).execute()
                    if not recheck.data:
                        raise ValueError("Embeddings still missing after generation")
                    
                    logger.info(f"Successfully generated embeddings for report {report_id} on-demand")
                except Exception as gen_err:
                    logger.error(f"On-demand embedding generation failed for report {report_id}: {gen_err}")
                    raise ValueError(f"Report {report_id} does not have embeddings and generation failed: {gen_err}")
            
            logger.debug(f"Report {report_id} has embeddings available")
            
        except Exception as e:
            logger.error(f"Failed to verify report embeddings: {str(e)}")
            raise
    
    async def _generate_comprehensive_insights(
        self, 
        report_id: str, 
        user_context: UserContext
    ) -> List[ActionableInsight]:
        """Generate comprehensive actionable insights using the structured prompt template."""
        try:
            logger.info(f"Generating comprehensive actionable insights for report {report_id}")
            
            # Initialize the chat service (dynamic import to avoid circular imports)
            from ..chat.service import ReportChatService
            chat_service = ReportChatService()
            
            # Get ALL chunks from the report for comprehensive insights
            all_chunks = await self._get_all_report_chunks(report_id)
            logger.info(f"Using {len(all_chunks)} chunks for comprehensive insights generation")
            
            # Use the proper detailed prompt template
            prompt_template = self._create_actionable_insights_prompt(user_context)
            
            # Create monitoring context
            monitoring_context = AIUsageContext(
                user_id=user_context.user_id,
                tenant_id=user_context.tenant_id if hasattr(user_context, 'tenant_id') else None,
                project_id=user_context.project_id if hasattr(user_context, 'project_id') else None,
                feature_id="actionable_insights_generation",
                workflow_name="actionable_insights_workflow",
                step_name="generate_comprehensive_insights",
                environment="prod"
            )
            
            started_at = datetime.utcnow()
            
            # Use Azure OpenAI semaphore for proper concurrency control
            async with azure_openai_semaphore:
                # Create direct prompt with actual chunk content (like successful test)
                chunk_content = "\n\n".join([
                    f"[Section {i}] {chunk.get('content', '')[:2000]}..." 
                    if len(chunk.get('content', '')) > 2000 
                    else f"[Section {i}] {chunk.get('content', '')}"
                    for i, chunk in enumerate(all_chunks[:10])  # Use first 10 chunks like test
                ])
                
                direct_prompt = f"{prompt_template}\n\nREPORT CONTENT TO ANALYZE:\n{chunk_content}"
                
                # Use centralized OpenAIProvider with Responses API for gpt-5-mini
                from ..ai.config import get_client_config
                from ..ai.models import ModelUseCase
                
                # Get configuration from centralized config
                provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
                
                if not client_config.get("api_key") or not client_config.get("base_url"):
                    raise ValueError("Azure OpenAI configuration missing")
                
                # Initialize centralized OpenAIProvider for Responses API
                from ..ai.models import ModelProvider
                provider_config = LLMConfig(
                    provider_type="llm",
                    provider_name="openai",
                    api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
                    model_name=model_name,
                    temperature=0.7,
                    max_tokens=16000,
                    api_key=client_config.get("api_key"),
                    azure_endpoint=client_config.get("azure_endpoint"),
                    api_version=client_config.get("api_version"),
                    base_url=client_config.get("base_url")
                )
                llm_provider = OpenAIProvider(provider_config)
                
                try:
                    # Generate insights using centralized Responses API
                    system_content = """You are an expert business analyst and venture builder. 
You MUST respond with valid JSON only. Do not include any text before or after the JSON.
Start your response with { and end with }."""
                    
                    messages = [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": direct_prompt}
                    ]
                    
                    logger.info(f"Calling LLM with model: {model_name} using centralized Responses API")
                    
                    # Retry logic for transient failures
                    max_retries = 3
                    retry_delay = 2.0
                    last_error = None
                    llm_response = None
                    
                    for attempt in range(max_retries):
                        try:
                            if attempt > 0:
                                logger.info(f"Retry attempt {attempt + 1}/{max_retries} for insight generation...")
                                await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))
                            
                            # Use centralized Responses API
                            llm_response = await llm_provider.generate_responses(messages)
                            break  # Success
                            
                        except Exception as retry_error:
                            last_error = retry_error
                            error_msg = str(retry_error).lower()
                            is_transient = any(x in error_msg for x in ["timeout", "connection", "reset", "disconnected"])
                            
                            if is_transient and attempt < max_retries - 1:
                                logger.warning(f"Transient error on attempt {attempt + 1}: {retry_error}")
                                continue
                            else:
                                raise retry_error
                    
                    if llm_response is None:
                        raise last_error or ValueError("No response from LLM after retries")
                    
                    finished_at = datetime.utcnow()
                    
                    # Record AI usage (fire-and-forget)
                    monitoring = get_monitoring_service()
                    usage = llm_response.usage
                    asyncio.create_task(
                        monitoring.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai",
                            model_name=llm_response.model or model_name,
                            operation_type="responses_api",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="success",
                            prompt_tokens=usage.get('prompt_tokens') if usage else None,
                            completion_tokens=usage.get('completion_tokens') if usage else None,
                            total_tokens=usage.get('total_tokens') if usage else None
                        )
                    )
                    
                    # Get content from LLMResponse object
                    insights_content = llm_response.content
                    logger.info(f"Response content length: {len(insights_content) if insights_content else 0}")
                    
                    if not insights_content:
                        logger.error(f"Empty content from model")
                        raise ValueError("Model returned empty content")
                    
                except Exception as ai_error:
                    finished_at = datetime.utcnow()
                    
                    # Record error (fire-and-forget)
                    monitoring = get_monitoring_service()
                    asyncio.create_task(
                        monitoring.record_ai_usage(
                            context=monitoring_context,
                            provider="azure_openai",
                            model_name=model_name,
                            operation_type="responses_api",
                            started_at=started_at,
                            finished_at=finished_at,
                            status="error",
                            error_type=type(ai_error).__name__
                        )
                    )
                    raise
                
                # Parse the JSON response directly with robust extraction
                try:
                    import json
                    import re
                    
                    # Try direct parsing first
                    try:
                        structured_insights = json.loads(insights_content)
                    except json.JSONDecodeError:
                        # Try to extract JSON from response (in case there's text before/after)
                        logger.warning("Direct JSON parse failed, attempting extraction...")
                        
                        # Find JSON object in response
                        json_match = re.search(r'\{[\s\S]*\}', insights_content)
                        if json_match:
                            extracted_json = json_match.group(0)
                            structured_insights = json.loads(extracted_json)
                            logger.info("Successfully extracted and parsed JSON from response")
                        else:
                            raise ValueError("No JSON object found in response")
                    
                    logger.info(f"Successfully parsed JSON insights: {list(structured_insights.keys())}")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response (first 500 chars): {insights_content[:500] if insights_content else 'EMPTY'}")
                    logger.error(f"Raw response (last 500 chars): {insights_content[-500:] if insights_content and len(insights_content) > 500 else insights_content}")
                    raise ValueError(f"Invalid JSON response from AI: {e}")
                
                # Create response structure
                response = {
                    'success': True,
                    'response': structured_insights,  # Direct JSON structure
                    'chunks': [{'content': self._clean_content_for_frontend(chunk.get('content', ''))} for chunk in all_chunks[:5]]
                }
            
            if not response or not response.get('success') or not response.get('response'):
                logger.error(f"Failed to generate actionable insights - no response or failed")
                return []
            
            # Extract supporting chunks from the response
            supporting_chunks = []
            if response.get('chunks'):
                supporting_chunks = [
                    self._clean_content_for_frontend(chunk.get('content', '')[:500] + '...' if len(chunk.get('content', '')) > 500 
                    else chunk.get('content', ''))
                    for chunk in response.get('chunks', [])[:5]  # Limit to top 5 sources
                ]
            
            # Parse the structured response into individual insights
            insights = self._parse_structured_insights_response(
                response.get('response'), 
                supporting_chunks, 
                user_context
            )
            
            logger.info(f"Successfully generated {len(insights)} actionable insights for report {report_id}")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating actionable insights for report {report_id}: {str(e)}")
            return []
    
    def _create_actionable_insights_prompt(self, user_context: InsightGenerationContext) -> str:
        """Create the comprehensive actionable insights prompt template for JSON generation."""
        
        industry = user_context.industry or "the target industry"
        geography = user_context.geography or "the target geography" 
        product_type = user_context.product_type or "digital solutions"
        background = user_context.background or "entrepreneur"
        
        prompt = f"""
You are an Actionable Insight Agent: a cloned Venture Builder that will scan through the provided report and analyze missing pieces, areas where more information is needed, and then offer further recommendations to the user as they further their market research.

Based on the comprehensive market research report provided, generate actionable insights for entrepreneurs looking to build solutions in {industry} within {geography}. The target audience is {background}s developing {product_type}.

You must respond with a valid JSON object with the following exact structure:

{{
  "important_questions_industry_geography": {{
    "desirability_analysis": [
      "1. The emerging pain points such as [specific pain point #1], [specific pain point #2], and [specific pain point #3] indicate the heightened need of better and alternative solutions to address the problem.",
      "2. [Another one-liner insight about market desirability]"
    ],
    "recommended_research_areas": [
      "1. Individuals such as [specific individuals], or group of individuals such as [specific group of individuals], might be either contributing to, hence, benefiting from the problem by [specific action]. They might, therefore, be of a significant concern as far as the implementation of any solution goes. It is, hence, recommended that further research is conducted to understand their needs, influence, and implications on any solution."
    ],
    "key_stakeholders_institutions": [
      "1. In solving this problem in [specific country or region], regulators such as [specific regulator/s], and institutions such as [specific institutions] are critical stakeholders to engage early on as the former holds custody of regulations and licensing requirements, while the later may be an important partner in product development for solutions in this space.",
      "2. [Another stakeholder insight]"
    ]
  }},
  "emerging_key_insights": {{
    "customer_segments": "Detailed analysis of customer segments experiencing this problem the most, including specific demographics (age ranges, income levels, education), geographic distribution, behavioral patterns, pain points, and market size. Include specific data points and statistics from the report about who is most affected and why.",
    "existing_solutions": "Comprehensive analysis of existing alternative solutions in the market, their market share, pricing models, key features, limitations, and areas of inefficiency. Include specific companies, products, and their competitive positioning based on report findings.",
    "distribution_channels": "In-depth analysis of current distribution channels, their effectiveness, cost structures, reach limitations, and emerging alternatives. Include specific data about channel performance, market penetration, and opportunities for disruption based on report insights.",
    "regulations_policies": "Detailed examination of current regulations, policies, and compliance requirements that could impact solution development. Include specific regulatory bodies, licensing requirements, compliance costs, and timeline implications mentioned in the report.",
    "government_policies": "Analysis of government initiatives, draft policies, funding programs, and strategic priorities that could support or hinder solution development. Include specific policy names, implementation timelines, and potential impact on market dynamics.",
    "barriers_consumption": "Comprehensive analysis of barriers preventing widespread adoption, including affordability constraints (specific price points), accessibility issues (geographic, infrastructure), awareness gaps, availability limitations, complexity factors, cultural considerations, environmental concerns, and technological barriers. Include specific data points and examples from the report."
  }},
  "leverage_points": [
    "1. [Action/Subject] should [specific action] to [outcome/benefit]. [200-400 word detailed paragraph with founder-led, actionable recommendations grounded in report facts]",
    "2. [Another leverage point paragraph]",
    "3. [Another leverage point paragraph]",
    "4. [Another leverage point paragraph]"
  ],
  "key_questions_for_founders": [
    "1. [Generate specific question based on actual market data/trends from report]",
    "2. [Generate specific question based on actual stakeholders/companies mentioned in report]", 
    "3. [Generate specific question based on actual barriers/challenges identified in report]",
    "4. [Generate specific question based on actual customer segments/behaviors from report]",
    "5. [Generate specific question based on actual competitive landscape from report]",
    "6. [Generate specific question based on actual regulatory/policy findings from report]",
    "7. [Generate specific question based on actual technology/infrastructure insights from report]",
    "8. [Generate specific question based on actual business model/revenue opportunities from report]"
  ]
}}

MANDATORY REQUIREMENTS:
- Generate 2-3 desirability analysis points (50-70 words each)
- Generate 1-2 recommended research areas (60-80 words each)  
- Generate 2-3 key stakeholders points (50-70 words each)
- Generate 4-7 leverage points (200-400 words each)
- ALL LISTS MUST START WITH NUMBERS: "1. ", "2. ", "3. ", etc.
- Key Questions for Founders MUST be completely dynamic and based on actual report content
- Replace ALL placeholders [Generate specific question based on...] with REAL questions derived from the report
- Each question must reference specific companies, data points, stakeholders, or findings mentioned in the report
- Questions should help founders take next steps based on what they learned from THIS specific report
- Each recommendation must directly address the specific problem entrepreneurs are trying to solve
- Each recommendation must be grounded in facts from the report
- AVOID NON-FOUNDER ACTIONS (government reforms, central bank actions, telecom infrastructure, NGO campaigns)
- Focus on founder-led actions: pivoting business models, partnering with specific entities mentioned in the report, targeting underserved markets, using alternative distribution channels, creating tech workarounds, building MVPs
- Every point must be founder-led, feasible, and motivated by data from the report

CRITICAL: For key_questions_for_founders, you MUST generate actual questions based on the report content. Do NOT use the placeholder text. Extract specific findings, companies, stakeholders, market data, and challenges from the report and create targeted questions that help founders validate their approach.

Please analyze the provided market research report thoroughly and generate insights following this exact JSON structure.
"""
        
        return prompt
    
    def _clean_content_for_frontend(self, content: str) -> str:
        """Clean content to remove HTML elements that cause frontend rendering issues."""
        if not content or not isinstance(content, str):
            return ""
        
        import re
        
        # Remove HTML span elements with chunk IDs (main cause of the error)
        cleaned = re.sub(r'<span[^>]*class="report-chunk"[^>]*>', '', content)
        cleaned = re.sub(r'</span>', '', cleaned)
        
        # Remove other HTML tags that might interfere with markdown
        cleaned = re.sub(r'<[^>]*>', '', cleaned)
        
        # Clean up extra whitespace and normalize line breaks
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _parse_structured_insights_response(
        self, 
        response_content: Union[str, Dict[str, Any]], 
        supporting_chunks: List[str], 
        user_context: InsightGenerationContext
    ) -> List[ActionableInsight]:
        """Parse the structured insights response into individual ActionableInsight objects."""
        
        insights = []
        
        try:
            # Handle direct JSON structure (new approach)
            if isinstance(response_content, dict):
                structured_content = response_content
                logger.info(f"Using direct JSON structure with keys: {list(structured_content.keys())}")
            else:
                # Fallback for string content (legacy)
                logger.warning("Received string content, attempting JSON parse")
                try:
                    import json
                    structured_content = json.loads(response_content)
                except json.JSONDecodeError:
                    logger.error("Failed to parse string as JSON, falling back to markdown parsing")
                    structured_content = self._parse_insights_into_sections(response_content)
            
            # Validate required structure
            required_keys = [
                "important_questions_industry_geography",
                "emerging_key_insights", 
                "leverage_points",
                "key_questions_for_founders"
            ]
            
            missing_keys = [key for key in required_keys if key not in structured_content]
            if missing_keys:
                logger.warning(f"Missing required keys in JSON structure: {missing_keys}")
            
            # Create a single comprehensive insight with structured content
            comprehensive_insight = ActionableInsight(
                id=str(uuid.uuid4()),
                insight_type="comprehensive_actionable_insights",
                title="Comprehensive Actionable Insights for Market Entry",
                content=structured_content,  # Direct JSON structure
                supporting_chunks=supporting_chunks,
                confidence_score=0.90,  # High confidence for comprehensive analysis
                user_context={
                    "user_id": user_context.user_id,
                    "report_id": user_context.report_id,
                    "generation_source": "report_content_analysis"
                },
                generation_metadata={
                    "generated_at": datetime.utcnow().isoformat(),
                    "model_used": "gpt-5-mini",
                    "prompt_template": "actionable_insights_json_venture_builder",
                    "sources_count": len(supporting_chunks),
                    "structured_format": True,
                    "json_direct": True
                }
            )
            
            insights.append(comprehensive_insight)
            
            logger.info(f"Parsed structured insights response into {len(insights)} insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error parsing structured insights response: {str(e)}")
            return []
    
    def _parse_insights_into_sections(self, content: str) -> dict:
        """Parse the insights content into structured sections similar to the main report."""
        
        sections = {}
        
        # First, try to split by section headers using regex to handle content without line breaks
        import re
        
        # Split content by ## headers using a more robust approach
        section_splits = re.split(r'(## [^#]+?)(?=## |$)', content)
        
        # Process the splits to extract sections
        current_section = None
        for i, part in enumerate(section_splits):
            part = part.strip()
            if not part:
                continue
                
            if part.startswith('## '):
                # This is a section header
                section_title = part[3:].strip()  # Remove "## "
                current_section = self._normalize_section_key(section_title)
                logger.info(f"Found section header: '{section_title}' -> '{current_section}'")
                
                # Look for content in the next part
                if i + 1 < len(section_splits):
                    section_content = section_splits[i + 1].strip()
                    if section_content and not section_content.startswith('## '):
                        sections[current_section] = section_content
                        logger.info(f"Parsed section '{current_section}': {len(section_content)} characters")
        
        # If the split approach didn't work, try a simpler regex approach
        if not sections:
            logger.info("Split approach failed, trying direct regex matches")
            # Find all section headers and their positions - match just the header part
            header_pattern = r'## ([^#]*?)(?=### |## |$)'
            matches = list(re.finditer(header_pattern, content))
            
            for i, match in enumerate(matches):
                # Extract just the title part (before any content)
                full_match = match.group(1).strip()
                
                # The title is usually the first part before any detailed content
                # Look for common patterns like numbered lists, bullet points, etc.
                title_parts = full_match.split(' 1.', 1)  # Split on first numbered item
                if len(title_parts) > 1:
                    section_title = title_parts[0].strip()
                    section_content = '1.' + title_parts[1].strip()
                else:
                    # Try other common separators
                    title_parts = full_match.split(' ###', 1)
                    if len(title_parts) > 1:
                        section_title = title_parts[0].strip()
                        section_content = '###' + title_parts[1].strip()
                    else:
                        # If no clear separator, take first 100 chars as title, rest as content
                        if len(full_match) > 100:
                            section_title = full_match[:100].strip()
                            section_content = full_match[100:].strip()
                        else:
                            section_title = full_match
                            section_content = ""
                
                current_section = self._normalize_section_key(section_title)
                
                # Also get content until the next section
                start_pos = match.end()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                additional_content = content[start_pos:end_pos].strip()
                
                # Combine the content from within the match and after it
                full_section_content = section_content
                if additional_content and not additional_content.startswith('##'):
                    full_section_content += " " + additional_content
                
                if full_section_content:
                    sections[current_section] = full_section_content.strip()
                    logger.info(f"Regex parsed section '{current_section}': {len(full_section_content)} characters")
        
        # Fallback: try line-by-line parsing if regex didn't work
        if not sections:
            logger.info("Regex parsing failed, trying line-by-line parsing")
            current_section = None
            current_content = []
            
            lines = content.split('\n')
            
            for line in lines:
                stripped_line = line.strip()
                
                # Check for main section headers (## Header)
                if stripped_line.startswith('## '):
                    # Save previous section if exists
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    
                    # Start new section
                    section_title = stripped_line[3:].strip()  # Remove "## "
                    current_section = self._normalize_section_key(section_title)
                    current_content = []
                    
                # Add all other content to current section
                else:
                    current_content.append(line)  # Keep original formatting including indentation
            
            # Save the last section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
        
        # Debug logging
        logger.info(f"Final parsed sections: {len(sections)} sections: {list(sections.keys())}")
        for section_key, section_content in sections.items():
            logger.info(f"Section '{section_key}': {len(section_content)} characters")
        
        # If parsing still failed, return the original content as a single section
        if not sections:
            logger.warning("All parsing methods failed, returning content as single section")
            sections['comprehensive_insights'] = content
        
        return sections
    
    def _normalize_section_key(self, title: str) -> str:
        """Normalize section titles to consistent keys."""
        
        title_lower = title.lower().strip()
        
        # Match the actual sections from the prompt template
        if 'important questions' in title_lower and ('industry' in title_lower or 'geography' in title_lower):
            return 'important_questions_industry_geography'
        elif 'important questions' in title_lower and 'founders' in title_lower:
            return 'key_questions_for_founders'
        elif 'desirability' in title_lower:
            return 'desirability_analysis'
        elif 'recommended areas' in title_lower:
            return 'recommended_research_areas'
        elif 'stakeholders' in title_lower and 'institutions' in title_lower:
            return 'key_stakeholders_institutions'
        elif 'emerging' in title_lower and 'insights' in title_lower:
            return 'emerging_key_insights'
        elif 'leverage points' in title_lower:
            return 'leverage_points'
        else:
            # Convert to snake_case and clean up
            normalized = title_lower.replace(' ', '_').replace('-', '_').replace('&', 'and')
            # Remove special characters and multiple underscores
            import re
            normalized = re.sub(r'[^\w_]', '', normalized)
            normalized = re.sub(r'_+', '_', normalized)
            return normalized.strip('_')
    
    async def _store_insights(self, report_id: str, insights: List[ActionableInsight], user_context: InsightGenerationContext) -> None:
        """Store generated insights in the documents table."""
        try:
            # Delete any existing insights for this report to prevent duplicates
            logger.info(f"Deleting existing insights for report {report_id}")
            delete_result = self.supabase.client.table("documents").delete()\
                .eq("source_document_id", report_id)\
                .eq("source_type", "actionable_insights")\
                .execute()
            logger.info(f"Deleted {len(delete_result.data) if delete_result.data else 0} existing insights")
            
            # Get tenant_id from the parent PV report
            pv_report_result = self.supabase.client.table("documents").select("tenant_id, title")\
                .eq("id", report_id).eq("source_type", "pv_report").execute()
            
            if not pv_report_result.data:
                raise ValueError(f"Parent PV report {report_id} not found")
            
            tenant_id = pv_report_result.data[0]["tenant_id"]
            pv_report_title = pv_report_result.data[0]["title"]
            
            # Store individual insights in documents table
            for insight in insights:
                # Content should already be a dict from JSON generation
                content_to_store = insight.content
                
                # Validate that content is structured properly
                if isinstance(content_to_store, dict):
                    logger.info(f"Storing structured JSON content with keys: {list(content_to_store.keys())}")
                    # Convert to JSON string for storage in content field
                    import json
                    content_json = json.dumps(content_to_store, ensure_ascii=False, indent=2)
                else:
                    logger.warning(f"Content is not a dict, type: {type(content_to_store)}")
                    # Try to convert if it's a string
                    if isinstance(content_to_store, str):
                        try:
                            import json
                            parsed_content = json.loads(content_to_store)
                            content_json = json.dumps(parsed_content, ensure_ascii=False, indent=2)
                            logger.info("Successfully converted string content to JSON")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(f"Failed to parse content as JSON: {e}")
                            # Keep as string
                            content_json = str(content_to_store)
                    else:
                        content_json = str(content_to_store)
            
                # Prepare document data for documents table
                document_data = {
                    "id": insight.id,
                    "tenant_id": tenant_id,
                    "project_id": None,  # Will be set when VPM project is created
                    "source_type": "actionable_insights",
                    "source_document_id": report_id,  # Links to parent PV report
                    "document_type": "actionable_insights",
                    "title": f"Actionable Insights: {pv_report_title}",
                    "content": content_json,
                    "storage_path": None,
                    "sha256": None,
                    "created_by": user_context.user_id,
                    "metadata": {
                        "insight_type": insight.insight_type,
                        "supporting_chunks": insight.supporting_chunks,
                        "confidence_score": insight.confidence_score,
                        "user_context": insight.user_context,
                        "generation_metadata": insight.generation_metadata,
                        "parent_report_id": report_id,
                        "generated_at": datetime.now().isoformat(),
                        "version": 1
                    }
                }
                
                logger.info(f"Storing insight in documents table with ID: {insight.id}")
                if isinstance(content_to_store, dict):
                    logger.info(f"Structured content sections: {list(content_to_store.keys())}")
                
                self.supabase.client.table("documents").insert(document_data).execute()
            
            # Update parent PV report with insights summary in metadata
            insights_summary = {
                "total_insights": len(insights),
                "insight_types": [insight.insight_type for insight in insights],
                "generated_at": datetime.now().isoformat(),
                "version": 1,
                "insight_ids": [insight.id for insight in insights]
            }
            
            # Get current metadata and update it
            current_report = self.supabase.client.table("documents").select("metadata").eq("id", report_id).execute()
            if current_report.data:
                current_metadata = current_report.data[0].get("metadata", {}) or {}
                current_metadata["actionable_insights"] = insights_summary
                
                # Update the parent PV report's metadata
                self.supabase.client.table("documents").update({
                    "metadata": current_metadata
                }).eq("id", report_id).execute()
            
            logger.info(f"Stored {len(insights)} insights in documents table for report {report_id}")
            
            # NEW: Automatically chunk and embed insights for vector search
            await self._chunk_and_embed_insights(insights, report_id, user_context)
            
        except Exception as e:
            logger.error(f"Failed to store insights: {str(e)}")
            raise
    
    async def _chunk_and_embed_insights(self, insights: List[ActionableInsight], report_id: str, user_context: InsightGenerationContext) -> None:
        """Chunk and embed actionable insights for vector search."""
        try:
            logger.info(f"Starting chunking and embedding for {len(insights)} insights")
            
            embedding_service = get_embedding_service()
            chunk_storage_service = get_chunk_storage_service()
            
            for insight in insights:
                try:
                    # Chunk the insight content
                    chunks = self._chunk_insight_content(insight)
                    logger.info(f"Created {len(chunks)} chunks for insight {insight.id}")
                    
                    if not chunks:
                        logger.warning(f"No chunks created for insight {insight.id}")
                        continue
                    
                    # Generate embeddings for chunks
                    chunk_texts = [chunk.content for chunk in chunks]
                    embeddings = await embedding_service.generate_embeddings(chunk_texts)
                    
                    # Create chunks with embeddings
                    chunks_with_embeddings = []
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        if embedding is not None:
                            chunk_with_embedding = ReportChunkWithEmbedding(
                                chunk_index=chunk.chunk_index,
                                content=chunk.content,
                                metadata={
                                    **chunk.metadata,
                                    "insight_id": insight.id,
                                    "insight_type": insight.insight_type,
                                    "parent_report_id": report_id,
                                    "source_type": "actionable_insights",
                                    "confidence_score": insight.confidence_score
                                },
                                embedding=embedding
                            )
                            chunks_with_embeddings.append(chunk_with_embedding)
                        else:
                            logger.warning(f"Failed to generate embedding for chunk {i} of insight {insight.id}")
                    
                    # Store chunks in the chunks table
                    if chunks_with_embeddings:
                        success = await chunk_storage_service.store_chunks(insight.id, chunks_with_embeddings)
                        if success:
                            logger.info(f"Successfully stored {len(chunks_with_embeddings)} chunks for insight {insight.id}")
                        else:
                            logger.error(f"Failed to store chunks for insight {insight.id}")
                    
                except Exception as insight_error:
                    logger.error(f"Error processing insight {insight.id}: {str(insight_error)}")
                    continue
            
            logger.info(f"Completed chunking and embedding for all insights")
            
        except Exception as e:
            logger.error(f"Error in chunking and embedding insights: {str(e)}")
            # Don't raise - chunking failure shouldn't break insight generation
    
    def _chunk_insight_content(self, insight: ActionableInsight, chunk_size: int = 800, chunk_overlap: int = 100) -> List[ReportChunk]:
        """Chunk an actionable insight into smaller pieces for vector search."""
        try:
            # Extract text content from insight
            content_text = self._extract_text_from_insight(insight)
            
            if not content_text or len(content_text.strip()) < 50:
                logger.warning(f"Insight {insight.id} has insufficient content for chunking")
                return []
            
            logger.info(f"Chunking insight {insight.id} with {len(content_text)} characters")
            
            # Clean up the content
            content_text = re.sub(r'[ \t]+', ' ', content_text)
            content_text = re.sub(r'\n{3,}', '\n\n', content_text)
            
            # Split into logical sections (by headers, bullet points, etc.)
            sections = self._split_insight_into_sections(content_text)
            
            chunks = []
            current_chunk = ""
            chunk_index = 0
            section_context = insight.title  # Use insight title as context
            
            for section in sections:
                # Check if this section is a header
                is_header = re.match(r'^(#{1,6}\s+|[A-Z][^.!?]*:|\d+\.\s+[A-Z])', section.strip())
                if is_header:
                    section_context = section.strip()[:100]  # Limit context length
                
                # If adding this section would exceed chunk size, create new chunk
                if len(current_chunk) + len(section) > chunk_size and current_chunk:
                    # Create chunk with metadata
                    chunks.append(
                        ReportChunk(
                            chunk_index=chunk_index,
                            content=current_chunk.strip(),
                            metadata={
                                "section": section_context,
                                "position": chunk_index + 1,
                                "insight_title": insight.title,
                                "insight_type": insight.insight_type,
                                "chunk_type": "insight_content"
                            }
                        )
                    )
                    
                    # Start new chunk with overlap
                    if len(current_chunk) > chunk_overlap:
                        overlap_text = current_chunk[-chunk_overlap:]
                        # Find good break point
                        sentence_break = re.search(r'[.!?]\s+', overlap_text)
                        if sentence_break:
                            overlap_text = overlap_text[sentence_break.end():]
                        current_chunk = overlap_text + " " + section
                    else:
                        current_chunk = current_chunk + " " + section
                    
                    chunk_index += 1
                else:
                    # Add section to current chunk
                    if current_chunk:
                        current_chunk += " " + section
                    else:
                        current_chunk = section
            
            # Add final chunk
            if current_chunk.strip():
                chunks.append(
                    ReportChunk(
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        metadata={
                            "section": section_context,
                            "position": chunk_index + 1,
                            "insight_title": insight.title,
                            "insight_type": insight.insight_type,
                            "chunk_type": "insight_content"
                        }
                    )
                )
            
            logger.info(f"Created {len(chunks)} chunks for insight {insight.id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking insight {insight.id}: {str(e)}")
            return []
    
    def _extract_text_from_insight(self, insight: ActionableInsight) -> str:
        """Extract plain text from insight content (handles both string and dict formats)."""
        try:
            content = insight.content
            
            if isinstance(content, str):
                return content
            elif isinstance(content, dict):
                # Extract text from structured content
                text_parts = []
                
                # Add title
                text_parts.append(f"# {insight.title}")
                
                # Extract from common structured fields
                for key, value in content.items():
                    if isinstance(value, str) and value.strip():
                        text_parts.append(f"## {key.replace('_', ' ').title()}")
                        text_parts.append(value.strip())
                    elif isinstance(value, list):
                        text_parts.append(f"## {key.replace('_', ' ').title()}")
                        for item in value:
                            if isinstance(item, str):
                                text_parts.append(f"- {item}")
                            elif isinstance(item, dict):
                                for sub_key, sub_value in item.items():
                                    if isinstance(sub_value, str):
                                        text_parts.append(f"- {sub_key}: {sub_value}")
                
                return "\n\n".join(text_parts)
            else:
                return str(content)
                
        except Exception as e:
            logger.error(f"Error extracting text from insight: {str(e)}")
            return ""
    
    def _split_insight_into_sections(self, content: str) -> List[str]:
        """Split insight content into logical sections."""
        try:
            # Split by headers, bullet points, and paragraph breaks
            sections = []
            current_section = ""
            
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Check for headers or list items
                is_section_break = (
                    re.match(r'^#{1,6}\s+', line) or  # Markdown headers
                    re.match(r'^[A-Z][^.!?]*:$', line) or  # Title case headers ending with colon
                    re.match(r'^\d+\.\s+', line) or  # Numbered lists
                    re.match(r'^[•\-\*]\s+', line)  # Bullet points
                )
                
                if is_section_break and current_section:
                    sections.append(current_section)
                    current_section = line
                else:
                    if current_section:
                        current_section += " " + line
                    else:
                        current_section = line
            
            # Add final section
            if current_section:
                sections.append(current_section)
            
            # If no logical sections found, split by sentences
            if len(sections) <= 1 and content:
                sentences = re.split(r'[.!?]+\s+', content)
                sections = [s.strip() for s in sentences if s.strip()]
            
            return sections
            
        except Exception as e:
            logger.error(f"Error splitting content into sections: {str(e)}")
            return [content] if content else []


# Singleton instance
_actionable_insights_service = None

def get_actionable_insights_service() -> ActionableInsightsService:
    """Get the singleton ActionableInsightsService instance."""
    global _actionable_insights_service
    if _actionable_insights_service is None:
        _actionable_insights_service = ActionableInsightsService()
    return _actionable_insights_service
