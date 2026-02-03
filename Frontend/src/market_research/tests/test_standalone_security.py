"""
Standalone security tests that validate security measures without complex dependencies.
"""

import pytest
import asyncio
import time
import hashlib
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock
from io import BytesIO

from fastapi import UploadFile, HTTPException


class SecurityTestData:
    """Test data for security validation."""
    
    @staticmethod
    def create_malicious_pdf_content() -> str:
        """Create potentially malicious PDF content for testing."""
        return """
        %PDF-1.4
        <script>alert('XSS Attack');</script>
        javascript:void(0)
        <iframe src="malicious-site.com"></iframe>
        Normal PDF content mixed with potentially harmful elements.
        """
    
    @staticmethod
    def create_malicious_csv_content() -> str:
        """Create potentially malicious CSV content for testing."""
        return """respondent_id,role,malicious_field
"=cmd|'/c calc'!A0","Analyst","=HYPERLINK(""http://malicious-site.com"",""Click here"")"
"R002","Manager","@SUM(1+1)*cmd|'/c notepad'!A0"
"'; DROP TABLE users; --","Admin","Normal content"
"""
    
    @staticmethod
    def create_oversized_content(size_kb: int) -> str:
        """Create oversized content for testing file size limits."""
        chunk = "A" * 1024  # 1KB chunk
        return chunk * size_kb
    
    @staticmethod
    def create_invalid_file_types() -> List[tuple]:
        """Create files with invalid types for testing."""
        return [
            ("malicious.exe", b"\x4d\x5a\x90\x00", "application/octet-stream"),
            ("script.js", b"alert('xss');", "application/javascript"),
            ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            ("archive.zip", b"PK\x03\x04", "application/zip")
        ]


class MockSecurityValidator:
    """Mock security validator for testing."""
    
    def __init__(self):
        self.validation_calls = []
        self.sanitization_calls = []
    
    async def validate_file_upload(self, file: UploadFile) -> Dict[str, Any]:
        """Mock file upload validation."""
        self.validation_calls.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "timestamp": time.time()
        })
        
        # Check file size
        content = await file.read()
        file.file.seek(0)  # Reset file pointer
        
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise ValueError("File size exceeds maximum allowed size")
        
        # Check file type
        if not file.filename.endswith(('.pdf', '.csv')):
            raise ValueError("Invalid file type. Only PDF and CSV files are allowed")
        
        # Check for malicious content patterns
        content_str = content.decode('utf-8', errors='ignore')
        malicious_patterns = [
            '<script>',
            'javascript:',
            '=cmd|',
            'DROP TABLE',
            '<iframe'
        ]
        
        detected_threats = []
        for pattern in malicious_patterns:
            if pattern in content_str:
                detected_threats.append(pattern)
        
        return {
            "is_valid": len(detected_threats) == 0,
            "file_size": len(content),
            "detected_threats": detected_threats,
            "validation_timestamp": time.time()
        }
    
    async def sanitize_content(self, content: str) -> str:
        """Mock content sanitization."""
        self.sanitization_calls.append({
            "original_length": len(content),
            "timestamp": time.time()
        })
        
        # Remove potentially harmful content
        sanitized = content
        harmful_patterns = [
            ('<script>', '&lt;script&gt;'),
            ('</script>', '&lt;/script&gt;'),
            ('javascript:', 'javascript_removed:'),
            ('=cmd|', '=cmd_removed|'),
            ('DROP TABLE', 'DROP_TABLE_removed'),
            ('<iframe', '&lt;iframe')
        ]
        
        for pattern, replacement in harmful_patterns:
            sanitized = sanitized.replace(pattern, replacement)
        
        return sanitized


