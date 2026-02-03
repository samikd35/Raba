"""
Report Sharing Service

Business logic for sharing problem validation reports with external stakeholders.
Handles share creation, access control, analytics, and security.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import bcrypt
from supabase import Client

from ..models.sharing_models import (
    AccessLogEntry,
    AccessLogsResponse,
    AccessShareRequest,
    AccessShareResponse,
    CreateShareRequest,
    CreateShareResponse,
    RevokeShareRequest,
    RevokeShareResponse,
    ShareAnalyticsResponse,
    ShareInfo,
    ShareListResponse,
    SharedReportContent,
    UpdateShareRequest,
    UpdateShareResponse,
)
from ..api.system.core.supabase_client import get_supabase_client
from ..api.report.report_retrieval_service import ReportRetrievalService, strip_industry_analysis_prefix

logger = logging.getLogger(__name__)


class SharingService:
    """Service for managing report sharing"""
    
    def __init__(self, use_service_role: bool = False):
        """Initialize sharing service"""
        supabase_wrapper = get_supabase_client(use_service_role=use_service_role)
        self.supabase = supabase_wrapper.client  # Get the actual Supabase client
        self.use_service_role = use_service_role
        self.report_retrieval_service = ReportRetrievalService(supabase_wrapper)
    
    # =============================================
    # SHARE CREATION & MANAGEMENT
    # =============================================
    
    def _generate_share_token(self) -> str:
        """Generate a secure random share token"""
        return secrets.token_urlsafe(32)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    async def create_share(
        self,
        request: CreateShareRequest,
        user_id: str,
        tenant_id: str,
        base_url: str = "https://app.example.com"
    ) -> CreateShareResponse:
        """
        Create a new share link for a PV report.
        
        Args:
            request: Share creation request (uses report_id from documents table)
            user_id: ID of user creating the share
            tenant_id: Tenant ID for RLS
            base_url: Base URL for generating share links
            
        Returns:
            CreateShareResponse with share info
        """
        try:
            logger.info(f"Creating share for report {request.session_id} by user {user_id}")
            logger.info(f"🔍 SHARE DEBUG: tenant_id={tenant_id}, base_url={base_url}")
            
            # Get the report from documents table
            # session_id can be either the document ID or a session_id in metadata
            report_id_or_session = request.session_id
            
            # Try direct lookup first
            report_result = self.supabase.table("documents").select(
                "id, title, created_by, metadata"
            ).eq("id", report_id_or_session).eq("source_type", "pv_report").execute()
            
            if not report_result.data:
                # Try session_id lookup in metadata
                all_reports = self.supabase.table("documents").select(
                    "id, title, created_by, metadata"
                ).eq("source_type", "pv_report").eq("created_by", user_id).execute()
                
                matching_report = None
                for doc in all_reports.data:
                    metadata = doc.get("metadata", {})
                    if metadata.get("session_id") == report_id_or_session:
                        matching_report = doc
                        break
                
                if not matching_report:
                    return CreateShareResponse(
                        success=False,
                        message="Report not found or access denied",
                        share=None
                    )
                report = matching_report
            else:
                report = report_result.data[0]
                # Verify ownership
                if report["created_by"] != user_id:
                    return CreateShareResponse(
                        success=False,
                        message="Access denied - you can only share your own reports",
                        share=None
                    )
            
            report_id = report["id"]
            
            # Generate share token
            share_token = self._generate_share_token()
            
            # Hash password if provided
            password_hash = None
            if request.password:
                password_hash = self._hash_password(request.password)
            
            # Calculate expiration
            expires_at = None
            if request.expires_in_days:
                expires_at = datetime.now() + timedelta(days=request.expires_in_days)
            
            # Create share record
            share_data = {
                "report_id": report_id,
                "session_id": report_id_or_session,  # Store original identifier
                "user_id": user_id,
                "tenant_id": tenant_id,
                "share_token": share_token,
                "password_hash": password_hash,
                "access_type": request.access_type,
                "is_public": request.is_public,
                "allowed_emails": request.allowed_emails,
                "max_views": request.max_views,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "share_message": request.share_message,
            }
            
            logger.info(f"🔍 SHARE DEBUG: Inserting share record with data keys: {list(share_data.keys())}")
            logger.info(f"🔍 SHARE DEBUG: share_data = {{report_id: {share_data.get('report_id')}, session_id: {share_data.get('session_id')}, user_id: {share_data.get('user_id')}, tenant_id: {share_data.get('tenant_id')}}}")
            
            try:
                result = self.supabase.table("report_shares").insert(share_data).execute()
                logger.info(f"🔍 SHARE DEBUG: Insert result data: {result.data}")
            except Exception as insert_error:
                logger.error(f"❌ SHARE INSERT ERROR: {str(insert_error)}")
                logger.error(f"❌ SHARE INSERT ERROR type: {type(insert_error).__name__}")
                # Check if it's a foreign key violation
                error_str = str(insert_error)
                if "23503" in error_str or "foreign key" in error_str.lower():
                    if "user_id" in error_str:
                        return CreateShareResponse(
                            success=False,
                            message="User profile not synchronized. Please contact support.",
                            share=None
                        )
                    elif "report_id" in error_str or "document" in error_str:
                        return CreateShareResponse(
                            success=False,
                            message="Report not found or has been deleted.",
                            share=None
                        )
                return CreateShareResponse(
                    success=False,
                    message=f"Database error creating share: {str(insert_error)}",
                    share=None
                )
            
            if not result.data:
                logger.error(f"❌ SHARE ERROR: Insert returned no data")
                return CreateShareResponse(
                    success=False,
                    message="Failed to create share - no data returned",
                    share=None
                )
            
            share_record = result.data[0]
            
            # Build share info
            share_info = self._build_share_info(share_record, report, base_url)
            
            logger.info(f"✅ Share created: {share_token}")
            
            return CreateShareResponse(
                success=True,
                message="Share link created successfully",
                share=share_info
            )
            
        except Exception as e:
            logger.error(f"❌ SHARE EXCEPTION: {str(e)}")
            logger.error(f"❌ SHARE EXCEPTION type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ SHARE TRACEBACK: {traceback.format_exc()}")
            return CreateShareResponse(
                success=False,
                message=f"Failed to create share: {str(e)}",
                share=None
            )
    
    async def list_shares(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        include_revoked: bool = False
    ) -> ShareListResponse:
        """
        List all shares created by a user.
        
        Args:
            user_id: User ID
            session_id: Optional filter by session
            include_revoked: Include revoked shares
            
        Returns:
            ShareListResponse with list of shares
        """
        try:
            query = self.supabase.table("report_shares").select(
                "*, documents!report_shares_document_id_fkey(title)"
            ).eq("user_id", user_id)
            
            if session_id:
                query = query.eq("session_id", session_id)
            
            if not include_revoked:
                query = query.eq("is_active", True)
            
            result = query.order("created_at", desc=True).execute()
            
            shares = []
            for share_record in result.data:
                report = share_record.get("documents", {})
                share_info = self._build_share_info(share_record, report)
                shares.append(share_info)
            
            return ShareListResponse(
                success=True,
                message=f"Found {len(shares)} shares",
                shares=shares,
                total=len(shares)
            )
            
        except Exception as e:
            logger.error(f"Error listing shares: {str(e)}")
            return ShareListResponse(
                success=False,
                message=f"Failed to list shares: {str(e)}",
                shares=[],
                total=0
            )
    
    async def update_share(
        self,
        share_id: str,
        request: UpdateShareRequest,
        user_id: str
    ) -> UpdateShareResponse:
        """
        Update share settings.
        
        Args:
            share_id: Share ID
            request: Update request
            user_id: User ID (for authorization)
            
        Returns:
            UpdateShareResponse with updated share info
        """
        try:
            # Build update data
            update_data = {}
            
            if request.is_active is not None:
                update_data["is_active"] = request.is_active
            
            if request.access_type is not None:
                update_data["access_type"] = request.access_type
            
            if request.password is not None:
                if request.password == "":
                    update_data["password_hash"] = None
                else:
                    update_data["password_hash"] = self._hash_password(request.password)
            
            if request.allowed_emails is not None:
                update_data["allowed_emails"] = request.allowed_emails
            
            if request.max_views is not None:
                update_data["max_views"] = request.max_views
            
            if request.expires_in_days is not None:
                expires_at = datetime.now() + timedelta(days=request.expires_in_days)
                update_data["expires_at"] = expires_at.isoformat()
            
            if request.share_message is not None:
                update_data["share_message"] = request.share_message
            
            if not update_data:
                return UpdateShareResponse(
                    success=False,
                    message="No fields to update",
                    share=None
                )
            
            # Update share
            result = self.supabase.table("report_shares").update(update_data).eq(
                "id", share_id
            ).eq("user_id", user_id).execute()
            
            if not result.data:
                return UpdateShareResponse(
                    success=False,
                    message="Share not found or access denied",
                    share=None
                )
            
            # Get updated share with document info
            share_result = self.supabase.table("report_shares").select(
                "*, documents!report_shares_document_id_fkey(title)"
            ).eq("id", share_id).execute()
            
            share_record = share_result.data[0]
            report = share_record.get("documents", {})
            share_info = self._build_share_info(share_record, report)
            
            return UpdateShareResponse(
                success=True,
                message="Share updated successfully",
                share=share_info
            )
            
        except Exception as e:
            logger.error(f"Error updating share: {str(e)}")
            return UpdateShareResponse(
                success=False,
                message=f"Failed to update share: {str(e)}",
                share=None
            )
    
    async def revoke_share(
        self,
        request: RevokeShareRequest,
        user_id: str
    ) -> RevokeShareResponse:
        """
        Revoke a share link.
        
        Args:
            request: Revoke request
            user_id: User ID (for authorization)
            
        Returns:
            RevokeShareResponse
        """
        try:
            # Call the database function
            result = self.supabase.rpc(
                "revoke_share",
                {"share_id_param": str(request.share_id), "user_id_param": user_id}
            ).execute()
            
            if result.data:
                return RevokeShareResponse(
                    success=True,
                    message="Share revoked successfully"
                )
            else:
                return RevokeShareResponse(
                    success=False,
                    message="Share not found or access denied"
                )
                
        except Exception as e:
            logger.error(f"Error revoking share: {str(e)}")
            return RevokeShareResponse(
                success=False,
                message=f"Failed to revoke share: {str(e)}"
            )
    
    # =============================================
    # SHARE ACCESS
    # =============================================
    
    async def access_shared_report(
        self,
        request: AccessShareRequest,
        accessor_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AccessShareResponse:
        """
        Access a shared report using share token.
        
        Args:
            request: Access request with token and optional password
            accessor_ip: IP address of accessor
            user_agent: User agent string
            
        Returns:
            AccessShareResponse with report content
        """
        try:
            # Get share record with document info
            share_result = self.supabase.table("report_shares").select(
                "*, documents!report_shares_document_id_fkey(id, title, content, created_by)"
            ).eq("share_token", request.share_token).execute()
            
            if not share_result.data:
                await self._log_access(
                    None, request, False, "Share token not found", accessor_ip, user_agent
                )
                return AccessShareResponse(
                    success=False,
                    message="Invalid share link",
                    report=None,
                    access_type="",
                    can_download=False
                )
            
            share = share_result.data[0]
            report = share.get("documents")
            
            # Debug: Check what we got from the join
            logger.info(f"🔍 Share data keys: {share.keys()}")
            logger.info(f"🔍 Report type: {type(report)}, value: {report}")
            
            # Handle case where join didn't work or report is missing
            if not report or isinstance(report, str):
                logger.error(f"Document join failed. Share data: {share}")
                return AccessShareResponse(
                    success=False,
                    message="Report not found or has been deleted",
                    report=None,
                    access_type="",
                    can_download=False
                )
            
            # Validate share
            validation_result = self._validate_share_access(share, request)
            if not validation_result["valid"]:
                await self._log_access(
                    share["id"], request, False, validation_result["reason"], accessor_ip, user_agent
                )
                return AccessShareResponse(
                    success=False,
                    message=validation_result["reason"],
                    report=None,
                    access_type="",
                    can_download=False
                )
            
            # Increment view count
            self.supabase.rpc(
                "increment_share_view_count",
                {"share_token_param": request.share_token}
            ).execute()
            
            # Get clean report content using the same service as history endpoint
            report_id = report["id"]
            created_by = report["created_by"]
            
            try:
                clean_report = await self.report_retrieval_service.get_report_for_display(
                    report_id=report_id,
                    user_id=created_by  # Use report owner's ID
                )
                
                # Debug: Log what we got from retrieval service
                logger.info(f"🔍 SHARING: Clean report keys: {clean_report.keys()}")
                logger.info(f"🔍 SHARING: Content keys: {clean_report.get('content', {}).keys() if isinstance(clean_report.get('content'), dict) else 'not a dict'}")
                
                # Build shared report content from clean report
                report_content = self._build_shared_report_content_from_clean(clean_report, share)
            except Exception as e:
                logger.error(f"Failed to retrieve clean report: {str(e)}")
                # Fallback to basic content extraction
                report_content = self._build_shared_report_content_fallback(report, share)
            
            # Log successful access
            await self._log_access(
                share["id"], request, True, None, accessor_ip, user_agent
            )
            
            return AccessShareResponse(
                success=True,
                message="Access granted",
                report=report_content,
                access_type=share["access_type"],
                can_download=share["access_type"] == "download"
            )
            
        except Exception as e:
            logger.error(f"Error accessing shared report: {str(e)}")
            return AccessShareResponse(
                success=False,
                message=f"Failed to access report: {str(e)}",
                report=None,
                access_type="",
                can_download=False
            )
    
    def _validate_share_access(
        self,
        share: Dict[str, Any],
        request: AccessShareRequest
    ) -> Dict[str, Any]:
        """Validate if share can be accessed"""
        
        # Check if active
        if not share["is_active"]:
            return {"valid": False, "reason": "This share link has been disabled"}
        
        # Check expiration
        if share["expires_at"]:
            expires_at = datetime.fromisoformat(share["expires_at"].replace('Z', '+00:00'))
            if datetime.now(expires_at.tzinfo) > expires_at:
                return {"valid": False, "reason": "This share link has expired"}
        
        # Check view limit
        if share["max_views"] and share["view_count"] >= share["max_views"]:
            return {"valid": False, "reason": "View limit reached for this share link"}
        
        # Check password
        if share["password_hash"]:
            if not request.password:
                return {"valid": False, "reason": "Password required"}
            if not self._verify_password(request.password, share["password_hash"]):
                return {"valid": False, "reason": "Incorrect password"}
        
        # Check email whitelist (only if NOT public)
        if not share.get("is_public", True):
            # Private share - email whitelist is enforced
            if share["allowed_emails"] and len(share["allowed_emails"]) > 0:
                if not request.accessor_email:
                    return {"valid": False, "reason": "Email required for access"}
                if request.accessor_email not in share["allowed_emails"]:
                    return {"valid": False, "reason": "Email not authorized"}
            else:
                # Private share but no allowed emails specified - deny access
                return {"valid": False, "reason": "This is a private share with no authorized emails"}
        # If is_public is True, skip email validation entirely
        
        return {"valid": True, "reason": None}
    
    def _build_shared_report_content_from_clean(
        self,
        clean_report: Dict[str, Any],
        share: Dict[str, Any]
    ) -> SharedReportContent:
        """Build shared report content from clean report (same as history endpoint)"""
        
        # Extract content from clean report structure
        content = clean_report.get("content", {})
        
        # The content might have nested structure, try to extract all possible fields
        # Check if content has a 'report' key (some reports store everything under 'report')
        if isinstance(content, dict) and "report" in content:
            actual_content = content.get("report", {})
            if isinstance(actual_content, str):
                # If report is a string, it might be the full report text
                import json
                try:
                    actual_content = json.loads(actual_content)
                except:
                    actual_content = {}
        else:
            actual_content = content
        
        # Try to get fields from multiple possible locations with field name mapping
        def get_field(field_name, alt_names=None):
            """Get field value, trying alternative names if primary not found"""
            if alt_names is None:
                alt_names = []
            
            # Try primary field name first
            for location in [actual_content, content, clean_report]:
                if field_name in location:
                    return location[field_name]
            
            # Try alternative field names
            for alt_name in alt_names:
                for location in [actual_content, content, clean_report]:
                    if alt_name in location:
                        return location[alt_name]
            
            return None
        
        # Build report content - use actual field names from PV reports
        raw_title = clean_report.get("title", "Untitled Report")
        return SharedReportContent(
            title=strip_industry_analysis_prefix(raw_title),
            executive_summary=get_field("executive_summary"),
            # PV Report sections - use actual field names
            industry_analysis=get_field("industry_analysis"),
            challenges_analysis=get_field("challenges_analysis"),
            recommendations=get_field("recommendations"),
            sources=get_field("sources"),
            report_type=clean_report.get("report_type", "problem_validation"),
            share_message=share.get("share_message"),
            shared_by="Report Owner",
            shared_at=datetime.fromisoformat(share["created_at"].replace('Z', '+00:00'))
        )
    
    def _build_shared_report_content_fallback(
        self,
        report: Dict[str, Any],
        share: Dict[str, Any]
    ) -> SharedReportContent:
        """Fallback method if clean report retrieval fails"""
        
        # Extract content from JSONB column
        content = report.get("content", {})
        
        # Handle case where content might be a JSON string
        if isinstance(content, str):
            import json
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse content JSON: {content[:100]}")
                content = {}
        
        # Build report content from the JSONB structure
        raw_title = report.get("title", "Untitled Report")
        return SharedReportContent(
            title=strip_industry_analysis_prefix(raw_title),
            executive_summary=content.get("executive_summary"),
            industry_analysis=content.get("industry_analysis"),
            challenges_analysis=content.get("challenges_analysis"),
            recommendations=content.get("recommendations"),
            sources=content.get("sources"),
            report_type=content.get("report_type", "problem_validation"),
            share_message=share.get("share_message"),
            shared_by="Report Owner",
            shared_at=datetime.fromisoformat(share["created_at"].replace('Z', '+00:00'))
        )
    
    async def _log_access(
        self,
        share_id: Optional[str],
        request: AccessShareRequest,
        access_granted: bool,
        denial_reason: Optional[str],
        accessor_ip: Optional[str],
        user_agent: Optional[str]
    ):
        """Log share access attempt"""
        try:
            if not share_id:
                return
            
            log_data = {
                "share_id": share_id,
                "accessor_email": request.accessor_email,
                "accessor_ip": accessor_ip,
                "user_agent": user_agent,
                "access_granted": access_granted,
                "access_denied_reason": denial_reason
            }
            
            self.supabase.table("share_access_logs").insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging access: {str(e)}")
    
    # =============================================
    # ANALYTICS
    # =============================================
    
    async def get_share_analytics(
        self,
        share_id: str,
        user_id: str
    ) -> ShareAnalyticsResponse:
        """
        Get analytics for a share.
        
        Args:
            share_id: Share ID
            user_id: User ID (for authorization)
            
        Returns:
            ShareAnalyticsResponse with analytics data
        """
        try:
            # Verify ownership
            share_result = self.supabase.table("report_shares").select("*").eq(
                "id", share_id
            ).eq("user_id", user_id).execute()
            
            if not share_result.data:
                return ShareAnalyticsResponse(
                    success=False,
                    message="Share not found or access denied",
                    analytics=None
                )
            
            share = share_result.data[0]
            
            # Get access logs
            logs_result = self.supabase.table("share_access_logs").select("*").eq(
                "share_id", share_id
            ).eq("access_granted", True).order("accessed_at", desc=True).execute()
            
            logs = logs_result.data
            
            # Calculate analytics
            total_views = len(logs)
            unique_emails = set(log["accessor_email"] for log in logs if log["accessor_email"])
            unique_accessors = len(unique_emails)
            
            last_accessed = None
            if logs:
                last_accessed = datetime.fromisoformat(logs[0]["accessed_at"].replace('Z', '+00:00'))
            
            # Group by date
            access_by_date = {}
            for log in logs:
                date = log["accessed_at"][:10]
                access_by_date[date] = access_by_date.get(date, 0) + 1
            
            access_by_date_list = [
                {"date": date, "count": count}
                for date, count in sorted(access_by_date.items())
            ]
            
            # Group by email
            access_by_email = {}
            for log in logs:
                email = log["accessor_email"] or "Anonymous"
                access_by_email[email] = access_by_email.get(email, 0) + 1
            
            access_by_email_list = [
                {"email": email, "count": count}
                for email, count in sorted(access_by_email.items(), key=lambda x: x[1], reverse=True)
            ]
            
            analytics = ShareAnalytics(
                share_id=UUID(share_id),
                total_views=total_views,
                unique_accessors=unique_accessors,
                last_accessed_at=last_accessed,
                access_by_date=access_by_date_list,
                access_by_email=access_by_email_list,
                access_by_location=None  # Could be enhanced with IP geolocation
            )
            
            return ShareAnalyticsResponse(
                success=True,
                message="Analytics retrieved successfully",
                analytics=analytics
            )
            
        except Exception as e:
            logger.error(f"Error getting share analytics: {str(e)}")
            return ShareAnalyticsResponse(
                success=False,
                message=f"Failed to get analytics: {str(e)}",
                analytics=None
            )
    
    async def get_access_logs(
        self,
        share_id: str,
        user_id: str,
        limit: int = 100
    ) -> AccessLogsResponse:
        """
        Get access logs for a share.
        
        Args:
            share_id: Share ID
            user_id: User ID (for authorization)
            limit: Maximum number of logs to return
            
        Returns:
            AccessLogsResponse with log entries
        """
        try:
            # Verify ownership
            share_result = self.supabase.table("report_shares").select("*").eq(
                "id", share_id
            ).eq("user_id", user_id).execute()
            
            if not share_result.data:
                return AccessLogsResponse(
                    success=False,
                    message="Share not found or access denied",
                    logs=[],
                    total=0
                )
            
            # Get logs
            logs_result = self.supabase.table("share_access_logs").select("*").eq(
                "share_id", share_id
            ).order("accessed_at", desc=True).limit(limit).execute()
            
            logs = [AccessLogEntry(**log) for log in logs_result.data]
            
            return AccessLogsResponse(
                success=True,
                message=f"Retrieved {len(logs)} access logs",
                logs=logs,
                total=len(logs)
            )
            
        except Exception as e:
            logger.error(f"Error getting access logs: {str(e)}")
            return AccessLogsResponse(
                success=False,
                message=f"Failed to get access logs: {str(e)}",
                logs=[],
                total=0
            )
    
    # =============================================
    # HELPER METHODS
    # =============================================
    
    def _build_share_info(
        self,
        share_record: Dict[str, Any],
        report: Dict[str, Any],
        base_url: str = "https://app.example.com"
    ) -> ShareInfo:
        """Build ShareInfo from database record"""
        
        share_token = share_record["share_token"]
        share_url = f"{base_url}/shared/{share_token}"
        
        # Check if expired
        is_expired = False
        if share_record.get("expires_at"):
            expires_at = datetime.fromisoformat(share_record["expires_at"].replace('Z', '+00:00'))
            is_expired = datetime.now(expires_at.tzinfo) > expires_at
        
        # Check if view limit reached
        is_view_limit_reached = False
        if share_record.get("max_views"):
            is_view_limit_reached = share_record["view_count"] >= share_record["max_views"]
        
        return ShareInfo(
            id=UUID(share_record["id"]),
            share_token=share_token,
            share_url=share_url,
            session_id=UUID(share_record["session_id"]),
            report_id=UUID(share_record["report_id"]),
            report_title=report.get("title", "Untitled Report"),
            access_type=share_record["access_type"],
            is_public=share_record["is_public"],
            has_password=share_record.get("password_hash") is not None,
            allowed_emails=share_record.get("allowed_emails"),
            max_views=share_record.get("max_views"),
            view_count=share_record["view_count"],
            expires_at=datetime.fromisoformat(share_record["expires_at"].replace('Z', '+00:00')) if share_record.get("expires_at") else None,
            is_active=share_record["is_active"],
            is_expired=is_expired,
            is_view_limit_reached=is_view_limit_reached,
            share_message=share_record.get("share_message"),
            created_at=datetime.fromisoformat(share_record["created_at"].replace('Z', '+00:00')),
            last_accessed_at=datetime.fromisoformat(share_record["last_accessed_at"].replace('Z', '+00:00')) if share_record.get("last_accessed_at") else None,
            revoked_at=datetime.fromisoformat(share_record["revoked_at"].replace('Z', '+00:00')) if share_record.get("revoked_at") else None
        )
