"""Question Generator Service

Generates prioritized clarifying questions based on bootstrap intake content.
Uses LLM with dynamic prompt templates to generate contextual questions.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# System prompt for question generation
QUESTION_GENERATION_SYSTEM_PROMPT = """<role>
You are a senior business analyst specializing in startup validation and business model design.
</role>

<task>
Analyze the provided context about a business idea and generate targeted clarifying questions to gather information needed for:
1. Value Proposition Statement (VPS) - articulating customer value
2. Business Model Canvas (BMC) - defining the complete business model
</task>

<priority_framework>
- P0 (Critical): Information absolutely required for VPS/BMC generation
- P1 (Important): Information that significantly improves quality
- P2 (Nice-to-have): Information that adds depth but isn't essential
</priority_framework>

<assessment_areas>
P0 (Critical):
1. TARGET CUSTOMER: Who exactly is the customer? Demographics, behaviors, needs
2. PROBLEM/PAIN: What specific problem are they solving? How severe is it?
3. SOLUTION: What is the product/service? How does it work?
4. DIFFERENTIATION: What makes this unique vs alternatives?
5. REVENUE MODEL: How will they make money?

P1 (Important):
6. MARKET SCOPE: Geographic focus, market size
7. COMPETITION: Who are competitors? What alternatives exist?
8. CHANNELS: How will customers find and buy?
9. CONSTRAINTS: Regulatory, technical, resource limitations

P2 (Nice-to-have):
10. PARTNERSHIPS: Key dependencies and partners needed
</assessment_areas>

<rules>
- Only ask about information that is MISSING or UNCLEAR
- Make questions specific and actionable, not generic
- Reference specific details from their input to show understanding
- Prioritize P0 questions first, then P1, then P2
- Each question should unlock critical business model insights
</rules>"""

# User prompt template for question generation
QUESTION_GENERATION_USER_PROMPT = """<task>
Analyze this business idea intake and generate clarifying questions.
</task>

<business_idea_context>
{intake_content}
</business_idea_context>

<analysis_steps>
1. Identify what information IS already provided (be specific)
2. Identify critical GAPS that need clarification
3. Generate {max_questions} targeted questions to fill the most important gaps
</analysis_steps>

<valid_categories>
target_customer, problem, solution, differentiation, revenue, market_scope, competition, channels, constraints, partnerships
</valid_categories>

<output_schema>
{{
  "content_analysis": {{
    "provided": ["list of key information already provided"],
    "gaps": ["list of critical missing information"]
  }},
  "questions": [
    {{
      "id": "q1",
      "priority": "P0|P1|P2",
      "category": "one of valid_categories",
      "question": "Your specific, contextual question here?",
      "why_needed": "Brief explanation of why this is important for VPS/BMC",
      "required": true
    }}
  ]
}}
</output_schema>

