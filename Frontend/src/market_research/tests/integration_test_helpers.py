"""
Helper utilities for integration testing of the Data Analysis Agent.
"""

import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
import time
import logging

from fastapi import UploadFile
from io import BytesIO
import csv


class IntegrationTestEnvironment:
    """Manages integration test environment setup and teardown."""
    
    def __init__(self):
        self.temp_files = []
        self.mock_services = {}
        self.test_data = {}
        self.cleanup_tasks = []
    
    def add_temp_file(self, filepath: str):
        """Track temporary file for cleanup."""
        self.temp_files.append(filepath)
    
    def add_cleanup_task(self, task: Callable):
        """Add cleanup task to be executed during teardown."""
        self.cleanup_tasks.append(task)
    
    def cleanup(self):
        """Clean up test environment."""
        # Remove temporary files
        for filepath in self.temp_files:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                logging.warning(f"Failed to remove temp file {filepath}: {e}")
        
        # Execute cleanup tasks
        for task in self.cleanup_tasks:
            try:
                task()
            except Exception as e:
                logging.warning(f"Cleanup task failed: {e}")
        
        # Clear collections
        self.temp_files.clear()
        self.mock_services.clear()
        self.test_data.clear()
        self.cleanup_tasks.clear()


class MockServiceFactory:
    """Factory for creating consistent mock services across tests."""
    
    @staticmethod
    def create_database_adapter(project_data: Optional[Dict] = None) -> AsyncMock:
        """Create mock database adapter with consistent behavior."""
        adapter = AsyncMock()
        
        # Default project data if none provided
        if project_data is None:
            project_data = {
                "project_id": "test-project",
                "tenant_id": "test-tenant",
                "user_id": "test-user",
                "field_prep_data": {
                    "personas": [{"name": "Test Persona", "role": "Analyst"}],
                    "assumptions": [{"id": "test-assumption", "text": "Test assumption"}]
                },
                "analysis_status": "not_started",
                "analysis_data": {},
                "research_documents_data": {}
            }
        
        adapter.get_project_by_id.return_value = project_data
        adapter.update_project_analysis_data.return_value = True
        adapter.update_project_research_documents.return_value = True
        adapter.update_project_status.return_value = True
        
        return adapter
    
    @staticmethod
    def create_vector_adapter() -> AsyncMock:
        """Create mock vector adapter with consistent behavior."""
        adapter = AsyncMock()
        
        # Mock embedding generation
        adapter.generate_embeddings.return_value = [[0.1, 0.2, 0.3] for _ in range(10)]
        
        # Mock similarity search
        adapter.similarity_search.return_value = [
            {"content": "Relevant research content", "score": 0.9, "metadata": {}},
            {"content": "Additional relevant content", "score": 0.8, "metadata": {}}
        ]
        
        return adapter
    
    @staticmethod
    def create_auth_adapter(credits: int = 100) -> AsyncMock:
        """Create mock auth adapter with consistent behavior."""
        adapter = AsyncMock()
        
        adapter.validate_tenant_access.return_value = True
        adapter.validate_user_permissions.return_value = True
        adapter.get_user_credits.return_value = credits
        adapter.deduct_credits.return_value = True
        
        return adapter
    
    @staticmethod
    def create_ai_service() -> AsyncMock:
        """Create mock AI service with consistent behavior."""
        service = AsyncMock()
        
        # Default analysis response
        service.analyze_with_structured_output.return_value = {
            "claim": "Test analysis claim",
            "accuracy_level": "high",
            "supporting_evidence": ["Evidence 1", "Evidence 2"],
            "debunking_evidence": [],
            "statistical_data": {},
            "confidence_score": 0.85
        }
        
        return service


