"""
Query Expander Node

Node 1 in the Problem Generator agent graph.
Generates 10-15 search queries from validated parameters using Azure OpenAI gpt-5-mini.
"""

import logging
import random
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config, get_llm_config
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.api.ai.models import ModelProvider, AZURE_DEPLOYMENTS
from src.mint.api.ai.providers import LLMProvider, OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.providers.registry import ProviderError

from ..graph_state import ProblemGraphState

# Import monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


# =============================================
# SEMANTIC MATCHING HELPERS
# =============================================

# Industry synonyms for semantic matching
INDUSTRY_SYNONYMS = {
    "Agriculture": ["farming", "agri", "crop", "livestock", "agribusiness", "food production", "agricultural"],
    "Healthcare": ["health", "medical", "hospital", "clinic", "pharma", "wellness", "healthcare"],
    "FinTech": ["finance", "banking", "payments", "lending", "credit", "insurance", "fintech", "financial"],
    "Education": ["learning", "school", "training", "edtech", "skills", "university", "educational"],
    "Energy": ["power", "electricity", "solar", "renewable", "utilities", "energy"],
    "Transportation": ["logistics", "mobility", "transport", "shipping", "delivery"],
    "ICT": ["technology", "digital", "mobile", "telecom", "tech", "ict", "software"],
    "Manufacturing": ["production", "industrial", "factory", "manufacturing"],
    "Construction": ["building", "infrastructure", "real estate", "construction"],
    "Tourism": ["travel", "hospitality", "hotel", "tourism"],
    "Water": ["sanitation", "clean water", "wash", "water"],
    "Climate": ["environment", "sustainability", "green", "climate", "environmental"],
    "Government": ["public", "policy", "govtech", "government"],
    "Mining": ["natural resources", "extraction", "mining"],
    "Media": ["entertainment", "content", "media", "broadcast"],
    "Retail": ["commerce", "shopping", "e-commerce", "ecommerce", "retail"],
    "Sports & Recreation": ["sports", "recreation", "fitness", "athletics", "gym", "wellness", "exercise", "sport"]
}

# Region to country mapping for geography matching
REGION_COUNTRIES = {
    "east africa": ["kenya", "ethiopia", "uganda", "tanzania", "rwanda", "burundi", "south sudan", "somalia"],
    "west africa": ["nigeria", "ghana", "senegal", "mali", "burkina faso", "côte d'ivoire", "ivory coast", "liberia", "sierra leone"],
    "southern africa": ["south africa", "botswana", "namibia", "zambia", "zimbabwe", "mozambique", "malawi"],
    "north africa": ["egypt", "morocco", "tunisia", "algeria", "libya", "sudan"],
    "central africa": ["cameroon", "democratic republic of congo", "drc", "congo", "chad", "gabon"]
}


def _semantic_industry_match(query: str, industries: list) -> bool:
    """
    Check for semantic industry match, not just exact string.
    
    Args:
        query: The search query to check
        industries: List of user's selected industries
        
    Returns:
        True if query semantically matches any of the user's industries
    """
    query_lower = query.lower()
    
    for industry in industries:
        industry_lower = industry.lower()
        
        # Direct match
        if industry_lower in query_lower:
            return True
        
        # Check synonyms
        synonyms = INDUSTRY_SYNONYMS.get(industry, [])
        for synonym in synonyms:
            if synonym.lower() in query_lower:
                return True
        
        # Also check if industry key matches (for cases like "Sports & Recreation" -> "sports")
        for key, syns in INDUSTRY_SYNONYMS.items():
            if industry_lower in key.lower() or key.lower() in industry_lower:
                for syn in syns:
                    if syn.lower() in query_lower:
                        return True
    
    return False


def _semantic_geography_match(query: str, geography: str) -> bool:
    """
    Check for semantic geography match.
    
    Args:
        query: The search query to check
        geography: User's selected geography
        
    Returns:
        True if query semantically matches the geography
    """
    if not geography:
        return False
        
    query_lower = query.lower()
    geo_lower = geography.lower()
    
    # Direct match
    if geo_lower in query_lower:
        return True
    
    # Region-to-country matching
    for region, countries in REGION_COUNTRIES.items():
        # If user specified a region, allow countries within that region
        if geo_lower == region:
            if any(country in query_lower for country in countries):
                return True
        # If user specified a country, allow region match
        if geo_lower in countries:
            if region in query_lower:
                return True
    
    return False


