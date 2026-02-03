"""
Scraper Pool Node

Node 3 in the Problem Generator agent graph.
Scrapes full content from web search results using Firecrawl/Jina Reader.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config

from ..graph_state import ProblemGraphState
from ...services.web_scraper_service import WebScraperService, ScrapingResult

logger = logging.getLogger(__name__)

# URL filtering patterns
BLOCKED_DOMAINS = [
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.com", "reddit.com"
]

# Comprehensive list of Africa-specific and authoritative sources
PREFERRED_DOMAINS = [
    # International with African focus (HIGH VALUE - statistics-rich)
    "worldbank.org", "afdb.org", "un.org", "who.int", "fao.org",
    "ifc.org", "imf.org", "unctad.org",
    
    # Pan-African news and business
    "africanews.com", "theafricareport.com", "allafrica.com",
    "africabusiness.com", "african.business", "howwemadeitinafrica.com",
    
    # Research and consulting (statistics-rich)
    "gsma.com", "mckinsey.com", "pwc.com", "kpmg.com", "deloitte.com",
    "cgap.org", "ifpri.org", "brookings.edu",
    
    # Country-specific: Ethiopia
    "capitalethiopia.com", "addisfortune.com", "ethiopianmonitor.com",
    "thereporterethiopia.com", "fanabc.com",
    
    # Country-specific: Kenya
    "businessdailyafrica.com", "nation.africa", "standardmedia.co.ke",
    "the-star.co.ke", "capitalfm.co.ke",
    
    # Country-specific: Nigeria
    "guardian.ng", "punchng.com", "businessdayonline.com",
    "nairametrics.com", "premiumtimesng.com", "thisdaylive.com",
    
    # Country-specific: Ghana
    "myjoyonline.com", "ghanaweb.com", "graphic.com.gh",
    "citibusinessnews.com",
    
    # Country-specific: South Africa
    "news24.com", "dailymaverick.co.za", "businesslive.co.za",
    "fin24.com", "iol.co.za",
    
    # Country-specific: Tanzania
    "thecitizen.co.tz", "dailynews.co.tz", "ippmedia.com",
    
    # Country-specific: Uganda
    "monitor.co.ug", "newvision.co.ug", "observer.ug",
    
    # Country-specific: Rwanda
    "newtimes.co.rw", "ktpress.rw",
    
    # General quality news with Africa coverage
    "reuters.com", "bbc.com", "aljazeera.com", "economist.com",
    "ft.com", "bloomberg.com"
]

# Geography-specific source mapping for dynamic boosting
GEOGRAPHY_SOURCES = {
    "Ethiopia": ["capitalethiopia.com", "addisfortune.com", "thereporterethiopia.com", "ethiopianmonitor.com"],
    "Kenya": ["businessdailyafrica.com", "nation.africa", "standardmedia.co.ke", "the-star.co.ke"],
    "Nigeria": ["guardian.ng", "punchng.com", "businessdayonline.com", "nairametrics.com", "premiumtimesng.com"],
    "Ghana": ["myjoyonline.com", "ghanaweb.com", "citibusinessnews.com", "graphic.com.gh"],
    "South Africa": ["news24.com", "dailymaverick.co.za", "businesslive.co.za", "fin24.com"],
    "Tanzania": ["thecitizen.co.tz", "dailynews.co.tz", "ippmedia.com"],
    "Uganda": ["monitor.co.ug", "newvision.co.ug", "observer.ug"],
    "Rwanda": ["newtimes.co.rw", "ktpress.rw"],
    "Senegal": ["seneweb.com", "lequotidien.sn"],
    "Egypt": ["egypttoday.com", "dailynewsegypt.com", "ahram.org.eg"],
    "Morocco": ["moroccoworldnews.com", "hespress.com"]
}

# Content quality thresholds
MIN_CONTENT_LENGTH = 500  # Minimum characters for useful content
MAX_CONTENT_LENGTH = 10000  # Maximum to avoid overwhelming passages


@traceable(name="scraper_pool_node")
async def scraper_pool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 3: Scraper Pool
    
    Scrapes full content from web search results using Firecrawl/Jina Reader.
    Filters and prioritizes URLs for quality content extraction.
    
    Args:
        state: Current workflow state with search results
        
    Returns:
        Updated workflow state with scraped content
    """
    logger.info("Starting scraper pool")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "scraper_pool"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        scraper_config = agent_config.get("scraper", {})
        
        # Get search results from db_hits and web_hits
        db_hits = state.get("db_hits", [])
        web_hits = state.get("web_hits", [])
        docs = db_hits + web_hits
        
        if not docs:
            logger.warning("No search results found for scraping")
            state["scraped_content"] = []
            return state
        
        logger.info(f"Starting content scraping for {len(docs)} URLs (DB: {len(db_hits)}, Web: {len(web_hits)})")
        
        # =============================================
        # FILTER AND PRIORITIZE URLS
        # =============================================
        
        # Filter and score URLs
        scored_urls = []
        
        for doc in docs:
            url = doc.get("url", "")
            if not url:
                continue
                
            # Parse URL
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
            except Exception:
                continue
            
            # Skip blocked domains
            if any(blocked in domain for blocked in BLOCKED_DOMAINS):
                logger.debug(f"Skipping blocked domain: {domain}")
                continue
            
            # Get user geography for source prioritization
            user_params = state.get("params", {})
            user_geography = user_params.get("geography", [""])
            user_geography_str = user_geography[0] if user_geography else ""
            
            # Calculate URL priority score with geography context
            score = calculate_url_score(doc, domain, user_geography_str)
            
            if score > 0:
                scored_urls.append({
                    "url": url,
                    "score": score,
                    "doc_data": doc
                })
        
        # Sort by score - scrape all URLs for maximum content coverage
        scored_urls.sort(key=lambda x: x["score"], reverse=True)
        # Remove artificial limit - attempt to scrape all available URLs
        max_urls = scraper_config.get("max_urls", len(scored_urls))  # Default to all URLs
        selected_urls = scored_urls[:max_urls] if max_urls < len(scored_urls) else scored_urls
        
        logger.info(f"Selected {len(selected_urls)} URLs for scraping (from {len(docs)} total) - attempting all available URLs")
        
        # =============================================
        # EXECUTE PARALLEL SCRAPING
        # =============================================
        
        # Extract URLs for scraping
        urls_to_scrape = [url_data["url"] for url_data in selected_urls]
        
        # Use the web scraper service
        async with WebScraperService(
            timeout=scraper_config.get("timeout", 30),
            max_content_length=scraper_config.get("max_content_length", 50000)
        ) as scraper:
            scraping_results = await scraper.scrape_urls(
                urls_to_scrape,
                max_concurrent=scraper_config.get("concurrent_limit", 8)  # Increased from 5 to 15 for better performance
            )
        
        # =============================================
        # PROCESS SCRAPING RESULTS
        # =============================================
        
        scraped_content = []
        scraping_stats = {
            "attempted": len(selected_urls),
            "successful": 0,
            "failed": 0,
            "empty_content": 0,
            "total_content_length": 0
        }
        
        for i, result in enumerate(scraping_results):
            if not result.success:
                logger.warning(f"Scraping failed for {result.url}: {result.error}")
                scraping_stats["failed"] += 1
                continue
            
            if not result.content:
                scraping_stats["empty_content"] += 1
                continue
            
            # Validate content quality
            content = result.content
            if len(content) < 100:  # Minimum content length
                logger.debug(f"Content too short ({len(content)} chars): {result.url}")
                scraping_stats["empty_content"] += 1
                continue
            
            # Create content object with metadata
            content_obj = {
                "url": result.url,
                "title": result.title,
                "content": content,
                "content_length": result.content_length,
                "scraping_method": result.method,
                "scraped_at": datetime.now().isoformat(),
                "source_query": selected_urls[i].get("doc_data", {}).get("source_query", ""),
                "search_type": selected_urls[i].get("doc_data", {}).get("search_type", "")
            }
            
            scraped_content.append(content_obj)
            scraping_stats["successful"] += 1
            scraping_stats["total_content_length"] += len(content)
        
        # =============================================
        # STORE RESULTS
        # =============================================
        
        state["scraped_content"] = scraped_content
        state["scraping_stats"] = scraping_stats
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        scraper_metrics = {
            "urls_attempted": scraping_stats["attempted"],
            "urls_successful": scraping_stats["successful"],
            "success_rate": scraping_stats["successful"] / max(scraping_stats["attempted"], 1),
            "total_content_chars": scraping_stats["total_content_length"],
            "avg_content_length": scraping_stats["total_content_length"] / max(scraping_stats["successful"], 1),
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["scraper_pool"] = scraper_metrics
        
        logger.info(f"Scraper pool completed successfully")
        logger.info(f"Scraped {scraping_stats['successful']}/{scraping_stats['attempted']} URLs")
        logger.info(f"Total content: {scraping_stats['total_content_length']:,} characters")
        
        return state
        
    except Exception as e:
        error_msg = f"Scraper pool failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state


def calculate_url_score(hit: Dict[str, Any], domain: str, user_geography: str = None) -> float:
    """
    Calculate priority score for a URL based on various factors.
    
    Args:
        hit: Search result hit data
        domain: Parsed domain name
        
    Returns:
        Priority score (higher = better)
    """
    score = 1.0  # Base score
    
    # Domain reputation bonus
    if any(preferred in domain for preferred in PREFERRED_DOMAINS):
        score += 2.0
    
    # Geography-specific source bonus (highest priority)
    if user_geography and user_geography in GEOGRAPHY_SOURCES:
        geo_sources = GEOGRAPHY_SOURCES[user_geography]
        if any(geo_source in domain for geo_source in geo_sources):
            score += 5.0  # High boost for geography-specific sources
            logger.debug(f"Geography boost applied for {domain} (user geography: {user_geography})")
    
    # Government/organization domains
    if domain.endswith(('.gov', '.org', '.edu')):
        score += 1.5
    
    # African domains
    african_tlds = ['.za', '.ng', '.ke', '.gh', '.tz', '.ug', '.rw', '.et', '.eg', '.ma']
    if any(domain.endswith(tld) for tld in african_tlds):
        score += 1.0
    
    # Content quality indicators
    title = hit.get("title", "").lower()
    snippet = hit.get("snippet", "").lower()
    
    # Problem-indicating keywords
    problem_keywords = [
        "challenge", "problem", "issue", "lack", "shortage", "crisis",
        "difficulty", "barrier", "obstacle", "gap", "need", "struggle"
    ]
    
    keyword_count = sum(1 for keyword in problem_keywords 
                       if keyword in title or keyword in snippet)
    score += keyword_count * 0.3
    
    # Recent content bonus
    published_at = hit.get("published_at")
    if published_at:
        try:
            # Simple recency check (this would need proper date parsing)
            if "2024" in str(published_at) or "2023" in str(published_at):
                score += 0.5
        except Exception:
            pass
    
    # Search type bonus
    search_type = hit.get("search_type", "")
    if search_type == "news":
        score += 0.5
    elif search_type == "deep":
        score += 0.3
    
    return score


# Old scrape_single_url function removed - now using WebScraperService
