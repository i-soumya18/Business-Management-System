"""
Order and Sales Models

Models for multi-channel orders, order items, pricing tiers, payments, and shipping.
Supports B2B wholesale, B2C retail, and e-commerce sales channels.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4
from enum import Enum as PyEnum
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, String, Text, UUID, Numeric, Integer, ForeignKey, Index, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import ProductVariant
    from app.models.order_management import OrderHistory, OrderNote, OrderFulfillment, InventoryReservation
    from app.models.user import User
    from app.models.wholesale import WholesaleCustomer


class SalesChannel(str, PyEnum):
    """Sales Channel Types"""
    WHOLESALE = "wholesale"  # B2B wholesale orders
    RETAIL = "retail"  # In-store POS sales
    ECOMMERCE = "ecommerce"  # Online store sales
    MARKETPLACE = "marketplace"  # Third-party marketplace (Amazon, etc.)


class OrderStatus(str, PyEnum):
    """Order Status Workflow"""
    DRAFT = "draft"  # Order being created, not submitted
    PENDING = "pending"  # Awaiting approval/payment
    CONFIRMED = "confirmed"  # Order confirmed, ready for fulfillment
    PROCESSING = "processing"  # Being prepared/packed
    READY_TO_SHIP = "ready_to_ship"  # Packed and ready for pickup
    SHIPPED = "shipped"  # Dispatched to customer
    IN_TRANSIT = "in_transit"  # In delivery
    DELIVERED = "delivered"  # Successfully delivered
    COMPLETED = "completed"  # Order completed and closed
    CANCELLED = "cancelled"  # Order cancelled
    REFUNDED = "refunded"  # Order refunded
    RETURN_REQUESTED = "return_requested"  # Return initiated
    RETURNED = "returned"  # Return completed
    FAILED = "failed"  # Order failed (payment/fulfillment)


class PaymentStatus(str, PyEnum):
    """Payment Status"""
    PENDING = "pending"  # Awaiting payment
    AUTHORIZED = "authorized"  # Payment authorized but not captured
    PAID = "paid"  # Payment completed
    PARTIAL = "partial"  # Partially paid
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Payment refunded
    CANCELLED = "cancelled"  # Payment cancelled


class PaymentMethod(str, PyEnum):
    """Payment Methods"""
    CASH = "cash"
    CARD = "card"  # Credit/Debit card
    UPI = "upi"  # UPI payment
    NET_BANKING = "net_banking"
    WALLET = "wallet"  # Digital wallet
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"
    CREDIT = "credit"  # Credit terms (Net 30/60)
    COD = "cod"  # Cash on delivery


class ShippingStatus(str, PyEnum):
    """Shipping Status"""
    PENDING = "pending"
    PREPARING = "preparing"
    READY_TO_SHIP = "ready_to_ship"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


class PricingTierType(str, PyEnum):
    """Pricing Tier Types"""
    QUANTITY = "quantity"  # Volume-based pricing
    VALUE = "value"  # Order value-based pricing
    CUSTOMER = "customer"  # Customer-specific pricing
    SEASONAL = "seasonal"  # Seasonal/promotional pricing


class Order(Base):
    """Order Model
    
    Core order entity supporting multiple sales channels (wholesale, retail, e-commerce).
    """
    
    __tablename__ = "orders"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Order Number - Human-readable unique identifier
    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Sales Channel
    channel: Mapped[SalesChannel] = mapped_column(
        Enum(SalesChannel),
        nullable=False,
        index=True
    )
    
    # Order Status
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Customer Information
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Wholesale Customer (for B2B orders)
    wholesale_customer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Customer details (for guest checkout or stored separately)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Sales Representative (for wholesale/B2B)
    sales_rep_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Financial Information
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Subtotal (sum of order items)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    
    # Discounts
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    discount_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    discount_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Tax
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    tax_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Shipping
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    
    # Total Amount
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    
    # Payment Information
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod),
        nullable=True
    )
    
    # Payment Terms (for B2B)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Net 30, Net 60
    payment_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Notes and References
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # PO number, etc.
    
    # Order Metadata
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Website, App, POS, etc.
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Additional Data (flexible JSON field)
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Important Dates
    order_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
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
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    payments: Mapped[List["PaymentTransaction"]] = relationship(
        "PaymentTransaction",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    shipping_details: Mapped[Optional["ShippingDetails"]] = relationship(
        "ShippingDetails",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    customer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[customer_id],
        back_populates="orders"
    )
    
    wholesale_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        foreign_keys=[wholesale_customer_id],
        back_populates="orders"
    )
    
    sales_rep: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[sales_rep_id]
    )
    
    # Order Management Relationships
    history: Mapped[List["OrderHistory"]] = relationship(
        "OrderHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderHistory.created_at.desc()"
    )
    
    notes: Mapped[List["OrderNote"]] = relationship(
        "OrderNote",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderNote.created_at.desc()"
    )
    
    fulfillments: Mapped[List["OrderFulfillment"]] = relationship(
        "OrderFulfillment",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    inventory_reservations: Mapped[List["InventoryReservation"]] = relationship(
        "InventoryReservation",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_order_customer_date', 'customer_id', 'order_date'),
        Index('idx_order_status_channel', 'status', 'channel'),
        Index('idx_order_payment_status', 'payment_status'),
    )
    
    def __repr__(self):
        return f"<Order {self.order_number} - {self.status.value}>"
    
    def calculate_totals(self):
        """Calculate order totals from items"""
        self.subtotal = sum(item.total_price for item in self.items)
        self.total_amount = (
            self.subtotal 
            - self.discount_amount 
            + self.tax_amount 
            + self.shipping_amount
        )


class OrderItem(Base):
    """Order Item Model
    
    Individual line items in an order with pricing details.
    """
    
    __tablename__ = "order_items"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    product_variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Product Information (snapshot at order time)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    product_sku: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Quantity
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Pricing (at time of order)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    # Discount on this item
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    discount_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Tax on this item
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False
    )
    tax_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Total Price (quantity * unit_price - discount + tax)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    # Cost Price (for profit calculation)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Additional Data (customization, etc.)
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
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
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    
    def __repr__(self):
        return f"<OrderItem {self.product_sku} x {self.quantity}>"
    
    def calculate_total(self):
        """Calculate total price for this line item"""
        base_price = self.unit_price * self.quantity
        self.total_price = base_price - self.discount_amount + self.tax_amount


class PricingTier(Base):
    """Pricing Tier Model
    
    Defines volume-based, value-based, or customer-specific pricing rules.
    """
    
    __tablename__ = "pricing_tiers"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pricing Tier Type
    tier_type: Mapped[PricingTierType] = mapped_column(
        Enum(PricingTierType),
        nullable=False,
        index=True
    )
    
    # Applicable Channel
    channel: Mapped[Optional[SalesChannel]] = mapped_column(
        Enum(SalesChannel),
        nullable=True,
        index=True
    )
    
    # Tier Rules (quantity/value thresholds)
    min_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    max_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Discount Configuration
    discount_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    discount_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Fixed Price (alternative to discount)
    fixed_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Priority (higher priority tiers are applied first)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Applicability
    product_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of product IDs
    category_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of category IDs
    customer_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of customer IDs
    
    # Validity Period
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
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
    
    def __repr__(self):
        return f"<PricingTier {self.code} - {self.tier_type.value}>"
    
    def is_valid(self, check_date: Optional[datetime] = None) -> bool:
        """Check if pricing tier is currently valid"""
        if not self.is_active:
            return False
        
        check_date = check_date or datetime.utcnow()
        
        if self.valid_from and check_date < self.valid_from:
            return False
        
        if self.valid_until and check_date > self.valid_until:
            return False
        
        return True


class PaymentTransaction(Base):
    """Payment Transaction Model
    
    Records all payment transactions for orders.
    """
    
    __tablename__ = "payment_transactions"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Key
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Transaction Details
    transaction_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod),
        nullable=False,
        index=True
    )
    
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Amount Information
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Payment Gateway Details
    gateway: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Stripe, Razorpay, etc.
    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Card/Bank Details (masked)
    card_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    card_brand: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # UPI Details
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Cheque Details
    cheque_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cheque_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Reference
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Failure Information
    failure_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Refund Information
    refund_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    refund_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Processed By
    processed_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
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
    order: Mapped["Order"] = relationship("Order", back_populates="payments")
    processed_by: Mapped[Optional["User"]] = relationship("User")
    
    def __repr__(self):
        return f"<PaymentTransaction {self.transaction_id} - {self.payment_status.value}>"


class ShippingDetails(Base):
    """Shipping Details Model
    
    Stores shipping and delivery information for orders.
    """
    
    __tablename__ = "shipping_details"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Key
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Shipping Status
    shipping_status: Mapped[ShippingStatus] = mapped_column(
        Enum(ShippingStatus),
        default=ShippingStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Shipping Address
    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    
    # Landmark
    landmark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Shipping Method
    shipping_method: Mapped[str] = mapped_column(String(100), nullable=False)  # Standard, Express, etc.
    shipping_carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # FedEx, DHL, etc.
    
    # Tracking
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tracking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Estimated Delivery
    estimated_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Package Details
    weight: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # in kg
    dimensions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # length, width, height
    package_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Delivery Instructions
    delivery_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Delivery Proof
    delivered_to: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    delivery_signature_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    delivery_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    
    # Relationship
    order: Mapped["Order"] = relationship("Order", back_populates="shipping_details")
    
    def __repr__(self):
        return f"<ShippingDetails for Order {self.order_id} - {self.shipping_status.value}>"
    
    @property
    def full_address(self) -> str:
        """Get formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join([p for p in parts if p])
