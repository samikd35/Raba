import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from src.mint.schemas.schemas import Fact, ResearchSpec
from src.mint.utils.config import get_config
from src.mint.agents.agent_config import get_agent_config, get_llm_config, get_search_config, get_hybrid_search_strategy
from src.mint.agents.report_templates import INDUSTRY_REPORT_PROMPT
from src.mint.agents.enhanced_report_parser import get_enhanced_parser, ReportParsingError
from src.mint.agents.json_validator import get_validator, validate_json_response, generate_report_with_validation, INDUSTRY_REPORT_SCHEMA
from src.mint.api.ai.providers import (
    LLMProvider,
    OpenAIProvider,
    GeminiProvider,
    ProviderError
)
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.models import (
    ModelProvider,
    ModelUseCase
)
from src.mint.api.ai.config import (
    get_client_config,
    get_provider_with_fallback
)
from src.mint.providers.search import (
    BraveSearchProvider,
    TavilySearchProvider,
    SerperSearchProvider,
    SearchConfig,
    SearchProviderError,
    SearchProvider,
    SearchResult
)
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext


class SourceDocument(BaseModel):
    """Extracted content from a source URL."""
    title: str
    url: str
    source: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    storage_uri: Optional[str] = None
    relevance_score: float = 0.0  # Relevance score from 0.0 to 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata for reference tracking
    trust_score: float = 0.0      # Trust score from 0.0 to 1.0

from src.mint.utils.tracing import traceable
import httpx


@traceable(name="_execute_search")
async def _execute_search(search_queries: List[str], state: Dict[str, Any], max_sources: int = 5) -> List[SearchResult]:
    all_results = []
    seen_urls = set()
    
    # Define priority source patterns with categorization
    priority_sources = [
        # Tier 1: Official/Government sources (highest authority)
        r'.*\.gov(\.\w+)?$',  # Government sites (any country)
        r'.*\.mil$',          # Military domains
        r'.*\.int$',          # International organizations
        r'worldbank\.org',    # World Bank
        r'imf\.org',          # International Monetary Fund
        r'wto\.org',          # World Trade Organization
        r'.*\.un\.org$',      # United Nations and its agencies
        r'.*\.who\.int$',     # World Health Organization
        r'europa\.eu',        # European Union
        r'oecd\.org',         # Organization for Economic Cooperation and Development
        
        # Tier 2: Academic and Research Institutions
        r'.*\.edu$',          # US educational institutions
        r'.*\.ac\.[a-z]{2}$', # Academic institutions with country codes
        r'.*\.edu\.[a-z]{2}$',# Educational domains with country codes
        
        # Tier 3: Non-profit/NGO organizations
        r'.*\.org$',          # Non-profit organizations
    ]
    
    # Define diverse source patterns to ensure variety
    diverse_sources = [
        # Research and Academic Publications
        r'.*\.researchgate\.net$', # ResearchGate
        r'.*\.academia\.edu$',    # Academia
        r'.*\.sciencedirect\.com$', # Science Direct
        r'.*\.springer\.com$',    # Springer
        r'.*\.wiley\.com$',      # Wiley
        r'.*\.jstor\.org$',      # JSTOR
        r'.*\.ieee\.org$',       # IEEE
        r'.*\.acm\.org$',        # ACM
        r'.*\.sciencemag\.org$', # Science Magazine
        r'.*\.nature\.com$',     # Nature
        r'.*\.lancet\.com$',     # The Lancet
        
        # Comprehensive Data Sources
        r'statista\.com$',       # Statista - statistics
        r'kaggle\.com$',         # Kaggle - datasets
        r'crunchbase\.com$',     # Crunchbase - company data
        r'bloomberg\.com$',      # Bloomberg - financial data
        r'marketwatch\.com$',    # MarketWatch
        r'morningstar\.com$',    # Morningstar - investment research
        
        # News Media
        r'reuters\.com$',        # Reuters
        r'apnews\.com$',         # Associated Press
        r'bbc\.(co\.uk|com)$',   # BBC
        r'ft\.com$',             # Financial Times
        r'economist\.com$',      # The Economist
        r'wsj\.com$',            # Wall Street Journal
        r'bloomberg\.com$',      # Bloomberg 
        r'cnbc\.com$',           # CNBC
        r'aljazeera\.com$',      # Al Jazeera
        
        # Industry Analysis
        r'mckinsey\.com$',       # McKinsey
        r'bcg\.com$',            # Boston Consulting Group
        r'gartner\.com$',        # Gartner
        r'forrester\.com$',      # Forrester
        r'idc\.com$',            # IDC
        r'pwc\.com$',            # PwC
        r'deloitte\.com$',       # Deloitte
        r'kpmg\.com$',           # KPMG
        r'ey\.com$',             # Ernst & Young
        
        # Tech Analysis and Reviews
        r'techcrunch\.com$',      # TechCrunch
        r'wired\.com$',          # Wired
        r'cnet\.com$',           # CNET
        r'zdnet\.com$',          # ZDNet
        r'theverge\.com$',       # The Verge
    ]
    
    search_config = get_search_config(state) if state else get_config().get_search_config()
    provider_name = search_config.get('provider', 'tavily')
    
    search_providers = []
    if provider_name.lower() == 'tavily':
        try:
            tavily_config = search_config.get('tavily', {})
            api_key_env_var = tavily_config.get('api_key_env_var', 'TAVILY_API_KEY')
            max_results = min(tavily_config.get('max_results', 5), max_sources)
            search_depth = tavily_config.get('search_depth', 'advanced')
            include_domains = tavily_config.get('include_domains', [])
            exclude_domains = tavily_config.get('exclude_domains', [])
            
            # Create a proper search config object for Tavily
            # SearchConfig is already imported at the top of the file
            search_provider_config = SearchConfig(
                provider_name="tavily",
                api_key_env_var=api_key_env_var
            )
            # Apply additional settings through the provider itself
            provider = TavilySearchProvider(search_provider_config)
            provider.max_results = max_results
            if hasattr(provider, 'search_depth'):
                provider.search_depth = search_depth
            if hasattr(provider, 'include_domains'):
                provider.include_domains = include_domains
            if hasattr(provider, 'exclude_domains'):
                provider.exclude_domains = exclude_domains
            search_providers.append(provider)
            logger.info(f"Initialized Tavily search provider with {max_results} max results")
        except SearchProviderError as e:
            logger.warning(f"Failed to initialize Tavily search provider: {e}")
    
    elif provider_name.lower() == 'brave':
        try:
            brave_config = search_config.get('brave', {})
            api_key_env_var = brave_config.get('api_key_env_var', 'BRAVE_API_KEY')
            max_results = min(brave_config.get('max_results', 5), max_sources)
            
            # Create search provider config object
            search_provider_config = SearchConfig(
                provider_name="brave",
                api_key_env_var=api_key_env_var
            )
            
            # Set the number of results directly on the config
            search_provider_config.num_results = max_results
            
            # Create the provider with the config
            provider = BraveSearchProvider(config=search_provider_config)
            search_providers.append(provider)
            logger.info(f"Initialized Brave search provider with {max_results} max results")
        except SearchProviderError as e:
            logger.warning(f"Failed to initialize Brave search provider: {e}")
    
    elif provider_name.lower() == 'serper':
        try:
            serper_config = search_config.get('serper', {})
            api_key_env_var = serper_config.get('api_key_env_var', 'SERPER_API_KEY')
            max_results = min(serper_config.get('max_results', 5), max_sources)
            
            # Create search provider config object
            search_provider_config = SearchConfig(
                provider_name="serper",
                api_key_env_var=api_key_env_var
            )
            
            # Set the number of results directly on the config
            search_provider_config.num_results = max_results
            
            # Create the provider with the config
            provider = SerperSearchProvider(config=search_provider_config)
            search_providers.append(provider)
            logger.info(f"Initialized Serper search provider with {max_results} max results")
        except SearchProviderError as e:
            logger.warning(f"Failed to initialize Serper search provider: {e}")
    
    if not search_providers:
        logger.warning("No valid search providers available")
    
    results_per_query = 1
    max_queries = min(len(search_queries), 5)
    
    # Helper function to check source types and assign priority scores
    def get_priority_score(url) -> tuple:
        # Convert URL to string if it's a HttpUrl object
        url_str = str(url)
        # Extract domain from URL for better pattern matching
        domain = re.sub(r'^https?://(www\.)?', '', url_str)
        domain = re.sub(r'/.*$', '', domain)
        
        # Default values
        priority_score = 0
        source_type = "Other"
        diversity_score = 0
        
        # Debug info
        logger.debug(f"Processing URL: {url_str}, extracted domain: {domain}")
        
        # Check against priority sources
        for i, pattern in enumerate(priority_sources):
            if re.search(pattern, domain, re.IGNORECASE):
                # Higher score for higher priority patterns
                priority_score = len(priority_sources) - i
                
                # Determine source type based on our tier system
                if i < 10:  # Tier 1: Official/Government sources
                    source_type = "Government/International"
                elif i < 14:  # Tier 2: Academic institutions
                    source_type = "Academic/Organization"
                else:  # Tier 3: Non-profit/NGO
                    source_type = "Research/Statistics"
                
                logger.debug(f"Matched priority pattern {i}: {pattern} for {domain} -> {source_type}")
                break
        
        # Check for diversity sources
        for i, pattern in enumerate(diverse_sources):
            if re.search(pattern, domain, re.IGNORECASE):
                diversity_score = len(diverse_sources) - i
                
                # Only set source_type if not already set by priority sources
                if source_type == "Other":
                    if i < 11:  # Research and Academic Publications
                        source_type = "Academic/Research"
                    elif i < 17:  # Comprehensive Data Sources
                        source_type = "Data/Statistics"
                    elif i < 26:  # News Media
                        source_type = "News/Media"
                    elif i < 35:  # Industry Analysis
                        source_type = "Industry Analysis"
                    else:  # Tech Analysis
                        source_type = "Tech/Reviews"
                
                logger.debug(f"Matched diversity pattern {i}: {pattern} for {domain} -> {source_type}")
                break
        
        # Calculate a combined score that balances priority and diversity
        # Prioritize first but ensure some diverse sources are included
        combined_score = (priority_score * 2) + diversity_score
        
        return (combined_score, source_type)
    
    def add_unique_result(result):
        if result.url not in seen_urls:
            # Initialize metadata if not present
            result.metadata = result.metadata or {}
            
            # Get combined score and source type
            combined_score, source_type = get_priority_score(result.url)
            
            # Add scores and categorization to metadata
            result.metadata['combined_score'] = combined_score
            result.metadata['source_type'] = source_type
            
            seen_urls.add(result.url)
            all_results.append(result)
    
    # Get hybrid search strategy configuration
    hybrid_strategy = get_hybrid_search_strategy(state)
    search_config = get_search_config(state)
    
    # Initialize providers based on hybrid strategy
    providers = {}
    all_providers = []
    
    if hybrid_strategy['mode'] == 'hybrid':
        # Initialize primary provider (Tavily)
        try:
            tavily_config = SearchConfig(
                provider_name="tavily",
                api_key_env_var="TAVILY_API_KEY",
                num_results=search_config.get('tavily', {}).get('max_results', 20)
            )
            tavily_provider = TavilySearchProvider(config=tavily_config)
            providers['tavily'] = tavily_provider
            all_providers.append(tavily_provider)
            logger.info(f"Initialized Tavily (primary) with {search_config.get('tavily', {}).get('max_results', 20)} max results")
        except Exception as e:
            logger.error(f"Failed to initialize primary Tavily provider: {str(e)}")
        
        # Initialize secondary provider (Brave)
        try:
            brave_config = SearchConfig(
                provider_name="brave",
                api_key_env_var="BRAVE_API_KEY",
                num_results=search_config.get('brave', {}).get('max_results', 20)
            )
            brave_provider = BraveSearchProvider(config=brave_config)
            providers['brave'] = brave_provider
            all_providers.append(brave_provider)
            logger.info(f"Initialized Brave (secondary) with {search_config.get('brave', {}).get('max_results', 20)} max results")
        except Exception as e:
            logger.error(f"Failed to initialize secondary Brave provider: {str(e)}")
        
        # Initialize fallback provider (Serper)
        try:
            serper_config = SearchConfig(
                provider_name="serper",
                api_key_env_var="SERPER_API_KEY",
                num_results=search_config.get('serper', {}).get('max_results', 20)
            )
            serper_provider = SerperSearchProvider(config=serper_config)
            providers['serper'] = serper_provider
            logger.info(f"Initialized Serper (fallback) with {search_config.get('serper', {}).get('max_results', 20)} max results")
        except Exception as e:
            logger.warning(f"Failed to initialize fallback Serper provider: {str(e)}")
    else:
        # Legacy single provider mode
        provider_name = search_config.get('provider', 'tavily')
        try:
            if provider_name == 'tavily':
                config = SearchConfig(
                    provider_name="tavily",
                    api_key_env_var="TAVILY_API_KEY",
                    num_results=search_config.get('tavily', {}).get('max_results', 20)
                )
                all_providers.append(TavilySearchProvider(config=config))
            elif provider_name == 'brave':
                config = SearchConfig(
                    provider_name="brave",
                    api_key_env_var="BRAVE_API_KEY",
                    num_results=search_config.get('brave', {}).get('max_results', 20)
                )
                all_providers.append(BraveSearchProvider(config=config))
            elif provider_name == 'serper':
                config = SearchConfig(
                    provider_name="serper",
                    api_key_env_var="SERPER_API_KEY",
                    num_results=search_config.get('serper', {}).get('max_results', 20)
                )
                all_providers.append(SerperSearchProvider(config=config))
            logger.info(f"Initialized single {provider_name} provider")
        except Exception as e:
            logger.error(f"Failed to initialize {provider_name} provider: {str(e)}")
    
    # Make sure we have at least one provider
    if not all_providers:
        logger.warning("No search providers available, using empty results")
        return []
    
    # Take up to max_queries queries and create search tasks for each
    # Assign providers based on hybrid strategy
    search_tasks = []
    
    if hybrid_strategy['mode'] == 'hybrid' and len(providers) >= 2:
        # Hybrid mode: assign first N queries to primary, rest to secondary
        primary_count = hybrid_strategy['primary_query_count']
        primary_provider_name = hybrid_strategy['primary_provider']
        secondary_provider_name = hybrid_strategy['secondary_provider']
        fallback_provider_name = hybrid_strategy['fallback_provider']
        
        for i, query in enumerate(search_queries):
            if i >= max_queries:
                break
                
            # Assign provider based on query index
            if i < primary_count and primary_provider_name in providers:
                provider = providers[primary_provider_name]
                provider_type = "primary"
            elif secondary_provider_name in providers:
                provider = providers[secondary_provider_name]
                provider_type = "secondary"
            elif fallback_provider_name in providers:
                provider = providers[fallback_provider_name]
                provider_type = "fallback"
            elif all_providers:
                provider = all_providers[0]  # Use first available
                provider_type = "available"
            else:
                logger.error(f"No providers available for query {i+1}")
                continue
                
            search_tasks.append((provider, query))
            logger.info(f"Query {i+1} assigned to {provider.__class__.__name__} ({provider_type})")
    else:
        # Legacy round-robin mode
        for i, query in enumerate(search_queries):
            if i >= max_queries:
                break
            # Select provider using round-robin
            provider = all_providers[i % len(all_providers)]
            search_tasks.append((provider, query))
    
    logger.info(f"Created {len(search_tasks)} search tasks using {hybrid_strategy['mode']} strategy")
    logger.info(f"Configured max_sources: {max_sources}")
    
    # Execute searches with optimizations for paid tiers
    results_lists = []
    
    # Check if we should use concurrent execution for paid tiers
    use_concurrent = hybrid_strategy.get('concurrent_searches', False) and hybrid_strategy.get('paid_tier', True)
    use_rate_limiting = hybrid_strategy.get('rate_limiting', True)
    
    # Log execution mode
    logger.info(f"Execution mode: concurrent={use_concurrent}, rate_limiting={use_rate_limiting}")
    
    if use_concurrent:
        # Concurrent execution for paid tiers
        logger.info(f"Executing {len(search_tasks)} searches concurrently (paid tier optimization)")
        
        async def execute_search_task(i, provider, query):
            try:
                logger.info(f"Starting concurrent search {i+1}/{len(search_tasks)} using {provider.__class__.__name__}")
                results = await provider.search(query)
                logger.info(f"Concurrent search {i+1} returned {len(results)} results using {provider.__class__.__name__}")
                return results
            except Exception as e:
                logger.error(f"Concurrent search error from task {i+1}: {str(e)}")
                return []
        
        # Execute all searches concurrently
        search_coroutines = [
            execute_search_task(i, provider, query) 
            for i, (provider, query) in enumerate(search_tasks)
        ]
        results_lists = await asyncio.gather(*search_coroutines)
        
        # Add all results
        for results in results_lists:
            for result in results:
                add_unique_result(result)
    else:
        # Sequential execution (with optional rate limiting)
        for i, (provider, query) in enumerate(search_tasks):
            try:
                logger.info(f"Executing search {i+1}/{len(search_tasks)} using {provider.__class__.__name__}")
                # Execute the search with the provider
                results = await provider.search(query)
                results_lists.append(results)
                
                # Log the number of results from this query
                logger.info(f"Search task {i+1} returned {len(results)} results using {provider.__class__.__name__}")
                
                # Add all valid results from this query
                for result in results:
                    add_unique_result(result)
                    
                # Add delay only if rate limiting is enabled and not the last search
                if use_rate_limiting and i < len(search_tasks) - 1:
                    delay = 1.0  # 1 second delay between searches
                    logger.info(f"Adding {delay}s delay before next search (rate limiting enabled)")
                    await asyncio.sleep(delay)
                elif not use_rate_limiting:
                    logger.info(f"No rate limiting delay (paid tier optimization)")
                    
            except Exception as e:
                logger.error(f"Search error from task {i+1}: {str(e)}")
                results_lists.append([])  # Add empty list for failed search
    
    # Log the total number of results before filtering
    logger.info(f"Total raw search results before deduplication: {len(all_results)}")
    
    # First, sort all results by their combined score
    all_results.sort(key=lambda r: r.metadata.get('combined_score', 0) if r.metadata else 0, reverse=True)
    
    # Ensure source diversity by:  
    # 1. First take the top 66% based on combined score (prioritizing authority)
    # 2. Then add sources from diverse categories to fill the remaining slots
    if len(all_results) > max_sources:
        # Calculate how many results to keep based on pure score
        priority_count = int(max_sources * 0.66)
        priority_results = all_results[:priority_count]
        
        # Get remaining results, but organize by source type to ensure diversity
        remaining = all_results[priority_count:]
        source_types_needed = ["News", "Magazine/Journal", "Industry Analysis", "Research/Statistics"]
        
        diverse_results = []
        for source_type in source_types_needed:
            # Find results matching this source type
            matches = [r for r in remaining if r.metadata.get('source_type') == source_type]
            # Take up to ~8% from each diverse category (adjust as needed)
            diverse_results.extend(matches[:max(1, int(max_sources * 0.08))])
            if len(priority_results) + len(diverse_results) >= max_sources:
                break
        
        # If we still have room, add any remaining high-scored results
        if len(priority_results) + len(diverse_results) < max_sources:
            extra_needed = max_sources - len(priority_results) - len(diverse_results)
            remaining_sorted = sorted(remaining, key=lambda r: r.metadata.get('combined_score', 0) if r.metadata else 0, reverse=True)
            diverse_results.extend(remaining_sorted[:extra_needed])
        
        # Combine priority results with diverse results
        all_results = priority_results + diverse_results[:max_sources - len(priority_results)]
        logger.info(f"Selected {len(priority_results)} high-authority results and {len(all_results) - len(priority_results)} diverse results")
    
    from collections import Counter
    logger.info(f"Search completed with {len(all_results)} results from target of {max_sources}")
    logger.info(f"Source type breakdown: {Counter([r.metadata.get('source_type', 'Unknown') for r in all_results])}")
    
    return all_results


