"""
Role repository for database operations
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.role import Role, Permission


class RoleRepository:
    """
    Repository for Role model database operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, role_data: dict) -> Role:
        """Create a new role"""
        role = Role(**role_data)
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role
    
    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID"""
        query = select(Role).where(Role.id == role_id).options(
            selectinload(Role.permissions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name"""
        query = select(Role).where(Role.name == name).options(
            selectinload(Role.permissions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Role]:
        """Get all roles"""
        query = select(Role).options(selectinload(Role.permissions))
        
        if is_active is not None:
            query = query.where(Role.is_active == is_active)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, role: Role, update_data: dict) -> Role:
        """Update role"""
        for key, value in update_data.items():
            if value is not None:
                setattr(role, key, value)
        
        await self.db.commit()
        await self.db.refresh(role)
        return role
    
    async def delete(self, role: Role) -> bool:
        """Delete role"""
        await self.db.delete(role)
        await self.db.commit()
        return True
    
    async def add_permission(self, role: Role, permission: Permission) -> Role:
        """Add permission to role"""
        if permission not in role.permissions:
            role.permissions.append(permission)
            await self.db.commit()
            await self.db.refresh(role)
        return role
    
    async def remove_permission(self, role: Role, permission: Permission) -> Role:
        """Remove permission from role"""
        if permission in role.permissions:
            role.permissions.remove(permission)
            await self.db.commit()
            await self.db.refresh(role)
        return role


class PermissionRepository:
    """
    Repository for Permission model database operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, permission_data: dict) -> Permission:
        """Create a new permission"""
        permission = Permission(**permission_data)
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission
    
    async def get_by_id(self, permission_id: UUID) -> Optional[Permission]:
        """Get permission by ID"""
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name"""
        query = select(Permission).where(Permission.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        resource: Optional[str] = None
    ) -> List[Permission]:
        """Get all permissions"""
        query = select(Permission)
        
        if resource:
            query = query.where(Permission.resource == resource)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def delete(self, permission: Permission) -> bool:
        """Delete permission"""
        await self.db.delete(permission)
        await self.db.commit()
        return True
