"""
Demo Request Models

Pydantic models for enterprise demo request functionality.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class OrganizationLocation(BaseModel):
    """Organization location details."""
    country: str = Field(..., min_length=1, max_length=100, description="Country name")
    city: str = Field(..., min_length=1, max_length=100, description="City name")


class OrganizationDetails(BaseModel):
    """Organization details for demo request."""
    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    type: str = Field(..., min_length=1, max_length=100, description="Organization type (e.g., ESO, NGO, Corporation)")
    size: str = Field(..., min_length=1, max_length=50, description="Organization size (e.g., 1-10, 11-50, 51-200)")
    location: OrganizationLocation


class DemoRequestMetadata(BaseModel):
    """Metadata for demo request."""
    requested_tier: str = Field(default="organization", description="Requested pricing tier")
    source: str = Field(default="pricing_page", description="Source of the request")
    submitted_at: Optional[str] = Field(default=None, description="Submission timestamp (auto-generated if not provided)")


class DemoRequestData(BaseModel):
    """Complete demo request data structure."""
    full_name: str = Field(..., min_length=1, max_length=200, description="Full name of the requester")
    email: EmailStr = Field(..., description="Email address of the requester")
    phone_number: str = Field(..., min_length=1, max_length=50, description="Phone number of the requester")
    job_title: str = Field(..., min_length=1, max_length=100, description="Job title of the requester")
    organization: OrganizationDetails
    expected_users: str = Field(..., min_length=1, max_length=50, description="Expected number of users")
    additional_notes: Optional[str] = Field(default="", max_length=2000, description="Additional notes or requirements")
    metadata: Optional[DemoRequestMetadata] = Field(default_factory=DemoRequestMetadata)


class DemoRequest(BaseModel):
    """Root demo request model with nested demo_request field."""
    demo_request: DemoRequestData


class DemoRequestResponse(BaseModel):
    """Response model for demo request submission."""
    success: bool
    message: str
    request_id: Optional[str] = None
    submitted_at: str