@traceable(name="_rank_sources")
async def _rank_sources(source_documents: List[SourceDocument], spec: ResearchSpec, state: Dict[str, Any] = None) -> List[SourceDocument]:
    """
    Rank sources based on relevance to research specification and content quality.
    
    This enhanced implementation considers both content relevance to the research topic
    and source trustworthiness. It utilizes rich metadata from the source extraction process
    and applies both automated scoring and LLM-based ranking.
    
    Args:
        source_documents: List of source documents with extracted content
        spec: Research specification with industry focus and key questions
        state: Current workflow state with configuration
        
    Returns:
        List of source documents sorted by combined relevance and trust scores
    """
    from urllib.parse import urlparse
    import re
    
    logger.info("===========================================")
    logger.info("Industry AGENT: Starting Source Ranking")
    logger.info(f"Number of sources to rank: {len(source_documents)}")
    
    # If no documents or in test mode, return as is
    if not source_documents or os.environ.get("MINT_TEST_MODE"):
        return source_documents
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # First pass: Apply automatic ranking based on metadata and content characteristics
    for doc in source_documents:
        # Initialize scores
        auto_relevance_score = 0.0
        auto_trust_score = 0.0
        
        # 1. Relevance scoring based on content and metadata
        # Check if key topics from spec appear in content
        if spec and spec.industry_focus:
            industry_terms = [term.lower() for term in spec.industry_focus]
            content_lower = doc.content.lower()
            
            # Count occurrences of industry terms in content
            term_occurrences = sum(content_lower.count(term) for term in industry_terms)
            if term_occurrences > 0:
                auto_relevance_score += min(0.3, term_occurrences / 100 * 0.3)  # Cap at 0.3
        
        # Check if content has structured data (tables, charts) which is valuable
        if doc.metadata.get("has_structured_data", False):
            auto_relevance_score += 0.1
        
        # Check content length - longer content often has more information
        content_length = doc.metadata.get("content_length", 0)
        if content_length > 1000:
            auto_relevance_score += 0.1
        
        # 2. Trust scoring based on source characteristics
        domain = doc.metadata.get("domain", "")
        
        # Check for reputable domains (academic, government, established publications)
        reputable_domain_patterns = [
            r'\.edu$', r'\.gov$', r'\.org$',
            r'(reuters|bloomberg|wsj|economist|forbes|ft\.com)'
        ]
        if any(re.search(pattern, domain, re.IGNORECASE) for pattern in reputable_domain_patterns):
            auto_trust_score += 0.3
        
        # Check for content quality indicators
        paragraphs_count = doc.metadata.get("paragraphs_count", 0)
        words_count = doc.metadata.get("words_count", 0)
        
        # Well-structured content with multiple paragraphs
        if paragraphs_count > 5:
            auto_trust_score += 0.1
        
        # Content with substantial information
        if words_count > 500:
            auto_trust_score += 0.1
        
        # Store automatic scores as preliminary values
        doc.relevance_score = min(0.7, auto_relevance_score)  # Cap at 0.7 to leave room for LLM scoring
        doc.trust_score = min(0.7, auto_trust_score)  # Cap at 0.7 to leave room for LLM scoring
    
    # Define the enhanced source ranking tool with more detailed parameters
    source_ranking_tool = {
        "type": "function",
        "function": {
            "name": "rank_industry_sources",
            "description": "Rank sources by relevance and trustworthiness for industry analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_rankings": {
                        "type": "array",
                        "description": "Rankings for each source with detailed evaluation",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL of the source"
                                },
                                "relevance_score": {
                                    "type": "number",
                                    "description": "Relevance score from 0.0 to 1.0 based on how relevant the content is to the industry research"
                                },
                                "trust_score": {
                                    "type": "number",
                                    "description": "Trust score from 0.0 to 1.0 based on source reliability and content quality"
                                },
                                "relevance_factors": {
                                    "type": "array",
                                    "description": "Specific factors contributing to relevance score",
                                    "items": {
                                        "type": "string"
                                    }
                                },
                                "key_insights": {
                                    "type": "array",
                                    "description": "Key insights or facts from this source that are relevant",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["url", "relevance_score", "trust_score"]
                        }
                    }
                },
                "required": ["source_rankings"]
            }
        }
    }
    
    # Prepare message for ranking
    system_message = """You are an expert industry and market research analyst.
    Evaluate and rank sources based on their relevance to the industry research specification and trustworthiness.
    For each source, provide:
    1. A relevance score (0.0-1.0) indicating how well it addresses the research needs
    2. A trust score (0.0-1.0) based on source reputation, content quality, and factual reliability
    """
    
    # Prepare content for each source (truncate to avoid token limits)
    source_summaries = []
    for doc in source_documents:
        # Truncate content to first 500 characters for ranking
        truncated_content = doc.content[:500] + "..." if len(doc.content) > 500 else doc.content
        source_summaries.append(f"URL: {doc.url}\nTitle: {doc.title}\nSource: {doc.source}\nExcerpt:\n{truncated_content}\n")
    
    # Build message for ranking
    separator = '-' * 40 + "\n"
    ranked_sources = separator.join(source_summaries)

    ranking_message = f"""
    Research Specification:
    Title: {spec.title}
    Description: {spec.description}
    Key Questions: {', '.join(spec.key_questions)}
    Geography Focus: {', '.join(spec.geography_focus)}
    Industry Focus: {', '.join(spec.industry_focus)}

    Sources to Rank:
    {'-' * 40}
    {ranked_sources}

    Rank these sources by relevance to the industry analysis and trustworthiness.
    For each source, provide a relevance score and trust score.
    """
    
    # Prepare message for ranking with improved prompt
    system_message = """You are an expert industry and market research analyst specializing in source evaluation.
    Your task is to deeply analyze content from various sources and evaluate them based on two key dimensions:
    
    1. RELEVANCE - How well the content addresses the specific industry research questions and topics.
       Consider factors like: industry-specific data, market trends, competitive insights, and technical depth.
       
    2. TRUSTWORTHINESS - The credibility and quality of the information provided.
       Consider factors like: source reputation, data quality, citation of evidence, and balanced reporting.
       
    For each source, provide:
    - Relevance score (0.0-1.0) - Higher scores for sources with detailed, specific information addressing research needs
    - Trust score (0.0-1.0) - Higher scores for reputable sources with verifiable, properly presented information
    - Relevance factors - List specific aspects of the content that are valuable to the research topic
    - Key insights - Extract 1-3 of the most important facts or insights from the source
    
    Prioritize sources that contain concrete data, research findings, or expert analysis over general information.
    """
    
    # Prepare source summaries with metadata for better context
    source_summaries = []
    for doc in source_documents:
        # Include metadata in summary for better context
        metadata_summary = []
        if doc.metadata.get("published_date"):
            metadata_summary.append(f"Published: {doc.metadata.get('published_date')}")
            
        if doc.metadata.get("author"):
            metadata_summary.append(f"Author: {doc.metadata.get('author')}")
            
        if doc.metadata.get("has_tables", False):
            metadata_summary.append("Contains tables/structured data")
            
        if doc.metadata.get("keywords"):
            metadata_summary.append(f"Key terms: {', '.join(doc.metadata.get('keywords')[:5])}")
            
            
        # Create a more informative summary with metadata context
        summary = f"URL: {doc.url}\n"
        summary += f"Title: {doc.title}\n"
        summary += f"Source: {doc.source}\n"
        if metadata_summary:
            summary += f"Metadata: {', '.join(metadata_summary)}\n"
            
        
        # Extract most meaningful content sections (focus on beginning and any structured data)
        content_preview = ""
        
        # First include any detected structured data which is highly valuable
        if doc.metadata.get("has_tables", False) and "TABLE" in doc.content:
            # Find and include table sections (limited to first table)
            table_match = re.search(r"(TABLE \d+:[\s\S]+?)(?=TABLE \d+:|$)", doc.content)
            if table_match:
                content_preview += f"\n[STRUCTURED DATA]\n{table_match.group(1)}\n"
                
        
        # Include beginning of content which often has key information
        content_parts = doc.content.split('\n\n')
        # Take first few paragraphs, prioritizing those with industry terms
        selected_parts = []
        
        # Look for industry terms in content if spec is available
        industry_terms = []
        if spec and spec.industry_focus:
            industry_terms = [term.lower() for term in spec.industry_focus]
            
        # Select paragraphs with highest relevance
        for i, part in enumerate(content_parts[:10]):  # Look in first 10 paragraphs
            if part and len(part) > 50:  # Skip very short fragments
                # Prioritize paragraphs with industry terms
                if industry_terms and any(term in part.lower() for term in industry_terms):
                    selected_parts.append(part)
                elif len(selected_parts) < 3:  # Take up to 3 paragraphs if not enough with terms
                    selected_parts.append(part)
                    
                if len(selected_parts) >= 5:  # Limit to 5 paragraphs maximum
                    break
                    
        content_preview += "\n\n".join(selected_parts)
        
        # Truncate if still too long
        if len(content_preview) > 1000:
            content_preview = content_preview[:997] + "..."
            
            
        summary += f"Content Excerpt:\n{content_preview}\n"
        
        source_summaries.append(summary)
    
    # Build message for ranking with more specific instructions
    industry_focus = ", ".join(spec.industry_focus) if spec and spec.industry_focus else "specified industries"
    geography_focus = ", ".join(spec.geography_focus) if spec and spec.geography_focus else "relevant geographies"
    
    separator = '-' * 80 + "\n"
    ranked_sources = separator.join(source_summaries)

    ranking_message = f"""
    RESEARCH FOCUS:
    Title: {spec.title if spec else 'Industry Analysis'}
    Industry Focus: {industry_focus}
    Geography Focus: {geography_focus}
    Key Questions: {', '.join(spec.key_questions) if spec and spec.key_questions else 'Industry trends, market conditions, competitive analysis'}

    SOURCES TO ANALYZE AND RANK:
    {'-' * 80}
    {ranked_sources}

    For each source, provide:
    1. A relevance score (0.0-1.0) indicating how valuable this content is for the research focus
    2. A trust score (0.0-1.0) indicating the credibility and quality of the information
    3. 2-3 specific relevance factors that make this source valuable (or not)
    4. 1-3 key insights or facts extracted from the source that are most relevant
    """
    

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": ranking_message}
    ]
    
    # Log ranking start
    logger.info(f"Sending {len(source_documents)} sources for LLM-based relevance ranking")
    
    # Prepare monitoring context
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_industry",
        workflow_name="pv_report_workflow",
        step_name="source_ranking",
        environment="prod"
    )
    started_at = datetime.now()
    
    try:
        # Call LLM with the ranking tool
        response = await llm.generate_responses_with_tools(messages, [source_ranking_tool])
        rankings = {item["url"]: item for item in response.arguments["source_rankings"]}
        
        # Record successful AI usage
        finished_at = datetime.now()
        usage = getattr(response, 'usage', {}) or {}
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="azure_openai",
                model_name=getattr(response, 'model', 'gpt-5-mini'),
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                extra_metadata={"step": "source_ranking", "sources_ranked": len(source_documents)}
            )
        )
        
        # Update document scores and metadata with LLM ranking results
        for doc in source_documents:
            if doc.url in rankings:
                ranking = rankings[doc.url]
                
                # Combine automatic scoring with LLM scoring (weighted average)
                auto_weight = 0.3  # Give 30% weight to automatic scoring
                llm_weight = 0.7   # Give 70% weight to LLM judgment
                
                # Get LLM scores
                llm_relevance = ranking["relevance_score"]
                llm_trust = ranking["trust_score"]
                
                # Combine scores
                doc.relevance_score = (doc.relevance_score * auto_weight) + (llm_relevance * llm_weight)
                doc.trust_score = (doc.trust_score * auto_weight) + (llm_trust * llm_weight)
                
                # Store additional insights in metadata
                if "relevance_factors" in ranking:
                    doc.metadata["relevance_factors"] = ranking["relevance_factors"]
                    
                if "key_insights" in ranking:
                    doc.metadata["key_insights"] = ranking["key_insights"]
                    
        # Sort documents by combined score (relevance * trust)
        ranked_documents = sorted(source_documents, key=lambda d: d.relevance_score * d.trust_score, reverse=True)
        
        # Log ranking results
        logger.info(f"Completed source ranking, top source: {ranked_documents[0].title if ranked_documents else 'None'}")
        
        if ranked_documents:
            logger.info(f"Top source score: relevance={ranked_documents[0].relevance_score:.2f}, trust={ranked_documents[0].trust_score:.2f}")
            
            logger.info(f"Score range: top={ranked_documents[0].relevance_score * ranked_documents[0].trust_score:.2f}, "
                        f"bottom={ranked_documents[-1].relevance_score * ranked_documents[-1].trust_score:.2f}")
                  
    except Exception as e:
        # Record error AI usage
        finished_at = datetime.now()
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="azure_openai",
                model_name="gpt-5-mini",
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                error_type=type(e).__name__,
                extra_metadata={"step": "source_ranking", "error": str(e)[:200]}
            )
        )
        
        # Fallback to basic ranking if LLM ranking fails
        logger.error(f"Error in LLM-based ranking: {e}")
        
        logger.info("Falling back to basic metadata-based ranking")
        
        
        # Sort by automatically calculated scores
        ranked_documents = sorted(source_documents, key=lambda d: d.relevance_score * d.trust_score, reverse=True)
        
    return ranked_documents


