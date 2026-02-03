"""
Configuration and utilities for stress testing the Data Analysis Agent.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class StressTestConfig:
    """Configuration for stress testing parameters."""
    
    # Document size limits
    large_pdf_pages: int = 150
    large_csv_rows: int = 12000
    
    # Concurrency limits
    max_concurrent_users: int = 20
    analyses_per_user: int = 3
    
    # Performance thresholds
    max_pdf_processing_time: float = 30.0  # seconds
    max_csv_processing_time: float = 20.0  # seconds
    max_chunking_time: float = 60.0  # seconds
    
    # Memory limits (MB)
    max_memory_usage: float = 3000.0
    max_memory_growth_ratio: float = 2.0
    
    # Error rate thresholds
    max_error_rate: float = 0.1  # 10%
    max_concurrent_error_rate: float = 0.05  # 5%
    
    # Throughput targets
    target_requests_per_second: float = 5.0
    min_throughput_ratio: float = 0.8  # 80% of target
    
    # Test duration
    throughput_test_duration: int = 30  # seconds
    
    @classmethod
    def from_environment(cls) -> 'StressTestConfig':
        """Create configuration from environment variables."""
        return cls(
            large_pdf_pages=int(os.getenv('STRESS_TEST_PDF_PAGES', '150')),
            large_csv_rows=int(os.getenv('STRESS_TEST_CSV_ROWS', '12000')),
            max_concurrent_users=int(os.getenv('STRESS_TEST_MAX_USERS', '20')),
            analyses_per_user=int(os.getenv('STRESS_TEST_ANALYSES_PER_USER', '3')),
            max_pdf_processing_time=float(os.getenv('STRESS_TEST_MAX_PDF_TIME', '30.0')),
            max_csv_processing_time=float(os.getenv('STRESS_TEST_MAX_CSV_TIME', '20.0')),
            max_chunking_time=float(os.getenv('STRESS_TEST_MAX_CHUNKING_TIME', '60.0')),
            max_memory_usage=float(os.getenv('STRESS_TEST_MAX_MEMORY_MB', '3000.0')),
            max_memory_growth_ratio=float(os.getenv('STRESS_TEST_MAX_MEMORY_GROWTH', '2.0')),
            max_error_rate=float(os.getenv('STRESS_TEST_MAX_ERROR_RATE', '0.1')),
            max_concurrent_error_rate=float(os.getenv('STRESS_TEST_MAX_CONCURRENT_ERROR_RATE', '0.05')),
            target_requests_per_second=float(os.getenv('STRESS_TEST_TARGET_RPS', '5.0')),
            min_throughput_ratio=float(os.getenv('STRESS_TEST_MIN_THROUGHPUT_RATIO', '0.8')),
            throughput_test_duration=int(os.getenv('STRESS_TEST_THROUGHPUT_DURATION', '30'))
        )


class StressTestDataGenerator:
    """Generate test data for stress testing."""
    
    @staticmethod
    def generate_interview_content(pages: int) -> str:
        """Generate realistic interview transcript content."""
        base_content = """
        Interview Transcript - Market Research Study
        Date: {date}
        Participant ID: {participant_id}
        
        SECTION: PROBLEM IDENTIFICATION
        
        Interviewer: Can you describe the main challenges you face in your current workflow?
        
        Participant: The biggest challenge is the manual nature of our data processing. We spend approximately 4-5 hours daily on tasks that could be automated. This includes data entry, validation, and basic analysis. The current tools we use are outdated and don't integrate well with our existing systems.
        
        The pain points are particularly acute when dealing with large datasets. We often encounter errors due to manual processing, which leads to rework and delays. Our team of 12 people is constantly struggling with these inefficiencies.
        
        SECTION: CURRENT SOLUTIONS
        
        Interviewer: What solutions are you currently using to address these challenges?
        
        Participant: We're using a combination of Excel spreadsheets, some basic database queries, and a legacy system that was implemented about 5 years ago. The Excel approach works for small datasets but becomes unwieldy with larger volumes.
        
        We've also tried a few third-party tools, but they either lack the specific features we need or are too expensive for our budget. The learning curve for new tools is also a concern, as we can't afford significant downtime for training.
        
        SECTION: DESIRED OUTCOMES
        
        Interviewer: What would an ideal solution provide for your team?
        
        Participant: An ideal solution would automate at least 70% of our current manual processes. We need something that can handle large datasets efficiently, provide real-time insights, and integrate seamlessly with our CRM and ERP systems.
        
        Time savings is crucial - we're looking for at least 3 hours of saved time per person per day. Accuracy improvements are equally important, as manual errors cost us both time and credibility with clients.
        
        SECTION: DECISION FACTORS
        
        Interviewer: What factors would influence your decision to adopt a new solution?
        
        Participant: Cost is definitely a major factor. We have a limited budget of around $50,000 annually for new tools. Implementation time is also critical - we need something that can be deployed within 3 months.
        
        User adoption is another key consideration. The solution needs to be intuitive enough that our team can start using it with minimal training. Integration capabilities are non-negotiable, as we can't afford to maintain data silos.
        
        SECTION: FREQUENCY AND IMPACT
        
        Interviewer: How often do you encounter these problems, and what's the business impact?
        
        Participant: These issues occur daily. I'd estimate that inefficient data processing affects about 80% of our operations. The business impact is significant - we're probably losing around $200,000 annually due to these inefficiencies.
        
        Customer satisfaction is also affected because delays in data processing lead to slower response times. We've had several clients express concerns about our turnaround times.
        
        SECTION: JOBS TO BE DONE
        
        Interviewer: Can you walk me through your typical workflow and what jobs need to be accomplished?
        
        Participant: Our primary job is to process customer data and generate insights for decision-making. This involves collecting data from multiple sources, cleaning and validating it, performing analysis, and creating reports.
        
        We also need to maintain data quality standards, ensure compliance with regulations, and collaborate with other departments. The workflow typically takes 2-3 days for a complete cycle, but it should ideally be completed within a few hours.
        
        Additional context: Our industry is highly regulated, so compliance and audit trails are essential. We also need mobile access for field teams and real-time dashboards for management.
        """
        
        content_blocks = []
        for page in range(1, pages + 1):
            page_content = base_content.format(
                date=f"2024-{(page % 12) + 1:02d}-{(page % 28) + 1:02d}",
                participant_id=f"P{page:04d}"
            )
            content_blocks.append(f"PAGE {page}\n{page_content}\nEND OF PAGE {page}\n")
        
        return "\n".join(content_blocks)
    
    @staticmethod
    def generate_survey_data(rows: int) -> list:
        """Generate realistic survey data."""
        industries = ["Technology", "Finance", "Healthcare", "Manufacturing", "Retail", "Education"]
        roles = ["Manager", "Analyst", "Director", "Specialist", "Coordinator", "Executive"]
        pain_points = [
            "Manual data processing takes too much time",
            "Lack of integration between systems",
            "Difficulty in generating accurate reports",
            "Poor data quality and validation",
            "Limited automation capabilities",
            "Inadequate analytics and insights"
        ]
        solutions = ["Excel/Spreadsheets", "Custom Software", "Third-party Tools", "Manual Processes", "Legacy Systems"]
        
        data = []
        for i in range(1, rows + 1):
            row = {
                "response_id": f"R{i:06d}",
                "timestamp": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d} {(i % 24):02d}:{(i % 60):02d}:00",
                "age": 25 + (i % 40),
                "gender": ["Male", "Female", "Other"][i % 3],
                "role": roles[i % len(roles)],
                "industry": industries[i % len(industries)],
                "company_size": ["1-10", "11-50", "51-200", "201-1000", "1000+"][i % 5],
                "experience_years": (i % 20) + 1,
                
                # Pain points
                "primary_pain_point": pain_points[i % len(pain_points)],
                "pain_frequency": ["Daily", "Weekly", "Monthly", "Rarely"][i % 4],
                "pain_severity": (i % 5) + 1,  # 1-5 scale
                "time_lost_hours": (i % 8) + 1,  # 1-8 hours per day
                
                # Current solutions
                "current_solution": solutions[i % len(solutions)],
                "solution_satisfaction": (i % 5) + 1,  # 1-5 scale
                "solution_cost_monthly": (i % 20 + 1) * 100,
                
                # Desired outcomes
                "desired_time_savings": f"{(i % 6) + 2} hours per day",
                "budget_range": f"${(i % 10 + 1) * 5000}-{(i % 10 + 2) * 5000}",
                "implementation_timeline": ["Immediate", "1-3 months", "3-6 months", "6-12 months"][i % 4],
                "priority_features": "Automation, Integration, Analytics, Reporting",
                
                # Decision factors
                "decision_influence": ["Cost", "Features", "Ease of use", "Integration", "Support"][i % 5],
                "willingness_to_pay": (i % 10 + 1) * 50,
                "trial_interest": ["Very interested", "Somewhat interested", "Not interested"][i % 3],
                
                # Additional context
                "team_size": (i % 20) + 1,
                "data_volume": ["Small", "Medium", "Large", "Very Large"][i % 4],
                "compliance_requirements": ["Yes", "No"][i % 2],
                "mobile_access_needed": ["Yes", "No"][i % 2],
                "integration_systems": "CRM, ERP, Database, Analytics Tools",
                
                "comments": f"Additional feedback from respondent {i}. Looking for comprehensive solution that addresses our workflow challenges and provides measurable ROI."
            }
            data.append(row)
        
        return data


class StressTestReporter:
    """Generate reports for stress test results."""
    
    @staticmethod
    def generate_performance_report(metrics: Dict[str, Any], test_name: str) -> str:
        """Generate a formatted performance report."""
        report = f"""
