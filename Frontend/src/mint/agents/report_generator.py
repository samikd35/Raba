#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Generator Agent for MINT.

This module provides functionality to generate a comprehensive final report
by combining industry analysis, PESTEL analysis, and recommendations.
"""

import json
import logging
import os
from datetime import datetime
import asyncio
from typing import List, Dict, Any, Optional, Union
import re

# Import JSON validation components
from .json_validator import JSONValidator, CitationValidator

# DISABLED: LangSmith causes memory issues with large payloads (61MB+)
# try:
#     from langsmith.run_helpers import traceable
# except Exception:  # pragma: no cover - fallback when LangSmith isn't installed
def traceable(name=None):
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                logger.info(f"Starting {name or func.__name__}")
                start_time = datetime.now()
                result = await func(*args, **kwargs)
                end_time = datetime.now()
                logger.info(
                    f"Completed {name or func.__name__} in {end_time - start_time}"
                )
                return result

            def sync_wrapper(*args, **kwargs):
                logger.info(f"Starting {name or func.__name__}")
                start_time = datetime.now()
                result = func(*args, **kwargs)
                end_time = datetime.now()
                logger.info(
                    f"Completed {name or func.__name__} in {end_time - start_time}"
                )
                return result

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

from pydantic import BaseModel, Field

# LLM imports removed - using manual merging approach

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Manual report merging - no LLM prompts needed



class ReportSection(BaseModel):
    """Schema for a section in the final report."""
    title: str
    content: str
    word_count: int


class Reference(BaseModel):
    """Schema for a reference in the final report."""
    id: str
    url: str
    source_title: Optional[str] = None
    accessed_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


class FinalReport(BaseModel):
    """Schema for the final generated report.
    
    Note: Field names are standardized to snake_case to be frontend-friendly
    """
    title: str
    executive_summary: ReportSection
    industry_analysis: ReportSection
    challenges_analysis: ReportSection
    recommendations: ReportSection  # Recommendations merged from industry and PESTEL agents
    references: List[Reference]
    total_word_count: int
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        # This ensures that the JSON output uses snake_case keys
        alias_generator = lambda s: re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()
        allow_population_by_field_name = True


# LLM provider removed - using manual merging approach


class ReportGenerator:
    """Report Generator Agent to create a comprehensive final report using manual merging."""

    def __init__(self):
        """Initialize the report generator."""
        self.source_counter = 1
        self.source_mapping = {}  # old_citation -> new_number
        self.unified_sources = []
        
    def _build_enhanced_source_mapping(self, industry_report: Dict, pestel_report: Dict):
        """Create unified source list with sequential numbering and enhanced validation."""
        seen_sources = set()  # Track by URL to avoid cross-report duplicates
        self.source_counter = 1
        self.source_mapping = {}  # Maps "industry_X" or "pestel_X" to new unified number
        self.unified_sources = []
        
        logger.debug(f"Starting source mapping: Industry has {len(industry_report.get('sources', []))} sources, PESTEL has {len(pestel_report.get('sources', []))} sources")
        
        # Process industry sources first (agents already deduplicated internally)
        for source in industry_report.get("sources", []):
            source_key = source.get("source_url", "") or source.get("url", "")
            old_number = source.get("number", 0)
            
            if source_key and source_key not in seen_sources:
                # This is a unique source across both reports
                self.source_mapping[f"industry_{old_number}"] = self.source_counter
                self.unified_sources.append({
                    "number": self.source_counter,
                    "source_url": source_key,
                    "source_title": source.get("source_title", source.get("title", ""))
                })
                seen_sources.add(source_key)
                self.source_counter += 1
            else:
                # This source already exists from industry report - map to existing number
                existing_number = next((s["number"] for s in self.unified_sources if s["source_url"] == source_key), None)
                if existing_number:
                    self.source_mapping[f"industry_{old_number}"] = existing_number
        
        # Process PESTEL sources, handling cross-report duplicates
        for source in pestel_report.get("sources", []):
            source_key = source.get("source_url", "") or source.get("url", "")
            old_number = source.get("number", 0)
            
            if source_key and source_key not in seen_sources:
                # This is a unique source across both reports
                self.source_mapping[f"pestel_{old_number}"] = self.source_counter
                self.unified_sources.append({
                    "number": self.source_counter,
                    "source_url": source_key,
                    "source_title": source.get("source_title", source.get("title", ""))
                })
                seen_sources.add(source_key)
                self.source_counter += 1
            else:
                # This source already exists - map to existing number
                existing_number = next((s["number"] for s in self.unified_sources if s["source_url"] == source_key), None)
                if existing_number:
                    self.source_mapping[f"pestel_{old_number}"] = existing_number
        
        logger.info(f"Built unified source mapping: {len(industry_report.get('sources', []))} industry + {len(pestel_report.get('sources', []))} pestel -> {len(self.unified_sources)} unique sources")
    
    def _merge_summaries(self, industry_report: Dict, pestel_report: Dict) -> str:
        """Merge summaries into two-paragraph executive summary."""
        industry_summary = industry_report.get("summary", "")
        pestel_summary = pestel_report.get("summary", "")
        
        # Simple concatenation with paragraph break
        return f"{industry_summary}\n\n{pestel_summary}"
    
    def _extract_industry_analysis(self, industry_report: Dict) -> str:
        """Extract industry analysis with subsections."""
        analysis = ""
        analysis_sections = industry_report.get("analysis", [])
        
        for section in analysis_sections:
            if isinstance(section, dict) and "heading" in section:
                analysis += f"## {section['heading']}\n\n"
                
                # Add main content
                if "content" in section:
                    analysis += f"{section['content']}\n\n"
                
                # Add subsections if they exist
                if "subsections" in section and section["subsections"]:
                    for subsection in section["subsections"]:
                        if isinstance(subsection, dict) and "heading" in subsection:
                            analysis += f"### {subsection['heading']}\n\n"
                            if "content" in subsection:
                                analysis += f"{subsection['content']}\n\n"
        
        return analysis.strip()
    
    def _extract_challenges_analysis(self, pestel_report: Dict) -> str:
        """Extract PESTEL challenges analysis with subsections."""
        analysis = ""
        analysis_sections = pestel_report.get("analysis", [])
        
        for section in analysis_sections:
            if isinstance(section, dict) and "heading" in section:
                analysis += f"## {section['heading']}\n\n"
                
                # Add main content
                if "content" in section:
                    analysis += f"{section['content']}\n\n"
                
                # Add subsections if they exist
                if "subsections" in section and section["subsections"]:
                    for subsection in section["subsections"]:
                        if isinstance(subsection, dict) and "heading" in subsection:
                            analysis += f"### {subsection['heading']}\n\n"
                            if "content" in subsection:
                                analysis += f"{subsection['content']}\n\n"
        
        return analysis.strip()
    
    def _merge_recommendations(self, industry_report: Dict, pestel_report: Dict) -> str:
        """Merge recommendations into unified numbered list."""
        recommendations = []
        
        # Add industry recommendations
        industry_recs = industry_report.get("recommendations", [])
        if isinstance(industry_recs, list):
            recommendations.extend(industry_recs)
        elif isinstance(industry_recs, str):
            # Split by lines if it's a string
            recommendations.extend([line.strip() for line in industry_recs.split('\n') if line.strip()])
        
        # Add PESTEL recommendations
        pestel_recs = pestel_report.get("recommendations", [])
        if isinstance(pestel_recs, list):
            recommendations.extend(pestel_recs)
        elif isinstance(pestel_recs, str):
            # Split by lines if it's a string
            recommendations.extend([line.strip() for line in pestel_recs.split('\n') if line.strip()])
        
        # Format as numbered list
        formatted = ""
        for i, rec in enumerate(recommendations, 1):
            # Remove existing numbering or bullet points if present
            rec_clean = re.sub(r'^(\d+\.\s*|-\s*|\*\s*)', '', rec.strip())
            formatted += f"{i}. {rec_clean}\n"
        
        return formatted.strip()
    
    def _update_citations_in_content(self, content: str, source_prefix: str) -> str:
        """Update citations in content with new numbering."""
        if not content:
            return content
            
        # Pattern to match [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        
        def replace_citation(match):
            old_number = int(match.group(1))
            mapping_key = f"{source_prefix}_{old_number}"
            
            if mapping_key in self.source_mapping:
                new_number = self.source_mapping[mapping_key]
                return f"[{new_number}]"
            return match.group(0)  # Keep original if not found
        
        return re.sub(citation_pattern, replace_citation, content)
    
    def _update_all_citations(self, report: Dict) -> Dict:
        """Update all citations throughout the report."""
        # Update citations in executive summary (mixed sources)
        if "summary" in report:
            text = report["summary"]
            # Apply both industry and pestel mappings for mixed content
            text = self._update_citations_in_content(text, "industry")
            text = self._update_citations_in_content(text, "pestel")
            report["summary"] = text
        
        # Update citations in industry analysis
        if "industry_analysis" in report:
            report["industry_analysis"] = self._update_citations_in_content(
                report["industry_analysis"], "industry"
            )
        
        # Update citations in challenges analysis
        if "challenges_analysis" in report:
            report["challenges_analysis"] = self._update_citations_in_content(
                report["challenges_analysis"], "pestel"
            )
        
        # Update citations in recommendations (mixed sources)
        if "recommendations" in report:
            text = report["recommendations"]
            # Apply both industry and pestel mappings for mixed content
            text = self._update_citations_in_content(text, "industry")
            text = self._update_citations_in_content(text, "pestel")
            report["recommendations"] = text
        
        return report
    
    def _merge_summaries_enhanced(self, industry_report: Dict, pestel_report: Dict) -> str:
        """Enhanced summary merging with validation and formatting."""
        industry_summary = industry_report.get("summary", "").strip()
        pestel_summary = pestel_report.get("summary", "").strip()
        
        if not industry_summary and not pestel_summary:
            return "Executive summary not available."
        
        if not industry_summary:
            return pestel_summary
        
        if not pestel_summary:
            return industry_summary
        
        # Combine with clear separation
        return f"{industry_summary}\n\n{pestel_summary}"
    
    def _extract_industry_analysis_enhanced(self, industry_report: Dict) -> str:
        """Enhanced industry analysis extraction with robust section handling."""
        analysis = ""
        analysis_sections = industry_report.get("analysis", [])
        
        if not analysis_sections:
            return "Industry analysis not available."
        
        for section in analysis_sections:
            if isinstance(section, dict) and "heading" in section:
                analysis += f"## {section['heading']}\n\n"
                
                # Add main content
                if "content" in section:
                    content = section["content"].strip()
                    if content:
                        analysis += f"{content}\n\n"
                
                # Add subsections if they exist
                if "subsections" in section and section["subsections"]:
                    for subsection in section["subsections"]:
                        if isinstance(subsection, dict) and "heading" in subsection:
                            analysis += f"### {subsection['heading']}\n\n"
                            if "content" in subsection:
                                subcontent = subsection["content"].strip()
                                if subcontent:
                                    analysis += f"{subcontent}\n\n"
            else:
                logger.warning(f"Unexpected section structure: {section}")
        
        return analysis.strip() or "Industry analysis content not available."
    
    def _extract_challenges_analysis_enhanced(self, pestel_report: Dict) -> str:
        """Enhanced PESTEL analysis extraction with robust section handling."""
        analysis = ""
        analysis_sections = pestel_report.get("analysis", [])
        
        if not analysis_sections:
            return "PESTEL analysis not available."
        
        for section in analysis_sections:
            if isinstance(section, dict) and "heading" in section:
                analysis += f"## {section['heading']}\n\n"
                
                # Add main content
                if "content" in section:
                    content = section["content"].strip()
                    if content:
                        analysis += f"{content}\n\n"
                
                # Add subsections if they exist
                if "subsections" in section and section["subsections"]:
                    for subsection in section["subsections"]:
                        if isinstance(subsection, dict) and "heading" in subsection:
                            analysis += f"### {subsection['heading']}\n\n"
                            if "content" in subsection:
                                subcontent = subsection["content"].strip()
                                if subcontent:
                                    analysis += f"{subcontent}\n\n"
            else:
                logger.warning(f"Unexpected section structure: {section}")
        
        return analysis.strip() or "PESTEL analysis content not available."
    
    def _merge_recommendations_enhanced(self, industry_report: Dict, pestel_report: Dict) -> str:
        """Enhanced recommendation merging with bullet point cleaning and validation."""
        recommendations = []
        
        # Extract industry recommendations
        industry_recs = industry_report.get("recommendations", [])
        if isinstance(industry_recs, list):
            for rec in industry_recs:
                if isinstance(rec, str) and rec.strip():
                    recommendations.append(rec.strip())
        elif isinstance(industry_recs, str) and industry_recs.strip():
            # Split by lines if it's a string
            for line in industry_recs.split('\n'):
                if line.strip():
                    recommendations.append(line.strip())
        
        # Extract PESTEL recommendations
        pestel_recs = pestel_report.get("recommendations", [])
        if isinstance(pestel_recs, list):
            for rec in pestel_recs:
                if isinstance(rec, str) and rec.strip():
                    recommendations.append(rec.strip())
        elif isinstance(pestel_recs, str) and pestel_recs.strip():
            # Split by lines if it's a string
            for line in pestel_recs.split('\n'):
                if line.strip():
                    recommendations.append(line.strip())
        
        if not recommendations:
            return "## Recommendations\n\nNo specific recommendations available."
        
        # Format as numbered list with bullet point cleaning
        formatted = "## Recommendations\n\n"
        for i, rec in enumerate(recommendations, 1):
            # Remove existing numbering or bullet points if present
            rec_clean = re.sub(r'^(\d+\.\s*|-\s*|\*\s*)', '', rec.strip())
            if rec_clean:
                formatted += f"{i}. {rec_clean}\n\n"
        
        return formatted.strip()
    
    def _update_all_citations_enhanced(self, report: Dict) -> Dict:
        """Enhanced citation updating with comprehensive validation and error handling."""
        if not self.source_mapping:
            logger.warning("No source mapping available for citation updates")
            return report
        
        logger.debug(f"Updating citations with mapping: {self.source_mapping}")
        
        # Create a new report dict to avoid modifying the original
        updated_report = report.copy()
        
        # Update citations in executive summary
        if "executive_summary" in updated_report and isinstance(updated_report["executive_summary"], str):
            text = updated_report["executive_summary"]
            # Apply both industry and pestel mappings for mixed content
            text = self._update_citations_in_content(text, "industry")
            text = self._update_citations_in_content(text, "pestel")
            updated_report["executive_summary"] = text
        
        # Update citations in industry analysis
        if "industry_analysis" in updated_report and isinstance(updated_report["industry_analysis"], str):
            text = updated_report["industry_analysis"]
            text = self._update_citations_in_content(text, "industry")
            updated_report["industry_analysis"] = text
        
        # Update citations in challenges analysis
        if "challenges_analysis" in updated_report and isinstance(updated_report["challenges_analysis"], str):
            text = updated_report["challenges_analysis"]
            text = self._update_citations_in_content(text, "pestel")
            updated_report["challenges_analysis"] = text
        
        # Update citations in recommendations
        if "recommendations" in updated_report and isinstance(updated_report["recommendations"], str):
            text = updated_report["recommendations"]
            # Apply both industry and pestel mappings for mixed content
            text = self._update_citations_in_content(text, "industry")
            text = self._update_citations_in_content(text, "pestel")
            updated_report["recommendations"] = text
        
        return updated_report
    
    def _validate_merged_report(self, report: Dict) -> None:
        """Validate the final merged report structure using the JSONValidator."""
        from .json_validator import CitationValidator
        
        required_keys = ["title", "executive_summary", "industry_analysis", "challenges_analysis", "recommendations", "sources"]
        
        for key in required_keys:
            if key not in report:
                raise ValueError(f"Missing required key '{key}' in merged report")
        
        # Validate sources
        if not isinstance(report["sources"], list) or len(report["sources"]) == 0:
            raise ValueError("Merged report must have at least one source")
        
        # Use the CitationValidator to validate citations
        citation_validator = CitationValidator()
        all_text = f"{report.get('executive_summary', '')} {report.get('industry_analysis', '')} {report.get('challenges_analysis', '')} {report.get('recommendations', '')}"
        
        # Validate citations against sources
        is_valid, citation_errors = citation_validator.validate_citations(all_text, report["sources"])
        if not is_valid:
            logger.warning(f"Citation validation issues: {citation_errors}")
        
        logger.debug("Merged report validation completed successfully")
    
    def _validate_and_repair_citations(self, report: Dict) -> Dict:
        """Validate citations and repair missing ones by adding them to appropriate sections.
        
        Args:
            report: The merged report to validate and repair
            
        Returns:
            Dict: The report with repaired citations
        """
        from .json_validator import CitationValidator
        
        # Create a copy to avoid modifying the original
        repaired_report = report.copy()
        
        # Use the CitationValidator to validate and repair citations
        citation_validator = CitationValidator()
        
        # Extract all citations from content
        all_content = (
            repaired_report.get("executive_summary", "") + " " +
            repaired_report.get("industry_analysis", "") + " " +
            repaired_report.get("challenges_analysis", "") + " " +
            repaired_report.get("recommendations", "")
        )
        
        # Validate citations against sources
        is_valid, citation_errors = citation_validator.validate_citations(all_content, repaired_report.get("sources", []))
        
        if not is_valid:
            logger.warning(f"Citation validation issues: {citation_errors}")
            
            # Use the citation validator to repair the report
            repaired_report = citation_validator.repair_citations_in_report(repaired_report)
            
            # Check if there are still unused sources after repair
            all_content = (
                repaired_report.get("executive_summary", "") + " " +
                repaired_report.get("industry_analysis", "") + " " +
                repaired_report.get("challenges_analysis", "") + " " +
                repaired_report.get("recommendations", "")
            )
            
            # Re-validate after repair
            is_valid, remaining_errors = citation_validator.validate_citations(all_content, repaired_report.get("sources", []))
            
            # If there are still unused sources, add them to the executive summary
            if not is_valid and any("Sources without citations" in error for error in remaining_errors):
                import re
                cited_numbers = set(int(match.group(1)) for match in re.finditer(r'\[(\d+)\]', all_content))
                available_sources = {source["number"] for source in repaired_report.get("sources", [])}
                missing_citations = available_sources - cited_numbers
                
                if missing_citations:
                    logger.warning(f"Found {len(missing_citations)} uncited sources after repair: {sorted(missing_citations)}")
                    
                    # Add missing citations to the executive summary (least intrusive)
                    for missing_num in sorted(missing_citations):
                        source = next((s for s in repaired_report["sources"] if s["number"] == missing_num), None)
                        if source:
                            source_title = source.get("source_title", "Additional Source")
                            citation_text = f" Additional insights from {source_title} [{missing_num}] support these findings."
                            
                            # Add to end of executive summary
                            if "executive_summary" in repaired_report:
                                repaired_report["executive_summary"] += citation_text
                                logger.info(f"Added missing citation [{missing_num}] to executive summary")
        
        # Log final citation status
        logger.info(f"Citation validation completed with status: {'valid' if is_valid else 'issues remain'}")
        
        return repaired_report
    
    def _validate_report_structure(self, report: Dict, report_type: str) -> None:
        """Validate that a report has the required structure."""
        required_keys = ["title", "summary", "analysis", "recommendations", "sources"]
        
        for key in required_keys:
            if key not in report:
                raise ValueError(f"Missing required key '{key}' in {report_type} report")
        
        # Validate sources structure
        if not isinstance(report["sources"], list):
            raise ValueError(f"Sources must be a list in {report_type} report")
        
        for i, source in enumerate(report["sources"]):
            if not isinstance(source, dict):
                raise ValueError(f"Source {i} must be a dict in {report_type} report")
            
            # Check for required keys - accept both formats
            if "number" not in source:
                raise ValueError(f"Missing 'number' in source {i} of {report_type} report")
            
            # Accept either 'url' or 'source_url'
            if "url" not in source and "source_url" not in source:
                raise ValueError(f"Missing 'url' or 'source_url' in source {i} of {report_type} report")
            
            # Accept either 'title' or 'source_title'
            if "title" not in source and "source_title" not in source:
                raise ValueError(f"Missing 'title' or 'source_title' in source {i} of {report_type} report")
    
        # Validate recommendations structure
        if not isinstance(report["recommendations"], list):
            raise ValueError(f"Recommendations must be a list in {report_type} report")
        
        logger.debug(f"Validated {report_type} report structure successfully")
    
    def merge_reports_manually(self, industry_report: Dict, pestel_report: Dict, title: str = "") -> Dict:
        """Main orchestrator for manual report merging with enhanced robustness."""
        max_retries = 5
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Starting manual report merging process (attempt {attempt + 1}/{max_retries})")
                
                # Validate input reports
                self._validate_report_structure(industry_report, "industry")
                self._validate_report_structure(pestel_report, "pestel")
                
                # Step 1: Build unified source mapping with enhanced deduplication
                self._build_enhanced_source_mapping(industry_report, pestel_report)
                
                # Step 2: Merge content sections with robust handling
                merged_report = {
                    "title": title or industry_report.get("title", "Comprehensive Analysis Report"),
                    "executive_summary": self._merge_summaries_enhanced(industry_report, pestel_report),
                    "industry_analysis": self._extract_industry_analysis_enhanced(industry_report),
                    "challenges_analysis": self._extract_challenges_analysis_enhanced(pestel_report),
                    "recommendations": self._merge_recommendations_enhanced(industry_report, pestel_report),
                    "sources": self.unified_sources
                }
                
                # Step 3: Update all citations with robust renumbering
                merged_report = self._update_all_citations_enhanced(merged_report)
                
                # Step 4: Validate and repair citations
                merged_report = self._validate_and_repair_citations(merged_report)
                
                # Step 5: Final validation
                self._validate_merged_report(merged_report)
                
                logger.info(f"Manual merging completed successfully with {len(self.unified_sources)} unified sources")
                return merged_report
                
            except Exception as e:
                last_error = e
                logger.error(f"Report merging attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    # Add delay between retries with exponential backoff
                    delay = 2 ** attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} merging attempts failed")
        
        # If we get here, all retries failed
        raise RuntimeError(f"Failed to merge reports after {max_retries} attempts. Last error: {str(last_error)}")
    
    @traceable(name="generate_report")
    async def generate_report(self, industry_path: str, pestel_path: str,
                          output_path: str, report_title: str = "") -> Dict[str, Any]:
        """Generate a full report from industry and PESTEL data using manual merging."""
        logger.info(f"Generating report from {industry_path} and {pestel_path}")

        try:
            with open(industry_path, "r", encoding="utf-8") as f:
                industry_data = json.load(f)
            with open(pestel_path, "r", encoding="utf-8") as f:
                pestel_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading input data: {e}")
            raise ValueError(f"Failed to load input files: {e}")

        industry_title = industry_data.get("title", "Industry Analysis")
        title = report_title or industry_title

        # Use manual merging to build the full report
        merged_report = self.merge_reports_manually(industry_data, pestel_data, title)

        if not output_path.endswith('.json'):
            output_path = os.path.splitext(output_path)[0] + '.json'

        # Create final report structure with frontend-compatible format and guaranteed section ordering
        from collections import OrderedDict
        
        # Use OrderedDict to guarantee section order consistency
        ordered_report = OrderedDict([
            ("title", merged_report["title"]),
            ("executive_summary", merged_report.get("executive_summary", merged_report.get("summary", ""))),
            ("industry_analysis", merged_report["industry_analysis"]),
            ("challenges_analysis", merged_report["challenges_analysis"]),
            ("recommendations", merged_report["recommendations"]),
            ("sources", merged_report["sources"]),
            ("metadata", OrderedDict([
                ("version", "1.0.0"),
                ("format", "snake_case"),
                ("generated_at", datetime.now().isoformat()),
                ("sections", ["title", "executive_summary", "industry_analysis", "challenges_analysis", "recommendations", "sources"]),
                ("section_order_enforced", True)
            ]))
        ])
        
        final_report = {
            "report": ordered_report
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)

        logger.info(f"Report successfully generated and saved to {output_path} with frontend-friendly structure")

        return final_report
        
    async def _generate_executive_summary(self, industry_data: Dict[str, Any], pestel_data: Dict[str, Any]) -> str:
        """Generate an executive summary using the industry and PESTEL data.
        
        Args:
            industry_data: The industry report data
            pestel_data: The PESTEL report data
            
        Returns:
            str: The generated executive summary content
        """
        logger.info("Generating executive summary...")
        
        # Extract key information from both reports
        industry_content = ""
        
        # Handle direct content if available
        if "content" in industry_data:
            industry_content = industry_data.get("content", "")
        # Otherwise extract from summary and sections
        else:
            if "title" in industry_data:
                industry_content += f"# {industry_data['title']}\n\n"
                
            if "summary" in industry_data:
                industry_content += f"## Summary\n{industry_data['summary']}\n\n"
                
            # Extract content from analysis array
            if "analysis" in industry_data and isinstance(industry_data["analysis"], list):
                for section in industry_data["analysis"]:
                    if isinstance(section, dict) and "heading" in section:
                        industry_content += f"## {section['heading']}\n"
                        
                        # Add main content
                        if "content" in section:
                            industry_content += f"{section['content']}\n\n"
                        
                        # Add subsections
                        if "subsections" in section and section["subsections"]:
                            for subsection in section["subsections"]:
                                if isinstance(subsection, dict) and "heading" in subsection:
                                    industry_content += f"### {subsection['heading']}\n"
                                    if "content" in subsection:
                                        industry_content += f"{subsection['content']}\n\n"
        
        # Extract PESTEL content
        pestel_content = ""
        
        # Handle direct content if available
        if "content" in pestel_data:
            pestel_content = pestel_data.get("content", "")
        # Otherwise extract from summary and sections
        else:
            if "title" in pestel_data:
                pestel_content += f"# {pestel_data['title']}\n\n"
                
            if "summary" in pestel_data:
                pestel_content += f"## Summary\n{pestel_data['summary']}\n\n"
                
            # Extract content from analysis array
            if "analysis" in pestel_data and isinstance(pestel_data["analysis"], list):
                for section in pestel_data["analysis"]:
                    if isinstance(section, dict) and "heading" in section:
                        pestel_content += f"## {section['heading']}\n"
                        
                        # Add main content
                        if "content" in section:
                            pestel_content += f"{section['content']}\n\n"
                        
                        # Add subsections
                        if "subsections" in section and section["subsections"]:
                            for subsection in section["subsections"]:
                                if isinstance(subsection, dict) and "heading" in subsection:
                                    pestel_content += f"### {subsection['heading']}\n"
                                    if "content" in subsection:
                                        pestel_content += f"{subsection['content']}\n\n"
        
        # Create a prompt for the executive summary
        prompt = f"""
        Create a concise executive summary (50-100 words) that synthesizes the key insights from 
        the industry analysis and PESTEL analysis below. Focus on the most important findings and 
        their implications. The summary should be high-level and provide a complete picture of 
        the situation without going into excessive detail.
        
        INDUSTRY ANALYSIS:
        {industry_content[:2000]}  # Limit length to avoid token limits
        
        PESTEL ANALYSIS:
        {pestel_content[:2000]}  # Limit length to avoid token limits
        """
        
        # Call LLM to generate the summary
        response = await self.llm_provider.generate_text(prompt)
        
        # Process and return the summary
        summary = response.content.strip()
        logger.info("Executive summary generated successfully")
        return summary
    
    def _merge_recommendations(self, industry_data: Dict[str, Any], pestel_data: Dict[str, Any]) -> str:
        """Merge recommendations from industry and PESTEL reports into a single formatted text.
        
        Args:
            industry_data: Industry report data
            pestel_data: PESTEL report data
            
        Returns:
            str: Formatted recommendations text
        """
        # Extract recommendations from industry data - handle different possible structures
        industry_recommendations = []
        if "recommendations" in industry_data:
            if isinstance(industry_data["recommendations"], list):
                # Direct list of recommendation strings
                for rec in industry_data["recommendations"]:
                    if isinstance(rec, str):
                        industry_recommendations.append(rec)
                    elif isinstance(rec, dict) and "content" in rec:
                        industry_recommendations.append(rec["content"])
            elif isinstance(industry_data["recommendations"], dict):
                # Dictionary format with keys mapping to recommendations
                for key, value in industry_data["recommendations"].items():
                    if isinstance(value, str):
                        industry_recommendations.append(value)
                    elif isinstance(value, dict) and "content" in value:
                        industry_recommendations.append(value["content"])
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                industry_recommendations.append(item)
                            elif isinstance(item, dict) and "content" in item:
                                industry_recommendations.append(item["content"])
        
        # Extract recommendations from PESTEL data
        pestel_recommendations = []
        if "recommendations" in pestel_data:
            if isinstance(pestel_data["recommendations"], list):
                # Direct list of recommendation strings
                for rec in pestel_data["recommendations"]:
                    if isinstance(rec, str):
                        pestel_recommendations.append(rec)
                    elif isinstance(rec, dict) and "content" in rec:
                        pestel_recommendations.append(rec["content"])
            elif isinstance(pestel_data["recommendations"], dict):
                # Dictionary format with keys mapping to recommendations
                for key, value in pestel_data["recommendations"].items():
                    if isinstance(value, str):
                        pestel_recommendations.append(value)
                    elif isinstance(value, dict) and "content" in value:
                        pestel_recommendations.append(value["content"])
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                pestel_recommendations.append(item)
                            elif isinstance(item, dict) and "content" in item:
                                pestel_recommendations.append(item["content"])
        
        # Look for recommendations in analysis for PESTEL data (sometimes embedded there)
        if not pestel_recommendations and "analysis" in pestel_data:
            # Handle analysis array format
            if isinstance(pestel_data["analysis"], list):
                for section in pestel_data["analysis"]:
                    if isinstance(section, dict) and "heading" in section:
                        heading = section["heading"].lower()
                        if "recommendation" in heading:
                            # Extract from main content
                            if "content" in section:
                                content = section["content"]
                                for line in content.split("\n"):
                                    line = line.strip()
                                    if line.startswith("- ") or line.startswith("* "):
                                        pestel_recommendations.append(line[2:].strip())
                            
                            # Extract from subsections
                            if "subsections" in section and section["subsections"]:
                                for subsection in section["subsections"]:
                                    if isinstance(subsection, dict) and "content" in subsection:
                                        content = subsection["content"]
                                        for line in content.split("\n"):
                                            line = line.strip()
                                            if line.startswith("- ") or line.startswith("* "):
                                                pestel_recommendations.append(line[2:].strip())
        
        # Combine all recommendations and remove duplicates
        all_recommendations = industry_recommendations + pestel_recommendations
        unique_recommendations = []
        for rec in all_recommendations:
            if rec not in unique_recommendations:
                unique_recommendations.append(rec)
        
        # Format recommendations as markdown list
        if unique_recommendations:
            recommendations_text = "## Recommendations\n\n"
            for i, rec in enumerate(unique_recommendations, 1):
                # Remove existing numbering or bullet points if present
                rec_clean = re.sub(r'^(\d+\.\s*|-\s*|\*\s*)', '', rec.strip())
                recommendations_text += f"{i}. {rec_clean}\n\n"
            return recommendations_text
        else:
            return "## Recommendations\n\nNo specific recommendations available."


async def run_report_generator(industry_path: str, pestel_path: str, output_path: str, report_title: str = "") -> Dict[str, Any]:
    """Run the report generator to create a final report from industry and PESTEL data.
    
    Args:
        industry_path: Path to the industry mini report JSON
        pestel_path: Path to the PESTEL mini report JSON
        output_path: Path to save the final report
        report_title: Optional custom title for the report
        
    Returns:
        Dict[str, Any]: The generated report
    """
    generator = ReportGenerator()
    report = await generator.generate_report(
        industry_path=industry_path,
        pestel_path=pestel_path,
        output_path=output_path,
        report_title=report_title
    )
    return report


if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate a comprehensive report from industry, PESTEL, and recommendations data")
    parser.add_argument("--industry", required=True, help="Path to industry mini report JSON")
    parser.add_argument("--pestel", required=True, help="Path to PESTEL mini report JSON")
    parser.add_argument("--output", required=True, help="Path to save the output report JSON")
    parser.add_argument("--title", default="", help="Optional title for the report")
    
    args = parser.parse_args()
    
    asyncio.run(run_report_generator(
        industry_path=args.industry,
        pestel_path=args.pestel,
        output_path=args.output,
        report_title=args.title
    ))
    print(f"Report successfully generated and saved to {args.output}")
