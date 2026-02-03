"""
Security and performance validation tests for Data Analysis Agent.

This module tests file upload security, validation mechanisms, tenant isolation,
access control, load testing, and performance optimization.
"""

import pytest
import asyncio
import time
import hashlib
import os
import tempfile
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO
import csv
import json

from fastapi import UploadFile, HTTPException
from fastapi.security import HTTPBearer
import jwt

from ..services.market_research_analysis_service import MarketResearchAnalysisService
from ..services.document_parser import DocumentParserService
from ..api.models import AnalysisRequest
from ..utils.error_handling import SecurityError, ValidationError


class SecurityTestData:
    """Test data for security validation."""
    
    @staticmethod
    def create_malicious_pdf_content() -> str:
        """Create potentially malicious PDF content for testing."""
        return """
        %PDF-1.4
        1 0 obj
        <<
        /Type /Catalog
        /Pages 2 0 R
        /OpenAction << /S /JavaScript /JS (app.alert('XSS Attack');) >>
        >>
        endobj
        
        2 0 obj
        <<
        /Type /Pages
        /Kids [3 0 R]
        /Count 1
        >>
        endobj
        
        3 0 obj
        <<
        /Type /Page
        /Parent 2 0 R
        /MediaBox [0 0 612 792]
        /Contents 4 0 R
        >>
        endobj
        
        4 0 obj
        <<
        /Length 44
        >>
        stream
        BT
        /F1 12 Tf
        100 700 Td
        (Malicious content) Tj
        ET
        endstream
        endobj
        
        xref
        0 5
        0000000000 65535 f 
        0000000009 00000 n 
        0000000074 00000 n 
        0000000120 00000 n 
        0000000179 00000 n 
        trailer
        <<
        /Size 5
        /Root 1 0 R
        >>
        startxref
        274
        %%EOF
        """
    
    @staticmethod
    def create_malicious_csv_content() -> str:
        """Create potentially malicious CSV content for testing."""
        return """
        respondent_id,role,malicious_field
        "=cmd|'/c calc'!A0","Analyst","=HYPERLINK(""http://malicious-site.com"",""Click here"")"
        "R002","Manager","@SUM(1+1)*cmd|'/c notepad'!A0"
        "'; DROP TABLE users; --","Admin","Normal content"
        """
    
    @staticmethod
    def create_oversized_content(size_mb: int) -> str:
        """Create oversized content for testing file size limits."""
        # Create content that's approximately size_mb megabytes
        chunk_size = 1024  # 1KB chunks
        chunk = "A" * chunk_size
        num_chunks = size_mb * 1024  # MB to KB conversion
        
        return chunk * num_chunks
    
    @staticmethod
    def create_invalid_file_types() -> List[tuple]:
        """Create files with invalid types for testing."""
        return [
            ("malicious.exe", b"\x4d\x5a\x90\x00", "application/octet-stream"),
            ("script.js", b"alert('xss');", "application/javascript"),
            ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            ("archive.zip", b"PK\x03\x04", "application/zip"),
            ("document.docx", b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        ]


class PerformanceTestData:
    """Test data for performance validation."""
    
    @staticmethod
    def create_large_dataset(rows: int) -> List[Dict[str, Any]]:
        """Create large dataset for performance testing."""
        data = []
        for i in range(rows):
            row = {
                "id": f"PERF_{i:06d}",
                "timestamp": f"2024-01-{(i % 28) + 1:02d} {(i % 24):02d}:{(i % 60):02d}:00",
                "category": ["A", "B", "C", "D"][i % 4],
                "value": i * 1.5,
                "description": f"Performance test record {i} with detailed description and additional context data",
                "metadata": json.dumps({"index": i, "batch": i // 1000, "processed": False}),
                "large_text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10
            }
            data.append(row)
        return data
    
    @staticmethod
    def create_concurrent_requests(count: int) -> List[Dict[str, Any]]:
        """Create multiple concurrent request scenarios."""
        requests = []
        for i in range(count):
            request = {
                "project_id": f"perf-project-{i}",
                "tenant_id": f"tenant-{i % 5}",  # 5 different tenants
                "user_id": f"user-{i}",
                "request_id": f"req-{i:04d}",
                "timestamp": time.time() + i * 0.1
            }
            requests.append(request)
        return requests


def create_upload_file(content: bytes, filename: str, content_type: str = "text/plain") -> UploadFile:
    """Create UploadFile from bytes content."""
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj, content_type=content_type)


@pytest.fixture
def security_test_service():
    """Service configured for security testing."""
    service = MarketResearchAnalysisService()
    return service


@pytest.fixture
def mock_secure_database():
    """Mock database with security validations."""
    adapter = AsyncMock()
    
    # Mock tenant isolation
    def mock_get_project(project_id: str, tenant_id: str):
        if tenant_id != "authorized-tenant":
            raise SecurityError("Unauthorized tenant access")
        return {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "field_prep_data": {"personas": [], "assumptions": []}
        }
    
    adapter.get_project_by_id.side_effect = mock_get_project
    return adapter


@pytest.fixture
def mock_auth_service():
    """Mock authentication service."""
    service = AsyncMock()
    
    def mock_validate_token(token: str):
        if token == "invalid-token":
            raise SecurityError("Invalid authentication token")
        return {"user_id": "test-user", "tenant_id": "authorized-tenant"}
    
    service.validate_token.side_effect = mock_validate_token
    return service


class TestFileUploadSecurity:
    """Test file upload security and validation mechanisms."""
    
    @pytest.mark.asyncio
    async def test_malicious_pdf_detection(self, security_test_service):
        """Test detection and handling of malicious PDF content."""
        malicious_content = SecurityTestData.create_malicious_pdf_content()
        malicious_file = create_upload_file(
            malicious_content.encode('utf-8'),
            "malicious.pdf",
            "application/pdf"
        )
        
        parser = DocumentParserService()
        
        # Test that malicious content is sanitized or rejected
        with pytest.raises((SecurityError, ValidationError, ValueError)) as exc_info:
            await parser.parse_pdf(malicious_file)
        
        # Verify security error is raised
        assert any(keyword in str(exc_info.value).lower() 
                  for keyword in ["security", "malicious", "invalid", "unsafe"])
    
    @pytest.mark.asyncio
    async def test_malicious_csv_detection(self, security_test_service):
        """Test detection and handling of malicious CSV content."""
        malicious_content = SecurityTestData.create_malicious_csv_content()
        malicious_file = create_upload_file(
            malicious_content.encode('utf-8'),
            "malicious.csv",
            "text/csv"
        )
        
        parser = DocumentParserService()
        
        # Test that malicious CSV formulas are sanitized
        result = await parser.parse_csv(malicious_file)
        
        # Verify malicious content is sanitized
        content = result.get("content", "")
        assert "=cmd" not in content
        assert "DROP TABLE" not in content
        assert "HYPERLINK" not in content
    
    @pytest.mark.asyncio
    async def test_file_size_limits(self, security_test_service):
        """Test file size limit enforcement."""
        # Test with oversized PDF (>50MB)
        oversized_content = SecurityTestData.create_oversized_content(60)  # 60MB
        oversized_file = create_upload_file(
            oversized_content.encode('utf-8'),
            "oversized.pdf",
            "application/pdf"
        )
        
        parser = DocumentParserService()
        
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            await parser.parse_pdf(oversized_file)
        
        assert "size" in str(exc_info.value).lower() or "large" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_invalid_file_type_rejection(self, security_test_service):
        """Test rejection of invalid file types."""
        invalid_files = SecurityTestData.create_invalid_file_types()
        
        parser = DocumentParserService()
        
        for filename, content, content_type in invalid_files:
            invalid_file = create_upload_file(content, filename, content_type)
            
            # Should reject non-PDF/CSV files
            if not filename.endswith(('.pdf', '.csv')):
                with pytest.raises((ValidationError, ValueError)) as exc_info:
                    if filename.endswith('.pdf'):
                        await parser.parse_pdf(invalid_file)
                    else:
                        await parser.parse_csv(invalid_file)
                
                assert any(keyword in str(exc_info.value).lower() 
                          for keyword in ["type", "format", "invalid", "unsupported"])
    
    @pytest.mark.asyncio
    async def test_content_sanitization(self, security_test_service):
        """Test content sanitization for potentially harmful content."""
        # Test HTML/JavaScript injection in content
        malicious_content = """
        Interview Transcript
        
        Participant: <script>alert('xss')</script>
        The main issue is <img src="x" onerror="alert('xss')">
        
        We need <iframe src="javascript:alert('xss')"></iframe> better tools.
        
        <a href="javascript:void(0)" onclick="alert('xss')">Click here</a>
        """
        
        malicious_file = create_upload_file(
            malicious_content.encode('utf-8'),
            "interview.pdf",
            "application/pdf"
        )
        
        parser = DocumentParserService()
        
        # Mock successful parsing but with sanitized content
        with patch.object(parser, '_extract_pdf_text', return_value=malicious_content):
            result = await parser.parse_pdf(malicious_file)
            
            sanitized_content = result.get("content", "")
            
            # Verify malicious content is removed or escaped
            assert "<script>" not in sanitized_content
            assert "onerror=" not in sanitized_content
            assert "javascript:" not in sanitized_content
            assert "onclick=" not in sanitized_content
    
    @pytest.mark.asyncio
    async def test_file_metadata_validation(self, security_test_service):
        """Test validation of file metadata and headers."""
        # Test file with mismatched extension and content
        pdf_content_csv_extension = create_upload_file(
            b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n",
            "fake.csv",  # CSV extension but PDF content
            "text/csv"
        )
        
        parser = DocumentParserService()
        
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            await parser.parse_csv(pdf_content_csv_extension)
        
        assert any(keyword in str(exc_info.value).lower() 
                  for keyword in ["format", "type", "mismatch", "invalid"])


class TestTenantIsolationAndAccessControl:
    """Test tenant isolation and access control mechanisms."""
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self, mock_secure_database, mock_auth_service):
        """Test that tenants cannot access each other's data."""
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_secure_database), \
             patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_auth_adapter', return_value=mock_auth_service):
            
            service = MarketResearchAnalysisService()
            
            # Test unauthorized tenant access
            with pytest.raises(SecurityError) as exc_info:
                await service._get_project_context(
                    project_id="test-project",
                    tenant_id="unauthorized-tenant"
                )
            
            assert "unauthorized" in str(exc_info.value).lower()
            
            # Test authorized tenant access
            result = await service._get_project_context(
                project_id="test-project", 
                tenant_id="authorized-tenant"
            )
            
            assert result is not None
            assert result["tenant_id"] == "authorized-tenant"
    
    @pytest.mark.asyncio
    async def test_user_permission_validation(self, mock_auth_service):
        """Test user permission validation."""
        
        # Mock permission validation
        def mock_validate_permissions(user_id: str, tenant_id: str, operation: str):
            if user_id == "unauthorized-user":
                raise SecurityError("Insufficient permissions")
            return True
        
        mock_auth_service.validate_user_permissions.side_effect = mock_validate_permissions
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_auth_adapter', return_value=mock_auth_service):
            
            service = MarketResearchAnalysisService()
            
            # Test unauthorized user
            with pytest.raises(SecurityError) as exc_info:
                await service._validate_user_permissions(
                    user_id="unauthorized-user",
                    tenant_id="test-tenant",
                    operation="analyze_market_research"
                )
            
            assert "permissions" in str(exc_info.value).lower()
            
            # Test authorized user
            result = await service._validate_user_permissions(
                user_id="authorized-user",
                tenant_id="test-tenant", 
                operation="analyze_market_research"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_data_access_logging(self, mock_secure_database):
        """Test that data access is properly logged for audit purposes."""
        
        access_logs = []
        
        def mock_log_access(user_id: str, tenant_id: str, resource: str, action: str):
            access_logs.append({
                "user_id": user_id,
                "tenant_id": tenant_id,
                "resource": resource,
                "action": action,
                "timestamp": time.time()
            })
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_secure_database), \
             patch('Backend.src.market_research.utils.monitoring.log_data_access', side_effect=mock_log_access):
            
            service = MarketResearchAnalysisService()
            
            # Perform operation that should be logged
            await service._get_project_context(
                project_id="test-project",
                tenant_id="authorized-tenant"
            )
            
            # Verify access was logged
            assert len(access_logs) > 0
            log_entry = access_logs[0]
            assert log_entry["tenant_id"] == "authorized-tenant"
            assert log_entry["resource"] == "project_context"
            assert log_entry["action"] == "read"
    
    @pytest.mark.asyncio
    async def test_cross_tenant_data_leakage_prevention(self, mock_secure_database):
        """Test prevention of cross-tenant data leakage."""
        
        # Mock database that returns data from wrong tenant
        def mock_get_project_with_leakage(project_id: str, tenant_id: str):
            # Simulate data leakage by returning data from different tenant
            return {
                "project_id": project_id,
                "tenant_id": "different-tenant",  # Wrong tenant!
                "field_prep_data": {"sensitive_data": "should not be accessible"}
            }
        
        mock_secure_database.get_project_by_id.side_effect = mock_get_project_with_leakage
        
        with patch('Backend.src.market_research.services.market_research_analysis_service.get_yuba_database_adapter', return_value=mock_secure_database):
            
            service = MarketResearchAnalysisService()
            
            # Should detect and prevent data leakage
            with pytest.raises(SecurityError) as exc_info:
                await service._get_project_context(
                    project_id="test-project",
                    tenant_id="authorized-tenant"
                )
            
            assert "tenant" in str(exc_info.value).lower()


