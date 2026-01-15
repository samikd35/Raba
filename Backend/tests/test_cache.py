"""RABA Cache Tests.

Tests for Phase 4.3 - Caching Layer implementation.
Tests Redis service, cache key generation, and caching behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.cache import CacheKeys, generate_topic_hash, generate_content_hash
from app.services.redis import RedisService, get_redis_service


class TestCacheKeys:
    """Tests for CacheKeys utility class."""
    
    def test_research_key_format(self):
        """TC-007: Cache key format validation for research."""
        key = CacheKeys.research("How black holes work", "standard")
        
        assert key.startswith("raba:research:")
        assert ":standard" in key
        assert len(key) > 20  # Includes hash
    
    def test_research_key_consistency(self):
        """Same topic should produce same key."""
        key1 = CacheKeys.research("How black holes work", "standard")
        key2 = CacheKeys.research("How black holes work", "standard")
        key3 = CacheKeys.research("HOW BLACK HOLES WORK", "standard")  # Different case
        
        assert key1 == key2
        assert key1 == key3  # Case-insensitive
    
    def test_research_key_different_depth(self):
        """Different depths should produce different keys."""
        key_standard = CacheKeys.research("topic", "standard")
        key_deep = CacheKeys.research("topic", "deep")
        key_quick = CacheKeys.research("topic", "quick")
        
        assert key_standard != key_deep
        assert key_standard != key_quick
        assert key_deep != key_quick
    
    def test_tools_list_key(self):
        """TC-007: Cache key format validation for tools list."""
        key = CacheKeys.tools_list()
        
        assert key == "raba:tools:list"
    
    def test_tools_by_category_key(self):
        """Test tools by category key format."""
        key = CacheKeys.tools_by_category("surreal_realism")
        
        assert key == "raba:tools:category:surreal_realism"
    
    def test_script_key_format(self):
        """Test script cache key format."""
        key = CacheKeys.script("abc123", "tool_1")
        
        assert key == "raba:script:abc123:tool_1"
    
    def test_image_prompt_key_format(self):
        """Test image prompt cache key format."""
        key = CacheKeys.image_prompt("xyz789")
        
        assert key == "raba:image_prompt:xyz789"
    
    def test_job_status_key_format(self):
        """Test job status cache key format."""
        key = CacheKeys.job_status("workflow-123")
        
        assert key == "raba:job:workflow-123"
    
    def test_rate_limit_key_format(self):
        """Test rate limit cache key format."""
        key = CacheKeys.rate_limit("192.168.1.1", "/api/v1/generate")
        
        assert key.startswith("raba:ratelimit:192.168.1.1:")
    
    def test_ttl_values(self):
        """Test TTL helper methods return correct values."""
        assert CacheKeys.research_ttl() == 604800  # 7 days
        assert CacheKeys.tools_ttl() == 3600      # 1 hour
        assert CacheKeys.script_ttl() == 86400   # 1 day
        assert CacheKeys.session_ttl() == 3600   # 1 hour
        assert CacheKeys.rate_limit_ttl() == 60  # 1 minute


class TestHashFunctions:
    """Tests for hash generation functions."""
    
    def test_generate_topic_hash(self):
        """Test topic hash generation."""
        hash1 = generate_topic_hash("How black holes work")
        hash2 = generate_topic_hash("how black holes work")
        
        assert len(hash1) == 16
        assert hash1 == hash2  # Case-insensitive
    
    def test_generate_content_hash(self):
        """Test content hash generation."""
        hash1 = generate_content_hash("some content")
        hash2 = generate_content_hash("some content")
        hash3 = generate_content_hash("different content")
        
        assert len(hash1) == 16
        assert hash1 == hash2
        assert hash1 != hash3
    
    def test_generate_content_hash_custom_length(self):
        """Test content hash with custom length."""
        hash_short = generate_content_hash("content", length=8)
        hash_long = generate_content_hash("content", length=32)
        
        assert len(hash_short) == 8
        assert len(hash_long) == 32


class TestRedisService:
    """Tests for RedisService."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = MagicMock()
        client.get.return_value = None
        client.set.return_value = True
        client.setex.return_value = True
        client.delete.return_value = 1
        client.exists.return_value = 0
        client.ttl.return_value = -2
        client.keys.return_value = []
        client.ping.return_value = True
        client.pipeline.return_value = MagicMock()
        return client
    
    @pytest.fixture
    def redis_service(self, mock_redis_client):
        """Create RedisService with mocked client."""
        service = RedisService()
        service._client = mock_redis_client
        service._available = True
        return service
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, redis_service, mock_redis_client):
        """TC-001: Basic set/get operations."""
        test_data = {"key": "value", "number": 42}
        
        # Test set
        mock_redis_client.setex.return_value = True
        result = await redis_service.set("test_key", test_data, ttl=3600)
        assert result is True
        
        # Test get
        import json
        mock_redis_client.get.return_value = json.dumps(test_data)
        result = await redis_service.get("test_key")
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, redis_service, mock_redis_client):
        """TC-004: Cache miss returns None."""
        mock_redis_client.get.return_value = None
        
        result = await redis_service.get("nonexistent_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, redis_service, mock_redis_client):
        """Test cache deletion."""
        mock_redis_client.delete.return_value = 1
        
        result = await redis_service.delete("test_key")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_exists(self, redis_service, mock_redis_client):
        """Test cache exists check."""
        mock_redis_client.exists.return_value = 1
        
        result = await redis_service.exists("test_key")
        assert result is True
        
        mock_redis_client.exists.return_value = 0
        result = await redis_service.exists("missing_key")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cache_ttl(self, redis_service, mock_redis_client):
        """TC-002: Test TTL retrieval."""
        mock_redis_client.ttl.return_value = 3500
        
        result = await redis_service.get_ttl("test_key")
        assert result == 3500
    
    @pytest.mark.asyncio
    async def test_cache_delete_pattern(self, redis_service, mock_redis_client):
        """TC-006: Test pattern-based cache deletion."""
        mock_redis_client.keys.return_value = ["raba:script:abc:1", "raba:script:abc:2"]
        mock_redis_client.delete.return_value = 2
        
        result = await redis_service.delete_pattern("script:abc:*")
        assert result == 2
    
    def test_is_available(self, redis_service, mock_redis_client):
        """TC-008: Test availability check."""
        mock_redis_client.ping.return_value = True
        redis_service._available = None  # Reset cached status
        
        result = redis_service.is_available()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_with_metadata(self, redis_service, mock_redis_client):
        """Test get with metadata returns TTL info."""
        import json
        test_data = {"key": "value"}
        
        pipeline = MagicMock()
        pipeline.execute.return_value = [json.dumps(test_data), 3500]
        mock_redis_client.pipeline.return_value = pipeline
        
        result = await redis_service.get_with_metadata("test_key")
        
        assert result is not None
        assert result["data"] == test_data
        assert result["ttl_remaining"] == 3500
        assert result["cache_hit"] is True


class TestRedisServiceUnavailable:
    """Tests for graceful fallback when Redis is unavailable."""
    
    @pytest.fixture
    def unavailable_service(self):
        """Create RedisService that simulates unavailable Redis."""
        service = RedisService()
        service._available = False
        return service
    
    @pytest.mark.asyncio
    async def test_get_returns_none_when_unavailable(self, unavailable_service):
        """TC-008: System works without cache - get returns None."""
        result = await unavailable_service.get("any_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_returns_false_when_unavailable(self, unavailable_service):
        """TC-008: System works without cache - set returns False."""
        result = await unavailable_service.set("any_key", {"data": "test"})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_returns_false_when_unavailable(self, unavailable_service):
        """TC-008: System works without cache - delete returns False."""
        result = await unavailable_service.delete("any_key")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_exists_returns_false_when_unavailable(self, unavailable_service):
        """TC-008: System works without cache - exists returns False."""
        result = await unavailable_service.exists("any_key")
        assert result is False


class TestResearchCaching:
    """Tests for research caching integration."""
    
    @pytest.mark.asyncio
    async def test_research_cache_key_generation(self):
        """TC-003/TC-004: Research cache key is generated correctly."""
        topic = "How do quantum computers work?"
        
        cache_key = CacheKeys.research(topic, "standard")
        
        # Key should be consistent
        assert cache_key == CacheKeys.research(topic, "standard")
        
        # Different topics should have different keys
        other_key = CacheKeys.research("Different topic", "standard")
        assert cache_key != other_key


class TestToolListCaching:
    """Tests for tool list caching integration."""
    
    def test_tool_list_cache_key(self):
        """TC-005: Tool list caching uses correct key."""
        key = CacheKeys.tools_list()
        assert key == "raba:tools:list"
    
    def test_tool_category_cache_key(self):
        """Tool category filter uses correct key."""
        key = CacheKeys.tools_by_category("high_octane_anime")
        assert key == "raba:tools:category:high_octane_anime"
