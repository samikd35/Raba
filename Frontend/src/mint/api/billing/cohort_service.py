"""
Cohort service for managing organization-level member cohorts and credit allocation.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..system.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class CohortError(Exception):
    """Base exception for cohort errors"""
    pass


class CohortNotFoundError(CohortError):
    """Raised when cohort is not found"""
    pass


class DuplicateCohortNameError(CohortError):
    """Raised when cohort name already exists in organization"""
    pass


class CohortMembershipError(CohortError):
    """Raised when cohort membership operation fails"""
    pass


class CohortTenantMismatchError(CohortError):
    """Raised when cohort does not belong to the specified tenant"""
    pass


class CohortService:
    """Service for managing organization cohorts and memberships"""

    def __init__(self, use_service_role: bool = True):
        """Initialize cohort service with Supabase client"""
        self.supabase = get_supabase_client(use_service_role=use_service_role).client
        self.use_service_role = use_service_role

    @staticmethod
    def _now() -> datetime:
        """Get current UTC datetime"""
        return datetime.now(timezone.utc)

    def create_cohort(
        self,
        tenant_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
        current_user_tenant_type: Optional[str] = None,
        current_user_roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new cohort in an organization.

        Args:
            tenant_id: Organization tenant ID
            name: Cohort name (must be unique within organization)
            description: Optional cohort description
            color: Optional color code for UI display
            settings: Optional cohort settings as JSON
            created_by: User ID creating the cohort
            current_user_tenant_type: Current user's tenant type (for validation)
            current_user_roles: Current user's roles (for validation)

        Returns:
            Dict containing created cohort

        Raises:
            CohortError: If tenant is not an organization
            DuplicateCohortNameError: If cohort name already exists
        """
        logger.info(f"Creating cohort '{name}' for tenant {tenant_id}")

        # Verify this is an organization
        # For non-global admins, use current_user tenant_type (validated by auth)
        # For global admins, query the database
        is_global_admin = current_user_roles and current_user_roles[0] in ["admin", "super_admin"]

        if is_global_admin:
            # Global admin: need to verify the target tenant is an organization
            tenant_response = self.supabase.table('tenants') \
                .select('tenant_type') \
                .eq('id', tenant_id) \
                .execute()

            if not tenant_response.data:
                raise CohortError(f"Tenant {tenant_id} not found")

            if tenant_response.data[0].get('tenant_type') != 'organization':
                raise CohortError("Cohorts can only be created for organizations")
        else:
            # Non-global admin: current_user tenant_type is for this organization
            if current_user_tenant_type != 'organization':
                raise CohortError("Cohorts can only be created for organizations")

        # Check for duplicate name
        existing_response = self.supabase.table('cohorts') \
            .select('id') \
            .eq('tenant_id', tenant_id) \
            .eq('name', name) \
            .execute()

        if existing_response.data:
            raise DuplicateCohortNameError(f"Cohort with name '{name}' already exists in this organization")

        # Create cohort
        cohort_data = {
            'tenant_id': tenant_id,
            'name': name,
            'description': description,
            'color': color,
            'is_active': True,
            'settings': settings or {},
            'created_by': created_by
        }

        response = self.supabase.table('cohorts') \
            .insert(cohort_data) \
            .execute()

        if not response.data:
            raise CohortError("Failed to create cohort")

        cohort = response.data[0]
        logger.info(f"Created cohort {cohort['id']} ('{name}') for tenant {tenant_id}")

        return cohort

    def get_cohort(self, cohort_id: str) -> Dict[str, Any]:
        """
        Get a cohort by ID.

        Args:
            cohort_id: Cohort ID

        Returns:
            Dict containing cohort data

        Raises:
            CohortNotFoundError: If cohort not found
        """
        response = self.supabase.table('cohorts') \
            .select('*') \
            .eq('id', cohort_id) \
            .single() \
            .execute()

        if not response.data:
            raise CohortNotFoundError(f"Cohort {cohort_id} not found")

        return response.data

    def list_cohorts(
        self,
        tenant_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all cohorts for an organization.

        Args:
            tenant_id: Organization tenant ID
            include_inactive: Whether to include inactive cohorts

        Returns:
            List of cohort dicts
        """
        query = self.supabase.table('cohorts') \
            .select('*') \
            .eq('tenant_id', tenant_id)

        if not include_inactive:
            query = query.eq('is_active', True)

        response = query.order('created_at', desc=True).execute()

        return response.data or []

    def update_cohort(
        self,
        cohort_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update a cohort's properties.

        Args:
            cohort_id: Cohort ID
            name: Optional new name
            description: Optional new description
            color: Optional new color
            settings: Optional new settings

        Returns:
            Dict containing updated cohort

        Raises:
            CohortNotFoundError: If cohort not found
            DuplicateCohortNameError: If new name conflicts with existing cohort
            CohortError: If update fails
        """
        logger.info(f"Updating cohort {cohort_id}")

        # Get current cohort
        cohort = self.get_cohort(cohort_id)

        # Check for name conflict if changing name
        if name and name != cohort['name']:
            existing_response = self.supabase.table('cohorts') \
                .select('id') \
                .eq('tenant_id', cohort['tenant_id']) \
                .eq('name', name) \
                .execute()

            if existing_response.data:
                raise DuplicateCohortNameError(f"Cohort with name '{name}' already exists in this organization")

        # Build update data
        update_data = {
            'updated_at': self._now().isoformat()
        }

        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if color is not None:
            update_data['color'] = color
        if settings is not None:
            update_data['settings'] = settings

        # Update cohort
        response = self.supabase.table('cohorts') \
            .update(update_data) \
            .eq('id', cohort_id) \
            .execute()

        if not response.data:
            raise CohortError(f"Failed to update cohort {cohort_id}")

        logger.info(f"Updated cohort {cohort_id}")

        return response.data[0]

    def delete_cohort(self, cohort_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Deactivate a cohort (soft delete).
        This will also deactivate all credit_lots associated with this cohort
        via the database trigger.

        Args:
            cohort_id: Cohort ID
            tenant_id: Tenant ID to verify ownership

        Returns:
            Dict containing deactivated cohort

        Raises:
            CohortNotFoundError: If cohort not found
            CohortTenantMismatchError: If cohort doesn't belong to tenant
            CohortError: If deactivation fails
        """
        logger.info(f"Deactivating cohort {cohort_id}")

        # Get cohort and verify tenant ownership
        cohort = self.get_cohort(cohort_id)

        if cohort['tenant_id'] != tenant_id:
            raise CohortTenantMismatchError(f"Cohort {cohort_id} does not belong to tenant {tenant_id}")

        if not cohort['is_active']:
            logger.warning(f"Cohort {cohort_id} is already inactive")
            return cohort

        # Deactivate cohort
        # The database trigger will automatically deactivate associated credit_lots
        response = self.supabase.table('cohorts') \
            .update({
                'is_active': False,
                'updated_at': self._now().isoformat()
            }) \
            .eq('id', cohort_id) \
            .execute()

        if not response.data:
            raise CohortError(f"Failed to deactivate cohort {cohort_id}")

        logger.info(f"Deactivated cohort {cohort_id} (credits also deactivated by trigger)")

        return response.data[0]

    def set_cohort_active_status(self, cohort_id: str, tenant_id: str, is_active: bool) -> Dict[str, Any]:
        """
        Set a cohort's active status.

        Args:
            cohort_id: Cohort ID
            tenant_id: Tenant ID to verify ownership
            is_active: Whether to activate (True) or deactivate (False)

        Returns:
            Dict containing updated cohort

        Raises:
            CohortNotFoundError: If cohort not found
            CohortTenantMismatchError: If cohort doesn't belong to tenant
            CohortError: If update fails
        """
        action = "Activating" if is_active else "Deactivating"
        logger.info(f"{action} cohort {cohort_id}")

        # Get cohort and verify tenant ownership
        cohort = self.get_cohort(cohort_id)

        if cohort['tenant_id'] != tenant_id:
            raise CohortTenantMismatchError(f"Cohort {cohort_id} does not belong to tenant {tenant_id}")

        if cohort['is_active'] == is_active:
            status = "active" if is_active else "inactive"
            logger.warning(f"Cohort {cohort_id} is already {status}")
            return cohort

        response = self.supabase.table('cohorts') \
            .update({
                'is_active': is_active,
                'updated_at': self._now().isoformat()
            }) \
            .eq('id', cohort_id) \
            .execute()

        if not response.data:
            raise CohortError(f"Failed to update cohort {cohort_id} status")

        action_past = "Activated" if is_active else "Deactivated"
        logger.info(f"{action_past} cohort {cohort_id}")

        return response.data[0]

    def _validate_tenant_belongs_to_org(self, member_tenant_id: str, org_id: str) -> Dict[str, Any]:
        """
        Validate that a tenant belongs to the organization via org_individuals or org_teams.

        Args:
            member_tenant_id: The tenant ID to validate
            org_id: The organization ID

        Returns:
            Dict with tenant info including 'type' ('individual' or 'team')

        Raises:
            CohortMembershipError: If tenant doesn't belong to org
        """
        # Check org_individuals first
        individual_response = self.supabase.table('org_individuals') \
            .select('id, user_id') \
            .eq('organization_id', org_id) \
            .eq('individual_tenant_id', member_tenant_id) \
            .execute()

        if individual_response.data:
            return {
                'type': 'individual',
                'user_id': individual_response.data[0]['user_id'],
                'org_link_id': individual_response.data[0]['id']
            }

        # Check org_teams
        team_response = self.supabase.table('org_teams') \
            .select('id') \
            .eq('organization_id', org_id) \
            .eq('team_id', member_tenant_id) \
            .execute()

        if team_response.data:
            return {
                'type': 'team',
                'user_id': None,
                'org_link_id': team_response.data[0]['id']
            }

        raise CohortMembershipError(
            f"Tenant {member_tenant_id} does not belong to organization {org_id}"
        )

    def assign_member_to_cohort(
        self,
        cohort_id: str,
        member_tenant_id: str,
        assigned_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign a tenant (individual or team) to a cohort.
        Note: A tenant can only belong to ONE cohort per organization.

        Args:
            cohort_id: Cohort ID
            member_tenant_id: Tenant ID (individual or team) to assign
            assigned_by: User ID of who is assigning the member

        Returns:
            Dict containing cohort membership

        Raises:
            CohortNotFoundError: If cohort not found
            CohortMembershipError: If assignment fails or tenant already in a cohort
        """
        logger.info(f"Assigning tenant {member_tenant_id} to cohort {cohort_id}")

        # Verify cohort exists and is active
        cohort = self.get_cohort(cohort_id)

        if not cohort['is_active']:
            raise CohortError(f"Cannot assign members to inactive cohort {cohort_id}")

        tenant_id = cohort['tenant_id']

        # Validate that member_tenant_id belongs to this organization
        tenant_info = self._validate_tenant_belongs_to_org(member_tenant_id, tenant_id)

        # Check if tenant is already in ANY cohort for this organization
        # The database has a unique constraint on member_tenant_id, so this will fail if violated
        # But we check here for a better error message
        existing_cohort_response = self.supabase.table('cohort_memberships') \
            .select('cohort_id, cohorts!inner(id, name)') \
            .eq('member_tenant_id', member_tenant_id) \
            .execute()

        if existing_cohort_response.data:
            existing_cohort = existing_cohort_response.data[0]['cohorts']
            raise CohortMembershipError(
                f"Tenant {member_tenant_id} is already a member of cohort '{existing_cohort['name']}' "
                f"in this organization. A tenant can only belong to one cohort per organization."
            )

        # Create membership
        membership_data = {
            'cohort_id': cohort_id,
            'member_tenant_id': member_tenant_id,
            'assigned_by': assigned_by
        }

        response = self.supabase.table('cohort_memberships') \
            .insert(membership_data) \
            .execute()

        if not response.data:
            raise CohortMembershipError(f"Failed to assign tenant {member_tenant_id} to cohort {cohort_id}")

        logger.info(f"Assigned tenant {member_tenant_id} ({tenant_info['type']}) to cohort {cohort_id}")

        return response.data[0]

    def remove_member_from_cohort(
        self,
        cohort_id: str,
        member_tenant_id: str
    ) -> Dict[str, Any]:
        """
        Remove a tenant from a cohort.

        Args:
            cohort_id: Cohort ID
            member_tenant_id: Tenant ID (individual or team) to remove

        Returns:
            Dict with success message

        Raises:
            CohortNotFoundError: If cohort not found
            CohortMembershipError: If removal fails or tenant not in cohort
        """
        logger.info(f"Removing tenant {member_tenant_id} from cohort {cohort_id}")

        # Verify cohort exists
        self.get_cohort(cohort_id)

        # Check if tenant is in this cohort
        existing_response = self.supabase.table('cohort_memberships') \
            .select('id') \
            .eq('cohort_id', cohort_id) \
            .eq('member_tenant_id', member_tenant_id) \
            .execute()

        if not existing_response.data:
            raise CohortMembershipError(f"Tenant {member_tenant_id} is not a member of cohort {cohort_id}")

        # Delete membership
        self.supabase.table('cohort_memberships') \
            .delete() \
            .eq('cohort_id', cohort_id) \
            .eq('member_tenant_id', member_tenant_id) \
            .execute()

        logger.info(f"Removed tenant {member_tenant_id} from cohort {cohort_id}")

        return {
            'success': True,
            'message': f'Tenant {member_tenant_id} removed from cohort {cohort_id}'
        }

    def move_member_between_cohorts(
        self,
        member_tenant_id: str,
        source_cohort_id: str,
        target_cohort_id: str,
        tenant_id: str,
        assigned_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Move a tenant from one cohort to another within the same organization.
        This is an atomic operation that removes from source and adds to target.

        Args:
            member_tenant_id: Tenant ID (individual or team) to move
            source_cohort_id: Current cohort ID
            target_cohort_id: Destination cohort ID
            tenant_id: Organization tenant ID (for validation)
            assigned_by: User ID of who is moving the member

        Returns:
            Dict containing the new cohort membership

        Raises:
            CohortNotFoundError: If either cohort not found
            CohortError: If cohorts don't belong to organization or target is inactive
            CohortMembershipError: If tenant not in source cohort or other membership issues
        """
        logger.info(f"Moving tenant {member_tenant_id} from cohort {source_cohort_id} to {target_cohort_id} in org {tenant_id}")

        # Verify both cohorts exist
        source_cohort = self.get_cohort(source_cohort_id)
        target_cohort = self.get_cohort(target_cohort_id)

        # Verify source cohort belongs to the organization
        if source_cohort['tenant_id'] != tenant_id:
            raise CohortError(f"Source cohort {source_cohort_id} does not belong to organization {tenant_id}")

        # Verify target cohort belongs to the organization
        if target_cohort['tenant_id'] != tenant_id:
            raise CohortError(f"Target cohort {target_cohort_id} does not belong to organization {tenant_id}")

        # Verify target cohort is active
        if not target_cohort['is_active']:
            raise CohortError(f"Cannot move member to inactive cohort {target_cohort_id}")

        # Validate that member_tenant_id belongs to this organization
        self._validate_tenant_belongs_to_org(member_tenant_id, tenant_id)

        # Verify tenant is in source cohort
        existing_membership = self.supabase.table('cohort_memberships') \
            .select('id') \
            .eq('cohort_id', source_cohort_id) \
            .eq('member_tenant_id', member_tenant_id) \
            .execute()

        if not existing_membership.data:
            raise CohortMembershipError(
                f"Tenant {member_tenant_id} is not a member of source cohort {source_cohort_id}"
            )

        # Check if tenant is already in target cohort (defensive check)
        target_check = self.supabase.table('cohort_memberships') \
            .select('id') \
            .eq('cohort_id', target_cohort_id) \
            .eq('member_tenant_id', member_tenant_id) \
            .execute()

        if target_check.data:
            raise CohortMembershipError(
                f"Tenant {member_tenant_id} is already in target cohort {target_cohort_id}"
            )

        # Step 1: Delete from source cohort
        self.supabase.table('cohort_memberships') \
            .delete() \
            .eq('cohort_id', source_cohort_id) \
            .eq('member_tenant_id', member_tenant_id) \
            .execute()

        # Step 2: Add to target cohort
        membership_data = {
            'cohort_id': target_cohort_id,
            'member_tenant_id': member_tenant_id,
            'assigned_by': assigned_by,
            'created_at': self._now().isoformat()
        }

        insert_response = self.supabase.table('cohort_memberships') \
            .insert(membership_data) \
            .execute()

        if not insert_response.data:
            # Rollback: Add back to source cohort if target insertion fails
            logger.error(f"Failed to add tenant {member_tenant_id} to target cohort, attempting rollback")
            try:
                rollback_data = {
                    'cohort_id': source_cohort_id,
                    'member_tenant_id': member_tenant_id,
                    'created_at': self._now().isoformat()
                }
                self.supabase.table('cohort_memberships').insert(rollback_data).execute()
                logger.info(f"Rollback successful: tenant {member_tenant_id} restored to source cohort")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")

            raise CohortMembershipError(
                f"Failed to move tenant {member_tenant_id} to target cohort {target_cohort_id}"
            )

        logger.info(f"Successfully moved tenant {member_tenant_id} from cohort {source_cohort_id} to {target_cohort_id}")

        return insert_response.data[0]

    def get_cohort_members(
        self,
        cohort_id: str,
        page: int = 1,
        page_size: int = 20,
        member_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Get paginated members of a cohort with batched queries.

        Args:
            cohort_id: Cohort ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            member_type: Filter by member type: 'individual', 'team', or 'all'

        Returns:
            Dict with members list and pagination info

        Raises:
            CohortNotFoundError: If cohort not found
        """
        # Verify cohort exists and get org_id
        cohort = self.get_cohort(cohort_id)
        org_id = cohort['tenant_id']

        # Get cohort memberships with tenant info
        query = self.supabase.table('cohort_memberships') \
            .select('*, tenants!member_tenant_id(id, name, tenant_type, contact_email)') \
            .eq('cohort_id', cohort_id)

        response = query.order('created_at', desc=False).execute()
        all_members = response.data or []

        # Filter by member type if specified
        if member_type != "all":
            all_members = [
                m for m in all_members
                if m.get('tenants', {}).get('tenant_type') == member_type
            ]

        # Separate individual and team tenant IDs for batched queries
        individual_tenant_ids = []
        team_tenant_ids = []
        for member in all_members:
            tenant = member.get('tenants', {})
            tenant_id = member['member_tenant_id']
            if tenant.get('tenant_type') == 'individual':
                individual_tenant_ids.append(tenant_id)
            elif tenant.get('tenant_type') == 'team':
                team_tenant_ids.append(tenant_id)

        # Batch query: Get individual user info from org_individuals
        individual_info_map: Dict[str, Dict[str, Any]] = {}
        if individual_tenant_ids:
            ind_response = self.supabase.table('org_individuals') \
                .select('user_id, individual_tenant_id, user_profiles!user_id(email, full_name)') \
                .eq('organization_id', org_id) \
                .in_('individual_tenant_id', individual_tenant_ids) \
                .execute()

            for ind in (ind_response.data or []):
                individual_info_map[ind['individual_tenant_id']] = ind

        # Batch query: Get user roles in org for individuals
        user_ids = [ind.get('user_id') for ind in individual_info_map.values() if ind.get('user_id')]
        user_role_map: Dict[str, str] = {}
        if user_ids:
            tm_response = self.supabase.table('tenant_memberships') \
                .select('user_id, role') \
                .eq('tenant_id', org_id) \
                .in_('user_id', user_ids) \
                .eq('is_active', True) \
                .execute()

            for tm in (tm_response.data or []):
                user_role_map[tm['user_id']] = tm['role']

        # Batch query: Get team admin user IDs
        team_admin_users: Dict[str, List[str]] = {}
        if team_tenant_ids:
            admin_response = self.supabase.table('tenant_memberships') \
                .select('tenant_id, user_id') \
                .in_('tenant_id', team_tenant_ids) \
                .in_('role', ['owner', 'admin']) \
                .eq('is_active', True) \
                .execute()

            for m in (admin_response.data or []):
                tid = m['tenant_id']
                if tid not in team_admin_users:
                    team_admin_users[tid] = []
                team_admin_users[tid].append(m['user_id'])

        # Batch query: Get team admin profiles (emails)
        all_admin_user_ids = list(set(uid for uids in team_admin_users.values() for uid in uids))
        admin_profiles: Dict[str, Dict[str, Any]] = {}
        if all_admin_user_ids:
            admin_prof_response = self.supabase.table('user_profiles') \
                .select('id, email') \
                .in_('id', all_admin_user_ids) \
                .execute()

            for prof in (admin_prof_response.data or []):
                admin_profiles[prof['id']] = prof

        # Batch query: Get all VPM projects for cohort member tenants (aligned with org member projects)
        all_tenant_ids = individual_tenant_ids + team_tenant_ids
        project_count_by_tenant: Dict[str, int] = {}
        recent_project_by_tenant: Dict[str, Dict[str, Any]] = {}
        if all_tenant_ids:
            # Get project counts
            projects_response = self.supabase.table('vmp_projects') \
                .select('id, tenant_id') \
                .in_('tenant_id', all_tenant_ids) \
                .execute()

            for p in (projects_response.data or []):
                tid = p['tenant_id']
                project_count_by_tenant[tid] = project_count_by_tenant.get(tid, 0) + 1

            # Get recent projects with details (ordered by updated_at desc)
            recent_projects_response = self.supabase.table('vmp_projects') \
                .select('id, name, description, current_step, created_at, updated_at, tenant_id') \
                .in_('tenant_id', all_tenant_ids) \
                .order('updated_at', desc=True) \
                .limit(len(all_tenant_ids) * 2) \
                .execute()

            for p in (recent_projects_response.data or []):
                tid = p['tenant_id']
                if tid not in recent_project_by_tenant:
                    recent_project_by_tenant[tid] = p

        # Batch query: Get PV report counts for individuals (by user_id/created_by)
        pv_report_count_by_user: Dict[str, int] = {}
        if user_ids:
            pv_response = self.supabase.table('documents') \
                .select('created_by') \
                .in_('created_by', user_ids) \
                .eq('source_type', 'pv_report') \
                .execute()

            for d in (pv_response.data or []):
                uid = d['created_by']
                pv_report_count_by_user[uid] = pv_report_count_by_user.get(uid, 0) + 1

        # Batch query: Get team member user IDs for PV report counting
        team_member_users: Dict[str, List[str]] = {}
        if team_tenant_ids:
            team_members_response = self.supabase.table('tenant_memberships') \
                .select('tenant_id, user_id') \
                .in_('tenant_id', team_tenant_ids) \
                .eq('is_active', True) \
                .execute()

            for m in (team_members_response.data or []):
                tid = m['tenant_id']
                if tid not in team_member_users:
                    team_member_users[tid] = []
                team_member_users[tid].append(m['user_id'])

        # Batch query: Get PV report counts for team members
        all_team_member_user_ids = list(set(uid for uids in team_member_users.values() for uid in uids))
        team_pv_counts: Dict[str, int] = {}
        if all_team_member_user_ids:
            team_pv_response = self.supabase.table('documents') \
                .select('created_by') \
                .in_('created_by', all_team_member_user_ids) \
                .eq('source_type', 'pv_report') \
                .execute()

            # Map user PV counts back to teams
            user_pv_counts: Dict[str, int] = {}
            for d in (team_pv_response.data or []):
                uid = d['created_by']
                user_pv_counts[uid] = user_pv_counts.get(uid, 0) + 1

            for team_id, member_uids in team_member_users.items():
                team_pv_counts[team_id] = sum(user_pv_counts.get(uid, 0) for uid in member_uids)

        # Enrich member data
        enriched_members = []
        for member in all_members:
            tenant = member.get('tenants', {})
            tenant_id = member['member_tenant_id']
            tenant_type = tenant.get('tenant_type')
            tenant_name = tenant.get('name', '')

            enriched = {
                'id': member['id'],
                'cohort_id': member['cohort_id'],
                'member_tenant_id': tenant_id,
                'tenant_type': tenant_type,
                'tenant_name': tenant_name,
                'created_at': member['created_at'],
            }

            # Get project data for this member
            recent_proj = recent_project_by_tenant.get(tenant_id)
            projects = [recent_proj] if recent_proj else []

            if tenant_type == 'individual':
                ind_info = individual_info_map.get(tenant_id, {})
                user_id = ind_info.get('user_id')
                profile = ind_info.get('user_profiles', {}) or {}

                enriched['user_id'] = user_id
                enriched['user_email'] = profile.get('email')
                enriched['user_name'] = profile.get('full_name')
                enriched['user_role'] = user_role_map.get(user_id) if user_id else None
                # Team fields are None for individuals
                enriched['team_name'] = None
                enriched['team_contact_email'] = None
                enriched['team_admin_emails'] = None
                # Project data
                enriched['project_count'] = project_count_by_tenant.get(tenant_id, 0)
                enriched['pv_report_count'] = pv_report_count_by_user.get(user_id, 0) if user_id else 0
                enriched['projects'] = projects

            elif tenant_type == 'team':
                admin_user_ids = team_admin_users.get(tenant_id, [])
                team_admin_emails = [
                    admin_profiles.get(uid, {}).get('email')
                    for uid in admin_user_ids
                    if admin_profiles.get(uid, {}).get('email')
                ]
                first_admin_email = team_admin_emails[0] if team_admin_emails else None

                enriched['user_id'] = tenant_id  # Use tenant_id for consistency
                enriched['user_email'] = first_admin_email
                enriched['user_name'] = tenant_name
                enriched['user_role'] = None
                enriched['team_name'] = tenant_name
                enriched['team_contact_email'] = tenant.get('contact_email')
                enriched['team_admin_emails'] = team_admin_emails if team_admin_emails else None
                # Project data
                enriched['project_count'] = project_count_by_tenant.get(tenant_id, 0)
                enriched['pv_report_count'] = team_pv_counts.get(tenant_id, 0)
                enriched['projects'] = projects

            enriched_members.append(enriched)

        # Pagination
        total_count = len(enriched_members)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_members = enriched_members[start_idx:end_idx]
        has_next = end_idx < total_count

        return {
            'members': paginated_members,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'has_next': has_next,
        }

    # =========================================================================
    # Bulk Membership Operations
    # =========================================================================

    def bulk_assign_members_to_cohort(
        self,
        cohort_id: str,
        member_tenant_ids: List[str],
        assigned_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk assign multiple tenants to a cohort efficiently.

        Args:
            cohort_id: Cohort ID
            member_tenant_ids: List of tenant IDs to assign
            assigned_by: User ID of who is assigning

        Returns:
            Dict with results for each member
        """
        logger.info(f"Bulk assigning {len(member_tenant_ids)} members to cohort {cohort_id}")

        results = []

        # Verify cohort exists and is active
        try:
            cohort = self.get_cohort(cohort_id)
            if not cohort['is_active']:
                return {
                    'cohort_id': cohort_id,
                    'total_requested': len(member_tenant_ids),
                    'successful': 0,
                    'failed': len(member_tenant_ids),
                    'results': [
                        {'member_tenant_id': tid, 'success': False, 'error': 'Cohort is inactive'}
                        for tid in member_tenant_ids
                    ]
                }
        except CohortNotFoundError:
            return {
                'cohort_id': cohort_id,
                'total_requested': len(member_tenant_ids),
                'successful': 0,
                'failed': len(member_tenant_ids),
                'results': [
                    {'member_tenant_id': tid, 'success': False, 'error': 'Cohort not found'}
                    for tid in member_tenant_ids
                ]
            }

        tenant_id = cohort['tenant_id']

        # Batch validate: Check which tenants belong to org via org_individuals
        individual_response = self.supabase.table('org_individuals') \
            .select('individual_tenant_id') \
            .eq('organization_id', tenant_id) \
            .in_('individual_tenant_id', member_tenant_ids) \
            .execute()
        valid_individuals = {r['individual_tenant_id'] for r in (individual_response.data or [])}

        # Batch validate: Check which tenants belong to org via org_teams
        team_response = self.supabase.table('org_teams') \
            .select('team_id') \
            .eq('organization_id', tenant_id) \
            .in_('team_id', member_tenant_ids) \
            .execute()
        valid_teams = {r['team_id'] for r in (team_response.data or [])}

        valid_members = valid_individuals | valid_teams
        invalid_members = set(member_tenant_ids) - valid_members

        # Batch check: Which members are already in any cohort
        existing_response = self.supabase.table('cohort_memberships') \
            .select('member_tenant_id, cohorts!inner(name)') \
            .in_('member_tenant_id', list(valid_members)) \
            .execute()
        already_in_cohort = {
            r['member_tenant_id']: r['cohorts']['name']
            for r in (existing_response.data or [])
        }

        # Separate valid members that can be added
        members_to_add = [tid for tid in valid_members if tid not in already_in_cohort]

        # Batch insert all valid members
        if members_to_add:
            insert_data = [
                {
                    'cohort_id': cohort_id,
                    'member_tenant_id': tid,
                    'assigned_by': assigned_by
                }
                for tid in members_to_add
            ]
            self.supabase.table('cohort_memberships').insert(insert_data).execute()

        # Build results
        successful = 0
        for tid in member_tenant_ids:
            if tid in invalid_members:
                results.append({
                    'member_tenant_id': tid,
                    'success': False,
                    'error': f'Tenant does not belong to organization {tenant_id}'
                })
            elif tid in already_in_cohort:
                results.append({
                    'member_tenant_id': tid,
                    'success': False,
                    'error': f"Already in cohort '{already_in_cohort[tid]}'"
                })
            else:
                results.append({'member_tenant_id': tid, 'success': True, 'error': None})
                successful += 1

        logger.info(f"Bulk assigned {successful}/{len(member_tenant_ids)} members to cohort {cohort_id}")

        return {
            'cohort_id': cohort_id,
            'total_requested': len(member_tenant_ids),
            'successful': successful,
            'failed': len(member_tenant_ids) - successful,
            'results': results
        }

    def bulk_remove_members_from_cohort(
        self,
        cohort_id: str,
        member_tenant_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Bulk remove multiple tenants from a cohort efficiently.

        Args:
            cohort_id: Cohort ID
            member_tenant_ids: List of tenant IDs to remove

        Returns:
            Dict with results for each member
        """
        logger.info(f"Bulk removing {len(member_tenant_ids)} members from cohort {cohort_id}")

        results = []

        # Verify cohort exists
        try:
            self.get_cohort(cohort_id)
        except CohortNotFoundError:
            return {
                'cohort_id': cohort_id,
                'total_requested': len(member_tenant_ids),
                'successful': 0,
                'failed': len(member_tenant_ids),
                'results': [
                    {'member_tenant_id': tid, 'success': False, 'error': 'Cohort not found'}
                    for tid in member_tenant_ids
                ]
            }

        # Batch check: Which members are actually in this cohort
        existing_response = self.supabase.table('cohort_memberships') \
            .select('member_tenant_id') \
            .eq('cohort_id', cohort_id) \
            .in_('member_tenant_id', member_tenant_ids) \
            .execute()
        members_in_cohort = {r['member_tenant_id'] for r in (existing_response.data or [])}
        members_not_in_cohort = set(member_tenant_ids) - members_in_cohort

        # Batch delete all members that are in the cohort
        if members_in_cohort:
            self.supabase.table('cohort_memberships') \
                .delete() \
                .eq('cohort_id', cohort_id) \
                .in_('member_tenant_id', list(members_in_cohort)) \
                .execute()

        # Build results
        successful = 0
        for tid in member_tenant_ids:
            if tid in members_not_in_cohort:
                results.append({
                    'member_tenant_id': tid,
                    'success': False,
                    'error': f'Not a member of cohort {cohort_id}'
                })
            else:
                results.append({'member_tenant_id': tid, 'success': True, 'error': None})
                successful += 1

        logger.info(f"Bulk removed {successful}/{len(member_tenant_ids)} members from cohort {cohort_id}")

        return {
            'cohort_id': cohort_id,
            'total_requested': len(member_tenant_ids),
            'successful': successful,
            'failed': len(member_tenant_ids) - successful,
            'results': results
        }

    def bulk_move_members_between_cohorts(
        self,
        member_tenant_ids: List[str],
        source_cohort_id: str,
        target_cohort_id: str,
        tenant_id: str,
        assigned_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk move multiple tenants from one cohort to another efficiently.

        Args:
            member_tenant_ids: List of tenant IDs to move
            source_cohort_id: Source cohort ID
            target_cohort_id: Target cohort ID
            tenant_id: Organization tenant ID
            assigned_by: User ID of who is moving

        Returns:
            Dict with results for each member
        """
        logger.info(
            f"Bulk moving {len(member_tenant_ids)} members from cohort {source_cohort_id} "
            f"to {target_cohort_id} in org {tenant_id}"
        )

        results = []

        # Verify both cohorts exist and belong to the organization
        try:
            source_cohort = self.get_cohort(source_cohort_id)
            target_cohort = self.get_cohort(target_cohort_id)
        except CohortNotFoundError as e:
            return {
                'source_cohort_id': source_cohort_id,
                'target_cohort_id': target_cohort_id,
                'total_requested': len(member_tenant_ids),
                'successful': 0,
                'failed': len(member_tenant_ids),
                'results': [
                    {'member_tenant_id': tid, 'success': False, 'error': str(e)}
                    for tid in member_tenant_ids
                ]
            }

        # Validate cohorts belong to organization
        if source_cohort['tenant_id'] != tenant_id:
            error = f"Source cohort does not belong to organization {tenant_id}"
            return {
                'source_cohort_id': source_cohort_id,
                'target_cohort_id': target_cohort_id,
                'total_requested': len(member_tenant_ids),
                'successful': 0,
                'failed': len(member_tenant_ids),
                'results': [
                    {'member_tenant_id': tid, 'success': False, 'error': error}
                    for tid in member_tenant_ids
                ]
            }

        if target_cohort['tenant_id'] != tenant_id:
            error = f"Target cohort does not belong to organization {tenant_id}"
            return {
                'source_cohort_id': source_cohort_id,
                'target_cohort_id': target_cohort_id,
                'total_requested': len(member_tenant_ids),
                'successful': 0,
                'failed': len(member_tenant_ids),
                'results': [
                    {'member_tenant_id': tid, 'success': False, 'error': error}
                    for tid in member_tenant_ids
                ]
            }

        # Verify target cohort is active
        if not target_cohort['is_active']:
            error = f"Target cohort {target_cohort_id} is inactive"
            return {
                'source_cohort_id': source_cohort_id,
                'target_cohort_id': target_cohort_id,
                'total_requested': len(member_tenant_ids),
                'successful': 0,
                'failed': len(member_tenant_ids),
                'results': [
                    {'member_tenant_id': tid, 'success': False, 'error': error}
                    for tid in member_tenant_ids
                ]
            }

        # Batch check: Which members are in source cohort
        source_membership_response = self.supabase.table('cohort_memberships') \
            .select('member_tenant_id') \
            .eq('cohort_id', source_cohort_id) \
            .in_('member_tenant_id', member_tenant_ids) \
            .execute()
        members_in_source = {r['member_tenant_id'] for r in (source_membership_response.data or [])}
        members_not_in_source = set(member_tenant_ids) - members_in_source

        # Batch check: Which members are already in target cohort (defensive)
        target_membership_response = self.supabase.table('cohort_memberships') \
            .select('member_tenant_id') \
            .eq('cohort_id', target_cohort_id) \
            .in_('member_tenant_id', member_tenant_ids) \
            .execute()
        members_already_in_target = {r['member_tenant_id'] for r in (target_membership_response.data or [])}

        # Members that can be moved: in source, not already in target
        members_to_move = members_in_source - members_already_in_target

        # Batch delete from source cohort
        if members_to_move:
            self.supabase.table('cohort_memberships') \
                .delete() \
                .eq('cohort_id', source_cohort_id) \
                .in_('member_tenant_id', list(members_to_move)) \
                .execute()

            # Batch insert into target cohort
            insert_data = [
                {
                    'cohort_id': target_cohort_id,
                    'member_tenant_id': tid,
                    'assigned_by': assigned_by,
                    'created_at': self._now().isoformat()
                }
                for tid in members_to_move
            ]
            self.supabase.table('cohort_memberships').insert(insert_data).execute()

        # Build results
        successful = 0
        for tid in member_tenant_ids:
            if tid in members_not_in_source:
                results.append({
                    'member_tenant_id': tid,
                    'success': False,
                    'error': f'Not a member of source cohort {source_cohort_id}'
                })
            elif tid in members_already_in_target:
                results.append({
                    'member_tenant_id': tid,
                    'success': False,
                    'error': f'Already in target cohort {target_cohort_id}'
                })
            else:
                results.append({'member_tenant_id': tid, 'success': True, 'error': None})
                successful += 1

        logger.info(
            f"Bulk moved {successful}/{len(member_tenant_ids)} members from cohort "
            f"{source_cohort_id} to {target_cohort_id}"
        )

        return {
            'source_cohort_id': source_cohort_id,
            'target_cohort_id': target_cohort_id,
            'total_requested': len(member_tenant_ids),
            'successful': successful,
            'failed': len(member_tenant_ids) - successful,
            'results': results
        }

    def get_user_cohorts(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all cohorts a user belongs to (via their individual tenants).

        Args:
            user_id: User ID
            tenant_id: Optional filter by specific organization

        Returns:
            List of cohorts the user belongs to
        """
        # Get user's individual tenant IDs from org_individuals
        oi_query = self.supabase.table('org_individuals') \
            .select('individual_tenant_id, organization_id') \
            .eq('user_id', user_id)

        if tenant_id:
            oi_query = oi_query.eq('organization_id', tenant_id)

        oi_response = oi_query.execute()

        if not oi_response.data:
            return []

        individual_tenant_ids = [oi['individual_tenant_id'] for oi in oi_response.data]

        # Get cohort memberships for these individual tenant IDs
        query = self.supabase.table('cohort_memberships') \
            .select('*, cohorts!inner(*)') \
            .in_('member_tenant_id', individual_tenant_ids)

        response = query.execute()

        # Extract cohort data from the join
        cohorts = []
        for membership in (response.data or []):
            cohort = membership.get('cohorts')
            if cohort:
                cohorts.append(cohort)

        return cohorts

    # =========================================================================
    # Cohort Projects
    # =========================================================================

    def get_cohort_projects(
        self,
        cohort_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Get paginated projects for all members of a cohort.

        Args:
            cohort_id: Cohort ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dict with projects list and pagination info

        Raises:
            CohortNotFoundError: If cohort not found
        """
        # Verify cohort exists and get cohort details
        cohort = self.get_cohort(cohort_id)
        org_id = cohort['tenant_id']

        # Get all cohort member tenant IDs
        members_response = self.supabase.table('cohort_memberships') \
            .select('member_tenant_id') \
            .eq('cohort_id', cohort_id) \
            .execute()

        member_tenant_ids = [m['member_tenant_id'] for m in (members_response.data or [])]

        if not member_tenant_ids:
            return {
                'projects': [],
                'total_count': 0,
                'page': page,
                'page_size': page_size,
                'has_next': False,
                'cohort_id': cohort_id,
                'cohort_name': cohort['name'],
            }

        # Get total count of projects for pagination
        count_response = self.supabase.table('vmp_projects') \
            .select('id', count='exact') \
            .in_('tenant_id', member_tenant_ids) \
            .execute()

        total_count = count_response.count if count_response.count is not None else 0

        # Calculate pagination
        offset = (page - 1) * page_size
        has_next = offset + page_size < total_count

        # Get paginated projects with tenant info
        projects_response = self.supabase.table('vmp_projects') \
            .select('id, name, description, current_step, status, created_at, updated_at, tenant_id') \
            .in_('tenant_id', member_tenant_ids) \
            .order('updated_at', desc=True) \
            .range(offset, offset + page_size - 1) \
            .execute()

        projects = projects_response.data or []

        # Batch get tenant info for enrichment
        project_tenant_ids = list(set(p['tenant_id'] for p in projects))
        tenant_info_map: Dict[str, Dict[str, Any]] = {}

        if project_tenant_ids:
            tenants_response = self.supabase.table('tenants') \
                .select('id, name, tenant_type') \
                .in_('id', project_tenant_ids) \
                .execute()

            for t in (tenants_response.data or []):
                tenant_info_map[t['id']] = t

        # Get individual user info for individual tenants
        individual_tenant_ids = [
            tid for tid in project_tenant_ids
            if tenant_info_map.get(tid, {}).get('tenant_type') == 'individual'
        ]

        individual_user_map: Dict[str, Dict[str, Any]] = {}
        if individual_tenant_ids:
            oi_response = self.supabase.table('org_individuals') \
                .select('individual_tenant_id, user_id, user_profiles!user_id(email, full_name)') \
                .eq('organization_id', org_id) \
                .in_('individual_tenant_id', individual_tenant_ids) \
                .execute()

            for oi in (oi_response.data or []):
                individual_user_map[oi['individual_tenant_id']] = oi

        # Enrich projects with owner information
        enriched_projects = []
        for project in projects:
            tenant_id = project['tenant_id']
            tenant = tenant_info_map.get(tenant_id, {})
            tenant_type = tenant.get('tenant_type')

            enriched = {
                'id': project['id'],
                'name': project['name'],
                'description': project.get('description'),
                'current_step': project.get('current_step'),
                'status': project.get('status'),
                'created_at': project['created_at'],
                'updated_at': project['updated_at'],
                'tenant_id': tenant_id,
                'tenant_name': tenant.get('name'),
                'tenant_type': tenant_type,
                'owner_email': None,
                'owner_name': None,
            }

            # Add individual user info if available
            if tenant_type == 'individual':
                ind_info = individual_user_map.get(tenant_id, {})
                user_profile = ind_info.get('user_profiles', {})
                enriched['owner_email'] = user_profile.get('email')
                enriched['owner_name'] = user_profile.get('full_name')

            enriched_projects.append(enriched)

        return {
            'projects': enriched_projects,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'has_next': has_next,
            'cohort_id': cohort_id,
            'cohort_name': cohort['name'],
        }
