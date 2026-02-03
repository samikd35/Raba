"""
LangGraph Workflow for Pitch Deck Generator

Implements the complete deck generation flow:
1. LoadProjectContext - Load project summary and available artifacts
2. DeckIntentRouter - Classify purpose/stage/category
3. DeckPlanner - Generate ordered slide plan
4. SlideLoop - For each slide:
   - SlideQueryBuilder - Create retrieval query
   - ProjectRetrieve - Get project evidence
   - EvidenceGrader - Grade sufficiency
   - WebResearchPlanner (optional) - Plan web queries
   - WebSearch (optional) - Execute web search
   - SlideWriter - Generate slide content
5. ConsistencyCheck - Verify cross-slide consistency
6. DeckAssembler - Compile final deck with citations
7. PersistDeckRun - Save to database
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import StateGraph, END

from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.providers import OpenAIProvider
from src.mav.chat.services.web_search_service import WebSearchService
from src.vpm.services.project_chunking_service import VMPProjectChunkingService, VMPFeatureType

from ..models import PitchDeckState, DEFAULT_PITCH_CONFIG, SLIDE_ARTIFACT_HINTS
from ..adapters.database_adapter import PitchDeckDatabaseAdapter
from ..services.pitch_rag_service import PitchDeckRAGService
from .prompts.pitch_prompts import (
    SYSTEM_PROMPT,
    DECK_INTENT_ROUTER_PROMPT,
    DECK_PLANNER_PROMPT,
    SLIDE_QUERY_BUILDER_PROMPT,
    EVIDENCE_GRADER_PROMPT,
    WEB_RESEARCH_PLANNER_PROMPT,
    WEB_EVIDENCE_EXTRACTOR_PROMPT,
    SLIDE_WRITER_PROMPT,
    CONSISTENCY_CHECK_PROMPT,
)

logger = logging.getLogger(__name__)


class PitchDeckWorkflow:
    """
    LangGraph workflow for generating pitch decks.
    
    Uses Azure OpenAI for LLM calls and existing services for RAG and web search.
    """
    
    def __init__(self):
        """Initialize workflow with required services."""
        # Initialize services
        self.db_adapter = PitchDeckDatabaseAdapter()
        self.rag_service = PitchDeckRAGService()
        self.web_search_service = WebSearchService()
        
        # Initialize LLM client
        self._init_llm_client()
        
        logger.info("✅ PitchDeckWorkflow initialized")
    
    def _init_llm_client(self):
        """Initialize the LLM provider for deck generation (centralized Responses API)."""
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
        temperature: float = 0.3
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
        """Parse JSON from LLM response, handling markdown fences. Returns None on failure."""
        try:
            # Remove markdown code fences if present
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
    
    async def load_project_context(self, state: PitchDeckState) -> PitchDeckState:
        """Load project context and available artifacts."""
        logger.info(f"📋 PITCH: Loading project context for {state['project_id']}")
        
        project_id = state["project_id"]
        tenant_id = state["tenant_id"]
        
        # Get project summary
        summary = await self.db_adapter.get_project_summary(project_id, tenant_id)
        
        state["project_name"] = summary.get("project_name") or "Unknown Project"
        state["project_description"] = summary.get("project_description") or ""
        state["project_summary"] = summary.get("summary_text") or ""
        state["available_artifacts"] = summary.get("available_artifacts") or []
        state["detected_category"] = summary.get("detected_category") or "OTHER"
        # Use 'or {}' pattern to handle None values (not just missing keys)
        state["enhanced_context"] = summary.get("enhanced_context") or {}
        
        logger.info(f"📋 PITCH: Auto-detected category: {state['detected_category']}")
        
        # Initialize tool trace
        state["tool_trace"] = {
            "retrieval_queries": [],
            "web_queries": [],
            "node_executions": [],
            "start_time": datetime.utcnow().isoformat()
        }
        state["start_time"] = datetime.utcnow().isoformat()
        
        logger.info(f"📋 PITCH: Found {len(state['available_artifacts'])} artifact types")
        
        return state
    
    # =========================================================================
    # NODE: Deck Intent Router
    # =========================================================================
    
    async def deck_intent_router(self, state: PitchDeckState) -> PitchDeckState:
        """Classify deck purpose, stage, and category."""
        logger.info("🎯 PITCH: Routing deck intent...")
        
        user_hints = state.get("user_hints") or {}
        
        # Category is auto-detected from project context (not from user input)
        # User can override with user_hints["category"] but it's optional
        detected_category = state.get("detected_category", "OTHER")
        
        # If purpose and stage provided by user, use auto-detected category
        if user_hints.get("deck_purpose") and user_hints.get("stage"):
            state["deck_purpose"] = user_hints["deck_purpose"]
            state["stage"] = user_hints["stage"]
            # Use user-provided category if given, otherwise use auto-detected
            state["category"] = user_hints.get("category") or detected_category
            state["reasoning_brief"] = f"User provided purpose/stage. Category auto-detected from project data: {detected_category}"
            state["missing_inputs"] = []
            logger.info(f"🎯 PITCH: Using context: {state['deck_purpose']}/{state['stage']}/{state['category']} (category from project)")
            return state
        
        # Build prompt for missing intent values
        prompt = DECK_INTENT_ROUTER_PROMPT.format(
            user_hints=json.dumps(user_hints),
            project_summary=state.get("project_summary", "No summary available")
        )
        
        response = await self._call_llm(prompt)
        result = self._parse_json_response(response) or {}
        
        state["deck_purpose"] = user_hints.get("deck_purpose") or result.get("deck_purpose", "FUNDRAISING")
        state["stage"] = user_hints.get("stage") or result.get("stage", "PRE_SEED")
        # Always prefer detected_category from project data over LLM inference
        state["category"] = user_hints.get("category") or detected_category
        state["reasoning_brief"] = f"{result.get('reasoning_brief', '')} Category detected from project data."
        state["missing_inputs"] = result.get("missing_inputs", [])
        
        logger.info(f"🎯 PITCH: Classified as {state['deck_purpose']}/{state['stage']}/{state['category']}")
        
        return state
    
    # =========================================================================
    # NODE: Deck Planner
    # =========================================================================
    
    async def deck_planner(self, state: PitchDeckState) -> PitchDeckState:
        """Generate ordered slide plan."""
        logger.info("📝 PITCH: Planning deck structure...")
        
        user_hints = state.get("user_hints") or {}
        
        # Determine what's missing
        known_missing = []
        if not user_hints.get("team_info"):
            known_missing.append("team_info")
        if not user_hints.get("financial_inputs"):
            known_missing.append("financial_inputs")
        if not user_hints.get("traction_metrics"):
            known_missing.append("traction_metrics")
        
        prompt = DECK_PLANNER_PROMPT.format(
            deck_purpose=state["deck_purpose"],
            stage=state["stage"],
            category=state["category"],
            available_artifacts=json.dumps(state.get("available_artifacts", [])),
            known_missing=json.dumps(known_missing),
            user_hints=json.dumps(user_hints)
        )
        
        response = await self._call_llm(prompt)
        result = self._parse_json_response(response) or {}
        
        slides_plan = result.get("slides_plan", [])
        
        # Force web_allowed=true for Market and Competition slides
        # This ensures these slides get web research for credible market data
        for slide in slides_plan:
            if slide.get("slide_type") in {"Market", "Competition"}:
                slide["web_allowed"] = True
                logger.info(f"📝 PITCH: Forcing web_allowed=True for {slide['slide_type']} slide")
        
        state["slides_plan"] = slides_plan
        state["deck_warnings"] = result.get("deck_warnings", [])
        state["current_slide_index"] = 0
        state["slides_draft"] = []
        state["all_project_citations"] = []
        state["all_web_citations"] = []
        
        logger.info(f"📝 PITCH: Planned {len(state['slides_plan'])} slides")
        
        return state
    
    # =========================================================================
    # NODE: Slide Query Builder
    # =========================================================================
    
    async def slide_query_builder(self, state: PitchDeckState) -> PitchDeckState:
        """Build retrieval query for current slide."""
        idx = state["current_slide_index"]
        slide_spec = state["slides_plan"][idx]
        
        logger.info(f"🔎 PITCH: Building query for slide {idx + 1}: {slide_spec['slide_type']}")
        
        deck_context = {
            "deck_purpose": state["deck_purpose"],
            "stage": state["stage"],
            "category": state["category"]
        }
        
        prompt = SLIDE_QUERY_BUILDER_PROMPT.format(
            slide_spec=json.dumps(slide_spec),
            project_summary=state.get("project_summary", ""),
            deck_context=json.dumps(deck_context)
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        result = self._parse_json_response(response) or {}
        
        state["current_slide_spec"] = slide_spec
        state["current_retrieval_query"] = result.get("retrieval_query", f"Information for {slide_spec['slide_type']} slide")
        state["current_artifact_hints"] = result.get("artifact_hints", SLIDE_ARTIFACT_HINTS.get(slide_spec["slide_type"], []))
        
        # Track in tool trace
        state["tool_trace"]["retrieval_queries"].append({
            "slide_type": slide_spec["slide_type"],
            "query": state["current_retrieval_query"],
            "artifact_hints": state["current_artifact_hints"]
        })
        
        return state
    
    # =========================================================================
    # NODE: Project Retrieve
    # =========================================================================
    
    async def project_retrieve(self, state: PitchDeckState) -> PitchDeckState:
        """Retrieve project evidence for current slide."""
        slide_type = state["current_slide_spec"]["slide_type"]
        logger.info(f"📚 PITCH: Retrieving evidence for {slide_type}")
        
        # Skip retrieval for slides that only use user input
        if slide_type in ["Team", "Financials", "Ask"]:
            state["current_project_evidence"] = []
            logger.info(f"📚 PITCH: Skipping RAG for {slide_type} (user input only)")
            return state
        
        evidence = await self.rag_service.retrieve_for_slide(
            query=state["current_retrieval_query"],
            project_id=state["project_id"],
            tenant_id=state["tenant_id"],
            slide_type=slide_type,
            artifact_hints=state.get("current_artifact_hints", []),
            top_k=DEFAULT_PITCH_CONFIG.rag_top_k
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
        
        logger.info(f"📚 PITCH: Retrieved {len(evidence)} evidence chunks")
        
        return state
    
    # =========================================================================
    # NODE: Evidence Grader
    # =========================================================================
    
    async def evidence_grader(self, state: PitchDeckState) -> PitchDeckState:
        """Grade evidence sufficiency for current slide."""
        slide_spec = state["current_slide_spec"]
        slide_type = slide_spec["slide_type"]
        
        logger.info(f"⚖️ PITCH: Grading evidence for {slide_type}")
        
        # Special handling for user-input-only slides
        if slide_type in ["Team", "Financials", "Ask"]:
            user_hints = state.get("user_hints") or {}
            has_data = (
                (slide_type == "Team" and user_hints.get("team_info")) or
                (slide_type == "Financials" and user_hints.get("financial_inputs")) or
                (slide_type == "Ask" and user_hints.get("financial_inputs", {}).get("funding_ask"))
            )
            state["current_evidence_grade"] = "SUFFICIENT" if has_data else "INSUFFICIENT"
            state["current_missing_items"] = [] if has_data else [f"{slide_type.lower()}_info"]
            state["current_next_step"] = "WRITE_FROM_PROJECT" if has_data else "PLACEHOLDER_ONLY"
            return state
        
        # Format evidence for prompt
        evidence_text = self.rag_service.format_evidence_for_prompt(
            [type('obj', (object,), ev)() for ev in state["current_project_evidence"]]
            if state["current_project_evidence"] else []
        ) if state["current_project_evidence"] else "No project evidence retrieved."
        
        # Quick fix - format evidence properly
        if state["current_project_evidence"]:
            evidence_lines = []
            for i, ev in enumerate(state["current_project_evidence"], 1):
                evidence_lines.append(f"[P{i}] ({ev['artifact_type']}): {ev['content'][:500]}")
            evidence_text = "\n\n".join(evidence_lines)
        
        prompt = EVIDENCE_GRADER_PROMPT.format(
            slide_type=slide_type,
            data_requirements=json.dumps(slide_spec.get("data_requirements", [])),
            user_hints=json.dumps(state.get("user_hints") or {}),
            web_allowed=slide_spec.get("web_allowed", False),
            project_evidence=evidence_text
        )
        
        response = await self._call_llm(prompt, temperature=0.1)
        result = self._parse_json_response(response) or {}
        
        grade = result.get("grade", "PARTIAL")
        missing_items = result.get("missing_items", [])
        next_step = result.get("next_step", "WRITE_FROM_PROJECT")
        web_allowed = slide_spec.get("web_allowed", False)
        
        # Force web research for Market/Competition slides if web is allowed and evidence is not sufficient
        # This overrides whatever the LLM returned - Market/Competition NEED web research for credible data
        web_required_slides = {"Market", "Competition"}
        if slide_type in web_required_slides and web_allowed and grade != "SUFFICIENT":
            # Force DO_WEB_RESEARCH regardless of what LLM returned (WRITE_FROM_PROJECT or PLACEHOLDER_ONLY)
            next_step = "DO_WEB_RESEARCH"
            logger.info(f"⚖️ PITCH: Forcing web research for {slide_type} slide (grade={grade}, web_allowed=True)")
        
        state["current_evidence_grade"] = grade
        state["current_missing_items"] = missing_items
        state["current_next_step"] = next_step
        
        logger.info(f"⚖️ PITCH: Grade={grade}, next={next_step}, web_allowed={web_allowed}")
        
        return state
    
    # =========================================================================
    # NODE: Web Research Planner
    # =========================================================================
    
    async def web_research_planner(self, state: PitchDeckState) -> PitchDeckState:
        """Plan web research queries for missing items."""
        slide_type = state["current_slide_spec"]["slide_type"]
        logger.info(f"🌐 PITCH: Planning web research for {slide_type}")
        
        # Get geography/industry hints - use 'or {}' to handle None values
        user_hints = state.get("user_hints") or {}
        enhanced_context = state.get("enhanced_context") or {}
        geo_industry = {
            "geography": user_hints.get("geography") or enhanced_context.get("target_market", ""),
            "industry": user_hints.get("sector") or enhanced_context.get("industry", "")
        }
        
        prompt = WEB_RESEARCH_PLANNER_PROMPT.format(
            slide_type=slide_type,
            missing_items=json.dumps(state["current_missing_items"]),
            project_summary=state.get("project_summary", ""),
            geography_industry=json.dumps(geo_industry),
            current_date=datetime.utcnow().strftime("%B %Y")
        )
        
        response = await self._call_llm(prompt, temperature=0.2)
        result = self._parse_json_response(response)
        
        # Handle null result from LLM parsing failure
        if result is None:
            logger.warning(f"🌐 PITCH: Failed to parse web research planner response, using defaults")
            result = {}
        
        state["web_queries"] = result.get("queries", [])[:DEFAULT_PITCH_CONFIG.max_web_queries_per_slide]
        state["extraction_targets"] = result.get("extraction_targets", [])
        
        # Generate default queries if none returned
        if not state["web_queries"]:
            # Fallback: generate basic queries based on slide type and project context
            project_name = state.get("project_name") or ""
            industry = (state.get("enhanced_context") or {}).get("industry", "")
            geography = (state.get("user_hints") or {}).get("geography", "")
            
            slide_type = state["current_slide_spec"]["slide_type"]
            if slide_type == "Market":
                state["web_queries"] = [
                    f"{industry} market size 2024",
                    f"{industry} market growth rate forecast",
                    f"{industry} TAM SAM SOM {geography}" if geography else f"{industry} addressable market"
                ]
            elif slide_type == "Competition":
                state["web_queries"] = [
                    f"{industry} competitors {geography}" if geography else f"{industry} market leaders",
                    f"{industry} competitive landscape 2024"
                ]
            state["extraction_targets"] = ["market size", "growth rate", "key players"]
            logger.info(f"🌐 PITCH: Using fallback queries for {slide_type}")
        
        logger.info(f"🌐 PITCH: Planned {len(state['web_queries'])} web queries")
        
        return state
    
    # =========================================================================
    # NODE: Web Search
    # =========================================================================
    
    async def web_search(self, state: PitchDeckState) -> PitchDeckState:
        """Execute web search and extract evidence."""
        slide_type = state["current_slide_spec"]["slide_type"]
        queries = state.get("web_queries", [])
        
        if not queries:
            state["current_web_evidence"] = []
            return state
        
        logger.info(f"🔍 PITCH: Executing {len(queries)} web searches for {slide_type}")
        
        # Track queries in tool trace
        state["tool_trace"]["web_queries"].extend(queries)
        
        try:
            # Use existing web search service
            web_evidence = await self.web_search_service.search_and_extract(
                queries=queries,
                what_to_extract=state.get("extraction_targets", []),
                max_results_per_query=DEFAULT_PITCH_CONFIG.max_web_results_per_query
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
            
            logger.info(f"🔍 PITCH: Found {len(state['current_web_evidence'])} web evidence items")
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            state["current_web_evidence"] = []
        
        return state
    
    # =========================================================================
    # NODE: Slide Writer
    # =========================================================================
    
    async def slide_writer(self, state: PitchDeckState) -> PitchDeckState:
        """Generate slide content."""
        slide_spec = state["current_slide_spec"]
        slide_type = slide_spec["slide_type"]
        
        logger.info(f"✍️ PITCH: Writing slide {state['current_slide_index'] + 1}: {slide_type}")
        
        # Format project evidence
        project_evidence_text = "No project evidence available."
        if state.get("current_project_evidence"):
            lines = []
            for i, ev in enumerate(state["current_project_evidence"], 1):
                lines.append(f"[P{i}] ({ev['artifact_type']}): {ev['content'][:600]}")
            project_evidence_text = "\n\n".join(lines)
        
        # Format web evidence
        web_evidence_text = "No web evidence available."
        if state.get("current_web_evidence"):
            lines = []
            for i, ev in enumerate(state["current_web_evidence"], 1):
                lines.append(f"[W{i}] ({ev['domain']}): {ev['claim']} - \"{ev['snippet'][:200]}\"")
            web_evidence_text = "\n\n".join(lines)
        
        deck_context = {
            "deck_purpose": state["deck_purpose"],
            "stage": state["stage"],
            "category": state["category"],
            "project_name": state.get("project_name", "")
        }
        
        grader_info = {
            "grade": state["current_evidence_grade"],
            "missing_items": state["current_missing_items"],
            "next_step": state["current_next_step"]
        }
        
        prompt = SLIDE_WRITER_PROMPT.format(
            slide_spec=json.dumps(slide_spec),
            deck_context=json.dumps(deck_context),
            user_hints=json.dumps(state.get("user_hints") or {}),
            grader=json.dumps(grader_info),
            project_evidence=project_evidence_text,
            web_evidence=web_evidence_text,
            slide_type=slide_type
        )
        
        response = await self._call_llm(prompt, temperature=0.4)
        result = self._parse_json_response(response) or {}
        
        # Build local citation ID to chunk_ref mapping for later global ID remapping
        local_cite_to_chunk = {}
        for i, ev in enumerate(state.get("current_project_evidence", []), 1):
            local_cite_to_chunk[f"P{i}"] = ev["chunk_id"]
        for i, ev in enumerate(state.get("current_web_evidence", []), 1):
            local_cite_to_chunk[f"W{i}"] = ev.get("url", f"web_{i}")
        
        # Add slide to draft with citation mapping
        slide_content = {
            "slide_type": result.get("slide_type", slide_type),
            "slide_title": result.get("slide_title", f"{slide_type} Slide"),
            "slide_bullets": result.get("slide_bullets", []),
            "description": result.get("description", ""),
            "citations_used": result.get("citations_used", []),
            "placeholders": result.get("placeholders", []),
            "warnings": result.get("warnings", []),
            "_local_cite_to_chunk": local_cite_to_chunk  # Internal: for global ID remapping
        }
        
        state["slides_draft"].append(slide_content)
        
        # Collect citations with chunk_ref for deduplication
        project_citations = self.rag_service.create_citations_from_evidence(
            [type('obj', (object,), {
                'chunk_id': ev['chunk_id'],
                'content': ev['content'],
                'artifact_type': ev['artifact_type'],
                'score': ev['score'],
                'metadata': ev['metadata']
            })() for ev in state.get("current_project_evidence", [])],
            [c for c in result.get("citations_used", []) if c.startswith("P")]
        )
        state["all_project_citations"].extend(project_citations)
        
        # Add web citations
        for cite_id in result.get("citations_used", []):
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
        
        logger.info(f"✍️ PITCH: Completed slide {slide_type} with {len(slide_content['slide_bullets'])} bullets")
        
        return state
    
    # =========================================================================
    # NODE: Next Slide Router
    # =========================================================================
    
    def should_continue_slides(self, state: PitchDeckState) -> Literal["continue", "done"]:
        """Determine if there are more slides to process."""
        current_idx = state["current_slide_index"]
        total_slides = len(state["slides_plan"])
        
        if current_idx < total_slides - 1:
            return "continue"
        return "done"
    
    async def increment_slide_index(self, state: PitchDeckState) -> PitchDeckState:
        """Move to next slide."""
        state["current_slide_index"] += 1
        logger.info(f"➡️ PITCH: Moving to slide {state['current_slide_index'] + 1}")
        return state
    
    # =========================================================================
    # NODE: Consistency Check
    # =========================================================================
    
    async def consistency_check(self, state: PitchDeckState) -> PitchDeckState:
        """Check cross-slide consistency."""
        logger.info("🔍 PITCH: Running consistency check...")
        
        deck_context = {
            "deck_purpose": state["deck_purpose"],
            "stage": state["stage"],
            "category": state["category"],
            "project_name": state.get("project_name", "")
        }
        
        prompt = CONSISTENCY_CHECK_PROMPT.format(
            deck_context=json.dumps(deck_context),
            slides_draft=json.dumps(state["slides_draft"])
        )
        
        response = await self._call_llm(prompt, temperature=0.1)
        result = self._parse_json_response(response) or {}
        
        state["consistency_issues"] = result.get("issues", [])
        state["auto_fixes"] = result.get("auto_fixes", [])
        
        logger.info(f"🔍 PITCH: LLM returned {len(state['auto_fixes'])} auto-fixes")
        for i, fix in enumerate(state["auto_fixes"]):
            logger.debug(f"  Fix {i+1}: '{fix.get('original_text', '')[:50]}...' → '{fix.get('replacement_text', '')[:50]}...'")
        
        # Apply auto-fixes with robust matching
        fixes_applied = 0
        for fix in state["auto_fixes"]:
            original_text = fix.get("original_text", "")
            replacement_text = fix.get("replacement_text", "")
            target_slide_type = fix.get("slide_type")
            target_field = fix.get("field")
            
            if not original_text or not replacement_text:
                continue
            
            for slide in state["slides_draft"]:
                # Match by slide_type if specified, otherwise apply to all slides
                if target_slide_type and slide["slide_type"] != target_slide_type:
                    continue
                
                # Apply to specific field or all text fields
                fields_to_check = [target_field] if target_field else ["slide_title", "slide_bullets", "description"]
                
                for field in fields_to_check:
                    if field not in slide:
                        continue
                    
                    if isinstance(slide[field], str):
                        if original_text in slide[field]:
                            slide[field] = slide[field].replace(original_text, replacement_text)
                            fixes_applied += 1
                    elif isinstance(slide[field], list):
                        new_list = []
                        for item in slide[field]:
                            if isinstance(item, str) and original_text in item:
                                new_list.append(item.replace(original_text, replacement_text))
                                fixes_applied += 1
                            else:
                                new_list.append(item)
                        slide[field] = new_list
        
        # If LLM auto_fixes didn't apply and there are INCONSISTENT_TERM issues,
        # make a second LLM call to get proper term standardization
        inconsistent_term_issues = [
            issue for issue in state["consistency_issues"] 
            if issue.get("type") == "INCONSISTENT_TERM"
        ]
        
        if inconsistent_term_issues and fixes_applied == 0:
            logger.info(f"🔍 PITCH: {len(inconsistent_term_issues)} term inconsistencies detected, requesting LLM standardization...")
            
            # Build a focused prompt for term standardization
            term_fix_prompt = f"""You found these term inconsistencies in a pitch deck:
{json.dumps(inconsistent_term_issues, indent=2)}

