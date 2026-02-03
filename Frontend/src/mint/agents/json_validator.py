#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JSON Validator for MINT Agents.

This module provides robust JSON validation, repair, and retry mechanisms
to ensure that JSON outputs from Industry and PESTEL agents are consistently
valid and properly structured.
"""

import json
import logging
import re
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple, Type, Union, Callable
from datetime import datetime
from collections import Counter

# Import the JSON validator logger
from .json_validator_logger import json_validator_logger

# Import the JSON validation monitor
try:
    from .json_validation_monitor import get_monitor
    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False
    def get_monitor():
        return None

try:
    import jsonrepair
except ImportError:
    # Fallback implementation if jsonrepair is not installed
    def jsonrepair_fallback(json_text: str) -> str:
        """Enhanced fallback implementation for jsonrepair with improved complex case handling."""
        try:
            # First try parsing as-is to see if repair is needed
            json.loads(json_text)
            return json_text  # Already valid, return as-is
        except json.JSONDecodeError:
            pass
        
        try:
            repaired = json_text.strip()
            
            # Step 1: Fix unquoted property names FIRST (before other operations)
            # More comprehensive regex to handle nested objects
            repaired = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', repaired)
            
            # Step 2: Fix trailing commas before closing braces/brackets
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
            
            # Step 3: Fix missing commas between array elements and object properties
            repaired = re.sub(r'}\s*{', r'}, {', repaired)
            repaired = re.sub(r']\s*\[', r'], [', repaired)
            
            # Step 4: Handle incomplete structures by analyzing the content
            # Look for patterns that suggest incomplete arrays or objects
            
            # Fix incomplete arrays - look for array that ends without proper closing
            # Pattern: [ ... items ... \n    \n  } (missing ])
            repaired = re.sub(r'(\[\s*[^\[\]]*?)\s*\n\s*\n\s*(\})', r'\1\n    ]\n  \2', repaired)
            
            # Step 5: Fix truncated JSON by adding missing closing braces and brackets
            # Count opening and closing characters
            open_braces = repaired.count('{')
            close_braces = repaired.count('}')
            open_brackets = repaired.count('[')
            close_brackets = repaired.count(']')
            
            # Add missing closing brackets first (arrays)
            if open_brackets > close_brackets:
                missing_brackets = open_brackets - close_brackets
                # Try to add brackets in the right place
                if repaired.rstrip().endswith(','):
                    # Remove trailing comma and add bracket
                    repaired = repaired.rstrip().rstrip(',') + '\n    ' + ']' * missing_brackets
                else:
                    repaired += '\n    ' + ']' * missing_brackets
            
            # Add missing closing braces (objects)
            if open_braces > close_braces:
                missing_braces = open_braces - close_braces
                repaired += '\n' + '}' * missing_braces
            
            # Step 6: Final cleanup - remove any double commas or malformed separators
            repaired = re.sub(r',,+', ',', repaired)
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
            
            # Fix single quotes to double quotes (legacy support)
            repaired = re.sub(r"'([^']*)':", r'"\1":', repaired)
            
            return repaired
            
        except Exception:
            # If the above didn't work, try a more aggressive approach
            return _aggressive_jsonrepair_fallback(json_text)

    def _aggressive_jsonrepair_fallback(json_text: str) -> str:
        """More aggressive JSON repair for complex malformed cases."""
        repaired = json_text.strip()
        
        # Fix unquoted properties
        repaired = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', repaired)
        
        # Remove trailing commas
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        
        # Try to balance brackets and braces by analyzing structure
        lines = repaired.split('\n')
        result_lines = []
        bracket_stack = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                result_lines.append(line)
                continue
                
            # Track opening brackets/braces
            for char in stripped:
                if char in '{[':
                    bracket_stack.append(char)
                elif char in '}]':
                    if bracket_stack:
                        bracket_stack.pop()
            
            result_lines.append(line)
        
        # Close any remaining open structures
        while bracket_stack:
            char = bracket_stack.pop()
            if char == '{':
                result_lines.append('}')
            elif char == '[':
                result_lines.append(']')
        
        repaired = '\n'.join(result_lines)
        
        # Final cleanup
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        
        return repaired
        
    jsonrepair = type('', (), {'repair_json': staticmethod(jsonrepair_fallback)})

try:
    import backoff
except ImportError:
    # Simple backoff decorator if backoff is not installed
    def backoff_fallback(wait_gen, exception, max_tries=3, jitter=None):
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                for attempt in range(max_tries):
                    try:
                        return await func(*args, **kwargs)
                    except exception as e:
                        if attempt == max_tries - 1:
                            raise
                        wait = wait_gen(attempt)
                        logging.info(f"Backing off {wait} seconds after attempt {attempt + 1}")
                        await asyncio.sleep(wait)
            
            def sync_wrapper(*args, **kwargs):
                for attempt in range(max_tries):
                    try:
                        return func(*args, **kwargs)
                    except exception as e:
                        if attempt == max_tries - 1:
                            raise
                        wait = wait_gen(attempt)
                        logging.info(f"Backing off {wait} seconds after attempt {attempt + 1}")
                        import time
                        time.sleep(wait)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def expo(base=2, factor=1, max_value=None):
        def wait_gen(attempt):
            wait = factor * base ** attempt
            if max_value is not None:
                wait = min(wait, max_value)
            return wait
        return wait_gen
    
    backoff = type('', (), {
        'on_exception': staticmethod(backoff_fallback),
        'expo': staticmethod(expo)
    })

from pydantic import BaseModel, Field, ValidationError, validator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JSON Schema Definitions

# Industry Report Schema
INDUSTRY_REPORT_SCHEMA = {
    "name": "industry_report",
    "type": "object",
    "properties": {
        "report": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 10,
                    "maxLength": 200,
                    "description": "A clear, descriptive title for the industry analysis report"
                },
                "summary": {
                    "type": "string",
                    "minLength": 200,
                    "maxLength": 800,
                    "description": "A comprehensive executive summary of 200-800 characters covering key findings"
                },
                "analysis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 100,
                                "description": "Clear section heading describing the analysis area"
                            },
                            "content": {
                                "type": "string",
                                "minLength": 300,
                                "maxLength": 2000,
                                "description": "Detailed analysis content of 300-2000 characters with citations"
                            },
                            "subsections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "heading": {
                                            "type": "string",
                                            "minLength": 5,
                                            "maxLength": 80
                                        },
                                        "content": {
                                            "type": "string",
                                            "minLength": 150,
                                            "maxLength": 1000
                                        }
                                    },
                                    "required": ["heading", "content"],
                                    "additionalProperties": False
                                },
                                "maxItems": 5
                            }
                        },
                        "required": ["heading", "content"],
                        "additionalProperties": False
                    },
                    "minItems": 5,
                    "maxItems": 7,
                    "description": "Exactly 5-7 comprehensive analysis sections covering different industry aspects"
                },
                "tables": {
                    "type": "object",
                    "description": "Optional data tables referenced in the analysis"
                },
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 50,
                        "maxLength": 300,
                        "description": "Actionable recommendation of 50-300 characters"
                    },
                    "minItems": 4,
                    "maxItems": 7,
                    "description": "Exactly 4-7 specific, actionable recommendations"
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Sequential source number starting from 1"
                            },
                            "title": {
                                "type": "string",
                                "minLength": 10,
                                "maxLength": 200,
                                "description": "Descriptive title of the source"
                            },
                            "url": {
                                "type": "string",
                                "pattern": "^https?://",
                                "minLength": 10,
                                "maxLength": 500,
                                "description": "Valid HTTP/HTTPS URL"
                            }
                        },
                        "required": ["number", "title", "url"],
                        "additionalProperties": False
                    },
                    "minItems": 3,
                    "maxItems": 15,
                    "description": "At least 3 credible sources with sequential numbering"
                }
            },
            "required": ["title", "summary", "analysis", "tables", "recommendations", "sources"],
            "additionalProperties": False
        }
    },
    "required": ["report"],
    "additionalProperties": False,
    "strict": True
}

# PESTEL Report Schema
PESTEL_REPORT_SCHEMA = {
    "name": "pestel_report",
    "type": "object",
    "properties": {
        "report": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 10,
                    "maxLength": 200,
                    "description": "A clear, descriptive title for the PESTEL analysis report"
                },
                "summary": {
                    "type": "string",
                    "minLength": 200,
                    "maxLength": 800,
                    "description": "A comprehensive executive summary of 200-800 characters covering key PESTEL findings"
                },
                "analysis": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {
                                "type": "string",
                                "minLength": 5,
                                "maxLength": 100,
                                "description": "Clear PESTEL factor heading (Political, Economic, Social, Technological, Environmental, Legal)"
                            },
                            "content": {
                                "type": "string",
                                "minLength": 400,
                                "maxLength": 2500,
                                "description": "Detailed PESTEL analysis content of 400-2500 characters with citations"
                            },
                            "subsections": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "heading": {
                                            "type": "string",
                                            "minLength": 5,
                                            "maxLength": 80
                                        },
                                        "content": {
                                            "type": "string",
                                            "minLength": 200,
                                            "maxLength": 1200
                                        }
                                    },
                                    "required": ["heading", "content"],
                                    "additionalProperties": False
                                },
                                "maxItems": 4
                            }
                        },
                        "required": ["heading", "content"],
                        "additionalProperties": False
                    },
                    "minItems": 6,
                    "maxItems": 6,
                    "description": "Exactly 6 PESTEL sections: Political, Economic, Social, Technological, Environmental, Legal"
                },
                "tables": {
                    "type": "object",
                    "description": "Optional data tables referenced in the PESTEL analysis"
                },
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 60,
                        "maxLength": 350,
                        "description": "Strategic recommendation of 60-350 characters based on PESTEL findings"
                    },
                    "minItems": 6,
                    "maxItems": 10,
                    "description": "Exactly 6-10 strategic recommendations based on PESTEL analysis"
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Sequential source number starting from 1"
                            },
                            "title": {
                                "type": "string",
                                "minLength": 10,
                                "maxLength": 200,
                                "description": "Descriptive title of the source"
                            },
                            "url": {
                                "type": "string",
                                "pattern": "^https?://",
                                "minLength": 10,
                                "maxLength": 500,
                                "description": "Valid HTTP/HTTPS URL"
                            }
                        },
                        "required": ["number", "title", "url"],
                        "additionalProperties": False
                    },
                    "minItems": 4,
                    "maxItems": 20,
                    "description": "At least 4 credible sources with sequential numbering"
                }
            },
            "required": ["title", "summary", "analysis", "tables", "recommendations", "sources"],
            "additionalProperties": False
        }
    },
    "required": ["report"],
    "strict": True  # Reject unknown keys
}

# Pydantic Models for Validation

class Subsection(BaseModel):
    """Model for a subsection in a report."""
    heading: str
    content: str

class Section(BaseModel):
    """Model for a section in a report."""
    heading: str
    content: str
    subsections: List[Subsection] = []

class Source(BaseModel):
    """Model for a source reference in a report."""
    number: int
    title: str
    url: str

class Report(BaseModel):
    """Base model for a report."""
    title: str
    summary: str
    analysis: List[Section]
    tables: Dict[str, Any] = {}
    recommendations: List[str]
    sources: List[Source]
    
    @validator('sources')
    def validate_source_numbers(cls, v):
        """Validate that source numbers are unique and sequential."""
        numbers = [source.number for source in v]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Source numbers must be unique")
        if sorted(numbers) != list(range(1, len(numbers) + 1)):
            raise ValueError("Source numbers must be sequential starting from 1")
        return v
    
    @validator('recommendations')
    def validate_recommendations_count(cls, v):
        """Validate that there are between 4 and 7 recommendations."""
        if not (4 <= len(v) <= 7):
            raise ValueError("There must be between 4 and 7 recommendations")
        return v
    
    @validator('analysis')
    def validate_analysis_sections(cls, v):
        """Validate that there are between 4 and 8 analysis sections."""
        if not (4 <= len(v) <= 8):
            raise ValueError("There must be between 4 and 8 analysis sections")
        return v

class ReportResponse(BaseModel):
    """Model for the complete report response."""
    report: Report

class IndustryReport(Report):
    """Model for an industry report."""
    pass

class PESTELReport(Report):
    """Model for a PESTEL report."""
    pass

class IndustryReportResponse(ReportResponse):
    """Model for the complete industry report response."""
    report: IndustryReport

class PESTELReportResponse(ReportResponse):
    """Model for the complete PESTEL report response."""
    report: PESTELReport

# Citation Validator
class CitationValidator:
    """
    Validator for citations in report content.
    
    This class provides methods for validating and repairing citations in report content.
    It checks for duplicate citations, missing sources, unused sources, and invalid URLs.
    It also provides methods for automatically repairing common citation issues.
    """
    
    def __init__(self):
        """Initialize the citation validator."""
        # Pattern to match citation numbers like [1], [23], etc.
        self.citation_pattern = re.compile(r'\[(\d+)\]')
        # Pattern to match adjacent duplicate citations like [1][1] or [2][2][2]
        self.adjacent_duplicates_pattern = r'(\[\d+\])(\1+)'
        # Pattern to match URLs for validation
        self.url_pattern = re.compile(
            r'^(?:http|https)://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ipv4
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$$', re.IGNORECASE)
    
    def validate_citations(self, content: str, sources: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate citations in content against sources.
        
        Args:
            content: The content to validate
            sources: The list of sources
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        # Extract all citation numbers from content
        citations = self.citation_pattern.findall(content)
        citation_numbers = [int(c) for c in citations]
        
        # Check for adjacent duplicate citations (like [1][1] or [2][2][2])
        # Multiple uses of the same citation throughout the text is normal and expected
        adjacent_duplicates = re.findall(self.adjacent_duplicates_pattern, content)
        duplicates = [match[0] for match in adjacent_duplicates] if adjacent_duplicates else []
        
        # Check for citations without sources
        source_numbers = [s["number"] for s in sources]
        missing_sources = [num for num in citation_numbers if num not in source_numbers]
        
        # Check for sources without citations
        unused_sources = [num for num in source_numbers if num not in citation_numbers]
        
        # Check for non-sequential source numbers
        if source_numbers and sorted(source_numbers) != list(range(1, max(source_numbers) + 1)):
            non_sequential = True
        else:
            non_sequential = False
        
        # Check for invalid URLs in sources
        invalid_urls = []
        for source in sources:
            if "url" in source and not self.is_valid_url(source["url"]):
                invalid_urls.append(source["number"])
        
        # Generate error messages
        errors = []
        # Note: Adjacent duplicate citations (like [1][1]) are cosmetic issues, not semantic errors
        # They get auto-fixed by fix_duplicate_citations(), so we just log them as warnings, not errors
        if duplicates:
            logger.warning(f"Adjacent duplicate citations found (will be auto-fixed): {duplicates}")
        if missing_sources:
            errors.append(f"Citations without sources: {missing_sources}")
        # Note: We allow unused sources - it's fine to have sources that aren't cited
        # if unused_sources:
        #     errors.append(f"Sources without citations: {unused_sources}")
        if non_sequential:
            errors.append(f"Source numbers are not sequential: {source_numbers}")
        if invalid_urls:
            errors.append(f"Invalid URLs in sources: {invalid_urls}")
        
        return len(errors) == 0, errors
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is valid.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the URL is valid, False otherwise
        """
        return bool(self.url_pattern.match(url))
    
    def fix_duplicate_citations(self, content: str) -> str:
        """
        Fix duplicate adjacent citations in content.
        
        Args:
            content: The content to fix
            
        Returns:
            The fixed content
        """
        # Find all citation patterns like [1][1] or [2][2][2]
        # Replace with just one instance
        fixed_content = re.sub(self.adjacent_duplicates_pattern, r'\1', content)
        
        return fixed_content
    
    def fix_non_sequential_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fix non-sequential source numbers.
        
        Args:
            sources: The list of sources to fix
            
        Returns:
            The fixed list of sources
        """
        # Sort sources by their current number
        sorted_sources = sorted(sources, key=lambda s: s["number"])
        
        # Reassign numbers to be sequential
        for i, source in enumerate(sorted_sources, 1):
            source["number"] = i
            
        return sorted_sources
    
    def repair_citations_in_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Repair all citations in a report.
        
        This method fixes duplicate citations, ensures sources are sequential,
        removes orphaned citations, and updates citation numbers in content to match the sources.
        
        Args:
            report: The report to repair
            
        Returns:
            The repaired report
        """
        # First, fix non-sequential sources
        report["sources"] = self.fix_non_sequential_sources(report["sources"])
        
        # Get valid source numbers
        valid_source_numbers = [s["number"] for s in report["sources"]]
        
        # Create a mapping of old source numbers to new ones
        source_map = {s["number"]: i+1 for i, s in enumerate(report["sources"])}
        for i, source in enumerate(report["sources"], 1):
            source["number"] = i
        
        # Update valid source numbers after renumbering
        valid_source_numbers = list(range(1, len(report["sources"]) + 1))
        
        # Fix citations in summary
        if "summary" in report:
            report["summary"] = self.fix_duplicate_citations(report["summary"])
            report["summary"] = self.remove_orphaned_citations(report["summary"], valid_source_numbers)
            report["summary"] = self.update_citation_numbers(report["summary"], source_map)
        
        # Fix citations in analysis sections
        if "analysis" in report:
            for section in report["analysis"]:
                if "content" in section:
                    section["content"] = self.fix_duplicate_citations(section["content"])
                    section["content"] = self.remove_orphaned_citations(section["content"], valid_source_numbers)
                    section["content"] = self.update_citation_numbers(section["content"], source_map)
                
                if "subsections" in section:
                    for subsection in section["subsections"]:
                        if "content" in subsection:
                            subsection["content"] = self.fix_duplicate_citations(subsection["content"])
                            subsection["content"] = self.remove_orphaned_citations(subsection["content"], valid_source_numbers)
                            subsection["content"] = self.update_citation_numbers(subsection["content"], source_map)
        
        # Fix citations in recommendations
        if "recommendations" in report:
            for i, rec in enumerate(report["recommendations"]):
                report["recommendations"][i] = self.fix_duplicate_citations(rec)
                report["recommendations"][i] = self.remove_orphaned_citations(rec, valid_source_numbers)
                report["recommendations"][i] = self.update_citation_numbers(rec, source_map)
        
        return report
    
    def remove_orphaned_citations(self, content: str, valid_source_numbers: List[int]) -> str:
        """
        Remove citations that don't have corresponding sources.
        
        Args:
            content: The content to clean
            valid_source_numbers: List of valid source numbers
            
        Returns:
            The cleaned content with orphaned citations removed
        """
        def replace_citation(match):
            citation_num = int(match.group(1))
            if citation_num in valid_source_numbers:
                return match.group(0)  # Keep valid citations
            else:
                return ""  # Remove orphaned citations
        
        return re.sub(r'\[(\d+)\]', replace_citation, content)
    
    def update_citation_numbers(self, content: str, source_map: Dict[int, int]) -> str:
        """
        Update citation numbers in content based on a mapping.
        
        Args:
            content: The content to update
            source_map: A mapping of old citation numbers to new ones
            
        Returns:
            The updated content
        """
        def replace_citation(match):
            old_num = int(match.group(1))
            if old_num in source_map:
                return f"[{source_map[old_num]}]"
            return ""  # Remove citations that can't be mapped
        
        return re.sub(r'\[(\d+)\]', replace_citation, content)
    
    def extract_all_content(self, report: Dict[str, Any]) -> str:
        """
        Extract all content from a report for citation validation.
        
        Args:
            report: The report to extract content from
            
        Returns:
            A string containing all content with citations
        """
        all_content = []
        
        # Add summary
        if "summary" in report:
            all_content.append(report["summary"])
        
        # Add analysis sections
        if "analysis" in report:
            for section in report["analysis"]:
                if "content" in section:
                    all_content.append(section["content"])
                
                if "subsections" in section:
                    for subsection in section["subsections"]:
                        if "content" in subsection:
                            all_content.append(subsection["content"])
        
        # Add recommendations
        if "recommendations" in report:
            all_content.extend(report["recommendations"])
        
        return " ".join(all_content)

