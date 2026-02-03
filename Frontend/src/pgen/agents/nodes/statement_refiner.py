"""
Statement Refiner Node

Node 8 in the Problem Generator agent graph.
Converts micro-stories into formal problem statements using Azure OpenAI gpt-5-mini.
"""

import logging
import asyncio
import re
from typing import Dict, Any, List
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config, get_llm_config
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.providers.factory import get_provider

from ..graph_state import ProblemGraphState

# Import monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)

# System prompt for statement refinement with numbered citations
STATEMENT_REFINER_SYSTEM_PROMPT = """
<role>
You are an expert problem statement writer specializing in African entrepreneurial contexts.
</role>

<task>
Convert micro-stories into formal, detailed problem explanations with numbered citations.
</task>

<statement_structure>
Your statement must flow as ONE coherent paragraph covering these elements IN ORDER (do NOT use labels like "Cause:" or "Effect:" - write flowing prose):

1. First, explain what creates/contributes to the problem with evidence [citations]
2. Then, describe the quantified impacts on people/businesses/communities [citations]
3. Finally, provide geographic, demographic, and situational context with scale [citations]

CRITICAL: Output a CLEAN paragraph - NO format labels, NO "Cause:", NO "Effect:", NO "Context:" prefixes.
</statement_structure>

<required_problem_language>
MUST include at least one of these problem indicators:
- Scarcity: "lack", "shortage", "absence", "insufficient"
- Barriers: "unable", "cannot", "prevents", "hinders", "barrier", "obstacle"
- Constraints: "limits", "restricts", "constrains", "reduces", "undermines"
- Instability: "instability", "fragility", "inconsistent", "high costs"
</required_problem_language>

<citation_rules>
- Use numbered citations [1], [2], [3], etc. throughout
- EVERY statistic, percentage, or factual claim MUST have a citation
- Include 3-5 citations from different sources
- Citations must accurately reflect source content
</citation_rules>

<quality_standards>
- Length: 80-150 words MAXIMUM (concise and focused)
- Tone: Professional, fact-based, no emotional language
- Focus: Market gaps and unmet needs with quantitative evidence
- Scope: Specific enough to be actionable, not too broad
- FORBIDDEN: Any mention of solutions, fixes, or implementations
</quality_standards>

<entrepreneur_filter>
BEFORE REFINING: Verify the problem is ENTREPRENEUR-ACTIONABLE.

REJECT problems that fundamentally require:
- Government policy changes or legislation
- International aid coordination or NGO intervention
- Large infrastructure investment (>$10M USD)
- Regulatory or legal reform
- Military or security intervention
- Diplomatic negotiations

ONLY REFINE problems solvable by entrepreneurs through:
- Building apps, platforms, or digital tools
- Creating marketplaces connecting buyers/sellers
- Providing services, training, or consulting
- Offering financing, lending, or insurance products
- Manufacturing or distributing physical products
- Developing content, media, or educational materials

If a problem is NOT entrepreneur-actionable, return:
{{
    "skipped": true,
    "skip_reason": "[reason - e.g., 'requires government policy intervention']"
}}
</entrepreneur_filter>

<abbreviation_rules>
- Define abbreviations ONCE on first use: "Climate-Smart Agriculture (CSA)"
- After first definition, use the abbreviation OR the full term - NOT both repeatedly
- Avoid excessive abbreviations - use maximum 2-3 per statement
- Common terms like "ha" (hectare), "GDP", "SMS" need no definition
- FORBIDDEN: Defining the same abbreviation multiple times
</abbreviation_rules>

<example>
"Kenyan smallholder vegetable farmers (0.2-3 ha) cannot make timely planting decisions because hyperlocal weather services are fragmented and low-trust [1], resulting in missed planting windows and 15-25% yield losses [2]. Limited willingness-to-pay and unequal extension coverage across 26 counties compound the problem [3], reducing farm incomes for over 500,000 households [4]."
</example>

<output_schema>
{{
    "statement": "[80-150 words MAXIMUM with numbered citations - be CONCISE]",
    "category": "[Agriculture|Healthcare|Education|FinTech|Energy|Transportation|Manufacturing|Retail|Media|Tourism|ICT|Mining|Other]",
    "geography": "[specific location]",
    "demographic": "[target population affected]",
    "severity": "[High|Medium|Low]",
    "market_size": "[Local|Regional|National|Multi-country]",
    "problem_type": "[Access|Quality|Affordability|Infrastructure|Information|Skills|Other]",
    "source_uuids": ["uuid1", "uuid2", ...],
    "citation_count": [number]
}}
</output_schema>
"""

