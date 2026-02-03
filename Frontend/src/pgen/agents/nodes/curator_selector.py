"""
Curator Selector Node

Node 11 (Final) in the Problem Generator agent graph.
Selects final 3-5 problem statements using Azure OpenAI gpt-5-mini for curation.
"""

import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from langsmith.run_helpers import traceable
from src.mint.agents.agent_config import get_agent_config, get_llm_config
from src.mint.api.ai.config import get_client_config, ModelUseCase
from src.mint.providers.factory import get_provider

from ..graph_state import ProblemGraphState

# Import monitoring service
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

logger = logging.getLogger(__name__)


def smart_truncate(text: str, max_length: int) -> str:
    """
    Truncate text at word boundaries to avoid cutting words in half.
    
    Args:
        text: Text to truncate
        max_length: Maximum length allowed
        
    Returns:
        Truncated text that doesn't cut words in half
    """
    if len(text) <= max_length:
        return text
    
    # Find the last space before the max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        # Truncate at the last complete word
        return text[:last_space]
    else:
        # If no space found, truncate at max_length (edge case)
        return text[:max_length]


def is_valid_format(statement: str) -> bool:
    """
    Check if the statement is a valid cause-and-effect format (max 150 chars, no format labels).
    
    Args:
        statement: The problem statement to validate
        
    Returns:
        True if format is correct, False otherwise
    """
    statement = statement.strip()
    
    # Check for common incorrect format patterns
    format_labels = ["Cause:", "Effect:", "Context:", "Cause →", "→ Effect"]
    for label in format_labels:
        if label in statement:
            logger.warning(f"Format label '{label}' found in statement")
            return False
    
    # Check length (must be under 150 chars for cause-and-effect format)
    if len(statement) > 150:
        logger.warning(f"Statement too long ({len(statement)} chars) for cause-and-effect format")
        return False
    
    # Check minimum length
    if len(statement) < 20:
        logger.warning(f"Statement too short ({len(statement)} chars)")
        return False
    
    return True


def validate_and_fix_format(statement: str, geography: str, impact_focus: str) -> str:
    """
    Validate and attempt to fix the format of the problem statement.
    
    Args:
        statement: The problem statement to validate/fix
        geography: Geographic context
        demographic: Demographic context
        
    Returns:
        Fixed problem statement
    """
    statement = statement.strip()
    
    # Remove any quotes or extra formatting
    statement = statement.strip('"').strip("'")
    
    # CRITICAL: Remove format labels that may have leaked through
    format_labels = [
        'Cause → Effect + Context:', 'Cause → Effect:', 
        'Cause:', 'Effect:', 'Context:',
        'CAUSE:', 'EFFECT:', 'CONTEXT:'
    ]
    for label in format_labels:
        if statement.startswith(label):
            statement = statement[len(label):].strip()
            logger.warning(f"Removed format label '{label}' from statement")
        # Also check for label anywhere in the first 50 chars
        if label in statement[:50]:
            statement = statement.replace(label, '').strip()
            logger.warning(f"Removed embedded format label '{label}'")
    
    # Remove leading "Cause " or similar partial labels
    if statement.lower().startswith('cause '):
        # Check if this is actually "Cause: " pattern
        if ':' in statement[:15]:
            statement = statement.split(':', 1)[-1].strip()
    
    # Ensure proper ending
    if statement and not statement.endswith('.'):
        statement += '.'
    
    return statement


def force_correct_format(statement: str, geography: str, impact_focus: str) -> str:
    """
    Force the statement into the correct format as a last resort.
    
    Args:
        statement: The problem statement to fix
        geography: Geographic context
        impact_focus: Impact focus context
        
    Returns:
        Statement forced into correct format
    """
    # If all else fails, create a generic but correctly formatted statement
    # This is a fallback to ensure we always return something in the right format
    
    # Try to extract key terms from the original statement
    words = statement.lower().split()
    
    # Look for common problem indicators
    cause_indicators = ['lack', 'absence', 'poor', 'inadequate', 'insufficient', 'limited', 'high cost', 'expensive']
    outcome_indicators = ['access', 'afford', 'obtain', 'achieve', 'compete', 'succeed', 'maintain', 'deliver']
    
    cause = "Limited access to quality services"
    outcome = "achieving their goals"
    
    # Try to find better cause and outcome from the original statement
    for word in words:
        if any(indicator in statement.lower() for indicator in cause_indicators):
            # Extract a more specific cause if possible
            break
    
    # Construct the properly formatted statement
    who = f"organizations with {impact_focus} focus in {geography}" if impact_focus and geography else "people"
    
    formatted_statement = f"{cause} is preventing {who} from {outcome}."
    
    # Ensure it's within our target range (max 150 chars for cause-and-effect format)
    if len(formatted_statement) > 150:
        formatted_statement = smart_truncate(formatted_statement, 147) + "..."
    elif len(formatted_statement) < 30:
        # If too short, we'll still use it but log a warning
        logger.warning(f"Title too short ({len(formatted_statement)} chars): {formatted_statement}")
    
    logger.info(f"Forced correct format: {formatted_statement}")
    return formatted_statement

