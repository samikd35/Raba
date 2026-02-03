"""Utility for extracting quantitative metrics from structured research data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import json

import pandas as pd

logger = logging.getLogger(__name__)


class QuantitativeAnalyzer:
    """Analyse tabular research data to extract quantitative insights."""

    def __init__(self, top_categories: int = 10, use_llm: bool = True) -> None:
        self.top_categories = top_categories
        self.use_llm = use_llm
        self._ai_service = None

    def _get_ai_service(self):
        """Lazy load AI service to avoid circular imports."""
        if self._ai_service is None:
            try:
                from ..utils.ai_service_wrapper import get_ai_service_wrapper
                self._ai_service = get_ai_service_wrapper()
            except Exception as e:
                logger.warning(f"⚠️ Could not load AI service: {e}. Falling back to pandas-only analysis.")
                self.use_llm = False
        return self._ai_service

    async def analyze_dataframe_with_llm(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Use LLM to analyze CSV data and extract rich statistics."""
        try:
            # Sample data for LLM analysis (first 10 rows)
            sample_data = df.head(10).to_dict('records')
            total_rows = len(df)
            
            # Create prompt for LLM
            system_prompt = """You are a data analyst extracting statistical insights from survey data.

Analyze the CSV data and extract:
1. Total response count
2. Percentage distributions for categorical fields (gender, age groups, locations, etc.)
3. Demographic breakdowns
4. Field distributions

Return ONLY valid JSON with this structure:
{
  "row_count": <number>,
  "column_count": <number>,
  "demographics": {
    "gender_distribution": {"male": 48.0, "female": 52.0},
    "age_groups": {"18-30": 25.0, "31-40": 35.0, "41-50": 25.0, "50+": 15.0}
  },
  "field_distributions": {
    "main_crop": {"maize": 40.0, "avocado": 25.0},
    "county": {"nairobi": 20.0, "kisumu": 15.0}
  },
  "categorical_columns": {
    "gender": [{"value": "Male", "count": 96, "percentage": 48.0}],
    "age_group": [{"value": "31-40", "count": 70, "percentage": 35.0}]
  }
}"""
            
            user_prompt = f"""Analyze this CSV survey data:

TOTAL ROWS: {total_rows}
COLUMNS: {list(df.columns)}

SAMPLE DATA (first 10 rows):
{json.dumps(sample_data, indent=2)}

Extract statistical distributions and demographics. Return ONLY the JSON object."""
            
            ai_service = self._get_ai_service()
            if not ai_service:
                logger.warning("⚠️ No AI service available for LLM CSV analysis")
                return None
            
            logger.info(f"🚀 QUANTITATIVE ANALYZER: Calling LLM for {total_rows} rows")
            
            import asyncio
            try:
                response = await asyncio.wait_for(
                    ai_service.generate_analysis_response(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model="gpt-5-mini",
                        max_completion_tokens=16000,  # gpt-5-mini needs large token budget
                        json_mode=True
                    ),
                    timeout=30.0  # 30 second timeout
                )
                logger.info(f"✅ QUANTITATIVE ANALYZER: LLM response received")
            except asyncio.TimeoutError:
                logger.error(f"❌ QUANTITATIVE ANALYZER: LLM call timed out after 30 seconds")
                return None
            
            # Parse response
            if isinstance(response, dict):
                content = response.get("content", "{}")
            else:
                content = str(response)
            
            llm_stats = json.loads(content)
            
            # Ensure correct counts
            llm_stats["row_count"] = total_rows
            llm_stats["column_count"] = len(df.columns)
            llm_stats["generated_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"✅ LLM CSV ANALYSIS: Extracted statistics for {total_rows} rows")
            return llm_stats
            
        except Exception as e:
            logger.error(f"❌ LLM CSV ANALYSIS ERROR: {e}")
            return None

    def analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return quantitative summary statistics for a dataframe."""
        
        # Try LLM-powered analysis first if enabled
        if self.use_llm and df.shape[0] > 0:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, create a task
                    llm_stats = asyncio.create_task(self.analyze_dataframe_with_llm(df))
                    # Note: This won't block, so we fall through to pandas analysis
                    # In practice, this should be called with await from async code
                    logger.info("🤖 LLM analysis scheduled (async context)")
                else:
                    # If no loop is running, run the async function
                    llm_stats = loop.run_until_complete(self.analyze_dataframe_with_llm(df))
                    if llm_stats:
                        logger.info(f"✅ Using LLM-powered CSV analysis: {llm_stats.get('row_count', 0)} rows")
                        return llm_stats
            except Exception as e:
                logger.warning(f"⚠️ LLM analysis failed, falling back to pandas: {e}")

        # Fallback to pandas-based analysis
        summary: Dict[str, Any] = {
            "row_count": int(df.shape[0]),
            "column_count": int(df.shape[1]),
            "generated_at": datetime.utcnow().isoformat(),
            "column_types": {},
            "missing_values": {},
            "numeric_columns": {},
            "categorical_columns": {},
        }

        if df.empty:
            return summary

        for column in df.columns:
            dtype = str(df[column].dtype)
            summary["column_types"][column] = dtype
            missing = int(df[column].isna().sum())
            if missing:
                summary["missing_values"][column] = missing

        numeric_columns = df.select_dtypes(include=["number"]).columns
        for column in numeric_columns:
            series = df[column].dropna()
            if series.empty:
                continue

            stats = {
                "count": int(series.count()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "min": float(series.min()),
                "max": float(series.max()),
                "std": float(series.std(ddof=0)) if series.count() > 1 else 0.0,
                "sum": float(series.sum()),
            }

            summary["numeric_columns"][column] = stats

        categorical_columns = df.select_dtypes(include=["object", "category", "bool"]).columns

        for column in categorical_columns:
            column_summary = self._summarise_categorical_column(df[column])
            if column_summary:
                summary["categorical_columns"][column] = column_summary

        return summary

    def _summarise_categorical_column(self, series: pd.Series) -> Optional[List[Dict[str, Any]]]:
        if series.empty:
            return None

        string_series = series.dropna().astype(str).str.strip()
        string_series = string_series[string_series != ""]

        if string_series.empty:
            return None

        normalized = string_series.str.lower()
        display_map: Dict[str, str] = {}

        for original, norm in zip(string_series, normalized):
            if norm not in display_map:
                display_map[norm] = original

        value_counts = normalized.value_counts()

        top_counts = value_counts.head(self.top_categories)

        total = int(string_series.size)
        summary_rows: List[Dict[str, Any]] = []

        for value, count in top_counts.items():
            display_value = display_map.get(value, value)
            percentage = (count / total) * 100 if total else 0
            summary_rows.append(
                {
                    "value": display_value,
                    "count": int(count),
                    "percentage": float(percentage),
                }
            )

        others_count = int(total - top_counts.sum())
        if others_count > 0:
            percentage = (others_count / total) * 100 if total else 0
            summary_rows.append(
                {
                    "value": "Other responses",
                    "count": others_count,
                    "percentage": float(percentage),
                }
            )

        return summary_rows or None


__all__ = ["QuantitativeAnalyzer"]
