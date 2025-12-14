"""
Order Management Extensions

Additional models for order history, notes, fulfillment, and tracking.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from enum import Enum as PyEnum

from sqlalchemy import DateTime, String, Text, UUID, ForeignKey, Index, Enum, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class OrderHistoryAction(str, PyEnum):
    """Order History Action Types"""
    CREATED = "created"
    CONFIRMED = "confirmed"
    PAYMENT_RECEIVED = "payment_received"
    PROCESSING_STARTED = "processing_started"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    STATUS_CHANGED = "status_changed"
    NOTE_ADDED = "note_added"
    PAYMENT_FAILED = "payment_failed"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"
    EDITED = "edited"
    ASSIGNED = "assigned"
    INVENTORY_RESERVED = "inventory_reserved"
    INVENTORY_RELEASED = "inventory_released"


class FulfillmentStatus(str, PyEnum):
    """Fulfillment Status"""
    PENDING = "pending"
    PICKING = "picking"
    PACKING = "packing"
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class OrderHistory(Base):
    """Order History Model
    
    Tracks all changes and actions performed on an order for audit trail.
    """
    
    __tablename__ = "order_history"
    
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
    
    # Action Details
    action: Mapped[OrderHistoryAction] = mapped_column(
        Enum(OrderHistoryAction),
        nullable=False,
        index=True
    )
    
    # Status Transition (if applicable)
    old_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # User who performed the action
    performed_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Additional Data (JSON for flexibility)
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # IP Address and User Agent (for security audit)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="history")
    performed_by: Mapped[Optional["User"]] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_order_history_order_date', 'order_id', 'created_at'),
        Index('idx_order_history_action', 'action'),
    )
    
    def __repr__(self):
        return f"<OrderHistory {self.order_id} - {self.action.value}>"


class OrderNote(Base):
    """Order Note Model
    
    Stores notes and comments on orders for internal communication.
    """
    
    __tablename__ = "order_notes"
    
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
    
    # Note Content
    note: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Visibility
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )  # True = internal only, False = visible to customer
    
    # Customer Notification
    notify_customer: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Created By
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="notes")
    created_by: Mapped[Optional["User"]] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_order_note_order_date', 'order_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<OrderNote {self.order_id} - {'Internal' if self.is_internal else 'Customer'}>"


class OrderFulfillment(Base):
    """Order Fulfillment Model
    
    Tracks the fulfillment process for orders including picking, packing, and shipping.
    """
    
    __tablename__ = "order_fulfillments"
    
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
    
    # Fulfillment Number
    fulfillment_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Status
    status: Mapped[FulfillmentStatus] = mapped_column(
        Enum(FulfillmentStatus),
        default=FulfillmentStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Location
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Assigned To
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Fulfillment Items (JSON array of item IDs and quantities)
    items: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Packing Details
    box_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(String(20), nullable=True)
    packing_materials: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Notes
    picking_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    packing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    picking_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    picking_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    packing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    packing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
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
    order: Mapped["Order"] = relationship("Order", back_populates="fulfillments")
    assigned_to: Mapped[Optional["User"]] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_fulfillment_order', 'order_id'),
        Index('idx_fulfillment_status', 'status'),
        Index('idx_fulfillment_assigned', 'assigned_to_id'),
    )
    
    def __repr__(self):
        return f"<OrderFulfillment {self.fulfillment_number} - {self.status.value}>"


class InventoryReservation(Base):
    """Inventory Reservation Model
    
    Tracks inventory reserved for orders to prevent overselling.
    """
    
    __tablename__ = "inventory_reservations"
    
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
    
    order_item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    product_variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    stock_location_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Reservation Details
    quantity_reserved: Mapped[int] = mapped_column(String(20), nullable=False)
    quantity_fulfilled: Mapped[int] = mapped_column(String(20), default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
    # Expiry
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
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
    order: Mapped["Order"] = relationship("Order", back_populates="inventory_reservations")
    
    # Indexes
    __table_args__ = (
        Index('idx_reservation_order', 'order_id'),
        Index('idx_reservation_variant', 'product_variant_id'),
        Index('idx_reservation_active', 'is_active', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<InventoryReservation Order:{self.order_id} Qty:{self.quantity_reserved}>"
    
    @property
    def quantity_remaining(self) -> int:
        """Get remaining quantity to fulfill"""
        return self.quantity_reserved - self.quantity_fulfilled
