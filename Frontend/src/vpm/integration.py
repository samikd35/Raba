"""
VPM Integration with Yuba Main Application

This module provides the integration point to add VPM functionality
to the existing Yuba application without breaking any existing code.
"""

import sys
import os
from dotenv import load_dotenv

# Add VPM directory to Python path before any VPM imports
vpm_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'VPM')
vpm_path = os.path.abspath(vpm_path)
if vpm_path not in sys.path:
    sys.path.insert(0, vpm_path)

# Load Yuba's environment variables first (for VPM services to use)
yuba_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
yuba_env_path = os.path.abspath(yuba_env_path)
if os.path.exists(yuba_env_path):
    load_dotenv(yuba_env_path, override=False)  # Load Yuba's env vars
    print(f"✅ Loaded Yuba environment for VPM services from {yuba_env_path}")

# Load VPM-specific environment variables (if any)
vpm_env_path = os.path.join(vpm_path, '.env')
if os.path.exists(vpm_env_path):
    load_dotenv(vpm_env_path, override=False)  # Don't override existing Yuba env vars
    print(f"✅ Loaded VPM-specific environment from {vpm_env_path}")

from fastapi import FastAPI
from .api.endpoints import router as vpm_router


def integrate_vpm_with_yuba(app: FastAPI) -> None:
    """
    Integrate VPM module with the main Yuba FastAPI application.
    
    This function should be called from the main Yuba application
    to add VPM functionality seamlessly.
    
    Args:
        app: The main Yuba FastAPI application instance
    """
    
    # Add VPM router to the main application
    app.include_router(
        vpm_router,
        # No additional dependencies needed - VPM endpoints handle auth internally
    )
    
    print("✅ VPM (Value Proposition Module) successfully integrated with Yuba!")
    print("📍 VPM endpoints available at: /api/v2/vpm/*")
    print("🔗 Integration features:")
    print("   - Uses existing Yuba authentication system")
    print("   - Integrates with existing credit system") 
    print("   - Leverages existing vector storage")
    print("   - Implements dual vector store strategy")
    print("   - Maintains tenant isolation")


def get_vpm_info() -> dict:
    """
    Get information about the VPM integration.
    
    Returns:
        Dictionary with VPM integration details
    """
    return {
        "module_name": "Value Proposition Module (VPM)",
        "module_number": 2,
        "version": "2.0.0",
        "status": "integrated",
        "endpoints_prefix": "/api/v2/vpm",
        "features": [
            "PV Report Discovery",
            "VPM Project Creation", 
            "Dual Vector Store Integration",
            "VPC Generation",
            "Context Search",
            "Credit System Integration"
        ],
        "integration_points": [
            "Yuba Authentication System",
            "Yuba Credit System",
            "Yuba Vector Storage",
            "Yuba Database (Supabase)",
            "Yuba Tenant Management"
        ],
        "original_vpm_preserved": True,
        "breaking_changes": False
    }
