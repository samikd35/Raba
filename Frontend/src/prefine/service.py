"""
Idea Refinement Service

This service provides the core functionality for transforming raw ideas into
clear, testable problem statements using Azure OpenAI gpt-5-mini.

USES CENTRALIZED RESPONSES API (Dec 2025):
- Uses OpenAIProvider.generate_responses() from src/mint/api/ai/providers.py
- Leverages reasoning={"effort": "minimal"} and text={"verbosity": "low"} for grounded output
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.mint.api.ai.models import (
    ModelUseCase, 
    ModelProvider
)
from src.mint.api.ai.config import (
    get_client_config, 
    get_provider_with_fallback
)
from src.mint.api.ai.providers import OpenAIProvider, LLMConfig as ProviderLLMConfig
from src.mint.api.ai.models import LLMConfig, LLMResponse

from .models import (
    ParsedContext,
    ProblemStatement,
    ProblemStatementsOutput,
    RefinedVariants,
    IdeaRefinementResponse,
    InterviewQuestion,
    ValidationCue,
    ProblemScore,
    EnhancedRefinementResponse
)
from .database_service import ProblemRefinerDatabaseService

# Import AI token monitoring
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


class IdeaRefinementService:
    """Service for refining raw ideas into problem statements.
    
    USES CENTRALIZED RESPONSES API:
    Uses OpenAIProvider.generate_responses() with reasoning.effort and text.verbosity
    for factually grounded, concise outputs.
    """
    
    def __init__(self):
        """Initialize the idea refinement service."""
        self._provider = None
        self._provider_type = None
        self._model_name = None
        self.db_service = ProblemRefinerDatabaseService(use_service_role=True)
        
    @property
    def provider(self) -> OpenAIProvider:
        """Get the OpenAI provider instance configured for Responses API."""
        if self._provider is None:
            # Use Azure OpenAI GPT-4.1 for idea refinement (heavy processing)
            provider_type = get_provider_with_fallback()
            provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION, provider_type)
            
            # Store for monitoring
            self._provider_type = provider_type
            self._model_name = model_name
            
            if provider_type == ModelProvider.AZURE_OPENAI:
                logger.info(f"Using Azure OpenAI gpt-5-mini for idea refinement (model: {model_name})")
                llm_config = LLMConfig(
                    model_name=model_name,  # This is the deployment name for Azure
                    temperature=0.7,
                    max_tokens=16000,  # gpt-5-mini needs large token budget
                    azure_endpoint=client_config.get("azure_endpoint"),
                    api_version=client_config.get("api_version"),
                    api_key=client_config.get("api_key")
                )
            else:
                logger.info("Using OpenAI GPT-4.1 for idea refinement")
                llm_config = LLMConfig(
                    model_name=model_name,  # This is the model name for OpenAI
                    temperature=0.7,
                    max_tokens=16000,  # gpt-5-mini needs large token budget
                    api_key=client_config.get("api_key")
                )
            
            # Convert to the provider's expected config format
            provider_config = ProviderLLMConfig(
                provider_type="llm",
                provider_name="openai",  # Required field
                api_key_env_var="AZURE_OPENAI_API_KEY" if hasattr(llm_config, 'azure_endpoint') and llm_config.azure_endpoint else "OPENAI_API_KEY",
                model_name=llm_config.model_name,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                api_key=llm_config.api_key,  # Direct API key for immediate use
                azure_endpoint=getattr(llm_config, 'azure_endpoint', None),
                api_version=getattr(llm_config, 'api_version', None)
            )
            
            self._provider = OpenAIProvider(provider_config)
        
        return self._provider

    async def parse_context(self, raw_idea: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> ParsedContext:
        """Parse context from a raw idea."""
        system_prompt = """<role>
You are an expert business analyst specializing in parsing raw business ideas into structured context.
</role>

<task>
Extract 5 key context elements from a raw business idea:
1. **Persona**: The specific type of person with this idea (e.g., "first-time founder with technical background", "experienced restaurateur")
2. **Industry**: The specific industry or domain (e.g., "B2B SaaS for healthcare", "consumer fintech")
3. **Geography**: The target market or location (e.g., "East Africa urban markets", "US enterprise")
4. **Delivery Mode**: How the solution would reach users (e.g., "mobile app", "API service", "physical product")
5. **Assumptions**: 3 key assumptions embedded in the idea
</task>

