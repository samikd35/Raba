"""
Web Scraper Service for Problem Generator

This module provides web scraping functionality using the EnhancedScraperService
which implements multiple fallback strategies:
1. trafilatura (primary) - Fast, high-quality article extraction
2. Playwright (fallback) - For JS-heavy sites
3. httpx + BeautifulSoup (fallback) - Basic HTTP scraping
4. Firecrawl (optional) - Last resort if API key configured
"""

import logging
import asyncio
import aiohttp
import os
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
import re

# Import enhanced scraper
from src.mint.utils.enhanced_scraper import (
    EnhancedScraperService,
    ScrapingResult as EnhancedScrapingResult,
    ScrapingStats,
    TRAFILATURA_AVAILABLE,
    PLAYWRIGHT_AVAILABLE
)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    FirecrawlApp = None

logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Result of a web scraping operation."""
    url: str
    title: str
    content: str
    success: bool
    error: Optional[str] = None
    method: str = "unknown"
    content_length: int = 0
    
    @classmethod
    def from_enhanced(cls, enhanced: EnhancedScrapingResult) -> "ScrapingResult":
        """Convert from EnhancedScrapingResult."""
        return cls(
            url=enhanced.url,
            title=enhanced.title,
            content=enhanced.content,
            success=enhanced.success,
            error=enhanced.error,
            method=enhanced.method,
            content_length=enhanced.content_length
        )

class WebScraperService:
    """
    Service for scraping web content using EnhancedScraperService.
    
    This class provides backward compatibility while leveraging the new
    enhanced scraper with trafilatura + Playwright fallback support.
    """
    
    def __init__(self, timeout: int = 30, max_content_length: int = 50000, use_firecrawl_fallback: bool = True):
        """
        Initialize the web scraper service.
        
        Args:
            timeout: Request timeout in seconds
            max_content_length: Maximum content length to extract
            use_firecrawl_fallback: Whether to use Firecrawl as fallback
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.use_firecrawl_fallback = use_firecrawl_fallback
        
        # Initialize enhanced scraper (will be started in __aenter__)
        self.enhanced_scraper: Optional[EnhancedScraperService] = None
        
        # Legacy support: keep these for any code that checks them
        self.session = None
        self.firecrawl_app = None
        
        # Log available methods
        methods = ["httpx+bs4"]
        if TRAFILATURA_AVAILABLE:
            methods.insert(0, "trafilatura")
        if PLAYWRIGHT_AVAILABLE:
            methods.append("playwright")
        if use_firecrawl_fallback and FIRECRAWL_AVAILABLE and os.getenv('FIRECRAWL_API_KEY'):
            methods.append("firecrawl")
        
        logger.info(f"WebScraperService initialized with methods: {' -> '.join(methods)}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize enhanced scraper
        self.enhanced_scraper = EnhancedScraperService(
            timeout=self.timeout,
            max_content_length=self.max_content_length,
            use_playwright=PLAYWRIGHT_AVAILABLE,
            use_firecrawl=self.use_firecrawl_fallback
        )
        await self.enhanced_scraper.__aenter__()
        
        # Legacy support: also initialize aiohttp session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.enhanced_scraper:
            await self.enhanced_scraper.__aexit__(exc_type, exc_val, exc_tb)
        if self.session:
            await self.session.close()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common navigation/footer text patterns
        patterns_to_remove = [
            r'Cookie Policy.*?$',
            r'Privacy Policy.*?$',
            r'Terms of Service.*?$',
            r'Subscribe to.*?newsletter.*?$',
            r'Follow us on.*?$',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _extract_content_with_bs4(self, html: str, url: str) -> Dict[str, str]:
        """Extract content using BeautifulSoup."""
        if not BS4_AVAILABLE:
            raise ImportError("BeautifulSoup4 is required for HTML parsing")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else ""
        
        # Try to find main content areas
        content_selectors = [
            'main', 'article', '[role="main"]', '.content', '.main-content',
            '.article-content', '.post-content', '.entry-content', '#content'
        ]
        
        content_text = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content_text = content_elem.get_text(separator=' ', strip=True)
                break
        
        # Fallback to body if no main content found
        if not content_text:
            body = soup.find('body')
            if body:
                content_text = body.get_text(separator=' ', strip=True)
        
        # Clean the content
        content_text = self._clean_text(content_text)
        
        # Truncate if too long
        if len(content_text) > self.max_content_length:
            content_text = content_text[:self.max_content_length] + "..."
        
        return {
            'title': title,
            'content': content_text
        }
    
    async def _scrape_with_firecrawl(self, url: str) -> Dict[str, str]:
        """Scrape content using Firecrawl API."""
        if not self.firecrawl_app:
            raise RuntimeError("Firecrawl not initialized")
        
        try:
            # Use Firecrawl to scrape the URL
            result = self.firecrawl_app.scrape_url(
                url, 
                formats=['markdown', 'html']
            )
            
            # Extract content from Firecrawl response
            if result and 'data' in result:
                data = result['data']
                title = data.get('metadata', {}).get('title', '')
                content = data.get('markdown', '') or data.get('html', '')
                
                # Clean HTML tags if we got HTML content
                if content and '<' in content and '>' in content:
                    import re
                    content = re.sub(r'<[^>]+>', ' ', content)
                
                content = self._clean_text(content)
                
                # Truncate if too long
                if len(content) > self.max_content_length:
                    content = content[:self.max_content_length] + "..."
                
                return {
                    'title': title,
                    'content': content
                }
            
            return {'title': '', 'content': ''}
            
        except Exception as e:
            logger.warning(f"Firecrawl scraping failed for {url}: {e}")
            raise
    
    async def scrape_url(self, url: str) -> ScrapingResult:
        """
        Scrape content from a single URL using enhanced scraper.
        
        Uses multiple fallback strategies:
        1. trafilatura (fast, good for articles)
        2. Playwright (for JS-heavy sites)
        3. httpx + BeautifulSoup (basic fallback)
        4. Firecrawl (last resort if configured)
        
        Args:
            url: URL to scrape
            
        Returns:
            ScrapingResult with the scraped content
        """
        logger.debug(f"Scraping URL: {url}")
        
        # Use enhanced scraper if available
        if self.enhanced_scraper:
            enhanced_result = await self.enhanced_scraper.scrape_url(url)
            return ScrapingResult.from_enhanced(enhanced_result)
        
        # Fallback to legacy behavior if enhanced scraper not initialized
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ScrapingResult(
                    url=url,
                    title="",
                    content="",
                    success=False,
                    error="Invalid URL",
                    method="validation"
                )
            
            # Make HTTP request
            if not self.session:
                raise RuntimeError("Scraper session not initialized. Use async context manager.")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return ScrapingResult(
                        url=url,
                        title="",
                        content="",
                        success=False,
                        error=f"HTTP {response.status}",
                        method="http"
                    )
                
                # Get content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    return ScrapingResult(
                        url=url,
                        title="",
                        content="",
                        success=False,
                        error=f"Unsupported content type: {content_type}",
                        method="content-type"
                    )
                
                # Read HTML content
                html = await response.text()
                
                # Extract content using BeautifulSoup
                if BS4_AVAILABLE:
                    extracted = self._extract_content_with_bs4(html, url)
                    return ScrapingResult(
                        url=url,
                        title=extracted['title'],
                        content=extracted['content'],
                        success=True,
                        method="beautifulsoup",
                        content_length=len(extracted['content'])
                    )
                else:
                    # Fallback: simple text extraction
                    text = re.sub(r'<[^>]+>', ' ', html)
                    text = self._clean_text(text)
                    
                    if len(text) > self.max_content_length:
                        text = text[:self.max_content_length] + "..."
                    
                    return ScrapingResult(
                        url=url,
                        title="",
                        content=text,
                        success=True,
                        method="regex",
                        content_length=len(text)
                    )
        
        except asyncio.TimeoutError:
            return ScrapingResult(
                url=url,
                title="",
                content="",
                success=False,
                error="Request timeout",
                method="timeout"
            )
        except Exception as e:
            logger.warning(f"Legacy scraping failed for {url}: {str(e)}")
            return ScrapingResult(
                url=url,
                title="",
                content="",
                success=False,
                error=str(e),
                method="failed"
            )
    
    async def scrape_urls(self, urls: List[str], max_concurrent: int = 10) -> List[ScrapingResult]:
        """
        Scrape multiple URLs concurrently using enhanced scraper.
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum number of concurrent requests (default increased to 10)
            
        Returns:
            List of ScrapingResult objects
        """
        logger.info(f"Scraping {len(urls)} URLs with max {max_concurrent} concurrent requests")
        
        # Use enhanced scraper if available
        if self.enhanced_scraper:
            enhanced_results, stats = await self.enhanced_scraper.scrape_urls(urls, max_concurrent=max_concurrent)
            
            # Convert to ScrapingResult format
            results = [ScrapingResult.from_enhanced(r) for r in enhanced_results]
            
            # Log detailed stats
            logger.info(f"Enhanced scraper stats: {stats.successful}/{stats.total_urls} successful")
            logger.info(f"Methods used: {stats.by_method}")
            logger.info(f"Total content: {stats.total_content_length:,} chars")
            
            return results
        
        # Fallback to legacy concurrent scraping
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ScrapingResult(
                    url=urls[i],
                    title="",
                    content="",
                    success=False,
                    error=str(result),
                    method="exception"
                ))
            else:
                final_results.append(result)
        
        successful = sum(1 for r in final_results if r.success)
        logger.info(f"Successfully scraped {successful}/{len(urls)} URLs")
        
        return final_results


# Export for use by other agents (PESTEL, INDUSTRY)
__all__ = ['WebScraperService', 'ScrapingResult']
