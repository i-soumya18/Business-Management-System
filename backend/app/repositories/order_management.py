"""
Order Management Repository

Repository for order management operations including:
- Order history tracking
- Order notes and comments
- Order fulfillment operations
- Inventory reservations
"""

from datetime import datetime
from typing import Optional, List, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.order_management import (
    OrderHistory,
    OrderNote,
    OrderFulfillment,
    InventoryReservation,
    OrderHistoryAction,
    FulfillmentStatus
)
from app.models.order import Order
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.order_management import (
    OrderHistoryCreate,
    OrderHistoryUpdate,
    OrderNoteCreate,
    OrderNoteUpdate,
    OrderFulfillmentCreate,
    OrderFulfillmentUpdate,
    OrderFulfillmentStatusUpdate,
    InventoryReservationCreate,
    InventoryReservationUpdate,
    OrderSearchFilters
)


class OrderHistoryRepository(BaseRepository[OrderHistory]):
    """Repository for Order History operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(OrderHistory, db)
    
    async def get_by_order(
        self,
        order_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[OrderHistory]:
        """Get order history for a specific order"""
        query = (
            select(OrderHistory)
            .where(OrderHistory.order_id == order_id)
            .order_by(desc(OrderHistory.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_action(
        self,
        action: OrderHistoryAction,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[OrderHistory]:
        """Get order history by action type"""
        query = (
            select(OrderHistory)
            .where(OrderHistory.action == action)
            .order_by(desc(OrderHistory.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_history_entry(
        self,
        order_id: UUID,
        action: OrderHistoryAction,
        description: str,
        performed_by_id: Optional[UUID] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        additional_data: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OrderHistory:
        """Create a new history entry"""
        history = OrderHistory(
            order_id=order_id,
            action=action,
            description=description,
            performed_by_id=performed_by_id,
            old_status=old_status,
            new_status=new_status,
            additional_data=additional_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history


class OrderNoteRepository(BaseRepository[OrderNote]):
    """Repository for Order Note operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(OrderNote, db)
    
    async def get_by_order(
        self,
        order_id: UUID,
        include_internal: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[OrderNote]:
        """Get notes for a specific order"""
        query = select(OrderNote).where(OrderNote.order_id == order_id)
        
        if not include_internal:
            query = query.where(OrderNote.is_internal == False)
        
        query = query.order_by(desc(OrderNote.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_customer_visible_notes(
        self,
        order_id: UUID
    ) -> Sequence[OrderNote]:
        """Get customer-visible notes only"""
        query = (
            select(OrderNote)
            .where(
                and_(
                    OrderNote.order_id == order_id,
                    OrderNote.is_internal == False
                )
            )
            .order_by(desc(OrderNote.created_at))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_as_notified(self, note_id: UUID) -> Optional[OrderNote]:
        """Mark a note as notified to customer"""
        note = await self.get(note_id)
        if note:
            note.notified_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(note)
        return note


class OrderFulfillmentRepository(BaseRepository[OrderFulfillment]):
    """Repository for Order Fulfillment operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(OrderFulfillment, db)
    
    async def get_by_order(self, order_id: UUID) -> Sequence[OrderFulfillment]:
        """Get fulfillments for a specific order"""
        query = (
            select(OrderFulfillment)
            .where(OrderFulfillment.order_id == order_id)
            .order_by(desc(OrderFulfillment.created_at))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: FulfillmentStatus,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[OrderFulfillment]:
        """Get fulfillments by status"""
        query = (
            select(OrderFulfillment)
            .where(OrderFulfillment.status == status)
            .order_by(OrderFulfillment.created_at)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_assigned_user(
        self,
        user_id: UUID,
        status: Optional[FulfillmentStatus] = None
    ) -> Sequence[OrderFulfillment]:
        """Get fulfillments assigned to a user"""
        query = select(OrderFulfillment).where(OrderFulfillment.assigned_to_id == user_id)
        
        if status:
            query = query.where(OrderFulfillment.status == status)
        
        query = query.order_by(OrderFulfillment.created_at)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_status(
        self,
        fulfillment_id: UUID,
        new_status: FulfillmentStatus,
        notes: Optional[str] = None
    ) -> Optional[OrderFulfillment]:
        """Update fulfillment status and set timestamps"""
        fulfillment = await self.get(fulfillment_id)
        if not fulfillment:
            return None
        
        now = datetime.utcnow()
        fulfillment.status = new_status
        
        # Update timestamps based on status
        if new_status == FulfillmentStatus.PICKING and not fulfillment.picking_started_at:
            fulfillment.picking_started_at = now
        elif new_status == FulfillmentStatus.PACKING:
            if not fulfillment.picking_completed_at:
                fulfillment.picking_completed_at = now
            if not fulfillment.packing_started_at:
                fulfillment.packing_started_at = now
        elif new_status == FulfillmentStatus.READY_TO_SHIP:
            if not fulfillment.packing_completed_at:
                fulfillment.packing_completed_at = now
        elif new_status == FulfillmentStatus.SHIPPED:
            if not fulfillment.shipped_at:
                fulfillment.shipped_at = now
        
        # Add notes if provided
        if notes:
            if fulfillment.status == FulfillmentStatus.PICKING:
                fulfillment.picking_notes = notes
            else:
                fulfillment.packing_notes = notes
        
        await self.db.flush()
        await self.db.refresh(fulfillment)
        return fulfillment
    
    async def generate_fulfillment_number(self) -> str:
        """Generate unique fulfillment number"""
        # Get count for today
        today = datetime.utcnow().date()
        query = select(func.count()).select_from(OrderFulfillment).where(
            func.date(OrderFulfillment.created_at) == today
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        # Format: FUL-YYYYMMDD-XXXX
        return f"FUL-{today.strftime('%Y%m%d')}-{count + 1:04d}"
    
    async def get_statistics(self) -> dict:
        """Get fulfillment statistics"""
        query = select(
            OrderFulfillment.status,
            func.count(OrderFulfillment.id).label('count')
        ).group_by(OrderFulfillment.status)
        
        result = await self.db.execute(query)
        stats = {row.status.value: row.count for row in result}
        stats['total'] = sum(stats.values())
        return stats


class InventoryReservationRepository(BaseRepository[InventoryReservation]):
    """Repository for Inventory Reservation operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(InventoryReservation, db)
    
    async def get_by_order(self, order_id: UUID) -> Sequence[InventoryReservation]:
        """Get reservations for a specific order"""
        query = (
            select(InventoryReservation)
            .where(InventoryReservation.order_id == order_id)
            .order_by(InventoryReservation.created_at)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_variant(
        self,
        variant_id: UUID,
        active_only: bool = True
    ) -> Sequence[InventoryReservation]:
        """Get reservations for a product variant"""
        query = select(InventoryReservation).where(
            InventoryReservation.product_variant_id == variant_id
        )
        
        if active_only:
            query = query.where(InventoryReservation.is_active == True)
        
        query = query.order_by(InventoryReservation.reserved_at)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_active_reservations(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[InventoryReservation]:
        """Get all active reservations"""
        query = (
            select(InventoryReservation)
            .where(InventoryReservation.is_active == True)
            .order_by(InventoryReservation.reserved_at)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_expired_reservations(self) -> Sequence[InventoryReservation]:
        """Get expired but still active reservations"""
        now = datetime.utcnow()
        query = select(InventoryReservation).where(
            and_(
                InventoryReservation.is_active == True,
                InventoryReservation.expires_at <= now
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def release_reservation(
        self,
        reservation_id: UUID
    ) -> Optional[InventoryReservation]:
        """Release a reservation"""
        reservation = await self.get(reservation_id)
        if reservation:
            reservation.is_active = False
            reservation.released_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(reservation)
        return reservation
    
    async def release_order_reservations(
        self,
        order_id: UUID
    ) -> int:
        """Release all reservations for an order"""
        stmt = (
            update(InventoryReservation)
            .where(
                and_(
                    InventoryReservation.order_id == order_id,
                    InventoryReservation.is_active == True
                )
            )
            .values(
                is_active=False,
                released_at=datetime.utcnow()
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount
    
    async def fulfill_reservation(
        self,
        reservation_id: UUID,
        quantity_fulfilled: int
    ) -> Optional[InventoryReservation]:
        """Update fulfillment quantity"""
        reservation = await self.get(reservation_id)
        if reservation:
            reservation.quantity_fulfilled += quantity_fulfilled
            
            # If fully fulfilled, mark as complete
            if reservation.quantity_fulfilled >= reservation.quantity_reserved:
                reservation.is_active = False
                reservation.fulfilled_at = datetime.utcnow()
            
            await self.db.flush()
            await self.db.refresh(reservation)
        return reservation
    
    async def get_total_reserved_quantity(
        self,
        variant_id: UUID,
        location_id: Optional[UUID] = None
    ) -> int:
        """Get total reserved quantity for a variant"""
        query = select(func.sum(InventoryReservation.quantity_reserved)).where(
            and_(
                InventoryReservation.product_variant_id == variant_id,
                InventoryReservation.is_active == True
            )
        )
        
        if location_id:
            query = query.where(InventoryReservation.stock_location_id == location_id)
        
        result = await self.db.execute(query)
        return result.scalar() or 0


__all__ = [
    "OrderHistoryRepository",
    "OrderNoteRepository",
    "OrderFulfillmentRepository",
    "InventoryReservationRepository",
]