class MockTenantIsolation:
    """Mock tenant isolation for testing."""
    
    def __init__(self):
        self.access_attempts = []
        self.authorized_tenants = {"tenant-123", "tenant-456"}
    
    async def validate_tenant_access(self, tenant_id: str, resource_id: str) -> bool:
        """Mock tenant access validation."""
        self.access_attempts.append({
            "tenant_id": tenant_id,
            "resource_id": resource_id,
            "timestamp": time.time(),
            "authorized": tenant_id in self.authorized_tenants
        })
        
        if tenant_id not in self.authorized_tenants:
            raise HTTPException(status_code=403, detail="Unauthorized tenant access")
        
        return True
    
    async def get_tenant_data(self, tenant_id: str, data_type: str) -> Dict[str, Any]:
        """Mock tenant data retrieval with isolation."""
        await self.validate_tenant_access(tenant_id, f"{data_type}_data")
        
        # Return tenant-specific data
        return {
            "tenant_id": tenant_id,
            "data_type": data_type,
            "data": f"Data for {tenant_id}",
            "access_timestamp": time.time()
        }


class MockRateLimiter:
    """Mock rate limiter for testing."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_history = {}
    
    async def check_rate_limit(self, user_id: str, endpoint: str) -> bool:
        """Mock rate limiting check."""
        key = f"{user_id}:{endpoint}"
        current_time = time.time()
        
        if key not in self.request_history:
            self.request_history[key] = []
        
        # Clean old requests
        self.request_history[key] = [
            timestamp for timestamp in self.request_history[key]
            if current_time - timestamp < self.window_seconds
        ]
        
        # Check rate limit
        if len(self.request_history[key]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Record current request
        self.request_history[key].append(current_time)
        return True


def create_upload_file(content: bytes, filename: str, content_type: str = "text/plain") -> UploadFile:
    """Create UploadFile from bytes content."""
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj)


@pytest.fixture
def security_validator():
    """Security validator fixture."""
    return MockSecurityValidator()


@pytest.fixture
def tenant_isolation():
    """Tenant isolation fixture."""
    return MockTenantIsolation()


@pytest.fixture
def rate_limiter():
    """Rate limiter fixture."""
    return MockRateLimiter()


class TestFileUploadSecurity:
    """Test file upload security measures."""
    
    @pytest.mark.asyncio
    async def test_malicious_pdf_detection(self, security_validator):
        """Test detection of malicious PDF content."""
        malicious_content = SecurityTestData.create_malicious_pdf_content()
        malicious_file = create_upload_file(
            malicious_content.encode('utf-8'),
            "malicious.pdf",
            "application/pdf"
        )
        
        result = await security_validator.validate_file_upload(malicious_file)
        
        # Should detect malicious content
        assert not result["is_valid"]
        assert len(result["detected_threats"]) > 0
        assert any("script" in threat for threat in result["detected_threats"])
        
        print(f"✅ Malicious PDF detection test passed")
        print(f"   - Detected {len(result['detected_threats'])} threats")
        print(f"   - Threats: {result['detected_threats']}")
    
    @pytest.mark.asyncio
    async def test_malicious_csv_detection(self, security_validator):
        """Test detection of malicious CSV content."""
        malicious_content = SecurityTestData.create_malicious_csv_content()
        malicious_file = create_upload_file(
            malicious_content.encode('utf-8'),
            "malicious.csv",
            "text/csv"
        )
        
        result = await security_validator.validate_file_upload(malicious_file)
        
        # Should detect malicious content
        assert not result["is_valid"]
        assert len(result["detected_threats"]) > 0
        assert any("cmd" in threat for threat in result["detected_threats"])
        
        print(f"✅ Malicious CSV detection test passed")
        print(f"   - Detected {len(result['detected_threats'])} threats")
    
    @pytest.mark.asyncio
    async def test_file_size_limits(self, security_validator):
        """Test file size limit enforcement."""
        # Create oversized file (60MB)
        oversized_content = SecurityTestData.create_oversized_content(60 * 1024)  # 60MB
        oversized_file = create_upload_file(
            oversized_content.encode('utf-8'),
            "oversized.pdf",
            "application/pdf"
        )
        
        with pytest.raises(ValueError) as exc_info:
            await security_validator.validate_file_upload(oversized_file)
        
        assert "size exceeds" in str(exc_info.value).lower()
        
        print(f"✅ File size limit test passed")
        print(f"   - Correctly rejected {len(oversized_content)} byte file")
    
    @pytest.mark.asyncio
    async def test_invalid_file_type_rejection(self, security_validator):
        """Test rejection of invalid file types."""
        invalid_files = SecurityTestData.create_invalid_file_types()
        
        for filename, content, content_type in invalid_files:
            invalid_file = create_upload_file(content, filename, content_type)
            
            with pytest.raises(ValueError) as exc_info:
                await security_validator.validate_file_upload(invalid_file)
            
            assert "invalid file type" in str(exc_info.value).lower()
        
        print(f"✅ Invalid file type rejection test passed")
        print(f"   - Rejected {len(invalid_files)} invalid file types")
    
    @pytest.mark.asyncio
    async def test_content_sanitization(self, security_validator):
        """Test content sanitization."""
        malicious_content = """
        Interview content with <script>alert('xss')</script> embedded.
        Also contains javascript:void(0) and =cmd|'/c calc' formulas.
        Normal content should remain unchanged.
        """
        
        sanitized_content = await security_validator.sanitize_content(malicious_content)
        
        # Verify malicious content is sanitized
        assert "<script>" not in sanitized_content
        assert "javascript:" not in sanitized_content
        assert "=cmd|" not in sanitized_content
        
        # Verify normal content remains
        assert "Interview content" in sanitized_content
        assert "Normal content" in sanitized_content
        
        print(f"✅ Content sanitization test passed")
        print(f"   - Original length: {len(malicious_content)}")
        print(f"   - Sanitized length: {len(sanitized_content)}")


class TestTenantIsolationSecurity:
    """Test tenant isolation and access control."""
    
    @pytest.mark.asyncio
    async def test_authorized_tenant_access(self, tenant_isolation):
        """Test authorized tenant access."""
        # Test authorized tenant
        result = await tenant_isolation.get_tenant_data("tenant-123", "project")
        
        assert result["tenant_id"] == "tenant-123"
        assert result["data_type"] == "project"
        assert "tenant-123" in result["data"]
        
        print(f"✅ Authorized tenant access test passed")
        print(f"   - Tenant: {result['tenant_id']}")
        print(f"   - Data type: {result['data_type']}")
    
    @pytest.mark.asyncio
    async def test_unauthorized_tenant_access(self, tenant_isolation):
        """Test unauthorized tenant access prevention."""
        # Test unauthorized tenant
        with pytest.raises(HTTPException) as exc_info:
            await tenant_isolation.get_tenant_data("unauthorized-tenant", "project")
        
        assert exc_info.value.status_code == 403
        assert "unauthorized" in str(exc_info.value.detail).lower()
        
        print(f"✅ Unauthorized tenant access prevention test passed")
        print(f"   - Correctly blocked unauthorized tenant")
    
    @pytest.mark.asyncio
    async def test_cross_tenant_data_isolation(self, tenant_isolation):
        """Test that tenants cannot access each other's data."""
        # Get data for tenant-123
        data_123 = await tenant_isolation.get_tenant_data("tenant-123", "project")
        
        # Get data for tenant-456
        data_456 = await tenant_isolation.get_tenant_data("tenant-456", "project")
        
        # Verify data isolation
        assert data_123["tenant_id"] != data_456["tenant_id"]
        assert data_123["data"] != data_456["data"]
        assert "tenant-123" in data_123["data"]
        assert "tenant-456" in data_456["data"]
        
        print(f"✅ Cross-tenant data isolation test passed")
        print(f"   - Tenant 123 data: {data_123['data'][:50]}...")
        print(f"   - Tenant 456 data: {data_456['data'][:50]}...")


