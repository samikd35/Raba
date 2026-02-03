"""
Enums and Constants for MVP Requirements Generator (AMRG)

Template codes are stable backend contracts used throughout:
- Run state
- Persistence tables
- Logs/metrics
- API responses
"""

from enum import Enum


class TemplateCode(str, Enum):
    """
    Product type template codes.
    
    A = Digital & Software Products
    B = Services (Offline)
    C = Physical Products
    """
    # Digital & Software Products
    A1 = "A1"  # Software / SaaS / App
    A2 = "A2"  # Digital Content / Course / EdTech
    A3 = "A3"  # Platform / Marketplace
    A4 = "A4"  # Tech-enabled Services
    A5 = "A5"  # Fintech / Financial Products
    
    # Services (Offline)
    B1 = "B1"  # Analog Services (Creatives and Operations)
    
    # Physical Products
    C1 = "C1"  # CPG / FMCG
    C2 = "C2"  # Hardware / IoT

    @classmethod
    def get_category(cls, code: "TemplateCode") -> str:
        """Get the category name for a template code."""
        categories = {
            cls.A1: "Digital & Software Products",
            cls.A2: "Digital & Software Products",
            cls.A3: "Digital & Software Products",
            cls.A4: "Digital & Software Products",
            cls.A5: "Digital & Software Products",
            cls.B1: "Services (Offline)",
            cls.C1: "Physical Products",
            cls.C2: "Physical Products",
        }
        return categories.get(code, "Unknown")
    
    @classmethod
    def get_display_name(cls, code: "TemplateCode") -> str:
        """Get human-readable display name for a template code."""
        names = {
            cls.A1: "Software / SaaS Product",
            cls.A2: "Digital Content / EdTech",
            cls.A3: "Platform / Marketplace",
            cls.A4: "Tech-Enabled Service",
            cls.A5: "Fintech / Financial Product",
            cls.B1: "Analog Services Business",
            cls.C1: "Physical Consumer Product (CPG/FMCG)",
            cls.C2: "Hardware / IoT Product",
        }
        return names.get(code, "Unknown")


class ResearchMode(str, Enum):
    """
    Web research mode for AMRG runs.
    
    Controls whether optional bounded web research is performed.
    """
    OFF = "off"    # Never use web research
    AUTO = "auto"  # Planner decides based on template + context gaps
    ON = "on"      # Always run bounded research


class RunStatus(str, Enum):
    """
    Status of an AMRG run.
    
    Tracks the lifecycle of a PRD generation run.
    """
    CREATED = "created"                    # Run created, eligibility being checked
    AWAITING_ANSWERS = "awaiting_answers"  # Waiting for clarifying question answers
    RUNNING = "running"                    # PRD generation in progress
    COMPLETED = "completed"                # Successfully completed
    FAILED = "failed"                      # Failed with error


class QuestionCategory(str, Enum):
    """
    Categories for clarifying questions.
    
    Used to organize and prioritize questions.
    """
    TEMPLATE_DISAMBIGUATION = "template_disambiguation"  # Disambiguate between top templates
    SCOPE_CLARIFICATION = "scope_clarification"          # Clarify MVP scope
    FEATURE_PRIORITY = "feature_priority"                # Feature prioritization
    USER_CONTEXT = "user_context"                        # Target user context
    TECHNICAL_CONSTRAINT = "technical_constraint"        # Technical constraints
    BUSINESS_MODEL = "business_model"                    # Business model specifics


class ValidationStatus(str, Enum):
    """
    Status of PRD JSON schema validation.
    """
    VALID = "valid"
    INVALID = "invalid"
    REPAIRED = "repaired"
    REPAIR_FAILED = "repair_failed"