# System prompt for query generation
QUERY_EXPANSION_SYSTEM_PROMPT = """
<role>
You are QueryBuilder, an expert research analyst specializing in African markets and emerging economies. You generate precise, high-yield search queries to uncover real-world problems.
</role>

<task>
Generate EXACTLY 12 search queries to discover authentic problems based on user parameters.
</task>

<sacred_rules>
These rules are INVIOLABLE - violation of any rule invalidates the entire output:

1. **INDUSTRY LOCK**: Every query MUST contain the user's exact industry. "Sports & Recreation" means ONLY sports/fitness/athletics/recreation/wellness queries.
2. **GEOGRAPHY LOCK**: Every query MUST contain the user's exact country. "Ethiopia" means ONLY Ethiopia-specific queries - not Nigeria, Kenya, or generic "Africa".
3. **PRODUCT TYPE CONTEXT**: Every query SHOULD reflect the user's product type context (digital, physical, services, etc.).
4. **PAIN KEYWORD REQUIRED**: Every query MUST contain at least one pain indicator.
5. **NO SUBSTITUTIONS**: Never substitute a "more common" industry or country.
</sacred_rules>

<pain_keywords>
Include at least one per query:
- Scarcity: "lack of", "shortage of", "absence of", "insufficient"
- Barriers: "prevents", "hampers", "restricts", "barriers to", "limited access to"
- Quality: "poor quality", "unreliable", "inadequate", "inconsistent"
- Cost: "high cost of", "expensive", "unaffordable"
- Impact: "causes", "delays", "worsens", "challenges in"
</pain_keywords>

<product_specific_templates>
FOR DIGITAL PRODUCTS (apps, platforms, software):
- "[INDUSTRY] mobile app challenges [GEOGRAPHY] [PAIN]"
- "[GEOGRAPHY] [INDUSTRY] digital platform gaps [PAIN]"
- "[INDUSTRY] tech startup problems [GEOGRAPHY] [PAIN]"
- "[PAIN] [INDUSTRY] software solutions needed [GEOGRAPHY]"

FOR PHYSICAL PRODUCTS (goods, equipment, consumables):
- "[INDUSTRY] supply chain gaps [GEOGRAPHY] [PAIN]"
- "[GEOGRAPHY] [INDUSTRY] distribution challenges [PAIN]"
- "[INDUSTRY] product quality issues [GEOGRAPHY] [PAIN]"
- "[PAIN] [INDUSTRY] manufacturing barriers [GEOGRAPHY]"

FOR SERVICES (training, consulting, support):
- "[INDUSTRY] service delivery problems [GEOGRAPHY] [PAIN]"
- "[GEOGRAPHY] [INDUSTRY] training gaps [PAIN]"
- "[PAIN] [INDUSTRY] consultation needs [GEOGRAPHY]"

FOR CREATIVE PRODUCTS/SERVICES:
- "[INDUSTRY] market access barriers [GEOGRAPHY] [PAIN]"
- "[GEOGRAPHY] [INDUSTRY] innovation opportunities [PAIN]"
</product_specific_templates>

<query_templates>
Use these patterns, always including [INDUSTRY] + [GEOGRAPHY] + [PAIN]:
- "[INDUSTRY] challenges [GEOGRAPHY] [PAIN]"
- "[GEOGRAPHY] [INDUSTRY] [PAIN] [TARGET_CUSTOMER]"
- "[PAIN] [INDUSTRY] in [GEOGRAPHY]"
- "[INDUSTRY] infrastructure issues [GEOGRAPHY]"
- "[GEOGRAPHY] [INDUSTRY] market gaps [PAIN]"
</query_templates>

<validation_examples>
For "Sports & Recreation" + "Ethiopia" + "Digital Products":

✅ VALID:
- "Sports facilities challenges Ethiopia lack of mobile apps"
- "Ethiopia recreation digital platform problems barriers"
- "Athletics training app challenges Ethiopia insufficient"
- "Sports booking platform gaps Ethiopia limited access"

❌ INVALID (reject these patterns):
- "Agriculture challenges Ethiopia" → WRONG INDUSTRY
- "Sports facilities Nigeria" → WRONG GEOGRAPHY
- "African sports challenges" → TOO GENERIC (must specify Ethiopia)
</validation_examples>

<output_rules>
- Return EXACTLY 12 queries
- Each query: 5-35 words
- Output: JSON object with "queries" array
- No prose, no explanations
</output_rules>
"""

