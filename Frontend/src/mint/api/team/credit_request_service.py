"""
Service layer for Team Credit Request system.
Handles business logic for credit requests, approvals, and notifications.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import HTTPException

from ..system.core.supabase_client import get_service_role_client
from ..organization.service import OrganizationService
from ..credit.service import CreditService
from .service import TeamService

logger = logging.getLogger(__name__)


class CreditRequestService:
    """Service for managing team credit requests."""

    def __init__(self, use_service_role: bool = True):
        """Initialize the credit request service."""
        self.client = get_service_role_client() if use_service_role else None
        self.org_service = OrganizationService(use_service_role=True)
        self.credit_service = CreditService()
        self.team_service = TeamService()

    def create_request(
        self,
        team_id: str,
        requester_id: str,
        requested_credits: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new credit request from a team leader.
        
        Args:
            team_id: Team requesting credits
            requester_id: User submitting the request
            requested_credits: Number of credits requested
            reason: Optional reason for the request
            
        Returns:
            Created request record
            
        Raises:
            HTTPException: If validation fails or creation fails
        """
        try:
            # 1. Verify team exists and get organization_id
            team_query = (
                self.client.client.table("tenants")
                .select("id, name, settings")
                .eq("id", team_id)
                .eq("tenant_type", "team")
                .eq("is_active", True)
                .execute()
            )
            
            if not team_query.data:
                raise HTTPException(status_code=404, detail="Team not found")
            
            team = team_query.data[0]
            organization_id = team.get("settings", {}).get("organization_id")
            
            if not organization_id:
                raise HTTPException(
                    status_code=400,
                    detail="Team is not associated with an organization"
                )
            
            # 2. Verify requester is a team member
            membership_query = (
                self.client.client.table("tenant_memberships")
                .select("id")
                .eq("tenant_id", team_id)
                .eq("user_id", requester_id)
                .eq("is_active", True)
                .execute()
            )
            
            if not membership_query.data:
                raise HTTPException(
                    status_code=403,
                    detail="User is not a member of this team"
                )
            
            # 3. Check for existing pending requests (optional - prevent duplicates)
            existing_query = (
                self.client.client.table("team_credit_requests")
                .select("id")
                .eq("team_id", team_id)
                .eq("status", "pending")
                .execute()
            )
            
            if existing_query.data:
                logger.warning(f"Team {team_id} already has a pending credit request")
                # Allow multiple pending requests for now
                # raise HTTPException(
                #     status_code=400,
                #     detail="Team already has a pending credit request"
                # )
            
            # 4. Create the request
            request_data = {
                "team_id": team_id,
                "organization_id": organization_id,
                "requester_id": requester_id,
                "requested_credits": requested_credits,
                "reason": reason,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = (
                self.client.client.table("team_credit_requests")
                .insert(request_data)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create credit request"
                )
            
            created_request = result.data[0]
            
            # 5. TODO: Send notification to org admins
            # self._notify_org_admins_new_request(organization_id, created_request)
            
            logger.info(
                f"Credit request created: {created_request['id']} "
                f"for team {team_id} requesting {requested_credits} credits"
            )
            
            return created_request
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating credit request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create credit request: {str(e)}"
            )

    def get_team_requests(
        self,
        team_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get all credit requests for a team.
        
        Args:
            team_id: Team ID
            status: Optional status filter
            page: Page number
            page_size: Items per page
            
        Returns:
            List of requests with pagination info
        """
        try:
            # Build query
            query = (
                self.client.client.table("team_credit_requests")
                .select("*, requester:requester_id(id, email, raw_user_meta_data), reviewer:reviewed_by(id, email, raw_user_meta_data)", count="exact")
                .eq("team_id", team_id)
                .order("created_at", desc=True)
            )
            
            if status:
                query = query.eq("status", status)
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)
            
            result = query.execute()
            
            # Format response
            requests = []
            for req in result.data or []:
                requester = req.get("requester", {})
                reviewer = req.get("reviewer", {})
                
                formatted_req = {
                    "request_id": req["id"],
                    "team_id": req["team_id"],
                    "organization_id": req["organization_id"],
                    "requester_id": req["requester_id"],
                    "requester_email": requester.get("email"),
                    "requester_name": requester.get("raw_user_meta_data", {}).get("full_name"),
                    "requested_credits": req["requested_credits"],
                    "reason": req.get("reason"),
                    "status": req["status"],
                    "reviewed_by": req.get("reviewed_by"),
                    "reviewed_by_name": reviewer.get("raw_user_meta_data", {}).get("full_name") if reviewer else None,
                    "reviewed_at": req.get("reviewed_at"),
                    "review_notes": req.get("review_notes"),
                    "credits_allocated": req.get("credits_allocated"),
                    "created_at": req["created_at"],
                    "updated_at": req["updated_at"]
                }
                requests.append(formatted_req)
            
            # Count pending requests
            pending_count = len([r for r in requests if r["status"] == "pending"])
            
            return {
                "requests": requests,
                "total_count": result.count or 0,
                "pending_count": pending_count,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"Error fetching team requests: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch credit requests: {str(e)}"
            )

    def get_organization_requests(
        self,
        organization_id: str,
        status: Optional[str] = None,
        team_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get all credit requests for an organization.
        
        Args:
            organization_id: Organization ID
            status: Optional status filter
            team_id: Optional team filter
            page: Page number
            page_size: Items per page
            
        Returns:
            List of requests with pagination and team metrics
        """
        try:
            # Build query
            query = (
                self.client.client.table("team_credit_requests")
                .select(
                    "*, "
                    "team:team_id(id, name), "
                    "requester:requester_id(id, email, raw_user_meta_data), "
                    "reviewer:reviewed_by(id, email, raw_user_meta_data)",
                    count="exact"
                )
                .eq("organization_id", organization_id)
                .order("created_at", desc=True)
            )
            
            if status:
                query = query.eq("status", status)
            
            if team_id:
                query = query.eq("team_id", team_id)
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.range(offset, offset + page_size - 1)
            
            result = query.execute()
            
            # Format response with team metrics
            requests = []
            for req in result.data or []:
                team = req.get("team", {})
                requester = req.get("requester", {})
                reviewer = req.get("reviewer", {})
                
                # Get current team metrics
                team_metrics = None
                try:
                    team_metrics = self.team_service.get_team_metrics(req["team_id"])
                except:
                    pass
                
                formatted_req = {
                    "request_id": req["id"],
                    "team_id": req["team_id"],
                    "team_name": team.get("name"),
                    "organization_id": req["organization_id"],
                    "requester_id": req["requester_id"],
                    "requester_name": requester.get("raw_user_meta_data", {}).get("full_name"),
                    "requester_email": requester.get("email"),
                    "requested_credits": req["requested_credits"],
                    "reason": req.get("reason"),
                    "status": req["status"],
                    "reviewed_by": req.get("reviewed_by"),
                    "reviewed_by_name": reviewer.get("raw_user_meta_data", {}).get("full_name") if reviewer else None,
                    "reviewed_at": req.get("reviewed_at"),
                    "review_notes": req.get("review_notes"),
                    "credits_allocated": req.get("credits_allocated"),
                    "created_at": req["created_at"],
                    "updated_at": req["updated_at"],
                    "current_team_credits": team_metrics.get("credits_remaining") if team_metrics else None
                }
                requests.append(formatted_req)
            
            # Count pending requests
            pending_count = len([r for r in requests if r["status"] == "pending"])
            
            return {
                "requests": requests,
                "total_count": result.count or 0,
                "pending_count": pending_count,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"Error fetching organization requests: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch credit requests: {str(e)}"
            )

    def review_request(
        self,
        request_id: str,
        reviewer_id: str,
        action: str,
        credits_to_allocate: Optional[int] = None,
        review_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve or reject a credit request.
        
        Args:
            request_id: Request ID
            reviewer_id: Admin reviewing the request
            action: 'approve' or 'reject'
            credits_to_allocate: Credits to allocate (required for approval)
            review_notes: Optional review notes
            
        Returns:
            Updated request record
            
        Raises:
            HTTPException: If validation fails or review fails
        """
        try:
            # 1. Get the request
            request_query = (
                self.client.client.table("team_credit_requests")
                .select("*")
                .eq("id", request_id)
                .execute()
            )
            
            if not request_query.data:
                raise HTTPException(status_code=404, detail="Request not found")
            
            request = request_query.data[0]
            
            # 2. Verify request is pending
            if request["status"] != "pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"Request is already {request['status']}"
                )
            
            # 3. Handle approval
            if action == "approve":
                if not credits_to_allocate or credits_to_allocate <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="credits_to_allocate is required and must be > 0 for approval"
                    )
                
                # Check org has sufficient credits
                available_credits = self.credit_service.get_available_credits(
                    request["organization_id"]
                )
                
                if credits_to_allocate > available_credits:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient organization credits. Available: {available_credits}, Requested: {credits_to_allocate}"
                    )
                
                # Allocate credits using existing service
                try:
                    allocation_result = self.org_service.allocate_from_org_to_user(
                        organization_id=request["organization_id"],
                        user_id=request["requester_id"],
                        credits=credits_to_allocate,
                        reason=f"Credit request approved: {request_id}"
                    )
                    
                    logger.info(
                        f"Credits allocated: {credits_to_allocate} to user {request['requester_id']} "
                        f"from org {request['organization_id']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to allocate credits: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to allocate credits: {str(e)}"
                    )
                
                # Update request status
                update_data = {
                    "status": "approved",
                    "reviewed_by": reviewer_id,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "review_notes": review_notes,
                    "credits_allocated": credits_to_allocate,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                message = f"Credit request approved and {credits_to_allocate} credits allocated"
                
            else:  # reject
                update_data = {
                    "status": "rejected",
                    "reviewed_by": reviewer_id,
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "review_notes": review_notes,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                message = "Credit request rejected"
            
            # 4. Update the request
            result = (
                self.client.client.table("team_credit_requests")
                .update(update_data)
                .eq("id", request_id)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update request"
                )
            
            updated_request = result.data[0]
            
            # 5. TODO: Send notification to team leader
            # self._notify_team_leader_review(updated_request)
            
            logger.info(
                f"Credit request {request_id} {action}ed by {reviewer_id}"
            )
            
            return {
                "success": True,
                "request_id": request_id,
                "status": updated_request["status"],
                "credits_allocated": updated_request.get("credits_allocated"),
                "reviewed_by": reviewer_id,
                "reviewed_at": updated_request["reviewed_at"],
                "message": message
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reviewing request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to review request: {str(e)}"
            )

    def cancel_request(
        self,
        request_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a pending credit request.
        
        Args:
            request_id: Request ID
            user_id: User cancelling the request
            
        Returns:
            Success response
            
        Raises:
            HTTPException: If validation fails or cancellation fails
        """
        try:
            # 1. Get the request
            request_query = (
                self.client.client.table("team_credit_requests")
                .select("*")
                .eq("id", request_id)
                .execute()
            )
            
            if not request_query.data:
                raise HTTPException(status_code=404, detail="Request not found")
            
            request = request_query.data[0]
            
            # 2. Verify user is the requester
            if request["requester_id"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Only the requester can cancel this request"
                )
            
            # 3. Verify request is pending
            if request["status"] != "pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot cancel {request['status']} request"
                )
            
            # 4. Update status to cancelled
            result = (
                self.client.client.table("team_credit_requests")
                .update({
                    "status": "cancelled",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("id", request_id)
                .execute()
            )
            
            if not result.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to cancel request"
                )
            
            logger.info(f"Credit request {request_id} cancelled by {user_id}")
            
            return {
                "success": True,
                "request_id": request_id,
                "message": "Credit request cancelled successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to cancel request: {str(e)}"
            )
