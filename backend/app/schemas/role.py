"""
Role and Permission schemas for API requests and responses
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime


class PermissionBase(BaseModel):
    """Base permission schema"""
    name: str = Field(..., max_length=100)
    resource: str = Field(..., max_length=50)
    action: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)


class PermissionCreate(PermissionBase):
    """Schema for creating a permission"""
    pass


class PermissionResponse(PermissionBase):
    """Schema for permission response"""
    id: UUID4
    created_at: datetime
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base role schema"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class RoleCreate(RoleBase):
    """Schema for creating a role"""
    permission_ids: List[UUID4] = []


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Schema for role response"""
    id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Schema for role with permissions"""
    permissions: List[PermissionResponse] = []
    
    class Config:
        from_attributes = True
