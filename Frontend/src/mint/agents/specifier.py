import json
import logging
import re
from typing import Dict, Any, List
import asyncio
import concurrent.futures

from src.mint.providers.factory import get_provider
from src.mint.api.ai.models import LLMConfig, LLMResponse
from src.mint.utils.config import get_llm_config
from src.mint.agents.agent_config import get_agent_config
from src.mint.utils.tracing import traceable
from src.mint.api.ai.models import (
    ModelProvider,
    ModelUseCase
)
from src.mint.api.ai.config import (
    get_client_config,
    get_provider_with_fallback
)

# Configure logging
logger = logging.getLogger(__name__)


@traceable(name="_normalize_user_answers")
def _normalize_user_answers(raw_answers: Dict[str, Any]) -> Dict[str, str]:
    """
    Normalize user answers into a consistent format for the specification agent.
    Supports multiple flexible input formats and standardizes them.
    
    Args:
        raw_answers: User answers in various possible formats
        
    Returns:
        Dict with normalized question keys and answer strings
    """
    logger.debug(f"Normalizing user answers: {raw_answers}")
    
    if not raw_answers:
        logger.warning("No user answers provided to normalize")
        return {}
        
    if isinstance(raw_answers, dict) and all(isinstance(k, str) for k, v in raw_answers.items()):
        normalized_answers = {}
        
        # Process dictionary format answers
        for question_key, answer in raw_answers.items():
            if not isinstance(answer, str):
                answer = str(answer) if answer is not None else ""
                
            answer = _clean_answer_format(answer)
            
            # Always include the original key-value pair
            normalized_answers[question_key] = answer
            
            # Also normalize standard formats like "question_1", "q1", etc.
            if question_key.startswith("question_") and question_key[9:].isdigit():
                q_num = int(question_key[9:])
                normalized_answers[f"q{q_num}"] = answer
                normalized_answers[f"answer_{q_num}"] = answer
            elif question_key.startswith("q") and question_key[1:].isdigit():
                q_num = int(question_key[1:])
                normalized_answers[f"question_{q_num}"] = answer
                normalized_answers[f"answer_{q_num}"] = answer
            
        return normalized_answers
    
    # Handle string format (raw text response)
    if isinstance(raw_answers, str):
        return _parse_paragraph_response(raw_answers)
    
    # Handle list format (ordered answers)
    if isinstance(raw_answers, list):
        normalized_answers = {}
        for i, answer in enumerate(raw_answers):
            if isinstance(answer, dict) and "question" in answer and "answer" in answer:
                # Handle structured format: [{"question": "...", "answer": "..."}]
                q = answer["question"]
                a = _clean_answer_format(str(answer["answer"]))
                normalized_answers[q] = a
                # Also add standardized keys
                normalized_answers[f"question_{i+1}"] = a
                normalized_answers[f"q{i+1}"] = a
            else:
                # Handle simple list of answers
                a = _clean_answer_format(str(answer))
                normalized_answers[f"question_{i+1}"] = a
                normalized_answers[f"q{i+1}"] = a
                normalized_answers[f"answer_{i+1}"] = a
        return normalized_answers
    
    # Fallback for unexpected formats
    if not isinstance(raw_answers, dict):
        logger.warning(f"Unexpected user answer format: {type(raw_answers).__name__}")
        return {"generic_question": str(raw_answers)}
        
    # Fallback for unexpected dictionary format
    logger.debug("Using general dictionary normalization for user answers")
    return {str(k): _clean_answer_format(str(v)) if v is not None else "" for k, v in raw_answers.items()}


def _clean_answer_format(answer: str) -> str:
    answer = answer.strip()
    
    prefixes = ["Answer:", "A:", "Response:", "R:"]
    for prefix in prefixes:
        if answer.startswith(prefix):
            answer = answer[len(prefix):].strip()
            
    return answer.strip()


