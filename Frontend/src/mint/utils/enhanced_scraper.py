"""
Enhanced Web Scraper Service

A robust web scraping service that provides multiple fallback strategies:
1. trafilatura (primary) - Fast, high-quality article extraction
2. Playwright (fallback) - For JS-heavy sites that require rendering
3. httpx + BeautifulSoup (fallback) - Basic HTTP scraping
4. Firecrawl (optional fallback) - If API key is configured

This service is designed to maximize scraping success rate by:
- Using trafilatura first (fast, handles most news/blog sites)
- Falling back to Playwright for JS-heavy sites
- Respecting rate limits with per-domain delays
- Caching results to avoid redundant fetches
"""

import asyncio
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

# Try to import trafilatura
TRAFILATURA_AVAILABLE = False
try:
    import trafilatura
    from trafilatura.settings import use_config
    TRAFILATURA_AVAILABLE = True
except ImportError:
    pass

# Try to import playwright
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# Try to import firecrawl
FIRECRAWL_AVAILABLE = False
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    url: str
    title: str = ""
    content: str = ""
    success: bool = False
    error: Optional[str] = None
    method: str = "unknown"
    content_length: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ScrapingStats:
    """Statistics for a batch scraping operation."""
    total_urls: int = 0
    successful: int = 0
    failed: int = 0
    by_method: Dict[str, int] = field(default_factory=dict)
    total_content_length: int = 0
    avg_content_length: float = 0.0
    processing_time_ms: int = 0