<inference_rules>
- If persona is unclear: Infer from language style, problem domain, and implied expertise level
- If industry is unclear: Identify from the problem space and stakeholders mentioned
- If geography is unclear: Default to "Global" only if truly location-agnostic; otherwise infer from context clues (currency, regulations, cultural references)
- If delivery mode is unclear: Infer from the nature of the problem and target users
- For assumptions: Extract implicit beliefs about market, technology, or user behavior
</inference_rules>

<output_format>
Respond with ONLY valid JSON. No markdown, no explanation.
</output_format>"""

        user_prompt = f"""<input>
{raw_idea}
</input>

<output_schema>
{{
    "persona": "[specific persona with context]",
    "industry": "[specific industry/domain]",
    "geography": "[specific market or region]",
    "delivery_mode": "[specific delivery mechanism]",
    "assumptions": ["[assumption 1]", "[assumption 2]", "[assumption 3]"]
}}
</output_schema>"""

        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_id="idea_refiner_refinement",
            workflow_name="idea_refinement_workflow",
            step_name="parse_context",
            environment="prod"
        )
        
        started_at = datetime.utcnow()
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            # MIGRATED TO RESPONSES API: Uses reasoning.effort and text.verbosity
            response = await self.provider.generate_responses(messages)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
            monitoring = get_monitoring_service()
            usage = response.usage or {}
            actual_model = response.model or self._model_name or "unknown"
            actual_provider = "azure_openai" if self._provider_type == ModelProvider.AZURE_OPENAI else "openai"
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider=actual_provider,
                    model_name=actual_model,
                    operation_type="responses_api",  # Updated from chat_completion
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens')
                )
            )
            
            # Parse JSON response
            import json
            content = response.content
            if not content:
                raise ValueError("LLM returned empty content")
            parsed_data = json.loads(content)
            return ParsedContext(**parsed_data)
            
        except Exception as e:
            finished_at = datetime.utcnow()
            logger.error(f"Error parsing context: {str(e)}")
            
            # Record error (fire-and-forget)
            monitoring = get_monitoring_service()
            actual_provider = "azure_openai" if self._provider_type == ModelProvider.AZURE_OPENAI else "openai"
            actual_model = self._model_name or 'unknown'
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider=actual_provider,
                    model_name=actual_model,
                    operation_type="responses_api",
                    started_at=started_at,
                    finished_at=finished_at,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            # TESTING: Raise error instead of fallback to see actual error
            raise
            # # Return default context if parsing fails
            # return ParsedContext(
            #     persona="Entrepreneur",
            #     industry="General",
            #     geography="Global",
            #     delivery_mode="Digital platform",
            #     assumptions=["Market demand exists", "Technical feasibility", "Resource availability"]
            # )

    async def generate_problem_statements(self, raw_idea: str, context: ParsedContext, user_id: Optional[str] = None, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> ProblemStatementsOutput:
        """Generate problem statements from raw idea and context."""
        system_prompt = """<role>
You are an expert problem statement generator who transforms raw business ideas into clear, testable problem statements in CAUSE-AND-EFFECT format.
</role>

<mandatory_format>
Every problem statement MUST follow the CAUSE-AND-EFFECT pattern:
"[CAUSE/Root Problem] is [EFFECT VERB] [WHO/Stakeholder] from [BLOCKED OUTCOME/Consequence]."

Effect verbs to use: "preventing", "forcing", "causing", "blocking", "leaving"
</mandatory_format>

<examples>
✅ CORRECT (cause-and-effect, concise):
- "The lack of affordable diapers with acceptable standards is preventing Kenyan urban parents from maintaining their babies' proper hygiene."
- "Ethiopian university graduates' inability to meet global standards is preventing them from competing in the international job market."
- "The ambulance's long response time more than triples the amount of preventable deaths in Lagos."
- "The absence of real-time weather data is preventing Kenyan smallholder farmers from optimizing their planting dates."

❌ WRONG (too long, verbose, not cause-effect):
- "Rainfed smallholder maize and bean farmers in western and central Kenya owning 0.5-2 hectares struggle to decide the optimal planting date because they lack timely information..." → TOO LONG
- "Farmers face challenges with weather prediction" → Missing cause-effect structure
</examples>

