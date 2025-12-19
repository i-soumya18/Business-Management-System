"""
Retail Customer Models - B2C CRM

Models for retail/online customer management including:
- Customer profiles and preferences
- Loyalty points and rewards
- Purchase history tracking
- RFM analysis (Recency, Frequency, Monetary)
- Customer lifetime value
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, String, Text, UUID, Numeric, Integer,
    ForeignKey, Index, Enum, JSON, Date, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order


class CustomerTierLevel(str, PyEnum):
    """Customer tier/loyalty level"""
    BRONZE = "bronze"  # New/low-value customers
    SILVER = "silver"  # Regular customers
    GOLD = "gold"  # High-value customers
    PLATINUM = "platinum"  # VIP customers


class CustomerPreferenceType(str, PyEnum):
    """Types of customer preferences"""
    COMMUNICATION = "communication"  # Email, SMS, push notifications
    SHOPPING = "shopping"  # Preferred categories, brands
    PAYMENT = "payment"  # Preferred payment method
    DELIVERY = "delivery"  # Preferred delivery method
    MARKETING = "marketing"  # Marketing consent


class RetailCustomer(Base):
    """
    Retail Customer Model for B2C customers
    
    Manages individual consumers shopping through retail stores, e-commerce,
    and other B2C channels. Includes loyalty program, preferences, and
    analytics for personalized marketing.
    """
    __tablename__ = "retail_customers"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Customer Identification
    customer_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Personal Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Date of Birth (for birthday promotions)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(20))  # Male, Female, Other, Prefer not to say
    
    # Account Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Email/phone verified
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Address (Primary)
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    
    # Loyalty Program
    loyalty_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loyalty_points_lifetime: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loyalty_tier: Mapped[CustomerTierLevel] = mapped_column(
        Enum(CustomerTierLevel, native_enum=False, length=50),
        nullable=False,
        default=CustomerTierLevel.BRONZE,
        index=True
    )
    tier_start_date: Mapped[Optional[datetime]] = mapped_column(Date)
    tier_expiry_date: Mapped[Optional[datetime]] = mapped_column(Date)
    
    # Purchase Behavior Metrics
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_spent: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    average_order_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    first_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # RFM Metrics (Recency, Frequency, Monetary)
    rfm_recency_score: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    rfm_frequency_score: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    rfm_monetary_score: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    rfm_segment: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # Champion, Loyal, etc.
    rfm_last_calculated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Customer Lifetime Value
    clv: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )  # Predicted Customer Lifetime Value
    clv_last_calculated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Engagement Metrics
    email_open_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # Percentage
    email_click_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # Percentage
    last_email_sent: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_email_opened: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Marketing Preferences
    email_marketing_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_marketing_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    push_notification_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Shopping Preferences (stored as JSON for flexibility)
    preferred_categories: Mapped[Optional[dict]] = mapped_column(JSON)  # Category IDs/names
    preferred_brands: Mapped[Optional[dict]] = mapped_column(JSON)  # Brand IDs/names
    preferred_sizes: Mapped[Optional[dict]] = mapped_column(JSON)  # Size preferences
    preferred_colors: Mapped[Optional[dict]] = mapped_column(JSON)  # Color preferences
    preferred_payment_method: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Source & Attribution
    acquisition_source: Mapped[Optional[str]] = mapped_column(String(100))  # Where they came from
    acquisition_campaign: Mapped[Optional[str]] = mapped_column(String(100))  # Marketing campaign
    referrer_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_customers.id", ondelete="SET NULL")
    )  # Referred by another customer
    
    # User Account Link (if registered online)
    user_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
        index=True
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[dict]] = mapped_column(JSON)  # Flexible tagging
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="retail_customer"
    )
    referrer: Mapped[Optional["RetailCustomer"]] = relationship(
        "RetailCustomer",
        remote_side=[id],
        foreign_keys=[referrer_customer_id]
    )
    loyalty_transactions: Mapped[list["LoyaltyTransaction"]] = relationship(
        "LoyaltyTransaction",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    preferences: Mapped[list["CustomerPreference"]] = relationship(
        "CustomerPreference",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("loyalty_points >= 0", name="check_loyalty_points_positive"),
        CheckConstraint(
            "rfm_recency_score IS NULL OR (rfm_recency_score >= 1 AND rfm_recency_score <= 5)",
            name="check_rfm_recency_range"
        ),
        CheckConstraint(
            "rfm_frequency_score IS NULL OR (rfm_frequency_score >= 1 AND rfm_frequency_score <= 5)",
            name="check_rfm_frequency_range"
        ),
        CheckConstraint(
            "rfm_monetary_score IS NULL OR (rfm_monetary_score >= 1 AND rfm_monetary_score <= 5)",
            name="check_rfm_monetary_range"
        ),
        Index("idx_retail_customer_email", "email"),
        Index("idx_retail_customer_phone", "phone"),
        Index("idx_retail_customer_tier", "loyalty_tier"),
        Index("idx_retail_customer_rfm_segment", "rfm_segment"),
        Index("idx_retail_customer_last_order", "last_order_date"),
    )
    
    def __repr__(self) -> str:
        return f"<RetailCustomer {self.customer_number}: {self.first_name} {self.last_name}>"
    
    @property
    def full_name(self) -> str:
        """Get full customer name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self) -> Optional[str]:
        """Get formatted full address"""
        if not self.address_line1:
            return None
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join(filter(None, parts))


class LoyaltyTransaction(Base):
    """
    Loyalty Points Transaction Log
    
    Tracks all loyalty points earned and redeemed by customers.
    """
    __tablename__ = "loyalty_transactions"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Customer
    customer_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Transaction Details
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # EARNED, REDEEMED, EXPIRED, ADJUSTED
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Context
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    order_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True
    )
    
    # Balance after transaction
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Expiry (for earned points)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Additional data (renamed from metadata to avoid SQLAlchemy reserved word)
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    customer: Mapped["RetailCustomer"] = relationship(
        "RetailCustomer",
        back_populates="loyalty_transactions"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_loyalty_txn_customer_date", "customer_id", "created_at"),
        Index("idx_loyalty_txn_type", "transaction_type"),
    )
    
    def __repr__(self) -> str:
        return f"<LoyaltyTransaction {self.transaction_type}: {self.points} points>"


class CustomerPreference(Base):
    """
    Customer Preferences
    
    Stores customer preferences for communication, shopping, delivery, etc.
    """
    __tablename__ = "customer_preferences"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Customer
    customer_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Preference Details
    preference_type: Mapped[CustomerPreferenceType] = mapped_column(
        Enum(CustomerPreferenceType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False)
    preference_value: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    customer: Mapped["RetailCustomer"] = relationship(
        "RetailCustomer",
        back_populates="preferences"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_customer_pref_customer_type", "customer_id", "preference_type"),
        Index("idx_customer_pref_key", "preference_key"),
    )
    
    def __repr__(self) -> str:
        return f"<CustomerPreference {self.preference_type}: {self.preference_key}>"