def _parse_paragraph_response(paragraph: str) -> Dict[str, str]:
    numbered_pattern = re.compile(r'(\d+\.\s*)(.*?)(?=\d+\.\s*|$)', re.DOTALL)
    matches = numbered_pattern.findall(paragraph)
    if matches:
        return {f"question_{num}": _clean_answer_format(answer) 
                for num, answer in matches}
    
    bullet_pattern = re.compile(r'([*\-\•]\s*)(.*?)(?=[*\-\•]\s*|$)', re.DOTALL)
    matches = bullet_pattern.findall(paragraph)
    if matches:
        return {f"question_{i+1}": _clean_answer_format(answer) 
                for i, (_, answer) in enumerate(matches)}
    
    qa_pattern = re.compile(r'(?:Question\s*|Q)(\d+)\s*[:.-]\s*(.*?)(?=(?:Question\s*|Q)\d+\s*[:.-]|$)', re.IGNORECASE | re.DOTALL)
    matches = qa_pattern.findall(paragraph)
    if matches:
        return {f"question_{num}": _clean_answer_format(answer) 
                for num, answer in matches}
    
    result = {}
    
    categories = {
        "geography": ["region", "country", "location", "market", "africa", "global"],
        "industry": ["industry", "sector", "business", "market"],
        "problem": ["problem", "challenge", "issue", "objective", "goal"],
        "timeline": ["time", "period", "duration", "horizon", "year", "month"],
    }
    
    sentences = re.split(r'[.!?]\s+', paragraph)
    
    for category, keywords in categories.items():
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                if category not in result:
                    result[category] = sentence.strip()
                else:
                    result[category] += " " + sentence.strip()
    
    if result:
        return result
    
    return {"generic_answer": paragraph.strip()}


