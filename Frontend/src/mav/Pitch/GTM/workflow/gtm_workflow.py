"""
LangGraph Workflow for GTM Strategy Generator

Implements the complete GTM generation flow:
1. LoadProjectContext - Load project summary and available artifacts
2. GTMPlanner - Define 8-step structure + execution layer
3. StepLoop - For each step:
   - StepSpecBuilder - Define step expectations
   - RetrievalQueryBuilder - Create artifact-aware query
   - ProjectRetrieve - Get project evidence
   - EvidenceGrader - Grade sufficiency
   - WebResearchPlanner (optional) - Plan web queries
   - WebSearch (optional) - Execute web search
   - StepWriter - Generate step content
4. CrossStepConsistencyCheck - Verify cross-step consistency
5. Assembler - Compile final GTM pack
6. Persist - Save to database
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import StateGraph, END

from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.api.ai.models import LLMConfig, ModelProvider
from src.mint.api.ai.providers import OpenAIProvider
from src.mav.chat.services.web_search_service import WebSearchService, get_web_search_service

from ..models import (
    GTMState,
    DEFAULT_GTM_CONFIG,
    GTM_STEP_ARTIFACT_HINTS,
    GTM_STEPS_WEB_ALLOWED,
)
from ..adapters.database_adapter import GTMDatabaseAdapter, get_gtm_database_adapter
from ..services.gtm_rag_service import GTMRAGService, get_gtm_rag_service
from .prompts.gtm_prompts import (
    SYSTEM_PROMPT,
    GTM_PLANNER_PROMPT,
    STEP_SPEC_BUILDER_PROMPT,
    RETRIEVAL_QUERY_BUILDER_PROMPT,
    EVIDENCE_GRADER_PROMPT,
    WEB_RESEARCH_PLANNER_PROMPT,
    STEP_WRITER_PROMPT,
    CROSS_STEP_CONSISTENCY_PROMPT,
    ASSEMBLER_PROMPT,
)

logger = logging.getLogger(__name__)


class GTMWorkflow:
    """
    LangGraph workflow for generating GTM Strategy Packs.
    
    Uses Azure OpenAI for LLM calls and existing services for RAG and web search.
    """
    
    def __init__(self):
        """Initialize workflow with required services."""
        # Initialize services
        self.db_adapter = get_gtm_database_adapter()
        self.rag_service = get_gtm_rag_service()
        self.web_search_service = get_web_search_service()
        
        # Initialize LLM client
        self._init_llm_client()
        
        logger.info("✅ GTMWorkflow initialized")
    
    def _init_llm_client(self):
        """Initialize the LLM provider for GTM generation (centralized Responses API)."""
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        config = LLMConfig(
            provider_name=str(provider_type.value) if hasattr(provider_type, 'value') else str(provider_type),
            model_name=model_name,
            max_tokens=16000,
            azure_endpoint=client_config.get("azure_endpoint"),
            api_version=client_config.get("api_version"),
            api_key=client_config.get("api_key")
        )
        self.ai_provider = OpenAIProvider(config)
        self.model_name = model_name
    
    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = 0.3,
        max_tokens: int = 16000
    ) -> str:
        """Make an LLM call using centralized Responses API."""
        try:
            response = await self.ai_provider.generate_responses(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response, handling markdown fences."""
        try:
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return None
    
    # =========================================================================
    # NODE: Load Project Context
    # =========================================================================
    
    async def load_project_context(self, state: GTMState) -> GTMState:
        """Load project context and available artifacts."""
        logger.info(f"📋 GTM: Loading project context for {state['project_id']}")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        
        # Get project summary
        summary = await self.db_adapter.get_project_summary(project_id, tenant_id)
        
        state["project_name"] = summary.get("project_name") or "Unknown Project"
        state["project_description"] = summary.get("project_description") or ""
        state["project_summary"] = summary.get("summary_text") or ""
        state["available_artifacts"] = summary.get("available_artifacts") or []
        state["enhanced_context"] = summary.get("enhanced_context") or {}
        
        # Build artifact version map (to track v2 vs v1)
        artifact_version_map = {}
        for artifact in state["available_artifacts"]:
            if "_v2" in artifact:
                base = artifact.replace("_v2", "")
                artifact_version_map[base] = 2
            elif "_v1" in artifact:
                base = artifact.replace("_v1", "")
                if base not in artifact_version_map:
                    artifact_version_map[base] = 1
        state["artifact_version_map"] = artifact_version_map
        
        # Initialize tool trace
        state["tool_trace"] = {
            "retrieval_queries": [],
            "web_queries": [],
            "web_urls_fetched": [],
            "node_executions": [],
            "llm_calls": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        state["start_time"] = datetime.utcnow().isoformat()
        
        logger.info(f"📋 GTM: Found {len(state['available_artifacts'])} artifact types")
        
        return state
    
    # =========================================================================
    # NODE: GTM Planner
    # =========================================================================
    
    async def gtm_planner(self, state: GTMState) -> GTMState:
        """Define the 8-step GTM structure and execution layer configuration."""
        logger.info("📝 GTM: Planning GTM structure...")
        
        context_constraints = state.get("context_constraints") or {}
        
        prompt = GTM_PLANNER_PROMPT.format(
            project_summary=state.get("project_summary", ""),
            stage_hint=context_constraints.get("product_stage", ""),
            category_hint=state.get("enhanced_context", {}).get("category", ""),
            context_constraints=json.dumps(context_constraints)
        )
        
        response = await self._call_llm(prompt)
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        # Get the 8 steps
        state["gtm_steps_plan"] = result.get("gtm_steps", [])
        state["execution_layer_plan"] = result.get("execution_layer", {
            "include_30_60_90": True,
            "include_experiment_backlog": True,
            "include_metrics_dashboard_spec": True
        })
        
        # Initialize step processing
        state["current_step_index"] = 0
        state["steps_draft"] = []
        state["all_project_citations"] = []
        state["all_web_citations"] = []
        
        logger.info(f"📝 GTM: Planned {len(state['gtm_steps_plan'])} steps")
        
        return state
    
    # =========================================================================
    # NODE: Step Spec Builder
    # =========================================================================
    
    async def step_spec_builder(self, state: GTMState) -> GTMState:
        """Define expectations for the current GTM step."""
        idx = state["current_step_index"]
        step_plan = state["gtm_steps_plan"][idx]
        
        logger.info(f"🎯 GTM: Building spec for step {idx + 1}: {step_plan.get('name')}")
        
        prompt = STEP_SPEC_BUILDER_PROMPT.format(
            step_number=step_plan.get("step", idx + 1),
            step_name=step_plan.get("name", f"Step {idx + 1}"),
            deliverables=json.dumps(step_plan.get("deliverables", [])),
            project_summary=state.get("project_summary", "")
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        state["current_step_spec"] = {
            "step": step_plan.get("step", idx + 1),
            "name": step_plan.get("name", f"Step {idx + 1}"),
            "deliverables": step_plan.get("deliverables", []),
            "web_allowed": step_plan.get("web_allowed", False),
            "objective": result.get("step_objective", ""),
            "must_include": result.get("must_include_checks", []),
            "avoid": result.get("avoid", []),
            "evidence_priority": result.get("evidence_priority", [])
        }
        
        return state
    
    # =========================================================================
    # NODE: Retrieval Query Builder
    # =========================================================================
    
    async def retrieval_query_builder(self, state: GTMState) -> GTMState:
        """Build retrieval query for current step."""
        step_spec = state["current_step_spec"]
        step_name = step_spec.get("name", "")
        
        logger.info(f"🔎 GTM: Building query for step: {step_name}")
        
        # Get artifact hints for this step type
        step_type_key = step_name.lower().replace(" ", "_").replace("define_the_", "").replace("gather_", "").replace("&", "and")
        
        # Map step names to artifact hint keys
        step_type_mapping = {
            "define_the_problem": "problem",
            "define_the_audience": "audience_icp",
            "gather_market_insights": "market_insights",
            "value_proposition": "value_proposition",
            "messaging/manifesto": "messaging",
            "channel_mastery": "channels",
            "customer_success_methodology": "customer_success",
            "goals_and_metrics": "goals_metrics",
        }
        
        mapped_type = step_type_mapping.get(step_type_key, step_type_key)
        default_hints = GTM_STEP_ARTIFACT_HINTS.get(mapped_type, [])
        
        prompt = RETRIEVAL_QUERY_BUILDER_PROMPT.format(
            step_name=step_name,
            step_objective=step_spec.get("objective", ""),
            project_summary=state.get("project_summary", ""),
            evidence_priority=json.dumps(step_spec.get("evidence_priority", default_hints))
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        state["current_retrieval_query"] = result.get(
            "retrieval_query",
            f"Information for {step_name} GTM step"
        )
        state["current_artifact_hints"] = result.get("artifact_hints", default_hints)
        
        # Track in tool trace
        state["tool_trace"]["retrieval_queries"].append({
            "step_name": step_name,
            "query": state["current_retrieval_query"],
            "artifact_hints": state["current_artifact_hints"]
        })
        
        return state
    
    # =========================================================================
    # NODE: Project Retrieve
    # =========================================================================
    
    async def project_retrieve(self, state: GTMState) -> GTMState:
        """Retrieve project evidence for current step."""
        step_name = state["current_step_spec"].get("name", "")
        step_type_key = step_name.lower().replace(" ", "_").replace("define_the_", "").replace("gather_", "")
        
        logger.info(f"📚 GTM: Retrieving evidence for {step_name}")
        
        # Map to artifact hint key
        step_type_mapping = {
            "define_the_problem": "problem",
            "define_the_audience": "audience_icp",
            "gather_market_insights": "market_insights",
            "value_proposition": "value_proposition",
            "messaging/manifesto": "messaging",
            "channel_mastery": "channels",
            "customer_success_methodology": "customer_success",
            "goals_and_metrics": "goals_metrics",
        }
        mapped_type = step_type_mapping.get(step_type_key, step_type_key)
        
        evidence = await self.rag_service.retrieve_for_step(
            query=state["current_retrieval_query"],
            project_id=state["project_id"],
            tenant_id=state["tenant_id"],
            step_type=mapped_type,
            artifact_hints=state.get("current_artifact_hints"),
            top_k=DEFAULT_GTM_CONFIG.rag_top_k
        )
        
        state["current_project_evidence"] = [
            {
                "chunk_id": ev.chunk_id,
                "content": ev.content,
                "artifact_type": ev.artifact_type,
                "score": ev.score,
                "metadata": ev.metadata
            }
            for ev in evidence
        ]
        
        logger.info(f"📚 GTM: Retrieved {len(evidence)} evidence chunks")
        
        return state
    
    # =========================================================================
    # NODE: Evidence Grader
    # =========================================================================
    
    async def evidence_grader(self, state: GTMState) -> GTMState:
        """Grade evidence sufficiency for current step."""
        step_spec = state["current_step_spec"]
        step_name = step_spec.get("name", "")
        
        logger.info(f"⚖️ GTM: Grading evidence for {step_name}")
        
        # Format evidence for prompt
        evidence_text = "No project evidence retrieved."
        if state.get("current_project_evidence"):
            lines = []
            for i, ev in enumerate(state["current_project_evidence"], 1):
                version_tag = ""
                if "_v2" in ev["artifact_type"]:
                    version_tag = " [v2-LATEST]"
                elif "_v1" in ev["artifact_type"]:
                    version_tag = " [v1]"
                lines.append(f"[P{i}] ({ev['artifact_type']}{version_tag}): {ev['content'][:600]}")
            evidence_text = "\n\n".join(lines)
        
        prompt = EVIDENCE_GRADER_PROMPT.format(
            step_name=step_name,
            deliverables=json.dumps(step_spec.get("deliverables", [])),
            web_allowed=step_spec.get("web_allowed", False),
            project_evidence_block=evidence_text
        )
        
        response = await self._call_llm(prompt, temperature=0.1)
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        grade = result.get("grade", "PARTIAL")
        missing_items = result.get("missing_items", [])
        next_step = result.get("recommended_action", "WRITE_FROM_PROJECT")
        web_allowed = step_spec.get("web_allowed", False)
        
        # Force web research for specific steps if allowed and evidence insufficient
        step_name_lower = step_name.lower()
        if web_allowed and grade != "SUFFICIENT" and missing_items:
            if any(kw in step_name_lower for kw in ["market", "channel", "insight"]):
                next_step = "DO_WEB_RESEARCH"
                logger.info(f"⚖️ GTM: Forcing web research for {step_name} (grade={grade}, web_allowed=True)")
        
        state["current_evidence_grade"] = grade
        state["current_missing_items"] = missing_items
        state["current_next_step"] = next_step
        
        logger.info(f"⚖️ GTM: Grade={grade}, next={next_step}, web_allowed={web_allowed}")
        
        return state
    
    # =========================================================================
    # NODE: Web Research Planner
    # =========================================================================
    
    async def web_research_planner(self, state: GTMState) -> GTMState:
        """Plan web research queries for missing items."""
        step_name = state["current_step_spec"].get("name", "")
        logger.info(f"🌐 GTM: Planning web research for {step_name}")
        
        # Get geography/industry hints
        context_constraints = state.get("context_constraints") or {}
        enhanced_context = state.get("enhanced_context") or {}
        geo_industry = {
            "geography": context_constraints.get("geography_focus") or enhanced_context.get("target_market", ""),
            "industry": enhanced_context.get("industry", "")
        }
        
        prompt = WEB_RESEARCH_PLANNER_PROMPT.format(
            step_name=step_name,
            missing_items=json.dumps(state["current_missing_items"]),
            project_summary=state.get("project_summary", ""),
            geography_industry=json.dumps(geo_industry),
            current_date=datetime.utcnow().strftime("%B %Y")
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        state["web_queries"] = result.get("queries", [])[:DEFAULT_GTM_CONFIG.max_web_queries_per_step]
        state["extraction_targets"] = result.get("extraction_targets", [])
        
        # Fallback queries if none returned
        if not state["web_queries"]:
            industry = enhanced_context.get("industry", "")
            geography = context_constraints.get("geography_focus", "")
            
            if "market" in step_name.lower():
                state["web_queries"] = [
                    f"{industry} market size 2024",
                    f"{industry} market trends {geography}" if geography else f"{industry} market trends"
                ]
            elif "channel" in step_name.lower():
                state["web_queries"] = [
                    f"{industry} marketing channels best practices",
                    f"{industry} customer acquisition channels {geography}" if geography else f"{industry} go to market channels"
                ]
            state["extraction_targets"] = state["current_missing_items"]
            logger.info(f"🌐 GTM: Using fallback queries for {step_name}")
        
        logger.info(f"🌐 GTM: Planned {len(state['web_queries'])} web queries")
        
        return state
    
    # =========================================================================
    # NODE: Web Search
    # =========================================================================
    
    async def web_search(self, state: GTMState) -> GTMState:
        """Execute web search and extract evidence."""
        step_name = state["current_step_spec"].get("name", "")
        queries = state.get("web_queries", [])
        
        if not queries:
            state["current_web_evidence"] = []
            return state
        
        logger.info(f"🔍 GTM: Executing {len(queries)} web searches for {step_name}")
        
        # Track queries in tool trace
        state["tool_trace"]["web_queries"].extend(queries)
        
        try:
            # Use existing web search service
            web_evidence = await self.web_search_service.search_and_extract(
                queries=queries,
                what_to_extract=state.get("extraction_targets", []),
                user_question=f"GTM research for {step_name}",
                max_queries=DEFAULT_GTM_CONFIG.max_web_queries_per_step
            )
            
            state["current_web_evidence"] = [
                {
                    "claim": ev.claim,
                    "snippet": ev.snippet,
                    "url": ev.url,
                    "title": ev.title,
                    "domain": ev.domain,
                    "fetched_at": ev.fetched_at
                }
                for ev in web_evidence
            ]
            
            # Track URLs fetched
            state["tool_trace"]["web_urls_fetched"].extend([ev.url for ev in web_evidence])
            
            logger.info(f"🔍 GTM: Found {len(state['current_web_evidence'])} web evidence items")
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            state["current_web_evidence"] = []
        
        return state
    
    # =========================================================================
    # NODE: Step Writer
    # =========================================================================
    
    async def step_writer(self, state: GTMState) -> GTMState:
        """Generate GTM step content."""
        step_spec = state["current_step_spec"]
        step_name = step_spec.get("name", "")
        step_number = step_spec.get("step", state["current_step_index"] + 1)
        
        logger.info(f"✍️ GTM: Writing step {step_number}: {step_name}")
        
        # Format project evidence
        project_evidence_text = "No project evidence available."
        if state.get("current_project_evidence"):
            lines = []
            for i, ev in enumerate(state["current_project_evidence"], 1):
                version_tag = ""
                if "_v2" in ev["artifact_type"]:
                    version_tag = " [v2-LATEST]"
                elif "_v1" in ev["artifact_type"]:
                    version_tag = " [v1]"
                lines.append(f"[P{i}] ({ev['artifact_type']}{version_tag}): {ev['content'][:700]}")
            project_evidence_text = "\n\n".join(lines)
        
        # Format web evidence
        web_evidence_text = "No web evidence available."
        if state.get("current_web_evidence"):
            lines = []
            for i, ev in enumerate(state["current_web_evidence"], 1):
                lines.append(f"[W{i}] ({ev['domain']}): {ev['claim']} - \"{ev['snippet'][:250]}\"")
            web_evidence_text = "\n\n".join(lines)
        
        prompt = STEP_WRITER_PROMPT.format(
            step_name=step_name,
            step_number=step_number,
            deliverables=json.dumps(step_spec.get("deliverables", [])),
            step_objective=step_spec.get("objective", ""),
            project_summary=state.get("project_summary", ""),
            grade=state["current_evidence_grade"],
            context_constraints=json.dumps(state.get("context_constraints") or {}),
            project_evidence_block=project_evidence_text,
            web_evidence_block=web_evidence_text
        )
        
        response = await self._call_llm(prompt, temperature=0.4, max_tokens=16000)  # gpt-5-mini needs large token budget
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        # Build step content
        step_content = {
            "step": result.get("step", step_number),
            "name": result.get("name", step_name),
            "content": result.get("content", {"decisions": [], "plan": [], "experiments": []}),
            "description": result.get("description", ""),
            "sources_used": result.get("sources_used", []),
            "assumptions_applied": result.get("assumptions_applied", [])
        }
        
        state["steps_draft"].append(step_content)
        
        # Collect project citations
        for cite_id in result.get("sources_used", []):
            if cite_id.startswith("P"):
                try:
                    idx = int(cite_id[1:]) - 1
                    if 0 <= idx < len(state.get("current_project_evidence", [])):
                        ev = state["current_project_evidence"][idx]
                        # Determine version
                        version = None
                        if "_v2" in ev["artifact_type"]:
                            version = 2
                        elif "_v1" in ev["artifact_type"]:
                            version = 1
                        
                        state["all_project_citations"].append({
                            "id": cite_id,
                            "type": "project",
                            "artifact_ref": ev["artifact_type"],
                            "artifact_version": version,
                            "chunk_ref": ev["chunk_id"],
                            "snippet": ev["content"][:200]
                        })
                except (ValueError, IndexError):
                    pass
        
        # Collect web citations
        for cite_id in result.get("sources_used", []):
            if cite_id.startswith("W"):
                try:
                    idx = int(cite_id[1:]) - 1
                    if 0 <= idx < len(state.get("current_web_evidence", [])):
                        ev = state["current_web_evidence"][idx]
                        state["all_web_citations"].append({
                            "id": cite_id,
                            "type": "web",
                            "url": ev["url"],
                            "domain": ev["domain"],
                            "title": ev["title"],
                            "snippet": ev["snippet"][:200],
                            "fetched_at": ev["fetched_at"]
                        })
                except (ValueError, IndexError):
                    pass
        
        logger.info(f"✍️ GTM: Completed step {step_number}: {step_name}")
        
        return state
    
    # =========================================================================
    # NODE: Next Step Router
    # =========================================================================
    
    def should_continue_steps(self, state: GTMState) -> Literal["continue", "done"]:
        """Determine if there are more steps to process."""
        current_idx = state["current_step_index"]
        total_steps = len(state["gtm_steps_plan"])
        
        if current_idx < total_steps - 1:
            return "continue"
        return "done"
    
    async def increment_step_index(self, state: GTMState) -> GTMState:
        """Move to next step."""
        state["current_step_index"] += 1
        logger.info(f"➡️ GTM: Moving to step {state['current_step_index'] + 1}")
        return state
    
    # =========================================================================
    # NODE: Cross-Step Consistency Check
    # =========================================================================
    
    async def consistency_check(self, state: GTMState) -> GTMState:
        """Check cross-step consistency."""
        logger.info("🔍 GTM: Running consistency check...")
        
        prompt = CROSS_STEP_CONSISTENCY_PROMPT.format(
            gtm_steps_draft=json.dumps(state["steps_draft"]),
            project_summary=state.get("project_summary", "")
        )
        
        response = await self._call_llm(prompt, temperature=0.1)
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        state["consistency_issues"] = result.get("issues", [])
        state["auto_fixes"] = result.get("auto_fixes", [])
        
        logger.info(f"🔍 GTM: Found {len(state['consistency_issues'])} issues, {len(state['auto_fixes'])} auto-fixes")
        
        # Apply auto-fixes
        fixes_applied = 0
        for fix in state["auto_fixes"]:
            original = fix.get("original", "")
            replacement = fix.get("replacement", "")
            target_step = fix.get("where")
            target_field = fix.get("field", "description")
            
            if not original or not replacement:
                continue
            
            for step in state["steps_draft"]:
                if target_step and step["name"] != target_step:
                    continue
                
                if target_field == "description" and original in step.get("description", ""):
                    step["description"] = step["description"].replace(original, replacement)
                    fixes_applied += 1
                elif target_field == "content":
                    content = step.get("content", {})
                    for key in ["decisions", "plan"]:
                        if key in content and isinstance(content[key], list):
                            new_list = []
                            for item in content[key]:
                                if isinstance(item, str) and original in item:
                                    new_list.append(item.replace(original, replacement))
                                    fixes_applied += 1
                                else:
                                    new_list.append(item)
                            content[key] = new_list
        
        logger.info(f"🔍 GTM: Applied {fixes_applied} auto-fixes")
        
        return state
    
    # =========================================================================
    # NODE: Assembler
    # =========================================================================
    
    async def assembler(self, state: GTMState) -> GTMState:
        """Assemble the final GTM Strategy Pack."""
        logger.info("📦 GTM: Assembling final GTM pack...")
        
        prompt = ASSEMBLER_PROMPT.format(
            steps_final=json.dumps(state["steps_draft"]),
            raw_citations_project=json.dumps(state["all_project_citations"]),
            raw_citations_web=json.dumps(state["all_web_citations"]),
            project_summary=state.get("project_summary", ""),
            context_constraints=json.dumps(state.get("context_constraints") or {})
        )
        
        response = await self._call_llm(prompt, temperature=0.3, max_tokens=16000)  # gpt-5-mini needs large token budget
        state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
        
        result = self._parse_json_response(response) or {}
        
        # Build the GTM pack
        gtm_pack = {
            "version": state.get("gtm_version", 1),
            "summary": result.get("summary", "GTM Strategy Pack generated."),
            "steps": state["steps_draft"],
            "channel_plan": result.get("channel_plan", {}),
            "customer_success_motion": result.get("customer_success_motion", {}),
            "metrics_plan": result.get("metrics_dashboard_spec", {}),
            "execution_plan_30_60_90": result.get("execution_plan_30_60_90", {}),
            "experiment_backlog": result.get("experiment_backlog", {}),
            "sources": result.get("sources", state["all_project_citations"] + state["all_web_citations"]),
            "run_trace": state["tool_trace"],
            "consistency_check_results": {
                "issues": state.get("consistency_issues", []),
                "auto_fixes_applied": len(state.get("auto_fixes", []))
            },
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        }
        
        state["gtm_pack"] = gtm_pack
        state["generation_status"] = "completed"
        
        logger.info(f"📦 GTM: Assembled pack with {len(state['steps_draft'])} steps, {len(gtm_pack['sources'])} sources")
        
        return state
    
    # =========================================================================
    # NODE: Persist
    # =========================================================================
    
    async def persist(self, state: GTMState) -> GTMState:
        """Save the GTM pack to database."""
        logger.info("💾 GTM: Persisting to database...")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        user_id = state.get("user_id", "")
        
        try:
            # Calculate total latency
            if state.get("start_time"):
                start = datetime.fromisoformat(state["start_time"])
                latency_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
                state["gtm_pack"]["run_trace"]["latency_ms"] = latency_ms
            
            # Save the GTM pack
            success = await self.db_adapter.save_gtm_version(
                project_id=project_id,
                tenant_id=tenant_id,
                user_id=user_id,
                gtm_pack=state["gtm_pack"]
            )
            
            if success:
                logger.info(f"✅ GTM: Saved version {state['gtm_pack']['version']} for project {project_id}")
            else:
                logger.error(f"❌ GTM: Failed to save GTM pack")
                state["generation_status"] = "failed"
                state["error_message"] = "Database save failed"
            
        except Exception as e:
            logger.error(f"❌ GTM: Persist error: {e}")
            state["generation_status"] = "failed"
            state["error_message"] = str(e)
        
        return state
    
    # =========================================================================
    # ROUTING FUNCTIONS
    # =========================================================================
    
    def route_after_grade(self, state: GTMState) -> Literal["write", "web"]:
        """Route based on evidence grade and step configuration."""
        next_step = state.get("current_next_step", "WRITE_FROM_PROJECT")
        
        if next_step == "DO_WEB_RESEARCH":
            return "web"
        return "write"
    
    # =========================================================================
    # BUILD GRAPH
    # =========================================================================
    
    def build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(GTMState)
        
        # Add nodes
        workflow.add_node("load_context", self.load_project_context)
        workflow.add_node("gtm_planner", self.gtm_planner)
        workflow.add_node("step_spec_builder", self.step_spec_builder)
        workflow.add_node("retrieval_query_builder", self.retrieval_query_builder)
        workflow.add_node("project_retrieve", self.project_retrieve)
        workflow.add_node("evidence_grader", self.evidence_grader)
        workflow.add_node("web_research_planner", self.web_research_planner)
        workflow.add_node("web_search", self.web_search)
        workflow.add_node("step_writer", self.step_writer)
        workflow.add_node("increment_step", self.increment_step_index)
        workflow.add_node("consistency_check", self.consistency_check)
        workflow.add_node("assembler", self.assembler)
        workflow.add_node("persist", self.persist)
        
        # Set entry point
        workflow.set_entry_point("load_context")
        
        # Add edges
        workflow.add_edge("load_context", "gtm_planner")
        workflow.add_edge("gtm_planner", "step_spec_builder")
        workflow.add_edge("step_spec_builder", "retrieval_query_builder")
        workflow.add_edge("retrieval_query_builder", "project_retrieve")
        workflow.add_edge("project_retrieve", "evidence_grader")
        
        # Conditional routing after evidence grading
        workflow.add_conditional_edges(
            "evidence_grader",
            self.route_after_grade,
            {
                "write": "step_writer",
                "web": "web_research_planner",
            }
        )
        
        # Web research path
        workflow.add_edge("web_research_planner", "web_search")
        workflow.add_edge("web_search", "step_writer")
        
        # After step writer, check if more steps
        workflow.add_conditional_edges(
            "step_writer",
            self.should_continue_steps,
            {
                "continue": "increment_step",
                "done": "consistency_check",
            }
        )
        
        # Loop back to step spec builder
        workflow.add_edge("increment_step", "step_spec_builder")
        
        # Final assembly
        workflow.add_edge("consistency_check", "assembler")
        workflow.add_edge("assembler", "persist")
        workflow.add_edge("persist", END)
        
        return workflow.compile()
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    async def run(
        self,
        project_id: str,
        tenant_id: str,
        user_id: str,
        context_constraints: Optional[Dict[str, Any]] = None
    ) -> GTMState:
        """
        Run the GTM generation workflow.
        
        Args:
            project_id: VMP project ID
            tenant_id: Tenant ID
            user_id: User ID
            context_constraints: Optional constraints (geography, timeline, budget)
            
        Returns:
            Final GTMState with GTM pack
        """
        logger.info(f"🚀 Starting GTM workflow - project={project_id}")
        
        # Get next version
        next_version = await self.db_adapter.get_next_version(project_id, tenant_id)
        
        # Initialize state
        initial_state: GTMState = {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "context_constraints": context_constraints or {},
            "gtm_version": next_version,
        }
        
        # Build and run the graph
        graph = self.build_graph()
        final_state = await graph.ainvoke(
            initial_state,
            config={"recursion_limit": 200}
        )
        
        total_time = 0
        if final_state.get("start_time"):
            start = datetime.fromisoformat(final_state["start_time"])
            total_time = (datetime.utcnow() - start).total_seconds()
        
        logger.info(f"✅ GTM workflow complete - {total_time:.2f}s total")
        
        return final_state


# ============================================================================
# PUBLIC FUNCTION
# ============================================================================

async def run_gtm_generation(
    project_id: str,
    tenant_id: str,
    user_id: str,
    context_constraints: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run GTM generation and return results.
    
    Args:
        project_id: VMP project ID
        tenant_id: Tenant ID
        user_id: User ID
        context_constraints: Optional constraints
        
    Returns:
        Dict with generation_status, gtm_pack, error_message
    """
    workflow = GTMWorkflow()
    
    try:
        final_state = await workflow.run(
            project_id=project_id,
            tenant_id=tenant_id,
            user_id=user_id,
            context_constraints=context_constraints
        )
        
        return {
            "generation_status": final_state.get("generation_status", "completed"),
            "gtm_pack": final_state.get("gtm_pack"),
            "gtm_version": final_state.get("gtm_version", 1),
            "error_message": final_state.get("error_message")
        }
        
    except Exception as e:
        logger.error(f"❌ GTM generation failed: {e}")
        return {
            "generation_status": "failed",
            "gtm_pack": None,
            "error_message": str(e)
        }