class TestDataGenerator:
    """Generate realistic test data for integration testing."""
    
    @staticmethod
    def create_comprehensive_project_data() -> Dict[str, Any]:
        """Create comprehensive project data for testing."""
        return {
            "project_id": "integration-test-project",
            "tenant_id": "integration-test-tenant",
            "user_id": "integration-test-user",
            "field_prep_data": {
                "personas": [
                    {
                        "name": "Data Analyst",
                        "role": "Senior Analyst",
                        "company_size": "Medium (50-200 employees)",
                        "industry": "Technology",
                        "pain_points": [
                            "Spends 4+ hours daily on manual data processing",
                            "Lacks automated validation tools",
                            "Struggles with data integration across systems"
                        ],
                        "goals": [
                            "Reduce manual processing time by 70%",
                            "Improve data accuracy and consistency",
                            "Enable real-time insights and reporting"
                        ],
                        "context": "Works in fast-paced tech environment with high data volumes"
                    },
                    {
                        "name": "Business Manager",
                        "role": "Operations Manager", 
                        "company_size": "Large (200+ employees)",
                        "industry": "Finance",
                        "pain_points": [
                            "Delayed decision-making due to slow data processing",
                            "High operational costs from manual processes",
                            "Compliance risks from manual errors"
                        ],
                        "goals": [
                            "Accelerate decision-making processes",
                            "Reduce operational costs by 30%",
                            "Ensure regulatory compliance"
                        ],
                        "context": "Manages team of 15 analysts in regulated environment"
                    }
                ],
                "customer_profiles": [
                    {
                        "segment": "Mid-Market Technology Companies",
                        "size": "50-200 employees",
                        "characteristics": [
                            "Data-driven decision making",
                            "Growth-focused",
                            "Technology-savvy",
                            "Budget-conscious"
                        ],
                        "needs": [
                            "Scalable automation solutions",
                            "Easy integration with existing tools",
                            "Cost-effective pricing",
                            "Quick implementation"
                        ],
                        "pain_points": [
                            "Manual processes limiting growth",
                            "Lack of real-time insights",
                            "Integration challenges"
                        ]
                    }
                ],
                "hypotheses": [
                    {
                        "id": "hyp-001",
                        "text": "Companies in our target market spend excessive time on manual data processing",
                        "category": "problem_validation",
                        "confidence": "medium"
                    },
                    {
                        "id": "hyp-002", 
                        "text": "Automation can reduce data processing time by 70% or more",
                        "category": "solution_validation",
                        "confidence": "high"
                    }
                ],
                "assumptions": [
                    {
                        "id": "assumption-001",
                        "text": "Data analysts in mid-market companies spend 4+ hours daily on manual data processing tasks",
                        "persona": "Data Analyst",
                        "category": "pain_point",
                        "confidence": "medium",
                        "hypothesis_id": "hyp-001"
                    },
                    {
                        "id": "assumption-002",
                        "text": "80% of target companies experience daily inefficiencies due to manual data processing",
                        "persona": "Data Analyst", 
                        "category": "market_size",
                        "confidence": "low",
                        "hypothesis_id": "hyp-001"
                    },
                    {
                        "id": "assumption-003",
                        "text": "Current solutions (Excel, basic tools) satisfy less than 40% of user needs",
                        "persona": "Data Analyst",
                        "category": "solution_gap",
                        "confidence": "medium",
                        "hypothesis_id": "hyp-002"
                    },
                    {
                        "id": "assumption-004",
                        "text": "Automated solutions can save 3+ hours per day per analyst",
                        "persona": "Data Analyst",
                        "category": "value_proposition",
                        "confidence": "high",
                        "hypothesis_id": "hyp-002"
                    },
                    {
                        "id": "assumption-005",
                        "text": "Decision-making delays cost companies $50K+ annually in missed opportunities",
                        "persona": "Business Manager",
                        "category": "business_impact",
                        "confidence": "low",
                        "hypothesis_id": "hyp-001"
                    }
                ]
            },
            "vpc_data": {
                "value_propositions": [
                    {
                        "id": "vp-001",
                        "text": "Automate data processing to save 3+ hours daily per analyst",
                        "target_persona": "Data Analyst",
                        "category": "time_savings"
                    },
                    {
                        "id": "vp-002",
                        "text": "Reduce operational costs by 30% through process automation",
                        "target_persona": "Business Manager", 
                        "category": "cost_reduction"
                    }
                ]
            },
            "analysis_status": "not_started",
            "analysis_data": {},
            "research_documents_data": {}
        }
    
    @staticmethod
    def create_realistic_interview_content() -> str:
        """Create realistic interview transcript content."""
        return """
        MARKET RESEARCH INTERVIEW TRANSCRIPT
        
        Date: 2024-01-15
        Participant: Senior Data Analyst, TechCorp Inc.
        Company Size: 150 employees
        Industry: Software Technology
        
        SECTION 1: CURRENT WORKFLOW AND PAIN POINTS
        
        Interviewer: Can you walk me through your typical data processing workflow?
        
        Participant: Sure. My day starts with collecting data from multiple sources - our CRM, marketing automation platform, customer support tickets, and various spreadsheets from different departments. This alone takes about an hour because the data formats are inconsistent.
        
        Then I spend roughly 3-4 hours cleaning and validating this data. We're talking about manually checking for duplicates, standardizing formats, and cross-referencing information across systems. It's incredibly tedious and error-prone.
        
        After that, I create reports and dashboards, which takes another 2-3 hours. By the time I'm done with the basic processing, there's little time left for actual analysis and insights.
        
        Interviewer: How frequently do you encounter errors in this process?
        
        Participant: Daily. I'd say about 20-30% of my time is spent fixing errors that could have been prevented with better automation. Manual data entry mistakes, formula errors in Excel, inconsistent data formats - it's a constant battle.
        
        The worst part is when these errors make it into executive reports. It damages credibility and creates additional work to correct and re-distribute information.
        
        SECTION 2: CURRENT SOLUTIONS AND LIMITATIONS
        
        Interviewer: What tools are you currently using to address these challenges?
        
        Participant: We primarily use Excel for data manipulation, Tableau for visualization, and some basic SQL queries for database access. We also have a few Python scripts that I've written, but they're not robust enough for production use.
        
        The problem is that none of these tools talk to each other effectively. I'm constantly exporting and importing data between systems. Excel works fine for small datasets, but we're dealing with hundreds of thousands of records now.
        
        We tried implementing a more sophisticated analytics platform last year, but it was too complex for our team and didn't integrate well with our existing systems. The learning curve was steep, and we couldn't justify the time investment.
        
        Interviewer: What's your satisfaction level with current solutions?
        
        Participant: On a scale of 1-10, I'd say about a 3. They get the job done, but barely. The inefficiency is frustrating, and I know we're capable of much more if we had the right tools.
        
        SECTION 3: DESIRED OUTCOMES AND REQUIREMENTS
        
        Interviewer: What would an ideal solution look like for your team?
        
        Participant: First and foremost, automation. I want to eliminate at least 70% of the manual data processing tasks. The system should be able to automatically pull data from our various sources, clean it, and prepare it for analysis.
        
        Integration is crucial. It needs to work seamlessly with our CRM, marketing tools, and database systems. No more manual exports and imports.
        
        Real-time or near-real-time processing would be game-changing. Instead of spending days preparing reports, I could focus on interpreting results and providing strategic insights.
        
        The interface needs to be intuitive. Our team doesn't have extensive technical backgrounds, so complexity is a barrier to adoption.
        
        Interviewer: What kind of time savings would justify an investment in new tools?
        
        Participant: If we could save even 2-3 hours per day per analyst, that would be transformational. With our team of 5 analysts, that's 10-15 hours daily that could be redirected to higher-value activities.
        
        Financially, I estimate we're losing about $150,000 annually in productivity due to these inefficiencies. A solution that addresses even half of that would pay for itself quickly.
        
        SECTION 4: DECISION FACTORS AND CONSTRAINTS
        
        Interviewer: What factors would influence your decision to adopt a new solution?
        
        Participant: Budget is always a consideration. We have about $75,000 allocated for new tools this year, but we'd need to see clear ROI projections.
        
        Implementation time is critical. We can't afford months of downtime or extensive training periods. Ideally, we'd want something that can be deployed within 6-8 weeks.
        
        Support and maintenance are important too. We don't have a large IT team, so the solution needs to be reliable and well-supported.
        
        Security and compliance are non-negotiable. We handle sensitive customer data, so any solution must meet our security standards and regulatory requirements.
        
        Interviewer: Who else would be involved in the decision-making process?
        
        Participant: My manager, the VP of Operations, would need to approve any significant investment. The IT director would evaluate technical requirements and security implications. And we'd probably want buy-in from the finance team for budget approval.
        
        The decision timeline is typically 3-6 months for tools in this price range, including evaluation, approval, and implementation phases.
        
        SECTION 5: BUSINESS IMPACT AND URGENCY
        
        Interviewer: How do these inefficiencies impact the broader business?
        
        Participant: The delays in data processing directly affect decision-making speed. Marketing campaigns get delayed because we can't quickly analyze performance data. Sales forecasting is less accurate because the data preparation takes too long.
        
        Customer satisfaction is also impacted. When support tickets take longer to analyze and resolve due to data processing delays, it affects our response times.
        
        From a competitive standpoint, we're slower to market with insights and responses compared to companies with more automated processes.
        
        Interviewer: How urgent is finding a solution?
        
        Participant: Very urgent. We're growing rapidly, and the current manual processes won't scale. We're already at a breaking point with current data volumes. If we don't address this soon, we'll need to hire additional analysts just to maintain current service levels.
        
        The executive team is aware of the issue and has made process automation a priority for this year.
        
        ADDITIONAL NOTES:
        - Team size: 5 data analysts, 1 manager
        - Data volume: ~500K records processed monthly
        - Current tools budget: $75K annually
        - Growth rate: 30% year-over-year
        - Regulatory requirements: SOC 2, GDPR compliance
        - Integration needs: Salesforce CRM, HubSpot, PostgreSQL database, Tableau
        - Mobile access: Preferred but not required
        - Reporting frequency: Daily operational reports, weekly executive summaries
        
        END OF TRANSCRIPT
        """
    
    @staticmethod
    def create_realistic_survey_data() -> List[Dict[str, Any]]:
        """Create realistic survey response data."""
        return [
            {
                "response_id": "SURV_001",
                "timestamp": "2024-01-10 09:15:00",
                "role": "Data Analyst",
                "company_size": "51-200 employees",
                "industry": "Technology",
                "experience_years": "5",
                "team_size": "4",
                
                # Pain points
                "primary_pain_point": "Manual data processing takes 4+ hours daily",
                "pain_frequency": "Daily",
                "pain_severity": "5",
                "time_lost_daily": "4",
                "error_frequency": "Daily",
                "error_impact": "High",
                
                # Current solutions
                "current_tools": "Excel, Basic SQL, Python scripts",
                "tool_satisfaction": "2",
                "integration_quality": "Poor",
                "automation_level": "10%",
                
                # Desired outcomes
                "desired_time_savings": "3+ hours daily",
                "automation_target": "70%",
                "priority_features": "Data integration, Automated validation, Real-time processing",
                "success_metrics": "Time savings, Error reduction, Faster insights",
                
                # Decision factors
                "budget_range": "$50,000-$100,000",
                "implementation_timeline": "3-6 months",
                "decision_factors": "ROI, Ease of use, Integration capabilities",
                "approval_process": "Manager and VP approval required",
                
                # Business impact
                "productivity_impact": "High",
                "revenue_impact": "Medium",
                "competitive_impact": "High",
                "urgency_level": "Critical",
                
                "additional_comments": "Current manual processes are not scalable. Need solution that grows with our data volume."
            },
            {
                "response_id": "SURV_002", 
                "timestamp": "2024-01-10 14:30:00",
                "role": "Business Analyst",
                "company_size": "201-500 employees",
                "industry": "Finance",
                "experience_years": "7",
                "team_size": "8",
                
                # Pain points
                "primary_pain_point": "Delayed decision-making due to slow data processing",
                "pain_frequency": "Daily",
                "pain_severity": "4",
                "time_lost_daily": "3",
                "error_frequency": "Weekly",
                "error_impact": "Medium",
                
                # Current solutions
                "current_tools": "Excel, Tableau, Custom database queries",
                "tool_satisfaction": "3",
                "integration_quality": "Fair",
                "automation_level": "25%",
                
                # Desired outcomes
                "desired_time_savings": "2-3 hours daily",
                "automation_target": "60%",
                "priority_features": "Automated reporting, Data validation, Executive dashboards",
                "success_metrics": "Faster reporting, Improved accuracy, Cost reduction",
                
                # Decision factors
                "budget_range": "$100,000-$200,000",
                "implementation_timeline": "6-12 months",
                "decision_factors": "Security, Compliance, Scalability",
                "approval_process": "IT, Finance, and Executive approval",
                
                # Business impact
                "productivity_impact": "High",
                "revenue_impact": "High",
                "competitive_impact": "Medium",
                "urgency_level": "Important",
                
                "additional_comments": "Regulatory compliance is critical. Solution must meet SOX and other financial regulations."
            },
            {
                "response_id": "SURV_003",
                "timestamp": "2024-01-11 11:45:00", 
                "role": "Operations Manager",
                "company_size": "11-50 employees",
                "industry": "Healthcare",
                "experience_years": "10",
                "team_size": "3",
                
                # Pain points
                "primary_pain_point": "High error rates in manual data processing",
                "pain_frequency": "Daily",
                "pain_severity": "5",
                "time_lost_daily": "5",
                "error_frequency": "Daily",
                "error_impact": "Critical",
                
                # Current solutions
                "current_tools": "Excel, Manual processes, Legacy database",
                "tool_satisfaction": "1",
                "integration_quality": "Poor",
                "automation_level": "5%",
                
                # Desired outcomes
                "desired_time_savings": "4+ hours daily",
                "automation_target": "80%",
                "priority_features": "Error prevention, Compliance reporting, Audit trails",
                "success_metrics": "Zero errors, Compliance adherence, Time savings",
                
                # Decision factors
                "budget_range": "$25,000-$50,000",
                "implementation_timeline": "1-3 months",
                "decision_factors": "Compliance, Reliability, Cost",
                "approval_process": "Owner approval only",
                
                # Business impact
                "productivity_impact": "Critical",
                "revenue_impact": "High",
                "competitive_impact": "High",
                "urgency_level": "Critical",
                
                "additional_comments": "Patient data accuracy is life-critical. Cannot afford any errors in processing."
            }
        ]


