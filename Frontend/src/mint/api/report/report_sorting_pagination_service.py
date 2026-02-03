"""
Report Sorting and Pagination Service

This service provides advanced sorting and pagination functionality for user reports,
including various sorting options, optimized query performance, and efficient pagination.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID

from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..system.core.utils import is_valid_uuid

logger = logging.getLogger(__name__)


class ReportSortingPaginationService:
    """Service for advanced report sorting and pagination operations."""
    
    # Supported sorting fields and their database column mappings
    SORT_FIELDS = {
        "created_at": "created_at",
        "updated_at": "updated_at",
        "last_viewed_at": "last_viewed_at",
        "title": "title",
        "category": "category",
        "view_count": "view_count",
        "relevance": "view_count",  # Fallback for relevance sorting
        "alphabetical": "title",
        "date": "created_at",
        "recent": "created_at",
        "popular": "view_count"
    }
    
    # Default sorting configurations
    DEFAULT_SORTS = {
        "newest_first": {"field": "created_at", "order": "desc"},
        "oldest_first": {"field": "created_at", "order": "asc"},
        "most_viewed": {"field": "view_count", "order": "desc"},
        "least_viewed": {"field": "view_count", "order": "asc"},
        "alphabetical_asc": {"field": "title", "order": "asc"},
        "alphabetical_desc": {"field": "title", "order": "desc"},
        "recently_viewed": {"field": "last_viewed_at", "order": "desc"},
        "recently_updated": {"field": "updated_at", "order": "desc"}
    }
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the sorting and pagination service.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.reports_table = "mint_reports"
        
    def get_sorted_paginated_reports(
        self,
        user_id: str,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get sorted and paginated reports for a user.
        
        Args:
            user_id: The ID of the user
            sort_by: Field to sort by
            sort_order: Sort order - 'asc' or 'desc'
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Optional filters to apply
            
        Returns:
            Dict containing sorted and paginated reports with metadata
        """
        try:
            logger.info(f"Getting sorted paginated reports for user {user_id}")
            
            # Validate inputs
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            # Validate and normalize sorting parameters
            sort_config = self._validate_and_normalize_sort(sort_by, sort_order)
            
            # Validate pagination parameters
            page, page_size = self._validate_pagination(page, page_size)
            
            # Build base query
            query = self._build_base_query(user_id, filters)
            
            # Get total count for pagination
            count_query = self._build_base_query(user_id, filters, count_only=True)
            count_result = count_query.execute()
            total_count = count_result.count
            
            # Apply sorting
            query = self._apply_sorting(query, sort_config)
            
            # Apply pagination
            query = self._apply_pagination(query, page, page_size)
            
            # Execute query
            response = query.execute()
            reports = response.data
            
            # Process results
            processed_reports = []
            for report in reports:
                processed_report = self._process_report_for_json(report)
                processed_reports.append(processed_report)
                
            # Calculate pagination metadata
            pagination_metadata = self._calculate_pagination_metadata(
                page, page_size, total_count
            )
            
            # Generate sorting metadata
            sorting_metadata = self._generate_sorting_metadata(sort_config)
            
            result = {
                "reports": processed_reports,
                "pagination": pagination_metadata,
                "sorting": sorting_metadata,
                "filters_applied": filters or {},
                "performance": {
                    "total_count": total_count,
                    "page_count": len(processed_reports),
                    "sort_field": sort_config["field"],
                    "sort_order": sort_config["order"]
                }
            }
            
            logger.info(f"Retrieved {len(processed_reports)} sorted reports for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting sorted paginated reports for user {user_id}: {str(e)}")
            raise
            
    def _validate_and_normalize_sort(self, sort_by: str, sort_order: str) -> Dict[str, str]:
        """
        Validate and normalize sorting parameters.
        
        Args:
            sort_by: Field to sort by
            sort_order: Sort order
            
        Returns:
            Normalized sort configuration
        """
        try:
            # Check if it's a predefined sort
            if sort_by in self.DEFAULT_SORTS:
                config = self.DEFAULT_SORTS[sort_by].copy()
                config["original_field"] = sort_by
                return config
                
            # Validate sort field
            if sort_by not in self.SORT_FIELDS:
                logger.warning(f"Invalid sort field '{sort_by}', using default 'created_at'")
                sort_by = "created_at"
                
            # Validate sort order
            if sort_order.lower() not in ["asc", "desc"]:
                logger.warning(f"Invalid sort order '{sort_order}', using default 'desc'")
                sort_order = "desc"
                
            return {
                "field": self.SORT_FIELDS[sort_by],
                "order": sort_order.lower(),
                "original_field": sort_by
            }
            
        except Exception as e:
            logger.error(f"Error validating sort parameters: {str(e)}")
            # Return safe defaults
            return {
                "field": "created_at",
                "order": "desc",
                "original_field": "created_at"
            }
            
    def _validate_pagination(self, page: int, page_size: int) -> Tuple[int, int]:
        """
        Validate and normalize pagination parameters.
        
        Args:
            page: Page number
            page_size: Page size
            
        Returns:
            Tuple of validated (page, page_size)
        """
        try:
            # Validate page number
            if page < 1:
                logger.warning(f"Invalid page number {page}, using 1")
                page = 1
                
            # Validate page size
            if page_size < 1:
                logger.warning(f"Invalid page size {page_size}, using 20")
                page_size = 20
            elif page_size > 100:
                logger.warning(f"Page size {page_size} too large, using 100")
                page_size = 100
                
            return page, page_size
            
        except Exception as e:
            logger.error(f"Error validating pagination parameters: {str(e)}")
            return 1, 20
            
    def _build_base_query(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        count_only: bool = False
    ):
        """
        Build the base query with optional filters.
        
        Args:
            user_id: The ID of the user
            filters: Optional filters to apply
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
                
            # Apply filters if provided
            if filters:
                query = self._apply_filters(query, filters)
                
            return query
            
        except Exception as e:
            logger.error(f"Error building base query: {str(e)}")
            raise
            
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        Apply filters to the query.
        
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
                
            # Archived filter
            if "only_archived" in filters and filters["only_archived"]:
                query = query.eq("is_archived", True)
            elif "exclude_archived" in filters and filters["exclude_archived"]:
                query = query.eq("is_archived", False)
                
            # Search filter
            # Note: Removed .or_() as Supabase Python client doesn't support it
            # Using ilike on title only - summary filtering done separately if needed
            if "search" in filters and filters["search"]:
                search_term = filters["search"].strip()
                if search_term:
                    query = query.ilike("title", f"%{search_term}%")
                    
            return query
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            raise
            
    def _apply_sorting(self, query, sort_config: Dict[str, str]):
        """
        Apply sorting to the query.
        
        Args:
            query: The Supabase query object
            sort_config: Sort configuration
            
        Returns:
            Modified query object with sorting applied
        """
        try:
            field = sort_config["field"]
            order = sort_config["order"]
            
            # Handle special sorting cases
            if sort_config.get("original_field") == "relevance":
                # For relevance, sort by view_count desc, then created_at desc
                query = query.order("view_count", desc=True) \
                    .order("created_at", desc=True)
            elif sort_config.get("original_field") == "popular":
                # For popular, sort by view_count desc, then last_viewed_at desc
                query = query.order("view_count", desc=True) \
                    .order("last_viewed_at", desc=True)
            else:
                # Standard sorting
                query = query.order(field, desc=(order == "desc"))
                
                # Add secondary sort for consistency
                if field != "created_at":
                    query = query.order("created_at", desc=True)
                    
            return query
            
        except Exception as e:
            logger.error(f"Error applying sorting: {str(e)}")
            # Fallback to default sorting
            return query.order("created_at", desc=True)
            
    def _apply_pagination(self, query, page: int, page_size: int):
        """
        Apply pagination to the query.
        
        Args:
            query: The Supabase query object
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Modified query object with pagination applied
        """
        try:
            offset = (page - 1) * page_size
            return query.range(offset, offset + page_size - 1)
            
        except Exception as e:
            logger.error(f"Error applying pagination: {str(e)}")
            raise
            
    def _calculate_pagination_metadata(
        self,
        page: int,
        page_size: int,
        total_count: int
    ) -> Dict[str, Any]:
        """
        Calculate pagination metadata.
        
        Args:
            page: Current page number
            page_size: Number of items per page
            total_count: Total number of items
            
        Returns:
            Pagination metadata dictionary
        """
        try:
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            has_next = page < total_pages
            has_prev = page > 1
            
            # Calculate page ranges for UI
            start_item = (page - 1) * page_size + 1 if total_count > 0 else 0
            end_item = min(page * page_size, total_count)
            
            # Generate page numbers for pagination UI
            page_numbers = self._generate_page_numbers(page, total_pages)
            
            return {
                "current_page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "start_item": start_item,
                "end_item": end_item,
                "page_numbers": page_numbers,
                "is_first_page": page == 1,
                "is_last_page": page == total_pages,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating pagination metadata: {str(e)}")
            return {
                "current_page": 1,
                "page_size": page_size,
                "total_count": 0,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
                "start_item": 0,
                "end_item": 0,
                "page_numbers": [1],
                "is_first_page": True,
                "is_last_page": True,
                "next_page": None,
                "prev_page": None
            }
            
    def _generate_page_numbers(self, current_page: int, total_pages: int, window: int = 5) -> List[int]:
        """
        Generate page numbers for pagination UI.
        
        Args:
            current_page: Current page number
            total_pages: Total number of pages
            window: Number of pages to show around current page
            
        Returns:
            List of page numbers to display
        """
        try:
            if total_pages <= window:
                return list(range(1, total_pages + 1))
                
            # Calculate start and end of window
            half_window = window // 2
            start = max(1, current_page - half_window)
            end = min(total_pages, current_page + half_window)
            
            # Adjust if we're near the beginning or end
            if end - start + 1 < window:
                if start == 1:
                    end = min(total_pages, start + window - 1)
                else:
                    start = max(1, end - window + 1)
                    
            return list(range(start, end + 1))
            
        except Exception as e:
            logger.error(f"Error generating page numbers: {str(e)}")
            return [1]
            
    def _generate_sorting_metadata(self, sort_config: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate sorting metadata for the response.
        
        Args:
            sort_config: Sort configuration
            
        Returns:
            Sorting metadata dictionary
        """
        try:
            return {
                "field": sort_config["field"],
                "order": sort_config["order"],
                "original_field": sort_config.get("original_field", sort_config["field"]),
                "display_name": self._get_sort_display_name(sort_config.get("original_field", sort_config["field"])),
                "available_sorts": self._get_available_sorts()
            }
            
        except Exception as e:
            logger.error(f"Error generating sorting metadata: {str(e)}")
            return {
                "field": "created_at",
                "order": "desc",
                "original_field": "created_at",
                "display_name": "Date Created",
                "available_sorts": []
            }
            
    def _get_sort_display_name(self, field: str) -> str:
        """
        Get display name for a sort field.
        
        Args:
            field: Sort field name
            
        Returns:
            Human-readable display name
        """
        display_names = {
            "created_at": "Date Created",
            "updated_at": "Date Updated",
            "last_viewed_at": "Last Viewed",
            "title": "Title",
            "category": "Category",
            "view_count": "View Count",
            "relevance": "Relevance",
            "alphabetical": "Alphabetical",
            "date": "Date",
            "recent": "Most Recent",
            "popular": "Most Popular"
        }
        
        return display_names.get(field, field.replace("_", " ").title())
        
    def _get_available_sorts(self) -> List[Dict[str, str]]:
        """
        Get list of available sorting options.
        
        Returns:
            List of available sort options with metadata
        """
        try:
            available_sorts = []
            
            # Add predefined sorts
            for key, config in self.DEFAULT_SORTS.items():
                available_sorts.append({
                    "key": key,
                    "field": config["field"],
                    "order": config["order"],
                    "display_name": self._get_sort_display_name(key),
                    "description": self._get_sort_description(key)
                })
                
            # Add basic field sorts
            for field in ["title", "category", "view_count"]:
                if field in self.SORT_FIELDS:
                    for order in ["asc", "desc"]:
                        key = f"{field}_{order}"
                        if key not in self.DEFAULT_SORTS:
                            available_sorts.append({
                                "key": key,
                                "field": self.SORT_FIELDS[field],
                                "order": order,
                                "display_name": f"{self._get_sort_display_name(field)} ({order.upper()})",
                                "description": f"Sort by {self._get_sort_display_name(field)} in {order}ending order"
                            })
                            
            return available_sorts
            
        except Exception as e:
            logger.error(f"Error getting available sorts: {str(e)}")
            return []
            
    def _get_sort_description(self, sort_key: str) -> str:
        """
        Get description for a sort option.
        
        Args:
            sort_key: Sort key
            
        Returns:
            Description of the sort option
        """
        descriptions = {
            "newest_first": "Show newest reports first",
            "oldest_first": "Show oldest reports first",
            "most_viewed": "Show most viewed reports first",
            "least_viewed": "Show least viewed reports first",
            "alphabetical_asc": "Sort by title A-Z",
            "alphabetical_desc": "Sort by title Z-A",
            "recently_viewed": "Show recently viewed reports first",
            "recently_updated": "Show recently updated reports first"
        }
        
        return descriptions.get(sort_key, f"Sort by {sort_key}")
        
    def get_sort_options(self, user_id: str) -> Dict[str, Any]:
        """
        Get available sorting options for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dictionary of available sorting options
        """
        try:
            logger.info(f"Getting sort options for user {user_id}")
            
            if not is_valid_uuid(user_id):
                raise ValueError("Invalid user_id format")
                
            # Get user's report statistics for context
            stats_response = self.client.client.table(self.reports_table) \
                .select("view_count, created_at, last_viewed_at") \
                .eq("user_id", user_id) \
                .is_("deleted_at", "null") \
                .execute()
                
            reports = stats_response.data
            
            # Calculate statistics
            total_reports = len(reports)
            has_view_counts = any(r.get("view_count", 0) > 0 for r in reports)
            has_last_viewed = any(r.get("last_viewed_at") for r in reports)
            
            # Get available sorts
            available_sorts = self._get_available_sorts()
            
            # Filter sorts based on data availability
            if not has_view_counts:
                available_sorts = [s for s in available_sorts if "view" not in s["key"].lower()]
                
            if not has_last_viewed:
                available_sorts = [s for s in available_sorts if "viewed" not in s["key"].lower()]
                
            # Group sorts by category
            sort_categories = {
                "date": [s for s in available_sorts if any(word in s["key"] for word in ["newest", "oldest", "recent", "updated"])],
                "alphabetical": [s for s in available_sorts if "alphabetical" in s["key"]],
                "popularity": [s for s in available_sorts if any(word in s["key"] for word in ["viewed", "popular"])],
                "other": [s for s in available_sorts if not any(cat in s["key"] for cat in ["newest", "oldest", "recent", "updated", "alphabetical", "viewed", "popular"])]
            }
            
            # Remove empty categories
            sort_categories = {k: v for k, v in sort_categories.items() if v}
            
            return {
                "available_sorts": available_sorts,
                "sort_categories": sort_categories,
                "default_sort": "newest_first",
                "recommended_sorts": self._get_recommended_sorts(total_reports, has_view_counts),
                "statistics": {
                    "total_reports": total_reports,
                    "has_view_counts": has_view_counts,
                    "has_last_viewed": has_last_viewed
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting sort options for user {user_id}: {str(e)}")
            raise
            
    def _get_recommended_sorts(self, total_reports: int, has_view_counts: bool) -> List[str]:
        """
        Get recommended sort options based on user's data.
        
        Args:
            total_reports: Total number of reports
            has_view_counts: Whether user has reports with view counts
            
        Returns:
            List of recommended sort keys
        """
        try:
            recommended = ["newest_first", "alphabetical_asc"]
            
            if has_view_counts:
                recommended.insert(1, "most_viewed")
                
            if total_reports > 10:
                recommended.append("recently_updated")
                
            return recommended
            
        except Exception as e:
            logger.error(f"Error getting recommended sorts: {str(e)}")
            return ["newest_first"]
            
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
            for field in ["created_at", "updated_at", "last_viewed_at"]:
                if report.get(field):
                    if not isinstance(report[field], str):
                        report[field] = report[field].isoformat()
                        
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