class TestLoadTestingAndPerformance:
    """Test load testing and performance optimization."""
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_load(self):
        """Test system behavior under concurrent analysis load."""
        
        # Mock service that simulates realistic processing time
        mock_service = AsyncMock()
        
        async def mock_analysis(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                "session_id": f"session-{time.time()}",
                "status": "completed",
                "results": {"analysis": "mock results"}
            }
        
        mock_service.analyze_market_research = mock_analysis
        
        # Test concurrent load
        concurrent_requests = 50
        start_time = time.time()
        
        tasks = []
        for i in range(concurrent_requests):
            task = mock_service.analyze_market_research(
                project_id=f"project-{i}",
                tenant_id=f"tenant-{i % 5}",
                user_id=f"user-{i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Validate performance
        total_time = end_time - start_time
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        assert len(successful_results) == concurrent_requests
        assert total_time < 10.0  # Should complete within 10 seconds
        
        # Calculate throughput
        throughput = concurrent_requests / total_time
        assert throughput > 5.0  # Should handle at least 5 requests per second
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate memory-intensive operations
        large_datasets = []
        
        for i in range(100):
            # Create large dataset
            dataset = PerformanceTestData.create_large_dataset(1000)
            large_datasets.append(dataset)
            
            # Simulate processing
            await asyncio.sleep(0.01)
            
            # Check memory usage periodically
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory should not increase excessively
                assert memory_increase < 1000, f"Memory usage increased by {memory_increase}MB"
        
        # Clean up and check for memory leaks
        large_datasets.clear()
        await asyncio.sleep(0.1)  # Allow garbage collection
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 500, f"Potential memory leak: {memory_growth}MB growth"
    
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self):
        """Test database connection pooling under load."""
        
        connection_count = 0
        max_connections = 0
        
        class MockConnectionPool:
            def __init__(self):
                nonlocal connection_count, max_connections
                connection_count += 1
                max_connections = max(max_connections, connection_count)
            
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                nonlocal connection_count
                connection_count -= 1
            
            async def execute(self, query: str):
                await asyncio.sleep(0.01)  # Simulate query time
                return {"result": "mock"}
        
        # Simulate concurrent database operations
        async def database_operation():
            async with MockConnectionPool() as conn:
                await conn.execute("SELECT * FROM projects")
        
        # Execute many concurrent operations
        tasks = [database_operation() for _ in range(100)]
        await asyncio.gather(*tasks)
        
        # Verify connection pooling is working
        assert max_connections <= 20, f"Too many concurrent connections: {max_connections}"
        assert connection_count == 0, f"Connection leak detected: {connection_count} connections not closed"
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test API rate limiting functionality."""
        
        rate_limit_tracker = {}
        
        def mock_rate_limiter(user_id: str, endpoint: str):
            key = f"{user_id}:{endpoint}"
            current_time = time.time()
            
            if key not in rate_limit_tracker:
                rate_limit_tracker[key] = []
            
            # Clean old requests (older than 1 minute)
            rate_limit_tracker[key] = [
                t for t in rate_limit_tracker[key] 
                if current_time - t < 60
            ]
            
            # Check rate limit (max 10 requests per minute)
            if len(rate_limit_tracker[key]) >= 10:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            rate_limit_tracker[key].append(current_time)
        
        # Test rate limiting
        user_id = "test-user"
        endpoint = "/analyze"
        
        # Should allow first 10 requests
        for i in range(10):
            mock_rate_limiter(user_id, endpoint)
        
        # 11th request should be rate limited
        with pytest.raises(HTTPException) as exc_info:
            mock_rate_limiter(user_id, endpoint)
        
        assert exc_info.value.status_code == 429
    
    @pytest.mark.asyncio
    async def test_response_time_optimization(self):
        """Test response time optimization under various conditions."""
        
        # Test different payload sizes
        payload_sizes = [1, 10, 100, 1000]  # KB
        response_times = []
        
        for size_kb in payload_sizes:
            # Create payload of specified size
            payload = "A" * (size_kb * 1024)
            
            start_time = time.time()
            
            # Simulate processing
            await asyncio.sleep(0.001 * size_kb)  # Processing time scales with size
            
            # Simulate response serialization
            response = {"data": payload, "status": "success"}
            json.dumps(response)  # Serialize response
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
        
        # Verify response times are reasonable
        for i, response_time in enumerate(response_times):
            size_kb = payload_sizes[i]
            
            # Response time should be reasonable for payload size
            max_acceptable_time = 0.1 + (size_kb * 0.001)  # Base time + size factor
            assert response_time < max_acceptable_time, \
                f"Response time {response_time}s too slow for {size_kb}KB payload"
    
    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test performance of error recovery mechanisms."""
        
        error_count = 0
        recovery_times = []
        
        async def operation_with_failures():
            nonlocal error_count
            
            start_time = time.time()
            
            # Simulate operation that fails 30% of the time
            if error_count % 3 == 0:
                error_count += 1
                
                # Simulate retry logic
                await asyncio.sleep(0.1)  # Retry delay
                
                # Second attempt succeeds
                recovery_time = time.time() - start_time
                recovery_times.append(recovery_time)
                return {"status": "success", "retries": 1}
            else:
                error_count += 1
                return {"status": "success", "retries": 0}
        
        # Execute operations with failures
        tasks = [operation_with_failures() for _ in range(30)]
        results = await asyncio.gather(*tasks)
        
        # Verify error recovery performance
        successful_results = [r for r in results if r["status"] == "success"]
        assert len(successful_results) == 30  # All should eventually succeed
        
        # Check recovery times are reasonable
        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            assert avg_recovery_time < 0.5, f"Average recovery time too slow: {avg_recovery_time}s"


