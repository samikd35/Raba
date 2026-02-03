"""
User Management Module

This module provides user management functionality for the MINT system,
including user analytics, engagement, profile management, and workspace switching.

Components:
- analytics: User analytics service
- engagement: User engagement service
- profile: User profile service
- workspaces: User workspace switcher endpoints
"""

# Note: We don't import analytics, engagement, and profile here to avoid
# circular import issues. Import them directly where needed.

# Module metadata
__version__ = "1.0.0"
__author__ = "MINT Development Team"
__description__ = "User management module for MINT API"
