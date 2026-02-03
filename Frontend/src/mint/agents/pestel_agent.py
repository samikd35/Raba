"""
PESTEL Analysis Agent for the MINT platform.

This agent processes a research specification and generates a structured PESTEL analysis
report by orchestrating a multi-step research pipeline: search, extraction, analysis, and synthesis.
The PESTEL framework covers Political, Economic, Social, Technological, Environmental, and Legal factors.
"""

import asyncio
import json
import logging
import os
import pickle
import random
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Literal, Union
from pydantic import BaseModel, Field, AnyHttpUrl

from src.mint.agents.report_templates import PESTEL_REPORT_PROMPT
from src.mint.agents.enhanced_report_parser import get_enhanced_parser, ReportParsingError
from src.mint.agents.json_validator import get_validator, validate_json_response, generate_report_with_validation, PESTEL_REPORT_SCHEMA
from monitor.tokens.service import get_monitoring_service
from monitor.tokens.models import AIUsageContext

# Custom JSON encoder for Pydantic models
class PydanticJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle Pydantic models and special types."""
    def default(self, obj):
        # Handle Pydantic models
        if hasattr(obj, 'model_dump'):
            # For Pydantic v2+
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            # For older Pydantic versions
            return obj.dict()
        
        # Handle HttpUrl type from Pydantic
        if obj.__class__.__name__ == 'HttpUrl':
            return str(obj)
        
        # Handle AnyHttpUrl type from Pydantic
        if obj.__class__.__name__ == 'AnyHttpUrl':
            return str(obj)
        
        # Handle any URL-like objects with __str__ method
        if hasattr(obj, '__str__') and ('Url' in obj.__class__.__name__ or 'URL' in obj.__class__.__name__):
            return str(obj)
            
        return super().default(obj)

# PESTEL Mini-Report data model
class PESTELMiniReport(BaseModel):
    """Data model for standardized PESTEL mini-report
    
    Contains structured analysis of PESTEL factors with supporting facts,
    organized sections, and strategic recommendations.
    """
    title: str = Field(..., description="Title of the PESTEL analysis report")
    summary: str = Field(..., description="Executive summary of PESTEL findings")
    analysis: List[Dict[str, Any]] = Field(default_factory=list, description="Structured analysis sections with subsections")
    recommendations: List[str] = Field(default_factory=list, description="Strategic recommendations based on PESTEL analysis")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source references with numbers and URLs")
    
    @classmethod
    def from_facts(cls, title: str, summary: str, analysis: List[Dict[str, Any]] = None, recommendations: List[str] = None):
        """Factory method to create a PESTELMiniReport with proper type conversions
        
        Args:
            title: The title of the PESTEL report
            summary: Executive summary of findings
            analysis: Structured analysis sections with subsections
            recommendations: Strategic recommendations based on analysis
            
        Returns:
            PESTELMiniReport: A properly formatted PESTEL mini report
        """
        return cls(
            title=title,
            summary=summary,
            analysis=analysis or [],
            recommendations=recommendations or []
        )

# DISABLED: LangSmith causes memory issues with large payloads (61MB+)
# Enable LangSmith tracing if API key is available
# if os.environ.get("LANGSMITH_API_KEY"):
#     try:
#         from langsmith.run_helpers import traceable
#     except (ImportError, AttributeError):
if True:  # Always use dummy traceable
        # Create a no-op decorator if langsmith is not properly installed
        def traceable(name=None):
            def decorator(func):
                return func
            return decorator
else:
    # Create a no-op decorator when LangSmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator

from src.mint.utils.config import get_config
from src.mint.agents.agent_config import get_agent_config, get_llm_config, get_search_config, get_hybrid_search_strategy

from src.mint.api.ai.providers import (
    LLMProvider,
    OpenAIProvider,
    GeminiProvider,
    LLMToolResponse,
    ProviderError,
)
from src.mint.api.ai.models import (
    ModelProvider,
    ModelUseCase
)
from src.mint.api.ai.config import (
    get_client_config,
    get_provider_with_fallback
)
from src.mint.providers.search import (
    BraveSearchProvider,
    TavilySearchProvider,
    SerperSearchProvider,
    SearchConfig,
    ProviderError as SearchProviderError,
)
from src.mint.schemas.schemas import Fact, MiniReport, ResearchSpec

# Configure logging
logger = logging.getLogger(__name__)

# Define a custom agent error
class PESTELAgentError(Exception):
    """Error raised when the PESTEL agent encounters an irrecoverable failure."""
    pass


# Define PESTEL pillar type
PESTELPillar = Literal["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]


# Extend the Fact model with additional metadata for internal use
class EnhancedPESTELFact(Fact):
    """
    Extended fact with source metadata, confidence score, and PESTEL categorization.
    
    This extends the base Fact model with additional metadata needed for
    fact validation, source tracking, PESTEL categorization, and reference management
    throughout the research pipeline.
    """
    source_url: Union[AnyHttpUrl, str]
    source_title: str
    confidence: float = 0.7  # Default confidence
    source_date: Optional[str] = None  # Publication date if available
    source_author: Optional[str] = None  # Author if available
    reference_id: str = Field(default_factory=lambda: f"ref-{uuid.uuid4().hex[:8]}")  # Unique reference ID
    pestel_pillar: PESTELPillar  # PESTEL categorization (Political, Economic, Social, Technological, Environmental, Legal)
    
    def get_citation_markdown(self) -> str:
        """
        Generate a properly formatted citation in markdown.
        
        Returns:
            Markdown citation with link to source
        """
        return f"[{self.source_title}]({self.source_url})"
    
    def get_citation_text(self) -> str:
        """
        Generate a properly formatted citation in plain text.
        
        Returns:
            Text citation with source information
        """
        citation = f"{self.source_title}"
        if self.source_author:
            citation = f"{self.source_author}, {citation}"
        if self.source_date:
            citation += f" ({self.source_date})"
        return citation


# This would be imported from a search provider module in the full implementation
class SearchResult(BaseModel):
    """Search result from a search provider."""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PESTELEntities(BaseModel):
    """Extracted entities from a research specification for PESTEL analysis."""
    industry_names: List[str]
    geography_names: List[str]
    timeframe: Optional[str] = None
    target_segments: List[str] = []
    key_topics: List[str] = []
    expected_output_sections: List[str] = []  # Should include the PESTEL categories
    political_factors: List[str] = []  # Specific political factors to research
    economic_factors: List[str] = []  # Specific economic factors to research
    social_factors: List[str] = []  # Specific social factors to research
    technological_factors: List[str] = []  # Specific technological factors to research
    environmental_factors: List[str] = []  # Specific environmental factors to research
    legal_factors: List[str] = []  # Specific legal factors to research


class SourceDocument(BaseModel):
    """Extracted content from a source URL with rich metadata for reference tracking."""
    title: str
    url: str
    source: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    storage_uri: Optional[str] = None
    relevance_score: float = 0.0  # Relevance score from 0.0 to 1.0
    trust_score: float = 0.0      # Trust score from 0.0 to 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata for reference tracking


def _get_llm_provider(state: Dict[str, Any] = None) -> tuple[LLMProvider, str, str]:
    """Get LLM provider with Azure OpenAI support for report generation.
    
    PESTEL Agent uses REPORT_GENERATION use case which maps to gpt-4.1 deployment.
    
    Returns:
        Tuple of (provider, model_name, provider_type) for monitoring
    """
    from src.mint.api.ai.models import LLMConfig
    
    # Use centralized Azure OpenAI configuration for report generation
    provider_type, model_name, client_config = get_client_config(ModelUseCase.REPORT_GENERATION)
    
    # Get legacy config for temperature and max_tokens if available
    llm_config = get_llm_config(state) if state else get_config().get_llm_config()
    
    # Extract temperature and max_tokens from legacy config or use defaults
    openai_config = llm_config.get("openai", {})
    temperature = openai_config.get("temperature", 0.2)
    max_tokens = openai_config.get("max_tokens", 32000)
    
    # Create LLMConfig with Azure OpenAI or OpenAI model using gpt-5-mini pattern
    if provider_type == ModelProvider.AZURE_OPENAI:
        logger.info(f"PESTEL Agent using Azure OpenAI gpt-5-mini: {model_name} for report generation")
        llm_config_obj = LLMConfig(
            model_name=model_name,  # gpt-5-mini deployment
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name="openai",  # Use openai provider with base_url
            azure_endpoint=client_config.get("azure_endpoint"),
            api_version=client_config.get("api_version"),
            api_key=client_config.get("api_key"),
            base_url=client_config.get("base_url")  # For gpt-5-mini pattern
        )
    else:
        logger.info(f"PESTEL Agent using OpenAI model: {model_name} for report generation")
        llm_config_obj = LLMConfig(
            model_name=model_name,  # OpenAI model name
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name="openai",
            api_key=client_config.get("api_key")
        )
    
    provider = OpenAIProvider(config=llm_config_obj)
    
    # Determine provider name for monitoring
    provider_name = "azure_openai" if provider_type == ModelProvider.AZURE_OPENAI else "openai"
    
    return provider, model_name, provider_name


@traceable(name="_compose_pestel_report")
async def _compose_pestel_report(facts: List[EnhancedPESTELFact], entities: PESTELEntities, spec: ResearchSpec, state: Dict[str, Any] = None) -> MiniReport:
    """
    Compose a structured mini-report from validated facts, organized by PESTEL pillars.
    
    Args:
        facts: List of validated facts with PESTEL tagging
        entities: Extracted entities from research specification
        spec: Research specification
        
    Returns:
        A structured MiniReport with PESTEL analysis
    """
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Prepare monitoring context for report generation
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_pestel",
        workflow_name="pv_report_workflow",
        step_name="report_generation",
        environment="prod"
    )
    
    # Define the report structure tool
    report_tool = {
        "type": "function",
        "function": {
            "name": "generate_pestel_report",
            "description": "Generate a structured PESTEL analysis report focusing on industry challenges",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the PESTEL report"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Executive summary of the PESTEL analysis focusing on key industry challenges (20-40 words, extremely concise)"
                    },
                    "sections": {
                        "type": "object",
                        "description": "Report sections organized by traditional PESTEL framework pillars as keys",
                        "additionalProperties": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "Section content with analysis of challenges and implications (part of 300-600 words total content)"
                                    },
                                    "key_points": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Key points for this section (3-5 points)"
                                    },
                                    "source_url": {
                                        "type": "string",
                                        "description": "URL of the source document"
                                    },
                                    "source_title": {
                                        "type": "string",
                                        "description": "Title of the source document"
                                    }
                                },
                                "required": ["content"]
                            }
                        }
                    },
                    "facts": {
                        "type": "array",
                        "description": "Collection of factual information supporting the analysis",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The factual statement"
                                },
                                "source_url": {
                                    "type": "string",
                                    "description": "URL of the source document"
                                },
                                "source_title": {
                                    "type": "string",
                                    "description": "Title of the source document"
                                }
                            },
                            "required": ["content", "source_url", "source_title"]
                        }
                    },
                    "conclusion": {
                        "type": "string",
                        "description": "Comprehensive conclusion summarizing the analysis and strategic implications (30-60 words)"
                    },
                    "limitations": {
                        "type": "array",
                        "description": "Limitations in the analysis",
                        "items": {"type": "string"}
                    },
                    "challenges": {
                        "type": "array",
                        "description": "Industry challenges identified across multiple dimensions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "challenge": {
                                    "type": "string",
                                    "description": "Description of the challenge"
                                },
                                "impact": {
                                    "type": "string",
                                    "description": "Impact of this challenge on the industry"
                                }
                            },
                            "required": ["challenge"]
                        }
                    }
                },
                "required": ["title", "summary", "sections", "conclusion"]
            }
        }
    }
    
    # Prepare comprehensive system message for detailed PESTEL reporting
    system_message = """
    You are an expert business analyst specializing in PESTEL analysis with deep expertise in industry research.
    Your task is to synthesize the provided facts into a comprehensive, detailed, and well-structured PESTEL report.
    
    Follow these detailed guidelines:
    1. Create a clear, specific title relevant to the industry and geography that captures the analysis scope
    2. Write a brief executive summary (20-40 words) highlighting key findings and challenges
    3. Organize content into the traditional PESTEL framework sections:
       - Political
       - Economic
       - Social
       - Technological
       - Environmental
       - Legal
    4. For each section:
       a. Write a detailed analysis with all sections totaling 300-600 words for the entire content
       b. Synthesize facts into coherent, flowing paragraphs with logical structure
       c. Analyze implications and connections between factors
       d. Include specific data points, statistics, and trends when available
       e. Extract 3-5 key points that summarize critical insights for decision-makers
    5. Write a comprehensive conclusion (30-60 words) analyzing strategic implications
    6. Document any limitations transparently
    
    Important formatting requirements for JSON output:
    - Create your output as a valid JSON object following the provided schema exactly
    - Format sections as an object with pillar names as keys and arrays of content objects as values
    - For each section, include only the essential fields: content, key_points, source_url, and source_title
    - For facts, include only the essential fields: content, source_url, and source_title
    - For challenges, include only the challenge description and impact when available
    - DO NOT include metadata fields like confidence scores, extracted_at timestamps, categories, or other non-essential fields
    - The final JSON structure must be valid and parseable
    
    Content guidelines:
    - Treat all facts as a unified collection - do not filter out facts based on pillar categorization
    - Focus on industry challenges and implications across all dimensions
    - Feel free to discuss facts that span multiple pillars where they make the most logical sense
    - Create connections between different factors where appropriate
    
    Use formal, professional language appropriate for business stakeholders and C-suite executives.
    Focus on insights, strategic implications, and business impact - not just restatement of facts.
    When appropriate, indicate connections between different PESTEL pillars to show systemic relationships.
    Ensure references to sources are maintained throughout the analysis.
    """
    
    # Create structured references system for citation and traceability
    references = {}
    reference_counter = 1
    
    # Group facts by pillar for report composition, but don't filter any out
    logger.info(f"Organizing {len(facts)} total facts for PESTEL report generation")
    
    # Create a collection of all facts
    all_facts = []
    
    # Organize facts by pillar for reporting, but ALSO keep a unified list
    facts_by_pillar = {}
    facts_without_pillar = []
    
    for fact in facts:
        # Add to all_facts list regardless of pillar
        if hasattr(fact, 'content') and fact.content:
            all_facts.append(fact)
        
        # Use pestel_pillar attribute if available
        if hasattr(fact, 'pestel_pillar') and fact.pestel_pillar:
            pillar = fact.pestel_pillar
            if pillar not in facts_by_pillar:
                facts_by_pillar[pillar] = []
            facts_by_pillar[pillar].append(fact)
        else:
            # Store facts without pillar separately
            facts_without_pillar.append(fact)
            # Try to infer pillar but don't force a classification
            if hasattr(fact, 'content') and fact.content:
                inferred_pillar = _infer_pestel_pillar(fact.content)
                if inferred_pillar:
                    if inferred_pillar not in facts_by_pillar:
                        facts_by_pillar[inferred_pillar] = []
                    facts_by_pillar[inferred_pillar].append(fact)
                    logger.info(f"Inferred pillar {inferred_pillar} for fact: {fact.content[:50]}...")
                else:
                    logger.info(f"Could not infer pillar for fact: {fact.content[:50]}...")
                    
    logger.info(f"Total facts: {len(all_facts)}, Facts without specific pillar: {len(facts_without_pillar)}")
    logger.info(f"All facts will be included in the analysis regardless of pillar assignment")
    
    # Log fact distribution across pillars for visibility
    for pillar, pillar_facts in facts_by_pillar.items():
        logger.info(f"Pillar {pillar}: {len(pillar_facts)} facts for report generation")
    
    # Ensure all pillars are represented in the dictionary
    for pillar in ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]:
        if pillar not in facts_by_pillar:
            facts_by_pillar[pillar] = []
            logger.info(f"No facts found for {pillar} pillar, initializing empty list")
    
    # Format facts with enhanced reference system for report generation
    formatted_facts = []
    for pillar, pillar_facts in facts_by_pillar.items():
        facts_for_pillar = []
        for fact in pillar_facts:
            # Create a reference ID if this source hasn't been referenced before
            source_key = f"{fact.source_url}:{fact.source_title}"
            if source_key not in references:
                ref_id = f"ref-{reference_counter}"
                reference_counter += 1
                references[source_key] = {
                    "id": ref_id,
                    "title": fact.source_title or "Unknown Source",
                    "url": fact.source_url or "",
                    "date": fact.publication_date if hasattr(fact, 'publication_date') else "",
                    "citation_count": 1
                }
            else:
                ref_id = references[source_key]["id"]
                references[source_key]["citation_count"] += 1
            
            # Format the fact with reference ID for citation - only include essential fields
            facts_for_pillar.append({
                "statement": fact.content,
                "source": fact.source_title,
                "url": fact.source_url,
                "reference_id": ref_id
            })
        
        # Structure facts for each pillar without adding unnecessary pillar field
        formatted_facts.append({
            "section": pillar,
            "facts": facts_for_pillar
        })
    
    # Prepare comprehensive user message with rich context and all facts
    user_message = f"""
    Research Specification:
    Title: {spec.title}
    Description: {spec.description}
    Industry Focus: {', '.join(spec.industry_focus)}
    Geography Focus: {', '.join(spec.geography_focus)}
    Time Period: {spec.time_period if hasattr(spec, 'time_period') and spec.time_period else 'Current'}
    
    References:
    {json.dumps([{"id": ref_data["id"], "title": ref_data["title"], "url": ref_data["url"]} 
               for ref_data in references.values()], indent=2, cls=PydanticJSONEncoder)}
    
    Research Facts (Include appropriate reference IDs in your analysis):
    {json.dumps(formatted_facts, indent=2, cls=PydanticJSONEncoder)}
    
    Create a comprehensive and detailed analysis report focusing on industry challenges based on these facts.
    The report should be detailed (300-600 words total for all content sections combined, 20-40 words for summary, 30-60 words for conclusion) with proper academic citations using the reference IDs.
    While organizing content within the traditional PESTEL framework, focus primarily on industry challenges and their implications.
    
    IMPORTANT - Output Format Requirements:
    1. Your output MUST follow the JSON schema provided exactly
    2. Format sections as an object with pillar names as keys (e.g., "Political", "Economic", etc.)
    3. For each section, include ONLY the fields: content, key_points, source_url, and source_title
    4. For facts, include ONLY the fields: content, source_url, and source_title
    5. For challenges, include ONLY the challenge description and impact
    6. DO NOT include metadata fields like confidence scores, extracted_at timestamps, or other non-essential fields
    7. The final JSON structure must be valid and parseable
    
    Include strategic business implications for each factor and conclude with actionable recommendations.
    Structure your analysis with logical flow and appropriate subsections.
    Ensure all relevant facts are incorporated regardless of pillar categorization.
    """
    
    try:
        # Make API call with tool calling
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        try:
            logger.info("📝 Calling LLM for PESTEL report generation...")
            report_started_at = datetime.now()
            response = await asyncio.wait_for(
                llm.generate_responses_with_tools(messages, [report_tool]),
                timeout=180.0  # 3 minutes for report generation (complex task)
            )
            logger.info("✅ PESTEL report generation LLM call completed")
            
            # Record report generation AI usage
            report_finished_at = datetime.now()
            usage = getattr(response, 'usage', {}) or {}
            asyncio.create_task(
                monitoring.record_ai_usage(
                    context=monitoring_context,
                    provider="azure_openai",
                    model_name=getattr(response, 'model', 'gpt-5-mini'),
                    operation_type="responses_api",
                    started_at=report_started_at,
                    finished_at=report_finished_at,
                    status="success",
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens'),
                    extra_metadata={"step": "pestel_report_generation"}
                )
            )
            
            report_data = response.arguments if response.arguments else {}
            
            # Validate and ensure required keys exist
            if not report_data or "sections" not in report_data or not report_data.get("sections"):
                logger.warning("Missing or empty 'sections' in LLM response, adding default sections structure")
                report_data["sections"] = {}
                for pillar in ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]:
                    report_data["sections"][pillar] = [{
                        "content": f"No {pillar.lower()} factors were analyzed.",
                        "key_points": []
                    }]
            elif isinstance(report_data["sections"], list):
                # Convert from array format to object format
                logger.warning("Converting sections from array to object format")
                sections_dict = {}
                for section in report_data["sections"]:
                    if "title" in section:
                        pillar = section["title"]
                        sections_dict[pillar] = [{
                            "content": section.get("content", ""),
                            "key_points": section.get("key_points", [])
                        }]
                report_data["sections"] = sections_dict
        except Exception as e:
            logger.error(f"Error calling LLM tool: {str(e)}")
            # Create a fallback report with minimal structure - using object with pillar keys for sections
            logger.info("Creating fallback report due to LLM tool error")
            report_data = {
                "title": spec.title,
                "summary": "Analysis could not be completed due to technical issues. Please see the raw facts below.",
                "sections": {}
            }
            
            # Create basic sections for each PESTEL pillar as a dictionary
            for pillar in ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]:
                pillar_facts = [f for f in facts if hasattr(f, 'pestel_pillar') and f.pestel_pillar == pillar]
                content = f"Facts related to {pillar} factors:\n\n"
                
                # Add raw facts to the content
                for fact in pillar_facts:
                    content += f"- {fact.content} (Source: {fact.source_title or 'Unknown'})\n"
                
                # Add section to dictionary with pillar as key
                report_data["sections"][pillar] = [{
                    "content": content or f"No {pillar} factors were identified.",
                    "key_points": []
                }]
            
            # Add basic conclusion
            report_data["conclusion"] = "Analysis was limited due to technical issues. Please refer to the raw facts in each section."
            
            # Add simple limitations note
            report_data["limitations"] = ["Analysis was conducted based solely on available facts."]
            
            # Add empty challenges list
            report_data["challenges"] = []
        
        # Construct the MiniReport
        title = report_data.get("title", "PESTEL Analysis")
        
        # Build content with markdown formatting
        content = f"# {title}\n\n"
        content += f"## Executive Summary\n\n{report_data.get('summary', 'No summary available.')}\n\n"
        
        # Add sections for each PESTEL pillar - sections are now an object with pillar keys
        if isinstance(report_data.get("sections", {}), dict):
            # Handle new format: sections as an object with pillar names as keys
            for pillar_name, section_data in report_data["sections"].items():
                content += f"## {pillar_name}\n\n"
                
                # Check if section_data is a list (array of content) or a direct object
                if isinstance(section_data, list):
                    # Handle array of content objects
                    for item in section_data:
                        if isinstance(item, dict) and "content" in item:
                            content += f"{item['content']}\n\n"
                            
                            # Only add key points if they exist in the item
                            if "key_points" in item and item["key_points"]:
                                content += "**Key Points:**\n"
                                for point in item["key_points"]:
                                    content += f"* {point}\n"
                                content += "\n"
                else:
                    # Handle direct content object
                    if isinstance(section_data, dict) and "content" in section_data:
                        content += f"{section_data['content']}\n\n"
                        
                        # Only add key points if they exist
                        if "key_points" in section_data and section_data["key_points"]:
                            content += "**Key Points:**\n"
                            for point in section_data["key_points"]:
                                content += f"* {point}\n"
                            content += "\n"
        elif isinstance(report_data.get("sections", []), list):
            # Handle original format for backward compatibility
            for section in report_data["sections"]:
                title = section.get('title', '') or section.get('pillar', '')
                content += f"## {title}\n\n{section.get('content', '')}\n\n"
                
                # Only add key points if they exist in the section
                if "key_points" in section and section["key_points"]:
                    content += "**Key Points:**\n"
                    for point in section["key_points"]:
                        content += f"* {point}\n"
                    content += "\n"
        
        # Add conclusion if available
        if "conclusion" in report_data and report_data["conclusion"]:
            content += f"## Conclusion\n\n{report_data['conclusion']}\n\n"
        else:
            content += "## Conclusion\n\nAnalysis complete. Please refer to the sections above for key findings across all PESTEL dimensions.\n\n"
        
        # Add challenges if available (new section)
        if "challenges" in report_data and report_data["challenges"]:
            content += "## Key Industry Challenges\n\n"
            for challenge in report_data["challenges"]:
                content += f"* {challenge}\n"
            content += "\n"
        
        # Add limitations if available
        if "limitations" in report_data and report_data["limitations"]:
            content += "## Limitations\n\n"
            for limitation in report_data["limitations"]:
                content += f"* {limitation}\n"
        
        # Extract a proper summary from the executive summary section
        # Look for the Executive Summary section and extract its content
        summary = ""
        content_parts = content.split('## Executive Summary')
        if len(content_parts) > 1:
            summary_section = content_parts[1].split('##')[0].strip()
            summary = summary_section
        else:
            # Fallback: Extract first substantial paragraph as summary
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if len(para.strip()) > 100:  # Find first substantial paragraph
                    summary = para
                    break
            if not summary:  # If still no summary, use first paragraph
                summary = paragraphs[0] if paragraphs else content
        
        # Create structured sections with proper formatting and citation preservation
        formatted_sections = {}
        
        # Process each PESTEL pillar to create structured sections
        for pillar in ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]:
            # Find the content for this pillar
            section_content = ""
            section_match = re.search(f'## {pillar}[^#]*', content)
            if section_match:
                section_content = section_match.group(0)
            
            # Create facts for this section with proper attribution
            if section_content:
                section_facts = []
                
                # Extract the main content paragraphs
                content_paragraphs = section_content.split('**Key Points:**')[0] if '**Key Points:**' in section_content else section_content
                
                # Break into logical chunks while preserving headers and structure
                chunks = []
                current_chunk = ""
                for line in content_paragraphs.strip().split('\n'):
                    if line.startswith('###'):  # Subsection header
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = line + "\n"
                    else:
                        current_chunk += line + "\n"
                        if line.strip() == "" and current_chunk.strip():
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                
                # Add the final chunk if not empty
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Build a database of URLs from all facts, indexed by content snippets for fuzzy matching
                # This should be above the chunk processing loop to build the URL database once
                all_urls = {}
                references_by_pillar = {}
                
                # Build URL database from facts
                for p, facts_list in facts_by_pillar.items():
                    if p not in references_by_pillar:
                        references_by_pillar[p] = {}
                        
                    for fact in facts_list:
                        # Skip facts without valid URLs
                        if not hasattr(fact, 'source_url') or not fact.source_url:
                            continue
                            
                        # Use content snippets as keys for content matching later
                        content_snippet = fact.content[:100]
                        all_urls[content_snippet] = {
                            'url': fact.source_url,
                            'title': fact.source_title if hasattr(fact, 'source_title') else None
                        }
                        
                        # If the fact has a reference_id, store it for reference matching
                        if hasattr(fact, 'reference_id') and fact.reference_id:
                            references_by_pillar[p][fact.reference_id] = {
                                'url': fact.source_url,
                                'title': fact.source_title if hasattr(fact, 'source_title') else None
                            }
                            
                # Log URL database stats
                logger.info(f"Built URL database with {len(all_urls)} entries from facts")
                for p, refs in references_by_pillar.items():
                    logger.info(f"Pillar {p}: {len(refs)} reference IDs with URLs")
                
                # Create a Fact for each substantive chunk
                for chunk in chunks:
                    if len(chunk.strip()) > 20:  # Only include substantive content
                        source_url = None
                        source_title = f"PESTEL Report: {pillar}"
                        
                        # Find the best URL match for this chunk from our original facts
                        # First try to get a URL from a similar content match
                        for key, url_data in all_urls.items():
                            if key in chunk or chunk[:50] in key:
                                source_url = url_data['url']
                                if url_data['title']:
                                    source_title = url_data['title']
                                break
                        
                        # If no URL found from content matching, get the first available URL from a fact in this pillar
                        if not source_url and pillar in facts_by_pillar and facts_by_pillar[pillar]:
                            for fact in facts_by_pillar[pillar]:
                                if hasattr(fact, 'source_url') and fact.source_url:
                                    source_url = fact.source_url
                                    if hasattr(fact, 'source_title') and fact.source_title:
                                        source_title = fact.source_title
                                    break
                        
                        # Extract any references from the text [ref-id] as fallback
                        if not source_url:
                            ref_ids = re.findall(r'\[(\w+-\d+)\]', chunk)
                            if ref_ids and pillar in references_by_pillar:
                                for ref_id, ref_data in references_by_pillar[pillar].items():
                                    if ref_id in ref_ids and 'url' in ref_data and ref_data['url']:
                                        source_url = ref_data['url']
                                        source_title = ref_data.get('title', source_title)
                                        break
                        
                        # Ensure we have a valid URL - if we don't have one from real facts, don't create this fact
                        if source_url:
                            section_facts.append(Fact(
                                content=chunk,
                                category=pillar,
                                citation=f"PESTEL Analysis: {pillar} Factors",
                                source_url=source_url,
                                confidence=0.95,  # High confidence for synthesized content
                                extracted_at=datetime.now().isoformat(),
                                source_title=source_title
                            ))
                
                # Add the original facts as well for full traceability
                pillar_facts = facts_by_pillar.get(pillar, [])
                section_facts.extend(pillar_facts)
                
                if section_facts:  # Only add non-empty sections
                    formatted_sections[pillar] = section_facts
        
        # Generate recommendations based on facts
        
        # Generate 5 actionable recommendations based on the PESTEL analysis
        recommendation_tool = {
            "type": "function",
            "function": {
                "name": "generate_pestel_recommendations",
                "description": "Generate actionable recommendations based on the PESTEL analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommendations": {
                            "type": "array",
                            "description": "List of 5 specific, actionable recommendations based on the PESTEL analysis",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["recommendations"]
                }
            }
        }
        
        # Create recommendation prompt
        recommendation_prompt = f"""
        Based on the PESTEL analysis provided, generate 5 specific, actionable recommendations 
        for businesses or organizations dealing with {spec.industry_focus} in {', '.join(spec.geography_focus)}.
        
        PESTEL summary: {summary}
        
        PESTEL factors analysis:
        {json.dumps(formatted_sections, indent=2, cls=PydanticJSONEncoder)}
        
        Each recommendation should:
        1. Address a specific challenge or opportunity identified in the PESTEL analysis
        2. Be actionable with clear implementation steps
        3. Consider both short-term and long-term impacts
        4. Relate to specific environmental contexts identified
        5. Include consideration of relevant regulatory, social, or technological factors
        """
        
        # Call LLM to generate recommendations
        messages = [
            {"role": "system", "content": "You are a PESTEL analysis expert providing strategic recommendations based on external environmental factors."},
            {"role": "user", "content": recommendation_prompt}
        ]
        
        # Prepare monitoring context for recommendations
        rec_monitoring = get_monitoring_service()
        rec_monitoring_context = AIUsageContext(
            user_id=state.get('user_id') if state else None,
            tenant_id=state.get('tenant_id') if state else None,
            project_id=state.get('session_id') if state else None,
            feature_id="pv_report_pestel",
            workflow_name="pv_report_workflow",
            step_name="recommendations_generation",
            environment="prod"
        )
        
        try:
            logger.info("Generating PESTEL-based recommendations")
            llm, _, _ = _get_llm_provider(state)
            rec_started_at = datetime.now()
            response = await llm.generate_responses_with_tools(messages, [recommendation_tool])
            recommendations = response.arguments.get("recommendations", []) if response.arguments else []
            
            # Record recommendations AI usage
            rec_finished_at = datetime.now()
            usage = getattr(response, 'usage', {}) or {}
            asyncio.create_task(
                rec_monitoring.record_ai_usage(
                    context=rec_monitoring_context,
                    provider="azure_openai",
                    model_name=getattr(response, 'model', 'gpt-5-mini'),
                    operation_type="responses_api",
                    started_at=rec_started_at,
                    finished_at=rec_finished_at,
                    status="success",
                    prompt_tokens=usage.get('prompt_tokens'),
                    completion_tokens=usage.get('completion_tokens'),
                    total_tokens=usage.get('total_tokens'),
                    extra_metadata={"step": "pestel_recommendations", "recommendations_count": len(recommendations)}
                )
            )
            
            # Ensure we have exactly 5 recommendations
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            while len(recommendations) < 5:
                recommendations.append(f"Monitor {random.choice(['Political', 'Economic', 'Social', 'Technological', 'Environmental', 'Legal'])} developments in {', '.join(spec.geography_focus)} related to {spec.industry_focus}")
                
            logger.info(f"Generated {len(recommendations)} recommendations based on PESTEL analysis")
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            # Provide generic recommendations as fallback
            recommendations = [
                f"Develop a comprehensive regulatory compliance strategy for {', '.join(spec.geography_focus)}",
                f"Assess economic vulnerabilities and develop contingency plans for market fluctuations",
                f"Implement social responsibility initiatives aligned with local cultural values",
                f"Invest in emerging technologies to maintain competitive advantage in {spec.industry_focus}",
                f"Develop environmental sustainability practices aligned with local regulations"
            ]
        
        # Create the properly structured MiniReport
        mini_report = PESTELMiniReport(
            title=title,
            summary=summary,
            sections=formatted_sections,
            recommendations=recommendations
        )
        
        # Save the report to the workflow state for downstream use
        if state is not None:
            state["pestel_report"] = mini_report
            logger.info(f"Saved PESTEL report to state with {len(formatted_sections)} sections and {len(facts)} facts")
        
        return mini_report
        
    except Exception as e:
        logger.error(f"Report composition failed: {str(e)}")
        raise


@traceable(name="run_pestel_analysis")
async def run_pestel_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the PESTEL analysis agent on the given workflow state.
    
    Args:
        state: The current workflow state
        
    Returns:
        Modified workflow state with PESTEL analysis results
    """
    # Add critical debug logging for workflow tracing
    logger = logging.getLogger(__name__)
    logger.info("===========================================")
    logger.info("PESTEL AGENT: Starting run_pestel_analysis")
    logger.info(f"PESTEL AGENT: Received state keys: {list(state.keys()) if state else 'None'}")
    
    if 'input_config' in state and 'original_question' in state['input_config']:
        logger.info(f"PESTEL AGENT: Original question found: {state['input_config']['original_question'][:50]}...")
    else:
        logger.warning("PESTEL AGENT: No original question found in input_config")
        
    try:
        # Since we're already in an async context, just await the async function
        result = await _run_pestel_analysis_async(state)
        
        # Log the result keys
        logger.info(f"PESTEL AGENT: Completed analysis with result keys: {list(result.keys()) if result else 'None'}")
        logger.info("===========================================")
        
        # Make sure we have a valid result
        if result is None or not isinstance(result, dict):
            logger.error("PESTEL AGENT: Invalid return value")
            raise ValueError("PESTEL analysis failed to produce a valid result dictionary")
        
        # Ensure pestel_analysis_complete is set in the result
        if 'pestel_report' in result and 'pestel_analysis_complete' not in result:
            logger.info("PESTEL AGENT: Adding explicit pestel_analysis_complete flag")
            result['pestel_analysis_complete'] = True
        
        return result
    except Exception as e:
        logger.error(f"PESTEL AGENT: Exception in run_pestel_analysis: {str(e)}", exc_info=True)
        # Re-raise the exception instead of returning a fallback
        raise
    """
    Run the PESTEL analysis agent on the given workflow state.
    
    Args:
        state: The current workflow state
        
    Returns:
        Modified workflow state with PESTEL analysis results
    """
    # Add critical debug logging for workflow tracing
    logger = logging.getLogger(__name__)
    logger.info("===========================================")
    logger.info("PESTEL AGENT: Starting run_pestel_analysis")
    logger.info(f"PESTEL AGENT: Received state keys: {list(state.keys()) if state else 'None'}")
    
    if 'input_config' in state and 'original_question' in state['input_config']:
        logger.info(f"PESTEL AGENT: Original question found: {state['input_config']['original_question'][:50]}...")
    else:
        logger.warning("PESTEL AGENT: No original question found in input_config")
        
    try:
        # Since we're already in an async context, just await the async function
        result = await _run_pestel_analysis_async(state)
        
        # Log the result keys
        logger.info(f"PESTEL AGENT: Completed analysis with result keys: {list(result.keys()) if result else 'None'}")
        logger.info("===========================================")
        
        # Make sure we have a valid result
        if result is None or not isinstance(result, dict):
            logger.error("PESTEL AGENT: Invalid return value")
            raise ValueError("PESTEL analysis failed to produce a valid result dictionary")
        
        # Ensure pestel_analysis_complete is set in the result
        if 'pestel_report' in result and 'pestel_analysis_complete' not in result:
            logger.info("PESTEL AGENT: Adding explicit pestel_analysis_complete flag")
            result['pestel_analysis_complete'] = True
        
        return result
    except Exception as e:
        logger.error(f"PESTEL AGENT: Exception in run_pestel_analysis: {str(e)}", exc_info=True)
        # Re-raise the exception instead of returning a fallback
        raise


