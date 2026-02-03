"""
Passage Extractor Node

Node 4 in the Problem Generator agent graph.
Extracts relevant passages from scraped content and DB results using Azure OpenAI gpt-5-mini.
"""

import logging
import asyncio
import uuid
from typing import Dict, Any, List
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config, get_llm_config
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.api.ai.models import ModelProvider
from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig

from ..graph_state import ProblemGraphState

# Import monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)

# System prompt for passage extraction
PASSAGE_EXTRACTION_SYSTEM_PROMPT = """
<role>
You are an expert content analyst specializing in identifying problem statements from African market contexts.
</role>

<task>
Extract 2-4 relevant passages that describe real problems, challenges, or unmet needs matching the target filters.
</task>

<strict_matching_rules>
These rules are INVIOLABLE:
1. **INDUSTRY MATCH**: Only extract passages about the TARGET INDUSTRY
2. **GEOGRAPHY MATCH**: Only extract passages about the TARGET GEOGRAPHY
3. **REJECT NON-MATCHING**: Skip passages about other industries/countries, even if interesting
</strict_matching_rules>

<problem_indicators>
Look for these signals:
- **Scarcity**: "lack of", "shortage", "absence of", "insufficient"
- **Barriers**: "unable to", "difficulty", "challenge", "barrier", "prevents", "hinders"
- **Evidence**: Statistics, percentages, numbers quantifying the problem
- **Voices**: Quotes from affected people, experts, officials
- **Reports**: Government/NGO findings on issues
- **Gaps**: Market gaps, unmet needs, friction points
</problem_indicators>

<quality_priority>
STRONGLY PREFER passages that include:
1. **Specific statistics** (percentages, numbers, monetary values)
   - Example: "Only 35% of farmers have access to credit"
   - Example: "The market gap is estimated at $2.3 billion"

2. **Quantified impact** (number of people affected)
   - Example: "Affecting over 12 million smallholder farmers"
   - Example: "Leaving 4 out of 5 households without access"

3. **Time-bound data** (year, month, recent timeframe)
   - Example: "As of 2024", "In the last five years", "Recent studies show"

4. **Named sources** (organizations, reports, studies)
   - Example: "According to World Bank data", "AfDB reports indicate"

SCORING ADJUSTMENT:
- Passages WITH quantitative evidence: relevance_score 7-10
- Passages WITHOUT quantitative evidence: relevance_score ≤ 6
- Passages with multiple statistics: relevance_score 9-10
</quality_priority>

<extraction_criteria>
- Focus on PROBLEMS only (not solutions or success stories)
- Prioritize cause-and-effect relationships
- Each passage: 50-200 words, self-contained
- Reject: marketing content, advertisements, promotional material
- PREFER passages with quantitative data over qualitative descriptions
</extraction_criteria>

<scoring_rubric>
- **10**: Perfect match to BOTH target industry AND geography, with MULTIPLE quantified statistics
- **9**: Strong match to both targets, with at least ONE quantified statistic
- **8**: Strong match to both targets, clear problem with named source
- **7**: Matches both targets, problem described with context but no statistics
- **6**: Matches both targets but problem is vague or lacks specifics
- **4-5**: Matches only one target (industry OR geography)
- **1-3**: Weak or tangential relevance
</scoring_rubric>

<output_format>
Return JSON array with each passage containing:
- "text": Extracted passage (50-200 words)
- "relevance_score": 1-10 per rubric above
- "context": Brief problem context description
- "location": Geographic location (must match target for high scores)
- "industry": Industry/sector (must match target for high scores)
</output_format>
"""

# User prompt template
PASSAGE_EXTRACTION_USER_PROMPT = """
<target_filters>
- Industry: {target_industry}
- Geography: {target_geography}
</target_filters>

<source>
{source_info}
</source>

<content>
{content}
</content>

<extraction_rules>
1. Extract ONLY passages matching BOTH {target_industry} AND {target_geography}
2. If content doesn't mention both targets → return empty array []
3. Score 10 = matches BOTH targets with quantified evidence
4. Score 1-5 = partial match only
</extraction_rules>

<output_schema>
{{
    "passages": [
        {{
            "text": "[50-200 word passage]",
            "relevance_score": [1-10],
            "context": "[brief problem context]",
            "location": "[must match {target_geography}]",
            "industry": "[must match {target_industry}]"
        }}
    ]
}}
</output_schema>

Extract 2-4 passages about problems in {target_industry} within {target_geography}.
If no matching passages exist, return: {{"passages": []}}
"""