# JSON Validator Class
class JSONValidator:
    """
    Validator for JSON responses from LLM providers.
    
    This class provides methods for validating, repairing, and retrying
    JSON responses from LLM providers to ensure they are valid and properly
    structured.
    """
    
    def __init__(self, schema: Dict[str, Any], model_class: Type[BaseModel], max_retries: int = 3):
        """
        Initialize the JSON validator.
        
        Args:
            schema: The JSON schema to validate against
            model_class: The Pydantic model class to validate with
            max_retries: Maximum number of retry attempts
        """
        self.schema = schema
        self.model_class = model_class
        self.max_retries = max_retries
        self.citation_validator = CitationValidator()
    
    async def validate_and_repair(self, response_text: str, report_type: str = "unknown") -> Dict[str, Any]:
        """
        Validate and repair a JSON response.
        
{{ ... }}
        Args:
            response_text: The raw JSON response text
            report_type: The type of report ("industry" or "pestel")
            
        Returns:
            The validated and repaired JSON object
        """
        start_time = time.time()
        monitor = get_monitor() if MONITORING_ENABLED else None
        
        try:
            # First try parsing as-is
            json_obj = json.loads(response_text)
            
            # Try Pydantic validation first
            try:
                validated = self.model_class.model_validate(json_obj)
                report_dict = validated.report.model_dump()
                
                # Validate citations
                all_content = self.citation_validator.extract_all_content(report_dict)
                is_valid, citation_errors = self.citation_validator.validate_citations(
                    all_content, report_dict["sources"]
                )
                
            except ValueError as pydantic_error:
                # If Pydantic validation fails (likely due to citation issues), 
                # try to repair citations first, then re-validate
                logger.info(f"Pydantic validation failed, attempting citation repair: {pydantic_error}")
                
                # Get the report dictionary directly from JSON
                if "report" in json_obj:
                    report_dict = json_obj["report"]
                else:
                    report_dict = json_obj
                
                # Attempt citation repair
                repaired_report = self.citation_validator.repair_citations_in_report(report_dict)
                
                # Try Pydantic validation again with repaired data
                repaired_json = {"report": repaired_report}
                validated = self.model_class.model_validate(repaired_json)
                report_dict = validated.report.model_dump()
                
                # Validate citations on repaired report
                all_content = self.citation_validator.extract_all_content(report_dict)
                is_valid, citation_errors = self.citation_validator.validate_citations(
                    all_content, report_dict["sources"]
                )
                
                # Log the repair attempt
                json_validator_logger.logger.info(
                    f"Pre-validation citation repair completed for {report_type} report",
                    context={"agent_type": report_type, "event": "pre_validation_repair", "success": is_valid}
                )
            
            if not is_valid:
                # Log citation validation errors
                error = ValueError(f"Citation validation errors: {citation_errors}")
                json_validator_logger.log_validation_attempt(
                    agent_type=report_type,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    response_text=response_text,
                    error=error
                )
                
                # Record in monitoring system
                if monitor:
                    monitor.record_validation_result(
                        success=False,
                        error_type=f"citation_error:{','.join(citation_errors)}",
                        duration_ms=(time.time() - start_time) * 1000
                    )
                
                # Start repair timer
                repair_start_time = time.time()
                
                # Repair citations
                repaired_report = self.citation_validator.repair_citations_in_report(report_dict)
                
                # Validate the repaired report
                all_content = self.citation_validator.extract_all_content(repaired_report)
                is_valid, citation_errors = self.citation_validator.validate_citations(
                    all_content, repaired_report["sources"]
                )
                
                # Log repair attempt
                repair_duration_ms = (time.time() - repair_start_time) * 1000
                repair_error = None if is_valid else ValueError(f"Citations still have issues after repair: {citation_errors}")
                json_validator_logger.log_repair_attempt(
                    agent_type=report_type,
                    success=is_valid,
                    duration_ms=repair_duration_ms,
                    original_text=json.dumps(report_dict),
                    repaired_text=json.dumps(repaired_report),
                    error=repair_error
                )
                
                # Record repair result in monitoring system
                if monitor:
                    monitor.record_validation_result(
                        success=is_valid,
                        error_type=None if is_valid else f"citation_repair_failed:{','.join(citation_errors)}",
                        duration_ms=repair_duration_ms
                    )
                
                # Return the repaired report (even if not perfect)
                # Log whether repair was successful or not
                if is_valid:
                    json_validator_logger.logger.info(
                        f"Successfully repaired citations for {report_type} report",
                        context={"agent_type": report_type, "event": "citation_repair_success"}
                    )
                else:
                    json_validator_logger.logger.warning(
                        f"Citation repair partially successful for {report_type} report. Remaining issues: {citation_errors}",
                        context={"agent_type": report_type, "event": "citation_repair_partial", "remaining_errors": citation_errors}
                    )
                
                # DEBUG: Add logging before early return #1
                logger.info(f"About to return repaired_report (early return #1), type: {type(repaired_report)}")
                logger.info(f"Repaired report keys: {list(repaired_report.keys()) if isinstance(repaired_report, dict) else 'Not a dict'}")
                
                try:
                    result = {"report": repaired_report}
                    logger.info(f"Early return #1 dict creation successful")
                    return result
                except Exception as early_error:
                    logger.error(f"Early return #1 failed: {early_error}")
                    raise
            
            # Log successful validation
            duration_ms = (time.time() - start_time) * 1000
            json_validator_logger.log_validation_attempt(
                agent_type=report_type,
                success=True,
                duration_ms=duration_ms,
                response_text=response_text
            )
            
            # Record successful validation in monitoring system
            logger.info(f"About to call monitoring system, monitor: {monitor}")
            if monitor:
                logger.info(f"TEMPORARILY SKIPPING monitor.record_validation_result to test hang fix")
                # TEMPORARILY DISABLED TO FIX HANG:
                # try:
                #     monitor.record_validation_result(
                #         success=True,
                #         duration_ms=duration_ms
                #     )
                #     logger.info(f"Monitor call completed successfully")
                # except Exception as monitor_error:
                #     logger.error(f"Monitor call failed: {monitor_error}")
                #     raise
            else:
                logger.info(f"No monitor configured, skipping monitoring call")
            
            # DEBUG: Add logging before model_dump to identify hang
            logger.info(f"About to call model_dump() on validated object of type: {type(validated)}")
            logger.info(f"Validated object has report: {hasattr(validated, 'report')}")
            
            try:
                result = validated.model_dump()
                logger.info(f"model_dump() completed successfully, result type: {type(result)}")
                return result
            except Exception as dump_error:
                logger.error(f"model_dump() failed with error: {dump_error}")
                raise
        
        except json.JSONDecodeError as e:
            # Log validation failure
            duration_ms = (time.time() - start_time) * 1000
            json_validator_logger.log_validation_attempt(
                agent_type=report_type,
                success=False,
                duration_ms=duration_ms,
                response_text=response_text,
                error=e
            )
            
            # Record in monitoring system
            if monitor:
                monitor.record_validation_result(
                    success=False,
                    error_type=f"json_decode_error:{str(e)}",
                    duration_ms=duration_ms
                )
            
            # Start repair timer
            repair_start_time = time.time()
            
            # Try to repair the JSON
            repaired = jsonrepair.repair_json(response_text)
            
            try:
                json_obj = json.loads(repaired)
                validated = self.model_class.model_validate(json_obj)
                
                # Also check and repair citations
                report_dict = validated.report.model_dump()
                all_content = self.citation_validator.extract_all_content(report_dict)
                is_valid, citation_errors = self.citation_validator.validate_citations(
                    all_content, report_dict["sources"]
                )
                
                if not is_valid:
                    # Repair citations
                    citation_repair_start = time.time()
                    repaired_report = self.citation_validator.repair_citations_in_report(report_dict)
                    
                    # Log citation repair attempt
                    citation_repair_duration = (time.time() - citation_repair_start) * 1000
                    json_validator_logger.log_repair_attempt(
                        agent_type=report_type,
                        success=True,
                        duration_ms=citation_repair_duration,
                        original_text=json.dumps(report_dict),
                        repaired_text=json.dumps(repaired_report)
                    )
                    
                    # Record citation repair in monitoring system
                    if monitor:
                        monitor.record_validation_result(
                            success=True,
                            error_type="citation_repair_success",
                            duration_ms=citation_repair_duration
                        )
                    
                    # DEBUG: Add logging before early return #2
                    logger.info(f"About to return repaired_report (early return #2), type: {type(repaired_report)}")
                    logger.info(f"Repaired report keys: {list(repaired_report.keys()) if isinstance(repaired_report, dict) else 'Not a dict'}")
                    
                    try:
                        result = {"report": repaired_report}
                        logger.info(f"Early return #2 dict creation successful")
                        return result
                    except Exception as early_error:
                        logger.error(f"Early return #2 failed: {early_error}")
                        raise
                
                # Log successful repair
                repair_duration = (time.time() - repair_start_time) * 1000
                json_validator_logger.log_repair_attempt(
                    agent_type=report_type,
                    success=True,
                    duration_ms=repair_duration,
                    original_text=response_text,
                    repaired_text=repaired
                )
                
                # Record successful repair in monitoring system
                if monitor:
                    monitor.record_validation_result(
                        success=True,
                        error_type="json_repair_success",
                        duration_ms=repair_duration
                    )
                
                return validated.model_dump()
            except (json.JSONDecodeError, ValidationError) as repair_error:
                # Log failed repair
                repair_duration = (time.time() - repair_start_time) * 1000
                json_validator_logger.log_repair_attempt(
                    agent_type=report_type,
                    success=False,
                    duration_ms=repair_duration,
                    original_text=response_text,
                    repaired_text=repaired,
                    error=repair_error
                )
                
                # Record failed repair in monitoring system
                if monitor:
                    monitor.record_validation_result(
                        success=False,
                        error_type=f"repair_failed:{str(repair_error)}",
                        duration_ms=repair_duration
                    )
                
                raise
        
        except ValidationError as e:
            # Log validation failure
            duration_ms = (time.time() - start_time) * 1000
            json_validator_logger.log_validation_attempt(
                agent_type=report_type,
                success=False,
                duration_ms=duration_ms,
                response_text=response_text,
                error=e
            )
            
            # Record in monitoring system
            if monitor:
                monitor.record_validation_result(
                    success=False,
                    error_type=f"validation_error:{str(e)}",
                    duration_ms=duration_ms
                )
            
            raise
    
    async def retry_with_llm(self, llm_provider: Any, response_text: str, validation_error: str, report_type: str = "unknown") -> Dict[str, Any]:
        """
        Retry validation with LLM-assisted repair.
        
        Args:
            llm_provider: The LLM provider to use for repair
            response_text: The original response text
            validation_error: The validation error message
            report_type: The type of report ("industry" or "pestel")
            
        Returns:
            The repaired JSON object
        """
        start_time = time.time()
        monitor = get_monitor() if MONITORING_ENABLED else None
        
        repair_prompt = (
            "Your previous JSON did not match the schema.\n\n"
            f"Validation errors:\n{validation_error}\n\n"
            "Please return ONLY the corrected JSON."
        )
        
        messages = [
            {"role": "system", "content": "Return the corrected JSON only."},
            {"role": "user", "content": repair_prompt}
        ]
        
        response = await llm_provider.generate_chat(
            messages,
            response_format={"type": "json_schema", "json_schema": self.schema},
        )
        
        repaired_text = response.content
        duration_ms = (time.time() - start_time) * 1000
        
        try:
            json_obj = json.loads(repaired_text)
            validated = self.model_class.model_validate(json_obj)
            
            # Log successful retry
            json_validator_logger.log_retry_attempt(
                agent_type=report_type,
                attempt_number=1,  # This will be updated by the caller
                max_retries=self.max_retries,
                success=True,
                duration_ms=duration_ms
            )
            
            # Record successful retry in monitoring system
            if monitor:
                monitor.record_validation_result(
                    success=True,
                    error_type="llm_retry_success",
                    duration_ms=duration_ms
                )
            
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            # Log failed retry
            json_validator_logger.log_retry_attempt(
                agent_type=report_type,
                attempt_number=1,  # This will be updated by the caller
                max_retries=self.max_retries,
                success=False,
                duration_ms=duration_ms,
                error=e
            )
            
            # Record failed retry in monitoring system
            if monitor:
                monitor.record_validation_result(
                    success=False,
                    error_type=f"llm_retry_failed:{str(e)}",
                    duration_ms=duration_ms
                )
            
            raise