<quality_criteria>
1. **Concise**: Maximum 150 characters - one clear sentence
2. **Cause-Effect Structure**: Must show WHAT causes WHAT outcome
3. **Specific Stakeholder**: Name a concrete group with geography
4. **Solution-Agnostic**: Zero mention of solutions or technologies
5. **Testable**: Can be validated through interviews
</quality_criteria>

<assumptions_extraction>
For each problem, extract 4 testable assumptions:
- One about the stakeholder (who they are, how many exist)
- One about the problem frequency (how often it occurs)
- One about the problem severity (how painful it is)
- One about current alternatives (what they do today)
</assumptions_extraction>

<output_rules>
- Generate exactly 3-5 DISTINCT problem statements
- Each statement MUST be under 150 characters
- Each MUST follow cause-and-effect format
- Respond with ONLY valid JSON. No markdown, no explanation.
</output_rules>"""

        user_prompt = f"""<raw_idea>
{raw_idea}
</raw_idea>

<context>
- Persona: {context.persona}
- Industry: {context.industry}
- Geography: {context.geography}
- Delivery Mode: {context.delivery_mode}
</context>

<cause_effect_reminder>
EVERY statement MUST follow this pattern:
"[CAUSE] is [preventing/forcing/causing] [WHO in {context.geography}] from [OUTCOME]"

Example for this context:
"The lack of [X] is preventing {context.geography} [stakeholders] from [achieving Y]."
</cause_effect_reminder>

<output_schema>
{{
    "problem_statements": [
        {{
            "stakeholder": "[specific group in {context.geography}]",
            "statement": "[CAUSE-AND-EFFECT statement under 150 chars]",
            "assumptions": ["[stakeholder assumption]", "[frequency assumption]", "[severity assumption]", "[alternatives assumption]"]
        }}
    ]
}}
</output_schema>"""

        # Create monitoring context
        monitoring_context = AIUsageContext(
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_id="idea_refiner_refinement",
            workflow_name="idea_refinement_workflow",
            step_name="generate_problem_statements",
            environment="prod"
        )
        
        started_at = datetime.utcnow()

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            # MIGRATED TO RESPONSES API: Uses reasoning.effort and text.verbosity
            response = await self.provider.generate_responses(messages)
            
            finished_at = datetime.utcnow()
            
            # Record AI usage (fire-and-forget)
            monitoring = get_monitoring_service()
            usage = response.usage or {}
            actual_model = response.model or self._model_name or "unknown"
            actual_provider = "azure_openai" if self._provider_type == ModelProvider.AZURE_OPENAI else "openai"
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider=actual_provider,
                    model_name=actual_model,
                    operation_type="responses_api",  # Updated from chat_completion
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens')
                )
            )
            
            # Parse JSON response
            import json
            content = response.content
            if not content:
                raise ValueError("LLM returned empty content")
            parsed_data = json.loads(content)
            return ProblemStatementsOutput(**parsed_data)
            
        except Exception as e:
            finished_at = datetime.utcnow()
            logger.error(f"Error generating problem statements: {str(e)}")
            
            # Record error (fire-and-forget)
            monitoring = get_monitoring_service()
            actual_provider = "azure_openai" if self._provider_type == ModelProvider.AZURE_OPENAI else "openai"
            actual_model = self._model_name or 'unknown'
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider=actual_provider,
                    model_name=actual_model,
                    operation_type="responses_api",  # Updated from chat_completion
                    started_at=started_at,
                    finished_at=finished_at,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            raise

    async def score_problems(self, problem_statements: ProblemStatementsOutput, user_id: Optional[str] = None, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> List[ProblemScore]:
        """Score problem statements for clarity, urgency, market size, and testability."""
        system_prompt = """<role>
You are an expert problem evaluator who scores problem statements using standardized criteria for startup validation.
</role>

<scoring_rubric>

**1. Clarity Score (0-10)**
- 9-10: Stakeholder is named specifically; problem is observable and measurable; no ambiguity
- 7-8: Stakeholder is reasonably specific; problem is clear but could be more precise
- 5-6: Some vagueness in stakeholder or problem definition
- 3-4: Significant ambiguity; hard to understand who or what
- 0-2: Unclear who has the problem or what it is