@traceable(name="run_specification")
def run_specification(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the specification agent to generate research specifications based on the
    standardized JSON structure containing initial query, clarification questions, and answers.
    
    1. Process the clarification JSON from the clarifier agent
    2. Generate master specifications using LLM
    3. Generate industry and PESTEL specifications based on master spec
    4. Return all specifications in JSON format
    
    Args:
        state: Current workflow state containing clarification_json
        
    Returns:
        Updated workflow state with master, industry, and PESTEL specifications
    """
    logger.info("Starting specification agent processing")
    
    # Extract clarification JSON from state
    clarification_json_str = state.get("clarification_json")
    if not clarification_json_str:
        logger.error("No clarification_json found in state")
        raise ValueError("Missing clarification_json in workflow state")
    
    # Parse clarification JSON
    try:
        clarification_data = json.loads(clarification_json_str) if isinstance(clarification_json_str, str) else clarification_json_str
        logger.debug(f"Parsed clarification data: {clarification_data}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse clarification JSON: {e}")
        raise ValueError(f"Invalid clarification_json format: {e}")
    
    # Validate clarification data has required fields
    if not isinstance(clarification_data, dict):
        logger.error(f"Clarification data is not a dictionary: {type(clarification_data)}")
        raise ValueError("Clarification data must be a dictionary")
    
    # Extract initial query and answers
    initial_query = clarification_data.get("initial_query")
    if not initial_query:
        logger.error("No initial_query found in clarification data")
        raise ValueError("Missing initial_query in clarification data")
    
    clarification_questions = clarification_data.get("questions", [])
    if not clarification_questions or len(clarification_questions) < 3:
        logger.warning(f"Expected at least 3 clarification questions, got {len(clarification_questions)}")
    
    answers = clarification_data.get("answers", {})
    if not answers:
        logger.error("No answers found in clarification data")
        raise ValueError("Missing answers in clarification data")
    
    # Normalize user answers
    normalized_answers = _normalize_user_answers(answers)
    if not normalized_answers:
        logger.error("Failed to normalize user answers")
        raise ValueError("Could not normalize user answers")
    
    logger.info(f"Processing query: {initial_query} with {len(normalized_answers)} answers")
    
       
    # Use centralized Azure OpenAI configuration for chat completion
    # Specifier uses CHAT_COMPLETION use case which maps to gpt-4.1-mini deployment
    provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
    
    # Get legacy config for temperature and max_tokens if available
    config = get_llm_config(state)
    temperature = float(config.get("temperature", 0.2))
    max_tokens = int(config.get("max_tokens", 32000))
    
    # Create OpenAI client with gpt-5-mini pattern
    from openai import OpenAI
    import os
    if provider_type == ModelProvider.AZURE_OPENAI:
        # Use Azure OpenAI with deployment name in path
        base_url = client_config.get("base_url")
        api_version = client_config.get("api_version") or os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
        if not base_url:
            endpoint = client_config.get("azure_endpoint", "").rstrip('/')
            deployment_name = client_config.get("deployment_name") or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini")
            base_url = f"{endpoint}/openai/deployments/{deployment_name}/"
        logger.info(f"Specifier using Azure OpenAI gpt-5-mini: {model_name} (base_url: {base_url})")
        client = OpenAI(
            api_key=client_config.get("api_key"),
            base_url=base_url,
            default_query={"api-version": api_version}
        )
    else:
        logger.info(f"Specifier using OpenAI model: {model_name} for chat completion")
        client = OpenAI(api_key=client_config.get("api_key"))
    
    # Construct prompt for LLM
    prompt = f"""
<role>
You are an expert market research planner creating comprehensive research specifications.
</role>

<task>
Create three research specifications based on the user's query and clarification answers.
</task>

<user_input>
<query>{initial_query}</query>
<clarification_answers>
{json.dumps(normalized_answers, indent=2)}
</clarification_answers>
</user_input>

<specifications_to_create>
1. **MASTER SPECIFICATION**: Overarching research plan derived from query and answers
2. **INDUSTRY SPECIFICATION**: Industry analysis focus derived from master spec
3. **PESTEL SPECIFICATION**: Political, Economic, Social, Technological, Environmental, Legal factors
</specifications_to_create>

<master_specification_schema>
{{
    "problem_statement": "[Clear, concise problem statement]",
    "geography_focus": ["[region1]", "[region2]"],
    "industry_focus": ["[industry1]", "[industry2]"],
    "research_depth": "[low|medium|high]",
    "time_horizon": "[timeframe]",
    "output_format": "[report|dashboard|presentation]",
    "competitor_analysis": [true|false],
    "market_size_analysis": [true|false],
    "trend_analysis": [true|false],
    "regulatory_analysis": [true|false],
    "customer_segments": ["[segment1]", "[segment2]"] or null,
    "raw_query": "{initial_query}",
    "raw_answers": [clarification answers object]
}}
</master_specification_schema>

<research_specification_schema>
Used for BOTH Industry and PESTEL specifications:
{{
    "title": "[Concise, descriptive title]",
    "description": "[Detailed description of research focus]",
    "key_questions": ["[5-7 research questions]"],
    "required_fact_categories": ["[fact categories to research]"],
    "geography_focus": ["[same as master spec]"],
    "industry_focus": ["[same as master spec]"],
    "keywords": ["[10-15 relevant search keywords]"]
}}
</research_specification_schema>

<output_schema>
{{
    "master_specification": {{[MASTER_SPECIFICATION_SCHEMA]}},
    "industry_specification": {{[RESEARCH_SPECIFICATION_SCHEMA]}},
    "pestel_specification": {{[RESEARCH_SPECIFICATION_SCHEMA]}}
}}
</output_schema>

<output_rules>
- Return ONLY valid JSON
- No explanations or additional text
- All fields must be populated
</output_rules>
"""
    
    # Call LLM asynchronously with timeout
    llm_output = None
    try:
        logger.info("Making LLM call for specification generation")
        
        # Build kwargs - gpt-5-mini requires max_completion_tokens instead of max_tokens
        # and only supports temperature=1 (default)
        api_kwargs = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        model_name_lower = model_name.lower()
        if "gpt-5" in model_name_lower or "o1" in model_name_lower or "o3" in model_name_lower:
            # Don't set temperature for these models - they only support default (1)
            api_kwargs["max_completion_tokens"] = max_tokens
        else:
            api_kwargs["temperature"] = temperature
            api_kwargs["max_tokens"] = max_tokens
        
        response = client.chat.completions.create(**api_kwargs)
        
        # Extract LLM output
        llm_output = response.choices[0].message.content
        
        logger.debug(f"LLM output received: {llm_output[:500]}...")
    except concurrent.futures.TimeoutError:
        logger.error("LLM call timed out after 60 seconds")
    except Exception as e:
        logger.error(f"Error during LLM call: {e}")
    
    # Parse LLM output into specifications
    specifications = None
    if llm_output:
        try:
            # Extract JSON from LLM output if it's wrapped in markdown or other text
            json_match = re.search(r'\{[\s\S]*\}', llm_output)
            if json_match:
                json_str = json_match.group(0)
                specifications = json.loads(json_str)
                logger.info("Successfully parsed LLM output into specifications")
            else:
                logger.error("Could not find JSON in LLM output")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM output: {e}")
        except Exception as e:
            logger.error(f"Error processing LLM output: {e}")
    
    # Update state with LLM-generated specifications (direct JSON approach)
    if specifications and isinstance(specifications, dict):
        try:
            # Add specifications directly to state
            if "master_specification" in specifications:
                master_spec = specifications["master_specification"]
                state["master_specification"] = json.dumps(master_spec)
                logger.info("Using LLM-generated master specification")
            
            # Process industry specification
            if "industry_specification" in specifications:
                industry_spec = specifications["industry_specification"]
                
                # Ensure keywords are present in industry specification
                if "keywords" not in industry_spec or not industry_spec["keywords"]:
                    # Generate keywords from industry specification
                    industry_keywords = []
                    
                    # Extract from title and description
                    if "title" in industry_spec:
                        industry_keywords.extend([w for w in industry_spec["title"].split() 
                                               if len(w) > 3 and w.lower() not in ["and", "the", "for", "with"]])
                    
                    # Add industry focus terms
                    if "industry_focus" in industry_spec and industry_spec["industry_focus"]:
                        industry_keywords.extend(industry_spec["industry_focus"])
                    
                    # Add geography terms
                    if "geography_focus" in industry_spec and industry_spec["geography_focus"]:
                        industry_keywords.extend(industry_spec["geography_focus"])
                    
                    # Add key terms from required fact categories
                    if "required_fact_categories" in industry_spec and industry_spec["required_fact_categories"]:
                        for category in industry_spec["required_fact_categories"]:
                            industry_keywords.extend(category.split())
                    
                    # Remove duplicates and limit to 15 keywords
                    industry_keywords = list(set([k for k in industry_keywords if len(k) > 2]))
                    industry_spec["keywords"] = industry_keywords[:15]
                    logger.info(f"Generated {len(industry_spec['keywords'])} keywords for industry specification")
                
                state["industry_specification"] = json.dumps(industry_spec)
                logger.info("Using LLM-generated industry specification")
            
            # Process PESTEL specification
            if "pestel_specification" in specifications:
                pestel_spec = specifications["pestel_specification"]
                
                # Ensure keywords are present in PESTEL specification
                if "keywords" not in pestel_spec or not pestel_spec["keywords"]:
                    # Generate keywords from PESTEL specification
                    pestel_keywords = ["PESTEL", "analysis"]
                    
                    # Extract from title and description
                    if "title" in pestel_spec:
                        pestel_keywords.extend([w for w in pestel_spec["title"].split() 
                                             if len(w) > 3 and w.lower() not in ["and", "the", "for", "with"]])
                    
                    # Add industry focus terms
                    if "industry_focus" in pestel_spec and pestel_spec["industry_focus"]:
                        pestel_keywords.extend(pestel_spec["industry_focus"])
                    
                    # Add geography terms
                    if "geography_focus" in pestel_spec and pestel_spec["geography_focus"]:
                        pestel_keywords.extend(pestel_spec["geography_focus"])
                    
                    # Add "political", "economic", etc. terms
                    pestel_factors = ["political", "economic", "social", "technological", "environmental", "legal"]
                    pestel_keywords.extend(pestel_factors)
                    
                    # Remove duplicates and limit to 15 keywords
                    pestel_keywords = list(set([k for k in pestel_keywords if len(k) > 2]))
                    pestel_spec["keywords"] = pestel_keywords[:15]
                    logger.info(f"Generated {len(pestel_spec['keywords'])} keywords for PESTEL specification")
                
                state["pestel_specification"] = json.dumps(pestel_spec)
                logger.info("Using LLM-generated PESTEL specification")
                
        except Exception as e:
            logger.error(f"Error processing specifications: {e}")
    
    return state
