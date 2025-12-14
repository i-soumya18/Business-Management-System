"""
Pricing Engine Models

Models for dynamic pricing rules, channel-specific pricing, volume discounts,
promotional pricing, customer-specific pricing, and price history tracking.
"""

from datetime import datetime, date
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, String, Text, UUID, Numeric, Integer,
    ForeignKey, Index, Enum, JSON, Date, CheckConstraint, Time
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import Product, ProductVariant, Category
    from app.models.user import User
    from app.models.wholesale import WholesaleCustomer


class PricingRuleType(str, PyEnum):
    """Types of Pricing Rules"""
    CHANNEL = "channel"  # Channel-specific pricing
    VOLUME = "volume"  # Volume/quantity-based pricing
    PROMOTIONAL = "promotional"  # Time-limited promotions
    CUSTOMER_TIER = "customer_tier"  # Customer tier pricing
    CUSTOMER_SPECIFIC = "customer_specific"  # Individual customer pricing
    BUNDLE = "bundle"  # Bundle pricing
    SEASONAL = "seasonal"  # Seasonal pricing
    DYNAMIC = "dynamic"  # ML-driven dynamic pricing
    CLEARANCE = "clearance"  # Clearance/markdown pricing


class DiscountType(str, PyEnum):
    """Discount Calculation Type"""
    PERCENTAGE = "percentage"  # Percentage off base price
    FIXED_AMOUNT = "fixed_amount"  # Fixed amount off
    FIXED_PRICE = "fixed_price"  # Fixed sale price
    BUY_X_GET_Y = "buy_x_get_y"  # Buy X get Y free/discounted


class PricingRuleStatus(str, PyEnum):
    """Pricing Rule Status"""
    DRAFT = "draft"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    PAUSED = "paused"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class CustomerTier(str, PyEnum):
    """Customer Pricing Tiers"""
    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    VIP = "vip"


class PriceChangeReason(str, PyEnum):
    """Reason for Price Change"""
    INITIAL_PRICE = "initial_price"
    COST_CHANGE = "cost_change"
    MARKET_ADJUSTMENT = "market_adjustment"
    COMPETITOR_PRICE = "competitor_price"
    PROMOTION = "promotion"
    SEASONAL = "seasonal"
    CLEARANCE = "clearance"
    PRICE_CORRECTION = "price_correction"
    SUPPLIER_CHANGE = "supplier_change"
    CURRENCY_FLUCTUATION = "currency_fluctuation"
    MANUAL_OVERRIDE = "manual_override"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    CHANNEL_PRICE = "channel_price"