class TestRateLimitingSecurity:
    """Test rate limiting security measures."""
    
    @pytest.mark.asyncio
    async def test_normal_request_rate(self, rate_limiter):
        """Test normal request rate handling."""
        user_id = "test-user"
        endpoint = "/analyze"
        
        # Make requests within rate limit
        for i in range(5):
            result = await rate_limiter.check_rate_limit(user_id, endpoint)
            assert result is True
        
        print(f"✅ Normal request rate test passed")
        print(f"   - Successfully processed 5 requests")
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, rate_limiter):
        """Test rate limit enforcement."""
        user_id = "test-user"
        endpoint = "/analyze"
        
        # Make requests up to the limit
        for i in range(10):  # Max requests
            await rate_limiter.check_rate_limit(user_id, endpoint)
        
        # Next request should be rate limited
        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter.check_rate_limit(user_id, endpoint)
        
        assert exc_info.value.status_code == 429
        assert "rate limit" in str(exc_info.value.detail).lower()
        
        print(f"✅ Rate limit enforcement test passed")
        print(f"   - Correctly blocked request after 10 attempts")
    
    @pytest.mark.asyncio
    async def test_per_user_rate_limiting(self, rate_limiter):
        """Test per-user rate limiting isolation."""
        endpoint = "/analyze"
        
        # User 1 makes maximum requests
        for i in range(10):
            await rate_limiter.check_rate_limit("user-1", endpoint)
        
        # User 1 should be rate limited
        with pytest.raises(HTTPException):
            await rate_limiter.check_rate_limit("user-1", endpoint)
        
        # User 2 should still be able to make requests
        result = await rate_limiter.check_rate_limit("user-2", endpoint)
        assert result is True
        
        print(f"✅ Per-user rate limiting test passed")
        print(f"   - User 1 correctly rate limited")
        print(f"   - User 2 still has access")


