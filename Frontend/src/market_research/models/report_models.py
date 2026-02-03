"""
Structured Report Models for JSON Output.

Defines the complete JSON schema for market research analysis reports.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ReportMetadata(BaseModel):
    """Report metadata and generation info."""
    generated_at: str = Field(..., description="ISO timestamp of report generation")
    project_id: str = Field(..., description="Unique project identifier")
    project_name: str = Field(default="Market Research Analysis", description="Project name")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    report_version: str = Field(default="1.0", description="Report schema version")
    report_type: Literal["standard", "enterprise_intelligence"] = Field(
        default="standard",
        description="Type of report generated"
    )


class ExecutiveSummaryStatistics(BaseModel):
    """Statistics for executive summary."""
    total_assumptions: int = Field(..., description="Total number of assumptions analyzed")
    validated: int = Field(..., description="Number of validated assumptions")
    partially_validated: int = Field(..., description="Number of partially validated assumptions")
    invalidated: int = Field(..., description="Number of invalidated assumptions")
    average_confidence: float = Field(..., description="Average confidence score across all assumptions")


class ExecutiveSummary(BaseModel):
    """Executive summary section."""
    content: str = Field(..., description="Executive summary text content")
    statistics: ExecutiveSummaryStatistics = Field(..., description="Summary statistics")
    key_insights: List[str] = Field(default_factory=list, description="Key insights extracted")


class CSVDataSource(BaseModel):
    """CSV data source information."""
    filename: str = Field(..., description="CSV filename")
    respondents: int = Field(..., description="Total number of respondents/records")
    fields: int = Field(..., description="Number of data fields analyzed")
    source_type: Literal["csv"] = Field(default="csv")
    generated_at: Optional[str] = Field(None, description="Analysis generation timestamp")
    highlights: Optional[str] = Field(None, description="Key highlights from CSV data")


class PDFDataSource(BaseModel):
    """PDF data source information."""
    filename: str = Field(..., description="PDF filename")
    pages: int = Field(default=3, description="Estimated number of pages")
    source_type: Literal["pdf"] = Field(default="pdf")
    chunks: int = Field(..., description="Number of content chunks")


class InterviewParticipant(BaseModel):
    """Interview participant information."""
    interview_id: str = Field(..., description="Interview identifier (e.g., I01)")
    name: Optional[str] = Field(None, description="Participant name")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Dynamic demographic fields")


class ResearchDataSummary(BaseModel):
    """Research data summary section."""
    csv_files: List[CSVDataSource] = Field(default_factory=list, description="CSV data sources")
    pdf_files: List[PDFDataSource] = Field(default_factory=list, description="PDF data sources")
    total_respondents: int = Field(..., description="Total research participants")
    total_data_fields: int = Field(..., description="Total data points analyzed")
    total_interview_files: int = Field(..., description="Total interview documents")
    total_files_processed: int = Field(..., description="Total files processed")
    interview_participants: List[InterviewParticipant] = Field(
        default_factory=list,
        description="Interview participant details"
    )
    data_type: Literal["mixed_method", "quantitative_only", "qualitative_only"] = Field(
        ...,
        description="Type of research data"
    )


class EvidenceItem(BaseModel):
    """Evidence item with citation."""
    text: str = Field(..., description="Evidence text")
    citations: List[str] = Field(default_factory=list, description="Source citations")
    confidence: Optional[float] = Field(None, description="Evidence confidence score")


class AnalysisDimension(BaseModel):
    """Individual analysis dimension (pain points, gains, JTBD)."""
    dimension_type: Literal["pain_points", "gains_benefits", "jobs_to_be_done"] = Field(
        ...,
        description="Type of analysis dimension"
    )
    title: str = Field(..., description="Analysis dimension title")
    accuracy_level: Literal["high", "medium", "low"] = Field(..., description="Accuracy level")
    primary_insight: str = Field(..., description="Main insight from this analysis")
    confidence_score: float = Field(..., description="Confidence score for this dimension")
    statistical_summary: Optional[str] = Field(None, description="Statistical data highlights")
    supporting_evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Supporting evidence items"
    )
    counter_evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Counter evidence items"
    )
    quantitative_findings: Optional[Dict[str, Any]] = Field(
        None,
        description="Quantitative analysis results"
    )
    data_limitations: Optional[str] = Field(None, description="Data gaps or limitations")


class AssumptionAnalysis(BaseModel):
    """Complete analysis for a single assumption."""
    assumption_id: str = Field(..., description="Unique assumption identifier")
    assumption_text: str = Field(..., description="The assumption being validated")
    persona_name: str = Field(..., description="Target persona for this assumption")
    persona_id: Optional[str] = Field(None, description="Persona identifier")
    component_type: Optional[Literal["pain", "gain", "jtbd"]] = Field(
        None,
        description="Type of assumption: pain (Pain Points), gain (Gains & Benefits), or jtbd (Jobs-to-be-Done)"
    )
    validation_status: Literal["validated", "partially_validated", "invalidated", "unknown"] = Field(
        ...,
        description="Overall validation status"
    )
    overall_confidence: float = Field(..., description="Overall confidence score (0-1)")
    confidence_label: Literal["High", "Medium", "Low"] = Field(..., description="Confidence label")
    analyses: List[AnalysisDimension] = Field(
        ..., 
        description="Analysis dimensions (single dimension based on component_type)"
    )
    key_findings: List[str] = Field(default_factory=list, description="Key findings summary")
    recommendation: Optional[str] = Field(None, description="Recommended action")


class StructuredReport(BaseModel):
    """Complete structured report in JSON format."""
    metadata: ReportMetadata = Field(..., description="Report metadata")
    executive_summary: ExecutiveSummary = Field(..., description="Executive summary")
    research_data_summary: ResearchDataSummary = Field(..., description="Research data overview")
    assumptions: List[AssumptionAnalysis] = Field(..., description="All assumption analyses")
    
    # Optional sections
    markdown_report: Optional[str] = Field(
        None,
        description="Full markdown report for backward compatibility"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "generated_at": "2025-10-28T09:13:07",
                    "project_id": "afaa0ec9-5af4-413d-8da7-9214f173a315",
                    "project_name": "Market Research Analysis",
                    "report_version": "1.0",
                    "report_type": "standard"
                },
                "executive_summary": {
                    "content": "This market validation study examined...",
                    "statistics": {
                        "total_assumptions": 3,
                        "validated": 2,
                        "partially_validated": 1,
                        "invalidated": 0,
                        "average_confidence": 0.51
                    }
                },
                "assumptions": []
            }
        }


class ReportExportFormat(BaseModel):
    """Report export format options."""
    format: Literal["json", "markdown", "html", "pdf"] = Field(..., description="Export format")
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    include_citations: bool = Field(default=True, description="Include citations")
    compact: bool = Field(default=False, description="Use compact JSON format")
