

import json
import logging
import time
import asyncio
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, List

from pydantic import BaseModel, Field

from src.mint.api.ai.providers import OpenAIProvider
from src.mint.api.ai.models import LLMConfig
from src.mint.api.ai.providers import LLMToolResponse
# Using standard dictionary instead of GraphState
from src.mint.agents.agent_config import get_agent_config, get_llm_config
from src.mint.api.ai.models import (
    ModelProvider,
    ModelUseCase
)
from src.mint.api.ai.config import (
    get_client_config,
    get_provider_with_fallback
)
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

# DISABLED: LangSmith causes memory issues with large payloads (61MB+)
# from langsmith.run_helpers import traceable
def traceable(name=None):
    def decorator(func):
        return func
    return decorator

logger = logging.getLogger(__name__)

class ClarificationResult(BaseModel):
    """Schema for the output of the clarification agent."""
    has_clear_problem: bool = Field(
        ...,
        description="Whether the query contains a clear problem statement"
    )
    has_geography: bool = Field(
        ...,
        description="Whether the query specifies geographic regions"
    )
    has_industry: bool = Field(
        ...,
        description="Whether the query specifies an industry or market"
    )
    questions: List[str] = Field(
        ...,
        min_items=0,
        max_items=3,
        description="List of clarification questions (max 3)"
    )

# System prompt template
CLARIFICATION_SYSTEM_PROMPT = """
<role>
You are an expert business analyst specializing in African markets and emerging economies. You help entrepreneurs validate market problems through clarifying questions.
</role>

<task>
Analyze the user's query and assess the presence of key elements, then generate clarifying questions.
</task>

<assessment_criteria>
Determine if the query contains:
1. **Problem Statement**: Is there a clear, specific problem being addressed?
2. **Geographic Focus**: Is a country, region, or market location specified?
3. **Industry Context**: Is the industry, sector, or market defined?
</assessment_criteria>

<question_generation_rules>
Priority order for questions (ask about what's missing first):
1. Problem scope and specifics
2. Geography (emphasize African contexts when relevant)
3. Industry context

If all elements are clear, ask about:
- Target market specifics
- User pain points
- Existing alternatives
- Timeline
</question_generation_rules>

<question_guidelines>
- Maximum 20 words per question
- Simple, clear language
- Focus on understanding the problem space
- Generate 1-3 questions
</question_guidelines>

<output_schema>
{{
  "has_clear_problem": [true|false],
  "has_geography": [true|false],
  "has_industry": [true|false],
  "questions": ["question 1", "question 2", "question 3"]
}}
</output_schema>
"""

# User prompt template
CLARIFICATION_USER_PROMPT = """
<query>
{initial_query}
</query>

<instructions>
1. Assess presence of: problem statement, geography, industry
2. Generate 1-3 clarifying questions based on what's missing
3. Return JSON per the output schema
</instructions>
"""