# User prompt template
QUERY_EXPANSION_USER_PROMPT = """
<locked_parameters>
These MUST appear in EVERY query:
- Industry: {industry}
- Geography: {geography}
- Product Type Context: {product_type}
</locked_parameters>

<distributable_context>
Distribute these across the 12 queries for variety:
- Target Customer: {target_customer}
- Impact Focus: {impact_focus}
- Background: {background}
</distributable_context>

<validation_checklist>
Before outputting, verify each query:
☐ Contains "{industry}" or direct synonym
☐ Contains "{geography}" explicitly (not generic "Africa")
☐ Contains at least one pain keyword
☐ Is 5-35 words
</validation_checklist>

<output_schema>
{{
    "queries": [
        "[query 1 about {industry} in {geography} with pain keyword]",
        "[query 2 about {industry} in {geography} with pain keyword]",
        ... (exactly 12 total)
    ]
}}
</output_schema>
"""


@traceable(name="query_expander_node")
async def query_expander_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 1: Query Expander
    
    Generates 10-15 search queries from validated parameters using Azure OpenAI gpt-5-mini.
    
    Args:
        state: Current workflow state with validated parameters
        
    Returns:
        Updated workflow state with generated queries
    """
    logger.info("Starting query expansion")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "query_expander"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        llm_config = get_llm_config(state)
        
        # Get validated parameters
        params = state.get("params", {})
        if not params:
            raise ValueError("No validated parameters found for query expansion")
        
        logger.info("Generating search queries from validated parameters")
        
        # =============================================
        # PREPARE PARAMETER STRINGS
        # =============================================
        
        # Convert parameter lists to readable strings and map to expected format
        param_strings = {}
        for key, value in params.items():
            if isinstance(value, list):
                if len(value) <= 3:
                    param_strings[key] = ", ".join(value)
                else:
                    # For long lists, show first 3 + count
                    param_strings[key] = f"{', '.join(value[:3])} (and {len(value)-3} others)"
            else:
                param_strings[key] = str(value)
        
        # Map parameters to expected prompt format with defaults (optimized to 6 core parameters)
        prompt_params = {
            "industry": param_strings.get("industry", "Not specified"),
            "geography": param_strings.get("geography", "Not specified"),
            "background": param_strings.get("background", "Not specified"),
            "product_type": param_strings.get("product_type", "Not specified"),
            "target_customer": param_strings.get("target_customer", "Not specified"),
            "impact_focus": param_strings.get("impact_focus", "Not specified")
        }
        
        # =============================================
        # GENERATE QUERIES USING LLM
        # =============================================
        
        # Format the user prompt
        user_prompt = QUERY_EXPANSION_USER_PROMPT.format(**prompt_params)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": QUERY_EXPANSION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get LLM provider (using gpt-5-mini for query expansion)
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        # Use gpt-5-mini for query expansion
        if provider_type == ModelProvider.AZURE_OPENAI:
            # Use gpt-5-mini deployment from Azure configuration
            model_name = AZURE_DEPLOYMENTS.get(ModelUseCase.REPORT_GENERATION, "gpt-5-mini")
            logger.info(f"Using Azure OpenAI gpt-5-mini for query expansion (model: {model_name})")
        else:
            # Use OpenAI model
            model_name = "gpt-4.1-mini"
            logger.info(f"Using OpenAI for query expansion (model: {model_name})")
        
        # Get legacy config for temperature and max_tokens if available
        llm_config = get_llm_config(state)
        
        # Use lower temperature for more precise, focused queries
        openai_config = llm_config.get("openai", {})
        temperature = 0.1  # Lower temperature for more deterministic, precise outputs
        max_tokens = 16000  # gpt-5-mini needs large token budget
        
        # Create LLMConfig with Azure OpenAI or OpenAI model
        if provider_type == ModelProvider.AZURE_OPENAI:
            logger.info(f"Query Expander using Azure OpenAI gpt-5-mini: {model_name}")
            llm_config_obj = LLMConfig(
                model_name=model_name,  # Azure deployment name
                temperature=temperature,
                max_tokens=max_tokens,
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            logger.info(f"Query Expander using OpenAI model: {model_name}")
            llm_config_obj = LLMConfig(
                model_name=model_name,  # OpenAI model name
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=client_config.get("api_key")
            )
        
        # Use the AI module's OpenAI provider directly with proper config
        from src.mint.api.ai.providers import OpenAIProvider, LLMConfig as ProviderLLMConfig
        
        # Convert to the provider's expected config format
        provider_config = ProviderLLMConfig(
            provider_type="llm",
            provider_name="openai",  # Required field
            api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=llm_config_obj.model_name,
            temperature=llm_config_obj.temperature,
            max_tokens=llm_config_obj.max_tokens,
            api_key=llm_config_obj.api_key,  # Direct API key for immediate use
            azure_endpoint=getattr(llm_config_obj, 'azure_endpoint', None),
            api_version=getattr(llm_config_obj, 'api_version', None),
            base_url=getattr(llm_config_obj, 'base_url', None)  # For gpt-5-mini pattern
        )
        
        llm_provider = OpenAIProvider(provider_config)
        llm_provider.health_check()
        
        # Define tool for structured query generation
        query_tool = {
            "type": "function",
            "function": {
                "name": "generate_search_queries",
                "description": "Generate search queries for problem discovery",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of 10-15 search queries",
                            "minItems": 10,
                            "maxItems": 15
                        }
                    },
                    "required": ["queries"]
                }
            }
        }
        
        # Call LLM with tool and monitor usage
        logger.info("Calling LLM for query generation")
        
        # Record start time for monitoring
        llm_start_time = datetime.now()
        
        try:
            response = await llm_provider.generate_responses_with_tools(messages, [query_tool])
            llm_end_time = datetime.now()
            
            # Fire-and-forget monitoring (async, non-blocking)
            monitoring = get_monitoring_service()
            
            # Create monitoring context
            monitor_context = AIUsageContext(
                user_id=state.get("user_id"),
                tenant_id=state.get("tenant_id"),
                team_id=state.get("team_id"),
                project_id=state.get("project_id"),
                feature_id="pgen_query_expansion",
                workflow_name="problem_generator_workflow",
                step_name="query_expander",
                environment="prod",
                request_id=state.get("job_id")
            )
            
            # Extract token usage from response
            usage = getattr(response, 'usage', {}) or {}
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = usage.get('total_tokens')
            
            # Record usage asynchronously
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=model_name,
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
            
            # Record error asynchronously
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=state.get("user_id"),
                tenant_id=state.get("tenant_id"),
                team_id=state.get("team_id"),
                project_id=state.get("project_id"),
                feature_id="pgen_query_expansion",
                workflow_name="problem_generator_workflow",
                step_name="query_expander",
                environment="prod",
                request_id=state.get("job_id")
            )
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            raise  # Re-raise to maintain normal error handling
        
        if not response or not response.arguments:
            raise ValueError("Failed to generate queries from LLM")
        
        generated_queries = response.arguments.get("queries", [])
        
        if len(generated_queries) < 10:
            logger.warning(f"Only {len(generated_queries)} queries generated, expected 10-15")
        
        # =============================================
        # ENHANCE QUERIES WITH PARAMETER-BASED TEMPLATES
        # =============================================
        
        # Add some template-based queries to ensure coverage
        template_queries = []
        
        # Pain keyword pool for template generation
        pain_keywords = [
            "lack of", "shortage of", "high cost of", "prevents", "causes", 
            "hampers", "restricts", "delays", "worsens", "inadequate", 
            "insufficient", "barriers to", "challenges in", "limited access to", 
            "poor quality", "unreliable"
        ]
        
        # Get first few values from each parameter for template generation (optimized to 6 core parameters)
        industries = params.get("industry", [])[:2]
        geographies = params.get("geography", [])  # Single geography selection
        impact_focus = params.get("impact_focus", [])[:2]
        target_customers = params.get("target_customer", [])[:2]
        
        # Get product types for template generation
        product_types = params.get("product_type", [])[:2]
        if not product_types:  # Fallback if product type is missing
            product_types = ["product", "solution"]
        
        # Generate template queries with mandatory industry + geography + product type + pain keyword
        # Since geography is now single selection, use it directly
        selected_geography = geographies[0] if geographies else "Africa"
        for industry in industries:
                for product in product_types[:1]:  # Just use first product type for each combo
                    # Select different pain keywords for variety
                    pain1 = random.choice(pain_keywords)
                    pain2 = random.choice([p for p in pain_keywords if p != pain1])
                    
                    # Basic templates with industry + geography + product type + pain keyword
                    template_queries.extend([
                        f"{pain1} {industry} {product} in {selected_geography}",
                        f"{industry} {product} {pain2} {selected_geography}"
                    ])
                
                # Add time-sensitive queries for current relevance
                if len(template_queries) < 8:  # Add time filter for some queries
                    product = product_types[0] if product_types else "product"
                    template_queries.append(f"{industry} {product} {random.choice(pain_keywords)} {selected_geography} 2024..2025")
        
        # Add impact-focused queries for ~50% of templates
        for focus in impact_focus:
            for industry in industries[:1]:  # Just first industry
                    product = product_types[0] if product_types else "product"
                    template_queries.append(
                        f"{random.choice(pain_keywords)} {industry} {product} for {focus} in {selected_geography}"
                    )
        
        # Add target customer focused queries
        if target_customers:
            customer = target_customers[0]
            geo = geographies[0] if geographies else "Africa"
            industry = industries[0] if industries else "business"
            product = product_types[0] if product_types else "product"
            template_queries.append(f"{random.choice(pain_keywords)} {customer} access to {product} in {industry} {geo}")
        
        # Combine and deduplicate queries
        all_queries = generated_queries + template_queries
        unique_queries = []
        seen = set()
        
        for query in all_queries:
            query_clean = query.lower().strip()
            # Ensure query has industry AND geography AND (pain keyword OR product type) AND is not too long
            if query_clean not in seen and len(query.split()) >= 3 and len(query.split()) <= 30:
                # Verify query has at least one pain keyword
                has_pain_keyword = any(pain in query_clean for pain in [p.lower() for p in pain_keywords])
                
                # Use SEMANTIC matching for industry and geography (more flexible)
                has_industry = _semantic_industry_match(query_clean, industries)
                has_geography = _semantic_geography_match(query_clean, selected_geography)
                
                # Check product type (can be flexible)
                has_product_type = any(prod.lower() in query_clean for prod in product_types)
                
                # RELAXED FILTERING: Industry + Geography are MANDATORY
                # At least ONE of (pain keyword OR product type) must be present
                # This trusts the LLM-generated queries more while ensuring relevance
                if has_industry and has_geography and (has_pain_keyword or has_product_type):
                    seen.add(query_clean)
                    unique_queries.append(query)
                    logger.debug(f"Query passed filter: {query[:50]}... (industry={has_industry}, geo={has_geography}, pain={has_pain_keyword}, product={has_product_type})")
                else:
                    logger.debug(f"Query filtered out: {query[:50]}... (industry={has_industry}, geo={has_geography}, pain={has_pain_keyword}, product={has_product_type})")
        
        # Ensure we have between 12-15 queries
        if len(unique_queries) < 12:
            logger.warning(f"Only {len(unique_queries)} unique queries after filtering, expected 12-15")
            # Add any remaining original queries to reach minimum 12
            # Since LLM was given strict instructions, trust its output more
            for query in generated_queries:
                if len(unique_queries) >= 12:
                    break
                query_clean = query.lower().strip()
                if query_clean not in seen:
                    # For fallback queries, only require geography match (most critical)
                    if _semantic_geography_match(query_clean, selected_geography):
                        seen.add(query_clean)
                        unique_queries.append(query)
                        logger.debug(f"Fallback query added (geo match only): {query[:50]}...")
            
            # If still not enough, add remaining LLM queries without filtering
            # The LLM was given strict instructions, so we trust its output
            for query in generated_queries:
                if len(unique_queries) >= 12:
                    break
                query_clean = query.lower().strip()
                if query_clean not in seen:
                    seen.add(query_clean)
                    unique_queries.append(query)
                    logger.debug(f"Fallback query added (trusting LLM): {query[:50]}...")
        
        # Trim to maximum 15 queries if we have more
        final_queries = unique_queries[:15]
        
        # If we have more than 12 but less than 15, that's perfect
        logger.info(f"Final query count: {len(final_queries)} (target: 12-15)")
            
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["queries"] = final_queries
        
        # Add processing metrics
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        query_metrics = {
            "llm_generated_count": len(generated_queries),
            "template_generated_count": len(template_queries),
            "final_query_count": len(final_queries),
            "processing_time_ms": processing_time,
            "model_used": model_name
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["query_expander"] = query_metrics
        
        # Log results
        logger.info(f"Query expansion completed successfully")
        logger.info(f"Generated {len(final_queries)} unique search queries")
        
        # Verify all queries have industry, geography and pain keywords
        for i, query in enumerate(final_queries):
            logger.info(f"Query {i+1}: {query} ({len(query)} chars, {len(query.split())} words)")
        
        # Store in state
        state["search_queries"] = final_queries
        state["query_count"] = len(final_queries)
        
        return state
        
    except Exception as e:
        error_msg = f"Query expansion failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state
