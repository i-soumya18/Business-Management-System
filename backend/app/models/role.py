"""
Role and Permission models for RBAC (Role-Based Access Control)
"""
from sqlalchemy import Column, String, Text, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel
from app.models.user import user_roles


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)


class Role(BaseModel):
    """
    Role model for RBAC
    """
    __tablename__ = "roles"
    
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin"
    )
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin"
    )
    
    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(BaseModel):
    """
    Permission model for fine-grained access control
    """
    __tablename__ = "permissions"
    
    name = Column(String(100), unique=True, index=True, nullable=False)
    resource = Column(String(50), nullable=False, index=True)  # e.g., 'inventory', 'orders'
    action = Column(String(50), nullable=False, index=True)  # e.g., 'create', 'read', 'update', 'delete'
    description = Column(Text, nullable=True)
    
    # Relationships
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin"
    )
    
    def __repr__(self):
        return f"<Permission {self.name}>"
    
    @classmethod
    def create_name(cls, resource: str, action: str) -> str:
        """Create permission name from resource and action"""
        return f"{resource}:{action}"