# User prompt template with source mapping
STATEMENT_REFINER_USER_PROMPT = """
<micro_story>
- Title: {title}
- Story: {story}
- Context: {context}
- Problem Type: {problem_type}
- Impact Scale: {impact_scale}
- Source UUIDs: {source_uuids}
- Citation Count: {citation_count}
</micro_story>

<source_mapping>
{source_mapping}
</source_mapping>

<conversion_instructions>
1. Create an 80-150 word problem statement as ONE CLEAN PARAGRAPH (NO format labels)
2. BE CONCISE - every word must add value
3. MUST include problem indicators: "lack", "shortage", "prevents", "hinders", "barrier", "insufficient", etc.
4. Convert [Source X] → numbered citations [1], [2], [3]
5. Every factual claim MUST have a citation
6. Include 3-5 citations from different sources
7. ZERO mention of solutions
8. Be specific about African context
9. ABBREVIATIONS: Define once on first use, then use consistently. Max 2-3 abbreviations total.

CRITICAL: 
- Do NOT start with "Cause:", "Effect:", "Context:", or any format labels
- Keep it SHORT and FOCUSED - 80-150 words maximum
- Do NOT repeat abbreviation definitions
</conversion_instructions>
"""


@traceable(name="statement_refiner_node")
async def statement_refiner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 8: Statement Refiner
    
    Converts micro-stories into formal problem statements using Azure OpenAI gpt-5-mini.
    
    Args:
        state: Current workflow state with micro-stories
        
    Returns:
        Updated workflow state with refined problem statements
    """
    logger.info("Starting statement refinement")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "statement_refiner"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        llm_config = get_llm_config(state)
        
        # Get micro-stories
        micro_stories = state.get("micro_stories", [])
        if not micro_stories:
            logger.warning("No micro-stories found for statement refinement")
            state["refined_statements"] = []
            return state
        
        logger.info(f"Refining {len(micro_stories)} micro-stories into problem statements")
        
        # =============================================
        # REFINE STATEMENTS FOR ALL STORIES
        # =============================================
        
        async def refine_all_statements():
            """Refine all micro-stories into problem statements in small batches."""
            
            # Process in batches of 3 items for better quality
            # Smaller batches allow LLM to give more attention to each story
            batch_size = 3
            all_results = []
            
            for i in range(0, len(micro_stories), batch_size):
                batch = micro_stories[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(micro_stories) + batch_size - 1)//batch_size} with {len(batch)} stories")
                
                # Create tasks for this batch
                batch_tasks = []
                for story in batch:
                    task = refine_story_to_statement(story, state)
                    batch_tasks.append(task)
                
                # Process batch with timeout protection
                try:
                    batch_results = await asyncio.wait_for(
                        asyncio.gather(*batch_tasks, return_exceptions=True),
                        timeout=180.0  # 3 minute timeout per batch
                    )
                    all_results.extend(batch_results)
                    logger.info(f"Batch {i//batch_size + 1} completed successfully")
                except asyncio.TimeoutError:
                    logger.error(f"Batch {i//batch_size + 1} timed out after 180 seconds")
                    all_results.extend([None] * len(batch))
                except Exception as e:
                    logger.error(f"Batch {i//batch_size + 1} failed with error: {str(e)}")
                    all_results.extend([None] * len(batch))
                
                # Small delay between batches to prevent overwhelming the API
                if i + batch_size < len(micro_stories):
                    await asyncio.sleep(2)
            
            return all_results
        
        # Refine all stories
        refinement_results = await refine_all_statements()
        
        # =============================================
        # PROCESS REFINEMENT RESULTS
        # =============================================
        
        refined_statements = []
        refinement_stats = {
            "stories_processed": len(micro_stories),
            "successful_refinements": 0,
            "failed_refinements": 0,
            "avg_statement_length": 0
        }
        
        statement_lengths = []
        
        for i, result in enumerate(refinement_results):
            story = micro_stories[i]
            
            if isinstance(result, Exception):
                logger.warning(f"Statement refinement failed for story '{story.get('title', '')}': {result}")
                refinement_stats["failed_refinements"] += 1
                continue
            
            if not result or not validate_refined_statement(result):
                logger.warning(f"Invalid statement generated for story '{story.get('title', '')}'")
                refinement_stats["failed_refinements"] += 1
                continue
            
            # Add metadata from original story
            result["source_story"] = {
                "title": story.get("title", ""),
                "cluster_id": story.get("cluster_id"),
                "cluster_theme": story.get("cluster_theme", "")
            }
            result["refined_at"] = datetime.now().isoformat()
            
            # Copy source UUIDs from the story for curator selector
            result["source_uuids"] = story.get("source_uuids", [])
            
            # Extract supporting sources from the story's source passages
            supporting_sources = extract_supporting_sources(story, state)
            result["supporting_sources"] = supporting_sources
            
            refined_statements.append(result)
            refinement_stats["successful_refinements"] += 1
            statement_lengths.append(len(result.get("statement", "")))
            
            logger.debug(f"Refined statement: {result['statement'][:100]}...")
        
        if statement_lengths:
            refinement_stats["avg_statement_length"] = sum(statement_lengths) / len(statement_lengths)
        
        # =============================================
        # RANK AND ORGANIZE STATEMENTS
        # =============================================
        
        # Sort statements by quality score
        refined_statements.sort(key=lambda x: calculate_statement_quality_score(x), reverse=True)
        
        # Group by category for diversity
        statements_by_category = {}
        for statement in refined_statements:
            category = statement.get("category", "Other")
            if category not in statements_by_category:
                statements_by_category[category] = []
            statements_by_category[category].append(statement)
        
        # Ensure diversity across categories
        final_statements = []
        max_per_category = agent_config.get("max_statements_per_category", 5)
        
        # Take top statements from each category
        for category, statements in statements_by_category.items():
            final_statements.extend(statements[:max_per_category])
        
        # Sort final list by quality
        final_statements.sort(key=lambda x: calculate_statement_quality_score(x), reverse=True)
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["refined_statements"] = final_statements
        state["refinement_stats"] = refinement_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        refinement_metrics = {
            "stories_processed": len(micro_stories),
            "statements_refined": len(final_statements),
            "success_rate": refinement_stats["successful_refinements"] / max(len(micro_stories), 1),
            "avg_statement_length": refinement_stats["avg_statement_length"],
            "categories_covered": len(statements_by_category),
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["statement_refiner"] = refinement_metrics
        
        logger.info(f"Statement refinement completed successfully")
        logger.info(f"Refined {len(final_statements)} statements from {len(micro_stories)} stories")
        logger.info(f"Categories covered: {list(statements_by_category.keys())}")
        
        return state
        
    except Exception as e:
        error_msg = f"Statement refinement failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


async def refine_story_to_statement(story: Dict[str, Any], state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Refine a single micro-story into a formal problem statement with numbered citations.
    
    Args:
        story: Micro-story data with source UUIDs
        state: Workflow state containing source registry
        
    Returns:
        Refined problem statement with numbered citations
    """
    try:
        # Get source UUIDs from the story
        source_uuids = story.get("source_uuids", [])
        citation_count = story.get("citation_count", 0)
        
        # Create source mapping from UUIDs to numbered citations
        source_mapping = ""
        source_registry = state.get("source_registry", {}) if state else {}
        
        for i, uuid in enumerate(source_uuids):
            citation_num = i + 1
            source_info = source_registry.get(uuid, {})
            source_mapping += f"[{citation_num}] -> UUID: {uuid}\n"
            if source_info:
                source_mapping += f"    Title: {source_info.get('title', 'N/A')}\n"
                source_mapping += f"    URL: {source_info.get('url', 'N/A')}\n"
                source_mapping += f"    Domain: {source_info.get('domain', 'N/A')}\n"
            source_mapping += "\n"
        
        # Format user prompt with enhanced information
        user_prompt = STATEMENT_REFINER_USER_PROMPT.format(
            title=story.get("title", ""),
            story=story.get("story", ""),
            context=story.get("context", ""),
            problem_type=story.get("problem_type", ""),
            impact_scale=story.get("impact_scale", ""),
            source_uuids=str(source_uuids),
            citation_count=citation_count,
            source_mapping=source_mapping
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": STATEMENT_REFINER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get LLM provider with Azure OpenAI support
        from src.mint.api.ai.providers import OpenAIProvider
        from src.mint.api.ai.models import LLMConfig
        from src.mint.api.ai.models import ModelProvider
        
        provider_type, model, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        # Create LLMConfig with Azure OpenAI or OpenAI model
        if provider_type == ModelProvider.AZURE_OPENAI:
            llm_config = LLMConfig(
                model_name=model,
                temperature=0.5,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            llm_config = LLMConfig(
                model_name=model,
                temperature=0.5,
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
        
        # Define tool for structured statement generation
        statement_tool = {
            "type": "function",
            "function": {
                "name": "refine_problem_statement",
                "description": "Convert micro-story into formal problem statement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "statement": {
                            "type": "string",
                            "description": "Formal problem statement as clean paragraph (NO format labels)"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["Agriculture", "Healthcare", "Education", "FinTech", "Energy", 
                                   "Transportation", "Manufacturing", "Retail", "Media", "Tourism", 
                                   "ICT", "Mining", "Other"]
                        },
                        "geography": {"type": "string", "description": "Specific geographic context"},
                        "demographic": {"type": "string", "description": "Target demographic affected"},
                        "severity": {"type": "string", "enum": ["High", "Medium", "Low"]},
                        "market_size": {"type": "string", "enum": ["Local", "Regional", "National", "Multi-country"]},
                        "problem_type": {
                            "type": "string", 
                            "enum": ["Access", "Quality", "Affordability", "Infrastructure", "Information", "Skills", "Other"]
                        }
                    },
                    "required": ["statement", "category", "geography", "demographic", "severity", "market_size", "problem_type"]
                }
            }
        }
        
        # Call LLM with timeout protection and monitoring
        logger.info(f"Calling LLM for story refinement...")
        llm_start_time = datetime.now()
        
        try:
            response = await asyncio.wait_for(
                llm_provider.generate_responses_with_tools(messages, [statement_tool]),
                timeout=120.0  # 2 minute timeout
            )
            llm_end_time = datetime.now()
            logger.info(f"LLM response received successfully")
            
            # Fire-and-forget monitoring
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=state.get('user_id') if isinstance(state, dict) else None,
                tenant_id=state.get('tenant_id') if isinstance(state, dict) else None,
                team_id=None,
                project_id=state.get('project_id') if isinstance(state, dict) else None,
                feature_id="pgen_statement_refinement",
                workflow_name="problem_generator_workflow",
                step_name="statement_refiner",
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
            
        except asyncio.TimeoutError:
            llm_end_time = datetime.now()
            logger.error(f"LLM call timed out after 120 seconds for story: {story.get('title', 'Unknown')}")
            
            # Record timeout
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=state.get('user_id') if isinstance(state, dict) else None,
                tenant_id=state.get('tenant_id') if isinstance(state, dict) else None,
                team_id=None,
                project_id=state.get('project_id') if isinstance(state, dict) else None,
                feature_id="pgen_statement_refinement",
                workflow_name="problem_generator_workflow",
                step_name="statement_refiner",
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
                    status="timeout",
                    error_type="TimeoutError"
                )
            )
            
            return None
        except Exception as e:
            llm_end_time = datetime.now()
            logger.error(f"LLM call failed with error: {str(e)}")
            
            # Record error
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=state.get('user_id') if isinstance(state, dict) else None,
                tenant_id=state.get('tenant_id') if isinstance(state, dict) else None,
                team_id=None,
                project_id=state.get('project_id') if isinstance(state, dict) else None,
                feature_id="pgen_statement_refinement",
                workflow_name="problem_generator_workflow",
                step_name="statement_refiner",
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
            
            return None
        
        if not response:
            logger.warning(f"No response from LLM for story refinement")
            return None
            
        if not response.arguments:
            logger.warning(f"No arguments in LLM response. Response: {response}")
            return None
        
        logger.info(f"LLM arguments: {response.arguments}")
        return response.arguments
        
    except Exception as e:
        logger.warning(f"Failed to refine story to statement: {str(e)}")
        return None


