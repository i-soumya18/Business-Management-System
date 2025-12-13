"""
Garment-Specific Models

Models for garment-specific features including size charts, colors, fabrics,
styles, collections, seasons, and measurements.
"""

from sqlalchemy import String, Integer, Float, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
import enum

from app.models.base import BaseModel


class SizeCategory(str, enum.Enum):
    """Size category enumeration"""
    TOPS = "tops"
    BOTTOMS = "bottoms"
    DRESSES = "dresses"
    OUTERWEAR = "outerwear"
    FOOTWEAR = "footwear"
    ACCESSORIES = "accessories"
    ONE_SIZE = "one_size"


class Region(str, enum.Enum):
    """Region enumeration for size charts"""
    US = "us"
    EU = "eu"
    UK = "uk"
    ASIA = "asia"
    INTERNATIONAL = "international"


class Season(str, enum.Enum):
    """Season enumeration"""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all_season"


class SizeChart(BaseModel):
    """Size chart model for different garment categories and regions"""
    
    __tablename__ = "size_charts"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[SizeCategory] = mapped_column(SQLEnum(SizeCategory), nullable=False)
    region: Mapped[Region] = mapped_column(SQLEnum(Region), nullable=False, default=Region.INTERNATIONAL)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Size definitions as JSON: [{"size": "S", "label": "Small", "measurements": {...}}]
    sizes: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Relationships
    products = relationship("Product", back_populates="size_chart")
    
    def __repr__(self):
        return f"<SizeChart {self.name} ({self.category} - {self.region})>"


class Color(BaseModel):
    """Color variant model with hex codes"""
    
    __tablename__ = "colors"
    
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # e.g., "BLK", "NVY"
    hex_code: Mapped[str] = mapped_column(String(7), nullable=False)  # e.g., "#000000"
    pantone_code: Mapped[Optional[str]] = mapped_column(String(20))  # e.g., "19-4052 TCX"
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    variants = relationship("ProductVariant", back_populates="color_obj")
    
    def __repr__(self):
        return f"<Color {self.name} ({self.hex_code})>"


class Fabric(BaseModel):
    """Fabric/material model"""
    
    __tablename__ = "fabrics"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    composition: Mapped[Optional[str]] = mapped_column(Text)  # e.g., "100% Cotton", "60% Cotton, 40% Polyester"
    weight: Mapped[Optional[float]] = mapped_column(Float)  # GSM (grams per square meter)
    care_instructions: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Additional properties as JSON
    properties: Mapped[Optional[dict]] = mapped_column(JSON)  # breathable, stretchable, etc.
    
    def __repr__(self):
        return f"<Fabric {self.name} ({self.composition})>"


class Style(BaseModel):
    """Style/design category model"""
    
    __tablename__ = "styles"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    products = relationship("Product", back_populates="style")
    
    def __repr__(self):
        return f"<Style {self.name}>"


class Collection(BaseModel):
    """Collection model for grouping products"""
    
    __tablename__ = "collections"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    season: Mapped[Season] = mapped_column(SQLEnum(Season), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Launch and end dates
    launch_date: Mapped[Optional[str]] = mapped_column(String(50))
    end_date: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    products = relationship("Product", back_populates="collection")
    
    def __repr__(self):
        return f"<Collection {self.name} ({self.season} {self.year})>"


class MeasurementSpec(BaseModel):
    """Measurement specification model for products"""
    
    __tablename__ = "measurement_specs"
    
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Standard measurements in cm
    chest: Mapped[Optional[float]] = mapped_column(Float)
    waist: Mapped[Optional[float]] = mapped_column(Float)
    hips: Mapped[Optional[float]] = mapped_column(Float)
    length: Mapped[Optional[float]] = mapped_column(Float)
    shoulder: Mapped[Optional[float]] = mapped_column(Float)
    sleeve_length: Mapped[Optional[float]] = mapped_column(Float)
    inseam: Mapped[Optional[float]] = mapped_column(Float)
    
    # Additional measurements as JSON for flexibility
    additional_measurements: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Tolerances
    tolerance: Mapped[float] = mapped_column(Float, default=1.0)  # +/- cm
    
    # Relationships
    product = relationship("Product", back_populates="measurement_specs")
    
    def __repr__(self):
        return f"<MeasurementSpec Product {self.product_id} Size {self.size}>"


class GarmentImage(BaseModel):
    """Garment image gallery model for multiple product images"""
    
    __tablename__ = "garment_images"
    
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    alt_text: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Image type/angle
    image_type: Mapped[str] = mapped_column(String(50), default="product")  # product, detail, lifestyle, etc.
    angle: Mapped[Optional[str]] = mapped_column(String(50))  # front, back, side, detail, etc.
    
    # Display order
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Color variant (optional - if image is specific to a color)
    color_id: Mapped[Optional[int]] = mapped_column(ForeignKey("colors.id"))
    
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Image metadata
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    
    # Relationships
    product = relationship("Product", back_populates="images")
    color = relationship("Color")
    
    def __repr__(self):
        return f"<GarmentImage {self.product_id} - {self.angle or 'default'}>"


# Many-to-many relationship tables
class ProductFabric(BaseModel):
    """Product-Fabric relationship for garments with multiple fabrics"""
    
    __tablename__ = "product_fabrics"
    
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, primary_key=True)
    fabric_id: Mapped[int] = mapped_column(ForeignKey("fabrics.id"), nullable=False, primary_key=True)
    percentage: Mapped[float] = mapped_column(Float, default=100.0)  # Composition percentage
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    product = relationship("Product", back_populates="product_fabrics")
    fabric = relationship("Fabric")
    
    def __repr__(self):
        return f"<ProductFabric Product {self.product_id} Fabric {self.fabric_id} ({self.percentage}%)>"
