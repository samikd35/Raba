"""
Database Adapter for VPM Integration

Bridges VPM database operations with Yuba's existing database infrastructure.
This adapter ensures VPM's data_access.py works seamlessly with Yuba's database.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import traceback
from src.mint.api.system.core.supabase_client import get_supabase_client, get_service_role_client
from src.mint.api.vector_storage.service import VectorStorageService


class YubaDatabaseAdapter:
    """
    Adapter to integrate VPM database operations with Yuba's existing database layer.
    
    This class provides the same interface that VPM's data_access expects while using
    Yuba's existing database infrastructure under the hood.
    """
    
    def __init__(self, use_service_role: bool = False):
        """Initialize with Yuba's existing database clients"""
        self.supabase = get_service_role_client() if use_service_role else get_supabase_client()
        self.vector_service = VectorStorageService()
    
    async def get_pv_reports(
        self, 
        tenant_id: str, 
        page: int = 1, 
        page_size: int = 35, 
        search_query: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get PV reports using Yuba's existing vector storage system.
        
        This method provides the same interface VPM expects while leveraging
        Yuba's existing document storage and vector search capabilities.
        """
        try:
            # Calculate offset for pagination
            offset = (page - 1) * page_size
            
            # Build query for PV reports using Yuba's existing documents table
            query = self.supabase.client.table('documents').select(
                'id, title, created_at, metadata, storage_path',
                count='exact'
            ).eq('source_type', 'pv_report').eq('tenant_id', tenant_id)
            
            # Add search filter if provided
            if search_query:
                query = query.ilike('title', f'%{search_query}%')
            
            # Apply pagination and ordering
            query = query.order('created_at', desc=True).range(offset, offset + page_size - 1)
            
            # Execute query
            response = query.execute()
            
            # Transform to VPM expected format
            reports = []
            for doc in response.data:
                reports.append({
                    'id': doc['id'],
                    'title': doc['title'],
                    'created_at': doc['created_at'],
                    'tenant_name': None,  # Can be populated from tenant lookup if needed
                    'summary_preview': doc.get('metadata', {}).get('summary', 'No summary available'),
                    'document_count': 1,  # Each document is one report
                    'has_insights': await self._check_has_insights(doc['id']),
                    'file_size_mb': self._calculate_file_size(doc.get('storage_path'))
                })
            
            total_count = response.count or 0
            
            return reports, total_count
            
        except Exception as e:
            print(f"Error fetching PV reports: {e}")
            return [], 0
    
    async def get_report_detail(self, report_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific PV report.
        
        Uses Yuba's existing document storage to fetch report details.
        """
        try:
            # Get report from Yuba's documents table
            response = self.supabase.client.table('documents').select(
                'id, title, content, created_at, tenant_id, metadata, storage_path'
            ).eq('id', report_id).eq('tenant_id', tenant_id).eq('source_type', 'pv_report').execute()
            
            if not response.data:
                return None
            
            doc = response.data[0]
            
            # Get insights count
            insights_count = await self._get_insights_count(report_id)
            
            # Transform to VPM expected format
            return {
                'id': doc['id'],
                'title': doc['title'],
                'created_at': doc['created_at'],
                'tenant_id': doc['tenant_id'],
                'tenant_name': None,  # Can be populated from tenant lookup if needed
                'summary_preview': doc.get('metadata', {}).get('summary', 'No summary available'),
                'full_content_preview': (doc.get('content', '') or '')[:500] + '...',
                'document_count': 1,
                'has_insights': insights_count > 0,
                'file_size_mb': self._calculate_file_size(doc.get('storage_path')),
                'insights_count': insights_count,
                'metadata': doc.get('metadata', {})
            }
            
        except Exception as e:
            print(f"Error fetching report detail: {e}")
            return None
    
    async def get_pv_report_executive_summary(self, pv_report_id: str, tenant_id: str) -> Optional[str]:
        """
        Fetch the executive summary from a Problem Validation report.
        
        Args:
            pv_report_id: The PV report ID
            tenant_id: The tenant ID for security
            
        Returns:
            Executive summary text or None if not found
        """
        try:
            print(f"🔍 DEBUG: Fetching executive summary for PV report: {pv_report_id}")
            
            # First try the problem_validation_reports table (newer structure)
            pv_response = self.supabase.client.table('problem_validation_reports').select(
                'executive_summary'
            ).eq('id', pv_report_id).execute()
            
            if pv_response.data and pv_response.data[0].get('executive_summary'):
                executive_summary = pv_response.data[0]['executive_summary']
                print(f"✅ DEBUG: Found executive summary in problem_validation_reports: {len(executive_summary)} chars")
                return executive_summary
            
            # Fallback: try documents table (older structure)
            doc_response = self.supabase.client.table('documents').select(
                'content, metadata'
            ).eq('id', pv_report_id).eq('source_type', 'pv_report').execute()
            
            if doc_response.data:
                doc = doc_response.data[0]
                
                # Try to extract from metadata first
                metadata = doc.get('metadata', {})
                if metadata.get('executive_summary'):
                    executive_summary = metadata['executive_summary']
                    print(f"✅ DEBUG: Found executive summary in documents.metadata: {len(executive_summary)} chars")
                    return executive_summary
                
                # Try to parse content as JSON first (for structured reports)
                content = doc.get('content', '')
                if content:
                    try:
                        import json
                        # Try to parse as JSON
                        content_json = json.loads(content)
                        if isinstance(content_json, dict) and content_json.get('executive_summary'):
                            executive_summary = content_json['executive_summary']
                            print(f"✅ DEBUG: Extracted executive summary from JSON content: {len(executive_summary)} chars")
                            return executive_summary
                    except (json.JSONDecodeError, TypeError):
                        # If not JSON, try regex patterns
                        print(f"🔍 DEBUG: Content is not JSON, trying regex patterns")
                        pass
                    
                    # Look for executive summary patterns in the content
                    import re
                    patterns = [
                        r'(?i)(?:^|\n)#+\s*executive\s+summary\s*\n(.*?)(?=\n#+|\n\n|\Z)',
                        r'(?i)(?:^|\n)executive\s+summary:?\s*\n(.*?)(?=\n\n|\Z)',
                        r'(?i)(?:^|\n)\*\*executive\s+summary\*\*:?\s*\n(.*?)(?=\n\n|\Z)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, content, re.DOTALL)
                        if match:
                            executive_summary = match.group(1).strip()
                            print(f"✅ DEBUG: Extracted executive summary from content: {len(executive_summary)} chars")
                            return executive_summary
                
                    # If no specific section found, use first paragraph as fallback
                    first_paragraph = content.split('\n\n')[0].strip()
                    if len(first_paragraph) > 50:  # Only use if substantial
                        print(f"⚠️ DEBUG: Using first paragraph as executive summary: {len(first_paragraph)} chars")
                        return first_paragraph
            
            print(f"❌ DEBUG: No executive summary found for PV report: {pv_report_id}")
            return None
            
        except Exception as e:
            print(f"❌ ERROR fetching executive summary: {e}")
            return None
    
    async def create_vmp_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create VPM project using Yuba's database patterns.
        
        This uses the existing VPM schema that's already integrated with Yuba.
        """
        try:
            print(f"🔍 DEBUG: Attempting to create VPM project with data: {project_data}")
            
            # Insert into vmp_projects table (VPM-specific table that exists)
            response = self.supabase.client.table('vmp_projects').insert(project_data).execute()
            
            print(f"🔍 DEBUG: Supabase response: {response}")
            print(f"🔍 DEBUG: Response data: {response.data}")
            print(f"🔍 DEBUG: Response count: {getattr(response, 'count', 'N/A')}")
            
            if response.data:
                created_project = response.data[0]
                print(f"✅ DEBUG: Project created successfully with ID: {created_project.get('id')}")
                return created_project
            else:
                print(f"❌ DEBUG: No data returned from Supabase insert")
                raise Exception("Failed to create project - no data returned")
                
        except Exception as e:
            print(f"❌ ERROR creating VPM project: {e}")
            print(f"❌ ERROR type: {type(e)}")
            import traceback
            print(f"❌ ERROR traceback: {traceback.format_exc()}")
            raise
    
    async def get_vmp_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        OPTIMIZED: Get VPM projects for a tenant (team/org/personal).
        
        Returns MINIMAL data for performance:
        - Only essential columns (id, name, description, status, dates)
        - Problem statement (replacing pv_report_title)
        - Artifact counts fetched in batch
        - No large JSONB fields loaded
        
        CRITICAL FIX: Only filter by tenant_id to enable team collaboration.
        All members of a team should see all projects created within that team.
        The tenant_id determines project visibility, not user_id.
        """
        try:
            offset = (page - 1) * page_size
            
            print(f"🔍 DEBUG: [GET_VMP_PROJECTS_OPTIMIZED] Fetching projects for tenant: {tenant_id}")
            print(f"🔍 DEBUG: [GET_VMP_PROJECTS_OPTIMIZED] Page: {page}, Size: {page_size}, Status: {status_filter}, Search: {search_query}")
            
            # OPTIMIZED QUERY: Fetch only minimal columns needed for project listing UI
            # REMOVED personas JSONB - too heavy, we'll fetch count separately
            select_clause = '''
                id,
                tenant_id,
                user_id,
                name,
                description,
                refined_problem_statement,
                status,
                current_step,
                context_mode,
                created_at,
                updated_at
            '''
            
            # Build query - lightweight, no heavy JSONB fields
            query = self.supabase.client.table('vmp_projects').select(
                select_clause,
                count='exact'
            ).eq('tenant_id', tenant_id)
            
            # NOTE: Bootstrap projects are filtered out in Python below (not in SQL)
            # because SQL's neq filter excludes NULL values, and most projects have NULL context_mode
            
            # Add filters
            if status_filter:
                query = query.eq('status', status_filter)
            
            if search_query:
                query = query.ilike('name', f'%{search_query}%')
            
            # FIX: Fetch reasonable batch for Python filtering
            # We'll paginate AFTER filtering out bootstrap projects
            max_fetch = min(page_size * 3, 100)  # Fetch 3x but cap at 100
            query = query.order('updated_at', desc=True).range(0, max_fetch - 1)
            
            # Execute query
            response = query.execute()
            
            print(f"🔍 DEBUG: [GET_VMP_PROJECTS_OPTIMIZED] Query returned {len(response.data)} projects (before bootstrap filter)")
            
            # PERFORMANCE: Skip extra queries for artifact_count and personas_count
            # These are nice-to-have but not critical for listing - can be fetched on demand
            
            # Build minimal response objects
            # FIX: Filter out bootstrap projects in Python (SQL neq excludes NULLs)
            all_projects = []
            bootstrap_count = 0
            
            for project in response.data:
                project_id = project['id']
                
                # Skip bootstrap projects (they should only appear in value-maps/Module 3 endpoints)
                if project.get('context_mode') == 'bootstrap':
                    bootstrap_count += 1
                    continue
                
                # Fallback: Use description if refined_problem_statement is NULL
                problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                
                minimal_project = {
                    'id': project['id'],
                    'tenant_id': project['tenant_id'],
                    'user_id': project['user_id'],
                    'name': project['name'],
                    'description': project.get('description', ''),
                    'problem_statement': problem_statement,  # Replacing pv_report_title
                    'status': project['status'],
                    'current_step': project['current_step'],
                    'created_at': project['created_at'],
                    'updated_at': project['updated_at'],
                    'progress_percentage': self._calculate_progress(project.get('current_step')),
                    'artifact_count': 0,  # Skipped for performance
                    'personas_count': 0   # Skipped for performance
                }
                
                all_projects.append(minimal_project)
            
            # FIX: Apply pagination AFTER filtering bootstrap projects
            total_count = len(all_projects)
            start_idx = offset
            end_idx = offset + page_size
            projects = all_projects[start_idx:end_idx]
            
            print(f"🔍 DEBUG: [GET_VMP_PROJECTS_OPTIMIZED] Filtered out {bootstrap_count} bootstrap projects")
            print(f"✅ DEBUG: [GET_VMP_PROJECTS_OPTIMIZED] Returning {len(projects)} projects (page {page} of {total_count} total)")
            
            return projects, total_count
            
        except Exception as e:
            print(f"❌ ERROR: [GET_VMP_PROJECTS_OPTIMIZED] Failed to fetch projects: {e}")
            import traceback
            print(f"❌ ERROR: [GET_VMP_PROJECTS_OPTIMIZED] Traceback: {traceback.format_exc()}")
            return [], 0
    
    async def get_questionnaire_completed_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        search_query: Optional[str] = None,
        include_metadata: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        OPTIMIZED: Get VMP projects that have questionnaires (completed or advanced past this stage).
        
        IMPORTANT: This returns projects that have EVER completed questionnaires, including
        projects that have advanced to later stages (value maps, VPS v2, etc.). A project
        that has completed VPS v2 should still appear here because it HAS questionnaires.
        
        Returns MINIMAL data for performance:
        - Only essential columns (id, tenant_id, user_id, name, problem_statement, status, dates)
        - Counts only (no full arrays)
        - Uses PostgreSQL JSONB functions for efficient count extraction
        
        Filters projects where:
        1. field_prep_data.questionnaires array exists and is not empty
        2. Excludes bootstrap projects (they skip questionnaire workflow)
        
        Args:
            tenant_id: Tenant ID for filtering (team collaboration enabled)
            user_id: User ID (for audit logging, not used in filtering)
            page: Page number for pagination
            page_size: Number of items per page
            search_query: Optional search query for project names
            include_metadata: Whether to include counts (always included now for UI)
            
        Returns:
            Tuple of (minimal projects list, total count)
        """
        try:
            offset = (page - 1) * page_size
            
            print(f"🔍 DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Fetching projects for tenant: {tenant_id}")
            print(f"🔍 DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Page: {page}, Size: {page_size}, Search: {search_query}")
            
            # OPTIMIZED QUERY: Fetch only minimal columns + use PostgreSQL JSONB functions for counts
            # This avoids transferring large JSONB arrays over the network
            select_clause = '''
                id,
                tenant_id,
                user_id,
                name,
                refined_problem_statement,
                description,
                status,
                created_at,
                updated_at,
                context_mode,
                field_prep_data->>'questionnaires_generated_at' as questionnaires_generated_at
            '''
            
            # Build query with questionnaire completion filters
            query = self.supabase.client.table('vmp_projects').select(
                select_clause,
                count='exact'
            ).eq('tenant_id', tenant_id)
            
            # NOTE: Bootstrap projects are filtered out in Python below (not in SQL)
            # because SQL's neq filter excludes NULL values, and most projects have NULL context_mode
            
            # FIX: Instead of checking stage == 'questionnaires_completed', we check if
            # questionnaires exist. This ensures projects that have ADVANCED past this stage
            # still appear in this listing. A project that has completed VPS v2 still has
            # questionnaires and should appear here.
            # We'll validate questionnaires exist in Python after fetching.
            
            # FILTER 3: Search filter (optional)
            if search_query:
                query = query.ilike('name', f'%{search_query}%')
            
            # Apply pagination and ordering
            query = query.order('updated_at', desc=True).range(offset, offset + page_size - 1)
            
            # Execute query
            response = query.execute()
            
            print(f"🔍 DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Query returned {len(response.data)} projects")
            print(f"🔍 DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Total count: {response.count}")
            
            # Fetch counts efficiently by fetching only the JSONB fields we need
            # Then count the arrays in Python (still more efficient than loading full content)
            project_ids = [p['id'] for p in response.data]
            
            if not project_ids:
                return [], 0
            
            # Fetch ONLY the JSONB fields needed for counting (not the full arrays)
            # Use PostgreSQL JSONB operators to extract just array lengths
            counts_select = 'id, field_prep_data, personas'
            
            counts_query = self.supabase.client.table('vmp_projects').select(
                counts_select
            ).in_('id', project_ids)
            
            counts_response = counts_query.execute()
            
            # Create a mapping of project_id to counts by counting arrays
            counts_map = {}
            if counts_response.data:
                for row in counts_response.data:
                    field_prep_data = row.get('field_prep_data', {})
                    personas = row.get('personas', [])
                    
                    counts_map[row['id']] = {
                        'questionnaires_count': len(field_prep_data.get('questionnaires', [])),
                        'assumptions_count': len(field_prep_data.get('assumptions', [])),
                        'hypotheses_count': len(field_prep_data.get('hypotheses', [])),
                        'personas_count': len(personas) if isinstance(personas, list) else 0
                    }
            
            # Build minimal response objects
            # FIX: Filter out bootstrap projects in Python (SQL neq excludes NULLs)
            projects = []
            bootstrap_count = 0
            for project in response.data:
                project_id = project['id']
                
                # Skip bootstrap projects (they skip questionnaire workflow)
                if project.get('context_mode') == 'bootstrap':
                    bootstrap_count += 1
                    print(f"⏭️ DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Skipping bootstrap project {project_id}")
                    continue
                
                counts_data = counts_map.get(project_id, {})
                counts = {
                    'questionnaires_count': counts_data.get('questionnaires_count', 0),
                    'assumptions_count': counts_data.get('assumptions_count', 0),
                    'hypotheses_count': counts_data.get('hypotheses_count', 0),
                    'personas_count': counts_data.get('personas_count', 0)
                }
                
                # Skip projects with no questionnaires (validation)
                if counts['questionnaires_count'] == 0:
                    print(f"⚠️ DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Skipping project {project_id} - empty questionnaires")
                    continue
                
                # Build minimal project object
                # Fallback: Use description if refined_problem_statement is NULL
                problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                
                minimal_project = {
                    'id': project['id'],
                    'tenant_id': project['tenant_id'],
                    'user_id': project['user_id'],
                    'name': project['name'],
                    'problem_statement': problem_statement,
                    'status': project['status'],
                    'created_at': project['created_at'],
                    'updated_at': project['updated_at'],
                    'questionnaires_count': counts['questionnaires_count'],
                    'assumptions_count': counts['assumptions_count'],
                    'hypotheses_count': counts['hypotheses_count'],
                    'personas_count': counts['personas_count'],
                    'questionnaires_generated_at': project.get('questionnaires_generated_at')
                }
                
                projects.append(minimal_project)
                
                print(f"✅ DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Project {project_id}: "
                      f"{counts['questionnaires_count']} questions, "
                      f"{counts['assumptions_count']} assumptions, "
                      f"{counts['hypotheses_count']} hypotheses, "
                      f"{counts['personas_count']} personas")
            
            actual_count = len(projects)
            total_count = response.count or 0
            
            if actual_count < (response.count or 0):
                print(f"⚠️ DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Filtered out {(response.count or 0) - actual_count} projects with empty questionnaires")
            
            print(f"✅ DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Returning {actual_count} minimal projects")
            
            return projects, total_count
            
        except Exception as e:
            print(f"❌ ERROR: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Failed to fetch projects: {e}")
            import traceback
            print(f"❌ ERROR: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Traceback: {traceback.format_exc()}")
            
            # Fallback to basic query without RPC if exec_sql fails
            try:
                print(f"🔄 DEBUG: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Attempting fallback without RPC...")
                offset = (page - 1) * page_size
                
                # Basic query without counts - include context_mode for bootstrap filtering
                select_clause = 'id, tenant_id, user_id, name, refined_problem_statement, description, status, created_at, updated_at, field_prep_data, personas, context_mode'
                
                query = self.supabase.client.table('vmp_projects').select(
                    select_clause,
                    count='exact'
                ).eq('tenant_id', tenant_id)
                
                if search_query:
                    query = query.ilike('name', f'%{search_query}%')
                
                query = query.order('updated_at', desc=True).range(offset, offset + page_size - 1)
                response = query.execute()
                
                # Manual count extraction
                projects = []
                for project in response.data:
                    # Skip bootstrap projects (they skip questionnaire workflow)
                    if project.get('context_mode') == 'bootstrap':
                        continue
                    
                    field_prep_data = project.get('field_prep_data', {})
                    personas = project.get('personas', [])
                    
                    questionnaires_count = len(field_prep_data.get('questionnaires', []))
                    if questionnaires_count == 0:
                        continue
                    
                    # Fallback: Use description if refined_problem_statement is NULL
                    problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                    
                    minimal_project = {
                        'id': project['id'],
                        'tenant_id': project['tenant_id'],
                        'user_id': project['user_id'],
                        'name': project['name'],
                        'problem_statement': problem_statement,
                        'status': project['status'],
                        'created_at': project['created_at'],
                        'updated_at': project['updated_at'],
                        'questionnaires_count': questionnaires_count,
                        'assumptions_count': len(field_prep_data.get('assumptions', [])),
                        'hypotheses_count': len(field_prep_data.get('hypotheses', [])),
                        'personas_count': len(personas) if isinstance(personas, list) else 0,
                        'questionnaires_generated_at': field_prep_data.get('questionnaires_generated_at')
                    }
                    projects.append(minimal_project)
                
                return projects, response.count or 0
                
            except Exception as fallback_error:
                print(f"❌ ERROR: [GET_QUESTIONNAIRE_COMPLETED_OPTIMIZED] Fallback also failed: {fallback_error}")
                return [], 0
    
    async def get_value_map_completed_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        search_query: Optional[str] = None,
        include_metadata: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        OPTIMIZED: Get VMP projects that have completed Value Map selections (Module 2 final step).
        
        These projects are READY FOR MODULE 3 (VPS v1 generation).
        
        Returns MINIMAL data for performance:
        - Only essential columns
        - Persona counts
        - Value map completion status per persona
        
        Filters projects where:
        1. personas array has at least 1 item
        2. ALL personas have value_map_selections in vpc_v2_data
        3. Each value_map_selections has 3+ items in products_services, pain_relievers, gain_creators
        
        Args:
            tenant_id: Tenant ID for filtering (team collaboration enabled)
            user_id: User ID (for audit logging, not used in filtering)
            page: Page number for pagination
            page_size: Number of items per page
            search_query: Optional search query for project names
            include_metadata: Whether to include metadata (always included for UI)
            
        Returns:
            Tuple of (minimal projects list, total count)
        """
        try:
            offset = (page - 1) * page_size
            
            print(f"🔍 DEBUG: [GET_VALUE_MAP_COMPLETED] Fetching Module 3-ready projects for tenant: {tenant_id}")
            print(f"🔍 DEBUG: [GET_VALUE_MAP_COMPLETED] Page: {page}, Size: {page_size}, Search: {search_query}")
            
            # OPTIMIZED QUERY: Fetch only columns needed for filtering
            # NOTE: Removed enhanced_context (heavy JSONB) - not needed for validation
            select_clause = '''
                id,
                tenant_id,
                user_id,
                name,
                refined_problem_statement,
                description,
                status,
                created_at,
                updated_at,
                personas,
                vpc_v2_data,
                context_mode,
                context_status
            '''
            
            # Build query - includes both normal projects with value maps AND bootstrap projects
            query = self.supabase.client.table('vmp_projects').select(
                select_clause,
                count='exact'
            ).eq('tenant_id', tenant_id)
            
            # NOTE: NO context_mode filter here - we want BOTH:
            # 1. Normal projects with completed value maps
            # 2. Bootstrap projects that are context-ready
            # We'll filter appropriately in Python
            
            # Search filter (optional)
            if search_query:
                query = query.ilike('name', f'%{search_query}%')
            
            # Order by most recent
            query = query.order('updated_at', desc=True)
            
            # Fetch projects with reasonable limit for filtering
            # Reduced from 10x to 5x to avoid fetching too much data
            max_fetch = page_size * 5
            query = query.range(0, max_fetch - 1)
            
            # Execute query
            response = query.execute()
            
            print(f"🔍 DEBUG: [GET_VALUE_MAP_COMPLETED] Query returned {len(response.data)} projects (before filtering)")
            
            # Filter projects in Python to validate value map completion OR bootstrap readiness
            validated_projects = []
            
            for project in response.data:
                project_id = project['id']
                context_mode = project.get('context_mode', 'normal')
                context_status = project.get('context_status')
                personas = project.get('personas', [])
                vpc_v2_data = project.get('vpc_v2_data', {})
                
                # =====================================================================
                # BOOTSTRAP PROJECTS: Include if context is ready/confirmed
                # Bootstrap projects skip the normal VPM workflow and enter Module 3 directly
                # =====================================================================
                if context_mode == 'bootstrap':
                    # Check if bootstrap context is ready for Module 3
                    bootstrap_ready_statuses = ['context_ready', 'context_confirmed']
                    if context_status not in bootstrap_ready_statuses:
                        print(f"⏭️ DEBUG: [GET_VALUE_MAP_COMPLETED] Skipping bootstrap project {project_id} - "
                              f"context_status='{context_status}' (not ready)")
                        continue
                    
                    # Bootstrap project is ready - include it
                    problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                    
                    minimal_project = {
                        'id': project['id'],
                        'tenant_id': project['tenant_id'],
                        'user_id': project['user_id'],
                        'name': project['name'],
                        'problem_statement': problem_statement,
                        'status': project['status'],
                        'created_at': project['created_at'],
                        'updated_at': project['updated_at'],
                        'personas_count': 0,  # Bootstrap projects don't have traditional personas
                        'customer_profile_completed': True,  # Implicit for bootstrap
                        'value_map_completed': True,  # Implicit for bootstrap
                        'value_map_completed_at': project['updated_at'],
                        'personas': [],  # Bootstrap projects use enhanced_context instead
                        'module_3_ready': True,
                        'vps_v1_generated': False,
                        'context_mode': 'bootstrap',
                        'context_status': context_status
                    }
                    
                    validated_projects.append(minimal_project)
                    print(f"✅ DEBUG: [GET_VALUE_MAP_COMPLETED] Bootstrap project {project_id}: "
                          f"context_status='{context_status}' - ready for Module 3")
                    continue
                
                # =====================================================================
                # NORMAL PROJECTS: Validate value map completion for all personas
                # =====================================================================
                
                # Skip if no personas
                if not personas or len(personas) == 0:
                    print(f"⏭️ DEBUG: [GET_VALUE_MAP_COMPLETED] Skipping {project_id} - no personas")
                    continue
                
                # Validate ALL personas have completed value maps
                all_personas_complete = True
                persona_statuses = []
                
                for persona in personas:
                    persona_id = persona.get('id')
                    persona_name = persona.get('name', 'Unknown')
                    
                    # Get persona data from vpc_v2_data
                    persona_data = vpc_v2_data.get(persona_id, {})
                    value_map = persona_data.get('value_map_selections')
                    
                    # Check if value_map_selections exists and is complete
                    if not value_map or not isinstance(value_map, dict):
                        all_personas_complete = False
                        persona_statuses.append({
                            'id': persona_id,
                            'name': persona_name,
                            'value_map_completed': False
                        })
                        print(f"❌ DEBUG: [GET_VALUE_MAP_COMPLETED] {project_id} - Persona {persona_id} missing value_map_selections")
                        continue
                    
                    # Check all 3 categories have 3+ items
                    products = value_map.get('products_services', [])
                    relievers = value_map.get('pain_relievers', [])
                    creators = value_map.get('gain_creators', [])
                    
                    is_complete = (
                        isinstance(products, list) and len(products) >= 3 and
                        isinstance(relievers, list) and len(relievers) >= 3 and
                        isinstance(creators, list) and len(creators) >= 3
                    )
                    
                    if not is_complete:
                        all_personas_complete = False
                        print(f"❌ DEBUG: [GET_VALUE_MAP_COMPLETED] {project_id} - Persona {persona_id} incomplete: "
                              f"products={len(products)}, relievers={len(relievers)}, creators={len(creators)}")
                    
                    persona_statuses.append({
                        'id': persona_id,
                        'name': persona_name,
                        'value_map_completed': is_complete
                    })
                
                # Only include if ALL personas are complete
                if not all_personas_complete:
                    print(f"⏭️ DEBUG: [GET_VALUE_MAP_COMPLETED] Skipping {project_id} - not all personas complete")
                    continue
                
                # Get value_map completion timestamp (use updated_at from first persona's data)
                value_map_completed_at = None
                if personas and len(personas) > 0:
                    first_persona_id = personas[0].get('id')
                    first_persona_data = vpc_v2_data.get(first_persona_id, {})
                    value_map_completed_at = first_persona_data.get('updated_at')
                
                # Check if VPS v1 already generated (from mvp_projects table)
                # Note: This requires a separate query or join - for now, default to False
                vps_v1_generated = False
                
                # Fallback: Use description if refined_problem_statement is NULL
                problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                
                # Build minimal project object
                minimal_project = {
                    'id': project['id'],
                    'tenant_id': project['tenant_id'],
                    'user_id': project['user_id'],
                    'name': project['name'],
                    'problem_statement': problem_statement,
                    'status': project['status'],
                    'created_at': project['created_at'],
                    'updated_at': project['updated_at'],
                    'personas_count': len(personas),
                    'customer_profile_completed': True,  # Implicit if value_map exists
                    'value_map_completed': True,
                    'value_map_completed_at': value_map_completed_at or project['updated_at'],
                    'personas': persona_statuses,
                    'module_3_ready': True,
                    'vps_v1_generated': vps_v1_generated,
                    'context_mode': 'normal'
                }
                
                validated_projects.append(minimal_project)
                
                print(f"✅ DEBUG: [GET_VALUE_MAP_COMPLETED] Project {project_id}: "
                      f"{len(personas)} personas, all value maps complete")
            
            # Apply pagination to filtered results
            total_count = len(validated_projects)
            start_idx = offset
            end_idx = offset + page_size
            paginated_projects = validated_projects[start_idx:end_idx]
            
            print(f"✅ DEBUG: [GET_VALUE_MAP_COMPLETED] Returning {len(paginated_projects)} projects (page {page} of {total_count} total)")
            
            return paginated_projects, total_count
            
        except Exception as e:
            print(f"❌ ERROR: [GET_VALUE_MAP_COMPLETED] Failed to fetch projects: {e}")
            import traceback
            print(f"❌ ERROR: [GET_VALUE_MAP_COMPLETED] Traceback: {traceback.format_exc()}")
            return [], 0
    
    async def get_vps_v2_completed_projects(
        self, 
        tenant_id: str, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 35,
        search_query: Optional[str] = None,
        include_metadata: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get VMP projects that have completed VPS v2 generation (Module 3 refinement).
        
        These projects are READY FOR AMRG (MVP Requirements Generator).
        
        Returns MINIMAL data for performance:
        - Only essential columns
        - VPS v2 metadata (persona count, generation timestamp)
        
        Filters projects where:
        1. mvp_data.vps_v2 exists and is not empty
        2. mvp_data.current_version.vps = 'v2'
        
        Args:
            tenant_id: Tenant ID for filtering (team collaboration enabled)
            user_id: User ID (for audit logging, not used in filtering)
            page: Page number for pagination
            page_size: Number of items per page
            search_query: Optional search query for project names
            include_metadata: Whether to include metadata (always included for UI)
            
        Returns:
            Tuple of (minimal projects list, total count)
        """
        try:
            offset = (page - 1) * page_size
            
            print(f"🔍 DEBUG: [GET_VPS_V2_COMPLETED] Fetching AMRG-ready projects for tenant: {tenant_id}")
            print(f"🔍 DEBUG: [GET_VPS_V2_COMPLETED] Page: {page}, Size: {page_size}, Search: {search_query}")
            
            # OPTIMIZED QUERY: Fetch columns needed for filtering + VPS v2 validation
            # NOTE: Includes context_mode to identify bootstrap projects
            select_clause = '''
                id,
                tenant_id,
                user_id,
                name,
                refined_problem_statement,
                description,
                status,
                created_at,
                updated_at,
                mvp_data,
                personas,
                context_mode,
                context_status
            '''
            
            # Build query - includes both normal projects AND bootstrap projects with VPS v2
            query = self.supabase.client.table('vmp_projects').select(
                select_clause,
                count='exact'
            ).eq('tenant_id', tenant_id)
            
            # Search filter (optional)
            if search_query:
                query = query.ilike('name', f'%{search_query}%')
            
            # Order by most recent
            query = query.order('updated_at', desc=True)
            
            # Fetch projects with reasonable limit for filtering
            max_fetch = page_size * 5
            query = query.range(0, max_fetch - 1)
            
            # Execute query
            response = query.execute()
            
            print(f"🔍 DEBUG: [GET_VPS_V2_COMPLETED] Query returned {len(response.data)} projects (before filtering)")
            
            # Filter projects in Python to validate VPS v2 completion
            validated_projects = []
            
            for project in response.data:
                project_id = project['id']
                mvp_data = project.get('mvp_data', {})
                personas = project.get('personas', [])
                
                # Skip if no mvp_data
                if not mvp_data or not isinstance(mvp_data, dict):
                    print(f"⏭️ DEBUG: [GET_VPS_V2_COMPLETED] Skipping {project_id} - no mvp_data")
                    continue
                
                # Check if VPS v2 exists
                vps_v2 = mvp_data.get('vps_v2')
                if not vps_v2:
                    print(f"⏭️ DEBUG: [GET_VPS_V2_COMPLETED] Skipping {project_id} - no vps_v2")
                    continue
                
                # Ensure vps_v2 is a non-empty list/dict
                vps_v2_count = 0
                if isinstance(vps_v2, list):
                    vps_v2_count = len(vps_v2)
                elif isinstance(vps_v2, dict):
                    vps_v2_count = 1
                
                if vps_v2_count == 0:
                    print(f"⏭️ DEBUG: [GET_VPS_V2_COMPLETED] Skipping {project_id} - empty vps_v2")
                    continue
                
                # Check version tracking (optional, for additional validation)
                current_version = mvp_data.get('current_version', {})
                vps_version = current_version.get('vps', 'unknown')
                vps_updated_at = current_version.get('vps_updated_at')
                
                # Check if BMC v2 also exists (indicates full Module 3 completion)
                bmc_v2 = mvp_data.get('bmc_v2')
                bmc_v2_exists = bool(bmc_v2 and isinstance(bmc_v2, dict) and len(bmc_v2) > 0)
                
                # Check if Solution Critique exists
                soln_critique = mvp_data.get('solution_critique') or project.get('soln_critique_data')
                critique_exists = bool(soln_critique and isinstance(soln_critique, dict))
                
                # Fallback: Use description if refined_problem_statement is NULL
                problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                
                # Build minimal project object
                # Include context_mode to identify bootstrap projects
                context_mode = project.get('context_mode', 'normal')
                context_status = project.get('context_status')
                
                minimal_project = {
                    'id': project['id'],
                    'tenant_id': project['tenant_id'],
                    'user_id': project['user_id'],
                    'name': project['name'],
                    'problem_statement': problem_statement,
                    'status': project['status'],
                    'created_at': project['created_at'],
                    'updated_at': project['updated_at'],
                    'personas_count': len(personas) if isinstance(personas, list) else 0,
                    'vps_v2_count': vps_v2_count,
                    'vps_version': vps_version,
                    'vps_updated_at': vps_updated_at,
                    'bmc_v2_exists': bmc_v2_exists,
                    'critique_exists': critique_exists,
                    'amrg_ready': vps_v2_count > 0 and bmc_v2_exists and critique_exists,
                    'module_3_status': 'complete' if (vps_v2_count > 0 and bmc_v2_exists) else 'partial',
                    'context_mode': context_mode,
                    'context_status': context_status
                }
                
                validated_projects.append(minimal_project)
                
                print(f"✅ DEBUG: [GET_VPS_V2_COMPLETED] Project {project_id}: "
                      f"{vps_v2_count} VPS v2, BMC v2={bmc_v2_exists}, Critique={critique_exists}")
            
            # Apply pagination to filtered results
            total_count = len(validated_projects)
            start_idx = offset
            end_idx = offset + page_size
            paginated_projects = validated_projects[start_idx:end_idx]
            
            print(f"✅ DEBUG: [GET_VPS_V2_COMPLETED] Returning {len(paginated_projects)} projects (page {page} of {total_count} total)")
            
            return paginated_projects, total_count
            
        except Exception as e:
            print(f"❌ ERROR: [GET_VPS_V2_COMPLETED] Failed to fetch projects: {e}")
            import traceback
            print(f"❌ ERROR: [GET_VPS_V2_COMPLETED] Traceback: {traceback.format_exc()}")
            return [], 0
    
    async def get_latest_projects(
        self, 
        tenant_id: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the latest VMP projects ordered by updated_at (most recent first).
        
        OPTIMIZED for fast fetching:
        - Minimal columns selected
        - Single direct query with LIMIT
        - No pagination overhead
        - No complex filtering
        
        Args:
            tenant_id: Tenant ID for filtering
            limit: Maximum number of projects to return (default 5)
            
        Returns:
            List of minimal project objects
        """
        try:
            print(f"🚀 DEBUG: [GET_LATEST_PROJECTS] Fetching top {limit} projects for tenant: {tenant_id}")
            
            # ULTRA-OPTIMIZED QUERY: Only essential columns for display
            # Include context_mode for bootstrap filtering
            response = self.supabase.client.table('vmp_projects').select(
                'id, name, refined_problem_statement, description, status, current_step, created_at, updated_at, personas, context_mode'
            ).eq(
                'tenant_id', tenant_id
            ).order(
                'updated_at', desc=True
            ).limit(limit * 2).execute()  # Fetch extra to account for filtered bootstrap projects
            
            if not response.data:
                print(f"🚀 DEBUG: [GET_LATEST_PROJECTS] No projects found")
                return []
            
            print(f"🚀 DEBUG: [GET_LATEST_PROJECTS] Found {len(response.data)} projects")
            
            # Build minimal project objects
            # NOTE: Bootstrap projects are filtered out - they should only appear in Module 3 bootstrap endpoints
            projects = []
            bootstrap_count = 0
            for project in response.data:
                # Skip bootstrap projects
                if project.get('context_mode') == 'bootstrap':
                    bootstrap_count += 1
                    continue
                
                # Stop once we have enough non-bootstrap projects
                if len(projects) >= limit:
                    break
                
                personas = project.get('personas', [])
                # Use refined_problem_statement if available, fallback to description
                problem_statement = project.get('refined_problem_statement') or project.get('description') or ''
                minimal_project = {
                    'id': project['id'],
                    'name': project['name'],
                    'problem_statement': problem_statement,
                    'status': project.get('status', 'active'),
                    'current_step': project.get('current_step', 'project_setup'),
                    'created_at': project['created_at'],
                    'updated_at': project['updated_at'],
                    'personas_count': len(personas) if isinstance(personas, list) else 0
                }
                projects.append(minimal_project)
            
            if bootstrap_count > 0:
                print(f"🚀 DEBUG: [GET_LATEST_PROJECTS] Filtered out {bootstrap_count} bootstrap projects")
            
            return projects
            
        except Exception as e:
            print(f"❌ ERROR: [GET_LATEST_PROJECTS] Failed to fetch projects: {e}")
            import traceback
            print(f"❌ ERROR: [GET_LATEST_PROJECTS] Traceback: {traceback.format_exc()}")
            return []
    
    async def get_vmp_project(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single VMP project by ID.
        
        Returns the project data including vpc_data and other metadata.
        """
        try:
            print(f"🔍 DEBUG: [GET_VMP_PROJECT] Querying project_id={project_id}, tenant_id={tenant_id}")
            
            # CRITICAL FIX: Include analysis_data, vpc_v2_data, refined_problem_statement and all market research columns
            response = self.supabase.client.table('vmp_projects').select(
                'id, tenant_id, user_id, name, description, pv_report_id, status, current_step, '
                'vpc_data, vpc_v2_data, field_prep_data, settings, created_at, updated_at, '
                'analysis_data, analysis_status, research_documents_data, personas, '
                'refined_problem_statement, '
                'documents!vmp_projects_pv_report_id_fkey(title)'
            ).eq('id', project_id).limit(1).execute()
            
            print(f"🔍 DEBUG: [GET_VMP_PROJECT] Response data count: {len(response.data) if response.data else 0}")
            
            if not response.data:
                print(f"❌ DEBUG: [GET_VMP_PROJECT] No project found with id={project_id}")
                return None
            
            project = response.data[0]
            print(f"✅ DEBUG: [GET_VMP_PROJECT] Found project: {project.get('id')}")
            print(f"🔍 DEBUG: [GET_VMP_PROJECT] Project tenant_id: {project.get('tenant_id')}")
            print(f"🔍 DEBUG: [GET_VMP_PROJECT] Project user_id: {project.get('user_id')}")
            print(f"🔍 DEBUG: [GET_VMP_PROJECT] Field prep data keys: {list(project.get('field_prep_data', {}).keys())}")
            
            # Debug VPC v2 data
            vpc_v2_data = project.get('vpc_v2_data', {})
            if vpc_v2_data:
                print(f"🔍 DEBUG: [GET_VMP_PROJECT] vpc_v2_data keys: {list(vpc_v2_data.keys()) if isinstance(vpc_v2_data, dict) else 'not a dict'}")
            else:
                print(f"🔍 DEBUG: [GET_VMP_PROJECT] vpc_v2_data is empty or None")
            
            # Ensure vpc_data is properly structured
            if not project.get('vpc_data'):
                project['vpc_data'] = {}
            
            # Ensure vpc_v2_data is properly structured
            if not project.get('vpc_v2_data'):
                project['vpc_v2_data'] = {}
            
            return project
            
        except Exception as e:
            print(f"❌ ERROR: [GET_VMP_PROJECT] Error fetching VMP project {project_id}: {e}")
            print(f"❌ ERROR: [GET_VMP_PROJECT] Traceback: {traceback.format_exc()}")
            return None
    
    async def update_project_stage(self, project_id: str, stage: str) -> bool:
        """Update project workflow stage."""
        try:
            response = self.supabase.client.table('vmp_projects').update({
                'current_step': stage,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error updating project stage: {e}")
            return False
    
    async def link_project_contexts(self, project_id: str, pv_report_id: str) -> bool:
        """
        Link project to both PV report and actionable insights contexts.
        
        This implements the dual vector store integration described in VPM docs.
        """
        try:
            # For now, skip the context linking since we're using the main projects table
            # The PV report ID is already stored in the project record itself
            # TODO: Implement proper context linking using existing tables or create project_contexts table
            print(f"🔍 DEBUG: Skipping context linking for now - PV report ID {pv_report_id} is stored in project")
            
            # Find related actionable insights for reference
            insights_response = self.supabase.client.table('documents').select('id').eq(
                'source_type', 'actionable_insights'
            ).eq('metadata->>pv_report_id', pv_report_id).execute()
            
            print(f"🔍 DEBUG: Found {len(insights_response.data or [])} actionable insights for PV report {pv_report_id}")
            
            return True
            
        except Exception as e:
            print(f"Error linking project contexts: {e}")
            return False
    
    # Helper methods
    async def _check_has_insights(self, report_id: str) -> bool:
        """Check if report has associated actionable insights"""
        try:
            response = self.supabase.client.table('documents').select('id', count='exact').eq(
                'source_type', 'actionable_insights'
            ).eq('metadata->>pv_report_id', report_id).execute()
            
            return (response.count or 0) > 0
        except:
            return False
    
    async def _get_insights_count(self, report_id: str) -> int:
        """Get count of actionable insights for a report"""
        try:
            response = self.supabase.client.table('documents').select('id', count='exact').eq(
                'source_type', 'actionable_insights'
            ).eq('metadata->>pv_report_id', report_id).execute()
            
            return response.count or 0
        except:
            return 0
    
    async def _get_artifact_count(self, project_id: str) -> int:
        """Get count of artifacts for a project"""
        try:
            response = self.supabase.client.table('vmp_vpc_artifacts').select('id', count='exact').eq(
                'project_id', project_id
            ).execute()
            
            return response.count or 0
        except:
            return 0

    def _calculate_file_size(self, storage_path: Optional[str]) -> Optional[float]:
        """Calculate file size in MB (placeholder implementation)"""
        # TODO: Implement actual file size calculation if needed
        return 1.5 if storage_path else None

    def _calculate_progress(self, current_step: Optional[str]) -> int:
        """Calculate progress percentage based on current step"""
        step_progress = {
            'project_setup': 10,
            'customer_profile_generation': 25,
            'customer_profile_selection': 35,
            'value_map_generation': 60,
            'value_map_selection': 75,
            'vpc_composition': 90,
            'field_prep_hypothesis': 80,
            'field_prep_assumptions': 85,
            'field_prep_stakeholders': 90,
            'field_prep_questionnaires': 95,
            'completed': 100
        }
        return step_progress.get(current_step, 0)

    async def save_customer_profile_selections(
        self,
        project_id: str,
        selected_candidates: Dict[str, List[Dict]],
        user_id: str
    ) -> bool:
        """
        Save customer profile selections as full objects in vpc_data.
        
        Args:
            project_id: VMP project ID
            selected_candidates: Full candidate objects mapped from IDs
            user_id: User ID for security
        """
        try:
            # Get current project data
            # CRITICAL FIX: Removed user_id filter to enable team collaboration
            project_result = self.supabase.client.table('vmp_projects').select('*').eq(
                'id', project_id
            ).single().execute()
            
            if not project_result.data:
                return False
            
            # Update project with customer profile selections in vpc_data
            current_data = project_result.data
            vpc_data = current_data.get('vpc_data', {})
            
            # FIXED: Check if we have current personas to determine project type
            current_personas = current_data.get('personas', [])
            print(f"🔍 DEBUG: [SAVE_CP] Current personas count: {len(current_personas)}")
            
            # If we have exactly 1 persona, force single persona format (clear old multi-persona data)
            if len(current_personas) == 1:
                print(f"🔍 DEBUG: [SAVE_CP] Single persona detected - clearing old multi-persona data and using single format")
                # Clear any old multi-persona structure and use single persona format
                vpc_data = {  # Reset vpc_data to clean state
                    'customer_profile': {
                        'jobs_to_be_done': selected_candidates.get('jtbd', []),
                        'pains': selected_candidates.get('pain', []),
                        'gains': selected_candidates.get('gain', [])
                    }
                }
                print(f"✅ DEBUG: [SAVE_CP] Single persona customer profile saved: JTBD={len(selected_candidates.get('jtbd', []))}, Pains={len(selected_candidates.get('pain', []))}, Gains={len(selected_candidates.get('gain', []))}")
                
            elif len(current_personas) > 1:
                # Multi-persona project - initialize or update VPCs structure
                print(f"🔍 DEBUG: [SAVE_CP] Multi-persona project detected with {len(current_personas)} personas")
                
                # Initialize VPCs structure if it doesn't exist
                if 'vpcs' not in vpc_data or not isinstance(vpc_data['vpcs'], dict):
                    print(f"🔍 DEBUG: [SAVE_CP] Initializing VPCs structure for multi-persona project")
                    vpc_data['vpcs'] = {}
                
                # CRITICAL FIX: Ensure ALL current personas have VPC entries
                # This handles cases where personas were added after initial VPC creation
                for persona in current_personas:
                    persona_id = persona.get('id', f'P{len(vpc_data["vpcs"]) + 1}')
                    
                    if persona_id not in vpc_data['vpcs']:
                        # Create missing VPC entry
                        vpc_data['vpcs'][persona_id] = {
                            'persona_id': persona_id,
                            'persona_name': persona.get('name', f'Persona {persona_id}'),
                            'status': 'persona_identified',
                            'customer_profile': None,
                            'value_map': None,
                            'canvas_data': None,
                            'created_at': datetime.utcnow().isoformat()
                        }
                        print(f"✅ DEBUG: [SAVE_CP] Created missing VPC entry for {persona_id}: {persona.get('name')}")
                    else:
                        print(f"🔍 DEBUG: [SAVE_CP] VPC entry already exists for {persona_id}: {persona.get('name')}")
                
                print(f"🔍 DEBUG: [SAVE_CP] VPCs available after initialization: {list(vpc_data['vpcs'].keys())}")
                
                # Group selections by persona_id
                persona_profiles = {}
                for category, items in selected_candidates.items():
                    for item in items:
                        persona_id = item.get('persona_id', 'P1')  # Default to P1 if no persona_id
                        if persona_id not in persona_profiles:
                            persona_profiles[persona_id] = {'jobs_to_be_done': [], 'pains': [], 'gains': []}
                        
                        # Map category names
                        if category == 'jtbd':
                            persona_profiles[persona_id]['jobs_to_be_done'].append(item)
                        elif category == 'pain':
                            persona_profiles[persona_id]['pains'].append(item)
                        elif category == 'gain':
                            persona_profiles[persona_id]['gains'].append(item)
                
                # VALIDATION: Ensure all current personas have selections
                print(f"🔍 DEBUG: [SAVE_CP] Persona profiles created: {list(persona_profiles.keys())}")
                print(f"🔍 DEBUG: [SAVE_CP] Current personas in project: {[p.get('id') for p in current_personas]}")
                
                missing_personas = []
                for persona in current_personas:
                    persona_id = persona.get('id')
                    if persona_id not in persona_profiles:
                        missing_personas.append(persona_id)
                        print(f"⚠️ WARNING: [SAVE_CP] No selections found for persona {persona_id}")
                
                if missing_personas:
                    print(f"🚨 ERROR: [SAVE_CP] Missing selections for personas: {missing_personas}")
                    print(f"🚨 ERROR: [SAVE_CP] This means the frontend sent incomplete data or persona_id mismatch")
                
                # Save to each persona's VPC
                for persona_id, profile in persona_profiles.items():
                    if persona_id in vpc_data['vpcs']:
                        vpc_data['vpcs'][persona_id]['customer_profile'] = profile
                        vpc_data['vpcs'][persona_id]['status'] = 'customer_profile_completed'
                        print(f"✅ DEBUG: [SAVE_CP] Saved customer profile for {persona_id}: JTBD={len(profile['jobs_to_be_done'])}, Pains={len(profile['pains'])}, Gains={len(profile['gains'])}")
                    else:
                        # CRITICAL ERROR: This should never happen after the fix above
                        error_msg = f"CRITICAL ERROR: Persona {persona_id} not found in VPCs structure even after initialization. Available personas: {list(vpc_data['vpcs'].keys())}"
                        print(f"🚨 {error_msg}")
                        raise Exception(error_msg)
                
            else:
                # Fallback: Single persona project - use traditional structure
                print(f"🔍 DEBUG: [SAVE_CP] Fallback single persona project - using traditional structure")
                vpc_data['customer_profile'] = {
                    'jobs_to_be_done': selected_candidates.get('jtbd', []),
                    'pains': selected_candidates.get('pain', []),
                    'gains': selected_candidates.get('gain', [])
                }
            
            # Update project - FIXED: Set correct next step for field prep workflow
            update_result = self.supabase.client.table('vmp_projects').update({
                'vpc_data': vpc_data,
                'current_step': 'customer_profile',  # Correct step for field prep workflow
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            success = bool(update_result.data)
            
            # 🔄 BACKGROUND CHUNKING: Chunk customer profile for "Chat with Project" feature
            if success:
                try:
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    tenant_id = current_data.get('tenant_id')
                    customer_profile = vpc_data.get('customer_profile')
                    if tenant_id and customer_profile:
                        await chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.CUSTOMER_PROFILE,
                            feature_data={"customer_profile": customer_profile}
                        )
                        print(f"🚀 DEBUG: [SAVE_CP] Background chunking spawned for customer profile")
                except Exception as chunk_error:
                    print(f"⚠️ DEBUG: [SAVE_CP] Background chunking failed (non-blocking): {chunk_error}")
            
            return success
            
        except Exception as e:
            print(f"Error saving customer profile selections: {e}")
            return False

    async def save_value_map_selections(
        self,
        project_id: str,
        selected_candidates: Dict[str, List[Dict]],
        user_id: str
    ) -> bool:
        """
        Save value map selections and complete the VPC in vpc_data.
        
        Args:
            project_id: VMP project ID
            selected_candidates: Full value map candidate objects
            user_id: User ID for security
        """
        try:
            # Get current project data
            # CRITICAL FIX: Removed user_id filter to enable team collaboration
            project_result = self.supabase.client.table('vmp_projects').select('*').eq(
                'id', project_id
            ).single().execute()
            
            if not project_result.data:
                return False
            
            # Update project with value map selections in vpc_data
            current_data = project_result.data
            vpc_data = current_data.get('vpc_data', {})
            
            # Ensure customer profile exists (preserve existing customer profile data)
            if 'customer_profile' not in vpc_data:
                vpc_data['customer_profile'] = {}
            
            # Add value map to existing customer profile (MERGE with existing data)
            vpc_data['value_map'] = {
                'products_services': selected_candidates.get('product_service', []),
                'pain_relievers': selected_candidates.get('pain_reliever', []),
                'gain_creators': selected_candidates.get('gain_creator', [])
            }
            
            # Mark VPC as complete
            vpc_data['vpc_complete'] = True
            vpc_data['completed_at'] = datetime.utcnow().isoformat()
            
            print(f"🔍 DEBUG: Merging value map with existing customer profile in vpc_data")
            print(f"🔍 DEBUG: Customer profile exists: {'customer_profile' in vpc_data}")
            print(f"🔍 DEBUG: Value map added with {len(vpc_data['value_map']['products_services'])} products, {len(vpc_data['value_map']['pain_relievers'])} pain relievers, {len(vpc_data['value_map']['gain_creators'])} gain creators")
            
            # Update project
            update_result = self.supabase.client.table('vmp_projects').update({
                'vpc_data': vpc_data,
                'current_step': 'vpc_composition',  # Move to composition step
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            success = bool(update_result.data)
            
            # 🔄 BACKGROUND CHUNKING: Chunk value map for "Chat with Project" feature
            if success:
                try:
                    from src.vpm.services.project_chunking_service import chunk_vmp_feature_background, VMPFeatureType
                    tenant_id = current_data.get('tenant_id')
                    value_map = vpc_data.get('value_map')
                    if tenant_id and value_map:
                        await chunk_vmp_feature_background(
                            project_id=project_id,
                            tenant_id=tenant_id,
                            feature_type=VMPFeatureType.VALUE_MAP,
                            feature_data={"value_map": value_map}
                        )
                        print(f"🚀 DEBUG: [SAVE_VM] Background chunking spawned for value map")
                except Exception as chunk_error:
                    print(f"⚠️ DEBUG: [SAVE_VM] Background chunking failed (non-blocking): {chunk_error}")
            
            return success
            
        except Exception as e:
            print(f"Error saving value map selections: {e}")
            return False

    async def get_project_with_selections(self, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project data including all selections and workflow status.
        Uses hybrid approach - gets data from both tables.
        """
        try:
            # Get VMP project data (specialized) - FIXED: Remove .single() for current Supabase API
            # CRITICAL FIX: Removed user_id filter to enable team collaboration
            vmp_result = self.supabase.client.table('vmp_projects').select('*').eq(
                'id', project_id
            ).execute()
            
            if not vmp_result.data or len(vmp_result.data) == 0:
                print(f"🔍 DEBUG: [GET_PROJECT] No VMP project found for project_id={project_id}, user_id={user_id}")
                return None
            
            vmp_data = vmp_result.data[0]  # Get first result instead of .single()
            print(f"🔍 DEBUG: [GET_PROJECT] Found VMP project: {vmp_data.get('id')}")
            print(f"🔍 DEBUG: [GET_PROJECT] VPC data keys: {list(vmp_data.get('vpc_data', {}).keys())}")
            
            workflow_data = vmp_data.get('workflow_data', {})
            
            # Get parent project data (journey tracking) if it exists
            parent_project = None
            if vmp_data.get('parent_project_id'):
                parent_result = self.supabase.client.table('projects').select('*').eq(
                    'id', vmp_data['parent_project_id']
                ).execute()
                
                if parent_result.data and len(parent_result.data) > 0:
                    parent_project = parent_result.data[0]  # Get first result instead of .single()
            
            # Extract selections from workflow data and include all VMP project fields
            return {
                'project_id': project_id,
                'pv_report_id': vmp_data.get('pv_report_id'),  # Add the missing pv_report_id
                'parent_project_id': vmp_data.get('parent_project_id'),
                'parent_project': parent_project,
                'vpc_data': vmp_data.get('vpc_data', {}),  # Add vpc_data for customer profile selections
                'workflow_data': workflow_data,  # Keep workflow_data for backward compatibility
                'customer_profile_selections': workflow_data.get('customer_profile_selections'),
                'value_map_selections': workflow_data.get('value_map_selections'),
                'final_vpc': workflow_data.get('final_vpc'),
                'step_1_completed': workflow_data.get('step_1_completed', False),
                'step_2_completed': workflow_data.get('step_2_completed', False),
                'step_3_completed': workflow_data.get('step_3_completed', False),
                'vmp_project_data': vmp_data,
                'project_data': vmp_data  # Backward compatibility
            }
            
        except Exception as e:
            print(f"❌ ERROR: [GET_PROJECT] Error getting project with selections: {e}")
            print(f"❌ ERROR: [GET_PROJECT] Traceback: {traceback.format_exc()}")
            return None

    async def save_final_vpc(self, project_id: str, final_vpc: Dict[str, Any], user_id: str) -> bool:
        """
        Save the final composed VPC to the project.
        """
        try:
            # Get current project data
            # CRITICAL FIX: Removed user_id filter to enable team collaboration
            project_result = self.supabase.client.table('vmp_projects').select('*').eq(
                'id', project_id
            ).single().execute()
            
            if not project_result.data:
                return False
            
            # Update project with final VPC
            current_data = project_result.data
            workflow_data = current_data.get('workflow_data', {})
            
            workflow_data['final_vpc'] = final_vpc
            workflow_data['step_3_completed'] = True
            workflow_data['vpc_completed_at'] = datetime.utcnow().isoformat()
            
            # Update project
            update_result = self.supabase.client.table('vmp_projects').update({
                'workflow_data': workflow_data,
                'status': 'completed',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            return bool(update_result.data)
            
        except Exception as e:
            print(f"Error saving final VPC: {e}")
            return False

    async def save_project_personas(
        self,
        project_id: str,
        personas: List[Dict[str, Any]]
    ) -> bool:
        """
        Save identified personas to the vmp_projects table.
        
        Args:
            project_id: VMP project ID
            personas: List of persona dictionaries
        
        Returns:
            bool: True if successful
        """
        try:
            supabase = get_service_role_client()
            
            print(f"🔍 DEBUG: [PERSONAS] Saving {len(personas)} personas for project {project_id}")
            for i, persona in enumerate(personas):
                print(f"🔍 DEBUG: [PERSONAS] Persona {i+1}: {persona.get('name', 'Unknown')} (ID: {persona.get('id', 'Unknown')})")
            
            # Update the project with personas and set current step
            result = supabase.client.table("vmp_projects").update({
                "personas": personas,
                "current_step": "customer_profile",  # Move to next step after persona identification
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", project_id).execute()
            
            if result.data:
                print(f"✅ DEBUG: [PERSONAS] Successfully saved {len(personas)} personas to project {project_id}")
                print(f"✅ DEBUG: [PERSONAS] Updated current_step to 'customer_profile'")
                return True
            else:
                print(f"❌ DEBUG: [PERSONAS] Failed to save personas - no data returned")
                return False
                
        except Exception as e:
            print(f"❌ DEBUG: [PERSONAS] Error saving personas: {e}")
            return False

    async def get_latest_vpc_artifacts(
        self,
        project_id: str,
        artifact_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest VPC artifacts for a project by type.
        
        Args:
            project_id: VMP project ID
            artifact_type: Type of artifact (e.g., 'customer_profile', 'value_map')
            
        Returns:
            Latest artifact data or None if not found
        """
        try:
            response = self.supabase.client.table('vmp_vpc_artifacts').select('*').eq(
                'project_id', project_id
            ).eq('artifact_type', artifact_type).order(
                'created_at', desc=True
            ).limit(1).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"Error getting latest VPC artifacts: {e}")
            return None

    async def get_project_detail(
        self,
        project_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete project details for VPS context loading.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID for security
        
        Returns:
            Dictionary with project details including vpc_data, personas, field_prep_data, etc.
        """
        try:
            supabase = get_service_role_client()
            
            result = supabase.client.table("vmp_projects").select("*").eq(
                "id", project_id
            ).eq("tenant_id", tenant_id).execute()
            
            if not result.data or len(result.data) == 0:
                print(f"❌ DEBUG: [PROJECT_DETAIL] No project found for {project_id}")
                return None
            
            project_data = result.data[0]
            print(f"✅ DEBUG: [PROJECT_DETAIL] Retrieved project {project_id}")
            
            # CRITICAL: VPC 2.0 can be stored in multiple places
            vpc_v2_data = project_data.get('vpc_v2_data', {})
            vpc_data = project_data.get('vpc_data', {})
            
            print(f"🔍 DEBUG: [PROJECT_DETAIL] vpc_data keys: {list(vpc_data.keys()) if vpc_data else 'None'}")
            print(f"🔍 DEBUG: [PROJECT_DETAIL] vpc_v2_data keys: {list(vpc_v2_data.keys()) if vpc_v2_data else 'None'}")
            
            # Strategy 1: Check vpc_v2_data first
            if vpc_v2_data and vpc_v2_data.get('customer_profile'):
                print(f"✅ DEBUG: [PROJECT_DETAIL] Using vpc_v2_data (VPC 2.0 format)")
                vpc_data = vpc_v2_data
            # Strategy 2: Check if vpc_data has 'vpcs' key (nested structure)
            elif vpc_data and 'vpcs' in vpc_data:
                print(f"🔍 DEBUG: [PROJECT_DETAIL] Found 'vpcs' key in vpc_data, extracting first VPC")
                vpcs = vpc_data.get('vpcs', {})
                if isinstance(vpcs, dict):
                    # Get the first VPC (usually keyed by persona_id like 'P1')
                    for persona_key, vpc_content in vpcs.items():
                        if isinstance(vpc_content, dict) and vpc_content.get('customer_profile'):
                            print(f"✅ DEBUG: [PROJECT_DETAIL] Using VPC from vpcs['{persona_key}']")
                            vpc_data = vpc_content
                            break
            # Strategy 3: Search for persona-specific VPC data directly in vpc_data
            elif vpc_data and not vpc_data.get('customer_profile'):
                print(f"🔍 DEBUG: [PROJECT_DETAIL] Searching for persona-specific VPC in vpc_data")
                for key, value in vpc_data.items():
                    if isinstance(value, dict) and (value.get('customer_profile') or value.get('value_map_selections')):
                        print(f"✅ DEBUG: [PROJECT_DETAIL] Found VPC data in key: {key}")
                        vpc_data = value
                        break
            
            # Return project data with all necessary fields
            return {
                'id': project_data.get('id'),
                'name': project_data.get('name'),
                'description': project_data.get('description'),
                'vpc_data': vpc_data,
                'vpc_v2_data': project_data.get('vpc_v2_data', {}),
                'personas': project_data.get('personas', []),
                'field_prep_data': project_data.get('field_prep_data', {}),
                'pv_report_id': project_data.get('pv_report_id'),
                'analysis_data': project_data.get('analysis_data', {}),
                'status': project_data.get('status'),
                'tenant_id': project_data.get('tenant_id'),
                'user_id': project_data.get('user_id'),
                # Bootstrap context fields
                'context_mode': project_data.get('context_mode'),
                'context_status': project_data.get('context_status'),
                'enhanced_context': project_data.get('enhanced_context', {})
            }
                
        except Exception as e:
            print(f"❌ DEBUG: [PROJECT_DETAIL] Error retrieving project: {e}")
            return None
    
    async def get_project_personas(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve stored personas for a VMP project.
        
        Args:
            project_id: VMP project ID
        
        Returns:
            List of persona dictionaries
        """
        try:
            supabase = get_service_role_client()
            
            result = supabase.client.table("vmp_projects").select("personas").eq(
                "id", project_id
            ).execute()
            
            if result.data and result.data[0].get("personas"):
                personas = result.data[0]["personas"]
                print(f"🔍 DEBUG: [PERSONAS] Retrieved {len(personas)} personas for project {project_id}")
                return personas
            else:
                print(f"🔍 DEBUG: [PERSONAS] No personas found for project {project_id}")
                return []
                
        except Exception as e:
            print(f"❌ DEBUG: [PERSONAS] Error retrieving personas: {e}")
            return []
    
    async def save_refined_problem_statement(
        self, 
        project_id: str, 
        problem_statement: str,
        user_id: str
    ) -> bool:
        """
        Save refined problem statement to VMP project.
        
        Args:
            project_id: VMP project ID
            problem_statement: Extracted/refined problem statement
            user_id: User ID for security
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            from datetime import datetime
            
            # CRITICAL FIX: Removed user_id filter to enable team collaboration
            result = self.supabase.client.table('vmp_projects').update({
                'refined_problem_statement': problem_statement,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
            
            if result.data:
                print(f"✅ DEBUG: [PROBLEM_STATEMENT] Saved refined problem statement for project {project_id}")
                return True
            else:
                print(f"❌ DEBUG: [PROBLEM_STATEMENT] Failed to save - no data returned")
                return False
                
        except Exception as e:
            print(f"❌ ERROR: Failed to save refined problem statement: {e}")
            return False
    
    async def get_refined_problem_statement(self, project_id: str) -> Optional[str]:
        """
        Get refined problem statement for a VMP project.
        
        Args:
            project_id: VMP project ID
            
        Returns:
            Problem statement string or None if not found
        """
        try:
            result = self.supabase.client.table('vmp_projects').select(
                'refined_problem_statement'
            ).eq('id', project_id).single().execute()
            
            if result.data and result.data.get('refined_problem_statement'):
                statement = result.data['refined_problem_statement']
                print(f"✅ DEBUG: [PROBLEM_STATEMENT] Retrieved statement for project {project_id}: {statement[:100]}...")
                return statement
            else:
                print(f"🔍 DEBUG: [PROBLEM_STATEMENT] No statement found for project {project_id}")
                return None
                
        except Exception as e:
            print(f"❌ ERROR: Failed to get refined problem statement: {e}")
            return None


# Singleton instance for VPM to use
_database_adapter_instance = None

def get_yuba_database_adapter() -> YubaDatabaseAdapter:
    """Get singleton instance of Yuba database adapter"""
    global _database_adapter_instance
    if _database_adapter_instance is None:
        _database_adapter_instance = YubaDatabaseAdapter()
    return _database_adapter_instance
