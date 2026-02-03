"""
User Workspaces API

Provides endpoints for users to view and switch between their workspaces
(organizations, teams, and personal workspace).
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth_v2.utils import get_current_user
from ..cache.decorators import cached_query
from ..organization.service import OrganizationService
from ..team.service import TeamService
from ..credit.service import CreditService

logger = logging.getLogger(__name__)

workspaces_router = APIRouter(prefix="/api/user/workspaces", tags=["user-workspaces"])


# =============================================
# RESPONSE MODELS
# =============================================

class OrganizationWorkspace(BaseModel):
    """Organization workspace information"""
    id: str
    name: str
    type: str = "organization"
    role: str
    member_count: int
    team_count: int
    credits_remaining: float
    last_accessed: Optional[str] = None
    is_active: bool
    description: Optional[str] = None


class TeamWorkspace(BaseModel):
    """Team workspace information"""
    id: str
    name: str
    type: str = "team"
    role: str
    organization_id: str
    organization_name: str
    member_count: int
    credits_remaining: float
    last_accessed: Optional[str] = None
    is_active: bool
    description: Optional[str] = None


class IndividualMemberWorkspace(BaseModel):
    """Individual member workspace within an organization"""
    id: str  # individual_tenant_id
    name: str
    type: str = "individual_member"
    role: str
    organization_id: str
    organization_name: str
    credits_remaining: float
    last_accessed: Optional[str] = None
    is_active: bool
    description: Optional[str] = None


class PersonalWorkspace(BaseModel):
    """Personal workspace information"""
    id: str
    name: str
    type: str = "personal"
    credits_remaining: float
    is_active: bool


class UserWorkspacesResponse(BaseModel):
    """Complete user workspaces response"""
    organizations: List[OrganizationWorkspace]
    teams: List[TeamWorkspace]
    individual_members: List[IndividualMemberWorkspace]
    personal: Optional[PersonalWorkspace]
    total_count: int


class WorkspaceListItem(BaseModel):
    """Simplified workspace list item"""
    id: str
    name: str
    type: str  # "organization", "team", "individual_member", or "personal"
    role: Optional[str] = None
    is_active: bool


class SimpleWorkspaceListResponse(BaseModel):
    """Simple list of all workspaces"""
    workspaces: List[WorkspaceListItem]
    total_count: int


class FastWorkspaceItem(BaseModel):
    """Optimized workspace item with essential display data"""
    id: str
    name: str
    type: str  # "organization", "team", "individual_member", or "personal"
    role: str
    member_count: int = 0
    description: Optional[str] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    is_active: bool = True
    total_credits: float = 0.0
    credits_remaining: float = 0.0


class FastWorkspacesResponse(BaseModel):
    """Optimized workspaces response - minimal queries, fast loading"""
    workspaces: List[FastWorkspaceItem]
    total_count: int


# =============================================
# ENDPOINTS
# =============================================

@workspaces_router.get("/contexts", response_model=UserWorkspacesResponse)
async def get_user_workspaces(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all workspaces (organizations, teams, personal) that the user has access to.
    
    This is the main endpoint for the workspace switcher UI.
    """
    try:
        user_id = current_user["user_id"]
        org_service = OrganizationService(use_service_role=True)
        team_service = TeamService(use_service_role=True)
        
        # ========================================
        # 1. GET USER'S ORGANIZATIONS
        # ========================================
        logger.info(f"🔍 Fetching organizations for user {user_id}")
        
        # Query tenant_memberships to get all organizations user belongs to
        org_memberships = org_service.client.client.table("tenant_memberships").select(
            "tenant_id, role, is_active, joined_at"
        ).eq("user_id", user_id).eq("is_active", True).execute()
        
        organizations = []
        org_ids = [m["tenant_id"] for m in org_memberships.data] if org_memberships.data else []
        
        # Get org-linked individual tenants for this user
        org_individuals_query = org_service.client.client.table("org_individuals").select(
            "organization_id, individual_tenant_id"
        ).eq("user_id", user_id).execute()
        
        # Map: individual_tenant_id -> organization_id
        individual_to_org_map = {
            item["individual_tenant_id"]: item["organization_id"] 
            for item in org_individuals_query.data
        } if org_individuals_query.data else {}
        
        # Map: organization_id -> individual_tenant_id (for credit lookup)
        org_to_individual_map = {
            item["organization_id"]: item["individual_tenant_id"]
            for item in org_individuals_query.data
        } if org_individuals_query.data else {}
        
        # Set of organization IDs where user has individual tenant (should not show as org)
        orgs_with_individual_tenant = set(org_to_individual_map.keys())
        
        logger.info(f"🔍 Found {len(individual_to_org_map)} org-linked individual tenants for user")
        logger.info(f"🔍 Organizations with individual tenant: {orgs_with_individual_tenant}")
        
        if org_ids:
            # Get organization details (filter out teams by checking org_teams table)
            # Organizations are tenants that are NOT in org_teams.team_id
            teams_query = org_service.client.client.table("org_teams").select("team_id").in_("team_id", org_ids).execute()
            team_ids_set = {t["team_id"] for t in teams_query.data} if teams_query.data else set()
            
            # Filter to get only organization IDs (not team IDs, not individual tenant IDs, not orgs with individual tenants)
            org_only_ids = [
                oid for oid in org_ids 
                if oid not in team_ids_set 
                and oid not in individual_to_org_map  # Exclude individual_tenant_ids
                and oid not in orgs_with_individual_tenant  # Exclude org_ids where user has individual tenant
            ]
            
            if org_only_ids:
                # Get organization tenant details (exclude individual tenants)
                orgs_data = org_service.client.client.table("tenants").select("*").in_("id", org_only_ids).neq("tenant_type", "individual").execute()
                
                for org in orgs_data.data if orgs_data.data else []:
                    org_id = org["id"]
                    
                    # Get user's role in this org
                    user_role = next(
                        (m["role"] for m in org_memberships.data if m["tenant_id"] == org_id),
                        "member"
                    )
                    
                    # Get member count
                    members = org_service.client.client.table("tenant_memberships").select(
                        "id", count="exact"
                    ).eq("tenant_id", org_id).eq("is_active", True).execute()
                    member_count = members.count or 0
                    
                    # Get team count
                    teams = org_service.client.client.table("org_teams").select(
                        "team_id", count="exact"
                    ).eq("organization_id", org_id).execute()
                    team_count = teams.count or 0
                    
                    # Get credits - check if user has individual tenant for this org
                    # If yes, use individual tenant's credits; otherwise use org credits
                    credit_tenant_id = org_to_individual_map.get(org_id, org_id)
                    
                    logger.info(
                        f"🔍 Fetching credits for org {org_id}: "
                        f"using tenant_id={credit_tenant_id} "
                        f"({'individual tenant' if credit_tenant_id != org_id else 'org tenant'})"
                    )
                    
                    # Use CreditService for proper credit calculation
                    credit_service = CreditService(use_service_role=True)
                    credit_summary = credit_service.get_credits_for_workspace_display(
                        credit_tenant_id, 
                        tenant_type="organization"
                    )
                    remaining_credits = credit_summary["remaining_credits"]
                    
                    organizations.append(OrganizationWorkspace(
                        id=org_id,
                        name=org["name"],
                        role=user_role,
                        member_count=member_count,
                        team_count=team_count,
                        credits_remaining=remaining_credits,
                        is_active=org.get("is_active", True),
                        description=org.get("description"),
                    ))
        
        logger.info(f"✅ Found {len(organizations)} organizations")
        
        # ========================================
        # 2. GET USER'S TEAMS
        # ========================================
        logger.info(f"🔍 Fetching teams for user {user_id}")
        
        teams = []
        team_only_ids = [tid for tid in org_ids if tid in team_ids_set]
        
        if team_only_ids:
            # Get team tenant details
            teams_data = team_service.supabase.table("tenants").select("*").in_("id", team_only_ids).execute()
            
            for team in teams_data.data if teams_data.data else []:
                team_id = team["id"]
                
                # Get user's role in this team
                user_role = next(
                    (m["role"] for m in org_memberships.data if m["tenant_id"] == team_id),
                    "member"
                )
                
                # Get parent organization
                org_link = team_service.supabase.table("org_teams").select(
                    "organization_id"
                ).eq("team_id", team_id).limit(1).execute()
                org_id = org_link.data[0]["organization_id"] if org_link.data else ""
                
                org_name = ""
                if org_id:
                    org_data = team_service.supabase.table("tenants").select(
                        "name"
                    ).eq("id", org_id).limit(1).execute()
                    org_name = org_data.data[0]["name"] if org_data.data else ""
                
                # Get member count
                members = team_service.supabase.table("tenant_memberships").select(
                    "id", count="exact"
                ).eq("tenant_id", team_id).eq("is_active", True).execute()
                member_count = members.count or 0
                
                # Use CreditService for proper credit calculation
                credit_service = CreditService(use_service_role=True)
                credit_summary = credit_service.get_credits_for_workspace_display(
                    team_id, 
                    tenant_type="team"
                )
                remaining_credits = credit_summary["remaining_credits"]
                
                teams.append(TeamWorkspace(
                    id=team_id,
                    name=team["name"],
                    role=user_role,
                    organization_id=org_id,
                    organization_name=org_name,
                    member_count=member_count,
                    credits_remaining=remaining_credits,
                    is_active=team.get("is_active", True),
                    description=team.get("description"),
                ))
        
        logger.info(f"✅ Found {len(teams)} teams")
        
        # ========================================
        # 3. GET INDIVIDUAL MEMBER WORKSPACES (ORG-LINKED INDIVIDUALS)
        # ========================================
        logger.info(f"🔍 Fetching individual member workspaces for user {user_id}")
        
        individual_members = []
        
        # Process org-linked individual tenants
        if org_individuals_query.data:
            for org_individual in org_individuals_query.data:
                individual_tenant_id = org_individual["individual_tenant_id"]
                org_id = org_individual["organization_id"]
                
                # Get individual tenant details
                individual_tenant = org_service.client.client.table("tenants").select(
                    "*"
                ).eq("id", individual_tenant_id).execute()
                
                if not individual_tenant.data:
                    continue
                
                tenant_data = individual_tenant.data[0]
                
                # Get user's role in the organization (not the individual tenant)
                user_role = next(
                    (m["role"] for m in org_memberships.data if m["tenant_id"] == org_id),
                    "member"
                )
                
                # Get organization name
                org_data = org_service.client.client.table("tenants").select(
                    "name"
                ).eq("id", org_id).limit(1).execute()
                org_name = org_data.data[0]["name"] if org_data.data else "Unknown Organization"
                
                # Use CreditService for proper credit calculation
                credit_service = CreditService(use_service_role=True)
                credit_summary = credit_service.get_credits_for_workspace_display(
                    individual_tenant_id, 
                    tenant_type="individual"
                )
                remaining_credits = credit_summary["remaining_credits"]
                
                logger.info(
                    f"🔍 Individual member workspace: {individual_tenant_id} "
                    f"(org: {org_id}, credits: {remaining_credits})"
                )
                
                individual_members.append(IndividualMemberWorkspace(
                    id=individual_tenant_id,  # Use individual_tenant_id as main id
                    name=org_name,  # Use organization name directly (cleaner display)
                    role=user_role,
                    organization_id=org_id,
                    organization_name=org_name,
                    credits_remaining=remaining_credits,
                    is_active=tenant_data.get("is_active", True),
                    description=tenant_data.get("description"),
                ))
        
        logger.info(f"✅ Found {len(individual_members)} individual member workspaces")
        
        # ========================================
        # 4. GET PERSONAL WORKSPACE (STANDALONE INDIVIDUAL TENANT)
        # ========================================
        logger.info(f"🔍 Fetching personal workspace for user {user_id}")
        
        personal = None
        
        # Find user's STANDALONE individual tenant (not linked to any organization)
        # Exclude org-linked individual tenants from personal workspace
        individual_memberships = org_service.client.client.table("tenant_memberships").select(
            "tenant_id, role, tenants!tenant_memberships_tenant_id_fkey(name, tenant_type, is_active)"
        ).eq("user_id", user_id).eq("role", "owner").eq("is_active", True).execute()
        
        if individual_memberships.data:
            for membership in individual_memberships.data:
                tenant_data = membership.get("tenants", {})
                tenant_id = membership["tenant_id"]
                
                # Only consider individual tenants that are NOT linked to organizations
                if (tenant_data and 
                    tenant_data.get("tenant_type") == "individual" and
                    tenant_id not in individual_to_org_map):
                    
                    logger.info(f"🔍 Found standalone personal workspace: {tenant_id}")
                    
                    # Use CreditService for proper credit calculation
                    credit_service = CreditService(use_service_role=True)
                    credit_summary = credit_service.get_credits_for_workspace_display(
                        tenant_id, 
                        tenant_type="individual"
                    )
                    remaining_credits = credit_summary["remaining_credits"]
                    
                    personal = PersonalWorkspace(
                        id=tenant_id,
                        name=tenant_data.get("name", "Personal Workspace"),
                        credits_remaining=remaining_credits,
                        is_active=tenant_data.get("is_active", True),
                    )
                    break  # Take the first standalone individual tenant found
                elif tenant_id in individual_to_org_map:
                    logger.info(
                        f"🔍 Skipping org-linked individual tenant {tenant_id} "
                        f"(belongs to org {individual_to_org_map[tenant_id]})"
                    )
        
        logger.info(f"✅ Personal workspace: {'Found' if personal else 'Not found'}")
        
        total_count = len(organizations) + len(teams) + len(individual_members) + (1 if personal else 0)
        
        return UserWorkspacesResponse(
            organizations=organizations,
            teams=teams,
            individual_members=individual_members,
            personal=personal,
            total_count=total_count,
        )
        
    except Exception as e:
        logger.error(f"❌ Error fetching user workspaces: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail="Failed to fetch workspaces")


@workspaces_router.get("/list", response_model=SimpleWorkspaceListResponse)
async def get_simple_workspace_list(
    current_user: dict = Depends(get_current_user),
):
    """
    Get a simple list of all workspaces for quick switching.
    
    This is a lighter endpoint for dropdown menus and quick access.
    """
    try:
        user_id = current_user["user_id"]
        org_service = OrganizationService(use_service_role=True)
        
        # Get all tenant memberships
        memberships = org_service.client.client.table("tenant_memberships").select(
            "tenant_id, role, tenants!tenant_memberships_tenant_id_fkey(name, tenant_type, is_active)"
        ).eq("user_id", user_id).eq("is_active", True).execute()
        
        workspaces = []
        
        if memberships.data:
            # Get team IDs to differentiate organizations from teams
            all_tenant_ids = [m["tenant_id"] for m in memberships.data]
            teams_query = org_service.client.client.table("org_teams").select(
                "team_id"
            ).in_("team_id", all_tenant_ids).execute()
            team_ids_set = {t["team_id"] for t in teams_query.data} if teams_query.data else set()
            
            # Get org-linked individual tenants
            org_individuals_query = org_service.client.client.table("org_individuals").select(
                "organization_id, individual_tenant_id"
            ).eq("user_id", user_id).execute()
            
            # Map: individual_tenant_id -> organization_id
            individual_to_org_map = {
                item["individual_tenant_id"]: item["organization_id"] 
                for item in org_individuals_query.data
            } if org_individuals_query.data else {}
            
            for membership in memberships.data:
                tenant_id = membership["tenant_id"]
                tenant_data = membership.get("tenants", {})
                
                if not tenant_data:
                    continue
                
                # Determine workspace type based on tenant_type and team membership
                tenant_type = tenant_data.get("tenant_type", "")
                if tenant_type == "individual":
                    # Check if this individual tenant is linked to an organization
                    if tenant_id in individual_to_org_map:
                        workspace_type = "individual_member"
                    else:
                        workspace_type = "personal"
                elif tenant_id in team_ids_set:
                    workspace_type = "team"
                else:
                    workspace_type = "organization"
                
                workspaces.append(WorkspaceListItem(
                    id=tenant_id,
                    name=tenant_data.get("name", "Unknown"),
                    type=workspace_type,
                    role=membership["role"],
                    is_active=tenant_data.get("is_active", True),
                ))
        
        return SimpleWorkspaceListResponse(
            workspaces=workspaces,
            total_count=len(workspaces),
        )
        
    except Exception as e:
        logger.error(f"❌ Error fetching workspace list: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail="Failed to fetch workspace list")


@workspaces_router.get("/organizations", response_model=List[OrganizationWorkspace])
async def get_user_organizations(
    current_user: dict = Depends(get_current_user),
):
    """
    Get only organizations that the user belongs to.
    """
    full_response = await get_user_workspaces(current_user)
    return full_response.organizations


@workspaces_router.get("/teams", response_model=List[TeamWorkspace])
async def get_user_teams(
    current_user: dict = Depends(get_current_user),
):
    """
    Get only teams that the user belongs to.
    """
    full_response = await get_user_workspaces(current_user)
    return full_response.teams


@workspaces_router.get("/fast", response_model=FastWorkspacesResponse)
@cached_query("user_workspaces_fast", ttl=60, user_specific=True)  # Reduced TTL: 60s instead of 600s for faster membership updates
async def get_fast_workspaces(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    🚀 OPTIMIZED: Get all workspaces with minimal database queries.
    
    This endpoint is designed for the workspace selection page where we need:
    - Name, type, role, member_count, description
    - NO credit calculations (expensive)
    - Uses batch queries instead of per-workspace queries
    
    Query optimization:
    - 1 query: Get all tenant memberships with tenant details (JOIN)
    - 1 query: Get team mappings (batch)
    - 1 query: Get org-individual mappings (batch)
    - 1 query: Get member counts (batch aggregation)
    - 1 query: Get team counts for orgs (batch aggregation)
    
    Total: ~5 queries instead of N*5 queries
    """
    try:
        user_id = current_user["user_id"]
        org_service = OrganizationService(use_service_role=True)
        credit_service = CreditService(use_service_role=True)
        db = org_service.client.client
        
        logger.info(f"🚀 FAST WORKSPACES: Starting optimized fetch for user {user_id}")
        
        # ========================================
        # QUERY 1: Get all memberships with tenant details (single JOIN query)
        # ========================================
        memberships = db.table("tenant_memberships").select(
            "tenant_id, role, tenants!tenant_memberships_tenant_id_fkey(id, name, tenant_type, is_active, description)"
        ).eq("user_id", user_id).eq("is_active", True).execute()
        
        if not memberships.data:
            logger.info("🚀 FAST WORKSPACES: No memberships found")
            return FastWorkspacesResponse(workspaces=[], total_count=0)
        
        all_tenant_ids = [m["tenant_id"] for m in memberships.data]
        logger.info(f"🚀 FAST WORKSPACES: Found {len(all_tenant_ids)} memberships")
        
        # ========================================
        # QUERY 2: Get team mappings (batch)
        # ========================================
        teams_query = db.table("org_teams").select(
            "team_id, organization_id"
        ).in_("team_id", all_tenant_ids).execute()
        
        team_to_org_map = {
            t["team_id"]: t["organization_id"] 
            for t in teams_query.data
        } if teams_query.data else {}
        team_ids_set = set(team_to_org_map.keys())
        
        # ========================================
        # QUERY 3: Get org-individual mappings (batch)
        # ========================================
        org_individuals_query = db.table("org_individuals").select(
            "organization_id, individual_tenant_id"
        ).eq("user_id", user_id).execute()
        
        individual_to_org_map = {
            item["individual_tenant_id"]: item["organization_id"] 
            for item in org_individuals_query.data
        } if org_individuals_query.data else {}
        
        # CRITICAL: Add individual tenant IDs to all_tenant_ids for credit queries
        # These tenants might not have direct memberships but DO have credit_lots
        individual_tenant_ids = list(individual_to_org_map.keys())
        if individual_tenant_ids:
            all_tenant_ids = list(set(all_tenant_ids) | set(individual_tenant_ids))
            logger.info(f"🚀 FAST WORKSPACES: Added {len(individual_tenant_ids)} individual tenant IDs for credit lookup")
        
        # Set of org IDs where user has individual tenant (exclude from org list)
        orgs_with_individual = set(individual_to_org_map.values())
        
        # ========================================
        # QUERY 4: Get member counts (batch aggregation via RPC or multiple)
        # We'll use a single query with count for all tenants
        # ========================================
        member_counts = {}
        
        # Get counts for all tenants in one query using group by simulation
        # Since Supabase doesn't support GROUP BY directly, we'll use a workaround
        for tenant_id in all_tenant_ids:
            # This is still N queries, but we can optimize with RPC later
            # For now, let's skip member counts for speed - UI can show without it
            member_counts[tenant_id] = 0
        
        # OPTIMIZATION: Get member counts in batch using a single query per tenant type
        # For organizations and teams, get counts
        org_and_team_ids = [tid for tid in all_tenant_ids if tid not in individual_to_org_map]
        
        if org_and_team_ids:
            # Use a single query to get all member counts
            # This is a workaround since Supabase doesn't support GROUP BY in REST API
            all_members = db.table("tenant_memberships").select(
                "tenant_id"
            ).in_("tenant_id", org_and_team_ids).eq("is_active", True).execute()
            
            if all_members.data:
                for m in all_members.data:
                    tid = m["tenant_id"]
                    member_counts[tid] = member_counts.get(tid, 0) + 1
        
        # ========================================
        # QUERY 5: Get team counts for organizations (batch)
        # ========================================
        team_counts = {}
        org_ids = [
            tid for tid in all_tenant_ids 
            if tid not in team_ids_set 
            and tid not in individual_to_org_map
            and tid not in orgs_with_individual
        ]
        
        if org_ids:
            org_teams = db.table("org_teams").select(
                "organization_id"
            ).in_("organization_id", org_ids).execute()
            
            if org_teams.data:
                for ot in org_teams.data:
                    oid = ot["organization_id"]
                    team_counts[oid] = team_counts.get(oid, 0) + 1
        
        # ========================================
        # QUERY 6: Get organization names for teams and individual members
        # ========================================
        org_names = {}
        org_ids_to_fetch = set(team_to_org_map.values()) | set(individual_to_org_map.values())
        
        if org_ids_to_fetch:
            orgs_data = db.table("tenants").select(
                "id, name"
            ).in_("id", list(org_ids_to_fetch)).execute()
            
            if orgs_data.data:
                org_names = {o["id"]: o["name"] for o in orgs_data.data}
        
        # ========================================
        # QUERY 7: Get credits for all workspaces using proper calculation
        # ========================================
        # 
        # IMPORTANT: credit_lots.credit_amount is the REMAINING balance, not the original total!
        # When credits are consumed or transferred, credit_amount is decremented.
        #
        # Correct formula:
        # - remaining_credits = sum of credit_amount (current balance in non-expired lots)
        # - consumed_credits = sum of costs from tenant_credit_consumptions
        # - expired_credits = remaining balance of expired lots (credits that expired unused)
        # - For organizations: allocated_out_credits = credits transferred to members
        # - total_credits = remaining + consumed + expired + allocated_out
        #
        credits_cache = {}  # tenant_id -> {total_credits, remaining_credits}
        now = datetime.now(timezone.utc)

        # Get remaining credits (current balance in lots) for all tenants
        remaining_credits_map = {}  # tenant_id -> remaining credits
        expired_credits_map = {}  # tenant_id -> expired credits (unused balance of expired lots)
        if all_tenant_ids:
            # Fetch all active credit lots and filter expires_at in Python
            # (avoiding .or_() which may not be available on all client versions)
            credit_lots_query = db.table("credit_lots").select(
                "tenant_id, credit_amount, is_active, expires_at, valid_from"
            ).in_("tenant_id", all_tenant_ids) \
                .eq("is_active", True) \
                .execute()
            if credit_lots_query.data:
                for lot in credit_lots_query.data:
                    # Check valid_from
                    valid_from = lot.get("valid_from")
                    lot_started = True
                    if valid_from:
                        try:
                            if isinstance(valid_from, str):
                                if valid_from.endswith('Z'):
                                    valid_from = valid_from[:-1] + '+00:00'
                                valid_from_dt = datetime.fromisoformat(valid_from)
                            else:
                                valid_from_dt = valid_from
                            if valid_from_dt.tzinfo is None:
                                valid_from_dt = valid_from_dt.replace(tzinfo=timezone.utc)
                            if valid_from_dt > now:
                                lot_started = False
                        except (ValueError, TypeError):
                            pass

                    if not lot_started:
                        continue  # Not yet valid, skip entirely

                    # Check if lot is expired
                    expires_at = lot.get("expires_at")
                    lot_expired = False
                    if expires_at:
                        try:
                            if isinstance(expires_at, str):
                                if expires_at.endswith('Z'):
                                    expires_at = expires_at[:-1] + '+00:00'
                                expires_dt = datetime.fromisoformat(expires_at)
                            else:
                                expires_dt = expires_at
                            if expires_dt.tzinfo is None:
                                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                            if expires_dt <= now:
                                lot_expired = True
                        except (ValueError, TypeError):
                            lot_expired = True

                    tid = lot["tenant_id"]
                    amount = float(lot["credit_amount"])

                    if lot_expired:
                        # Track expired credits (remaining balance that expired unused)
                        expired_credits_map[tid] = expired_credits_map.get(tid, 0) + amount
                    else:
                        remaining_credits_map[tid] = remaining_credits_map.get(tid, 0) + amount
        
        # Get consumed credits for all tenants
        consumed_credits_map = {}  # tenant_id -> consumed credits
        if all_tenant_ids:
            try:
                consumptions_query = db.table("tenant_credit_consumptions").select(
                    "tenant_id, cost"
                ).in_("tenant_id", all_tenant_ids).execute()
                
                if consumptions_query.data:
                    for consumption in consumptions_query.data:
                        tid = consumption["tenant_id"]
                        consumed_credits_map[tid] = consumed_credits_map.get(tid, 0) + float(consumption["cost"])
            except Exception as e:
                logger.warning(f"Failed to fetch credit consumptions: {e}")
        
        # For organizations: Get credits allocated OUT to members
        # These are credit_lots where original_tenant_id = org_id but tenant_id != org_id
        allocated_out_map = {}  # org_id -> total allocated out
        org_tenant_ids = [
            tid for tid in all_tenant_ids 
            if tid not in team_ids_set 
            and tid not in individual_to_org_map
            and tid not in orgs_with_individual
        ]
        
        if org_tenant_ids:
            try:
                # Get all lots that originated from these orgs but belong to someone else
                # Fetch without .or_() and filter in Python
                allocated_lots_query = db.table("credit_lots").select(
                    "original_tenant_id, tenant_id, credit_amount, valid_from, expires_at"
                ).in_("original_tenant_id", org_tenant_ids) \
                    .eq("is_active", True) \
                    .execute()
                
                if allocated_lots_query.data:
                    # Filter lots that have started (valid_from <= now) - include expired lots
                    # We want to count all allocations that were made, including expired ones
                    started_lots = []
                    for lot in allocated_lots_query.data:
                        # Check valid_from - skip lots that haven't started yet
                        valid_from = lot.get("valid_from")
                        if valid_from:
                            try:
                                if isinstance(valid_from, str):
                                    if valid_from.endswith('Z'):
                                        valid_from = valid_from[:-1] + '+00:00'
                                    valid_from_dt = datetime.fromisoformat(valid_from)
                                else:
                                    valid_from_dt = valid_from
                                if valid_from_dt.tzinfo is None:
                                    valid_from_dt = valid_from_dt.replace(tzinfo=timezone.utc)
                                if valid_from_dt > now:
                                    continue  # Not yet valid
                            except (ValueError, TypeError):
                                pass

                        started_lots.append(lot)

                    # Track allocation amounts per org and recipient tenants per org
                    org_allocations = {}  # org_id -> total remaining in allocated lots (active + expired)
                    org_recipients = {}  # org_id -> set of recipient tenant_ids

                    for lot in started_lots:
                        original_tid = lot["original_tenant_id"]
                        current_tid = lot["tenant_id"]
                        if original_tid != current_tid:  # This is an allocation OUT
                            amount = float(lot["credit_amount"])
                            org_allocations[original_tid] = org_allocations.get(original_tid, 0) + amount
                            if original_tid not in org_recipients:
                                org_recipients[original_tid] = set()
                            org_recipients[original_tid].add(current_tid)

                    # Get consumptions for all recipients
                    all_recipient_ids = set()
                    for recipients in org_recipients.values():
                        all_recipient_ids.update(recipients)

                    recipient_consumed = {}
                    if all_recipient_ids:
                        recipient_consumptions = db.table("tenant_credit_consumptions").select(
                            "tenant_id, cost"
                        ).in_("tenant_id", list(all_recipient_ids)).execute()
                        if recipient_consumptions.data:
                            for c in recipient_consumptions.data:
                                recipient_consumed[c["tenant_id"]] = recipient_consumed.get(c["tenant_id"], 0) + float(c["cost"])

                    # Calculate allocated_out for each org
                    # allocated_out = remaining in allocated lots + consumption by recipients
                    for org_id, remaining in org_allocations.items():
                        consumed = sum(recipient_consumed.get(tid, 0) for tid in org_recipients.get(org_id, set()))
                        allocated_out_map[org_id] = remaining + consumed
                            
            except Exception as e:
                logger.warning(f"Failed to fetch allocated out credits: {e}")
        
        logger.info(f"🚀 FAST WORKSPACES: Fetched credits for {len(remaining_credits_map)} workspaces")
        
        # ========================================
        # BUILD RESPONSE
        # ========================================
        workspaces = []
        
        for membership in memberships.data:
            tenant_id = membership["tenant_id"]
            tenant_data = membership.get("tenants", {})
            
            if not tenant_data or not tenant_data.get("is_active", True):
                continue
            
            tenant_type = tenant_data.get("tenant_type", "")
            role = membership["role"]
            
            # Determine workspace type
            if tenant_type == "individual":
                if tenant_id in individual_to_org_map:
                    workspace_type = "individual_member"
                    org_id = individual_to_org_map[tenant_id]
                    org_name = org_names.get(org_id, "Unknown Organization")
                else:
                    workspace_type = "personal"
                    org_id = None
                    org_name = None
            elif tenant_id in team_ids_set:
                workspace_type = "team"
                org_id = team_to_org_map[tenant_id]
                org_name = org_names.get(org_id, "Unknown Organization")
            else:
                # Skip organizations where user has individual tenant
                if tenant_id in orgs_with_individual:
                    continue
                workspace_type = "organization"
                org_id = None
                org_name = None
            
            # Calculate credits for this workspace using CORRECT formula
            # remaining_credits = current balance in credit_lots (already decremented for consumption/transfers)
            # consumed_credits = sum of consumptions
            # allocated_out = for orgs, credits sent to members
            # total_credits = remaining + consumed + allocated_out
            
            remaining_credits = remaining_credits_map.get(tenant_id, 0)
            consumed_credits = consumed_credits_map.get(tenant_id, 0)
            expired_credits = expired_credits_map.get(tenant_id, 0)

            # For organizations, add allocated_out to the total
            if workspace_type == "organization":
                allocated_out = allocated_out_map.get(tenant_id, 0)
                total_credits = remaining_credits + consumed_credits + allocated_out + expired_credits
            else:
                # For individuals/teams: total = remaining + consumed + expired
                total_credits = remaining_credits + consumed_credits + expired_credits
            
            workspaces.append(FastWorkspaceItem(
                id=tenant_id,
                name=tenant_data.get("name", "Unknown"),
                type=workspace_type,
                role=role,
                member_count=member_counts.get(tenant_id, 1),
                description=tenant_data.get("description"),
                organization_id=org_id,
                organization_name=org_name,
                is_active=tenant_data.get("is_active", True),
                total_credits=total_credits,
                credits_remaining=remaining_credits,
            ))
        
        # ========================================
        # ADD INDIVIDUAL MEMBER WORKSPACES (from org_individuals that might not have memberships)
        # ========================================
        # Some individual members might not have a direct tenant_membership record
        # but they DO have an entry in org_individuals with credits allocated
        membership_tenant_ids = set(m["tenant_id"] for m in memberships.data)
        
        for individual_tenant_id, org_id in individual_to_org_map.items():
            # Skip if already added via memberships
            if individual_tenant_id in membership_tenant_ids:
                continue
            
            # Get individual tenant details
            individual_tenant_query = db.table("tenants").select(
                "id, name, tenant_type, is_active, description"
            ).eq("id", individual_tenant_id).execute()
            
            if not individual_tenant_query.data:
                logger.warning(f"🚀 FAST WORKSPACES: Individual tenant {individual_tenant_id} not found")
                continue
            
            tenant_data = individual_tenant_query.data[0]
            if not tenant_data.get("is_active", True):
                continue
            
            org_name = org_names.get(org_id, "Unknown Organization")
            
            # Get credits for this individual tenant
            remaining_credits = remaining_credits_map.get(individual_tenant_id, 0)
            consumed_credits = consumed_credits_map.get(individual_tenant_id, 0)
            expired_credits = expired_credits_map.get(individual_tenant_id, 0)
            total_credits = remaining_credits + consumed_credits + expired_credits
            
            # Get user's role in the organization
            user_role = "member"  # Default role for individual members
            for m in memberships.data:
                if m["tenant_id"] == org_id:
                    user_role = m.get("role", "member")
                    break
            
            logger.info(f"🚀 FAST WORKSPACES: Adding individual member workspace {individual_tenant_id} (org: {org_name}, credits: {remaining_credits}/{total_credits})")
            
            workspaces.append(FastWorkspaceItem(
                id=individual_tenant_id,
                name=tenant_data.get("name", org_name),
                type="individual_member",
                role=user_role,
                member_count=1,
                description=tenant_data.get("description"),
                organization_id=org_id,
                organization_name=org_name,
                is_active=tenant_data.get("is_active", True),
                total_credits=total_credits,
                credits_remaining=remaining_credits,
            ))
        
        # Sort: organizations first, then teams, then individual_members, then personal
        type_order = {"organization": 0, "team": 1, "individual_member": 2, "personal": 3}
        workspaces.sort(key=lambda w: (type_order.get(w.type, 4), w.name.lower()))
        
        logger.info(f"🚀 FAST WORKSPACES: Returning {len(workspaces)} workspaces")
        
        return FastWorkspacesResponse(
            workspaces=workspaces,
            total_count=len(workspaces),
        )
        
    except Exception as e:
        logger.error(f"❌ Error in fast workspaces: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail="Failed to fetch workspaces")
