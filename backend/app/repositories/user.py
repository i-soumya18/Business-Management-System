"""
User repository for database operations
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.user import User
from app.models.role import Role


class UserRepository:
    """
    Repository for User model database operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, user_data: dict) -> User:
        """Create a new user"""
        user = User(**user_data)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        query = select(User).where(User.id == user_id).options(
            selectinload(User.roles)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        query = select(User).where(User.email == email).options(
            selectinload(User.roles)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """Get all users with pagination"""
        query = select(User).options(selectinload(User.roles))
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update(self, user: User, update_data: dict) -> User:
        """Update user"""
        for key, value in update_data.items():
            if value is not None:
                setattr(user, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def delete(self, user: User) -> bool:
        """Delete user"""
        await self.db.delete(user)
        await self.db.commit()
        return True
    
    async def add_role(self, user: User, role: Role) -> User:
        """Add role to user"""
        if role not in user.roles:
            user.roles.append(role)
            await self.db.commit()
            await self.db.refresh(user)
        return user
    
    async def remove_role(self, user: User, role: Role) -> User:
        """Remove role from user"""
        if role in user.roles:
            user.roles.remove(role)
            await self.db.commit()
            await self.db.refresh(user)
        return user
    
    async def search(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Search users by email, first name, or last name"""
        search_pattern = f"%{search_term}%"
        query = select(User).where(
            or_(
                User.email.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern)
            )
        ).options(selectinload(User.roles)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