class IntegrationTestValidator:
    """Validates integration test results and system behavior."""
    
    @staticmethod
    def validate_analysis_workflow_result(result: Dict[str, Any]) -> bool:
        """Validate that analysis workflow result has expected structure."""
        required_fields = [
            "session_id",
            "status", 
            "assumption_analyses",
            "final_report"
        ]
        
        for field in required_fields:
            if field not in result:
                return False
        
        # Validate assumption analyses structure
        if not isinstance(result["assumption_analyses"], list):
            return False
        
        for analysis in result["assumption_analyses"]:
            required_analysis_fields = [
                "assumption_id",
                "assumption_text",
                "validation_status",
                "analyses"
            ]
            
            for field in required_analysis_fields:
                if field not in analysis:
                    return False
        
        return True
    
    @staticmethod
    def validate_document_processing_result(result: Dict[str, Any]) -> bool:
        """Validate document processing result structure."""
        required_fields = ["content", "metadata", "chunks"]
        
        for field in required_fields:
            if field not in result:
                return False
        
        # Validate chunks structure
        if not isinstance(result["chunks"], list):
            return False
        
        for chunk in result["chunks"]:
            if "content" not in chunk or "embedding" not in chunk:
                return False
        
        return True
    
    @staticmethod
    def validate_vmp_integration(project_data: Dict[str, Any]) -> bool:
        """Validate VMP integration data structure."""
        required_sections = [
            "field_prep_data",
            "analysis_data", 
            "research_documents_data"
        ]
        
        for section in required_sections:
            if section not in project_data:
                return False
        
        # Validate field_prep_data structure
        field_prep = project_data["field_prep_data"]
        required_field_prep = ["personas", "assumptions"]
        
        for field in required_field_prep:
            if field not in field_prep:
                return False
        
        return True


@asynccontextmanager
async def integration_test_context():
    """Context manager for integration test setup and cleanup."""
    env = IntegrationTestEnvironment()
    
    try:
        yield env
    finally:
        env.cleanup()


def create_test_upload_file(content: str, filename: str) -> UploadFile:
    """Create UploadFile for testing."""
    file_obj = BytesIO(content.encode('utf-8'))
    return UploadFile(filename=filename, file=file_obj)


def create_test_csv_file(data: List[Dict], filename: str) -> UploadFile:
    """Create CSV UploadFile for testing."""
    output = BytesIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    output.seek(0)
    return UploadFile(filename=filename, file=output)