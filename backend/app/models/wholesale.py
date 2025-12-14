"""
Wholesale Customer Models

Models for B2B wholesale customer management, credit limits, payment terms,
and contract pricing.
"""

from datetime import datetime, date
from typing import TYPE_CHECKING, List, Optional
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
    from app.models.product import ProductVariant, Category


class CustomerType(str, PyEnum):
    """Wholesale Customer Type"""
    RETAILER = "retailer"  # Retail store/boutique
    DISTRIBUTOR = "distributor"  # Regional distributor
    WHOLESALER = "wholesaler"  # Another wholesaler
    MANUFACTURER = "manufacturer"  # Manufacturing company
    EXPORTER = "exporter"  # Export business
    ECOMMERCE = "ecommerce"  # Online retailer


class CustomerStatus(str, PyEnum):
    """Customer Account Status"""
    ACTIVE = "active"  # Active account
    INACTIVE = "inactive"  # Temporarily inactive
    SUSPENDED = "suspended"  # Suspended due to payment issues
    PENDING_APPROVAL = "pending_approval"  # New customer awaiting approval
    REJECTED = "rejected"  # Application rejected
    CLOSED = "closed"  # Account closed


class PaymentTerms(str, PyEnum):
    """Payment Terms"""
    IMMEDIATE = "immediate"  # Pay immediately
    NET_7 = "net_7"  # Payment due in 7 days
    NET_15 = "net_15"  # Payment due in 15 days
    NET_30 = "net_30"  # Payment due in 30 days
    NET_60 = "net_60"  # Payment due in 60 days
    NET_90 = "net_90"  # Payment due in 90 days
    COD = "cod"  # Cash on delivery
    ADVANCE = "advance"  # Full advance payment


class CreditStatus(str, PyEnum):
    """Credit Status"""
    GOOD = "good"  # Good credit standing
    WARNING = "warning"  # Approaching credit limit
    EXCEEDED = "exceeded"  # Credit limit exceeded
    SUSPENDED = "suspended"  # Credit suspended


class WholesaleCustomer(Base):
    """
    Wholesale Customer Model for B2B customers
    
    Manages B2B customer accounts with credit management, payment terms,
    pricing agreements, and relationship management.
    """
    __tablename__ = "wholesale_customers"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Company Information
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_legal_name: Mapped[Optional[str]] = mapped_column(String(255))
    business_registration_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # GST/VAT number
    
    # Customer Type & Status
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, native_enum=False, length=50),
        nullable=False,
        default=CustomerType.RETAILER
    )
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, native_enum=False, length=50),
        nullable=False,
        default=CustomerStatus.PENDING_APPROVAL
    )
    
    # Contact Information
    primary_contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    primary_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    secondary_contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    secondary_email: Mapped[Optional[str]] = mapped_column(String(255))
    secondary_phone: Mapped[Optional[str]] = mapped_column(String(20))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Business Address
    billing_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    billing_city: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_state: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    
    shipping_address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    shipping_address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    shipping_city: Mapped[Optional[str]] = mapped_column(String(100))
    shipping_state: Mapped[Optional[str]] = mapped_column(String(100))
    shipping_postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    shipping_country: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Credit Management
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    credit_used: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    credit_available: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    credit_status: Mapped[CreditStatus] = mapped_column(
        Enum(CreditStatus, native_enum=False, length=50),
        nullable=False,
        default=CreditStatus.GOOD
    )
    
    # Payment Terms
    payment_terms: Mapped[PaymentTerms] = mapped_column(
        Enum(PaymentTerms, native_enum=False, length=50),
        nullable=False,
        default=PaymentTerms.NET_30
    )
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    
    # Pricing & Discounts
    default_discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    has_contract_pricing: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_start_date: Mapped[Optional[date]] = mapped_column(Date)
    contract_end_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Minimum Order Requirements
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_order_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Sales Representative Assignment
    sales_rep_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    
    # Business Details
    business_since: Mapped[Optional[date]] = mapped_column(Date)
    annual_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    number_of_employees: Mapped[Optional[int]] = mapped_column(Integer)
    number_of_stores: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Preferences & Settings
    preferred_shipping_method: Mapped[Optional[str]] = mapped_column(String(100))
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)  # Orders need approval
    auto_approve_orders: Mapped[bool] = mapped_column(Boolean, default=False)
    send_invoices_via_email: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Performance Metrics
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
    last_order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Communication & Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)  # Internal notes
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Flexible storage
    
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
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relationships
    sales_rep: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[sales_rep_id],
        back_populates="wholesale_customers"
    )
    approved_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="wholesale_customer",
        foreign_keys="[Order.wholesale_customer_id]"
    )
    contract_prices: Mapped[List["ContractPricing"]] = relationship(
        "ContractPricing",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("credit_limit >= 0", name="check_credit_limit_positive"),
        CheckConstraint("credit_used >= 0", name="check_credit_used_positive"),
        CheckConstraint(
            "default_discount_percentage >= 0 AND default_discount_percentage <= 100",
            name="check_discount_percentage_range"
        ),
        CheckConstraint(
            "minimum_order_quantity >= 0",
            name="check_moq_positive"
        ),
        CheckConstraint(
            "minimum_order_value >= 0",
            name="check_mov_positive"
        ),
        Index("idx_wholesale_customer_company", "company_name"),
        Index("idx_wholesale_customer_status", "status"),
        Index("idx_wholesale_customer_sales_rep", "sales_rep_id"),
        Index("idx_wholesale_customer_credit_status", "credit_status"),
    )
    
    def __repr__(self) -> str:
        return f"<WholesaleCustomer(id={self.id}, company={self.company_name}, status={self.status})>"
    
    @property
    def full_billing_address(self) -> str:
        """Get full formatted billing address"""
        parts = [
            self.billing_address_line1,
            self.billing_address_line2,
            self.billing_city,
            self.billing_state,
            self.billing_postal_code,
            self.billing_country
        ]
        return ", ".join(filter(None, parts))
    
    @property
    def full_shipping_address(self) -> Optional[str]:
        """Get full formatted shipping address"""
        if not self.shipping_address_line1:
            return None
        parts = [
            self.shipping_address_line1,
            self.shipping_address_line2,
            self.shipping_city,
            self.shipping_state,
            self.shipping_postal_code,
            self.shipping_country
        ]
        return ", ".join(filter(None, parts))
    
    def update_credit_available(self) -> None:
        """Calculate and update available credit"""
        self.credit_available = self.credit_limit - self.credit_used
        
        # Update credit status
        if self.credit_used >= self.credit_limit:
            self.credit_status = CreditStatus.EXCEEDED
        elif self.credit_used >= (self.credit_limit * Decimal("0.9")):
            self.credit_status = CreditStatus.WARNING
        else:
            self.credit_status = CreditStatus.GOOD
    
    def has_sufficient_credit(self, amount: Decimal) -> bool:
        """Check if customer has sufficient credit for an amount"""
        return self.credit_available >= amount
    
    def is_contract_active(self) -> bool:
        """Check if contract pricing is currently active"""
        if not self.has_contract_pricing:
            return False
        if not self.contract_start_date or not self.contract_end_date:
            return False
        today = date.today()
        return self.contract_start_date <= today <= self.contract_end_date