<output_rules>
- Questions must be specific to THIS business idea, not generic templates
- Reference details from their input to show understanding
- P0 questions have required=true, others have required=false
- Return ONLY valid JSON. No markdown, no explanations.
</output_rules>"""

# Fallback questions when LLM is unavailable
FALLBACK_QUESTIONS = [
    {
        "id": "q1",
        "priority": "P0",
        "category": "target_customer",
        "question": "Who is your primary target customer? Please describe their demographics, behaviors, and key characteristics.",
        "why_needed": "Essential for customer segments and value proposition targeting",
        "required": True
    },
    {
        "id": "q2",
        "priority": "P0",
        "category": "problem",
        "question": "What is the core problem you're solving? How painful is this problem for your target customers?",
        "why_needed": "Fundamental to value proposition and product-market fit",
        "required": True
    },
    {
        "id": "q3",
        "priority": "P0",
        "category": "solution",
        "question": "How does your solution address this problem? What is your core product or service concept?",
        "why_needed": "Required for VPS and BMC solution components",
        "required": True
    },
    {
        "id": "q4",
        "priority": "P0",
        "category": "differentiation",
        "question": "What makes your solution different from existing alternatives? What is your unique advantage?",
        "why_needed": "Critical for competitive positioning in BMC",
        "required": True
    },
    {
        "id": "q5",
        "priority": "P0",
        "category": "revenue",
        "question": "How do you plan to make money? What is your initial pricing or revenue model hypothesis?",
        "why_needed": "Required for revenue streams in BMC",
        "required": True
    },
    {
        "id": "q6",
        "priority": "P1",
        "category": "market_scope",
        "question": "What is your initial target market geography? Are you starting local, regional, or global?",
        "why_needed": "Required to scope market research and competitive analysis",
        "required": False
    }
]


class QuestionGeneratorService:
    """
    Service for generating prioritized clarifying questions using LLM.
    
    Uses dynamic prompt templates to generate contextual questions
    based on the specific business idea content provided.
    """
    
    def __init__(self):
        """Initialize question generator."""
        self._init_services()
        logger.info("Question Generator Service initialized")
    
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
                llm_kwargs["max_tokens"] = 2000
            
            llm_config = LLMConfig(**llm_kwargs)
            
            self.openai_provider = OpenAIProvider(config=llm_config)
            self.model_name = model_name
            logger.info(f"✅ OpenAI provider initialized with model: {model_name}, azure_endpoint: {bool(client_config.get('azure_endpoint'))}")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI provider: {e}")
    
    async def generate_questions(
        self,
        project_id: str,
        tenant_id: str,
        intake_content: str = "",
        max_questions: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Generate clarifying questions using LLM with dynamic prompt templates.
        
        This is the PRIMARY method - uses LLM for contextual, dynamic questions.
        Falls back to static questions only if LLM is unavailable.
        
        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            intake_content: The user's business idea text and extracted PDF content
            max_questions: Maximum number of questions to generate
            
        Returns:
            List of question objects with priority and category
        """
        logger.info(f"🔍 Generating questions for project {project_id}")
        
        # If no intake content provided, try to retrieve from embeddings
        if not intake_content and self.embedding_service:
            intake_content = await self._retrieve_intake_content(project_id, tenant_id)
        
        # Try LLM-based generation first (primary approach)
        if intake_content and self.openai_provider:
            try:
                questions = await self._generate_with_llm(intake_content, max_questions)
                if questions:
                    logger.info(f"✅ Generated {len(questions)} dynamic questions via LLM")
                    return questions
            except Exception as e:
                logger.warning(f"LLM question generation failed: {e}, using fallback")
        
        # Fallback to static questions
        logger.info(f"Using fallback static questions")
        return self._get_fallback_questions(max_questions)
    
    async def _retrieve_intake_content(
        self,
        project_id: str,
        tenant_id: str
    ) -> str:
        """
        Retrieve intake content from embedded chunks.
        """
        try:
            if not self.embedding_service:
                return ""
            
            # Retrieve all content chunks for this project
            results = await self.embedding_service.retrieve(
                project_id=project_id,
                tenant_id=tenant_id,
                query="business idea problem solution customer",
                top_k=10
            )
            
            if results:
                # Combine chunk contents
                content_parts = [r.get("content", "") for r in results if r.get("content")]
                return "\n\n".join(content_parts)
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error retrieving intake content: {e}")
            return ""
    
    async def _generate_with_llm(
        self,
        intake_content: str,
        max_questions: int
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using LLM with prompt templates.
        """
        # Build the user prompt
        user_prompt = QUESTION_GENERATION_USER_PROMPT.format(
            intake_content=intake_content[:4000],  # Limit to avoid token overflow
            max_questions=max_questions
        )
        
        response_text = None
        
        # Use OpenAI provider (Azure OpenAI)
        if self.openai_provider:
            try:
                messages = [
                    {"role": "system", "content": QUESTION_GENERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
                
                response = await self.openai_provider.generate_responses(messages)
                # Handle both dict and LLMResponse object formats
                if isinstance(response, dict):
                    response_text = response.get("content", "")
                elif hasattr(response, 'content'):
                    response_text = response.content  # LLMResponse object
                else:
                    response_text = str(response)
                logger.info(f"✅ LLM generated response: {len(response_text)} chars")
            except Exception as e:
                logger.warning(f"OpenAI provider failed: {e}")
        
        if not response_text:
            return []
        
        # Parse the JSON response
        return self._parse_llm_response(response_text, max_questions)
    
    def _parse_llm_response(
        self,
        response_text: str,
        max_questions: int
    ) -> List[Dict[str, Any]]:
        """
        Parse LLM response and extract questions.
        Handles markdown code blocks, single quotes, and other common LLM output formats.
        """
        import re
        
        try:
            # Clean the response text
            cleaned = response_text.strip()
            
            # Log raw response for debugging
            logger.info(f"🔍 Raw response (first 300): {response_text[:300]}")
            
            # Remove markdown code blocks (```json ... ``` or ``` ... ```)
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = cleaned.strip()
            
            # Log cleaned response for debugging
            logger.info(f"🔍 Cleaned response (first 300): {cleaned[:300]}")
            
            questions = []
            
            # Try to parse as complete JSON object first
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict) and "questions" in data:
                    questions = data["questions"]
                    logger.info(f"📊 Content analysis: {data.get('content_analysis', {})}")
                elif isinstance(data, list):
                    questions = data
            except json.JSONDecodeError:
                # Try to extract JSON object containing questions
                json_match = re.search(r'\{[\s\S]*"questions"\s*:\s*\[[\s\S]*\]\s*\}', cleaned)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        questions = data.get("questions", [])
                    except json.JSONDecodeError:
                        pass
                
                # If still no questions, try to find just the array
                if not questions:
                    array_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', cleaned)
                    if array_match:
                        try:
                            questions = json.loads(array_match.group())
                        except json.JSONDecodeError:
                            pass
            
            if not questions:
                logger.warning(f"Could not parse questions from response")
                return []
            
            # Validate and normalize questions
            validated = []
            for i, q in enumerate(questions[:max_questions]):
                if isinstance(q, dict) and q.get("question"):
                    validated.append({
                        "id": q.get("id", f"q{i+1}"),
                        "priority": q.get("priority", "P0"),
                        "category": q.get("category", "general"),
                        "question": q.get("question", ""),
                        "why_needed": q.get("why_needed", q.get("context", "")),
                        "required": q.get("required", q.get("priority") == "P0")
                    })
            
            logger.info(f"✅ Parsed {len(validated)} questions from LLM response")
            return validated
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return []
    
    def _get_fallback_questions(self, max_questions: int) -> List[Dict[str, Any]]:
        """Return static fallback questions when LLM is unavailable."""
        return FALLBACK_QUESTIONS[:max_questions]


def get_question_generator_service() -> QuestionGeneratorService:
    """Factory function for QuestionGeneratorService."""
    return QuestionGeneratorService()
