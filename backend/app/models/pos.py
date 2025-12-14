"""
Point of Sale (POS) Models

Models for retail POS operations including cashier shifts, cash drawer management,
POS sessions, and return/exchange tracking.
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
    from app.models.order import Order


class ShiftStatus(str, PyEnum):
    """Cashier Shift Status"""
    ACTIVE = "active"  # Shift is currently active
    CLOSED = "closed"  # Shift has been closed
    RECONCILED = "reconciled"  # Shift has been reconciled


class CashDrawerStatus(str, PyEnum):
    """Cash Drawer Status"""
    OPEN = "open"  # Drawer is open and accepting transactions
    CLOSED = "closed"  # Drawer is closed
    BALANCED = "balanced"  # Drawer has been balanced/reconciled
    OVER = "over"  # Drawer has more cash than expected
    SHORT = "short"  # Drawer has less cash than expected


class POSTransactionType(str, PyEnum):
    """POS Transaction Type"""
    SALE = "sale"  # Regular sale
    RETURN = "return"  # Product return
    EXCHANGE = "exchange"  # Product exchange
    REFUND = "refund"  # Cash refund
    PAYOUT = "payout"  # Cash payout (petty cash, etc.)
    CASH_IN = "cash_in"  # Cash added to drawer
    CASH_OUT = "cash_out"  # Cash removed from drawer


class ReturnReason(str, PyEnum):
    """Return/Exchange Reason"""
    DEFECTIVE = "defective"  # Product is defective
    WRONG_SIZE = "wrong_size"  # Wrong size
    WRONG_COLOR = "wrong_color"  # Wrong color
    CHANGED_MIND = "changed_mind"  # Customer changed mind
    NOT_AS_EXPECTED = "not_as_expected"  # Not as expected
    DAMAGED = "damaged"  # Damaged during shipping/handling
    OTHER = "other"  # Other reason


class CashierShift(Base):
    """
    Cashier Shift Model
    
    Tracks individual cashier shifts including opening/closing times,
    cash drawer status, and shift performance metrics.
    """
    __tablename__ = "cashier_shifts"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Shift Information
    shift_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    cashier_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True
    )
    register_number: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Status
    status: Mapped[ShiftStatus] = mapped_column(
        Enum(ShiftStatus, native_enum=False, length=50),
        nullable=False,
        default=ShiftStatus.ACTIVE
    )
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Cash Management
    opening_cash: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    closing_cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    expected_cash: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    cash_variance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Sales Summary
    total_transactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sales: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    total_returns: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    total_exchanges: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Payment Method Breakdown
    cash_sales: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    card_sales: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    upi_sales: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    other_sales: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Notes
    opening_notes: Mapped[Optional[str]] = mapped_column(Text)
    closing_notes: Mapped[Optional[str]] = mapped_column(Text)
    reconciliation_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional Data
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
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
    cashier: Mapped["User"] = relationship(
        "User",
        foreign_keys=[cashier_id],
        back_populates="cashier_shifts"
    )
    cash_drawer: Mapped[Optional["CashDrawer"]] = relationship(
        "CashDrawer",
        back_populates="shift",
        uselist=False,
        cascade="all, delete-orphan"
    )
    pos_transactions: Mapped[List["POSTransaction"]] = relationship(
        "POSTransaction",
        back_populates="shift",
        cascade="all, delete-orphan"
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("opening_cash >= 0", name="check_opening_cash_positive"),
        CheckConstraint("closing_cash IS NULL OR closing_cash >= 0", name="check_closing_cash_positive"),
        Index("idx_cashier_shift_cashier", "cashier_id"),
        Index("idx_cashier_shift_status", "status"),
        Index("idx_cashier_shift_date", "started_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CashierShift(id={self.id}, shift_number={self.shift_number}, cashier_id={self.cashier_id})>"
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate shift duration in minutes"""
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds() / 60)
        return None
    
    def calculate_expected_cash(self) -> Decimal:
        """Calculate expected cash in drawer"""
        return self.opening_cash + self.cash_sales - self.total_returns
    
    def close_shift(self, closing_cash: Decimal) -> None:
        """Close the shift and calculate variance"""
        self.ended_at = datetime.utcnow()
        self.closing_cash = closing_cash
        self.expected_cash = self.calculate_expected_cash()
        self.cash_variance = closing_cash - self.expected_cash
        self.status = ShiftStatus.CLOSED