async def _run_pestel_analysis_async(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the PESTEL analysis research pipeline.
    
    This function orchestrates the 9-step process for PESTEL analysis:
    1. Query Understanding
    2. Search Query Generation
    3. Search Execution
    4. Source Extraction
    5. Source Ranking
    6. Fact Extraction
    7. Consistency Check
    8. Report Composition
    
    Args:
        state: Current workflow state with research specification and configuration
        
    Returns:
        Updated workflow state with PESTEL analysis results
    """
    logger.info("===========================================")
    logger.info("PESTEL AGENT: Starting _run_pestel_analysis_async")
    logger.info(f"State keys: {list(state.keys())}")
    logger.info(f"State values: {dict((k, type(v)) for k, v in state.items())}")
    
    try:
        # Get the agent config and research spec from state
        agent_config = get_agent_config('pestel_analysis', state)
        enabled = agent_config.get('enabled', True)
        
        # Try multiple potential keys for the research spec
        from src.mint.schemas.schemas import ResearchSpec
        spec = None
        pestel_spec = None  # Initialize pestel_spec variable
        
        # First try the pestel_specification (specific to this agent)
        if state.get("pestel_specification"):
            try:
                pestel_spec = state.get("pestel_specification")
                if isinstance(pestel_spec, str):
                    # Parse the string to proper object and convert back to dict
                    try:
                        spec = ResearchSpec.parse_raw(pestel_spec)
                        # Convert the parsed spec to a dictionary to use later
                        pestel_spec = spec.dict() if hasattr(spec, 'dict') else json.loads(pestel_spec)
                        logger.info("Successfully parsed pestel_specification from string")
                    except Exception as e:
                        logger.warning(f"Failed to parse string pestel_specification: {str(e)}")
                        # If parsing fails, try to load it as JSON directly
                        try:
                            pestel_spec = json.loads(pestel_spec)
                            logger.info("Parsed pestel_specification as JSON string")
                        except json.JSONDecodeError:
                            logger.error("Failed to parse pestel_specification as JSON string")
                            pestel_spec = None  # Clear it so we can detect the failure later
                elif isinstance(pestel_spec, dict):
                    spec = ResearchSpec.parse_obj(pestel_spec)
                    
                logger.info(f"Using existing PESTEL specification: {pestel_spec.get('title', 'non-dict spec') if isinstance(pestel_spec, dict) else 'non-dict spec'}")
            except Exception as e:
                logger.warning(f"Failed to process pestel_specification: {str(e)}")
                pestel_spec = None  # Clear it so we can detect the failure later
                
        # If that fails, try extracting from master specification
        if not pestel_spec:
            try:
                # Check all possible locations for master specification
                master_spec_data = None
                for key in ["master_specification", "specification", "research_spec"]:
                    if key in state and state[key]:
                        master_spec_data = state[key]
                        logger.info(f"Found potential specification in {key}")
                        break
                
                if master_spec_data:
                    # Handle string format (JSON serialized)
                    master_spec = None
                    if isinstance(master_spec_data, str):
                        try:
                            master_spec = json.loads(master_spec_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse {key} from JSON string")
                    else:
                        # Already a dict/object
                        master_spec = master_spec_data
                    
                    # Extract PESTEL specification from master spec
                    if isinstance(master_spec, dict):
                        # Try different possible paths to PESTEL spec
                        if 'pestel' in master_spec:
                            pestel_spec = master_spec['pestel']
                            logger.info("Found PESTEL spec in master_spec['pestel']")
                        elif 'specifications' in master_spec and 'pestel' in master_spec['specifications']:
                            pestel_spec = master_spec['specifications']['pestel']
                            logger.info("Found PESTEL spec in master_spec['specifications']['pestel']")
            except Exception as e:
                logger.warning(f"Error accessing master specification: {str(e)}")
                
        # Check if we're in interactive mode
        interactive_mode = state.get("interactive_mode", False)
        
        # If we're in interactive mode and awaiting clarification, stop here
        if interactive_mode and state.get("awaiting_clarification", False):
            logger.error("Cannot run PESTEL analysis while awaiting clarification")
            raise ValueError("Workflow sequence error: PESTEL analysis started before clarification completed")
        
        # Also check for user answers in interactive mode 
        if interactive_mode and not state.get("user_answers") and state.get("clarification", {}).get("questions"):
            logger.error("Interactive mode requires user answers before PESTEL analysis")
            raise ValueError("Workflow sequence error: PESTEL analysis started without user answers")
        
        # If we found a valid PESTEL specification, convert it to proper format if needed
        if pestel_spec:
            logger.info(f"Using existing PESTEL specification: {pestel_spec.get('title', '') if isinstance(pestel_spec, dict) else 'non-dict spec'}")
            if isinstance(pestel_spec, dict) and 'title' in pestel_spec:
                # Already in the right format
                logger.info(f"PESTEL spec has structure with title: {pestel_spec['title']}")
            else:
                # Try to convert to proper format
                try:
                    # If it's a ResearchSpec or similar model, extract relevant fields
                    spec_data = pestel_spec
                    if hasattr(spec_data, 'dict'):
                        spec_data = spec_data.dict()
                        
                    # Create a properly structured PESTEL spec
                    pestel_spec = {
                        "title": spec_data.get("title", "PESTEL Analysis"),
                        "description": spec_data.get("description", ""),
                        "geography_focus": spec_data.get("geography_focus", ["Global"]),
                        "industry_focus": spec_data.get("industry_focus", ["General"]),
                        "key_questions": spec_data.get("key_questions", []),
                        "required_pestel_factors": ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]
                    }
                    logger.info(f"Converted PESTEL spec to structured format: {pestel_spec['title']}")
                except Exception as e:
                    logger.warning(f"Error converting PESTEL spec to structured format: {str(e)}")
                    pestel_spec = None
        
        # If we don't have a valid spec, we need to create a default one or raise an error
        if not pestel_spec:
            # First check if we have a user query to work with
            user_query = state.get("initial_query") or state.get("question") or state.get("user_input") or \
                        state.get("input_config", {}).get("original_question", "")
                        
            if interactive_mode:
                # In interactive mode, we require a valid specification from the specifier
                logger.error("No specification available for PESTEL analysis in interactive mode")
                raise ValueError(f"Workflow sequence error: PESTEL analysis started without specification for query: {user_query}")
            else:
                # No fallback - enforce proper workflow sequence
                logger.error(f"No valid research spec found for PESTEL analysis: '{user_query}'")
                raise ValueError(f"PESTEL analysis requires a valid research spec. No spec available for query: {user_query}")
                
                # Add keywords to pestel_spec
                pestel_spec["keywords"] = ["PESTEL", "analysis", "market research"] + industry_focus + \
                                       [w for w in user_query.split() if len(w) > 4][:5]
        
        # Check if agent is enabled in config
        if not enabled:
            logger.info("PESTEL analysis agent is disabled in configuration. Skipping execution.")
            # Return empty dict to avoid state modifications
            return {}
        
        # Extract additional configuration parameters
        search_queries_limit = agent_config.get('search_queries', 5)
        max_sources = agent_config.get('max_sources', 20)
        include_factors = agent_config.get('include_factors', 
            ['political', 'economic', 'social', 'technological', 'environmental', 'legal'])
        
        # Convert include_factors to title case for matching with PESTEL pillars
        include_factors = [factor.title() for factor in include_factors]
        
        start_time = time.time()
        # Require a valid spec, no fallbacks
        if spec is None:
            logger.error("Research spec is missing")
            raise ValueError("PESTEL analysis requires a valid spec object")
        
        spec_title = spec.title
            
        logger.info(f"Starting PESTEL analysis for {spec_title}")
        logger.info(f"Configuration: queries={search_queries_limit}, max_sources={max_sources}, factors={include_factors}")
        
        # Step 1: Extract entities with PESTEL tagging
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Starting Step 1 - Entity Extraction")
        logger.info(f"Specification: {spec.title if spec else 'No spec'}")
        logger.info(f"State keys: {list(state.keys())}")
        
        entities = await _extract_pestel_entities(spec, state)
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Completed Step 1 - Entity Extraction")
        logger.info(f"Extracted entities: {entities.__dict__ if hasattr(entities, '__dict__') else 'No entities'}")
        logger.info(f"Entity keys: {list(entities.__dict__.keys()) if hasattr(entities, '__dict__') else 'No keys'}")
        logger.info(f"First entity: {next(iter(entities.__dict__.values()), 'No entities')[0] if hasattr(entities, '__dict__') else 'No entities'}")
        
        # Step 2: Generate optimized search queries for each PESTEL factor
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Starting Step 2 - Search Query Generation")
        logger.info(f"Entities: {entities.__dict__ if hasattr(entities, '__dict__') else 'No entities'}")
        logger.info(f"Search queries limit: {search_queries_limit}")
        logger.info(f"Include factors: {include_factors}")
        
        # Generate optimized search queries with link quotas for each factor
        query_data = await _generate_pestel_search_queries(spec, entities, search_queries_limit, include_factors, state)
        optimized_queries = query_data["optimized_queries"]  # Full structured query data with metadata
        query_strings = query_data["query_strings"]  # Simple query strings for backward compatibility
        
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Completed Step 2 - Search Query Generation")
        
        # Log the generated queries
        if query_strings:
            # query_strings is a flat list of query strings, not a dictionary
            total_queries = len(query_strings)
            logger.info(f"Generated {total_queries} optimized search queries")
            
            # Show example queries from the optimized queries list
            if isinstance(optimized_queries, list) and len(optimized_queries) > 0:
                # Display the top query
                example = optimized_queries[0]
                factors = ", ".join(example.get("targeted_factors", ["Unknown"]))
                logger.info(f"Top query: '{example.get('query', 'Unknown')}' (Importance: {example.get('importance_rank', 0)}, Links: {example.get('link_quota', 0)}, Factors: {factors})")
                
                # If we have more than one query, also show the second one
                if len(optimized_queries) > 1:
                    example = optimized_queries[1]
                    factors = ", ".join(example.get("targeted_factors", ["Unknown"]))
                    logger.info(f"Second query: '{example.get('query', 'Unknown')}' (Importance: {example.get('importance_rank', 0)}, Links: {example.get('link_quota', 0)}, Factors: {factors})")
            elif isinstance(optimized_queries, dict):
                # Handle the case where it might be a dictionary (original code path)
                for factor, queries in optimized_queries.items():
                    if queries and len(queries) > 0:
                        example = queries[0]
                        logger.info(f"{factor} factor - Top query: '{example.get('query', 'Unknown')}' (Importance: {example.get('importance_rank', 0)}, Links: {example.get('link_quota', 0)})")
                        break  # Just show the first one
        else:
            logger.warning("No search queries generated")
        
        # Store optimized queries in state for debugging/logging
        if "debug" not in state:
            state["debug"] = {}
        state["debug"]["pestel_optimized_queries"] = json.dumps(optimized_queries, cls=PydanticJSONEncoder)
        
        # Step 3: Search Execution - Get relevant URLs
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Starting Step 3 - Search Execution")
        logger.info(f"Number of factors with queries: {len(query_strings)}")
        logger.info(f"Max sources: {max_sources}")
        
        # Use the simple query strings for search execution (backward compatibility)
        search_results = await _execute_search(query_data["query_strings"], state, max_sources)
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Completed Step 3 - Search Execution")
        logger.info(f"Search returned {len(search_results)} unique results")
        if search_results:
            logger.info(f"First search result: {search_results[0]}")
            logger.info(f"Search result type: {type(search_results[0])}")
            logger.info(f"Search result keys: {list(search_results[0].__dict__.keys() if hasattr(search_results[0], '__dict__') else {})}")
        
        # Step 4: Source Extraction - Scrape and store content
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Starting Step 4 - Source Extraction")
        logger.info(f"Number of search results: {len(search_results)}")
        
        source_documents = await _extract_source_content(search_results, state)
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Completed Step 4 - Source Extraction")
        logger.info(f"Extracted content from {len(source_documents)} sources")
        if source_documents:
            logger.info(f"First document title: {source_documents[0].title}")
            logger.info(f"First document content length: {len(source_documents[0].content)}")
            logger.info(f"First document URL: {source_documents[0].url}")
        
        # Step 5: Relevance Ranking - Rank sources by relevance and trust
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Starting Step 5 - Source Ranking")
        logger.info(f"Number of source documents: {len(source_documents)}")
        logger.info(f"First source document title: {source_documents[0].title if source_documents else 'No documents'}")
        
        ranked_documents = await _rank_sources(source_documents, spec, state)
        logger.info("===========================================")
        logger.info("PESTEL AGENT: Completed Step 5 - Source Ranking")
        logger.info(f"Ranked {len(ranked_documents)} sources by relevance and trust")
        if ranked_documents:
            logger.info(f"Top ranked document: {ranked_documents[0].title}")
            logger.info(f"Top document relevance score: {ranked_documents[0].relevance_score}")
            logger.info(f"Top document trust score: {ranked_documents[0].trust_score}")
        
        # Step 6: Fact Extraction with PESTEL Tagging - Extract structured facts and tag with PESTEL pillars
        logger.info("Starting PESTEL fact extraction process...")
        logger.info(f"Number of ranked documents to process: {len(ranked_documents)}")
        logger.info(f"First document title: {ranked_documents[0].title if ranked_documents else 'No documents'}")
        logger.info(f"First document content length: {len(ranked_documents[0].content) if ranked_documents else 0}")
        
        start_time = time.time()
        facts = await _extract_pestel_facts(ranked_documents, spec, include_factors, state)
        extraction_time = time.time() - start_time
        
        logger.info(f"PESTEL fact extraction completed in {extraction_time:.2f} seconds")
        logger.info(f"Total facts extracted: {len(facts)}")
        if facts:
            logger.info(f"First fact content: {facts[0].content[:100]}...")
            logger.info(f"First fact pillar: {facts[0].pestel_pillar}")
        else:
            logger.warning("No facts were extracted from documents")
            logger.info("Checking if documents had content:")
            for i, doc in enumerate(ranked_documents[:3]):  # Check first 3 documents
                logger.info(f"Document {i+1} - Title: {doc.title}")
                logger.info(f"Document {i+1} - Content length: {len(doc.content)}")
                logger.info(f"Document {i+1} - First 100 chars: {doc.content[:100]}...")
        
        # Step 7: Consistency Check - Identify and resolve inconsistencies
        validated_facts = await _check_facts_consistency(facts, spec, state)
        logger.info(f"Validated {len(validated_facts)} facts after consistency check")
        
        # Step 8: Mini-Report Composition - Generate structured PESTEL research report using standardized template
        logger.info("Generating final standardized PESTEL mini-report")
        mini_report = await _compose_standardized_pestel_report(validated_facts, entities, spec, state)
        
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Completed PESTEL analysis in {execution_time:.2f} seconds")
        
        # Use PESTELMiniReport directly - no conversion needed
        logger.info("Using PESTELMiniReport directly without conversion")
        
        # Serialize the PESTELMiniReport object
        if hasattr(mini_report, 'model_dump_json'):
            mini_report_json = mini_report.model_dump_json()
        elif hasattr(mini_report, 'json'):
            mini_report_json = mini_report.json()
        else:
            # Fallback to manual JSON serialization
            mini_report_json = json.dumps(mini_report.model_dump() if hasattr(mini_report, 'model_dump') else mini_report.dict())
        
        # Create a result dict with ONLY modified fields
        # This is crucial for avoiding LangGraph concurrency errors
        result = {
            'pestel_analysis_result': mini_report_json,
            'pestel_report': mini_report_json,  # This is what workflow.py expects
            'pestel_analysis_complete': True,  # EXPLICITLY mark as complete for workflow to proceed
            # Store the validated facts for downstream use in the unified approach
            'enhanced_facts': validated_facts,  # Add facts to state for end-to-end test
            'pestel_analysis_metrics': {
                'execution_time': execution_time,
                'fact_count': len(validated_facts),
                'source_count': len(ranked_documents),
                'search_queries': len(query_data.get('query_strings', [])) if query_data and 'query_strings' in query_data else 0,
                'pillars_included': include_factors
            }
        }
        
        # Log the exact keys we're returning
        logger.info(f"PESTEL AGENT: Returning result with keys: {list(result.keys())}")
        logger.info("PESTEL AGENT: Analysis marked as complete")
        
        # Return ONLY modified fields, not the entire state
        return result
    
    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"Error in PESTEL analysis: {str(e)}", exc_info=True)
        
        # Create an error object
        error_entry = {
            'agent': 'pestel_analysis',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        
        # Create a minimal empty report
        empty_fact = EnhancedPESTELFact(
            content="Error generating PESTEL report",
            category="General",
            pestel_pillar="Political",  # Use a valid PESTEL pillar instead of "General"
            source_title="Error Report",
            source_url="https://example.com/error",
            confidence=0.0,
            extracted_at=datetime.now().isoformat(),
            relevance=0.0,
            impact=0.0
        )
        
        emergency_report = PESTELMiniReport.from_facts(
            title="PESTEL Analysis Error",
            summary="An error occurred while generating the PESTEL analysis.",
            analysis=[],
            recommendations=[]
        )
        
        # Create error result with only modified fields
        error_result = {
            'errors': [error_entry],
            'pestel_report': emergency_report.json(),
            'pestel_analysis_result': emergency_report.json(),
            'pestel_analysis_complete': True,  # EXPLICITLY mark as complete even on error
            'pestel_analysis_metrics': {
                'execution_time': 0,
                'fact_count': 0,
                'source_count': 0,
                'search_queries': 0,
                'pillars_included': []
            }
        }
        
        # Log error return values
        logger.error(f"PESTEL AGENT: Returning error result with keys: {list(error_result.keys())}")
        logger.error("PESTEL AGENT: Analysis marked as complete despite error to allow workflow to continue")
        
        # Return ONLY modified fields with error info, not the entire state
        return error_result


@traceable(name="_extract_pestel_entities")
async def _extract_pestel_entities(spec: ResearchSpec, state: Dict[str, Any] = None) -> PESTELEntities:
    """
    Extract key entities from the research specification using tool calling,
    with a focus on PESTEL factors.
    
    Args:
        spec: The research specification to analyze
        
    Returns:
        Structured entities extracted from the spec with PESTEL factors
    """
    # Get LLM provider
    llm, _, _ = _get_llm_provider(state)
    
    # Prepare monitoring context for entity extraction
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_pestel",
        workflow_name="pv_report_workflow",
        step_name="entity_extraction",
        environment="prod"
    )
    
    # Define the tool schema for PESTEL entity extraction
    pestel_entities_tool = {
        "type": "function",
        "function": {
            "name": "extract_pestel_entities",
            "description": "Extract key entities from the research specification for PESTEL analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry_names": {
                        "type": "array",
                        "description": "Primary industries being researched",
                        "items": {"type": "string"}
                    },
                    "geography_names": {
                        "type": "array",
                        "description": "Geographic regions being researched",
                        "items": {"type": "string"}
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Relevant time period for the research (e.g., '5 years', '2025-2030')"
                    },
                    "target_segments": {
                        "type": "array",
                        "description": "Specific market segments to focus on",
                        "items": {"type": "string"}
                    },
                    "key_topics": {
                        "type": "array", 
                        "description": "Key topics or themes within the industry (5-7 most important)",
                        "items": {"type": "string"}
                    },
                    "expected_output_sections": {
                        "type": "array",
                        "description": "Suggested sections for the final report based on required fact categories",
                        "items": {"type": "string"}
                    },
                    "political_factors": {
                        "type": "array",
                        "description": "Key political factors to research (e.g., government policies, political stability)",
                        "items": {"type": "string"}
                    },
                    "economic_factors": {
                        "type": "array",
                        "description": "Key economic factors to research (e.g., interest rates, economic growth)",
                        "items": {"type": "string"}
                    },
                    "social_factors": {
                        "type": "array",
                        "description": "Key social factors to research (e.g., demographics, cultural trends)",
                        "items": {"type": "string"}
                    },
                    "technological_factors": {
                        "type": "array",
                        "description": "Key technological factors to research (e.g., innovation, automation)",
                        "items": {"type": "string"}
                    },
                    "environmental_factors": {
                        "type": "array",
                        "description": "Key environmental factors to research (e.g., climate change, sustainability)",
                        "items": {"type": "string"}
                    },
                    "legal_factors": {
                        "type": "array",
                        "description": "Key legal factors to research (e.g., regulations, laws)",
                        "items": {"type": "string"}
                    }
                },
                "required": ["industry_names", "geography_names", "key_topics", "political_factors", "economic_factors", "social_factors", "technological_factors", "environmental_factors", "legal_factors"]
            }
        }
    }
    
    # Build messages for entity extraction with PESTEL focus
    # Handle different spec types (None, string, dict, or ResearchSpec object)
    from src.mint.schemas.schemas import ResearchSpec
    
    # Ensure spec is not None
    if spec is None:
        logger.error("ResearchSpec is None in _extract_pestel_entities")
        raise ValueError("ResearchSpec cannot be None for PESTEL entity extraction")
    # If spec is a string, parse it as JSON
    elif isinstance(spec, str):
        logger.warning("ResearchSpec is a string in _extract_pestel_entities, attempting to parse as JSON")
        try:
            import json
            spec_dict = json.loads(spec)
            spec = ResearchSpec.parse_obj(spec_dict)
        except Exception as e:
            logger.error(f"Failed to parse spec string as JSON: {e}")
            raise ValueError(f"Could not parse research spec from string: {str(e)}")
    # If spec is a dict, convert to ResearchSpec
    elif isinstance(spec, dict):
        logger.warning("ResearchSpec is a dict in _extract_pestel_entities, converting to ResearchSpec object")
        try:
            spec = ResearchSpec.parse_obj(spec)
        except Exception as e:
            logger.error(f"Failed to convert dict to ResearchSpec: {e}")
            raise ValueError(f"Could not parse ResearchSpec from dictionary: {str(e)}")
    # Now spec should be a ResearchSpec object
    
    messages = [
        {"role": "system", "content": "You are an expert research analyst specializing in PESTEL analysis. Extract key entities from the research specification with a focus on the six PESTEL pillars."}, 
        {"role": "user", "content": f"""
        Research Specification:
        Title: {spec.title}
        Description: {spec.description}
        Key Questions: {', '.join(spec.key_questions)}
        Required Fact Categories: {', '.join(spec.required_fact_categories)}
        Geography Focus: {', '.join(spec.geography_focus)}
        Industry Focus: {', '.join(spec.industry_focus)}
        Keywords: {', '.join(spec.keywords)}
        
        Extract all key entities from this research specification to help guide the PESTEL analysis.
        For each PESTEL pillar (Political, Economic, Social, Technological, Environmental, Legal),
        identify 3-5 specific factors that should be researched based on the specification.
        """}
    ]
    
    # Call LLM with tool calling - no fallbacks
    try:
        logger.info("🔍 Calling LLM for entity extraction...")
        entity_started_at = datetime.now()
        response = await asyncio.wait_for(
            llm.generate_responses_with_tools(messages, [pestel_entities_tool]),
            timeout=90.0  # 90 seconds for entity extraction
        )
        logger.info("✅ Entity extraction LLM call completed")
        
        # Record entity extraction AI usage
        entity_finished_at = datetime.now()
        usage = getattr(response, 'usage', {}) or {}
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider="azure_openai",
                model_name=getattr(response, 'model', 'gpt-5-mini'),
                operation_type="responses_api",
                started_at=entity_started_at,
                finished_at=entity_finished_at,
                status="success",
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens'),
                extra_metadata={"step": "pestel_entity_extraction"}
            )
        )
        
        # Process response to handle potential None values for list fields
        entity_data = response.arguments.copy() if response.arguments else {}
        
        # Ensure all list fields are properly initialized even if they come back as None
        list_fields = [
            'industry_names', 'geography_names', 'target_segments', 'key_topics', 'expected_output_sections',
            'political_factors', 'economic_factors', 'social_factors', 'technological_factors', 
            'environmental_factors', 'legal_factors'
        ]
        
        for field in list_fields:
            if field in entity_data and entity_data[field] is None:
                entity_data[field] = []  # Replace None with empty list
        
        return PESTELEntities(**entity_data)
    except Exception as e:
        logger.error(f"PESTEL entity extraction failed: {str(e)}")
        raise ValueError(f"Failed to extract PESTEL entities using LLM: {str(e)}")


@traceable(name="_generate_pestel_search_queries")
async def _generate_pestel_search_queries(spec: ResearchSpec, entities: PESTELEntities, search_queries_limit: int = 5, include_factors: List[str] = None, state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a unified set of optimized search queries that cover all relevant PESTEL factors.
    
    Args:
        spec: The research specification
        entities: Extracted entities with PESTEL factors
        search_queries_limit: Maximum number of search queries (default 5)
        include_factors: List of PESTEL factors to include (title cased)
        state: Current workflow state with configuration
        
    Returns:
        Dictionary containing optimized search queries with metadata and link quotas
    """
    # Get LLM provider from configuration
    llm, configured_model, configured_provider = _get_llm_provider(state)
    
    # Define base industry and geography strings
    industry_str = " ".join(entities.industry_names)
    geography_str = " ".join(entities.geography_names)
    
    # Require valid include_factors, no fallbacks
    if include_factors is None:
        logger.error("include_factors is None in _generate_pestel_search_queries")
        raise ValueError("PESTEL search query generation requires specified PESTEL factors")
    
    # Require a valid spec, no fallbacks
    if spec is None:
        logger.error("ResearchSpec is None in _generate_pestel_search_queries")
        raise ValueError("PESTEL search query generation requires a valid spec")
    
    # Get total link quota from configuration
    agent_config = get_agent_config(state, "pestel") if state else {}
    total_link_quota = agent_config.get("max_sources", 15)
    
    # Prepare factor-specific entities for the prompt
    factor_entities_dict = {}
    for factor in include_factors:
        if factor == "Political":
            factor_entities_dict[factor] = entities.political_factors
        elif factor == "Economic":
            factor_entities_dict[factor] = entities.economic_factors
        elif factor == "Social":
            factor_entities_dict[factor] = entities.social_factors
        elif factor == "Technological":
            factor_entities_dict[factor] = entities.technological_factors
        elif factor == "Environmental":
            factor_entities_dict[factor] = entities.environmental_factors
        elif factor == "Legal":
            factor_entities_dict[factor] = entities.legal_factors
    
    # Create a formatted string of all factor entities for the prompt
    factors_info = []
    for factor, entities_list in factor_entities_dict.items():
        factors_info.append(f"{factor}: {', '.join(entities_list)}")
    factors_info_str = "\n".join(factors_info)
    
    # Build a single prompt for holistic PESTEL query generation
    prompt = [
        {"role": "system", "content": "You are an expert research analyst specializing in comprehensive PESTEL analysis frameworks."},
        {"role": "user", "content": f"""
        Research Specification:
        Title: {spec.title}
        Description: {spec.description}
        Geography Focus: {geography_str}
        Industry Focus: {industry_str}
        Keywords: {', '.join(spec.keywords) if hasattr(spec, 'keywords') and spec.keywords else 'None provided'}
        
        PESTEL Factors to Research:
        {factors_info_str}
        
        Your task is to:
        1. Create a holistic set of search queries that comprehensively cover the PESTEL factors ({', '.join(include_factors)}) in an integrated way
        2. Generate EXACTLY {search_queries_limit} optimized search queries that will yield the most valuable information for a complete PESTEL analysis
        3. Ensure your set of queries addresses multiple PESTEL factors - each query should ideally target insights relevant to multiple factors
        4. CRITICAL: Keep queries SHORT and SIMPLE - maximum 80 characters. Use simple natural language phrases, NOT complex Boolean queries
        5. Do NOT use multiple AND/OR operators - Brave Search API rejects overly complex queries
        6. Include geography in simple form (e.g., "Kenya agriculture policy" not "Kenya AND (agriculture OR farming)")
        7. Rank the queries by importance (1-{search_queries_limit}, with 1 being most important)
        8. Allocate a total of {total_link_quota} search links across the {search_queries_limit} queries based on their importance
        9. Indicate which PESTEL factors each query targets in your rationale
        
        GOOD query examples: "Kenya digital agriculture policy 2024", "smallholder farmer mobile money Kenya", "weather services regulations Africa"
        BAD query examples (TOO COMPLEX): '"Kenya" AND ("digital" OR "agriculture") AND ("policy" OR "regulation")'
        
        Return a JSON array with the following structure for each query:
        [
          {{
            "query": "Your optimized search query with operators",
            "importance_rank": 1-{search_queries_limit},
            "link_quota": number of links allocated (total must be {total_link_quota}),
            "targeted_factors": ["List of PESTEL factors this query addresses"],
            "rationale": "Explanation of what this query targets and why it's important"
          }},
          // Additional query objects
        ]
        
        Make sure the link_quota values sum exactly to {total_link_quota} and allocate more links to higher importance queries.
        IMPORTANT: Return ONLY the JSON array, no additional text or explanation.
        """}
    ]
    
    # Call LLM to generate unified PESTEL queries with link quotas
    
    # Prepare monitoring context
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="mint_pestel_analysis",
        workflow_name="mint_workflow",
        step_name="generate_pestel_queries",
        environment="prod"
    )
    
    started_at = datetime.now()
    
    try:
        logger.info(f"Making LLM call for unified PESTEL query generation")
        # Add timeout protection to prevent indefinite hanging
        response = await asyncio.wait_for(
            llm.generate_responses(prompt),
            timeout=120.0  # 2 minutes timeout for query generation
        )
        content = response.content.strip()
        logger.info(f"✅ LLM response received for query generation")
        
        finished_at = datetime.now()
        
        # Record AI usage (fire-and-forget)
        usage = getattr(response, 'usage', {}) or {}
        # Use actual model from response, or configured model as fallback
        actual_model = getattr(response, 'model', configured_model or 'unknown')
        actual_provider = configured_provider or "openai"
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider=actual_provider,
                model_name=actual_model,
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                prompt_tokens=usage.get('prompt_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                total_tokens=usage.get('total_tokens')
            )
        )
        
        # Extract JSON array
        import re
        json_match = re.search(r'\[\s\S]*\]', content)
        if json_match:
            json_str = json_match.group(0)
            pestel_queries = json.loads(json_str)
        elif '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
            pestel_queries = json.loads(content)
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
            pestel_queries = json.loads(content)
        else:
            pestel_queries = json.loads(content)
            
        # Validate that we have a list
        if not isinstance(pestel_queries, list):
            logger.error("LLM did not return a list of search queries for PESTEL analysis")
            raise ValueError("Expected a list of search queries but received a different format")
        
        # Limit to the configured query count
        pestel_queries = pestel_queries[:search_queries_limit]
        
        # Validate total link quota
        total_links = sum(query.get("link_quota", 0) for query in pestel_queries)
        if total_links != total_link_quota:
            logger.warning(f"Total link quota ({total_links}) doesn't match expected ({total_link_quota}), normalizing")
            
            # Normalize link quotas to match the expected total
            importance_ranks = [query.get("importance_rank", 5) for query in pestel_queries]
            importance_weights = [1.0/rank for rank in importance_ranks]
            weight_sum = sum(importance_weights)
            
            # Calculate normalized quotas proportional to importance
            for i, query in enumerate(pestel_queries):
                normalized_quota = max(0, round((importance_weights[i] / weight_sum) * total_link_quota))
                query["link_quota"] = normalized_quota
            
            # Adjust for rounding errors
            adjusted_total = sum(query.get("link_quota", 0) for query in pestel_queries)
            if adjusted_total != total_link_quota:
                diff = total_link_quota - adjusted_total
                # Add/subtract from queries based on importance
                if diff > 0:
                    for i in range(diff):
                        pestel_queries[i % len(pestel_queries)]["link_quota"] += 1
                else:
                    for i in range(-diff):
                        idx = len(pestel_queries) - (i % len(pestel_queries)) - 1
                        if pestel_queries[idx]["link_quota"] > 0:
                            pestel_queries[idx]["link_quota"] -= 1
        
        # Extract simple query strings
        simple_queries = [query.get("query", "") for query in pestel_queries]
        
        logger.info(f"Successfully generated {len(pestel_queries)} unified PESTEL queries")
        
        return {
            "optimized_queries": pestel_queries,  # Detailed queries with metadata
            "query_strings": simple_queries,     # Simple query strings
        }
    
    except asyncio.TimeoutError:
        finished_at = datetime.now()
        logger.error(f"❌ Query generation timed out after 120 seconds")
        
        # Record timeout error (fire-and-forget)
        actual_provider = configured_provider or "openai"
        actual_model = configured_model or 'unknown'
        asyncio.create_task(
            monitoring.record_ai_usage(
                context=monitoring_context,
                provider=actual_provider,
                model_name=actual_model,
                operation_type="responses_api",
                started_at=started_at,
                finished_at=finished_at,
                status="error",
                error_type="TimeoutError"
            )
        )
        
        # Raise with clear message
        raise Exception("PESTEL query generation timed out - API may be overloaded or slow")
        
    except Exception as e:
        finished_at = datetime.now()
        
        # Record error (fire-and-forget)
        actual_provider = configured_provider or "openai"
        actual_model = configured_model or 'unknown'
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
        
        logger.error(f"Failed to generate unified PESTEL search queries: {str(e)}")
        raise ValueError(f"Failed to generate unified PESTEL search queries: {str(e)}")


