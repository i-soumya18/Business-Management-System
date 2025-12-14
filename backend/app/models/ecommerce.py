"""
E-Commerce Models

Models for online shopping functionality including shopping cart, wishlist,
product reviews, promotional codes, and abandoned cart tracking.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, String, Text, UUID, Numeric, Integer,
    ForeignKey, Index, Enum, JSON, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import ProductVariant
    from app.models.order import Order


class CartStatus(str, PyEnum):
    """Shopping Cart Status"""
    ACTIVE = "active"  # Active cart
    ABANDONED = "abandoned"  # Cart abandoned (no activity for X days)
    CONVERTED = "converted"  # Cart converted to order
    MERGED = "merged"  # Cart merged with another cart


class PromoCodeType(str, PyEnum):
    """Promotional Code Type"""
    PERCENTAGE = "percentage"  # Percentage discount
    FIXED_AMOUNT = "fixed_amount"  # Fixed amount discount
    FREE_SHIPPING = "free_shipping"  # Free shipping
    BUY_X_GET_Y = "buy_x_get_y"  # Buy X get Y free


class PromoCodeStatus(str, PyEnum):
    """Promotional Code Status"""
    ACTIVE = "active"  # Code is active
    INACTIVE = "inactive"  # Code is disabled
    EXPIRED = "expired"  # Code has expired
    EXHAUSTED = "exhausted"  # Usage limit reached


class ReviewStatus(str, PyEnum):
    """Product Review Status"""
    PENDING = "pending"  # Awaiting moderation
    APPROVED = "approved"  # Approved and visible
    REJECTED = "rejected"  # Rejected by moderator
    FLAGGED = "flagged"  # Flagged for review


class ShoppingCart(Base):
    """
    Shopping Cart Model
    
    Stores customer shopping cart items with session support.
    """
    __tablename__ = "shopping_carts"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # User Reference (nullable for guest carts)
    user_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    
    # Session ID for guest users
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Status
    status: Mapped[CartStatus] = mapped_column(
        Enum(CartStatus, native_enum=False, length=50),
        nullable=False,
        default=CartStatus.ACTIVE
    )
    
    # Order reference (when converted)
    order_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="shopping_carts")
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan"
    )
    order: Mapped[Optional["Order"]] = relationship("Order")
    
    # Table Constraints
    __table_args__ = (
        Index("idx_shopping_cart_user", "user_id"),
        Index("idx_shopping_cart_session", "session_id"),
        Index("idx_shopping_cart_status", "status"),
        Index("idx_shopping_cart_activity", "last_activity_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ShoppingCart(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def item_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items)
    
    @property
    def subtotal(self) -> Decimal:
        """Calculate cart subtotal"""
        return sum(item.subtotal for item in self.items)


class CartItem(Base):
    """
    Shopping Cart Item Model
    
    Individual items within a shopping cart.
    """
    __tablename__ = "cart_items"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Cart Reference
    cart_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Product Variant Reference
    product_variant_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Quantity
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Price at time of adding to cart
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    cart: Mapped["ShoppingCart"] = relationship("ShoppingCart", back_populates="items")
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_cart_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_cart_item_price_positive"),
        Index("idx_cart_item_cart", "cart_id"),
        Index("idx_cart_item_variant", "product_variant_id"),
    )
    
    def __repr__(self) -> str:
        return f"<CartItem(id={self.id}, cart_id={self.cart_id}, quantity={self.quantity})>"
    
    @property
    def subtotal(self) -> Decimal:
        """Calculate item subtotal"""
        return self.unit_price * self.quantity


class Wishlist(Base):
    """
    Wishlist Model
    
    Customer product wishlist for future purchases.
    """
    __tablename__ = "wishlists"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # User Reference
    user_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Name (e.g., "Summer Collection", "Gift Ideas")
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="My Wishlist")
    
    # Visibility
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wishlists")
    items: Mapped[List["WishlistItem"]] = relationship(
        "WishlistItem",
        back_populates="wishlist",
        cascade="all, delete-orphan"
    )
    
    # Table Constraints
    __table_args__ = (
        Index("idx_wishlist_user", "user_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Wishlist(id={self.id}, user_id={self.user_id}, name={self.name})>"


class WishlistItem(Base):
    """
    Wishlist Item Model
    
    Individual items within a wishlist.
    """
    __tablename__ = "wishlist_items"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Wishlist Reference
    wishlist_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wishlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Product Variant Reference
    product_variant_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Priority (1 = highest)
    priority: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamp
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    wishlist: Mapped["Wishlist"] = relationship("Wishlist", back_populates="items")
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    
    # Table Constraints
    __table_args__ = (
        Index("idx_wishlist_item_wishlist", "wishlist_id"),
        Index("idx_wishlist_item_variant", "product_variant_id"),
    )
    
    def __repr__(self) -> str:
        return f"<WishlistItem(id={self.id}, wishlist_id={self.wishlist_id})>"


class ProductReview(Base):
    """
    Product Review Model
    
    Customer reviews and ratings for products.
    """
    __tablename__ = "product_reviews"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Product Variant Reference
    product_variant_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User Reference
    user_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Order Reference (verified purchase)
    order_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True
    )
    
    # Rating (1-5 stars)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Review Content
    title: Mapped[Optional[str]] = mapped_column(String(200))
    review_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=50),
        nullable=False,
        default=ReviewStatus.PENDING
    )
    
    # Verification
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Helpfulness
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Moderation
    moderator_notes: Mapped[Optional[str]] = mapped_column(Text)
    moderated_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    order: Mapped[Optional["Order"]] = relationship("Order")
    moderator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[moderated_by_id])
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_review_rating_range"),
        CheckConstraint("helpful_count >= 0", name="check_helpful_count_positive"),
        CheckConstraint("not_helpful_count >= 0", name="check_not_helpful_count_positive"),
        Index("idx_product_review_variant", "product_variant_id"),
        Index("idx_product_review_user", "user_id"),
        Index("idx_product_review_status", "status"),
        Index("idx_product_review_rating", "rating"),
    )
    
    def __repr__(self) -> str:
        return f"<ProductReview(id={self.id}, rating={self.rating}, status={self.status})>"


class PromoCode(Base):
    """
    Promotional Code Model
    
    Discount codes and promotional offers for e-commerce.
    """
    __tablename__ = "promo_codes"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Code
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Type
    promo_type: Mapped[PromoCodeType] = mapped_column(
        Enum(PromoCodeType, native_enum=False, length=50),
        nullable=False
    )
    
    # Discount Value
    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Minimum Order Value
    minimum_order_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Maximum Discount Amount (for percentage discounts)
    maximum_discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Usage Limits
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer)
    usage_per_customer: Mapped[Optional[int]] = mapped_column(Integer)
    current_usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Validity
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Status
    status: Mapped[PromoCodeStatus] = mapped_column(
        Enum(PromoCodeStatus, native_enum=False, length=50),
        nullable=False,
        default=PromoCodeStatus.ACTIVE
    )
    
    # Restrictions (stored as JSON for flexibility)
    applicable_categories: Mapped[Optional[dict]] = mapped_column(JSON)
    applicable_products: Mapped[Optional[dict]] = mapped_column(JSON)
    excluded_products: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Customer Restrictions
    customer_emails: Mapped[Optional[dict]] = mapped_column(JSON)  # Specific customers
    new_customers_only: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    usages: Mapped[List["PromoCodeUsage"]] = relationship(
        "PromoCodeUsage",
        back_populates="promo_code",
        cascade="all, delete-orphan"
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint(
            "discount_percentage IS NULL OR (discount_percentage >= 0 AND discount_percentage <= 100)",
            name="check_promo_discount_percentage_range"
        ),
        CheckConstraint("discount_amount IS NULL OR discount_amount >= 0", name="check_promo_discount_amount_positive"),
        CheckConstraint("minimum_order_value IS NULL OR minimum_order_value >= 0", name="check_promo_min_order_positive"),
        CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="check_promo_usage_limit_positive"),
        CheckConstraint("current_usage_count >= 0", name="check_promo_usage_count_positive"),
        Index("idx_promo_code_code", "code"),
        Index("idx_promo_code_status", "status"),
        Index("idx_promo_code_validity", "valid_from", "valid_until"),
    )
    
    def __repr__(self) -> str:
        return f"<PromoCode(id={self.id}, code={self.code}, type={self.promo_type})>"
    
    def is_valid(self) -> bool:
        """Check if promo code is currently valid"""
        now = datetime.utcnow()
        return (
            self.status == PromoCodeStatus.ACTIVE and
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit is None or self.current_usage_count < self.usage_limit)
        )


class PromoCodeUsage(Base):
    """
    Promo Code Usage Model
    
    Tracks usage of promotional codes by customers.
    """
    __tablename__ = "promo_code_usages"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Promo Code Reference
    promo_code_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User Reference
    user_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    
    # Order Reference
    order_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Discount Applied
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Timestamp
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    promo_code: Mapped["PromoCode"] = relationship("PromoCode", back_populates="usages")
    user: Mapped[Optional["User"]] = relationship("User")
    order: Mapped["Order"] = relationship("Order")
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("discount_amount >= 0", name="check_promo_usage_discount_positive"),
        Index("idx_promo_usage_promo", "promo_code_id"),
        Index("idx_promo_usage_user", "user_id"),
        Index("idx_promo_usage_order", "order_id"),
    )
    
    def __repr__(self) -> str:
        return f"<PromoCodeUsage(id={self.id}, promo_code_id={self.promo_code_id}, order_id={self.order_id})>"