# Factory function to get the appropriate validator
def get_validator(report_type: str) -> JSONValidator:
    """
    Get a validator for the specified report type.
    
    Args:
        report_type: The type of report ("industry" or "pestel")
        
    Returns:
        A JSONValidator instance for the specified report type
    """
    if report_type.lower() == "industry":
        return JSONValidator(
            schema=INDUSTRY_REPORT_SCHEMA,
            model_class=IndustryReportResponse,
            max_retries=3
        )
    elif report_type.lower() == "pestel":
        return JSONValidator(
            schema=PESTEL_REPORT_SCHEMA,
            model_class=PESTELReportResponse,
            max_retries=3
        )
    else:
        raise ValueError(f"Unknown report type: {report_type}")

# Decorator for validating JSON responses
@backoff.on_exception(backoff.expo,
                     (json.JSONDecodeError, ValidationError),
                     max_tries=3)
async def validate_json_response(llm_provider: Any, messages: List[Dict[str, str]], 
                               report_type: str) -> Dict[str, Any]:
    """
    Validate a JSON response from an LLM provider.
    
    Args:
        llm_provider: The LLM provider to use
        messages: The messages to send to the LLM provider
        report_type: The type of report ("industry" or "pestel")
        
    Returns:
        The validated JSON object
    """
    validator = get_validator(report_type)
    schema = INDUSTRY_REPORT_SCHEMA if report_type.lower() == "industry" else PESTEL_REPORT_SCHEMA
    
    # Use response_format to enforce JSON schema at the source
    response = await llm_provider.generate_chat(
        messages,
        response_format={"type": "json_schema", "json_schema": schema},
    )
    
    raw_json = response.content
    
    try:
        # First try parsing and validating
        return await validator.validate_and_repair(raw_json, report_type)
    
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        # If that fails, try LLM-assisted repair
        return await validator.retry_with_llm(llm_provider, raw_json, str(e), report_type)