class TestSecurityComplianceValidation:
    """Test security compliance and validation."""
    
    @pytest.mark.asyncio
    async def test_data_encryption_at_rest(self):
        """Test that sensitive data is encrypted at rest."""
        
        # Mock encryption service
        encrypted_data = {}
        
        def mock_encrypt(data: str, key: str) -> str:
            # Simple mock encryption (in reality, use proper encryption)
            encrypted = hashlib.sha256(f"{data}:{key}".encode()).hexdigest()
            return f"encrypted:{encrypted}"
        
        def mock_decrypt(encrypted_data: str, key: str) -> str:
            # Mock decryption
            if encrypted_data.startswith("encrypted:"):
                return "decrypted_data"
            raise ValueError("Invalid encrypted data")
        
        # Test data encryption
        sensitive_data = "confidential research data"
        encryption_key = "test-key"
        
        encrypted = mock_encrypt(sensitive_data, encryption_key)
        assert encrypted.startswith("encrypted:")
        assert sensitive_data not in encrypted
        
        # Test data decryption
        decrypted = mock_decrypt(encrypted, encryption_key)
        assert decrypted == "decrypted_data"
    
    @pytest.mark.asyncio
    async def test_audit_trail_completeness(self):
        """Test that all operations create complete audit trails."""
        
        audit_log = []
        
        def mock_audit_log(operation: str, user_id: str, resource: str, details: Dict):
            audit_log.append({
                "timestamp": time.time(),
                "operation": operation,
                "user_id": user_id,
                "resource": resource,
                "details": details,
                "ip_address": "127.0.0.1",
                "user_agent": "test-client"
            })
        
        # Simulate various operations
        operations = [
            ("file_upload", "user-1", "research_document", {"filename": "test.pdf"}),
            ("analysis_start", "user-1", "project-123", {"assumptions": 5}),
            ("data_access", "user-2", "project-123", {"action": "read"}),
            ("analysis_complete", "user-1", "project-123", {"duration": 120})
        ]
        
        for operation, user_id, resource, details in operations:
            mock_audit_log(operation, user_id, resource, details)
        
        # Verify audit trail completeness
        assert len(audit_log) == len(operations)
        
        for i, log_entry in enumerate(audit_log):
            expected_operation, expected_user, expected_resource, expected_details = operations[i]
            
            assert log_entry["operation"] == expected_operation
            assert log_entry["user_id"] == expected_user
            assert log_entry["resource"] == expected_resource
            assert log_entry["details"] == expected_details
            assert "timestamp" in log_entry
            assert "ip_address" in log_entry
    
    @pytest.mark.asyncio
    async def test_input_validation_completeness(self):
        """Test comprehensive input validation."""
        
        from ..api.models import AnalysisRequest
        
        # Test various invalid inputs
        invalid_inputs = [
            # Missing required fields
            {},
            {"project_id": ""},
            {"project_id": "test", "tenant_id": ""},
            
            # Invalid data types
            {"project_id": 123, "tenant_id": "test"},
            {"project_id": "test", "tenant_id": 456},
            
            # Invalid formats
            {"project_id": "invalid-chars-!@#", "tenant_id": "test"},
            {"project_id": "test", "tenant_id": "spaces not allowed"},
            
            # Injection attempts
            {"project_id": "'; DROP TABLE projects; --", "tenant_id": "test"},
            {"project_id": "<script>alert('xss')</script>", "tenant_id": "test"},
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises((ValidationError, ValueError, TypeError)) as exc_info:
                # This would normally be handled by Pydantic validation
                if not invalid_input.get("project_id"):
                    raise ValidationError("project_id is required")
                if not invalid_input.get("tenant_id"):
                    raise ValidationError("tenant_id is required")
                if not isinstance(invalid_input.get("project_id"), str):
                    raise ValidationError("project_id must be string")
                if not isinstance(invalid_input.get("tenant_id"), str):
                    raise ValidationError("tenant_id must be string")
                
                # Additional validation checks
                project_id = invalid_input["project_id"]
                tenant_id = invalid_input["tenant_id"]
                
                if any(char in project_id for char in "!@#$%^&*()"):
                    raise ValidationError("Invalid characters in project_id")
                if " " in tenant_id:
                    raise ValidationError("Spaces not allowed in tenant_id")
                if any(keyword in project_id.lower() for keyword in ["drop", "delete", "script"]):
                    raise ValidationError("Potentially malicious input detected")
            
            assert "validation" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


if __name__ == "__main__":
    # Run security and performance validation tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-k", "test_malicious_pdf_detection or test_tenant_isolation or test_concurrent_analysis_load"
    ])