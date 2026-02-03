"""
Context Composer Service

Synthesizes the Enhanced Context Pack from all bootstrap inputs:
- User-provided idea text/PDFs
- Clarifying question answers
- Web research results

Produces the structured enhanced_context that feeds VPS/BMC generation.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextComposerService:
    """
    Service for composing the Enhanced Context Pack.
    
    Combines all gathered information into a structured format
    that can be used by VPS v1 and BMC v1 agents.
    """
    
    def __init__(self):
        """Initialize context composer."""
        self._init_services()
        logger.info("Context Composer Service initialized")
    
    def _init_services(self):
        """Initialize required services."""
        try:
            from src.mvp.bootstrap.services.embedding_service import get_bootstrap_embedding_service
            self.embedding_service = get_bootstrap_embedding_service()
        except Exception as e:
            logger.warning(f"Could not initialize embedding service: {e}")
            self.embedding_service = None
        
        # Initialize Azure OpenAI provider using the correct codebase pattern
        self.openai_provider = None
        try:
            from src.mint.api.ai.providers import OpenAIProvider, LLMConfig
            from src.mint.api.ai.config import get_client_config, ModelUseCase
            
            # Get Azure OpenAI configuration
            provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
            
            # Build LLMConfig with Azure endpoint if available
            # Note: gpt-5-mini doesn't support temperature, uses max_completion_tokens
            is_gpt5_model = "gpt-5" in model_name.lower() or "o1" in model_name.lower() or "o3" in model_name.lower()
            
            llm_kwargs = {
                "provider_name": "azure_openai" if client_config.get("azure_endpoint") else "openai",
                "model_name": model_name,
                "azure_endpoint": client_config.get("azure_endpoint"),
                "api_version": client_config.get("api_version"),
                "api_key": client_config.get("api_key")
            }
            
            if is_gpt5_model:
                llm_kwargs["max_tokens"] = 16000  # gpt-5-mini needs large token budget
            else:
                llm_kwargs["temperature"] = 0.3
                llm_kwargs["max_tokens"] = 3000
            
            llm_config = LLMConfig(**llm_kwargs)
            
            self.openai_provider = OpenAIProvider(config=llm_config)
            logger.info(f"✅ Context Composer: OpenAI provider initialized with model: {model_name}, azure_endpoint: {bool(client_config.get('azure_endpoint'))}")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI provider: {e}")
        
        try:
            from src.mvp.bootstrap.adapters.database_adapter import get_bootstrap_database_adapter
            self.db_adapter = get_bootstrap_database_adapter()
        except Exception as e:
            logger.warning(f"Could not initialize database adapter: {e}")
            self.db_adapter = None
    
    async def compose_enhanced_context(
        self,
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Compose the complete Enhanced Context Pack.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            
        Returns:
            Complete enhanced_context structure
        """
        try:
            logger.info(f"🔧 Composing enhanced context for project {project_id}")
            
            # Step 1: Gather all input data
            project = self.db_adapter.get_bootstrap_project(project_id, tenant_id)
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            enhanced_context = project.get("enhanced_context", {})
            metadata = enhanced_context.get("metadata", {})
            
            # Get intake data
            intake = metadata.get("intake", {})
            idea_text = intake.get("idea_text", "")
            
            # Get Q&A data
            questions = metadata.get("clarifying_questions", [])
            answers = metadata.get("clarifying_answers", [])
            
            # Get research data
            research_results = metadata.get("research_results", {})
            
            # Step 2: Build Q&A lookup
            qa_map = self._build_qa_map(questions, answers)
            
            # Step 3: Use LLM to synthesize the context
            draft = await self._synthesize_context(
                idea_text=idea_text,
                qa_map=qa_map,
                research_results=research_results,
                project_id=project_id,
                tenant_id=tenant_id
            )
            
            # Step 4: Build the complete enhanced_context structure
            result = {
                "version": 1,
                "draft": draft,
                "confirmed": None,
                "metadata": {
                    "context_mode": "bootstrap",
                    "invariants": self._extract_invariants(draft, qa_map),
                    "created_at": metadata.get("created_at", datetime.utcnow().isoformat()),
                    "updated_at": datetime.utcnow().isoformat(),
                    "intake": intake,
                    "clarifying_questions": questions,
                    "clarifying_answers": answers,
                    "research_results": research_results
                }
            }
            
            logger.info(f"✅ Composed enhanced context for project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error composing enhanced context: {e}")
            raise
    
    def _build_qa_map(
        self,
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Build a map of question_id to question + answer."""
        qa_map = {}
        
        # Index questions by ID
        questions_by_id = {q.get("id"): q for q in questions}
        
        # Match answers to questions
        for answer in answers:
            q_id = answer.get("question_id")
            if q_id in questions_by_id:
                qa_map[q_id] = {
                    "question": questions_by_id[q_id].get("question", ""),
                    "category": questions_by_id[q_id].get("category", ""),
                    "answer": answer.get("answer", "")
                }
        
        return qa_map
    
    async def _synthesize_context(
        self,
        idea_text: str,
        qa_map: Dict[str, Dict[str, Any]],
        research_results: Dict[str, Any],
        project_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Use LLM to synthesize all inputs into structured context.
        """
        if not self.openai_provider:
            # Fallback to template-based synthesis
            return self._template_synthesis(idea_text, qa_map, research_results)
        
        try:
            # Format Q&A for prompt
            qa_text = ""
            for q_id, qa in qa_map.items():
                qa_text += f"\nQ: {qa['question']}\nA: {qa['answer']}\n"
            
            # Format research for prompt - include more snippet content
            research_text = ""
            sources = research_results.get("sources", [])
            for source in sources[:10]:
                snippet = source.get('snippet', '')[:400]  # More context per source
                research_text += f"\n[{source.get('n')}] {source.get('title')}\nURL: {source.get('url')}\nSnippet: {snippet}\n"
            
            prompt = f"""<role>
You are a business analyst synthesizing comprehensive startup context from research and user inputs.
</role>

<task>
Synthesize all inputs into a structured Enhanced Context Pack that will feed VPS and BMC generation.
</task>

<original_idea>
{idea_text}
</original_idea>

<clarifying_qa>
{qa_text}
</clarifying_qa>

<web_research_sources>
{research_text}
</web_research_sources>

<citation_rules>
- Use [n] citations throughout ALL sections where research supports claims
- Every claim about market, competition, or problem should cite a source if available
- The Research section should be COMPREHENSIVE with multiple subsections
</citation_rules>

<output_schema>
{{
  "IdeaSummary": "2-3 sentence executive summary with key research insights",
  "CustomerSegments": ["segment1 with research-backed details [n]", "segment2"],
  "Problem": {{
    "who": "who experiences this problem [cite if research supports]",
    "what": "the core problem validated by research [n]",
    "where": "context/situation where problem occurs",
    "why_now": "why this problem is urgent now - cite market trends [n]"
  }},
  "SolutionOverview": "1-2 paragraph description citing research that validates the approach [n]",
  "Differentiation": ["differentiator1 backed by research [n]", "differentiator2"],
  "BusinessModelSeeds": {{
    "revenue_model": "how they'll make money - cite comparable models if found [n]",
    "pricing_hypothesis": "initial pricing thoughts based on market research [n]",
    "cost_drivers": ["key cost1", "key cost2"]
  }},
  "AlternativesAndCompetition": {{
    "direct_competitors": ["competitor1 found in research [n]", "competitor2"],
    "indirect_alternatives": ["alternative1 - how customers currently solve this [n]"],
    "differentiation_summary": "how this is different based on research gaps [n]"
  }},
  "ConstraintsAndRisks": ["constraint1 identified in research [n]", "risk1"],
  "Research": {{
    "summary": "2-3 paragraph executive summary of key research findings [n]",
    "market_context": "Market size, trends, and dynamics from research [n]",
    "problem_validation": "Evidence validating the problem exists [n]",
    "solution_landscape": "Existing solutions, gaps, and opportunities [n]",
    "adoption_factors": "Factors affecting adoption based on research [n]",
    "sources": []
  }}
}}
</output_schema>

<output_rules>
- Make the Research section rich and comprehensive - this is the foundation for business decisions
- Use citations [1], [2], etc. throughout the ENTIRE response where research supports claims
- Return ONLY valid JSON. No markdown wrapping.
</output_rules>"""

            messages = [
                {"role": "system", "content": "You are a business analyst synthesizing startup context. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.openai_provider.generate_responses(messages)
            # Handle both dict and LLMResponse object formats
            if isinstance(response, dict):
                response_text = response.get("content", "{}")
            elif hasattr(response, 'content'):
                response_text = response.content  # LLMResponse object
            else:
                response_text = str(response)
            logger.info(f"✅ LLM synthesized context: {len(response_text)} chars")
            
            # Parse JSON from response
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    draft = json.loads(json_match.group())
                    
                    # Normalize and add research sources
                    if "Research" in draft:
                        # Always rebuild sources to ensure correct schema
                        normalized_sources = []
                        for idx, s in enumerate(sources[:10]):
                            normalized_sources.append({
                                "n": s.get("n") or s.get("id") or (idx + 1),  # Use n, id, or index
                                "title": s.get("title", "Source"),
                                "publisher": s.get("publisher"),
                                "url": s.get("url", ""),
                                "captured_at": s.get("captured_at") or datetime.utcnow().isoformat(),
                                "snippet": s.get("snippet", "")[:200] if s.get("snippet") else None
                            })
                        draft["Research"]["sources"] = normalized_sources
                    
                    return draft
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response: {e}")
            
            return self._template_synthesis(idea_text, qa_map, research_results)
            
        except Exception as e:
            logger.error(f"❌ LLM synthesis failed: {e}")
            return self._template_synthesis(idea_text, qa_map, research_results)
    
    def _template_synthesis(
        self,
        idea_text: str,
        qa_map: Dict[str, Dict[str, Any]],
        research_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Template-based synthesis as fallback.
        """
        # Extract answers by category
        def get_answer(category: str) -> str:
            for qa in qa_map.values():
                if qa.get("category") == category:
                    return qa.get("answer", "")
            return ""
        
        # Build research body with citations
        sources = research_results.get("sources", [])
        research_body = ""
        if sources:
            snippets = [f"{s.get('snippet', '')} [{s.get('n')}]" for s in sources[:5]]
            research_body = " ".join(snippets)
        
        return {
            "IdeaSummary": idea_text[:500] if idea_text else "No idea summary provided",
            "CustomerSegments": [get_answer("target_customer")] if get_answer("target_customer") else ["To be defined"],
            "Problem": {
                "who": get_answer("target_customer") or "Target customers",
                "what": get_answer("problem") or "Problem to be defined",
                "where": get_answer("market_scope") or "Market scope to be defined",
                "why_now": "Market timing to be validated"
            },
            "SolutionOverview": get_answer("solution") or idea_text[:300] if idea_text else "Solution to be defined",
            "Differentiation": [get_answer("differentiation")] if get_answer("differentiation") else ["To be defined"],
            "BusinessModelSeeds": {
                "revenue_model": get_answer("revenue") or "To be defined",
                "pricing_hypothesis": None,
                "cost_drivers": []
            },
            "AlternativesAndCompetition": {
                "direct_competitors": [],
                "indirect_alternatives": [],
                "differentiation_summary": get_answer("differentiation") or "To be defined"
            },
            "ConstraintsAndRisks": [get_answer("constraints")] if get_answer("constraints") else [],
            "Research": {
                "summary": research_body or "No research data available",
                "market_context": "Market context to be researched",
                "problem_validation": "Problem validation pending",
                "solution_landscape": "Solution landscape to be analyzed",
                "adoption_factors": "Adoption factors to be identified",
                "sources": [
                    {
                        "n": s.get("n") or s.get("id") or (idx + 1),
                        "title": s.get("title", "Source"),
                        "publisher": s.get("publisher"),
                        "url": s.get("url", ""),
                        "captured_at": s.get("captured_at") or datetime.utcnow().isoformat(),
                        "snippet": s.get("snippet", "")[:200] if s.get("snippet") else None
                    }
                    for idx, s in enumerate(sources[:10])
                ]
            }
        }
    
    def _extract_invariants(
        self,
        draft: Dict[str, Any],
        qa_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Extract invariants that research cannot change.
        """
        def get_answer(category: str) -> str:
            for qa in qa_map.values():
                if qa.get("category") == category:
                    return qa.get("answer", "")
            return ""
        
        return {
            "customer_segment": (
                draft.get("CustomerSegments", [""])[0] 
                if draft.get("CustomerSegments") 
                else get_answer("target_customer") or "Not specified"
            ),
            "geography": get_answer("market_scope") or "Not specified",
            "core_problem": draft.get("Problem", {}).get("what", "") or get_answer("problem") or "Not specified",
            "core_solution_type": draft.get("SolutionOverview", "")[:100] or "Not specified"
        }


def get_context_composer_service() -> ContextComposerService:
    """Factory function for ContextComposerService."""
    return ContextComposerService()