@traceable(name="passage_extractor_node")
async def passage_extractor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 4: Passage Extractor
    
    Extracts relevant passages from scraped content and DB results using Azure OpenAI gpt-5-mini.
    
    Args:
        state: Current workflow state with scraped content and DB results
        
    Returns:
        Updated workflow state with extracted passages
    """
    logger.info("Starting passage extraction")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "passage_extractor"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        llm_config = get_llm_config(state)
        
        # Get content sources
        scraped_content = state.get("scraped_content", [])
        db_hits = state.get("db_hits", [])
        
        if not scraped_content and not db_hits:
            logger.warning("No content found for passage extraction")
            state["passages"] = []
            return state
        
        logger.info(f"Extracting passages from {len(scraped_content)} scraped + {len(db_hits)} DB sources")
        
        # =============================================
        # PREPARE CONTENT FOR EXTRACTION
        # =============================================
        
        # Prepare content items for processing
        content_items = []
        
        # Add scraped content
        for item in scraped_content:
            content_items.append({
                "content": item.get("content", ""),
                "source_type": "web",
                "source_info": {
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "domain": extract_domain(item.get("url", ""))
                }
            })
        
        # Add DB content
        for item in db_hits:
            content_items.append({
                "content": item.get("statement", "") + "\n\n" + item.get("context", ""),
                "source_type": "db",
                "source_info": {
                    "id": item.get("id", ""),
                    "category": item.get("category", ""),
                    "geography": item.get("geography", "")
                }
            })
        
        # Filter out empty content
        content_items = [item for item in content_items if len(item["content"].strip()) > 100]
        
        logger.info(f"Processing {len(content_items)} content items for passage extraction")
        
        # =============================================
        # EXECUTE PARALLEL PASSAGE EXTRACTION
        # =============================================
        
        # Get target industry and geography from user params for strict filtering
        params = state.get("params", {})
        target_industry = params.get("industry", ["Not specified"])
        if isinstance(target_industry, list):
            target_industry = ", ".join(target_industry[:2])  # Take first 2 industries
        target_geography = params.get("geography", ["Not specified"])
        if isinstance(target_geography, list):
            target_geography = ", ".join(target_geography[:2])  # Take first 2 geographies
        
        logger.info(f"Passage extraction with strict filters: industry={target_industry}, geography={target_geography}")
        
        # Extract monitoring context from state
        monitoring_user_id = state.get("user_id")
        monitoring_tenant_id = state.get("tenant_id")
        monitoring_project_id = state.get("project_id")
        
        async def extract_all_passages():
            """Extract passages using batch processing for efficiency."""
            
            # REDUCED BATCH SIZE: Smaller batches (2-3) for better extraction quality
            # LLM gives more attention to each content item with smaller batches
            batch_size = 2  # Reduced from 5 to 2 for better quality
            batches = [content_items[i:i + batch_size] for i in range(0, len(content_items), batch_size)]
            
            logger.info(f"Processing {len(batches)} batches with up to {batch_size} items each")
            
            # Create batch extraction tasks with target industry and geography
            tasks = []
            for batch in batches:
                task = extract_passages_from_batch(
                    batch, 
                    target_industry, 
                    target_geography,
                    user_id=monitoring_user_id,
                    tenant_id=monitoring_tenant_id,
                    project_id=monitoring_project_id
                )
                tasks.append(task)
            
            # Execute with higher concurrency limit for better parallelism
            semaphore = asyncio.Semaphore(10)  # Increased from 5 to 10
            
            async def limited_extract(task):
                async with semaphore:
                    return await task
            
            # Run all batch extraction tasks
            results = await asyncio.gather(
                *[limited_extract(task) for task in tasks],
                return_exceptions=True
            )
            
            return results
        
        # Execute extraction
        extraction_results = await extract_all_passages()
        
        # =============================================
        # PROCESS EXTRACTION RESULTS
        # =============================================
        
        all_passages = []
        extraction_stats = {
            "content_items_processed": len(content_items),
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_passages": 0,
            "avg_relevance_score": 0
        }
        
        relevance_scores = []
        
        # Process batch results (each result is a list of passage lists)
        batch_index = 0
        for batch_result in extraction_results:
            if isinstance(batch_result, Exception):
                logger.warning(f"Batch extraction failed: {batch_result}")
                extraction_stats["failed_extractions"] += 1
                continue
            
            if not batch_result or not isinstance(batch_result, list):
                extraction_stats["failed_extractions"] += 1
                continue
            
            # Process each content item's passages in the batch
            for item_passages in batch_result:
                if batch_index >= len(content_items):
                    break
                    
                if item_passages and isinstance(item_passages, list):
                    # Add passages from this content item
                    for passage in item_passages:
                        if validate_passage(passage):
                            # Generate unique source UUID and create rich source metadata
                            source_uuid = str(uuid.uuid4())
                            source_info = content_items[batch_index]["source_info"]
                            
                            # Create enhanced source metadata
                            enhanced_source = {
                                "source_uuid": source_uuid,
                                "url": source_info.get("url", ""),
                                "title": source_info.get("title", ""),
                                "domain": source_info.get("domain", ""),
                                "publication_date": source_info.get("publication_date"),
                                "author": source_info.get("author"),
                                "source_type": content_items[batch_index]["source_type"],
                                "credibility_score": source_info.get("credibility_score", 5.0),
                                "content_type": source_info.get("content_type", "article"),
                                "extracted_at": datetime.now().isoformat(),
                                "passage_text": passage.get("text", "")[:200] + "..."  # Preview
                            }
                            
                            # Add to source registry in state
                            if "source_registry" not in state:
                                state["source_registry"] = {}
                            state["source_registry"][source_uuid] = enhanced_source
                            
                            # Add UUID reference to passage
                            passage["source_uuid"] = source_uuid
                            passage["source_item"] = source_info  # Keep for backward compatibility
                            passage["source_type"] = content_items[batch_index]["source_type"]
                            passage["extracted_at"] = datetime.now().isoformat()
                            
                            all_passages.append(passage)
                            relevance_scores.append(passage.get("relevance_score", 0))
                    
                    extraction_stats["successful_extractions"] += 1
                else:
                    extraction_stats["failed_extractions"] += 1
                
                batch_index += 1
        
        extraction_stats["total_passages"] = len(all_passages)
        if relevance_scores:
            extraction_stats["avg_relevance_score"] = sum(relevance_scores) / len(relevance_scores)
        
        # =============================================
        # STRICT INDUSTRY/GEOGRAPHY FILTERING
        # =============================================
        
        # Post-extraction filter: Remove passages that don't match target industry/geography
        strictly_filtered_passages = []
        filtered_out_count = 0
        
        for passage in all_passages:
            passage_industry = passage.get("industry", "").lower()
            passage_location = passage.get("location", "").lower()
            
            # Check if passage matches target industry
            industry_match = False
            if target_industry.lower() != "not specified":
                for ind in target_industry.lower().split(", "):
                    if ind in passage_industry or passage_industry in ind:
                        industry_match = True
                        break
                    # Also check in the passage text for industry keywords
                    if ind in passage.get("text", "").lower():
                        industry_match = True
                        break
            else:
                industry_match = True  # No filter specified
            
            # Check if passage matches target geography
            geography_match = False
            if target_geography.lower() != "not specified":
                for geo in target_geography.lower().split(", "):
                    if geo in passage_location or passage_location in geo:
                        geography_match = True
                        break
                    # Also check in the passage text for geography
                    if geo in passage.get("text", "").lower():
                        geography_match = True
                        break
            else:
                geography_match = True  # No filter specified
            
            # Only keep passages that match BOTH industry AND geography
            if industry_match and geography_match:
                strictly_filtered_passages.append(passage)
            else:
                filtered_out_count += 1
                logger.debug(f"Filtered out passage: industry_match={industry_match}, geography_match={geography_match}")
        
        logger.info(f"Strict filtering: kept {len(strictly_filtered_passages)}/{len(all_passages)} passages (filtered out {filtered_out_count})")
        
        # =============================================
        # FILTER AND RANK PASSAGES
        # =============================================
        
        # Sort by relevance score
        strictly_filtered_passages.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Remove duplicates based on text similarity
        unique_passages = remove_duplicate_passages(strictly_filtered_passages)
        
        # Limit to top passages
        max_passages = agent_config.get("max_passages", 50)
        final_passages = unique_passages[:max_passages]
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["passages"] = final_passages
        state["extraction_stats"] = extraction_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        extraction_metrics = {
            "content_items": len(content_items),
            "passages_extracted": len(final_passages),
            "success_rate": extraction_stats["successful_extractions"] / max(len(content_items), 1),
            "avg_relevance_score": extraction_stats["avg_relevance_score"],
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["passage_extractor"] = extraction_metrics
        
        logger.info(f"Passage extraction completed successfully")
        logger.info(f"Extracted {len(final_passages)} passages from {len(content_items)} sources")
        logger.info(f"Average relevance score: {extraction_stats['avg_relevance_score']:.2f}")
        
        return state
        
    except Exception as e:
        error_msg = f"Passage extraction failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


async def extract_passages_from_content(content_item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract passages from a single content item using LLM.
    
    Args:
        content_item: Content item with text and metadata
        
    Returns:
        List of extracted passages
    """
    try:
        content = content_item["content"]
        source_info = content_item["source_info"]
        
        # Skip if content is too short
        if len(content) < 200:
            return []
        
        # Truncate very long content
        if len(content) > 8000:
            content = content[:8000] + "..."
        
        # Format source info
        if content_item["source_type"] == "web":
            source_desc = f"URL: {source_info.get('url', '')}\nTitle: {source_info.get('title', '')}"
        else:
            source_desc = f"Database ID: {source_info.get('id', '')}\nCategory: {source_info.get('category', '')}"
        
        # Prepare messages
        user_prompt = PASSAGE_EXTRACTION_USER_PROMPT.format(
            content=content,
            source_info=source_desc
        )
        
        messages = [
            {"role": "system", "content": PASSAGE_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get LLM provider with Azure OpenAI support
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        # Create LLMConfig with Azure OpenAI or OpenAI model
        if provider_type == ModelProvider.AZURE_OPENAI:
            logger.info(f"Passage extractor using Azure OpenAI gpt-5-mini: {model_name}")
            llm_config = LLMConfig(
                model_name=model_name,  # Azure deployment name
                temperature=0.3,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            logger.info(f"Passage extractor using OpenAI model: {model_name}")
            llm_config = LLMConfig(
                model_name=model_name,  # OpenAI model name
                temperature=0.3,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                api_key=client_config.get("api_key")
            )
        
        # Use the AI module's OpenAI provider directly with proper config
        from src.mint.api.ai.providers import LLMConfig as ProviderLLMConfig
        
        # Convert to the provider's expected config format
        provider_config = ProviderLLMConfig(
            provider_type="llm",
            provider_name="openai",  # Required field
            api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            api_key=llm_config.api_key,  # Direct API key for immediate use
            azure_endpoint=getattr(llm_config, 'azure_endpoint', None),
            api_version=getattr(llm_config, 'api_version', None),
            base_url=getattr(llm_config, 'base_url', None)  # For gpt-5-mini pattern
        )
        
        llm_provider = OpenAIProvider(provider_config)
        
        # Define tool for structured extraction
        extraction_tool = {
            "type": "function",
            "function": {
                "name": "extract_passages",
                "description": "Extract relevant problem-focused passages from content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "passages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string", "description": "The extracted passage text"},
                                    "relevance_score": {"type": "number", "minimum": 1, "maximum": 10},
                                    "context": {"type": "string", "description": "Brief problem context"},
                                    "location": {"type": "string", "description": "Geographic location if mentioned"},
                                    "industry": {"type": "string", "description": "Industry/sector if mentioned"}
                                },
                                "required": ["text", "relevance_score", "context"]
                            },
                            "minItems": 0,
                            "maxItems": 4
                        }
                    },
                    "required": ["passages"]
                }
            }
        }
        
        # Call LLM
        response = await llm_provider.generate_responses_with_tools(messages, [extraction_tool])
        
        if not response or not response.arguments:
            return []
        
        passages = response.arguments.get("passages", [])
        return passages
        
    except Exception as e:
        logger.warning(f"Failed to extract passages from content: {str(e)}")
        return []