@traceable(name="_execute_search")
async def _execute_search(search_queries: List[str], state: Dict[str, Any], max_sources: int = 5) -> List[SearchResult]:
    all_results = []
    seen_urls = set()
    
    # Define our search parameters - increase results per query to ensure we get enough results
    results_per_query = 5  # Increased from 1 to get more results per query
    max_queries = min(len(search_queries), 5)
    
    logger.info(f"PESTEL search targeting {max_sources} total results with {results_per_query} results per query")
    
    # Define priority source patterns with categorization
    priority_sources = [
        # Tier 1: Official/Government sources (highest authority)
        r'.*\.gov(\.\w+)?$',  # Government sites (any country)
        r'.*\.mil$',          # Military domains
        r'.*\.int$',          # International organizations
        r'worldbank\.org',    # World Bank
        r'imf\.org',          # International Monetary Fund
        r'wto\.org',          # World Trade Organization
        r'.*\.un\.org$',      # United Nations and its agencies
        r'.*\.who\.int$',     # World Health Organization
        r'europa\.eu',        # European Union
        r'oecd\.org',         # Organization for Economic Cooperation and Development
        
        # Tier 2: Academic and Research Institutions
        r'.*\.edu$',          # US educational institutions
        r'.*\.ac\.[a-z]{2}$', # Academic institutions with country codes
        r'.*\.edu\.[a-z]{2}$',# Educational domains with country codes
        
        # Tier 3: Non-profit/NGO organizations
        r'.*\.org$',          # Non-profit organizations
    ]
    
    # Define diverse source patterns to ensure variety
    diverse_sources = [
        # Research and Academic Publications
        r'.*\.researchgate\.net$', # ResearchGate
        r'.*\.academia\.edu$',    # Academia
        r'.*\.sciencedirect\.com$', # Science Direct
        r'.*\.springer\.com$',    # Springer
        r'.*\.wiley\.com$',      # Wiley
        r'.*\.jstor\.org$',      # JSTOR
        r'.*\.ieee\.org$',       # IEEE
        r'.*\.acm\.org$',        # ACM
        r'.*\.sciencemag\.org$', # Science Magazine
        r'.*\.nature\.com$',     # Nature
        r'.*\.lancet\.com$',     # The Lancet
        
        # Comprehensive Data Sources
        r'statista\.com$',       # Statista - statistics
        r'kaggle\.com$',         # Kaggle - datasets
        r'crunchbase\.com$',     # Crunchbase - company data
        r'bloomberg\.com$',      # Bloomberg - financial data
        r'marketwatch\.com$',    # MarketWatch
        r'morningstar\.com$',    # Morningstar - investment research
        
        # News Media
        r'reuters\.com$',        # Reuters
        r'apnews\.com$',         # Associated Press
        r'bbc\.(co\.uk|com)$',   # BBC
        r'ft\.com$',             # Financial Times
        r'economist\.com$',      # The Economist
        r'wsj\.com$',            # Wall Street Journal
        r'bloomberg\.com$',      # Bloomberg 
        r'cnbc\.com$',           # CNBC
        r'aljazeera\.com$',      # Al Jazeera
        
        # Industry Analysis
        r'mckinsey\.com$',       # McKinsey
        r'bcg\.com$',            # Boston Consulting Group
        r'gartner\.com$',        # Gartner
        r'forrester\.com$',      # Forrester
        r'idc\.com$',            # IDC
        r'pwc\.com$',            # PwC
        r'deloitte\.com$',       # Deloitte
        r'kpmg\.com$',           # KPMG
        r'ey\.com$',             # Ernst & Young
        
        # Tech Analysis and Reviews
        r'techcrunch\.com$',      # TechCrunch
        r'wired\.com$',          # Wired
        r'cnet\.com$',           # CNET
        r'zdnet\.com$',          # ZDNet
        r'theverge\.com$',       # The Verge
    ]
    
    # Get hybrid search strategy configuration
    hybrid_strategy = get_hybrid_search_strategy(state)
    search_config = get_search_config(state) if state else get_config().get_search_config()
    
    # Initialize providers based on hybrid strategy
    providers = {}
    search_providers = []
    
    from src.mint.providers.search import SearchConfig
    
    if hybrid_strategy['mode'] == 'hybrid':
        # Initialize primary provider (Brave - replaces Tavily)
        try:
            brave_primary_config = SearchConfig(
                provider_name="brave",
                api_key_env_var="BRAVE_API_KEY",
                num_results=search_config.get('brave', {}).get('max_results', 20)
            )
            brave_primary_provider = BraveSearchProvider(config=brave_primary_config)
            providers['brave_primary'] = brave_primary_provider
            search_providers.append(brave_primary_provider)
            logger.info(f"PESTEL: Initialized Brave (primary, replaces Tavily) with {search_config.get('brave', {}).get('max_results', 20)} max results")
        except Exception as e:
            logger.error(f"PESTEL: Failed to initialize primary Brave provider: {str(e)}")
        
        # Initialize secondary provider (Brave)
        try:
            brave_config = SearchConfig(
                provider_name="brave",
                api_key_env_var="BRAVE_API_KEY",
                num_results=search_config.get('brave', {}).get('max_results', 20)
            )
            brave_provider = BraveSearchProvider(config=brave_config)
            providers['brave'] = brave_provider
            search_providers.append(brave_provider)
            logger.info(f"PESTEL: Initialized Brave (secondary) with {search_config.get('brave', {}).get('max_results', 20)} max results")
        except Exception as e:
            logger.error(f"PESTEL: Failed to initialize secondary Brave provider: {str(e)}")
        
        # Initialize fallback provider (Serper)
        try:
            serper_config = SearchConfig(
                provider_name="serper",
                api_key_env_var="SERPER_API_KEY",
                num_results=search_config.get('serper', {}).get('max_results', 20)
            )
            serper_provider = SerperSearchProvider(config=serper_config)
            providers['serper'] = serper_provider
            logger.info(f"PESTEL: Initialized Serper (fallback) with {search_config.get('serper', {}).get('max_results', 20)} max results")
        except Exception as e:
            logger.warning(f"PESTEL: Failed to initialize fallback Serper provider: {str(e)}")
    else:
        # Legacy single provider mode
        provider_name = search_config.get('provider', 'brave')
        try:
            if provider_name.lower() == 'tavily':
                config = SearchConfig(
                    provider_name="tavily",
                    api_key_env_var="TAVILY_API_KEY",
                    num_results=search_config.get('tavily', {}).get('max_results', 20)
                )
                search_providers.append(TavilySearchProvider(config=config))
            elif provider_name.lower() == 'brave':
                config = SearchConfig(
                    provider_name="brave",
                    api_key_env_var="BRAVE_API_KEY",
                    num_results=search_config.get('brave', {}).get('max_results', 20)
                )
                search_providers.append(BraveSearchProvider(config=config))
            elif provider_name.lower() == 'serper':
                config = SearchConfig(
                    provider_name="serper",
                    api_key_env_var="SERPER_API_KEY",
                    num_results=search_config.get('serper', {}).get('max_results', 20)
                )
                search_providers.append(SerperSearchProvider(config=config))
            else:
                raise PESTELAgentError(f"Invalid search provider: {provider_name}")
            logger.info(f"PESTEL: Initialized single {provider_name} provider")
        except Exception as e:
            logger.error(f"PESTEL: Failed to initialize {provider_name} provider: {str(e)}")
    
    # Make sure we have at least one provider
    if not search_providers:
        raise PESTELAgentError("No search providers available")
    
    # Helper function to check source types and assign priority scores
    def get_priority_score(url) -> tuple:
        # Convert URL to string if it's a HttpUrl object
        url_str = str(url)
        # Extract domain from URL for better pattern matching
        domain = re.sub(r'^https?://(www\.)?', '', url_str)
        domain = re.sub(r'/.*$', '', domain)
        
        # Default values
        priority_score = 0
        source_type = "Other"
        diversity_score = 0
        
        # Debug info
        logger.debug(f"Processing URL: {url_str}, extracted domain: {domain}")
        
        # Check against priority sources
        for i, pattern in enumerate(priority_sources):
            if re.search(pattern, domain, re.IGNORECASE):
                # Higher score for higher priority patterns
                priority_score = len(priority_sources) - i
                
                # Determine source type based on our tier system
                if i < 10:  # Tier 1: Official/Government sources
                    source_type = "Government/International"
                elif i < 14:  # Tier 2: Academic institutions
                    source_type = "Academic/Organization"
                else:  # Tier 3: Non-profit/NGO
                    source_type = "Research/Statistics"
                
                logger.debug(f"Matched priority pattern {i}: {pattern} for {domain} -> {source_type}")
                break
        
        # Check for diversity sources
        for i, pattern in enumerate(diverse_sources):
            if re.search(pattern, domain, re.IGNORECASE):
                diversity_score = len(diverse_sources) - i
                
                # Only set source_type if not already set by priority sources
                if source_type == "Other":
                    if i < 11:  # Research and Academic Publications
                        source_type = "Academic/Research"
                    elif i < 17:  # Comprehensive Data Sources
                        source_type = "Data/Statistics"
                    elif i < 26:  # News Media
                        source_type = "News/Media"
                    elif i < 35:  # Industry Analysis
                        source_type = "Industry Analysis"
                    else:  # Tech Analysis
                        source_type = "Tech/Reviews"
                
                logger.debug(f"Matched diversity pattern {i}: {pattern} for {domain} -> {source_type}")
                break
        
        # Calculate a combined score that balances priority and diversity
        # Prioritize first but ensure some diverse sources are included
        combined_score = (priority_score * 2) + diversity_score
        
        return (combined_score, source_type)
    
    logger.info(f"PESTEL search targeting {max_sources} total results with {results_per_query} results per query")
    
    # Helper function to deduplicate results
    def add_unique_result(result):
        if result.url not in seen_urls:
            # Initialize metadata if not present
            result.metadata = result.metadata or {}
            
            # Get combined score and source type
            combined_score, source_type = get_priority_score(result.url)
            
            # Add scores and categorization to metadata
            result.metadata['combined_score'] = combined_score
            result.metadata['source_type'] = source_type
            
            seen_urls.add(result.url)
            all_results.append(result)
    
    # Create search tasks using hybrid strategy
    search_tasks = []
    
    if hybrid_strategy['mode'] == 'hybrid' and len(providers) >= 2:
        # Hybrid mode: assign first N queries to primary, rest to secondary
        primary_count = hybrid_strategy['primary_query_count']
        primary_provider_name = hybrid_strategy['primary_provider']
        secondary_provider_name = hybrid_strategy['secondary_provider']
        fallback_provider_name = hybrid_strategy['fallback_provider']
        
        for i, query in enumerate(search_queries):
            if i >= max_queries:
                break
                
            # Assign provider based on query index
            if i < primary_count and primary_provider_name in providers:
                provider = providers[primary_provider_name]
                provider_type = "primary"
            elif secondary_provider_name in providers:
                provider = providers[secondary_provider_name]
                provider_type = "secondary"
            elif fallback_provider_name in providers:
                provider = providers[fallback_provider_name]
                provider_type = "fallback"
            elif search_providers:
                provider = search_providers[0]  # Use first available
                provider_type = "available"
            else:
                logger.error(f"PESTEL: No providers available for query {i+1}")
                continue
                
            search_tasks.append((provider, query))
            logger.info(f"PESTEL: Query {i+1} assigned to {provider.__class__.__name__} ({provider_type})")
    else:
        # Legacy round-robin mode
        for i, query in enumerate(search_queries):
            if i >= max_queries:
                break
            # Select provider using round-robin
            provider = search_providers[i % len(search_providers)]
            search_tasks.append((provider, query))
    
    logger.info(f"PESTEL: Created {len(search_tasks)} search tasks using {hybrid_strategy['mode']} strategy")
    logger.info(f"PESTEL: Configured max_sources: {max_sources}")
    
    # Execute searches with optimizations for paid tiers
    results_lists = []
    
    # Check if we should use concurrent execution for paid tiers
    use_concurrent = hybrid_strategy.get('concurrent_searches', False) and hybrid_strategy.get('paid_tier', True)
    use_rate_limiting = hybrid_strategy.get('rate_limiting', True)
    
    # Log execution mode
    logger.info(f"Execution mode: concurrent={use_concurrent}, rate_limiting={use_rate_limiting}")
    
    if use_concurrent:
        # Concurrent execution for paid tiers
        logger.info(f"PESTEL: Executing {len(search_tasks)} searches concurrently (paid tier optimization)")
        
        async def execute_search_task(i, provider, query):
            try:
                logger.info(f"PESTEL: Starting concurrent search {i+1}/{len(search_tasks)} using {provider.__class__.__name__}")
                results = await provider.search(query)
                logger.info(f"PESTEL: Concurrent search {i+1} returned {len(results)} results using {provider.__class__.__name__}")
                return results
            except Exception as e:
                logger.error(f"PESTEL: Concurrent search error from task {i+1}: {str(e)}")
                return []
        
        # Execute all searches concurrently
        search_coroutines = [
            execute_search_task(i, provider, query) 
            for i, (provider, query) in enumerate(search_tasks)
        ]
        results_lists = await asyncio.gather(*search_coroutines)
        
        # Add all results
        for results in results_lists:
            for result in results:
                add_unique_result(result)
    else:
        # Sequential execution (with optional rate limiting)
        for i, (provider, query) in enumerate(search_tasks):
            try:
                logger.info(f"PESTEL: Executing search {i+1}/{len(search_tasks)} using {provider.__class__.__name__}")
                # Execute the search with the provider
                results = await provider.search(query)
                results_lists.append(results)
                
                # Log the number of results from this query
                logger.info(f"PESTEL: Search task {i+1} returned {len(results)} results using {provider.__class__.__name__}")
                
                # Add all valid results from this query
                for result in results:
                    add_unique_result(result)
                    
                # Add delay only if rate limiting is enabled and not the last search
                if use_rate_limiting and i < len(search_tasks) - 1:
                    delay = 1.0  # 1 second delay between searches
                    logger.info(f"PESTEL: Adding {delay}s delay before next search (rate limiting enabled)")
                    await asyncio.sleep(delay)
                elif not use_rate_limiting:
                    logger.info(f"PESTEL: No rate limiting delay (paid tier optimization)")
                    
            except Exception as e:
                logger.error(f"PESTEL: Search error from task {i+1}: {str(e)}")
                results_lists.append([])  # Add empty list for failed search
    
    # Log the total number of results before filtering
    logger.info(f"Total raw search results before filtering: {len(all_results)}")
    
    # First, sort all results by their combined score
    all_results.sort(key=lambda r: r.metadata.get('combined_score', 0) if r.metadata else 0, reverse=True)
    
    # Ensure source diversity by:  
    # 1. First take the top 66% based on combined score (prioritizing authority)
    # 2. Then add sources from diverse categories to fill the remaining slots
    if len(all_results) > max_sources:
        # Calculate how many results to keep based on pure score
        priority_count = int(max_sources * 0.66)
        priority_results = all_results[:priority_count]
        
        # Get remaining results, but organize by source type to ensure diversity
        remaining = all_results[priority_count:]
        source_types_needed = ["News", "Magazine/Journal", "Industry Analysis", "Research/Statistics"]
        
        diverse_results = []
        for source_type in source_types_needed:
            # Find results matching this source type
            matches = [r for r in remaining if r.metadata.get('source_type') == source_type]
            # Take up to ~8% from each diverse category (adjust as needed)
            diverse_results.extend(matches[:max(1, int(max_sources * 0.08))])
            if len(priority_results) + len(diverse_results) >= max_sources:
                break
        
        # If we still have room, add any remaining high-scored results
        if len(priority_results) + len(diverse_results) < max_sources:
            extra_needed = max_sources - len(priority_results) - len(diverse_results)
            remaining_sorted = sorted(remaining, key=lambda r: r.metadata.get('combined_score', 0) if r.metadata else 0, reverse=True)
            diverse_results.extend(remaining_sorted[:extra_needed])
        
        # Combine priority results with diverse results
        all_results = priority_results + diverse_results[:max_sources - len(priority_results)]
        logger.info(f"Selected {len(priority_results)} high-authority results and {len(all_results) - len(priority_results)} diverse results")
    
    logger.info(f"Search completed with {len(all_results)} results, balancing authority and diversity")
    logger.info(f"Source type breakdown: {[r.metadata.get('source_type', 'Unknown') for r in all_results]}")
    
    return all_results

