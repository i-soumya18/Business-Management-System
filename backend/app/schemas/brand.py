"""
Brand Schemas

Pydantic schemas for Brand API requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator


class BrandBase(BaseModel):
    """Base brand schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Brand name")
    slug: str = Field(..., min_length=1, max_length=250, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Brand description")
    logo_url: Optional[str] = Field(None, max_length=500, description="Brand logo URL")
    website_url: Optional[str] = Field(None, max_length=500, description="Brand website")
    country_of_origin: Optional[str] = Field(None, max_length=100, description="Country of origin")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact phone")
    display_order: int = Field(default=0, description="Display order")
    is_active: bool = Field(default=True, description="Active status")


class BrandCreate(BrandBase):
    """Schema for creating a brand"""
    pass


class BrandUpdate(BaseModel):
    """Schema for updating a brand"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = Field(None)
    logo_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    country_of_origin: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = Field(None)
    contact_phone: Optional[str] = Field(None, max_length=20)
    display_order: Optional[int] = Field(None)
    is_active: Optional[bool] = Field(None)


class BrandResponse(BrandBase):
    """Schema for brand response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandListResponse(BaseModel):
    """Schema for brand list response"""
    items: List[BrandResponse]
    total: int
    page: int
    size: int