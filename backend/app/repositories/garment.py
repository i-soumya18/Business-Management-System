"""
Garment-Specific Repositories

Repositories for managing garment features including size charts, colors,
fabrics, styles, collections, and measurements.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.garment import (
    SizeChart, Color, Fabric, Style, Collection,
    MeasurementSpec, GarmentImage, ProductFabric
)
from app.repositories.base import BaseRepository


class SizeChartRepository(BaseRepository[SizeChart]):
    """Repository for size chart operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(SizeChart, db)
    
    async def get_by_category(
        self,
        category: str,
        region: Optional[str] = None,
        active_only: bool = True
    ) -> List[SizeChart]:
        """Get size charts by category and optionally by region"""
        query = select(self.model).where(self.model.category == category)
        
        if region:
            query = query.where(self.model.region == region)
        
        if active_only:
            query = query.where(self.model.is_active == True)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[SizeChart], int]:
        """Search size charts by name"""
        search_query = select(self.model).where(
            self.model.name.ilike(f"%{query}%")
        )
        
        # Count total
        count_result = await self.db.execute(
            select(self.model).where(self.model.name.ilike(f"%{query}%"))
        )
        total = len(list(count_result.scalars().all()))
        
        # Get paginated results
        search_query = search_query.offset(skip).limit(limit)
        result = await self.db.execute(search_query)
        
        return list(result.scalars().all()), total


class ColorRepository(BaseRepository[Color]):
    """Repository for color operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Color, db)
    
    async def get_by_code(self, code: str) -> Optional[Color]:
        """Get color by code"""
        query = select(self.model).where(self.model.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_hex(self, hex_code: str) -> Optional[Color]:
        """Get color by hex code"""
        query = select(self.model).where(self.model.hex_code == hex_code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_colors(self) -> List[Color]:
        """Get all active colors"""
        query = select(self.model).where(self.model.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Color], int]:
        """Search colors by name or code"""
        search_query = select(self.model).where(
            (self.model.name.ilike(f"%{query}%")) |
            (self.model.code.ilike(f"%{query}%"))
        )
        
        # Count total
        count_result = await self.db.execute(
            select(self.model).where(
                (self.model.name.ilike(f"%{query}%")) |
                (self.model.code.ilike(f"%{query}%"))
            )
        )
        total = len(list(count_result.scalars().all()))
        
        # Get paginated results
        search_query = search_query.offset(skip).limit(limit)
        result = await self.db.execute(search_query)
        
        return list(result.scalars().all()), total


class FabricRepository(BaseRepository[Fabric]):
    """Repository for fabric operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Fabric, db)
    
    async def get_by_code(self, code: str) -> Optional[Fabric]:
        """Get fabric by code"""
        query = select(self.model).where(self.model.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_fabrics(self) -> List[Fabric]:
        """Get all active fabrics"""
        query = select(self.model).where(self.model.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[List[Fabric], int]:
        """Search fabrics by name or composition"""
        search_query = select(self.model).where(
            (self.model.name.ilike(f"%{query}%")) |
            (self.model.composition.ilike(f"%{query}%"))
        )
        
        # Count total
        count_result = await self.db.execute(
            select(self.model).where(
                (self.model.name.ilike(f"%{query}%")) |
                (self.model.composition.ilike(f"%{query}%"))
            )
        )
        total = len(list(count_result.scalars().all()))
        
        # Get paginated results
        search_query = search_query.offset(skip).limit(limit)
        result = await self.db.execute(search_query)
        
        return list(result.scalars().all()), total


class StyleRepository(BaseRepository[Style]):
    """Repository for style operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Style, db)
    
    async def get_by_code(self, code: str) -> Optional[Style]:
        """Get style by code"""
        query = select(self.model).where(self.model.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_styles(self) -> List[Style]:
        """Get all active styles"""
        query = select(self.model).where(self.model.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class CollectionRepository(BaseRepository[Collection]):
    """Repository for collection operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Collection, db)
    
    async def get_by_code(self, code: str) -> Optional[Collection]:
        """Get collection by code"""
        query = select(self.model).where(self.model.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_season(
        self,
        season: str,
        year: Optional[int] = None
    ) -> List[Collection]:
        """Get collections by season and optionally year"""
        query = select(self.model).where(self.model.season == season)
        
        if year:
            query = query.where(self.model.year == year)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active_collections(self) -> List[Collection]:
        """Get all active collections"""
        query = select(self.model).where(self.model.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class MeasurementSpecRepository(BaseRepository[MeasurementSpec]):
    """Repository for measurement specification operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(MeasurementSpec, db)
    
    async def get_by_product(
        self,
        product_id: int
    ) -> List[MeasurementSpec]:
        """Get all measurement specs for a product"""
        query = select(self.model).where(self.model.product_id == product_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_product_and_size(
        self,
        product_id: int,
        size: str
    ) -> Optional[MeasurementSpec]:
        """Get measurement spec for a specific product size"""
        query = select(self.model).where(
            (self.model.product_id == product_id) &
            (self.model.size == size)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class GarmentImageRepository(BaseRepository[GarmentImage]):
    """Repository for garment image operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(GarmentImage, db)
    
    async def get_by_product(
        self,
        product_id: int,
        active_only: bool = True
    ) -> List[GarmentImage]:
        """Get all images for a product"""
        query = select(self.model).where(self.model.product_id == product_id)
        
        if active_only:
            query = query.where(self.model.is_active == True)
        
        query = query.order_by(self.model.display_order)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_primary_image(
        self,
        product_id: int
    ) -> Optional[GarmentImage]:
        """Get primary image for a product"""
        query = select(self.model).where(
            (self.model.product_id == product_id) &
            (self.model.is_primary == True) &
            (self.model.is_active == True)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_color(
        self,
        product_id: int,
        color_id: int
    ) -> List[GarmentImage]:
        """Get images for a specific color variant"""
        query = select(self.model).where(
            (self.model.product_id == product_id) &
            (self.model.color_id == color_id) &
            (self.model.is_active == True)
        ).order_by(self.model.display_order)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class ProductFabricRepository(BaseRepository[ProductFabric]):
    """Repository for product-fabric relationship operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ProductFabric, db)
    
    async def get_by_product(
        self,
        product_id: int
    ) -> List[ProductFabric]:
        """Get all fabrics for a product"""
        query = select(self.model).where(
            self.model.product_id == product_id
        ).options(selectinload(self.model.fabric))
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_fabric(
        self,
        fabric_id: int
    ) -> List[ProductFabric]:
        """Get all products using a specific fabric"""
        query = select(self.model).where(self.model.fabric_id == fabric_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def delete_by_product(
        self,
        product_id: int
    ) -> None:
        """Delete all fabric associations for a product"""
        query = select(self.model).where(self.model.product_id == product_id)
        result = await self.db.execute(query)
        associations = list(result.scalars().all())
        
        for association in associations:
            await self.db.delete(association)
        
        await self.db.commit()
