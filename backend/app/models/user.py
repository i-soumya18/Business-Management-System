"""
User model for authentication and user management
"""
from sqlalchemy import Column, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.models.base import BaseModel


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)


class User(BaseModel):
    """
    User model for authentication and authorization
    """
    __tablename__ = "users"
    
    # Basic Information
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    last_login = Column(DateTime(timezone=True), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password Reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    roles = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin"
    )
    
    orders = relationship(
        "Order",
        back_populates="customer",
        foreign_keys="[Order.customer_id]"
    )
    
    wholesale_customers = relationship(
        "WholesaleCustomer",
        back_populates="sales_rep",
        foreign_keys="[WholesaleCustomer.sales_rep_id]"
    )
    
    cashier_shifts = relationship(
        "CashierShift",
        back_populates="cashier",
        foreign_keys="[CashierShift.cashier_id]"
    )
    
    shopping_carts = relationship(
        "ShoppingCart",
        back_populates="user"
    )
    
    wishlists = relationship(
        "Wishlist",
        back_populates="user"
    )
    
    # CRM relationships
    assigned_leads = relationship(
        "Lead",
        back_populates="assigned_to",
        foreign_keys="[Lead.assigned_to_id]"
    )
    
    owned_opportunities = relationship(
        "SalesOpportunity",
        back_populates="owner",
        foreign_keys="[SalesOpportunity.owner_id]"
    )
    
    retail_customer = relationship(
        "RetailCustomer",
        back_populates="user",
        uselist=False
    )
    
    def __repr__(self):
        return f"<User {self.email}>"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        for role in self.roles:
            if any(perm.name == permission_name for perm in role.permissions):
                return True
        return False
