"""
Parameter validation middleware for Problem Generator endpoints.

This module provides validation utilities that reuse existing patterns
from the MINT API for consistent parameter validation and error handling.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, validator

from ..models.problem_models import (
    ProblemCategory,
    SeverityLevel,
    ProblemType,
    TimeHorizon,
    ComplexityLevel
)

logger = logging.getLogger(__name__)

class PaginationParams(BaseModel):
    """Validation model for pagination parameters."""
    page: int = Field(1, ge=1, le=1000, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    
    @validator('page')
    def validate_page(cls, v):
        if v < 1:
            raise ValueError("Page number must be at least 1")
        if v > 1000:
            raise ValueError("Page number cannot exceed 1000")
        return v
    
    @validator('page_size')
    def validate_page_size(cls, v):
        if v < 1:
            raise ValueError("Page size must be at least 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v

class SearchFiltersParams(BaseModel):
    """Validation model for search filter parameters."""
    query: Optional[str] = Field(None, max_length=500, description="Search query")
    category: Optional[str] = Field(None, description="Problem category filter")
    severity: Optional[str] = Field(None, description="Severity level filter")
    problem_type: Optional[str] = Field(None, description="Problem type filter")
    time_horizon: Optional[str] = Field(None, description="Time horizon filter")
    complexity_level: Optional[str] = Field(None, description="Complexity level filter")
    industry: Optional[str] = Field(None, max_length=100, description="Industry filter")
    
    @validator('query')
    def validate_query(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 500:
                raise ValueError("Search query cannot exceed 500 characters")
        return v
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            try:
                ProblemCategory(v)
            except ValueError:
                valid_categories = [cat.value for cat in ProblemCategory]
                raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        return v
    
    @validator('severity')
    def validate_severity(cls, v):
        if v is not None:
            try:
                SeverityLevel(v)
            except ValueError:
                valid_severities = [sev.value for sev in SeverityLevel]
                raise ValueError(f"Invalid severity. Must be one of: {', '.join(valid_severities)}")
        return v
    
    @validator('problem_type')
    def validate_problem_type(cls, v):
        if v is not None:
            try:
                ProblemType(v)
            except ValueError:
                valid_types = [pt.value for pt in ProblemType]
                raise ValueError(f"Invalid problem type. Must be one of: {', '.join(valid_types)}")
        return v
    
    @validator('time_horizon')
    def validate_time_horizon(cls, v):
        if v is not None:
            try:
                TimeHorizon(v)
            except ValueError:
                valid_horizons = [th.value for th in TimeHorizon]
                raise ValueError(f"Invalid time horizon. Must be one of: {', '.join(valid_horizons)}")
        return v
    
    @validator('complexity_level')
    def validate_complexity_level(cls, v):
        if v is not None:
            try:
                ComplexityLevel(v)
            except ValueError:
                valid_levels = [cl.value for cl in ComplexityLevel]
                raise ValueError(f"Invalid complexity level. Must be one of: {', '.join(valid_levels)}")
        return v
    
    @validator('industry')
    def validate_industry(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) > 100:
                raise ValueError("Industry name cannot exceed 100 characters")
        return v

def validate_pagination_params(page: int = 1, page_size: int = 20) -> PaginationParams:
    """
    Validate pagination parameters using Pydantic model.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Validated pagination parameters
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        return PaginationParams(page=page, page_size=page_size)
    except ValueError as e:
        logger.warning(f"Pagination validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid pagination parameters: {str(e)}"
        )

