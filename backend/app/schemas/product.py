"""
Product and ProductVariant Schemas

Pydantic schemas for Product and ProductVariant API requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Product Schemas
# ============================================================================

class ProductBase(BaseModel):
    """Base product schema"""
    name: str = Field(..., min_length=1, max_length=300, description="Product name")
    slug: str = Field(..., min_length=1, max_length=350, description="URL-friendly slug")
    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    description: Optional[str] = Field(None, description="Product description")
    short_description: Optional[str] = Field(None, max_length=500, description="Short description")
    
    # Relationships
    category_id: Optional[UUID] = Field(None, description="Category ID")
    brand_id: Optional[UUID] = Field(None, description="Brand ID")
    supplier_id: Optional[UUID] = Field(None, description="Supplier ID")
    
    # Garment-specific
    garment_type: Optional[str] = Field(None, max_length=100, description="Garment type (Shirt, Pants, etc.)")
    fabric_type: Optional[str] = Field(None, max_length=200, description="Fabric type (Cotton, Polyester, etc.)")
    fabric_composition: Optional[str] = Field(None, max_length=500, description="Fabric composition")
    care_instructions: Optional[str] = Field(None, description="Care instructions")
    season: Optional[str] = Field(None, max_length=50, description="Season (Spring, Summer, Fall, Winter)")
    collection: Optional[str] = Field(None, max_length=200, description="Collection name")
    
    # Pricing
    base_cost_price: Optional[float] = Field(None, ge=0, description="Base cost price")
    base_retail_price: Optional[float] = Field(None, ge=0, description="Base retail price")
    base_wholesale_price: Optional[float] = Field(None, ge=0, description="Base wholesale price")
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    
    # Tax
    tax_rate: Optional[float] = Field(None, ge=0, le=100, description="Tax rate percentage")
    tax_category: Optional[str] = Field(None, max_length=100, description="Tax category")
    
    # Inventory settings
    track_inventory: bool = Field(default=True, description="Track inventory for this product")
    allow_backorder: bool = Field(default=False, description="Allow backorders")
    
    # Images
    primary_image_url: Optional[str] = Field(None, max_length=500, description="Primary image URL")
    image_urls: Optional[Dict[str, Any]] = Field(None, description="Additional images")
    
    # SEO
    meta_title: Optional[str] = Field(None, max_length=200, description="SEO meta title")
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    meta_keywords: Optional[str] = Field(None, max_length=500, description="SEO keywords")
    
    # Measurements
    measurement_unit: Optional[str] = Field(None, max_length=50, description="Measurement unit (cm, inches)")
    measurements: Optional[Dict[str, Any]] = Field(None, description="Product measurements")
    
    # Additional
    attributes: Optional[Dict[str, Any]] = Field(None, description="Custom attributes")
    tags: Optional[Dict[str, Any]] = Field(None, description="Product tags")
    
    # Status
    is_active: bool = Field(default=True, description="Active status")
    is_featured: bool = Field(default=False, description="Featured product")
    is_new_arrival: bool = Field(default=False, description="New arrival")
    is_on_sale: bool = Field(default=False, description="On sale")
    display_order: int = Field(default=0, description="Display order")

    @field_validator('slug', 'sku')
    @classmethod
    def validate_codes(cls, v: str, info) -> str:
        """Validate slug and SKU format"""
        if info.field_name == 'slug':
            if not v.replace('-', '').replace('_', '').isalnum():
                raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
            return v.lower()
        return v.upper()


class ProductCreate(ProductBase):
    """Schema for creating a new product"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    slug: Optional[str] = Field(None, min_length=1, max_length=350)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None
    brand_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    garment_type: Optional[str] = Field(None, max_length=100)
    fabric_type: Optional[str] = Field(None, max_length=200)
    fabric_composition: Optional[str] = Field(None, max_length=500)
    care_instructions: Optional[str] = None
    season: Optional[str] = Field(None, max_length=50)
    collection: Optional[str] = Field(None, max_length=200)
    base_cost_price: Optional[float] = Field(None, ge=0)
    base_retail_price: Optional[float] = Field(None, ge=0)
    base_wholesale_price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    tax_rate: Optional[float] = Field(None, ge=0, le=100)
    tax_category: Optional[str] = Field(None, max_length=100)
    track_inventory: Optional[bool] = None
    allow_backorder: Optional[bool] = None
    primary_image_url: Optional[str] = Field(None, max_length=500)
    image_urls: Optional[Dict[str, Any]] = None
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = Field(None, max_length=500)
    measurement_unit: Optional[str] = Field(None, max_length=50)
    measurements: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_new_arrival: Optional[bool] = None
    is_on_sale: Optional[bool] = None
    display_order: Optional[int] = None


