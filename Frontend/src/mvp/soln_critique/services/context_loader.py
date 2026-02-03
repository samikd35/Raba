"""
Context loader for solution critique
Loads VPC v2, VPS, and BMC data from vmp_projects
"""
import logging
from typing import Dict, Any, Optional, Tuple
from src.mvp.adapters.database_adapter import MVPDatabaseAdapter

logger = logging.getLogger(__name__)


class ContextLoader:
    """Loads project context for solution critique"""
    
    def __init__(self):
        self.db_adapter = MVPDatabaseAdapter(use_service_role=True)
    
    @staticmethod
    def _primary_statement_to_string(primary_stmt: Any) -> str:
        """Convert primary_statement to string, handling both dict and string formats."""
        if isinstance(primary_stmt, dict):
            # Structured format - concatenate all components
            return " ".join([
                primary_stmt.get('our', ''),
                primary_stmt.get('help', ''),
                primary_stmt.get('who_want_to', ''),
                primary_stmt.get('by', ''),
                primary_stmt.get('and', ''),
                primary_stmt.get('unlike', '')
            ]).strip()
        elif isinstance(primary_stmt, str):
            # Legacy string format
            return primary_stmt
        return ''
    
    async def load_project_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Load all required context for solution critique
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Tuple of (context_dict, error_message)
            context_dict contains all loaded data if successful
            error_message is None if successful, error string otherwise
        """
        try:
            logger.info(f"📋 Loading context for project {project_id}")
            
            # Load project data
            project_data = self.db_adapter.get_project(project_id, tenant_id)
            if not project_data:
                return {}, "Project not found"
            
            # Load MVP data
            mvp_data = self.db_adapter.get_mvp_data(project_id, tenant_id)
            if not mvp_data:
                return {}, "MVP data not found. Please ensure VPS and BMC are generated."
            
            # Extract VPS (prefer v2, fallback to v1)
            vps_data = mvp_data.get('vps_v2')
            if not vps_data:
                vps_data = mvp_data.get('vps_v1')
            
            if not vps_data:
                return {}, "VPS not generated. Please generate VPS before running solution critique."
            
            # Handle VPS data format - can be list (multi-persona) or dict (legacy)
            # For multi-persona, vps_data is a list of VPS dicts - use first one for critique
            if isinstance(vps_data, list):
                if len(vps_data) == 0:
                    return {}, "VPS data is empty. Please regenerate VPS."
                # Use the first VPS for solution critique (primary persona)
                vps_data = vps_data[0]
                logger.info(f"   Using first VPS from multi-persona list for critique")
            
            # Ensure vps_data is a dict
            if not isinstance(vps_data, dict):
                return {}, "VPS data is corrupted. Please regenerate VPS."
            
            # Extract BMC
            bmc_data = mvp_data.get('bmc')
            if not bmc_data:
                return {}, "BMC not generated. Please complete BMC before running solution critique."
            
            # Ensure bmc_data is a dict
            if not isinstance(bmc_data, dict):
                return {}, "BMC data is corrupted. Please regenerate BMC."
            
            # Load VPC data (VPC 2.0 support) - CRITICAL: Handle multiple storage formats
            vpc_data_raw = project_data.get('vpc_data', {})
            vpc_v2_data = project_data.get('vpc_v2_data', {})
            
            logger.info(f"\n🔍 DEEP DEBUG: VPC Data Analysis")
            logger.info(f"   vpc_data type: {type(vpc_data_raw)}")
            logger.info(f"   vpc_data keys: {list(vpc_data_raw.keys()) if isinstance(vpc_data_raw, dict) else 'not a dict'}")
            logger.info(f"   vpc_data value preview: {str(vpc_data_raw)[:200] if vpc_data_raw else 'None'}")
            
            logger.info(f"\n🔍 DEEP DEBUG: VPC v2 Data Analysis")
            logger.info(f"   vpc_v2_data type: {type(vpc_v2_data)}")
            logger.info(f"   vpc_v2_data is None: {vpc_v2_data is None}")
            logger.info(f"   vpc_v2_data is empty dict: {vpc_v2_data == {}}")
            logger.info(f"   vpc_v2_data bool: {bool(vpc_v2_data)}")
            
            if isinstance(vpc_v2_data, dict):
                logger.info(f"   vpc_v2_data keys: {list(vpc_v2_data.keys())}")
                logger.info(f"   vpc_v2_data length: {len(vpc_v2_data)}")
                
                # Deep inspection of each key
                for key, value in vpc_v2_data.items():
                    logger.info(f"\n   vpc_v2_data['{key}']:")
                    logger.info(f"      Type: {type(value)}")
                    if isinstance(value, dict):
                        logger.info(f"      Keys: {list(value.keys())}")
                        # Check for value_map_selections
                        if 'value_map_selections' in value:
                            logger.info(f"      ✅ HAS value_map_selections!")
                            vm_sel = value['value_map_selections']
                            logger.info(f"      value_map_selections type: {type(vm_sel)}")
                            if isinstance(vm_sel, dict):
                                logger.info(f"      value_map_selections keys: {list(vm_sel.keys())}")
                                logger.info(f"      products_services count: {len(vm_sel.get('products_services', []))}")
                                logger.info(f"      pain_relievers count: {len(vm_sel.get('pain_relievers', []))}")
                                logger.info(f"      gain_creators count: {len(vm_sel.get('gain_creators', []))}")
                        else:
                            logger.info(f"      ❌ NO value_map_selections")
                    elif isinstance(value, (str, int, float, bool)):
                        logger.info(f"      Value: {value}")
                    else:
                        logger.info(f"      Value preview: {str(value)[:100]}")
            else:
                logger.info(f"   vpc_v2_data is not a dict, it's: {type(vpc_v2_data)}")
            
            # Ensure vpc_data is a dict (handle None, 0, or other non-dict values)
            if not isinstance(vpc_data_raw, dict):
                logger.warning(f"   VPC data is not a dict (type: {type(vpc_data_raw)}), using empty dict")
                vpc_data_raw = {}
            
            # CRITICAL: VPC 2.0 can be stored in multiple places - use same logic as get_project_detail
            vpc_data = vpc_data_raw
            
            # Strategy 1: Check vpc_v2_data first (dedicated VPC 2.0 column)
            if vpc_v2_data and isinstance(vpc_v2_data, dict) and vpc_v2_data:
                # Check if vpc_v2_data has customer_profile at root (single persona)
                if vpc_v2_data.get('customer_profile'):
                    logger.info(f"   ✅ Using vpc_v2_data (single persona at root)")
                    vpc_data = vpc_v2_data
                # Check if vpc_v2_data has persona keys (P1, P2, etc.) - multi-persona
                else:
                    persona_keys = [k for k in vpc_v2_data.keys() if k.startswith('P') and k[1:].isdigit()]
                    if persona_keys:
                        first_persona_key = persona_keys[0]
                        persona_vpc = vpc_v2_data.get(first_persona_key, {})
                        if isinstance(persona_vpc, dict) and persona_vpc.get('customer_profile'):
                            logger.info(f"   ✅ Using vpc_v2_data[{first_persona_key}] (multi-persona)")
                            vpc_data = persona_vpc
            # Strategy 2: Check if vpc_data has 'vpcs' key (nested multi-persona structure)
            elif vpc_data and 'vpcs' in vpc_data:
                logger.info(f"   🔍 Found 'vpcs' key in vpc_data, extracting first VPC")
                vpcs_dict = vpc_data.get('vpcs', {})
                if isinstance(vpcs_dict, dict) and vpcs_dict:
                    first_persona_id = list(vpcs_dict.keys())[0]
                    persona_vpc = vpcs_dict[first_persona_id]
                    if isinstance(persona_vpc, dict) and persona_vpc.get('customer_profile'):
                        logger.info(f"   ✅ Using VPC from vpcs['{first_persona_id}']")
                        vpc_data = persona_vpc
            # Strategy 3: Search for persona-specific VPC data directly in vpc_data keys
            elif vpc_data and not vpc_data.get('customer_profile'):
                logger.info(f"   🔍 Searching for persona-specific VPC in vpc_data keys")
                for key, value in vpc_data.items():
                    if isinstance(value, dict) and (value.get('customer_profile') or value.get('value_map_selections') or value.get('value_map')):
                        logger.info(f"   ✅ Found VPC data in key: {key}")
                        vpc_data = value
                        break
            
            # Validate VPC - check for VPC 2.0 completion
            # VPC 2.0 can have customer_profile at root or nested structure
            has_vpc_content = (
                vpc_data.get('customer_profile') or 
                vpc_data.get('jobs_to_be_done') or 
                vpc_data.get('pains') or 
                vpc_data.get('gains') or
                vpc_data.get('value_map') or
                vpc_data.get('value_map_selections') or
                vpc_data.get('status') in ['customer_profile_completed', 'value_map_completed', 'completed'] or
                len(vpc_data) > 0  # If vpc_data has any content, consider it valid
            )
            
            # Log VPC status for debugging
            logger.info(f"   VPC validation: has_content={has_vpc_content}, status={vpc_data.get('status', 'N/A')}")
            
            if not has_vpc_content:
                logger.warning("   VPC appears empty, but proceeding with empty VPC data")
                # Don't fail - proceed with empty VPC
                vpc_data = {}
            
            # Extract metadata
            geography = self._extract_geography(vps_data, bmc_data, project_data)
            industry = self._extract_industry(vps_data, bmc_data)
            solution_description = self._extract_solution_description(vps_data)
            
            # ========== DETAILED CONTEXT LOGGING ==========
            logger.info("\n" + "="*80)
            logger.info("📊 DETAILED CONTEXT LOADING REPORT")
            logger.info("="*80)
            
            # VPS Logging
            logger.info("\n🎯 VPS (Value Proposition Statement) Context:")
            logger.info(f"   Version: {'v2' if mvp_data.get('vps_v2') else 'v1'}")
            logger.info(f"   Has primary_statement: {bool(vps_data.get('primary_statement'))}")
            logger.info(f"   Has extended_statement: {bool(vps_data.get('extended_statement'))}")
            logger.info(f"   Has key_differentiators: {bool(vps_data.get('key_differentiators'))} ({len(vps_data.get('key_differentiators', []))} items)")
            if vps_data.get('primary_statement'):
                primary_text = self._primary_statement_to_string(vps_data.get('primary_statement'))
                logger.info(f"   Primary statement length: {len(primary_text)} chars")
                logger.info(f"   Primary preview: {primary_text[:100]}...")
            if vps_data.get('extended_statement'):
                logger.info(f"   Extended statement length: {len(vps_data.get('extended_statement', ''))} chars")
            logger.info(f"   ✅ Solution description extracted: {len(solution_description)} chars")
            logger.info(f"   Solution preview: {solution_description[:120]}...")
            
            # BMC Logging
            logger.info("\n📦 BMC (Business Model Canvas) Context:")
            logger.info(f"   Total blocks present: {len(bmc_data.keys())}")
            bmc_blocks = [
                'customer_segments', 'value_propositions', 'channels',
                'customer_relationships', 'revenue_streams', 'key_resources',
                'key_activities', 'key_partnerships', 'cost_structure'
            ]
            for block in bmc_blocks:
                block_data = bmc_data.get(block, [])
                if isinstance(block_data, list):
                    count = len(block_data)
                    status = "✅" if count > 0 else "⚠️"
                    logger.info(f"   {status} {block}: {count} items")
                elif isinstance(block_data, dict):
                    count = len(block_data.keys())
                    status = "✅" if count > 0 else "⚠️"
                    logger.info(f"   {status} {block}: {count} keys")
                else:
                    logger.info(f"   ⚠️  {block}: unexpected type {type(block_data)}")
            
            # Build context dictionary
            # Normalize VPC data structure for consistent access
            # Ensure None values are converted to empty dicts
            
            # CRITICAL: Extract value_map from multiple possible locations
            value_map_data = {}
            
            logger.info(f"\n🔍 DEEP DEBUG: Value Map Extraction Process")
            
            # PRIORITY 1: Check vpc_v2_data first (this is where VPC v2 service saves it!)
            logger.info(f"   PRIORITY 1: Checking vpc_v2_data...")
            logger.info(f"      vpc_v2_data is dict: {isinstance(vpc_v2_data, dict)}")
            logger.info(f"      vpc_v2_data is truthy: {bool(vpc_v2_data)}")
            
            if isinstance(vpc_v2_data, dict) and vpc_v2_data:
                logger.info(f"      vpc_v2_data has content, checking structure...")
                
                # Check for persona keys (P1, P2, etc.)
                persona_keys = [k for k in vpc_v2_data.keys() if k.startswith('P') and k[1:].isdigit()]
                logger.info(f"      Found persona keys: {persona_keys}")
                
                # For multi-persona, check first persona
                if persona_keys:
                    first_persona_key = persona_keys[0]
                    logger.info(f"      Multi-persona detected, checking {first_persona_key}...")
                    persona_vpc = vpc_v2_data.get(first_persona_key, {})
                    logger.info(f"      persona_vpc type: {type(persona_vpc)}")
                    logger.info(f"      persona_vpc keys: {list(persona_vpc.keys()) if isinstance(persona_vpc, dict) else 'not a dict'}")
                    
                    if isinstance(persona_vpc, dict) and persona_vpc.get('value_map_selections'):
                        value_map_data = persona_vpc.get('value_map_selections')
                        logger.info(f"      ✅ FOUND value_map_selections in vpc_v2_data[{first_persona_key}]")
                        logger.info(f"      value_map_data keys: {list(value_map_data.keys()) if isinstance(value_map_data, dict) else 'not a dict'}")
                    else:
                        logger.info(f"      ❌ NO value_map_selections in vpc_v2_data[{first_persona_key}]")
                # For single persona, check directly
                else:
                    logger.info(f"      Single persona detected, checking root level...")
                    logger.info(f"      vpc_v2_data has 'value_map_selections': {'value_map_selections' in vpc_v2_data}")
                    
                    if vpc_v2_data.get('value_map_selections'):
                        value_map_data = vpc_v2_data.get('value_map_selections')
                        logger.info(f"      ✅ FOUND value_map_selections in vpc_v2_data (single persona)")
                        logger.info(f"      value_map_data keys: {list(value_map_data.keys()) if isinstance(value_map_data, dict) else 'not a dict'}")
                    else:
                        logger.info(f"      ❌ NO value_map_selections in vpc_v2_data root")
            else:
                logger.info(f"      ❌ vpc_v2_data is empty or not a dict, skipping")
            
            # PRIORITY 2: Check for value_map_selections in vpc_data (VPC 2.0 format after user selection)
            if not value_map_data and vpc_data.get('value_map_selections'):
                value_map_data = vpc_data.get('value_map_selections')
                logger.info(f"   ✅ Found value_map_selections in vpc_data")
            
            # PRIORITY 3: Check for value_map (legacy format or after save_value_map_selections)
            if not value_map_data and vpc_data.get('value_map'):
                value_map_data = vpc_data.get('value_map')
                logger.info(f"   ✅ Found value_map in vpc_data")
            
            # PRIORITY 4: Check inside customer_profile (some storage formats nest it there)
            if not value_map_data and isinstance(vpc_data.get('customer_profile'), dict):
                cp = vpc_data.get('customer_profile')
                if cp.get('value_map_selections'):
                    value_map_data = cp.get('value_map_selections')
                    logger.info(f"   ✅ Found value_map_selections inside customer_profile")
                elif cp.get('value_map'):
                    value_map_data = cp.get('value_map')
                    logger.info(f"   ✅ Found value_map inside customer_profile")
            
            if not value_map_data:
                logger.warning(f"   ⚠️  No value_map found in any expected location")
                logger.warning(f"   Checked: vpc_v2_data, vpc_data.value_map_selections, vpc_data.value_map, vpc_data.customer_profile")
            
            normalized_vpc = {
                'customer_profile': vpc_data.get('customer_profile') or {},
                'value_map': value_map_data
            }
            
            # VPC Logging
            logger.info("\n🎨 VPC (Value Proposition Canvas) Context:")
            logger.info(f"   VPC data type: {type(vpc_data)}")
            logger.info(f"   VPC keys: {list(vpc_data.keys()) if isinstance(vpc_data, dict) else 'not a dict'}")
            
            # Customer Profile
            customer_profile = normalized_vpc.get('customer_profile', {})
            logger.info(f"   Customer Profile:")
            if isinstance(customer_profile, dict):
                jobs = customer_profile.get('jobs_to_be_done', [])
                pains = customer_profile.get('pains', [])
                gains = customer_profile.get('gains', [])
                logger.info(f"      {'✅' if jobs else '⚠️'} jobs_to_be_done: {len(jobs) if isinstance(jobs, list) else 'not a list'}")
                logger.info(f"      {'✅' if pains else '⚠️'} pains: {len(pains) if isinstance(pains, list) else 'not a list'}")
                logger.info(f"      {'✅' if gains else '⚠️'} gains: {len(gains) if isinstance(gains, list) else 'not a list'}")
            else:
                logger.info(f"      ⚠️  Customer profile is not a dict: {type(customer_profile)}")
            
            # Value Map
            value_map = normalized_vpc.get('value_map', {})
            logger.info(f"   Value Map:")
            if isinstance(value_map, dict):
                products = value_map.get('products_services', [])
                pain_relievers = value_map.get('pain_relievers', [])
                gain_creators = value_map.get('gain_creators', [])
                logger.info(f"      {'✅' if products else '⚠️'} products_services: {len(products) if isinstance(products, list) else 'not a list'}")
                logger.info(f"      {'✅' if pain_relievers else '⚠️'} pain_relievers: {len(pain_relievers) if isinstance(pain_relievers, list) else 'not a list'}")
                logger.info(f"      {'✅' if gain_creators else '⚠️'} gain_creators: {len(gain_creators) if isinstance(gain_creators, list) else 'not a list'}")
            else:
                logger.info(f"      ⚠️  Value map is not a dict: {type(value_map)}")
            
            # Context Summary
            logger.info("\n📋 Context Summary:")
            logger.info(f"   Geography: {geography}")
            logger.info(f"   Industry: {industry}")
            logger.info(f"   Solution description: {'✅ Extracted' if solution_description != 'No solution description available' else '❌ Missing'}")
            logger.info(f"   BMC completeness: {len([b for b in bmc_blocks if bmc_data.get(b)])}/{len(bmc_blocks)} blocks")
            logger.info(f"   VPC completeness: {'✅ Complete' if customer_profile and value_map else '⚠️ Partial/Empty'}")
            logger.info("="*80 + "\n")
            
            context = {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'geography': geography,
                'industry': industry,
                'solution_description': solution_description,
                'vpc_data': normalized_vpc,
                'vps_data': vps_data,
                'bmc_data': bmc_data,
                'status': 'context_loaded'
            }
            
            logger.info(f"✅ Context loaded successfully for project {project_id}")
            
            return context, None
            
        except Exception as e:
            logger.error(f"❌ Failed to load context: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            logger.error(f"   Exception args: {e.args if hasattr(e, 'args') else 'N/A'}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return {}, f"Failed to load context: {str(e)}"
    
    def _extract_geography(
        self, 
        vps_data: Dict, 
        bmc_data: Dict,
        project_data: Dict
    ) -> str:
        """Extract geography from VPS, BMC, or project metadata"""
        # Try VPS metadata
        if isinstance(vps_data, dict):
            if 'metadata' in vps_data and 'geography' in vps_data['metadata']:
                return vps_data['metadata']['geography']
            
            # Try VPS primary_statement (v2) or statement (v1)
            primary_stmt = vps_data.get('primary_statement') or vps_data.get('statement', '')
            statement = self._primary_statement_to_string(primary_stmt)
            if statement:
                # Look for geography patterns in statement
                import re
                # Pattern: "in [Country/Region]" or "from [Country/Region]" or "across [Country/Region]"
                geo_pattern = r'\b(?:in|from|across)\s+(?:rural\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
                matches = re.findall(geo_pattern, statement)
                if matches:
                    # Return the first match (e.g., "Kenya", "East Africa")
                    return matches[0]
            
            # Try VPS components
            if 'components' in vps_data:
                components = vps_data['components']
                if isinstance(components, dict) and 'target_customer' in components:
                    target_customer = components['target_customer']
                    # Look for geography keywords
                    if isinstance(target_customer, str):
                        for keyword in ['in ', 'from ', 'across ']:
                            if keyword in target_customer.lower():
                                parts = target_customer.split(keyword)
                                if len(parts) > 1:
                                    potential_geo = parts[1].split()[0].strip('.,;')
                                    if len(potential_geo) > 2:
                                        return potential_geo
        
        # Try BMC customer segments
        if isinstance(bmc_data, dict):
            customer_segments = bmc_data.get('customer_segments', [])
            
            # Handle both list and dict formats
            segments_to_check = []
            if isinstance(customer_segments, list):
                segments_to_check = customer_segments
            elif isinstance(customer_segments, dict):
                segments_to_check = list(customer_segments.values())
            
            for segment in segments_to_check:
                if isinstance(segment, dict):
                    # Check for geography field
                    if 'geography' in segment:
                        return segment['geography']
                    # Check in description
                    if 'description' in segment:
                        desc = segment['description']
                        if isinstance(desc, str):
                            for keyword in ['in ', 'from ', 'across ']:
                                if keyword in desc.lower():
                                    parts = desc.split(keyword)
                                    if len(parts) > 1:
                                        potential_geo = parts[1].split()[0].strip('.,;')
                                        if len(potential_geo) > 2:
                                            return potential_geo
        
        # Try project-level metadata
        if isinstance(project_data, dict) and 'settings' in project_data:
            settings = project_data['settings']
            if isinstance(settings, dict) and 'geography' in settings:
                return settings['geography']
        
        return "Not specified"
    
    def _extract_industry(self, vps_data: Dict, bmc_data: Dict) -> str:
        """Extract industry from VPS or BMC"""
        # Try VPS metadata
        if isinstance(vps_data, dict):
            if 'metadata' in vps_data and 'industry' in vps_data['metadata']:
                return vps_data['metadata']['industry']
            
            # Try VPS statement analysis - look for industry keywords
            # Check both primary_statement (v2) and statement (v1)
            primary_stmt = vps_data.get('primary_statement') or vps_data.get('statement', '')
            statement = self._primary_statement_to_string(primary_stmt)
            extended = vps_data.get('extended_statement', '')
            full_statement = f"{statement} {extended}".lower() if statement else ""
            
            if full_statement:
                # Common industry patterns (ordered by specificity)
                industry_keywords = {
                    'Agriculture': ['farm', 'farmer', 'crop', 'agricultural', 'livestock', 'planting', 'harvesting', 'weather information services'],
                    'Healthcare': ['health', 'medical', 'clinic', 'hospital', 'patient', 'doctor', 'treatment'],
                    'Fintech': ['payment', 'financial', 'banking', 'money', 'credit', 'loan', 'transaction'],
                    'Education': ['education', 'learning', 'school', 'student', 'training', 'course', 'teaching'],
                    'Retail': ['retail', 'shop', 'store', 'merchant', 'seller', 'e-commerce'],
                    'Logistics': ['delivery', 'transport', 'logistics', 'shipping', 'supply chain'],
                    'Technology': ['software', 'app', 'platform', 'digital', 'tech', 'SaaS']
                }
                
                # Count keyword matches for each industry
                industry_scores = {}
                for industry, keywords in industry_keywords.items():
                    score = sum(1 for keyword in keywords if keyword in full_statement)
                    if score > 0:
                        industry_scores[industry] = score
                
                # Return industry with highest score
                if industry_scores:
                    return max(industry_scores, key=industry_scores.get)
        
        # Try BMC value propositions
        if isinstance(bmc_data, dict):
            value_props = bmc_data.get('value_propositions', [])
            # Handle both list and dict formats
            if isinstance(value_props, list) and len(value_props) > 0:
                first_vp = value_props[0]
                if isinstance(first_vp, dict) and 'title' in first_vp:
                    # Industry might be in the value prop title
                    return "General Business"
            elif isinstance(value_props, dict) and len(value_props) > 0:
                # If it's a dict, get first value
                first_key = list(value_props.keys())[0]
                first_vp = value_props[first_key]
                if isinstance(first_vp, dict) and 'title' in first_vp:
                    return "General Business"
        
        return "Not specified"
    
    def _extract_solution_description(self, vps_data: Dict) -> str:
        """Extract solution description from VPS"""
        if not isinstance(vps_data, dict):
            return 'No solution description available'
        
        # Try VPS v2 structure first (primary_statement + extended_statement)
        primary_stmt = vps_data.get('primary_statement', '')
        primary = self._primary_statement_to_string(primary_stmt)
        extended = vps_data.get('extended_statement', '')
        
        if primary:
            # Combine primary and extended for full context
            if extended and isinstance(extended, str):
                return f"{primary}\n\n{extended}"
            return primary
        
        # Fallback: Try VPS v1 structure (statement)
        statement = vps_data.get('statement', '')
        if statement and isinstance(statement, str):
            return statement
        
        # Fallback: Try components if statement not available
        components = vps_data.get('components', {})
        if isinstance(components, dict):
            solution = components.get('solution', '')
            if solution and isinstance(solution, str):
                return solution
        
        return 'No solution description available'
