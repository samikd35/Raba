"""
Search Fan-out Node

Node 2 in the Problem Generator agent graph.
Executes three parallel searches: dbSearch (Supabase), newsSearch (Brave/Serper), deepSearch (Brave).
"""

import logging
import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config, get_search_config
from src.mint.providers.factory import get_provider

from ..graph_state import ProblemGraphState
from src.pgen.services.problem_database_service import ProblemDatabaseService
from src.pgen.services.embedding_service import EmbeddingService
from src.pgen.utils.logging_config import get_contextual_logger

logger = logging.getLogger(__name__)

# Search-type specific recency configuration
SEARCH_RECENCY_CONFIG = {
    "news": 90,      # Current events - 3 months
    "deep": 365,     # Research/reports - 1 year  
    "database": None # No recency filter for curated DB
}

# Authoritative research source modifiers for deep search
RESEARCH_SOURCE_MODIFIERS = [
    "site:worldbank.org",
    "site:afdb.org",
    "site:un.org",
    "site:who.int",
    "site:fao.org",
    "site:gsma.com",
    "site:mckinsey.com",
    "site:ifc.org",
    "site:cgap.org",
    "site:ifpri.org"
]


@traceable(name="search_fanout_node")
async def search_fanout_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 2: Search Fan-out
    
    Executes three parallel searches:
    - dbSearch: Searches existing problem statements in Supabase
    - newsSearch: Searches recent news using Brave/Serper API
    - deepSearch: Searches comprehensive web content using Brave API
    
    Args:
        state: Current workflow state containing queries from previous node
        
    Returns:
        Updated state with search results from all three sources
    """
    # Get contextual logger with job_id and user_id from state
    job_id = state.get("job_id")
    user_id = state.get("user_id")
    ctx_logger = get_contextual_logger("src.pgen.agents.nodes.search_fanout", job_id=job_id, user_id=user_id)
    
    ctx_logger.info("Starting search fan-out node")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "search_fanout"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        search_config = get_search_config(state)
        
        # Get queries from previous node
        queries = state.get("queries", [])
        if not queries:
            raise ValueError("No queries found for search execution")
        
        ctx_logger.info(f"Executing parallel searches for {len(queries)} queries")
        
        # Initialize results containers
        db_hits = []
        web_hits = []
        search_metadata = {
            "db_search": {"status": "pending", "results": 0, "time_ms": 0},
            "news_search": {"status": "pending", "results": 0, "time_ms": 0},
            "deep_search": {"status": "pending", "results": 0, "time_ms": 0}
        }
        
        # =============================================
        # EXECUTE PARALLEL SEARCHES
        # =============================================
        
        async def run_parallel_searches():
            """Execute all three searches concurrently."""
            
            # Get search configuration
            search_config = get_search_config(state)
            
            # Add recency parameters if not present
            if "recency_days" not in search_config:
                search_config["recency_days"] = 90  # Default to 90 days for recency
            
            # Configure search providers
            news_provider = search_config.get("news_provider", "brave")
            deep_provider = search_config.get("deep_provider", "brave")
            
            ctx_logger.info(f"Using search providers - News: {news_provider}, Deep: {deep_provider}")
            ctx_logger.info(f"Recency filter: {search_config['recency_days']} days")
            
            # Get user parameters for geography-specific searches
            user_params = state.get("params", {})
            user_geography = user_params.get("geography", ["Africa"])
            user_geography_str = user_geography[0] if user_geography else "Africa"
            user_industry = user_params.get("industry", [""])
            user_industry_str = user_industry[0] if user_industry else ""
            
            ctx_logger.info(f"Search context - Geography: {user_geography_str}, Industry: {user_industry_str}")
            
            # Execute parallel searches with user context
            tasks = [
                db_search_task(queries, state),
                news_search_task(queries, search_config, news_provider, user_geography_str, user_industry_str),
                deep_search_task(queries, search_config, deep_provider, user_geography_str, user_industry_str)
            ]
            
            # Execute all searches concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return results
        
        # Run the parallel searches
        search_results = await run_parallel_searches()
        
        # =============================================
        # PROCESS SEARCH RESULTS
        # =============================================
        
        # Process DB search results
        if isinstance(search_results[0], Exception):
            ctx_logger.error(f"DB search failed: {search_results[0]}")
            search_metadata["db_search"]["status"] = "failed"
        else:
            db_results, db_time = search_results[0]
            db_hits.extend(db_results)
            search_metadata["db_search"]["status"] = "completed"
            search_metadata["db_search"]["results"] = len(db_results)
            search_metadata["db_search"]["time_ms"] = db_time
            ctx_logger.info(f"DB search completed: {len(db_results)} results in {db_time}ms")
        
        # Process news search results
        if isinstance(search_results[1], Exception):
            ctx_logger.error(f"News search failed: {search_results[1]}")
            search_metadata["news_search"]["status"] = "failed"
        else:
            news_results, news_time = search_results[1]
            web_hits.extend(news_results)
            search_metadata["news_search"]["status"] = "completed"
            search_metadata["news_search"]["results"] = len(news_results)
            search_metadata["news_search"]["time_ms"] = news_time
            ctx_logger.info(f"News search completed: {len(news_results)} results in {news_time}ms")
        
        # Process deep search results
        if isinstance(search_results[2], Exception):
            ctx_logger.error(f"Deep search failed: {search_results[2]}")
            search_metadata["deep_search"]["status"] = "failed"
        else:
            deep_results, deep_time = search_results[2]
            web_hits.extend(deep_results)
            search_metadata["deep_search"]["status"] = "completed"
            search_metadata["deep_search"]["results"] = len(deep_results)
            search_metadata["deep_search"]["time_ms"] = deep_time
            ctx_logger.info(f"Deep search completed: {len(deep_results)} results in {deep_time}ms")
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["db_hits"] = db_hits
        state["web_hits"] = web_hits
        state["search_metadata"] = search_metadata
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        search_metrics = {
            "total_queries": len(queries),
            "db_results": len(db_hits),
            "web_results": len(web_hits),
            "total_results": len(db_hits) + len(web_hits),
            "total_time_ms": total_time,
            "parallel_execution": True
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["search_fanout"] = search_metrics
        
        ctx_logger.info(f"Search fan-out completed successfully")
        ctx_logger.info(f"Total results: {len(db_hits)} DB + {len(web_hits)} web = {len(db_hits) + len(web_hits)}")
        
        return state
        
    except Exception as e:
        error_msg = f"Search fan-out failed: {str(e)}"
        ctx_logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


async def db_search_task(queries: List[str], state: Dict[str, Any]) -> tuple:
    """
    Execute database search using Supabase RPC on problem_statements pgvector index.
    
    Args:
        queries: List of search queries
        state: Current workflow state
        
    Returns:
        Tuple of (results, processing_time_ms)
    """
    start_time = datetime.now()
    
    try:
        logger.info("Starting database search")
        
        # Get database service
        db_service = ProblemDatabaseService(use_service_role=True)
        
        # Initialize services
        db_service = ProblemDatabaseService(use_service_role=True)
        embedding_service = EmbeddingService()
        params = state.get("params", {})
        
        # Execute searches for each query
        all_results = []
        
        # USE ALL QUERIES - African data is scarce, we need maximum coverage
        for query in queries:  # Use all queries for comprehensive DB search
            try:
                # Generate embedding for the query
                embedding_result = await embedding_service.generate_embedding(query)
                if not embedding_result:
                    logger.warning(f"Failed to generate embedding for query: {query}")
                    continue
                
                # Use vector similarity search
                results = db_service.search_similar_problems(
                    embedding=embedding_result.embedding,
                    threshold=0.7,
                    limit=3  # Limit per query
                )
                
                # Add origin tag and query context
                for result in results:
                    result["origin"] = "db"
                    result["source_query"] = query
                    result["search_type"] = "vector_similarity"
                
                all_results.extend(results)
                
            except Exception as e:
                logger.warning(f"DB search failed for query '{query}': {str(e)}")
                continue
        
        # Remove duplicates based on problem ID
        unique_results = []
        seen_ids = set()
        
        for result in all_results:
            problem_id = result.get("id")
            if problem_id and problem_id not in seen_ids:
                unique_results.append(result)
                seen_ids.add(problem_id)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"Database search completed: {len(unique_results)} unique results")
        return unique_results, processing_time
        
    except Exception as e:
        logger.error(f"Database search failed: {str(e)}")
        return [], int((datetime.now() - start_time).total_seconds() * 1000)


async def news_search_task(queries: List[str], search_config: Dict[str, Any], provider_name: Optional[str] = None, user_geography: str = "Africa", user_industry: str = "") -> tuple:
    """
    Execute news search using Brave/Serper for current news and reports.
    
    Args:
        queries: List of search queries
        search_config: Search configuration
        
    Returns:
        Tuple of (results, processing_time_ms)
    """
    start_time = datetime.now()
    
    try:
        logger.info("Starting news search")
        
        # Initialize search provider
        if not provider_name:
            provider_name = search_config.get("news_provider", "brave")
        
        # Get search provider configuration
        max_results = search_config.get("max_results", 5)
        
        # Initialize search provider
        
        if provider_name.lower() == 'brave':
            from src.mint.providers.search import BraveSearchProvider, SearchConfig
            try:
                config = SearchConfig(
                    provider_name="brave",
                    api_key_env_var="BRAVE_API_KEY",
                    num_results=max_results
                )
                search_provider = BraveSearchProvider(config=config)
                logger.info(f"Initialized Brave search provider with {max_results} max results")
            except Exception as e:
                logger.warning(f"Failed to initialize Brave search provider: {e}")
                
        elif provider_name.lower() == 'serper':
            from src.mint.providers.search import SerperSearchProvider, SearchConfig
            try:
                config = SearchConfig(
                    provider_name="serper",
                    api_key_env_var="SERPER_API_KEY",
                    num_results=max_results
                )
                search_provider = SerperSearchProvider(config=config)
                logger.info(f"Initialized Serper search provider with {max_results} max results")
            except Exception as e:
                logger.warning(f"Failed to initialize Serper search provider: {e}")
        
        if not search_provider:
            logger.warning("No valid news search provider available")
            return [], 0
        
        all_results = []
        
        # USE ALL QUERIES for news search - African data is scarce
        for query in queries:
            try:
                # Add news-specific modifiers with USER'S EXACT GEOGRAPHY (not generic "Africa")
                current_year = datetime.now().year
                last_year = current_year - 1
                
                # NEWS SEARCH: Use 90-day recency for current events
                recency_days = SEARCH_RECENCY_CONFIG["news"]  # 90 days for news
                date_str = ""
                
                # Add date range for specific providers
                if provider_name.lower() == "brave":
                    # Brave supports time range parameters
                    date_str = f"when:{recency_days}d"
                elif provider_name.lower() == "serper":
                    # For Serper, use natural language date range
                    if recency_days <= 7:
                        date_str = "this week"
                    elif recency_days <= 30:
                        date_str = "this month"
                    elif recency_days <= 90:
                        date_str = "past 3 months"
                    else:
                        date_str = f"{current_year} OR {last_year}"
                
                # Use USER'S EXACT GEOGRAPHY instead of generic "Africa"
                # This is critical for relevance - "Ethiopia" should return Ethiopian results
                news_query = f"{query} {user_geography} news report {date_str}"
                
                # Execute search
                results = await search_provider.search(news_query)
                
                # Process results
                for result in results:
                    processed_result = {
                        "title": getattr(result, 'title', ""),
                        "url": str(getattr(result, 'url', "")),
                        "snippet": getattr(result, 'snippet', ""),
                        "published_at": getattr(result, 'timestamp', None),
                        "source": getattr(result, 'source', ""),
                        "origin": "web",
                        "search_type": "news",
                        "source_query": query
                    }
                    all_results.append(processed_result)
                
            except Exception as e:
                logger.warning(f"News search failed for query '{query}': {str(e)}")
                continue
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"News search completed: {len(all_results)} results")
        return all_results, processing_time
        
    except Exception as e:
        logger.error(f"News search failed: {str(e)}")
        return [], int((datetime.now() - start_time).total_seconds() * 1000)


async def deep_search_task(queries: List[str], search_config: Dict[str, Any], provider_name: Optional[str] = None, user_geography: str = "Africa", user_industry: str = "") -> tuple:
    """
    Execute deep search using Brave for comprehensive web search.
    
    Args:
        queries: List of search queries
        search_config: Search configuration
        
    Returns:
        Tuple of (results, processing_time_ms)
    """
    start_time = datetime.now()
    
    try:
        logger.info("Starting deep search")
        
        # Initialize search provider
        if not provider_name:
            provider_name = search_config.get("deep_provider", "brave")
        
        # Get search provider configuration
        max_results = search_config.get("max_results", 7)
        
        # Initialize search provider
        
        if provider_name.lower() == 'brave':
            from src.mint.providers.search import BraveSearchProvider, SearchConfig
            try:
                config = SearchConfig(
                    provider_name="brave",
                    api_key_env_var="BRAVE_API_KEY",
                    num_results=max_results
                )
                search_provider = BraveSearchProvider(config=config)
                logger.info(f"Initialized Brave search provider with {max_results} max results")
            except Exception as e:
                logger.warning(f"Failed to initialize Brave search provider: {e}")
                
        elif provider_name.lower() == 'serper':
            from src.mint.providers.search import SerperSearchProvider, SearchConfig
            try:
                config = SearchConfig(
                    provider_name="serper",
                    api_key_env_var="SERPER_API_KEY",
                    num_results=max_results
                )
                search_provider = SerperSearchProvider(config=config)
                logger.info(f"Initialized Serper search provider with {max_results} max results")
            except Exception as e:
                logger.warning(f"Failed to initialize Serper search provider: {e}")
        
        if not search_provider:
            logger.warning("No valid deep search provider available")
            return [], 0
        
        all_results = []
        
        # USE ALL QUERIES for deep search - maximize research coverage
        for idx, query in enumerate(queries):
            try:
                # Add context with USER'S EXACT GEOGRAPHY and research focus
                current_year = datetime.now().year
                
                # DEEP SEARCH: Use 365-day recency for research/reports (longer timeframe)
                recency_days = SEARCH_RECENCY_CONFIG["deep"]  # 365 days for research
                date_str = ""
                
                # Add date range for specific providers
                if provider_name.lower() == "brave":
                    # Brave supports time range parameters
                    if recency_days <= 7:
                        date_str = "when:7d"
                    elif recency_days <= 30:
                        date_str = "when:30d"
                    elif recency_days <= 90:
                        date_str = "when:90d"
                    else:
                        date_str = f"when:365d"
                elif provider_name.lower() == "serper":
                    # For Serper, use natural language date range
                    if recency_days <= 30:
                        date_str = "this month"
                    elif recency_days <= 90:
                        date_str = "past 3 months"
                    else:
                        date_str = f"{current_year}"
                
                # Use USER'S EXACT GEOGRAPHY and INDUSTRY instead of generic terms
                # Add authoritative source modifiers for some queries to get high-quality research
                source_modifier = ""
                if idx < len(RESEARCH_SOURCE_MODIFIERS):
                    source_modifier = RESEARCH_SOURCE_MODIFIERS[idx]
                
                # Build targeted deep search query
                if user_industry:
                    deep_query = f"{user_industry} problems {user_geography} research study {date_str} {source_modifier}".strip()
                else:
                    deep_query = f"{query} {user_geography} research study report {date_str} {source_modifier}".strip()
                
                # Execute search
                results = await search_provider.search(deep_query)
                
                # Process results
                for result in results:
                    processed_result = {
                        "title": getattr(result, 'title', ""),
                        "url": str(getattr(result, 'url', "")),
                        "snippet": getattr(result, 'snippet', ""),
                        "published_at": getattr(result, 'timestamp', None),
                        "source": getattr(result, 'source', ""),
                        "origin": "web",
                        "search_type": "deep",
                        "source_query": query
                    }
                    all_results.append(processed_result)
                
            except Exception as e:
                logger.warning(f"Deep search failed for query '{query}': {str(e)}")
                continue
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"Deep search completed: {len(all_results)} results")
        return all_results, processing_time
        
    except Exception as e:
        logger.error(f"Deep search failed: {str(e)}")
        return [], int((datetime.now() - start_time).total_seconds() * 1000)
