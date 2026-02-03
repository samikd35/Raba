"""
Project Chat LangGraph Workflow

Main orchestration flow with 10 nodes:
1. LoadThreadContext - Load memory, recent messages
2. IntentRouter - Classify query intent
3. QueryRewrite - Optimize query for RAG
4. ProjectRetrieve - Vector search project chunks
5. EvidenceGrade - Check if evidence is sufficient
6. WebPlan - Plan web searches if needed
7. WebSearch - Execute searches and extract evidence
8. AnswerCompose - Generate response with citations
9. MemoryUpdate - Update thread memory
10. Persist - Save messages and traces
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import StateGraph, END

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.config import get_client_config, ModelUseCase, ModelProvider

from ..models import (
    ChatState,
    ChatIntent,
    EvidenceGrade,
    MessageRole,
    ThreadMemory,
    MemoryPatch,
    ProjectEvidence,
    WebEvidence,
    InternalCitation,
    ExternalCitation,
    ToolTrace,
    DEFAULT_CHAT_CONFIG,
)
from ..adapters.database_adapter import ChatDatabaseAdapter, get_chat_database_adapter
from ..services.project_rag_service import ProjectRAGService, get_project_rag_service
from ..services.web_search_service import WebSearchService, get_web_search_service
from .prompts.chat_prompts import ChatPrompts

logger = logging.getLogger(__name__)


class ProjectChatWorkflow:
    """
    LangGraph workflow for project chat with RAG and web search.
    
    Implements the 10-node orchestration flow:
    LoadContext → IntentRouter → [QueryRewrite → ProjectRetrieve → EvidenceGrade]
                                      ↓
                               [WebPlan → WebSearch] (if needed)
                                      ↓
                               AnswerCompose → MemoryUpdate → Persist
    """
    
    def __init__(self):
        """Initialize workflow with services and LLM client."""
        self.db_adapter: ChatDatabaseAdapter = get_chat_database_adapter()
        self.rag_service: ProjectRAGService = get_project_rag_service()
        self.web_service: WebSearchService = get_web_search_service()
        self.prompts = ChatPrompts()
        self.config = DEFAULT_CHAT_CONFIG
        
        # Initialize LLM provider (centralized Responses API)
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
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info("✅ ProjectChatWorkflow initialized")
    
    async def _call_llm(self, messages: list, response_format: dict = None) -> str:
        """Call LLM using centralized Responses API."""
        response = await self.ai_provider.generate_responses(
            messages=messages,
            response_format=response_format
        )
        return response.content
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(ChatState)
        
        # Add nodes
        workflow.add_node("load_context", self._load_context)
        workflow.add_node("route_intent", self._route_intent)
        workflow.add_node("rewrite_query", self._rewrite_query)
        workflow.add_node("retrieve_project", self._retrieve_project)
        workflow.add_node("grade_evidence", self._grade_evidence)
        workflow.add_node("plan_web", self._plan_web)
        workflow.add_node("search_web", self._search_web)
        workflow.add_node("compose_answer", self._compose_answer)
        workflow.add_node("update_memory", self._update_memory)
        workflow.add_node("persist", self._persist)
        workflow.add_node("handle_meta", self._handle_meta)
        
        # Set entry point
        workflow.set_entry_point("load_context")
        
        # Add edges
        workflow.add_edge("load_context", "route_intent")
        
        # Conditional routing from intent
        workflow.add_conditional_edges(
            "route_intent",
            self._route_after_intent,
            {
                "project": "rewrite_query",
                "web_only": "plan_web",
                "meta": "handle_meta",
            }
        )
        
        # Project retrieval path
        workflow.add_edge("rewrite_query", "retrieve_project")
        workflow.add_edge("retrieve_project", "grade_evidence")
        
        # Conditional routing after grading
        workflow.add_conditional_edges(
            "grade_evidence",
            self._route_after_grade,
            {
                "sufficient": "compose_answer",
                "needs_web": "plan_web",
            }
        )
        
        # Web search path
        workflow.add_edge("plan_web", "search_web")
        workflow.add_edge("search_web", "compose_answer")
        
        # Meta handler path
        workflow.add_edge("handle_meta", "update_memory")
        
        # Final path
        workflow.add_edge("compose_answer", "update_memory")
        workflow.add_edge("update_memory", "persist")
        workflow.add_edge("persist", END)
        
        return workflow.compile()
    
    # =========================================================================
    # ROUTING FUNCTIONS
    # =========================================================================
    
    def _route_after_intent(self, state: ChatState) -> str:
        """Route based on intent classification."""
        intent = state.get("intent", ChatIntent.PROJECT_ONLY.value)
        
        if intent == ChatIntent.META.value:
            return "meta"
        elif intent == ChatIntent.WEB_ONLY.value:
            return "web_only"
        else:
            # PROJECT_ONLY or PROJECT_PLUS_WEB both start with project retrieval
            return "project"
    
    def _route_after_grade(self, state: ChatState) -> str:
        """Route based on evidence grade and intent."""
        grade = state.get("evidence_grade", EvidenceGrade.SUFFICIENT.value)
        intent = state.get("intent", ChatIntent.PROJECT_ONLY.value)
        
        # PROJECT_ONLY: Never fall back to web search, answer with what we have
        if intent == ChatIntent.PROJECT_ONLY.value:
            return "sufficient"
        
        # PROJECT_PLUS_WEB: Always do web search to augment
        if intent == ChatIntent.PROJECT_PLUS_WEB.value:
            return "needs_web"
        
        # For other intents, only do web if evidence is insufficient
        if grade in [EvidenceGrade.PARTIAL.value, EvidenceGrade.INSUFFICIENT.value]:
            return "needs_web"
        
        return "sufficient"
    
    # =========================================================================
    # NODE: Load Context
    # =========================================================================
    
    async def _load_context(self, state: ChatState) -> ChatState:
        """Load thread context: memory and recent messages."""
        logger.info(f"📥 NODE: load_context - thread={state.get('thread_id')}")
        start_time = time.time()
        
        thread_id = state.get("thread_id")
        
        # Load thread memory
        memory = await self.db_adapter.get_thread_memory(thread_id)
        if memory:
            state["thread_summary"] = memory.running_summary or ""
            state["pinned_facts"] = memory.pinned_facts or []
            state["open_loops"] = memory.open_loops or []
        else:
            state["thread_summary"] = ""
            state["pinned_facts"] = []
            state["open_loops"] = []
        
        # Load recent messages
        messages_window = await self.db_adapter.get_recent_messages(
            thread_id,
            limit=self.config.messages_window_size
        )
        state["messages_window"] = messages_window
        
        # Initialize tool trace
        state["tool_trace"] = {
            "llm_calls": 0,
            "retrieval_chunk_ids": [],
            "retrieval_scores": [],
            "web_queries": [],
            "web_urls_fetched": [],
        }
        
        logger.info(f"✅ load_context: {len(messages_window)} messages, summary={len(state['thread_summary'])} chars ({time.time()-start_time:.2f}s)")
        return state
    
    # =========================================================================
    # NODE: Route Intent
    # =========================================================================
    
    async def _route_intent(self, state: ChatState) -> ChatState:
        """Classify user intent to determine routing."""
        logger.info(f"🔀 NODE: route_intent")
        start_time = time.time()
        
        prompt = self.prompts.INTENT_ROUTER_PROMPT.format(
            user_message=state.get("user_message", ""),
            thread_summary=state.get("thread_summary", ""),
            pinned_facts=", ".join(state.get("pinned_facts", []))
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": "You are an intent classifier. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["intent"] = result.get("intent", ChatIntent.PROJECT_ONLY.value)
            state["needs_clarification"] = result.get("needs_clarification", False)
            state["clarifying_questions"] = result.get("clarifying_questions", [])
            state["tool_trace"]["intent"] = state["intent"]
            
            logger.info(f"✅ route_intent: {state['intent']} ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ route_intent error: {e}")
            state["intent"] = ChatIntent.PROJECT_ONLY.value
            state["error"] = str(e)
            state["error_stage"] = "route_intent"
        
        return state
    
    # =========================================================================
    # NODE: Rewrite Query
    # =========================================================================
    
    async def _rewrite_query(self, state: ChatState) -> ChatState:
        """Optimize query for RAG retrieval."""
        logger.info(f"✏️ NODE: rewrite_query")
        start_time = time.time()
        
        prompt = self.prompts.QUERY_REWRITE_PROMPT.format(
            user_message=state.get("user_message", ""),
            thread_summary=state.get("thread_summary", ""),
            pinned_facts=", ".join(state.get("pinned_facts", []))
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": "You are a query optimizer. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["rewritten_query"] = result.get("rewritten_query", state.get("user_message", ""))
            state["query_filters"] = result.get("filters", {})
            state["tool_trace"]["rewritten_query"] = state["rewritten_query"]
            
            logger.info(f"✅ rewrite_query: '{state['rewritten_query'][:50]}...' ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ rewrite_query error: {e}")
            state["rewritten_query"] = state.get("user_message", "")
            state["query_filters"] = {}
        
        return state
    
    # =========================================================================
    # NODE: Retrieve Project
    # =========================================================================
    
    async def _retrieve_project(self, state: ChatState) -> ChatState:
        """Retrieve evidence from project chunks via RAG."""
        logger.info(f"🔍 NODE: retrieve_project")
        start_time = time.time()
        
        query = state.get("rewritten_query", state.get("user_message", ""))
        project_id = state.get("project_id")
        tenant_id = state.get("tenant_id")
        
        # Get artifact type filters if specified
        filters = state.get("query_filters", {})
        artifact_types = filters.get("artifact_types")
        
        try:
            evidence_list = await self.rag_service.retrieve_evidence(
                query=query,
                project_id=project_id,
                tenant_id=tenant_id,
                artifact_types=artifact_types if artifact_types else None
            )
            
            # Convert to dicts for state
            state["project_evidence"] = [e.model_dump() for e in evidence_list]
            
            # Update tool trace
            state["tool_trace"]["retrieval_chunk_ids"] = [e.chunk_id for e in evidence_list]
            state["tool_trace"]["retrieval_scores"] = [e.score for e in evidence_list]
            
            logger.info(f"✅ retrieve_project: {len(evidence_list)} chunks ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ retrieve_project error: {e}")
            state["project_evidence"] = []
            state["error"] = str(e)
            state["error_stage"] = "retrieve_project"
        
        return state
    
    # =========================================================================
    # NODE: Grade Evidence
    # =========================================================================
    
    async def _grade_evidence(self, state: ChatState) -> ChatState:
        """Grade if project evidence is sufficient."""
        logger.info(f"📊 NODE: grade_evidence")
        start_time = time.time()
        
        # Format evidence for grading
        evidence_list = [ProjectEvidence(**e) for e in state.get("project_evidence", [])]
        evidence_text = self.rag_service.format_evidence_for_context(evidence_list)
        
        prompt = self.prompts.EVIDENCE_GRADER_PROMPT.format(
            user_message=state.get("user_message", ""),
            project_evidence_text=evidence_text
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": "You are an evidence grader. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["evidence_grade"] = result.get("grade", EvidenceGrade.SUFFICIENT.value)
            state["missing_info"] = result.get("missing", [])
            state["tool_trace"]["evidence_grade"] = state["evidence_grade"]
            
            logger.info(f"✅ grade_evidence: {state['evidence_grade']} ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ grade_evidence error: {e}")
            state["evidence_grade"] = EvidenceGrade.SUFFICIENT.value
            state["missing_info"] = []
        
        return state
    
    # =========================================================================
    # NODE: Plan Web
    # =========================================================================
    
    async def _plan_web(self, state: ChatState) -> ChatState:
        """Plan web search queries."""
        logger.info(f"📝 NODE: plan_web")
        start_time = time.time()
        
        missing_info = state.get("missing_info", [])
        
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_year = now.year
        current_month = now.strftime("%B")  # e.g., "December"
        
        prompt = self.prompts.WEB_PLAN_PROMPT.format(
            user_message=state.get("user_message", ""),
            missing_info=", ".join(missing_info) if missing_info else "general context",
            thread_summary=state.get("thread_summary", ""),
            current_date=current_date,
            current_year=current_year,
            current_month=current_month
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": "You are a research planner. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["web_plan_queries"] = result.get("queries", [])[:self.config.max_web_queries]
            state["web_plan_what_to_extract"] = result.get("what_to_extract", [])
            
            logger.info(f"✅ plan_web: {len(state['web_plan_queries'])} queries planned ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ plan_web error: {e}")
            # Fallback: use user message as query
            state["web_plan_queries"] = [state.get("user_message", "")]
            state["web_plan_what_to_extract"] = ["relevant facts"]
        
        return state
    
    # =========================================================================
    # NODE: Search Web
    # =========================================================================
    
    async def _search_web(self, state: ChatState) -> ChatState:
        """Execute web searches and extract evidence."""
        logger.info(f"🌐 NODE: search_web")
        start_time = time.time()
        
        queries = state.get("web_plan_queries", [])
        what_to_extract = state.get("web_plan_what_to_extract", [])
        
        try:
            evidence_list = await self.web_service.search_and_extract(
                queries=queries,
                what_to_extract=what_to_extract,
                user_question=state.get("user_message", "")
            )
            
            # Convert to dicts for state
            state["web_evidence"] = [e.model_dump() for e in evidence_list]
            
            # Update tool trace
            state["tool_trace"]["web_queries"] = queries
            state["tool_trace"]["web_urls_fetched"] = [e.url for e in evidence_list]
            
            logger.info(f"✅ search_web: {len(evidence_list)} evidence items ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ search_web error: {e}")
            state["web_evidence"] = []
        
        return state
    
    # =========================================================================
    # NODE: Handle Meta
    # =========================================================================
    
    async def _handle_meta(self, state: ChatState) -> ChatState:
        """Handle meta requests (summarize, status, etc.)."""
        logger.info(f"ℹ️ NODE: handle_meta")
        start_time = time.time()
        
        prompt = self.prompts.META_HANDLER_PROMPT.format(
            user_message=state.get("user_message", ""),
            thread_summary=state.get("thread_summary", "No summary yet.")
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": self.prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["answer_text"] = result.get("answer_text", "I can help with that.")
            state["citations"] = []
            state["follow_ups"] = result.get("follow_ups", [])
            
            logger.info(f"✅ handle_meta ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ handle_meta error: {e}")
            state["answer_text"] = "I encountered an error processing your request."
            state["citations"] = []
            state["follow_ups"] = []
        
        return state
    
    # =========================================================================
    # NODE: Compose Answer
    # =========================================================================
    
    async def _compose_answer(self, state: ChatState) -> ChatState:
        """Compose the final answer with citations."""
        logger.info(f"💬 NODE: compose_answer")
        start_time = time.time()
        
        # Format evidence
        project_evidence = [ProjectEvidence(**e) for e in state.get("project_evidence", [])]
        web_evidence = [WebEvidence(**e) for e in state.get("web_evidence", [])]
        
        project_evidence_text = self.rag_service.format_evidence_for_context(project_evidence)
        web_evidence_text = self.web_service.format_evidence_for_context(web_evidence) if web_evidence else "No web evidence."
        
        prompt = self.prompts.ANSWER_COMPOSER_PROMPT.format(
            user_message=state.get("user_message", ""),
            thread_summary=state.get("thread_summary", ""),
            pinned_facts=", ".join(state.get("pinned_facts", [])),
            open_loops=", ".join(state.get("open_loops", [])),
            project_evidence_text=project_evidence_text,
            web_evidence_text=web_evidence_text
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": self.prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["answer_text"] = result.get("answer_text", "I couldn't generate a proper response.")
            state["follow_ups"] = result.get("follow_ups", [])[:3]
            
            # Build citations from evidence
            citations = self._build_citations(
                project_evidence=project_evidence,
                web_evidence=web_evidence,
                citations_used=result.get("citations_used", [])
            )
            state["citations"] = [c.model_dump() for c in citations]
            
            logger.info(f"✅ compose_answer: {len(state['answer_text'])} chars, {len(citations)} citations ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ compose_answer error: {e}")
            state["answer_text"] = "I encountered an error while composing my response. Please try again."
            state["citations"] = []
            state["follow_ups"] = []
            state["error"] = str(e)
            state["error_stage"] = "compose_answer"
        
        return state
    
    def _build_citations(
        self,
        project_evidence: List[ProjectEvidence],
        web_evidence: List[WebEvidence],
        citations_used: List[str]
    ) -> List:
        """Build citation objects from evidence."""
        citations = []
        
        # Project citations (P1, P2, ...)
        for i, evidence in enumerate(project_evidence, 1):
            ref_id = f"P{i}"
            if not citations_used or ref_id in citations_used:
                citations.append(InternalCitation(
                    ref_id=ref_id,
                    artifact_type=evidence.artifact_type,
                    chunk_id=evidence.chunk_id,
                    snippet=evidence.content[:200] if evidence.content else None,
                    score=evidence.score
                ))
        
        # Web citations (W1, W2, ...)
        for i, evidence in enumerate(web_evidence, 1):
            ref_id = f"W{i}"
            if not citations_used or ref_id in citations_used:
                citations.append(ExternalCitation(
                    ref_id=ref_id,
                    url=evidence.url,
                    title=evidence.title,
                    domain=evidence.domain,
                    snippet=evidence.snippet[:200] if evidence.snippet else None,
                    fetched_at=evidence.fetched_at,
                    published_at=evidence.published_at
                ))
        
        return citations
    
    # =========================================================================
    # NODE: Update Memory
    # =========================================================================
    
    async def _update_memory(self, state: ChatState) -> ChatState:
        """Update thread memory with this turn."""
        logger.info(f"🧠 NODE: update_memory")
        start_time = time.time()
        
        prompt = self.prompts.MEMORY_UPDATE_PROMPT.format(
            thread_summary=state.get("thread_summary", ""),
            pinned_facts=", ".join(state.get("pinned_facts", [])),
            open_loops=", ".join(state.get("open_loops", [])),
            user_message=state.get("user_message", ""),
            answer_text=state.get("answer_text", "")
        )
        
        try:
            response_content = await self._call_llm(
                messages=[
                    {"role": "system", "content": "You are a memory manager. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            state["tool_trace"]["llm_calls"] = state["tool_trace"].get("llm_calls", 0) + 1
            
            result = json.loads(response_content)
            
            state["memory_patch"] = {
                "new_summary": result.get("new_summary"),
                "pinned_facts_add": result.get("pinned_facts_add", []),
                "pinned_facts_remove": result.get("pinned_facts_remove", []),
                "open_loops_add": result.get("open_loops_add", []),
                "open_loops_remove": result.get("open_loops_remove", [])
            }
            
            logger.info(f"✅ update_memory ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ update_memory error: {e}")
            state["memory_patch"] = {}
        
        return state
    
    # =========================================================================
    # NODE: Persist
    # =========================================================================
    
    async def _persist(self, state: ChatState) -> ChatState:
        """Persist messages, citations, and tool trace to database."""
        logger.info(f"💾 NODE: persist")
        start_time = time.time()
        
        thread_id = state.get("thread_id")
        
        try:
            # Calculate latency
            if "start_time" in state:
                latency_ms = int((time.time() - state["start_time"]) * 1000)
                state["tool_trace"]["latency_ms"] = latency_ms
            
            # Save assistant message
            await self.db_adapter.create_message(
                thread_id=thread_id,
                role=MessageRole.ASSISTANT,
                content=state.get("answer_text", ""),
                citations=state.get("citations", []),
                tool_trace=state.get("tool_trace"),
                metadata={
                    "follow_ups": state.get("follow_ups", []),
                    "intent": state.get("intent"),
                    "evidence_grade": state.get("evidence_grade")
                }
            )
            
            # Update thread memory
            if state.get("memory_patch"):
                memory_patch = MemoryPatch(**state["memory_patch"])
                
                # Build last context refs
                last_context_refs = {
                    "project_chunks": state.get("tool_trace", {}).get("retrieval_chunk_ids", []),
                    "web_urls": state.get("tool_trace", {}).get("web_urls_fetched", [])
                }
                
                await self.db_adapter.update_thread_memory(
                    thread_id=thread_id,
                    memory_patch=memory_patch,
                    last_context_refs=last_context_refs
                )
            
            logger.info(f"✅ persist: message + memory saved ({time.time()-start_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"❌ persist error: {e}")
            state["error"] = str(e)
            state["error_stage"] = "persist"
        
        return state
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    async def run(
        self,
        project_id: str,
        thread_id: str,
        user_id: str,
        tenant_id: str,
        user_message: str
    ) -> ChatState:
        """
        Run the chat workflow for a user message.
        
        Args:
            project_id: VMP project ID
            thread_id: Chat thread ID
            user_id: User ID
            tenant_id: Tenant ID
            user_message: User's message content
            
        Returns:
            Final ChatState with answer and citations
        """
        logger.info(f"🚀 Starting chat workflow - thread={thread_id}, project={project_id}")
        
        # Initialize state
        initial_state: ChatState = {
            "project_id": project_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "user_message": user_message,
            "start_time": time.time()
        }
        
        # Save user message first
        await self.db_adapter.create_message(
            thread_id=thread_id,
            role=MessageRole.USER,
            content=user_message
        )
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        total_time = time.time() - initial_state["start_time"]
        logger.info(f"✅ Chat workflow complete - {total_time:.2f}s total")
        
        return final_state


# Singleton workflow instance
_chat_workflow: Optional[ProjectChatWorkflow] = None


def get_chat_workflow() -> ProjectChatWorkflow:
    """Get or create singleton ProjectChatWorkflow instance."""
    global _chat_workflow
    if _chat_workflow is None:
        _chat_workflow = ProjectChatWorkflow()
    return _chat_workflow


async def run_chat_workflow(
    project_id: str,
    thread_id: str,
    user_id: str,
    tenant_id: str,
    user_message: str
) -> ChatState:
    """
    Convenience function to run the chat workflow.
    
    Args:
        project_id: VMP project ID
        thread_id: Chat thread ID
        user_id: User ID
        tenant_id: Tenant ID
        user_message: User's message content
        
    Returns:
        Final ChatState with answer and citations
    """
    workflow = get_chat_workflow()
    return await workflow.run(
        project_id=project_id,
        thread_id=thread_id,
        user_id=user_id,
        tenant_id=tenant_id,
        user_message=user_message
    )
