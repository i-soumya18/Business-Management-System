"""
Inventory Management Models

Models for inventory tracking, stock locations, movements, adjustments, and alerts.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, String, Text, UUID, Numeric, Integer, ForeignKey, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import ProductVariant
    from app.models.user import User


class MovementType(str, PyEnum):
    """Inventory Movement Types"""
    PURCHASE = "purchase"  # Stock received from supplier
    SALE = "sale"  # Stock sold to customer
    TRANSFER = "transfer"  # Transfer between locations
    ADJUSTMENT = "adjustment"  # Stock adjustment (count correction)
    RETURN = "return"  # Customer return
    RETURN_TO_SUPPLIER = "return_to_supplier"  # Return to supplier
    DAMAGE = "damage"  # Damaged goods
    LOSS = "loss"  # Lost/stolen items
    PRODUCTION = "production"  # Manufactured goods
    CONSUMPTION = "consumption"  # Used in production


class StockLocation(Base):
    """Stock Location Model
    
    Represents physical locations where inventory is stored
    (warehouses, stores, distribution centers, etc.)
    """
    
    __tablename__ = "stock_locations"
    
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
    location_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # warehouse, store, dc
    
    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    
    # Contact
    contact_person: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # For fulfillment order
    
    # Capacity
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max items capacity
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    inventory_levels: Mapped[list["InventoryLevel"]] = relationship(
        "InventoryLevel",
        back_populates="location",
        cascade="all, delete-orphan"
    )
    movements_from: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        foreign_keys="[InventoryMovement.from_location_id]",
        back_populates="from_location"
    )
    movements_to: Mapped[list["InventoryMovement"]] = relationship(
        "InventoryMovement",
        foreign_keys="[InventoryMovement.to_location_id]",
        back_populates="to_location"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_locations_code_active", "code", "is_active"),
        Index("ix_locations_type_active", "location_type", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<StockLocation(id={self.id}, name='{self.name}', code='{self.code}')>"


class InventoryLevel(Base):
    """Inventory Level Model
    
    Tracks current stock quantity for each product variant at each location.
    Real-time inventory tracking with reserved quantities.
    """
    
    __tablename__ = "inventory_levels"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    product_variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Quantities
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Physical stock
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Reserved for orders
    quantity_available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # on_hand - reserved
    
    # Reorder Settings
    reorder_point: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Min quantity before reorder
    reorder_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Quantity to reorder
    max_stock_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max quantity to maintain
    
    # Timestamps
    last_counted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="inventory_levels")
    location: Mapped["StockLocation"] = relationship("StockLocation", back_populates="inventory_levels")
    
    # Indexes
    __table_args__ = (
        Index("ix_inventory_variant_location", "product_variant_id", "location_id", unique=True),
        Index("ix_inventory_available", "quantity_available"),
        Index("ix_inventory_low_stock", "quantity_available", "reorder_point"),
    )
    
    def __repr__(self) -> str:
        return f"<InventoryLevel(variant_id={self.product_variant_id}, location_id={self.location_id}, available={self.quantity_available})>"
    
    def is_low_stock(self) -> bool:
        """Check if stock is below reorder point"""
        if self.reorder_point is not None:
            return self.quantity_available <= self.reorder_point
        return False


class InventoryMovement(Base):
    """Inventory Movement Model
    
    Records all inventory transactions (purchases, sales, transfers, adjustments).
    Complete audit trail for stock movements.
    """
    
    __tablename__ = "inventory_movements"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    product_variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    from_location_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    to_location_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Movement Details
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Reference
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # order, purchase_order, etc.
    reference_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # For adjustments/damages
    
    # User tracking
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamp
    movement_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="inventory_movements")
    from_location: Mapped[Optional["StockLocation"]] = relationship(
        "StockLocation",
        foreign_keys=[from_location_id],
        back_populates="movements_from"
    )
    to_location: Mapped[Optional["StockLocation"]] = relationship(
        "StockLocation",
        foreign_keys=[to_location_id],
        back_populates="movements_to"
    )
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    
    # Indexes
    __table_args__ = (
        Index("ix_movements_variant_date", "product_variant_id", "movement_date"),
        Index("ix_movements_type_date", "movement_type", "movement_date"),
        Index("ix_movements_reference", "reference_type", "reference_id"),
    )
    
    def __repr__(self) -> str:
        return f"<InventoryMovement(id={self.id}, type={self.movement_type}, quantity={self.quantity})>"


class StockAdjustment(Base):
    """Stock Adjustment Model
    
    Records manual inventory adjustments and physical counts.
    Used for cycle counting and reconciliation.
    """
    
    __tablename__ = "stock_adjustments"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    location_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Adjustment Details
    adjustment_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Quantities
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    adjustment_quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # actual - expected
    
    # Cost Impact
    unit_cost: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_cost_impact: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # User tracking
    adjusted_by_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)  # pending, approved, rejected
    
    # Timestamps
    adjustment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    location: Mapped["StockLocation"] = relationship("StockLocation")
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    adjusted_by: Mapped["User"] = relationship("User", foreign_keys=[adjusted_by_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    
    # Indexes
    __table_args__ = (
        Index("ix_adjustments_location_date", "location_id", "adjustment_date"),
        Index("ix_adjustments_variant_date", "product_variant_id", "adjustment_date"),
        Index("ix_adjustments_status", "status", "adjustment_date"),
    )
    
    def __repr__(self) -> str:
        return f"<StockAdjustment(id={self.id}, number='{self.adjustment_number}', quantity={self.adjustment_quantity})>"


class LowStockAlert(Base):
    """Low Stock Alert Model
    
    Tracks products that have fallen below reorder point.
    Helps with proactive inventory replenishment.
    """
    
    __tablename__ = "low_stock_alerts"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    product_variant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    location_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Alert Details
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_order_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)  # active, resolved, ignored
    
    # Resolution
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    alert_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    product_variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    location: Mapped["StockLocation"] = relationship("StockLocation")
    resolved_by: Mapped[Optional["User"]] = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index("ix_alerts_variant_location", "product_variant_id", "location_id"),
        Index("ix_alerts_status_date", "status", "alert_date"),
    )
    
    def __repr__(self) -> str:
        return f"<LowStockAlert(id={self.id}, variant_id={self.product_variant_id}, current={self.current_quantity})>"
