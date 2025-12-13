"""
Inventory Service

Business logic for inventory management, stock movements, and reservations.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.inventory import MovementType
from app.repositories.inventory import (
    StockLocationRepository,
    InventoryLevelRepository,
    InventoryMovementRepository,
    StockAdjustmentRepository,
    LowStockAlertRepository
)
from app.repositories.product import ProductVariantRepository


logger = logging.getLogger(__name__)


class InventoryService:
    """Service for inventory management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.location_repo = StockLocationRepository(db)
        self.level_repo = InventoryLevelRepository(db)
        self.movement_repo = InventoryMovementRepository(db)
        self.adjustment_repo = StockAdjustmentRepository(db)
        self.alert_repo = LowStockAlertRepository(db)
        self.variant_repo = ProductVariantRepository(db)
    
    async def receive_stock(
        self,
        variant_id: UUID,
        location_id: UUID,
        quantity: int,
        unit_cost: Optional[float] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Receive stock into inventory
        
        Args:
            variant_id: Product variant ID
            location_id: Stock location ID
            quantity: Quantity received
            unit_cost: Cost per unit
            reference_type: Reference type (e.g., 'purchase_order')
            reference_id: Reference ID
            reference_number: Reference number
            notes: Additional notes
            user_id: User performing the action
            
        Returns:
            Dict with updated inventory level and movement record
        """
        # Validate variant exists
        variant = await self.variant_repo.get_by_id(variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product variant {variant_id} not found"
            )
        
        # Validate location exists
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock location {location_id} not found"
            )
        
        # Get or create inventory level
        level = await self.level_repo.get_by_variant_and_location(
            variant_id, location_id
        )
        
        if not level:
            # Create new inventory level
            level_data = {
                "product_variant_id": variant_id,
                "location_id": location_id,
                "quantity_on_hand": quantity,
                "quantity_reserved": 0,
                "quantity_available": quantity
            }
            level = await self.level_repo.create(level_data)
        else:
            # Update existing level
            level = await self.level_repo.update_quantities(
                level.id,
                on_hand_delta=quantity
            )
        
        # Create movement record
        movement = await self.movement_repo.create_movement(
            variant_id=variant_id,
            quantity=quantity,
            movement_type=MovementType.RECEIPT,
            to_location_id=location_id,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            notes=notes,
            created_by_id=user_id
        )
        
        # Check and resolve low stock alerts
        await self._check_and_resolve_alert(variant_id, location_id, user_id)
        
        return {
            "inventory_level": level,
            "movement": movement,
            "message": f"Received {quantity} units"
        }
    
    async def ship_stock(
        self,
        variant_id: UUID,
        location_id: UUID,
        quantity: int,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Ship stock out of inventory
        
        Reduces available stock. Stock must be reserved first.
        """
        # Get inventory level
        level = await self.level_repo.get_by_variant_and_location(
            variant_id, location_id
        )
        
        if not level:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory level not found"
            )
        
        # Check if enough reserved stock
        if quantity > level.quantity_reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot ship {quantity} units. Only {level.quantity_reserved} reserved."
            )
        
        # Update quantities (reduce both on_hand and reserved)
        level = await self.level_repo.update_quantities(
            level.id,
            on_hand_delta=-quantity,
            reserved_delta=-quantity
        )
        
        # Create movement record
        movement = await self.movement_repo.create_movement(
            variant_id=variant_id,
            quantity=quantity,
            movement_type=MovementType.SHIPMENT,
            from_location_id=location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            notes=notes,
            created_by_id=user_id
        )
        
        # Check for low stock
        await self._check_low_stock(variant_id, location_id)
        
        return {
            "inventory_level": level,
            "movement": movement,
            "message": f"Shipped {quantity} units"
        }
    
    async def transfer_stock(
        self,
        variant_id: UUID,
        from_location_id: UUID,
        to_location_id: UUID,
        quantity: int,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Transfer stock between locations
        """
        # Validate locations
        from_location = await self.location_repo.get_by_id(from_location_id)
        to_location = await self.location_repo.get_by_id(to_location_id)
        
        if not from_location or not to_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found"
            )
        
        # Get source inventory level
        from_level = await self.level_repo.get_by_variant_and_location(
            variant_id, from_location_id
        )
        
        if not from_level:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source inventory not found"
            )
        
        if quantity > from_level.quantity_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {from_level.quantity_available}"
            )
        
        # Reduce from source
        from_level = await self.level_repo.update_quantities(
            from_level.id,
            on_hand_delta=-quantity
        )
        
        # Add to destination
        to_level = await self.level_repo.get_by_variant_and_location(
            variant_id, to_location_id
        )
        
        if not to_level:
            to_level_data = {
                "product_variant_id": variant_id,
                "location_id": to_location_id,
                "quantity_on_hand": quantity,
                "quantity_reserved": 0,
                "quantity_available": quantity
            }
            to_level = await self.level_repo.create(to_level_data)
        else:
            to_level = await self.level_repo.update_quantities(
                to_level.id,
                on_hand_delta=quantity
            )
        
        # Create movement record
        movement = await self.movement_repo.create_movement(
            variant_id=variant_id,
            quantity=quantity,
            movement_type=MovementType.TRANSFER,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            notes=notes,
            created_by_id=user_id
        )
        
        # Check low stock at source location
        await self._check_low_stock(variant_id, from_location_id)
        
        return {
            "from_level": from_level,
            "to_level": to_level,
            "movement": movement,
            "message": f"Transferred {quantity} units"
        }
    
    async def reserve_stock(
        self,
        variant_id: UUID,
        location_id: UUID,
        quantity: int,
        reference_type: str,
        reference_id: UUID,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Reserve stock for an order or allocation
        """
        # Get inventory level
        level = await self.level_repo.get_by_variant_and_location(
            variant_id, location_id
        )
        
        if not level:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory level not found"
            )
        
        if quantity > level.quantity_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {level.quantity_available}"
            )
        
        # Increase reserved quantity
        level = await self.level_repo.update_quantities(
            level.id,
            reserved_delta=quantity
        )
        
        # Create movement record
        movement = await self.movement_repo.create_movement(
            variant_id=variant_id,
            quantity=quantity,
            movement_type=MovementType.RESERVATION,
            from_location_id=location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            created_by_id=user_id
        )
        
        return {
            "inventory_level": level,
            "movement": movement,
            "reserved_quantity": quantity,
            "available_quantity": level.quantity_available
        }
    
    async def release_reservation(
        self,
        variant_id: UUID,
        location_id: UUID,
        quantity: int,
        reference_type: str,
        reference_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Release a stock reservation
        """
        level = await self.level_repo.get_by_variant_and_location(
            variant_id, location_id
        )
        
        if not level:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory level not found"
            )
        
        if quantity > level.quantity_reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot release {quantity}. Only {level.quantity_reserved} reserved."
            )
        
        # Decrease reserved quantity
        level = await self.level_repo.update_quantities(
            level.id,
            reserved_delta=-quantity
        )
        
        # Create movement record
        movement = await self.movement_repo.create_movement(
            variant_id=variant_id,
            quantity=quantity,
            movement_type=MovementType.RELEASE,
            to_location_id=location_id,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by_id=user_id
        )
        
        return {
            "inventory_level": level,
            "movement": movement,
            "released_quantity": quantity
        }
    
    async def adjust_stock(
        self,
        location_id: UUID,
        variant_id: UUID,
        expected_quantity: int,
        actual_quantity: int,
        reason: str,
        user_id: UUID,
        unit_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a stock adjustment (for physical counts, damage, etc.)
        """
        # Create adjustment record
        adjustment = await self.adjustment_repo.create_adjustment(
            location_id=location_id,
            variant_id=variant_id,
            expected_quantity=expected_quantity,
            actual_quantity=actual_quantity,
            reason=reason,
            adjusted_by_id=user_id,
            unit_cost=unit_cost,
            notes=notes
        )
        
        return {
            "adjustment": adjustment,
            "message": "Adjustment created. Awaiting approval."
        }
    
    async def approve_adjustment(
        self,
        adjustment_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a stock adjustment and update inventory
        """
        adjustment = await self.adjustment_repo.get_by_id(adjustment_id)
        
        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Adjustment not found"
            )
        
        if adjustment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve adjustment with status: {adjustment.status}"
            )
        
        # Approve adjustment
        adjustment = await self.adjustment_repo.approve_adjustment(
            adjustment_id, user_id, notes
        )
        
        # Update inventory level
        level = await self.level_repo.get_by_variant_and_location(
            adjustment.product_variant_id,
            adjustment.location_id
        )
        
        if level:
            level = await self.level_repo.update_quantities(
                level.id,
                on_hand_delta=adjustment.adjustment_quantity
            )
        
        # Create movement record
        movement_type = (
            MovementType.ADJUSTMENT_IN 
            if adjustment.adjustment_quantity > 0 
            else MovementType.ADJUSTMENT_OUT
        )
        
        await self.movement_repo.create_movement(
            variant_id=adjustment.product_variant_id,
            quantity=abs(adjustment.adjustment_quantity),
            movement_type=movement_type,
            from_location_id=adjustment.location_id if adjustment.adjustment_quantity < 0 else None,
            to_location_id=adjustment.location_id if adjustment.adjustment_quantity > 0 else None,
            unit_cost=adjustment.unit_cost,
            reference_type="adjustment",
            reference_id=adjustment_id,
            reference_number=adjustment.adjustment_number,
            reason=adjustment.reason,
            notes=notes,
            created_by_id=user_id
        )
        
        # Check low stock
        if adjustment.adjustment_quantity < 0:
            await self._check_low_stock(
                adjustment.product_variant_id,
                adjustment.location_id
            )
        
        return {
            "adjustment": adjustment,
            "inventory_level": level,
            "message": "Adjustment approved and applied"
        }
    
    async def _check_low_stock(
        self,
        variant_id: UUID,
        location_id: UUID
    ) -> None:
        """Check if stock is low and create alert if needed"""
        level = await self.level_repo.get_by_variant_and_location(
            variant_id, location_id
        )
        
        if not level or not level.reorder_point:
            return
        
        if level.quantity_available < level.reorder_point:
            # Check if alert already exists
            existing_alert = await self.alert_repo.get_by_variant_and_location(
                variant_id, location_id
            )
            
            if not existing_alert:
                # Create new alert
                recommended_qty = level.reorder_quantity or (
                    level.reorder_point * 2 - level.quantity_available
                )
                
                await self.alert_repo.create_alert(
                    variant_id=variant_id,
                    location_id=location_id,
                    current_quantity=level.quantity_available,
                    reorder_point=level.reorder_point,
                    recommended_order_quantity=recommended_qty
                )
                
                logger.info(
                    f"Low stock alert created for variant {variant_id} "
                    f"at location {location_id}"
                )
    
    async def _check_and_resolve_alert(
        self,
        variant_id: UUID,
        location_id: UUID,
        user_id: Optional[UUID] = None
    ) -> None:
        """Check if alert can be resolved after stock receipt"""
        level = await self.level_repo.get_by_variant_and_location(
            variant_id, location_id
        )
        
        if not level or not level.reorder_point:
            return
        
        if level.quantity_available >= level.reorder_point:
            # Resolve any active alerts
            alert = await self.alert_repo.get_by_variant_and_location(
                variant_id, location_id
            )
            
            if alert and alert.status == "active":
                await self.alert_repo.resolve_alert(
                    alert.id,
                    resolved_by_id=user_id,
                    resolution_notes="Stock replenished above reorder point"
                )
                
                logger.info(
                    f"Low stock alert resolved for variant {variant_id} "
                    f"at location {location_id}"
                )