class TestSecurityCompliance:
    """Test security compliance measures."""
    
    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test comprehensive input validation."""
        
        # Test various invalid inputs
        invalid_inputs = [
            "",  # Empty string
            "   ",  # Whitespace only
            "a" * 10000,  # Too long
            "'; DROP TABLE users; --",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "../../../etc/passwd",  # Path traversal
            "user@domain.com'; DELETE FROM users; --"  # Email with injection
        ]
        
        def validate_input(input_str: str) -> bool:
            """Mock input validation function."""
            if not input_str or not input_str.strip():
                return False
            if len(input_str) > 1000:
                return False
            
            dangerous_patterns = [
                "DROP TABLE", "DELETE FROM", "<script>", "javascript:",
                "../", "etc/passwd", "'; ", "'; "
            ]
            
            for pattern in dangerous_patterns:
                if pattern in input_str:
                    return False
            
            return True
        
        valid_count = 0
        invalid_count = 0
        
        for input_str in invalid_inputs:
            if validate_input(input_str):
                valid_count += 1
            else:
                invalid_count += 1
        
        # All inputs should be invalid
        assert invalid_count == len(invalid_inputs)
        assert valid_count == 0
        
        print(f"✅ Input validation test passed")
        print(f"   - Rejected {invalid_count} invalid inputs")
    
    @pytest.mark.asyncio
    async def test_audit_logging(self):
        """Test audit logging functionality."""
        
        audit_log = []
        
        def log_security_event(event_type: str, user_id: str, details: Dict[str, Any]):
            """Mock audit logging function."""
            audit_log.append({
                "timestamp": time.time(),
                "event_type": event_type,
                "user_id": user_id,
                "details": details,
                "ip_address": "127.0.0.1"
            })
        
        # Simulate various security events
        security_events = [
            ("file_upload", "user-1", {"filename": "test.pdf", "size": 1024}),
            ("malicious_content_detected", "user-2", {"threats": ["script", "cmd"]}),
            ("rate_limit_exceeded", "user-3", {"endpoint": "/analyze", "attempts": 11}),
            ("unauthorized_access", "user-4", {"resource": "project-123", "tenant": "wrong-tenant"})
        ]
        
        for event_type, user_id, details in security_events:
            log_security_event(event_type, user_id, details)
        
        # Verify audit log
        assert len(audit_log) == len(security_events)
        
        for i, log_entry in enumerate(audit_log):
            expected_event, expected_user, expected_details = security_events[i]
            
            assert log_entry["event_type"] == expected_event
            assert log_entry["user_id"] == expected_user
            assert log_entry["details"] == expected_details
            assert "timestamp" in log_entry
            assert "ip_address" in log_entry
        
        print(f"✅ Audit logging test passed")
        print(f"   - Logged {len(audit_log)} security events")


if __name__ == "__main__":
    # Run standalone security tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ])