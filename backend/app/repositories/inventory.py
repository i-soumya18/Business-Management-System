"""
Inventory Repository

Repository for inventory tracking operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import (
    StockLocation,
    InventoryLevel,
    InventoryMovement,
    StockAdjustment,
    LowStockAlert,
    MovementType
)
from app.repositories.base import BaseRepository


class StockLocationRepository(BaseRepository[StockLocation]):
    """Repository for StockLocation operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(StockLocation, db)
    
    async def get_by_code(self, code: str) -> Optional[StockLocation]:
        """Get location by code"""
        return await self.get_by_field("code", code.upper())
    
    async def get_default(self) -> Optional[StockLocation]:
        """Get default stock location"""
        query = select(StockLocation).where(
            and_(
                StockLocation.is_default == True,
                StockLocation.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_locations(self) -> List[StockLocation]:
        """Get all active locations ordered by priority"""
        return await self.get_all(
            filters={"is_active": True},
            order_by="priority"
        )


class InventoryLevelRepository(BaseRepository[InventoryLevel]):
    """Repository for InventoryLevel operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryLevel, db)
    
    async def get_by_variant_and_location(
        self,
        variant_id: UUID,
        location_id: UUID
    ) -> Optional[InventoryLevel]:
        """Get inventory level for specific variant and location"""
        query = select(InventoryLevel).where(
            and_(
                InventoryLevel.product_variant_id == variant_id,
                InventoryLevel.location_id == location_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_variant(
        self,
        variant_id: UUID
    ) -> List[InventoryLevel]:
        """Get all inventory levels for a variant across locations"""
        return await self.get_all(
            filters={"product_variant_id": variant_id},
            relationships=["location"]
        )
    
    async def get_by_location(
        self,
        location_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[InventoryLevel]:
        """Get all inventory levels at a location"""
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={"location_id": location_id},
            relationships=["product_variant"]
        )
    
    async def get_low_stock_items(
        self,
        location_id: Optional[UUID] = None
    ) -> List[InventoryLevel]:
        """Get items with stock below reorder point"""
        query = select(InventoryLevel).where(
            and_(
                InventoryLevel.quantity_available < InventoryLevel.reorder_point,
                InventoryLevel.reorder_point.isnot(None)
            )
        ).options(
            selectinload(InventoryLevel.product_variant),
            selectinload(InventoryLevel.location)
        )
        
        if location_id:
            query = query.where(InventoryLevel.location_id == location_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_total_stock(self, variant_id: UUID) -> int:
        """Get total available stock across all locations"""
        query = select(func.sum(InventoryLevel.quantity_available)).where(
            InventoryLevel.product_variant_id == variant_id
        )
        result = await self.db.execute(query)
        total = result.scalar_one_or_none()
        return total or 0
    
    async def update_quantities(
        self,
        level_id: UUID,
        on_hand_delta: int = 0,
        reserved_delta: int = 0
    ) -> Optional[InventoryLevel]:
        """
        Update inventory quantities atomically
        
        Args:
            level_id: Inventory level ID
            on_hand_delta: Change in on-hand quantity (can be negative)
            reserved_delta: Change in reserved quantity (can be negative)
        """
        level = await self.get_by_id(level_id)
        if not level:
            return None
        
        new_on_hand = level.quantity_on_hand + on_hand_delta
        new_reserved = level.quantity_reserved + reserved_delta
        
        if new_on_hand < 0 or new_reserved < 0:
            raise ValueError("Quantities cannot be negative")
        
        new_available = new_on_hand - new_reserved
        
        return await self.update(level_id, {
            "quantity_on_hand": new_on_hand,
            "quantity_reserved": new_reserved,
            "quantity_available": new_available
        })


class InventoryMovementRepository(BaseRepository[InventoryMovement]):
    """Repository for InventoryMovement operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryMovement, db)
    
    async def create_movement(
        self,
        variant_id: UUID,
        quantity: int,
        movement_type: MovementType,
        from_location_id: Optional[UUID] = None,
        to_location_id: Optional[UUID] = None,
        unit_cost: Optional[float] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        reason: Optional[str] = None,
        created_by_id: Optional[UUID] = None
    ) -> InventoryMovement:
        """Create an inventory movement record"""
        total_cost = (unit_cost * quantity) if unit_cost else None
        
        movement_data = {
            "product_variant_id": variant_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "movement_type": movement_type,
            "quantity": quantity,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "reference_number": reference_number,
            "notes": notes,
            "reason": reason,
            "created_by_id": created_by_id,
            "movement_date": datetime.utcnow()
        }
        
        return await self.create(movement_data)
    
    async def get_by_variant(
        self,
        variant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[InventoryMovement], int]:
        """Get movement history for a variant"""
        query = select(InventoryMovement).where(
            InventoryMovement.product_variant_id == variant_id
        ).order_by(InventoryMovement.movement_date.desc())
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        movements = list(result.scalars().all())
        
        return movements, total
    
    async def get_by_location(
        self,
        location_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[InventoryMovement], int]:
        """Get movements for a location"""
        query = select(InventoryMovement).where(
            or_(
                InventoryMovement.from_location_id == location_id,
                InventoryMovement.to_location_id == location_id
            )
        ).order_by(InventoryMovement.movement_date.desc())
        
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        movements = list(result.scalars().all())
        
        return movements, total


class StockAdjustmentRepository(BaseRepository[StockAdjustment]):
    """Repository for StockAdjustment operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(StockAdjustment, db)
    
    async def create_adjustment(
        self,
        location_id: UUID,
        variant_id: UUID,
        expected_quantity: int,
        actual_quantity: int,
        reason: str,
        adjusted_by_id: UUID,
        unit_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> StockAdjustment:
        """Create a stock adjustment record"""
        adjustment_quantity = actual_quantity - expected_quantity
        total_cost_impact = (unit_cost * abs(adjustment_quantity)) if unit_cost else None
        
        # Generate adjustment number
        count = await self.count() + 1
        adjustment_number = f"ADJ-{datetime.utcnow().strftime('%Y%m%d')}-{count:04d}"
        
        adjustment_data = {
            "adjustment_number": adjustment_number,
            "location_id": location_id,
            "product_variant_id": variant_id,
            "expected_quantity": expected_quantity,
            "actual_quantity": actual_quantity,
            "adjustment_quantity": adjustment_quantity,
            "unit_cost": unit_cost,
            "total_cost_impact": total_cost_impact,
            "reason": reason,
            "notes": notes,
            "adjusted_by_id": adjusted_by_id,
            "status": "pending",
            "adjustment_date": datetime.utcnow()
        }
        
        return await self.create(adjustment_data)
    
    async def approve_adjustment(
        self,
        adjustment_id: UUID,
        approved_by_id: UUID,
        notes: Optional[str] = None
    ) -> Optional[StockAdjustment]:
        """Approve a stock adjustment"""
        return await self.update(adjustment_id, {
            "status": "approved",
            "approved_by_id": approved_by_id,
            "approved_at": datetime.utcnow(),
            "notes": notes if notes else None
        })
    
    async def reject_adjustment(
        self,
        adjustment_id: UUID,
        approved_by_id: UUID,
        notes: Optional[str] = None
    ) -> Optional[StockAdjustment]:
        """Reject a stock adjustment"""
        return await self.update(adjustment_id, {
            "status": "rejected",
            "approved_by_id": approved_by_id,
            "approved_at": datetime.utcnow(),
            "notes": notes if notes else None
        })
    
    async def get_pending_adjustments(
        self,
        location_id: Optional[UUID] = None
    ) -> List[StockAdjustment]:
        """Get all pending adjustments"""
        filters = {"status": "pending"}
        if location_id:
            filters["location_id"] = location_id
        
        return await self.get_all(
            filters=filters,
            order_by="adjustment_date"
        )


class LowStockAlertRepository(BaseRepository[LowStockAlert]):
    """Repository for LowStockAlert operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(LowStockAlert, db)
    
    async def create_alert(
        self,
        variant_id: UUID,
        location_id: UUID,
        current_quantity: int,
        reorder_point: int,
        recommended_order_quantity: Optional[int] = None
    ) -> LowStockAlert:
        """Create a low stock alert"""
        alert_data = {
            "product_variant_id": variant_id,
            "location_id": location_id,
            "current_quantity": current_quantity,
            "reorder_point": reorder_point,
            "recommended_order_quantity": recommended_order_quantity,
            "status": "active",
            "alert_date": datetime.utcnow()
        }
        
        return await self.create(alert_data)
    
    async def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by_id: UUID,
        resolution_notes: Optional[str] = None
    ) -> Optional[LowStockAlert]:
        """Resolve a low stock alert"""
        return await self.update(alert_id, {
            "status": "resolved",
            "resolved_by_id": resolved_by_id,
            "resolved_at": datetime.utcnow(),
            "resolution_notes": resolution_notes
        })
    
    async def get_active_alerts(
        self,
        location_id: Optional[UUID] = None
    ) -> List[LowStockAlert]:
        """Get all active alerts"""
        filters = {"status": "active"}
        if location_id:
            filters["location_id"] = location_id
        
        return await self.get_all(
            filters=filters,
            order_by="alert_date",
            relationships=["product_variant", "location"]
        )
    
    async def get_by_variant_and_location(
        self,
        variant_id: UUID,
        location_id: UUID
    ) -> Optional[LowStockAlert]:
        """Get active alert for variant at location"""
        query = select(LowStockAlert).where(
            and_(
                LowStockAlert.product_variant_id == variant_id,
                LowStockAlert.location_id == location_id,
                LowStockAlert.status == "active"
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