@traceable(name="_extract_facts")
async def _extract_facts(ranked_documents: List[SourceDocument], spec: ResearchSpec, state: Dict[str, Any] = None) -> List["EnhancedFact"]:
    logger.info("Starting industry fact extraction process")
    logger.info(f"Number of documents to process: {len(ranked_documents)}")
    logger.info(f"First document title: {ranked_documents[0].title if ranked_documents else 'No documents'}")
    logger.info(f"First document content length: {len(ranked_documents[0].content) if ranked_documents else 0}")
    
    start_time = time.time()
    
    if not ranked_documents:
        return []
    
    llm, _, _ = _get_llm_provider(state)
    fact_extraction_tool = {
        "type": "function",
        "function": {
            "name": "extract_industry_facts",
            "description": "Extract structured facts from content related to industry analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "facts": {
                        "type": "array",
                        "description": "Extracted facts from the document",
                        "items": {
                            "type": "object",
                            "properties": {
                                "statement": {
                                    "type": "string",
                                    "description": "A concise, factual statement (1-2 sentences)"
                                },
                                "industry_aspect": {
                                    "type": "string",
                                    "description": "The industry aspect this fact relates to (regulations and challenges are covered by PESTEL)",
                                    "enum": ["Market Size", "Growth Rate", "Competitors", "Market Share", "Trends", "Opportunities", "Technology", "Consumer Behavior", "Pricing", "Supply Chain", "Distribution Channel", "Market Segmentation"]
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "Confidence score from 0.0 to 1.0 about the accuracy of this fact"
                                }
                            },
                            "required": ["statement"]
                        }
                    }
                },
                "required": ["facts"]
            }
        }
    }
    
    all_facts = []
    extraction_tasks = []
    
    # Prepare monitoring context for fact extraction
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_industry",
        workflow_name="pv_report_workflow",
        step_name="fact_extraction",
        environment="prod"
    )
    
    async def process_document(doc):
        logger.info(f"Processing document: {doc.title[:50]}...")
        logger.info(f"Document content length: {len(doc.content)}")
            
        system_message = """You are an expert industry analyst specializing in extracting accurate facts from market research content.
Extract only factual information that is explicitly stated in the document. Do not make assumptions or extrapolations.
Each fact should be a concise statement (1-2 sentences) that captures a single piece of information.

IMPORTANT: Distribute facts across MULTIPLE diverse industry aspects from the provided categories.
Aim to use at least 5-7 different aspects to ensure comprehensive coverage of the industry landscape.
Avoid concentrating all facts under a single category - analyze the content from multiple business perspectives.

NOTE: Skip regulatory/political issues and challenges - those are covered by PESTEL analysis.
Focus on market dynamics, competition, opportunities, and operational aspects.
"""
            
        user_message = f"""
        Research Specification:
        Title: {spec.title}
        Description: {spec.description}
        Industry Focus: {', '.join(spec.industry_focus)}
        Geography Focus: {', '.join(spec.geography_focus)}

        Source Document:
        Title: {doc.title}
        URL: {doc.url}
        Source: {doc.source}

        Content:
        {doc.content[:8000]}

        Extract factual statements from this content related to the industry research specification.
        For each fact:
        1. Create a concise, well-formed statement (1-2 sentences)
        2. Assign it to the appropriate industry_aspect from the enum (use MULTIPLE different aspects)
        3. Provide a confidence score (0.0-1.0) based on how explicitly it is stated
        
        IMPORTANT: Categorize facts across MULTIPLE aspects (Market Size, Growth Rate, Competitors, 
        Trends, Opportunities, Technology, Supply Chain, etc.). Don't put all facts in one category.
        SKIP regulatory/political issues and challenges - PESTEL analysis covers those.
        """
            
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        fact_started_at = datetime.now()
        response = await llm.generate_responses_with_tools(messages, [fact_extraction_tool])
        doc_facts = response.arguments.get("facts", [])
        
        # Record fact extraction AI usage
        fact_finished_at = datetime.now()
        usage = getattr(response, 'usage', {}) or {}
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="azure_openai",
                model_name=getattr(response, 'model', 'gpt-5-mini'),
                operation_type="responses_api",
                started_at=fact_started_at,
                finished_at=fact_finished_at,
                status="success",
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                extra_metadata={"step": "fact_extraction", "document": doc.title[:50], "facts_extracted": len(doc_facts)}
            )
        )
        
        document_enhanced_facts = []
        
        for fact in doc_facts:
            if not fact.get("statement") or len(fact.get("statement", "")) < 10:
                continue
                
            # Create a unique reference ID that we'll preserve throughout the pipeline
            fact_ref_id = f"ref-{uuid.uuid4().hex[:8]}"
            
            enhanced_fact = EnhancedFact(
                content=fact["statement"],
                source_url=doc.url,  # Ensure URL is preserved
                source_title=doc.title,
                confidence=fact["confidence"],
                category=fact["industry_aspect"],
                extracted_at=datetime.now().isoformat(),
                industry_aspect=fact["industry_aspect"],
                reference_id=fact_ref_id  # Assign the unique reference ID
            )
            document_enhanced_facts.append(enhanced_fact)
            all_facts.append(enhanced_fact)
                    
        logger.info(f"Extracted {len(document_enhanced_facts)} facts from {doc.title[:30]}...")
        return document_enhanced_facts
    
    # Process documents in batches to avoid API rate limits (same as PESTEL agent)
    BATCH_SIZE = 3  # Process 3 documents at a time
    logger.info(f"Processing {len(ranked_documents)} documents in batches of {BATCH_SIZE} to avoid rate limits")
    
    for i in range(0, len(ranked_documents), BATCH_SIZE):
        batch = ranked_documents[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(ranked_documents) + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
        
        # Create tasks for this batch
        batch_tasks = [process_document(doc) for doc in batch]
        
        # Execute batch with exception handling
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Count successful extractions
        batch_fact_count = sum(len(r) if isinstance(r, list) else 0 for r in batch_results)
        logger.info(f"✅ Batch {batch_num} complete: extracted {batch_fact_count} facts")
        
        # Log any exceptions
        for idx, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Document {i+idx} failed: {result}")
    
    end_time = time.time()
    execution_time = end_time - start_time  
    logger.info(f"Industry fact extraction completed in {execution_time:.2f} seconds")
    logger.info(f"Total facts extracted: {len(all_facts)}")
    
    if not all_facts:
        logger.warning("No facts were extracted from documents")
    
    return all_facts


@traceable(name="_check_consistency")
async def _check_consistency(facts: List["EnhancedFact"], spec: ResearchSpec, state: Dict[str, Any] = None) -> List["EnhancedFact"]:
    """
    Check for inconsistencies among extracted facts and resolve conflicts.
    
    Args:
        facts: List of extracted facts
        spec: Research specification
        state: The current workflow state
        
    Returns:
        List of validated facts with inconsistencies resolved and confidence scores updated
    """
    logger.info("Starting fact consistency check")
    logger.info(f"Number of facts to validate: {len(facts)}")
    
    # If fewer than 2 facts, no consistency check needed
    if len(facts) < 2:
        return facts
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Prepare monitoring context for consistency check
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_industry",
        workflow_name="pv_report_workflow",
        step_name="fact_consistency_check",
        environment="prod"
    )
    
    # Group facts by industry aspect to check within similar categories
    aspect_groups = {}
    
    for fact in facts:
        aspect = getattr(fact, 'industry_aspect', 'General')
        if aspect not in aspect_groups:
            aspect_groups[aspect] = []
        aspect_groups[aspect].append(fact)
    
    logger.info(f"Grouped facts into {len(aspect_groups)} industry aspects")
    
    # Define consistency checking tool
    consistency_tool = {
        "type": "function",
        "function": {
            "name": "validate_facts_consistency",
            "description": "Check a set of facts for consistency and assign confidence scores",
            "parameters": {
                "type": "object",
                "properties": {
                    "validated_facts": {
                        "type": "array",
                        "description": "Facts with validation results",
                        "items": {
                            "type": "object",
                            "properties": {
                                "reference_id": {
                                    "type": "string",
                                    "description": "Reference ID of the original fact"
                                },
                                "is_consistent": {
                                    "type": "boolean",
                                    "description": "Whether the fact is consistent with other facts"
                                },
                                "confidence_score": {
                                    "type": "number",
                                    "description": "Updated confidence score from 0.0 to 1.0"
                                },
                                "validation_notes": {
                                    "type": "string",
                                    "description": "Any notes about validation or inconsistencies"
                                }
                            },
                            "required": ["reference_id", "is_consistent", "confidence_score"]
                        }
                    },
                    "inconsistencies": {
                        "type": "array",
                        "description": "List of detected inconsistencies",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fact_ids": {
                                    "type": "array",
                                    "description": "Reference IDs of conflicting facts",
                                    "items": {"type": "string"}
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Description of the inconsistency"
                                },
                                "resolution": {
                                    "type": "string",
                                    "description": "Proposed resolution based on source credibility"
                                }
                            },
                            "required": ["fact_ids", "description"]
                        }
                    }
                },
                "required": ["validated_facts", "inconsistencies"]
            }
        }
    }
    
    # Process each aspect separately to stay within context limits
    validated_facts = []
    inconsistencies = []
    
    for aspect, aspect_facts in aspect_groups.items():
        # Skip if too few facts to check consistency
        if len(aspect_facts) < 2:
            validated_facts.extend(aspect_facts)
            continue
        
        # Prepare system message
        system_message = f"""
        You are an expert industry analyst specializing in fact validation and consistency checking.
        Examine the provided facts about the {aspect} aspect of the industry for consistency and factual accuracy.
        
        For each fact:
        1. Verify its logical consistency with other facts in the same category
        2. Check for direct contradictions or inconsistencies with other facts
        3. Pay special attention to numerical claims, dates, statistics, and market information
        4. Adjust confidence scores based on consistency with other facts and source reliability
        5. Provide brief notes on any detected issues
        
        Identify any inconsistencies between facts, listing the conflicting facts and proposing a resolution.
        Facts from more reputable sources should be given higher confidence.
        """
        
        # Format facts for consistency checking
        formatted_facts = []
        for fact in aspect_facts:
            formatted_facts.append({
                "reference_id": fact.reference_id,
                "statement": fact.content,
                "source": fact.source_title,
                "url": fact.source_url,
                "current_confidence": fact.confidence
            })
        
        # Prepare user message
        user_message = f"""
        Research Specification:
        Title: {spec.title}
        Description: {spec.description}
        Industry Focus: {', '.join(spec.industry_focus)}
        Geography Focus: {', '.join(spec.geography_focus)}
        
        Industry Aspect: {aspect}
        
        Facts to validate (total: {len(formatted_facts)}):
        {json.dumps(formatted_facts, indent=2)}
        
        Check these facts for consistency and provide validation results, including any inconsistencies detected.
        """
        
        try:
            # Make API call with tool calling
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            consistency_started_at = datetime.now()
            response = await llm.generate_responses_with_tools(messages, [consistency_tool])
            validation_data = response.arguments
            
            # Record consistency check AI usage
            consistency_finished_at = datetime.now()
            usage = getattr(response, 'usage', {}) or {}
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider="azure_openai",
                    model_name=getattr(response, 'model', 'gpt-5-mini'),
                    operation_type="responses_api",
                    started_at=consistency_started_at,
                    finished_at=consistency_finished_at,
                    status="success",
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens'),
                    extra_metadata={"step": "fact_consistency_check", "aspect": aspect, "facts_checked": len(aspect_facts)}
                )
            )
            
            # Process validation results
            validation_results = validation_data.get("validated_facts", [])
            
            # Update the fact with validation results while preserving URLs and other metadata
            for fact in aspect_facts:
                for result in validation_results:
                    if getattr(fact, 'reference_id', 'unknown') == result.get('reference_id'):
                        original_confidence = getattr(fact, 'confidence', 0.5)
                        updated_confidence = result.get('confidence_score', original_confidence)
                        # Only allow confidence to decrease, not increase from validation
                        fact.confidence = min(original_confidence, updated_confidence)
                        fact.is_consistent = result.get('is_consistent', True)
                        fact.validation_notes = result.get('validation_notes', "")
                        
                        # Ensure source URLs and reference IDs are preserved
                        if not getattr(fact, 'source_url', None):
                            logger.warning(f"Missing source URL in fact: {fact.content[:50]}")
                        if not getattr(fact, 'reference_id', None):
                            fact.reference_id = f"ref-{uuid.uuid4().hex[:8]}"
                            logger.warning(f"Missing reference ID, generated new one: {fact.reference_id}")
                        break
                validated_facts.append(fact)
            
            # Record inconsistencies for reporting
            if "inconsistencies" in validation_data:
                inconsistencies.extend(validation_data["inconsistencies"])
                
        except Exception as e:
            logger.error(f"Consistency checking failed for {aspect} facts: {str(e)}")
            # In case of failure, keep all facts but log the error
            validated_facts.extend(aspect_facts)
    
    # Store inconsistencies in state for later use in report generation
    if state is not None and inconsistencies:
        if "industry_analysis" not in state:
            state["industry_analysis"] = {}
        state["industry_analysis"]["inconsistencies"] = inconsistencies
    
    logger.info(f"Consistency check complete. {len(validated_facts)} valid facts, {len(inconsistencies)} inconsistencies found")
    
    # Log information about inconsistencies found
    if inconsistencies:
        for inconsistency in inconsistencies[:3]:  # Log a few examples
            logger.debug(f"Inconsistency detected: {inconsistency.get('description', '')[:100]}...")
    
    return validated_facts


