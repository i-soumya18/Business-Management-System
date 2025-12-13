"""
Brand and Supplier Schemas

Pydantic schemas for Brand and Supplier API requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator


# ============================================================================
# Brand Schemas
# ============================================================================

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

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()


class BrandCreate(BrandBase):
    """Schema for creating a new brand"""
    pass


class BrandUpdate(BaseModel):
    """Schema for updating a brand"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    country_of_origin: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class BrandResponse(BrandBase):
    """Schema for brand response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    product_count: Optional[int] = Field(None, description="Number of products")
    
    class Config:
        from_attributes = True


class BrandListResponse(BaseModel):
    """Paginated brand list response"""
    items: List[BrandResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Supplier Schemas
# ============================================================================

class SupplierBase(BaseModel):
    """Base supplier schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Supplier name")
    code: str = Field(..., min_length=1, max_length=50, description="Unique supplier code")
    contact_person: Optional[str] = Field(None, max_length=200, description="Contact person")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    mobile: Optional[str] = Field(None, max_length=20, description="Mobile number")
    website: Optional[str] = Field(None, max_length=500, description="Website URL")
    
    # Address fields
    address_line1: Optional[str] = Field(None, max_length=255, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: str = Field(default="India", max_length=100, description="Country")
    
    # Business information
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID (GST/VAT)")
    business_registration: Optional[str] = Field(None, max_length=100, description="Business registration number")
    
    # Payment terms
    payment_terms: Optional[str] = Field(None, max_length=100, description="Payment terms (e.g., Net 30)")
    credit_limit: Optional[float] = Field(None, ge=0, description="Credit limit amount")
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    
    # Performance metrics
    rating: Optional[float] = Field(None, ge=0, le=5, description="Supplier rating (0-5)")
    on_time_delivery_rate: Optional[float] = Field(None, ge=0, le=100, description="On-time delivery %")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time in days")
    
    notes: Optional[str] = Field(None, description="Additional notes")
    is_active: bool = Field(default=True, description="Active status")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate supplier code format"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Code must contain only alphanumeric characters, hyphens, and underscores')
        return v.upper()


class SupplierCreate(SupplierBase):
    """Schema for creating a new supplier"""
    pass


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    mobile: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=500)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    business_registration: Optional[str] = Field(None, max_length=100)
    payment_terms: Optional[str] = Field(None, max_length=100)
    credit_limit: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    rating: Optional[float] = Field(None, ge=0, le=5)
    on_time_delivery_rate: Optional[float] = Field(None, ge=0, le=100)
    lead_time_days: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    """Schema for supplier response"""
    id: UUID
    total_orders: int = Field(default=0, description="Total orders placed")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    """Paginated supplier list response"""
    items: List[SupplierResponse]
    total: int
    page: int
    page_size: int
    pages: int
