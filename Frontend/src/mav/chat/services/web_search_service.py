"""
Web Search Service

Handles bounded web research with evidence extraction for the chat feature.
Uses BraveSearchProvider for search and LLM for evidence extraction.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.mint.providers.search import BraveSearchProvider, SearchConfig, SearchResult
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.providers import OpenAIProvider

from ..models import WebEvidence, DEFAULT_CHAT_CONFIG

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Service for bounded web research with evidence extraction.
    
    Features:
    - Executes bounded search queries (3-6 max)
    - Extracts relevant evidence from search results
    - Returns structured WebEvidence objects
    - Handles rate limiting and timeouts
    """
    
    def __init__(self):
        """Initialize web search service with search provider and LLM."""
        # Initialize Brave Search provider
        search_config = SearchConfig(
            provider_name="brave",
            api_key_env_var="BRAVE_API_KEY",
            num_results=DEFAULT_CHAT_CONFIG.max_web_results_per_query,
            safe_search=True
        )
        self.search_provider = BraveSearchProvider(search_config)
        
        # Get LLM config for evidence extraction
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        self.llm_config = LLMConfig(
            provider_name=str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
            model_name=model_name,
            temperature=0.1,
            max_tokens=16000,  # gpt-5-mini needs large token budget
            azure_endpoint=client_config.get("azure_endpoint"),
            api_version=client_config.get("api_version"),
            api_key=client_config.get("api_key")
        )
        
        # Initialize OpenAI provider for evidence extraction (centralized Responses API)
        self.ai_provider = OpenAIProvider(self.llm_config)
        
        logger.info("✅ WebSearchService initialized")
    
    async def search_and_extract(
        self,
        queries: List[str],
        what_to_extract: List[str],
        user_question: str,
        max_queries: int = None
    ) -> List[WebEvidence]:
        """
        Execute web searches and extract relevant evidence.
        
        Args:
            queries: List of search queries to execute
            what_to_extract: What specific facts to look for
            user_question: Original user question for context
            max_queries: Maximum queries to execute (default from config)
            
        Returns:
            List of WebEvidence objects
        """
        max_queries = max_queries or DEFAULT_CHAT_CONFIG.max_web_queries
        
        # Limit queries
        queries_to_run = queries[:max_queries]
        logger.info(f"🌐 WEB: Executing {len(queries_to_run)} search queries")
        
        all_results: List[SearchResult] = []
        
        # Execute searches (with some parallelism but bounded)
        for i, query in enumerate(queries_to_run):
            try:
                logger.info(f"🌐 WEB: Query {i+1}/{len(queries_to_run)}: {query[:50]}...")
                results = await self.search_provider.search(query)
                all_results.extend(results[:DEFAULT_CHAT_CONFIG.max_web_results_per_query])
                
                # Small delay between queries to avoid rate limiting
                if i < len(queries_to_run) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.warning(f"⚠️ WEB: Search failed for query '{query[:30]}...': {e}")
                continue
        
        if not all_results:
            logger.info("🌐 WEB: No search results found")
            return []
        
        logger.info(f"🌐 WEB: Got {len(all_results)} total results, extracting evidence...")
        
        # Extract evidence from results
        evidence_list = await self._extract_evidence(
            search_results=all_results,
            what_to_extract=what_to_extract,
            user_question=user_question
        )
        
        logger.info(f"✅ WEB: Extracted {len(evidence_list)} evidence items")
        return evidence_list
    
    async def _extract_evidence(
        self,
        search_results: List[SearchResult],
        what_to_extract: List[str],
        user_question: str
    ) -> List[WebEvidence]:
        """
        Extract relevant evidence from search results using LLM.
        
        Args:
            search_results: Raw search results
            what_to_extract: Specific facts to look for
            user_question: Original question for context
            
        Returns:
            List of WebEvidence objects
        """
        if not search_results:
            return []
        
        # Format search results for LLM
        results_text = self._format_results_for_extraction(search_results)
        
        # Build extraction prompt
        extraction_prompt = self._build_extraction_prompt(
            results_text=results_text,
            what_to_extract=what_to_extract,
            user_question=user_question
        )
        
        try:
            # Call LLM for extraction using centralized Responses API
            response = await self.ai_provider.generate_responses(
                messages=[
                    {"role": "system", "content": self._get_extraction_system_prompt()},
                    {"role": "user", "content": extraction_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse response
            import json
            content = response.content
            extracted = json.loads(content)
            
            # Convert to WebEvidence objects
            evidence_list = []
            fetched_at = datetime.utcnow().isoformat()
            
            for item in extracted.get("web_evidence", []):
                try:
                    evidence = WebEvidence(
                        claim=item.get("claim", ""),
                        snippet=item.get("snippet", ""),
                        url=item.get("source", {}).get("url", ""),
                        title=item.get("source", {}).get("title", ""),
                        domain=item.get("source", {}).get("domain", ""),
                        published_at=item.get("source", {}).get("published_at"),
                        fetched_at=fetched_at
                    )
                    if evidence.claim and evidence.url:
                        evidence_list.append(evidence)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse evidence item: {e}")
                    continue
            
            return evidence_list
            
        except Exception as e:
            logger.error(f"❌ Evidence extraction failed: {e}")
            # Fallback: create basic evidence from search snippets
            return self._fallback_evidence(search_results)
    
    def _format_results_for_extraction(self, results: List[SearchResult], max_results: int = 10) -> str:
        """Format search results as text for LLM extraction."""
        lines = []
        
        for i, result in enumerate(results[:max_results], 1):
            lines.append(f"[Result {i}]")
            lines.append(f"Title: {result.title}")
            lines.append(f"URL: {result.url}")
            lines.append(f"Domain: {result.source}")
            if result.published_date:
                lines.append(f"Published: {result.published_date}")
            lines.append(f"Snippet: {result.snippet}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_extraction_system_prompt(self) -> str:
        """Get system prompt for evidence extraction."""
        return """<role>
You are an evidence extractor for an entrepreneurship research assistant.
</role>

<task>
Extract only the evidence relevant to the user's question from web search results.
</task>

<extraction_rules>
- Extract short bullet evidence with minimal paraphrase
- Capture source metadata: title, domain, url, publication date if present
- Do not include unrelated content
- Each claim should be a single factual statement
- Include the specific snippet that supports the claim
- Prioritize recent, authoritative sources (government, research institutions, major news)
</extraction_rules>

<efficiency>
- Extract only the most relevant 3-5 evidence items
- Stop once you have enough evidence to answer the question
- Prefer quality over quantity
</efficiency>

<output_rules>
Return ONLY valid JSON. No markdown, no explanations.
</output_rules>

<output_schema>
{
  "web_evidence": [
    {
      "claim": "The specific factual claim",
      "snippet": "The supporting text from the source",
      "source": {
        "title": "Page title",
        "domain": "example.com",
        "url": "https://example.com/page",
        "published_at": "2024-01-01 or null"
      }
    }
  ]
}
</output_schema>"""
    
    def _build_extraction_prompt(
        self,
        results_text: str,
        what_to_extract: List[str],
        user_question: str
    ) -> str:
        """Build the extraction prompt."""
        what_to_extract_str = "\n".join(f"- {item}" for item in what_to_extract)
        
        return f"""User question: {user_question}

What to extract:
{what_to_extract_str}

UNTRUSTED_WEB_PAGES:
{results_text}

Extract relevant evidence from these search results. Return JSON only."""
    
    def _fallback_evidence(self, results: List[SearchResult]) -> List[WebEvidence]:
        """Create basic evidence from search snippets as fallback."""
        evidence_list = []
        fetched_at = datetime.utcnow().isoformat()
        
        for result in results[:5]:
            if result.snippet:
                evidence = WebEvidence(
                    claim=result.snippet[:200],
                    snippet=result.snippet,
                    url=str(result.url),
                    title=result.title,
                    domain=result.source,
                    published_at=result.published_date,
                    fetched_at=fetched_at
                )
                evidence_list.append(evidence)
        
        return evidence_list
    
    def format_evidence_for_context(
        self,
        evidence_list: List[WebEvidence],
        max_chars: int = 3000
    ) -> str:
        """
        Format web evidence as text for LLM context.
        
        Args:
            evidence_list: List of WebEvidence
            max_chars: Maximum total characters
            
        Returns:
            Formatted text with evidence blocks
        """
        if not evidence_list:
            return "No web evidence available."
        
        lines = []
        total_chars = 0
        
        for i, evidence in enumerate(evidence_list, 1):
            ref_id = f"W{i}"
            header = f"[{ref_id}] {evidence.title} ({evidence.domain})"
            content = f"Claim: {evidence.claim}\nSnippet: {evidence.snippet[:300]}"
            
            block = f"{header}\n{content}\n"
            
            if total_chars + len(block) > max_chars:
                break
            
            lines.append(block)
            total_chars += len(block)
        
        return "\n".join(lines)


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create singleton WebSearchService instance."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