async def extract_passages_from_batch(
    content_batch: List[Dict[str, Any]], 
    target_industry: str = "Not specified",
    target_geography: str = "Not specified",
    user_id: str = None,
    tenant_id: str = None,
    project_id: str = None
) -> List[List[Dict[str, Any]]]:
    """
    Extract passages from multiple content items in a single LLM call for efficiency.
    
    Args:
        content_batch: List of content items to process together
        target_industry: The user's specified industry for strict filtering
        target_geography: The user's specified geography for strict filtering
        user_id: User ID for AI monitoring
        tenant_id: Tenant ID for AI monitoring
        project_id: Project ID for AI monitoring
        
    Returns:
        List of passage lists (one per content item)
    """
    try:
        if not content_batch:
            return []
        
        # Prepare batch content for processing
        batch_content = []
        for i, content_item in enumerate(content_batch):
            content = content_item["content"]
            source_info = content_item["source_info"]
            
            # Skip if content is too short
            if len(content) < 200:
                batch_content.append({"index": i, "content": "", "source_desc": ""})
                continue
            
            # Truncate very long content - INCREASED to 16K to capture more context
            # Many African news sources have problem descriptions in the middle/end of articles
            # gpt-4o-mini has 128k context, so we can afford larger content
            if len(content) > 16000:
                content = content[:16000] + "..."
            
            # Format source info
            if content_item["source_type"] == "web":
                source_desc = f"URL: {source_info.get('url', '')}"
            else:
                source_desc = f"DB ID: {source_info.get('id', '')}"
            
            batch_content.append({
                "index": i,
                "content": content,
                "source_desc": source_desc
            })
        
        # Create batch prompt
        content_sections = []
        for item in batch_content:
            if item["content"]:
                content_sections.append(f"CONTENT {item['index'] + 1}:\nSource: {item['source_desc']}\n{item['content']}\n")
        
        if not content_sections:
            return [[] for _ in content_batch]
        
        batch_prompt = "\n" + "="*50 + "\n".join(content_sections)
        
        # Add strict filtering instructions to the system prompt
        strict_filter_instruction = f"""

### STRICT FILTERING REQUIREMENTS:
- TARGET INDUSTRY: {target_industry} - ONLY extract passages about this industry
- TARGET GEOGRAPHY: {target_geography} - ONLY extract passages about this country/region
- REJECT passages about other industries (e.g., if target is Sports, reject Agriculture passages)
- REJECT passages about other countries (e.g., if target is Ethiopia, reject Nigeria passages)
- If content doesn't match both target industry AND target geography, return empty passages for that section

Process multiple content sections and return passages for each section separately.
"""
        
        messages = [
            {"role": "system", "content": PASSAGE_EXTRACTION_SYSTEM_PROMPT + strict_filter_instruction},
            {"role": "user", "content": f"Extract relevant problem passages about {target_industry} in {target_geography} from the following content sections:{batch_prompt}"}
        ]
        
        # Get LLM provider (reuse configuration)
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        if provider_type == ModelProvider.AZURE_OPENAI:
            llm_config = LLMConfig(
                model_name=model_name,
                temperature=0.3,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            llm_config = LLMConfig(
                model_name=model_name,
                temperature=0.3,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                api_key=client_config.get("api_key")
            )
        
        # Use the AI module's OpenAI provider directly with proper config
        from src.mint.api.ai.providers import LLMConfig as ProviderLLMConfig
        
        # Convert to the provider's expected config format
        provider_config = ProviderLLMConfig(
            provider_type="llm",
            provider_name="openai",  # Required field
            api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            api_key=llm_config.api_key,  # Direct API key for immediate use
            azure_endpoint=getattr(llm_config, 'azure_endpoint', None),
            api_version=getattr(llm_config, 'api_version', None),
            base_url=getattr(llm_config, 'base_url', None)  # For gpt-5-mini pattern
        )
        
        llm_provider = OpenAIProvider(provider_config)
        
        # Define batch extraction tool
        batch_tool = {
            "type": "function",
            "function": {
                "name": "extract_batch_passages",
                "description": "Extract passages from multiple content sections",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content_results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content_index": {"type": "integer", "description": "Index of the content section (1-based)"},
                                    "passages": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "text": {"type": "string"},
                                                "relevance_score": {"type": "number", "minimum": 1, "maximum": 10},
                                                "context": {"type": "string"},
                                                "location": {"type": "string"},
                                                "industry": {"type": "string"}
                                            },
                                            "required": ["text", "relevance_score", "context"]
                                        }
                                    }
                                },
                                "required": ["content_index", "passages"]
                            }
                        }
                    },
                    "required": ["content_results"]
                }
            }
        }
        
        # Call LLM with monitoring
        llm_start_time = datetime.now()
        
        try:
            response = await llm_provider.generate_responses_with_tools(messages, [batch_tool])
            llm_end_time = datetime.now()
            
            # Fire-and-forget monitoring (async, non-blocking)
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_passage_extraction",
                workflow_name="problem_generator_workflow",
                step_name="passage_extractor",
                environment="prod"
            )
            
            # Extract token usage
            usage = getattr(response, 'usage', {}) or {}
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = usage.get('total_tokens')
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="success",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
            )
            
        except Exception as e:
            llm_end_time = datetime.now()
            
            # Record error
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_passage_extraction",
                workflow_name="problem_generator_workflow",
                step_name="passage_extractor",
                environment="prod"
            )
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            raise
        
        if not response or not response.arguments:
            return [[] for _ in content_batch]
        
        # Process batch results
        content_results = response.arguments.get("content_results", [])
        results = [[] for _ in content_batch]  # Initialize empty results
        
        for result in content_results:
            content_index = result.get("content_index", 1) - 1  # Convert to 0-based
            if 0 <= content_index < len(content_batch):
                results[content_index] = result.get("passages", [])
        
        return results
        
    except Exception as e:
        logger.warning(f"Failed to extract passages from batch: {str(e)}")
        return [[] for _ in content_batch]