@traceable(name="_extract_source_content")
async def _extract_source_content(search_results: List[SearchResult], state: Dict[str, Any] = None) -> List[SourceDocument]:
    """
    Extract rich content from search results URLs using async HTTP client.
    
    This function fetches web content from search result URLs, handles different content types
    including PDFs, HTML with tables, and structured data. It cleans and preserves the structure
    of the content for further processing.
    
    Args:
        search_results: List of search results with URLs
        state: Current workflow state with configuration
        
    Returns:
        List of source documents with extracted content, preserving structure and metadata
    """
    import httpx
    from bs4 import BeautifulSoup
    import aiofiles
    from urllib.parse import urlparse
    import re
    import hashlib
    
    logger.info("===========================================")
    logger.info("PESTEL AGENT: Starting Source Extraction")
    logger.info(f"Number of search results: {len(search_results)}")
    logger.info(f"First search result title: {search_results[0].title if search_results else 'No results'}")
    logger.info(f"First search result URL: {search_results[0].url if search_results else 'No URL'}")
    
    source_documents: List[SourceDocument] = []
    current_time = datetime.now().isoformat()
    
    async def extract_from_url(result):
        try:
            logger.info(f"Starting content extraction for {result.url}")
            
            # Parse URL to determine content type and source
            url_str = str(result.url)
            parsed_url = urlparse(url_str)
            domain = parsed_url.netloc
            
            # Set request headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Fetch content with async HTTP client and timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.get(url_str, headers=headers)
                    response.raise_for_status()  # Raise exception for bad status codes
                    
                    # Handle different content types
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/pdf' in content_type:
                        # Save PDF temporarily and extract text
                        pdf_path = f"temp_{uuid.uuid4()}.pdf"
                        async with aiofiles.open(pdf_path, 'wb') as f:
                            await f.write(response.content)
                        
                        # Use PyPDF2 to extract text from PDF with structure preservation
                        try:
                            from PyPDF2 import PdfReader
                            reader = PdfReader(pdf_path)
                            pdf_metadata = reader.metadata
                            num_pages = len(reader.pages)
                            
                            # Extract publication date if available
                            pub_date = None
                            if pdf_metadata and "/CreationDate" in pdf_metadata:
                                # Try to parse PDF creation date
                                try:
                                    date_str = pdf_metadata["/CreationDate"]
                                    # PDF dates are often in format: D:YYYYMMDDHHMMSSz
                                    if date_str.startswith("D:"):
                                        date_str = date_str[2:]
                                        pub_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                except:
                                    pass
                            
                            # Extract author if available
                            author = None
                            if pdf_metadata and "/Author" in pdf_metadata:
                                author = pdf_metadata["/Author"]
                            
                            # Process each page with page numbers
                            content_parts = []
                            for i, page in enumerate(reader.pages):
                                page_text = page.extract_text()
                                if page_text and page_text.strip():
                                    content_parts.append(f"--- Page {i+1}/{num_pages} ---\n{page_text}")
                            
                            # Join all pages with clear separators
                            content = "\n\n".join(content_parts)
                            
                            # Add metadata about the PDF
                            metadata_info = f"PDF METADATA:\n"
                            metadata_info += f"Pages: {num_pages}\n"
                            if pub_date:
                                metadata_info += f"Publication Date: {pub_date}\n"
                            if author:
                                metadata_info += f"Author: {author}\n"
                            
                            # Prepend metadata to content
                            content = metadata_info + "\n\n" + content
                        except Exception as e:
                            logger.error(f"Error extracting text from PDF {url_str}: {e}")
                            content = f"Error extracting PDF content: {str(e)}"
                        
                        # Clean up temporary file
                        os.remove(pdf_path)
                    else:
                        # For HTML content, use BeautifulSoup for structured extraction
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Remove script, style, and nav elements (typically navigation)
                        for element in soup(["script", "style", "nav", "footer", "header"]):
                            element.decompose()
                        
                        # Extract tables separately to preserve their structure
                        tables = []
                        for table_idx, table in enumerate(soup.find_all('table')):
                            table_data = []
                            # Get table headers
                            headers = [th.text.strip() for th in table.find_all('th')]
                            if not headers and table.find('tr'):
                                # Try to get headers from first row if not explicitly defined
                                headers = [td.text.strip() for td in table.find('tr').find_all('td')]
                            
                            # Process table rows
                            for tr in table.find_all('tr')[1:] if headers else table.find_all('tr'):
                                row = [td.text.strip() for td in tr.find_all(['td', 'th'])]
                                if row:
                                    table_data.append(row)
                            
                            # Format table as plain text
                            if headers and table_data:
                                table_text = f"TABLE {table_idx + 1}:\n"
                                table_text += " | ".join(headers) + "\n"
                                table_text += "-" * (sum(len(h) for h in headers) + 3 * (len(headers) - 1)) + "\n"
                                for row in table_data:
                                    table_text += " | ".join(row) + "\n"
                                tables.append(table_text)
                        
                        # Get main text content
                        # Focus on main content areas when possible
                        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
                        
                        # Get text content with paragraph structure preserved
                        paragraphs = []
                        for p in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                            text = p.get_text().strip()
                            if text and len(text) > 10:  # Skip very short fragments
                                if p.name.startswith('h'):
                                    # Format headings
                                    paragraphs.append(f"\n### {text} ###\n")
                                else:
                                    paragraphs.append(text)
                        
                        # Combine text content with preserved structure
                        content = "\n\n".join(paragraphs)
                        
                        # Add tables to the content
                        if tables:
                            content += "\n\n" + "\n\n".join(tables)
                        
                    # Get title from result or use domain if not available
                    title = getattr(result, 'title', domain)
                    
                    # Convert all fields to strings to avoid Pydantic validation errors
                    url_str = str(result.url)
                    title_str = str(title)
                    source_str = str(result.source or domain)
                    
                    # Extract metadata and content quality indicators
                    # Count paragraphs, words, extract keywords
                    paragraphs = content.split('\n\n')
                    paragraph_count = len(paragraphs)
                    word_count = len(content.split())
                    
                    # Check if content contains structured data (tables)
                    has_tables = 'TABLE' in content
                    has_structured_data = has_tables
                    
                    # Extract potential author from content or metadata
                    author = None
                    if 'application/pdf' in content_type and 'PDF METADATA' in content:
                        author_match = re.search(r"Author: ([^\n]+)", content)
                        if author_match:
                            author = author_match.group(1).strip()
                    else:
                        # Look for author patterns in HTML content
                        author_patterns = [
                            r"[aA]uthor[\s:]+([^\n,.]+)",
                            r"[bB]y[\s:]+([^\n,.]+)",
                            r"[wW]ritten by[\s:]+([^\n,.]+)"
                        ]
                        for pattern in author_patterns:
                            match = re.search(pattern, content)
                            if match:
                                author = match.group(1).strip()
                                break
                    
                    # Extract publication date
                    published_date = None
                    if 'application/pdf' in content_type and 'PDF METADATA' in content:
                        date_match = re.search(r"Publication Date: ([^\n]+)", content)
                        if date_match:
                            published_date = date_match.group(1).strip()
                    else:
                        # Look for date patterns in content
                        date_patterns = [
                            r"[pP]ublished[\s:]+([^\n,.]+\d{4})",
                            r"[dD]ate[\s:]+([^\n,.]+\d{4})"
                        ]
                        for pattern in date_patterns:
                            match = re.search(pattern, content)
                            if match:
                                published_date = match.group(1).strip()
                                break
                    
                    # Extract keywords based on frequency and industry relevance
                    # Simple approach: get most frequent words excluding common stop words
                    word_freq = {}
                    stop_words = set(['the', 'and', 'of', 'to', 'a', 'in', 'for', 'is', 'on', 'that', 'by', 'this', 'with'])
                    for word in content.lower().split():
                        word = re.sub(r'[^a-z]', '', word)
                        if word and len(word) > 3 and word not in stop_words:
                            word_freq[word] = word_freq.get(word, 0) + 1
                    
                    # Get top keywords
                    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                    keywords = [k for k, v in keywords]
                    
                    # Create reference ID for source tracking
                    # Format: domain-hash(url)-timestamp
                    url_hash = hashlib.md5(url_str.encode()).hexdigest()[:8]
                    reference_id = f"{domain.replace('.', '-')}-{url_hash}"
                    
                    logger.info(f"Successfully extracted content from {url_str}")
                    logger.info(f"Content length: {len(content)} characters")
                    logger.info(f"Content quality: {paragraph_count} paragraphs, {word_count} words")
                    logger.info(f"Metadata: has_tables={has_tables}, author={author}, published_date={published_date}")
                    
                    return SourceDocument(
                        title=title_str,
                        url=url_str,
                        source=source_str,
                        content=content,
                        metadata={
                            "content_type": content_type,
                            "domain": domain,
                            "extraction_date": current_time,
                            "published_date": published_date,
                            "author": author,
                            "content_length": len(content),
                            "paragraph_count": paragraph_count,
                            "word_count": word_count,
                            "has_tables": has_tables,
                            "has_structured_data": has_structured_data,
                            "keywords": keywords,
                            "reference_id": reference_id
                        },
                        timestamp=getattr(result, 'timestamp', current_time),
                        relevance_score=0.0,  # Will be set in ranking step
                        trust_score=0.0       # Will be set in ranking step
                    )
                except httpx.RequestError as e:
                    logger.error(f"HTTP request error for {url_str}: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Error processing response for {url_str}: {e}")
                    return None
        except Exception as e:
            logger.error(f"Error extracting content from {result.url}: {str(e)}")
            return None
    
    # Create tasks for all URLs
    tasks = [extract_from_url(result) for result in search_results]
    
    # Wait for all tasks to complete with a timeout
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=600.0)  # 10 minute timeout
    except asyncio.TimeoutError:
        logger.error("Timeout while waiting for source extraction tasks")
        results = []
    
    # Filter out None results (failed extractions)
    source_documents = [doc for doc in results if doc is not None]
    
    logger.info("===========================================")
    logger.info("PESTEL AGENT: Completed Source Extraction")
    logger.info(f"Successfully extracted content from {len(source_documents)}/{len(search_results)} sources")
    if source_documents:
        logger.info(f"First document title: {source_documents[0].title}")
        logger.info(f"First document content length: {len(source_documents[0].content)}")
        logger.info(f"First document URL: {source_documents[0].url}")
    else:
        logger.warning("No documents were successfully extracted")
    
    return source_documents
    from urllib.parse import urlparse
    import html2text
    import io
    
    # For PDF handling (if available)
    pdf_parser_available = False
    try:
        from pypdf import PdfReader
        pdf_parser_available = True
    except ImportError:
        logger.warning("pypdf not installed, PDF parsing will be unavailable")
    
    # Create HTML to text converter
    html_converter = html2text.HTML2Text()
    html_converter.ignore_links = False
    html_converter.ignore_images = True
    html_converter.ignore_tables = False
    html_converter.ignore_emphasis = True
    
    source_documents = []
    extraction_tasks = []
    
    # Helper function to extract content from a URL
    async def extract_from_url(result):
        try:
            # Parse URL to determine content type and source
            url_str = str(result.url)  # Convert to string in case it's a Pydantic HttpUrl
            parsed_url = urlparse(url_str)
            domain = parsed_url.netloc
            
            # Set request headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Fetch content with a timeout
            response = requests.get(url_str, headers=headers, timeout=1000)
            response.raise_for_status()
            
            content = ""
            
            # Handle PDF content
            if "application/pdf" in response.headers.get("Content-Type", ""):
                if pdf_parser_available:
                    # Extract text from PDF
                    pdf_file = io.BytesIO(response.content)
                    pdf_reader = PdfReader(pdf_file)
                    # Get text from each page
                    text_pages = []
                    for page in pdf_reader.pages:
                        text_content = page.extract_text()
                        if text_content:
                            text_pages.append(text_content)
                    content = "\n\n".join(text_pages)
                else:
                    # Skip PDF if parser not available
                    return None
            else:
                # Process HTML content
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove script, style, and other non-content elements
                for element in soup(["script", "style", "footer", "nav", "aside"]):
                    element.decompose()
                
                # Extract main content from article tags if available
                main_content = None
                for tag_name in ["article", "main", "div[role='main']", ".main-content", "#content"]:
                    main_content = soup.select_one(tag_name)
                    if main_content:
                        break
                
                # Use main content if found, otherwise use the whole page
                html_to_convert = str(main_content) if main_content else str(soup)
                content = html_converter.handle(html_to_convert)
            
            # Clean and normalize content
            content = content.strip()
            
            # Replace multiple newlines with a single one
            import re
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Truncate if too large
            max_chars = 10000
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content truncated due to length...]\n"
            
            # Return source document
            if content:
                # Get current timestamp if not available in result
                from datetime import datetime
                current_time = datetime.now().isoformat()
                
                # Convert all fields to strings to avoid Pydantic validation errors
                url_str = str(result.url)
                title_str = str(result.title)
                source_str = str(result.source or domain)
                
                return SourceDocument(
                    title=title_str,
                    url=url_str,
                    source=source_str,
                    content=content,
                    timestamp=getattr(result, 'timestamp', current_time),  # Use current time if no timestamp
                    relevance_score=0.0,  # Will be set in ranking step
                    trust_score=0.0       # Will be set in ranking step
                )
            return None
            
        except Exception as e:
            logger.error(f"Error extracting content from URL {result.url}: {e}")
            return None
    
    logger.info(f"Extracted content from {len(source_documents)} sources")
    return source_documents


