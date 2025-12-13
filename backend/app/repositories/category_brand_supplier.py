"""
Category and Brand/Supplier Repositories

Repositories for managing categories, brands, and suppliers.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.brand import Brand
from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)
    
    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug"""
        return await self.get_by_field("slug", slug)
    
    async def get_with_children(self, id: UUID) -> Optional[Category]:
        """Get category with its direct children"""
        query = (
            select(Category)
            .where(Category.id == id)
            .options(selectinload(Category.children))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_root_categories(self) -> List[Category]:
        """Get all root categories (no parent)"""
        query = select(Category).where(Category.parent_id.is_(None))
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_children(self, parent_id: UUID) -> List[Category]:
        """Get all children of a category"""
        return await self.get_all(filters={"parent_id": parent_id})
    
    async def get_tree(self, parent_id: Optional[UUID] = None) -> List[Category]:
        """
        Get category tree recursively
        
        If parent_id is None, returns root categories with all descendants.
        """
        if parent_id is None:
            # Get root categories
            root_categories = await self.get_root_categories()
        else:
            # Get children of specific category
            root_categories = await self.get_children(parent_id)
        
        # Load children recursively
        for category in root_categories:
            category.children = await self.get_tree(category.id)
        
        return root_categories


class BrandRepository(BaseRepository[Brand]):
    """Repository for Brand operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Brand, db)
    
    async def get_by_slug(self, slug: str) -> Optional[Brand]:
        """Get brand by slug"""
        return await self.get_by_field("slug", slug)
    
    async def get_by_code(self, code: str) -> Optional[Brand]:
        """Get brand by code"""
        return await self.get_by_field("code", code.upper())
    
    async def search_brands(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Brand], int]:
        """Search brands by name or code"""
        from sqlalchemy import or_, func
        
        stmt = select(Brand)
        
        if query:
            search_filter = or_(
                Brand.name.ilike(f"%{query}%"),
                Brand.code.ilike(f"%{query}%")
            )
            stmt = stmt.where(search_filter)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Brand.name)
        result = await self.db.execute(stmt)
        brands = list(result.scalars().all())
        
        return brands, total


class SupplierRepository(BaseRepository[Supplier]):
    """Repository for Supplier operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Supplier, db)
    
    async def get_by_code(self, code: str) -> Optional[Supplier]:
        """Get supplier by code"""
        return await self.get_by_field("code", code.upper())
    
    async def get_by_email(self, email: str) -> Optional[Supplier]:
        """Get supplier by email"""
        return await self.get_by_field("email", email.lower())
    
    async def search_suppliers(
        self,
        query: str,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Supplier], int]:
        """Search suppliers by name, code, or email"""
        from sqlalchemy import or_, func, and_
        
        stmt = select(Supplier)
        
        filters = []
        
        if query:
            search_filter = or_(
                Supplier.name.ilike(f"%{query}%"),
                Supplier.code.ilike(f"%{query}%"),
                Supplier.email.ilike(f"%{query}%")
            )
            filters.append(search_filter)
        
        if is_active is not None:
            filters.append(Supplier.is_active == is_active)
        
        if filters:
            stmt = stmt.where(and_(*filters))
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Supplier.name)
        result = await self.db.execute(stmt)
        suppliers = list(result.scalars().all())
        
        return suppliers, total
    
    async def get_active_suppliers(self) -> List[Supplier]:
        """Get all active suppliers ordered by rating"""
        query = (
            select(Supplier)
            .where(Supplier.is_active == True)
            .order_by(Supplier.rating.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