class PricingRule(Base):
    """
    Pricing Rule Model
    
    Defines flexible pricing rules that can be applied based on various conditions
    including channel, quantity, customer tier, time period, etc.
    """
    __tablename__ = "pricing_rules"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Rule Identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Rule Type and Status
    rule_type: Mapped[PricingRuleType] = mapped_column(
        Enum(PricingRuleType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    status: Mapped[PricingRuleStatus] = mapped_column(
        Enum(PricingRuleStatus, native_enum=False, length=50),
        default=PricingRuleStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Priority (higher = applied first)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    
    # Discount Configuration
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, native_enum=False, length=50),
        nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 4),
        nullable=False
    )
    
    # Maximum discount cap (optional)
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Minimum price floor (optional)
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Channel Applicability (null = all channels)
    applicable_channels: Mapped[Optional[list]] = mapped_column(JSON)  # ["wholesale", "retail", "ecommerce"]
    
    # Customer Tier Applicability (null = all tiers)
    applicable_customer_tiers: Mapped[Optional[list]] = mapped_column(JSON)  # ["gold", "platinum"]
    
    # Scheduling
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    
    # Time-of-day restrictions (for happy hour pricing, etc.)
    start_time: Mapped[Optional[str]] = mapped_column(String(10))  # HH:MM format
    end_time: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Day restrictions (0=Monday, 6=Sunday)
    applicable_days: Mapped[Optional[list]] = mapped_column(JSON)  # [0, 1, 2, 3, 4]
    
    # Quantity Thresholds (for volume pricing)
    min_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    max_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Order Value Thresholds
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    max_order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Buy X Get Y Configuration
    buy_quantity: Mapped[Optional[int]] = mapped_column(Integer)  # Buy X
    get_quantity: Mapped[Optional[int]] = mapped_column(Integer)  # Get Y
    get_discount_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # Discount on Y
    
    # Usage Limits
    max_uses: Mapped[Optional[int]] = mapped_column(Integer)  # Total uses allowed
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses_per_customer: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Stackable with other rules?
    is_stackable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Exclusivity (exclusive rules prevent other rules from applying)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Additional conditions (flexible JSON)
    conditions: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Metadata
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    updated_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="selectin"
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by_id],
        lazy="selectin"
    )
    
    # Rule applications (products, categories, variants)
    product_rules: Mapped[List["PricingRuleProduct"]] = relationship(
        "PricingRuleProduct",
        back_populates="pricing_rule",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    category_rules: Mapped[List["PricingRuleCategory"]] = relationship(
        "PricingRuleCategory",
        back_populates="pricing_rule",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    customer_rules: Mapped[List["PricingRuleCustomer"]] = relationship(
        "PricingRuleCustomer",
        back_populates="pricing_rule",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_pricing_rules_type_status", "rule_type", "status"),
        Index("ix_pricing_rules_priority_status", "priority", "status"),
        Index("ix_pricing_rules_dates", "start_date", "end_date"),
    )
    
    def __repr__(self) -> str:
        return f"<PricingRule {self.code}: {self.name}>"


class PricingRuleProduct(Base):
    """
    Links pricing rules to specific products or variants
    """
    __tablename__ = "pricing_rule_products"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    pricing_rule_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Can link to either product or specific variant
    product_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Exclusion flag (to exclude specific items from a broader rule)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Override discount for this specific product
    override_discount_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_rule: Mapped["PricingRule"] = relationship(
        "PricingRule",
        back_populates="product_rules"
    )
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
    product_variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", lazy="selectin")
    
    __table_args__ = (
        Index("ix_pricing_rule_products_rule_product", "pricing_rule_id", "product_id"),
        Index("ix_pricing_rule_products_rule_variant", "pricing_rule_id", "product_variant_id"),
        CheckConstraint(
            "(product_id IS NOT NULL) OR (product_variant_id IS NOT NULL)",
            name="check_product_or_variant"
        ),
    )


class PricingRuleCategory(Base):
    """
    Links pricing rules to product categories
    """
    __tablename__ = "pricing_rule_categories"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    pricing_rule_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    category_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Include subcategories?
    include_subcategories: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Exclusion flag
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_rule: Mapped["PricingRule"] = relationship(
        "PricingRule",
        back_populates="category_rules"
    )
    category: Mapped["Category"] = relationship("Category", lazy="selectin")
    
    __table_args__ = (
        Index("ix_pricing_rule_categories_rule_cat", "pricing_rule_id", "category_id"),
    )


class PricingRuleCustomer(Base):
    """
    Links pricing rules to specific customers
    """
    __tablename__ = "pricing_rule_customers"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    pricing_rule_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Can link to wholesale customer or regular user
    wholesale_customer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Override discount for this specific customer
    override_discount_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    pricing_rule: Mapped["PricingRule"] = relationship(
        "PricingRule",
        back_populates="customer_rules"
    )
    wholesale_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        lazy="selectin"
    )
    user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    
    __table_args__ = (
        Index("ix_pricing_rule_customers_rule_wholesale", "pricing_rule_id", "wholesale_customer_id"),
        Index("ix_pricing_rule_customers_rule_user", "pricing_rule_id", "user_id"),
    )


class ChannelPrice(Base):
    """
    Channel-Specific Base Pricing
    
    Stores base prices per channel for products/variants.
    """
    __tablename__ = "channel_prices"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Product or Variant
    product_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Channel
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Pricing
    base_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    compare_at_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))  # Original/strike-through price
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))  # For margin calculations
    
    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Minimum sale price
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Effective dates
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    effective_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
    product_variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", lazy="selectin")
    
    __table_args__ = (
        Index("ix_channel_prices_product_channel", "product_id", "channel"),
        Index("ix_channel_prices_variant_channel", "product_variant_id", "channel"),
        Index("ix_channel_prices_channel_active", "channel", "is_active"),
        CheckConstraint(
            "(product_id IS NOT NULL) OR (product_variant_id IS NOT NULL)",
            name="check_channel_price_product_or_variant"
        ),
    )


class VolumeDiscount(Base):
    """
    Volume-Based Discount Tiers
    
    Defines quantity-based discount tiers for products or categories.
    """
    __tablename__ = "volume_discounts"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Name and description
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Applies to (can be product, variant, category, or global)
    product_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    category_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # If all null, applies globally
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Quantity range
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Discount
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, native_enum=False, length=50),
        nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    
    # Channel restriction
    channel: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Customer tier restriction
    customer_tier: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Effective dates
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Priority (for overlapping tiers)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Audit fields
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
    product_variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", lazy="selectin")
    category: Mapped[Optional["Category"]] = relationship("Category", lazy="selectin")
    created_by: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    
    __table_args__ = (
        Index("ix_volume_discounts_product_qty", "product_id", "min_quantity"),
        Index("ix_volume_discounts_category_qty", "category_id", "min_quantity"),
        Index("ix_volume_discounts_active", "is_active", "priority"),
    )


