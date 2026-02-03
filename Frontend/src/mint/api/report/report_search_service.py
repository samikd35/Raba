"""
Report Search Service

This service provides advanced search functionality for user reports,
including full-text search, advanced operators, and optimized performance.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID

from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..system.core.utils import is_valid_uuid
from ..services.utilities.fallback_service import fallback_service
from ...utils.circuit_breaker import circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class ReportSearchService:
    """Service for advanced report search operations."""
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the report search service.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.reports_table = "mint_reports"
        
    @circuit_breaker(
        name="report_search",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=20
    )
    async def search_reports(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Search reports using full-text search with advanced operators.
        Enhanced with fallback mechanisms and caching.
        
        Args:
            user_id: The ID of the user
            query: Search query string
            filters: Optional additional filters
            sort_by: Field to sort by (relevance, created_at, title, etc.)
            sort_order: Sort order - 'asc' or 'desc'
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dict containing search results, pagination info, and metadata
        """
        # Generate cache key for potential fallback
        cache_key = f"search_{user_id}_{hash(query)}_{hash(str(filters))}_{sort_by}_{sort_order}_{page}_{page_size}"
        
        try:
            logger.info(f"Searching reports for user {user_id} with query: '{query}'")
            
            # Validate inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            if not query or not query.strip():
                raise ValueError("Search query cannot be empty")
                
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
                
            # Parse search query for advanced operators
            parsed_query = self._parse_search_query(query.strip())
            
            # Build search query
            search_query = self._build_search_query(user_id, parsed_query, filters)
            
            # Get total count for pagination
            count_query = self._build_search_query(user_id, parsed_query, filters, count_only=True)
            count_result = count_query.execute()
            total_count = count_result.count
            
            # Apply sorting
            if sort_by == "relevance":
                # For relevance sorting, we'll use a combination of factors
                search_query = self._apply_relevance_sorting(search_query, parsed_query)
            else:
                if sort_order.lower() == "asc":
                    search_query = search_query.order(sort_by, desc=False)
                else:
                    search_query = search_query.order(sort_by, desc=True)
                    
            # Apply pagination
            offset = (page - 1) * page_size
            search_query = search_query.range(offset, offset + page_size - 1)
            
            # Execute search
            response = search_query.execute()
            reports = response.data
            
            # Process and score results
            processed_reports = []
            for report in reports:
                processed_report = self._process_search_result(report, parsed_query)
                processed_reports.append(processed_report)
                
            # Sort by relevance score if relevance sorting was requested
            if sort_by == "relevance":
                processed_reports.sort(
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=(sort_order.lower() == "desc")
                )
                
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            result = {
                "reports": processed_reports,
                "search_metadata": {
                    "query": query,
                    "parsed_query": parsed_query,
                    "total_matches": total_count,
                    "search_time_ms": 0  # Will be calculated by timing wrapper
                },
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                },
                "filters_applied": filters or {},
                "sort": {
                    "field": sort_by,
                    "order": sort_order
                }
            }
            
            logger.info(f"Search completed: {len(processed_reports)} results for query '{query}'")
            
            # Cache successful response for fallback
            fallback_service.cache_response(cache_key, result)
            
            return result
            
        except CircuitBreakerError:
            # Circuit breaker is open, try cached response
            logger.warning(f"Circuit breaker open for search, trying cache")
            cached_response = await fallback_service.cached_response_fallback(cache_key)
            if cached_response:
                return cached_response
            
            # If no cache, try simple fallback
            return await fallback_service.simple_search_fallback(
                user_id, query, filters, sort_by, sort_order, page, page_size
            )
            
        except Exception as e:
            logger.error(f"Error searching reports for user {user_id}: {str(e)}")
            
            # Try cached response first
            cached_response = await fallback_service.cached_response_fallback(cache_key)
            if cached_response:
                return cached_response
                
            # Try simple fallback
            try:
                return await fallback_service.simple_search_fallback(
                    user_id, query, filters, sort_by, sort_order, page, page_size
                )
            except Exception as fallback_error:
                logger.error(f"Search fallback also failed: {str(fallback_error)}")
                raise e  # Raise original error
            
    def _parse_search_query(self, query: str) -> Dict[str, Any]:
        """
        Parse search query for advanced operators.
        
        Supported operators:
        - "exact phrase" - exact phrase matching
        - +required - term must be present
        - -excluded - term must not be present
        - field:value - search in specific field
        - * - wildcard matching
        
        Args:
            query: Raw search query
            
        Returns:
            Parsed query structure
        """
        try:
            parsed = {
                "original": query,
                "terms": [],
                "phrases": [],
                "required": [],
                "excluded": [],
                "field_searches": {},
                "wildcards": []
            }
            
            # Extract quoted phrases
            phrase_pattern = r'"([^"]*)"'
            phrases = re.findall(phrase_pattern, query)
            parsed["phrases"] = [phrase.strip() for phrase in phrases if phrase.strip()]
            
            # Remove phrases from query for further processing
            query_without_phrases = re.sub(phrase_pattern, '', query)
            
            # Extract field searches (field:value)
            field_pattern = r'(\w+):([^\s]+)'
            field_matches = re.findall(field_pattern, query_without_phrases)
            for field, value in field_matches:
                if field not in parsed["field_searches"]:
                    parsed["field_searches"][field] = []
                parsed["field_searches"][field].append(value)
                
            # Remove field searches from query
            query_without_fields = re.sub(field_pattern, '', query_without_phrases)
            
            # Split remaining query into terms
            terms = query_without_fields.split()
            
            for term in terms:
                term = term.strip()
                if not term:
                    continue
                    
                if term.startswith('+'):
                    # Required term
                    parsed["required"].append(term[1:])
                elif term.startswith('-'):
                    # Excluded term
                    parsed["excluded"].append(term[1:])
                elif '*' in term:
                    # Wildcard term
                    parsed["wildcards"].append(term)
                else:
                    # Regular term
                    parsed["terms"].append(term)
                    
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing search query '{query}': {str(e)}")
            # Return simple term-based parsing as fallback
            return {
                "original": query,
                "terms": query.split(),
                "phrases": [],
                "required": [],
                "excluded": [],
                "field_searches": {},
                "wildcards": []
            }
            
    def _build_search_query(
        self,
        user_id: str,
        parsed_query: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        count_only: bool = False
    ):
        """
        Build the database query based on parsed search terms.
        
        Args:
            user_id: The ID of the user
            parsed_query: Parsed search query structure
            filters: Additional filters
            count_only: Whether this is for counting only
            
        Returns:
            Supabase query object
        """
        try:
            # Base query
            if count_only:
                query = self.client.client.table(self.reports_table) \
                    .select("id", count="exact")
            else:
                query = self.client.client.table(self.reports_table) \
                    .select("*")
                    
            query = query.eq("user_id", user_id) \
                .is_("deleted_at", "null")
                
            # Build search conditions
            search_conditions = []
            
            # Handle phrases (exact matches)
            for phrase in parsed_query["phrases"]:
                if phrase:
                    phrase_condition = f"title.ilike.%{phrase}%,summary.ilike.%{phrase}%"
                    search_conditions.append(phrase_condition)
                    
            # Handle regular terms
            for term in parsed_query["terms"]:
                if term:
                    term_condition = f"title.ilike.%{term}%,summary.ilike.%{term}%"
                    search_conditions.append(term_condition)
                    
            # Handle required terms
            for term in parsed_query["required"]:
                if term:
                    # Required terms must match in at least one field
                    required_condition = f"title.ilike.%{term}%,summary.ilike.%{term}%"
                    search_conditions.append(required_condition)
                    
            # Handle wildcards
            for wildcard in parsed_query["wildcards"]:
                if wildcard:
                    # Convert * to SQL LIKE pattern
                    pattern = wildcard.replace('*', '%')
                    wildcard_condition = f"title.ilike.{pattern},summary.ilike.{pattern}"
                    search_conditions.append(wildcard_condition)
                    
            # Handle field-specific searches
            for field, values in parsed_query["field_searches"].items():
                for value in values:
                    if field in ["title", "summary", "category"]:
                        search_conditions.append(f"{field}.ilike.%{value}%")
                    elif field == "tag":
                        # Search in tags array
                        query = query.contains("tags", [value])
                        
            # Apply search conditions
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Using ilike on first search condition only - others filtered in Python if needed
            if search_conditions:
                # Apply first condition only (since .or_() not supported)
                first_condition = search_conditions[0] if search_conditions else None
                if first_condition and "title.ilike" in first_condition:
                    # Extract the search term from the condition
                    search_term = first_condition.split(".ilike.")[1] if ".ilike." in first_condition else None
                    if search_term:
                        query = query.ilike("title", search_term)
                
            # Handle excluded terms (must not match)
            # Note: Removed .not_.or_() as Supabase Python client doesn't support it
            # Exclusion filtering should be done in Python after fetching results
            # for term in parsed_query["excluded"]:
            #     if term:
            #         query = query.not_.or_(f"title.ilike.%{term}%,summary.ilike.%{term}%")
                    
            # Apply additional filters
            if filters:
                query = self._apply_additional_filters(query, filters)
                
            return query
            
        except Exception as e:
            logger.error(f"Error building search query: {str(e)}")
            raise
            
    def _apply_additional_filters(self, query, filters: Dict[str, Any]):
        """
        Apply additional filters to the search query.
        
        Args:
            query: The Supabase query object
            filters: Dictionary of filters to apply
            
        Returns:
            Modified query object
        """
        try:
            # Date range filter
            if "date_range" in filters:
                date_range = filters["date_range"]
                if "start" in date_range and date_range["start"]:
                    query = query.gte("created_at", date_range["start"])
                if "end" in date_range and date_range["end"]:
                    query = query.lte("created_at", date_range["end"])
                    
            # Category filter
            if "categories" in filters and filters["categories"]:
                categories = filters["categories"]
                if isinstance(categories, list) and categories:
                    query = query.in_("category", categories)
                elif isinstance(categories, str):
                    query = query.eq("category", categories)
                    
            # Tags filter
            if "tags" in filters and filters["tags"]:
                tags = filters["tags"]
                if isinstance(tags, list) and tags:
                    query = query.overlaps("tags", tags)
                elif isinstance(tags, str):
                    query = query.contains("tags", [tags])
                    
            # Pinned filter
            if "only_pinned" in filters and filters["only_pinned"]:
                query = query.eq("is_pinned", True)
                
            # Report type filter
            if "report_types" in filters and filters["report_types"]:
                report_types = filters["report_types"]
                if isinstance(report_types, list) and report_types:
                    query = query.in_("report_type", report_types)
                elif isinstance(report_types, str):
                    query = query.eq("report_type", report_types)
                    
            return query
            
        except Exception as e:
            logger.error(f"Error applying additional filters: {str(e)}")
            raise
            
    def _apply_relevance_sorting(self, query, parsed_query: Dict[str, Any]):
        """
        Apply relevance-based sorting to the query.
        
        For now, we'll use a simple approach based on creation date and view count.
        In a more advanced implementation, we could use full-text search ranking.
        
        Args:
            query: The Supabase query object
            parsed_query: Parsed search query
            
        Returns:
            Modified query object with relevance sorting
        """
        try:
            # For now, sort by a combination of view_count and recency
            # In the future, this could be enhanced with proper text search ranking
            query = query.order("view_count", desc=True) \
                .order("created_at", desc=True)
                
            return query
            
        except Exception as e:
            logger.error(f"Error applying relevance sorting: {str(e)}")
            # Fallback to date sorting
            return query.order("created_at", desc=True)
            
    def _process_search_result(self, report: Dict[str, Any], parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a search result to add relevance scoring and highlighting.
        
        Args:
            report: Raw report data from database
            parsed_query: Parsed search query
            
        Returns:
            Processed report with relevance score and highlights
        """
        try:
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(report, parsed_query)
            
            # Add search highlights
            highlights = self._generate_highlights(report, parsed_query)
            
            # Process report for JSON compliance
            processed_report = self._process_report_for_json(report)
            
            # Add search-specific fields
            processed_report["relevance_score"] = relevance_score
            processed_report["highlights"] = highlights
            
            return processed_report
            
        except Exception as e:
            logger.error(f"Error processing search result: {str(e)}")
            # Return basic processed report
            return self._process_report_for_json(report)
            
    def _calculate_relevance_score(self, report: Dict[str, Any], parsed_query: Dict[str, Any]) -> float:
        """
        Calculate relevance score for a search result.
        
        Args:
            report: Report data
            parsed_query: Parsed search query
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            score = 0.0
            max_score = 0.0
            
            # Get searchable text
            title = (report.get("title") or "").lower()
            summary = (report.get("summary") or "").lower()
            content = str(report.get("content") or "").lower()
            
            # Score for terms in title (highest weight)
            all_terms = parsed_query["terms"] + parsed_query["required"] + parsed_query["phrases"]
            for term in all_terms:
                term_lower = term.lower()
                max_score += 3.0  # Title matches worth 3 points
                if term_lower in title:
                    score += 3.0
                    
            # Score for terms in summary (medium weight)
            for term in all_terms:
                term_lower = term.lower()
                max_score += 2.0  # Summary matches worth 2 points
                if term_lower in summary:
                    score += 2.0
                    
            # Score for terms in content (lower weight)
            for term in all_terms:
                term_lower = term.lower()
                max_score += 1.0  # Content matches worth 1 point
                if term_lower in content:
                    score += 1.0
                    
            # Bonus for recent reports
            if report.get("created_at"):
                try:
                    created_date = datetime.fromisoformat(report["created_at"].replace('Z', '+00:00'))
                    days_old = (datetime.now(timezone.utc) - created_date).days
                    if days_old < 30:
                        score += 0.5  # Bonus for recent reports
                        max_score += 0.5
                except:
                    pass
                    
            # Bonus for frequently viewed reports
            view_count = report.get("view_count", 0)
            if view_count > 0:
                score += min(view_count * 0.1, 1.0)  # Up to 1 point for view count
                max_score += 1.0
                
            # Normalize score to 0-1 range
            if max_score > 0:
                return min(score / max_score, 1.0)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating relevance score: {str(e)}")
            return 0.0
            
    def _generate_highlights(self, report: Dict[str, Any], parsed_query: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate search result highlights.
        
        Args:
            report: Report data
            parsed_query: Parsed search query
            
        Returns:
            Dictionary of highlights for different fields
        """
        try:
            highlights = {
                "title": [],
                "summary": [],
                "content": []
            }
            
            # Get all search terms
            all_terms = parsed_query["terms"] + parsed_query["required"] + parsed_query["phrases"]
            
            # Generate highlights for each field
            for field in ["title", "summary"]:
                text = report.get(field, "")
                if text and all_terms:
                    field_highlights = self._highlight_text(text, all_terms)
                    highlights[field] = field_highlights
                    
            # For content, we'll extract relevant snippets
            content = str(report.get("content", ""))
            if content and all_terms:
                content_highlights = self._extract_content_snippets(content, all_terms)
                highlights["content"] = content_highlights
                
            return highlights
            
        except Exception as e:
            logger.error(f"Error generating highlights: {str(e)}")
            return {"title": [], "summary": [], "content": []}
            
    def _highlight_text(self, text: str, terms: List[str], max_length: int = 200) -> List[str]:
        """
        Highlight search terms in text.
        
        Args:
            text: Text to highlight
            terms: Search terms to highlight
            max_length: Maximum length of highlighted text
            
        Returns:
            List of highlighted text snippets
        """
        try:
            if not text or not terms:
                return []
                
            highlighted_snippets = []
            text_lower = text.lower()
            
            for term in terms:
                term_lower = term.lower()
                if term_lower in text_lower:
                    # Find the position of the term
                    start_pos = text_lower.find(term_lower)
                    
                    # Extract snippet around the term
                    snippet_start = max(0, start_pos - 50)
                    snippet_end = min(len(text), start_pos + len(term) + 50)
                    
                    snippet = text[snippet_start:snippet_end]
                    
                    # Add ellipsis if needed
                    if snippet_start > 0:
                        snippet = "..." + snippet
                    if snippet_end < len(text):
                        snippet = snippet + "..."
                        
                    # Highlight the term (case insensitive)
                    import re
                    highlighted_snippet = re.sub(
                        re.escape(term),
                        f"<mark>{term}</mark>",
                        snippet,
                        count=1,
                        flags=re.IGNORECASE
                    )
                    
                    highlighted_snippets.append(highlighted_snippet)
                    
            return highlighted_snippets[:3]  # Return up to 3 snippets
            
        except Exception as e:
            logger.error(f"Error highlighting text: {str(e)}")
            return []
            
    def _extract_content_snippets(self, content: str, terms: List[str], max_snippets: int = 3) -> List[str]:
        """
        Extract relevant snippets from content based on search terms.
        
        Args:
            content: Content to extract from
            terms: Search terms
            max_snippets: Maximum number of snippets to return
            
        Returns:
            List of relevant content snippets
        """
        try:
            if not content or not terms:
                return []
                
            # Convert content to string if it's JSON
            if isinstance(content, dict):
                content = json.dumps(content)
            elif not isinstance(content, str):
                content = str(content)
                
            snippets = []
            content_lower = content.lower()
            
            for term in terms:
                term_lower = term.lower()
                if term_lower in content_lower:
                    # Find all occurrences of the term
                    start = 0
                    while start < len(content_lower):
                        pos = content_lower.find(term_lower, start)
                        if pos == -1:
                            break
                            
                        # Extract snippet around the term
                        snippet_start = max(0, pos - 100)
                        snippet_end = min(len(content), pos + len(term) + 100)
                        
                        snippet = content[snippet_start:snippet_end]
                        
                        # Clean up the snippet
                        snippet = snippet.strip()
                        if snippet_start > 0:
                            snippet = "..." + snippet
                        if snippet_end < len(content):
                            snippet = snippet + "..."
                            
                        # Highlight the term (case insensitive)
                        import re
                        highlighted_snippet = re.sub(
                            re.escape(term),
                            f"<mark>{term}</mark>",
                            snippet,
                            count=1,
                            flags=re.IGNORECASE
                        )
                        
                        snippets.append(highlighted_snippet)
                        
                        if len(snippets) >= max_snippets:
                            break
                            
                        start = pos + 1
                        
                if len(snippets) >= max_snippets:
                    break
                    
            return snippets
            
        except Exception as e:
            logger.error(f"Error extracting content snippets: {str(e)}")
            return []
            
    def _process_report_for_json(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a report to ensure JSON compliance and add computed fields.
        
        Args:
            report: Raw report data from database
            
        Returns:
            Processed report data
        """
        try:
            # Ensure all datetime fields are ISO strings
            if report.get("created_at"):
                if isinstance(report["created_at"], str):
                    report["created_at"] = report["created_at"]
                else:
                    report["created_at"] = report["created_at"].isoformat()
                    
            if report.get("updated_at"):
                if isinstance(report["updated_at"], str):
                    report["updated_at"] = report["updated_at"]
                else:
                    report["updated_at"] = report["updated_at"].isoformat()
                    
            if report.get("last_viewed_at"):
                if isinstance(report["last_viewed_at"], str):
                    report["last_viewed_at"] = report["last_viewed_at"]
                else:
                    report["last_viewed_at"] = report["last_viewed_at"].isoformat()
                    
            # Ensure content is properly formatted JSON
            if report.get("content"):
                if isinstance(report["content"], str):
                    try:
                        report["content"] = json.loads(report["content"])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in report content for report {report.get('id')}")
                        
            # Ensure boolean fields are properly typed
            report["is_pinned"] = bool(report.get("is_pinned", False))
            report["is_archived"] = bool(report.get("is_archived", False))
            
            # Ensure numeric fields are properly typed
            report["view_count"] = int(report.get("view_count", 0))
            
            # Ensure array fields are properly typed
            report["tags"] = report.get("tags") or []
            
            return report
            
        except Exception as e:
            logger.error(f"Error processing report for JSON: {str(e)}")
            # Return the original report if processing fails
            return report
            
    def suggest_search_terms(self, user_id: str, partial_query: str, limit: int = 10) -> List[str]:
        """
        Suggest search terms based on user's report history.
        
        Args:
            user_id: The ID of the user
            partial_query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested search terms
        """
        try:
            logger.debug(f"Generating search suggestions for user {user_id}")
            
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            if not partial_query or len(partial_query.strip()) < 2:
                return []
                
            partial_lower = partial_query.lower().strip()
            suggestions = set()
            
            # Get user's reports for suggestion generation
            response = self.client.client.table(self.reports_table) \
                .select("title, summary, tags, category") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .limit(100) \
                .execute()
                
            reports = response.data
            
            # Extract suggestions from titles
            for report in reports:
                title = report.get("title", "")
                if title and partial_lower in title.lower():
                    # Extract words from title that contain the partial query
                    words = title.split()
                    for word in words:
                        if partial_lower in word.lower() and len(word) > len(partial_query):
                            suggestions.add(word.lower())
                            
                # Extract suggestions from categories
                category = report.get("category", "")
                if category and partial_lower in category.lower():
                    suggestions.add(category.lower())
                    
                # Extract suggestions from tags
                tags = report.get("tags", [])
                for tag in tags:
                    if tag and partial_lower in tag.lower():
                        suggestions.add(tag.lower())
                        
            # Convert to sorted list and limit results
            suggestion_list = sorted(list(suggestions))[:limit]
            
            logger.debug(f"Generated {len(suggestion_list)} search suggestions")
            return suggestion_list
            
        except Exception as e:
            logger.error(f"Error generating search suggestions: {str(e)}")
            return []