# DISABLED: LangSmith causes memory issues with large payloads (61MB+)
# if os.environ.get("LANGSMITH_API_KEY"):
#     from langsmith.run_helpers import traceable
# else:
def traceable(name=None):
        def decorator(func):
            return func
        return decorator

# Note: EnhancedFact class is now defined at the top of the file

# This would be imported from a search provider module in the full implementation
class SearchResult(BaseModel):
    """Search result from a search provider."""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    def __init__(self, **data):
        # Ensure timestamp is always set
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)

class ResearchEntities(BaseModel):
    """Extracted entities from a research specification."""
    industry_names: List[str]
    geography_names: List[str]
    timeframe: Optional[str] = None
    target_segments: List[str] = []
    key_topics: List[str] = []
    expected_output_sections: List[str] = []

class MiniReport(BaseModel):
    """
    Data model for standardized industry mini-report
    
    Contains structured industry analysis with supporting facts,
    organized sections, and strategic recommendations.
    """
    title: str = Field(..., description="Title of the industry analysis report")
    summary: str = Field(..., description="Executive summary of industry findings")
    analysis: List[Dict[str, Any]] = Field(default_factory=list, description="Structured analysis sections with subsections")
    recommendations: List[str] = Field(default_factory=list, description="Strategic recommendations based on industry analysis")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source references with numbers and URLs")
    
    def __init__(self, **data):
        super().__init__(**data)

    @classmethod
    def from_facts(cls, title: str, summary: str, analysis: List[Dict[str, Any]] = None, recommendations: List[str] = None):
        """Factory method to create a MiniReport with proper type conversions
        
        Args:
            title: The title of the industry report
            summary: Executive summary of findings
            analysis: Structured analysis sections with subsections
            recommendations: Strategic recommendations based on analysis
            
        Returns:
            MiniReport: A properly formatted industry mini report
        """
        return cls(
            title=title,
            summary=summary,
            analysis=analysis or [],
            recommendations=recommendations or []
        )

# Configure logging
logger = logging.getLogger(__name__)


# Extend the Fact model with additional metadata for internal use
class EnhancedFact(Fact):
    """
    Extended fact with source metadata and confidence score.
    
    This extends the base Fact model with additional metadata needed for
    fact validation, source tracking, and reference management throughout
    the research pipeline.
    """
    source_url: str
    source_title: str
    confidence: float = 0.7  # Default confidence
    source_date: Optional[str] = None  # Publication date if available
    source_author: Optional[str] = None  # Author if available
    reference_id: str = Field(default_factory=lambda: f"ref-{uuid.uuid4().hex[:8]}")  # Unique reference ID
    
    def get_citation_markdown(self) -> str:
        """
        Generate a properly formatted citation in markdown.
        
        Returns:
            Markdown citation with link to source
        """
        return f"[{self.source_title}]({self.source_url})"
    
    def get_citation_text(self) -> str:
        """
        Generate a properly formatted citation in plain text.
        
        Returns:
            Text citation with source information
        """
        citation = f"{self.source_title}"
        if self.source_author:
            citation = f"{self.source_author}, {citation}"
        if self.source_date:
            citation += f" ({self.source_date})"
        return citation

