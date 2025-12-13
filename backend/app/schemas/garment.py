"""
Garment-Specific Pydantic Schemas

Schemas for garment features including size charts, colors, fabrics,
styles, collections, seasons, and measurements.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class SizeCategoryEnum(str, Enum):
    """Size category enumeration"""
    TOPS = "tops"
    BOTTOMS = "bottoms"
    DRESSES = "dresses"
    OUTERWEAR = "outerwear"
    FOOTWEAR = "footwear"
    ACCESSORIES = "accessories"
    ONE_SIZE = "one_size"


class RegionEnum(str, Enum):
    """Region enumeration"""
    US = "us"
    EU = "eu"
    UK = "uk"
    ASIA = "asia"
    INTERNATIONAL = "international"


class SeasonEnum(str, Enum):
    """Season enumeration"""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all_season"


# Size Chart Schemas
class SizeDefinition(BaseModel):
    """Individual size definition"""
    size: str = Field(..., description="Size code (e.g., S, M, L)")
    label: str = Field(..., description="Size label (e.g., Small, Medium, Large)")
    measurements: Dict[str, float] = Field(default_factory=dict, description="Size measurements")


class SizeChartBase(BaseModel):
    """Base size chart schema"""
    name: str = Field(..., min_length=1, max_length=100)
    category: SizeCategoryEnum
    region: RegionEnum = RegionEnum.INTERNATIONAL
    description: Optional[str] = None
    sizes: List[SizeDefinition] = Field(..., min_items=1)
    is_active: bool = True


class SizeChartCreate(SizeChartBase):
    """Schema for creating a size chart"""
    pass


class SizeChartUpdate(BaseModel):
    """Schema for updating a size chart"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[SizeCategoryEnum] = None
    region: Optional[RegionEnum] = None
    description: Optional[str] = None
    sizes: Optional[List[SizeDefinition]] = None
    is_active: Optional[bool] = None


class SizeChartResponse(SizeChartBase):
    """Schema for size chart response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Color Schemas
class ColorBase(BaseModel):
    """Base color schema"""
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=2, max_length=20, description="Color code (e.g., BLK, NVY)")
    hex_code: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    pantone_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: bool = True


class ColorCreate(ColorBase):
    """Schema for creating a color"""
    pass


class ColorUpdate(BaseModel):
    """Schema for updating a color"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    hex_code: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    pantone_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ColorResponse(ColorBase):
    """Schema for color response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Fabric Schemas
class FabricBase(BaseModel):
    """Base fabric schema"""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    composition: Optional[str] = Field(None, description="e.g., 100% Cotton")
    weight: Optional[float] = Field(None, ge=0, description="GSM (grams per square meter)")
    care_instructions: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool = True


class FabricCreate(FabricBase):
    """Schema for creating a fabric"""
    pass


class FabricUpdate(BaseModel):
    """Schema for updating a fabric"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    composition: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0)
    care_instructions: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FabricResponse(FabricBase):
    """Schema for fabric response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Style Schemas
class StyleBase(BaseModel):
    """Base style schema"""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None
    is_active: bool = True


class StyleCreate(StyleBase):
    """Schema for creating a style"""
    pass


class StyleUpdate(BaseModel):
    """Schema for updating a style"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StyleResponse(StyleBase):
    """Schema for style response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Collection Schemas
class CollectionBase(BaseModel):
    """Base collection schema"""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    season: SeasonEnum
    year: int = Field(..., ge=2000, le=2100)
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    launch_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = True


class CollectionCreate(CollectionBase):
    """Schema for creating a collection"""
    pass


class CollectionUpdate(BaseModel):
    """Schema for updating a collection"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    season: Optional[SeasonEnum] = None
    year: Optional[int] = Field(None, ge=2000, le=2100)
    description: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=500)
    launch_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None