**2. Urgency Score (0-10)**
- 9-10: Hair-on-fire problem; people actively seeking solutions and willing to pay now
- 7-8: Significant pain; people complain about this regularly
- 5-6: Moderate inconvenience; people cope but would prefer a solution
- 3-4: Minor annoyance; low motivation to change
- 0-2: Nice-to-have; no real urgency

**3. Market Size Score (0-10)**
- 9-10: Millions of potential customers; billion-dollar market
- 7-8: Large addressable market; hundreds of thousands affected
- 5-6: Moderate market; tens of thousands affected
- 3-4: Niche market; thousands affected
- 0-2: Very small or unclear market

**4. Testability Score (0-10)**
- 9-10: Can validate in <1 week with 5-10 interviews; clear success criteria
- 7-8: Can validate in 1-2 weeks; stakeholders are accessible
- 5-6: Validation possible but requires more effort or specialized access
- 3-4: Difficult to find stakeholders or design validation
- 0-2: Nearly impossible to validate quickly

**5. Overall Score (0-10)**
Weighted combination: Clarity(20%) + Urgency(30%) + Market(25%) + Testability(25%)
Round to one decimal place.

</scoring_rubric>

<output_rules>
- Be rigorous and differentiate between problems - avoid giving all 7s
- Reasoning must reference specific elements from the problem statement
- Respond with ONLY valid JSON. No markdown, no explanation.
</output_rules>"""

        scores = []
        for problem in problem_statements.problem_statements:
            user_prompt = f"""<problem_to_score>
Stakeholder: {problem.stakeholder}
Statement: {problem.statement}
Assumptions: {', '.join(problem.assumptions)}
</problem_to_score>

<output_schema>
{{
    "clarity_score": [0-10],
    "urgency_score": [0-10],
    "market_size_score": [0-10],
    "testability_score": [0-10],
    "overall_score": [weighted average to 1 decimal],
    "reasoning": "[2-3 sentences citing specific elements from the problem that justify each score]"
}}
</output_schema>"""

            # Create monitoring context
            monitoring_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                project_id=project_id,
                feature_id="idea_refiner_refinement",
                workflow_name="idea_refinement_workflow",
                step_name="score_problems",
                environment="prod"
            )
            
            started_at = datetime.utcnow()

            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                # MIGRATED TO RESPONSES API: Uses reasoning.effort and text.verbosity
                response = await self.provider.generate_responses(messages)
                
                finished_at = datetime.utcnow()
                
                # Record AI usage (fire-and-forget)
                monitoring = get_monitoring_service()
                usage = response.usage or {}
                actual_model = response.model or self._model_name or "unknown"
                actual_provider = "azure_openai" if self._provider_type == ModelProvider.AZURE_OPENAI else "openai"
                asyncio.create_task(
                    monitoring.record_ai_usage(
                        context=monitoring_context,
                        provider=actual_provider,
                        model_name=actual_model,
                        operation_type="responses_api",  # Updated from chat_completion
                        started_at=started_at,
                        finished_at=finished_at,
                        status="success",
                        prompt_tokens=usage.get('prompt_tokens'),
                        completion_tokens=usage.get('completion_tokens'),
                        total_tokens=usage.get('total_tokens')
                    )
                )
                
                import json
                content = response.content
                if not content:
                    raise ValueError("LLM returned empty content")
                parsed_data = json.loads(content)
                scores.append(ProblemScore(**parsed_data))
                
            except Exception as e:
                finished_at = datetime.utcnow()
                logger.error(f"Error scoring problem: {str(e)}")
                
                # Record error (fire-and-forget)
                monitoring = get_monitoring_service()
                actual_provider = "azure_openai" if self._provider_type == ModelProvider.AZURE_OPENAI else "openai"
                actual_model = self._model_name or 'unknown'
                asyncio.create_task(
                    monitoring.record_ai_usage(
                        context=monitoring_context,
                        provider=actual_provider,
                        model_name=actual_model,
                        operation_type="responses_api",  # Updated from chat_completion
                        started_at=started_at,
                        finished_at=finished_at,
                        status="error",
                        error_type=type(e).__name__
                    )
                )
                
                # TESTING: Raise error instead of fallback
                raise
                # # Default score if scoring fails
                # scores.append(ProblemScore(
                #     clarity_score=7.0,
                #     urgency_score=7.0,
                #     market_size_score=7.0,
                #     testability_score=7.0,
                #     overall_score=7.0,
                #     reasoning="Default scoring due to processing error"
                # ))
        
        return scores

    async def generate_interview_questions(self, problem_statements: ProblemStatementsOutput, user_id: Optional[str] = None, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> List[InterviewQuestion]:
        """Generate interview questions to validate the problems."""
        system_prompt = """<role>