class EnhancedScraperService:
    """
    Enhanced web scraper with multiple fallback strategies.
    
    Usage:
        async with EnhancedScraperService() as scraper:
            results = await scraper.scrape_urls(urls)
    """
    
    # Domains that are known to block scrapers
    BLOCKED_DOMAINS = [
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "youtube.com", "tiktok.com", "pinterest.com", "reddit.com",
        "x.com", "threads.net"
    ]
    
    # Domains that typically require JS rendering
    JS_HEAVY_DOMAINS = [
        "bloomberg.com", "wsj.com", "ft.com", "economist.com",
        "statista.com", "forbes.com", "businessinsider.com",
        "medium.com", "substack.com", "ghost.io"
    ]
    
    # High-quality source domains (prioritize these)
    PRIORITY_DOMAINS = [
        "worldbank.org", "imf.org", "un.org", "who.int", "fao.org",
        "reuters.com", "bbc.com", "aljazeera.com", "apnews.com",
        "mckinsey.com", "bcg.com", "gartner.com", "deloitte.com",
        "nature.com", "sciencedirect.com", "springer.com"
    ]
    
    def __init__(
        self,
        timeout: int = 30,
        max_content_length: int = 100000,
        use_playwright: bool = True,
        use_firecrawl: bool = True,
        rate_limit_delay: float = 0.5,
        max_retries: int = 2
    ):
        """
        Initialize the enhanced scraper service.
        
        Args:
            timeout: Request timeout in seconds
            max_content_length: Maximum content length to extract
            use_playwright: Whether to use Playwright as fallback
            use_firecrawl: Whether to use Firecrawl as fallback
            rate_limit_delay: Delay between requests to same domain (seconds)
            max_retries: Maximum retries per URL
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.use_firecrawl = use_firecrawl and FIRECRAWL_AVAILABLE
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        
        # HTTP client
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Playwright browser
        self.playwright = None
        self.browser = None
        
        # Firecrawl client
        self.firecrawl_app = None
        if self.use_firecrawl:
            api_key = os.getenv('FIRECRAWL_API_KEY')
            if api_key:
                try:
                    self.firecrawl_app = FirecrawlApp(api_key=api_key)
                    logger.info("Firecrawl initialized as fallback")
                except Exception as e:
                    logger.warning(f"Failed to initialize Firecrawl: {e}")
                    self.firecrawl_app = None
        
        # Rate limiting: track last request time per domain
        self.domain_last_request: Dict[str, float] = {}
        
        # Cache for already scraped content (URL hash -> content)
        self.cache: Dict[str, ScrapingResult] = {}
        
        # Configure trafilatura for better extraction
        if TRAFILATURA_AVAILABLE:
            self.trafilatura_config = use_config()
            self.trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
            self.trafilatura_config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")
        
        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        self._ua_index = 0
        
        logger.info(f"EnhancedScraperService initialized: trafilatura={TRAFILATURA_AVAILABLE}, playwright={self.use_playwright}, firecrawl={self.firecrawl_app is not None}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        
        # Initialize Playwright browser if enabled
        if self.use_playwright:
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                logger.info("Playwright browser initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Playwright: {e}")
                self.use_playwright = False
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()
        
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _get_user_agent(self) -> str:
        """Get rotating user agent."""
        ua = self.user_agents[self._ua_index % len(self.user_agents)]
        self._ua_index += 1
        return ua
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""
    
    def _should_skip_domain(self, url: str) -> bool:
        """Check if domain should be skipped."""
        domain = self._get_domain(url)
        return any(blocked in domain for blocked in self.BLOCKED_DOMAINS)
    
    def _needs_js_rendering(self, url: str) -> bool:
        """Check if URL likely needs JavaScript rendering."""
        domain = self._get_domain(url)
        return any(js_domain in domain for js_domain in self.JS_HEAVY_DOMAINS)
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    async def _apply_rate_limit(self, url: str):
        """Apply rate limiting for domain."""
        domain = self._get_domain(url)
        if domain in self.domain_last_request:
            elapsed = time.time() - self.domain_last_request[domain]
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.domain_last_request[domain] = time.time()
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize extracted content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'Cookie Policy.*?$',
            r'Privacy Policy.*?$',
            r'Terms of Service.*?$',
            r'Subscribe to.*?newsletter.*?$',
            r'Follow us on.*?$',
            r'Share this article.*?$',
            r'Read more:.*?$',
            r'Advertisement.*?$',
            r'ADVERTISEMENT.*?$',
        ]
        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Truncate if too long
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length] + "..."
        
        return content.strip()
    
    async def _scrape_with_trafilatura(self, url: str) -> Optional[ScrapingResult]:
        """
        Scrape using trafilatura - fast and high quality for articles.
        """
        if not TRAFILATURA_AVAILABLE:
            return None
        
        try:
            await self._apply_rate_limit(url)
            
            # Fetch HTML first
            headers = {
                "User-Agent": self._get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            html = response.text
            
            # Extract with trafilatura
            content = trafilatura.extract(
                html,
                config=self.trafilatura_config,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_recall=True
            )
            
            if not content or len(content) < 100:
                logger.debug(f"trafilatura extraction too short for {url}")
                return None
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html)
            title = metadata.title if metadata else ""
            
            # If no title from metadata, try BeautifulSoup
            if not title:
                soup = BeautifulSoup(html, 'lxml')
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else self._get_domain(url)
            
            content = self._clean_content(content)
            
            return ScrapingResult(
                url=url,
                title=title,
                content=content,
                success=True,
                method="trafilatura",
                content_length=len(content),
                metadata={
                    "author": metadata.author if metadata else None,
                    "date": metadata.date if metadata else None,
                    "sitename": metadata.sitename if metadata else None,
                }
            )
            
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP error for {url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.debug(f"trafilatura failed for {url}: {e}")
            return None
    
    async def _scrape_with_playwright(self, url: str) -> Optional[ScrapingResult]:
        """
        Scrape using Playwright - for JS-heavy sites.
        """
        if not self.use_playwright or not self.browser:
            return None
        
        page = None
        try:
            await self._apply_rate_limit(url)
            
            page = await self.browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": self._get_user_agent()
            })
            
            # Navigate and wait for content to load
            await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
            
            # Wait a bit more for dynamic content
            await asyncio.sleep(1)
            
            # Get page content
            html = await page.content()
            
            # Try trafilatura extraction on the rendered HTML
            if TRAFILATURA_AVAILABLE:
                content = trafilatura.extract(
                    html,
                    config=self.trafilatura_config,
                    include_comments=False,
                    include_tables=True
                )
            else:
                # Fallback to BeautifulSoup
                soup = BeautifulSoup(html, 'lxml')
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()
                content = soup.get_text(separator='\n', strip=True)
            
            if not content or len(content) < 100:
                return None
            
            # Get title
            title = await page.title() or self._get_domain(url)
            
            content = self._clean_content(content)
            
            return ScrapingResult(
                url=url,
                title=title,
                content=content,
                success=True,
                method="playwright",
                content_length=len(content)
            )
            
        except PlaywrightTimeout:
            logger.debug(f"Playwright timeout for {url}")
            return None
        except Exception as e:
            logger.debug(f"Playwright failed for {url}: {e}")
            return None
        finally:
            if page:
                await page.close()
    
    async def _scrape_with_httpx(self, url: str) -> Optional[ScrapingResult]:
        """
        Scrape using basic httpx + BeautifulSoup.
        """
        try:
            await self._apply_rate_limit(url)
            
            headers = {
                "User-Agent": self._get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
            }
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            # Handle PDFs
            if 'application/pdf' in content_type:
                return await self._handle_pdf(url, response.content)
            
            # Handle HTML
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                return None
            
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                element.decompose()
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else self._get_domain(url)
            
            # Try to find main content area
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_=re.compile(r'content|article|post|entry', re.I)) or
                soup.find('div', id=re.compile(r'content|article|post|entry', re.I)) or
                soup.body
            )
            
            if not main_content:
                return None
            
            # Extract text with structure
            paragraphs = []
            for elem in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = elem.get_text().strip()
                if text and len(text) > 20:
                    if elem.name.startswith('h'):
                        paragraphs.append(f"\n### {text}\n")
                    else:
                        paragraphs.append(text)
            
            content = '\n\n'.join(paragraphs)
            
            if not content or len(content) < 100:
                return None
            
            content = self._clean_content(content)
            
            return ScrapingResult(
                url=url,
                title=title,
                content=content,
                success=True,
                method="httpx",
                content_length=len(content)
            )
            
        except Exception as e:
            logger.debug(f"httpx failed for {url}: {e}")
            return None
    
    async def _handle_pdf(self, url: str, content: bytes) -> Optional[ScrapingResult]:
        """Handle PDF content extraction."""
        try:
            from pypdf import PdfReader
            import io
            
            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            
            for i, page in enumerate(reader.pages[:50]):  # Limit pages
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")
            
            content = '\n\n'.join(text_parts)
            
            if not content or len(content) < 100:
                return None
            
            content = self._clean_content(content)
            
            # Extract title from metadata or URL
            title = ""
            if reader.metadata:
                title = reader.metadata.get('/Title', '') or ''
            if not title:
                title = url.split('/')[-1].replace('.pdf', '').replace('-', ' ').replace('_', ' ')
            
            return ScrapingResult(
                url=url,
                title=title,
                content=content,
                success=True,
                method="pdf",
                content_length=len(content),
                metadata={"pages": len(reader.pages)}
            )
            
        except Exception as e:
            logger.debug(f"PDF extraction failed for {url}: {e}")
            return None
    
    async def _scrape_with_firecrawl(self, url: str) -> Optional[ScrapingResult]:
        """
        Scrape using Firecrawl API as last resort.
        """
        if not self.firecrawl_app:
            return None
        
        try:
            # Firecrawl is synchronous, run in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.firecrawl_app.scrape_url(url, formats=['markdown'])
            )
            
            if not result or 'data' not in result:
                return None
            
            data = result['data']
            content = data.get('markdown', '') or data.get('html', '')
            
            if not content or len(content) < 100:
                return None
            
            # Clean HTML tags if present
            if '<' in content and '>' in content:
                content = re.sub(r'<[^>]+>', ' ', content)
            
            content = self._clean_content(content)
            title = data.get('metadata', {}).get('title', self._get_domain(url))
            
            return ScrapingResult(
                url=url,
                title=title,
                content=content,
                success=True,
                method="firecrawl",
                content_length=len(content)
            )
            
        except Exception as e:
            logger.debug(f"Firecrawl failed for {url}: {e}")
            return None
    
    async def scrape_url(self, url: str) -> ScrapingResult:
        """
        Scrape a single URL with multiple fallback strategies.
        
        Order of attempts:
        1. trafilatura (fast, good for articles)
        2. Playwright (for JS-heavy sites)
        3. httpx + BeautifulSoup (basic fallback)
        4. Firecrawl (last resort if configured)
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapingResult with content or error
        """
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return ScrapingResult(
                url=url,
                success=False,
                error="Invalid URL",
                method="validation"
            )
        
        # Check cache
        cache_key = self._get_cache_key(url)
        if cache_key in self.cache:
            logger.debug(f"Cache hit for {url}")
            return self.cache[cache_key]
        
        # Skip blocked domains
        if self._should_skip_domain(url):
            return ScrapingResult(
                url=url,
                success=False,
                error="Blocked domain",
                method="blocked"
            )
        
        # Determine if JS rendering is likely needed
        needs_js = self._needs_js_rendering(url)
        
        result = None
        
        # Strategy 1: If JS-heavy, try Playwright first
        if needs_js and self.use_playwright:
            logger.debug(f"Trying Playwright first for JS-heavy site: {url}")
            result = await self._scrape_with_playwright(url)
            if result and result.success:
                self.cache[cache_key] = result
                return result
        
        # Strategy 2: Try trafilatura (fast, good for most sites)
        if TRAFILATURA_AVAILABLE:
            logger.debug(f"Trying trafilatura for {url}")
            result = await self._scrape_with_trafilatura(url)
            if result and result.success:
                self.cache[cache_key] = result
                return result
        
        # Strategy 3: Try Playwright as fallback
        if self.use_playwright and not needs_js:
            logger.debug(f"Trying Playwright fallback for {url}")
            result = await self._scrape_with_playwright(url)
            if result and result.success:
                self.cache[cache_key] = result
                return result
        
        # Strategy 4: Try basic httpx
        logger.debug(f"Trying httpx for {url}")
        result = await self._scrape_with_httpx(url)
        if result and result.success:
            self.cache[cache_key] = result
            return result
        
        # Strategy 5: Try Firecrawl as last resort
        if self.firecrawl_app:
            logger.debug(f"Trying Firecrawl for {url}")
            result = await self._scrape_with_firecrawl(url)
            if result and result.success:
                self.cache[cache_key] = result
                return result
        
        # All methods failed
        return ScrapingResult(
            url=url,
            success=False,
            error="All scraping methods failed",
            method="failed"
        )
    
    async def scrape_urls(
        self,
        urls: List[str],
        max_concurrent: int = 10
    ) -> Tuple[List[ScrapingResult], ScrapingStats]:
        """
        Scrape multiple URLs concurrently with statistics.
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent scraping tasks
            
        Returns:
            Tuple of (results list, statistics)
        """
        start_time = time.time()
        
        # Deduplicate URLs
        unique_urls = list(dict.fromkeys(urls))
        logger.info(f"Scraping {len(unique_urls)} unique URLs (from {len(urls)} total)")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                return await self.scrape_url(url)
        
        # Execute all scraping tasks
        tasks = [scrape_with_semaphore(url) for url in unique_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and collect stats
        final_results = []
        stats = ScrapingStats(total_urls=len(unique_urls))
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ScrapingResult(
                    url=unique_urls[i],
                    success=False,
                    error=str(result),
                    method="exception"
                ))
                stats.failed += 1
            else:
                final_results.append(result)
                if result.success:
                    stats.successful += 1
                    stats.total_content_length += result.content_length
                    stats.by_method[result.method] = stats.by_method.get(result.method, 0) + 1
                else:
                    stats.failed += 1
        
        # Calculate averages
        if stats.successful > 0:
            stats.avg_content_length = stats.total_content_length / stats.successful
        
        stats.processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Scraping completed: {stats.successful}/{stats.total_urls} successful")
        logger.info(f"Methods used: {stats.by_method}")
        logger.info(f"Total content: {stats.total_content_length:,} chars in {stats.processing_time_ms}ms")
        
        return final_results, stats


# Convenience function for simple use cases
async def scrape_urls_simple(
    urls: List[str],
    max_concurrent: int = 10,
    timeout: int = 30
) -> List[ScrapingResult]:
    """
    Simple function to scrape URLs without managing context.
    
    Args:
        urls: List of URLs to scrape
        max_concurrent: Maximum concurrent tasks
        timeout: Timeout per request
        
    Returns:
        List of ScrapingResult objects
    """
    async with EnhancedScraperService(timeout=timeout) as scraper:
        results, _ = await scraper.scrape_urls(urls, max_concurrent=max_concurrent)
        return results


async def extract_sources_enhanced(
    search_results: List[Any],
    state: Optional[Dict[str, Any]] = None,
    max_concurrent: int = 15,
    timeout: int = 30
) -> List[Dict[str, Any]]:
    """
    Extract content from search results using enhanced scraping.
    
    This function is designed to be a drop-in replacement for the
    _extract_sources functions in PESTEL and INDUSTRY agents.
    
    Args:
        search_results: List of search result objects with 'url' and 'title' attributes
        state: Optional workflow state (unused but kept for API compatibility)
        max_concurrent: Maximum concurrent scraping tasks
        timeout: Timeout per request in seconds
        
    Returns:
        List of source documents as dictionaries with:
        - title: str
        - url: str  
        - source: str
        - content: str
        - timestamp: str
        - metadata: dict
    """
    if not search_results:
        logger.warning("No search results provided for extraction")
        return []
    
    # Extract URLs from search results
    urls = []
    url_to_result = {}
    for result in search_results:
        url = getattr(result, 'url', None) or result.get('url') if isinstance(result, dict) else None
        if url:
            url_str = str(url)
            urls.append(url_str)
            url_to_result[url_str] = result
    
    logger.info(f"🔍 Enhanced extraction starting for {len(urls)} URLs")
    logger.info(f"   Methods available: trafilatura={TRAFILATURA_AVAILABLE}, playwright={PLAYWRIGHT_AVAILABLE}")
    
    # Scrape all URLs
    async with EnhancedScraperService(
        timeout=timeout,
        max_content_length=100000,
        use_playwright=PLAYWRIGHT_AVAILABLE
    ) as scraper:
        scrape_results, stats = await scraper.scrape_urls(urls, max_concurrent=max_concurrent)
    
    # Convert to source documents format
    source_documents = []
    current_time = datetime.now().isoformat()
    
    for result in scrape_results:
        if not result.success:
            logger.debug(f"Skipping failed scrape: {result.url} - {result.error}")
            continue
        
        if not result.content or len(result.content) < 100:
            logger.debug(f"Skipping empty/short content: {result.url}")
            continue
        
        # Get original search result for metadata
        original = url_to_result.get(result.url, {})
        
        # Extract domain for source field
        domain = ""
        try:
            domain = urlparse(result.url).netloc
        except:
            pass
        
        source_doc = {
            "title": result.title or getattr(original, 'title', domain),
            "url": result.url,
            "source": getattr(original, 'source', domain) if hasattr(original, 'source') else domain,
            "content": result.content,
            "timestamp": current_time,
            "metadata": {
                "content_type": "text/html",
                "domain": domain,
                "extraction_date": current_time,
                "content_length": result.content_length,
                "extraction_method": result.method,
                "word_count": len(result.content.split()),
                **result.metadata
            },
            "relevance_score": 0.0,  # Will be set in ranking step
            "trust_score": 0.0       # Will be set in ranking step
        }
        
        source_documents.append(source_doc)
    
    logger.info(f"✅ Enhanced extraction completed: {len(source_documents)}/{len(urls)} sources extracted")
    logger.info(f"   Methods used: {stats.by_method}")
    logger.info(f"   Total content: {stats.total_content_length:,} characters")
    
    return source_documents
