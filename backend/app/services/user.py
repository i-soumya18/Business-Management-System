"""
User service for business logic
"""
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.models.user import User
from app.schemas.user import UserUpdate


class UserService:
    """
    Service for user management operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
    
    async def get_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """
        Get all users
        """
        return await self.user_repo.get_all(skip=skip, limit=limit, is_active=is_active)
    
    async def get_user_by_id(self, user_id: UUID) -> User:
        """
        Get user by ID
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    
    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> User:
        """
        Update user
        """
        user = await self.get_user_by_id(user_id)
        
        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return user
        
        return await self.user_repo.update(user, update_data)
    
    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user
        """
        user = await self.get_user_by_id(user_id)
        return await self.user_repo.delete(user)
    
    async def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Search users
        """
        return await self.user_repo.search(search_term, skip=skip, limit=limit)
    
    async def add_role_to_user(self, user_id: UUID, role_id: UUID) -> User:
        """
        Add role to user
        """
        user = await self.get_user_by_id(user_id)
        role = await self.role_repo.get_by_id(role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        return await self.user_repo.add_role(user, role)
    
    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> User:
        """
        Remove role from user
        """
        user = await self.get_user_by_id(user_id)
        role = await self.role_repo.get_by_id(role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        return await self.user_repo.remove_role(user, role)