You are an expert customer development interviewer trained in "The Mom Test" methodology. You generate questions that extract honest, actionable insights.
</role>

<question_principles>
1. **Past Behavior Only**: Ask about specific past events, never hypotheticals ("Would you..." → "Tell me about the last time you...")
2. **Open-Ended**: Questions should invite stories, not yes/no answers
3. **Solution-Blind**: Zero mention of any solution, product, or feature
4. **Pain-Focused**: Dig into consequences, workarounds, and emotional impact
5. **Commitment-Seeking**: End with questions that test willingness to act
</question_principles>

<question_types>
Generate a mix of these question types:
- **Context Questions**: Understand their world and workflow
- **Problem Discovery**: Uncover if/how they experience the problem
- **Frequency/Severity**: Quantify how often and how painful
- **Current Solutions**: What do they do today? What have they tried?
- **Commitment**: Would they pay? Refer others? Spend time on a call?
</question_types>

<follow_up_strategy>
Each question should have 2-3 follow-ups that:
- Go deeper on specifics ("Can you walk me through exactly what happened?")
- Quantify impact ("How much time/money did that cost you?")
- Test severity ("What would happen if you couldn't solve this?")
</follow_up_strategy>

<output_rules>
- Generate exactly 5-7 questions
- Each question must map to a specific validation purpose
- Respond with ONLY valid JSON. No markdown, no explanation.
</output_rules>"""

        problems_text = "\n".join([
            f"- {p.stakeholder}: {p.statement}" 
            for p in problem_statements.problem_statements
        ])

        user_prompt = f"""<problems_to_validate>
{problems_text}
</problems_to_validate>

