"""
Bootstrap Research Service

Performs bounded web research to enhance user-provided context.
Research can ENRICH but not CHANGE the core idea invariants.

Uses LLM-based query generation following the pattern from
src/mvp/soln_critique/services/query_planner.py
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# System prompt for query generation - follows Solution Critique pattern
QUERY_GENERATION_SYSTEM_PROMPT = """<role>
You are a research query planner for validating business ideas through web search.
</role>

<task>
Generate 8-12 targeted web search queries to validate a proposed business idea.
</task>

<query_categories>
1. market_validation (2-3 queries): market size, demand, customer behavior
2. competitive_analysis (2-3 queries): competitors, alternatives, market leaders
3. industry_trends (2 queries): industry trends, technology adoption
4. regulatory (1-2 queries): regulations, compliance, licensing if relevant
</query_categories>

<query_requirements>
- Queries must be CONCISE (< 80 characters each)
- Include geography when relevant
- Prioritize queries: 1=high, 2=medium, 3=low based on criticality
- Focus on finding evidence to validate key assumptions
</query_requirements>

<examples>
GOOD: "Ethiopia drip irrigation market size 2024"
BAD: "Primary target customers are smallholder farmers who use drip irrigation systems..."
</examples>

<output_schema>
{{
  "queries": [
    {{
      "id": "query-001",
      "category": "market_validation|competitive_analysis|industry_trends|regulatory",
      "query": "concise search query under 80 chars",
      "priority": 1
    }}
  ]
}}
</output_schema>