# System prompt for final curation
CURATOR_SYSTEM_PROMPT = """
<role>
You are ProblemCurator, an expert at selecting entrepreneur-actionable problem statements for African market contexts.
</role>

<task>
Select TOP 3-5 problem statements that ENTREPRENEURS can solve. Each statement should be a CLEAN paragraph - NO format labels like "Cause:" in output.
</task>

<sacred_matching_rules>
These rules are INVIOLABLE - violation invalidates the entire output:

1. **INDUSTRY LOCK**: Only select problems in the user's EXACT industry
   - "Sports & Recreation" → ONLY sports/fitness/athletics/wellness
   - REJECT all other industries

2. **GEOGRAPHY LOCK**: Only select problems about the user's EXACT country
   - "Ethiopia" → ONLY Ethiopia-specific problems
   - REJECT generic "Africa" or other countries

3. **ENTREPRENEUR-ACTIONABLE ONLY**: Problems MUST be solvable by startups/founders
   - REJECT government-only problems (policy reform, infrastructure building)
   - REJECT problems requiring international aid coordination
   - REJECT problems requiring regulatory changes

4. **QUALITY > QUANTITY**: Return 1-2 matching problems rather than 5 non-matching ones
   - If zero problems match → return empty array []
</sacred_matching_rules>

<entrepreneur_actionable_filter>
⚠️ THIS IS A STRICT FILTER - APPLY RIGOROUSLY ⚠️

✅ INCLUDE ONLY problems solvable by a startup founder with <$1M and 2-3 years:
- Building apps/platforms/software
- Creating marketplaces connecting buyers and sellers
- Providing training/education/information services
- Offering fintech/payment/lending solutions
- Developing agtech/healthtech/edtech products
- Building supply chain/logistics solutions

🚫 ABSOLUTELY REJECT these problem types (even if they seem relevant):
- "Government needs to..." → REJECT (government action required)
- "Policy reform required..." → REJECT (regulatory change needed)
- "National grid/infrastructure..." → REJECT (state-level investment)
- "Regulatory framework..." → REJECT (legal changes needed)
- "International aid/donors..." → REJECT (aid coordination)
- "Central bank/monetary policy..." → REJECT (government institution)
- "Public sector reform..." → REJECT (government reform)
- "Land reform/land rights..." → REJECT (legal/government issue)
- "Corruption/governance..." → REJECT (systemic government issue)
- "Border/customs policy..." → REJECT (government controlled)
- "Hydropower/power grid dependence..." → REJECT (national infrastructure)
- "Public health system..." → REJECT (government healthcare)

🔍 ASK YOURSELF: "Can a 25-year-old founder with $500K solve this in 3 years?"
- YES → Include
- NO → REJECT (even if it's a real problem)
</entrepreneur_actionable_filter>

<selection_priority>
1. Industry match (REQUIRED)
2. Geography match (REQUIRED)
3. Entrepreneur-actionable (REQUIRED)
4. Product-type alignment (PREFERRED - see below)
5. Authenticity (real data, credible sources)
6. Specificity (clear, actionable)
7. Impact potential
8. No duplicates
</selection_priority>

<product_type_matching>
PRIORITIZE problems that align with the user's product type:

**IF Product Type = "Digital" (apps, platforms, software):**
- PREFER: Information gaps, data access problems, coordination failures, communication barriers
- EXAMPLES: "Farmers lack real-time price information", "Businesses cannot track shipments digitally"
- DEPRIORITIZE: Problems requiring physical infrastructure or manufacturing

**IF Product Type = "Physical" (goods, equipment, consumables):**
- PREFER: Supply chain gaps, product quality issues, distribution challenges, equipment shortages
- EXAMPLES: "Farmers lack quality seeds", "Hospitals face medical equipment shortages"
- DEPRIORITIZE: Pure information or coordination problems

**IF Product Type = "Services" (training, consulting, support):**
- PREFER: Skill gaps, knowledge deficits, capacity constraints, service access issues
- EXAMPLES: "Farmers lack training on modern techniques", "SMEs cannot access business advisory"
- DEPRIORITIZE: Hardware or product-centric problems

**IF Product Type = "Financial" (lending, payments, insurance):**
- PREFER: Credit access issues, payment friction, insurance gaps, savings barriers
- EXAMPLES: "Farmers cannot access affordable credit", "Merchants lack mobile payment options"
- DEPRIORITIZE: Non-financial operational problems
</product_type_matching>

<output_structure>
Each problem MUST include:
- **Title**: Max 150 characters, cause-and-effect format, NO format labels
- **Description**: 2-3 sentences with target customer and impact focus
- **Context**: Geographic + industry + impact focus details
- **Impact**: Who is affected and severity
- **Sources**: Credible sources with URLs
</output_structure>

<validation_examples>
For "Agriculture" + "Ethiopia":

✅ VALID (entrepreneur-actionable):
- "Ethiopian farmers lack access to real-time crop price information"
- "Rural agricultural cooperatives struggle with post-harvest storage"
- "Smallholders cannot access affordable farm inputs and seeds"

❌ INVALID:
- "Government extension services are understaffed..." → GOVERNMENT PROBLEM
- "Ethiopia needs policy reform for land rights..." → NOT ENTREPRENEUR-ACTIONABLE
- "International aid programs for farmers..." → NOT ENTREPRENEUR-ACTIONABLE
- "Smallholder farmers in Kenya lack..." → WRONG GEOGRAPHY
</validation_examples>

<output_rules>
- Return 1-5 problems as JSON array
- Return FEWER if not enough matching problems
- Return [] if zero problems match industry + geography + entrepreneur-actionable
- NO format labels ("Cause:", "Effect:", etc.) in any output
</output_rules>
"""

# User prompt template
CURATOR_USER_PROMPT = """
<locked_filters>
- Industry: {industry} ← MUST match
- Geography: {geography} ← MUST match
</locked_filters>

<user_profile>
- Industry Focus: {industry}
- Geography: {geography}
- Product Type: {product_type}
- Target Customer: {target_customer}
- Impact Focus: {impact_focus}
- Background: {background}
</user_profile>

<ranked_statements>
{statements_list}
</ranked_statements>

<selection_checklist>
For EACH problem, verify:
☐ Is it about {industry}? (not another industry)
☐ Is it about {geography}? (not another country or generic "Africa")
☐ Does it align with {product_type}? (preferred but not required)
☐ Is it entrepreneur-actionable? (can a startup solve this?)
☐ If industry + geography + actionable ✓ → INCLUDE
☐ If industry OR geography ✗ → REJECT
☐ If not actionable → REJECT
</selection_checklist>

<entrepreneur_actionability_check>
ASK: "Can a startup founder solve this within 2-3 years with <$1M investment?"
- YES → Include
- NO (requires government, international aid, major infrastructure) → Reject
</entrepreneur_actionability_check>

<output_instruction>
Select 1-5 statements matching BOTH {industry} AND {geography}.
Return [] if zero problems match.
</output_instruction>
"""