def validate_search_filters(**kwargs) -> SearchFiltersParams:
    """
    Validate search filter parameters using Pydantic model.
    
    Args:
        **kwargs: Search filter parameters
        
    Returns:
        Validated search filters
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        return SearchFiltersParams(**kwargs)
    except ValueError as e:
        logger.warning(f"Search filter validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search parameters: {str(e)}"
        )

def validate_uuid_param(param_value: str, param_name: str = "ID") -> str:
    """
    Validate UUID parameter format.
    
    Args:
        param_value: UUID string to validate
        param_name: Name of the parameter for error messages
        
    Returns:
        Validated UUID string
        
    Raises:
        HTTPException: If UUID format is invalid
    """
    import uuid
    
    try:
        # This will raise ValueError if not a valid UUID
        uuid.UUID(param_value)
        return param_value
    except ValueError:
        logger.warning(f"Invalid UUID format for {param_name}: {param_value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {param_name} format. Must be a valid UUID."
        )

def validate_job_id(job_id: str) -> str:
    """
    Validate job ID parameter.
    
    Args:
        job_id: Job ID to validate
        
    Returns:
        Validated job ID
        
    Raises:
        HTTPException: If job ID format is invalid
    """
    return validate_uuid_param(job_id, "job ID")

def validate_problem_id(problem_id: str) -> str:
    """
    Validate problem ID parameter.
    
    Args:
        problem_id: Problem ID to validate
        
    Returns:
        Validated problem ID
        
    Raises:
        HTTPException: If problem ID format is invalid
    """
    return validate_uuid_param(problem_id, "problem ID")

def validate_user_id(user_id: str) -> str:
    """
    Validate user ID parameter.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        Validated user ID
        
    Raises:
        HTTPException: If user ID format is invalid
    """
    if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required and cannot be empty"
        )
    
    return validate_uuid_param(user_id.strip(), "user ID")

class RequestSizeValidator:
    """Validator for request size limits following existing patterns."""
    
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB limit
    MAX_GENERATION_PARAMS = 50  # Max number of generation parameters
    MAX_FOCUS_AREAS = 20  # Max number of focus areas
    MAX_STRING_LENGTH = 10000  # Max length for text fields
    
    @classmethod
    def validate_request_size(cls, request_data: Dict[str, Any]) -> None:
        """
        Validate overall request size.
        
        Args:
            request_data: Request data dictionary
            
        Raises:
            HTTPException: If request is too large
        """
        import json
        
        try:
            request_size = len(json.dumps(request_data).encode('utf-8'))
            if request_size > cls.MAX_REQUEST_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request size ({request_size} bytes) exceeds maximum allowed size ({cls.MAX_REQUEST_SIZE} bytes)"
                )
        except (TypeError, ValueError) as e:
            logger.error(f"Error calculating request size: {str(e)}")
            # Continue without size validation if serialization fails
    
    @classmethod
    def validate_generation_parameters(cls, parameters: Dict[str, Any]) -> None:
        """
        Validate generation parameters structure and limits.
        
        Args:
            parameters: Generation parameters dictionary
            
        Raises:
            HTTPException: If parameters are invalid
        """
        if len(parameters) > cls.MAX_GENERATION_PARAMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many generation parameters. Maximum allowed: {cls.MAX_GENERATION_PARAMS}"
            )
        
        # Validate focus areas if present
        focus_areas = parameters.get('focus_areas', [])
        if isinstance(focus_areas, list) and len(focus_areas) > cls.MAX_FOCUS_AREAS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many focus areas. Maximum allowed: {cls.MAX_FOCUS_AREAS}"
            )
        
        # Validate string field lengths
        for key, value in parameters.items():
            if isinstance(value, str) and len(value) > cls.MAX_STRING_LENGTH:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{key}' exceeds maximum length of {cls.MAX_STRING_LENGTH} characters"
                )

def validate_content_type(content_type: Optional[str]) -> None:
    """
    Validate request content type.
    
    Args:
        content_type: Content-Type header value
        
    Raises:
        HTTPException: If content type is not supported
    """
    if content_type and not content_type.startswith('application/json'):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type must be application/json"
        )

def create_validation_error_response(errors: List[Dict[str, Any]]) -> HTTPException:
    """
    Create standardized validation error response following existing patterns.
    
    Args:
        errors: List of validation errors
        
    Returns:
        HTTPException with formatted error details
    """
    error_details = []
    for error in errors:
        location = " -> ".join(str(loc) for loc in error.get('loc', []))
        message = error.get('msg', 'Validation error')
        error_details.append(f"{location}: {message}")
    
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": "Validation failed",
            "errors": error_details,
            "error_count": len(error_details)
        }
    )

# Rate limiting helpers (following existing patterns)
class RateLimitValidator:
    """Rate limiting validation following existing MINT patterns."""
    
    @staticmethod
    def check_user_rate_limit(user_id: str, endpoint: str) -> None:
        """
        Check if user has exceeded rate limits for the endpoint.
        
        Args:
            user_id: User identifier
            endpoint: Endpoint name
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # TODO: Implement actual rate limiting using Redis or similar
        # This is a placeholder following the existing pattern
        
        # For now, we'll implement basic validation
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID required for rate limiting"
            )
        
        logger.debug(f"Rate limit check for user {user_id} on endpoint {endpoint}")
        # In production, this would check Redis for rate limit counters
