"""RABA Monitoring Service.

Tracks token usage and costs for text, image, and video generation.
Stores metrics in Supabase for analytics and billing.

Reference: Phase 5 - Production Readiness
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services.supabase import get_supabase_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GenerationType(str, Enum):
    """Type of generation for cost tracking."""

    TEXT = "text"  # Gemini text generation
    IMAGE = "image"  # Nano Banana Pro image generation
    VIDEO = "video"  # Veo 3.1 video generation
    AUDIO = "audio"  # Gemini TTS generation
    RESEARCH = "research"  # Deep Research API
    EMBEDDING = "embedding"  # Vector embeddings


class TokenUsage(BaseModel):
    """Token usage for a single API call."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0  # Tokens served from cache


class UsageRecord(BaseModel):
    """A single usage record for tracking."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: Optional[str] = None  # Workflow ID (historical name)
    generation_type: GenerationType
    model_name: str
    token_usage: TokenUsage
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CostCalculator:
    """
    Calculate costs based on token usage and generation type.

    Pricing as of January 2026 (Google AI pricing):
    - Gemini 2.5 Flash: $0.075/1M input, $0.30/1M output
    - Gemini 2.5 Pro: $1.25/1M input, $5.00/1M output
    - Gemini 3 Flash Preview: $0.10/1M input, $0.40/1M output
    - Gemini 3 Pro (Nano Banana): $2.50/1M input, $10.00/1M output + $0.02/image
    - Veo 3.1: $0.10/second of video
    - Gemini 2.5 Flash TTS: $0.50/1M input tokens, $10.00/1M output tokens
    - Gemini 2.5 Pro TTS: $1.00/1M input tokens, $20.00/1M output tokens
    - Deep Research: ~$0.05 per research query (estimated)
    """

    PRICING = {
        # Text models (per million tokens)
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-3-flash-preview": {"input": 0.10, "output": 0.40},
        "gemini-3-pro": {"input": 2.50, "output": 10.00},
        # Image generation (per image + tokens)
        "gemini-3-pro-image-preview": {"input": 2.50, "output": 10.00, "per_image": 0.02},
        "nano-banana-pro": {"input": 2.50, "output": 10.00, "per_image": 0.02},
        # Video generation (per second)
        "veo-3.1": {"per_second": 0.10},
        # Audio generation (per million tokens)
        "gemini-2.5-flash-preview-tts": {"input": 0.50, "output": 10.00},
        "gemini-2.5-pro-preview-tts": {"input": 1.00, "output": 20.00},
        # Research (per query)
        "deep-research-pro-preview": {"per_query": 0.05},
    }

    @classmethod
    def calculate_text_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for text generation."""
        pricing = cls.PRICING.get(model, cls.PRICING["gemini-2.5-flash"])

        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0.075)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0.30)

        return round(input_cost + output_cost, 6)

    @classmethod
    def calculate_image_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
        num_images: int = 1,
    ) -> float:
        """Calculate cost for image generation."""
        pricing = cls.PRICING.get(model, cls.PRICING["nano-banana-pro"])

        # Token cost
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 2.50)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 10.00)

        # Per-image cost
        image_cost = num_images * pricing.get("per_image", 0.02)

        return round(input_cost + output_cost + image_cost, 6)

    @classmethod
    def calculate_video_cost(
        cls,
        model: str,
        duration_seconds: float,
    ) -> float:
        """Calculate cost for video generation."""
        pricing = cls.PRICING.get(model, cls.PRICING["veo-3.1"])

        return round(duration_seconds * pricing.get("per_second", 0.10), 6)

    @classmethod
    def calculate_audio_cost_tokens(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for audio generation."""
        pricing = cls.PRICING.get(model, cls.PRICING["gemini-2.5-flash-preview-tts"])
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0.50)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 10.00)
        return round(input_cost + output_cost, 6)

    @classmethod
    def calculate_research_cost(cls, model: str) -> float:
        """Calculate cost for deep research query."""
        pricing = cls.PRICING.get(model, cls.PRICING["deep-research-pro-preview"])
        return pricing.get("per_query", 0.05)


class MonitoringService:
    """
    Service for tracking and storing usage metrics.

    Features:
    - Track token usage per generation type
    - Calculate costs based on model pricing
    - Store metrics in Supabase for analytics
    - Aggregate usage by workflow, time period
    """

    TABLE_NAME = "usage_metrics"

    def __init__(self):
        self._supabase = None
        self._logger = get_logger(f"{__name__}.MonitoringService")
        # If schema is missing, disable further inserts to avoid log spam
        self._disabled_reason: Optional[str] = None

    @property
    def supabase(self):
        """Get Supabase client (lazy initialization)."""
        if self._supabase is None:
            self._supabase = get_supabase_client()
        return self._supabase

    async def record_text_usage(
        self,
        video_id: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_seconds: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UsageRecord:
        """Record text generation usage."""
        cost = CostCalculator.calculate_text_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            video_id=video_id,
            generation_type=GenerationType.TEXT,
            model_name=model,
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            cost_usd=cost,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

        await self._store_record(record)
        return record

    async def record_image_usage(
        self,
        video_id: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int,
        num_images: int = 1,
        duration_seconds: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UsageRecord:
        """Record image generation usage."""
        cost = CostCalculator.calculate_image_cost(model, input_tokens, output_tokens, num_images)

        record = UsageRecord(
            video_id=video_id,
            generation_type=GenerationType.IMAGE,
            model_name=model,
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            cost_usd=cost,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
            metadata={"num_images": num_images, **(metadata or {})},
        )

        await self._store_record(record)
        return record

    async def record_video_usage(
        self,
        video_id: Optional[str],
        model: str,
        video_duration_seconds: float,
        generation_duration_seconds: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UsageRecord:
        """Record video generation usage."""
        cost = CostCalculator.calculate_video_cost(model, video_duration_seconds)

        record = UsageRecord(
            video_id=video_id,
            generation_type=GenerationType.VIDEO,
            model_name=model,
            token_usage=TokenUsage(),  # No tokens for video
            cost_usd=cost,
            duration_seconds=generation_duration_seconds,
            success=success,
            error_message=error_message,
            metadata={"video_duration": video_duration_seconds, **(metadata or {})},
        )

        await self._store_record(record)
        return record

    async def record_audio_usage(
        self,
        video_id: Optional[str],
        model: str,
        audio_duration_seconds: float,
        input_tokens: int,
        output_tokens: int,
        generation_duration_seconds: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UsageRecord:
        """Record audio generation usage."""
        cost = CostCalculator.calculate_audio_cost_tokens(
            model,
            input_tokens,
            output_tokens,
        )

        record = UsageRecord(
            video_id=video_id,
            generation_type=GenerationType.AUDIO,
            model_name=model,
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            cost_usd=cost,
            duration_seconds=generation_duration_seconds,
            success=success,
            error_message=error_message,
            metadata={"audio_duration": audio_duration_seconds, **(metadata or {})},
        )

        await self._store_record(record)
        return record

    async def record_research_usage(
        self,
        video_id: Optional[str],
        model: str,
        duration_seconds: float = 0.0,
        success: bool = True,
        cache_hit: bool = False,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UsageRecord:
        """Record deep research usage."""
        # No cost if cache hit
        cost = 0.0 if cache_hit else CostCalculator.calculate_research_cost(model)

        record = UsageRecord(
            video_id=video_id,
            generation_type=GenerationType.RESEARCH,
            model_name=model,
            token_usage=TokenUsage(cached_tokens=1 if cache_hit else 0),
            cost_usd=cost,
            duration_seconds=duration_seconds,
            success=success,
            error_message=error_message,
            metadata={"cache_hit": cache_hit, **(metadata or {})},
        )

        await self._store_record(record)
        return record

    async def _store_record(self, record: UsageRecord) -> None:
        """Store usage record in database."""
        try:
            if self._disabled_reason:
                self._logger.debug(
                    f"Monitoring disabled (reason={self._disabled_reason}); skipping store"
                )
                return
            base = {
                "id": record.id,
                "generation_type": record.generation_type.value,
                "model_name": record.model_name,
                "input_tokens": record.token_usage.input_tokens,
                "output_tokens": record.token_usage.output_tokens,
                "total_tokens": record.token_usage.total_tokens,
                "cached_tokens": record.token_usage.cached_tokens,
                "cost_usd": record.cost_usd,
                "duration_seconds": record.duration_seconds,
                "success": record.success,
                "error_message": record.error_message,
                "metadata": record.metadata,
                "created_at": record.created_at.isoformat(),
            }
            # Prefer workflow_id column; fallback to legacy video_id if needed
            try:
                data = {**base, "workflow_id": record.video_id}
                self.supabase.table(self.TABLE_NAME).insert(data).execute()
            except Exception as e1:
                msg1 = str(e1)
                if 'column "workflow_id" does not exist' in msg1.lower():
                    data = {**base, "video_id": record.video_id}
                    self.supabase.table(self.TABLE_NAME).insert(data).execute()
                else:
                    raise
            self._logger.debug(f"Stored usage record: {record.id}")

        except Exception as e:
            msg = str(e)
            self._logger.warning(f"Failed to store usage record: {msg}")
            if "PGRST205" in msg or "Could not find the table 'public.usage_metrics'" in msg:
                self._disabled_reason = "missing_table"
                self._logger.error(
                    "Monitoring table missing. Apply migration: Backend/migrations/usage_metrics.sql. "
                    "Until then, usage metrics will not be persisted."
                )

    async def get_workflow_usage(self, video_id: str) -> dict[str, Any]:
        """Get aggregated usage for a workflow."""
        try:
            # Prefer workflow_id filter, fallback to video_id
            table = self.supabase.table(self.TABLE_NAME).select("*")
            try:
                response = table.eq("workflow_id", video_id).execute()
            except Exception:
                response = table.eq("video_id", video_id).execute()

            records = response.data or []

            return self._aggregate_records(records)

        except Exception as e:
            msg = str(e)
            if "PGRST205" in msg or "Could not find the table 'public.usage_metrics'" in msg:
                self._logger.warning("Usage metrics table missing; returning empty usage summary")
                return self._aggregate_records([])
            self._logger.error(f"Failed to get workflow usage: {e}")
            return {"error": str(e)}

    async def get_usage_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get aggregated usage summary for a time period."""
        try:
            query = self.supabase.table(self.TABLE_NAME).select("*")

            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())

            response = query.order("created_at", desc=True).limit(1000).execute()
            records = response.data or []

            return self._aggregate_records(records)

        except Exception as e:
            msg = str(e)
            if "PGRST205" in msg or "Could not find the table 'public.usage_metrics'" in msg:
                self._logger.warning("Usage metrics table missing; returning empty summary")
                return self._aggregate_records([])
            self._logger.error(f"Failed to get usage summary: {e}")
            return {"error": str(e)}

    def _aggregate_records(self, records: list[dict]) -> dict[str, Any]:
        """Aggregate usage records into summary suitable for API and UI."""
        summary = {
            "total_records": len(records),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "by_type": {},
            "by_model": {},
            "success_rate": 0.0,  # percent (legacy)
            "cache_hit_rate": 0.0,  # percent (legacy)
        }

        if not records:
            return summary

        success_count = 0
        cache_hits = 0
        research_count = 0
        total_duration = 0.0
        video_count = 0
        video_success = 0
        video_fail = 0
        video_cost = 0.0

        for record in records:
            gen_type = record.get("generation_type", "unknown")
            model = record.get("model_name", "unknown")
            cost = record.get("cost_usd", 0) or 0
            tokens = record.get("total_tokens", 0) or 0
            duration = float(record.get("duration_seconds") or 0.0)

            summary["total_cost_usd"] += cost
            summary["total_tokens"] += tokens
            total_duration += duration

            # By type
            if gen_type not in summary["by_type"]:
                summary["by_type"][gen_type] = {
                    "count": 0,
                    "cost_usd": 0.0,
                    "tokens": 0,
                }
            summary["by_type"][gen_type]["count"] += 1
            summary["by_type"][gen_type]["cost_usd"] += cost
            summary["by_type"][gen_type]["tokens"] += tokens

            # By model
            if model not in summary["by_model"]:
                summary["by_model"][model] = {
                    "count": 0,
                    "cost_usd": 0.0,
                    "tokens": 0,
                }
            summary["by_model"][model]["count"] += 1
            summary["by_model"][model]["cost_usd"] += cost
            summary["by_model"][model]["tokens"] += tokens

            # Success/cache tracking
            if record.get("success"):
                success_count += 1

            if gen_type == "research":
                research_count += 1
                metadata = record.get("metadata") or {}
                if metadata.get("cache_hit"):
                    cache_hits += 1
            if gen_type == "video":
                video_count += 1
                video_cost += cost
                if record.get("success"):
                    video_success += 1
                else:
                    video_fail += 1

        summary["total_cost_usd"] = round(summary["total_cost_usd"], 4)
        summary["success_rate"] = round((success_count / len(records)) * 100, 2)

        if research_count > 0:
            summary["cache_hit_rate"] = round((cache_hits / research_count) * 100, 2)

        # Extended fields for Frontend UI
        totals = {
            "total_tokens": summary["total_tokens"],
            "total_cost_usd": summary["total_cost_usd"],
            "total_videos": video_count,
            "completed_videos": video_success,
            "failed_videos": video_fail,
        }
        # Normalize by_type/by_model to shapes expected by UI when possible
        by_generation_type = {}
        for k, v in summary["by_type"].items():
            by_generation_type[k] = {
                "tokens": v.get("tokens", 0),
                "cost_usd": round(v.get("cost_usd", 0.0), 4),
                "count": v.get("count", 0),
            }
        by_model = {}
        for k, v in summary["by_model"].items():
            by_model[k] = {
                "tokens": v.get("tokens", 0),
                "cost_usd": round(v.get("cost_usd", 0.0), 4),
                "calls": v.get("count", 0),
            }
        avg_generation_time_seconds = round(total_duration / max(1, len(records)), 2)
        avg_cost_per_video_usd = round(video_cost / max(1, video_count), 4)
        metrics = {
            "success_rate": round(success_count / max(1, len(records)), 4),  # fraction 0..1
            "cache_hit_rate": round(cache_hits / max(1, research_count), 4)
            if research_count
            else 0.0,
            "avg_generation_time_seconds": avg_generation_time_seconds,
            "avg_cost_per_video_usd": avg_cost_per_video_usd,
        }
        # Attach UI-friendly keys without breaking existing consumers
        summary.update(
            {
                "totals": totals,
                "by_generation_type": by_generation_type,
                "by_model": by_model,
                "metrics": metrics,
            }
        )

        return summary


_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get singleton MonitoringService instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