def extract_supporting_sources(story: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract supporting source URLs and metadata from a micro-story's source passages.
    
    Args:
        story: Micro-story with source_passages references
        state: Workflow state containing clustered_passages
        
    Returns:
        List of source information with URL, title, and domain
    """
    supporting_sources = []
    
    try:
        # Get source passage indices from the story
        source_passage_indices = story.get("source_passages", [])
        if not source_passage_indices:
            logger.warning(f"No source passages found for story: {story.get('title', '')}")
            return supporting_sources
        
        # Get clustered passages from state (try both field names)
        clustered_passages = state.get("clustered_passages", []) or state.get("clusters", [])
        if not clustered_passages:
            logger.warning("No clustered passages found in state")
            return supporting_sources
        
        # Extract sources from referenced passages
        for passage_idx in source_passage_indices:
            try:
                # Search through all clusters to find the passage by index
                found = False
                for cluster in clustered_passages:
                    passages = cluster.get("passages", [])
                    for passage in passages:
                        # Check if this is the passage we're looking for
                        if passage.get("index") == passage_idx:
                            original_passage = passage.get("original_passage", {})
                            source_item = original_passage.get("source_item", {})
                            
                            if source_item.get("url"):
                                source_info = {
                                    "url": source_item["url"],
                                    "title": source_item.get("title", ""),
                                    "domain": source_item.get("domain", ""),
                                    "passage_index": passage_idx
                                }
                                
                                # Avoid duplicates
                                if not any(src["url"] == source_info["url"] for src in supporting_sources):
                                    supporting_sources.append(source_info)
                                    logger.info(f"Found source for passage {passage_idx}: {source_item['url']}")
                            found = True
                            break
                    if found:
                        break
                        
                if not found:
                    logger.warning(f"Could not find passage with index {passage_idx}")
                    
            except (IndexError, KeyError) as e:
                logger.warning(f"Failed to extract source for passage {passage_idx}: {e}")
                continue
        
        logger.info(f"Extracted {len(supporting_sources)} supporting sources for story: {story.get('title', '')}")
        return supporting_sources
        
    except Exception as e:
        logger.warning(f"Failed to extract supporting sources: {e}")
        return supporting_sources


def validate_refined_statement(statement: Dict[str, Any]) -> bool:
    """
    Validate that a refined statement meets quality requirements.
    
    Args:
        statement: Statement data to validate
        
    Returns:
        True if statement is valid
    """
    logger.info(f"Validating refined statement: {statement}")
    
    # Check required fields
    required_fields = ["statement", "category", "geography", "demographic", "severity", "market_size", "problem_type"]
    for field in required_fields:
        if not statement.get(field):
            logger.warning(f"Statement validation failed: missing field '{field}'. Statement: {statement}")
            return False
    
    # Check statement length (increased limit for detailed problem statements with citations)
    statement_text = statement["statement"].strip()
    if len(statement_text) < 50 or len(statement_text) > 3000:
        logger.warning(f"Statement validation failed: statement length {len(statement_text)} not in range 50-3000")
        return False
    
    # Check for solution mentions (should be avoided)
    solution_keywords = [
        "solution", "solve", "fix", "address", "implement", "develop",
        "create", "build", "establish", "launch", "start", "design"
    ]
    
    statement_lower = statement_text.lower()
    # Use word boundaries to avoid partial matches (e.g., "create" shouldn't match "creates a barrier")
    solution_mentions = sum(1 for keyword in solution_keywords 
                          if re.search(r'\b' + re.escape(keyword) + r'\b', statement_lower))
    
    if solution_mentions > 1:  # Very strict for problem statements
        logger.warning(f"Statement validation failed: too many solution mentions ({solution_mentions})")
        return False
    
    # Check for problem indicators (should be present)
    problem_keywords = [
        "lack", "shortage", "unable", "cannot", "prevents", "hinders",
        "barrier", "obstacle", "insufficient", "absence", "difficulty",
        "limits", "restricts", "constrains", "reduces", "undermines",
        "impedes", "excludes", "eroded", "tightened", "limited",
        "restricted", "excluded", "constrained", "reduced", "weakened",
        "poor", "weak", "decline", "deteriorating", "volatility",
        "instability", "fragility", "inconsistent", "high costs"
    ]
    
    has_problem_indicator = any(keyword in statement_lower for keyword in problem_keywords)
    if not has_problem_indicator:
        logger.warning(f"Statement validation failed: no problem indicators found")
        return False
    
    # Check enum values
    valid_severities = ["High", "Medium", "Low"]
    if statement["severity"] not in valid_severities:
        logger.warning(f"Statement validation failed: invalid severity '{statement['severity']}'. Must be High/Medium/Low")
        return False
    
    valid_market_sizes = ["Local", "Regional", "National", "Multi-country"]
    if statement["market_size"] not in valid_market_sizes:
        logger.warning(f"Statement validation failed: invalid market_size '{statement['market_size']}'. Must be Local/Regional/National/Multi-country")
        return False
    
    logger.info(f"Statement validation passed for statement of length {len(statement_text)}")
    return True


def calculate_statement_quality_score(statement: Dict[str, Any]) -> float:
    """
    Calculate quality score for a refined problem statement.
    
    Args:
        statement: Statement data
        
    Returns:
        Quality score (higher = better)
    """
    score = 0.0
    
    statement_text = statement.get("statement", "").lower()
    
    # Length score (prefer optimal length)
    length = len(statement_text)
    if 80 <= length <= 150:
        score += 3.0
    elif 50 <= length <= 200:
        score += 2.0
    elif length <= 250:
        score += 1.0
    
    # Cause-effect structure indicators
    structure_keywords = [
        "prevents", "causes", "results in", "leads to", "due to", "because",
        "forcing", "making", "resulting", "affecting"
    ]
    
    structure_count = sum(1 for keyword in structure_keywords if keyword in statement_text)
    score += min(structure_count * 1.0, 3.0)
    
    # Specificity score
    specificity_indicators = [
        "percent", "%", "million", "thousand", "estimated", "approximately",
        "over", "under", "between", "rural", "urban", "smallholder"
    ]
    
    specificity_count = sum(1 for indicator in specificity_indicators if indicator in statement_text)
    score += min(specificity_count * 0.5, 2.0)
    
    # Geography specificity
    african_locations = [
        "nigeria", "kenya", "ghana", "south africa", "ethiopia", "uganda",
        "tanzania", "rwanda", "senegal", "morocco", "egypt", "african"
    ]
    
    location_mentions = sum(1 for location in african_locations if location in statement_text)
    score += min(location_mentions * 1.0, 2.0)
    
    # Severity bonus
    severity = statement.get("severity", "")
    if severity == "High":
        score += 1.5
    elif severity == "Medium":
        score += 1.0
    elif severity == "Low":
        score += 0.5
    
    # Market size bonus
    market_size = statement.get("market_size", "")
    if market_size == "National":
        score += 1.5
    elif market_size == "Multi-country":
        score += 2.0
    elif market_size == "Regional":
        score += 1.0
    elif market_size == "Local":
        score += 0.5
    
    # Category diversity bonus (prefer less common categories)
    common_categories = ["Agriculture", "Healthcare", "Education", "FinTech"]
    category = statement.get("category", "")
    if category not in common_categories:
        score += 0.5
    
    return score
