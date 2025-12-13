"""
Supplier Model

Represents suppliers/vendors for inventory procurement.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, UUID, Numeric, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Supplier(Base):
    """Supplier Model
    
    Stores supplier/vendor information for procurement management.
    Tracks supplier performance and payment terms.
    """
    
    __tablename__ = "suppliers"
    
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
    
    # Contact Information
    contact_person: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    
    # Business Information
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # GST/VAT number
    business_registration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Payment Terms
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "Net 30"
    credit_limit: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Performance Metrics
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)  # 0.00 to 5.00
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_time_delivery_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # percentage
    
    # Lead Time
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
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
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="supplier",
        lazy="dynamic"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_suppliers_code_active", "code", "is_active"),
        Index("ix_suppliers_name_active", "name", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}', code='{self.code}')>"
