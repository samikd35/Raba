"""
VMP Services Integration Layer

This module provides integrated services that bridge VMP functionality
with Yuba's existing infrastructure without breaking VMP code.
"""

# Import integrated services
from .integrated_vmp_service import get_integrated_vmp_service
from .field_prep_service import YubaFieldPrepService, get_yuba_field_prep_service

__all__ = [
    "get_integrated_vmp_service",
    "YubaFieldPrepService", 
    "get_yuba_field_prep_service"
]
