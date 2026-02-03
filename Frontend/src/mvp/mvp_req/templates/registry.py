"""
Template Registry for MVP Requirements Generator

Maps TemplateCode -> TemplateSpec with paths to prompts and schemas.
This registry is the authoritative definition of template configurations.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

from ..models.enums import TemplateCode


# Base path for templates
TEMPLATES_BASE_PATH = Path(__file__).parent


@dataclass
class TemplateSpec:
    """
    Specification for a PRD template.
    
    Contains all metadata and paths needed to generate a PRD for this template type.
    """
    code: TemplateCode
    name: str
    description: str
    category: str
    
    # Prompt template paths (relative to templates/prompts/)
    prd_prompt_path: str
    questions_prompt_path: str
    
    # Schema path (relative to templates/schemas/)
    schema_path: str
    
    # Version info
    template_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    
    # Template-specific configuration
    requires_research: bool = False  # Some templates benefit more from research
    typical_features_count: int = 5  # Expected must-have features
    key_sections: List[str] = None  # Template-specific sections
    
    def __post_init__(self):
        if self.key_sections is None:
            self.key_sections = []
    
    def get_prd_prompt_full_path(self) -> Path:
        """Get full path to PRD prompt template."""
        return TEMPLATES_BASE_PATH / "prompts" / self.prd_prompt_path
    
    def get_questions_prompt_full_path(self) -> Path:
        """Get full path to questions prompt template."""
        return TEMPLATES_BASE_PATH / "prompts" / self.questions_prompt_path
    
    def get_schema_full_path(self) -> Path:
        """Get full path to JSON schema."""
        return TEMPLATES_BASE_PATH / "schemas" / self.schema_path


# ==================== TEMPLATE REGISTRY ====================

TEMPLATE_REGISTRY: Dict[TemplateCode, TemplateSpec] = {
    
    # ========== A. Digital & Software Products ==========
    
    TemplateCode.A1: TemplateSpec(
        code=TemplateCode.A1,
        name="Software / SaaS Product",
        description="Web or mobile applications, CRM systems, management tools",
        category="Digital & Software Products",
        prd_prompt_path="prd_a1.j2",
        questions_prompt_path="questions_a1.j2",
        schema_path="a1_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=False,
        typical_features_count=6,
        key_sections=[
            "critical_user_flows",
            "data_requirements",
            "automation_level",
            "platform_choices"
        ]
    ),
    
    TemplateCode.A2: TemplateSpec(
        code=TemplateCode.A2,
        name="Digital Content / EdTech",
        description="Online courses, learning platforms, content delivery",
        category="Digital & Software Products",
        prd_prompt_path="prd_a2.j2",
        questions_prompt_path="questions_a2.j2",
        schema_path="a2_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=False,
        typical_features_count=5,
        key_sections=[
            "learning_journey",
            "content_format",
            "engagement_support",
            "assessment_proof"
        ]
    ),
    
    TemplateCode.A3: TemplateSpec(
        code=TemplateCode.A3,
        name="Platform / Marketplace",
        description="Two-sided or multi-sided platforms connecting buyers/sellers",
        category="Digital & Software Products",
        prd_prompt_path="prd_a3.j2",
        questions_prompt_path="questions_a3.j2",
        schema_path="a3_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=True,  # Marketplaces benefit from competitive research
        typical_features_count=7,
        key_sections=[
            "platform_sides",
            "matching_flow",
            "onboarding_structure",
            "trust_framework",
            "payments_transactions",
            "launch_strategy"
        ]
    ),
    
    TemplateCode.A4: TemplateSpec(
        code=TemplateCode.A4,
        name="Tech-Enabled Service",
        description="Software combined with operations (e.g., telemedicine, managed services)",
        category="Digital & Software Products",
        prd_prompt_path="prd_a4.j2",
        questions_prompt_path="questions_a4.j2",
        schema_path="a4_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=False,
        typical_features_count=6,
        key_sections=[
            "service_software_split",
            "end_to_end_journey",
            "operational_data_flows",
            "capacity_service_levels",
            "quality_management"
        ]
    ),
    
    TemplateCode.A5: TemplateSpec(
        code=TemplateCode.A5,
        name="Fintech / Financial Product",
        description="Lending, savings, insurance, payments, agent banking",
        category="Digital & Software Products",
        prd_prompt_path="prd_a5.j2",
        questions_prompt_path="questions_a5.j2",
        schema_path="a5_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=True,  # Regulatory research important
        typical_features_count=6,
        key_sections=[
            "financial_flow",
            "product_structure",
            "risk_compliance",
            "customer_protection",
            "tech_ops_split"
        ]
    ),
    
    # ========== B. Services (Offline) ==========
    
    TemplateCode.B1: TemplateSpec(
        code=TemplateCode.B1,
        name="Analog Services Business",
        description="Marketing agencies, accounting firms, logistics, cleaning services",
        category="Services (Offline)",
        prd_prompt_path="prd_b1.j2",
        questions_prompt_path="questions_b1.j2",
        schema_path="b1_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=False,
        typical_features_count=5,
        key_sections=[
            "service_target",
            "delivery_workflow",
            "job_intake_scheduling",
            "resources_capacity",
            "service_standards"
        ]
    ),
    
    # ========== C. Physical Products ==========
    
    TemplateCode.C1: TemplateSpec(
        code=TemplateCode.C1,
        name="Physical Consumer Product (CPG/FMCG)",
        description="Packaged foods, cosmetics, home care products",
        category="Physical Products",
        prd_prompt_path="prd_c1.j2",
        questions_prompt_path="questions_c1.j2",
        schema_path="c1_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=True,  # Market/regulatory research helpful
        typical_features_count=5,
        key_sections=[
            "consumer_use_case",
            "product_composition",
            "packaging_formats",
            "production_qc",
            "distribution_channels",
            "regulatory_safety"
        ]
    ),
    
    TemplateCode.C2: TemplateSpec(
        code=TemplateCode.C2,
        name="Hardware / IoT Product",
        description="Smart devices, sensors, GPS trackers, medical devices",
        category="Physical Products",
        prd_prompt_path="prd_c2.j2",
        questions_prompt_path="questions_c2.j2",
        schema_path="c2_schema.json",
        template_version="1.0.0",
        schema_version="1.0.0",
        requires_research=True,  # Technical/regulatory research important
        typical_features_count=6,
        key_sections=[
            "sensing_control_job",
            "device_software_interaction",
            "connectivity_power",
            "deployment_installation",
            "reliability_compliance"
        ]
    ),
}


# ==================== HELPER FUNCTIONS ====================

def get_template_spec(code: TemplateCode) -> Optional[TemplateSpec]:
    """
    Get TemplateSpec for a given template code.
    
    Args:
        code: TemplateCode enum value
        
    Returns:
        TemplateSpec if found, None otherwise
    """
    return TEMPLATE_REGISTRY.get(code)


def get_template_spec_by_string(code_str: str) -> Optional[TemplateSpec]:
    """
    Get TemplateSpec for a given template code string.
    
    Args:
        code_str: Template code string (e.g., "A1")
        
    Returns:
        TemplateSpec if found, None otherwise
    """
    try:
        code = TemplateCode(code_str)
        return get_template_spec(code)
    except ValueError:
        return None


def get_all_template_codes() -> List[TemplateCode]:
    """Get all available template codes."""
    return list(TEMPLATE_REGISTRY.keys())


def get_templates_by_category(category: str) -> List[TemplateSpec]:
    """
    Get all templates in a category.
    
    Args:
        category: Category name (e.g., "Digital & Software Products")
        
    Returns:
        List of TemplateSpec in that category
    """
    return [
        spec for spec in TEMPLATE_REGISTRY.values()
        if spec.category == category
    ]


def get_template_summary() -> Dict[str, List[Dict[str, str]]]:
    """
    Get summary of all templates organized by category.
    
    Useful for displaying template options to users.
    """
    summary = {}
    for spec in TEMPLATE_REGISTRY.values():
        if spec.category not in summary:
            summary[spec.category] = []
        summary[spec.category].append({
            "code": spec.code.value,
            "name": spec.name,
            "description": spec.description
        })
    return summary
