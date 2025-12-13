"""
Category Repository

Repository for Category operations.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)

    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug"""
        return await self.get_by_field("slug", slug)

    async def get_with_children(self, id: UUID) -> Optional[Category]:
        """Get category with children"""
        query = select(Category).options(
            selectinload(Category.children)
        ).where(Category.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_root_categories(self) -> List[Category]:
        """Get all root categories (no parent)"""
        query = select(Category).where(Category.parent_id.is_(None))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_children(self, parent_id: UUID) -> List[Category]:
        """Get children of a category"""
        query = select(Category).where(Category.parent_id == parent_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tree(self, root_id: Optional[UUID] = None) -> List[Category]:
        """Get category tree starting from root"""
        if root_id:
            query = select(Category).options(
                selectinload(Category.children)
            ).where(Category.id == root_id)
        else:
            query = select(Category).options(
                selectinload(Category.children)
            ).where(Category.parent_id.is_(None))

        result = await self.db.execute(query)
        return list(result.scalars().all())