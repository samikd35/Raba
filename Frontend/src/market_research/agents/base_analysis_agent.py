"""
Enterprise Base Analysis Agent for Market Research Intelligence.

Provides enterprise-grade abstract base class with advanced intelligence capabilities:
- Multi-source evidence synthesis from massive datasets
- Statistical significance testing and confidence intervals
- Cross-file validation and consistency checking
- AI-enhanced pattern recognition and semantic clustering
- Real-time accuracy monitoring and bias detection
- Comprehensive citation and traceability systems
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Iterable, Union, Set

from ..models.analysis_models import (
    AnalysisOutput,
    AssumptionAnalysisState,
    AnalysisContext
)
from ..utils.ai_service_wrapper import get_ai_service_wrapper
from ..utils.error_handling import (
    AIServiceError, TokenLimitError, RateLimitError,
    handle_ai_service_errors, monitor_performance,
    error_monitor, ErrorCategory, ErrorSeverity
)
from ..services.ground_truth_context_builder import GroundTruthContextBuilder
from ..services.evidence_retrieval_engine import EvidenceRetrievalEngine
from ..services.statistics_registry_service import StatisticsRegistryService
from ..services.fact_validation_engine import FactValidationEngine

# Import AI token monitoring
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


# ENTERPRISE PROMPT AND EVIDENCE BUDGETING CONSTANTS
#
# Enterprise-grade token management for massive dataset analysis with advanced
# intelligence capabilities. Optimized for comprehensive evidence synthesis
# from 25+ PDFs and 5+ CSVs while maintaining statistical accuracy.

# Enterprise token budgets for comprehensive analysis
MAX_TOTAL_INPUT_BUDGET = 12_000  # Increased for enterprise datasets
SYSTEM_PROMPT_TOKEN_RESERVE = 600  # More complex enterprise prompts
USER_PROMPT_STRUCTURE_RESERVE = 3_000  # Advanced statistical context
AI_RESPONSE_TOKEN_RESERVE = 2_400  # Comprehensive enterprise responses
DATA_TOKEN_BUDGET = (
    MAX_TOTAL_INPUT_BUDGET
    - SYSTEM_PROMPT_TOKEN_RESERVE
    - USER_PROMPT_STRUCTURE_RESERVE
    - AI_RESPONSE_TOKEN_RESERVE
)

# Enterprise Tier-2 evidence limits for comprehensive analysis
EVIDENCE_TOKEN_BUDGET = 4_000  # Significantly increased for enterprise
MAX_EVIDENCE_CHUNKS = 25  # Handle evidence from 25+ files
MIN_EVIDENCE_ENTRY_TOKENS = 150  # More detailed evidence entries
MAX_EVIDENCE_VERBATIM_CHARS = 400  # Longer verbatim quotes
MAX_EVIDENCE_SUMMARY_CHARS = 350  # More comprehensive summaries

# Enterprise statistical validation constants
MIN_STATISTICAL_SIGNIFICANCE = 0.05  # p-value threshold
MIN_CONFIDENCE_INTERVAL = 0.95  # Confidence level
MIN_SAMPLE_SIZE_FOR_STATS = 30  # Minimum for statistical tests
MAX_CROSS_FILE_INCONSISTENCY = 0.3  # Maximum allowed inconsistency


class EnterpriseBaseAnalysisAgent(ABC):
    """Enterprise-grade abstract base class for advanced market research intelligence.
    
    Features:
    - Multi-source evidence synthesis from massive datasets (25+ PDFs, 5+ CSVs)
    - Statistical significance testing and confidence interval calculations
    - Cross-file validation and consistency checking across all sources
    - AI-enhanced pattern recognition and semantic clustering
    - Real-time accuracy monitoring and bias detection
    - Comprehensive citation and traceability for all claims
    - Advanced persona-aware analysis with cross-demographic insights
    - Enterprise-grade error handling and fallback mechanisms
    """
    def __init__(
        self,
        statistics_registry: StatisticsRegistryService,
        ground_truth_builder: GroundTruthContextBuilder,
        evidence_retrieval: EvidenceRetrievalEngine,
        fact_validator: Optional[FactValidationEngine] = None
    ):
        """Initialize the base analysis agent with required enhanced components."""
        if not all([statistics_registry, ground_truth_builder, evidence_retrieval]):
            raise ValueError("All enhanced components are required. Legacy processing has been removed.")
            
        self.ai_service_wrapper = get_ai_service_wrapper()
        self.analysis_type = self._get_analysis_type()
        self.max_retries = 3
        self.fallback_enabled = False  # Disabled: fail-fast approach
        
        # Required enhanced components
        self.statistics_registry = statistics_registry
        self.ground_truth_builder = ground_truth_builder
        self.evidence_retrieval = evidence_retrieval
        self.use_two_tier_rag = True  # Always enabled
        
        # Fact validation component (required)
        self.fact_validator = fact_validator or FactValidationEngine()
        self.use_fact_validation = True
    
    @abstractmethod
    def _get_analysis_type(self) -> str:
        """Return the analysis type identifier for this agent."""
        pass
    
    @abstractmethod
    def _create_analysis_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        """Create the analysis prompt messages for this agent type."""
        pass
    
    async def _create_two_tier_analysis_prompt(self, context: AnalysisContext) -> Dict[str, str]:
        """Create a modular prompt bundle that supports a two-pass workflow."""
        try:
            project_id = context.project_context.get("project_id")
            tenant_id = context.project_context.get("tenant_id", "")
            persona_id = context.persona.get("id") if context.persona else None
            context_flags = context.context_flags or {}

            # Ground truth context (Tier 1)
            if context.ground_truth_statistics:
                ground_truth_context = self._render_ground_truth_section(
                    context.ground_truth_statistics,
                    context_flags,
                )
            else:
                ground_truth_context = await self.ground_truth_builder.build_statistics_context(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    analysis_type=self.analysis_type,
                    persona_id=persona_id,
                )
                if context_flags.get("partial_ground_truth"):
                    ground_truth_context += (
                        "\n⚠️ Only partial ground-truth statistics were available for this run."
                    )

            # Evidence context (Tier 2)
            evidence_chunks = context.evidence_chunks or []
            if not evidence_chunks:
                evidence_query = " ".join(
                    filter(
                        None,
                        [
                            context.assumption.get("text", ""),
                            context.persona.get("name") if context.persona else "",
                            self.analysis_type,
                        ],
                    )
                ).strip()
                evidence_chunks = await self.evidence_retrieval.retrieve_balanced_evidence(
                    query=evidence_query,
                    project_id=project_id,
                    tenant_id=tenant_id,
                    analysis_type=self.analysis_type,
                    persona_id=persona_id,
                    assumption_id=self._get_assumption_identifier(context.assumption),
                    assumption=context.assumption,
                    persona=context.persona,
                )

            evidence_context = self._render_evidence_digest(evidence_chunks)

            system_prompt = self._create_two_tier_system_prompt(context_flags)
            context_block = self._compose_context_block(context, ground_truth_context, evidence_context)
            notes_instruction = self._create_notes_prompt()
            summary_instruction = self._create_summary_prompt()

            return {
                "system_prompt": system_prompt,
                "context_block": context_block,
                "notes_instruction": notes_instruction,
                "summary_instruction": summary_instruction,
            }

        except Exception as e:
            logger.error(f"❌ CRITICAL: Enhanced two-tier prompt creation failed: {e}")
            raise ValueError(f"Enhanced two-tier prompt creation failed. Legacy fallback removed: {str(e)}")

    def _create_two_tier_system_prompt(self, context_flags: Dict[str, Any]) -> str:
        """Create a concise system prompt that adapts to partial data scenarios."""

        partial_notice = (
            "Ground-truth statistics may be incomplete in this run."
            " When statistics are missing, rely on well-supported qualitative evidence"
            " and clearly flag estimates that require manual review."
            if context_flags.get("partial_ground_truth")
            else ""
        )

        return (
            f"<role>\n"
            f"You are a market research analysis agent for {self.analysis_type} insights.\n"
            f"</role>\n\n"
            f"<approach>\n"
            f"Balance statistical accuracy with thoughtful synthesis.\n"
            f"Use tiered context: statistics provide quantitative truth; evidence provides narrative depth.\n"
            f"</approach>\n\n"
            + (f"<partial_data_notice>\n{partial_notice}\n</partial_data_notice>\n\n" if partial_notice else "")
            + f"<citation_rules>\n"
            f"Always cite the provided identifiers for any claim. NEVER fabricate citations.\n"
            f"</citation_rules>"
        )

    def _compose_context_block(
        self,
        context: AnalysisContext,
        ground_truth_context: str,
        evidence_context: str,
    ) -> str:
        assumption_text = context.assumption.get("text", "No assumption provided")
        persona_name = context.persona.get("name", "General Persona") if context.persona else "General Persona"

        header = (
            f"ASSUMPTION UNDER REVIEW:\n" f"• Persona: {persona_name}\n" f"• Statement: {assumption_text}\n"
        )

        return "\n\n".join([
            header,
            ground_truth_context.strip() or "⚠️ No persisted statistics available for this assumption.",
            evidence_context.strip() or "⚠️ No qualitative evidence retrieved for this assumption.",
        ])

    def _create_notes_prompt(self) -> str:
        return (
            "<task>\n"
            "Build exploratory findings.\n"
            "</task>\n\n"
            "<requirements>\n"
            "• Produce 4-6 bullet points capturing the most decision-ready insights\n"
            "• Each bullet must note whether it is statistical or qualitative and include citation IDs\n"
            "• Highlight contradicting evidence when it exists\n"
            "</requirements>\n\n"
            "<output_format>\n"
            "Respond with bullet points only. No JSON, no extra text.\n"
            "</output_format>"
        )

    def _create_summary_prompt(self) -> str:
        schema_json = json.dumps(self._get_output_schema(), indent=2)
        return (
            "<task>\n"
            "Create structured analysis from the INITIAL FINDINGS above.\n"
            "</task>\n\n"
            "<requirements>\n"
            "Craft a JSON object that matches the schema below.\n"
            "Incorporate supporting and debunking evidence, accuracy level, and confidence scoring.\n"
            "</requirements>\n\n"
            f"<output_schema>\n{schema_json}\n</output_schema>\n\n"
            "<output_format>\n"
            "Return ONLY valid JSON matching the schema. No extra text.\n"
            "</output_format>"
        )

    def _render_ground_truth_section(
        self,
        statistics: Dict[str, Any],
        context_flags: Dict[str, Any],
    ) -> str:
        if not isinstance(statistics, dict) or not statistics:
            if context_flags.get("partial_ground_truth"):
                return (
                    "📊 PARTIAL GROUND TRUTH\n"
                    "Statistics are incomplete; supplement with qualitative evidence and mark uncertain figures."
                )
            return "📊 No ground-truth statistics were available."

        lines = ["📊 GROUND TRUTH STATISTICS"]
        csv_stats = statistics.get("csv_statistics", {})
        pdf_stats = statistics.get("pdf_statistics", {})

        if csv_stats:
            metadata = csv_stats.get("metadata", {})
            if metadata:
                lines.append(
                    f"• Source: {metadata.get('filename', metadata.get('generated_from', 'CSV aggregate'))}"
                )
                if metadata.get("total_rows"):
                    lines.append(f"• Total Responses: {metadata['total_rows']}")

            distributions = csv_stats.get("categorical_distributions", {})
            for field, field_data in list(distributions.items())[:5]:
                lines.append(f"  - {field.replace('_', ' ').title()}:")
                for item in field_data.get("distribution", [])[:4]:
                    lines.append(
                        f"    • {item.get('value')}: {item.get('percentage', 0)}%"
                        f" ({item.get('count', 0)} responses) [Cite: {item.get('citation_id')}]"
                    )

        if pdf_stats:
            themes = pdf_stats.get("themes", {})
            if themes:
                lines.append("• Interview Themes:")
                for theme, data in list(themes.items())[:5]:
                    lines.append(
                        f"  - {theme}: {data.get('percentage', 0)}%"
                        f" ({data.get('frequency', 0)} mentions) [Cite: {data.get('citation_id')}]"
                    )

        return "\n".join(lines)

    def _render_evidence_digest(self, evidence_chunks: List[Dict[str, Any]]) -> str:
        if not evidence_chunks:
            return "📘 QUALITATIVE EVIDENCE\n⚠️ Retrieval returned no relevant chunks."

        formatted = ["📘 QUALITATIVE EVIDENCE"]
        remaining_tokens = EVIDENCE_TOKEN_BUDGET
        chunks_added = 0

        for idx, chunk in enumerate(evidence_chunks, 1):
            if chunks_added >= MAX_EVIDENCE_CHUNKS or remaining_tokens <= 0:
                logger.warning(
                    "Evidence digest reached allocation: %s chunks, %s tokens remaining",
                    chunks_added,
                    remaining_tokens,
                )
                break

            source_type = chunk.get("source_type", "unknown").upper()
            source_file = chunk.get("source_file", "unknown")
            summary_text = (chunk.get("summary") or chunk.get("content", ""))[:MAX_EVIDENCE_SUMMARY_CHARS]
            verbatim_text = (
                chunk.get("verbatim")
                or chunk.get("content", "")
            )[:MAX_EVIDENCE_VERBATIM_CHARS]
            similarity = chunk.get("similarity_score")
            citation = (
                chunk.get("metadata", {}).get("citation_id")
                or chunk.get("retrieval_metadata", {}).get("citation_id")
            )

            entry_lines = [f"• [{source_type} {idx}] {source_file}"]
            if similarity is not None:
                entry_lines[0] += f" — relevance {similarity:.2f}"
            entry_lines.extend([
                f"  Summary: {summary_text.strip()}",
                f"  Verbatim: {verbatim_text.strip()}",
            ])
            if citation:
                entry_lines.append(f"  Citation: {citation}")

            entry_text = "\n".join(entry_lines)
            entry_tokens = self._estimate_token_count(entry_text)

            if entry_tokens > remaining_tokens:
                if remaining_tokens < MIN_EVIDENCE_ENTRY_TOKENS:
                    logger.warning(
                        "Skipping remaining evidence due to tight token budget (%s tokens left)",
                        remaining_tokens,
                    )
                    break

                truncated_text = self._truncate_text_to_tokens(entry_text, remaining_tokens)
                entry_tokens = self._estimate_token_count(truncated_text)
                if not truncated_text:
                    break
                formatted.append(truncated_text)
                remaining_tokens -= entry_tokens
                chunks_added += 1
                logger.warning(
                    "Truncated evidence chunk %s to fit remaining budget (%s tokens)",
                    idx,
                    remaining_tokens,
                )
                break

            formatted.append(entry_text)
            remaining_tokens -= entry_tokens
            chunks_added += 1

        if chunks_added == 0:
            formatted.append("⚠️ Evidence available but omitted to respect the prompt budget.")
        elif remaining_tokens <= 0 or len(evidence_chunks) > chunks_added:
            formatted.append("… additional evidence omitted to preserve the token budget …")

        return "\n".join(formatted)

    def _get_assumption_identifier(self, assumption: Dict[str, Any]) -> str:
        candidates = [
            assumption.get("id"),
            assumption.get("assumption_id"),
            assumption.get("uuid"),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        text_value = assumption.get("text")
        if isinstance(text_value, str) and text_value.strip():
            return text_value[:48]
        return "unknown"

    @abstractmethod
    def _get_output_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for structured output validation."""
        pass

    # ------------------------------------------------------------------
    # AI response normalisation helpers
    # ------------------------------------------------------------------

    def _normalise_key(self, key: str) -> str:
        """Normalise dictionary keys for fuzzy matching."""
        if not isinstance(key, str):
            key = str(key)
        return "".join(ch for ch in key.lower() if ch.isalnum())

    def _deep_find_value(
        self,
        payload: Union[Dict[str, Any], List[Any], Tuple[Any, ...]],
        candidate_keys: Iterable[str]
    ) -> Optional[Any]:
        """Search nested payload for the first matching key."""
        if payload is None:
            return None

        normalised_candidates = {self._normalise_key(key) for key in candidate_keys}
        stack: List[Any] = [payload]

        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    normalised_key = self._normalise_key(key)
                    if normalised_key in normalised_candidates:
                        return value

                    if isinstance(value, (dict, list, tuple)):
                        stack.append(value)
            elif isinstance(current, (list, tuple)):
                for item in current:
                    if isinstance(item, (dict, list, tuple)):
                        stack.append(item)

        return None

    def _maybe_parse_json_value(self, value: Any) -> Any:
        """Attempt to parse a JSON string value into Python structures."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped[0] in "[{":
                try:
                    return json.loads(stripped)
                except (json.JSONDecodeError, TypeError):
                    return value
        return value

    def _coerce_to_list(self, value: Any) -> List[Any]:
        """Convert various evidence representations to a list."""
        value = self._maybe_parse_json_value(value)

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, dict):
            flattened: List[Any] = []
            for item in value.values():
                if isinstance(item, (list, tuple)):
                    flattened.extend(item)
                else:
                    flattened.append(item)
            return flattened

        if isinstance(value, str):
            # Split on common bullet/line delimiters while keeping rich evidence
            items: List[str] = []
            for line in value.replace("\r", "").split("\n"):
                cleaned = line.strip(" •-\t")
                if cleaned:
                    items.append(cleaned)
            return items

        if value is None:
            return []

        # Fallback: return the scalar inside a list so callers can format it
        return [value]

    _FAKE_CITATION_PATTERN = re.compile(r"\[(?:CSV|PDF)\s*[0-9,\s]*\]", re.IGNORECASE)

    def _clean_evidence_text(self, text: str) -> str:
        """Remove hallucinated CSV/PDF citations and normalise whitespace."""
        if not isinstance(text, str):
            return ""

        cleaned = self._FAKE_CITATION_PATTERN.sub("", text)
        # Collapse any duplicate whitespace created by removing citations
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _normalise_evidence_items(self, items: Iterable[Any]) -> List[str]:
        """Normalise evidence entries into human-readable strings."""
        normalised: List[str] = []
        seen_lower: Set[str] = set()

        def _append_if_valid(text: str):
            cleaned = self._clean_evidence_text(text)
            lowered = cleaned.lower()
            if cleaned and lowered not in seen_lower:
                seen_lower.add(lowered)
                normalised.append(cleaned)

        for item in items or []:
            if isinstance(item, str):
                _append_if_valid(item)
            elif isinstance(item, (int, float)):
                _append_if_valid(str(item))
            elif isinstance(item, dict):
                # Prefer descriptive fields, otherwise serialise compactly
                for key in ("text", "statement", "summary", "evidence", "detail", "value"):
                    if key in item and isinstance(item[key], (str, int, float)):
                        _append_if_valid(str(item[key]))
                        break
                else:
                    try:
                        _append_if_valid(json.dumps(item, ensure_ascii=False))
                    except (TypeError, ValueError):
                        continue
            elif isinstance(item, (list, tuple)):
                for nested in self._normalise_evidence_items(item):
                    _append_if_valid(nested)

        # Limit runaway evidence lists for safety (production guard)
        return normalised[:20]

    def _extract_numeric_field(self, payload: Dict[str, Any], candidate_keys: Iterable[str]) -> Optional[float]:
        """Extract numeric value from payload."""
        raw_value = self._deep_find_value(payload, candidate_keys)
        raw_value = self._maybe_parse_json_value(raw_value)

        if isinstance(raw_value, (int, float)):
            return float(raw_value)

        if isinstance(raw_value, str):
            try:
                return float(raw_value)
            except ValueError:
                return None

        return None

    def _extract_text_field(self, payload: Dict[str, Any], candidate_keys: Iterable[str]) -> Optional[str]:
        """Extract textual value from payload."""
        raw_value = self._deep_find_value(payload, candidate_keys)
        raw_value = self._maybe_parse_json_value(raw_value)

        if isinstance(raw_value, str):
            cleaned = raw_value.strip()
            return cleaned or None

        if isinstance(raw_value, (int, float)):
            return str(raw_value)

        return None

    def _extract_dict_field(self, payload: Dict[str, Any], candidate_keys: Iterable[str]) -> Dict[str, Any]:
        """Extract dictionary payload by candidate keys."""
        raw_value = self._deep_find_value(payload, candidate_keys)
        raw_value = self._maybe_parse_json_value(raw_value)

        if isinstance(raw_value, dict):
            return raw_value

        return {}

    def _infer_accuracy_level(
        self,
        confidence_score: float,
        supporting_evidence: List[str],
        debunking_evidence: List[str]
    ) -> str:
        """Infer accuracy level using confidence score and evidence balance."""
        confidence_score = confidence_score or 0.0
        support_count = len(supporting_evidence or [])
        debunk_count = len(debunking_evidence or [])

        if confidence_score >= 0.7 and support_count >= 3 and debunk_count == 0:
            return "high"
        if confidence_score >= 0.5 and support_count >= 1:
            return "medium"
        if confidence_score >= 0.4 and support_count >= debunk_count:
            return "medium"
        return "low"
    
    async def analyze_for_assumption(self, state: AssumptionAnalysisState) -> AssumptionAnalysisState:
        """
        Main entry point for analysis agent execution in LangGraph workflow.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with analysis results
        """
        try:
            assumption_id = state['current_assumption'].get('id', 'unknown')
            logger.info(f"🚨 CRITICAL DEBUG: {self.analysis_type} agent CALLED for assumption {assumption_id}")
            logger.info(f"Starting {self.analysis_type} analysis for assumption: {assumption_id}")
            
            # Prepare analysis context
            context = self._prepare_analysis_context(state)
            
            # Create monitoring context for AI usage tracking
            monitoring_context = self._create_monitoring_context(state, f"{self.analysis_type}_analysis")
            
            # Perform the analysis with monitoring context
            analysis_result = await self._analyze_with_context(context, monitoring_context)
            
            # Check if analysis failed and add error to state
            if analysis_result.claim.startswith("Analysis failed due to error:"):
                error_msg = analysis_result.claim.replace("Analysis failed due to error: ", "")
                state["errors"].append(f"{self.analysis_type} analysis failed: {error_msg}")
            
            # Update state with results
            state = self._update_state_with_results(state, analysis_result)
            
            logger.info(f"Completed {self.analysis_type} analysis with confidence: {analysis_result.confidence_score:.2f}")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in {self.analysis_type} analysis: {str(e)}")
            state["errors"].append(f"{self.analysis_type} analysis failed: {str(e)}")
            return state
    
    def _prepare_analysis_context(self, state: AssumptionAnalysisState) -> AnalysisContext:
        """
        Prepare analysis context from workflow state.
        
        Args:
            state: Current workflow state
            
        Returns:
            Analysis context for this agent
        """
        # Prefer the correlation-filtered research data when available. This keeps
        # prompts small and prevents runaway token usage when the raw research
        # corpus is very large. Fall back to the complete chunk list if the
        # filtered data is missing or empty so we preserve backwards
        # compatibility with existing workflows.
        relevant_data = state.get("current_relevant_data")
        if not isinstance(relevant_data, list) or not relevant_data:
            relevant_data = state.get("research_chunks", [])

        # Ensure project_context has project_id and tenant_id
        project_context = state["project_context"].copy()
        project_context["project_id"] = state.get("project_id")
        project_context["tenant_id"] = state.get("tenant_id")
        
        return AnalysisContext(
            assumption=state["current_assumption"],
            persona=state["target_persona"],
            research_data=relevant_data,
            project_context=project_context,
            analysis_type=self.analysis_type,
            statistics_registry=state.get("statistics_registry", {}),
            ground_truth_statistics=state.get("current_ground_truth"),
            evidence_chunks=state.get("current_evidence_chunks"),
            context_flags=state.get("context_flags", {})
        )
    
    def _create_monitoring_context(self, state: AssumptionAnalysisState, step_name: str) -> AIUsageContext:
        """
        Create AI usage monitoring context for tracking token usage.
        
        Args:
            state: Current workflow state
            step_name: Name of the analysis step (e.g., 'pain_analysis', 'gains_analysis')
            
        Returns:
            AIUsageContext for monitoring
        """
        project_context = state.get("project_context", {})
        current_assumption = state.get("current_assumption", {})
        
        return AIUsageContext(
            user_id=project_context.get("user_id"),
            tenant_id=state.get("tenant_id"),
            team_id=project_context.get("team_id"),
            project_id=state.get("project_id"),
            feature_id=f"market_research_{self.analysis_type}",
            workflow_name="market_research_workflow",
            step_name=step_name,
            environment="prod",
            request_id=current_assumption.get("id")
        )
    
    @handle_ai_service_errors
    @monitor_performance("agent_analysis")
    async def _analyze_with_context(self, context: AnalysisContext, monitoring_context: Optional[AIUsageContext] = None) -> AnalysisOutput:
        """
        Perform analysis with the given context using enhanced AI service with fact verification.
        
        Args:
            context: Analysis context containing assumption, persona, and research data
            monitoring_context: Optional AI usage monitoring context for token tracking
            
        Returns:
            Structured analysis output with fact-checking validation
        """
        try:
            # CRITICAL DIAGNOSTIC: Log what data the agent is receiving
            total_chunks = len(context.research_data)
            # 🚨 CRITICAL FIX: Intelligent source type detection in agents
            csv_chunks = []
            pdf_chunks = []
            
            for chunk in context.research_data:
                chunk_content = str(chunk.get('content', '')).lower()
                original_source_type = chunk.get('source_type', 'unknown')
                
                # Intelligent detection based on content patterns
                is_csv_data = any([
                    'respondent_id:' in chunk_content,
                    'submission_date:' in chunk_content,
                    'survey data with' in chunk_content,
                    'responses and' in chunk_content,
                    'county:' in chunk_content and 'household_size:' in chunk_content
                ])
                
                is_pdf_data = any([
                    'interview transcript' in chunk_content,
                    'interviewer:' in chunk_content,
                    'interviewee:' in chunk_content
                ])
                
                # Classify intelligently
                if is_csv_data:
                    csv_chunks.append(chunk)
                    if original_source_type != 'csv':
                        logger.info(f"🔧 AGENT FIX: Reclassified chunk from '{original_source_type}' to 'csv' based on content")
                elif is_pdf_data:
                    pdf_chunks.append(chunk)
                    if original_source_type != 'pdf':
                        logger.info(f"🔧 AGENT FIX: Reclassified chunk from '{original_source_type}' to 'pdf' based on content")
                else:
                    # Fallback to original classification
                    if original_source_type == 'csv':
                        csv_chunks.append(chunk)
                    else:
                        pdf_chunks.append(chunk)
            
            logger.info(f"🔍 AGENT INPUT: {self.analysis_type} agent received {total_chunks} total chunks")
            logger.info(f"🔍 AGENT INPUT: - CSV chunks: {len(csv_chunks)} (intelligently detected)")
            logger.info(f"🔍 AGENT INPUT: - PDF chunks: {len(pdf_chunks)} (intelligently detected)")
            
            # CRITICAL FIX: Use statistics registry from workflow state (not database)
            statistics_registry = getattr(context, 'statistics_registry', None)
            if statistics_registry:
                logger.info(f"🔍 FACT CHECK: Using statistics registry from workflow state")
                # Debug statistics registry content
                if hasattr(statistics_registry, 'statistics') and statistics_registry.statistics:
                    stats_count = len(statistics_registry.statistics)
                    logger.info(f"🔍 STATS REGISTRY DEBUG: Contains {stats_count} statistics entries")
                elif isinstance(statistics_registry, dict) and statistics_registry.get('csv_statistics'):
                    stats_count = len(statistics_registry.get('csv_statistics', {}))
                    logger.info(f"🔍 STATS REGISTRY DEBUG: Contains {stats_count} CSV statistics entries")
                else:
                    logger.warning(f"⚠️ STATS REGISTRY DEBUG: Registry exists but has no statistics data")
                    # CRITICAL FIX: If registry is empty, populate it with our CSV aggregation
                    if not statistics_registry or not isinstance(statistics_registry, dict):
                        statistics_registry = {}
                    
                    # Add CSV aggregation to statistics registry - use already classified chunks
                    # csv_chunks already classified above with intelligent detection
                    if csv_chunks:
                        csv_stats = await self._aggregate_csv_statistical_data(csv_chunks)
                        statistics_registry['csv_statistics'] = csv_stats.get('percentages', {})
                        statistics_registry['sample_sizes'] = {'total_responses': csv_stats.get('total_responses', 0)}
                        logger.info(f"🔧 EMERGENCY FIX: Populated empty registry with {len(csv_stats.get('percentages', {}))} CSV statistics")
            else:
                logger.error(f"❌ FACT CHECK: No statistics registry in workflow state - this should not happen")
            
            # FACTUALNESS ENHANCEMENT: Extract verifiable facts before AI generation (fallback)
            verifiable_facts = await self._extract_verifiable_facts(context.research_data)
            logger.info(f"🔍 FACT CHECK: Extracted {len(verifiable_facts['percentages'])} percentages, "
                       f"{len(verifiable_facts['sample_sizes'])} sample sizes from {len(verifiable_facts['sources'])} sources")
            
            prompt_bundle = await self._create_two_tier_analysis_prompt(context)
            logger.info(f"Using enhanced two-tier RAG prompt for {self.analysis_type} analysis")

            context_and_notes = (
                f"{prompt_bundle['context_block']}\n\n{prompt_bundle['notes_instruction']}"
            )
            notes_messages = [
                {"role": "system", "content": prompt_bundle["system_prompt"]},
                {"role": "user", "content": context_and_notes},
            ]

            notes_response = await self.ai_service_wrapper.generate_analysis_response(
                messages=notes_messages,
                model="gpt-5-mini",
                max_completion_tokens=16000,  # gpt-5-mini needs large token budget for reasoning
                json_mode=False,
                monitoring_context=monitoring_context
            )

            initial_findings = ""
            if isinstance(notes_response, dict):
                initial_findings = str(notes_response.get("content", "")).strip()
            else:
                initial_findings = str(notes_response).strip()

            if not initial_findings:
                initial_findings = "No initial findings were generated."

            summary_prompt = "\n\n".join(
                [
                    prompt_bundle["context_block"],
                    "INITIAL FINDINGS:\n" + initial_findings,
                    prompt_bundle["summary_instruction"],
                ]
            )
            summary_messages = [
                {"role": "system", "content": prompt_bundle["system_prompt"]},
                {"role": "user", "content": summary_prompt},
            ]

            total_tokens = self._estimate_prompt_tokens(summary_messages)
            if total_tokens > MAX_TOTAL_INPUT_BUDGET:
                logger.warning(
                    f"Prompt exceeds budget for {self.analysis_type}: {total_tokens} tokens (limit: {MAX_TOTAL_INPUT_BUDGET})"
                )
                summary_messages = self._truncate_prompt_if_needed(summary_messages)
            else:
                logger.info(
                    f"✅ Prompt within budget for {self.analysis_type}: {total_tokens}/{MAX_TOTAL_INPUT_BUDGET} tokens"
                )

            if self.fallback_enabled:
                response = await self.ai_service_wrapper.generate_with_fallback(
                    messages=summary_messages,
                    fallback_key="partial_analysis",
                    model="gpt-5-mini",
                    max_completion_tokens=16000,  # gpt-5-mini needs large token budget for reasoning
                    json_mode=True,
                    monitoring_context=monitoring_context
                )
            else:
                response = await self.ai_service_wrapper.generate_analysis_response(
                    messages=summary_messages,
                    model="gpt-5-mini",
                    max_completion_tokens=16000,  # gpt-5-mini needs large token budget for reasoning
                    json_mode=True,
                    monitoring_context=monitoring_context
                )

            if response.get("fallback", False):
                logger.warning(
                    f"Fallback used for {self.analysis_type} analysis: {response.get('error', 'Unknown error')}"
                )
                return self._create_fallback_analysis(context, response.get("error", "Service unavailable"))

            analysis_output = self._parse_ai_response(response)

            # ENHANCED FACT VALIDATION: Use new fact validation engine
            ai_response_text = str(response.get("content", ""))
            fact_validation = await self._perform_enhanced_fact_validation(
                ai_response_text, statistics_registry, verifiable_facts
            )
            
            # Add fact-checking results to analysis output
            if hasattr(analysis_output, 'statistical_data'):
                if isinstance(analysis_output.statistical_data, dict):
                    analysis_output.statistical_data["fact_validation"] = fact_validation
                else:
                    # If statistical_data is not a dict, create new dict with validation
                    analysis_output.statistical_data = {
                        "original_data": analysis_output.statistical_data,
                        "fact_validation": fact_validation
                    }
            
            # Populate new validation fields
            analysis_output.fact_validation_score = fact_validation["fact_check_score"]
            metadata_payload = {**fact_validation, "initial_findings": initial_findings}
            if context.context_flags:
                metadata_payload["context_flags"] = context.context_flags
            analysis_output.validation_metadata = metadata_payload
            
            # Extract citation IDs from validation results if available
            if "validation_details" in fact_validation:
                citation_ids = []
                for detail in fact_validation["validation_details"]:
                    if detail.get("registry_match") and detail["registry_match"].get("citation_id"):
                        citation_ids.append(detail["registry_match"]["citation_id"])
                if citation_ids:
                    analysis_output.citation_ids = list(set(citation_ids))  # Remove duplicates
            
            # Calculate persona relevance score if persona context is available
            if context.persona:
                persona_relevance = self._calculate_persona_relevance(
                    analysis_output.claim, context.persona
                )
                analysis_output.persona_relevance_score = persona_relevance
            
            # Adjust confidence score based on enhanced fact-checking
            original_confidence = analysis_output.confidence_score
            fact_check_score = fact_validation["fact_check_score"]
            
            logger.info(f"🔍 CONFIDENCE FLOW DEBUG: Before adjustment - original: {original_confidence:.3f}, fact_check_score: {fact_check_score:.3f}")
            
            adjusted_confidence = self.fact_validator.adjust_confidence_score(
                original_confidence, fact_check_score, fact_validation
            )
            analysis_output.confidence_score = adjusted_confidence
            
            logger.info(f"🔍 CONFIDENCE FLOW DEBUG: After adjustment - final: {adjusted_confidence:.3f}")
            
            # Log enhanced fact-checking results
            if fact_validation["unsupported_claims"]:
                logger.warning(f"🚨 ENHANCED FACT CHECK: Found {len(fact_validation['unsupported_claims'])} unsupported claims")
                logger.warning(f"🚨 UNSUPPORTED: {fact_validation['unsupported_claims']}")
            
            if fact_validation["questionable_claims"]:
                logger.warning(f"⚠️ ENHANCED FACT CHECK: Found {len(fact_validation['questionable_claims'])} questionable claims")
                logger.warning(f"⚠️ QUESTIONABLE: {fact_validation['questionable_claims']}")
            
            logger.info(f"✅ ENHANCED FACT CHECK: Score {fact_check_score:.2f}, Confidence adjusted: {original_confidence:.2f} → {adjusted_confidence:.2f}")

            analysis_output = self._finalize_analysis_output(analysis_output, context)

            return analysis_output
            
        except (AIServiceError, TokenLimitError, RateLimitError) as e:
            logger.error(f"AI service error in {self.analysis_type} analysis: {str(e)}")
            
            # Record the error
            error_monitor.record_error(
                e,
                ErrorCategory.AI_SERVICE,
                ErrorSeverity.HIGH,
                {"analysis_type": self.analysis_type, "assumption_id": context.assumption.get("id")}
            )
            
            # Return fallback analysis
            return self._create_fallback_analysis(context, str(e))
            
        except Exception as e:
            logger.error(f"Unexpected error in AI analysis for {self.analysis_type}: {str(e)}")
            
            # Record unexpected error
            error_monitor.record_error(
                e,
                ErrorCategory.AI_SERVICE,
                ErrorSeverity.HIGH,
                {"analysis_type": self.analysis_type, "error_type": "unexpected"}
            )
            
            # Return fallback analysis
            return self._create_fallback_analysis(context, f"Unexpected error: {str(e)}")
    
    def _truncate_prompt_if_needed(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Truncate prompt content if it's too large for AI service
        
        Args:
            messages: Original messages
            
        Returns:
            Truncated messages if needed
        """
        truncated_messages = []
        total_length = 0
        max_length = 40000  # Conservative limit
        
        for message in messages:
            content = message.get("content", "")
            
            if message.get("role") == "system":
                # Always include system message
                truncated_messages.append(message)
                total_length += len(content)
            elif total_length + len(content) <= max_length:
                # Include full message if within limit
                truncated_messages.append(message)
                total_length += len(content)
            else:
                # Truncate this message
                remaining_space = max_length - total_length
                if remaining_space > 1000:  # Only truncate if we have reasonable space
                    truncated_content = content[:remaining_space] + "\n\n[Content truncated due to length...]"
                    truncated_messages.append({
                        **message,
                        "content": truncated_content
                    })
                break
        
        if len(truncated_messages) < len(messages):
            logger.warning(f"Truncated prompt from {len(messages)} to {len(truncated_messages)} messages")

        return truncated_messages

    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for a block of text using a 4 chars/token heuristic."""

        if not text:
            return 0

        # Ensure we always count at least one token for non-empty text
        return max(1, len(text) // 4)
    
    def _estimate_prompt_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate total token count for a complete prompt (all messages)."""
        total_tokens = 0
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")
            # Add tokens for content + overhead for message structure
            total_tokens += self._estimate_token_count(content)
            total_tokens += 4  # Overhead for role, message structure
        return total_tokens

    def _truncate_text_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within a token budget while keeping whole sentences when possible."""

        if max_tokens <= 0 or not text:
            return ""

        approx_chars = max_tokens * 4
        if len(text) <= approx_chars:
            return text

        truncated = text[:approx_chars]

        # Try to avoid cutting mid-sentence
        last_period = truncated.rfind(". ")
        last_space = truncated.rfind(" ")
        cut_point = max(last_period, last_space)
        if cut_point > 0:
            truncated = truncated[:cut_point]

        truncated = truncated.rstrip()
        return f"{truncated}\n[Content truncated to fit token budget]"

    def _append_with_budget(
        self,
        entries: List[str],
        text: str,
        remaining_tokens: int,
        label: str,
        *,
        force: bool = False,
        min_tokens: int = 80
    ) -> Tuple[int, bool]:
        """Append text to the entries list if it fits within the remaining token budget."""

        if not text:
            return remaining_tokens, False

        estimated_tokens = self._estimate_token_count(text)

        if estimated_tokens <= remaining_tokens:
            entries.append(text)
            return remaining_tokens - estimated_tokens, True

        if force and remaining_tokens >= min_tokens:
            truncated_text = self._truncate_text_to_tokens(text, remaining_tokens)
            if truncated_text:
                entries.append(truncated_text)
                logger.warning(
                    "Token budget exceeded for %s – truncated to fit remaining %s tokens",
                    label,
                    remaining_tokens
                )
                return 0, True

        logger.warning(
            "Skipped %s because it requires %s tokens with only %s tokens remaining",
            label,
            estimated_tokens,
            remaining_tokens
        )
        return remaining_tokens, False

    def _get_chunk_token_estimate(self, chunk: Dict[str, Any]) -> int:
        """Return an estimated token count for a research chunk."""

        token_count = chunk.get("token_count") or chunk.get("metadata", {}).get("token_count")
        if isinstance(token_count, (int, float)):
            return int(token_count)

        return self._estimate_token_count(chunk.get("content", ""))

    def _create_fallback_analysis(self, context: AnalysisContext, error_message: str) -> AnalysisOutput:
        """
        Create a fallback analysis when AI service fails

        Args:
            context: Analysis context
            error_message: Error that caused fallback

        Returns:
            Fallback analysis output
        """
        # Create basic analysis based on available data
        research_data_count = len(context.research_data) if context.research_data else 0

        fallback_claim = f"Unable to complete {self.analysis_type} analysis due to service limitations. "
        fallback_claim += f"Analysis was attempted with {research_data_count} research data points."

        return AnalysisOutput(
            claim=fallback_claim,
            accuracy_level="low",
            supporting_evidence=[f"Service error: {error_message}"],
            debunking_evidence=[],
            statistical_data={"error": "analysis_failed", "research_data_count": research_data_count},
            confidence_score=0.1  # Very low confidence for fallback
        )

    def _describe_chunk_source(self, chunk: Dict[str, Any]) -> str:
        """Return a human-readable label for a research chunk source."""

        metadata = chunk.get("metadata", {}) or {}
        filename = metadata.get("filename") or chunk.get("source_filename")
        section = metadata.get("section") or chunk.get("section_label")

        if chunk.get("is_summary_chunk") and not section:
            section = "quantitative_highlights"

        parts: List[str] = []

        if filename:
            parts.append(filename)

        if section:
            if section == "quantitative_highlights":
                parts.append("Quantitative Highlights")
            else:
                formatted_section = section.replace("_", " ").title()
                parts.append(formatted_section)

        return " – ".join(parts)
    
    def _format_research_content_balanced(
        self, 
        research_data: List[Dict[str, Any]], 
        analysis_type: str = "analysis"
    ) -> str:
        """
        Format research data ensuring balanced representation of all data sources.
        
        This method ensures that both CSV survey data and PDF interview data are 
        properly represented in the analysis, preventing bias toward one data type.
        
        Args:
            research_data: List of research chunks
            analysis_type: Type of analysis for labeling (e.g., "pain", "gains")
            
        Returns:
            Formatted research content string with balanced data representation
        """
        if not research_data:
            return "No research data available."
        
        # CRITICAL FIX: Ensure balanced representation of CSV and PDF data
        # Separate chunks by source type
        pdf_chunks = [chunk for chunk in research_data if chunk.get('source_type') == 'pdf']
        csv_chunks = [chunk for chunk in research_data if chunk.get('source_type') == 'csv']
        
        # 🔧 CRITICAL: Count unique FILES, not chunks/segments
        pdf_files = set()
        for chunk in pdf_chunks:
            filename = (
                chunk.get("source_filename") or 
                chunk.get("source_document") or 
                chunk.get("metadata", {}).get("filename") or
                chunk.get("metadata", {}).get("source_filename") or
                "unknown"
            )
            if filename != "unknown":
                pdf_files.add(filename)
        
        total_interview_files = len(pdf_files)
        
        # CRITICAL: Extract actual survey sample size from CSV metadata
        total_survey_respondents = 0
        for chunk in csv_chunks:
            metadata = chunk.get('metadata', {})
            if 'row_count' in metadata:
                total_survey_respondents = max(total_survey_respondents, metadata.get('row_count', 0))
        
        formatted_content: List[str] = []
        remaining_tokens = DATA_TOKEN_BUDGET
        csv_summary_added = 0
        csv_data_added = 0
        pdf_added = 0

        # 🔧 CRITICAL STATISTICAL CONTEXT: Add file count for interviews
        if total_interview_files > 0:
            remaining_tokens, _ = self._append_with_budget(
                formatted_content,
                (
                    "═══════════════════════════════════════════════════════════════════════════════\n"
                    "📊 CRITICAL STATISTICAL CONTEXT - INTERVIEW FILES\n"
                    "═══════════════════════════════════════════════════════════════════════════════\n"
                    f"TOTAL INTERVIEW FILES: {total_interview_files} interview documents\n\n"
                    "⚠️ CRITICAL: When calculating percentages for interviews, use FILE COUNT, NOT segment/chunk count.\n"
                    f"Example: If 3 files mention a theme, say '60% (3/{total_interview_files} files)' NOT '7% (3/41 segments)'.\n"
                    "Each interview file represents ONE participant/interviewee.\n"
                    "Multiple segments/chunks from the same file = SAME participant = count as 1.\n"
                    "═══════════════════════════════════════════════════════════════════════════════\n"
                ),
                remaining_tokens,
                label="interview_file_context",
                force=True
            )
        
        # CRITICAL STATISTICAL CONTEXT: Add survey sample size information
        if total_survey_respondents > 0:
            remaining_tokens, _ = self._append_with_budget(
                formatted_content,
                (
                    "═══════════════════════════════════════════════════════════════════════════════\n"
                    "📊 CRITICAL STATISTICAL CONTEXT - SURVEY DATA\n"
                    "═══════════════════════════════════════════════════════════════════════════════\n"
                    f"TOTAL SURVEY SAMPLE SIZE: {total_survey_respondents} respondents\n\n"
                    "⚠️ IMPORTANT: When calculating percentages, you are analyzing a SUBSET of the full survey.\n"
                    f"If you analyze 4 responses, DO NOT say '100% (4/4)' - instead say '2% (4/{total_survey_respondents})'.\n"
                    "Always use the TOTAL SURVEY SAMPLE SIZE ({total_survey_respondents}) as your denominator, not the number of chunks you're analyzing.\n"
                    "═══════════════════════════════════════════════════════════════════════════════\n"
                ),
                remaining_tokens,
                label="survey_context",
                force=True
            )

        # Always include CSV summary chunks first (quantitative highlights)
        csv_summary_chunks = [chunk for chunk in csv_chunks if chunk.get('is_summary_chunk')]
        csv_data_chunks = [chunk for chunk in csv_chunks if not chunk.get('is_summary_chunk')]

        # Add CSV summary chunks (quantitative highlights)
        for idx, chunk in enumerate(csv_summary_chunks[:2]):  # Max 2 summary chunks
            content = chunk.get("content", "")
            source_info = self._describe_chunk_source(chunk)
            prefix = "[Survey Highlights]"
            if source_info:
                prefix += f" (Source: {source_info})"
            remaining_tokens, added = self._append_with_budget(
                formatted_content,
                f"{prefix}: {content}",
                remaining_tokens,
                label=f"csv_summary_{idx+1}",
                force=idx == 0  # Ensure at least one quantitative highlight is included
            )
            if added:
                csv_summary_added += 1
            else:
                break

        # Add balanced mix of CSV data chunks and PDF chunks
        # SMART TOKEN BUDGET: Calculate how many chunks we can fit within the
        # DATA_TOKEN_BUDGET (~4k tokens after accounting for prompt structure).
        # This is the ACTUAL space available for research data content.
        max_data_tokens = DATA_TOKEN_BUDGET
        avg_tokens_per_chunk = 250  # Conservative estimate
        max_chunks_for_data = max_data_tokens // avg_tokens_per_chunk  # ~16 chunks with 4k budget
        
        # Distribute chunks proportionally between CSV and PDF
        total_data_chunks = len(csv_data_chunks) + len(pdf_chunks)
        if total_data_chunks > 0:
            csv_ratio = len(csv_data_chunks) / total_data_chunks
            max_csv = int(max_chunks_for_data * csv_ratio)
            max_pdf = max_chunks_for_data - max_csv
        else:
            max_csv = max_chunks_for_data // 2
            max_pdf = max_chunks_for_data // 2
        
        selected_csv_data = sorted(csv_data_chunks[:max_csv], key=self._get_chunk_token_estimate)
        selected_pdf = sorted(pdf_chunks[:max_pdf], key=self._get_chunk_token_estimate)
        
        logger.info(
            "🔍 TOKEN BUDGET: Selected %s CSV + %s PDF chunks (max %s for %s token DATA budget)",
            len(selected_csv_data),
            len(selected_pdf),
            max_chunks_for_data,
            DATA_TOKEN_BUDGET,
        )
        logger.info(
            "📊 TOTAL BUDGET: %s tokens = %s (system) + %s (structure) + %s (data) + %s (response)",
            MAX_TOTAL_INPUT_BUDGET,
            SYSTEM_PROMPT_TOKEN_RESERVE,
            USER_PROMPT_STRUCTURE_RESERVE,
            DATA_TOKEN_BUDGET,
            AI_RESPONSE_TOKEN_RESERVE,
        )
        
        # Add CSV survey response chunks
        for i, chunk in enumerate(selected_csv_data):
            if remaining_tokens <= 0:
                logger.warning("Token budget exhausted before including all CSV survey chunks")
                break
            content = chunk.get("content", "")
            source_info = self._describe_chunk_source(chunk)
            prefix = f"[Survey Data {i+1}]"
            if source_info:
                prefix += f" (Source: {source_info})"
            remaining_tokens, added = self._append_with_budget(
                formatted_content,
                f"{prefix}: {content}",
                remaining_tokens,
                label=f"csv_data_{i+1}"
            )
            if added:
                csv_data_added += 1
            else:
                break

        # Add PDF interview chunks
        for i, chunk in enumerate(selected_pdf):
            if remaining_tokens <= 0:
                logger.warning("Token budget exhausted before including interview excerpts")
                break
            content = chunk.get("content", "")
            source_info = self._describe_chunk_source(chunk)
            prefix = f"[Interview {i+1}]"
            if source_info:
                prefix += f" (Source: {source_info})"
            remaining_tokens, added = self._append_with_budget(
                formatted_content,
                f"{prefix}: {content}",
                remaining_tokens,
                label=f"pdf_interview_{i+1}"
            )
            if added:
                pdf_added += 1
            else:
                break

        # Log the data balance for debugging
        total_chunks = len(formatted_content)
        tokens_used = DATA_TOKEN_BUDGET - max(0, remaining_tokens)
        logger.info(
            "🔍 %s ANALYSIS DATA BALANCE: %s entries (summaries: %s, csv: %s, pdf: %s) using ~%s tokens (budget %s)",
            analysis_type.upper(),
            total_chunks,
            csv_summary_added,
            csv_data_added,
            pdf_added,
            tokens_used,
            DATA_TOKEN_BUDGET,
        )
        if remaining_tokens <= 0:
            logger.warning("Token budget fully consumed for %s analysis context", analysis_type)

        return "\n\n".join(formatted_content)
    
    async def _extract_verifiable_facts(self, research_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract verifiable facts and statistics from research data for fact-checking.
        
        Args:
            research_data: List of research chunks
            
        Returns:
            Dictionary of verifiable facts that can be used for validation
        """
        facts = {
            "sample_sizes": {},
            "percentages": [],
            "numbers": [],
            "quotes": [],
            "demographics": {},
            "sources": set(),
            "csv_aggregations": {}  # For CSV statistical aggregations
        }
        
        import re
        
        for chunk in research_data:
            content = chunk.get("content", "")
            source_type = chunk.get("source_type", "unknown")
            filename = chunk.get("source_filename", "unknown")
            
            facts["sources"].add(f"{source_type}:{filename}")
            
            # Debug content format for first few chunks
            if len(facts["sources"]) <= 3:
                logger.info(f"🔍 STATS EXTRACTION DEBUG: {source_type} chunk preview: {content[:200]}...")
            
            # Extract sample sizes
            sample_patterns = [
                r'(\d+)\s+(?:respondents?|participants?|people|individuals)',
                r'(?:sample|n)\s*=\s*(\d+)',
                r'total\s+(?:of\s+)?(\d+)\s+(?:responses?|surveys?)'
            ]
            
            for pattern in sample_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    size = int(match)
                    facts["sample_sizes"][filename] = max(facts["sample_sizes"].get(filename, 0), size)
            
            # Extract percentages with multiple patterns
            percentage_patterns = [
                r'(\d+(?:\.\d+)?)\s*%',  # Standard: 25%
                r'(\d+(?:\.\d+)?)\s*percent',  # Written: 25 percent
                r'(\d+(?:\.\d+)?)/100',  # Fraction: 25/100
                r'0\.(\d{1,2})\b',  # Decimal: 0.25 -> 25%
            ]
            
            for pattern in percentage_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if pattern == r'0\.(\d{1,2})\b':
                        # Convert decimal to percentage
                        facts["percentages"].append(float(match))
                    else:
                        facts["percentages"].append(float(match))
            
            # Debug percentage extraction for first chunk
            if len(facts["sources"]) == 1:
                current_percentages = len(facts["percentages"])
                if current_percentages > 0:
                    logger.info(f"🔍 PERCENTAGE DEBUG: Found {current_percentages} percentages in first chunk")
            
            # Extract other numbers
            number_matches = re.findall(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b', content)
            facts["numbers"].extend([n.replace(',', '') for n in number_matches])
            
            # Extract direct quotes for evidence
            quote_matches = re.findall(r'["\']([^"\']{20,200})["\']', content)
            facts["quotes"].extend(quote_matches[:3])  # Limit to 3 quotes per chunk
            
            # Extract demographic information
            demo_patterns = {
                'gender': r'(?:female|male|women|men).*?(\d+(?:\.\d+)?)\s*%',
                'age': r'age.*?(\d+(?:\.\d+)?)',
                'occupation': r'(?:occupation|job|work).*?(\w+)'
            }
            
            for demo_type, pattern in demo_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches and demo_type not in facts["demographics"]:
                    facts["demographics"][demo_type] = matches[:2]  # Limit to 2 matches
        
        # ✅ PROPER CSV DETECTION: Use actual chunk metadata, not content keywords
        csv_chunks = []
        pdf_chunks = []
        unknown_chunks = []
        
        for chunk in research_data:
            # Check chunk metadata for actual source type
            chunk_source_type = None
            
            # Priority 1: Direct source_type field
            if 'source_type' in chunk:
                chunk_source_type = chunk['source_type']
            # Priority 2: Metadata dict
            elif 'metadata' in chunk and isinstance(chunk['metadata'], dict):
                chunk_source_type = chunk['metadata'].get('source_type') or chunk['metadata'].get('type')
            # Priority 3: Source filename extension
            elif 'source_filename' in chunk:
                filename = chunk['source_filename'].lower()
                if filename.endswith('.csv'):
                    chunk_source_type = 'csv'
                elif filename.endswith('.pdf'):
                    chunk_source_type = 'pdf'
            
            # Classify chunk based on actual metadata
            if chunk_source_type == 'csv':
                csv_chunks.append(chunk)
            elif chunk_source_type == 'pdf':
                pdf_chunks.append(chunk)
            else:
                unknown_chunks.append(chunk)
        
        logger.info(f"🔧 SOURCE TYPE DEBUG: Found {len(csv_chunks)} CSV, {len(pdf_chunks)} PDF, {len(unknown_chunks)} unknown chunks out of {len(research_data)} total")
        
        if csv_chunks:
            csv_stats = await self._aggregate_csv_statistical_data(csv_chunks)
            facts["csv_aggregations"] = csv_stats
            
            logger.info(f"🔧 CSV STATS DEBUG: Generated stats from {len(csv_chunks)} actual CSV chunks")
            
            # Add aggregated percentages to main percentages list
            for stat_name, percentage in csv_stats.get("percentages", {}).items():
                facts["percentages"].append(percentage)
                
            # Add sample size from CSV aggregation
            if csv_stats.get("total_responses"):
                facts["sample_sizes"]["csv_survey"] = csv_stats["total_responses"]
                
            logger.info(f"🔧 CSV AGGREGATION: Generated {len(csv_stats.get('percentages', {}))} percentage statistics from actual CSV data")
        else:
            logger.info(f"✅ NO CSV DATA: No CSV chunks found - this is expected for PDF-only analysis")
        
        # Convert set to list for JSON serialization
        facts["sources"] = list(facts["sources"])
        
        return facts
    
    async def _aggregate_csv_statistical_data(self, csv_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLM-POWERED CSV statistical analysis using prompt templates.
        Replaces hardcoded regex parsing with intelligent AI-driven analysis.
        
        Args:
            csv_chunks: List of CSV data chunks
            
        Returns:
            Dictionary with aggregated statistics extracted by LLM
        """
        stats = {
            "percentages": {},
            "total_responses": 0,
            "demographics": {},
            "response_patterns": {},
            "field_distributions": {}
        }
        
        if not csv_chunks:
            logger.info("✅ NO CSV DATA: No CSV chunks to analyze")
            return stats
        
        logger.info(f"🤖 LLM CSV ANALYSIS: Processing {len(csv_chunks)} CSV chunks with AI")
        
        try:
            # Use LLM to analyze CSV structure and extract statistics
            csv_stats = await self._llm_analyze_csv_statistics(csv_chunks)
            
            if csv_stats:
                stats.update(csv_stats)
                logger.info(f"✅ LLM CSV ANALYSIS: Extracted {stats.get('total_responses', 0)} responses, "
                          f"{len(stats.get('percentages', {}))} statistical measures")
            else:
                logger.warning("⚠️ LLM CSV ANALYSIS: No statistics extracted")
                
        except Exception as e:
            logger.error(f"❌ LLM CSV ANALYSIS ERROR: {e}")
            # Fallback to basic counting if LLM fails
            stats["total_responses"] = len(csv_chunks)
        
        return stats
    
    async def _llm_analyze_csv_statistics(self, csv_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use LLM with prompt template to intelligently extract statistics from CSV data.
        
        Args:
            csv_chunks: List of CSV data chunks
            
        Returns:
            Dictionary with extracted statistics
        """
        # Sample chunks for analysis (use first 50 for efficiency)
        sample_chunks = csv_chunks[:50] if len(csv_chunks) > 50 else csv_chunks
        
        # Prepare CSV data for LLM
        csv_sample = "\n\n".join([
            f"Record {i+1}:\n{chunk.get('content', '')[:500]}"
            for i, chunk in enumerate(sample_chunks[:10])  # Show first 10 records
        ])
        
        # Get total count
        total_records = len(csv_chunks)
        
        # LLM PROMPT TEMPLATE for CSV statistical analysis
        system_prompt = """You are a data analyst specializing in extracting statistical insights from survey data.

Your task is to analyze CSV survey data and extract key demographic and response statistics.

IMPORTANT RULES:
1. Identify the data fields present in the CSV (age, gender, location, occupation, etc.)
2. Calculate percentage distributions for categorical fields
3. Identify age groups and their distributions
4. Extract any frequency patterns or common responses
5. Return ONLY valid JSON - no markdown, no explanations
6. Use the exact field names found in the data
7. If a field is missing or unclear, skip it

Output format:
{
  "total_responses": <number>,
  "percentages": {
    "field_name_value": <percentage>,
    "gender_male": 45.5,
    "gender_female": 54.5,
    "age_18_30": 25.0,
    "age_31_40": 35.0,
    "location_nairobi": 20.0
  },
  "demographics": {
    "gender_distribution": {"male": 45.5, "female": 54.5},
    "age_groups": {"18-30": 25.0, "31-40": 35.0, "41-50": 25.0, "50+": 15.0}
  },
  "field_distributions": {
    "main_crop": {"maize": 40.0, "avocado": 25.0, "sunflower": 20.0},
    "county": {"nairobi": 20.0, "kisumu": 15.0}
  }
}"""
        
        user_prompt = f"""Analyze this CSV survey data and extract statistical distributions.

TOTAL RECORDS IN DATASET: {total_records}

SAMPLE RECORDS (first 10 of {total_records}):
{csv_sample}

Extract:
1. Total response count: {total_records}
2. Percentage distributions for all categorical fields (gender, age groups, locations, occupations, crops, etc.)
3. Demographic breakdowns
4. Any other relevant statistical patterns

Return ONLY the JSON object with statistics. Use the EXACT field names from the data."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            import asyncio
            
            logger.info(f"🚀 CALLING LLM: Starting CSV analysis with {len(messages)} messages")
            
            # Call LLM with JSON mode and timeout
            try:
                response = await asyncio.wait_for(
                    self.ai_service_wrapper.generate_analysis_response(
                        messages=messages,
                        model="gpt-5-mini",
                        max_completion_tokens=16000,  # gpt-5-mini needs large token budget for reasoning
                        json_mode=True
                    ),
                    timeout=120.0  # 120 second timeout
                )
                logger.info(f"✅ LLM RESPONSE RECEIVED: {type(response)}")
            except asyncio.TimeoutError:
                logger.error(f"❌ LLM CSV ANALYSIS TIMEOUT: Call exceeded 120 seconds")
                return {"total_responses": total_records}
            
            # Parse LLM response
            if isinstance(response, dict):
                content = response.get("content", "{}")
            else:
                content = str(response)
            
            logger.info(f"📄 LLM CONTENT LENGTH: {len(content)} characters")
            
            # Parse JSON response
            import json
            stats = json.loads(content)
            
            # Ensure total_responses is set correctly
            stats["total_responses"] = total_records
            
            logger.info(f"✅ LLM CSV STATS: Extracted {len(stats.get('percentages', {}))} percentage measures")
            
            return stats
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ LLM CSV JSON PARSE ERROR: {e}")
            logger.error(f"❌ CONTENT WAS: {content[:500] if 'content' in locals() else 'N/A'}")
            return {"total_responses": total_records}
        except Exception as e:
            logger.error(f"❌ LLM CSV ANALYSIS ERROR: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            return {"total_responses": total_records}
    
    async def _perform_enhanced_fact_validation(
        self,
        ai_response: str,
        statistics_registry: Optional[Dict[str, Any]],
        verifiable_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform enhanced fact validation using the new fact validation engine.
        
        Args:
            ai_response: AI-generated analysis response
            statistics_registry: Statistics registry from two-tier RAG system
            verifiable_facts: Fallback verifiable facts from chunks
            
        Returns:
            Enhanced validation results
        """
        try:
            claims = self.fact_validator.extract_quantitative_claims(ai_response)

            if not self._registry_has_statistics(statistics_registry):
                logger.warning("⚠️ FACT VALIDATION: Statistics registry missing or empty, attempting runtime synthesis")
                runtime_registry = self._build_registry_from_verifiable_facts(verifiable_facts)
                if runtime_registry:
                    statistics_registry = runtime_registry
                    logger.info("🛠️ FACT VALIDATION: Using runtime statistics derived from verifiable facts")
                else:
                    logger.warning(
                        "⚠️ FACT VALIDATION: Unable to construct runtime registry – treating analysis as qualitative"
                    )
                    return {
                        "fact_check_score": 0.6 if claims else 0.75,
                        "valid_claims": [],
                        "unsupported_claims": [],
                        "questionable_claims": [c.claim_text for c in claims] if claims else [],
                        "validation_details": [],
                        "total_claims": len(claims),
                        "validation_method": "qualitative_only",
                        "claims_extracted": len(claims),
                        "validated_at": datetime.utcnow().isoformat(),
                        "notes": "No ground-truth statistics available; claims require qualitative review",
                    }

            # Use enhanced fact validation engine with statistics registry
            validation_results = self.fact_validator.validate_claims_against_registry(
                claims, statistics_registry
            )

            # Add validation metadata
            validation_results["validation_method"] = "enhanced_registry"
            validation_results["claims_extracted"] = len(claims)
            
            logger.info(f"✅ Enhanced fact validation completed: {len(claims)} claims extracted")
            return validation_results
                
        except Exception as e:
            logger.error(f"❌ CRITICAL: Enhanced fact validation failed: {e}")
            # Fail-fast: Enhanced processing is required
            raise ValueError(f"Enhanced fact validation failed. Legacy fallback removed: {str(e)}")
    
    # Legacy validation method removed - enhanced processing only

    @staticmethod
    def _registry_has_statistics(statistics_registry: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(statistics_registry, dict):
            return False

        csv_stats = statistics_registry.get("csv_statistics", {})
        pdf_stats = statistics_registry.get("pdf_statistics", {})

        has_csv = isinstance(csv_stats, dict) and bool(
            csv_stats.get("categorical_distributions") or csv_stats.get("numerical_summaries")
        )
        has_pdf = isinstance(pdf_stats, dict) and bool(pdf_stats.get("themes"))

        return has_csv or has_pdf

    def _build_registry_from_verifiable_facts(self, facts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(facts, dict):
            return None

        csv_facts = facts.get("csv_aggregations", {})
        if not isinstance(csv_facts, dict):
            return None

        percentages = csv_facts.get("percentages", {})
        total_responses = csv_facts.get("total_responses") or 0

        if not isinstance(percentages, dict) or not percentages:
            return None

        distributions = []
        citation_registry = {}

        for key, percentage in percentages.items():
            try:
                percentage_value = float(percentage)
            except (TypeError, ValueError):
                continue

            if total_responses:
                count_estimate = max(int(round((percentage_value / 100) * total_responses)), 0)
            else:
                count_estimate = 0

            value_label = key.replace("_percentage", "").replace("_", " ").title()
            citation_id = f"RUNTIME_FACT_{self.analysis_type}_{key}"[:64]

            distributions.append(
                {
                    "value": value_label,
                    "count": count_estimate,
                    "percentage": round(percentage_value, 1),
                    "source": "verifiable_facts",
                    "citation_id": citation_id,
                }
            )

            citation_registry[citation_id] = {
                "source_type": "csv",
                "source_files": list(facts.get("sources", [])),
                "descriptor": f"Derived from verifiable facts: {value_label}",
                "generated_at": datetime.utcnow().isoformat(),
                "generation_method": "verifiable_facts_runtime",
            }

        if not distributions:
            return None

        csv_statistics = {
            "metadata": {
                "generated_from": "verifiable_facts",
                "total_rows": total_responses,
                "generated_at": datetime.utcnow().isoformat(),
            },
            "categorical_distributions": {
                "verifiable_facts": {
                    "label": "Runtime Verifiable Facts",
                    "total_responses": total_responses,
                    "distribution": distributions,
                    "source": "verifiable_facts",
                }
            },
        }

        runtime_registry = {
            "csv_statistics": csv_statistics,
            "citation_registry": citation_registry,
            "analysis_context": {
                "generated_at": datetime.utcnow().isoformat(),
                "builder": "verifiable_facts",
            },
        }

        return runtime_registry
    
    def _parse_ai_response(self, response: Dict[str, Any]) -> AnalysisOutput:
        """
        Parse AI response into structured AnalysisOutput.
        
        Args:
            response: Raw AI response dictionary
            
        Returns:
            Parsed and validated AnalysisOutput
        """
        try:
            # Debug: Log the raw response
            logger.info(f"🔍 DEBUG: Raw AI response for {self.analysis_type}: {response}")
            logger.info(f"🔍 DEBUG: AI response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            # First, try to extract JSON from content if it's a string response
            content = response.get("content", "")
            logger.info(f"🔍 DEBUG: Content for {self.analysis_type} - Type: {type(content)}, Length: {len(content) if isinstance(content, str) else 'N/A'}, Empty: {not content}")
            
            if isinstance(content, str) and content.strip():
                logger.info(f"🔍 DEBUG: Content string for {self.analysis_type}: {content[:200]}...")
                try:
                    # Try to parse as JSON
                    import json
                    parsed_content = json.loads(content)
                    logger.info(f"✅ DEBUG: Successfully parsed JSON for {self.analysis_type}")
                    # Merge parsed content with response
                    response = {**response, **parsed_content}
                except json.JSONDecodeError as e:
                    logger.warning(f"❌ DEBUG: JSON parse failed for {self.analysis_type}: {e}")
                    # If not JSON, treat as plain text claim
                    response["claim"] = content
                    response["confidence_score"] = 0.5  # Default for text responses
                    response["accuracy_level"] = "medium"
            else:
                logger.error(f"❌ DEBUG: Empty or invalid content for {self.analysis_type}! Full response: {response}")
                # Handle empty response - this indicates AI service failure
                response["claim"] = f"AI service returned empty response for {self.analysis_type} analysis"
                response["confidence_score"] = 0.0
                response["accuracy_level"] = "low"
            
            # Harmonize responses from statistical prompts that may omit legacy fields
            claim = response.get("claim")
            statistical_summary = response.get("statistical_summary")
            if (not claim or not isinstance(claim, str) or not claim.strip()) and statistical_summary:
                candidate = self._clean_evidence_text(statistical_summary)
                if candidate:
                    claim = candidate

            # Some of the new statistical prompts return their main summary under
            # alternative keys such as "summary" or "analysis_summary". Use the first
            # non-empty textual field we can find to avoid empty claims.
            if not claim or not isinstance(claim, str) or not claim.strip():
                alt_claim = self._extract_text_field(
                    response,
                    (
                        "analysis_summary",
                        "summary",
                        "statistical_overview",
                        "overall_summary",
                        "key_insight",
                        "primary_finding",
                    )
                )
                if alt_claim:
                    claim = alt_claim

            if not claim or not isinstance(claim, str) or not claim.strip():
                claim = ""

            accuracy_level = response.get("accuracy_level")
            if isinstance(accuracy_level, str):
                accuracy_level = accuracy_level.strip().lower()
            if not isinstance(accuracy_level, str) or not accuracy_level:
                accuracy_level = self._extract_text_field(
                    response,
                    (
                        "accuracy_level",
                        "analysis_accuracy",
                        "confidence_level",
                        "evidence_confidence",
                    )
                ) or "low"
            elif accuracy_level not in ["high", "medium", "low"]:
                # Normalise unexpected casing values such as "High" or "HIGH"
                accuracy_level = accuracy_level.lower()

            supporting_evidence = response.get("supporting_evidence")
            logger.info(f"🔍 AI EVIDENCE DEBUG: Raw supporting_evidence = {supporting_evidence}")
            
            if not isinstance(supporting_evidence, list) or not supporting_evidence:
                supporting_evidence = response.get("quantitative_evidence")
                logger.info(f"🔍 AI EVIDENCE DEBUG: Fallback quantitative_evidence = {supporting_evidence}")
                
                # NEW: Extract from multiple response formats
                if not isinstance(supporting_evidence, list) or not supporting_evidence:
                    # FORMAT 1: Two-tier RAG format (size_frequency, pain_points)
                    tier1 = response.get("analysis_tier_1_ground_truth", {})
                    if isinstance(tier1, dict):
                        statistical_findings = tier1.get("statistical_findings", [])
                        if isinstance(statistical_findings, list) and statistical_findings:
                            supporting_evidence = []
                            for finding in statistical_findings:
                                if isinstance(finding, dict):
                                    stat = finding.get("statistic", "")
                                    interpretation = finding.get("interpretation", "")
                                    source = finding.get("source", "")
                                    if stat:
                                        evidence_text = f"{stat} - {interpretation}" if interpretation else stat
                                        if source:
                                            evidence_text += f" [Source: {source}]"
                                        supporting_evidence.append(evidence_text)
                            logger.info(f"🔍 AI EVIDENCE DEBUG: Extracted {len(supporting_evidence)} items from tier 1 statistical_findings")
                    
                    if not supporting_evidence:
                        tier2 = response.get("analysis_tier_2_qualitative_evidence", {})
                        if isinstance(tier2, dict):
                            patterns = tier2.get("patterns_and_examples", [])
                            if isinstance(patterns, list) and patterns:
                                supporting_evidence = []
                                for pattern in patterns:
                                    if isinstance(pattern, dict):
                                        pattern_text = pattern.get("pattern", "")
                                        example = pattern.get("example", "")
                                        source = pattern.get("source", "")
                                        if pattern_text:
                                            evidence_text = f"{pattern_text}"
                                            if example:
                                                evidence_text += f" Example: {example}"
                                            if source:
                                                evidence_text += f" [Source: {source}]"
                                            supporting_evidence.append(evidence_text)
                                logger.info(f"🔍 AI EVIDENCE DEBUG: Extracted {len(supporting_evidence)} items from tier 2 patterns_and_examples")
                    
                    # FORMAT 2: Analysis object format (jobs_to_be_done, gains_benefits)
                    if not supporting_evidence:
                        analysis_obj = response.get("analysis", {})
                        if isinstance(analysis_obj, dict):
                            # Try quantitative_summary
                            quant_summary = analysis_obj.get("quantitative_summary", {})
                            qual_summary = analysis_obj.get("qualitative_summary", {})
                            
                            supporting_evidence = []
                            
                            # Extract from quantitative summary
                            if isinstance(quant_summary, dict):
                                summary_statement = quant_summary.get("summary_statement", "")
                                if summary_statement:
                                    supporting_evidence.append(f"[Quantitative] {summary_statement}")
                                
                                # Extract nested statistics
                                for key, value in quant_summary.items():
                                    if isinstance(value, dict) and key != "summary_statement":
                                        for subkey, subvalue in value.items():
                                            if isinstance(subvalue, dict):
                                                count = subvalue.get("count", "")
                                                percent = subvalue.get("percent", "")
                                                citation = subvalue.get("citation", "")
                                                if count and percent:
                                                    evidence_text = f"{subkey}: {count} ({percent}%)"
                                                    if citation:
                                                        evidence_text += f" [Source: {citation}]"
                                                    supporting_evidence.append(evidence_text)
                            
                            # Extract from qualitative summary
                            if isinstance(qual_summary, dict):
                                summary_statement = qual_summary.get("summary_statement", "")
                                if summary_statement:
                                    supporting_evidence.append(f"[Qualitative] {summary_statement}")
                                
                                # Extract evidence arrays
                                for key, value in qual_summary.items():
                                    if isinstance(value, list) and key != "summary_statement":
                                        for item in value:
                                            if isinstance(item, dict):
                                                evidence = item.get("evidence", "")
                                                citation = item.get("citation", "")
                                                if evidence:
                                                    evidence_text = evidence
                                                    if citation:
                                                        evidence_text += f" [Source: {citation}]"
                                                    supporting_evidence.append(evidence_text)
                            
                            # Extract from jobs_to_be_done_insights
                            jtbd_insights = analysis_obj.get("jobs_to_be_done_insights", [])
                            if isinstance(jtbd_insights, list):
                                for insight in jtbd_insights:
                                    if isinstance(insight, dict):
                                        job = insight.get("job", "")
                                        evidence = insight.get("evidence", "")
                                        citations = insight.get("citations", [])
                                        if job and evidence:
                                            evidence_text = f"Job: {job} - {evidence}"
                                            # Filter out empty citations before joining
                                            if citations:
                                                valid_citations = [c for c in citations if c and str(c).strip()]
                                                if valid_citations:
                                                    evidence_text += f" [Sources: {', '.join(valid_citations)}]"
                                            supporting_evidence.append(evidence_text)
                            
                            if supporting_evidence:
                                logger.info(f"🔍 AI EVIDENCE DEBUG: Extracted {len(supporting_evidence)} items from analysis object format")
                
                # Additional fallbacks for different evidence field names
                if not isinstance(supporting_evidence, list) or not supporting_evidence:
                    for evidence_key in ["evidence", "findings", "data_points"]:
                        fallback_evidence = response.get(evidence_key)
                        if isinstance(fallback_evidence, list) and fallback_evidence:
                            supporting_evidence = fallback_evidence
                            logger.info(f"🔍 AI EVIDENCE DEBUG: Found evidence in '{evidence_key}' field = {supporting_evidence}")
                            break

            if (not isinstance(supporting_evidence, list) or not supporting_evidence):
                nested_support = self._deep_find_value(
                    response,
                    (
                        "supporting_evidence",
                        "supportingevidence",
                        "supporting_points",
                        "supportingfindings",
                        "support",
                        "evidence_supporting",
                        "supportingfacts",
                        "evidence_points",
                    )
                )
                if nested_support is not None:
                    supporting_evidence = self._coerce_to_list(nested_support)

            if not isinstance(supporting_evidence, list):
                supporting_evidence = self._coerce_to_list(supporting_evidence)

            supporting_evidence = self._normalise_evidence_items(supporting_evidence)

            if not isinstance(supporting_evidence, list) or not supporting_evidence:
                supporting_evidence = []
                logger.warning(f"⚠️ AI EVIDENCE DEBUG: No valid evidence found in AI response - defaulting to empty list")
            else:
                logger.info(f"✅ AI EVIDENCE DEBUG: Successfully extracted {len(supporting_evidence)} evidence items")

            debunking_evidence = response.get("debunking_evidence", [])
            if not isinstance(debunking_evidence, list):
                nested_debunking = self._deep_find_value(
                    response,
                    (
                        "debunking_evidence",
                        "contradicting_evidence",
                        "counterpoints",
                        "debunking",
                        "refuting_evidence",
                        "challenging_findings",
                    )
                )
                debunking_evidence = self._coerce_to_list(nested_debunking)

            debunking_evidence = self._normalise_evidence_items(debunking_evidence)

            # Merge statistical payloads coming from the new agents with the legacy
            # "statistical_data" field so downstream components always receive a
            # consistent dictionary.
            statistical_data = response.get("statistical_data", {})
            if not isinstance(statistical_data, dict):
                statistical_data = self._extract_dict_field(
                    response,
                    (
                        "statistical_data",
                        "statistics",
                        "quantitative_data",
                        "quantitativefindings",
                        "numerical_analysis",
                    )
                )
            extra_statistical_fields = {}

            # Agents emit a range of quantitative structures depending on the
            # assumption dimension being analysed. Collect any recognised payloads
            # so that the report formatter can render them.
            recognised_stat_keys = {
                "pain_statistics",
                "quantitative_findings",
                "size_frequency_statistics",
                "solution_statistics",
                "gain_statistics",
                "benefit_statistics",
                "jtbd_statistics",
                "quantitative_analysis",
            }

            # Dynamically include any key that follows the *_statistics naming
            # convention so future prompt updates continue to flow through without
            # requiring code changes.
            for key, value in response.items():
                if key in recognised_stat_keys or key.endswith("_statistics"):
                    if value:
                        extra_statistical_fields[key] = value

            # Some prompts include "data_gaps" or "data_limitations" fields that
            # are important for interpreting the numbers. Preserve them as part of
            # the statistical payload as well.
            for meta_key in ("data_gaps", "data_limitations"):
                value = response.get(meta_key)
                if value:
                    extra_statistical_fields[meta_key] = value

            if extra_statistical_fields:
                if not isinstance(statistical_data, dict):
                    statistical_data = {}
                statistical_data = {**statistical_data, **extra_statistical_fields}

            confidence_score = response.get("confidence_score")
            if not isinstance(confidence_score, (int, float)):
                # Try standard fields first
                nested_confidence = self._extract_numeric_field(
                    response,
                    (
                        "confidence_score",
                        "confidence",
                        "overall_confidence",
                        "confidencevalue",
                        "confidencelevel",
                        "analysis_confidence",
                    )
                )
                confidence_score = nested_confidence if nested_confidence is not None else 0.0
                
                # NEW: Try to extract from new response formats
                if confidence_score == 0.0:
                    # Try confidence_score_statistical and confidence_score_qualitative
                    stat_conf = response.get("confidence_score_statistical", 0.0)
                    qual_conf = response.get("confidence_score_qualitative", 0.0)
                    
                    if isinstance(stat_conf, (int, float)) and isinstance(qual_conf, (int, float)):
                        # Average the two confidence scores
                        confidence_score = (stat_conf + qual_conf) / 2.0
                        logger.info(f"🔍 AI CONFIDENCE DEBUG: Calculated from stat={stat_conf}, qual={qual_conf}, avg={confidence_score}")
                    elif isinstance(stat_conf, (int, float)) and stat_conf > 0:
                        confidence_score = stat_conf
                        logger.info(f"🔍 AI CONFIDENCE DEBUG: Using statistical confidence={stat_conf}")
                    elif isinstance(qual_conf, (int, float)) and qual_conf > 0:
                        confidence_score = qual_conf
                        logger.info(f"🔍 AI CONFIDENCE DEBUG: Using qualitative confidence={qual_conf}")
                    
                    # Try tier-specific confidence scores
                    if confidence_score == 0.0:
                        tier1 = response.get("analysis_tier_1_ground_truth", {})
                        if isinstance(tier1, dict):
                            tier1_conf = tier1.get("statistical_accuracy_confidence", 0.0)
                            if isinstance(tier1_conf, (int, float)) and tier1_conf > 0:
                                confidence_score = tier1_conf
                                logger.info(f"🔍 AI CONFIDENCE DEBUG: Using tier 1 confidence={tier1_conf}")
                        
                        tier2 = response.get("analysis_tier_2_qualitative_evidence", {})
                        if isinstance(tier2, dict) and confidence_score == 0.0:
                            tier2_conf = tier2.get("interpretive_confidence", 0.0)
                            if isinstance(tier2_conf, (int, float)) and tier2_conf > 0:
                                confidence_score = tier2_conf
                                logger.info(f"🔍 AI CONFIDENCE DEBUG: Using tier 2 confidence={tier2_conf}")
            
            logger.info(f"🔍 AI CONFIDENCE DEBUG: Raw AI response confidence_score = {confidence_score}")
            logger.info(f"🔍 AI CONFIDENCE DEBUG: Supporting evidence count = {len(supporting_evidence) if supporting_evidence else 0}")

            # Validate accuracy level
            if accuracy_level not in ["high", "medium", "low"]:
                inferred_accuracy = self._infer_accuracy_level(float(confidence_score or 0.0), supporting_evidence, debunking_evidence)
                logger.warning(
                    f"Invalid accuracy level '{accuracy_level}', using inferred level '{inferred_accuracy}'"
                )
                accuracy_level = inferred_accuracy
            
            # Validate confidence score
            if not isinstance(confidence_score, (int, float)) or confidence_score < 0 or confidence_score > 1:
                logger.warning(f"Invalid confidence score '{confidence_score}', defaulting to 0.2")
                confidence_score = 0.2  # Minimum confidence instead of 0.0
            elif confidence_score == 0.0 and len(supporting_evidence) > 0:
                # If AI returned 0.0 but there's supporting evidence, apply minimum confidence
                confidence_score = 0.25
                logger.info(f"🔧 AI CONFIDENCE FLOOR: Applied minimum confidence due to supporting evidence")
            elif confidence_score == 0.0 and len(supporting_evidence) == 0:
                # CRITICAL FIX: If AI found no evidence, apply emergency minimum confidence
                confidence_score = 0.15  # Emergency minimum when no evidence extracted
                logger.warning(f"🚨 EMERGENCY CONFIDENCE FLOOR: AI found no evidence - applying minimum confidence of {confidence_score}")
            
            # Ensure evidence lists are actually lists
            if not isinstance(supporting_evidence, list):
                supporting_evidence = []
            if not isinstance(debunking_evidence, list):
                debunking_evidence = []
            if not isinstance(statistical_data, dict):
                statistical_data = {}
            
            # Extract fact validation fields if present
            citation_ids = response.get("citation_ids", [])
            persona_relevance_score = response.get("persona_relevance_score")
            fact_validation_score = response.get("fact_validation_score")
            validation_metadata = response.get("validation_metadata", {})
            
            # Ensure citation_ids is a list
            if not isinstance(citation_ids, list):
                citation_ids = []
            
            # Validate persona relevance score
            if persona_relevance_score is not None:
                if not isinstance(persona_relevance_score, (int, float)) or persona_relevance_score < 0 or persona_relevance_score > 1:
                    logger.warning(f"Invalid persona relevance score '{persona_relevance_score}', setting to None")
                    persona_relevance_score = None
            
            # Validate fact validation score
            if fact_validation_score is not None:
                if not isinstance(fact_validation_score, (int, float)) or fact_validation_score < 0 or fact_validation_score > 1:
                    logger.warning(f"Invalid fact validation score '{fact_validation_score}', setting to None")
                    fact_validation_score = None
            
            # Ensure validation metadata is a dict
            if not isinstance(validation_metadata, dict):
                validation_metadata = {}
            
            return AnalysisOutput(
                claim=claim,
                accuracy_level=accuracy_level,
                supporting_evidence=supporting_evidence,
                debunking_evidence=debunking_evidence,
                statistical_data=statistical_data,
                confidence_score=float(confidence_score),
                citation_ids=citation_ids,
                persona_relevance_score=persona_relevance_score,
                fact_validation_score=fact_validation_score,
                validation_metadata=validation_metadata
            )

        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return AnalysisOutput(
                claim="Failed to parse analysis response",
                accuracy_level="low",
                supporting_evidence=[],
                debunking_evidence=[],
                statistical_data={},
                confidence_score=0.0,
                citation_ids=[],
                persona_relevance_score=None,
                fact_validation_score=None,
                validation_metadata={}
            )

    def _finalize_analysis_output(
        self,
        analysis_output: AnalysisOutput,
        context: AnalysisContext
    ) -> AnalysisOutput:
        """Sanitise final analysis output and calibrate scores for qualitative datasets."""

        assumption_text = self._clean_evidence_text(
            context.assumption.get("text", "") if isinstance(context.assumption, dict) else ""
        )

        claim = self._clean_evidence_text(analysis_output.claim or "")
        if assumption_text and claim and claim.lower() == assumption_text.lower():
            alternative = self._pick_alternative_claim(analysis_output)
            if alternative:
                claim = alternative

        if not claim:
            claim = self._pick_alternative_claim(analysis_output) or "No new finding identified from current research data."

        analysis_output.claim = claim

        cleaned_support: List[str] = []
        for item in analysis_output.supporting_evidence:
            if not isinstance(item, str):
                continue
            cleaned_item = self._clean_evidence_text(item)
            if cleaned_item:
                cleaned_support.append(cleaned_item)
        analysis_output.supporting_evidence = cleaned_support

        cleaned_debunking: List[str] = []
        for item in analysis_output.debunking_evidence or []:
            if not isinstance(item, str):
                continue
            cleaned_item = self._clean_evidence_text(item)
            if cleaned_item:
                cleaned_debunking.append(cleaned_item)
        analysis_output.debunking_evidence = cleaned_debunking

        analysis_output.statistical_data = self._normalise_statistical_data(analysis_output.statistical_data)

        calibrated_confidence = self._calibrate_confidence_for_sample_size(
            analysis_output.confidence_score,
            context.research_data
        )
        analysis_output.confidence_score = calibrated_confidence

        return analysis_output

    def _pick_alternative_claim(self, analysis_output: AnalysisOutput) -> Optional[str]:
        """Derive a concise claim from supporting evidence when the claim is unusable."""

        for evidence in analysis_output.supporting_evidence or []:
            cleaned = self._clean_evidence_text(evidence)
            if cleaned and len(cleaned.split()) >= 5:
                return cleaned

        for evidence in analysis_output.debunking_evidence or []:
            cleaned = self._clean_evidence_text(evidence)
            if cleaned and len(cleaned.split()) >= 5:
                return cleaned

        return None

    def _normalise_statistical_data(self, statistical_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure statistical data payloads are human-readable and citation free."""

        if not isinstance(statistical_data, dict):
            return {}

        normalised: Dict[str, Any] = {}
        for key, value in statistical_data.items():
            if key == "fact_validation":
                normalised[key] = value
                continue

            if isinstance(value, dict):
                normalised[key] = {
                    sub_key: self._clean_evidence_text(str(sub_value)) if isinstance(sub_value, (str, int, float)) else sub_value
                    for sub_key, sub_value in value.items()
                }
            elif isinstance(value, list):
                cleaned_list = [
                    self._clean_evidence_text(str(item))
                    for item in value
                    if str(item).strip()
                ]
                if cleaned_list:
                    normalised[key] = cleaned_list
            elif isinstance(value, (str, int, float)):
                cleaned_value = self._clean_evidence_text(str(value))
                if cleaned_value:
                    normalised[key] = cleaned_value

        return normalised

    def _calibrate_confidence_for_sample_size(
        self,
        confidence_score: float,
        research_chunks: List[Dict[str, Any]]
    ) -> float:
        """Clamp confidence scores to realistic bands based on available research."""

        if not isinstance(confidence_score, (int, float)):
            confidence_score = 0.2

        participant_count = self._estimate_participant_count(research_chunks)

        if participant_count:
            if participant_count <= 6:
                return max(0.2, min(float(confidence_score), 0.6))
            if participant_count <= 15:
                return max(0.25, min(float(confidence_score), 0.7))

        return max(0.25, min(float(confidence_score), 0.85))

    def _estimate_participant_count(self, research_chunks: List[Dict[str, Any]]) -> int:
        """Approximate participant/sample size from research metadata."""

        if not isinstance(research_chunks, list):
            return 0

        participants: Set[str] = set()
        documents: Set[str] = set()

        for chunk in research_chunks:
            if not isinstance(chunk, dict):
                continue

            metadata = chunk.get("metadata", {})
            if isinstance(metadata, dict):
                participant = (
                    metadata.get("participant")
                    or metadata.get("interviewee")
                    or metadata.get("respondent")
                    or metadata.get("speaker")
                )
                if participant:
                    participants.add(str(participant).strip().lower())

                document_id = metadata.get("document_id") or metadata.get("source_id") or metadata.get("filename")
                if document_id:
                    documents.add(str(document_id).strip().lower())

        if participants:
            return len(participants)

        if documents:
            return len(documents)

        return 0

    def _update_state_with_results(
        self,
        state: AssumptionAnalysisState,
        analysis_result: AnalysisOutput
    ) -> AssumptionAnalysisState:
        """
        Update workflow state with analysis results.
        
        Args:
            state: Current workflow state
            analysis_result: Analysis output to add to state
            
        Returns:
            Updated state
        """
        # Use concurrent-safe state updates for parallel execution
        assumption_id = state["current_assumption"].get("id", "unknown")
        
        # Initialize (or reset) current_assumption_analysis when switching assumptions
        existing_analysis = state.get("current_assumption_analysis")
        existing_assumption_id = (
            existing_analysis.get("assumption_id")
            if isinstance(existing_analysis, dict)
            else None
        )
        needs_reset = (
            not isinstance(existing_analysis, dict)
            or not existing_analysis
            or existing_assumption_id is None
            or existing_assumption_id != assumption_id
        )

        if needs_reset:
            logger.info(
                "🧹 STATE RESET: Preparing fresh analysis container for assumption %s",
                assumption_id,
            )
            state["current_assumption_analysis"] = {
                "assumption_id": assumption_id,
                "assumption_text": state["current_assumption"].get("text", ""),
                "persona_name": state["target_persona"].get("name", "Unknown"),
                "analyses": {},
                "validation_status": "pending",
                "overall_confidence": 0.0,
                "key_findings": []
            }
        
        # Update with this analysis result (concurrent-safe merge)
        analysis_update = {
            "analyses": {
                **state["current_assumption_analysis"].get("analyses", {}),
                self.analysis_type: analysis_result.model_dump()
            }
        }
        
        # Add key findings if this analysis has high confidence
        if analysis_result.confidence_score > 0.7:
            finding = f"{self.analysis_type.title()}: {analysis_result.claim}"
            existing_findings = state["current_assumption_analysis"].get("key_findings", [])
            if finding not in existing_findings:
                analysis_update["key_findings"] = existing_findings + [finding]
        
        # Merge the update into existing state (concurrent-safe)
        state["current_assumption_analysis"].update(analysis_update)
        
        # DEBUG: Log what's in the state after update
        logger.info(f"🔍 DEBUG: After {self.analysis_type} update - analyses keys: {list(state['current_assumption_analysis'].get('analyses', {}).keys())}")
        logger.info(f"🔍 DEBUG: After {self.analysis_type} update - current_assumption_analysis keys: {list(state['current_assumption_analysis'].keys())}")
        
        return state
    
    def _calculate_persona_relevance(self, claim: str, persona: Dict[str, Any]) -> float:
        """
        Calculate relevance score between analysis claim and target persona.
        
        Args:
            claim: Analysis claim text
            persona: Target persona data
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            if not claim or not persona:
                return 0.0
            
            # Extract persona keywords
            persona_keywords = set()
            
            # Add persona name and description words
            if persona.get('name'):
                persona_keywords.update(persona['name'].lower().split())
            if persona.get('description'):
                persona_keywords.update(persona['description'].lower().split())
            
            # Add demographic and behavioral keywords
            for field in ['demographics', 'behaviors', 'goals', 'pain_points']:
                if persona.get(field):
                    if isinstance(persona[field], str):
                        persona_keywords.update(persona[field].lower().split())
                    elif isinstance(persona[field], list):
                        for item in persona[field]:
                            if isinstance(item, str):
                                persona_keywords.update(item.lower().split())
            
            # Extract claim keywords
            claim_keywords = set(claim.lower().split())
            
            # Calculate overlap
            if not persona_keywords or not claim_keywords:
                return 0.5  # Neutral relevance if no keywords
            
            intersection = persona_keywords.intersection(claim_keywords)
            union = persona_keywords.union(claim_keywords)
            
            relevance_score = len(intersection) / len(union) if union else 0.0
            
            # Boost score if persona name appears in claim
            if persona.get('name') and persona['name'].lower() in claim.lower():
                relevance_score = min(1.0, relevance_score + 0.3)
            
            return relevance_score
            
        except Exception as e:
            logger.error(f"Error calculating persona relevance: {e}")
            return 0.5  # Default neutral relevance on error
    
    def _extract_relevant_quotes(self, research_data: List[Dict[str, Any]], max_quotes: int = 3) -> List[str]:
        """
        Extract relevant quotes from research data for evidence.
        
        Args:
            research_data: List of research chunks
            max_quotes: Maximum number of quotes to extract
            
        Returns:
            List of relevant quotes
        """
        quotes = []
        
        for chunk in research_data[:max_quotes]:
            content = chunk.get("content", "")
            if content and len(content) > 50:  # Only include substantial content
                # Truncate long quotes
                if len(content) > 200:
                    content = content[:197] + "..."
                quotes.append(f'"{content}"')
        
        return quotes
    
    def _calculate_confidence_score(
        self, 
        supporting_evidence: List[str], 
        debunking_evidence: List[str],
        statistical_data: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score based on evidence strength.
        
        Args:
            supporting_evidence: List of supporting evidence
            debunking_evidence: List of contradicting evidence
            statistical_data: Quantitative data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base score from evidence balance
        support_count = len(supporting_evidence)
        debunk_count = len(debunking_evidence)
        
        if support_count + debunk_count == 0:
            return 0.0
        
        # Calculate evidence ratio
        evidence_ratio = support_count / (support_count + debunk_count)
        
        # Boost for statistical data
        stats_boost = 0.1 if statistical_data else 0.0
        
        # Boost for multiple supporting evidence
        multiple_evidence_boost = 0.1 if support_count >= 3 else 0.0
        
        confidence = min(1.0, evidence_ratio + stats_boost + multiple_evidence_boost)
        return confidence
    
    # ============================================================================
    # ENTERPRISE-GRADE ANALYSIS METHODS
    # ============================================================================
    
    async def perform_enterprise_analysis(
        self,
        context: AnalysisContext,
        enterprise_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform enterprise-grade analysis with advanced intelligence capabilities.
        
        Features:
        - Multi-source evidence synthesis from massive datasets
        - Statistical significance testing and confidence intervals
        - Cross-file validation and consistency checking
        - AI-enhanced pattern recognition
        """
        try:
            # STEP 1: Comprehensive Evidence Synthesis
            evidence_synthesis = await self._synthesize_multi_source_evidence(
                context, enterprise_data
            )
            
            # STEP 2: Statistical Significance Testing
            statistical_validation = await self._perform_statistical_validation(
                evidence_synthesis, enterprise_data
            )
            
            # STEP 3: Cross-File Consistency Checking
            consistency_analysis = await self._analyze_cross_file_consistency(
                evidence_synthesis, enterprise_data
            )
            
            # STEP 4: AI-Enhanced Pattern Recognition
            pattern_insights = await self._detect_ai_enhanced_patterns(
                evidence_synthesis, context
            )
            
            # STEP 5: Comprehensive Analysis Synthesis
            enterprise_analysis = {
                "evidence_synthesis": evidence_synthesis,
                "statistical_validation": statistical_validation,
                "consistency_analysis": consistency_analysis,
                "pattern_insights": pattern_insights,
                "enterprise_confidence_score": self._calculate_enterprise_confidence(
                    statistical_validation, consistency_analysis, pattern_insights
                ),
                "analysis_metadata": {
                    "analysis_type": self._get_analysis_type(),
                    "files_analyzed": len(enterprise_data.get("source_files", [])),
                    "total_evidence_points": len(evidence_synthesis.get("all_evidence", [])),
                    "statistical_tests_performed": len(statistical_validation.get("tests", [])),
                    "analyzed_at": datetime.utcnow().isoformat()
                }
            }
            
            return enterprise_analysis
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE ANALYSIS: Failed for {self._get_analysis_type()}: {e}")
            raise
    
    async def _synthesize_multi_source_evidence(
        self,
        context: AnalysisContext,
        enterprise_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize evidence from multiple sources with advanced intelligence."""
        try:
            synthesis = {
                "csv_evidence": [],
                "pdf_evidence": [],
                "cross_source_correlations": [],
                "evidence_strength_scores": {},
                "source_reliability_scores": {},
                "all_evidence": []
            }
            
            # Process CSV evidence from multiple files
            csv_stats = enterprise_data.get("multi_csv_statistics", {})
            combined_distributions = csv_stats.get("combined_distributions", {})
            
            for field_name, field_data in combined_distributions.items():
                if self._is_relevant_to_analysis_type(field_name):
                    csv_evidence = {
                        "field": field_name,
                        "total_responses": field_data.get("total_responses", 0),
                        "source_files": field_data.get("source_files", []),
                        "value_distributions": field_data.get("value_counts", {}),
                        "evidence_type": "quantitative",
                        "reliability_score": self._calculate_source_reliability(field_data)
                    }
                    synthesis["csv_evidence"].append(csv_evidence)
                    synthesis["all_evidence"].append(csv_evidence)
            
            # Process PDF evidence from multiple files
            pdf_stats = enterprise_data.get("multi_pdf_statistics", {})
            combined_themes = pdf_stats.get("combined_themes", {})
            
            for theme_name, theme_data in combined_themes.items():
                if self._is_relevant_to_analysis_type(theme_name):
                    pdf_evidence = {
                        "theme": theme_name,
                        "total_mentions": theme_data.get("total_mentions", 0),
                        "source_files": theme_data.get("source_files", []),
                        "representative_quotes": theme_data.get("representative_quotes", []),
                        "evidence_type": "qualitative",
                        "reliability_score": self._calculate_theme_reliability(theme_data)
                    }
                    synthesis["pdf_evidence"].append(pdf_evidence)
                    synthesis["all_evidence"].append(pdf_evidence)
            
            # Detect cross-source correlations
            synthesis["cross_source_correlations"] = await self._detect_cross_source_correlations(
                synthesis["csv_evidence"], synthesis["pdf_evidence"]
            )
            
            return synthesis
            
        except Exception as e:
            logger.error(f"❌ EVIDENCE SYNTHESIS: Failed: {e}")
            return {"error": str(e)}
    
    async def _perform_statistical_validation(
        self,
        evidence_synthesis: Dict[str, Any],
        enterprise_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform statistical significance testing and confidence intervals."""
        try:
            validation = {
                "significance_tests": [],
                "confidence_intervals": [],
                "sample_size_adequacy": {},
                "statistical_power": {},
                "overall_statistical_confidence": 0.0
            }
            
            # Perform significance tests on CSV data
            for csv_evidence in evidence_synthesis.get("csv_evidence", []):
                total_responses = csv_evidence.get("total_responses", 0)
                
                if total_responses >= MIN_SAMPLE_SIZE_FOR_STATS:
                    # Chi-square test for categorical distributions
                    chi_square_result = self._perform_chi_square_test(csv_evidence)
                    validation["significance_tests"].append(chi_square_result)
                    
                    # Confidence intervals for proportions
                    confidence_intervals = self._calculate_confidence_intervals(csv_evidence)
                    validation["confidence_intervals"].extend(confidence_intervals)
                    
                    # Sample size adequacy assessment
                    validation["sample_size_adequacy"][csv_evidence["field"]] = {
                        "sample_size": total_responses,
                        "adequate": total_responses >= MIN_SAMPLE_SIZE_FOR_STATS,
                        "power_analysis": self._calculate_statistical_power(total_responses)
                    }
            
            # Calculate overall statistical confidence
            significant_tests = [t for t in validation["significance_tests"] if t.get("is_significant", False)]
            validation["overall_statistical_confidence"] = (
                len(significant_tests) / len(validation["significance_tests"])
                if validation["significance_tests"] else 0.0
            )
            
            return validation
            
        except Exception as e:
            logger.error(f"❌ STATISTICAL VALIDATION: Failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_cross_file_consistency(
        self,
        evidence_synthesis: Dict[str, Any],
        enterprise_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze consistency across multiple files."""
        try:
            consistency = {
                "field_consistency_scores": {},
                "theme_consistency_scores": {},
                "cross_file_contradictions": [],
                "overall_consistency_score": 0.0,
                "reliability_assessment": {}
            }
            
            # Analyze CSV field consistency
            for csv_evidence in evidence_synthesis.get("csv_evidence", []):
                source_files = csv_evidence.get("source_files", [])
                if len(source_files) > 1:
                    consistency_score = self._calculate_field_consistency_score(csv_evidence)
                    consistency["field_consistency_scores"][csv_evidence["field"]] = {
                        "score": consistency_score,
                        "files_count": len(source_files),
                        "assessment": "high" if consistency_score > 0.8 else "medium" if consistency_score > 0.6 else "low"
                    }
            
            # Analyze PDF theme consistency
            for pdf_evidence in evidence_synthesis.get("pdf_evidence", []):
                source_files = pdf_evidence.get("source_files", [])
                if len(source_files) > 1:
                    consistency_score = self._calculate_theme_consistency_score(pdf_evidence)
                    consistency["theme_consistency_scores"][pdf_evidence["theme"]] = {
                        "score": consistency_score,
                        "files_count": len(source_files),
                        "assessment": "high" if consistency_score > 0.7 else "medium" if consistency_score > 0.5 else "low"
                    }
            
            # Detect contradictions
            consistency["cross_file_contradictions"] = self._detect_cross_file_contradictions(
                evidence_synthesis
            )
            
            # Calculate overall consistency
            all_scores = list(consistency["field_consistency_scores"].values()) + list(consistency["theme_consistency_scores"].values())
            if all_scores:
                consistency["overall_consistency_score"] = sum(s["score"] for s in all_scores) / len(all_scores)
            
            return consistency
            
        except Exception as e:
            logger.error(f"❌ CONSISTENCY ANALYSIS: Failed: {e}")
            return {"error": str(e)}
    
    async def _detect_ai_enhanced_patterns(
        self,
        evidence_synthesis: Dict[str, Any],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """Use AI to detect advanced patterns in the evidence."""
        try:
            patterns = {
                "semantic_clusters": [],
                "hidden_correlations": [],
                "emerging_themes": [],
                "anomaly_detection": [],
                "predictive_insights": []
            }
            
            # Prepare evidence for AI analysis
            all_evidence = evidence_synthesis.get("all_evidence", [])
            if not all_evidence:
                return patterns
            
            # Create AI prompt for pattern detection
            pattern_prompt = self._create_pattern_detection_prompt(all_evidence, context)
            
            # Call AI service for pattern recognition
            ai_service = self.ai_service_wrapper
            response = await ai_service.generate_with_fallback(
                pattern_prompt,
                json_mode=True,
                max_tokens=16000,  # gpt-5-mini needs large token budget
                temperature=0.3
            )
            
            if response and response.get("content"):
                try:
                    ai_patterns = json.loads(response["content"])
                    patterns.update(ai_patterns)
                except json.JSONDecodeError:
                    logger.warning("❌ AI PATTERNS: Invalid JSON response")
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ AI PATTERN DETECTION: Failed: {e}")
            return {"error": str(e)}
    
    def _calculate_enterprise_confidence(
        self,
        statistical_validation: Dict[str, Any],
        consistency_analysis: Dict[str, Any],
        pattern_insights: Dict[str, Any]
    ) -> float:
        """Calculate overall enterprise confidence score."""
        try:
            # Statistical confidence (40% weight)
            stat_confidence = statistical_validation.get("overall_statistical_confidence", 0.0) * 0.4
            
            # Consistency confidence (35% weight)
            consistency_confidence = consistency_analysis.get("overall_consistency_score", 0.0) * 0.35
            
            # Pattern insights confidence (25% weight)
            pattern_confidence = 0.25
            if pattern_insights.get("semantic_clusters"):
                pattern_confidence *= 0.8
            if pattern_insights.get("hidden_correlations"):
                pattern_confidence *= 1.2
            if pattern_insights.get("anomaly_detection"):
                pattern_confidence *= 0.9
            
            pattern_confidence = min(0.25, pattern_confidence)
            
            enterprise_confidence = stat_confidence + consistency_confidence + pattern_confidence
            return min(1.0, max(0.0, enterprise_confidence))
            
        except Exception as e:
            logger.error(f"❌ ENTERPRISE CONFIDENCE: Calculation failed: {e}")
            return 0.5
    
    # Helper methods for enterprise analysis
    def _is_relevant_to_analysis_type(self, field_or_theme: str) -> bool:
        """Check if field or theme is relevant to this analysis type."""
        analysis_type = self._get_analysis_type().lower()
        field_lower = field_or_theme.lower()
        
        relevance_keywords = {
            "pain": ["pain", "problem", "issue", "challenge", "difficulty", "frustration"],
            "size": ["size", "frequency", "count", "number", "amount", "volume"],
            "solution": ["solution", "tool", "product", "service", "method", "approach"],
            "gains": ["benefit", "gain", "advantage", "improvement", "value", "outcome"],
            "jtbd": ["job", "task", "goal", "objective", "need", "want", "desire"]
        }
        
        keywords = relevance_keywords.get(analysis_type, [])
        return any(keyword in field_lower for keyword in keywords)


# Create alias for backward compatibility
BaseAnalysisAgent = EnterpriseBaseAnalysisAgent