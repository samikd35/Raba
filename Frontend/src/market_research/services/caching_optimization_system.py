"""
Caching and Optimization System for Market Research Analysis

Implements intelligent caching, token budget optimization, and resource management
for improved performance and concurrent request handling.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, OrderedDict
from contextlib import asynccontextmanager
import threading
import psutil
from concurrent.futures import ThreadPoolExecutor

from ..utils.error_handling import (
    PerformanceError, CacheError,
    handle_document_processing_errors, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity
)

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds
    
    def update_access(self):
        """Update access metadata."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class ResourceUsage:
    """Resource usage tracking."""
    memory_mb: float
    cpu_percent: float
    active_requests: int
    cache_size_mb: float
    timestamp: datetime


class StatisticsRegistryCache:
    """
    Intelligent cache for statistics registry operations.
    
    Features:
    - LRU eviction with size-based limits
    - TTL-based expiration
    - Memory usage monitoring
    - Cache hit/miss statistics
    - Automatic cleanup and optimization
    """
    
    def __init__(
        self,
        max_size_mb: int = 100,
        default_ttl_seconds: int = 3600,  # 1 hour
        cleanup_interval_seconds: int = 300  # 5 minutes
    ):
        """Initialize statistics registry cache."""
        self.max_size_mb = max_size_mb
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size_bytes": 0
        }
        
        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
        
        self.logger = logger
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval_seconds)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in cache cleanup: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._stats["size_bytes"] -= entry.size_bytes
                self._stats["misses"] += 1
                return None
            
            # Update access and move to end (LRU)
            entry.update_access()
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            
            return entry.data
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL override
            
        Returns:
            True if successfully cached
        """
        try:
            # Calculate size
            size_bytes = len(json.dumps(value, default=str).encode('utf-8'))
            
            with self._lock:
                # Remove existing entry if present
                if key in self._cache:
                    old_entry = self._cache[key]
                    self._stats["size_bytes"] -= old_entry.size_bytes
                    del self._cache[key]
                
                # Check if we need to evict entries
                await self._ensure_space(size_bytes)
                
                # Create new entry
                entry = CacheEntry(
                    key=key,
                    data=value,
                    created_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow(),
                    access_count=0,
                    size_bytes=size_bytes,
                    ttl_seconds=ttl_seconds or self.default_ttl_seconds
                )
                
                self._cache[key] = entry
                self._stats["size_bytes"] += size_bytes
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting cache entry {key}: {e}")
            return False
    
    async def _ensure_space(self, required_bytes: int):
        """Ensure sufficient space by evicting LRU entries."""
        max_bytes = self.max_size_mb * 1024 * 1024
        
        while (self._stats["size_bytes"] + required_bytes) > max_bytes and self._cache:
            # Evict least recently used entry
            oldest_key, oldest_entry = self._cache.popitem(last=False)
            self._stats["size_bytes"] -= oldest_entry.size_bytes
            self._stats["evictions"] += 1
            
            self.logger.debug(f"Evicted cache entry: {oldest_key}")
    
    async def _cleanup_expired(self):
        """Clean up expired cache entries."""
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache[key]
                self._stats["size_bytes"] -= entry.size_bytes
                del self._cache[key]
            
            if expired_keys:
                self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": round(hit_rate, 3),
                "size_bytes": self._stats["size_bytes"],
                "size_mb": round(self._stats["size_bytes"] / (1024 * 1024), 2),
                "entry_count": len(self._cache),
                "max_size_mb": self.max_size_mb
            }
    
    async def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "size_bytes": 0
            }
    
    def __del__(self):
        """Cleanup on destruction."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