class CashDrawer(Base):
    """
    Cash Drawer Model
    
    Tracks cash drawer transactions and balance throughout a shift.
    """
    __tablename__ = "cash_drawers"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Shift Reference
    shift_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cashier_shifts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Status
    status: Mapped[CashDrawerStatus] = mapped_column(
        Enum(CashDrawerStatus, native_enum=False, length=50),
        nullable=False,
        default=CashDrawerStatus.OPEN
    )
    
    # Cash Tracking
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Denomination Breakdown (in JSON for flexibility)
    denomination_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Last Transaction
    last_transaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
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
    shift: Mapped["CashierShift"] = relationship(
        "CashierShift",
        back_populates="cash_drawer"
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("current_balance >= 0", name="check_drawer_balance_positive"),
        Index("idx_cash_drawer_shift", "shift_id"),
        Index("idx_cash_drawer_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<CashDrawer(id={self.id}, shift_id={self.shift_id}, balance={self.current_balance})>"


class POSTransaction(Base):
    """
    POS Transaction Model
    
    Records all POS transactions including sales, returns, exchanges, and cash movements.
    """
    __tablename__ = "pos_transactions"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Transaction Information
    transaction_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    transaction_type: Mapped[POSTransactionType] = mapped_column(
        Enum(POSTransactionType, native_enum=False, length=50),
        nullable=False
    )
    
    # References
    shift_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cashier_shifts.id", ondelete="SET NULL"),
        nullable=False,
        index=True
    )
    order_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True
    )
    original_order_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True
    )  # For returns/exchanges
    
    # Transaction Details
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Customer Information
    customer_name: Mapped[Optional[str]] = mapped_column(String(200))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20))
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Receipt Information
    receipt_number: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    receipt_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamp
    transaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Relationships
    shift: Mapped["CashierShift"] = relationship(
        "CashierShift",
        foreign_keys=[shift_id],
        back_populates="pos_transactions"
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id]
    )
    original_order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[original_order_id]
    )
    
    # Table Constraints
    __table_args__ = (
        Index("idx_pos_transaction_shift", "shift_id"),
        Index("idx_pos_transaction_type", "transaction_type"),
        Index("idx_pos_transaction_date", "transaction_at"),
    )
    
    def __repr__(self) -> str:
        return f"<POSTransaction(id={self.id}, transaction_number={self.transaction_number}, type={self.transaction_type})>"


class ReturnExchange(Base):
    """
    Return/Exchange Model
    
    Tracks product returns and exchanges with reasons and restocking information.
    """
    __tablename__ = "return_exchanges"
    
    # Primary Key
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Return/Exchange Number
    return_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Type
    is_exchange: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Original Order Reference
    original_order_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # New Order (for exchanges)
    new_order_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True
    )
    
    # POS Transaction
    pos_transaction_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pos_transactions.id", ondelete="SET NULL"),
        index=True
    )
    
    # Return Details
    reason: Mapped[ReturnReason] = mapped_column(
        Enum(ReturnReason, native_enum=False, length=50),
        nullable=False
    )
    reason_description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Financial
    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    restocking_fee: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    # Processing
    processed_by_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    restocked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Items Details (stored as JSON for flexibility)
    returned_items: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    returned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    original_order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[original_order_id]
    )
    new_order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[new_order_id]
    )
    pos_transaction: Mapped[Optional["POSTransaction"]] = relationship(
        "POSTransaction",
        foreign_keys=[pos_transaction_id]
    )
    processed_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[processed_by_id]
    )
    
    # Table Constraints
    __table_args__ = (
        CheckConstraint("refund_amount >= 0", name="check_refund_amount_positive"),
        CheckConstraint("restocking_fee >= 0", name="check_restocking_fee_positive"),
        Index("idx_return_exchange_original_order", "original_order_id"),
        Index("idx_return_exchange_date", "returned_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ReturnExchange(id={self.id}, return_number={self.return_number})>"
