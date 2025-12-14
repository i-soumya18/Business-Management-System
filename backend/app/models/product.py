"""
Product and ProductVariant Models

Core product models with support for variants (size, color, style).
Designed specifically for garment business management.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, UUID, Numeric, Integer, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.brand import Brand
    from app.models.supplier import Supplier
    from app.models.inventory import InventoryLevel, InventoryMovement
    from app.models.garment import SizeChart, Style, Collection, Color, MeasurementSpec, GarmentImage, ProductFabric


class Product(Base):
    """Product Model
    
    Master product information. Each product can have multiple variants
    (different sizes, colors, styles) represented by ProductVariant model.
    """
    
    __tablename__ = "products"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(350), unique=True, nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Foreign Keys
    category_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    brand_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    supplier_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    size_chart_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("size_charts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    style_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("styles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    collection_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Garment-Specific Information
    garment_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Shirt, Pants, Dress, etc.
    fabric_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Cotton, Polyester, etc.
    fabric_composition: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # "80% Cotton, 20% Polyester"
    care_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Season & Collection
    season: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Spring, Summer, Fall, Winter
    collection: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 2024 Summer Collection
    
    # Pricing (Base prices - variants can override)
    base_cost_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    base_retail_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    base_wholesale_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Tax Information
    tax_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # percentage
    tax_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Inventory Management
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Images
    primary_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_urls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of additional images
    
    # SEO
    meta_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Measurements (optional standard measurements)
    measurement_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # cm, inches
    measurements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"chest": 38, "waist": 32, ...}
    
    # Additional Attributes
    attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Custom attributes
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["casual", "formal", "summer"]
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    size_chart: Mapped[Optional["SizeChart"]] = relationship("SizeChart", back_populates="products")
    style: Mapped[Optional["Style"]] = relationship("Style", back_populates="products")
    collection: Mapped[Optional["Collection"]] = relationship("Collection", back_populates="products")
    is_new_arrival: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_on_sale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Display
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="products")
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier", back_populates="products")
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    measurement_specs: Mapped[List["MeasurementSpec"]] = relationship(
        "MeasurementSpec",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    images: Mapped[List["GarmentImage"]] = relationship(
        "GarmentImage",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    product_fabrics: Mapped[List["ProductFabric"]] = relationship(
        "ProductFabric",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_products_category_active", "category_id", "is_active"),
        Index("ix_products_brand_active", "brand_id", "is_active"),
        Index("ix_products_sku_active", "sku", "is_active"),
        Index("ix_products_featured", "is_featured", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"


class ProductVariant(Base):
    """Product Variant Model
    
    Represents specific variations of a product (e.g., Red T-Shirt in Size M).
    Each variant has its own SKU, pricing, and inventory tracking.
    """
    
    __tablename__ = "product_variants"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Key
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Foreign Key to Color table (optional - for linking to garment colors)
    color_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Variant Information
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    
    # Variant Attributes
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # XS, S, M, L, XL, XXL
    color: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    color_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Hex code #FF0000
    style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Slim Fit, Regular, etc.
    
    # Additional Variant Attributes
    variant_attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Custom attributes
    
    # Pricing (Overrides product base prices if set)
    cost_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    retail_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    wholesale_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    sale_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Weight & Dimensions (for shipping)
    weight: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    weight_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # kg, lb
    length: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    width: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    dimension_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # cm, inch
    
    # Images (variant-specific)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Default variant to display
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    color_obj: Mapped[Optional["Color"]] = relationship("Color", back_populates="variants")
    inventory_levels: Mapped[List["InventoryLevel"]] = relationship(
        "InventoryLevel",
        back_populates="product_variant",
        cascade="all, delete-orphan"
    )
    inventory_movements: Mapped[List["InventoryMovement"]] = relationship(
        "InventoryMovement",
        back_populates="product_variant"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_variants_product_active", "product_id", "is_active"),
        Index("ix_variants_sku_active", "sku", "is_active"),
        Index("ix_variants_size_color", "size", "color", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<ProductVariant(id={self.id}, sku='{self.sku}', size='{self.size}', color='{self.color}')>"
    
    @property
    def display_name(self) -> str:
        """Generate display name for variant"""
        parts = []
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        if self.style:
            parts.append(self.style)
        return " / ".join(parts) if parts else "Default"