@traceable(name="run_clarification")
def run_clarification(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Starting clarification generation")
    
    start_time = time.time()
    
    agent_config = get_agent_config(state, "clarifier")
    enabled = agent_config.get("enabled", True)
    
    logger.info(f"Clarifier agent config: enabled={enabled}")
    
    if not enabled:
        logger.info("Clarifier agent is disabled in config, skipping clarification")
        raise ValueError("Clarifier agent is required and cannot be disabled")
    
    # Prepare inputs
    # Get the query from initial_query or from input_config if available
    initial_query = state.get("initial_query", "")
    if not initial_query and "input_config" in state:
        initial_query = state["input_config"].get("original_question", "")
    
    if not initial_query:
        logger.error("No initial query found in state")
        raise ValueError("Initial query is required")
    
    # Format messages for chat completion
    messages = [
        {"role": "system", "content": CLARIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": CLARIFICATION_USER_PROMPT.format(initial_query=initial_query)}
    ]
    
    # Get LLM configuration from state or global config
    llm_config_dict = get_llm_config(state)
    
    # Use centralized Azure OpenAI configuration for chat completion
    # Clarifier uses CHAT_COMPLETION use case which maps to gpt-4.1-mini deployment
    provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
    
    # Get legacy config for temperature and max_tokens if available
    temperature = 0.2
    max_tokens = None
    
    # Create LLMConfig with proper Azure/OpenAI configuration
    # CRITICAL: Must pass client_config to provider for Azure to work!
    logger.info(f"Clarifier using {provider_type} with model: {model_name} for chat completion")
    
    # Build LLMConfig with the correct provider settings and base_url for gpt-5-mini
    llm_config = LLMConfig(
        provider_name=provider_type.value if hasattr(provider_type, 'value') else str(provider_type),
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=client_config.get("api_key"),
        azure_endpoint=client_config.get("azure_endpoint"),
        api_version=client_config.get("api_version"),
        base_url=client_config.get("base_url")  # For gpt-5-mini pattern
    )
    
    # Initialize the OpenAI provider with proper config (supports both Azure and OpenAI)
    openai_provider = OpenAIProvider(config=llm_config)
    logger.info(f"Provider initialized with gpt-5-mini base_url: {bool(llm_config.base_url)}")
    
    # Clarification can be slow - run in a separate thread to allow proper async handling
    def run_async_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(generate_clarification_with_provider(messages, openai_provider, model_name, temperature, max_tokens))
        finally:
            loop.close()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_async_in_thread)
        clarification_result = future.result()
    
    state["clarification"] = clarification_result.model_dump()
    
    user_question = state.get("initial_query") or state.get("question") or "your research topic"
    current_questions = clarification_result.questions if clarification_result.questions else []
    
    # Always ensure we have exactly 3 questions
    if len(current_questions) != 3:
        logger.info("Adjusting questions to ensure exactly 3 are provided")
        
        if len(current_questions) < 3:
            # Add default questions if we have fewer than 3
            default_questions = [
                f"What specific aspects of {user_question} are you most interested in researching?",
                "Which geographic regions or countries should this research focus on?", 
                "What timeframe should the research cover?"
            ]
            
            # Add only as many default questions as needed to reach 3
            needed_questions = 3 - len(current_questions)
            clarification_result.questions = current_questions + default_questions[:needed_questions]
        else:
            # Trim to 3 questions if we have more
            clarification_result.questions = current_questions[:3]
            
    # Create structured JSON data with initial query and questions
    # This will be used by the specifier when answers are added
    clarification_data = {
        "initial_query": state.get("initial_query", "") or state.get("question", ""),
        "questions": clarification_result.questions,
        "answers": None,  # Will be populated later when user provides answers
        "timestamp": time.time()
    }
    
    # Store the structured data in state
    state["clarification"] = clarification_data
    
    # Also create a serialized JSON string for easy passing
    state["clarification_json"] = json.dumps({
        "initial_query": clarification_data["initial_query"],
        "questions": clarification_data["questions"],
        "answers": None
    }, indent=2)
    
    # Always use interactive mode
    state["interactive_mode"] = True
    state["awaiting_clarification"] = True
    state["_workflow_paused_for_input"] = True
    state["auto_advance"] = False
    state["_halt_execution_until_answers"] = True
    state["clarification_complete"] = False  # Explicitly mark clarification as incomplete
    
    # Log the questions for debugging
    for i, q in enumerate(clarification_result.questions):
        logger.info(f"Question {i+1}: {q}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Clarification questions generated in {elapsed_time:.2f} seconds")
    logger.info(f"Awaiting answers to complete the clarification process") 
    
    return state


@traceable(name="generate_clarification_with_provider")
async def generate_clarification_with_provider(
    messages: List[Dict[str, str]],
    provider: OpenAIProvider,
    model_name: str,
    temperature: float = 0.2,
    state: Dict[str, Any] = None,
    max_tokens: int = None
) -> ClarificationResult:
    """Generate clarification using the new LLM client service"""
    max_items = 3
    
    clarification_tool = {
        "type": "function",
        "function": {
            "name": "generate_clarification",
            "description": "Generate clarification questions for ambiguous queries",
            "parameters": {
                "type": "object",
                "properties": {
                    "has_clear_problem": {
                        "type": "boolean",
                        "description": "Whether the query contains a clear problem statement"
                    },
                    "has_geography": {
                        "type": "boolean",
                        "description": "Whether the query specifies geographic regions"
                    },
                    "has_industry": {
                        "type": "boolean",
                        "description": "Whether the query specifies an industry or market"
                    },
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"List of clarification questions (1-{max_items} items)",
                        "maxItems": max_items
                    }
                },
                "required": ["has_clear_problem", "has_geography", "has_industry", "questions"]
            }
        }
    }
    
    # Prepare monitoring context
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="mint_clarification",
        workflow_name="mint_workflow",
        step_name="generate_clarification",
        environment="prod"
    )
    
    started_at = datetime.now()
    
    try:
        # Use the OpenAI provider for chat generation
        # Use Responses API for gpt-5-mini
        response = await provider.generate_responses(messages)
        
        finished_at = datetime.now()
        
        # Record AI usage (fire-and-forget)
        usage = getattr(response, 'usage', {}) or {}
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="openai",
                model_name=model_name,
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens')
            )
        )
        
        # Handle both LLMResponse and raw OpenAI response formats
        if hasattr(response, 'choices') and response.choices and response.choices[0].message.tool_calls:
            # Raw OpenAI response format
            tool_call = response.choices[0].message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            
            return ClarificationResult(
                has_clear_problem=function_args.get("has_clear_problem", False),
                has_geography=function_args.get("has_geography", False),
                has_industry=function_args.get("has_industry", False),
                questions=function_args.get("questions", [])
            )
        elif hasattr(response, 'content') and response.content:
            # LLMResponse format - parse JSON content
            try:
                content_data = json.loads(response.content)
                return ClarificationResult(
                    has_clear_problem=content_data.get("has_clear_problem", False),
                    has_geography=content_data.get("has_geography", False),
                    has_industry=content_data.get("has_industry", False),
                    questions=content_data.get("questions", [])
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON content: {response.content}")
                raise ValueError(f"Failed to parse clarification response: {e}")
        else:
            # No recognizable response format - raise error
            logger.error(f"Unrecognized response format from LLM: {response}")
            raise ValueError("LLM returned unrecognized response format")
            
    except Exception as e:
        finished_at = datetime.now()
        
        # Record error (fire-and-forget)
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="openai",
                model_name=model_name,
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                error_type=type(e).__name__
            )
        )
        
        logger.error(f"Error in clarification generation: {e}")
        raise  # Re-raise the exception instead of returning fallback

