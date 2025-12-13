"""
Category Model

Hierarchical category structure for product organization.
Supports unlimited nesting levels for flexible categorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, UUID, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base):
    """Product Category Model
    
    Supports hierarchical category structure (e.g., Clothing > Men's > Shirts > Casual Shirts).
    Each category can have multiple subcategories and products.
    """
    
    __tablename__ = "categories"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Hierarchy
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Display & SEO
    display_order: Mapped[int] = mapped_column(default=0, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
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
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        back_populates="subcategories"
    )
    subcategories: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category",
        lazy="dynamic"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_categories_parent_active", "parent_id", "is_active"),
        Index("ix_categories_slug_active", "slug", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', parent_id={self.parent_id})>"
    
    def get_full_path(self) -> str:
        """Get full category path (e.g., 'Clothing > Men's > Shirts')"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " > ".join(path)
    
    def get_level(self) -> int:
        """Get category level (0 for root, 1 for first level, etc.)"""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level