<output_schema>
{{
    "questions": [
        {{
            "question": "[open-ended question about past behavior]",
            "purpose": "[what this validates: frequency/severity/alternatives/commitment]",
            "follow_up_prompts": ["[dig deeper]", "[quantify impact]", "[test severity]"]
        }}
    ]
}}
</output_schema>"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            # MIGRATED TO RESPONSES API: Uses reasoning.effort and text.verbosity
            response = await self.provider.generate_responses(messages)
            
            import json
            content = response.content
            if not content:
                raise ValueError("LLM returned empty content")
            parsed_data = json.loads(content)
            return [InterviewQuestion(**q) for q in parsed_data["questions"]]
            
        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            # TESTING: Raise error instead of fallback
            raise
            # return [
            #     InterviewQuestion(
            #         question="Tell me about challenges you face in this area",
            #         purpose="Understand problem context",
            #         follow_up_prompts=["How do you currently handle this?", "How often does this occur?"]
            #     )
            # ]

    async def generate_validation_cues(self, problem_statements: ProblemStatementsOutput, user_id: Optional[str] = None, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> List[ValidationCue]:
        """Generate validation cues for testing the problems."""
        system_prompt = """<role>
You are an expert lean startup advisor specializing in rapid, low-cost problem validation experiments.
</role>

<validation_principles>
1. **Behavior Over Opinion**: Test what people DO, not what they SAY they would do
2. **Speed**: Each experiment should take <2 weeks to run
3. **Cost**: Each experiment should cost <$500 (ideally $0-100)
4. **Binary Outcome**: Success criteria must be measurable and unambiguous
5. **Learning-Focused**: Even "failure" should teach something actionable
</validation_principles>

<experiment_types>
Generate a mix of these validation approaches:
- **Smoke Test**: Landing page, fake door test, or waitlist to gauge demand
- **Concierge**: Manually deliver the solution to 5-10 people
- **Interview Blitz**: 10+ problem interviews in 1 week
- **Observation**: Shadow or observe stakeholders in their natural environment
- **Competitor Analysis**: Analyze reviews/complaints about existing solutions
- **Community Probe**: Post in relevant forums/groups to gauge response
</experiment_types>

<success_criteria_guidelines>
Criteria must be:
- Quantified ("20%+ signup rate", not "good engagement")
- Time-bound ("within 1 week")
- Comparable to benchmarks where possible
- Tied to a clear go/no-go decision
</success_criteria_guidelines>

<output_rules>
- Generate exactly 4-6 validation experiments
- Each must be achievable by a solo founder with limited resources
- Order from fastest/cheapest to more involved
- Respond with ONLY valid JSON. No markdown, no explanation.
</output_rules>"""

        problems_text = "\n".join([
            f"- {p.stakeholder}: {p.statement}" 
            for p in problem_statements.problem_statements
        ])

        user_prompt = f"""<problems_to_validate>
{problems_text}
</problems_to_validate>

<output_schema>
{{
    "cues": [
        {{
            "cue": "[specific experiment name]",
            "method": "[step-by-step execution plan in 2-3 sentences]",
            "success_criteria": "[quantified threshold that signals problem is validated]"
        }}
    ]
}}
</output_schema>"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            # MIGRATED TO RESPONSES API: Uses reasoning.effort and text.verbosity
            response = await self.provider.generate_responses(messages)
            
            import json
            content = response.content
            if not content:
                raise ValueError("LLM returned empty content")
            parsed_data = json.loads(content)
            return [ValidationCue(**c) for c in parsed_data["cues"]]
            
        except Exception as e:
            logger.error(f"Error generating validation cues: {str(e)}")
            # TESTING: Raise error instead of fallback
            raise
            # return [
            #     ValidationCue(
            #         cue="Conduct customer interviews",
            #         method="Interview 10-15 potential customers about their challenges",
            #         success_criteria="80%+ confirm this is a significant problem"
            #     )
            # ]

    async def refine_idea_complete(self, raw_idea: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> EnhancedRefinementResponse:
        """Complete idea refinement workflow with scoring only.
        
        Args:
            raw_idea: The raw idea text to refine
            user_id: User ID for session tracking
            tenant_id: Tenant ID for AI usage monitoring
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())
        
        logger.info(f"Starting idea refinement for session {session_id}")
        
        try:
            # Step 1: Create database session if user_id provided
            session_data = None
            if user_id:
                logger.info(f"Creating database session for user_id: {user_id}")
                session_title = self.db_service.generate_session_title(raw_idea)
                logger.info(f"Generated session title: {session_title}")
                
                session_data = self.db_service.create_refiner_session(
                    user_id=uuid.UUID(user_id),
                    session_title=session_title,
                    original_idea=raw_idea
                )
                
                if session_data:
                    session_id = session_data['id']  # Fixed: use 'id' not 'session_id'
                    logger.info(f"✅ Successfully created database session {session_id}")
                    logger.info(f"Session data keys: {list(session_data.keys())}")
                else:
                    logger.error(f"❌ Failed to create database session for user {user_id}")
                    logger.error("Continuing with in-memory session only")
            else:
                logger.info("No user_id provided, skipping database session creation")
            
            # Step 2: Parse context
            logger.info("Parsing context from raw idea")
            context = await self.parse_context(raw_idea, user_id=user_id, tenant_id=tenant_id, project_id=None)
            
            # Step 3: Generate problem statements
            logger.info("Generating problem statements")
            problem_statements = await self.generate_problem_statements(raw_idea, context, user_id=user_id, tenant_id=tenant_id, project_id=None)
            
            # Step 4: Score problems
            logger.info("Scoring problem statements")
            problem_scores = await self.score_problems(problem_statements, user_id=user_id, tenant_id=tenant_id, project_id=None)
            
            processing_time = time.time() - start_time
            
            # Step 5: Save results to database (session should already exist)
            if user_id and session_data:
                try:
                    # Convert problem statements to dict format for database
                    problem_statements_dict = []
                    for i, stmt in enumerate(problem_statements.problem_statements):
                        stmt_dict = {
                            "stakeholder": stmt.stakeholder,
                            "statement": stmt.statement,
                            "assumptions": stmt.assumptions,
                            "overall_score": problem_scores[i].overall_score if i < len(problem_scores) else 0.0
                        }
                        problem_statements_dict.append(stmt_dict)
                    
                    # Save all results to the session (single table)
                    results_data = {
                        "problem_statements": problem_statements_dict,
                        "problem_scores": problem_scores_list if 'problem_scores_list' in locals() else None,
                        "interview_questions": interview_questions_list if 'interview_questions_list' in locals() else None,
                        "validation_cues": validation_cues_list if 'validation_cues_list' in locals() else None
                    }
                    
                    results_saved = self.db_service.save_refiner_results(
                            session_id=session_id,
                            user_id=uuid.UUID(user_id),
                            results_data=results_data
                        )
                        
                    if results_saved:
                            logger.info(f"Saved {len(problem_statements.problem_statements)} refiner results for session {session_id}")
                            
                            # Session is already updated with results and status in save_refiner_results
                            # Just update processing time
                            self.db_service.update_refiner_session(
                                session_id=session_id,
                                user_id=uuid.UUID(user_id),
                                updates={
                                    "processing_time_seconds": processing_time
                                }
                            )
                            
                            # Analytics are stored in the session metadata
                            analytics_metadata = {
                                "idea_length": len(raw_idea),
                                "problems_generated": len(problem_statements_dict),
                                "average_score": sum(p.get('overall_score', 0) for p in problem_statements_dict if p.get('overall_score')) / len(problem_statements_dict) if problem_statements_dict else 0
                            }
                            
                            self.db_service.update_refiner_session(
                                session_id=session_id,
                                user_id=uuid.UUID(user_id),
                                updates={
                                    "metadata": analytics_metadata
                                }
                            )
                            
                            logger.info(f"Saved refiner session {session_id} to database")
                    else:
                            logger.error(f"Failed to save refiner results for session {session_id}")
                            
                except Exception as db_error:
                        logger.error(f"Database error saving session {session_id}: {str(db_error)}")
                        # Mark session as failed (using problem generator pattern)
                        try:
                            self.db_service.update_refiner_session(
                                session_id=session_id,
                                user_id=uuid.UUID(user_id),
                                updates={
                                    "status": "failed",
                                    "generation_success": False,
                                    "error_occurred": True,
                                    "error_message": str(db_error)
                                }
                            )
                        except Exception as update_error:
                            logger.error(f"Failed to mark session {session_id} as failed: {str(update_error)}")
            
            logger.info(f"Idea refinement completed in {processing_time:.2f} seconds")
            
            return EnhancedRefinementResponse(
                session_id=session_id,
                parsed_context=context,
                problem_statements=problem_statements,
                problem_scores=problem_scores,
                interview_questions=[],  # Empty list - no interview questions generated
                validation_cues=[],  # Empty list - no validation cues generated
                original_idea=raw_idea,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error in complete idea refinement: {str(e)}")
            # Mark session as failed if it was created (using problem generator pattern)
            if user_id and session_data:
                self.db_service.update_refiner_session(
                    session_id=session_id,
                    user_id=uuid.UUID(user_id),
                    updates={
                        "status": "failed",
                        "generation_success": False,
                        "error_occurred": True,
                        "error_message": str(e)
                    }
                )
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the idea refinement service.
        
        Returns:
            Dict containing health status and details
        """
        try:
            # Test Responses API connectivity
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'OK' if you can respond."}
            ]
            
            # MIGRATED TO RESPONSES API: Uses reasoning.effort and text.verbosity
            response = await self.provider.generate_responses(test_messages)
            
            if response and response.content:
                return {
                    "healthy": True,
                    "ai_provider": "available (Responses API)",
                    "database": "available",
                    "last_check": datetime.now().isoformat(),
                    "response_time_ms": 0  # Could add timing if needed
                }
            else:
                return {
                    "healthy": False,
                    "ai_provider": "unavailable",
                    "database": "available",
                    "last_check": datetime.now().isoformat(),
                    "error": "AI provider not responding"
                }
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "healthy": False,
                "ai_provider": "error",
                "database": "unknown",
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }

    async def refine_idea(self, request, tenant_id: Optional[str] = None) -> EnhancedRefinementResponse:
        """
        Main refine_idea method that the router expects.
        This is a wrapper around refine_idea_complete for compatibility.
        
        Args:
            request: IdeaRefinementRequest object
            tenant_id: Tenant ID for AI usage monitoring
            
        Returns:
            EnhancedRefinementResponse with refinement results
        """
        return await self.refine_idea_complete(
            raw_idea=request.raw_idea,
            user_id=request.user_id,
            tenant_id=tenant_id
        )