Current slides:
{json.dumps(state["slides_draft"], indent=2)}

For EACH inconsistency, identify:
1. The EXACT variants used (copy exact text from slides)
2. Choose ONE canonical term (the most specific and descriptive)
3. Generate replacement rules

Return JSON only:
{{
  "canonical_term": "the chosen standard term",
  "replacements": [
    {{"find": "exact text to find", "replace": "canonical term"}}
  ]
}}"""
            
            try:
                fix_response = await self._call_llm(term_fix_prompt, temperature=0.1)
                fix_result = self._parse_json_response(fix_response) or {}
                
                replacements = fix_result.get("replacements", [])
                canonical = fix_result.get("canonical_term", "")
                
                if replacements and canonical:
                    logger.info(f"🔍 PITCH: Standardizing to canonical term: '{canonical}'")
                    
                    for replacement in replacements:
                        find_text = replacement.get("find", "")
                        replace_text = replacement.get("replace", canonical)
                        
                        if not find_text or find_text == replace_text:
                            continue
                        
                        for slide in state["slides_draft"]:
                            for field in ["slide_title", "slide_bullets", "description"]:
                                if field not in slide:
                                    continue
                                
                                if isinstance(slide[field], str):
                                    if find_text in slide[field]:
                                        slide[field] = slide[field].replace(find_text, replace_text)
                                        fixes_applied += 1
                                elif isinstance(slide[field], list):
                                    new_list = []
                                    for item in slide[field]:
                                        if isinstance(item, str) and find_text in item:
                                            new_list.append(item.replace(find_text, replace_text))
                                            fixes_applied += 1
                                        else:
                                            new_list.append(item)
                                    slide[field] = new_list
            except Exception as e:
                logger.warning(f"🔍 PITCH: Term standardization failed: {e}")
        
        logger.info(f"🔍 PITCH: Found {len(state['consistency_issues'])} issues, applied {fixes_applied} total fixes")
        
        return state
    
    # =========================================================================
    # NODE: Deck Assembler
    # =========================================================================
    
    async def deck_assembler(self, state: PitchDeckState) -> PitchDeckState:
        """Assemble final deck with deduplicated citations and globally unique IDs."""
        logger.info("📦 PITCH: Assembling final deck...")
        
        # Step 1: Deduplicate citations and assign globally unique IDs
        chunk_to_global_id = {}  # chunk_ref/url -> new global ID
        final_citations = []
        
        project_counter = 1
        web_counter = 1
        
        for cite in state["all_project_citations"] + state["all_web_citations"]:
            cite_key = cite.get("chunk_ref") or cite.get("url", cite["id"])
            
            if cite_key not in chunk_to_global_id:
                # Assign new globally unique ID
                if cite.get("type") == "web":
                    new_id = f"W{web_counter}"
                    web_counter += 1
                else:
                    new_id = f"P{project_counter}"
                    project_counter += 1
                
                chunk_to_global_id[cite_key] = new_id
                
                # Create new citation with global ID
                new_cite = cite.copy()
                new_cite["id"] = new_id
                final_citations.append(new_cite)
        
        # Step 2: Update slide citation references to use global IDs
        updated_slides = []
        for slide in state["slides_draft"]:
            updated_slide = slide.copy()
            local_cite_to_chunk = slide.get("_local_cite_to_chunk", {})
            
            # Remap local citations to global IDs
            new_citations_used = []
            for local_cite_id in slide.get("citations_used", []):
                chunk_ref = local_cite_to_chunk.get(local_cite_id)
                if chunk_ref and chunk_ref in chunk_to_global_id:
                    global_id = chunk_to_global_id[chunk_ref]
                    if global_id not in new_citations_used:
                        new_citations_used.append(global_id)
                else:
                    # Keep original if no mapping found (shouldn't happen)
                    if local_cite_id not in new_citations_used:
                        new_citations_used.append(local_cite_id)
            
            updated_slide["citations_used"] = new_citations_used
            
            # Also update citations in description text [P1], [P2] -> [Pglobal]
            description = updated_slide.get("description", "")
            for local_id, chunk_ref in local_cite_to_chunk.items():
                if chunk_ref in chunk_to_global_id:
                    global_id = chunk_to_global_id[chunk_ref]
                    # Replace [P1] with [Pglobal], [W1] with [Wglobal]
                    description = description.replace(f"[{local_id}]", f"[{global_id}]")
            updated_slide["description"] = description
            
            # Remove internal mapping field from output
            updated_slide.pop("_local_cite_to_chunk", None)
            updated_slides.append(updated_slide)
        
        state["slides_final"] = updated_slides
        state["citations"] = final_citations
        
        # Compile warnings
        all_warnings = list(state.get("deck_warnings", []))
        for issue in state.get("consistency_issues", []):
            all_warnings.append(f"{issue['type']}: {issue['detail']}")
        
        state["deck_warnings"] = all_warnings[:10]  # Limit warnings
        
        logger.info(f"📦 PITCH: Final deck: {len(state['slides_final'])} slides, {len(state['citations'])} unique citations")
        
        return state
    
    # =========================================================================
    # NODE: Persist Deck Run
    # =========================================================================
    
    async def persist_deck_run(self, state: PitchDeckState) -> PitchDeckState:
        """Save deck to database."""
        logger.info("💾 PITCH: Persisting deck...")
        
        # Calculate run duration
        start_time = datetime.fromisoformat(state["start_time"])
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        state["tool_trace"]["latency_ms"] = duration_ms
        
        # Get next version
        version = await self.db_adapter.get_next_version(
            state["project_id"],
            state["tenant_id"]
        )
        
        deck_version = {
            "version": version,
            "deck_purpose": state["deck_purpose"],
            "stage": state["stage"],
            "category": state["category"],
            "slides": state["slides_final"],
            "citations": state["citations"],
            "warnings": state.get("deck_warnings", []),
            "user_inputs": state.get("user_hints", {}),
            "run_trace": state["tool_trace"],
            "status": "completed"
        }
        
        success = await self.db_adapter.save_deck_version(
            project_id=state["project_id"],
            tenant_id=state["tenant_id"],
            user_id=state["user_id"],
            deck_version=deck_version
        )
        
        if success:
            state["deck_version"] = version
            state["generation_status"] = "completed"
            logger.info(f"💾 PITCH: Saved deck version {version}")
            
            # Trigger background chunking and embedding for "Chat with Project"
            # This replaces any existing pitch deck chunks with the new version
            try:
                chunking_service = VMPProjectChunkingService()
                pitch_deck_data = {
                    "pitch_deck": {
                        "deck_purpose": state["deck_purpose"],
                        "stage": state["stage"],
                        "category": state["category"],
                        "version": version,
                        "slides": state["slides_final"],
                        "citations": state["citations"],
                        "warnings": state.get("deck_warnings", []),
                    }
                }
                
                # Fire-and-forget background task for chunking
                await chunking_service.chunk_feature_background(
                    project_id=state["project_id"],
                    tenant_id=state["tenant_id"],
                    feature_type=VMPFeatureType.PITCH_DECK,
                    feature_data=pitch_deck_data
                )
                logger.info(f"🚀 PITCH: Background chunking triggered for pitch deck v{version}")
            except Exception as e:
                # Don't fail the entire operation if chunking fails
                logger.warning(f"⚠️ PITCH: Background chunking failed to start: {e}")
        else:
            state["generation_status"] = "failed"
            state["error_message"] = "Failed to save deck to database"
            logger.error("💾 PITCH: Failed to save deck")
        
        return state
    
    # =========================================================================
    # ROUTING
    # =========================================================================
    
    def route_after_grading(self, state: PitchDeckState) -> Literal["web_research", "write_slide"]:
        """Route based on evidence grade."""
        next_step = state.get("current_next_step") or "WRITE_FROM_PROJECT"
        web_allowed = (state.get("current_slide_spec") or {}).get("web_allowed", False)
        
        if next_step == "DO_WEB_RESEARCH" and web_allowed:
            return "web_research"
        return "write_slide"


def create_pitch_deck_graph() -> StateGraph:
    """Create the LangGraph state graph for pitch deck generation."""
    workflow = PitchDeckWorkflow()
    
    # Create graph
    graph = StateGraph(PitchDeckState)
    
    # Add nodes
    graph.add_node("load_context", workflow.load_project_context)
    graph.add_node("intent_router", workflow.deck_intent_router)
    graph.add_node("planner", workflow.deck_planner)
    graph.add_node("query_builder", workflow.slide_query_builder)
    graph.add_node("retrieve", workflow.project_retrieve)
    graph.add_node("grader", workflow.evidence_grader)
    graph.add_node("web_planner", workflow.web_research_planner)
    graph.add_node("web_search", workflow.web_search)
    graph.add_node("writer", workflow.slide_writer)
    graph.add_node("next_slide", workflow.increment_slide_index)
    graph.add_node("consistency", workflow.consistency_check)
    graph.add_node("assembler", workflow.deck_assembler)
    graph.add_node("persist", workflow.persist_deck_run)
    
    # Define edges
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "intent_router")
    graph.add_edge("intent_router", "planner")
    graph.add_edge("planner", "query_builder")
    graph.add_edge("query_builder", "retrieve")
    graph.add_edge("retrieve", "grader")
    
    # Conditional: after grading, go to web research or write
    graph.add_conditional_edges(
        "grader",
        workflow.route_after_grading,
        {
            "web_research": "web_planner",
            "write_slide": "writer"
        }
    )
    
    graph.add_edge("web_planner", "web_search")
    graph.add_edge("web_search", "writer")
    
    # After writing, check if more slides
    graph.add_conditional_edges(
        "writer",
        workflow.should_continue_slides,
        {
            "continue": "next_slide",
            "done": "consistency"
        }
    )
    
    graph.add_edge("next_slide", "query_builder")
    graph.add_edge("consistency", "assembler")
    graph.add_edge("assembler", "persist")
    graph.add_edge("persist", END)
    
    return graph.compile()


async def run_pitch_deck_generation(
    project_id: str,
    tenant_id: str,
    user_id: str,
    user_hints: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the pitch deck generation workflow.
    
    Args:
        project_id: VMP project ID
        tenant_id: Tenant ID
        user_id: User ID triggering generation
        user_hints: Optional user-provided hints (purpose, stage, team, etc.)
        
    Returns:
        Final state dict with generated deck
    """
    logger.info(f"🚀 PITCH: Starting deck generation for project {project_id}")
    
    # Initialize state
    initial_state: PitchDeckState = {
        "project_id": project_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "user_hints": user_hints or {},
        "project_summary": "",
        "project_name": "",
        "project_description": "",
        "available_artifacts": [],
        "detected_category": "OTHER",  # Auto-detected from project data
        "enhanced_context": {},  # From requirement generator
        "deck_purpose": "",
        "stage": "",
        "category": "",
        "reasoning_brief": "",
        "missing_inputs": [],
        "slides_plan": [],
        "deck_warnings": [],
        "current_slide_index": 0,
        "current_slide_spec": {},
        "current_retrieval_query": "",
        "current_artifact_hints": [],
        "current_project_evidence": [],
        "current_web_evidence": [],
        "current_evidence_grade": "",
        "current_missing_items": [],
        "current_next_step": "",
        "web_queries": [],
        "extraction_targets": [],
        "slides_draft": [],
        "all_project_citations": [],
        "all_web_citations": [],
        "slides_final": [],
        "citations": [],
        "consistency_issues": [],
        "auto_fixes": [],
        "tool_trace": {},
        "start_time": "",
        "deck_version": 0,
        "generation_status": "processing",
        "error_message": None
    }
    
    # Create and run graph with increased recursion limit
    # Each slide goes through ~5 nodes, so 15 slides × 5 = 75 + overhead
    graph = create_pitch_deck_graph()
    
    try:
        final_state = await graph.ainvoke(
            initial_state,
            config={"recursion_limit": 150}  # Support up to ~25 slides
        )
        logger.info(f"✅ PITCH: Deck generation completed - version {final_state.get('deck_version')}")
        return final_state
    except Exception as e:
        logger.error(f"❌ PITCH: Deck generation failed: {e}")
        initial_state["generation_status"] = "failed"
        initial_state["error_message"] = str(e)
        return initial_state
