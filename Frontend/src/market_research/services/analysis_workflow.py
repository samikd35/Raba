"""
LangGraph orchestration workflow for assumption analysis.

Implements the multi-agent analysis workflow using LangGraph for orchestrating
specialized analysis agents in a sequential manner.
"""

import asyncio
import gc
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from ..models.analysis_models import AssumptionAnalysisState
from ..agents.base_analysis_agent import BaseAnalysisAgent
from ..agents.pain_analysis_agent import PainAnalysisAgent
# REMOVED: SizeFrequencyAgent - Problem Size & Frequency Analysis removed
# from ..agents.size_frequency_agent import SizeFrequencyAgent
# REMOVED: SolutionAnalysisAgent - Current Solutions Analysis removed
# from ..agents.solution_analysis_agent import SolutionAnalysisAgent
from ..agents.gains_analysis_agent import GainsAnalysisAgent
from ..agents.jtbd_analysis_agent import JTBDAnalysisAgent
from ..agents.validator_agent import ValidatorAgent
# REMOVED: ComparisonAgent - PV comparison no longer needed
# from ..agents.comparison_agent import ComparisonAgent
from ..agents.report_synthesizer_agent import ReportSynthesizerAgent
# 🔧 REMOVED: RuntimeStatisticsBuilder - creates segment-based stats and RUNTIME citations
# from ..services.runtime_statistics_builder import RuntimeStatisticsBuilder

logger = logging.getLogger(__name__)


