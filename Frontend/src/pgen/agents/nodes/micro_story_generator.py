"""
Micro Story Generator Node

Node 7 in the Problem Generator agent graph.
Generates 2-3 micro-stories per cluster using Azure OpenAI gpt-5-mini.
"""

import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config, get_llm_config
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.providers.factory import get_provider

from ..graph_state import ProblemGraphState
from ..utils.llm_utils import call_llm_with_timeout_and_retry

# Import monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)

# System prompt for micro-story generation with rich citations
MICRO_STORY_SYSTEM_PROMPT = """
<role>
You are an expert storyteller specializing in African market contexts and entrepreneurial problem identification.
</role>

<task>
Generate 2-3 compelling micro-stories from the provided cluster of problem passages.
</task>

<story_structure>
Each story MUST follow this Cause → Effect structure:

1. **Context** [Source X]: Set the scene with specific location, demographics, scale
2. **Cause** [Source Y]: What creates/drives the problem with evidence
3. **Effect** [Source Z]: Quantified impacts on people/communities
4. **Scale** [Source W]: Specific numbers showing problem magnitude
</story_structure>

<quality_requirements>
- **Specificity**: Include exact locations, percentages, statistics from sources
- **Human Impact**: Show how real people/communities are affected
- **Entrepreneurial Relevance**: Problems that could realistically be addressed by business solutions
- **African Context**: Culturally relevant details that ground the story
- **Solution-Free**: ZERO mention of solutions, fixes, or implementations
</quality_requirements>

<citation_rules>
- Use [Source 1], [Source 2], etc. format
- EVERY statistic, percentage, or factual claim MUST have a citation
- Include 3-5 citations per story from different passages
- Citations must accurately reflect source content
</citation_rules>

<length_requirements>
- Each story: 150-300 words
- Title: 5-8 words, descriptive
</length_requirements>

<output_schema>
{{
    "stories": [
        {{
            "title": "[5-8 word descriptive title]",
            "story": "[150-300 words with [Source X] citations embedded]",
            "context": "[geographic/demographic context]",
            "problem_type": "[Access|Quality|Affordability|Infrastructure|Information|Skills]",
            "impact_scale": "[Local|Regional|National]",
            "source_uuids": ["uuid1", "uuid2", ...],
            "citation_count": [number of citations]
        }}
    ]
}}
</output_schema>
"""

# User prompt template with source mapping
MICRO_STORY_USER_PROMPT = """
<cluster_info>
- Theme: {cluster_theme}
- Size: {cluster_size} passages
</cluster_info>

<source_passages>
{passages_with_sources}
</source_passages>

<source_mapping>
{source_mapping}
</source_mapping>

<instructions>
1. Create 2-3 micro-stories following the Cause → Effect structure
2. Use [Source 1], [Source 2], etc. to cite specific passages
3. Every factual claim MUST have a citation
4. Include 3-5 citations per story from different passages
5. Focus on cause-and-effect relationships
6. ZERO mention of solutions or fixes
7. Ground each story in authentic African context
</instructions>
"""


