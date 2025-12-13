"""
Product Repository

Repository for Product and ProductVariant operations with business logic.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.product import Product, ProductVariant
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Repository for Product operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Product, db)
    
    async def get_with_variants(self, id: UUID) -> Optional[Product]:
        """Get product with all variants"""
        query = (
            select(Product)
            .where(Product.id == id)
            .options(
                selectinload(Product.variants),
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.primary_supplier)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        return await self.get_by_field("sku", sku.upper())
    
    async def search(
        self,
        query: str,
        category_id: Optional[UUID] = None,
        brand_id: Optional[UUID] = None,
        supplier_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Product], int]:
        """
        Search products with filters
        
        Returns:
            (products, total_count)
        """
        # Build base query
        stmt = select(Product)
        
        # Add search filters
        if query:
            search_filter = or_(
                Product.name.ilike(f"%{query}%"),
                Product.sku.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
            stmt = stmt.where(search_filter)
        
        # Add field filters
        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        if brand_id:
            stmt = stmt.where(Product.brand_id == brand_id)
        if supplier_id:
            stmt = stmt.where(Product.primary_supplier_id == supplier_id)
        if is_active is not None:
            stmt = stmt.where(Product.is_active == is_active)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(Product.name)
        result = await self.db.execute(stmt)
        products = list(result.scalars().all())
        
        return products, total
    
    async def get_by_category(
        self, 
        category_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get all products in a category"""
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={"category_id": category_id}
        )
    
    async def get_low_stock_products(
        self,
        location_id: Optional[UUID] = None
    ) -> List[Product]:
        """Get products with low stock levels"""
        # This requires joining with inventory levels
        from app.models.inventory import InventoryLevel
        
        query = (
            select(Product)
            .join(ProductVariant, Product.id == ProductVariant.product_id)
            .join(InventoryLevel, ProductVariant.id == InventoryLevel.product_variant_id)
            .where(
                and_(
                    InventoryLevel.quantity_available < InventoryLevel.reorder_point,
                    InventoryLevel.reorder_point.isnot(None)
                )
            )
        )
        
        if location_id:
            query = query.where(InventoryLevel.location_id == location_id)
        
        query = query.distinct()
        
        result = await self.db.execute(query)
        return list(result.scalars().all())


class ProductVariantRepository(BaseRepository[ProductVariant]):
    """Repository for ProductVariant operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ProductVariant, db)
    
    async def get_with_inventory(
        self, 
        id: UUID
    ) -> Optional[ProductVariant]:
        """Get variant with inventory levels"""
        query = (
            select(ProductVariant)
            .where(ProductVariant.id == id)
            .options(
                selectinload(ProductVariant.product),
                selectinload(ProductVariant.inventory_levels)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Get variant by SKU"""
        return await self.get_by_field("sku", sku.upper())
    
    async def get_by_barcode(self, barcode: str) -> Optional[ProductVariant]:
        """Get variant by barcode"""
        return await self.get_by_field("barcode", barcode.upper())
    
    async def get_by_product(
        self,
        product_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductVariant]:
        """Get all variants for a product"""
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={"product_id": product_id}
        )
    
    async def search(
        self,
        query: str,
        product_id: Optional[UUID] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ProductVariant], int]:
        """
        Search variants with filters
        
        Returns:
            (variants, total_count)
        """
        stmt = select(ProductVariant)
        
        # Add search filters
        if query:
            search_filter = or_(
                ProductVariant.sku.ilike(f"%{query}%"),
                ProductVariant.barcode.ilike(f"%{query}%"),
                ProductVariant.size.ilike(f"%{query}%"),
                ProductVariant.color.ilike(f"%{query}%")
            )
            stmt = stmt.where(search_filter)
        
        # Add field filters
        if product_id:
            stmt = stmt.where(ProductVariant.product_id == product_id)
        if size:
            stmt = stmt.where(ProductVariant.size == size)
        if color:
            stmt = stmt.where(ProductVariant.color.ilike(f"%{color}%"))
        if is_active is not None:
            stmt = stmt.where(ProductVariant.is_active == is_active)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit).order_by(ProductVariant.sku)
        result = await self.db.execute(stmt)
        variants = list(result.scalars().all())
        
        return variants, total
    
    async def get_available_stock(
        self,
        variant_id: UUID,
        location_id: Optional[UUID] = None
    ) -> int:
        """Get available stock for a variant"""
        from app.models.inventory import InventoryLevel
        
        query = select(func.sum(InventoryLevel.quantity_available)).where(
            InventoryLevel.product_variant_id == variant_id
        )
        
        if location_id:
            query = query.where(InventoryLevel.location_id == location_id)
        
        result = await self.db.execute(query)
        total = result.scalar_one_or_none()
        
        return total or 0