# Stress Test Performance Report: {test_name}

## Test Summary
- **Test Duration**: {metrics.get('total_duration_seconds', 0):.2f} seconds
- **Total Operations**: {metrics.get('total_operations', 0)}
- **Peak Memory Usage**: {metrics.get('peak_memory_mb', 0):.2f} MB
- **Peak CPU Usage**: {metrics.get('peak_cpu_percent', 0):.2f}%
- **Max Concurrent Operations**: {metrics.get('max_concurrent_operations', 0)}

## Performance Metrics
- **Average Processing Time**: {metrics.get('average_processing_time', 0):.3f} seconds
- **Error Rate**: {metrics.get('error_rate', 0):.2%}
- **Error Count**: {metrics.get('error_count', 0)}

## Resource Utilization
- **Memory Efficiency**: {'PASS' if metrics.get('peak_memory_mb', 0) < 3000 else 'FAIL'}
- **CPU Efficiency**: {'PASS' if metrics.get('peak_cpu_percent', 0) < 90 else 'FAIL'}
- **Error Rate**: {'PASS' if metrics.get('error_rate', 0) < 0.1 else 'FAIL'}

## Errors (First 10)
"""
        
        errors = metrics.get('errors', [])
        if errors:
            for i, error in enumerate(errors[:10], 1):
                report += f"{i}. {error}\n"
        else:
            report += "No errors recorded.\n"
        
        return report
    
    @staticmethod
    def save_report(report: str, filename: str):
        """Save report to file."""
        os.makedirs("stress_test_reports", exist_ok=True)
        filepath = os.path.join("stress_test_reports", filename)
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        print(f"Stress test report saved to: {filepath}")