class TokenBudgetOptimizer:
    """
    Intelligent token budget optimization for maximum information density.
    
    Features:
    - Content prioritization based on relevance scores
    - Adaptive token allocation
    - Information density calculation
    - Source balancing optimization
    """
    
    def __init__(self):
        """Initialize token budget optimizer."""
        self.logger = logger
    
    @monitor_performance("token_budget_optimization")
    async def optimize_content_selection(
        self,
        available_content: List[Dict[str, Any]],
        token_budget: int,
        analysis_type: str,
        persona_context: Optional[Dict[str, Any]] = None,
        source_balance_requirements: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Optimize content selection within token budget for maximum information density.
        
        Args:
            available_content: List of content items with metadata
            token_budget: Maximum tokens available
            analysis_type: Type of analysis (pain, size, solutions, etc.)
            persona_context: Optional persona context for relevance scoring
            source_balance_requirements: Optional source type balance requirements
            
        Returns:
            Dictionary containing optimized content selection
        """
        try:
            # Score content items for relevance
            scored_content = await self._score_content_relevance(
                available_content, analysis_type, persona_context
            )
            
            # Apply source balancing if required
            if source_balance_requirements:
                balanced_content = await self._apply_source_balancing(
                    scored_content, source_balance_requirements
                )
            else:
                balanced_content = scored_content
            
            # Optimize selection within token budget
            selected_content = await self._select_optimal_content(
                balanced_content, token_budget
            )
            
            # Calculate optimization metrics
            optimization_metrics = self._calculate_optimization_metrics(
                available_content, selected_content, token_budget
            )
            
            return {
                "selected_content": selected_content,
                "optimization_metrics": optimization_metrics,
                "token_usage": sum(item.get("estimated_tokens", 0) for item in selected_content),
                "information_density": optimization_metrics["information_density"],
                "source_distribution": optimization_metrics["source_distribution"]
            }
            
        except Exception as e:
            self.logger.error(f"Error in token budget optimization: {e}")
            raise PerformanceError(
                f"Token budget optimization failed: {str(e)}",
                error_code="TOKEN_OPTIMIZATION_ERROR"
            )
    
    async def _score_content_relevance(
        self,
        content_items: List[Dict[str, Any]],
        analysis_type: str,
        persona_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Score content items for relevance to analysis type and persona."""
        
        # Analysis type keywords for relevance scoring
        type_keywords = {
            'pain': ['problem', 'issue', 'challenge', 'difficulty', 'frustration', 'pain'],
            'size': ['frequency', 'percentage', 'often', 'many', 'statistics', 'data'],
            'solution': ['solution', 'fix', 'resolve', 'tool', 'method', 'approach'],
            'gains': ['benefit', 'advantage', 'value', 'improvement', 'better'],
            'jtbd': ['task', 'job', 'goal', 'objective', 'accomplish', 'need']
        }
        
        analysis_keywords = type_keywords.get(analysis_type, [])
        
        scored_items = []
        
        for item in content_items:
            content_text = item.get("content", "").lower()
            
            # Base relevance score from keyword matching
            keyword_score = sum(1 for keyword in analysis_keywords if keyword in content_text)
            keyword_score = min(keyword_score / len(analysis_keywords), 1.0) if analysis_keywords else 0.0
            
            # Persona relevance score
            persona_score = 0.0
            if persona_context:
                persona_keywords = self._extract_persona_keywords(persona_context)
                persona_matches = sum(1 for keyword in persona_keywords if keyword in content_text)
                persona_score = min(persona_matches / len(persona_keywords), 1.0) if persona_keywords else 0.0
            
            # Content quality score
            quality_score = self._calculate_content_quality(item)
            
            # Statistical content bonus
            stats_score = 0.0
            if any(indicator in content_text for indicator in ['%', 'percent', 'statistics', 'survey']):
                stats_score = 0.3
            
            # Combine scores
            total_score = (
                keyword_score * 0.4 +
                persona_score * 0.3 +
                quality_score * 0.2 +
                stats_score * 0.1
            )
            
            scored_item = {
                **item,
                "relevance_score": round(total_score, 3),
                "keyword_score": round(keyword_score, 3),
                "persona_score": round(persona_score, 3),
                "quality_score": round(quality_score, 3),
                "stats_score": round(stats_score, 3)
            }
            
            scored_items.append(scored_item)
        
        # Sort by relevance score
        scored_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return scored_items
    
    def _extract_persona_keywords(self, persona_context: Dict[str, Any]) -> List[str]:
        """Extract keywords from persona context."""
        keywords = []
        
        # Extract from persona description
        description = persona_context.get("description", "")
        if description:
            # Simple keyword extraction (could be enhanced with NLP)
            words = description.lower().split()
            keywords.extend([word.strip('.,!?') for word in words if len(word) > 3])
        
        # Extract from persona attributes
        for key, value in persona_context.items():
            if isinstance(value, str) and key in ["role", "industry", "goals", "challenges"]:
                words = value.lower().split()
                keywords.extend([word.strip('.,!?') for word in words if len(word) > 3])
        
        return list(set(keywords))[:10]  # Limit to top 10 unique keywords
    
    def _calculate_content_quality(self, content_item: Dict[str, Any]) -> float:
        """Calculate content quality score."""
        content = content_item.get("content", "")
        
        if not content:
            return 0.0
        
        quality_score = 0.0
        
        # Length appropriateness (not too short, not too long)
        word_count = len(content.split())
        if 20 <= word_count <= 200:
            quality_score += 0.3
        elif 10 <= word_count <= 300:
            quality_score += 0.2
        
        # Sentence structure
        sentence_count = content.count('.') + content.count('!') + content.count('?')
        if sentence_count > 0:
            quality_score += 0.2
        
        # Quote presence (indicates direct feedback)
        if '"' in content or "'" in content:
            quality_score += 0.2
        
        # Statistical content
        if any(char in content for char in ['%', '$', '#']):
            quality_score += 0.2
        
        # Emotional indicators (valuable for insights)
        emotional_words = ['feel', 'think', 'believe', 'frustrated', 'happy', 'satisfied']
        if any(word in content.lower() for word in emotional_words):
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    async def _apply_source_balancing(
        self,
        scored_content: List[Dict[str, Any]],
        balance_requirements: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Apply source balancing requirements."""
        
        # Group content by source type
        content_by_source = defaultdict(list)
        for item in scored_content:
            source_type = item.get("source_type", "unknown")
            content_by_source[source_type].append(item)
        
        balanced_content = []
        
        # Ensure minimum representation from each required source
        for source_type, min_ratio in balance_requirements.items():
            if source_type in content_by_source:
                source_items = content_by_source[source_type]
                # Sort by relevance and take top items
                source_items.sort(key=lambda x: x["relevance_score"], reverse=True)
                
                # Calculate minimum items needed
                total_items = len(scored_content)
                min_items = max(1, int(total_items * min_ratio))
                
                # Add top items from this source
                balanced_content.extend(source_items[:min_items])
        
        # Add remaining high-scoring items
        used_items = set(id(item) for item in balanced_content)
        remaining_items = [item for item in scored_content if id(item) not in used_items]
        
        # Sort remaining by score and add
        remaining_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        balanced_content.extend(remaining_items)
        
        return balanced_content
    
    async def _select_optimal_content(
        self,
        scored_content: List[Dict[str, Any]],
        token_budget: int
    ) -> List[Dict[str, Any]]:
        """Select optimal content within token budget using greedy algorithm."""
        
        selected_content = []
        used_tokens = 0
        
        # Estimate tokens for each item if not provided
        for item in scored_content:
            if "estimated_tokens" not in item:
                content = item.get("content", "")
                # Rough estimation: 1 token ≈ 4 characters
                item["estimated_tokens"] = len(content) // 4
        
        # Greedy selection based on relevance score per token
        for item in scored_content:
            item_tokens = item["estimated_tokens"]
            
            if used_tokens + item_tokens <= token_budget:
                selected_content.append(item)
                used_tokens += item_tokens
            elif token_budget - used_tokens > 50:  # If significant budget remains
                # Try to fit a truncated version
                available_tokens = token_budget - used_tokens
                truncated_content = self._truncate_content(
                    item["content"], available_tokens
                )
                
                if truncated_content:
                    truncated_item = {
                        **item,
                        "content": truncated_content,
                        "estimated_tokens": available_tokens,
                        "truncated": True
                    }
                    selected_content.append(truncated_item)
                    used_tokens = token_budget
                    break
        
        return selected_content
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit."""
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(content) <= max_chars:
            return content
        
        # Try to truncate at sentence boundary
        truncated = content[:max_chars]
        last_sentence = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence > max_chars * 0.7:  # If sentence boundary is not too early
            return truncated[:last_sentence + 1]
        
        # Truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + "..."
        
        return truncated + "..."
    
    def _calculate_optimization_metrics(
        self,
        available_content: List[Dict[str, Any]],
        selected_content: List[Dict[str, Any]],
        token_budget: int
    ) -> Dict[str, Any]:
        """Calculate optimization metrics."""
        
        total_available = len(available_content)
        total_selected = len(selected_content)
        
        # Calculate information density
        total_relevance = sum(item.get("relevance_score", 0) for item in selected_content)
        used_tokens = sum(item.get("estimated_tokens", 0) for item in selected_content)
        information_density = total_relevance / used_tokens if used_tokens > 0 else 0
        
        # Calculate source distribution
        source_distribution = defaultdict(int)
        for item in selected_content:
            source_type = item.get("source_type", "unknown")
            source_distribution[source_type] += 1
        
        # Calculate coverage metrics
        avg_relevance_available = sum(item.get("relevance_score", 0) for item in available_content) / total_available if total_available > 0 else 0
        avg_relevance_selected = sum(item.get("relevance_score", 0) for item in selected_content) / total_selected if total_selected > 0 else 0
        
        return {
            "selection_ratio": round(total_selected / total_available, 3) if total_available > 0 else 0,
            "token_utilization": round(used_tokens / token_budget, 3) if token_budget > 0 else 0,
            "information_density": round(information_density, 3),
            "avg_relevance_improvement": round(avg_relevance_selected - avg_relevance_available, 3),
            "source_distribution": dict(source_distribution),
            "total_available": total_available,
            "total_selected": total_selected,
            "used_tokens": used_tokens,
            "budget_tokens": token_budget
        }


class ResourceManager:
    """
    Resource management system for concurrent analysis requests.
    
    Features:
    - Request queuing and throttling
    - Memory usage monitoring
    - CPU usage tracking
    - Automatic resource scaling
    - Performance monitoring
    """
    
    def __init__(
        self,
        max_concurrent_requests: int = 5,
        memory_threshold_mb: int = 1000,
        cpu_threshold_percent: float = 80.0
    ):
        """Initialize resource manager."""
        self.max_concurrent_requests = max_concurrent_requests
        self.memory_threshold_mb = memory_threshold_mb
        self.cpu_threshold_percent = cpu_threshold_percent
        
        self._active_requests: Set[str] = set()
        self._request_queue: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._lock = asyncio.Lock()
        
        self._resource_history: List[ResourceUsage] = []
        self._performance_metrics = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "avg_processing_time": 0.0,
            "queue_wait_times": []
        }
        
        self.logger = logger
    
    @asynccontextmanager
    async def acquire_resources(self, request_id: str):
        """
        Acquire resources for a request with automatic management.
        
        Args:
            request_id: Unique request identifier
        """
        start_time = time.time()
        
        try:
            # Check resource availability
            await self._check_resource_availability()
            
            # Acquire semaphore (limits concurrent requests)
            await self._semaphore.acquire()
            
            async with self._lock:
                self._active_requests.add(request_id)
                self._performance_metrics["total_requests"] += 1
            
            # Record queue wait time
            wait_time = time.time() - start_time
            self._performance_metrics["queue_wait_times"].append(wait_time)
            
            # Keep only recent wait times
            if len(self._performance_metrics["queue_wait_times"]) > 100:
                self._performance_metrics["queue_wait_times"] = self._performance_metrics["queue_wait_times"][-50:]
            
            self.logger.info(f"Acquired resources for request {request_id} (wait: {wait_time:.2f}s)")
            
            yield
            
            # Request completed successfully
            async with self._lock:
                self._performance_metrics["completed_requests"] += 1
            
        except Exception as e:
            # Request failed
            async with self._lock:
                self._performance_metrics["failed_requests"] += 1
            
            self.logger.error(f"Request {request_id} failed: {e}")
            raise
            
        finally:
            # Clean up resources
            async with self._lock:
                self._active_requests.discard(request_id)
            
            self._semaphore.release()
            
            # Update processing time metrics
            processing_time = time.time() - start_time
            self._update_processing_time_metrics(processing_time)
    
    async def _check_resource_availability(self):
        """Check if resources are available for new requests."""
        
        # Get current resource usage
        current_usage = self._get_current_resource_usage()
        
        # Record usage history
        self._resource_history.append(current_usage)
        
        # Keep only recent history
        if len(self._resource_history) > 100:
            self._resource_history = self._resource_history[-50:]
        
        # Check memory threshold
        if current_usage.memory_mb > self.memory_threshold_mb:
            self.logger.warning(f"Memory usage high: {current_usage.memory_mb:.1f}MB")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Wait a bit for memory to be freed
            await asyncio.sleep(1.0)
            
            # Check again
            updated_usage = self._get_current_resource_usage()
            if updated_usage.memory_mb > self.memory_threshold_mb:
                raise PerformanceError(
                    f"Memory usage too high: {updated_usage.memory_mb:.1f}MB > {self.memory_threshold_mb}MB",
                    error_code="MEMORY_THRESHOLD_EXCEEDED"
                )
        
        # Check CPU threshold
        if current_usage.cpu_percent > self.cpu_threshold_percent:
            self.logger.warning(f"CPU usage high: {current_usage.cpu_percent:.1f}%")
            
            # Add delay to reduce CPU pressure
            await asyncio.sleep(2.0)
    
    def _get_current_resource_usage(self) -> ResourceUsage:
        """Get current system resource usage."""
        process = psutil.Process()
        
        return ResourceUsage(
            memory_mb=process.memory_info().rss / (1024 * 1024),
            cpu_percent=process.cpu_percent(),
            active_requests=len(self._active_requests),
            cache_size_mb=0.0,  # Would be populated by cache system
            timestamp=datetime.utcnow()
        )
    
    def _update_processing_time_metrics(self, processing_time: float):
        """Update processing time metrics."""
        completed = self._performance_metrics["completed_requests"]
        if completed > 0:
            current_avg = self._performance_metrics["avg_processing_time"]
            # Exponential moving average
            self._performance_metrics["avg_processing_time"] = (
                current_avg * 0.9 + processing_time * 0.1
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        total_requests = self._performance_metrics["total_requests"]
        completed_requests = self._performance_metrics["completed_requests"]
        failed_requests = self._performance_metrics["failed_requests"]
        
        success_rate = completed_requests / total_requests if total_requests > 0 else 0
        
        wait_times = self._performance_metrics["queue_wait_times"]
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        current_usage = self._get_current_resource_usage()
        
        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "failed_requests": failed_requests,
            "success_rate": round(success_rate, 3),
            "avg_processing_time": round(self._performance_metrics["avg_processing_time"], 2),
            "avg_wait_time": round(avg_wait_time, 2),
            "active_requests": len(self._active_requests),
            "max_concurrent": self.max_concurrent_requests,
            "current_memory_mb": round(current_usage.memory_mb, 1),
            "current_cpu_percent": round(current_usage.cpu_percent, 1),
            "memory_threshold_mb": self.memory_threshold_mb,
            "cpu_threshold_percent": self.cpu_threshold_percent
        }
    
    async def get_resource_recommendations(self) -> Dict[str, Any]:
        """Get resource optimization recommendations."""
        metrics = self.get_performance_metrics()
        recommendations = []
        
        # Memory recommendations
        if metrics["current_memory_mb"] > self.memory_threshold_mb * 0.8:
            recommendations.append({
                "type": "memory",
                "severity": "warning",
                "message": "Memory usage is approaching threshold",
                "suggestion": "Consider reducing cache size or concurrent request limit"
            })
        
        # CPU recommendations
        if metrics["current_cpu_percent"] > self.cpu_threshold_percent * 0.8:
            recommendations.append({
                "type": "cpu",
                "severity": "warning", 
                "message": "CPU usage is high",
                "suggestion": "Consider reducing concurrent request limit or optimizing processing"
            })
        
        # Queue recommendations
        if metrics["avg_wait_time"] > 5.0:
            recommendations.append({
                "type": "queue",
                "severity": "info",
                "message": "Average wait time is high",
                "suggestion": "Consider increasing concurrent request limit if resources allow"
            })
        
        # Success rate recommendations
        if metrics["success_rate"] < 0.95:
            recommendations.append({
                "type": "reliability",
                "severity": "warning",
                "message": "Request success rate is below 95%",
                "suggestion": "Investigate error patterns and improve error handling"
            })
        
        return {
            "recommendations": recommendations,
            "current_metrics": metrics,
            "resource_history": [asdict(usage) for usage in self._resource_history[-10:]]
        }


# Service instance getters following VMP patterns
_statistics_cache: Optional[StatisticsRegistryCache] = None
_token_optimizer: Optional[TokenBudgetOptimizer] = None
_resource_manager: Optional[ResourceManager] = None

def get_statistics_cache() -> StatisticsRegistryCache:
    """Get statistics registry cache service singleton."""
    global _statistics_cache
    if _statistics_cache is None:
        _statistics_cache = StatisticsRegistryCache()
    return _statistics_cache

def get_token_optimizer() -> TokenBudgetOptimizer:
    """Get token budget optimizer service singleton."""
    global _token_optimizer
    if _token_optimizer is None:
        _token_optimizer = TokenBudgetOptimizer()
    return _token_optimizer

def get_resource_manager() -> ResourceManager:
    """Get resource manager service singleton."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager