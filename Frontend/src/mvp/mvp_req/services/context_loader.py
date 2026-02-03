"""
Context Loader Service for MVP Requirements Generator

Loads and validates project artifacts required for PRD generation.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.mvp.adapters.database_adapter import MVPDatabaseAdapter
from ..models.state_models import ContextPack, ArtifactData
from ..models.response_models import MissingArtifactDetail

logger = logging.getLogger(__name__)


# Required artifacts for AMRG eligibility
REQUIRED_ARTIFACTS = {
    "vps_v1": {
        "description": "Value Proposition Statement v1",
        "how_to_generate": "Generate VPS v1 from the MVP Development Suite"
    },
    "bmc_v1": {
        "description": "Business Model Canvas v1 (original)",
        "how_to_generate": "Generate BMC from the MVP Development Suite after VPS v1"
    },
    "solution_critique": {
        "description": "Solution Critique analysis",
        "how_to_generate": "Run Solution Critique after completing BMC v1"
    },
    "vps_v2": {
        "description": "Value Proposition Statement v2 (refined)",
        "how_to_generate": "Generate VPS v2 after Solution Critique"
    },
    "bmc_v2": {
        "description": "Business Model Canvas v2 (refined)",
        "how_to_generate": "Generate BMC v2 after VPS v2"
    }
}

# Optional artifacts (loaded if available)
OPTIONAL_ARTIFACTS = {
    "vpc_v2": {
        "description": "Value Proposition Canvas v2 (Customer Profile + Value Map)",
        "how_to_generate": "Complete VPC v2 after Market Research Analysis"
    }
}


class ContextLoaderService:
    """
    Service for loading and validating project context for AMRG.
    
    Handles:
    - Eligibility validation (all required artifacts present)
    - Context pack assembly from project data
    - Metadata extraction (industry, geography, etc.)
    """
    
    def __init__(self, use_service_role: bool = True):
        """Initialize with database adapter."""
        self.db_adapter = MVPDatabaseAdapter(use_service_role=use_service_role)
    
    def validate_eligibility(
        self,
        project_id: str,
        tenant_id: str
    ) -> Tuple[bool, List[str], List[MissingArtifactDetail]]:
        """
        Validate that project has all required artifacts for AMRG.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Tuple of (is_eligible, missing_artifact_names, missing_artifact_details)
        """
        logger.info(f"🔍 Validating eligibility for project {project_id}")
        
        missing_names = []
        missing_details = []
        
        try:
            # Get project data
            project_data = self.db_adapter.get_project(project_id, tenant_id)
            if not project_data:
                logger.error(f"Project {project_id} not found")
                return False, ["project"], [MissingArtifactDetail(
                    artifact_name="project",
                    description="Project not found",
                    how_to_generate="Create a VMP project first"
                )]
            
            # Get MVP data
            mvp_data = self.db_adapter.get_mvp_data(project_id, tenant_id)
            if not mvp_data:
                mvp_data = {}
            
            # Check each required artifact
            for artifact_key, artifact_info in REQUIRED_ARTIFACTS.items():
                has_artifact = self._check_artifact_exists(
                    artifact_key, mvp_data, project_data
                )
                
                if not has_artifact:
                    missing_names.append(artifact_key)
                    missing_details.append(MissingArtifactDetail(
                        artifact_name=artifact_key,
                        description=artifact_info["description"],
                        how_to_generate=artifact_info["how_to_generate"]
                    ))
                    logger.warning(f"   ❌ Missing: {artifact_key}")
                else:
                    logger.info(f"   ✅ Found: {artifact_key}")
            
            is_eligible = len(missing_names) == 0
            
            if is_eligible:
                logger.info(f"✅ Project {project_id} is eligible for AMRG")
            else:
                logger.warning(f"❌ Project {project_id} missing {len(missing_names)} artifacts")
            
            return is_eligible, missing_names, missing_details
            
        except Exception as e:
            logger.error(f"Error validating eligibility: {e}")
            return False, ["error"], [MissingArtifactDetail(
                artifact_name="error",
                description=f"Error checking eligibility: {str(e)}",
                how_to_generate="Please try again or contact support"
            )]
    
    def _check_artifact_exists(
        self,
        artifact_key: str,
        mvp_data: Dict[str, Any],
        project_data: Dict[str, Any]
    ) -> bool:
        """Check if a specific artifact exists and has content."""
        
        if artifact_key == "vps_v1":
            vps_v1 = mvp_data.get("vps_v1")
            return vps_v1 is not None and len(vps_v1) > 0 if isinstance(vps_v1, list) else vps_v1 is not None
        
        elif artifact_key == "vps_v2":
            vps_v2 = mvp_data.get("vps_v2")
            return vps_v2 is not None and len(vps_v2) > 0 if isinstance(vps_v2, list) else vps_v2 is not None
        
        elif artifact_key == "bmc_v1":
            bmc = mvp_data.get("bmc")
            return bmc is not None and isinstance(bmc, dict) and len(bmc) > 0
        
        elif artifact_key == "bmc_v2":
            bmc_v2 = mvp_data.get("bmc_v2")
            return bmc_v2 is not None and isinstance(bmc_v2, dict) and len(bmc_v2) > 0
        
        elif artifact_key == "solution_critique":
            critique_data = project_data.get("soln_critique_data")
            return (
                critique_data is not None and 
                isinstance(critique_data, dict) and 
                critique_data.get("status") == "completed"
            )
        
        return False
    
    def load_context_pack(
        self,
        project_id: str,
        tenant_id: str
    ) -> Tuple[Optional[ContextPack], Optional[str]]:
        """
        Load complete context pack from project.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            
        Returns:
            Tuple of (ContextPack, error_message)
            Returns (None, error) if loading fails
        """
        logger.info(f"📦 Loading context pack for project {project_id}")
        
        try:
            # Get project and MVP data
            project_data = self.db_adapter.get_project(project_id, tenant_id)
            if not project_data:
                return None, f"Project {project_id} not found"
            
            mvp_data = self.db_adapter.get_mvp_data(project_id, tenant_id)
            if not mvp_data:
                mvp_data = {}
            
            # Load required artifacts
            artifacts = {}
            
            # VPS v1 (handle array format)
            vps_v1 = mvp_data.get("vps_v1")
            if isinstance(vps_v1, list) and len(vps_v1) > 0:
                vps_v1 = vps_v1[0]  # Use first persona
            artifacts["vps_v1"] = self._wrap_artifact(vps_v1, "vps_v1")
            
            # VPS v2 (handle array format)
            vps_v2 = mvp_data.get("vps_v2")
            if isinstance(vps_v2, list) and len(vps_v2) > 0:
                vps_v2 = vps_v2[0]  # Use first persona
            artifacts["vps_v2"] = self._wrap_artifact(vps_v2, "vps_v2")
            
            # BMC v1
            artifacts["bmc_v1"] = self._wrap_artifact(
                mvp_data.get("bmc"), "bmc_v1"
            )
            
            # BMC v2
            artifacts["bmc_v2"] = self._wrap_artifact(
                mvp_data.get("bmc_v2"), "bmc_v2"
            )
            
            # Solution Critique
            artifacts["solution_critique"] = self._wrap_artifact(
                project_data.get("soln_critique_data"), "solution_critique"
            )
            
            # Load optional artifacts
            optional_artifacts = {}
            
            # VPC v2 (optional - use if exists)
            vpc_v2_data = self._extract_vpc_v2(project_data)
            if vpc_v2_data:
                optional_artifacts["vpc_v2"] = self._wrap_artifact(vpc_v2_data, "vpc_v2")
                logger.info("   ✅ VPC v2 found and loaded (optional)")
            else:
                logger.info("   ℹ️  VPC v2 not available (optional, skipping)")
            
            # Extract metadata
            metadata = self._extract_metadata(project_data, artifacts)
            
            # Build context pack
            context_pack: ContextPack = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "artifacts": artifacts,
                "optional_artifacts": optional_artifacts,
                "metadata": metadata
            }
            
            logger.info(f"✅ Context pack loaded successfully")
            logger.info(f"   Required artifacts: {len(artifacts)}")
            logger.info(f"   Optional artifacts: {len(optional_artifacts)}")
            
            return context_pack, None
            
        except Exception as e:
            logger.error(f"Error loading context pack: {e}")
            return None, f"Error loading context: {str(e)}"
    
    def _wrap_artifact(
        self,
        data: Any,
        artifact_name: str
    ) -> ArtifactData:
        """Wrap artifact data with metadata."""
        if data is None:
            return {"data": {}, "version": "unknown", "generated_at": None}
        
        # Extract version and timestamp if available
        version = "v1"
        generated_at = None
        
        if isinstance(data, dict):
            # Check for version in metadata
            if "generation_metadata" in data:
                generated_at = data["generation_metadata"].get("generated_at")
            elif "completed_at" in data:
                generated_at = data.get("completed_at")
            
            # Determine version from artifact name
            if "_v2" in artifact_name or artifact_name.endswith("_v2"):
                version = "v2"
        
        return {
            "data": data,
            "version": version,
            "generated_at": generated_at
        }
    
    def _extract_vpc_v2(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract VPC v2 data from project (handles multiple storage formats).
        
        VPC v2 contains:
        - customer_profile: Jobs to be Done, Pains, Gains
        - value_map_selections: Products & Services, Pain Relievers, Gain Creators
        
        VPC v2 can be stored in:
        - vpc_v2_data column directly
        - vpc_data with nested structure
        - vpc_data with 'vpcs' key for multi-persona
        """
        logger.info("   🔍 Extracting VPC v2 (optional context)...")
        
        vpc_v2_data = project_data.get("vpc_v2_data")
        vpc_data_raw = project_data.get("vpc_data", {})
        
        # Ensure vpc_data_raw is a dict
        if not isinstance(vpc_data_raw, dict):
            vpc_data_raw = {}
        
        vpc_data = None
        
        # Strategy 1: Check vpc_v2_data first (dedicated VPC 2.0 column)
        if vpc_v2_data and isinstance(vpc_v2_data, dict) and vpc_v2_data:
            logger.info(f"      Found vpc_v2_data with keys: {list(vpc_v2_data.keys())}")
            
            # Check if vpc_v2_data has customer_profile at root (single persona)
            if vpc_v2_data.get('customer_profile') or vpc_v2_data.get('value_map_selections'):
                logger.info(f"      ✅ Using vpc_v2_data (single persona at root)")
                vpc_data = vpc_v2_data
            else:
                # Check if vpc_v2_data has persona keys (P1, P2, etc.) - multi-persona
                persona_keys = [k for k in vpc_v2_data.keys() if k.startswith('P') and k[1:].isdigit()]
                if persona_keys:
                    first_persona_key = persona_keys[0]
                    persona_vpc = vpc_v2_data.get(first_persona_key, {})
                    if isinstance(persona_vpc, dict) and (persona_vpc.get('customer_profile') or persona_vpc.get('value_map_selections')):
                        logger.info(f"      ✅ Using vpc_v2_data[{first_persona_key}] (multi-persona)")
                        vpc_data = persona_vpc
        
        # Strategy 2: Check if vpc_data has 'vpcs' key (nested multi-persona structure)
        if not vpc_data and vpc_data_raw and 'vpcs' in vpc_data_raw:
            logger.info(f"      Found 'vpcs' key in vpc_data, extracting first VPC")
            vpcs_dict = vpc_data_raw.get('vpcs', {})
            if isinstance(vpcs_dict, dict) and vpcs_dict:
                first_persona_id = list(vpcs_dict.keys())[0]
                persona_vpc = vpcs_dict[first_persona_id]
                if isinstance(persona_vpc, dict) and (persona_vpc.get('customer_profile') or persona_vpc.get('value_map_selections')):
                    logger.info(f"      ✅ Using VPC from vpcs['{first_persona_id}']")
                    vpc_data = persona_vpc
        
        # Strategy 3: Check if vpc_data itself has VPC 2.0 content
        if not vpc_data and vpc_data_raw:
            # Check for VPC 2.0 completion markers
            if vpc_data_raw.get("status") in ["customer_profile_completed", "value_map_completed", "completed"]:
                logger.info(f"      ✅ Using vpc_data (has completion status)")
                vpc_data = vpc_data_raw
            # Check for customer_profile or value_map_selections at root
            elif vpc_data_raw.get('customer_profile') or vpc_data_raw.get('value_map_selections'):
                logger.info(f"      ✅ Using vpc_data (has customer_profile/value_map at root)")
                vpc_data = vpc_data_raw
            # Search for persona-specific VPC data in vpc_data keys
            elif not vpc_data_raw.get('customer_profile'):
                for key, value in vpc_data_raw.items():
                    if isinstance(value, dict) and (value.get('customer_profile') or value.get('value_map_selections') or value.get('value_map')):
                        logger.info(f"      ✅ Found VPC data in key: {key}")
                        vpc_data = value
                        break
        
        # Validate VPC has meaningful content
        if vpc_data:
            has_customer_profile = bool(vpc_data.get('customer_profile'))
            has_value_map = bool(vpc_data.get('value_map_selections') or vpc_data.get('value_map'))
            has_jobs = bool(vpc_data.get('jobs_to_be_done'))
            has_pains = bool(vpc_data.get('pains'))
            has_gains = bool(vpc_data.get('gains'))
            
            has_content = has_customer_profile or has_value_map or has_jobs or has_pains or has_gains
            
            if has_content:
                logger.info(f"      VPC v2 content: customer_profile={has_customer_profile}, value_map={has_value_map}")
                return vpc_data
            else:
                logger.info(f"      VPC v2 found but appears empty")
                return None
        
        logger.info(f"      VPC v2 not found in project")
        return None
    
    def _extract_metadata(
        self,
        project_data: Dict[str, Any],
        artifacts: Dict[str, ArtifactData]
    ) -> Dict[str, Any]:
        """Extract project metadata for context pack."""
        
        # Basic project info
        metadata = {
            "project_title": project_data.get("name", "Untitled Project"),
            "project_description": project_data.get("description", ""),
            "industry": None,
            "geography": None
        }
        
        # Try to extract industry from various sources
        # 1. From VPS data
        vps_v2_data = artifacts.get("vps_v2", {}).get("data", {})
        if isinstance(vps_v2_data, dict):
            metadata["industry"] = vps_v2_data.get("industry")
            metadata["geography"] = vps_v2_data.get("geography")
        
        # 2. From BMC data
        if not metadata["industry"]:
            bmc_data = artifacts.get("bmc_v2", {}).get("data", {})
            if isinstance(bmc_data, dict):
                # Check customer_segments for industry hints
                segments = bmc_data.get("customer_segments", [])
                if segments and isinstance(segments, list) and len(segments) > 0:
                    first_segment = segments[0]
                    if isinstance(first_segment, dict):
                        metadata["industry"] = first_segment.get("industry")
        
        # 3. From solution critique
        if not metadata["geography"]:
            critique_data = artifacts.get("solution_critique", {}).get("data", {})
            if isinstance(critique_data, dict):
                metadata["geography"] = critique_data.get("geography")
        
        logger.info(f"   Metadata: industry={metadata['industry']}, geography={metadata['geography']}")
        
        return metadata
