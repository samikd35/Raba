"""
Clarifying Questions Agent for AMRG

Generates exactly 3 clarifying questions based on:
- Coarse routing ambiguity
- Context gaps
- Template-specific requirements
"""

import logging
from typing import Dict, Any, List

from .base_agent import BaseAMRGAgent
from ..models.state_models import ContextPack, TemplateRoutingResult, ClarifyingQuestion
from ..services.context_summarizer import get_summarized_context

logger = logging.getLogger(__name__)


class ClarifyingQuestionsAgent(BaseAMRGAgent):
    """
    Agent for generating clarifying questions.
    
    Always generates exactly 3 questions:
    - Q1: Template disambiguation (if confidence < threshold)
    - Q2: Scope/feature clarification
    - Q3: User context or business model
    """
    
    def get_agent_name(self) -> str:
        return "clarifying_questions"
    
    async def generate_questions(
        self,
        context_pack: ContextPack,
        coarse_routing: TemplateRoutingResult,
        tenant_id: str,
        user_id: str,
        project_id: str
    ) -> List[ClarifyingQuestion]:
        """
        Generate 3 clarifying questions.
        
        Args:
            context_pack: Loaded context pack
            coarse_routing: Result from coarse routing
            tenant_id: Tenant ID
            user_id: User ID
            project_id: Project ID
            
        Returns:
            List of exactly 3 ClarifyingQuestion
        """
        logger.info(f"❓ Generating clarifying questions for project {project_id}")
        
        try:
            # Create monitoring context
            monitoring_context = self.create_monitoring_context(
                tenant_id=tenant_id,
                user_id=user_id,
                project_id=project_id,
                step_name="generate_questions"
            )
            
            # Summarize context to fit within token limits
            summarized_context = get_summarized_context(context_pack, use_case="questions_base")
            logger.info(f"   Token estimate: ~{summarized_context.token_estimate} tokens")
            
            # Render prompt with summarized context
            prompt = self.render_prompt("questions_base.j2", {
                "summarized_context": summarized_context,
                "coarse_routing": coarse_routing
            })
            
            # Call LLM
            response = await self.call_llm_with_retry(
                prompt=prompt,
                monitoring_context=monitoring_context,
                temperature=0.3,
                max_tokens=16000  # gpt-5-mini needs large token budget
            )
            
            # Parse and validate response
            questions = self._parse_questions_response(response, coarse_routing)
            
            logger.info(f"✅ Generated {len(questions)} clarifying questions")
            for q in questions:
                logger.info(f"   Q{q['q_index']}: {q['question_text'][:50]}...")
            
            return questions
            
        except Exception as e:
            logger.error(f"❌ Question generation failed: {e}")
            return self._create_fallback_questions(coarse_routing)
    
    def _parse_questions_response(
        self,
        response: Dict[str, Any],
        coarse_routing: TemplateRoutingResult
    ) -> List[ClarifyingQuestion]:
        """Parse and validate questions response."""
        
        questions_raw = response.get("questions", [])
        questions: List[ClarifyingQuestion] = []
        
        for q in questions_raw:
            questions.append({
                "q_index": q.get("q_index", len(questions) + 1),
                "question_text": q.get("question_text", ""),
                "category": q.get("category", "scope_clarification"),
                "purpose": q.get("purpose", ""),
                "relates_to_templates": q.get("relates_to_templates", [])
            })
        
        # Ensure exactly 3 questions
        while len(questions) < 3:
            idx = len(questions) + 1
            questions.append(self._create_default_question(idx, coarse_routing))
        
        # Truncate to 3 if more
        questions = questions[:3]
        
        # Renumber
        for i, q in enumerate(questions):
            q["q_index"] = i + 1
        
        return questions
    
    def _create_default_question(
        self,
        idx: int,
        coarse_routing: TemplateRoutingResult
    ) -> ClarifyingQuestion:
        """Create default question when LLM doesn't provide enough."""
        
        default_questions = [
            {
                "q_index": 1,
                "question_text": "What is the primary way users will interact with your product - through a web/mobile interface, in-person service, or physical product?",
                "category": "template_disambiguation",
                "purpose": "Determine the core product type",
                "relates_to_templates": [t["code"] for t in coarse_routing["top_templates"]]
            },
            {
                "q_index": 2,
                "question_text": "What are the 2-3 most critical features that must be in your MVP for initial users to get value?",
                "category": "feature_priority",
                "purpose": "Identify must-have features",
                "relates_to_templates": [coarse_routing["top_templates"][0]["code"]]
            },
            {
                "q_index": 3,
                "question_text": "Who is your primary target user, and what is the single most important problem you're solving for them?",
                "category": "user_context",
                "purpose": "Clarify target persona and core problem",
                "relates_to_templates": [coarse_routing["top_templates"][0]["code"]]
            }
        ]
        
        if idx <= 3:
            return default_questions[idx - 1]
        return default_questions[2]  # Fallback to Q3
    
    def _create_fallback_questions(
        self,
        coarse_routing: TemplateRoutingResult
    ) -> List[ClarifyingQuestion]:
        """Create fallback questions when generation fails."""
        return [
            self._create_default_question(1, coarse_routing),
            self._create_default_question(2, coarse_routing),
            self._create_default_question(3, coarse_routing)
        ]