@traceable(name="_rank_sources")
async def _rank_sources(source_documents: List[SourceDocument], spec: ResearchSpec, state: Dict[str, Any] = None) -> List[SourceDocument]:
    """
    Rank sources by relevance to the research specification and reliability of the source.
    
    Args:
        source_documents: List of source documents with extracted content
        spec: The research specification
        
    Returns:
        Ranked list of source documents
    """
    from urllib.parse import urlparse
    # If no documents or in test mode, return as is
    if not source_documents or os.environ.get("MINT_TEST_MODE"):
        return source_documents
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Prepare monitoring context for source ranking
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_pestel",
        workflow_name="pv_report_workflow",
        step_name="source_ranking",
        environment="prod"
    )
    
    # Define the source ranking tool
    source_ranking_tool = {
        "type": "function",
        "function": {
            "name": "rank_pestel_sources",
            "description": "Rank sources by relevance and trustworthiness for PESTEL analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_rankings": {
                        "type": "array",
                        "description": "Rankings for each source",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL of the source"
                                },
                                "relevance_score": {
                                    "type": "number",
                                    "description": "Relevance score from 0.0 to 1.0 based on how relevant the content is to the research specification"
                                },
                                "trust_score": {
                                    "type": "number",
                                    "description": "Trust score from 0.0 to 1.0 based on source reliability and content quality"
                                },
                                "pestel_relevance": {
                                    "type": "object",
                                    "description": "Relevance scores for each PESTEL pillar",
                                    "properties": {
                                        "political": {"type": "number"},
                                        "economic": {"type": "number"},
                                        "social": {"type": "number"},
                                        "technological": {"type": "number"},
                                        "environmental": {"type": "number"},
                                        "legal": {"type": "number"}
                                    }
                                }
                            },
                            "required": ["url", "relevance_score", "trust_score"]
                        }
                    }
                },
                "required": ["source_rankings"]
            }
        }
    }
    
    # Prepare message for ranking
    system_message = """You are an expert research analyst specializing in source evaluation.
    Evaluate and rank sources based on their relevance to the research specification and trustworthiness.
    For each source, provide:
    1. A relevance score (0.0-1.0) indicating how well it addresses the research needs
    2. A trust score (0.0-1.0) based on source reputation, content quality, and factual reliability
    3. Relevance scores for each PESTEL pillar (Political, Economic, Social, Technological, Environmental, Legal)
    """
    
    # Prepare content for each source (truncate to avoid token limits)
    source_summaries = []
    for doc in source_documents:
        # Truncate content to first 500 characters for ranking
        truncated_content = doc.content[:500] + "..." if len(doc.content) > 500 else doc.content
        source_summaries.append(f"URL: {doc.url}\nTitle: {doc.title}\nSource: {doc.source}\nExcerpt:\n{truncated_content}\n")
    
    # First perform automated preliminary scoring based on metadata
    for doc in source_documents:
        # 1. Calculate automatic relevance score
        auto_relevance_score = 0.3  # Base score
        
        # Check content length and structure (longer, structured content is often more relevant)
        content_length = doc.metadata.get("content_length", len(doc.content))
        if content_length > 5000:  # Long content
            auto_relevance_score += 0.15
        elif content_length > 2500:  # Medium content
            auto_relevance_score += 0.1
            
        # Check for presence of structured data (tables are valuable)
        if doc.metadata.get("has_structured_data", False):
            auto_relevance_score += 0.15
        
        # Check for geography relevance
        if spec and spec.geography_focus:
            for geo in spec.geography_focus:
                geo_lower = geo.lower()
                # Check title and content for geography mentions
                if geo_lower in doc.title.lower():
                    auto_relevance_score += 0.1
                    break
                content_sample = doc.content[:1000].lower()  # Check beginning of content
                if geo_lower in content_sample:
                    auto_relevance_score += 0.05
                    break
        
        # Check for PESTEL relevance based on keywords
        pestel_terms = {
            "political": ["government", "policy", "regulation", "political", "election", "tax", "tariff"],
            "economic": ["economy", "market", "recession", "inflation", "gdp", "economic", "financial"],
            "social": ["demographic", "cultural", "social", "consumer", "trend", "lifestyle", "population"],
            "technological": ["technology", "innovation", "digital", "automation", "ai", "tech", "software"],
            "environmental": ["sustainability", "climate", "environmental", "green", "carbon", "pollution", "renewable"],
            "legal": ["law", "compliance", "legal", "legislation", "regulation", "liability", "statutory"]
        }
        
        # Check content for PESTEL categories match
        pestel_match_count = 0
        for category, terms in pestel_terms.items():
            for term in terms:
                if term in doc.content.lower():
                    pestel_match_count += 1
                    break
                    
        # Add score based on PESTEL coverage
        auto_relevance_score += min(0.15, pestel_match_count * 0.025)  # Max 0.15 for all 6 categories
        
        # 2. Calculate automatic trust score
        auto_trust_score = 0.3  # Base score
        
        # Check domain reputation
        domain = doc.metadata.get("domain", urlparse(doc.url).netloc)
        
        # High trust TLDs and domains
        high_trust_domains = [
            r'\.gov$', r'\.edu$', r'\.org$',  # Government, education, non-profit
            r'reuters\.com$', r'bloomberg\.com$', r'ft\.com$',  # News agencies
            r'worldbank\.org$', r'imf\.org$', r'un\.org$',  # International organizations
        ]
        
        # Check for trusted domains
        for pattern in high_trust_domains:
            if re.search(pattern, domain):
                auto_trust_score += 0.15
                break
        
        # Check content quality indicators
        paragraph_count = doc.metadata.get("paragraph_count", 0)
        if paragraph_count > 15:  # Many paragraphs indicate depth
            auto_trust_score += 0.1
        elif paragraph_count > 7:
            auto_trust_score += 0.05
            
        # Award higher score for having author and publication date
        if doc.metadata.get("author"):
            auto_trust_score += 0.05
            
        if doc.metadata.get("published_date"):
            auto_trust_score += 0.05
            
        # Cap automatic scores at 0.7 to leave room for LLM adjustment
        doc.relevance_score = min(0.7, auto_relevance_score)
        doc.trust_score = min(0.7, auto_trust_score)
        
        # Log preliminary scoring
        logger.info(f"Preliminary scoring for {doc.title}: relevance={doc.relevance_score:.2f}, trust={doc.trust_score:.2f}")
    
    # Create the list of sources for ranking with detailed information
    source_list = ""
    for i, doc in enumerate(source_documents):
        # Include metadata in source list for better context
        metadata_str = ""
        if doc.metadata.get("author"):
            metadata_str += f"Author: {doc.metadata['author']}, "
        if doc.metadata.get("published_date"):
            metadata_str += f"Published: {doc.metadata['published_date']}, "
        if doc.metadata.get("has_structured_data", False):
            metadata_str += "Contains structured data, "    
        if metadata_str:
            metadata_str = f" [{metadata_str.rstrip(', ')}]"
            
        source_list += f"{i+1}. {doc.title} - {doc.url}{metadata_str}\n"
    
    # Require valid spec, no fallbacks
    if spec is None:
        logger.error("spec is None in _rank_sources")
        raise ValueError("PESTEL source ranking requires a valid spec")
    
    # Prepare system message with improved prompt for PESTEL-specific ranking
    system_message = """You are an expert PESTEL analyst specializing in source evaluation.
    Your task is to deeply analyze content from various sources and evaluate them based on three key dimensions:
    
    1. RELEVANCE - How well the content addresses the specific PESTEL research questions and topics.
       Consider factors like: political insights, economic data, social trends, technological developments,
       environmental information, and legal/regulatory content relevant to the research focus.
       
    2. TRUSTWORTHINESS - The credibility and quality of the information provided.
       Consider factors like: source reputation, data quality, citation of evidence, and balanced reporting.
       
    3. PESTEL COVERAGE - How well each source covers the different PESTEL dimensions.
       For each source, evaluate its coverage of Political, Economic, Social, Technological, Environmental, and Legal factors.
       
    For each source, provide:
    - Relevance score (0.0-1.0) - Higher scores for sources with detailed PESTEL information addressing research needs
    - Trust score (0.0-1.0) - Higher scores for reputable sources with verifiable information
    - PESTEL dimension relevance - Score each PESTEL dimension from 0.0-1.0 based on coverage
    - Relevance factors - List specific aspects of the content that are valuable to the PESTEL analysis
    - Key insights - Extract 1-2 of the most important PESTEL insights from the source
    
    Prioritize sources that contain concrete data, research findings, or expert analysis over general information.
    """
    
    # Prepare source summaries with richer content excerpts
    source_summaries = []
    for idx, doc in enumerate(source_documents):
        # Include metadata in summary for better context
        metadata_summary = []
        if doc.metadata.get("published_date"):
            metadata_summary.append(f"Published: {doc.metadata.get('published_date')}")
            
        if doc.metadata.get("author"):
            metadata_summary.append(f"Author: {doc.metadata.get('author')}")
            
        if doc.metadata.get("has_tables", False):
            metadata_summary.append("Contains tables/structured data")
            
        if doc.metadata.get("keywords"):
            metadata_summary.append(f"Key terms: {', '.join(doc.metadata.get('keywords')[:5])}")
        
        # Create a more informative summary with metadata context
        summary = f"SOURCE {idx+1}:\n"
        summary += f"URL: {doc.url}\n"
        summary += f"Title: {doc.title}\n"
        summary += f"Source: {doc.source}\n"
        
        if metadata_summary:
            summary += f"Metadata: {', '.join(metadata_summary)}\n"
        
        # Extract most meaningful content selections for PESTEL analysis
        content_preview = ""
        
        # First check for tables which often contain valuable structured data
        if doc.metadata.get("has_tables", False) and "TABLE" in doc.content:
            table_match = re.search(r"(TABLE \d+:[\s\S]+?)(?=TABLE \d+:|$)", doc.content)
            if table_match:
                content_preview += f"\n[STRUCTURED DATA]\n{table_match.group(1)}\n"
        
        # Look for PESTEL-specific content sections
        pestel_sections = {}
        for category in ["political", "economic", "social", "technological", "environmental", "legal"]:
            # Look for sections containing PESTEL terms
            pattern = fr"(?i)[\s\n][^\n]{{0,50}}{category}[^\n]{{0,100}}[.\n]"
            matches = re.findall(pattern, doc.content)
            if matches:
                pestel_sections[category] = matches[0].strip()
        
        # Add found PESTEL sections
        if pestel_sections:
            content_preview += "\n\n[PESTEL-SPECIFIC SECTIONS]\n"
            for category, text in pestel_sections.items():
                content_preview += f"[{category.upper()}]: {text}\n"
        
        # If no PESTEL sections found, add general content beginning
        if not pestel_sections and not content_preview:
            # Split content into paragraphs and select most informative ones
            paragraphs = doc.content.split("\n\n")[:5]  # Take first 5 paragraphs
            content_preview += "\n\n[CONTENT EXCERPT]\n" + "\n\n".join(paragraphs[:3])
        
        # Truncate if too long
        if len(content_preview) > 1000:
            content_preview = content_preview[:997] + "..."
            
        summary += f"\nContent:\n{content_preview}\n"
        source_summaries.append(summary)
    
    # Build message for ranking
    geography_focus = ", ".join(spec.geography_focus) if spec and spec.geography_focus else "relevant geographies"
    industry_focus = ", ".join(spec.industry_focus) if spec and spec.industry_focus else "specified industries"
    key_questions = "\n    - " + "\n    - ".join(spec.key_questions) if spec and spec.key_questions else "PESTEL analysis"
    
    separator = '-' * 80 + "\n"
    ranked_sources = separator.join(source_summaries)

    ranking_message = f"""
    RESEARCH FOCUS:
    Title: {spec.title}
    Description: {spec.description}
    Geography Focus: {geography_focus}
    Industry Focus: {industry_focus}
    Key Questions: {key_questions}

    SOURCES TO ANALYZE AND RANK:
    {'-' * 80}
    {ranked_sources}

    For each source, provide:
    1. A relevance score (0.0-1.0) indicating how valuable this content is for PESTEL analysis
    2. A trust score (0.0-1.0) indicating the credibility and quality of the information
    3. PESTEL dimension relevance scores (0.0-1.0 for each dimension)
    4. 1-2 specific relevance factors that make this source valuable for PESTEL analysis
    5. 1-2 key insights extracted from the source that are most relevant to the PESTEL questions
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": ranking_message}
    ]
    
    ranking_started_at = datetime.now()
    response = await llm.generate_responses_with_tools(messages, [source_ranking_tool])
    
    # Record source ranking AI usage
    ranking_finished_at = datetime.now()
    usage = getattr(response, 'usage', {}) or {}
    asyncio.create_task(
        monitoring.record_ai_usage(
            context=monitoring_context,
            provider="azure_openai",
            model_name=getattr(response, 'model', 'gpt-5-mini'),
            operation_type="responses_api",
            started_at=ranking_started_at,
            finished_at=ranking_finished_at,
            status="success",
            prompt_tokens=usage.get('prompt_tokens'),
            completion_tokens=usage.get('completion_tokens'),
            total_tokens=usage.get('total_tokens'),
            extra_metadata={"step": "pestel_source_ranking", "sources_ranked": len(source_documents)}
        )
    )
    
    # Handle response.arguments which might be a string, dict, or None
    try:
        if response.arguments is None:
            logger.error("Response arguments is None")
            for doc in source_documents:
                doc.relevance_score = 0.5
                doc.trust_score = 0.5
            return source_documents
        elif isinstance(response.arguments, str):
            import json
            arguments = json.loads(response.arguments)
        else:
            arguments = response.arguments
            
        if not arguments or "source_rankings" not in arguments:
            logger.error(f"Missing source_rankings in response: {arguments}")
            # Fallback: assign default scores
            for doc in source_documents:
                doc.relevance_score = 0.5
                doc.trust_score = 0.5
            return source_documents
            
        rankings = {item["url"]: item for item in arguments["source_rankings"]}
    except (KeyError, TypeError) as e:
        logger.error(f"Error parsing source ranking response: {e}")
        logger.error(f"Response arguments: {response.arguments}")
        # Fallback: assign default scores
        for doc in source_documents:
            doc.relevance_score = 0.5
            doc.trust_score = 0.5
        return source_documents
    
    # Apply rankings to source documents
    for doc in source_documents:
        if doc.url in rankings:
            ranking = rankings[doc.url]
            doc.relevance_score = ranking["relevance_score"]
            doc.trust_score = ranking["trust_score"]
    
    # Sort by combined score (relevance * trust)
    ranked_documents = sorted(source_documents, key=lambda d: d.relevance_score * d.trust_score, reverse=True)
    return ranked_documents


@traceable(name="_extract_pestel_facts")
async def _extract_pestel_facts(ranked_documents: List[SourceDocument], spec: ResearchSpec, include_factors: List[str] = None, state: Dict[str, Any] = None) -> List[EnhancedPESTELFact]:
    """
    Extract structured facts from source documents and tag with PESTEL pillars.
    
    Args:
        ranked_documents: Ranked list of source documents
        spec: Research specification
        
    Returns:
        List of structured facts tagged with appropriate PESTEL pillars
    """
    logger.info("Starting PESTEL fact extraction process")
    logger.info(f"Number of documents to process: {len(ranked_documents)}")
    logger.info(f"First document title: {ranked_documents[0].title if ranked_documents else 'No documents'}")
    logger.info(f"First document content length: {len(ranked_documents[0].content) if ranked_documents else 0}")
    
    start_time = time.time()
    if include_factors is None:
        include_factors = ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]
    
    # If no documents, return empty list
    if not ranked_documents:
        return []
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Prepare monitoring context for fact extraction
    monitoring = get_monitoring_service()
    monitoring_context = AIUsageContext(
        user_id=state.get('user_id') if state else None,
        tenant_id=state.get('tenant_id') if state else None,
        project_id=state.get('session_id') if state else None,
        feature_id="pv_report_pestel",
        workflow_name="pv_report_workflow",
        step_name="fact_extraction",
        environment="prod"
    )
    
    # Define fact extraction tool with PESTEL tagging
    pestel_facts_tool = {
        "type": "function",
        "function": {
            "name": "extract_pestel_facts",
            "description": "Extract structured facts from content and tag with appropriate PESTEL pillar",
            "parameters": {
                "type": "object",
                "properties": {
                    "facts": {
                        "type": "array",
                        "description": "Extracted facts with PESTEL categorization",
                        "items": {
                            "type": "object",
                            "properties": {
                                "statement": {
                                    "type": "string",
                                    "description": "A concise, factual statement (1-2 sentences)"
                                },
                                "pestel_pillar": {
                                    "type": "string",
                                    "description": "The PESTEL pillar this fact belongs to",
                                    "enum": ["Political", "Economic", "Social", "Technological", "Environmental", "Legal"]
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "Confidence score from 0.0 to 1.0 about the accuracy of this fact"
                                },
                                "specific_aspect": {
                                    "type": "string",
                                    "description": "The specific aspect of the PESTEL pillar (e.g., 'Regulations' for Legal)"
                                }
                            },
                            "required": ["statement", "pestel_pillar"]
                        }
                    }
                },
                "required": ["facts"]
            }
        }
    }
    
    all_facts = []
    extraction_tasks = []
    
    # Process each document to extract facts with timeout handling
    async def process_document(doc):
        try:
            logger.info(f"Processing document: {doc.title[:50]}...")
            logger.info(f"Document content length: {len(doc.content)}")
            logger.info(f"Document URL: {doc.url}")
            
            # Prepare system message
            system_message = """
            You are an expert PESTEL analyst. Extract factual information from the provided text and categorize each fact
            according to the PESTEL framework (Political, Economic, Social, Technological, Environmental, Legal).
            
            For each fact:
            1. Create a concise, well-formed statement (1-2 sentences)
            2. Assign it to the appropriate PESTEL pillar
            3. Assign a confidence score (0.0-1.0) based on how clearly stated the fact is
            4. Identify the specific aspect of the PESTEL pillar it relates to
            
            Focus only on extracting clear facts that are relevant to the research specification.
            Each fact should be specific and not overly general.
            Do not make up or infer facts that are not supported by the text.
            """
            
            # Prepare user message with research context and document
            user_message = f"""
            Research Specification:
            Title: {spec.title}
            Description: {spec.description}
            Industry Focus: {', '.join(spec.industry_focus)}
            Geography Focus: {', '.join(spec.geography_focus)}
            
            Source Document:
            Title: {doc.title}
            URL: {doc.url}
            Source: {doc.source}
            
            Content:
            {doc.content[:7000] if len(doc.content) > 7000 else doc.content}
            
            Extract all relevant PESTEL facts from this content. Categorize each fact by the appropriate PESTEL pillar.
            """
            
            # Make API call with tool calling and timeout
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # Set a timeout for the LLM call
            try:
                # Create a task for the LLM call
                llm_task = asyncio.create_task(llm.generate_responses_with_tools(messages, [pestel_facts_tool]))
                
                # Wait for the task with a timeout (60 seconds)
                fact_started_at = datetime.now()
                start_time = time.time()
                response = await asyncio.wait_for(llm_task, timeout=60.0)
                llm_time = time.time() - start_time
                
                extracted_facts = response.arguments.get("facts", []) if response.arguments else []
                
                # Record fact extraction AI usage
                fact_finished_at = datetime.now()
                usage = getattr(response, 'usage', {}) or {}
                asyncio.create_task(
                    monitoring.record_ai_usage(
                        context=monitoring_context,
                        provider="azure_openai",
                        model_name=getattr(response, 'model', 'gpt-5-mini'),
                        operation_type="responses_api",
                        started_at=fact_started_at,
                        finished_at=fact_finished_at,
                        status="success",
                        prompt_tokens=usage.get('prompt_tokens'),
                        completion_tokens=usage.get('completion_tokens'),
                        total_tokens=usage.get('total_tokens'),
                        extra_metadata={"step": "pestel_fact_extraction", "document": doc.title[:50], "facts_extracted": len(extracted_facts)}
                    )
                )
                
                logger.info(f"Successfully extracted {len(extracted_facts)} facts from document: {doc.title[:30]}...")
                logger.info(f"LLM call took {llm_time:.2f} seconds")
                if extracted_facts:
                    logger.info(f"First extracted fact: {extracted_facts[0]['statement'][:100]}...")
                    logger.info(f"First fact pillar: {extracted_facts[0]['pestel_pillar']}")
            except asyncio.TimeoutError:
                logger.error(f"LLM call timed out for document: {doc.title[:30]}...")
                return []
            except Exception as e:
                logger.error(f"Error in LLM call for document {doc.url}: {str(e)}")
                return []
            
            # Convert to EnhancedPESTELFact objects
            document_facts = []
            for i, fact_data in enumerate(extracted_facts):
                try:
                    # Create a unique reference ID that we'll preserve throughout the pipeline
                    fact_ref_id = f"ref-{uuid.uuid4().hex[:8]}"
                    
                    # Create enhanced fact with source metadata and explicit reference ID
                    fact = EnhancedPESTELFact(
                        # Required fields from base Fact class
                        content=fact_data["statement"],
                        extracted_at=datetime.now().isoformat(),
                        
                        # Other fields
                        statement=fact_data["statement"],
                        category=fact_data.get("specific_aspect", fact_data["pestel_pillar"]),
                        source_url=doc.url,  # Ensure URL is preserved
                        source_title=doc.title,
                        confidence=fact_data.get("confidence", 0.7),
                        pestel_pillar=fact_data["pestel_pillar"],
                        reference_id=fact_ref_id  # Explicitly assign reference ID for traceability
                    )
                    document_facts.append(fact)
                    logger.info(f"Created fact {i+1} from document {doc.title[:30]}...")
                    logger.info(f"Fact content: {fact.content[:100]}...")
                    logger.info(f"Fact pillar: {fact.pestel_pillar}")
                except Exception as fact_error:
                    logger.error(f"Error creating fact {i+1}: {str(fact_error)}")
                    logger.error(f"Failed fact data: {fact_data}")
            
            return document_facts
            
        except Exception as e:
            logger.error(f"Error extracting facts from {doc.url}: {str(e)}")
            return []
        

    
    # Process documents in batches to avoid overwhelming API rate limits
    # Azure OpenAI has strict rate limits - processing all docs in parallel causes timeouts
    BATCH_SIZE = 3  # Process 3 documents at a time
    logger.info(f"Processing {len(ranked_documents)} documents in batches of {BATCH_SIZE} to avoid rate limits")
    
    start_time = time.time()
    
    try:
        # Process documents in batches
        for i in range(0, len(ranked_documents), BATCH_SIZE):
            batch = ranked_documents[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(ranked_documents) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} documents)")
            
            # Create tasks for this batch
            batch_tasks = [asyncio.create_task(process_document(doc)) for doc in batch]
            
            # Execute batch with timeout
            try:
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*batch_tasks, return_exceptions=True),
                    timeout=180.0  # 3 minutes per batch (60s per doc * 3 docs)
                )
                
                # Collect successful results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch task failed with exception: {result}")
                    elif isinstance(result, list):
                        all_facts.extend(result)
                        
                logger.info(f"✅ Batch {batch_num} complete: extracted {sum(len(r) if isinstance(r, list) else 0 for r in batch_results)} facts")
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Batch {batch_num} timed out after 180 seconds")
                continue
        
        extraction_time = time.time() - start_time
        
        logger.info(f"Extracted {len(all_facts)} facts with PESTEL tagging")
        logger.info(f"Total extraction time: {extraction_time:.2f} seconds")
        logger.info(f"Average time per document: {(extraction_time / len(ranked_documents) if ranked_documents else 0):.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in fact extraction process: {str(e)}")
            
    # Log if no facts were extracted
    if not all_facts:
        logger.warning("No facts were extracted from any sources")
    
    logger.info(f"Final fact count: {len(all_facts)} facts with PESTEL tagging")
    return all_facts


def _infer_pestel_pillar(content: str) -> Optional[str]:
    """
    Infers the most likely PESTEL pillar for a fact based on its content.
    Returns None if no clear match is found, avoiding default fallbacks.
    
    Args:
        content: The text content of the fact
        
    Returns:
        The inferred PESTEL pillar or None if no confident match
    """
    if not content:
        return None
        
    # Dictionary mapping pillars to relevant keywords
    pillar_keywords = {
        "Political": ["government", "policy", "regulation", "election", "political", "democracy", 
                    "legislation", "government", "parliament", "minister", "president", 
                    "governance", "lobby", "tax policy", "trade restriction"],
        
        "Economic": ["economy", "inflation", "interest rate", "gdp", "recession", "economic growth",
                    "market", "unemployment", "currency", "fiscal", "monetary", "price", "cost",
                    "investment", "budget", "economic", "income", "profit", "financial"],
        
        "Social": ["demographic", "population", "culture", "attitude", "lifestyle", "education",
                  "social", "health", "religion", "language", "ethics", "diversity", "inclusion",
                  "consumer", "trend", "behavior", "belief", "community", "society"],
        
        "Technological": ["technology", "innovation", "automation", "digital", "internet", "AI",
                        "machine learning", "robotics", "software", "hardware", "tech", "patent",
                        "R&D", "research", "computing", "IT", "database", "algorithm", "platform"],
        
        "Environmental": ["climate", "environment", "sustainability", "green", "carbon", "emission",
                        "energy", "renewable", "waste", "pollution", "recycling", "ecosystem",
                        "weather", "wildlife", "conservation", "biodiversity", "natural resource"],
        
        "Legal": ["law", "legal", "legislation", "court", "regulation", "compliance", "liability",
                 "lawsuit", "sue", "rights", "patent", "intellectual property", "contract", "license",
                 "regulatory", "statute", "attorney", "judge"]
    }
    
    # Normalize content for matching
    content_lower = content.lower()
    
    # Count matches for each pillar
    scores = {}
    for pillar, keywords in pillar_keywords.items():
        score = sum(1 for keyword in keywords if keyword.lower() in content_lower)
        scores[pillar] = score
    
    # Find the pillar with highest score
    max_score = max(scores.values()) if scores else 0
    max_pillars = [p for p, s in scores.items() if s == max_score]
    
    # Only return a pillar if we have a clear winner with at least some matches
    if max_score > 0 and len(max_pillars) == 1:
        return max_pillars[0]
    
    # If tied or no significant matches, return None
    return None


@traceable(name="_check_facts_consistency")
async def _check_facts_consistency(facts: List[EnhancedPESTELFact], spec: ResearchSpec, state: Dict[str, Any] = None) -> List[EnhancedPESTELFact]:
    """
    Check facts for consistency and assign confidence scores based on validation.
    This function treats all facts as a unified collection rather than dividing by pillars.
    
    Args:
        facts: List of extracted facts with PESTEL tagging
        spec: Research specification
        
    Returns:
        List of validated facts with updated confidence scores
    """
    # If no facts, return empty list
    if not facts:
        logger.warning("No facts provided to consistency checker")
        return []
    
    logger.info(f"Checking consistency of {len(facts)} facts as a unified collection")
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Ensure all facts have the necessary attributes
    processed_facts = []
    
    for i, fact in enumerate(facts):
        # Ensure the fact has a reference ID
        if not hasattr(fact, 'reference_id') or not fact.reference_id:
            fact.reference_id = f"fact-{i}"
        
        # Assign default confidence if missing
        if not hasattr(fact, 'confidence') or fact.confidence is None:
            fact.confidence = 0.7
        
        # Try to infer a pillar category if missing, but don't add a default
        if not hasattr(fact, 'pestel_pillar') or not fact.pestel_pillar:
            # Only try to infer from content if available
            if hasattr(fact, 'content') and fact.content:
                inferred_pillar = _infer_pestel_pillar(fact.content)
                if inferred_pillar: # Only set if inference produced a valid result
                    fact.pestel_pillar = inferred_pillar
            # No default fallback - leave unclassified if no pillar determined
        
        # Keep all facts that have content
        if hasattr(fact, 'content') and fact.content:
            processed_facts.append(fact)
    
    # Log processing results
    logger.info(f"Initial processing complete: {len(processed_facts)}/{len(facts)} facts retained")
    
    # IMPORTANT: If we have no facts after processing, return empty list
    if not processed_facts:
        logger.warning("No facts survived initial processing")
        return facts if facts else []  # Return original facts as fallback
    
    return processed_facts


# Streamlined report generation workflow


@traceable(name="_compose_standardized_pestel_report")
async def _compose_standardized_pestel_report(facts: List[EnhancedPESTELFact], entities: PESTELEntities, spec: ResearchSpec, state: Dict[str, Any] = None) -> PESTELMiniReport:
    """
    Compose a structured PESTEL mini-report from validated facts using the standardized PESTEL report prompt.
    
    This implementation uses the new prompt template that generates structured reports with
    numbered citations [1], [2] and separate sources section.
    
    Args:
        facts: List of validated facts with PESTEL tagging
        entities: Extracted entities from research specification
        spec: Research specification
        state: Optional workflow state for configuration and LLM provider
        
    Returns:
        A standardized PESTELMiniReport structure
    """
    logger.info("Generating standardized PESTEL report using new prompt template")
    
    # Get LLM provider from configuration
    llm, _, _ = _get_llm_provider(state)
    
    # Use ALL facts for comprehensive report generation (no artificial limits)
    # Sort facts by confidence score to prioritize high-quality facts in the prompt
    facts_to_use = sorted(facts, key=lambda x: x.confidence, reverse=True)
    
    logger.info(f"📊 Using ALL {len(facts_to_use)} facts for comprehensive PESTEL report generation (no limits)")
    
    # Format facts for the prompt - include source information for citation mapping
    formatted_facts = []
    unique_sources = {}
    source_counter = 1
    
    for fact in facts_to_use:  # Using ALL facts for comprehensive analysis
        # Create unique source mapping
        source_key = (fact.source_title, str(fact.source_url) if fact.source_url else "")
        if source_key not in unique_sources:
            unique_sources[source_key] = source_counter
            source_counter += 1
        
        formatted_facts.append({
            "content": fact.content,
            "pillar": fact.pestel_pillar if hasattr(fact, 'pestel_pillar') and fact.pestel_pillar else "Uncategorized",
            "source_title": fact.source_title,
            "source_url": str(fact.source_url) if fact.source_url else "",
            "citation_number": unique_sources[source_key]
        })
    
    # Format research spec for prompt
    research_spec_dict = {
        "title": spec.title if hasattr(spec, 'title') else "",
        "description": spec.description if hasattr(spec, 'description') else "",
        "industry_focus": spec.industry_focus if hasattr(spec, 'industry_focus') else [],
        "geography_focus": spec.geography_focus if hasattr(spec, 'geography_focus') else [],
        "time_period": spec.time_period if hasattr(spec, 'time_period') else "Current"
    }
    
    # Create EXPLICIT citation instruction that tells LLM to use the pre-assigned citation_number field
    max_citation_number = len(unique_sources)
    citation_instruction = f"""