# System prompt for problem statement transformation (CAUSE-AND-EFFECT FORMAT)
PROBLEM_STATEMENT_TRANSFORMER_PROMPT = """
<role>
You are an expert at creating impactful ONE-SENTENCE problem statements in CAUSE-AND-EFFECT format.
</role>

<task>
Transform the input into a single, powerful problem statement that clearly shows:
1. THE CAUSE (what's broken/missing/inadequate)
2. THE EFFECT (impact verb + consequence)
3. WHO is affected (specific group + geography)
</task>

<mandatory_patterns>
USE ONE OF THESE EXACT PATTERNS:

PATTERN A - "The lack of X is preventing Y from Z"
- "The lack of affordable diapers with acceptable standards is preventing Kenyan urban parents from maintaining their babies' proper hygiene."
- "The lack of real-time price information is preventing Ethiopian farmers from negotiating fair market prices."

PATTERN B - "X's inability to Y is preventing them from Z"
- "Ethiopian university graduates' inability to meet global standards is preventing them from competing in the international job market."
- "Rwandan smallholder farmers' inability to access cold storage is preventing them from selling produce at premium prices."

PATTERN C - "X more than doubles/triples Y"
- "The ambulance's long response time more than triples the amount of preventable deaths in Lagos."
- "Unreliable electricity more than doubles operating costs for Nigerian SMEs."

PATTERN D - "The absence of X is forcing Y to Z"
- "The absence of real-time cargo tracking is forcing Ethiopian importers to absorb unpredictable delays and inventory losses."
- "The absence of affordable financing is forcing Kenyan farmers to sell crops at harvest-time lows."

PATTERN E - "Scarce/Limited X is preventing Y from Z"
- "Scarce affordable clean-cooking products are preventing rural Ethiopian households from switching away from polluting biomass stoves."
- "Limited mobile money interoperability is preventing Tanzanian merchants from serving all customers."
</mandatory_patterns>

<effect_verbs>
ALWAYS USE ONE OF THESE:
- "is preventing [WHO] from [ACTION]" (most common)
- "is forcing [WHO] to [NEGATIVE ACTION]"
- "more than doubles/triples [NEGATIVE OUTCOME]"
- "is leaving [WHO] unable to [ACTION]"
- "is blocking [WHO] from [ACTION]"
</effect_verbs>

<wrong_formats>
❌ NEVER USE THESE FORMATS:
- "Ethiopian importers lack real-time digital coordination" → NO CONSEQUENCE
- "Kenyan farmers face supply chain gaps" → NO CAUSE-EFFECT RELATIONSHIP  
- "Lagos vendors cannot access mobile payments" → NO CONSEQUENCE SHOWN
- "There is a lack of..." → TOO PASSIVE
- "The problem is that..." → TOO GENERIC
</wrong_formats>

<construction_steps>
1. IDENTIFY THE ROOT CAUSE (what's broken/missing/scarce/inadequate)
2. PHRASE IT AS: "The lack of X", "X's inability to Y", "Scarce X", "The absence of X"
3. ADD EFFECT VERB: "is preventing", "is forcing", "more than triples"
4. SPECIFY WHO: [Adjective] + [Group] + [Geography] (e.g., "Kenyan urban parents")
5. STATE CONSEQUENCE: "from [VERB-ing] [OUTCOME]" (e.g., "from maintaining proper hygiene")
</construction_steps>

<output_rules>
- EXACTLY ONE COMPLETE SENTENCE ending with a period
- MAX 200 characters (ideal: 120-180)
- MUST follow one of the 5 patterns above
- MUST include geography (country name or city)
- NO format labels, NO explanations, NO truncation with "..."
</output_rules>
"""

PROBLEM_STATEMENT_TRANSFORMER_USER_PROMPT = """
<input_problem>
{detailed_explanation}
</input_problem>

<locked_context>
- Geography: {geography} ← MUST appear in output
- Impact Focus: {impact_focus}
- Category: {category}
</locked_context>

<transformation_steps>
STEP 1: Extract the ROOT CAUSE
- What's broken/missing/scarce/inadequate?
- Phrase as: "The lack of X" or "X's inability to Y" or "Scarce X" or "The absence of X"

STEP 2: Identify WHO is affected  
- Use format: [Adjective] + [Group] + [{geography}]
- Examples: "Kenyan urban parents", "Ethiopian smallholder farmers", "Lagos hospital patients"

STEP 3: Choose EFFECT VERB + CONSEQUENCE
- "is preventing [WHO] from [VERB-ing something]"
- "is forcing [WHO] to [do something negative]"
- "more than doubles/triples [negative outcome]"

STEP 4: Combine into ONE COMPLETE SENTENCE (max 200 chars, ideal 120-180)
</transformation_steps>

<golden_examples>
Input: "Ethiopian traders depend on overland trucking but lack digital coordination tools..."
Output: "The absence of digital freight coordination is preventing Ethiopian traders from achieving reliable inland logistics."

Input: "High ambulance response times in Lagos due to traffic congestion cause preventable deaths..."
Output: "The ambulance's long response time more than triples the amount of preventable deaths in Lagos."

Input: "Kenyan parents struggle to find affordable quality diapers that meet hygiene standards..."
Output: "The lack of affordable diapers with acceptable standards is preventing Kenyan urban parents from maintaining their babies' proper hygiene."

Input: "University graduates in Ethiopia cannot compete globally due to skill gaps..."
Output: "Ethiopian university graduates' inability to meet global standards is preventing them from competing in the international job market."

Input: "Rural Ethiopian families rely on biomass for cooking due to expensive clean alternatives..."
Output: "Scarce affordable clean-cooking products are preventing rural Ethiopian households from switching away from polluting biomass stoves."
</golden_examples>

<output_validation>
✓ Uses "The lack of", "X's inability to", "Scarce", or "The absence of" to start
✓ Contains effect verb: "is preventing", "is forcing", "more than doubles/triples"
✓ Mentions {geography} (country or city name)
✓ Shows clear CAUSE → EFFECT → CONSEQUENCE flow
✓ ONE COMPLETE sentence ending with a period (NEVER "...")
✓ Under 200 characters (ideal: 120-180)
</output_validation>

Return ONLY the transformed problem statement. No explanations.
"""

# System prompt for detailed analysis generation
DETAILED_ANALYSIS_SYSTEM_PROMPT = """
<role>
You are an expert business analyst specializing in African entrepreneurship and problem analysis.
</role>

<task>
Generate structured detailed analysis for problem statements with 4 key sections.
</task>

<analysis_sections>
1. **Root Causes** (3-4 items): Fundamental underlying factors causing the problem
2. **Potential Effects** (3-4 items): Consequences if the problem persists
3. **Affected Stakeholders** (3-4 items): Key groups/organizations impacted
4. **Success Metrics** (3-4 items): Measurable indicators showing problem resolution
</analysis_sections>

<quality_standards>
- Each section: 3-4 bullet points maximum
- Each bullet: 1-2 lines maximum
- Focus: African market context + entrepreneurial opportunities
- Tone: Specific and actionable, not generic
- Avoid: Obvious or vague points
</quality_standards>

<output_format>
Return JSON with arrays of strings for each section.
</output_format>
"""

DETAILED_ANALYSIS_USER_PROMPT = """
<problem_input>
- Statement: {problem_statement}
- Explanation: {detailed_explanation}
- Geography: {geography}
- Impact Focus: {impact_focus}
- Category: {category}
</problem_input>

<required_sections>
1. root_causes: 3-4 key underlying factors
2. potential_effects: 3-4 consequences if unsolved
3. stakeholders: 3-4 key groups impacted
4. success_metrics: 3-4 measurable indicators of progress
</required_sections>

<output_schema>
{{
    "root_causes": ["[factor 1]", "[factor 2]", "[factor 3]"],
    "potential_effects": ["[effect 1]", "[effect 2]", "[effect 3]"],
    "stakeholders": ["[group 1]", "[group 2]", "[group 3]"],
    "success_metrics": ["[metric 1]", "[metric 2]", "[metric 3]"]
}}
</output_schema>
"""