class CollectionResponse(CollectionBase):
    """Schema for collection response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Measurement Spec Schemas
class MeasurementSpecBase(BaseModel):
    """Base measurement specification schema"""
    product_id: int
    size: str = Field(..., max_length=20)
    chest: Optional[float] = Field(None, ge=0, description="Chest measurement in cm")
    waist: Optional[float] = Field(None, ge=0, description="Waist measurement in cm")
    hips: Optional[float] = Field(None, ge=0, description="Hips measurement in cm")
    length: Optional[float] = Field(None, ge=0, description="Length measurement in cm")
    shoulder: Optional[float] = Field(None, ge=0, description="Shoulder measurement in cm")
    sleeve_length: Optional[float] = Field(None, ge=0, description="Sleeve length in cm")
    inseam: Optional[float] = Field(None, ge=0, description="Inseam measurement in cm")
    additional_measurements: Optional[Dict[str, float]] = Field(default_factory=dict)
    tolerance: float = Field(1.0, ge=0, description="Measurement tolerance in cm")


class MeasurementSpecCreate(MeasurementSpecBase):
    """Schema for creating a measurement spec"""
    pass


class MeasurementSpecUpdate(BaseModel):
    """Schema for updating a measurement spec"""
    size: Optional[str] = Field(None, max_length=20)
    chest: Optional[float] = Field(None, ge=0)
    waist: Optional[float] = Field(None, ge=0)
    hips: Optional[float] = Field(None, ge=0)
    length: Optional[float] = Field(None, ge=0)
    shoulder: Optional[float] = Field(None, ge=0)
    sleeve_length: Optional[float] = Field(None, ge=0)
    inseam: Optional[float] = Field(None, ge=0)
    additional_measurements: Optional[Dict[str, float]] = None
    tolerance: Optional[float] = Field(None, ge=0)


class MeasurementSpecResponse(MeasurementSpecBase):
    """Schema for measurement spec response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Garment Image Schemas
class GarmentImageBase(BaseModel):
    """Base garment image schema"""
    product_id: int
    url: str = Field(..., max_length=500)
    title: Optional[str] = Field(None, max_length=200)
    alt_text: Optional[str] = Field(None, max_length=200)
    image_type: str = Field("product", max_length=50)
    angle: Optional[str] = Field(None, max_length=50, description="front, back, side, detail, etc.")
    display_order: int = Field(0, ge=0)
    color_id: Optional[int] = None
    is_primary: bool = False
    is_active: bool = True
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")


class GarmentImageCreate(GarmentImageBase):
    """Schema for creating a garment image"""
    pass


class GarmentImageUpdate(BaseModel):
    """Schema for updating a garment image"""
    url: Optional[str] = Field(None, max_length=500)
    title: Optional[str] = Field(None, max_length=200)
    alt_text: Optional[str] = Field(None, max_length=200)
    image_type: Optional[str] = Field(None, max_length=50)
    angle: Optional[str] = Field(None, max_length=50)
    display_order: Optional[int] = Field(None, ge=0)
    color_id: Optional[int] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    file_size: Optional[int] = Field(None, ge=0)


class GarmentImageResponse(GarmentImageBase):
    """Schema for garment image response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Product Fabric Schemas
class ProductFabricBase(BaseModel):
    """Base product-fabric relationship schema"""
    product_id: int
    fabric_id: int
    percentage: float = Field(100.0, ge=0, le=100, description="Fabric composition percentage")
    notes: Optional[str] = None


class ProductFabricCreate(ProductFabricBase):
    """Schema for creating a product-fabric relationship"""
    pass


class ProductFabricUpdate(BaseModel):
    """Schema for updating a product-fabric relationship"""
    percentage: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class ProductFabricResponse(ProductFabricBase):
    """Schema for product-fabric response"""
    created_at: datetime
    updated_at: datetime
    fabric: Optional[FabricResponse] = None
    
    class Config:
        from_attributes = True


# List Response Schemas
class ColorListResponse(BaseModel):
    """Schema for color list response"""
    items: List[ColorResponse]
    total: int
    skip: int
    limit: int


class FabricListResponse(BaseModel):
    """Schema for fabric list response"""
    items: List[FabricResponse]
    total: int
    skip: int
    limit: int


class StyleListResponse(BaseModel):
    """Schema for style list response"""
    items: List[StyleResponse]
    total: int
    skip: int
    limit: int


class CollectionListResponse(BaseModel):
    """Schema for collection list response"""
    items: List[CollectionResponse]
    total: int
    skip: int
    limit: int


class SizeChartListResponse(BaseModel):
    """Schema for size chart list response"""
    items: List[SizeChartResponse]
    total: int
    skip: int
    limit: int
