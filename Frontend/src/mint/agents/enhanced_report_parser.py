#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Report Parser for MINT Agents.

This module provides robust parsing functionality for the new dynamic-structure
report format with retry logic and comprehensive error handling.
"""

import json
import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Import JSON validation components
from .json_validator import JSONValidator, CitationValidator, get_validator

# Configure logging
logger = logging.getLogger(__name__)

class ReportParsingError(Exception):
    """Custom exception for report parsing failures."""
    pass

class EnhancedReportParser:
    """Enhanced parser for dynamic-structure reports with retry logic."""
    
    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        self.retry_count = 0
    
    async def parse_report_with_retry(self, 
                                    llm_provider, 
                                    messages: List[Dict[str, str]], 
                                    report_type: str = "industry") -> Dict[str, Any]:
        """
        Parse report with retry logic for robust JSON extraction.
        
        Args:
            llm_provider: The LLM provider instance
            messages: List of messages for the LLM
            report_type: Type of report ("industry" or "pestel")
            
        Returns:
            Parsed report data
            
        Raises:
            ReportParsingError: If parsing fails after all retries
        """
        self.retry_count = 0
        last_error = None
        
        for attempt in range(self.max_retries):
            self.retry_count = attempt + 1
            logger.info(f"Report parsing attempt {self.retry_count}/{self.max_retries}")
            
            try:
                # Get LLM response
                response = await llm_provider.generate_responses(messages)
                response_text = response.content
                
                logger.debug(f"LLM response (attempt {self.retry_count}): {response_text[:500]}...")
                
                # Parse the response
                parsed_data = await self._parse_json_response(response_text, report_type)
                
                logger.info(f"Successfully parsed {report_type} report on attempt {self.retry_count}")
                return parsed_data
                
            except Exception as e:
                last_error = e
                logger.warning(f"Parsing attempt {self.retry_count} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Add delay between retries with exponential backoff
                    delay = 2 ** attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} parsing attempts failed")
        
        # If we get here, all retries failed
        raise ReportParsingError(f"Failed to parse {report_type} report after {self.max_retries} attempts. Last error: {str(last_error)}")
    
    async def _parse_json_response(self, response_text: str, report_type: str) -> Dict[str, Any]:
        """
        Parse JSON response with enhanced error handling for new format.
        
        Args:
            response_text: Raw LLM response text
            report_type: Type of report for validation
            
        Returns:
            Parsed and validated report data
        """
        try:
            # Step 1: Clean and extract JSON
            json_text = self._extract_json_from_response(response_text)
            
            if not json_text or json_text.strip() == "":
                raise ValueError("No JSON content found in response")
            
            # Step 2: Use the JSONValidator for validation and repair
            from .json_validator import get_validator
            
            # Get the appropriate validator for the report type
            validator = get_validator(report_type)
            
            try:
                # Validate and repair the JSON
                validated_data = await validator.validate_and_repair(json_text, report_type)
                
                if not validated_data or "report" not in validated_data:
                    raise ValueError("Validation failed - no valid report structure found")
                
                # Step 3: Convert to legacy format for compatibility
                legacy_format = self._convert_to_legacy_format(validated_data, report_type)
                
                if not legacy_format or not isinstance(legacy_format, dict):
                    raise ValueError("Legacy format conversion failed")
                
                return legacy_format
                
            except Exception as validation_error:
                logger.error(f"JSON validation error: {str(validation_error)}")
                # Fall back to the old parsing method if validation fails
                logger.warning("Falling back to legacy parsing method")
                
                # Step 1.5: Preprocess to fix malformed citations before JSON parsing
                json_text = self._preprocess_malformed_citations(json_text)
                
                # Step 2: Parse JSON with repair attempts
                report_data = self._parse_json_with_repair(json_text)
                
                if not report_data or not isinstance(report_data, dict):
                    raise ValueError("Parsed data is not a valid dictionary")
                
                # Step 3: Validate structure for new format
                validated_data = self._validate_new_report_structure(report_data, report_type)
                
                if not validated_data or "report" not in validated_data:
                    raise ValueError("Validation failed - no valid report structure found")
                
                # Step 4: Deduplicate sources and update citations
                validated_data["report"] = self._deduplicate_sources(validated_data["report"])
                
                # Step 5: Convert to legacy format for compatibility
                legacy_format = self._convert_to_legacy_format(validated_data, report_type)
                
                if not legacy_format or not isinstance(legacy_format, dict):
                    raise ValueError("Legacy format conversion failed")
                
                return legacy_format
            
        except Exception as e:
            logger.error(f"Error in _parse_json_response: {str(e)}")
            logger.debug(f"Response text (first 500 chars): {response_text[:500]}...")
            
            # Create a fallback report structure
            fallback_report = self._create_fallback_report(report_type, str(e))
            return fallback_report
    
    def parse_report(self, response_text: str, report_type: str = "industry") -> Dict[str, Any]:
        """Public method for testing - parse a report response synchronously."""
        return asyncio.run(self._parse_json_response(response_text, report_type))
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from LLM response, handling various formats."""
        json_text = response_text.strip()
        
        # Remove markdown code blocks
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        elif json_text.startswith('```'):
            json_text = json_text[3:]
            
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        
        # Find JSON boundaries
        if '{' in json_text and '}' in json_text:
            start = json_text.find('{')
            end = json_text.rfind('}') + 1
            json_text = json_text[start:end]
        
        return json_text.strip()
    
    def _parse_json_with_repair(self, json_text: str) -> Dict[str, Any]:
        """Parse JSON with automatic repair for common issues."""
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parsing failed: {e}. Attempting repair...")
            
            # Attempt to repair common JSON issues
            repaired_json = self._repair_json(json_text)
            
            try:
                return json.loads(repaired_json)
            except json.JSONDecodeError as repair_error:
                logger.error(f"JSON repair also failed: {repair_error}")
                raise ValueError(f"Unable to parse JSON. Original error: {e}, Repair error: {repair_error}")
    
    def _repair_json(self, json_text: str) -> str:
        """Repair common JSON formatting issues."""
        repaired = json_text
        
        # 1. Fix truncated JSON by adding missing closing braces/brackets
        open_braces = repaired.count('{')
        close_braces = repaired.count('}')
        if open_braces > close_braces:
            repaired += '}' * (open_braces - close_braces)
        
        open_brackets = repaired.count('[')
        close_brackets = repaired.count(']')
        if open_brackets > close_brackets:
            repaired += ']' * (open_brackets - close_brackets)
        
        # 2. Fix unquoted property names
        repaired = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', repaired)
        
        # 3. Fix trailing commas
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        
        # 4. Fix missing commas between objects/arrays
        repaired = re.sub(r'}\s*{', r'}, {', repaired)
        repaired = re.sub(r']\s*\[', r'], [', repaired)
        
        # 5. Fix single quotes to double quotes
        repaired = re.sub(r"'([^']*)':", r'"\1":', repaired)
        
        # 6. Fix comments in JSON (/* ... */)
        repaired = re.sub(r'/\*.*?\*/', '', repaired, flags=re.DOTALL)
        
        return repaired
    
    def _deduplicate_sources(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Deduplicate sources by URL and renumber citations accordingly using CitationValidator."""
        if "sources" not in report or not report["sources"]:
            return report
        
        # Use the CitationValidator to fix non-sequential sources
        citation_validator = CitationValidator()
        
        # Fix non-sequential sources
        report["sources"] = citation_validator.fix_non_sequential_sources(report["sources"])
        
        # Create a mapping of old source numbers to new ones
        source_map = {s["number"]: i+1 for i, s in enumerate(report["sources"])}
        for i, source in enumerate(report["sources"], 1):
            source["number"] = i
        
        # Extract all content for citation validation
        all_content = citation_validator.extract_all_content(report)
        
        # Validate citations against sources
        is_valid, citation_errors = citation_validator.validate_citations(all_content, report["sources"])
        
        if not is_valid:
            logger.warning(f"Citation validation issues: {citation_errors}")
            
            # Use the citation validator to repair the report
            report = citation_validator.repair_citations_in_report(report)
            
        return report
    
    def _preprocess_malformed_citations(self, text: str) -> str:
        """Preprocess text to fix malformed citations like [1][1][1] -> [1] before JSON parsing."""
        if not text:
            return text
        
        # Use the CitationValidator to fix duplicate citations
        citation_validator = CitationValidator()
        fixed_text = citation_validator.fix_duplicate_citations(text)
        
        logger.debug(f"Preprocessed malformed citations in text")
        return fixed_text
    
    def _create_fallback_report(self, report_type: str, error_message: str) -> Dict[str, Any]:
        """Create a fallback report structure when parsing fails completely."""
        logger.warning(f"Creating fallback report for {report_type} due to parsing failure: {error_message}")
        
        fallback_content = f"""## Analysis Error

The {report_type} analysis could not be completed due to a parsing error in the LLM response.

**Error Details**: {error_message}

**Recommended Actions**:
- Review the input data quality
- Check for any formatting issues in the source facts
- Retry the analysis with simplified parameters
- Contact support if the issue persists

This is a fallback report generated to maintain system stability."""
        
        return {
            "title": f"{report_type.title()} Analysis Report (Error)",
            "summary": f"Analysis failed due to parsing error: {error_message[:100]}...",
            "sections": {
                f"{report_type.title()} Analysis": [{
                    "content": fallback_content
                }]
            },
            "recommendations": [
                f"Review and retry the {report_type} analysis with corrected input data.",
                "Check system logs for detailed error information.",
                "Contact technical support if the issue persists."
            ],
            "sources": []
        }
        
        # Update citations in analysis sections
        if "analysis" in report and isinstance(report["analysis"], list):
            for section in report["analysis"]:
                if isinstance(section, dict):
                    if "content" in section:
                        section["content"] = update_citations_in_text(section["content"])
                    
                    # Update subsections
                    if "subsections" in section and isinstance(section["subsections"], list):
                        for subsection in section["subsections"]:
                            if isinstance(subsection, dict) and "content" in subsection:
                                subsection["content"] = update_citations_in_text(subsection["content"])
        
        # Update citations in summary
        if "summary" in report:
            report["summary"] = update_citations_in_text(report["summary"])
        
        # Update citations in recommendations
        if "recommendations" in report and isinstance(report["recommendations"], list):
            for i, rec in enumerate(report["recommendations"]):
                if isinstance(rec, dict):
                    for key in ["recommendation", "rationale", "description", "content"]:
                        if key in rec and isinstance(rec[key], str):
                            rec[key] = update_citations_in_text(rec[key])
                elif isinstance(rec, str):
                    report["recommendations"][i] = update_citations_in_text(rec)
        
        # Replace sources with deduplicated list
        report["sources"] = unique_sources
        
        logger.info(f"Deduplicated sources: {len(report.get('sources', []))} -> {len(unique_sources)} unique sources")
        return report
    
    def _validate_new_report_structure(self, report_data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
        """Validate the new dynamic report structure."""
        if "report" not in report_data:
            raise ValueError("Missing 'report' key in response")
        
        report = report_data["report"]
        required_keys = ["title", "summary", "analysis", "recommendations", "sources"]
        
        for key in required_keys:
            if key not in report:
                logger.warning(f"Missing required key '{key}' in report")
                # Provide default values
                if key == "analysis":
                    report[key] = []
                elif key == "recommendations":
                    report[key] = []
                elif key == "sources":
                    report[key] = []
                elif key == "title":
                    report[key] = f"{report_type.title()} Analysis Report"
                elif key == "summary":
                    report[key] = "Summary not provided"
        
        # Validate analysis structure (should be array of section objects)
        if not isinstance(report["analysis"], list):
            raise ValueError("'analysis' should be an array of section objects")
        
        # Validate each analysis section
        for i, section in enumerate(report["analysis"]):
            if not isinstance(section, dict):
                raise ValueError(f"Analysis section {i} should be an object")
            
            if "heading" not in section:
                section["heading"] = f"Section {i+1}"
            
            if "content" not in section:
                section["content"] = ""
            
            # Validate subsections if present
            if "subsections" in section:
                if not isinstance(section["subsections"], list):
                    section["subsections"] = []
                
                for j, subsection in enumerate(section["subsections"]):
                    if not isinstance(subsection, dict):
                        continue
                    if "heading" not in subsection:
                        subsection["heading"] = f"Subsection {j+1}"
                    if "content" not in subsection:
                        subsection["content"] = ""
        
        # Validate tables structure
        if "tables" in report:
            if not isinstance(report["tables"], dict):
                report["tables"] = {}
            
            # Validate each table
            for table_name, table_data in report["tables"].items():
                if not isinstance(table_data, dict):
                    continue
                if "headers" not in table_data:
                    table_data["headers"] = []
                if "rows" not in table_data:
                    table_data["rows"] = []
        else:
            report["tables"] = {}
        
        # Validate sources structure
        if isinstance(report["sources"], list):
            for source in report["sources"]:
                if isinstance(source, dict):
                    # Ensure required source fields
                    if "number" not in source:
                        source["number"] = 1
                    if "title" not in source:
                        source["title"] = "Unknown Source"
                    if "url" not in source:
                        source["url"] = ""
        
        return report_data
    
    def _convert_to_legacy_format(self, validated_data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
        """Convert new format to legacy format for compatibility with existing code."""
        report = validated_data["report"]
        
        # Instead of converting to sections, maintain the dynamic structure
        # but create a single analysis section that contains all the dynamic content
        analysis_content = ""
        
        for i, section in enumerate(report["analysis"]):
            section_name = section["heading"]
            section_content = section["content"]
            
            # Add section heading
            analysis_content += f"## {section_name}\n\n{section_content}\n\n"
            
            # Handle subsections by appending to main content
            if "subsections" in section and section["subsections"]:
                for subsection in section["subsections"]:
                    analysis_content += f"### {subsection['heading']}\n\n{subsection['content']}\n\n"
            
            # Handle table references in content
            if "tables" in report and report["tables"]:
                for table_name, table_data in report["tables"].items():
                    table_placeholder = f"{{TABLE: {table_name}}}"
                    if table_placeholder in analysis_content:
                        # Convert table to markdown format
                        table_md = self._convert_table_to_markdown(table_data)
                        analysis_content = analysis_content.replace(table_placeholder, table_md)
        
        # Create a single analysis section instead of multiple fixed sections
        sections = {
            f"{report_type.title()} Analysis": [{
                "content": analysis_content.strip()
            }]
        }
        
        # Prepare sources list
        sources_list = []
        if report.get("sources"):
            for source in report["sources"]:
                if isinstance(source, dict):
                    sources_list.append({
                        "number": source.get("number", 1),
                        "source_url": source.get("url", ""),
                        "source_title": source.get("title", "Unknown Source")
                    })
        
        # Return in legacy format
        return {
            "title": report.get("title", f"{report_type.title()} Analysis"),
            "summary": report.get("summary", ""),
            "sections": sections,
            "recommendations": report.get("recommendations", []),
            "sources": sources_list
        }
    
    def _convert_table_to_markdown(self, table_data: Dict[str, Any]) -> str:
        """Convert table data to markdown format."""
        if not isinstance(table_data, dict) or "headers" not in table_data or "rows" not in table_data:
            return ""
        
        headers = table_data["headers"]
        rows = table_data["rows"]
        
        if not headers or not rows:
            return ""
        
        # Create markdown table
        md_lines = []
        
        # Header row
        md_lines.append("| " + " | ".join(headers) + " |")
        
        # Separator row
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Data rows
        for row in rows:
            if isinstance(row, list) and len(row) >= len(headers):
                md_lines.append("| " + " | ".join(str(cell) for cell in row[:len(headers)]) + " |")
        
        return "\n".join(md_lines)


# Global parser instance
_parser_instance = None

def get_enhanced_parser(max_retries: int = 5) -> EnhancedReportParser:
    """Get singleton instance of enhanced parser."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = EnhancedReportParser(max_retries=max_retries)
    return _parser_instance