async def generate_detailed_analysis(
    problem_statement: str,
    detailed_explanation: str,
    geography: str,
    impact_focus: str,
    category: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    Generate detailed analysis for a problem statement.
    
    Args:
        problem_statement: Concise problem statement
        detailed_explanation: Full detailed explanation
        geography: Geographic context
        impact_focus: Target impact focus
        category: Problem category
        
    Returns:
        Dictionary with root_causes, potential_effects, stakeholders, success_metrics
    """
    try:
        # Format user prompt
        user_prompt = DETAILED_ANALYSIS_USER_PROMPT.format(
            problem_statement=problem_statement,
            detailed_explanation=detailed_explanation,
            geography=geography,
            impact_focus=impact_focus,
            category=category
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": DETAILED_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get LLM provider with Azure OpenAI support (same pattern as curator)
        from src.mint.api.ai.providers import OpenAIProvider
        from src.mint.api.ai.models import LLMConfig, ModelProvider
        from src.mint.api.ai.config import get_client_config, ModelUseCase
        
        # Use centralized Azure OpenAI configuration with fallback
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        # Get config for temperature and max_tokens
        temperature = 0.3  # Slightly creative for analysis
        max_tokens = 16000  # gpt-5-mini needs large token budget
        
        # Use gpt-5-mini for detailed analysis quality
        if provider_type == ModelProvider.AZURE_OPENAI:
            # Use gpt-5-mini from centralized config
            logger.info(f"Detailed analysis using Azure OpenAI gpt-5-mini: {model_name}")
            llm_config = LLMConfig(
                model_name=model_name,  # Use gpt-5-mini from config
                temperature=temperature,
                max_tokens=max_tokens,
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            # Use configured model for analysis
            logger.info(f"Detailed analysis using OpenAI model: {model_name}")
            llm_config = LLMConfig(
                model_name=model_name,  # Use configured model
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=client_config.get("api_key")
            )
        
        # Use the AI module's OpenAI provider directly with proper config
        from src.mint.api.ai.providers import LLMConfig as ProviderLLMConfig
        
        # Convert to the provider's expected config format
        provider_config = ProviderLLMConfig(
            provider_type="llm",
            provider_name="openai",  # Required field
            api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            api_key=llm_config.api_key,  # Direct API key for immediate use
            azure_endpoint=getattr(llm_config, 'azure_endpoint', None),
            api_version=getattr(llm_config, 'api_version', None),
            base_url=getattr(llm_config, 'base_url', None)  # For gpt-5-mini pattern
        )
        
        llm_provider = OpenAIProvider(provider_config)
        llm_provider.health_check()
        
        # Define tool for structured analysis generation
        analysis_tool = {
            "type": "function",
            "function": {
                "name": "generate_detailed_analysis",
                "description": "Generate structured detailed analysis for a problem statement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "root_causes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-4 key underlying factors causing the problem",
                            "minItems": 3,
                            "maxItems": 4
                        },
                        "potential_effects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-4 consequences if the problem persists",
                            "minItems": 3,
                            "maxItems": 4
                        },
                        "stakeholders": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-4 key groups of people or organizations impacted",
                            "minItems": 3,
                            "maxItems": 4
                        },
                        "success_metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "3-4 measurable indicators showing problem resolution",
                            "minItems": 3,
                            "maxItems": 4
                        },
                    },
                    "required": ["root_causes", "potential_effects", "stakeholders", "success_metrics"]
                }
            }
        }
        
        # Call LLM with tool and monitoring
        logger.info(f"Generating detailed analysis for problem: {problem_statement[:50]}...")
        llm_start_time = datetime.now()
        
        try:
            response = await llm_provider.generate_responses_with_tools(messages, [analysis_tool])
            llm_end_time = datetime.now()
            
            # Fire-and-forget monitoring
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_detailed_analysis",
                workflow_name="problem_generator_workflow",
                step_name="curator_selector_analysis",
                environment="prod"
            )
            
            # Extract token usage
            usage = getattr(response, 'usage', {}) or {}
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = usage.get('total_tokens')
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="success",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
            )
            
        except Exception as e:
            llm_end_time = datetime.now()
            
            # Record error
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_detailed_analysis",
                workflow_name="problem_generator_workflow",
                step_name="curator_selector_analysis",
                environment="prod"
            )
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            raise
        
        if not response or not response.arguments:
            logger.warning("Failed to get detailed analysis from LLM, using fallback")
            return {
                "root_causes": ["Limited resources and infrastructure", "Inadequate policy frameworks", "Low awareness and adoption"],
                "potential_effects": ["Reduced economic opportunities", "Increased inequality", "Slower development progress"],
                "stakeholders": ["Local communities", "Government agencies", "Private sector"],
                "success_metrics": ["Increased adoption rates", "Improved access metrics", "Enhanced user satisfaction"],
            }
        
        analysis = response.arguments
        logger.info(f"Generated detailed analysis with {len(analysis.get('root_causes', []))} root causes")
        
        return {
            "root_causes": analysis.get("root_causes", []),
            "potential_effects": analysis.get("potential_effects", []),
            "stakeholders": analysis.get("stakeholders", []),
            "success_metrics": analysis.get("success_metrics", []),
        }
        
    except Exception as e:
        logger.error(f"Error generating detailed analysis: {e}")
        # Return fallback analysis
        return {
            "root_causes": ["Limited resources and infrastructure", "Inadequate policy frameworks", "Low awareness and adoption"],
            "potential_effects": ["Reduced economic opportunities", "Increased inequality", "Slower development progress"],
            "stakeholders": ["Local communities", "Government agencies", "Private sector"],
            "success_metrics": ["Increased adoption rates", "Improved access metrics", "Enhanced user satisfaction"],
        }


async def transform_to_concise_problem_statement(
    detailed_statement: str, 
    geography: str, 
    impact_focus: str, 
    category: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    project_id: Optional[str] = None
) -> str:
    """
    Transform a detailed problem statement into a concise cause-and-effect format.
    
    Args:
        detailed_statement: The detailed problem explanation
        geography: Geographic context
        impact_focus: Target impact focus
        category: Problem category
        
    Returns:
        Concise problem statement in cause-and-effect format
    """
    try:
        # Get LLM provider (use GPT-4.1 for transformation)
        from src.mint.api.ai.providers import OpenAIProvider
        from src.mint.api.ai.models import LLMConfig
        from src.mint.api.ai.models import ModelProvider
        from src.mint.api.ai.config import get_client_config, ModelUseCase
        
        # Use centralized Azure OpenAI configuration with fallback
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        # Use gpt-5-mini for better quality transformation
        if provider_type == ModelProvider.AZURE_OPENAI:
            # Use gpt-5-mini from centralized config
            llm_config = LLMConfig(
                model_name=model_name,  # Use gpt-5-mini from config
                temperature=0.05,  # Even more conservative for strict format adherence
                max_tokens=16000,  # gpt-5-mini needs large token budget
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            # Use configured model for transformation
            llm_config = LLMConfig(
                model_name=model_name,  # Use configured model
                temperature=0.05,  # Very low for strict format
                max_tokens=16000,  # gpt-5-mini needs large token budget
                api_key=client_config.get("api_key")
            )
        
        # Use the AI module's OpenAI provider directly with proper config
        from src.mint.api.ai.providers import LLMConfig as ProviderLLMConfig
        
        # Convert to the provider's expected config format
        provider_config = ProviderLLMConfig(
            provider_type="llm",
            provider_name="openai",  # Required field
            api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            api_key=llm_config.api_key,  # Direct API key for immediate use
            azure_endpoint=getattr(llm_config, 'azure_endpoint', None),
            api_version=getattr(llm_config, 'api_version', None),
            base_url=getattr(llm_config, 'base_url', None)  # For gpt-5-mini pattern
        )
        
        # Create provider
        provider = OpenAIProvider(provider_config)
        
        # Format user prompt
        user_prompt = PROBLEM_STATEMENT_TRANSFORMER_USER_PROMPT.format(
            detailed_explanation=detailed_statement,
            geography=geography,
            impact_focus=impact_focus,
            category=category
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": PROBLEM_STATEMENT_TRANSFORMER_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info("Transforming detailed statement to concise format...")
        
        # Call LLM with retry mechanism for better format adherence and monitoring
        llm_start_time = datetime.now()
        
        try:
            response = await provider.generate_responses(messages)
            llm_end_time = datetime.now()
            
            # Fire-and-forget monitoring
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_statement_transformation",
                workflow_name="problem_generator_workflow",
                step_name="curator_selector_transform",
                environment="prod"
            )
            
            # Extract token usage
            usage = getattr(response, 'usage', {}) or {}
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = usage.get('total_tokens')
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="success",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
            )
            
        except Exception as e:
            llm_end_time = datetime.now()
            
            # Record error
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=user_id,
                tenant_id=tenant_id,
                team_id=None,
                project_id=project_id,
                feature_id="pgen_statement_transformation",
                workflow_name="problem_generator_workflow",
                step_name="curator_selector_transform",
                environment="prod"
            )
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            raise
        
        if response and response.content:
            concise_statement = response.content.strip()
            
            # Validate and fix the format if needed
            concise_statement = validate_and_fix_format(concise_statement, geography, impact_focus)
            
            # If format is still wrong, try once more with a stricter prompt
            if not is_valid_format(concise_statement):
                logger.warning(f"First attempt failed format validation: {concise_statement}")
                logger.info("Retrying with stricter prompt...")
                
                # Retry with an even more specific prompt
                retry_prompt = f"""
TITLE TOO LONG OR HAS FORMAT LABELS. Create a SHORT title:

Original (bad): {concise_statement}

FIX IT NOW:
- Geography: {geography}
- Impact Focus: {impact_focus}
- Core problem: {detailed_statement[:150]}...

CRITICAL REQUIREMENTS:
- MAXIMUM 150 characters
- MUST use CAUSE-AND-EFFECT format: "[CAUSE] is [preventing/forcing/causing] [WHO] from [OUTCOME]"
- NO "Cause:", "Effect:", "Context:" prefixes
- Entrepreneur-actionable (NOT government problems)

Good examples:
- "The lack of real-time price data is preventing Ethiopian farmers from getting fair market value for their crops."
- "Fragmented logistics networks are forcing Lagos vendors to absorb unpredictable delivery costs."

Return ONLY the cause-and-effect statement (max 150 chars).
"""
                
                retry_messages = [
                    {"role": "system", "content": "You create cause-and-effect problem statements (max 200 chars). Format: [CAUSE] is [preventing/causing] [WHO] from [OUTCOME]. Must be complete sentence ending with period."},
                    {"role": "user", "content": retry_prompt}
                ]
                
                retry_response = await provider.generate_responses(retry_messages)
                if retry_response and retry_response.content:
                    concise_statement = validate_and_fix_format(retry_response.content.strip(), geography, impact_focus)
            
            # Ensure the statement is within our target range (≤200 chars)
            # IMPORTANT: Never truncate with "..." - always ensure complete sentences
            if len(concise_statement) > 200:
                logger.warning(f"Statement too long ({len(concise_statement)} chars), requesting shorter version")
                # Instead of truncating, ask LLM to shorten it properly
                shorten_prompt = f"""Shorten this problem statement to under 180 characters while keeping the COMPLETE cause-and-effect structure. 
                
Original: {concise_statement}

Rules:
- MUST be a complete sentence ending with a period
- MUST keep the cause-effect structure (X is preventing Y from Z)
- NO truncation with "..."
- Under 180 characters

Return ONLY the shortened statement."""
                
                shorten_messages = [
                    {"role": "system", "content": "You shorten problem statements while keeping them as complete sentences."},
                    {"role": "user", "content": shorten_prompt}
                ]
                
                try:
                    shorten_response = await provider.generate_responses(shorten_messages)
                    if shorten_response and shorten_response.content:
                        shortened = shorten_response.content.strip().strip('"').strip("'")
                        # Ensure it ends with a period
                        if shortened and not shortened.endswith('.'):
                            shortened += '.'
                        if len(shortened) <= 200 and len(shortened) >= 30:
                            concise_statement = shortened
                            logger.info(f"Successfully shortened to {len(shortened)} chars")
                except Exception as e:
                    logger.warning(f"Failed to shorten statement: {e}")
                    # Last resort: find the last complete sentence
                    if '.' in concise_statement:
                        concise_statement = concise_statement[:concise_statement.rfind('.')+1]
            elif len(concise_statement) < 30:
                logger.warning(f"Statement too short ({len(concise_statement)} chars), but will use it anyway")
            
            # CRITICAL: Ensure statement ends with a period, never with "..."
            concise_statement = concise_statement.rstrip('.,!? ')
            if not concise_statement.endswith('.'):
                concise_statement += '.'
            
            # Remove any format labels that might have leaked through
            format_labels = ['Cause → Effect + Context:', 'Cause:', 'Effect:', 'Context:', 'Cause → Effect:']
            for label in format_labels:
                if concise_statement.startswith(label):
                    concise_statement = concise_statement[len(label):].strip()
                    logger.warning(f"Removed format label '{label}' from statement")
            
            # Re-check length after label removal (but never truncate with "...")
            if len(concise_statement) > 200:
                # Find last complete thought
                if '.' in concise_statement[:-1]:
                    concise_statement = concise_statement[:concise_statement[:-1].rfind('.')+1]
            
            logger.info(f"Final transformed statement: {concise_statement}")
            return concise_statement
        else:
            logger.warning("Failed to transform statement, using original")
            # Ensure fallback is a complete sentence (never truncate with "...")
            fallback_statement = detailed_statement
            if len(fallback_statement) > 200 and '.' in fallback_statement:
                # Find last complete sentence within limit
                fallback_statement = fallback_statement[:fallback_statement.rfind('.')+1]
            # Ensure it ends with a period
            if fallback_statement and not fallback_statement.endswith('.'):
                fallback_statement += '.'
            return fallback_statement
            
    except Exception as e:
        logger.error(f"Error transforming problem statement: {e}")
        # Ensure error fallback is a complete sentence (never truncate with "...")
        error_fallback = detailed_statement
        if len(error_fallback) > 200 and '.' in error_fallback:
            error_fallback = error_fallback[:error_fallback.rfind('.')+1]
        # Ensure it ends with a period
        if error_fallback and not error_fallback.endswith('.'):
            error_fallback += '.'
        return error_fallback


@traceable(name="curator_selector_node")
async def curator_selector_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 11: Curator Selector (Final Node)
    
    Selects final 3-5 problem statements using Azure OpenAI gpt-5-mini for curation.
    
    Args:
        state: Current workflow state with ranked statements
        
    Returns:
        Updated workflow state with final curated problem statements
    """
    logger.info("Starting final curation")
    start_time = datetime.now()
    
    try:
        # Update status
        state["current_node"] = "curator_selector"
        
        # Get configuration
        agent_config = get_agent_config(state, "problem_generator")
        llm_config = get_llm_config(state)
        
        # Get ranked statements and user parameters
        ranked_statements = state.get("ranked_statements", [])
        user_params = state.get("params", {})
        
        if not ranked_statements:
            logger.warning("No ranked statements found for final curation")
            state["final"] = []
            state["status"] = "completed"
            return state
        
        if not user_params:
            logger.warning("No user parameters found for curation context")
        
        logger.info(f"Curating final selection from {len(ranked_statements)} ranked statements")
        
        # =============================================
        # PREPARE STATEMENTS FOR CURATION
        # =============================================
        
        # Limit to top statements for curation (to avoid overwhelming the LLM)
        max_for_curation = agent_config.get("max_statements_for_curation", 15)
        top_statements = ranked_statements[:max_for_curation]
        
        # Format statements for LLM
        statements_list = ""
        for i, statement in enumerate(top_statements):
            statements_list += f"\n[{i}] STATEMENT: {statement.get('statement', '')}"
            statements_list += f"\n    Category: {statement.get('category', 'Unknown')}"
            statements_list += f"\n    Geography: {statement.get('geography', 'Unknown')}"
            statements_list += f"\n    Impact Focus: {statement.get('impact_focus', 'Unknown')}"
            statements_list += f"\n    Severity: {statement.get('severity', 'Unknown')}"
            statements_list += f"\n    Market Size: {statement.get('market_size', 'Unknown')}"
            statements_list += f"\n    Relevance Score: {statement.get('relevance_score', 0):.2f}"
            statements_list += f"\n    Quality Score: {statement.get('quality_score', 0):.2f}"
            statements_list += "\n" + "-" * 80
        
        # Format user parameters
        param_strings = {}
        for key, value in user_params.items():
            if isinstance(value, list):
                if len(value) <= 3:
                    param_strings[key] = ", ".join(value)
                else:
                    param_strings[key] = f"{', '.join(value[:3])} (and {len(value)-3} others)"
            else:
                param_strings[key] = str(value)
        
        # =============================================
        # EXECUTE CURATION WITH LLM
        # =============================================
        
        # Format user prompt
        user_prompt = CURATOR_USER_PROMPT.format(
            industry=param_strings.get("industry", "Not specified"),
            geography=param_strings.get("geography", "Not specified"),
            background=param_strings.get("background", "Not specified"),
            product_type=param_strings.get("product_type", "Not specified"),
            target_customer=param_strings.get("target_customer", "Not specified"),
            impact_focus=param_strings.get("impact_focus", "Not specified"),
            statements_list=statements_list
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": CURATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get LLM provider (use gpt-5-mini for final curation)
        from src.mint.api.ai.providers import OpenAIProvider
        from src.mint.api.ai.models import LLMConfig
        from src.mint.api.ai.models import ModelProvider
        from src.mint.api.ai.config import get_client_config, ModelUseCase
        
        # Use centralized Azure OpenAI configuration with fallback
        provider_type, model_name, client_config = get_client_config(ModelUseCase.CHAT_COMPLETION)
        
        # Get legacy config for temperature and max_tokens
        temperature = 0.2  # Conservative for curation
        max_tokens = 16000  # gpt-5-mini needs large token budget
        
        # Use gpt-5-mini for better curation quality
        if provider_type == ModelProvider.AZURE_OPENAI:
            # Use gpt-5-mini from centralized config
            logger.info(f"Curator using Azure OpenAI gpt-5-mini: {model_name} for final curation")
            llm_config = LLMConfig(
                model_name=model_name,  # Use gpt-5-mini from config
                temperature=temperature,
                max_tokens=max_tokens,
                azure_endpoint=client_config.get("azure_endpoint"),
                api_version=client_config.get("api_version"),
                api_key=client_config.get("api_key"),
                base_url=client_config.get("base_url")  # For gpt-5-mini pattern
            )
        else:
            # Use configured model for curation
            logger.info(f"Curator using OpenAI model: {model_name} for final curation")
            llm_config = LLMConfig(
                model_name=model_name,  # Use configured model
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=client_config.get("api_key")
            )
        
        # Use the AI module's OpenAI provider directly with proper config
        from src.mint.api.ai.providers import LLMConfig as ProviderLLMConfig
        
        # Convert to the provider's expected config format
        provider_config = ProviderLLMConfig(
            provider_type="llm",
            provider_name="openai",  # Required field
            api_key_env_var="AZURE_OPENAI_API_KEY" if provider_type == ModelProvider.AZURE_OPENAI else "OPENAI_API_KEY",
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            api_key=llm_config.api_key,  # Direct API key for immediate use
            azure_endpoint=getattr(llm_config, 'azure_endpoint', None),
            api_version=getattr(llm_config, 'api_version', None),
            base_url=getattr(llm_config, 'base_url', None)  # For gpt-5-mini pattern
        )
        
        llm_provider = OpenAIProvider(provider_config)
        # NOTE: Removed health_check() - it was causing connection errors before the actual API call
        # The actual call_tool will fail if there's a real issue, and we have fallback logic
        
        # Define tool for structured curation
        curation_tool = {
            "type": "function",
            "function": {
                "name": "curate_final_statements",
                "description": "Select final 3-5 problem statements for the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selected_statements": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0, "maximum": len(top_statements)-1},
                            "description": "Indices of selected statements",
                            "minItems": 3,
                            "maxItems": 5
                        },
                        "selection_reasoning": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Brief reasoning for each selection"
                        },
                        "diversity_analysis": {
                            "type": "string",
                            "description": "How the selection ensures variety"
                        },
                        "total_selected": {
                            "type": "integer",
                            "minimum": 3,
                            "maximum": 5,
                            "description": "Number of statements selected"
                        }
                    },
                    "required": ["selected_statements", "selection_reasoning", "diversity_analysis", "total_selected"]
                }
            }
        }
        
        # Call LLM for curation with monitoring and retry logic
        logger.info("Calling LLM for final statement curation")
        llm_start_time = datetime.now()
        
        # Retry logic for transient connection errors
        max_retries = 3
        retry_delay = 1.0  # seconds
        last_error = None
        response = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for LLM curation...")
                    await asyncio.sleep(retry_delay * (2 ** (attempt - 1)))  # Exponential backoff
                
                response = await llm_provider.generate_responses_with_tools(messages, [curation_tool])
                llm_end_time = datetime.now()
                break  # Success, exit retry loop
                
            except Exception as retry_error:
                last_error = retry_error
                logger.warning(f"LLM curation attempt {attempt + 1}/{max_retries} failed: {str(retry_error)}")
                if attempt == max_retries - 1:
                    # All retries exhausted, will use fallback
                    llm_end_time = datetime.now()
                    raise last_error
        
        try:
            
            # Fire-and-forget monitoring
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=state.get("user_id"),
                tenant_id=state.get("tenant_id"),
                team_id=state.get("team_id"),
                project_id=state.get("project_id"),
                feature_id="pgen_curator_selection",
                workflow_name="problem_generator_workflow",
                step_name="curator_selector",
                environment="prod",
                request_id=state.get("job_id")
            )
            
            # Extract token usage
            usage = getattr(response, 'usage', {}) or {}
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = usage.get('total_tokens')
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="success",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
            )
            
        except Exception as e:
            llm_end_time = datetime.now()
            
            # Record error
            monitoring = get_monitoring_service()
            monitor_context = AIUsageContext(
                user_id=state.get("user_id"),
                tenant_id=state.get("tenant_id"),
                team_id=state.get("team_id"),
                project_id=state.get("project_id"),
                feature_id="pgen_curator_selection",
                workflow_name="problem_generator_workflow",
                step_name="curator_selector",
                environment="prod",
                request_id=state.get("job_id")
            )
            
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitor_context,
                    provider="azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai",
                    model_name=llm_config.model_name,
                    operation_type="responses_api",
                    started_at=llm_start_time,
                    finished_at=llm_end_time,
                    status="error",
                    error_type=type(e).__name__
                )
            )
            
            # FALLBACK: Use top ranked statements directly when LLM curation fails
            logger.warning(f"LLM curation failed ({str(e)}), using fallback: top {min(5, len(top_statements))} ranked statements")
            
            # Create fallback curation result using top statements by relevance score
            fallback_count = min(5, max(3, len(top_statements)))
            response = type('FallbackResponse', (), {
                'arguments': {
                    'selected_statements': list(range(fallback_count)),
                    'selection_reasoning': [f"Fallback selection #{i+1} - selected by relevance score" for i in range(fallback_count)],
                    'diversity_analysis': "Fallback selection based on relevance ranking (LLM curation unavailable)",
                    'total_selected': fallback_count
                }
            })()
            logger.info(f"Using fallback curation with {fallback_count} statements")
        
        logger.info(f"LLM curation response received: {response}")
        
        if not response or not response.arguments:
            logger.error(f"Failed to get curation response from LLM. Response: {response}")
            raise ValueError("Failed to get curation response from LLM")
        
        curation_result = response.arguments
        logger.info(f"Curation result: {curation_result}")
        
        # =============================================
        # PROCESS CURATION RESULTS
        # =============================================
        
        selected_indices = curation_result.get("selected_statements", [])
        selection_reasoning = curation_result.get("selection_reasoning", [])
        diversity_analysis = curation_result.get("diversity_analysis", "")
        total_selected = curation_result.get("total_selected", 0)
        
        # Validate selection
        if not selected_indices or len(selected_indices) < 3 or len(selected_indices) > 5:
            logger.warning(f"Invalid selection count: {len(selected_indices)}, using fallback selection")
            selected_indices = list(range(min(5, len(top_statements))))
        
        # Create final problem statements
        final_statements = []
        
        for i, statement_idx in enumerate(selected_indices):
            if 0 <= statement_idx < len(top_statements):
                statement = top_statements[statement_idx].copy()
                
                # Transform detailed statement to concise cause-and-effect format
                detailed_statement = statement.get("statement", "")
                geography = statement.get("geography", "")
                impact_focus = statement.get("impact_focus", "")
                category = statement.get("category", "")
                source_uuids = statement.get("source_uuids", [])
                
                logger.info(f"Transforming statement {i+1} to concise format...")
                concise_statement = await transform_to_concise_problem_statement(
                    detailed_statement, geography, impact_focus, category
                )
                
                # Merge sources from both statement refiner and curator registry
                existing_sources = statement.get("supporting_sources", [])
                source_registry = state.get("source_registry", {})
                
                logger.info(f"Source registry has {len(source_registry)} entries")
                logger.info(f"Statement {i+1} has {len(source_uuids)} source UUIDs: {source_uuids}")
                logger.info(f"Existing sources from refiner: {len(existing_sources)} sources")
                
                # Start with sources from curator registry (richer metadata)
                registry_sources = []
                for j, uuid in enumerate(source_uuids):
                    source_info = source_registry.get(uuid, {})
                    if source_info:
                        registry_sources.append({
                            "citation_number": j + 1,
                            "source_uuid": uuid,
                            "url": source_info.get("url", ""),
                            "title": source_info.get("title", ""),
                            "domain": source_info.get("domain", ""),
                            "publication_date": source_info.get("publication_date"),
                            "author": source_info.get("author"),
                            "credibility_score": source_info.get("credibility_score", 5.0),
                            "content_type": source_info.get("content_type", "article")
                        })
                        logger.info(f"Added registry source {j+1}: {source_info.get('title', 'No title')[:50]}...")
                    else:
                        logger.warning(f"Source UUID {uuid} not found in source registry")
                
                # Merge with existing sources from refiner (comprehensive deduplication)
                supporting_sources = registry_sources.copy()
                
                # Create comprehensive deduplication keys (URL + title combination)
                existing_source_keys = set()
                for src in registry_sources:
                    url = src.get("url", "").strip()
                    title = src.get("title", "").strip()
                    # Create a unique key combining URL and title
                    source_key = f"{url}|{title}".lower()
                    existing_source_keys.add(source_key)
                
                for refiner_source in existing_sources:
                    refiner_url = refiner_source.get("url", "").strip()
                    refiner_title = refiner_source.get("title", "").strip()
                    refiner_key = f"{refiner_url}|{refiner_title}".lower()
                    
                    # Only add if this exact combination doesn't exist
                    if refiner_key and refiner_key not in existing_source_keys:
                        # Add unique sources from refiner with incremented citation numbers
                        refiner_source_copy = refiner_source.copy()
                        refiner_source_copy["citation_number"] = len(supporting_sources) + 1
                        supporting_sources.append(refiner_source_copy)
                        existing_source_keys.add(refiner_key)  # Track this addition
                        logger.info(f"Added refiner source: {refiner_source.get('title', refiner_url)[:50]}...")
                    else:
                        logger.info(f"Skipped duplicate source: {refiner_title[:50]}...")
                
                # Final deduplication pass to ensure no duplicates within the final list
                final_sources = []
                final_source_keys = set()
                
                for src in supporting_sources:
                    url = src.get("url", "").strip()
                    title = src.get("title", "").strip()
                    source_key = f"{url}|{title}".lower()
                    
                    if source_key not in final_source_keys:
                        # Reassign citation numbers sequentially
                        src["citation_number"] = len(final_sources) + 1
                        final_sources.append(src)
                        final_source_keys.add(source_key)
                
                supporting_sources = final_sources
                logger.info(f"Final merged sources after deduplication: {len(supporting_sources)} total sources")
                
                # Generate detailed analysis for frontend
                logger.info(f"Generating detailed analysis for statement {i+1}...")
                detailed_analysis = await generate_detailed_analysis(
                    concise_statement,
                    detailed_statement,
                    geography,
                    impact_focus,
                    category
                )
                
                # Restructure the statement for better frontend organization
                # Core statement information
                statement["problem_statement"] = concise_statement  # Concise problem statement
                statement["detailed_explanation"] = detailed_statement  # Detailed explanation
                
                # Contextual information
                statement["industry"] = category  # Industry/category
                statement["geography"] = geography  # Geographic focus
                statement["impact_focus"] = impact_focus  # Target impact focus
                
                # Detailed analysis sections
                statement["root_causes"] = detailed_analysis["root_causes"]
                statement["potential_effects"] = detailed_analysis["potential_effects"]
                statement["stakeholders"] = detailed_analysis["stakeholders"]
                statement["success_metrics"] = detailed_analysis["success_metrics"]
                
                # Source information
                statement["supporting_sources"] = supporting_sources  # Rich source metadata
                logger.info(f"Statement {i+1} final supporting_sources count: {len(supporting_sources)}")
                if supporting_sources:
                    logger.info(f"First source: {supporting_sources[0]}")
                
                # Inject citation references into detailed explanation if sources are available
                if supporting_sources and statement["detailed_explanation"]:
                    detailed_explanation = statement["detailed_explanation"]
                    # Check if citations are already present
                    if not any(f"[{i+1}]" in detailed_explanation for i in range(len(supporting_sources))):
                        logger.info(f"Injecting {len(supporting_sources)} citations into detailed explanation for statement {i+1}")
                        
                        # Split text into sentences, preserving the separators
                        sentences = []
                        sentence_parts = re.split(r'([.!?]\s)', detailed_explanation)
                        
                        # Recombine the parts to get complete sentences with their ending punctuation
                        i = 0
                        while i < len(sentence_parts):
                            if i + 1 < len(sentence_parts) and re.match(r'[.!?]\s', sentence_parts[i+1]):
                                sentences.append(sentence_parts[i] + sentence_parts[i+1])
                                i += 2
                            else:
                                sentences.append(sentence_parts[i])
                                i += 1
                        
                        # Filter out empty sentences
                        sentences = [s for s in sentences if s.strip()]
                        
                        # Add citations to sentences, distributed evenly
                        modified_sentences = []
                        citations_added = 0
                        
                        # Calculate how many sentences to add citations to
                        # Aim for approximately 1 citation per source, evenly distributed
                        if len(sentences) >= len(supporting_sources):
                            # If we have enough sentences, distribute sources evenly
                            citation_interval = max(1, len(sentences) // len(supporting_sources))
                            for idx, sentence in enumerate(sentences):
                                if idx > 0 and idx % citation_interval == 0 and citations_added < len(supporting_sources):
                                    citation_idx = citations_added
                                    modified_sentences.append(f"{sentence.rstrip()} [{citation_idx + 1}] ")
                                    citations_added += 1
                                else:
                                    modified_sentences.append(sentence)
                        else:
                            # If we have fewer sentences than sources, add one citation to each sentence
                            for idx, sentence in enumerate(sentences):
                                if citations_added < len(supporting_sources):
                                    citation_idx = citations_added
                                    modified_sentences.append(f"{sentence.rstrip()} [{citation_idx + 1}] ")
                                    citations_added += 1
                                else:
                                    modified_sentences.append(sentence)
                        
                        # Update the detailed explanation with citations
                        statement["detailed_explanation"] = ''.join(modified_sentences)
                        logger.info(f"Added {citations_added} citations to detailed explanation for statement {i+1}")
                
                # Add curation metadata
                statement["final_rank"] = i + 1
                statement["selection_reasoning"] = (
                    selection_reasoning[i] if i < len(selection_reasoning) 
                    else "Selected based on relevance and quality"
                )
                statement["curated_at"] = datetime.now().isoformat()
                
                # Debug: Log final statement structure
                logger.info(f"Final statement {i+1} keys: {list(statement.keys())}")
                logger.info(f"Final statement {i+1} supporting_sources: {len(statement.get('supporting_sources', []))} sources")
                
                final_statements.append(statement)
        
        # =============================================
        # ADD FINAL METADATA
        # =============================================
        
        curation_metadata = {
            "total_candidates": len(ranked_statements),
            "considered_for_curation": len(top_statements),
            "final_selected": len(final_statements),
            "diversity_analysis": diversity_analysis,
            "curation_model": model_name,
            "categories_selected": list(set(s.get("category", "") for s in final_statements)),
            "geographies_selected": list(set(s.get("geography", "") for s in final_statements)),
            "avg_relevance_score": sum(s.get("relevance_score", 0) for s in final_statements) / max(len(final_statements), 1),
            "avg_quality_score": sum(s.get("quality_score", 0) for s in final_statements) / max(len(final_statements), 1)
        }
        
        # =============================================
        # STORE FINAL RESULTS
        # =============================================
        
        state["final"] = final_statements
        state["curation_metadata"] = curation_metadata
        state["status"] = "completed"
        
        # Add processing metrics
        total_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        curation_metrics = {
            "candidates_considered": len(top_statements),
            "final_statements": len(final_statements),
            "selection_rate": len(final_statements) / max(len(top_statements), 1),
            "avg_final_relevance": curation_metadata["avg_relevance_score"],
            "avg_final_quality": curation_metadata["avg_quality_score"],
            "processing_time_ms": total_time
        }
        
        if "processing_metrics" not in state:
            state["processing_metrics"] = {}
        state["processing_metrics"]["curator_selector"] = curation_metrics
        
        logger.info(f"Final curation completed successfully")
        logger.info(f"Selected {len(final_statements)} final problem statements")
        logger.info(f"Categories: {curation_metadata['categories_selected']}")
        logger.info(f"Geographies: {curation_metadata['geographies_selected']}")
        
        # Log final statements
        for i, statement in enumerate(final_statements, 1):
            logger.info(f"Final #{i}: {statement['statement'][:100]}...")
        
        return state
        
    except Exception as e:
        error_msg = f"Final curation failed: {str(e)}"
        logger.error(error_msg)
        state["error"] = error_msg
        state["status"] = "failed"
        return state