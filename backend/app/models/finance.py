"""
Financial Management Models

Models for financial management including:
- Invoices (Accounts Receivable)
- Bills/Purchase Orders (Accounts Payable)
- Payment Processing
- Payment Reconciliation
- Credit Notes
- Expense Management
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
    from app.models.wholesale import WholesaleCustomer
    from app.models.retail_customer import RetailCustomer
    from app.models.supplier import Supplier


class InvoiceStatus(str, PyEnum):
    """Invoice status"""
    DRAFT = "draft"  # Draft invoice
    PENDING = "pending"  # Pending sending
    SENT = "sent"  # Sent to customer
    VIEWED = "viewed"  # Customer viewed the invoice
    PARTIALLY_PAID = "partially_paid"  # Partial payment received
    PAID = "paid"  # Fully paid
    OVERDUE = "overdue"  # Payment overdue
    CANCELLED = "cancelled"  # Invoice cancelled
    VOID = "void"  # Voided invoice
    REFUNDED = "refunded"  # Refunded


class ReminderType(str, PyEnum):
    """Payment reminder types"""
    FRIENDLY = "friendly"  # Friendly reminder before due date
    FIRST = "first"  # First reminder after due date
    SECOND = "second"  # Second reminder
    FINAL = "final"  # Final notice
    LEGAL = "legal"  # Legal action notice


class CreditNoteReason(str, PyEnum):
    """Credit note reason types"""
    PRODUCT_RETURN = "product_return"
    DAMAGED_GOODS = "damaged_goods"
    PRICING_ERROR = "pricing_error"
    DISCOUNT_ADJUSTMENT = "discount_adjustment"
    SERVICE_ISSUE = "service_issue"
    CANCELLATION = "cancellation"
    GOODWILL = "goodwill"
    OTHER = "other"


class PaymentGateway(str, PyEnum):
    """Payment gateway/processor"""
    RAZORPAY = "razorpay"  # Razorpay (India)
    STRIPE = "stripe"  # Stripe (International)
    PAYPAL = "paypal"  # PayPal
    BANK_TRANSFER = "bank_transfer"  # Direct bank transfer
    CASH = "cash"  # Cash payment
    CHECK = "check"  # Check payment
    UPI = "upi"  # UPI payment (India)
    CREDIT_CARD = "credit_card"  # Direct credit card
    DEBIT_CARD = "debit_card"  # Direct debit card
    NET_BANKING = "net_banking"  # Net banking
    WALLET = "wallet"  # Digital wallet
    OTHER = "other"  # Other payment method


class PaymentRecordStatus(str, PyEnum):
    """Payment record status"""
    PENDING = "pending"  # Payment initiated
    PROCESSING = "processing"  # Being processed
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Refunded
    PARTIALLY_REFUNDED = "partially_refunded"  # Partially refunded
    CANCELLED = "cancelled"  # Cancelled


class BillStatus(str, PyEnum):
    """Bill (Accounts Payable) status"""
    DRAFT = "draft"  # Draft bill
    PENDING = "pending"  # Pending approval
    APPROVED = "approved"  # Approved for payment
    PARTIALLY_PAID = "partially_paid"  # Partially paid
    PAID = "paid"  # Fully paid
    OVERDUE = "overdue"  # Payment overdue
    CANCELLED = "cancelled"  # Cancelled


class ExpenseCategory(str, PyEnum):
    """Expense categories"""
    INVENTORY = "inventory"  # Inventory/stock purchase
    RENT = "rent"  # Rent
    UTILITIES = "utilities"  # Electricity, water, internet
    SALARIES = "salaries"  # Employee salaries
    MARKETING = "marketing"  # Marketing expenses
    SHIPPING = "shipping"  # Shipping/logistics
    OFFICE_SUPPLIES = "office_supplies"  # Office supplies
    EQUIPMENT = "equipment"  # Equipment purchase
    MAINTENANCE = "maintenance"  # Maintenance/repairs
    INSURANCE = "insurance"  # Insurance
    TAXES = "taxes"  # Tax payments
    PROFESSIONAL_FEES = "professional_fees"  # Legal, accounting fees
    TRAVEL = "travel"  # Travel expenses
    OTHER = "other"  # Other expenses


class Invoice(Base):
    """
    Invoice Model - Accounts Receivable
    
    Tracks invoices sent to customers for payment. Linked to orders
    and supports partial payments, aging reports, and payment reminders.
    """
    __tablename__ = "invoices"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Invoice Identification
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Related Order
    order_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Customer (B2B or B2C)
    wholesale_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )
    
    retail_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_customers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )
    
    # Customer snapshot (at time of invoice)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20))
    customer_tax_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Billing Address (detailed fields)
    billing_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    billing_city: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_state: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    
    # Invoice Status
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, length=50),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        index=True
    )
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        index=True
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    balance_due: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Credit Notes Applied
    credit_applied: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Tax Details
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))  # Percentage
    
    # Dates
    invoice_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    due_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    paid_date: Mapped[Optional[datetime]] = mapped_column(Date)
    
    # Payment Terms
    payment_terms: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="NET_30"
    )
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    
    # Communication & Reminders
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reminders_sent: Mapped[int] = mapped_column(Integer, default=0)
    
    # Flags
    is_overdue_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Metadata
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Audit Fields
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
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
    order: Mapped["Order"] = relationship("Order", back_populates="invoices")
    
    wholesale_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        foreign_keys=[wholesale_customer_id]
    )
    
    retail_customer: Mapped[Optional["RetailCustomer"]] = relationship(
        "RetailCustomer",
        foreign_keys=[retail_customer_id]
    )
    
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    
    items: Mapped[list["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    
    payments: Mapped[list["PaymentRecord"]] = relationship(
        "PaymentRecord",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    
    credit_notes: Mapped[list["CreditNote"]] = relationship(
        "CreditNote",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    
    reminders: Mapped[list["PaymentReminder"]] = relationship(
        "PaymentReminder",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_invoices_customer_wholesale", "wholesale_customer_id", "status"),
        Index("ix_invoices_customer_retail", "retail_customer_id", "status"),
        Index("ix_invoices_dates", "invoice_date", "due_date"),
        Index("ix_invoices_overdue", "is_overdue_flag", "status"),
        Index("ix_invoices_created_at", "created_at"),
        CheckConstraint("subtotal >= 0", name="check_invoice_subtotal_positive"),
        CheckConstraint("total_amount >= 0", name="check_invoice_total_positive"),
        CheckConstraint("paid_amount >= 0", name="check_invoice_paid_positive"),
        CheckConstraint(
            "(wholesale_customer_id IS NOT NULL) OR (retail_customer_id IS NOT NULL)",
            name="check_invoice_has_customer"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}: {self.total_amount} ({self.status})>"
    
    @property
    def is_fully_paid(self) -> bool:
        """Check if invoice is fully paid"""
        return self.balance_due <= Decimal("0.00")
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        if self.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.REFUNDED, InvoiceStatus.VOID]:
            return False
        from datetime import date
        return date.today() > self.due_date
    
    @property
    def days_overdue(self) -> int:
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        from datetime import date
        return (date.today() - self.due_date).days
    
    @property
    def aging_bucket(self) -> str:
        """Get aging bucket (Current, 1-30, 31-60, 61-90, 90+)"""
        if not self.is_overdue:
            return "Current"
        days = self.days_overdue
        if days <= 30:
            return "1-30 days"
        elif days <= 60:
            return "31-60 days"
        elif days <= 90:
            return "61-90 days"
        else:
            return "90+ days"


class InvoiceItem(Base):
    """
    Invoice Line Item Model
    
    Individual items on an invoice with pricing and tax details.
    """
    __tablename__ = "invoice_items"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Key
    invoice_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Item Details
    item_description: Mapped[str] = mapped_column(String(500), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Discounts
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Tax
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Total
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="items"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_invoice_items_invoice", "invoice_id"),
        CheckConstraint("quantity > 0", name="check_invoice_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_invoice_item_price_positive"),
    )
    
    def __repr__(self) -> str:
        return f"<InvoiceItem(id={self.id}, description={self.item_description})>"


class PaymentRecord(Base):
    """
    Payment Record - Tracks all payment transactions
    
    Records payments made against invoices, including payment gateway
    details, reconciliation, and refunds.
    """
    __tablename__ = "payment_records"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Payment Identification
    payment_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Related Invoice
    invoice_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Customer References (for easier queries)
    wholesale_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    retail_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Payment Details
    payment_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True,
        default=datetime.utcnow
    )
    
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    
    # Payment Gateway
    payment_gateway: Mapped[PaymentGateway] = mapped_column(
        Enum(PaymentGateway, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    
    # Status
    status: Mapped[PaymentRecordStatus] = mapped_column(
        Enum(PaymentRecordStatus, native_enum=False, length=50),
        nullable=False,
        default=PaymentRecordStatus.PENDING,
        index=True
    )
    
    # Gateway Transaction Details
    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        index=True
    )  # Transaction ID from payment gateway
    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    gateway_order_id: Mapped[Optional[str]] = mapped_column(String(255))
    gateway_response: Mapped[Optional[dict]] = mapped_column(JSON)  # Full gateway response
    
    # Payment Method Details
    payment_method_type: Mapped[Optional[str]] = mapped_column(String(50))  # card, netbanking, upi, etc.
    payment_method_details: Mapped[Optional[dict]] = mapped_column(JSON)  # Card last 4 digits, etc.
    
    # Reconciliation
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reconciled_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Refund Details (if refunded)
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    refund_transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    refund_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Fees & Charges
    gateway_fee: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )  # Fee charged by payment gateway
    
    # Additional Transaction Details
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(255))
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    bank_account_last4: Mapped[Optional[str]] = mapped_column(String(4))
    cheque_number: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)  # Internal use only
    reference_number: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Additional Data
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Audit Fields
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
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
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")
    
    wholesale_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        foreign_keys=[wholesale_customer_id]
    )
    
    retail_customer: Mapped[Optional["RetailCustomer"]] = relationship(
        "RetailCustomer",
        foreign_keys=[retail_customer_id]
    )
    
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    
    reconciled_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reconciled_by_id]
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_payments_customer_wholesale", "wholesale_customer_id", "status"),
        Index("ix_payments_customer_retail", "retail_customer_id", "status"),
        Index("ix_payments_reconciliation", "is_reconciled", "payment_date"),
        Index("idx_payment_invoice_status", "invoice_id", "status"),
        Index("idx_payment_gateway_txn", "gateway_transaction_id"),
        Index("idx_payment_date", "payment_date"),
        Index("idx_payment_reconciled", "is_reconciled"),
        CheckConstraint("amount > 0", name="check_payment_amount_positive"),
    )
    
    def __repr__(self) -> str:
        return f"<PaymentRecord {self.payment_number}: {self.amount} via {self.payment_gateway}>"


class CreditNote(Base):
    """
    Credit Note - For refunds and adjustments
    
    Issued when goods are returned or there's a price adjustment.
    Reduces the amount owed by the customer.
    """
    __tablename__ = "credit_notes"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Credit Note Identification
    credit_note_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Related Invoice
    invoice_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Customer References
    wholesale_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wholesale_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    retail_customer_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retail_customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Credit Note Details
    issue_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    reason: Mapped[CreditNoteReason] = mapped_column(
        Enum(CreditNoteReason, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    
    # Financial Details
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    amount_used: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    amount_remaining: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Status
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(Date)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Audit Fields
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    approved_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
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
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="credit_notes")
    
    wholesale_customer: Mapped[Optional["WholesaleCustomer"]] = relationship(
        "WholesaleCustomer",
        foreign_keys=[wholesale_customer_id]
    )
    
    retail_customer: Mapped[Optional["RetailCustomer"]] = relationship(
        "RetailCustomer",
        foreign_keys=[retail_customer_id]
    )
    
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    
    approved_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_credit_notes_customer_wholesale", "wholesale_customer_id", "is_applied"),
        Index("ix_credit_notes_customer_retail", "retail_customer_id", "is_applied"),
        Index("ix_credit_notes_status", "is_applied", "is_expired"),
        Index("idx_credit_note_invoice", "invoice_id"),
        Index("idx_credit_note_date", "issue_date"),
        CheckConstraint("total_amount > 0", name="check_credit_note_amount_positive"),
    )
    
    def __repr__(self) -> str:
        return f"<CreditNote {self.credit_note_number}: {self.total_amount}>"
    
    @property
    def is_fully_used(self) -> bool:
        """Check if credit note is fully used"""
        return self.amount_remaining <= Decimal("0.00")


class Bill(Base):
    """
    Bill Model - Accounts Payable
    
    Tracks bills from suppliers and other vendors that need to be paid.
    """
    __tablename__ = "bills"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Bill Identification
    bill_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    supplier_bill_number: Mapped[Optional[str]] = mapped_column(String(100))  # Supplier's invoice number
    
    # Supplier
    supplier_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Bill Details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    
    # Status
    status: Mapped[BillStatus] = mapped_column(
        Enum(BillStatus, native_enum=False, length=50),
        nullable=False,
        default=BillStatus.DRAFT,
        index=True
    )
    
    # Amounts
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    balance_due: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Dates
    bill_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    due_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    paid_date: Mapped[Optional[datetime]] = mapped_column(Date)
    
    # Payment Terms
    payment_terms: Mapped[str] = mapped_column(String(50), nullable=False, default="NET_30")
    
    # Approval
    approved_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Attachments (PDFs, images of bills)
    attachments: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    
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
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier")
    approved_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    payments: Mapped[list["VendorPayment"]] = relationship(
        "VendorPayment",
        back_populates="bill",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_bill_supplier_status", "supplier_id", "status"),
        Index("idx_bill_due_date_status", "due_date", "status"),
        Index("idx_bill_category", "category"),
        CheckConstraint("subtotal >= 0", name="check_bill_subtotal_positive"),
        CheckConstraint("total_amount >= 0", name="check_bill_total_positive"),
    )
    
    def __repr__(self) -> str:
        return f"<Bill {self.bill_number}: {self.total_amount} ({self.status})>"


class VendorPayment(Base):
    """
    Vendor Payment - Payments made to suppliers
    
    Tracks all payments made against bills.
    """
    __tablename__ = "vendor_payments"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Payment Identification
    payment_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Related Bill
    bill_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Payment Details
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # BANK_TRANSFER, CHECK, CASH, etc.
    
    # Bank/Transaction Details
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(255))
    bank_account: Mapped[Optional[str]] = mapped_column(String(100))
    check_number: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Status
    status: Mapped[PaymentRecordStatus] = mapped_column(
        Enum(PaymentRecordStatus, native_enum=False, length=50),
        nullable=False,
        default=PaymentRecordStatus.PENDING,
        index=True
    )
    
    # Dates
    payment_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relationships
    bill: Mapped["Bill"] = relationship("Bill", back_populates="payments")
    created_by: Mapped[Optional["User"]] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("idx_vendor_payment_bill", "bill_id"),
        Index("idx_vendor_payment_date", "payment_date"),
        CheckConstraint("amount > 0", name="check_vendor_payment_amount_positive"),
    )
    
    def __repr__(self) -> str:
        return f"<VendorPayment {self.payment_number}: {self.amount}>"


class PaymentReminder(Base):
    """
    Payment Reminder Model
    
    Tracks payment reminders sent to customers for overdue invoices.
    Supports escalation workflow (friendly -> first -> second -> final -> legal).
    """
    __tablename__ = "payment_reminders"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Key
    invoice_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Reminder Details
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    days_overdue: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Communication Details
    sent_to_email: Mapped[Optional[str]] = mapped_column(String(255))
    sent_to_phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sms_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Message Content
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Response Tracking
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    customer_response: Mapped[Optional[str]] = mapped_column(Text)
    
    # Audit Fields
    created_by_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="reminders"
    )
    
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id]
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_payment_reminders_invoice_type", "invoice_id", "reminder_type"),
        Index("ix_payment_reminders_sent", "sent_at", "reminder_type"),
    )
    
    def __repr__(self) -> str:
        return f"<PaymentReminder(id={self.id}, type={self.reminder_type}, days_overdue={self.days_overdue})>"
