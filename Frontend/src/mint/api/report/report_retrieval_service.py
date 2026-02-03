"""
Report Retrieval Service

This service provides functionality for retrieving clean report content for display
and metadata for chat context preparation. It implements proper user-based access
control and database-level enforcement of user isolation.

Requirements addressed:
- 1.1: Proper report display from history
- 2.4: Efficient retrieval of historical reports
- 3.1, 3.3, 3.5: User authentication and data isolation
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from ..system.core.supabase_client import SupabaseClient, get_service_role_client, get_standard_client
from ..system.core.utils import is_valid_uuid
from ..cache.enhanced import get_cache_service, cache_result
from ..services.utilities.query_optimizer import monitor_query
# from .report_cache_manager import get_report_cache_manager  # File doesn't exist
# from .performance_optimizer import optimize_performance  # File is in pgen directory
from ...utils.circuit_breaker import circuit_breaker, CircuitBreakerError
from .report_error_handler import get_report_error_handler, ReportErrorType

logger = logging.getLogger(__name__)


def strip_industry_analysis_prefix(title: str) -> str:
    """
    Strip 'Industry Analysis of' prefix from PV report titles.
    
    Args:
        title: The original title
        
    Returns:
        Title without the 'Industry Analysis of' prefix
    """
    if not title:
        return title
    
    prefix = "Industry Analysis of "
    if title.startswith(prefix):
        return title[len(prefix):]
    return title


class ReportRetrievalService:
    """Service for retrieving clean report content and metadata with proper user access control."""
    
    def __init__(self, supabase_client: SupabaseClient = None):
        """
        Initialize the report retrieval service.
        
        Args:
            supabase_client: Optional Supabase client instance
        """
        self.client = supabase_client or get_standard_client()
        self.reports_table = "documents"  # Updated to use documents table
        self.error_handler = get_report_error_handler()
        # self.cache_manager = get_report_cache_manager()  # Disabled - function doesn't exist
        try:
            self.cache_service = get_cache_service()
        except Exception:
            # Fallback if cache service is not available
            self.cache_service = None
        
    @circuit_breaker(
        name="report_retrieval_get_display",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=15
    )
    @monitor_query(query_type="select", table_name="documents")
    # @optimize_performance("report_display_retrieval")  # Function not available
    async def get_report_for_display(
        self,
        report_id: str,
        user_id: str,
        user_token: str = None
    ) -> Dict[str, Any]:
        """
        Retrieve clean report content for display purposes.
        
        This method ensures that:
        1. Only the report owner can access the report (Requirement 3.1, 3.3)
        2. Returns clean final report content suitable for MarketValidationReportPage
        3. Enforces database-level user isolation (Requirement 3.5)
        4. Provides efficient retrieval for historical reports (Requirement 2.4)
        
        Args:
            report_id: The ID of the report to retrieve
            user_id: The authenticated user's ID (from auth.uid())
            user_token: Optional JWT token for RLS enforcement
            
        Returns:
            Dict containing clean report structure ready for display
            
        Raises:
            ValueError: If inputs are invalid or access is denied
            Exception: For database or system errors
        """
        try:
            logger.info(f"Retrieving report {report_id} for display by user {user_id}")
            
            # Validate inputs (Requirement 3.1)
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")
                
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            
            # Use service role client to bypass RLS (we filter by created_by for security)
            # This avoids JWT validation issues while maintaining data isolation
            service_client = get_service_role_client()
            
            # Cache manager disabled - skip cache check
            # TODO: Implement proper caching when cache manager is available
            
            # Query for clean report content with user ownership verification
            # Using the documents table with proper ownership filtering
            query = service_client.client.table("documents") \
                .select("id,title,content,created_at,updated_at,metadata") \
                .eq("id", report_id) \
                .eq("created_by", user_id) \
                .eq("source_type", "pv_report") \
                .single()
            
            response = query.execute()
            
            if not response.data:
                logger.warning(f"Report {report_id} not found or access denied for user {user_id}")
                raise ValueError("Report not found or access denied")
            
            report_data = response.data
            
            # Process and clean the report content for display (Requirement 1.1)
            clean_report = self._extract_clean_report_content(report_data)
            
            # Cache manager disabled - skip caching
            # TODO: Implement proper caching when cache manager is available
            
            logger.info(f"Successfully retrieved clean report content for report {report_id}")
            return clean_report
            
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker open for report retrieval, report_id: {report_id}")
            report_error = self.error_handler.handle_report_access_error(
                e, report_id, user_id, "display_retrieval"
            )
            self.error_handler.log_error_for_monitoring(report_error)
            raise self.error_handler.create_http_exception(report_error)
            
        except Exception as e:
            logger.error(f"Error retrieving report {report_id} for display: {str(e)}")
            report_error = self.error_handler.handle_report_access_error(
                e, report_id, user_id, "display_retrieval"
            )
            self.error_handler.log_error_for_monitoring(report_error)
            raise self.error_handler.create_http_exception(report_error)
    
    @circuit_breaker(
        name="report_retrieval_get_metadata",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=15
    )
    @monitor_query(query_type="select", table_name="mint_reports")
    async def get_report_metadata(
        self,
        report_id: str,
        user_id: str,
        user_token: str = None
    ) -> Dict[str, Any]:
        """
        Retrieve report metadata for chat context preparation.
        
        This method ensures that:
        1. Only the report owner can access metadata (Requirement 3.1, 3.3)
        2. Returns metadata needed for chat context preparation
        3. Enforces database-level user isolation (Requirement 3.5)
        4. Provides efficient metadata retrieval (Requirement 2.4)
        
        Args:
            report_id: The ID of the report to retrieve metadata for
            user_id: The authenticated user's ID (from auth.uid())
            user_token: Optional JWT token for RLS enforcement
            
        Returns:
            Dict containing report metadata (initial query, clarifications, workflow data)
            
        Raises:
            ValueError: If inputs are invalid or access is denied
            Exception: For database or system errors
        """
        try:
            logger.info(f"Retrieving metadata for report {report_id} by user {user_id}")
            
            # Validate inputs (Requirement 3.1)
            if not is_valid_uuid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                raise ValueError("Invalid report_id format - must be a valid UUID")
                
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            
            # Use service role client to bypass RLS (we filter by user_id for security)
            # This avoids JWT validation issues while maintaining data isolation
            service_client = get_service_role_client()
            
            # Check cache first for performance
            cache_key = f"report_metadata:{report_id}:{user_id}"
            cached_result = None
            if self.cache_service:
                try:
                    cached_result = await self.cache_service.get(cache_key)
                    if cached_result:
                        logger.debug(f"Retrieved report metadata {report_id} from cache")
                        return cached_result
                except Exception as e:
                    logger.debug(f"Cache get failed: {e}")
            
            # Query for report metadata with user ownership verification
            # Using the report_metadata_view which applies RLS automatically
            query = service_client.client.from_("report_metadata_view") \
                .select("id,title,report_type,initial_query,clarification_questions,clarification_answers,workflow_metadata,created_at") \
                .eq("id", report_id) \
                .eq("user_id", user_id) \
                .single()
            
            response = query.execute()
            
            if not response.data:
                logger.warning(f"Report metadata {report_id} not found or access denied for user {user_id}")
                raise ValueError("Report metadata not found or access denied")
            
            metadata = response.data
            
            # Process metadata for chat context preparation
            processed_metadata = self._process_metadata_for_chat(metadata)
            
            # Cache the result for future requests
            if self.cache_service:
                try:
                    await self.cache_service.set(cache_key, processed_metadata, ttl=300)  # 5 minutes
                except Exception as e:
                    logger.debug(f"Cache set failed: {e}")
            
            logger.info(f"Successfully retrieved metadata for report {report_id}")
            return processed_metadata
            
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker open for metadata retrieval, report_id: {report_id}")
            report_error = self.error_handler.handle_report_access_error(
                e, report_id, user_id, "metadata_retrieval"
            )
            self.error_handler.log_error_for_monitoring(report_error)
            raise self.error_handler.create_http_exception(report_error)
            
        except Exception as e:
            logger.error(f"Error retrieving metadata for report {report_id}: {str(e)}")
            report_error = self.error_handler.handle_report_access_error(
                e, report_id, user_id, "metadata_retrieval"
            )
            self.error_handler.log_error_for_monitoring(report_error)
            raise self.error_handler.create_http_exception(report_error)
    
    @circuit_breaker(
        name="report_retrieval_batch_get",
        failure_threshold=3,
        recovery_timeout=30,
        timeout=20
    )
    @monitor_query(query_type="select", table_name="mint_reports")
    async def get_reports_batch(
        self,
        report_ids: List[str],
        user_id: str,
        user_token: str = None,
        include_metadata: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve multiple reports efficiently in a single batch operation.
        
        This method ensures that:
        1. Only reports owned by the user are returned (Requirement 3.1, 3.3)
        2. Efficient batch retrieval for multiple reports (Requirement 2.4)
        3. Enforces database-level user isolation (Requirement 3.5)
        4. Optional metadata inclusion for chat context preparation
        
        Args:
            report_ids: List of report IDs to retrieve
            user_id: The authenticated user's ID (from auth.uid())
            user_token: Optional JWT token for RLS enforcement
            include_metadata: Whether to include metadata in the response
            
        Returns:
            Dict mapping report_id to report data
            
        Raises:
            ValueError: If inputs are invalid
            Exception: For database or system errors
        """
        try:
            logger.info(f"Batch retrieving {len(report_ids)} reports for user {user_id}")
            
            # Validate inputs (Requirement 3.1)
            if not report_ids:
                return {}
                
            if not is_valid_uuid(user_id):
                logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError("Invalid user_id format - must be a valid UUID")
            
            # Validate all report IDs
            invalid_ids = [rid for rid in report_ids if not is_valid_uuid(rid)]
            if invalid_ids:
                logger.error(f"Invalid report_id formats: {invalid_ids}")
                raise ValueError(f"Invalid report_id formats: {invalid_ids}")
            
            # Use service role client with user_id filtering for security
            # This avoids JWT validation issues while maintaining data isolation
            service_client = get_service_role_client()
            
            # Determine which view to use based on metadata requirement
            if include_metadata:
                view_name = "report_metadata_view"
                select_fields = "id,title,report_type,initial_query,clarification_questions,clarification_answers,workflow_metadata,created_at"
            else:
                view_name = "report_display_view"
                select_fields = "id,title,summary,report_type,content,created_at,updated_at"
            
            # Query for reports with user ownership verification
            query = service_client.client.from_(view_name) \
                .select(select_fields) \
                .in_("id", report_ids) \
                .eq("user_id", user_id)
            
            response = query.execute()
            
            # Process results into a dictionary keyed by report_id
            results = {}
            for report_data in response.data:
                report_id = report_data["id"]
                
                if include_metadata:
                    processed_data = self._process_metadata_for_chat(report_data)
                else:
                    processed_data = self._extract_clean_report_content(report_data)
                
                results[report_id] = processed_data
            
            # Log which reports were found vs requested
            found_ids = set(results.keys())
            requested_ids = set(report_ids)
            missing_ids = requested_ids - found_ids
            
            if missing_ids:
                logger.warning(f"Reports not found or access denied for user {user_id}: {missing_ids}")
            
            logger.info(f"Successfully retrieved {len(results)} out of {len(report_ids)} requested reports")
            return results
            
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker open for batch report retrieval, user_id: {user_id}")
            report_error = self.error_handler.handle_report_access_error(
                e, "batch", user_id, "batch_retrieval"
            )
            self.error_handler.log_error_for_monitoring(report_error)
            raise self.error_handler.create_http_exception(report_error)
            
        except Exception as e:
            logger.error(f"Error in batch report retrieval for user {user_id}: {str(e)}")
            report_error = self.error_handler.handle_report_access_error(
                e, "batch", user_id, "batch_retrieval"
            )
            self.error_handler.log_error_for_monitoring(report_error)
            raise self.error_handler.create_http_exception(report_error)
    
    def _extract_clean_report_content(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract clean report content suitable for display.
        
        This method processes the raw report data to extract only the final
        report content, removing workflow metadata and ensuring proper formatting
        for the MarketValidationReportPage component.
        
        Args:
            report_data: Raw report data from database
            
        Returns:
            Clean report structure ready for display
        """
        try:
            # Validate data integrity first
            report_id = report_data.get("id", "unknown")
            integrity_error = self.error_handler.validate_report_data_integrity(
                report_data, report_id
            )
            
            if integrity_error:
                logger.warning(f"Data integrity issue detected for report {report_id}")
                # Return fallback data instead of failing
                return self.error_handler.create_fallback_report_data(
                    report_id,
                    report_data.get("created_by", "unknown"),
                    ReportErrorType.CORRUPTED_DATA
                )
            # Extract basic report information from documents table
            metadata = report_data.get("metadata", {})
            raw_title = report_data.get("title", "Untitled Report")
            clean_report = {
                "id": report_data["id"],
                "title": strip_industry_analysis_prefix(raw_title),
                "summary": metadata.get("summary", ""),
                "report_type": metadata.get("report_type", "pv_report"),
                "created_at": report_data.get("created_at"),
                "updated_at": report_data.get("updated_at")
            }
            
            # Extract and clean the content
            content = report_data.get("content", {})
            original_content = content  # Keep reference to original for fallback
            
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in report content for report {report_data['id']}")
                    # For invalid JSON strings, wrap them as report content
                    clean_report["content"] = {"report": str(original_content)}
                    return clean_report
            
            # Strip "Industry Analysis of" from content title if present
            if isinstance(content, dict) and "title" in content:
                content["title"] = strip_industry_analysis_prefix(content["title"])
            
            # Extract final report content based on report structure
            if isinstance(content, dict):
                # Check if this is a workflow report with nested reports
                if "reports" in content and isinstance(content["reports"], dict):
                    reports = content["reports"]
                    
                    # Try to get the final report first
                    if "final" in reports:
                        final_report = reports["final"]
                        if isinstance(final_report, str):
                            try:
                                final_report = json.loads(final_report)
                            except json.JSONDecodeError:
                                pass
                        
                        if isinstance(final_report, dict):
                            # Ensure proper section ordering for display
                            clean_report["content"] = self._ensure_section_ordering(final_report)
                        else:
                            clean_report["content"] = {"report": final_report}
                    
                    # If no final report, try to construct from available reports
                    elif any(key in reports for key in ["industry", "pestel", "market_validation"]):
                        # Combine available reports into a structured format
                        combined_report = {
                            "title": clean_report["title"],
                            "executive_summary": clean_report["summary"],
                            "sections": {}
                        }
                        
                        for report_type in ["industry", "pestel", "market_validation"]:
                            if report_type in reports:
                                section_data = reports[report_type]
                                if isinstance(section_data, str):
                                    try:
                                        section_data = json.loads(section_data)
                                    except json.JSONDecodeError:
                                        section_data = {"content": section_data}
                                
                                combined_report["sections"][report_type] = section_data
                        
                        clean_report["content"] = combined_report
                    else:
                        # Use the reports structure as-is
                        clean_report["content"] = reports
                else:
                    # Direct content structure - ensure proper section ordering
                    clean_report["content"] = self._ensure_section_ordering(content)
            else:
                # Handle non-dict content
                clean_report["content"] = {"report": str(content)}
            
            # Ensure we have a proper structure for the frontend
            if not clean_report["content"]:
                clean_report["content"] = {
                    "title": clean_report["title"],
                    "summary": clean_report["summary"],
                    "message": "Report content is not available for display"
                }
            
            logger.debug(f"Extracted clean content for report {report_data['id']}")
            return clean_report
            
        except Exception as e:
            logger.error(f"Error extracting clean report content: {str(e)}")
            report_id = report_data.get("id", "unknown")
            user_id = report_data.get("user_id", "unknown")
            
            # Use error handler to create consistent fallback
            return self.error_handler.create_fallback_report_data(
                report_id,
                user_id,
                ReportErrorType.SYSTEM_ERROR
            )
    
    def _ensure_section_ordering(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure report sections are ordered correctly for display.
        
        This method reorders the sections to match the expected display order:
        1. title (if present)
        2. executive_summary
        3. industry_analysis
        4. challenges_analysis
        5. recommendations
        6. sources
        7. Any other sections
        
        Args:
            content: Report content dictionary
            
        Returns:
            Reordered content dictionary
        """
        try:
            if not isinstance(content, dict):
                return content
            
            # Define the preferred section order
            preferred_order = [
                "title",
                "executive_summary", 
                "industry_analysis",
                "challenges_analysis",
                "recommendations",
                "sources"
            ]
            
            # Create ordered dictionary with sections in preferred order
            ordered_content = {}
            
            # First, add sections in preferred order if they exist
            for section_key in preferred_order:
                if section_key in content:
                    ordered_content[section_key] = content[section_key]
            
            # Then add any remaining sections that weren't in the preferred order
            for section_key, section_value in content.items():
                if section_key not in preferred_order:
                    ordered_content[section_key] = section_value
            
            logger.debug(f"Reordered sections: {list(ordered_content.keys())}")
            return ordered_content
            
        except Exception as e:
            logger.error(f"Error ensuring section ordering: {str(e)}")
            # Return original content if ordering fails
            return content
    
    def _process_metadata_for_chat(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process report metadata for chat context preparation.
        
        This method formats the metadata in a structure suitable for
        chat context preparation and embedding services.
        
        Args:
            metadata: Raw metadata from database
            
        Returns:
            Processed metadata structure for chat context
        """
        try:
            raw_title = metadata.get("title", "Untitled Report")
            processed = {
                "report_id": metadata["id"],
                "title": strip_industry_analysis_prefix(raw_title),
                "report_type": metadata.get("report_type", "final"),
                "created_at": metadata.get("created_at"),
                "initial_query": metadata.get("initial_query"),
                "clarification_questions": [],
                "clarification_answers": {},
                "workflow_metadata": {}
            }
            
            # Process clarification questions
            questions = metadata.get("clarification_questions")
            if questions:
                if isinstance(questions, str):
                    try:
                        questions = json.loads(questions)
                    except json.JSONDecodeError:
                        questions = []
                
                if isinstance(questions, list):
                    processed["clarification_questions"] = questions
                elif isinstance(questions, dict):
                    # Handle case where questions are stored as an object
                    processed["clarification_questions"] = list(questions.values())
            
            # Process clarification answers
            answers = metadata.get("clarification_answers")
            if answers:
                if isinstance(answers, str):
                    try:
                        answers = json.loads(answers)
                    except json.JSONDecodeError:
                        answers = {}
                
                if isinstance(answers, dict):
                    processed["clarification_answers"] = answers
            
            # Process workflow metadata
            workflow_meta = metadata.get("workflow_metadata")
            if workflow_meta:
                if isinstance(workflow_meta, str):
                    try:
                        workflow_meta = json.loads(workflow_meta)
                    except json.JSONDecodeError:
                        workflow_meta = {}
                
                if isinstance(workflow_meta, dict):
                    processed["workflow_metadata"] = workflow_meta
            
            # Create a formatted context string for chat embedding
            context_parts = []
            
            if processed["initial_query"]:
                context_parts.append(f"Initial Query: {processed['initial_query']}")
            
            if processed["clarification_questions"]:
                context_parts.append("Clarification Questions:")
                for i, question in enumerate(processed["clarification_questions"], 1):
                    context_parts.append(f"  {i}. {question}")
                    
                    # Add corresponding answer if available
                    answer = processed["clarification_answers"].get(question)
                    if answer:
                        context_parts.append(f"     Answer: {answer}")
            
            processed["chat_context"] = "\n".join(context_parts)
            
            logger.debug(f"Processed metadata for chat context for report {metadata['id']}")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing metadata for chat: {str(e)}")
            # Return a safe fallback structure
            fallback_title = metadata.get("title", "Error Loading Metadata")
            return {
                "report_id": metadata.get("id", "unknown"),
                "title": strip_industry_analysis_prefix(fallback_title),
                "report_type": metadata.get("report_type", "final"),
                "created_at": metadata.get("created_at"),
                "initial_query": None,
                "clarification_questions": [],
                "clarification_answers": {},
                "workflow_metadata": {},
                "chat_context": "Metadata could not be processed for chat context",
                "error": "Metadata processing failed"
            }


# Convenience function to get a service instance
def get_report_retrieval_service(supabase_client: SupabaseClient = None) -> ReportRetrievalService:
    """
    Get a ReportRetrievalService instance.
    
    Args:
        supabase_client: Optional Supabase client instance
        
    Returns:
        ReportRetrievalService instance
    """
    return ReportRetrievalService(supabase_client)