════════════════════════════════════════════════════════════════════════════════
CRITICAL CITATION INSTRUCTIONS - READ CAREFULLY
════════════════════════════════════════════════════════════════════════════════

CITATION SYSTEM:
- Each fact in the JSON above has a "citation_number" field (e.g., "citation_number": 5)
- This number is PRE-ASSIGNED and maps to the source document for that fact
- You have {max_citation_number} unique sources, so valid citations are ONLY [1] through [{max_citation_number}]

MANDATORY RULES:
1. When citing a fact, use its EXACT "citation_number" value from the JSON
   Example: If fact says {{"content": "Market grew 15%", "citation_number": 3}}, 
   you MUST cite it as [3], NOT [1] or any other number

2. NEVER invent citation numbers - ONLY use citation_number values from the facts JSON

3. Multiple facts can share the same citation_number (they're from the same source)
   This is CORRECT and EXPECTED

4. Your "sources" array must have EXACTLY {max_citation_number} entries
   Source [1] = first unique source, Source [2] = second unique source, etc.

5. NEVER use citations higher than [{max_citation_number}] - these don't exist!

VIOLATION WILL CAUSE VALIDATION FAILURE - Follow these rules exactly.
════════════════════════════════════════════════════════════════════════════════
"""
    
    # Format the prompt with research spec and facts
    # PERFORMANCE: Use compact JSON (no indent) for facts to reduce prompt size
    prompt_input = {
        "research_spec": json.dumps(research_spec_dict, indent=2),
        "facts": json.dumps(formatted_facts)  # Compact JSON - no indent
    }
    
    # Add citation instruction to the formatted prompt
    base_prompt = PESTEL_REPORT_PROMPT.format(**prompt_input)
    formatted_prompt = base_prompt + citation_instruction
    
    # Log prompt size for performance monitoring
    prompt_size_chars = len(formatted_prompt)
    prompt_size_kb = prompt_size_chars / 1024
    logger.info(f"📊 PROMPT SIZE: {prompt_size_chars} chars ({prompt_size_kb:.1f} KB) with {len(formatted_facts)} facts")
    
    # Call LLM with the prompt
    messages = [
        {"role": "system", "content": "You are an expert business analyst specializing in PESTEL analysis."},
        {"role": "user", "content": formatted_prompt}
    ]
    
    try:
        # Use the JSONValidator for validation and repair
        validated_data = await generate_report_with_validation(llm, messages, "pestel")
        
        # Extract the report data from the validated response
        report_data = validated_data.get("report", {})
        
        # Create the PESTELMiniReport from validated data
        mini_report = PESTELMiniReport(
            title=report_data.get("title", "PESTEL Analysis"),
            summary=report_data.get("summary", ""),
            analysis=report_data.get("analysis", []),
            recommendations=report_data.get("recommendations", []),
            sources=report_data.get("sources", [])
        )
        
        # Save to state
        if state is not None:
            state["pestel_report"] = mini_report
            logger.info(f"Saved standardized PESTEL report to state with {len(report_data.get('analysis', []))} sections")
        
        logger.info(f"Generated PESTEL report with {len(report_data.get('analysis', []))} sections and {len(report_data.get('recommendations', []))} recommendations")
        return mini_report
            
    except Exception as e:
        logger.error(f"Failed to generate PESTEL report with JSONValidator: {e}")
        
        # Fallback to the enhanced parser if JSONValidator fails
        try:
            logger.info("Falling back to enhanced parser")
            parser = get_enhanced_parser(max_retries=5)
            parsed_data = await parser.parse_report_with_retry(llm, messages, "pestel")
            
            # Create the PESTELMiniReport from parsed data
            # Note: Enhanced parser returns "sections", but PESTELMiniReport uses "analysis"
            # Handle both field names for robustness
            analysis_data = parsed_data.get("analysis") or parsed_data.get("sections", [])
            
            mini_report = PESTELMiniReport(
                title=parsed_data["title"],
                summary=parsed_data["summary"],
                analysis=analysis_data,
                recommendations=parsed_data.get("recommendations", []),
                sources=parsed_data.get("sources", [])
            )
            
            # Save to state
            if state is not None:
                state["pestel_report"] = mini_report
                logger.info(f"Saved standardized PESTEL report to state with {len(analysis_data)} sections")
            
            logger.info(f"Generated PESTEL report with {len(analysis_data)} sections and {len(parsed_data.get('recommendations', []))} recommendations")
            return mini_report
                
        except ReportParsingError as e:
            logger.error(f"Failed to parse PESTEL report after {e.attempts} attempts: {e}")
            # NO FALLBACK - Force proper implementation
            raise RuntimeError(f"PESTEL report parsing failed: {e}")
        except Exception as e:
            logger.error(f"Error generating standardized PESTEL report: {str(e)}")
            # NO FALLBACK - Force proper implementation
            raise RuntimeError(f"PESTEL report generation failed: {e}")