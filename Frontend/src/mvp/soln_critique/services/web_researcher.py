"""
Web research execution using Brave Search API
Executes search queries in parallel batches with rate limiting
"""
import logging
import asyncio
from typing import Dict, Any, List
from src.mint.providers.search import BraveSearchProvider, SearchConfig

logger = logging.getLogger(__name__)


class WebResearcher:
    """Executes web searches and aggregates results"""
    
    # Domains to deprioritize (move to end of results) or filter out
    # These are often misleading or low-quality sources for business research
    DEPRIORITIZED_DOMAINS = [
        'ubuy.et',
        'ubuy.com',
        'alibaba.com',
        'aliexpress.com',
    ]
    
    def __init__(self):
        self.search_provider = BraveSearchProvider(
            SearchConfig(
                provider_name="brave",
                api_key_env_var="BRAVE_API_KEY",
                num_results=10,
                safe_search=True
            )
        )
        self.batch_size = 5  # Process 5 queries at a time
        self.batch_delay = 1.0  # 1 second delay between batches
    
    async def execute_research(
        self,
        queries: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Execute all search queries in parallel batches
        
        Args:
            queries: List of query objects with category, query, priority
            
        Returns:
            Dictionary of results grouped by category
        """
        try:
            logger.info(f"🔍 Executing {len(queries)} search queries")
            
            # Group queries by category
            categorized_queries = self._group_by_category(queries)
            
            # Execute in parallel batches per category
            results_by_category = {}
            
            for category, category_queries in categorized_queries.items():
                logger.info(f"   Searching {category}: {len(category_queries)} queries")
                category_results = await self._execute_category_queries(
                    category_queries
                )
                results_by_category[category] = category_results
            
            # Count total results
            total_results = sum(
                sum(len(q.get('results', [])) for q in cat_results)
                for cat_results in results_by_category.values()
            )
            
            logger.info(f"✅ Completed web research: {total_results} total results")
            return results_by_category
            
        except Exception as e:
            logger.error(f"❌ Web research failed: {e}")
            return {}
    
    def _group_by_category(
        self,
        queries: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group queries by category"""
        categorized = {}
        for query in queries:
            category = query.get('category', 'general')
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(query)
        return categorized
    
    async def _execute_category_queries(
        self,
        queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute queries for a category in parallel batches"""
        results = []
        
        # Process in batches to respect rate limits
        for i in range(0, len(queries), self.batch_size):
            batch = queries[i:i + self.batch_size]
            
            logger.info(f"      Batch {i // self.batch_size + 1}: {len(batch)} queries")
            
            # Execute batch in parallel
            tasks = [
                self._execute_single_query(query)
                for query in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for query, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"      Query failed: '{query.get('query', 'unknown')}' - {result}")
                    # Add empty result to maintain structure
                    results.append({
                        'query': query.get('query', ''),
                        'query_id': query.get('id', ''),
                        'results': [],
                        'error': str(result)
                    })
                else:
                    results.append({
                        'query': query.get('query', ''),
                        'query_id': query.get('id', ''),
                        'results': result
                    })
            
            # Delay between batches (except for last batch)
            if i + self.batch_size < len(queries):
                await asyncio.sleep(self.batch_delay)
        
        return results
    
    def _is_deprioritized_domain(self, url: str) -> bool:
        """Check if URL is from a deprioritized domain"""
        url_lower = url.lower()
        for domain in self.DEPRIORITIZED_DOMAINS:
            if domain in url_lower:
                return True
        return False
    
    def _filter_and_sort_results(self, results: List[Dict]) -> List[Dict]:
        """Filter out or deprioritize results from low-quality domains
        
        Strategy: Move deprioritized domains to the end of results,
        so they're less likely to be used as citations (top 3 per query are used)
        """
        good_results = []
        deprioritized_results = []
        
        for result in results:
            url = result.get('url', '')
            if self._is_deprioritized_domain(url):
                logger.debug(f"      Deprioritizing result from: {url}")
                deprioritized_results.append(result)
            else:
                good_results.append(result)
        
        # Return good results first, then deprioritized at the end
        # This effectively removes them from citation consideration since
        # only top 3 results per query are used
        return good_results + deprioritized_results
    
    async def _execute_single_query(self, query: Dict[str, Any]) -> List[Dict]:
        """Execute a single search query"""
        try:
            search_query = query.get('query', '')
            if not search_query:
                raise ValueError("Empty query")
            
            # Execute search
            search_results = await self.search_provider.search(search_query)
            
            # Convert to dict format
            results = []
            for result in search_results:
                results.append({
                    'title': result.title,
                    'url': str(result.url),
                    'snippet': result.snippet,
                    'source': result.source,
                    'position': result.position,
                    'published_date': result.published_date
                })
            
            # Filter and deprioritize low-quality domains
            results = self._filter_and_sort_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"      Search failed for query '{query.get('query', 'unknown')}': {e}")
            raise