class ProductResponse(ProductBase):
    """Schema for product response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductWithVariants(ProductResponse):
    """Product with its variants"""
    variants: List['ProductVariantResponse'] = Field(default_factory=list)
    total_stock: Optional[int] = Field(None, description="Total stock across all variants")
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Paginated product list response"""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# ProductVariant Schemas
# ============================================================================

class ProductVariantBase(BaseModel):
    """Base product variant schema"""
    product_id: UUID = Field(..., description="Parent product ID")
    sku: str = Field(..., min_length=1, max_length=100, description="Variant SKU")
    barcode: Optional[str] = Field(None, max_length=100, description="Barcode")
    
    # Variant attributes
    size: Optional[str] = Field(None, max_length=50, description="Size (XS, S, M, L, XL, etc.)")
    color: Optional[str] = Field(None, max_length=100, description="Color")
    color_code: Optional[str] = Field(None, max_length=20, description="Color hex code")
    style: Optional[str] = Field(None, max_length=100, description="Style (Slim Fit, Regular, etc.)")
    variant_attributes: Optional[Dict[str, Any]] = Field(None, description="Custom variant attributes")
    
    # Pricing
    cost_price: Optional[float] = Field(None, ge=0, description="Cost price")
    retail_price: float = Field(..., ge=0, description="Retail price")
    wholesale_price: Optional[float] = Field(None, ge=0, description="Wholesale price")
    sale_price: Optional[float] = Field(None, ge=0, description="Sale price")
    
    # Shipping dimensions
    weight: Optional[float] = Field(None, ge=0, description="Weight")
    weight_unit: Optional[str] = Field(None, max_length=20, description="Weight unit (kg, lb)")
    length: Optional[float] = Field(None, ge=0, description="Length")
    width: Optional[float] = Field(None, ge=0, description="Width")
    height: Optional[float] = Field(None, ge=0, description="Height")
    dimension_unit: Optional[str] = Field(None, max_length=20, description="Dimension unit (cm, inch)")
    
    # Image
    image_url: Optional[str] = Field(None, max_length=500, description="Variant-specific image")
    
    # Status
    is_active: bool = Field(default=True, description="Active status")
    is_default: bool = Field(default=False, description="Default variant to display")

    @field_validator('sku', 'barcode')
    @classmethod
    def validate_codes(cls, v: Optional[str]) -> Optional[str]:
        """Validate SKU and barcode format"""
        if v is not None:
            return v.upper()
        return v

    @field_validator('sale_price')
    @classmethod
    def validate_sale_price(cls, v: Optional[float], info) -> Optional[float]:
        """Validate sale price is less than retail price"""
        if v is not None and 'retail_price' in info.data:
            if v >= info.data['retail_price']:
                raise ValueError('Sale price must be less than retail price')
        return v


class ProductVariantCreate(ProductVariantBase):
    """Schema for creating a new product variant"""
    pass


class ProductVariantUpdate(BaseModel):
    """Schema for updating a product variant"""
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    size: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=100)
    color_code: Optional[str] = Field(None, max_length=20)
    style: Optional[str] = Field(None, max_length=100)
    variant_attributes: Optional[Dict[str, Any]] = None
    cost_price: Optional[float] = Field(None, ge=0)
    retail_price: Optional[float] = Field(None, ge=0)
    wholesale_price: Optional[float] = Field(None, ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    weight_unit: Optional[str] = Field(None, max_length=20)
    length: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    dimension_unit: Optional[str] = Field(None, max_length=20)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ProductVariantResponse(ProductVariantBase):
    """Schema for product variant response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    display_name: Optional[str] = Field(None, description="Display name (e.g., 'Red / M / Slim Fit')")
    stock_available: Optional[int] = Field(None, description="Available stock across all locations")
    
    class Config:
        from_attributes = True


class ProductVariantListResponse(BaseModel):
    """Paginated product variant list response"""
    items: List[ProductVariantResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Enable forward references
ProductWithVariants.model_rebuild()
