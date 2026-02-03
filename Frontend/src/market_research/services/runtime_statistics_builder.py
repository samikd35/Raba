"""Runtime statistics builder for market research analysis.

This module dynamically derives quantitative statistics and qualitative themes
from the research chunks that are available in-memory during the analysis
workflow. It acts as a safety net when the persisted statistics registry is
missing or incomplete (for example in local environments without Supabase
access) so that the downstream agents and fact validation system always have
structured data to reference.

Key capabilities:
* Extract structured key/value pairs from CSV-derived chunks and aggregate them
  into categorical distributions and numerical summaries.
* Generate lightweight qualitative themes and quotes from PDF-derived chunks to
  provide narrative evidence.
* Produce a synthetic citation registry so every generated statistic remains
  traceable within the workflow.
* Merge the dynamically generated registry with any persisted statistics,
  favouring the persisted data when it is available.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from statistics import mean, median, pstdev
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..utils.ai_service_wrapper import AIServiceWrapper

logger = logging.getLogger(__name__)


class RuntimeStatisticsBuilder:
    """Build runtime statistics from research chunks for enhanced analysis."""

    def __init__(
        self,
        *,
        max_categories: int = 6,
        max_pdf_themes: int = 5,
        max_pdf_quotes: int = 5,
        enable_llm: Optional[bool] = None,
        ai_service_factory: Optional[Callable[[], AIServiceWrapper]] = None,
    ) -> None:
        self.max_categories = max_categories
        self.max_pdf_themes = max_pdf_themes
        self.max_pdf_quotes = max_pdf_quotes

        if enable_llm is None:
            # Allow operators to disable enrichment in environments without AI credentials.
            env_flag = os.getenv("MARKET_RESEARCH_ENABLE_RUNTIME_LLM", "1").lower()
            enable_llm = env_flag not in {"0", "false", "no"}

        self.enable_llm = enable_llm
        self._ai_service_factory = ai_service_factory
        self._ai_service: Optional[AIServiceWrapper] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def build_from_chunks(
        self, research_chunks: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Build a statistics registry snapshot from raw research chunks."""

        if not research_chunks:
            logger.warning("Runtime statistics builder received no research chunks")
            return {}

        csv_chunks = [c for c in research_chunks if c.get("source_type") == "csv"]
        pdf_chunks = [c for c in research_chunks if c.get("source_type") == "pdf"]

        logger.info(
            "🛠️ RUNTIME STATS: Building statistics from %s CSV chunks and %s PDF chunks",
            len(csv_chunks),
            len(pdf_chunks),
        )

        citation_registry: Dict[str, Any] = {}

        csv_stats = self._build_csv_statistics(csv_chunks, citation_registry)
        pdf_stats = self._build_pdf_statistics(pdf_chunks, citation_registry)

        if not csv_stats and not pdf_stats:
            logger.warning("Runtime statistics builder could not derive any statistics")
            return {}

        runtime_registry = {
            "csv_statistics": csv_stats,
            "pdf_statistics": pdf_stats,
            "citation_registry": citation_registry,
            "analysis_context": {
                "generated_at": datetime.utcnow().isoformat(),
                "builder": self.__class__.__name__,
                "csv_chunks": len(csv_chunks),
                "pdf_chunks": len(pdf_chunks),
                "llm_enriched": False,
            },
        }

        if self.enable_llm:
            llm_insights = await self._generate_llm_enrichment(
                csv_chunks=csv_chunks,
                pdf_chunks=pdf_chunks,
                runtime_registry=runtime_registry,
            )
            if llm_insights:
                runtime_registry.setdefault("analysis_context", {})["llm_enriched"] = True
                runtime_registry["llm_runtime_insights"] = llm_insights

        return runtime_registry

    def merge_registries(
        self,
        existing_registry: Optional[Dict[str, Any]],
        runtime_registry: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge persisted statistics with runtime-generated statistics."""

        existing_registry = deepcopy(existing_registry) if existing_registry else {}
        runtime_registry = runtime_registry or {}

        if not runtime_registry:
            return existing_registry

        merged = deepcopy(runtime_registry)

        def _merge_dict(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
            merged_dict = deepcopy(target)
            for key, value in source.items():
                if (
                    key in merged_dict
                    and isinstance(merged_dict[key], dict)
                    and isinstance(value, dict)
                ):
                    merged_dict[key] = _merge_dict(merged_dict[key], value)
                else:
                    merged_dict[key] = deepcopy(value)
            return merged_dict

        merged = _merge_dict(merged, existing_registry)

        return merged

    # ------------------------------------------------------------------
    # LLM enrichment helpers
    # ------------------------------------------------------------------
    async def _generate_llm_enrichment(
        self,
        *,
        csv_chunks: List[Dict[str, Any]],
        pdf_chunks: List[Dict[str, Any]],
        runtime_registry: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self.enable_llm:
            return None

        ai_service = self._get_ai_service()
        if ai_service is None:
            return None

        payload = {
            "csv_statistics": runtime_registry.get("csv_statistics", {}),
            "pdf_statistics": runtime_registry.get("pdf_statistics", {}),
            "representative_chunks": self._select_representative_chunks(csv_chunks, pdf_chunks),
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a meticulous market research analyst. "
                    "Review the provided statistics and example research snippets. "
                    "Return JSON with keys: \n"
                    "- smart_highlights: list of objects with 'insight', 'evidence', 'confidence'.\n"
                    "- data_quality_warnings: list of short strings describing gaps or inconsistencies.\n"
                    "- persona_hints: list of strings capturing which customer personas or segments are implied."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ]

        try:
            response = await ai_service.generate_with_fallback(
                messages,
                json_mode=True,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                temperature=0.2,
            )

            raw_content = response.get("content")
            parsed = self._safe_json_loads(raw_content)
            if not isinstance(parsed, dict):
                logger.warning("Runtime LLM enrichment returned non-dict payload")
                return None

            enriched = {
                "smart_highlights": parsed.get("smart_highlights", []),
                "data_quality_warnings": parsed.get("data_quality_warnings", []),
                "persona_hints": parsed.get("persona_hints", []),
                "model": response.get("model", "unknown"),
                "generated_at": datetime.utcnow().isoformat(),
            }

            return enriched

        except Exception as exc:
            logger.warning("Runtime LLM enrichment failed: %s", exc)
            return None

    def _get_ai_service(self) -> Optional[AIServiceWrapper]:
        if not self.enable_llm:
            return None

        if self._ai_service is not None:
            return self._ai_service

        try:
            if self._ai_service_factory is not None:
                self._ai_service = self._ai_service_factory()
            else:
                self._ai_service = AIServiceWrapper()
        except Exception as exc:
            logger.warning("Failed to initialize AI service for runtime registry: %s", exc)
            self._ai_service = None
            self.enable_llm = False

        return self._ai_service

    def _select_representative_chunks(
        self,
        csv_chunks: List[Dict[str, Any]],
        pdf_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        def _prepare(chunk: Dict[str, Any]) -> Dict[str, Any]:
            content = chunk.get("content") or chunk.get("text") or ""
            if isinstance(content, str):
                content = self._truncate_text(content, max_length=600)
            else:
                content = ""
            return {
                "source_type": chunk.get("source_type", "unknown"),
                "source": chunk.get("source_filename") or chunk.get("source_document") or "runtime",
                "content": content,
            }

        return {
            "csv_examples": [_prepare(chunk) for chunk in csv_chunks[:3]],
            "pdf_examples": [_prepare(chunk) for chunk in pdf_chunks[:3]],
        }

    # ------------------------------------------------------------------
    # CSV statistics helpers
    # ------------------------------------------------------------------
    def _build_csv_statistics(
        self,
        csv_chunks: List[Dict[str, Any]],
        citation_registry: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not csv_chunks:
            return {}

        parsed_responses: List[Tuple[Dict[str, Any], str]] = []

        for chunk in csv_chunks:
            parsed = self._parse_structured_fields(chunk.get("content", ""))
            if not parsed:
                continue

            source_file = chunk.get("source_filename", chunk.get("source_document", "csv_runtime"))
            parsed_responses.append((parsed, source_file))

        if not parsed_responses:
            logger.warning("Runtime CSV statistics: no structured responses detected")
            return {}

        total_responses = len(parsed_responses)
        field_counters: Dict[str, Counter] = defaultdict(Counter)
        numeric_values: Dict[str, List[float]] = defaultdict(list)
        field_labels: Dict[str, str] = {}
        field_value_sources: Dict[Tuple[str, str], set[str]] = defaultdict(set)

        for response, source_file in parsed_responses:
            for field, value in response.items():
                if value is None:
                    continue

                field_key = self._normalise_field_name(field)
                field_labels.setdefault(field_key, field)

                value_str = self._clean_value(value)
                if not value_str:
                    continue

                field_counters[field_key][value_str] += 1
                field_value_sources[(field_key, value_str)].add(source_file)

                numeric_value = self._to_number(value_str)
                if numeric_value is not None:
                    numeric_values[field_key].append(numeric_value)

        if not field_counters:
            logger.warning("Runtime CSV statistics: no aggregatable fields detected")
            return {}

        categorical_distributions: Dict[str, Any] = {}

        for field_key, counter in field_counters.items():
            top_values = counter.most_common(self.max_categories)
            other_count = sum(counter.values()) - sum(count for _, count in top_values)

            distribution = []
            for value, count in top_values:
                percentage = round((count / total_responses) * 100, 1)
                citation_id = self._build_citation_id("csv", field_key, value)
                distribution.append(
                    {
                        "value": value,
                        "count": count,
                        "percentage": percentage,
                        "source": "runtime_aggregation",
                        "citation_id": citation_id,
                    }
                )

                self._register_citation(
                    citation_registry,
                    citation_id,
                    source_type="csv",
                    source_files=field_value_sources.get((field_key, value), set()),
                    descriptor=f"{field_labels.get(field_key, field_key)} = {value}",
                )

            if other_count > 0:
                percentage = round((other_count / total_responses) * 100, 1)
                other_label = "Other"
                citation_id = self._build_citation_id("csv", field_key, "other")
                distribution.append(
                    {
                        "value": other_label,
                        "count": other_count,
                        "percentage": percentage,
                        "source": "runtime_aggregation",
                        "citation_id": citation_id,
                    }
                )
                self._register_citation(
                    citation_registry,
                    citation_id,
                    source_type="csv",
                    source_files=set(),
                    descriptor=f"{field_labels.get(field_key, field_key)} = Other",
                )

            categorical_distributions[field_key] = {
                "label": field_labels.get(field_key, field_key.title()),
                "total_responses": total_responses,
                "distribution": distribution,
                "source": "runtime_aggregation",
            }

        numerical_summaries: Dict[str, Any] = {}
        for field_key, values in numeric_values.items():
            if not values:
                continue

            citation_id = self._build_citation_id("csv", field_key, "summary")
            numerical_summaries[field_key] = {
                "count": len(values),
                "mean": round(mean(values), 2),
                "median": round(median(values), 2),
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "std_dev": round(pstdev(values), 2) if len(values) > 1 else 0.0,
                "source": "runtime_aggregation",
                "citation_id": citation_id,
            }
            self._register_citation(
                citation_registry,
                citation_id,
                source_type="csv",
                source_files=set(),
                descriptor=f"Summary statistics for {field_labels.get(field_key, field_key)}",
            )

        csv_statistics = {
            "metadata": {
                "generated_from": "runtime_statistics_builder",
                "total_rows": total_responses,
                "fields_detected": list(field_counters.keys()),
                "generated_at": datetime.utcnow().isoformat(),
            },
            "categorical_distributions": categorical_distributions,
        }

        if numerical_summaries:
            csv_statistics["numerical_summaries"] = numerical_summaries

        return csv_statistics

    def _parse_structured_fields(self, content: str) -> Dict[str, Any]:
        if not content or not isinstance(content, str):
            return {}

        content = content.strip()
        if not content:
            return {}

        # Try JSON payloads first
        if content.startswith("{") and content.endswith("}"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        fields: Dict[str, Any] = {}
        pattern = re.compile(r"^\s*([A-Za-z0-9_ /-]{2,50})\s*[:=]\s*(.+?)\s*$")

        for line in content.splitlines():
            match = pattern.match(line)
            if not match:
                continue
            key, value = match.groups()
            cleaned_key = key.strip()
            cleaned_value = value.strip()
            if cleaned_key and cleaned_value:
                fields[cleaned_key] = cleaned_value

        return fields

    # ------------------------------------------------------------------
    # PDF statistics helpers
    # ------------------------------------------------------------------
    def _build_pdf_statistics(
        self,
        pdf_chunks: List[Dict[str, Any]],
        citation_registry: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not pdf_chunks:
            return {}

        sentences: List[str] = []
        for chunk in pdf_chunks:
            content = chunk.get("content") or chunk.get("text") or ""
            if not isinstance(content, str):
                continue
            sentences.extend(self._split_sentences(content))

        sentences = [s.strip() for s in sentences if len(s.strip()) > 40]
        if not sentences:
            logger.warning("Runtime PDF statistics: no candidate sentences detected")
            return {}

        counter = Counter(sentences)
        total_sentences = sum(counter.values())

        themes: Dict[str, Any] = {}
        for idx, (sentence, freq) in enumerate(counter.most_common(self.max_pdf_themes), start=1):
            percentage = round((freq / total_sentences) * 100, 1) if total_sentences else 0.0
            theme_key = self._slugify(sentence, max_length=40) or f"theme_{idx}"
            citation_id = self._build_citation_id("pdf", theme_key, str(idx))
            themes[theme_key] = {
                "label": sentence[:160],
                "frequency": freq,
                "percentage": percentage,
                "source": "runtime_aggregation",
                "citation_id": citation_id,
            }
            self._register_citation(
                citation_registry,
                citation_id,
                source_type="pdf",
                source_files=set(),
                descriptor=sentence[:160],
            )

        key_quotes: List[Dict[str, Any]] = []
        for idx, sentence in enumerate(sentences[: self.max_pdf_quotes], start=1):
            citation_id = self._build_citation_id("pdf", "quote", str(idx))
            key_quotes.append(
                {
                    "quote": sentence[:300],
                    "source": "runtime_aggregation",
                    "citation_id": citation_id,
                }
            )
            self._register_citation(
                citation_registry,
                citation_id,
                source_type="pdf",
                source_files=set(),
                descriptor=sentence[:160],
            )

        pdf_statistics = {
            "metadata": {
                "generated_from": "runtime_statistics_builder",
                "total_segments": len(pdf_chunks),
                "generated_at": datetime.utcnow().isoformat(),
            },
            "themes": themes,
        }

        if key_quotes:
            pdf_statistics["key_quotes"] = key_quotes

        return pdf_statistics

    def _split_sentences(self, text: str) -> List[str]:
        return re.split(r"(?<=[.!?])\s+", text)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _safe_json_loads(self, raw: Any) -> Any:
        if not raw:
            return None

        if isinstance(raw, dict):
            return raw

        if not isinstance(raw, str):
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Runtime LLM enrichment returned invalid JSON payload: %s", raw[:200])
            return None

    def _truncate_text(self, text: str, *, max_length: int = 400) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _normalise_field_name(self, field: str) -> str:
        field = field.strip().lower()
        field = re.sub(r"[^a-z0-9]+", "_", field)
        return field.strip("_") or "field"

    def _clean_value(self, value: Any) -> str:
        value_str = str(value).strip()
        return value_str

    def _to_number(self, value: str) -> Optional[float]:
        try:
            if value.count(".") > 1:
                return None
            cleaned = value.replace(",", "")
            return float(cleaned)
        except ValueError:
            return None

    def _slugify(self, text: str, *, max_length: int = 32) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip("-")
        return slug

    def _build_citation_id(self, source: str, field: str, value: str) -> str:
        slug = self._slugify(f"{field}-{value}", max_length=48)
        return f"RUNTIME_{source.upper()}_{slug}"[:64]

    def _register_citation(
        self,
        citation_registry: Dict[str, Any],
        citation_id: str,
        *,
        source_type: str,
        source_files: Iterable[str],
        descriptor: str,
    ) -> None:
        if citation_id in citation_registry:
            return

        source_files = [s for s in source_files if s]
        citation_registry[citation_id] = {
            "source_type": source_type,
            "source_files": source_files or [f"runtime_{source_type}"],
            "descriptor": descriptor,
            "generated_at": datetime.utcnow().isoformat(),
            "generation_method": "runtime_statistics_builder",
        }