class ContractPricing(Base):
    """
    Contract-based pricing for specific customers and products
    
    Allows setting special prices for wholesale customers based on contracts.
    Can be product-specific, category-specific, or volume-based.
    """
    __tablename__ = "contract_pricing"
    
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
        ForeignKey("wholesale_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Product/Category Applicability
    product_variant_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        index=True
    )
    category_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True
    )
    
    # Pricing Details
    contract_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    # Volume-Based Pricing
    minimum_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    maximum_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Validity Period
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
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
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relationships
    customer: Mapped["WholesaleCustomer"] = relationship(
        "WholesaleCustomer",
        back_populates="contract_prices"
    )
    product_variant: Mapped[Optional["ProductVariant"]] = relationship(
        "ProductVariant",
        foreign_keys=[product_variant_id]
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        foreign_keys=[category_id]
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("contract_price >= 0", name="check_contract_price_positive"),
        CheckConstraint(
            "discount_percentage IS NULL OR (discount_percentage >= 0 AND discount_percentage <= 100)",
            name="check_contract_discount_range"
        ),
        CheckConstraint("minimum_quantity > 0", name="check_minimum_quantity_positive"),
        CheckConstraint(
            "maximum_quantity IS NULL OR maximum_quantity >= minimum_quantity",
            name="check_quantity_range_valid"
        ),
        CheckConstraint("valid_until >= valid_from", name="check_validity_period"),
        Index("idx_contract_pricing_customer", "customer_id"),
        Index("idx_contract_pricing_product", "product_variant_id"),
        Index("idx_contract_pricing_category", "category_id"),
        Index("idx_contract_pricing_validity", "valid_from", "valid_until"),
        Index("idx_contract_pricing_active", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<ContractPricing(id={self.id}, customer_id={self.customer_id}, price={self.contract_price})>"
    
    def is_valid(self, check_date: Optional[date] = None) -> bool:
        """Check if pricing is valid on a given date"""
        if not self.is_active:
            return False
        check_date = check_date or date.today()
        return self.valid_from <= check_date <= self.valid_until
    
    def applies_to_quantity(self, quantity: int) -> bool:
        """Check if pricing applies to a given quantity"""
        if quantity < self.minimum_quantity:
            return False
        if self.maximum_quantity and quantity > self.maximum_quantity:
            return False
        return True
