"""
Category Schemas

Pydantic schemas for Category API requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CategoryBase(BaseModel):
    """Base category schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Category name")
    slug: str = Field(..., min_length=1, max_length=250, description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Category description")
    parent_id: Optional[UUID] = Field(None, description="Parent category ID for hierarchy")
    display_order: int = Field(default=0, description="Display order for sorting")
    image_url: Optional[str] = Field(None, max_length=500, description="Category image URL")
    meta_title: Optional[str] = Field(None, max_length=200, description="SEO meta title")
    meta_description: Optional[str] = Field(None, description="SEO meta description")
    meta_keywords: Optional[str] = Field(None, max_length=500, description="SEO keywords")
    is_active: bool = Field(default=True, description="Active status")

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()


class CategoryCreate(CategoryBase):
    """Schema for creating a new category"""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    display_order: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """Validate slug format"""
        if v is not None:
            if not v.replace('-', '').replace('_', '').isalnum():
                raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
            return v.lower()
        return v


class CategoryResponse(CategoryBase):
    """Schema for category response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CategoryWithChildren(CategoryResponse):
    """Category with subcategories"""
    subcategories: List['CategoryResponse'] = Field(default_factory=list)
    product_count: Optional[int] = Field(None, description="Number of products in this category")
    
    class Config:
        from_attributes = True


class CategoryTree(CategoryResponse):
    """Recursive category tree structure"""
    subcategories: List['CategoryTree'] = Field(default_factory=list)
    full_path: str = Field(..., description="Full category path")
    level: int = Field(..., description="Category nesting level")
    
    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """Paginated category list response"""
    items: List[CategoryResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Enable forward references for recursive models
CategoryWithChildren.model_rebuild()
CategoryTree.model_rebuild()