<output_rules>
- Keep queries SHORT and SEARCHABLE
- Do NOT include full sentences or paragraphs
- Return ONLY valid JSON. No markdown, no explanations.
</output_rules>"""


class BootstrapResearchService:
    """
    Service for performing bounded web research to enhance bootstrap context.
    
    Key constraint: Research can only enhance, not change the idea's invariants
    (customer segment, geography, problem, solution type).
    
    Uses LLM-based query generation like src/mvp/soln_critique/services/query_planner.py
    """
    
    def __init__(self):
        """Initialize research service with web search provider."""
        self._init_services()
        logger.info("Bootstrap Research Service initialized")
    
    def _init_services(self):
        """Initialize required services."""
        try:
            from src.mvp.soln_critique.services.web_researcher import WebResearcher
            self.web_researcher = WebResearcher()
        except Exception as e:
            logger.warning(f"Could not initialize WebResearcher: {e}")
            self.web_researcher = None
        
        try:
            from src.mvp.bootstrap.services.embedding_service import get_bootstrap_embedding_service
            self.embedding_service = get_bootstrap_embedding_service()
        except Exception as e:
            logger.warning(f"Could not initialize embedding service: {e}")
            self.embedding_service = None
        
        # Initialize Azure OpenAI provider for query generation
        self.openai_provider = None
        try:
            from src.mint.api.ai.providers import OpenAIProvider, LLMConfig
            from src.mint.api.ai.config import get_client_config, ModelUseCase
            
            provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
            
            # Note: gpt-5-mini doesn't support temperature, uses max_completion_tokens
            is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
            
            llm_kwargs = {
                "provider_name": "azure_openai" if client_config.get("azure_endpoint") else "openai",
                "model_name": model_name,
                "azure_endpoint": client_config.get("azure_endpoint"),
                "api_version": client_config.get("api_version"),
                "api_key": client_config.get("api_key")
            }
            
            if is_gpt5_model:
                llm_kwargs["max_tokens"] = 16000  # gpt-5-mini needs large token budget
            else:
                llm_kwargs["temperature"] = 0.3
                llm_kwargs["max_tokens"] = 2000
            
            llm_config = LLMConfig(**llm_kwargs)
            
            self.openai_provider = OpenAIProvider(config=llm_config)
            logger.info(f"✅ Research Service: OpenAI provider initialized with model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI provider for query generation: {e}")
    
    async def generate_research_queries(
        self,
        project_id: str,
        tenant_id: str,
        context_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate research queries using LLM based on bootstrap context.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            context_summary: Summary of user-provided context
            
        Returns:
            List of query objects with category and priority
        """
        logger.info(f"🔍 Planning research queries for project {project_id}")
        
        # Try LLM-based generation first
        if self.openai_provider:
            try:
                queries = await self._generate_queries_with_llm(context_summary)
                if queries:
                    logger.info(f"✅ LLM generated {len(queries)} research queries")
                    return queries
            except Exception as e:
                logger.warning(f"LLM query generation failed: {e}, using fallback")
        
        # Fallback to simple rule-based queries
        logger.info("Using fallback static queries")
        return self._get_fallback_queries(context_summary)
    
    async def _generate_queries_with_llm(
        self,
        context_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate queries using LLM."""
        # Build user prompt with context
        user_prompt = self._build_user_prompt(context_summary)
        
        messages = [
            {"role": "system", "content": QUERY_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.openai_provider.generate_responses(messages)
        # Handle both dict and LLMResponse object formats
        if isinstance(response, dict):
            response_text = response.get("content", "{}")
        elif hasattr(response, 'content'):
            response_text = response.content  # LLMResponse object
        else:
            response_text = str(response)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
                queries = data.get("queries", [])
                
                # Ensure all queries have required fields and are short enough
                valid_queries = []
                for q in queries:
                    if q.get("query") and len(q["query"]) < 100:
                        valid_queries.append({
                            "id": q.get("id", str(uuid.uuid4())),
                            "category": q.get("category", "general"),
                            "query": q["query"][:80],  # Enforce max length
                            "priority": q.get("priority", 2)
                        })
                
                return valid_queries
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
        
        return []
    
    def _build_user_prompt(self, context_summary: Dict[str, Any]) -> str:
        """Build user prompt with context for query generation."""
        customer = context_summary.get("customer_segment", "Not specified")
        geography = context_summary.get("geography", "Not specified")
        problem = context_summary.get("problem", "Not specified")
        solution = context_summary.get("solution", "Not specified")
        industry = context_summary.get("industry", "Not specified")
        
        # Truncate long text to keep prompt manageable
        def truncate(text, max_len=300):
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text
        
        return f"""Generate research queries for this business idea:

**Target Customers:** {truncate(customer)}

**Geography:** {truncate(geography)}

**Problem Being Solved:** {truncate(problem)}

**Proposed Solution:** {truncate(solution)}

**Industry:** {truncate(industry)}

Generate 8-12 concise search queries (< 80 characters each) to validate this idea.
Focus on market size, competition, regulations, and industry trends.
Include the geography in relevant queries.
"""
    
    def _get_fallback_queries(self, context_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback queries if LLM generation fails."""
        geography = context_summary.get("geography", "")[:30] or "market"
        industry = context_summary.get("industry", "")[:30] or "business"
        year = datetime.now().year
        
        # Extract just first few words from problem/solution
        problem_words = context_summary.get("problem", "problem")[:50].split()[:3]
        problem_short = " ".join(problem_words)
        
        solution_words = context_summary.get("solution", "solution")[:50].split()[:3]
        solution_short = " ".join(solution_words)
        
        return [
            {
                "id": str(uuid.uuid4()),
                "category": "market_validation",
                "query": f"{geography} {industry} market size {year}"[:80],
                "priority": 1
            },
            {
                "id": str(uuid.uuid4()),
                "category": "market_validation", 
                "query": f"{problem_short} statistics {geography}"[:80],
                "priority": 1
            },
            {
                "id": str(uuid.uuid4()),
                "category": "competitive_analysis",
                "query": f"{solution_short} competitors {geography}"[:80],
                "priority": 2
            },
            {
                "id": str(uuid.uuid4()),
                "category": "competitive_analysis",
                "query": f"{industry} startups {geography} {year}"[:80],
                "priority": 2
            },
            {
                "id": str(uuid.uuid4()),
                "category": "industry_trends",
                "query": f"{industry} trends {year}"[:80],
                "priority": 3
            },
            {
                "id": str(uuid.uuid4()),
                "category": "regulatory",
                "query": f"{industry} regulations {geography}"[:80],
                "priority": 3
            }
        ]
    
    async def execute_research(
        self,
        queries: List[Dict[str, Any]],
        max_results_per_query: int = 5
    ) -> Dict[str, Any]:
        """
        Execute research queries using web search.
        
        Args:
            queries: List of query objects
            max_results_per_query: Max results per query
            
        Returns:
            Research results with numbered sources
        """
        if not self.web_researcher:
            logger.warning("Web researcher not available")
            return {
                "success": False,
                "error": "Web research service not available",
                "results_by_category": {},
                "sources": []
            }
        
        try:
            # Execute research using existing WebResearcher
            results_by_category = await self.web_researcher.execute_research(queries)
            
            # Process and number sources
            all_sources = []
            source_number = 1
            
            for category, category_results in results_by_category.items():
                for query_result in category_results:
                    for result in query_result.get("results", []):
                        # Add numbered source
                        all_sources.append({
                            "n": source_number,
                            "title": result.get("title", ""),
                            "publisher": self._extract_publisher(result.get("url", "")),
                            "url": result.get("url", ""),
                            "captured_at": datetime.utcnow().isoformat(),
                            "snippet": result.get("snippet", ""),
                            "category": category,
                            "query": query_result.get("query", "")
                        })
                        source_number += 1
            
            logger.info(f"✅ Research completed: {len(all_sources)} sources found")
            
            return {
                "success": True,
                "results_by_category": results_by_category,
                "sources": all_sources,
                "query_count": len(queries),
                "source_count": len(all_sources)
            }
            
        except Exception as e:
            logger.error(f"❌ Research execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results_by_category": {},
                "sources": []
            }
    
    def _extract_publisher(self, url: str) -> str:
        """Extract publisher/domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return ""
    
    async def store_research_results(
        self,
        project_id: str,
        tenant_id: str,
        research_results: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store research results as embedded chunks.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            research_results: Research results from execute_research
            user_id: User ID for created_by field
            
        Returns:
            True if successful
        """
        if not self.embedding_service:
            logger.warning("Embedding service not available, skipping storage")
            return False
        
        try:
            # Create chunks from research snippets
            chunks = []
            sources = research_results.get("sources", [])
            
            for source in sources:
                snippet = source.get("snippet", "")
                if snippet:
                    chunk = {
                        "id": str(uuid.uuid4()),
                        "content": snippet,
                        "metadata": {
                            "source_type": "bootstrap_web_research",
                            "project_id": project_id,
                            "source_number": source.get("n"),
                            "source_url": source.get("url"),
                            "source_title": source.get("title"),
                            "category": source.get("category"),
                            "captured_at": source.get("captured_at")
                        }
                    }
                    chunks.append(chunk)
            
            if not chunks:
                return True
            
            # Embed chunks
            embedded_chunks = await self.embedding_service.embed_chunks(chunks)
            
            # Store chunks
            stored = await self.embedding_service.store_chunks(
                project_id=project_id,
                tenant_id=tenant_id,
                chunks=embedded_chunks,
                user_id=user_id
            )
            
            logger.info(f"✅ Stored {len(chunks)} research chunks for project {project_id}")
            return stored
            
        except Exception as e:
            logger.error(f"❌ Error storing research results: {e}")
            return False
    
    def format_research_body(
        self,
        research_results: Dict[str, Any],
        max_sources: int = 10
    ) -> Dict[str, Any]:
        """
        Format research results into a body with inline citations.
        
        Args:
            research_results: Research results from execute_research
            max_sources: Maximum sources to include
            
        Returns:
            Dict with 'body' (text with [n] citations) and 'sources' list
        """
        sources = research_results.get("sources", [])[:max_sources]
        
        if not sources:
            return {
                "body": "No research results available.",
                "sources": []
            }
        
        # Group by category
        by_category = {}
        for source in sources:
            cat = source.get("category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(source)
        
        # Build body with citations
        body_parts = []
        
        if "market_validation" in by_category:
            snippets = [f"{s['snippet']} [{s['n']}]" for s in by_category["market_validation"][:3]]
            body_parts.append("**Market Validation**: " + " ".join(snippets))
        
        if "competitive_analysis" in by_category:
            snippets = [f"{s['snippet']} [{s['n']}]" for s in by_category["competitive_analysis"][:3]]
            body_parts.append("**Competitive Landscape**: " + " ".join(snippets))
        
        if "industry_trends" in by_category:
            snippets = [f"{s['snippet']} [{s['n']}]" for s in by_category["industry_trends"][:2]]
            body_parts.append("**Industry Trends**: " + " ".join(snippets))
        
        if "regulatory" in by_category:
            snippets = [f"{s['snippet']} [{s['n']}]" for s in by_category["regulatory"][:2]]
            body_parts.append("**Regulatory Considerations**: " + " ".join(snippets))
        
        body = "\n\n".join(body_parts)
        
        # Format sources list
        formatted_sources = [
            {
                "n": s["n"],
                "title": s["title"],
                "publisher": s["publisher"],
                "url": s["url"],
                "captured_at": s["captured_at"],
                "snippet": s["snippet"][:200] if s.get("snippet") else None
            }
            for s in sources
        ]
        
        return {
            "body": body,
            "sources": formatted_sources
        }


def get_bootstrap_research_service() -> BootstrapResearchService:
    """Factory function for BootstrapResearchService."""
    return BootstrapResearchService()