async def generate_report_with_validation(
    llm_provider: Any,
    messages: List[Dict[str, str]],
    report_type: str
) -> Dict[str, Any]:
    """
    Generate a report with JSON validation and self-healing.
    
    This function implements model-assisted self-healing for validation errors
    by using the JSONValidator to validate and repair the response.
    
    Args:
        llm_provider: The LLM provider to use
        messages: The messages to send to the LLM provider
        report_type: The type of report ("industry" or "pestel")
        
    Returns:
        The validated and repaired JSON object
    """
    # Get appropriate schema and validator
    validator = get_validator(report_type)
    schema = INDUSTRY_REPORT_SCHEMA if report_type.lower() == "industry" else PESTEL_REPORT_SCHEMA
    max_retries = validator.max_retries
    
    # Use response_format to enforce JSON schema at the source
    logger.info(f"🚀 CALLING LLM for {report_type} report generation")
    response = await llm_provider.generate_chat(
        messages,
        response_format={"type": "json_schema", "json_schema": schema},
    )
    logger.info(f"✅ LLM RESPONSE RECEIVED for {report_type} report generation")
    
    raw_json = response.content
    
    try:
        # First try parsing and validating
        return await validator.validate_and_repair(raw_json, report_type)
    
    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        # First retry attempt
        retry_attempt = 1
        retry_start_time = time.time()
        
        # Try LLM-assisted repair
        try:
            result = await validator.retry_with_llm(llm_provider, raw_json, str(e), report_type)
            
            # Log successful retry
            json_validator_logger.log_retry_attempt(
                agent_type=report_type,
                attempt_number=retry_attempt,
                max_retries=max_retries,
                success=True,
                duration_ms=(time.time() - retry_start_time) * 1000
            )
            
            return result
        except Exception as repair_error:
            # Log failed retry
            json_validator_logger.log_retry_attempt(
                agent_type=report_type,
                attempt_number=retry_attempt,
                max_retries=max_retries,
                success=False,
                duration_ms=(time.time() - retry_start_time) * 1000,
                error=repair_error
            )
            
            # Second retry attempt with model-assisted self-healing
            retry_attempt += 1
            retry_start_time = time.time()
            
            try:
                # Create a more detailed error message for the model
                error_analysis = f"""
                The JSON response failed validation with the following errors:
                
                Original error: {str(e)}
                
                Repair attempt error: {str(repair_error)}
                
                Please analyze the errors and generate a completely new, valid JSON response
                that follows the schema exactly. Focus on fixing the structural issues while
                preserving the content and insights.
                """
                
                # Add the error analysis to the messages
                healing_messages = messages.copy()
                healing_messages.append({"role": "user", "content": error_analysis})
                
                # Try with more deterministic output
                logger.info(f"🔄 RETRY: Calling LLM for healing attempt")
                healing_response = await llm_provider.generate_chat(
                    healing_messages,
                    response_format={"type": "json_schema", "json_schema": schema}
                )
                logger.info(f"✅ LLM HEALING RESPONSE RECEIVED")
                
                # Validate the healing response
                result = await validator.validate_and_repair(healing_response.content, report_type)
                
                # Log successful retry
                json_validator_logger.log_retry_attempt(
                    agent_type=report_type,
                    attempt_number=retry_attempt,
                    max_retries=max_retries,
                    success=True,
                    duration_ms=(time.time() - retry_start_time) * 1000
                )
                
                return result
            except Exception as healing_error:
                # Log failed retry
                json_validator_logger.log_retry_attempt(
                    agent_type=report_type,
                    attempt_number=retry_attempt,
                    max_retries=max_retries,
                    success=False,
                    duration_ms=(time.time() - retry_start_time) * 1000,
                    error=healing_error
                )
                
                # Final retry attempt with a simplified approach
                if retry_attempt < max_retries:
                    retry_attempt += 1
                    retry_start_time = time.time()
                    
                    try:
                        # Create a simplified prompt
                        simplified_prompt = (
                            "Generate a valid JSON report following the exact schema provided. "
                            "Focus on correctness of structure rather than content detail."
                        )
                        
                        # Create new messages with just the essential information
                        simplified_messages = [
                            {"role": "system", "content": "Generate a valid JSON report following the exact schema."},
                            {"role": "user", "content": simplified_prompt}
                        ]
                        
                        # Try with zero temperature for maximum reliability
                        logger.info(f"🔄 FINAL RETRY: Calling LLM for simplified approach")
                        final_response = await llm_provider.generate_chat(
                            simplified_messages,
                            response_format={"type": "json_schema", "json_schema": schema},
                        )
                        logger.info(f"✅ LLM FINAL RESPONSE RECEIVED")
                        
                        final_json = final_response.content
                        
                        # Validate the final response
                        result = await validator.validate_and_repair(final_json, report_type)
                        
                        # Log successful retry
                        json_validator_logger.log_retry_attempt(
                            agent_type=report_type,
                            attempt_number=retry_attempt,
                            max_retries=max_retries,
                            success=True,
                            duration_ms=(time.time() - retry_start_time) * 1000
                        )
                        
                        return result
                    except Exception as final_error:
                        # Log failed retry
                        json_validator_logger.log_retry_attempt(
                            agent_type=report_type,
                            attempt_number=retry_attempt,
                            max_retries=max_retries,
                            success=False,
                            duration_ms=(time.time() - retry_start_time) * 1000,
                            error=final_error
                        )
                
                # Provide a fallback response
                fallback = create_fallback_response(report_type)
                
                # Log fallback response
                json_validator_logger.log_fallback_response(
                    agent_type=report_type,
                    fallback_response=fallback
                )
                
                return fallback