class Promotion(Base):
    """
    Promotional Campaign Model
    
    Time-limited promotional campaigns with promo codes.
    """
    __tablename__ = "promotions"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Promotion Details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status
    status: Mapped[PricingRuleStatus] = mapped_column(
        Enum(PricingRuleStatus, native_enum=False, length=50),
        default=PricingRuleStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Discount Configuration
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, native_enum=False, length=50),
        nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    
    # Maximum discount cap
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Minimum requirements
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    min_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Buy X Get Y
    buy_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    get_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    get_discount_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    # Channel restrictions
    applicable_channels: Mapped[Optional[list]] = mapped_column(JSON)
    
    # Customer restrictions
    applicable_customer_tiers: Mapped[Optional[list]] = mapped_column(JSON)
    first_order_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Product/Category restrictions (JSON arrays of IDs)
    applicable_product_ids: Mapped[Optional[list]] = mapped_column(JSON)
    applicable_category_ids: Mapped[Optional[list]] = mapped_column(JSON)
    excluded_product_ids: Mapped[Optional[list]] = mapped_column(JSON)
    
    # Scheduling
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Usage Limits
    max_uses: Mapped[Optional[int]] = mapped_column(Integer)
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses_per_customer: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Combinability
    is_stackable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Auto-apply (doesn't need code entry)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Display
    display_name: Mapped[Optional[str]] = mapped_column(String(200))  # Customer-facing name
    terms_conditions: Mapped[Optional[str]] = mapped_column(Text)
    
    # Marketing
    banner_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Metadata
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    created_by: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    usages: Mapped[List["PromotionUsage"]] = relationship(
        "PromotionUsage",
        back_populates="promotion",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    __table_args__ = (
        Index("ix_promotions_dates_status", "start_date", "end_date", "status"),
        Index("ix_promotions_auto_apply", "auto_apply", "status"),
    )


class PromotionUsage(Base):
    """
    Tracks promotion code usage
    """
    __tablename__ = "promotion_usages"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    promotion_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promotions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    order_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Customer
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    wholesale_customer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Discount applied
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Order details at time of use
    order_total_before_discount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    order_total_after_discount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    promotion: Mapped["Promotion"] = relationship("Promotion", back_populates="usages")
    
    __table_args__ = (
        Index("ix_promotion_usages_promo_user", "promotion_id", "user_id"),
        Index("ix_promotion_usages_promo_wholesale", "promotion_id", "wholesale_customer_id"),
    )


class PriceHistory(Base):
    """
    Price History Tracking
    
    Records all price changes for audit and analysis.
    """
    __tablename__ = "price_history"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Product/Variant
    product_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Channel (optional - null for base price changes)
    channel: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    
    # Price changes
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    new_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Cost changes (for margin tracking)
    old_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    new_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Currency
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Change reason
    change_reason: Mapped[PriceChangeReason] = mapped_column(
        Enum(PriceChangeReason, native_enum=False, length=50),
        nullable=False
    )
    
    # Additional notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Who made the change
    changed_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Related pricing rule (if applicable)
    pricing_rule_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Effective date
    effective_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Additional context data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
    product_variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", lazy="selectin")
    changed_by: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    
    __table_args__ = (
        Index("ix_price_history_product_date", "product_id", "effective_date"),
        Index("ix_price_history_variant_date", "product_variant_id", "effective_date"),
        Index("ix_price_history_channel_date", "channel", "effective_date"),
        Index("ix_price_history_reason", "change_reason", "effective_date"),
        CheckConstraint(
            "(product_id IS NOT NULL) OR (product_variant_id IS NOT NULL)",
            name="check_price_history_product_or_variant"
        ),
    )


class CompetitorPrice(Base):
    """
    Competitor Price Monitoring
    
    Tracks competitor pricing for future ML integration.
    """
    __tablename__ = "competitor_prices"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Product reference
    product_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Competitor Information
    competitor_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    competitor_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Matching product on competitor site
    competitor_product_name: Mapped[Optional[str]] = mapped_column(String(500))
    competitor_sku: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    sale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Availability
    in_stock: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    # Data source
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # manual, scraper, api
    
    # Confidence score (for scraped/matched data)
    match_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    
    # When this price was observed
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Is this the latest observation?
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Additional data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
    product_variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", lazy="selectin")
    
    __table_args__ = (
        Index("ix_competitor_prices_product_competitor", "product_id", "competitor_name"),
        Index("ix_competitor_prices_variant_competitor", "product_variant_id", "competitor_name"),
        Index("ix_competitor_prices_observed", "observed_at"),
        Index("ix_competitor_prices_latest", "is_latest", "competitor_name"),
    )


class CustomerPricingTier(Base):
    """
    Customer Pricing Tier Assignment
    
    Assigns customers to pricing tiers for tier-based discounts.
    """
    __tablename__ = "customer_pricing_tiers"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Customer (user or wholesale)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    wholesale_customer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Tier assignment
    tier: Mapped[CustomerTier] = mapped_column(
        Enum(CustomerTier, native_enum=False, length=50),
        nullable=False,
        default=CustomerTier.STANDARD
    )
    
    # Tier details
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0"),
        nullable=False
    )
    
    # How tier was assigned
    assignment_reason: Mapped[Optional[str]] = mapped_column(String(200))
    
    # When tier becomes effective
    effective_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    effective_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Auto-calculated vs manual
    is_automatic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    wholesale_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        lazy="selectin"
    )
    
    __table_args__ = (
        Index("ix_customer_pricing_tiers_user", "user_id", "tier"),
        Index("ix_customer_pricing_tiers_wholesale", "wholesale_customer_id", "tier"),
        CheckConstraint(
            "(user_id IS NOT NULL) OR (wholesale_customer_id IS NOT NULL)",
            name="check_customer_tier_user_or_wholesale"
        ),
    )
