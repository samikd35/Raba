"""
Report Filtering Service

This service provides advanced filtering functionality for user reports,
including date range filtering, category and tag filtering, and combined operations.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID

from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..system.core.utils import is_valid_uuid

logger = logging.getLogger(__name__)


class ReportFilteringService:
    """Service for advanced report filtering operations."""
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the report filtering service.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.reports_table = "mint_reports"
        
    def filter_reports(
        self,
        user_id: str,
        filters: Dict[str, Any],
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Filter reports based on various criteria.
        
        Args:
            user_id: The ID of the user
            filters: Dictionary of filters to apply
            sort_by: Field to sort by (default: created_at)
            sort_order: Sort order - 'asc' or 'desc' (default: desc)
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dict containing filtered reports, pagination info, and metadata
        """
        try:
            logger.info(f"Filtering reports for user {user_id} with filters: {filters}")
            
            # Validate inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            if not filters:
                raise ValueError("Filters cannot be empty")
                
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
                
            # Build filter query
            filter_query = self._build_filter_query(user_id, filters)
            
            # Get total count for pagination
            count_query = self._build_filter_query(user_id, filters, count_only=True)
            count_result = count_query.execute()
            total_count = count_result.count
            
            # Apply sorting
            if sort_order.lower() == "asc":
                filter_query = filter_query.order(sort_by, desc=False)
            else:
                filter_query = filter_query.order(sort_by, desc=True)
                
            # Apply pagination
            offset = (page - 1) * page_size
            filter_query = filter_query.range(offset, offset + page_size - 1)
            
            # Execute filter query
            response = filter_query.execute()
            reports = response.data
            
            # Process results
            processed_reports = []
            for report in reports:
                processed_report = self._process_report_for_json(report)
                processed_reports.append(processed_report)
                
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            result = {
                "reports": processed_reports,
                "filter_metadata": {
                    "applied_filters": filters,
                    "total_matches": total_count,
                    "filter_summary": self._generate_filter_summary(filters)
                },
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                },
                "sort": {
                    "field": sort_by,
                    "order": sort_order
                }
            }
            
            logger.info(f"Filter completed: {len(processed_reports)} results for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error filtering reports for user {user_id}: {str(e)}")
            raise
            
    def _build_filter_query(
        self,
        user_id: str,
        filters: Dict[str, Any],
        count_only: bool = False
    ):
        """
        Build the database query based on filter criteria.
        
        Args:
            user_id: The ID of the user
            filters: Filter criteria
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
                
            # Apply date range filter
            if "date_range" in filters:
                query = self._apply_date_range_filter(query, filters["date_range"])
                
            # Apply category filter
            if "categories" in filters:
                query = self._apply_category_filter(query, filters["categories"])
                
            # Apply tags filter
            if "tags" in filters:
                query = self._apply_tags_filter(query, filters["tags"])
                
            # Apply report type filter
            if "report_types" in filters:
                query = self._apply_report_type_filter(query, filters["report_types"])
                
            # Apply status filters
            if "only_pinned" in filters and filters["only_pinned"]:
                query = query.eq("is_pinned", True)
                
            if "only_archived" in filters and filters["only_archived"]:
                query = query.eq("is_archived", True)
            elif "exclude_archived" in filters and filters["exclude_archived"]:
                query = query.eq("is_archived", False)
                
            # Apply view count filter
            if "min_view_count" in filters:
                query = query.gte("view_count", filters["min_view_count"])
                
            if "max_view_count" in filters:
                query = query.lte("view_count", filters["max_view_count"])
                
            # Apply creation date filters
            if "created_after" in filters:
                query = query.gte("created_at", filters["created_after"])
                
            if "created_before" in filters:
                query = query.lte("created_at", filters["created_before"])
                
            # Apply last viewed filters
            if "viewed_after" in filters:
                query = query.gte("last_viewed_at", filters["viewed_after"])
                
            if "viewed_before" in filters:
                query = query.lte("last_viewed_at", filters["viewed_before"])
                
            # Apply recently viewed filter
            if "recently_viewed" in filters and filters["recently_viewed"]:
                recent_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                query = query.gte("last_viewed_at", recent_date)
                
            return query
            
        except Exception as e:
            logger.error(f"Error building filter query: {str(e)}")
            raise
            
    def _apply_date_range_filter(self, query, date_range: Dict[str, str]):
        """
        Apply date range filter to the query.
        
        Args:
            query: The Supabase query object
            date_range: Dictionary with 'start' and/or 'end' dates
            
        Returns:
            Modified query object
        """
        try:
            if "start" in date_range and date_range["start"]:
                query = query.gte("created_at", date_range["start"])
                
            if "end" in date_range and date_range["end"]:
                query = query.lte("created_at", date_range["end"])
                
            return query
            
        except Exception as e:
            logger.error(f"Error applying date range filter: {str(e)}")
            raise
            
    def _apply_category_filter(self, query, categories: Union[str, List[str]]):
        """
        Apply category filter to the query.
        
        Args:
            query: The Supabase query object
            categories: Category or list of categories to filter by
            
        Returns:
            Modified query object
        """
        try:
            if isinstance(categories, list) and categories:
                query = query.in_("category", categories)
            elif isinstance(categories, str) and categories:
                query = query.eq("category", categories)
                
            return query
            
        except Exception as e:
            logger.error(f"Error applying category filter: {str(e)}")
            raise
            
    def _apply_tags_filter(self, query, tags: Union[str, List[str]]):
        """
        Apply tags filter to the query.
        
        Args:
            query: The Supabase query object
            tags: Tag or list of tags to filter by
            
        Returns:
            Modified query object
        """
        try:
            if isinstance(tags, list) and tags:
                # Use overlap operator for array fields
                query = query.overlaps("tags", tags)
            elif isinstance(tags, str) and tags:
                query = query.contains("tags", [tags])
                
            return query
            
        except Exception as e:
            logger.error(f"Error applying tags filter: {str(e)}")
            raise
            
    def _apply_report_type_filter(self, query, report_types: Union[str, List[str]]):
        """
        Apply report type filter to the query.
        
        Args:
            query: The Supabase query object
            report_types: Report type or list of report types to filter by
            
        Returns:
            Modified query object
        """
        try:
            if isinstance(report_types, list) and report_types:
                query = query.in_("report_type", report_types)
            elif isinstance(report_types, str) and report_types:
                query = query.eq("report_type", report_types)
                
            return query
            
        except Exception as e:
            logger.error(f"Error applying report type filter: {str(e)}")
            raise
            
    def _generate_filter_summary(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a human-readable summary of applied filters.
        
        Args:
            filters: Applied filters
            
        Returns:
            Filter summary dictionary
        """
        try:
            summary = {
                "total_filters": 0,
                "active_filters": [],
                "description": ""
            }
            
            descriptions = []
            
            # Date range filter
            if "date_range" in filters:
                date_range = filters["date_range"]
                if "start" in date_range and "end" in date_range:
                    descriptions.append(f"Created between {date_range['start']} and {date_range['end']}")
                elif "start" in date_range:
                    descriptions.append(f"Created after {date_range['start']}")
                elif "end" in date_range:
                    descriptions.append(f"Created before {date_range['end']}")
                summary["active_filters"].append("date_range")
                summary["total_filters"] += 1
                
            # Category filter
            if "categories" in filters and filters["categories"]:
                categories = filters["categories"]
                if isinstance(categories, list):
                    descriptions.append(f"Categories: {', '.join(categories)}")
                else:
                    descriptions.append(f"Category: {categories}")
                summary["active_filters"].append("categories")
                summary["total_filters"] += 1
                
            # Tags filter
            if "tags" in filters and filters["tags"]:
                tags = filters["tags"]
                if isinstance(tags, list):
                    descriptions.append(f"Tags: {', '.join(tags)}")
                else:
                    descriptions.append(f"Tag: {tags}")
                summary["active_filters"].append("tags")
                summary["total_filters"] += 1
                
            # Report types filter
            if "report_types" in filters and filters["report_types"]:
                report_types = filters["report_types"]
                if isinstance(report_types, list):
                    descriptions.append(f"Report types: {', '.join(report_types)}")
                else:
                    descriptions.append(f"Report type: {report_types}")
                summary["active_filters"].append("report_types")
                summary["total_filters"] += 1
                
            # Status filters
            if "only_pinned" in filters and filters["only_pinned"]:
                descriptions.append("Only pinned reports")
                summary["active_filters"].append("only_pinned")
                summary["total_filters"] += 1
                
            if "only_archived" in filters and filters["only_archived"]:
                descriptions.append("Only archived reports")
                summary["active_filters"].append("only_archived")
                summary["total_filters"] += 1
            elif "exclude_archived" in filters and filters["exclude_archived"]:
                descriptions.append("Excluding archived reports")
                summary["active_filters"].append("exclude_archived")
                summary["total_filters"] += 1
                
            # View count filters
            if "min_view_count" in filters:
                descriptions.append(f"Minimum {filters['min_view_count']} views")
                summary["active_filters"].append("min_view_count")
                summary["total_filters"] += 1
                
            if "max_view_count" in filters:
                descriptions.append(f"Maximum {filters['max_view_count']} views")
                summary["active_filters"].append("max_view_count")
                summary["total_filters"] += 1
                
            # Recently viewed filter
            if "recently_viewed" in filters and filters["recently_viewed"]:
                descriptions.append("Recently viewed (last 7 days)")
                summary["active_filters"].append("recently_viewed")
                summary["total_filters"] += 1
                
            summary["description"] = "; ".join(descriptions) if descriptions else "No filters applied"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating filter summary: {str(e)}")
            return {
                "total_filters": 0,
                "active_filters": [],
                "description": "Error generating summary"
            }
            
    def get_filter_options(self, user_id: str) -> Dict[str, Any]:
        """
        Get available filter options based on user's reports.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dictionary of available filter options
        """
        try:
            logger.info(f"Getting filter options for user {user_id}")
            
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            # Get user's reports for filter option generation
            response = self.client.client.table(self.reports_table) \
                .select("category, tags, report_type, created_at, view_count") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .execute()
                
            reports = response.data
            
            # Extract unique values
            categories = set()
            tags = set()
            report_types = set()
            date_range = {"earliest": None, "latest": None}
            view_count_range = {"min": 0, "max": 0}
            
            for report in reports:
                # Categories
                if report.get("category"):
                    categories.add(report["category"])
                    
                # Tags
                if report.get("tags"):
                    for tag in report["tags"]:
                        if tag:
                            tags.add(tag)
                            
                # Report types
                if report.get("report_type"):
                    report_types.add(report["report_type"])
                    
                # Date range
                if report.get("created_at"):
                    created_at = report["created_at"]
                    if date_range["earliest"] is None or created_at < date_range["earliest"]:
                        date_range["earliest"] = created_at
                    if date_range["latest"] is None or created_at > date_range["latest"]:
                        date_range["latest"] = created_at
                        
                # View count range
                view_count = report.get("view_count", 0)
                if view_count > view_count_range["max"]:
                    view_count_range["max"] = view_count
                    
            # Generate predefined date ranges
            now = datetime.now(timezone.utc)
            predefined_ranges = {
                "last_7_days": {
                    "start": (now - timedelta(days=7)).isoformat(),
                    "end": now.isoformat(),
                    "label": "Last 7 days"
                },
                "last_30_days": {
                    "start": (now - timedelta(days=30)).isoformat(),
                    "end": now.isoformat(),
                    "label": "Last 30 days"
                },
                "last_90_days": {
                    "start": (now - timedelta(days=90)).isoformat(),
                    "end": now.isoformat(),
                    "label": "Last 90 days"
                },
                "this_year": {
                    "start": now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(),
                    "end": now.isoformat(),
                    "label": "This year"
                }
            }
            
            options = {
                "categories": sorted(list(categories)),
                "tags": sorted(list(tags)),
                "report_types": sorted(list(report_types)),
                "date_range": {
                    "earliest": date_range["earliest"],
                    "latest": date_range["latest"],
                    "predefined": predefined_ranges
                },
                "view_count_range": view_count_range,
                "status_options": [
                    {"value": "only_pinned", "label": "Only pinned"},
                    {"value": "only_archived", "label": "Only archived"},
                    {"value": "exclude_archived", "label": "Exclude archived"},
                    {"value": "recently_viewed", "label": "Recently viewed"}
                ]
            }
            
            logger.info(f"Generated filter options for user {user_id}")
            return options
            
        except Exception as e:
            logger.error(f"Error getting filter options for user {user_id}: {str(e)}")
            raise
            
    def combine_search_and_filter(
        self,
        user_id: str,
        search_query: str,
        filters: Dict[str, Any],
        sort_by: str = "relevance",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Combine search and filter operations.
        
        Args:
            user_id: The ID of the user
            search_query: Search query string
            filters: Filter criteria
            sort_by: Field to sort by
            sort_order: Sort order - 'asc' or 'desc'
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dict containing combined search and filter results
        """
        try:
            logger.info(f"Combining search and filter for user {user_id}")
            
            # Import search service to avoid circular imports
            from .report_search_service import ReportSearchService
            
            search_service = ReportSearchService(self.client)
            
            # Use search service with additional filters
            result = search_service.search_reports(
                user_id=user_id,
                query=search_query,
                filters=filters,
                sort_by=sort_by,
                sort_order=sort_order,
                page=page,
                page_size=page_size
            )
            
            # Add filter metadata
            result["filter_metadata"] = {
                "applied_filters": filters,
                "filter_summary": self._generate_filter_summary(filters)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error combining search and filter: {str(e)}")
            raise
            
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