@traceable(name="run_industry_analysis")
async def run_industry_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run the industry analysis agent to generate industry analysis based on specifications"""
    # Just call the async implementation directly instead of using asyncio.run()
    return await _run_industry_analysis_async(state)


async def _run_industry_analysis_async(state: Dict[str, Any]) -> Dict[str, Any]:
    start_time = time.time()
    
    logger.info("==========================================")
    # Get agent-specific configuration    
    agent_config = get_agent_config(state, "industry")
    enabled = agent_config.get("enabled", True)
    search_queries_limit = agent_config.get('search_queries', 5)
    max_sources = agent_config.get('max_sources', 20)
    force_african_context = agent_config.get("force_african_context", True)
    
    if not enabled:
        logger.info("Industry Analysis agent disabled in config, skipping...")
        return state
        
    logger.info(f"Industry Analysis agent config: enabled={enabled}, search_queries={search_queries_limit}, max_sources={max_sources}, force_african_context={force_african_context}")
    
    # Get the user query from any available field
    user_query = state.get("initial_query", "") or state.get("question", "") or state.get("user_input", "")
    logger.info(f"Processing industry analysis for query: '{user_query}'")
    
    # Initialize variables
    spec = None
    
    # First, check for existing industry specification
    if state.get("industry_specification"):
        try:
            industry_spec_json = state.get("industry_specification")
            if isinstance(industry_spec_json, str):
                spec = ResearchSpec.parse_raw(industry_spec_json)
            elif isinstance(industry_spec_json, dict):
                spec = ResearchSpec.parse_obj(industry_spec_json)
            logger.info(f"Parsed industry specification from industry_specification")
        except Exception as e:
            logger.warning(f"Failed to parse industry_specification: {str(e)}")
    
    # If that fails, extract from master specification
    if not spec:
        try:
            # Check all possible locations for the master specification
            master_spec_data = None
            for key in ["master_specification", "specification", "research_spec"]:
                if key in state and state[key]:
                    master_spec_data = state[key]
                    logger.info(f"Found potential specification in {key}")
                    break
            
            if master_spec_data:
                # Handle string format (JSON serialized)
                if isinstance(master_spec_data, str):
                    try:
                        master_spec = json.loads(master_spec_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse {key} from JSON string")
                        master_spec = None
                else:
                    # Already a dict/object
                    master_spec = master_spec_data
                
                # Extract industry specification from master spec
                if isinstance(master_spec, dict):
                    # Try different possible paths to industry spec
                    if 'industry' in master_spec:
                        industry_spec = master_spec['industry']
                        logger.info("Found industry spec in master_spec['industry']")
                        spec = ResearchSpec.parse_obj(industry_spec)
                    elif 'specifications' in master_spec and 'industry' in master_spec['specifications']:
                        industry_spec = master_spec['specifications']['industry']
                        logger.info("Found industry spec in master_spec['specifications']['industry']")
                        spec = ResearchSpec.parse_obj(industry_spec)
        except Exception as e:
            logger.warning(f"Error accessing master specification: {str(e)}")
    
    # Check if we're in interactive mode
    interactive_mode = state.get("interactive_mode", False)

    # If we're in interactive mode and awaiting clarification, stop here
    if interactive_mode and state.get("awaiting_clarification", False):
        logger.error("Cannot run industry analysis while awaiting clarification")
        raise ValueError("Workflow sequence error: Industry analysis started before clarification completed")
    
    # Also check for user answers in interactive mode
    if interactive_mode and not state.get("user_answers") and state.get("clarification", {}).get("questions"):
        logger.error("Interactive mode requires user answers before industry analysis")
        raise ValueError("Workflow sequence error: Industry analysis started without user answers")
    
    # If still no spec, create a default one only if we're not in interactive mode
    if not spec:
        logger.error("No specification available for industry analysis")
        raise ValueError("Workflow sequence error: Industry analysis started without specification")
    
    entities = await _extract_key_entities(spec, state)
    logger.info(f"Extracted entities: {entities}")
    
    # Generate optimized search queries with link quotas
    query_data = await _generate_search_queries(spec, entities, search_queries_limit, state)
    optimized_queries = query_data["optimized_queries"]
    query_strings = query_data["query_strings"]
    
    logger.info(f"Generated {len(query_strings)} optimized search queries")
    
    # Store queries in state for debugging/logging
    if "debug" not in state:
        state["debug"] = {}
    state["debug"]["optimized_queries"] = json.dumps(optimized_queries)
    
    # Execute search with the query strings
    search_results = await _execute_search(query_strings, state, max_sources)
    logger.info(f"Search returned {len(search_results)} unique results")
    
    source_documents = await _extract_source_content(search_results)
    logger.info(f"Extracted content from {len(source_documents)} sources")
    
    ranked_documents = await _rank_sources(source_documents, spec, state)
    logger.info(f"Ranked {len(ranked_documents)} sources by relevance and trust")
    
    facts = await _extract_facts(ranked_documents, spec, state)
    logger.info(f"Extracted {len(facts)} facts from sources")
    
    validated_facts = await _check_consistency(facts, spec, state)
    logger.info(f"Validated {len(validated_facts)} facts after consistency check")
    
    # Generate standardized mini-report based on validated facts
    logger.info("Generating final standardized mini-report")
    mini_report = await _compose_standardized_industry_report(validated_facts, spec, state)
    
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Completed industry analysis in {execution_time:.2f} seconds")
    
    # The mini_report from standardized generator already has the correct format
    # No conversion needed - sections are strings as expected
    
    # Store the mini report in the state
    # Ensure mini_report is a valid MiniReport object and properly serialized
    if not isinstance(mini_report, MiniReport):
        logger.error("Invalid MiniReport object detected")
        raise TypeError("mini_report is not a valid MiniReport instance")
    
    # Convert to JSON directly without fallbacks
    mini_report_json = mini_report.json()
    
    # Store with both keys for compatibility
    state["industry_analysis_result"] = mini_report_json
    state["industry_report"] = mini_report_json  # This is what workflow.py expects
    logger.info("Successfully stored industry analysis results in state")
    
    # Store metrics in the state
    metrics = {
        "search_queries": len(query_strings) if isinstance(query_strings, (list, str, dict)) else 0,
        "search_results": len(search_results) if isinstance(search_results, (list, str, dict)) else 0,
        "sources_extracted": len(source_documents) if isinstance(source_documents, (list, str, dict)) else 0,
        "facts_extracted": len(facts) if isinstance(facts, (list, str, dict)) else 0,
        "validated_facts": len(validated_facts) if isinstance(validated_facts, (list, str, dict)) else 0,
        "execution_time_seconds": execution_time if isinstance(execution_time, (int, float)) else 0
    }
    # Create a result dict with ONLY modified fields
    # This is crucial for avoiding LangGraph concurrency errors
    result = {
        "industry_report": state.get("industry_report"),
        "industry_analysis_result": state.get("industry_analysis_result"),
        "industry_analysis_metrics": metrics
    }
    
    logger.info(f"Industry analysis metrics: {metrics}")
    
    # Only return the modified fields, not the entire state
    return result


@traceable(name="_compose_mini_report")
async def _compose_mini_report(facts: List["EnhancedFact"], spec: ResearchSpec, state: Dict[str, Any] = None) -> MiniReport:
    logger.info("Composing comprehensive mini-report from validated facts")
    
    # Create a URL database for content matching
    url_database = {}
    category_urls = {}
    
    # First pass: collect all URLs from facts organized by content and category
    for fact in facts:
        if hasattr(fact, 'source_url') and fact.source_url:
            # Map URL by content snippet (for content matching)
            key = fact.content[:50]
            url_database[key] = {
                'url': fact.source_url,
                'title': fact.source_title if hasattr(fact, 'source_title') else 'Industry Source'
            }
            
            # Map URLs by category (for category-based matching)
            category = fact.category
            if category not in category_urls:
                category_urls[category] = []
            category_urls[category].append({
                'url': fact.source_url,
                'title': fact.source_title if hasattr(fact, 'source_title') else 'Industry Source'
            })
    
    # Create a structured reference system for all sources
    references = {}
    categories = set()
    for fact in facts:
        categories.add(fact.category)  # Track all unique categories dynamically
        if fact.reference_id not in references:
            references[fact.reference_id] = {
                "id": fact.reference_id,
                "title": fact.source_title or "Unknown Source",
                "url": fact.source_url or "",
                "author": fact.source_author or "",
                "date": fact.source_date or "",
                "citation_count": 0  # Track how often this source is cited
            }
    
    # Create a comprehensive references section with academic-style citations
    references_markdown = "\n## References\n\n"
    for ref_id, ref_data in references.items():
        # Build a properly formatted citation
        citation_parts = []
        
        # Author
        if ref_data['author']:
            citation_parts.append(ref_data['author'])
        
        # Date in parentheses
        if ref_data['date']:
            citation_parts.append(f"({ref_data['date']})")
            
        # Title
        if ref_data['title']:
            citation_parts.append(f"\"{ref_data['title']}\"")
        
        # Format full citation with URL
        full_citation = ", ".join(citation_parts)
        if ref_data['url']:
            references_markdown += f"- [{ref_id}] {full_citation}. Retrieved from: {ref_data['url']}\n"
        else:
            references_markdown += f"- [{ref_id}] {full_citation}.\n"
    
    # Convert EnhancedFact to Fact with improved citations
    report_facts = []
    for f in facts:
        # Increment citation count for this reference
        if f.reference_id in references:
            references[f.reference_id]["citation_count"] += 1
            
        report_facts.append(
            Fact(
                content=f.content,
                category=f.category,
                citation=f.get_citation_markdown(),
                source_url=f.source_url,
                source_title=f.source_title,
                confidence=f.confidence if hasattr(f, 'confidence') and f.confidence is not None else 0.9,
                extracted_at=f.extracted_at if hasattr(f, 'extracted_at') and f.extracted_at is not None else datetime.now().isoformat()
            )
        )
    
    # Dynamically determine the report structure based on available facts
    # First by specified categories from spec, then by discovered categories
    facts_by_category = {}
    
    # Start with required categories from spec
    required_categories = spec.required_fact_categories if hasattr(spec, 'required_fact_categories') and spec.required_fact_categories else []
    
    # Add all dynamically discovered categories
    all_categories = list(set(required_categories) | categories)
    
    # Group facts by category
    for category in all_categories:
        facts_by_category[category] = []
    
    for fact in facts:
        category = fact.category
        if category not in facts_by_category:
            facts_by_category[category] = []
        facts_by_category[category].append(fact)
    
    # Create dynamic report sections based on available facts
    sections = {}
    section_facts_map = {}
    
    # Generate content for each category with facts
    llm, configured_model, configured_provider = _get_llm_provider(state)
    
    # Track which categories actually have facts
    active_categories = [category for category, fact_list in facts_by_category.items() if fact_list]
    logger.info(f"Generating content for {len(active_categories)} categories with facts: {active_categories}")
    
    # Generate content for each active category
    for category in active_categories:
        section_facts_map[category] = facts_by_category[category]
        
        # Generate detailed section content using LLM
        section_name, section_content = await _generate_section_content(
            section_name=category,
            section_facts=facts_by_category[category],
            spec=spec,
            references=references,
            url_database=url_database,
            category_urls=category_urls,
            llm=llm,
            state=state,
            configured_model=configured_model,
            configured_provider=configured_provider
        )
        sections[section_name] = section_content
    
    # Generate summary
    # Add the references section to the report
    sections["References"] = references_markdown
    
    # Generate comprehensive executive summary using all high-quality facts
    logger.info("Generating detailed executive summary")
    summary = await _generate_summary(facts, spec, state, configured_model, configured_provider)
    
    # Convert markdown sections to lists of Facts with proper source attribution
    formatted_sections = {}
    for section_name, section_content in sections.items():
        logger.debug(f"Processing section: {section_name} with {len(section_content)} characters")
        
        # Skip empty sections
        if not section_content or section_content.strip() == "":
            continue
            
        # Split the markdown content into paragraphs or logical chunks
        # First split by headers, then by paragraphs
        content_chunks = []
        
        # Handle headers and content together
        current_chunk = ""
        for line in section_content.split('\n'):
            if line.startswith('#'):
                if current_chunk.strip():  # Save previous chunk if not empty
                    content_chunks.append(current_chunk.strip())
                current_chunk = line + "\n"  # Start new chunk with header
            else:
                current_chunk += line + "\n"  # Add line to current chunk
                
                # If we hit a blank line and have content, consider it a paragraph boundary
                if line.strip() == "" and current_chunk.strip():
                    content_chunks.append(current_chunk.strip())
                    current_chunk = ""
        
        # Add the final chunk if not empty
        if current_chunk.strip():
            content_chunks.append(current_chunk.strip())
        
        # Create a Fact for each meaningful content chunk
        section_facts = []
        for chunk in content_chunks:
            if chunk.strip() and not chunk.strip().startswith('##'):  # Skip section headers themselves
                # Extract any references from the text [ref-id]
                ref_ids = re.findall(r'\[(\w+-\d+)\]', chunk)
                source_url = None  # No default placeholder URL
                source_title = "Industry Analysis"
                
                # If references found, use the first one's metadata
                
                # If no reference was found, try content matching
                if not source_url:
                    for key, url_data in url_database.items():
                        if (key in chunk or chunk[:50] in key) and url_data['url']:
                            source_url = url_data['url']
                            source_title = url_data['title']
                            logger.info(f"Found URL from content match: {key[:20]}... -> {source_url}")
                            break
                
                # Try matching by category as a last resort
                if not source_url and section_name in category_urls and category_urls[section_name]:
                    # Use the first URL from this category with a valid URL
                    for url_data in category_urls[section_name]:
                        if url_data['url'] and len(url_data['url'].strip()) > 0:
                            source_url = url_data['url']
                            source_title = url_data['title']
                            logger.info(f"Found URL from category match: {section_name} -> {source_url}")
                            break
                    
                # Only create a fact if we have a valid URL
                if source_url and len(str(source_url).strip()) > 0:
                    # Generate a reference ID if one wasn't found
                    if not ref_id:
                        ref_id = f"ref-{uuid.uuid4().hex[:8]}"
                        
                    # Create a dictionary with only the essential fields for standardization
                    new_fact = {
                        "content": chunk,
                        "source_url": source_url,
                        "source_title": source_title or section_name
                    }
                    # Add key_points for consistency with PESTEL format if this is a section with bullet points
                    if '•' in chunk or '*' in chunk:
                        bullets = [line.strip().lstrip('•').lstrip('*').strip() for line in chunk.split('\n') 
                                  if line.strip().startswith('•') or line.strip().startswith('*')]
                        if bullets:
                            new_fact["key_points"] = bullets
                    section_facts.append(new_fact)
                    logger.info(f"Created fact with valid URL: {source_url}")
                else:
                    logger.warning(f"Skipping fact creation due to missing URL: {chunk[:50]}...")
                    # This ensures we don't have facts without valid URLs
        formatted_sections[section_name] = section_facts
    
    # Generate 5 actionable recommendations based on the industry analysis
    recommendation_tool = {
        "type": "function",
        "function": {
            "name": "generate_industry_recommendations",
            "description": "Generate actionable recommendations based on the industry analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommendations": {
                        "type": "array",
                        "description": "List of 5 specific, actionable recommendations based on the industry analysis",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["recommendations"]
            }
        }
    }
    
    # Create recommendation prompt
    recommendation_prompt = f"""
    Based on the industry analysis and facts provided, generate 5 specific, actionable recommendations 
    for businesses operating in the {spec.industry_focus} industry in {', '.join(spec.geography_focus)}.
    
    Industry summary: {summary}
    
    Key sections:
    {json.dumps(sections, indent=2)}
    
    Each recommendation should:
    1. Address a specific challenge or opportunity in the industry
    2. Be actionable with clear implementation steps
    3. Consider both short-term and long-term impacts
    4. Be tailored to the geography/market specified
    5. Include relevant information about potential ROI or benefits
    """
    
    # Call LLM to generate recommendations
    messages = [
        {"role": "system", "content": "You are an industry expert providing strategic recommendations based on in-depth analysis."},
        {"role": "user", "content": recommendation_prompt}
    ]
    
    # Prepare monitoring context for recommendations
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_industry",
        workflow_name="pv_report_workflow",
        step_name="recommendations_generation",
        environment="prod"
    )
    
    try:
        logger.info("Generating industry-based recommendations")
        llm, _, _ = _get_llm_provider(state)
        rec_started_at = datetime.now()
        response = await llm.generate_responses_with_tools(messages, [recommendation_tool])
        recommendations = response.arguments.get("recommendations", [])
        
        # Record recommendations AI usage
        rec_finished_at = datetime.now()
        usage = getattr(response, 'usage', {}) or {}
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="azure_openai",
                model_name=getattr(response, 'model', 'gpt-5-mini'),
                operation_type="responses_api",
                started_at=rec_started_at,
                finished_at=rec_finished_at,
                status="success",
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                extra_metadata={"step": "recommendations_generation", "recommendations_count": len(recommendations)}
            )
        )
        
        # Ensure we have exactly 5 recommendations
        if len(recommendations) > 5:
            recommendations = recommendations[:5]
        while len(recommendations) < 5:
            recommendations.append(f"Conduct further research on {spec.industry_focus} market trends in {', '.join(spec.geography_focus)}")
            
        logger.info(f"Generated {len(recommendations)} recommendations based on industry analysis")
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {str(e)}")
        # Provide generic recommendations as fallback
        recommendations = [
            f"Invest in digital transformation initiatives in the {spec.industry_focus} industry",
            f"Develop strategic partnerships with key stakeholders in {', '.join(spec.geography_focus)}",
            f"Optimize operational efficiency to reduce costs and improve margins",
            f"Enhance customer experience through personalized solutions",
            f"Monitor regulatory changes that might impact {spec.industry_focus} operations"
        ]
    
    # Create the final structured mini-report
    # Convert Fact objects to dictionaries for Pydantic validation
    # Only include essential fields in the standardized structure
    dict_facts = []
    for fact in report_facts:
        if hasattr(fact, 'model_dump'):
            # Get full dict and filter out unwanted fields
            fact_dict = fact.model_dump()
            # Keep only essential fields
            dict_facts.append({
                'content': fact_dict.get('content', ''),
                'category': fact_dict.get('category', ''),
                'citation': fact_dict.get('citation', ''),
                'source_url': str(fact_dict.get('source_url', '')),
                'source_title': fact_dict.get('source_title', '')
            })
        elif hasattr(fact, 'dict'):
            fact_dict = fact.dict()
            dict_facts.append({
                'content': fact_dict.get('content', ''),
                'category': fact_dict.get('category', ''),
                'citation': fact_dict.get('citation', ''),
                'source_url': str(fact_dict.get('source_url', '')),
                'source_title': fact_dict.get('source_title', '')
            })
        else:
            # Fallback to manual conversion
            dict_facts.append({
                'content': fact.content,
                'category': fact.category,
                'citation': fact.citation,
                'source_url': str(fact.source_url) if fact.source_url else '',
                'source_title': fact.source_title
            })
    
    mini_report = MiniReport(
        title=spec.title or 'Target Industry',
        summary=summary,
        facts=dict_facts,
        sections=formatted_sections,
        recommendations=recommendations
    )
    
    # Save the report to the workflow state for downstream use
    if state is not None:
        state["industry_report"] = mini_report
        logger.info(f"Saved industry report to state with {len(formatted_sections)} sections and {len(report_facts)} facts")
    
    return mini_report


@traceable(name="_generate_section_content")
async def _generate_section_content(section_name: str, section_facts: List[EnhancedFact], 
                                  spec: ResearchSpec, references: Dict, url_database: Dict, 
                                  category_urls: Dict, llm: LLMProvider, state: Dict[str, Any] = None,
                                  configured_model: str = None, configured_provider: str = None) -> Tuple[str, str]:
    """
    Generate detailed content for a report section using LLM.
    
    Args:
        section_name: Name of the section to generate
        section_facts: Facts relevant to this section
        spec: Research specification
        references: Dictionary of reference metadata
        url_database: Dictionary mapping content snippets to URLs and titles
        category_urls: Dictionary mapping categories to lists of URL data
        llm: LLM provider to use for generation
        
    Returns:
        Tuple of (section_name, formatted_section_content)
    """
    # Prepare facts with reference IDs for the LLM
    formatted_facts = []
    for fact in section_facts:
        # Format the fact with its reference ID for the LLM
        formatted_facts.append({
            "content": fact.content,
            "category": fact.category,
            "reference": fact.reference_id,
            "confidence": fact.confidence
        })
    
    # Sort facts by confidence
    formatted_facts = sorted(formatted_facts, key=lambda f: f["confidence"], reverse=True)
    
    # Create the prompt for section content generation
    prompt = [
        {"role": "system", "content": f"""
        You are an expert market research analyst creating a detailed industry report section.
        
        Your task is to write a comprehensive, detailed section titled "{section_name}" for a professional industry analysis report.
        
        Guidelines:
        1. Create a well-structured narrative using ONLY the facts provided - do not add any information not contained in the facts
        2. Properly cite all facts using the provided reference IDs in square brackets [ref-id] at the end of the relevant sentence
        3. Write in a formal, professional tone appropriate for a business audience
        4. Organize information logically with proper paragraph breaks
        5. Focus on synthesizing the information rather than simply listing facts
        6. Aim for approximately 300-600 words total across all sections combined, with depth and detail
        7. Include exact figures, numbers and statistics from the facts
        8. Analyze trends, patterns and implications where the facts support such analysis
        9. Create subsections with markdown subheadings (### level) where appropriate
        10. Do not include your own opinions or speculations
        11. Do not include any confidence scores, extraction dates, or other metadata - focus only on the content and sources
        
        The final output must be formatted in markdown with the section heading:
        ## {section_name}
        
        [Your coherent, well-structured content with proper citations using reference IDs in square brackets]
        """}, 
        {"role": "user", "content": f"""
        Here are the facts to include in this section, with their reference IDs:
        
        {json.dumps(formatted_facts, indent=2)}
        
        Write a comprehensive section for "{section_name}" that synthesizes these facts into a coherent narrative.
        Include all relevant information from the facts and cite them properly using their reference IDs.
        
        IMPORTANT OUTPUT FORMAT:
        - Focus only on content and sources - do not include confidence scores, extraction timestamps, or other metadata
        - Each paragraph should be informative and well-structured
        - When extracting key points, format them as bullet points using * or •
        - The section should have a clear logical flow from introduction to conclusion
        - Cite all sources using their reference IDs in square brackets [ref-id]
        """}
    ]
    
    # Prepare monitoring context
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="mint_industry_analysis",
        workflow_name="mint_workflow",
        step_name="generate_section_content",
        environment="prod"
    )
    
    started_at = datetime.now()
    
    try:
        # Call LLM to generate section content without fallbacks
        response = await llm.generate_responses(prompt)
        content = response.content.strip()
        
        finished_at = datetime.now()
        
        # Record AI usage (fire-and-forget)
        usage = getattr(response, 'usage', {}) or {}
        # Use actual model from response, or fall back to configured model
        actual_model = getattr(response, 'model', configured_model or 'unknown')
        actual_provider = configured_provider or "openai"
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider=actual_provider,
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
        
        # Ensure section starts with proper heading
        if not content.startswith(f"## {section_name}"):
            content = f"## {section_name}\n\n{content}"
        
        return section_name, content
        
    except Exception as e:
        finished_at = datetime.now()
        
        # Record error (fire-and-forget)
        actual_provider = configured_provider or "openai"
        actual_model = configured_model or 'unknown'
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider=actual_provider,
                model_name=actual_model,
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                error_type=type(e).__name__
            )
        )
        raise


@traceable(name="_generate_summary")
async def _generate_summary(facts: List[EnhancedFact], spec: ResearchSpec, state: Dict[str, Any] = None,
                            configured_model: str = None, configured_provider: str = None) -> str:
    """
    Generate an executive summary from validated facts using LLM.
    
    This creates a brief executive summary that highlights the key findings
    and significant trends in the analysis. The summary aims to be
    approximately 20-40 words (extremely concise).
    
    Args:
        facts: Validated facts to include in summary
        spec: Research specification
        state: Current workflow state with configuration
        
    Returns:
        Executive summary of key findings
    """
    if not facts:
        return "Insufficient information available for analysis."
    
    # Get LLM provider without fallbacks
    llm, _, _ = _get_llm_provider(state)
    
    # Select highest confidence facts for summary
    high_confidence_facts = sorted([f for f in facts if f.confidence > 0.7], 
                                 key=lambda f: f.confidence, 
                                 reverse=True)
    
    if not high_confidence_facts or len(high_confidence_facts) < 3:
        high_confidence_facts = sorted(facts, key=lambda f: f.confidence, reverse=True)[:10]
    else:
        high_confidence_facts = high_confidence_facts[:10]  # Use top 10 high-confidence facts
    
    # Prepare facts for the LLM - only include essential fields
    formatted_facts = []
    for fact in high_confidence_facts:
        formatted_facts.append({
            "content": fact.content,
            "category": fact.category
        })
        
    # Create the prompt for comprehensive summary generation
    prompt = [
        {"role": "system", "content": """
        You are an expert market analyst specializing in executive summaries with deep industry expertise.
        
        Your task is to write a concise, informative executive summary for an industry report.
        
        Guidelines:
        1. Focus on the most important trends, challenges, and opportunities in the industry
        2. Highlight key market dynamics, competitive factors, and strategic implications
        3. Write in a formal, professional tone suitable for C-suite executives
        4. Include specific data points and statistics when available
        5. Be insightful, analytical, and forward-looking
        6. Aim for approximately 20-40 words in total (be extremely concise)
        7. Do not include citations or references in this summary
        8. Create a cohesive narrative rather than a list of disconnected facts
        9. Present a balanced view of risks and opportunities
        10. Focus only on the most important insights for decision-makers
        
        IMPORTANT FORMAT REQUIREMENTS:
        1. Do not include any confidence scores, extraction timestamps, or other metadata in your response
        2. Focus only on the content itself in a pure text format
        3. Write in a clear, professional style with precise language
        4. The summary should be directly usable in a standardized JSON structure
        
        The summary should provide a comprehensive overview of the key findings, emerging trends, market size, growth projections,
        competitive dynamics, regulatory considerations, and strategic implications if available in the facts.
        Include quantitative data where available to strengthen your analysis.
        """}, 
        {"role": "user", "content": f"""
        Title: {spec.title}
        
        Key Facts:
        {json.dumps(formatted_facts, indent=2)}
        
        Write a comprehensive executive summary that synthesizes these facts into a coherent narrative.
        Focus on the most significant findings and provide a holistic view of {spec.title or 'this industry'}.
        """}
    ]
    
    # Prepare monitoring context
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="mint_industry_analysis",
        workflow_name="mint_workflow",
        step_name="generate_summary",
        environment="prod"
    )
    
    started_at = datetime.now()
    
    try:
        # Call LLM to generate summary without fallbacks
        response = await llm.generate_responses(prompt)
        summary = response.content.strip()
        
        finished_at = datetime.now()
        
        # Record AI usage (fire-and-forget)
        usage = getattr(response, 'usage', {}) or {}
        # Use actual model from response, or fall back to configured model
        actual_model = getattr(response, 'model', configured_model or 'unknown')
        actual_provider = configured_provider or "openai"
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider=actual_provider,
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
        
        return summary
        
    except Exception as e:
        finished_at = datetime.now()
        
        # Record error (fire-and-forget)
        actual_provider = configured_provider or "openai"
        actual_model = configured_model or 'unknown'
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider=actual_provider,
                model_name=actual_model,
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                error_type=type(e).__name__
            )
        )
        raise


# Simplified analysis workflow


@traceable(name="_extract_keywords")
def _extract_keywords(text: str) -> List[str]:
    """
    Extract significant keywords from text.
    
    Args:
        text: Text to extract keywords from
        
    Returns:
        List of significant keywords
    """
    # This is a simplified keyword extraction
    # In a real implementation, we might use NLP techniques like Part-of-Speech tagging
    # to identify significant nouns, named entities, etc.
    
    # Remove common stopwords
    stopwords = {
        "a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
        "in", "on", "at", "to", "for", "with", "about", "by", "of", "from", "as", "what", "when",
        "where", "why", "how", "who", "whom", "which", "whose", "this", "that", "these", "those"
    }
    
    # Split text into words, remove stopwords and short words
    words = [word.strip('.,?!()[]{}"\'\'') for word in text.split()]  # Remove punctuation
    keywords = [word.lower() for word in words if word.lower() not in stopwords and len(word) > 2]
    
    return keywords


async def _extract_source_content(search_results: List[SearchResult], state: Dict[str, Any] = None) -> List[SourceDocument]:
    """
    Extract rich content from search results URLs using async HTTP client.
    
    This function fetches web content from search result URLs, handles different content types
    including PDFs, HTML with tables, and structured data. It cleans and preserves the structure
    of the content for further processing.
    
    Args:
        search_results: List of search results with URLs
        state: Current workflow state with configuration
        
    Returns:
        List of source documents with extracted content, preserving structure and metadata
    """
    import httpx
    from bs4 import BeautifulSoup
    import aiofiles
    from urllib.parse import urlparse
    import uuid
    import os
    
    logger.info("===========================================")
    logger.info("Industry AGENT: Starting Source Extraction")
    logger.info(f"Number of search results: {len(search_results)}")
    logger.info(f"First search result title: {search_results[0].title if search_results else 'No results'}")
    logger.info(f"First search result URL: {search_results[0].url if search_results else 'No URL'}")
    
    source_documents: List[SourceDocument] = []
    current_time = datetime.now().isoformat()
    
    async def extract_from_url(result):
        try:
            logger.info(f"Starting content extraction for {result.url}")
            
            # Parse URL to determine content type and source
            url_str = str(result.url)
            parsed_url = urlparse(url_str)
            domain = parsed_url.netloc
            
            # Set request headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Fetch content with async HTTP client and timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.get(url_str, headers=headers)
                    response.raise_for_status()  # Raise exception for bad status codes
                    
                    # Handle different content types
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/pdf' in content_type:
                        # Save PDF temporarily and extract text
                        pdf_path = f"temp_{uuid.uuid4()}.pdf"
                        async with aiofiles.open(pdf_path, 'wb') as f:
                            await f.write(response.content)
                        
                        # Use PyPDF2 to extract text from PDF with structure preservation
                        try:
                            from PyPDF2 import PdfReader
                            reader = PdfReader(pdf_path)
                            pdf_metadata = reader.metadata
                            num_pages = len(reader.pages)
                            
                            # Extract publication date if available
                            pub_date = None
                            if pdf_metadata and "/CreationDate" in pdf_metadata:
                                # Try to parse PDF creation date
                                try:
                                    date_str = pdf_metadata["/CreationDate"]
                                    # PDF dates are often in format: D:YYYYMMDDHHMMSSz
                                    if date_str.startswith("D:"):
                                        date_str = date_str[2:]
                                        pub_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                except:
                                    pass
                            
                            # Extract author if available
                            author = None
                            if pdf_metadata and "/Author" in pdf_metadata:
                                author = pdf_metadata["/Author"]
                            
                            # Process each page with page numbers
                            content_parts = []
                            for i, page in enumerate(reader.pages):
                                page_text = page.extract_text()
                                if page_text and page_text.strip():
                                    content_parts.append(f"--- Page {i+1}/{num_pages} ---\n{page_text}")
                            
                            # Join all pages with clear separators
                            content = "\n\n".join(content_parts)
                            
                            # Add metadata about the PDF
                            metadata_info = f"PDF METADATA:\n"
                            metadata_info += f"Pages: {num_pages}\n"
                            if pub_date:
                                metadata_info += f"Publication Date: {pub_date}\n"
                            if author:
                                metadata_info += f"Author: {author}\n"
                            
                            # Prepend metadata to content
                            content = metadata_info + "\n\n" + content
                        except Exception as e:
                            logger.error(f"Error extracting text from PDF {url_str}: {e}")
                            content = f"Error extracting PDF content: {str(e)}"
                        
                        # Clean up temporary file
                        os.remove(pdf_path)
                    else:
                        # For HTML content, use BeautifulSoup for structured extraction
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Remove script, style, and nav elements (typically navigation)
                        for element in soup(["script", "style", "nav", "footer", "header"]):
                            element.decompose()
                        
                        # Extract tables separately to preserve their structure
                        tables = []
                        for table_idx, table in enumerate(soup.find_all('table')):
                            table_data = []
                            # Get table headers
                            headers = [th.text.strip() for th in table.find_all('th')]
                            if not headers and table.find('tr'):
                                # Try to get headers from first row if not explicitly defined
                                headers = [td.text.strip() for td in table.find('tr').find_all('td')]
                            
                            # Process table rows
                            for tr in table.find_all('tr')[1:] if headers else table.find_all('tr'):
                                row = [td.text.strip() for td in tr.find_all(['td', 'th'])]
                                if row:
                                    table_data.append(row)
                            
                            # Format table as plain text
                            if headers and table_data:
                                table_text = f"TABLE {table_idx + 1}:\n"
                                table_text += " | ".join(headers) + "\n"
                                table_text += "-" * (sum(len(h) for h in headers) + 3 * (len(headers) - 1)) + "\n"
                                for row in table_data:
                                    table_text += " | ".join(row) + "\n"
                                tables.append(table_text)
                        
                        # Get main text content
                        # Focus on main content areas when possible
                        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
                        
                        # Get text content with paragraph structure preserved
                        paragraphs = []
                        for p in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                            text = p.get_text().strip()
                            if text and len(text) > 10:  # Skip very short fragments
                                if p.name.startswith('h'):
                                    # Format headings
                                    paragraphs.append(f"\n### {text} ###\n")
                                else:
                                    paragraphs.append(text)
                        
                        # Combine text content with preserved structure
                        content = "\n\n".join(paragraphs)
                        
                        # Add tables to the content
                        if tables:
                            content += "\n\n" + "\n\n".join(tables)
                        
                    # Get title from result or use domain if not available
                    title = getattr(result, 'title', domain)
                    
                    # Convert all fields to strings to avoid Pydantic validation errors
                    url_str = str(result.url)
                    title_str = str(title)
                    source_str = str(result.source or domain)
                    
                    logger.info(f"Successfully extracted content from {url_str}")
                    logger.info(f"Content length: {len(content)} characters")
                    logger.info(f"First 100 chars: {content[:100]}...")
                    
                    # Extract additional metadata
                    published_date = getattr(result, 'published_date', None)
                    
                    # Extract potential author information
                    author = None
                    if 'application/pdf' in content_type and 'pdf_metadata' in locals() and pdf_metadata and "/Author" in pdf_metadata:
                        author = pdf_metadata["/Author"]
                        
                    # Count paragraphs and words for content quality assessment
                    paragraphs_count = content.count('\n\n') + 1
                    words_count = len(content.split())
                    
                    # Extract keywords/phrases for relevance assessment (simplified version)
                    keywords = []
                    if words_count > 0:
                        # Extract common phrases and terms that might be important
                        import re
                        # Find capitalized phrases which are often key terms
                        capitalized_phrases = re.findall(r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+\b', content)
                        if capitalized_phrases:
                            keywords.extend(capitalized_phrases[:10])  # Limit to avoid excessive data
                        
                        # Extract numeric data points which are often valuable
                        percentages = re.findall(r'\d+(\.\d+)?\s*%', content)
                        if percentages:
                            keywords.extend([f"Percentage: {p}" for p in percentages[:5]])
                            
                    # Detect if content has structured data sections
                    has_structured_data = False
                    if 'tables' in locals() and tables:
                        has_structured_data = True
                    elif re.search(r'\b(table|figure|chart|graph)\s+\d+\b', content, re.IGNORECASE):
                        has_structured_data = True
                    
                    # Create reference ID based on domain and position
                    reference_id = f"ref-{domain.split('.')[-2]}-{len(source_documents) + 1}"
                    
                    # Create source document with rich metadata
                    return SourceDocument(
                        title=title_str,
                        url=url_str,
                        source=source_str,
                        content=content,
                        timestamp=current_time,
                        metadata={
                            "content_type": content_type,
                            "domain": domain,
                            "extraction_date": current_time,
                            "published_date": published_date or ('pub_date' in locals() and pub_date),
                            "author": author,
                            "content_length": len(content),
                            "paragraphs_count": paragraphs_count,
                            "words_count": words_count,
                            "has_tables": bool('tables' in locals() and tables),
                            "has_structured_data": has_structured_data,
                            "keywords": keywords,
                            "reference_id": reference_id
                        }
                    )
                except httpx.RequestError as e:
                    logger.error(f"HTTP request error for {url_str}: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Error processing response for {url_str}: {e}")
                    return None
        except Exception as e:
            logger.error(f"Error extracting content from {result.url}: {str(e)}")
            return None

    # Create tasks for all URLs
    tasks = [extract_from_url(result) for result in search_results]
    
    # Wait for all tasks to complete with a timeout
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=600.0)  # 10 minute timeout
    except asyncio.TimeoutError:
        logger.error("Timeout while waiting for source extraction tasks")
        results = []
    
    # Filter out None results (failed extractions)
    source_documents = [doc for doc in results if doc is not None]
    
    logger.info("===========================================")
    logger.info("Industry AGENT: Completed Source Extraction")
    logger.info(f"Successfully extracted content from {len(source_documents)}/{len(search_results)} sources")
    if source_documents:
        logger.info(f"First document title: {source_documents[0].title}")
        logger.info(f"First document content length: {len(source_documents[0].content)}")
        logger.info(f"First document URL: {source_documents[0].url}")
    else:
        logger.warning("No documents were successfully extracted")
    
    return source_documents


@traceable(name="_extract_key_entities")
async def _extract_key_entities(spec: ResearchSpec, state: Dict[str, Any] = None) -> ResearchEntities:
    """
    Extract key entities from the research specification using tool calling.
    
    Args:
        spec: The research specification to analyze
        state: Current workflow state with configuration
        
    Returns:
        Structured entities extracted from the spec
    """
    # Get LLM provider
    llm, _, _ = _get_llm_provider(state)
    
    # Prepare monitoring context for entity extraction
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_industry",
        workflow_name="pv_report_workflow",
        step_name="entity_extraction",
        environment="prod"
    )
    
    # Define the tool schema for entity extraction
    entities_tool = {
        "type": "function",
        "function": {
            "name": "extract_research_entities",
            "description": "Extract key entities from the research specification for industry analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry_names": {
                        "type": "array",
                        "description": "Primary industries being researched",
                        "items": {"type": "string"}
                    },
                    "geography_names": {
                        "type": "array",
                        "description": "Geographic regions being researched",
                        "items": {"type": "string"}
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Relevant time period for the research (e.g., '5 years', '2025-2030')"
                    },
                    "target_segments": {
                        "type": "array",
                        "description": "Specific market segments to focus on",
                        "items": {"type": "string"}
                    },
                    "key_topics": {
                        "type": "array", 
                        "description": "Key topics or themes within the industry (5-7 most important)",
                        "items": {"type": "string"}
                    },
                    "expected_output_sections": {
                        "type": "array",
                        "description": "Suggested sections for the final report based on required fact categories",
                        "items": {"type": "string"}
                    }
                },
                "required": ["industry_names", "geography_names", "key_topics"]
            }
        }
    }
    
    # Build messages for entity extraction
    messages = [
        {"role": "system", "content": "You are an expert research analyst. Extract key entities from the research specification."}, 
        {"role": "user", "content": f"""
        Research Specification:
        Title: {spec.title}
        Description: {spec.description}
        Key Questions: {', '.join(spec.key_questions)}
        Required Fact Categories: {', '.join(spec.required_fact_categories)}
        Geography Focus: {', '.join(spec.geography_focus)}
        Industry Focus: {', '.join(spec.industry_focus)}
        Keywords: {', '.join(spec.keywords)}
        
        Extract all key entities from this research specification to help guide the industry analysis.
        """}
    ]
    
    # Call LLM with tool calling - no fallbacks
    entity_started_at = datetime.now()
    response = await llm.generate_responses_with_tools(messages, [entities_tool])
    
    # Record entity extraction AI usage
    entity_finished_at = datetime.now()
    usage = getattr(response, 'usage', {}) or {}
    asyncio.create_task(
        monitoring.record_ai_usage(
            context=monitoring_context,
            provider="azure_openai",
            model_name=getattr(response, 'model', 'gpt-5-mini'),
            operation_type="responses_api",
            started_at=entity_started_at,
            finished_at=entity_finished_at,
            status="success",
            prompt_tokens=usage.get('prompt_tokens'),
            completion_tokens=usage.get('completion_tokens'),
            total_tokens=usage.get('total_tokens'),
            extra_metadata={"step": "entity_extraction"}
        )
    )
    
    # Process the response to handle missing fields
    arguments = response.arguments
    
    # Ensure target_segments is a list
    if "target_segments" not in arguments or arguments.get("target_segments") is None:
        arguments["target_segments"] = []
        
    # Return the validated entity
    return ResearchEntities(**arguments)


async def _generate_search_queries(spec: ResearchSpec, entities: ResearchEntities, query_count: int = 5, state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate optimized search queries with link quotas based on the research spec and extracted entities.
    
    Args:
        spec: The research specification
        entities: Extracted entities from the spec
        query_count: Maximum number of search queries to generate (default 5)
        state: Current workflow state
        
    Returns:
        Dict with search queries and link quota allocation
    """
    # Get LLM provider
    llm, _, _ = _get_llm_provider()
    
    # Prepare monitoring context for query generation
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_industry",
        workflow_name="pv_report_workflow",
        step_name="query_generation",
        environment="prod"
    )
    
    # Determine total link quota from config
    agent_config = get_agent_config(state, "industry") if state else {}
    max_links = agent_config.get("max_sources", 15)
    
    # Build prompt for query generation with link quota allocation
    prompt = [
        {"role": "system", "content": "You are an expert research analyst tasked with generating optimized search queries based on research specifications."},
        {"role": "user", "content": f"""
        Research Specification:
        Title: {spec.title}
        Description: {spec.description}
        Key Questions: {', '.join(spec.key_questions)}
        Keywords: {', '.join(spec.keywords) if hasattr(spec, 'keywords') and spec.keywords else 'None provided'}
        
        Extracted Entities:
        Industry Names: {', '.join(entities.industry_names)}
        Geography Names: {', '.join(entities.geography_names)}
        Timeframe: {entities.timeframe if entities.timeframe else 'current'}
        Target Segments: {', '.join(entities.target_segments) if entities.target_segments else 'general'}
        Key Topics: {', '.join(entities.key_topics)}
        
        Your task is to:
        1. Analyze the specification and identify key themes, questions, and focus areas
        2. Generate EXACTLY {query_count} optimized search queries that will yield the most valuable information
        3. CRITICAL: Keep queries SHORT and SIMPLE - maximum 80 characters. Use simple natural language phrases, NOT complex Boolean queries
        4. Do NOT use multiple AND/OR operators - Brave Search API rejects overly complex queries
        5. Include geography in simple form (e.g., "Kenya vegetable farming market" not "Kenya AND (vegetable OR farming)")
        6. Rank the queries by importance (1-{query_count}, with 1 being most important)
        7. Allocate a total of {max_links} search links across the {query_count} queries based on their importance
        
        GOOD query examples: "vegetable farming Kenya market size", "smallholder farmer technology adoption Africa"
        BAD query examples (TOO COMPLEX): '"Kenya" AND ("vegetable" OR "farming") AND ("market" OR "size")'
        
        Return a JSON array with the following structure for each query:
        [
          {{
            "query": "Your optimized search query with operators",
            "importance_rank": 1-{query_count},
            "link_quota": number of links allocated (total must be {max_links}),
            "rationale": "Brief explanation of what this query targets and why it's important"
          }},
          // Additional query objects
        ]
        
        Make sure the link_quota values sum exactly to {max_links} and allocate more links to higher importance queries.
        IMPORTANT: Return ONLY the JSON array, no additional text or explanation.
        """}
    ]
    
    # Call LLM to generate queries
    logger.info("Making LLM call for optimized search query generation")
    query_started_at = datetime.now()
    response = await llm.generate_responses(prompt)
    content = response.content.strip()
    
    # Record query generation AI usage
    query_finished_at = datetime.now()
    usage = getattr(response, 'usage', {}) or {}
    asyncio.create_task(
        monitoring.record_ai_usage(
            context=monitoring_context,
            provider="azure_openai",
            model_name=getattr(response, 'model', 'gpt-5-mini'),
            operation_type="responses_api",
            started_at=query_started_at,
            finished_at=query_finished_at,
            status="success",
            prompt_tokens=usage.get('prompt_tokens'),
            completion_tokens=usage.get('completion_tokens'),
            total_tokens=usage.get('total_tokens'),
            extra_metadata={"step": "query_generation", "query_count": query_count}
        )
    )
    
    # Extract JSON array
    import re
    try:
        # First try to find JSON array pattern with balanced brackets
        json_match = re.search(r'\[\s*\{.*?\}\s*(,\s*\{.*?\}\s*)*\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            search_queries = json.loads(json_str)
        elif '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
            search_queries = json.loads(content)
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
            search_queries = json.loads(content)
        else:
            # Clean common issues before parsing
            cleaned_content = content
            # Remove any trailing commas inside arrays
            cleaned_content = re.sub(r',\s*([\]\}])', r'\1', cleaned_content)
            # Remove comments
            cleaned_content = re.sub(r'//.*?\n', '\n', cleaned_content)
            search_queries = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {str(e)}\nContent: {content}")
        # Fall back to a default set of queries based on the spec
        search_queries = [
            {
                "query": f"\"{' '.join(entities.industry_names)}\" market size {' '.join(entities.geography_names)}",
                "importance_rank": 1,
                "link_quota": max_links // 3,
                "rationale": "Basic market size query for the target industry"
            },
            {
                "query": f"\"{' '.join(entities.industry_names)}\" trends {entities.timeframe if entities.timeframe else 'current'}",
                "importance_rank": 2,
                "link_quota": max_links // 3,
                "rationale": "Key trends in the target industry"
            },
            {
                "query": f"\"{' '.join(entities.industry_names)}\" key players competitors",
                "importance_rank": 3,
                "link_quota": max_links - (2 * (max_links // 3)),
                "rationale": "Major companies and competitive landscape"
            }
        ]
        
    # Validate that we have a list
    if not isinstance(search_queries, list):
        logger.error("LLM did not return a list of search queries")
        raise ValueError("Expected a list of search queries but received a different format")
    
    # Limit to the configured query count
    search_queries = search_queries[:query_count]
    
    # Validate total link quota
    total_links = sum(query.get("link_quota", 0) for query in search_queries)
    if total_links != max_links:
        logger.warning(f"Total link quota ({total_links}) doesn't match expected ({max_links}), normalizing")
        # Normalize link quotas
        factor = max_links / total_links if total_links > 0 else 0
        for query in search_queries:
            query["link_quota"] = int(query["link_quota"] * factor)
        
        # Ensure we hit exactly max_links by adding remaining to highest importance query
        remaining_links = max_links - sum(query.get("link_quota", 0) for query in search_queries)
        if remaining_links > 0:
            highest_importance = min([query.get("importance_rank", i+1) for i, query in enumerate(search_queries)])
            for query in search_queries:
                if query.get("importance_rank") == highest_importance:
                    query["link_quota"] += remaining_links
                    break
    
    # Create result dict with both the full queries with metadata and a simple list of query strings
    result = {
        "optimized_queries": search_queries,
        "query_strings": [q["query"] for q in search_queries]
    }
    
    logger.info(f"Generated {len(search_queries)} optimized search queries with link quotas")
    return result


def _get_llm_provider(state: Dict[str, Any] = None) -> tuple[LLMProvider, str, str]:
    """Get LLM provider with Azure OpenAI support for report generation.
    
    Industry Agent uses REPORT_GENERATION use case which maps to gpt-4.1 deployment.
    
    Returns:
        Tuple of (provider, model_name, provider_type) for monitoring
    """
    # Use centralized Azure OpenAI configuration for report generation
    provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
    
    # Get legacy config for temperature and max_tokens if available
    if state is not None:
        llm_config = get_llm_config(state)
    else:
        config = get_config()
        llm_config = config.get_llm_config()
    
    # Extract temperature and max_tokens from legacy config or use defaults
    openai_config = llm_config.get("openai", {})
    temperature = openai_config.get("temperature", 0.2)
    max_tokens = openai_config.get("max_tokens", 32000)
    
    # Create LLMConfig with Azure OpenAI or OpenAI model using gpt-5-mini pattern
    if provider_type == ModelProvider.AZURE_OPENAI:
        logger.info(f"Industry Agent using Azure OpenAI gpt-5-mini: {model_name} for report generation")
        llm_config_obj = LLMConfig(
            model_name=model_name,  # gpt-5-mini deployment
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name="openai",  # Use openai provider with base_url
            azure_endpoint=client_config.get("azure_endpoint"),
            api_version=client_config.get("api_version"),
            api_key=client_config.get("api_key"),
            base_url=client_config.get("base_url")  # For gpt-5-mini pattern
        )
    else:
        logger.info(f"Industry Agent using OpenAI model: {model_name} for report generation")
        llm_config_obj = LLMConfig(
            model_name=model_name,  # OpenAI model name
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name="openai",
            api_key=client_config.get("api_key")
        )
    
    provider = OpenAIProvider(config=llm_config_obj)
    provider.health_check()
    
    # Determine provider name for monitoring
    provider_name = "azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai"
    
    return provider, model_name, provider_name

# Standardized report generation implementation

@traceable(name="_compose_standardized_industry_report")
async def _compose_standardized_industry_report(facts: List["EnhancedFact"], spec: ResearchSpec, state: Dict[str, Any] = None) -> MiniReport:
    """
    Compose a structured industry mini-report from validated facts using the standardized industry report prompt.
    
    This implementation uses the new prompt template that generates structured reports with
    numbered citations [1], [2] and separate sources section.
    
    Args:
        facts: List of validated facts with category tagging
        spec: Research specification
        state: Optional workflow state for configuration and LLM provider
        
    Returns:
        A standardized MiniReport structure
    """
    logger.info("Generating standardized industry report using new prompt template")
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Use ALL facts for comprehensive report generation (no artificial limits)
    # Sort facts by confidence score to prioritize high-quality facts in the prompt
    facts_to_use = sorted(facts, key=lambda x: x.confidence if hasattr(x, 'confidence') else 0, reverse=True)
    
    logger.info(f"📊 Using ALL {len(facts_to_use)} facts for comprehensive report generation (no limits)")
    
    # Group facts by category for analysis and reporting
    facts_by_category = {}
    for fact in facts_to_use:
        category = fact.category if hasattr(fact, 'category') and fact.category else "General"
        if category not in facts_by_category:
            facts_by_category[category] = []
        facts_by_category[category].append(fact)
    
    logger.info(f"📊 Facts distributed across {len(facts_by_category)} categories: {list(facts_by_category.keys())}")
    logger.info(f"✅ Facts naturally organized into {len(facts_by_category)} categories - no forcing needed")
    
    # Format facts for the prompt - include source information for citation mapping
    formatted_facts = []
    unique_sources = {}
    source_counter = 1
    
    for fact in facts_to_use:  # Using ALL facts for comprehensive analysis
        # Create unique source mapping
        source_key = (fact.source_title, str(fact.source_url) if fact.source_url else "")
        if source_key not in unique_sources:
            unique_sources[source_key] = source_counter
            source_counter += 1
        
        formatted_facts.append({
            "content": fact.content,
            "category": fact.category,
            "source_title": fact.source_title,
            "source_url": str(fact.source_url) if fact.source_url else "",
            "citation_number": unique_sources[source_key]
        })
    
    # Format research spec for prompt
    research_spec_dict = {
        "title": spec.title if hasattr(spec, 'title') else "",
        "description": spec.description if hasattr(spec, 'description') else "",
        "industry_focus": spec.industry_focus if hasattr(spec, 'industry_focus') else [],
        "geography_focus": spec.geography_focus if hasattr(spec, 'geography_focus') else [],
        "time_period": spec.time_period if hasattr(spec, 'time_period') else "Current"
    }
    
    # Create EXPLICIT citation instruction that tells LLM to use the pre-assigned citation_number field
    max_citation_number = len(unique_sources)
    citation_instruction = f"""

════════════════════════════════════════════════════════════════════════════════
CRITICAL CITATION INSTRUCTIONS - READ CAREFULLY
════════════════════════════════════════════════════════════════════════════════

CITATION SYSTEM:
- Each fact in the JSON above has a "citation_number" field (e.g., "citation_number": 5)
- This number is PRE-ASSIGNED and maps to the source document for that fact
- You have {max_citation_number} unique sources, so valid citations are ONLY [1] through [{max_citation_number}]

MANDATORY RULES:
1. When citing a fact, use its EXACT "citation_number" value from the JSON
   Example: If fact says {{"content": "Market grew 15%", "citation_number": 3}}, 
   you MUST cite it as [3], NOT [1] or any other number

2. NEVER invent citation numbers - ONLY use citation_number values from the facts JSON

3. Multiple facts can share the same citation_number (they're from the same source)
   This is CORRECT and EXPECTED

4. Your "sources" array must have EXACTLY {max_citation_number} entries
   Source [1] = first unique source, Source [2] = second unique source, etc.

5. NEVER use citations higher than [{max_citation_number}] - these don't exist!

VIOLATION WILL CAUSE VALIDATION FAILURE - Follow these rules exactly.
════════════════════════════════════════════════════════════════════════════════
"""
    
    # Get top categories by fact count to guide section creation
    categories_by_count = sorted(
        [(cat, len(facts)) for cat, facts in facts_by_category.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Build dynamic section suggestions based on actual categories
    # Filter out regulations and challenges - those are covered by PESTEL analysis
    category_list = [c for c in facts_by_category.keys() 
                     if not any(k in c.lower() for k in ['regulation', 'regulatory', 'challenge'])]
    section_suggestions = []
    
    logger.info(f"🔧 Filtered out regulation/challenge categories - focusing on market dynamics (PESTEL covers those)")
    
    # Group similar categories dynamically (excluding PESTEL-covered topics)
    market_cats = [c for c in category_list if any(k in c.lower() for k in ['market', 'size', 'growth', 'segmentation'])]
    competitor_cats = [c for c in category_list if any(k in c.lower() for k in ['competitor', 'competition', 'structure'])]
    trend_cats = [c for c in category_list if any(k in c.lower() for k in ['trend', 'technology', 'consumer', 'behavior'])]
    supply_cats = [c for c in category_list if any(k in c.lower() for k in ['supply', 'distribution', 'production', 'capacity'])]
    opportunity_cats = [c for c in category_list if any(k in c.lower() for k in ['opportunity', 'pricing', 'strategy', 'channel'])]
    
    if market_cats:
        section_suggestions.append(f"1. Market Overview & Growth (use categories: {', '.join(market_cats[:3])})")
    if competitor_cats:
        section_suggestions.append(f"2. Competitive Landscape (use categories: {', '.join(competitor_cats[:2])})")
    if trend_cats:
        section_suggestions.append(f"3. Market Trends & Innovation (use categories: {', '.join(trend_cats[:3])})")
    if supply_cats:
        section_suggestions.append(f"4. Supply Chain & Distribution (use categories: {', '.join(supply_cats[:3])})")
    if opportunity_cats:
        section_suggestions.append(f"5. Market Opportunities & Strategy (use categories: {', '.join(opportunity_cats[:3])})")
    
    # Add fallback sections if we don't have enough suggestions
    remaining_cats = [c for c in category_list if c not in (market_cats + competitor_cats + trend_cats + supply_cats + opportunity_cats)]
    if len(section_suggestions) < 5 and remaining_cats:
        section_suggestions.append(f"6. Additional Market Insights (use categories: {', '.join(remaining_cats[:3])})")
    
    suggestions_text = "\n".join(section_suggestions) if section_suggestions else "Create 5-7 sections covering major industry aspects"
    
    logger.info(f"📋 Generated {len(section_suggestions)} section suggestions for LLM guidance")
    logger.info(f"📋 Top 5 categories by fact count: {', '.join([f'{cat}({count})' for cat, count in categories_by_count[:5]])}")
    
    # Add category diversity instruction
    category_instruction = f"""

CRITICAL REQUIREMENT - YOU MUST FOLLOW THIS EXACTLY:

1. SECTION STRUCTURE (MANDATORY):
   Create EXACTLY 5-7 analysis sections.
   
   Your {len(facts_by_category)} available fact categories are:
   {', '.join([f'"{cat}" ({count} facts)' for cat, count in categories_by_count[:10]])}
   
   Suggested section organization:
   {suggestions_text}

2. EACH SECTION MUST HAVE:
   - Descriptive heading (H2)
   - 500-600 words minimum
   - Data-rich opening paragraph with statistics
   - Bullet point list (4-6 items)
   - Analysis paragraph
   - Proper citations [1], [2], [3]

3. MANDATORY FIELDS:
   Your JSON response MUST include these fields (DO NOT OMIT):
   - "analysis" array (5-7 section objects)
   - "recommendations" array (4-7 items)
   - "sources" array (all cited sources with URLs)
   
   If any field is missing, the report will FAIL validation!"""
    
    # Format the prompt with research spec and facts
    # PERFORMANCE: Use compact JSON (no indent) for facts to reduce prompt size
    prompt_input = {
        "research_spec": json.dumps(research_spec_dict, indent=2),
        "facts": json.dumps(formatted_facts)  # Compact JSON - no indent
    }
    
    # Add instructions to the formatted prompt
    base_prompt = INDUSTRY_REPORT_PROMPT.format(**prompt_input)
    formatted_prompt = base_prompt + citation_instruction + category_instruction
    
    # Log prompt size for performance monitoring
    prompt_size_chars = len(formatted_prompt)
    prompt_size_kb = prompt_size_chars / 1024
    logger.info(f"📊 PROMPT SIZE: {prompt_size_chars} chars ({prompt_size_kb:.1f} KB) with {len(formatted_facts)} facts")
    
    # Call LLM with the prompt
    messages = [
        {"role": "system", "content": "You are an expert business analyst specializing in industry analysis."},
        {"role": "user", "content": formatted_prompt}
    ]
    
    try:
        # Use the JSONValidator for validation and repair
        validated_data = await generate_report_with_validation(llm, messages, "industry")
        
        # Extract the report data from the validated response
        report_data = validated_data.get("report", {})
        
        # CRITICAL VALIDATION: Check for empty analysis sections (schema requires min 5)
        analysis_sections = report_data.get("analysis", [])
        if not analysis_sections or len(analysis_sections) == 0:
            logger.error("❌ CRITICAL FAILURE: LLM returned EMPTY analysis sections!")
            logger.error(f"Report data keys: {list(report_data.keys())}")
            logger.error(f"Title: {report_data.get('title', 'N/A')}")
            logger.error(f"Summary length: {len(report_data.get('summary', ''))}")
            logger.error(f"Recommendations count: {len(report_data.get('recommendations', []))}")
            logger.error(f"Sources count: {len(report_data.get('sources', []))}")
            raise ValueError(
                "Industry report generation FAILED: LLM returned empty analysis sections. "
                "Schema requires minimum 5 sections but got 0. This indicates LLM timeout, "
                "validation bypass, or incomplete JSON generation."
            )
        
        if len(analysis_sections) < 5:
            logger.warning(f"⚠️ WARNING: Analysis has only {len(analysis_sections)} sections, schema requires minimum 5")
        
        # Create the MiniReport from validated data
        mini_report = MiniReport(
            title=report_data.get("title", "Industry Analysis"),
            summary=report_data.get("summary", ""),
            analysis=analysis_sections,
            recommendations=report_data.get("recommendations", []),
            sources=report_data.get("sources", [])
        )
        
        logger.info(f"✅ Generated industry report with {len(analysis_sections)} sections and {len(report_data.get('recommendations', []))} recommendations")
        return mini_report
            
    except Exception as e:
        logger.error(f"Failed to generate industry report: {e}")
        
        # Fallback to the enhanced parser if JSONValidator fails
        try:
            logger.info("Falling back to enhanced parser")
            parser = get_enhanced_parser(max_retries=5)
            parsed_data = await parser.parse_report_with_retry(llm, messages, "industry")
            
            # Create the MiniReport from parsed data
            # Note: Enhanced parser returns "sections", but MiniReport uses "analysis"
            # Handle both field names for robustness
            analysis_data = parsed_data.get("analysis") or parsed_data.get("sections", [])
            
            mini_report = MiniReport(
                title=parsed_data["title"],
                summary=parsed_data["summary"],
                analysis=analysis_data,
                recommendations=parsed_data.get("recommendations", []),
                sources=parsed_data.get("sources", [])
            )
            
            logger.info(f"Generated industry report with {len(analysis_data)} analysis sections and {len(parsed_data.get('recommendations', []))} recommendations")
            return mini_report
                
        except ReportParsingError as e:
            logger.error(f"Failed to parse industry report after {e.attempts} attempts: {e}")
        # NO FALLBACK - Force proper implementation
        raise
    except Exception as e:
        logger.error(f"Error generating industry report: {e}")
        # NO FALLBACK - Force proper implementation
        raise RuntimeError(f"Industry report generation failed: {e}")