@traceable(name="generate_clarification")
async def generate_clarification(
    messages: List[Dict[str, str]],
    provider: Any
) -> ClarificationResult:
    max_items = 3
    
    clarification_tool = {
        "type": "function",
        "function": {
            "name": "generate_clarification",
            "description": "Generate clarification questions for ambiguous queries",
            "parameters": {
                "type": "object",
                "properties": {
                    "has_clear_problem": {
                        "type": "boolean",
                        "description": "Whether the query contains a clear problem statement"
                    },
                    "has_geography": {
                        "type": "boolean",
                        "description": "Whether the query specifies geographic regions"
                    },
                    "has_industry": {
                        "type": "boolean",
                        "description": "Whether the query specifies an industry or market"
                    },
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": f"List of clarification questions (1-{max_items} items)",
                        "minItems": 0,
                        "maxItems": max_items
                    }
                },
                "required": ["has_clear_problem", "has_geography", "has_industry", "questions"]
            }
        }
    }
    
    # Use Responses API with tools for gpt-5-mini
    response: LLMToolResponse = await provider.generate_responses_with_tools(messages, [clarification_tool])
    
    if hasattr(response, 'usage') and response.usage:
        logger.info(f"Token usage: {response.usage}")
    
    tool_args = response.arguments
    
    result = ClarificationResult(
        has_clear_problem=tool_args["has_clear_problem"],
        has_geography=tool_args["has_geography"],
        has_industry=tool_args["has_industry"],
        questions=tool_args["questions"][:3]
    )
    
    return result



