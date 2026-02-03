"""
Unit Tests for AMRG Context Loader

Run with: pytest src/mvp/mvp_req/tests/unit_context_loader.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestContextLoaderEligibility:
    """Tests for context loader eligibility validation."""
    
    def test_required_artifacts_defined(self):
        """Test that required artifacts are properly defined."""
        from ..services.context_loader import REQUIRED_ARTIFACTS, OPTIONAL_ARTIFACTS
        
        required_keys = ["vps_v1", "bmc_v1", "solution_critique", "vps_v2", "bmc_v2"]
        
        for key in required_keys:
            assert key in REQUIRED_ARTIFACTS, f"Missing required artifact: {key}"
            assert "description" in REQUIRED_ARTIFACTS[key]
            assert "how_to_generate" in REQUIRED_ARTIFACTS[key]
        
        # VPC v2 should be optional
        assert "vpc_v2" in OPTIONAL_ARTIFACTS
    
    def test_validate_eligibility_missing_project(self):
        """Test eligibility fails when project not found."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            service.db_adapter = Mock()
            service.db_adapter.get_project.return_value = None
            
            is_eligible, missing_names, missing_details = service.validate_eligibility(
                "fake-project-id", "fake-tenant-id"
            )
            
            assert is_eligible == False
            assert "project" in missing_names
    
    def test_validate_eligibility_missing_vps_v1(self):
        """Test eligibility fails when VPS v1 is missing."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            service.db_adapter = Mock()
            
            # Project exists but no MVP data
            service.db_adapter.get_project.return_value = {"id": "test", "name": "Test"}
            service.db_adapter.get_mvp_data.return_value = {}
            
            is_eligible, missing_names, missing_details = service.validate_eligibility(
                "fake-project-id", "fake-tenant-id"
            )
            
            assert is_eligible == False
            assert "vps_v1" in missing_names
    
    def test_validate_eligibility_all_artifacts_present(self):
        """Test eligibility passes when all required artifacts are present."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            service.db_adapter = Mock()
            
            # Project with all required artifacts
            service.db_adapter.get_project.return_value = {
                "id": "test",
                "name": "Test Project",
                "soln_critique_data": {"status": "completed", "critiques": []}
            }
            service.db_adapter.get_mvp_data.return_value = {
                "vps_v1": [{"problem_statement": "Test"}],
                "vps_v2": [{"problem_statement": "Test v2"}],
                "bmc": {"customer_segments": []},
                "bmc_v2": {"customer_segments": []}
            }
            
            is_eligible, missing_names, missing_details = service.validate_eligibility(
                "fake-project-id", "fake-tenant-id"
            )
            
            assert is_eligible == True
            assert len(missing_names) == 0


class TestContextLoaderVPCExtraction:
    """Tests for VPC v2 extraction."""
    
    def test_extract_vpc_v2_from_vpc_v2_data(self):
        """Test VPC v2 extraction from vpc_v2_data column."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            
            project_data = {
                "vpc_v2_data": {
                    "customer_profile": {"jobs": [], "pains": [], "gains": []},
                    "value_map_selections": {"products": [], "pain_relievers": [], "gain_creators": []}
                }
            }
            
            vpc_data = service._extract_vpc_v2(project_data)
            
            assert vpc_data is not None
            assert "customer_profile" in vpc_data
    
    def test_extract_vpc_v2_multi_persona(self):
        """Test VPC v2 extraction from multi-persona format."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            
            project_data = {
                "vpc_v2_data": {
                    "P1": {
                        "customer_profile": {"jobs": ["Job 1"]},
                        "value_map_selections": {"products": ["Product 1"]}
                    },
                    "P2": {
                        "customer_profile": {"jobs": ["Job 2"]}
                    }
                }
            }
            
            vpc_data = service._extract_vpc_v2(project_data)
            
            assert vpc_data is not None
            assert "customer_profile" in vpc_data
    
    def test_extract_vpc_v2_empty(self):
        """Test VPC v2 returns None when not present."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            
            project_data = {
                "vpc_data": {},
                "vpc_v2_data": {}
            }
            
            vpc_data = service._extract_vpc_v2(project_data)
            
            assert vpc_data is None


class TestContextPackAssembly:
    """Tests for context pack assembly."""
    
    def test_context_pack_structure(self):
        """Test context pack has correct structure."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            service.db_adapter = Mock()
            
            # Mock full project data
            service.db_adapter.get_project.return_value = {
                "id": "test-id",
                "name": "Test Project",
                "description": "Test description",
                "soln_critique_data": {"status": "completed"}
            }
            service.db_adapter.get_mvp_data.return_value = {
                "vps_v1": [{"problem": "test"}],
                "vps_v2": [{"problem": "test v2"}],
                "bmc": {"segments": []},
                "bmc_v2": {"segments": []}
            }
            
            context_pack, error = service.load_context_pack("test-id", "test-tenant")
            
            assert error is None
            assert context_pack is not None
            assert "project_id" in context_pack
            assert "tenant_id" in context_pack
            assert "artifacts" in context_pack
            assert "optional_artifacts" in context_pack
            assert "metadata" in context_pack
    
    def test_artifact_wrapping(self):
        """Test artifacts are properly wrapped with metadata."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            
            data = {"test_key": "test_value"}
            wrapped = service._wrap_artifact(data, "test_artifact")
            
            assert "data" in wrapped
            assert "version" in wrapped
            assert "generated_at" in wrapped
            assert wrapped["data"] == data
    
    def test_wrap_none_artifact(self):
        """Test wrapping None artifact returns empty structure."""
        from ..services.context_loader import ContextLoaderService
        
        with patch.object(ContextLoaderService, '__init__', lambda x, **kwargs: None):
            service = ContextLoaderService()
            
            wrapped = service._wrap_artifact(None, "test_artifact")
            
            assert wrapped["data"] == {}
            assert wrapped["version"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