@traceable(name="micro_story_generator_node")
async def micro_story_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 7: Micro Story Generator
    
    Generates 2-3 micro-stories per cluster using Azure OpenAI gpt-5-mini.
    
    Args:
        state: Current workflow state with clustered passages
        
    Returns:
        Updated workflow state with generated micro-stories
    """
    logger.info("Starting micro-story generation")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "micro_story_generator"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        llm_config = get_llm_config(state)
        
        # Get clusters
        clusters = state.get("clusters", [])
        if not clusters:
            logger.warning("No clusters found for micro-story generation")
            state["micro_stories"] = []
            return state
        
        logger.info(f"Generating micro-stories for {len(clusters)} clusters")
        
        # =============================================
        # GENERATE STORIES FOR EACH CLUSTER
        # =============================================
        
        # Extract monitoring context from state
        monitoring_user_id = state.get("user_id")
        monitoring_tenant_id = state.get("tenant_id")
        monitoring_project_id = state.get("project_id")
        
        async def generate_all_stories():
            """Generate micro-stories for all clusters concurrently."""
            
            # Create story generation tasks
            tasks = []
            for cluster in clusters:
                task = generate_stories_for_cluster(
                    cluster,
                    user_id=monitoring_user_id,
                    tenant_id=monitoring_tenant_id,
                    project_id=monitoring_project_id
                )
                tasks.append(task)
            
            # Execute with concurrency limit
            semaphore = asyncio.Semaphore(5)  # Limit concurrent LLM calls
            
            async def limited_generate(task):
                async with semaphore:
                    return await task
            
            # Run all generation tasks
            results = await asyncio.gather(
                *[limited_generate(task) for task in tasks],
                return_exceptions=True
            )
            
            return results
        
        # Generate stories for all clusters
        story_results = await generate_all_stories()
        
        # =============================================
        # PROCESS STORY GENERATION RESULTS
        # =============================================
        
        all_micro_stories = []
        generation_stats = {
            "clusters_processed": len(clusters),
            "successful_generations": 0,
            "failed_generations": 0,
            "total_stories": 0,
            "avg_stories_per_cluster": 0
        }
        
        for i, result in enumerate(story_results):
            cluster = clusters[i]
            
            if isinstance(result, Exception):
                cluster_id = cluster.get("id", cluster.get("cluster_id", "unknown"))
                cluster_theme = cluster.get("theme", "unknown")
                logger.error(f"Story generation failed for cluster {cluster_id} (theme: {cluster_theme}): {result}")
                logger.error(f"Exception type: {type(result).__name__}")
                generation_stats["failed_generations"] += 1
                continue
            
            if not result or not isinstance(result, list):
                cluster_id = cluster.get("id", cluster.get("cluster_id", "unknown"))
                cluster_theme = cluster.get("theme", "unknown")
                logger.warning(f"No stories generated for cluster {cluster_id} (theme: {cluster_theme}). Result type: {type(result)}, Result: {result}")
                generation_stats["failed_generations"] += 1
                continue
            
            # Process stories from this cluster
            cluster_stories = []
            for story in result:
                if validate_micro_story(story):
                    # Add cluster metadata
                    story["cluster_id"] = cluster["id"]
                    story["cluster_theme"] = cluster["theme"]
                    story["generated_at"] = datetime.now().isoformat()
                    
                    cluster_stories.append(story)
            
            if cluster_stories:
                all_micro_stories.extend(cluster_stories)
                generation_stats["successful_generations"] += 1
                generation_stats["total_stories"] += len(cluster_stories)
                
                logger.info(f"Generated {len(cluster_stories)} stories for cluster {cluster['id']}: {cluster['theme']}")
            else:
                generation_stats["failed_generations"] += 1
        
        if generation_stats["successful_generations"] > 0:
            generation_stats["avg_stories_per_cluster"] = (
                generation_stats["total_stories"] / generation_stats["successful_generations"]
            )
        
        # =============================================
        # RANK AND FILTER STORIES
        # =============================================
        
        # Sort stories by quality indicators
        all_micro_stories.sort(key=lambda x: calculate_story_quality_score(x), reverse=True)
        
        # Limit total number of stories
        max_stories = agent_config.get("max_micro_stories", 20)
        final_stories = all_micro_stories[:max_stories]
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["micro_stories"] = final_stories
        state["story_generation_stats"] = generation_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        story_metrics = {
            "clusters_processed": len(clusters),
            "stories_generated": len(final_stories),
            "success_rate": generation_stats["successful_generations"] / max(len(clusters), 1),
            "avg_stories_per_cluster": generation_stats["avg_stories_per_cluster"],
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["micro_story_generator"] = story_metrics
        
        logger.info(f"Micro-story generation completed successfully")
        logger.info(f"Generated {len(final_stories)} stories from {len(clusters)} clusters")
        
        return state
        
    except Exception as e:
        error_msg = f"Micro-story generation failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


async def generate_stories_for_cluster(
    cluster: Dict[str, Any],
    user_id: str = None,
    tenant_id: str = None,
    project_id: str = None
) -> List[Dict[str, Any]]:
    """
    Generate micro-stories for a single cluster with rich source citations.
    
    Args:
        cluster: Cluster data with passages
        user_id: User ID for AI monitoring
        tenant_id: Tenant ID for AI monitoring
        project_id: Project ID for AI monitoring
        
    Returns:
        List of generated micro-stories with source UUIDs
    """
    try:
        cluster_theme = cluster.get("theme", "Unknown Theme")
        passages = cluster.get("passages", [])
        
        if not passages:
            logger.warning(f"No passages found in cluster: {cluster_theme}")
            return []
        
        logger.info(f"Generating stories for cluster '{cluster_theme}' with {len(passages)} passages")
        
        # Create source mapping for citations with UUID VALIDATION
        source_mapping = {}
        passages_with_sources = ""
        valid_uuid_count = 0
        
        for i, passage in enumerate(passages):
            source_num = i + 1
            
            # ENHANCED UUID EXTRACTION: Check multiple locations for UUID
            source_uuid = None
            
            # Priority 1: Check original_passage structure
            original_passage = passage.get("original_passage", {})
            if original_passage.get("source_uuid") and original_passage["source_uuid"] != "unknown":
                source_uuid = original_passage["source_uuid"]
            
            # Priority 2: Check direct source_uuid field
            if not source_uuid and passage.get("source_uuid") and passage["source_uuid"] != "unknown":
                source_uuid = passage["source_uuid"]
            
            # Priority 3: Check source_item for UUID
            source_item = passage.get("source_item", {})
            if not source_uuid and source_item.get("uuid") and source_item["uuid"] != "unknown":
                source_uuid = source_item["uuid"]
            
            # Priority 4: Generate a new UUID if none found (with warning)
            if not source_uuid or source_uuid == "unknown":
                import uuid as uuid_lib
                source_uuid = str(uuid_lib.uuid4())
                logger.warning(f"Generated new UUID for passage {source_num} (no valid UUID found): {source_uuid}")
            else:
                valid_uuid_count += 1
            
            # Validate UUID format (36 chars with dashes)
            if len(source_uuid) != 36 or source_uuid.count('-') != 4:
                import uuid as uuid_lib
                source_uuid = str(uuid_lib.uuid4())
                logger.warning(f"Invalid UUID format for passage {source_num}, generated new: {source_uuid}")
            
            source_mapping[f"Source {source_num}"] = source_uuid
            
            # Include source text SNIPPET in prompt to help LLM cite correctly
            passage_text = passage.get('text', '')
            text_snippet = passage_text[:200] + "..." if len(passage_text) > 200 else passage_text
            
            passages_with_sources += f"\n[Source {source_num}] (UUID: {source_uuid})\n"
            passages_with_sources += f"SNIPPET: \"{text_snippet}\"\n"
            passages_with_sources += f"Full Text: {passage_text}\n"
            passages_with_sources += f"Relevance: {passage.get('relevance_score', 0):.1f}\n"
            passages_with_sources += f"Location: {passage.get('location', 'Unknown')}\n"
            passages_with_sources += f"Industry: {passage.get('industry', 'Unknown')}\n"
            
            # Add source metadata if available
            if source_item:
                passages_with_sources += f"Source URL: {source_item.get('url', 'N/A')}\n"
                passages_with_sources += f"Source Title: {source_item.get('title', 'N/A')}\n"
            passages_with_sources += "-" * 60
        
        logger.info(f"Source mapping created: {valid_uuid_count}/{len(passages)} passages had valid UUIDs")
        
        # Create source mapping text
        source_mapping_text = "\n".join([f"{ref} -> UUID: {uuid}" for ref, uuid in source_mapping.items()])
        
        # Format user prompt with enhanced source information
        user_prompt = MICRO_STORY_USER_PROMPT.format(
            cluster_theme=cluster_theme,
            cluster_size=len(passages),
            passages_with_sources=passages_with_sources,
            source_mapping=source_mapping_text
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": MICRO_STORY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get LLM provider with Azure OpenAI support
        from src.mint.api.ai.providers import OpenAIProvider
        from src.mint.api.ai.models import LLMConfig
        from src.mint.api.ai.models import ModelProvider
        
        provider_type, model, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        if provider_type == ModelProvider.AZURE_OPENAI:
            # Use Azure OpenAI with gpt-5-mini
            llm_config = LLMConfig(
                model_name=model,
                temperature=0.7,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            # Fallback to regular OpenAI
            llm_config = LLMConfig(
                model_name=model,
                temperature=0.7,
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
        
        # Define tool for structured story generation
        story_tool = {
            "type": "function",
            "function": {
                "name": "generate_micro_stories",
                "description": "Generate micro-stories from problem passages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "stories": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "description": "Brief story title"},
                                    "story": {"type": "string", "description": "Full micro-story text with [Source X] citations"},
                                    "context": {"type": "string", "description": "Geographic/impact focus context"},
                                    "problem_type": {"type": "string", "description": "Category of problem"},
                                    "impact_scale": {"type": "string", "enum": ["Local", "Regional", "National"]},
                                    "source_uuids": {"type": "array", "items": {"type": "string"}, "description": "Array of source UUIDs used"},
                                    "citation_count": {"type": "integer", "description": "Number of citations in the story"}
                                },
                                "required": ["title", "story", "context", "problem_type", "impact_scale", "source_uuids", "citation_count"]
                            },
                            "minItems": 2,
                            "maxItems": 3
                        }
                    },
                    "required": ["stories"]
                }
            }
        }
        
        # Call LLM with timeout protection and retry logic
        cluster_id = cluster.get("id", cluster.get("cluster_id", "unknown"))
        logger.info(f"Calling LLM for cluster {cluster_id}...")
        
        llm_start_time = datetime.now()
        
        try:
            response = await call_llm_with_timeout_and_retry(
                llm_provider, messages, [story_tool], cluster_id
            )
            llm_end_time = datetime.now()
            
            # Fire-and-forget monitoring
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_micro_story_generation",
                workflow_name="problem_generator_workflow",
                step_name="micro_story_generator",
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
                feature_id="pgen_micro_story_generation",
                workflow_name="problem_generator_workflow",
                step_name="micro_story_generator",
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
        
        logger.info(f"LLM response for cluster {cluster_id}: {response}")
        
        if not response:
            logger.warning(f"No response from LLM for cluster {cluster_id}")
            return []
            
        if not response.arguments:
            logger.warning(f"No arguments in LLM response for cluster {cluster_id}. Response: {response}")
            return []
        
        logger.info(f"LLM arguments for cluster {cluster_id}: {response.arguments}")
        
        stories = response.arguments.get("stories", [])
        logger.info(f"Extracted {len(stories)} stories for cluster {cluster_id}: {stories}")
        
        # ENHANCED UUID MAPPING - Extract and validate UUIDs from story citations
        for story in stories:
            story_text = story.get("story", "")
            actual_uuids = []
            
            # Find all [Source X] references in the story
            import re
            source_refs = re.findall(r'\[Source (\d+)\]', story_text)
            
            for source_ref in source_refs:
                source_key = f"Source {source_ref}"
                if source_key in source_mapping:
                    actual_uuid = source_mapping[source_key]
                    # All UUIDs should be valid now (we validated/generated above)
                    if actual_uuid and actual_uuid not in actual_uuids:
                        actual_uuids.append(actual_uuid)
            
            # Set source_uuids based on what we found
            if actual_uuids:
                story["source_uuids"] = actual_uuids
                logger.info(f"Mapped {len(actual_uuids)} UUIDs for story '{story.get('title', 'Unknown')}'")
            else:
                # Fallback: Use all UUIDs from this cluster (story should cite at least one source)
                all_cluster_uuids = list(source_mapping.values())
                story["source_uuids"] = all_cluster_uuids[:3]  # Limit to first 3
                logger.warning(f"No [Source X] citations found in story '{story.get('title', 'Unknown')}', using cluster UUIDs")
            
            # Ensure source_uuids is never empty
            if not story.get("source_uuids"):
                import uuid as uuid_lib
                story["source_uuids"] = [str(uuid_lib.uuid4())]
                logger.warning(f"Generated fallback UUID for story '{story.get('title', 'Unknown')}'")
            
            # Store source_mapping in story for downstream use
            story["_source_mapping"] = source_mapping
        
        return stories
        
    except Exception as e:
        cluster_id = cluster.get("id", cluster.get("cluster_id", "unknown"))
        cluster_theme = cluster.get("theme", "unknown")
        passage_count = len(cluster.get("passages", []))
        logger.error(f"Failed to generate stories for cluster {cluster_id} (theme: {cluster_theme}, {passage_count} passages): {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []


def validate_micro_story(story: Dict[str, Any]) -> bool:
    """
    Validate that a micro-story meets quality requirements.
    
    Args:
        story: Story data to validate
        
    Returns:
        True if story is valid
    """
    logger.info(f"Validating story: {story.get('title', 'No title')}")
    
    # Check required fields
    required_fields = ["title", "story", "context", "problem_type", "impact_scale"]
    for field in required_fields:
        if not story.get(field):
            logger.warning(f"Story validation failed: missing field '{field}'. Story: {story}")
            return False
    
    # Check story length (increased limit for enhanced citations and richer content)
    story_text = story["story"].strip()
    if len(story_text) < 100 or len(story_text) > 3000:
        logger.warning(f"Story validation failed: story length {len(story_text)} not in range 100-3000. Title: {story.get('title')}")
        return False
    
    # Check title length
    title = story["title"].strip()
    if len(title) < 10 or len(title) > 80:
        logger.warning(f"Story validation failed: title length {len(title)} not in range 10-80. Title: '{title}'")
        return False
    
    # Check impact scale
    if story["impact_scale"] not in ["Local", "Regional", "National"]:
        logger.warning(f"Story validation failed: invalid impact_scale '{story['impact_scale']}'. Must be Local/Regional/National. Title: {story.get('title')}")
        return False
    
    # Check for solution mentions (should be avoided)
    solution_keywords = [
        "solution", "solve", "fix", "address", "implement", "develop",
        "create", "build", "establish", "launch", "start"
    ]
    
    story_lower = story_text.lower()
    # Use word boundaries to avoid partial matches
    solution_mentions = sum(1 for keyword in solution_keywords 
                          if re.search(r'\b' + re.escape(keyword) + r'\b', story_lower))
    
    if solution_mentions > 2:  # Allow some flexibility
        logger.warning(f"Story validation failed: too many solution mentions ({solution_mentions}). Title: {story.get('title')}")
        return False
    
    logger.info(f"Story validation passed: '{story.get('title')}'")
    return True


def calculate_story_quality_score(story: Dict[str, Any]) -> float:
    """
    Calculate quality score for a micro-story.
    
    Args:
        story: Story data
        
    Returns:
        Quality score (higher = better)
    """
    score = 0.0
    
    story_text = story.get("story", "").lower()
    
    # Length score (prefer optimal length)
    length = len(story_text)
    if 150 <= length <= 250:
        score += 2.0
    elif 100 <= length <= 300:
        score += 1.0
    
    # Problem indicator score
    problem_keywords = [
        "lack", "shortage", "unable", "difficulty", "challenge", "prevents",
        "hinders", "barrier", "obstacle", "insufficient", "absence"
    ]
    
    problem_count = sum(1 for keyword in problem_keywords if keyword in story_text)
    score += min(problem_count * 0.5, 2.0)
    
    # Context richness score
    context_indicators = [
        "percent", "%", "million", "thousand", "rural", "urban", "women",
        "farmers", "students", "businesses", "households"
    ]
    
    context_count = sum(1 for indicator in context_indicators if indicator in story_text)
    score += min(context_count * 0.3, 1.5)
    
    # Impact scale bonus
    impact_scale = story.get("impact_scale", "")
    if impact_scale == "National":
        score += 1.0
    elif impact_scale == "Regional":
        score += 0.7
    elif impact_scale == "Local":
        score += 0.5
    
    # Specificity score (specific locations, numbers, etc.)
    specificity_indicators = [
        "nigeria", "kenya", "ghana", "south africa", "ethiopia", "uganda",
        "tanzania", "rwanda", "senegal", "morocco", "egypt", "lagos",
        "nairobi", "accra", "cape town", "addis ababa", "kampala"
    ]
    
    specificity_count = sum(1 for indicator in specificity_indicators if indicator in story_text)
    score += min(specificity_count * 0.4, 1.0)
    
    return score