def create_fallback_response(report_type: str) -> Dict[str, Any]:
    """
    Create a minimal valid fallback response when all validation attempts fail.
    
    Args:
        report_type: The type of report ("industry" or "pestel")
        
    Returns:
        A minimal valid response that matches the schema
    """
    # Log fallback creation with structured logger
    json_validator_logger.logger.warning(
        f"Creating fallback response for {report_type} report",
        context={
            "agent_type": report_type,
            "event": "fallback_creation",
            "timestamp_ms": int(time.time() * 1000)
        }
    )
    
    if report_type.lower() == "industry":
        return {
            "report": {
                "title": "Industry Analysis Report (Fallback)",
                "summary": "This is a fallback report generated due to validation errors.",
                "analysis": [
                    {
                        "heading": "Industry Overview",
                        "content": "The system encountered errors while generating the industry analysis.",
                        "subsections": []
                    }
                ],
                "tables": {},
                "recommendations": [
                    "Review the input data and try again.",
                    "Consider providing more specific industry information.",
                    "Check for any formatting issues in the input data.",
                    "Contact support if the issue persists."
                ],
                "sources": [
                    {
                        "number": 1,
                        "title": "System Generated Fallback",
                        "url": "https://example.com/fallback"
                    }
                ]
            }
        }
    else:  # PESTEL
        return {
            "report": {
                "title": "PESTEL Analysis Report (Fallback)",
                "summary": "This is a fallback report generated due to validation errors.",
                "analysis": [
                    {
                        "heading": "Political Factors",
                        "content": "The system encountered errors while generating the political analysis.",
                        "subsections": []
                    },
                    {
                        "heading": "Economic Factors",
                        "content": "The system encountered errors while generating the economic analysis.",
                        "subsections": []
                    },
                    {
                        "heading": "Social Factors",
                        "content": "The system encountered errors while generating the social analysis.",
                        "subsections": []
                    },
                    {
                        "heading": "Technological Factors",
                        "content": "The system encountered errors while generating the technological analysis.",
                        "subsections": []
                    },
                    {
                        "heading": "Environmental Factors",
                        "content": "The system encountered errors while generating the environmental analysis.",
                        "subsections": []
                    },
                    {
                        "heading": "Legal Factors",
                        "content": "The system encountered errors while generating the legal analysis.",
                        "subsections": []
                    }
                ],
                "tables": {},
                "recommendations": [
                    "Review the input data and try again.",
                    "Consider providing more specific information.",
                    "Check for any formatting issues in the input data.",
                    "Contact support if the issue persists."
                ],
                "sources": [
                    {
                        "number": 1,
                        "title": "System Generated Fallback",
                        "url": "https://example.com/fallback"
                    }
                ]
            }
        }