class AnalysisWorkflow:
    """LangGraph workflow for assumption analysis."""
    
    def __init__(self, enhanced_components):
        """
        Initialize the analysis workflow with required enhanced components.
        
        Args:
            enhanced_components: Dict containing required enhanced components like statistics_registry,
                                ground_truth_builder, evidence_retrieval, etc.
        """
        if not enhanced_components:
            raise ValueError("Enhanced components are required. Legacy processing has been removed.")
            
        self.enhanced_components = enhanced_components

        required_components = [
            "statistics_registry",
            "ground_truth_builder",
            "evidence_retrieval",
        ]
        missing_components = [
            key for key in required_components if not enhanced_components.get(key)
        ]
        if missing_components:
            raise ValueError(
                "Enhanced workflow requires components: "
                + ", ".join(missing_components)
            )

        self.statistics_registry = enhanced_components["statistics_registry"]
        self.ground_truth_builder = enhanced_components["ground_truth_builder"]
        self.evidence_retrieval = enhanced_components["evidence_retrieval"]
        self.fact_validator = enhanced_components.get("fact_validator")
        # 🔧 REMOVED: self.runtime_statistics_builder = RuntimeStatisticsBuilder()

        # Always use enhanced correlation engine
        if not enhanced_components.get('persona_correlation'):
            raise ValueError("PersonaAwareCorrelationEngine is required. Legacy CorrelationEngine removed.")

        self.correlation_engine = enhanced_components['persona_correlation']
        logger.info("🚀 Enhanced workflow: Using persona-aware correlation engine")

        # Initialize analysis agents BEFORE building workflow with enhanced components
        agent_kwargs = {
            "statistics_registry": self.statistics_registry,
            "ground_truth_builder": self.ground_truth_builder,
            "evidence_retrieval": self.evidence_retrieval,
            "fact_validator": self.fact_validator,
        }

        self.pain_agent = PainAnalysisAgent(**agent_kwargs)
        # REMOVED: Size/Frequency Agent - Problem Size & Frequency Analysis removed
        # self.size_agent = SizeFrequencyAgent(**agent_kwargs)
        # REMOVED: Solution Agent - Current Solutions Analysis removed
        # self.solution_agent = SolutionAnalysisAgent(**agent_kwargs)
        self.gains_agent = GainsAnalysisAgent(**agent_kwargs)
        self.jtbd_agent = JTBDAnalysisAgent(**agent_kwargs)
        self.validator_agent = ValidatorAgent()
        # REMOVED: ComparisonAgent - PV comparison no longer needed
        # self.comparison_agent = ComparisonAgent()
        self.report_synthesizer = ReportSynthesizerAgent()
        
        # Build workflow after agents are initialized
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AssumptionAnalysisState)
        
        # Add workflow nodes
        workflow.add_node("initialize", self._initialize_analysis)
        workflow.add_node("select_assumption", self._select_next_assumption)
        workflow.add_node("prepare_context", self._prepare_analysis_context)
        workflow.add_node("pain_analysis", self._run_pain_analysis)
        workflow.add_node("gains_analysis", self._run_gains_analysis)
        workflow.add_node("jtbd_analysis", self._run_jtbd_analysis)
        workflow.add_node("validate_assumption", self._validate_assumption)
        workflow.add_node("check_completion", self._check_completion)
        workflow.add_node("synthesize_report", self._synthesize_report)
        workflow.add_node("finalize", self._finalize_analysis)
        
        # Define workflow edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "select_assumption")
        
        # CRITICAL FIX: After select_assumption, check if we have an assumption to process
        # If current_assumption is empty (all done), go directly to synthesize_report
        # This prevents the infinite loop bug where we'd route an empty assumption to analysis
        workflow.add_conditional_edges(
            "select_assumption",
            self._route_after_selection,
            {
                "process": "prepare_context",
                "finish": "synthesize_report"
            }
        )
        
        # COMPONENT-TYPE ROUTING: Route to the correct analysis agent based on assumption's component_type
        # Each assumption has a component_type field (jtbd, pain, or gain) that determines which
        # single analysis agent should process it. This replaces the previous sequential processing
        # where ALL agents ran for EVERY assumption.
        workflow.add_conditional_edges(
            "prepare_context",
            self._route_to_analysis_by_component_type,
            {
                "pain": "pain_analysis",
                "gain": "gains_analysis",
                "jtbd": "jtbd_analysis"
            }
        )
        
        # Each analysis type goes directly to validation (only ONE runs per assumption)
        workflow.add_edge("pain_analysis", "validate_assumption")
        workflow.add_edge("gains_analysis", "validate_assumption")
        workflow.add_edge("jtbd_analysis", "validate_assumption")
        
        # After validation, check if more assumptions remain
        workflow.add_edge("validate_assumption", "check_completion")
        
        # Conditional routing for completion check
        workflow.add_conditional_edges(
            "check_completion",
            self._should_continue,
            {
                "continue": "select_assumption",
                "finish": "synthesize_report"
            }
        )
        
        workflow.add_edge("synthesize_report", "finalize")
        workflow.add_edge("finalize", END)
        
        # Checkpointing with the in-memory saver kept duplicating the entire
        # workflow state (including large research corpora) on every node. That
        # behaviour quickly exhausted memory for real-world projects and the
        # host would kill the process. The workflow does not rely on
        # resumability, so we deliberately compile without a checkpointer to
        # keep memory usage bounded.
        return workflow.compile()
    
    def _route_after_selection(self, state: Dict[str, Any]) -> str:
        """
        Route after select_assumption: either process the assumption or finish.
        
        CRITICAL FIX: When _select_next_assumption finds no more unprocessed assumptions,
        it sets current_assumption = {}. We detect this and route directly to synthesize_report
        to prevent the infinite loop bug.
        
        Returns:
            str: 'process' to continue with analysis, 'finish' to synthesize report
        """
        current_assumption = state.get("current_assumption", {})
        
        # If no assumption to process, we're done - go to report synthesis
        if not current_assumption:
            assumptions = state.get("project_context", {}).get("assumptions", [])
            logger.info(f"🏁 ROUTE: All {len(assumptions)} assumptions processed, routing to synthesize_report")
            return "finish"
        
        # Validate we have a proper assumption ID
        assumption_id = self._extract_assumption_id(current_assumption)
        if assumption_id == "unknown" or not assumption_id:
            logger.warning(f"⚠️ ROUTE: Invalid assumption detected, routing to synthesize_report")
            return "finish"
        
        logger.info(f"▶️ ROUTE: Processing assumption '{assumption_id}'")
        return "process"
    
    def _route_to_analysis_by_component_type(self, state: Dict[str, Any]) -> str:
        """
        Route to the correct analysis agent based on assumption's component_type.
        
        Each assumption is generated with a component_type field:
        - 'jtbd' -> JTBDAnalysisAgent (Jobs-to-be-Done)
        - 'pain' -> PainAnalysisAgent (Pain Points)
        - 'gain' -> GainsAnalysisAgent (Gains & Benefits)
        
        This ensures each assumption is analyzed by only ONE agent that matches its type,
        rather than running all three agents for every assumption.
        
        Returns:
            str: The routing key ('pain', 'gain', or 'jtbd')
        """
        assumption = state.get("current_assumption", {})
        component_type = assumption.get("component_type", "").lower().strip()
        assumption_id = self._extract_assumption_id(assumption)
        
        # Map component_type to routing key
        valid_types = {"pain", "gain", "jtbd"}
        
        if component_type in valid_types:
            logger.info(f"🎯 ROUTING: Assumption '{assumption_id}' has component_type='{component_type}' -> routing to {component_type}_analysis")
            return component_type
        
        # Fallback: Try to infer from assumption text or other fields
        assumption_text = assumption.get("text", "").lower()
        
        # Check for keywords that might indicate the type
        if any(keyword in assumption_text for keyword in ["pain", "problem", "struggle", "difficult", "challenge", "frustrat"]):
            logger.warning(f"⚠️ ROUTING: Assumption '{assumption_id}' missing component_type, inferred 'pain' from text")
            return "pain"
        elif any(keyword in assumption_text for keyword in ["gain", "benefit", "value", "desire", "want", "prefer"]):
            logger.warning(f"⚠️ ROUTING: Assumption '{assumption_id}' missing component_type, inferred 'gain' from text")
            return "gain"
        elif any(keyword in assumption_text for keyword in ["job", "task", "accomplish", "goal", "trying to", "need to"]):
            logger.warning(f"⚠️ ROUTING: Assumption '{assumption_id}' missing component_type, inferred 'jtbd' from text")
            return "jtbd"
        
        # Ultimate fallback: default to pain analysis
        logger.error(f"❌ ROUTING: Assumption '{assumption_id}' has unknown component_type='{component_type}', defaulting to 'pain'")
        return "pain"
    
    def _get_expected_analysis_type(self, component_type: str) -> Optional[str]:
        """
        Map component_type to the expected analysis type key.
        
        This maps the assumption's component_type to the analysis key that will be
        stored in the analyses dictionary by the corresponding agent.
        
        Args:
            component_type: The assumption's component_type ('pain', 'gain', 'jtbd')
            
        Returns:
            The expected analysis type key, or None if unknown
        """
        mapping = {
            "pain": "pain_points",
            "gain": "gains_benefits",
            "jtbd": "jobs_to_be_done"
        }
        return mapping.get(component_type.lower().strip())

    @staticmethod
    def _extract_assumption_id(assumption: Dict[str, Any], fallback_index: Optional[int] = None) -> str:
        """Return a stable assumption identifier for any assumption payload."""

        if not isinstance(assumption, dict):
            if fallback_index is not None:
                return f"assumption_{fallback_index + 1}"
            return "unknown"

        candidate_keys = [
            "id",
            "assumption_id",
            "assumptionId",
            "assumptionID",
            "uuid",
            "uid",
        ]

        for key in candidate_keys:
            value = assumption.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Generate deterministic fallback IDs to avoid "unknown" markers that break state tracking
        if fallback_index is not None:
            return f"assumption_{fallback_index + 1}"

        text_value = assumption.get("text") or assumption.get("assumption")
        if isinstance(text_value, str) and text_value.strip():
            sanitized = "_".join(text_value.strip().split())[:32]
            if sanitized:
                return f"assumption_{sanitized}"

        return "unknown"

    def _normalize_assumptions(self, assumptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize assumptions to guarantee stable IDs and remove duplicates."""

        normalized: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        for index, assumption in enumerate(assumptions):
            if not isinstance(assumption, dict):
                logger.warning("⚠️ WORKFLOW: Skipping malformed assumption entry: %s", assumption)
                continue

            assumption_id = self._extract_assumption_id(assumption, index)

            if assumption_id in seen_ids:
                logger.warning(
                    "⚠️ WORKFLOW: Duplicate assumption '%s' detected. Keeping first instance only.",
                    assumption_id,
                )
                continue

            normalized_assumption = dict(assumption)
            normalized_assumption["id"] = assumption_id
            normalized_assumption.setdefault("assumption_id", assumption_id)

            seen_ids.add(assumption_id)
            normalized.append(normalized_assumption)

        return normalized
    
    async def run_analysis(
        self,
        project_id: str,
        tenant_id: str,
        project_context: Dict[str, Any],
        research_chunks: List[Dict[str, Any]],
        target_assumptions: Optional[List[str]] = None,
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the complete assumption analysis workflow with multi-persona support.
        
        Args:
            project_id: VMP project identifier
            tenant_id: Tenant identifier
            project_context: Full VMP project context
            research_chunks: Processed research data chunks (persona-specific for multi-persona projects)
            target_assumptions: Optional list of specific assumptions to analyze
            persona_id: Persona ID for multi-persona projects (filters assumptions/VPC/hypothesis)
            
        Returns:
            Complete analysis results
        """
        try:
            # Initialize enhanced state as dictionary (TypedDict)
            initial_state = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "persona_id": persona_id,  # Multi-persona support
                "project_context": project_context.copy(),
                "current_assumption": {},
                "target_persona": {},
                "research_chunks": research_chunks,
                
                # Enhanced fields for statistics registry and two-tier RAG
                "statistics_registry": {},  # Will be populated by enhanced components if available
                "persona_data_associations": {},
                "current_ground_truth": {},
                "current_evidence_chunks": [],
                "citation_registry": {},
                
                # Analysis results and metadata
                "assumption_analyses": [],
                "current_assumption_analysis": {},
                "fact_validation_results": {},
                "generated_visualizations": {},
                
                # Report generation
                "report_sections": {},
                "structured_report": None,  # 🚀 JSON ONLY
                
                # Control flow
                "current_step": "initialize",
                "processed_assumptions": [],
                "errors": []
            }
            
            # Initialize required enhanced components
            logger.info("🚀 Enhanced workflow: Initializing enhanced components")
            
            # Statistics registry is required
            if not self.enhanced_components.get('statistics_registry'):
                raise ValueError("Statistics registry is required. Legacy processing removed.")
                
            statistics_registry = self.enhanced_components['statistics_registry']
            if not hasattr(statistics_registry, 'get_statistics_for_analysis'):
                raise ValueError("Statistics registry must have get_statistics_for_analysis method.")
                
            # 🔧 REMOVED: Runtime Statistics Builder - it creates segment-based percentages and RUNTIME citations
            # We work directly with research chunks for file-based analysis
            logger.info("✅ RUNTIME STATS DISABLED: Using direct research chunk analysis (file-based approach)")
            
            # Use empty registries - AI agents work directly with research chunks
            initial_state["statistics_registry"] = {}
            initial_state["citation_registry"] = {}
            initial_state["persona_data_associations"] = {}
            
            # Debug: Check what assumptions are available
            field_prep_data = project_context.get("field_prep_data", {})
            available_assumptions = field_prep_data.get("assumptions", [])
            logger.info(f"🔍 WORKFLOW DEBUG: Available assumptions in field_prep_data: {len(available_assumptions)}")
            
            logger.debug(
                "Field prep data summary: keys=%s, type=%s, assumptions_type=%s, count=%s",
                list(field_prep_data.keys()),
                type(field_prep_data),
                type(available_assumptions),
                len(available_assumptions),
            )

            if isinstance(available_assumptions, list) and available_assumptions:
                sample = available_assumptions[0]
                logger.debug(
                    "First assumption snapshot: type=%s, keys=%s",
                    type(sample),
                    list(sample.keys()) if isinstance(sample, dict) else None,
                )

            # Guard against corrupt payloads without dumping the entire dataset to logs
            if len(available_assumptions) > 50:
                logger.warning(
                    "Unusually high assumption count detected (%s). Limiting to the first 5 entries to protect memory.",
                    len(available_assumptions),
                )
                available_assumptions = available_assumptions[:5]
            elif len(available_assumptions) > 20:
                logger.warning(
                    "High assumption count detected (%s). Limiting to the first 10 entries for stability.",
                    len(available_assumptions),
                )
                available_assumptions = available_assumptions[:10]
            
            for i, assumption in enumerate(available_assumptions):
                logger.info(f"🔍 WORKFLOW DEBUG: Assumption {i}: ID={assumption.get('id', 'NO_ID')}, persona_id={assumption.get('persona_id', 'NO_PERSONA')}, text={assumption.get('text', 'NO_TEXT')[:100]}...")
            
            # MULTI-PERSONA FILTERING: Filter assumptions by persona_id if provided
            if persona_id:
                logger.info(f"🎭 PERSONA FILTER: Filtering assumptions for persona_id='{persona_id}'")
                
                # Debug: Log all persona_ids in assumptions to diagnose mismatches
                all_persona_ids = set(a.get("persona_id") for a in available_assumptions)
                logger.info(f"🎭 PERSONA DEBUG: All persona_ids in assumptions: {all_persona_ids}")
                
                persona_filtered_assumptions = [
                    assumption for assumption in available_assumptions
                    if assumption.get("persona_id") == persona_id
                ]
                logger.info(f"🎭 PERSONA FILTER: Found {len(persona_filtered_assumptions)} assumptions for persona '{persona_id}' out of {len(available_assumptions)} total")
                
                if not persona_filtered_assumptions:
                    logger.warning(f"⚠️ PERSONA FILTER: No assumptions found for persona '{persona_id}'")
                    logger.warning(f"⚠️ PERSONA FILTER: Available persona_ids are: {all_persona_ids}")
                    logger.warning(f"⚠️ PERSONA FILTER: Falling back to ALL {len(available_assumptions)} assumptions")
                    # CRITICAL FIX: Explicitly keep available_assumptions unchanged (use all)
                    # This handles cases where assumptions don't have persona_id or have different format
                else:
                    available_assumptions = persona_filtered_assumptions
                    logger.info(f"✅ PERSONA FILTER: Using {len(available_assumptions)} persona-specific assumptions")
            else:
                logger.info(f"🎭 PERSONA FILTER: No persona_id provided, using all assumptions (single-persona mode)")
            
            # Handle assumptions - either filter by target or use all available
            if target_assumptions:
                logger.info(f"🔍 WORKFLOW DEBUG: Target assumptions requested: {target_assumptions}")
                # Filter assumptions that match target IDs
                assumptions = [
                    assumption for assumption in available_assumptions
                    if assumption.get("id") in target_assumptions
                ]
                logger.info(f"🔍 WORKFLOW DEBUG: Filtered assumptions found: {len(assumptions)}")
                
                if not assumptions:
                    logger.warning(f"⚠️ WORKFLOW: No assumptions found matching target IDs {target_assumptions}")
                    # Use all available assumptions if no matches found
                    assumptions = available_assumptions
                    logger.info(f"🔍 WORKFLOW DEBUG: Using all {len(assumptions)} available assumptions instead")
            else:
                logger.info(f"🔍 WORKFLOW DEBUG: No target assumptions specified, using all {len(available_assumptions)} available assumptions")
                assumptions = available_assumptions
            
            # Set assumptions in the state for workflow processing
            if assumptions:
                # Ensure assumptions have stable IDs and contain no duplicates.
                normalized_assumptions = self._normalize_assumptions(assumptions)

                if not normalized_assumptions:
                    logger.error("❌ WORKFLOW: Normalization removed all assumptions - aborting analysis")
                    initial_state["errors"].append("No valid assumptions available after normalization")
                    return {
                        "success": False,
                        "analysis_results": [],
                        "final_report": "",
                        "errors": initial_state["errors"],
                    }

                assumptions = normalized_assumptions

                # Store in both locations for compatibility
                initial_state["project_context"]["assumptions"] = assumptions
                initial_state["project_context"]["field_prep_data"] = initial_state["project_context"].get("field_prep_data", {})
                initial_state["project_context"]["field_prep_data"]["assumptions"] = assumptions
                logger.info(f"✅ WORKFLOW: Set {len(assumptions)} assumptions for analysis")

                # Log the assumptions that will be processed
                for i, assumption in enumerate(assumptions):
                    logger.info(f"📋 WORKFLOW: Will process assumption {i+1}: {assumption.get('id')} - {assumption.get('text', '')[:100]}...")
            else:
                logger.error(f"❌ WORKFLOW: No assumptions available for analysis!")
                initial_state["errors"].append("No assumptions available for analysis")
            
            # Run workflow with increased recursion limit and timeout
            # For 3-6 assumptions, we need ~20-30 steps max (5 agents + validation + comparison per assumption)
            # Setting to 100 to be safe, but should never hit this with proper state management
            config = {
                "configurable": {"thread_id": f"analysis_{project_id}"},
                "recursion_limit": 100,  # Increased from 50 (3-6 assumptions should need ~30 max)
                "max_execution_time": 600  # 10 minute timeout
            }
            
            logger.info(f"🚀 WORKFLOW: Starting LangGraph execution with {len(assumptions)} assumptions")
            final_state = await self.workflow.ainvoke(initial_state, config)
            logger.info(f"✅ WORKFLOW: LangGraph execution completed")
            
            # CRITICAL FIX: Load full analyses from database (streaming optimization)
            # Memory state only has summaries, we need full data for API response
            analysis_results = await self._load_analyses_from_database(final_state)
            
            if not analysis_results:
                # Fallback to memory state if database load fails
                logger.warning("⚠️ WORKFLOW: Database load failed, using memory state (may be incomplete)")
                analysis_results = final_state.get("assumption_analyses", [])
            
            # 🚀 JSON ONLY: Extract structured_report (NO MARKDOWN!)
            structured_report = final_state.get("structured_report")  # 🚀 JSON ONLY
            errors = final_state.get("errors", [])
            
            logger.info(f"✅ WORKFLOW: Completed analysis of {len(analysis_results)} assumptions")
            logger.info(f"🚀 JSON WORKFLOW: Structured report present: {structured_report is not None}")
            if structured_report:
                logger.info(f"🚀 JSON WORKFLOW: Structured report has {len(structured_report.get('assumptions', []))} assumptions")
            
            return {
                "success": True,
                "analysis_results": analysis_results,  # Now from database, not memory
                "structured_report": structured_report,  # 🚀 JSON ONLY - NO MARKDOWN!
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Analysis workflow failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis_results": [],
                "final_report": "",
                "errors": [str(e)]
            }
    
    async def _initialize_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the analysis workflow."""
        logger.info(f"Initializing analysis for project {state['project_id']}")
        
        state["current_step"] = "initialized"
        state["processed_assumptions"] = []
        state["retrieval_cache"] = {}
        state["context_flags"] = {}
        
        # Validate project context - check both locations for assumptions
        assumptions = (
            state.get("project_context", {}).get("assumptions", []) or
            state.get("project_context", {}).get("field_prep_data", {}).get("assumptions", [])
        )
        
        if not assumptions:
            state["errors"].append("No assumptions found in project context")
            return state
        
        if not state.get("research_chunks"):
            state["errors"].append("No research data available for analysis")
            return state
        
        # Normalize assumptions location for consistent access
        state["project_context"]["assumptions"] = assumptions
        
        logger.info(f"Found {len(assumptions)} assumptions to analyze")
        
        # EDGE CASE: Validate assumption count (normal is 2-6)
        if len(assumptions) == 0:
            logger.error(f"❌ ERROR: No assumptions found in project context")
            state["errors"].append("No assumptions available for analysis")
            return state
        elif len(assumptions) > 20:
            # Likely data corruption - limit to reasonable number
            logger.error(f"⚠️ DATA ISSUE: {len(assumptions)} assumptions found (expected 2-6)")
            logger.error(f"⚠️ DATA ISSUE: Limiting to first 10 to prevent memory issues")
            assumptions = assumptions[:10]
            state["project_context"]["assumptions"] = assumptions
        
        return state
    
    async def _select_next_assumption(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select the next assumption to analyze.
        
        CRITICAL FIX: Check database to see what's already been processed
        since state mutations aren't persisting properly in LangGraph.
        """
        # CRITICAL FIX: Clear current_assumption_analysis at the START of selection
        # This prevents previous assumption data from contaminating the next one
        state["current_assumption_analysis"] = {}
        logger.info("🧹 SELECT: Cleared current_assumption_analysis for fresh start")
        
        assumptions = state["project_context"].get("assumptions", [])
        processed = state.get("processed_assumptions", [])
        
        # CRITICAL: Load from database to see what's actually been processed
        # MULTI-PERSONA FIX: Filter by persona_id to avoid cross-persona contamination
        current_persona_id = state.get("persona_id")
        try:
            from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
            db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
            existing_analyses = await db_adapter.load_analysis_results(
                state.get("project_id"), state.get("tenant_id")
            )
            
            # Get unique assumption IDs from database
            # MULTI-PERSONA FIX: Only count analyses for the CURRENT persona as processed
            db_processed = set()
            for analysis in existing_analyses:
                assumption_id = analysis.get("assumption_id")
                analysis_persona_id = analysis.get("persona_id")
                
                # Only count as processed if it's for the same persona (or no persona specified)
                if assumption_id:
                    if current_persona_id:
                        # Multi-persona mode: only count same-persona analyses
                        if analysis_persona_id == current_persona_id:
                            db_processed.add(assumption_id)
                            logger.debug(f"🎭 SELECT: Counting '{assumption_id}' as processed (persona match: {analysis_persona_id})")
                        else:
                            logger.debug(f"🎭 SELECT: Ignoring '{assumption_id}' from different persona '{analysis_persona_id}' (current: {current_persona_id})")
                    else:
                        # Single-persona mode: count all
                        db_processed.add(assumption_id)
            
            logger.info(f"🔍 SELECT: Database has {len(existing_analyses)} total analyses")
            logger.info(f"🎭 SELECT: For persona '{current_persona_id}': {len(db_processed)} unique assumptions processed")
            logger.info(f"🔍 SELECT: Database processed IDs (this persona): {list(db_processed)}")
            logger.info(f"🔍 SELECT: Memory processed IDs: {processed}")
            
            # Use database as source of truth (filtered by persona)
            processed = list(db_processed)
            
        except Exception as e:
            logger.error(f"❌ SELECT: Failed to load from database: {e}")
        
        logger.info(f"📋 SELECT: Checking {len(assumptions)} assumptions, {len(processed)} already processed")
        
        # Simple iteration - find first unprocessed assumption
        for i, assumption in enumerate(assumptions):
            assumption_id = self._extract_assumption_id(assumption, i)
            
            logger.info(f"🔍 SELECT: Checking assumption '{assumption_id}' - in processed? {assumption_id in processed}")
            
            if assumption_id not in processed:
                # Found unprocessed assumption
                state["current_assumption"] = assumption
                
                # Find corresponding persona
                persona_name = assumption.get("persona_name", "")
                personas = state["project_context"].get("vpc_data", {}).get("personas_data", [])
                target_persona = next(
                    (p for p in personas if p.get("name") == persona_name),
                    {"name": persona_name, "description": f"Persona for {persona_name}"}
                )
                state["target_persona"] = target_persona
                
                logger.info(f"✅ SELECT: Selected assumption {i+1}/{len(assumptions)}: '{assumption_id}' for persona '{persona_name}'")
                return state
            else:
                logger.info(f"⏭️ SELECT: Skipping '{assumption_id}' - already processed")
        
        # All assumptions processed
        logger.info(f"🏁 SELECT: All {len(assumptions)} assumptions completed")
        state["current_assumption"] = {}
        state["target_persona"] = {}
        return state
    
    async def _prepare_analysis_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced context preparation with two-tier RAG system."""
        if not state.get("current_assumption"):
            return state
        
        try:
            assumption = state["current_assumption"]
            research_chunks = state["research_chunks"]
            statistics_registry = state.get("statistics_registry", {})
            
            assumption_id = self._extract_assumption_id(assumption)
            retrieval_cache = state.setdefault("retrieval_cache", {})
            context_flags: Dict[str, Any] = {"assumption_id": assumption_id}

            if assumption_id in retrieval_cache:
                cached_packet = retrieval_cache[assumption_id]
                logger.info(
                    "♻️ CONTEXT: Reusing cached retrieval packet for assumption %s", assumption_id
                )
                cached_flags = cached_packet.get("context_flags", {})
                context_flags.update(cached_flags)
                context_flags["retrieval_cached"] = True
                state["current_ground_truth"] = cached_packet.get("ground_truth", {})
                state["current_evidence_chunks"] = cached_packet.get("evidence", [])
                state["current_relevant_data"] = cached_packet.get("evidence", [])
                state["context_flags"] = context_flags
                return state

            logger.info("🚀 Enhanced context preparation: Using two-tier RAG system")

            persona_id = state.get("target_persona", {}).get("id")

            # 🔧 REMOVED: Runtime statistics builder fallback
            # We work directly with research chunks for file-based analysis
            has_registry_data = bool(statistics_registry)
            if not has_registry_data:
                logger.info(
                    "✅ CONTEXT: Empty statistics registry for assumption %s - using direct research chunk analysis",
                    assumption_id,
                )
                context_flags["partial_ground_truth"] = True
            else:
                context_flags["partial_ground_truth"] = False

            ground_truth = await self._get_ground_truth_statistics(
                state, assumption, persona_id
            )
            state["current_ground_truth"] = ground_truth

            evidence_chunks = await self._get_balanced_evidence_chunks(
                state, assumption, persona_id
            )
            state["current_evidence_chunks"] = evidence_chunks

            logger.info(
                "✅ Two-tier RAG: %s statistics + %s evidence chunks",
                len(ground_truth or {}),
                len(evidence_chunks),
            )

            state["current_relevant_data"] = evidence_chunks

            retrieval_cache[assumption_id] = {
                "ground_truth": ground_truth,
                "evidence": evidence_chunks,
                "context_flags": context_flags.copy(),
            }
            context_flags["retrieval_cached"] = False
            state["context_flags"] = context_flags

        except Exception as e:
            logger.error(f"❌ CRITICAL: Enhanced context preparation failed: {str(e)}")
            # Fail-fast: Enhanced processing is required
            raise ValueError(f"Enhanced context preparation failed. Legacy fallback removed: {str(e)}")
        
        return state
    
    async def _get_ground_truth_statistics(
        self, 
        state: Dict[str, Any], 
        assumption: Dict[str, Any], 
        persona_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get ground truth statistics for Tier 1 of two-tier RAG."""
        try:
            statistics_registry = state.get("statistics_registry", {})
            if not statistics_registry:
                return {}
            
            # Filter statistics relevant to this assumption and persona
            relevant_stats = {}
            
            # Get CSV statistics
            csv_stats = statistics_registry.get("csv_statistics", {})
            if csv_stats:
                relevant_stats["csv_statistics"] = csv_stats
            
            # Get PDF statistics
            pdf_stats = statistics_registry.get("pdf_statistics", {})
            if pdf_stats:
                relevant_stats["pdf_statistics"] = pdf_stats
            
            # Filter by persona if specified
            if persona_id:
                persona_mappings = statistics_registry.get("persona_mappings", {})
                persona_stats = persona_mappings.get(persona_id, {})
                if persona_stats:
                    relevant_stats["persona_specific"] = persona_stats
            
            return relevant_stats
            
        except Exception as e:
            logger.error(f"Error getting ground truth statistics: {e}")
            return {}
    
    async def _get_balanced_evidence_chunks(
        self,
        state: Dict[str, Any],
        assumption: Dict[str, Any],
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get balanced evidence chunks for Tier 2 of two-tier RAG."""
        try:
            project_id = state.get("project_id")
            tenant_id = state.get("tenant_id")
            persona = state.get("target_persona", {})
            assumption_id = self._extract_assumption_id(assumption)

            evidence_query = " ".join(
                filter(
                    None,
                    [
                        assumption.get("text", ""),
                        persona.get("name"),
                        "general" if not persona_id else persona_id,
                    ],
                )
            ).strip()

            retrieved = await self.evidence_retrieval.retrieve_balanced_evidence(
                query=evidence_query,
                project_id=project_id,
                tenant_id=tenant_id,
                analysis_type="general",
                persona_id=persona_id,
                assumption_id=assumption_id,
                assumption=assumption,
                persona=persona,
            )

            if retrieved:
                return retrieved

            research_chunks = state.get("research_chunks", [])

            if hasattr(self, "persona_correlation") and self.persona_correlation:
                return await self.persona_correlation.find_persona_relevant_data(
                    assumption, persona_id or "general", "general"
                )

            return await self.correlation_engine.find_relevant_data(
                assumption=assumption,
                research_chunks=research_chunks,
                analysis_type="general",
                top_k=20
            )

        except Exception as e:
            logger.error(f"Error getting balanced evidence chunks: {e}")
            return []
    
    async def _get_analysis_specific_statistics(
        self, 
        state: Dict[str, Any], 
        assumption: Dict[str, Any], 
        analysis_type: str
    ) -> Dict[str, Any]:
        """Get statistics specific to the analysis type."""
        try:
            statistics_registry = state.get("statistics_registry", {})
            if not statistics_registry:
                return {}
            
            # Filter statistics based on analysis type
            type_keywords = {
                'pain': ['problems', 'challenges', 'difficulties', 'frustrations'],
                'size': ['frequency', 'percentage', 'statistics', 'numbers'],
                'solution': ['solutions', 'alternatives', 'tools', 'methods'],
                'gains': ['benefits', 'advantages', 'value', 'outcomes'],
                'jtbd': ['tasks', 'jobs', 'goals', 'objectives']
            }
            
            keywords = type_keywords.get(analysis_type, [])
            
            # For now, return all statistics - filtering can be enhanced later
            return state.get("current_ground_truth", {})
            
        except Exception as e:
            logger.error(f"Error getting analysis-specific statistics: {e}")
            return {}
    
    async def _get_analysis_specific_evidence(
        self, 
        state: Dict[str, Any], 
        assumption: Dict[str, Any], 
        analysis_type: str
    ) -> List[Dict[str, Any]]:
        """Get evidence chunks specific to the analysis type."""
        try:
            research_chunks = state["research_chunks"]
            
            # Use correlation engine with analysis type
            relevant_data = await self.correlation_engine.find_relevant_data(
                assumption=assumption,
                research_chunks=research_chunks,
                analysis_type=analysis_type,
                top_k=20
            )
            
            return relevant_data
            
        except Exception as e:
            logger.error(f"Error getting analysis-specific evidence: {e}")
            return []
    
    async def _run_pain_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run pain point analysis."""
        return await self._run_agent_analysis(state, self.pain_agent, "pain")
    
    # REMOVED: _run_size_analysis - Problem Size & Frequency Analysis removed
    # async def _run_size_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
    #     """Run size/frequency analysis."""
    #     return await self._run_agent_analysis(state, self.size_agent, "size")
    
    # REMOVED: _run_solution_analysis - Current Solutions Analysis removed
    # async def _run_solution_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
    #     """Run solution analysis."""
    #     return await self._run_agent_analysis(state, self.solution_agent, "solution")
    
    async def _run_gains_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run gains analysis."""
        return await self._run_agent_analysis(state, self.gains_agent, "gains")
    
    async def _run_jtbd_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run jobs-to-be-done analysis."""
        return await self._run_agent_analysis(state, self.jtbd_agent, "jtbd")
    
    async def _run_agent_analysis(
        self,
        state: Dict[str, Any],
        agent: BaseAnalysisAgent,
        analysis_type: str
    ) -> Dict[str, Any]:
        """Enhanced agent analysis with two-tier RAG and fact validation."""
        if not state.get("current_assumption"):
            return state
        
        try:
            assumption = state["current_assumption"]
            statistics_registry = state.get("statistics_registry", {})
            
            # 🚨 CRITICAL FIX: Always use enhanced processing (two-tier RAG) regardless of statistics
            # The legacy correlation path is broken due to empty research_chunks
            if True:  # Force enhanced path - statistics_registry can be empty
                logger.info(f"🚀 FORCED Enhanced {analysis_type} analysis: Using two-tier RAG (bypassing statistics check)")
                
                # Get type-specific ground truth statistics
                ground_truth = await self._get_analysis_specific_statistics(
                    state, assumption, analysis_type
                )
                
                # Get type-specific evidence chunks
                evidence_chunks = await self._get_analysis_specific_evidence(
                    state, assumption, analysis_type
                )
                
                # Update state with analysis-specific data
                state["current_ground_truth"] = ground_truth
                state["current_evidence_chunks"] = evidence_chunks
                state["current_relevant_data"] = evidence_chunks  # Backward compatibility
                
                logger.info(f"✅ {analysis_type} analysis: {len(ground_truth)} stats + {len(evidence_chunks)} evidence")
                
            else:
                logger.info(f"📊 Standard {analysis_type} analysis: Using legacy correlation")
                
                # Use legacy correlation engine
                research_chunks = state["research_chunks"]
                relevant_data = await self.correlation_engine.find_relevant_data(
                    assumption=assumption,
                    research_chunks=research_chunks,
                    analysis_type=analysis_type,
                    top_k=20
                )
                
                state["current_relevant_data"] = relevant_data
                state["current_evidence_chunks"] = relevant_data
                state["current_ground_truth"] = {}
            
            # Run agent analysis - the agent handles state updates internally
            await agent.analyze_for_assumption(state)

            logger.info(f"Completed {analysis_type} analysis for assumption")

            # Clean up analysis-specific data
            state.pop("current_relevant_data", None)
            state.pop("current_ground_truth", None)
            state.pop("current_evidence_chunks", None)
            
        except Exception as e:
            assumption_id = (
                self._extract_assumption_id(assumption)
                if 'assumption' in locals()
                else "unknown"
            )
            logger.error(f"❌ WORKFLOW: Error in {analysis_type} analysis for assumption {assumption_id}: {str(e)}")
            state["errors"] = [f"{analysis_type} analysis failed for {assumption_id}: {str(e)}"]
            
            # Create error result for concurrent-safe merge
            error_analysis = {
                "analyses": {
                    analysis_type: {
                        "claim": f"Analysis failed: {str(e)}",
                        "accuracy_level": "low",
                        "supporting_evidence": [],
                        "confidence_score": 0.0,
                        "key_findings": []
                    }
                }
            }
            
            # Initialize if needed and merge error result
            if "current_assumption_analysis" not in state:
                state["current_assumption_analysis"] = {
                    "assumption_id": self._extract_assumption_id(state.get("current_assumption", {})),
                    "assumption_text": state.get("current_assumption", {}).get("text", ""),
                    "persona_name": state.get("target_persona", {}).get("name", ""),
                    "analyses": {}
                }
            
            # Merge error analysis (concurrent-safe)
            state["current_assumption_analysis"] = error_analysis
        
        return state
    
    async def _validate_assumption(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the assumption based on its single analysis type (component_type routing)."""
        assumption_id = self._extract_assumption_id(state.get("current_assumption", {}))
        assumption = state.get("current_assumption", {})
        component_type = assumption.get("component_type", "unknown")
        
        logger.debug("Validator invoked for assumption %s", assumption_id)
        logger.info(f"🔍 WORKFLOW: Validating assumption {assumption_id} (component_type: {component_type})")
        
        if not state.get("current_assumption_analysis"):
            logger.warning(f"⚠️ WORKFLOW: No analysis data available for assumption {assumption_id}")
            return state
        
        raw_analyses = state["current_assumption_analysis"].get("analyses", {})
        completed_types = set(raw_analyses.keys())
        
        # DEBUG: Log what's actually in the current_assumption_analysis
        logger.debug(
            "Validation input summary: keys=%s, analysis_types=%s",
            list(state["current_assumption_analysis"].keys()),
            list(raw_analyses.keys()),
        )
        
        # COMPONENT-TYPE ROUTING: Each assumption should have exactly ONE analysis type
        # based on its component_type (pain, gain, or jtbd)
        expected_analysis_type = self._get_expected_analysis_type(component_type)
        
        if not completed_types:
            logger.error(f"❌ WORKFLOW ERROR: No analysis completed for assumption {assumption_id}")
        elif expected_analysis_type and expected_analysis_type not in completed_types:
            logger.warning(
                f"⚠️ WORKFLOW: Expected analysis type '{expected_analysis_type}' not found for "
                f"assumption {assumption_id} (component_type: {component_type}). Found: {completed_types}"
            )
        else:
            logger.info(f"✅ WORKFLOW: Analysis type '{list(completed_types)[0]}' completed for assumption {assumption_id}")
        
        try:
            logger.debug("Starting validation merge for assumption %s", assumption_id)
            
            # Convert analyses to AnalysisOutput objects for validator
            analyses = {}
            
            for analysis_type, analysis_data in raw_analyses.items():
                from ..models.analysis_models import AnalysisOutput
                analyses[analysis_type] = AnalysisOutput(**analysis_data)
            
            # Ensure the current assumption analysis is complete before validation
            state["current_assumption_analysis"]["validation_status"] = "in_progress"
            
            # Use ValidatorAgent for validation
            validation_result = await self.validator_agent.validate_assumption(
                assumption=state["current_assumption"],
                analyses=analyses,
                persona=state["target_persona"]
            )
            
            # Merge validation results into current analysis
            state["current_assumption_analysis"].update({
                "validation": validation_result,
                "validation_status": validation_result.get("validation_status", "completed"),
                "overall_confidence": validation_result.get("overall_confidence", 0.0),
                "key_findings": validation_result.get("key_findings", []),
                "evidence_strength": validation_result.get("evidence_strength", {}),
                "validation_summary": validation_result.get("validation_summary", ""),
                "analysis_breakdown": validation_result.get("analysis_breakdown", {})
            })
            
            # Ensure core fields are set properly
            if not state["current_assumption_analysis"].get("assumption_text"):
                state["current_assumption_analysis"]["assumption_text"] = state["current_assumption"].get("text", "Unknown assumption")
            if not state["current_assumption_analysis"].get("assumption_id"):
                state["current_assumption_analysis"]["assumption_id"] = assumption_id
            if not state["current_assumption_analysis"].get("persona_name"):
                state["current_assumption_analysis"]["persona_name"] = state["target_persona"].get("name", "Unknown persona")
            
            # COMPONENT-TYPE ROUTING: Preserve component_type and persona_id for report generation
            if not state["current_assumption_analysis"].get("component_type"):
                state["current_assumption_analysis"]["component_type"] = state["current_assumption"].get("component_type", "")
            if not state["current_assumption_analysis"].get("persona_id"):
                state["current_assumption_analysis"]["persona_id"] = state["current_assumption"].get("persona_id", "")
            
            # Move completed analysis to the main assumption_analyses list
            completed_analysis = dict(state["current_assumption_analysis"])
            
            logger.info(f"✅ WORKFLOW: Validation completed for assumption {assumption_id}")
            
            # STREAMING RESULTS: Store analysis immediately to database and keep only ID in memory
            try:
                await self._stream_analysis_to_database(completed_analysis, state)
                logger.info(f"✅ STREAMING: Stored analysis {assumption_id} to database")
                
                # Keep only essential data in memory - store full analysis in DB
                analysis_summary = {
                    "assumption_id": completed_analysis.get("assumption_id"),
                    "assumption_text": completed_analysis.get("assumption_text", "")[:100] + "...",  # Truncated
                    "validation_status": completed_analysis.get("validation_status"),
                    "overall_confidence": completed_analysis.get("overall_confidence", 0.0),
                    "stored_in_db": True,
                    "stored_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ STREAMING ERROR: Failed to store analysis to database: {e}")
                # Fallback: keep in memory if DB storage fails
                analysis_summary = completed_analysis
            
            # For LangGraph operator.add, we need to return the items to be added
            current_processed = state.get("processed_assumptions", [])
            
            # Return minimal data - full analysis is in database
            # CRITICAL FIX: Only add to assumption_analyses if not already present (prevent LangGraph operator.add duplicates)
            existing_assumption_ids = [a.get("assumption_id") for a in state.get("assumption_analyses", [])]
            
            logger.info(f"🔍 DUPLICATE FIX: Checking if {assumption_id} already in assumption_analyses")
            logger.info(f"🔍 DUPLICATE FIX: Existing assumption IDs: {existing_assumption_ids}")
            logger.info(f"🔍 DUPLICATE FIX: Will add to list? {assumption_id not in existing_assumption_ids}")
            
            # CRITICAL FIX: NEVER add to assumption_analyses in workflow - only use database storage
            return {
                "processed_assumptions": [assumption_id],  # Always return to ensure state merge
                "current_assumption_analysis": {}  # Clear current analysis
            }
            
        except Exception as e:
            logger.error(f"❌ WORKFLOW: Validation failed for assumption {assumption_id}: {e}")
            state["errors"] = [f"Assumption validation failed: {str(e)}"]
            
            # Return error analysis for LangGraph merge
            logger.info(f"✅ WORKFLOW: Marked assumption {assumption_id} as COMPLETED (with errors)")
            
            # CRITICAL FIX: NEVER add to assumption_analyses in workflow - only use database storage
            return {
                "processed_assumptions": [assumption_id],  # Always return to ensure state merge
                "current_assumption_analysis": {}
            }
    
    # REMOVED: _run_pv_comparison method
    # PV comparison is no longer part of the market research workflow
    # The analysis now stands on its own without comparing to PV report
    
    async def _check_completion(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if all assumptions have been processed using DATABASE as source of truth."""
        assumptions = state["project_context"].get("assumptions", [])
        
        # CRITICAL FIX: Use database as source of truth, not in-memory state
        # This matches what _select_next_assumption does
        current_persona_id = state.get("persona_id")
        try:
            from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
            db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
            existing_analyses = await db_adapter.load_analysis_results(
                state.get("project_id"), state.get("tenant_id")
            )
            
            # Count unique assumption IDs from database for this persona
            db_processed = set()
            for analysis in existing_analyses:
                assumption_id = analysis.get("assumption_id")
                analysis_persona_id = analysis.get("persona_id")
                if assumption_id:
                    if current_persona_id:
                        if analysis_persona_id == current_persona_id:
                            db_processed.add(assumption_id)
                    else:
                        db_processed.add(assumption_id)
            
            processed_count = len(db_processed)
        except Exception as e:
            logger.error(f"❌ CHECK_COMPLETION: Failed to load from database: {e}")
            processed_count = len(state.get("processed_assumptions", []))
        
        logger.info(f"Analysis progress: {processed_count}/{len(assumptions)} assumptions completed")
        
        return state
    
    async def _synthesize_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize comprehensive report using ReportSynthesizerAgent with streamed data."""
        logger.info("Starting comprehensive report synthesis with streamed data")
        
        try:
            # STREAMING APPROACH: Load full analysis data from database for report synthesis
            full_analyses = await self._load_analyses_from_database(state)
            
            logger.info(f"📊 REPORT: Loaded {len(full_analyses)} analyses from database for synthesis")
            
            if full_analyses:
                # Create temporary state with full data for report synthesis
                temp_state = dict(state)
                temp_state["assumption_analyses"] = full_analyses
                
                # Use the ReportSynthesizerAgent to generate the full report
                updated_state = await self.report_synthesizer.synthesize_report(temp_state)
                
                # 🚀 JSON ONLY: Extract structured_report (NO MARKDOWN!)
                structured_report_from_agent = updated_state.get("structured_report")
                logger.info(f"🔍 EXTRACT: structured_report from agent: {structured_report_from_agent is not None}")
                logger.info(f"🔍 EXTRACT: Type: {type(structured_report_from_agent)}")
                
                if structured_report_from_agent:
                    logger.info(f"🔍 EXTRACT: Keys: {list(structured_report_from_agent.keys())}")
                    state["structured_report"] = structured_report_from_agent
                    logger.info(f"✅ STORED: structured_report in state")
                else:
                    logger.error(f"❌ ERROR: structured_report from agent is None!")
                
                # DO NOT merge assumption_analyses from updated_state back to state
                logger.info("✅ Report synthesis completed: JSON ONLY")
                logger.info(f"🚀 JSON: structured_report present: {state.get('structured_report') is not None}")
                logger.info(f"🔍 STATE CHECK: state keys = {list(state.keys())}")
                logger.info(f"🔍 STATE CHECK: 'structured_report' in state = {'structured_report' in state}")
                
                # Clear temporary full data to free memory
                del temp_state
                gc.collect()
                
            else:
                logger.warning("No full analyses available from database, using fallback")
                state["final_report"] = self._generate_basic_fallback_report(state["assumption_analyses"])
            
            return state
            
        except Exception as e:
            logger.error(f"Error in report synthesis: {str(e)}")
            state["errors"].append(f"Report synthesis failed: {str(e)}")
            
            # Fallback to basic report if synthesis fails
            state["final_report"] = self._generate_basic_fallback_report(state["assumption_analyses"])
            return state
    
    def _should_continue(self, state: Dict[str, Any]) -> str:
        """
        Determine if workflow should continue or finish.
        
        CRITICAL FIX: This is a SYNCHRONOUS function (LangGraph conditional edge).
        Cannot reliably run async database calls here. Instead, use the signal from
        _select_next_assumption: when it sets current_assumption = {}, all assumptions
        are processed and we should finish.
        
        The workflow flow is:
        1. validate_assumption -> check_completion -> _should_continue (this function)
        2. If "continue": select_assumption -> prepare_context -> analysis -> back to 1
        3. If "finish": synthesize_report -> finalize -> END
        
        When _select_next_assumption finds no more unprocessed assumptions, it sets
        current_assumption = {} and target_persona = {}. This is the reliable signal.
        """
        assumptions = state["project_context"].get("assumptions", [])
        current_assumption = state.get("current_assumption", {})
        
        # PRIMARY CHECK: If current_assumption is empty, _select_next_assumption found
        # no more unprocessed assumptions - we're done!
        if not current_assumption:
            logger.info(f"🏁 COMPLETE: All {len(assumptions)} assumptions processed (current_assumption is empty), finishing workflow")
            return "finish"
        
        # SECONDARY CHECK: If current_assumption has no valid ID, we're also done
        # This handles edge cases where current_assumption might be set but invalid
        assumption_id = self._extract_assumption_id(current_assumption)
        if assumption_id == "unknown" or not assumption_id:
            logger.info(f"🏁 COMPLETE: All assumptions processed (no valid current assumption), finishing workflow")
            return "finish"
        
        # We have a valid current assumption to process - continue the workflow
        logger.info(f"▶️ CONTINUE: Processing assumption '{assumption_id}'")
        return "continue"
    
    async def _finalize_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the analysis and generate report."""
        logger.info("✅ Finalizing analysis workflow")
        
        # 🔍 DEBUG: Check what's in state when finalize is called
        logger.info(f"🔍 FINALIZE DEBUG: state keys = {list(state.keys())}")
        logger.info(f"🔍 FINALIZE DEBUG: 'structured_report' in state = {'structured_report' in state}")
        logger.info(f"🔍 FINALIZE DEBUG: structured_report value = {state.get('structured_report')}")
        logger.info(f"🔍 FINALIZE DEBUG: structured_report type = {type(state.get('structured_report'))}")
        
        state["current_step"] = "completed"
        
        # Log completion summary
        analyses_count = len(state.get("assumption_analyses", []))
        logger.info(f"📊 FINALIZE: Completed with {analyses_count} analysis summaries in memory")
        
        # 🚀 JSON ONLY: Check for structured_report (NO MARKDOWN!)
        if state.get("structured_report"):
            logger.info(f"✅ FINALIZE: JSON report present with {len(state['structured_report'].get('assumptions', []))} assumptions")
            logger.info("💬 FINALIZE: Chat preparation will happen AFTER database save")
        else:
            logger.warning("⚠️ FINALIZE: No JSON report found!")
        
        # MEMORY CLEANUP: Force garbage collection after analysis completion
        gc.collect()
        logger.info("🧹 FINALIZE: Garbage collection completed")
        
        return state
    

    
    def _generate_basic_fallback_report(self, analyses: List[Dict[str, Any]]) -> str:
        """Generate a basic fallback report when full synthesis fails."""
        if not analyses:
            return "No analysis results available."
        
        report_lines = [
            "# Market Research Analysis Report (Basic Fallback)",
            "",
            f"**Note:** This is a basic fallback report. Full report synthesis failed.",
            "",
            f"Analyzed {len(analyses)} assumptions:",
            ""
        ]
        
        for i, analysis in enumerate(analyses, 1):
            assumption_text = analysis.get("assumption_text", "Unknown assumption")
            assumption_id = analysis.get("assumption_id", f"assumption-{i}")
            validation_status = analysis.get("validation_status", "unknown")
            confidence = analysis.get("overall_confidence", 0.0)
            persona_name = analysis.get("persona_name", "Unknown persona")
            
            # Status emoji
            status_emoji = "✅" if validation_status == "validated" else "⚠️" if validation_status == "partially_validated" else "❌"
            
            report_lines.extend([
                f"## {i}. {status_emoji} {assumption_text}",
                f"**ID:** {assumption_id}",
                f"**Persona:** {persona_name}",
                f"**Status:** {validation_status.replace('_', ' ').title()}",
                f"**Confidence:** {confidence:.2f}",
                ""
            ])
            
            # Add analysis breakdown if available
            analyses_data = analysis.get("analyses", {})
            if analyses_data:
                report_lines.append("**Analysis Results:**")
                for analysis_type, analysis_result in analyses_data.items():
                    claim = analysis_result.get("claim", "No claim available")
                    accuracy = analysis_result.get("accuracy_level", "unknown")
                    report_lines.append(f"- **{analysis_type.replace('_', ' ').title()}:** {claim} (Accuracy: {accuracy})")
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    async def _stream_analysis_to_database(self, analysis_data: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """
        Stream analysis results immediately to database to prevent memory accumulation.
        
        Args:
            analysis_data: Complete analysis data to store
            state: Current workflow state for context
            
        Returns:
            True if successful, False otherwise
        """
        try:
            project_id = state.get("project_id")
            tenant_id = state.get("tenant_id")
            
            if not project_id or not tenant_id:
                logger.error("❌ STREAMING: Missing project_id or tenant_id for database storage")
                return False
            
            # Use the database adapter to store analysis results
            from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
            db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
            
            # Create analysis record for database
            assumption_id = analysis_data.get("assumption_id")
            if not assumption_id or assumption_id == "unknown":
                assumption_id = self._extract_assumption_id(state.get("current_assumption", {}))
                if not assumption_id or assumption_id == "unknown":
                    logger.error("❌ STREAMING: Unable to determine assumption_id for database storage")
                    return False
                analysis_data["assumption_id"] = assumption_id

            analysis_record = {
                "project_id": project_id,
                "tenant_id": tenant_id,
                "assumption_id": assumption_id,
                "assumption_text": analysis_data.get("assumption_text") or state.get("current_assumption", {}).get("text"),
                "persona_name": analysis_data.get("persona_name"),
                "validation_status": analysis_data.get("validation_status"),
                "overall_confidence": analysis_data.get("overall_confidence", 0.0),
                "key_findings": analysis_data.get("key_findings", []),
                "evidence_strength": analysis_data.get("evidence_strength", {}),
                "validation_summary": analysis_data.get("validation_summary", ""),
                "analysis_breakdown": analysis_data.get("analysis_breakdown", {}),
                "analyses": analysis_data.get("analyses", {}),
                # REMOVED: pv_comparison field - no longer stored
                "created_at": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            # 🔍 CRITICAL DEBUG: Check if analyses dict has statistical_data
            analyses_dict = analysis_data.get("analyses", {})
            logger.info(f"🔍 STORAGE DEBUG: analyses dict keys: {list(analyses_dict.keys())}")
            for analysis_type, analysis_content in analyses_dict.items():
                if isinstance(analysis_content, dict):
                    has_stat_data = "statistical_data" in analysis_content
                    stat_data_empty = not analysis_content.get("statistical_data") if has_stat_data else True
                    logger.info(f"🔍 STORAGE DEBUG: {analysis_type} - has statistical_data: {has_stat_data}, is_empty: {stat_data_empty}")
                    if has_stat_data and not stat_data_empty:
                        stat_keys = list(analysis_content.get("statistical_data", {}).keys())
                        logger.info(f"🔍 STORAGE DEBUG: {analysis_type} statistical_data keys: {stat_keys}")
            
            # Store in database (implement this method in database adapter)
            success = await db_adapter.store_analysis_result(analysis_record)
            
            if success:
                logger.info(f"✅ STREAMING: Successfully stored analysis {analysis_data.get('assumption_id')} to database")
                return True
            else:
                logger.error(f"❌ STREAMING: Failed to store analysis to database")
                return False
                
        except Exception as e:
            logger.error(f"❌ STREAMING: Database storage error: {e}")
            return False
    
    async def _load_analyses_from_database(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Load full analysis data from database for report synthesis.
        
        Args:
            state: Current workflow state
            
        Returns:
            List of full analysis data from database
        """
        try:
            project_id = state.get("project_id")
            tenant_id = state.get("tenant_id")
            
            if not project_id or not tenant_id:
                logger.error("❌ STREAMING: Missing project_id or tenant_id for database loading")
                return []
            
            # Use the database adapter to load analysis results
            from ..adapters.database_adapter import AnalysisAgentDatabaseAdapter
            db_adapter = AnalysisAgentDatabaseAdapter(use_service_role=True)
            
            # Load all analysis results for this project
            analyses = await db_adapter.load_analysis_results(project_id, tenant_id)
            
            if analyses:
                logger.info(f"✅ STREAMING: Loaded {len(analyses)} full analyses from database")
                
                # 🔍 CRITICAL DEBUG: Check if loaded analyses have statistical_data
                for i, analysis in enumerate(analyses):
                    analyses_dict = analysis.get("analyses", {})
                    logger.info(f"🔍 LOAD DEBUG: Analysis {i+1} - analyses dict keys: {list(analyses_dict.keys())}")
                    for analysis_type, analysis_content in analyses_dict.items():
                        if isinstance(analysis_content, dict):
                            has_stat_data = "statistical_data" in analysis_content
                            stat_data_empty = not analysis_content.get("statistical_data") if has_stat_data else True
                            logger.info(f"🔍 LOAD DEBUG: {analysis_type} - has statistical_data: {has_stat_data}, is_empty: {stat_data_empty}")
                
                return analyses
            else:
                logger.warning("⚠️ STREAMING: No analyses found in database")
                return []
                
        except Exception as e:
            logger.error(f"❌ STREAMING: Database loading error: {e}")
            return []