def validate_passage(passage: Dict[str, Any]) -> bool:
    """
    Validate that a passage meets quality requirements.
    
    Args:
        passage: Passage data to validate
        
    Returns:
        True if passage is valid
    """
    # Check required fields
    if not passage.get("text") or not passage.get("context"):
        logger.warning(f"Passage missing required fields: text={bool(passage.get('text'))}, context={bool(passage.get('context'))}")
        return False
    
    # Check text length - RELAXED to allow longer passages (LLM often generates 1000-2500 chars)
    text = passage["text"].strip()
    if len(text) < 20:
        logger.warning(f"Passage text too short: {len(text)} chars")
        return False
    if len(text) > 3000:
        logger.warning(f"Passage text too long: {len(text)} chars (max 3000)")
        return False
    
    # Check relevance score
    score = passage.get("relevance_score", 0)
    if not isinstance(score, (int, float)) or score < 1 or score > 10:
        logger.warning(f"Passage relevance score invalid: {score} (type: {type(score)})")
        return False
    
    # Check for problem indicators - EXPANDED list to catch more problem-related content
    problem_keywords = [
        # Direct problem words
        "lack", "shortage", "challenge", "problem", "issue", "difficulty",
        "unable", "cannot", "prevents", "hinders", "barrier", "obstacle",
        # Additional problem indicators
        "insufficient", "inadequate", "limited", "restrict", "constrain",
        "gap", "need", "demand", "require", "struggle", "fail", "failure",
        "decline", "decrease", "reduce", "low", "poor", "weak", "absent",
        "missing", "unavailable", "inaccessible", "unaffordable", "expensive",
        "costly", "scarce", "rare", "few", "minimal", "deficient",
        # Context words that often indicate problems
        "despite", "although", "however", "but", "yet", "unfortunately",
        "concern", "risk", "threat", "crisis", "urgent", "critical"
    ]
    
    text_lower = text.lower()
    has_problem_indicator = any(keyword in text_lower for keyword in problem_keywords)
    
    # If no problem indicator found, check if relevance score is high (LLM thought it was relevant)
    # Trust the LLM's judgment if it gave a high relevance score
    if not has_problem_indicator:
        if score >= 7:
            logger.info(f"Passage lacks explicit problem keywords but has high relevance score ({score}). Accepting.")
            return True
        else:
            logger.warning(f"Passage lacks problem indicators and has low relevance score ({score}). Text: '{text[:100]}...'")
            return False
    
    return True


def remove_duplicate_passages(passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate passages based on text similarity.
    
    Args:
        passages: List of passages to deduplicate
        
    Returns:
        List of unique passages
    """
    unique_passages = []
    seen_texts = set()
    
    for passage in passages:
        text = passage.get("text", "").strip().lower()
        
        # Simple deduplication based on first 100 characters
        text_key = text[:100]
        
        if text_key not in seen_texts:
            unique_passages.append(passage)
            seen_texts.add(text_key)
    
    return unique_passages


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return ""
