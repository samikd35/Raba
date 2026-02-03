"""
Auth Adapter for Data Analysis Agent

Provides authentication and authorization following VMP service patterns.
"""

from typing import Optional, Dict, Any
from src.vpm.adapters.auth_adapter import YubaAuthAdapter


class AnalysisAgentAuthAdapter(YubaAuthAdapter):
    """
    Auth adapter for Data Analysis Agent operations.
    
    Inherits from VMP's YubaAuthAdapter to maintain consistency
    with existing VMP service patterns.
    """
    
    def __init__(self):
        """Initialize using the same pattern as VMP services"""
        super().__init__()
    
    async def validate_analysis_access(
        self, 
        user_id: str, 
        tenant_id: str, 
        project_id: str
    ) -> bool:
        """
        Validate that user has access to perform analysis on the project.
        
        Args:
            user_id: The user ID
            tenant_id: The tenant ID
            project_id: The project ID
            
        Returns:
            True if user has access, False otherwise
        """
        # Use the existing project access validation from parent class
        return await self.validate_project_access(user_id, tenant_id, project_id)
    
    async def validate_file_upload_access(
        self, 
        user_id: str, 
        tenant_id: str, 
        project_id: str
    ) -> bool:
        """
        Validate that user can upload research documents to the project.
        
        Args:
            user_id: The user ID
            tenant_id: The tenant ID
            project_id: The project ID
            
        Returns:
            True if user can upload files, False otherwise
        """
        # For now, same as analysis access - can be extended with specific permissions
        return await self.validate_analysis_access(user_id, tenant_id, project_id)