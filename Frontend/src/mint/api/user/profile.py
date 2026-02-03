"""
User Profile Service for managing user profiles in Supabase.

This module provides a service for managing user profiles, including
retrieving, updating, and validating profile data.
"""

import os
import logging
from typing import Dict, Optional, Any, List

from fastapi import HTTPException
from pydantic import BaseModel, Field, validator

from src.mint.api.supabase_client import SupabaseClient, get_service_role_client, get_standard_client

# Configure logging
logger = logging.getLogger(__name__)

class ProfileUpdateRequest(BaseModel):
    """Schema for profile update requests."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = None
    
    @validator('avatar_url')
    def validate_avatar_url(cls, v):
        """Validate avatar URL format."""
        if v is not None and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Avatar URL must be a valid HTTP or HTTPS URL')
        return v

class UserProfileService:
    """Service for managing user profiles."""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """Initialize the UserProfileService."""
        self.supabase_client = get_service_role_client()
        self.profiles_table = "user_profiles"
        
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user profile by user ID.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Optional[Dict]: The user profile data if found, None otherwise
        """
        try:
            response = self.supabase_client.client.table(self.profiles_table) \
                .select("*") \
                .eq("id", user_id) \
                .execute()
            
            profiles = response.data
            
            if not profiles:
                return None
                
            return profiles[0]
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve user profile: {str(e)}"
            )
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user profile.
        
        Args:
            user_id: The ID of the user
            profile_data: The profile data to update
            
        Returns:
            Dict: The updated user profile data
        """
        try:
            # Validate the profile data
            validated_data = ProfileUpdateRequest(**profile_data).dict(exclude_none=True)
            
            # Update the profile
            response = self.supabase_client.client.table(self.profiles_table) \
                .update(validated_data) \
                .eq("id", user_id) \
                .execute()
            
            if not response.data:
                # Profile doesn't exist, create it
                response = self.supabase_client.client.table(self.profiles_table) \
                    .insert({"id": user_id, **validated_data}) \
                    .execute()
                
                if not response.data:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create user profile"
                    )
            
            return response.data[0]
        except ValueError as e:
            # Validation error
            raise HTTPException(
                status_code=400,
                detail=f"Invalid profile data: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update user profile: {str(e)}"
            )
    
    async def create_user_profile(self, user_id: str, profile_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a user profile.
        
        Args:
            user_id: The ID of the user
            profile_data: Optional initial profile data
            
        Returns:
            Dict: The created user profile data
        """
        try:
            # Check if profile already exists
            existing_profile = await self.get_user_profile(user_id)
            if existing_profile:
                return existing_profile
            
            # Prepare profile data
            data_to_insert = {"id": user_id}
            if profile_data:
                # Validate the profile data
                validated_data = ProfileUpdateRequest(**profile_data).dict(exclude_none=True)
                data_to_insert.update(validated_data)
            
            # Create the profile
            response = self.supabase_client.client.table(self.profiles_table) \
                .insert(data_to_insert) \
                .execute()
            
            if not response.data:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create user profile"
                )
            
            return response.data[0]
        except ValueError as e:
            # Validation error
            raise HTTPException(
                status_code=400,
                detail=f"Invalid profile data: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create user profile: {str(e)}"
            )
    
    async def delete_user_profile(self, user_id: str) -> bool:
        """
        Delete a user profile.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            bool: True if the profile was deleted, False otherwise
        """
        try:
            response = self.supabase_client.client.table(self.profiles_table) \
                .delete() \
                .eq("id", user_id) \
                .execute()
            
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting user profile: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete user profile: {str(e)}"
            )