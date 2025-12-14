"""
Order Management Service

Unified business logic for order management operations including:
- Order lifecycle management (create, update, cancel)
- Order status workflow and transitions
- Order fulfillment workflow (picking, packing, shipping)
- Inventory reservation management
- Order history and audit trail
- Order notes and collaboration
- Dashboard and analytics
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import logging

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import (
    Order, OrderItem, OrderStatus, PaymentStatus, 
    SalesChannel, PaymentMethod
)
from app.models.order_management import (
    OrderHistory, OrderNote, OrderFulfillment, InventoryReservation,
    OrderHistoryAction, FulfillmentStatus
)
from app.models.product import ProductVariant
from app.models.inventory import InventoryLevel, StockLocation
from app.models.user import User
from app.repositories.order_management import (
    OrderHistoryRepository,
    OrderNoteRepository,
    OrderFulfillmentRepository,
    InventoryReservationRepository
)
from app.schemas.order_management import (
    OrderHistoryCreate,
    OrderNoteCreate,
    OrderNoteUpdate,
    OrderFulfillmentCreate,
    OrderFulfillmentUpdate,
    OrderFulfillmentStatusUpdate,
    InventoryReservationCreate,
    OrderSearchFilters,
    OrderManagementDashboard,
    OrderStatusCount,
    OrderFulfillmentStats,
    BulkOrderStatusUpdate,
    BulkOrderAssignment,
    BulkOperationResult
)


logger = logging.getLogger(__name__)


# Valid order status transitions
ORDER_STATUS_TRANSITIONS = {
    OrderStatus.DRAFT: [OrderStatus.PENDING, OrderStatus.CANCELLED],
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.READY_TO_SHIP, OrderStatus.CANCELLED],
    OrderStatus.READY_TO_SHIP: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED, OrderStatus.FAILED],
    OrderStatus.IN_TRANSIT: [OrderStatus.DELIVERED, OrderStatus.FAILED],
    OrderStatus.DELIVERED: [OrderStatus.COMPLETED, OrderStatus.RETURN_REQUESTED],
    OrderStatus.COMPLETED: [OrderStatus.RETURN_REQUESTED],
    OrderStatus.RETURN_REQUESTED: [OrderStatus.RETURNED, OrderStatus.COMPLETED],
    OrderStatus.RETURNED: [],
    OrderStatus.CANCELLED: [],
    OrderStatus.REFUNDED: [],
    OrderStatus.FAILED: [OrderStatus.PENDING, OrderStatus.CANCELLED],
}


class OrderManagementService:
    """Unified service for order management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.history_repo = OrderHistoryRepository(db)
        self.note_repo = OrderNoteRepository(db)
        self.fulfillment_repo = OrderFulfillmentRepository(db)
        self.reservation_repo = InventoryReservationRepository(db)
    
    # =========================================================================
    # Order Creation and Management
    # =========================================================================
    
    async def create_order(
        self,
        channel: SalesChannel,
        items: List[Dict[str, Any]],
        customer_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None,
        customer_name: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        payment_method: Optional[PaymentMethod] = None,
        payment_terms: Optional[str] = None,
        discount_amount: Decimal = Decimal("0"),
        discount_code: Optional[str] = None,
        tax_percentage: Optional[float] = None,
        shipping_amount: Decimal = Decimal("0"),
        customer_notes: Optional[str] = None,
        internal_notes: Optional[str] = None,
        reference_number: Optional[str] = None,
        source: Optional[str] = None,
        reserve_inventory: bool = True,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Order:
        """
        Create a new order with full workflow integration.
        
        Args:
            channel: Sales channel (wholesale, retail, ecommerce)
            items: List of order items with product_variant_id, quantity, unit_price
            customer_id: Optional customer user ID
            wholesale_customer_id: Optional wholesale customer ID for B2B
            customer_name: Customer name for guest checkout
            customer_email: Customer email
            customer_phone: Customer phone
            payment_method: Payment method
            payment_terms: Payment terms (Net 30, etc.)
            discount_amount: Total discount amount
            discount_code: Discount/promo code used
            tax_percentage: Tax percentage to apply
            shipping_amount: Shipping cost
            customer_notes: Notes from customer
            internal_notes: Internal notes
            reference_number: External reference (PO number, etc.)
            source: Order source (website, app, etc.)
            reserve_inventory: Whether to reserve inventory
            user_id: User creating the order
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created Order object
        """
        # Generate order number
        order_number = await self._generate_order_number(channel)
        
        # Create order
        order = Order(
            order_number=order_number,
            channel=channel,
            status=OrderStatus.DRAFT,
            customer_id=customer_id,
            wholesale_customer_id=wholesale_customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            payment_method=payment_method,
            payment_terms=payment_terms,
            discount_amount=discount_amount,
            discount_code=discount_code,
            shipping_amount=shipping_amount,
            customer_notes=customer_notes,
            internal_notes=internal_notes,
            reference_number=reference_number,
            source=source,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(order)
        await self.db.flush()
        
        # Create order items
        subtotal = Decimal("0")
        for item_data in items:
            # Get product variant
            variant = await self.db.get(ProductVariant, item_data["product_variant_id"])
            if not variant:
                raise ValueError(f"Product variant {item_data['product_variant_id']} not found")
            
            # Calculate item totals
            quantity = item_data["quantity"]
            unit_price = Decimal(str(item_data.get("unit_price", variant.price)))
            item_discount = Decimal(str(item_data.get("discount_amount", 0)))
            item_tax = Decimal("0")
            
            if tax_percentage:
                item_tax = (unit_price * quantity - item_discount) * Decimal(str(tax_percentage)) / 100
            
            item_total = (unit_price * quantity) - item_discount + item_tax
            subtotal += item_total
            
            order_item = OrderItem(
                order_id=order.id,
                product_variant_id=variant.id,
                product_name=variant.product.name if variant.product else "Unknown",
                product_sku=variant.sku,
                variant_name=variant.name,
                quantity=quantity,
                unit_price=unit_price,
                discount_amount=item_discount,
                tax_amount=item_tax,
                total_price=item_total,
                cost_price=variant.cost_price
            )
            self.db.add(order_item)
            await self.db.flush()
            
            # Reserve inventory if requested
            if reserve_inventory:
                await self._create_inventory_reservation(
                    order_id=order.id,
                    order_item_id=order_item.id,
                    product_variant_id=variant.id,
                    quantity=quantity
                )
        
        # Calculate totals
        order.subtotal = subtotal
        order.tax_amount = Decimal("0")
        if tax_percentage:
            order.tax_percentage = tax_percentage
            order.tax_amount = subtotal * Decimal(str(tax_percentage)) / 100
        
        order.total_amount = subtotal - discount_amount + order.tax_amount + shipping_amount
        
        # Create history entry
        await self._create_history_entry(
            order_id=order.id,
            action=OrderHistoryAction.CREATED,
            description=f"Order {order_number} created via {channel.value} channel",
            performed_by_id=user_id,
            new_status=OrderStatus.DRAFT.value,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self.db.commit()
        await self.db.refresh(order)
        
        logger.info(f"Created order {order_number} for channel {channel.value}")
        return order
    
    async def update_order_status(
        self,
        order_id: UUID,
        new_status: OrderStatus,
        user_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Order:
        """
        Update order status with validation and history tracking.
        
        Args:
            order_id: Order ID to update
            new_status: New status to set
            user_id: User performing the update
            notes: Optional notes for the status change
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Updated Order object
            
        Raises:
            ValueError: If transition is invalid
        """
        order = await self._get_order_with_details(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        old_status = order.status
        
        # Validate transition
        if not self._is_valid_status_transition(old_status, new_status):
            raise ValueError(
                f"Invalid status transition from {old_status.value} to {new_status.value}"
            )
        
        # Update status
        order.status = new_status
        
        # Set timestamps based on status
        now = datetime.utcnow()
        if new_status == OrderStatus.CONFIRMED:
            order.confirmed_at = now
        elif new_status == OrderStatus.SHIPPED:
            order.shipped_at = now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now
            # Release inventory reservations
            await self.release_order_reservations(order_id)
        
        # Determine action type
        action_map = {
            OrderStatus.CONFIRMED: OrderHistoryAction.CONFIRMED,
            OrderStatus.PROCESSING: OrderHistoryAction.PROCESSING_STARTED,
            OrderStatus.SHIPPED: OrderHistoryAction.SHIPPED,
            OrderStatus.DELIVERED: OrderHistoryAction.DELIVERED,
            OrderStatus.CANCELLED: OrderHistoryAction.CANCELLED,
            OrderStatus.REFUNDED: OrderHistoryAction.REFUNDED,
            OrderStatus.RETURN_REQUESTED: OrderHistoryAction.RETURN_REQUESTED,
            OrderStatus.RETURNED: OrderHistoryAction.RETURNED,
        }
        action = action_map.get(new_status, OrderHistoryAction.STATUS_CHANGED)
        
        # Create history entry
        description = f"Order status changed from {old_status.value} to {new_status.value}"
        if notes:
            description += f". Notes: {notes}"
        
        await self._create_history_entry(
            order_id=order_id,
            action=action,
            description=description,
            performed_by_id=user_id,
            old_status=old_status.value,
            new_status=new_status.value,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self.db.commit()
        await self.db.refresh(order)
        
        logger.info(f"Order {order.order_number} status changed: {old_status.value} -> {new_status.value}")
        return order
    
    async def cancel_order(
        self,
        order_id: UUID,
        reason: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Order:
        """
        Cancel an order with inventory release and history tracking.
        
        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason
            user_id: User performing the cancellation
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Cancelled Order object
        """
        order = await self._get_order_with_details(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED, OrderStatus.COMPLETED]:
            raise ValueError(f"Cannot cancel order in {order.status.value} status")
        
        old_status = order.status
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()
        
        # Release inventory reservations
        released_count = await self.release_order_reservations(order_id)
        
        # Create history entry
        await self._create_history_entry(
            order_id=order_id,
            action=OrderHistoryAction.CANCELLED,
            description=f"Order cancelled. Reason: {reason}. Released {released_count} inventory reservations.",
            performed_by_id=user_id,
            old_status=old_status.value,
            new_status=OrderStatus.CANCELLED.value,
            additional_data={"reason": reason, "reservations_released": released_count},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self.db.commit()
        await self.db.refresh(order)
        
        logger.info(f"Order {order.order_number} cancelled: {reason}")
        return order
    
    async def confirm_order(
        self,
        order_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Order:
        """Confirm a draft or pending order"""
        return await self.update_order_status(
            order_id=order_id,
            new_status=OrderStatus.CONFIRMED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    # =========================================================================
    # Order Search and Retrieval
    # =========================================================================
    
    async def get_order(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID with all related data"""
        return await self._get_order_with_details(order_id)
    
    async def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number"""
        query = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.history),
                selectinload(Order.notes),
                selectinload(Order.fulfillments),
                selectinload(Order.inventory_reservations)
            )
            .where(Order.order_number == order_number)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search_orders(
        self,
        filters: OrderSearchFilters
    ) -> Tuple[List[Order], int]:
        """
        Search orders with comprehensive filtering and pagination.
        
        Args:
            filters: Search filters and pagination options
            
        Returns:
            Tuple of (orders list, total count)
        """
        query = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.fulfillments)
        )
        count_query = select(func.count(Order.id))
        
        # Apply filters
        conditions = []
        
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    Order.order_number.ilike(search_term),
                    Order.customer_name.ilike(search_term),
                    Order.customer_email.ilike(search_term)
                )
            )
        
        if filters.statuses:
            conditions.append(Order.status.in_(filters.statuses))
        
        if filters.payment_statuses:
            conditions.append(Order.payment_status.in_(filters.payment_statuses))
        
        if filters.channels:
            conditions.append(Order.channel.in_(filters.channels))
        
        if filters.from_date:
            conditions.append(Order.created_at >= filters.from_date)
        
        if filters.to_date:
            conditions.append(Order.created_at <= filters.to_date)
        
        if filters.customer_id:
            conditions.append(Order.customer_id == filters.customer_id)
        
        if filters.customer_email:
            conditions.append(Order.customer_email == filters.customer_email)
        
        if filters.min_amount:
            conditions.append(Order.total_amount >= filters.min_amount)
        
        if filters.max_amount:
            conditions.append(Order.total_amount <= filters.max_amount)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(Order, filters.sort_by, Order.created_at)
        if filters.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)
        
        result = await self.db.execute(query)
        orders = list(result.scalars().all())
        
        return orders, total
    
    async def get_orders_by_customer(
        self,
        customer_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[Order]:
        """Get orders for a specific customer"""
        query = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(desc(Order.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_orders_by_status(
        self,
        status: OrderStatus,
        skip: int = 0,
        limit: int = 20
    ) -> List[Order]:
        """Get orders by status"""
        query = (
            select(Order)
            .where(Order.status == status)
            .order_by(desc(Order.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # =========================================================================
    # Order Notes
    # =========================================================================
    
    async def add_order_note(
        self,
        order_id: UUID,
        note: str,
        is_internal: bool = True,
        notify_customer: bool = False,
        user_id: Optional[UUID] = None
    ) -> OrderNote:
        """
        Add a note to an order.
        
        Args:
            order_id: Order ID
            note: Note content
            is_internal: Whether the note is internal only
            notify_customer: Whether to notify customer
            user_id: User adding the note
            
        Returns:
            Created OrderNote
        """
        # Verify order exists
        order = await self.db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        note_obj = OrderNote(
            order_id=order_id,
            note=note,
            is_internal=is_internal,
            notify_customer=notify_customer,
            created_by_id=user_id
        )
        
        self.db.add(note_obj)
        
        # Create history entry
        await self._create_history_entry(
            order_id=order_id,
            action=OrderHistoryAction.NOTE_ADDED,
            description=f"{'Internal' if is_internal else 'Customer'} note added",
            performed_by_id=user_id,
            additional_data={"note_preview": note[:100]}
        )
        
        await self.db.commit()
        await self.db.refresh(note_obj)
        
        return note_obj
    
    async def get_order_notes(
        self,
        order_id: UUID,
        include_internal: bool = True
    ) -> List[OrderNote]:
        """Get all notes for an order"""
        return list(await self.note_repo.get_by_order(
            order_id=order_id,
            include_internal=include_internal
        ))
    
    async def update_order_note(
        self,
        note_id: UUID,
        note_update: OrderNoteUpdate
    ) -> Optional[OrderNote]:
        """Update an order note"""
        return await self.note_repo.update(note_id, note_update)
    
    async def delete_order_note(self, note_id: UUID) -> bool:
        """Delete an order note"""
        note = await self.note_repo.get(note_id)
        if note:
            await self.note_repo.delete(note_id)
            await self.db.commit()
            return True
        return False
    
    # =========================================================================
    # Order History
    # =========================================================================
    
    async def get_order_history(
        self,
        order_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[OrderHistory]:
        """Get history entries for an order"""
        return list(await self.history_repo.get_by_order(
            order_id=order_id,
            skip=skip,
            limit=limit
        ))
    
    # =========================================================================
    # Fulfillment Management
    # =========================================================================
    
    async def create_fulfillment(
        self,
        order_id: UUID,
        items: Dict[str, int],
        warehouse_location: Optional[str] = None,
        assigned_to_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> OrderFulfillment:
        """
        Create a fulfillment for an order.
        
        Args:
            order_id: Order ID
            items: Dict mapping order_item_id to quantity
            warehouse_location: Warehouse location
            assigned_to_id: User assigned to fulfill
            user_id: User creating the fulfillment
            
        Returns:
            Created OrderFulfillment
        """
        # Verify order exists and is in valid status
        order = await self._get_order_with_details(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status not in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            raise ValueError(
                f"Cannot create fulfillment for order in {order.status.value} status"
            )
        
        # Generate fulfillment number
        fulfillment_number = await self.fulfillment_repo.generate_fulfillment_number()
        
        fulfillment = OrderFulfillment(
            order_id=order_id,
            fulfillment_number=fulfillment_number,
            status=FulfillmentStatus.PENDING,
            warehouse_location=warehouse_location,
            assigned_to_id=assigned_to_id,
            items=items,
            assigned_at=datetime.utcnow() if assigned_to_id else None
        )
        
        self.db.add(fulfillment)
        
        # Update order status to processing if confirmed
        if order.status == OrderStatus.CONFIRMED:
            order.status = OrderStatus.PROCESSING
        
        # Create history entry
        await self._create_history_entry(
            order_id=order_id,
            action=OrderHistoryAction.ASSIGNED,
            description=f"Fulfillment {fulfillment_number} created",
            performed_by_id=user_id,
            additional_data={
                "fulfillment_number": fulfillment_number,
                "assigned_to_id": str(assigned_to_id) if assigned_to_id else None
            }
        )
        
        await self.db.commit()
        await self.db.refresh(fulfillment)
        
        logger.info(f"Created fulfillment {fulfillment_number} for order {order.order_number}")
        return fulfillment
    
    async def update_fulfillment_status(
        self,
        fulfillment_id: UUID,
        new_status: FulfillmentStatus,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Optional[OrderFulfillment]:
        """
        Update fulfillment status with workflow management.
        
        Args:
            fulfillment_id: Fulfillment ID
            new_status: New status
            notes: Optional notes
            user_id: User updating the status
            
        Returns:
            Updated OrderFulfillment
        """
        fulfillment = await self.fulfillment_repo.get(fulfillment_id)
        if not fulfillment:
            raise ValueError(f"Fulfillment {fulfillment_id} not found")
        
        old_status = fulfillment.status
        
        # Update status with timestamps
        fulfillment = await self.fulfillment_repo.update_status(
            fulfillment_id=fulfillment_id,
            new_status=new_status,
            notes=notes
        )
        
        # Create history entry
        await self._create_history_entry(
            order_id=fulfillment.order_id,
            action=OrderHistoryAction.STATUS_CHANGED,
            description=f"Fulfillment {fulfillment.fulfillment_number} status: {old_status.value} -> {new_status.value}",
            performed_by_id=user_id,
            additional_data={
                "fulfillment_number": fulfillment.fulfillment_number,
                "old_status": old_status.value,
                "new_status": new_status.value
            }
        )
        
        # Update order status based on fulfillment status
        if new_status == FulfillmentStatus.READY_TO_SHIP:
            order = await self.db.get(Order, fulfillment.order_id)
            if order and order.status == OrderStatus.PROCESSING:
                order.status = OrderStatus.READY_TO_SHIP
        elif new_status == FulfillmentStatus.SHIPPED:
            order = await self.db.get(Order, fulfillment.order_id)
            if order:
                order.status = OrderStatus.SHIPPED
                order.shipped_at = datetime.utcnow()
        elif new_status == FulfillmentStatus.FULFILLED:
            # Check if all fulfillments are complete
            await self._check_order_fulfillment_complete(fulfillment.order_id)
        
        await self.db.commit()
        return fulfillment
    
    async def get_order_fulfillments(self, order_id: UUID) -> List[OrderFulfillment]:
        """Get all fulfillments for an order"""
        return list(await self.fulfillment_repo.get_by_order(order_id))
    
    async def get_pending_fulfillments(
        self,
        skip: int = 0,
        limit: int = 20
    ) -> List[OrderFulfillment]:
        """Get all pending fulfillments"""
        return list(await self.fulfillment_repo.get_by_status(
            FulfillmentStatus.PENDING,
            skip=skip,
            limit=limit
        ))
    
    async def assign_fulfillment(
        self,
        fulfillment_id: UUID,
        assigned_to_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[OrderFulfillment]:
        """Assign a fulfillment to a warehouse staff member"""
        fulfillment = await self.fulfillment_repo.get(fulfillment_id)
        if not fulfillment:
            raise ValueError(f"Fulfillment {fulfillment_id} not found")
        
        fulfillment.assigned_to_id = assigned_to_id
        fulfillment.assigned_at = datetime.utcnow()
        
        await self._create_history_entry(
            order_id=fulfillment.order_id,
            action=OrderHistoryAction.ASSIGNED,
            description=f"Fulfillment {fulfillment.fulfillment_number} assigned",
            performed_by_id=user_id,
            additional_data={
                "fulfillment_number": fulfillment.fulfillment_number,
                "assigned_to_id": str(assigned_to_id)
            }
        )
        
        await self.db.commit()
        await self.db.refresh(fulfillment)
        return fulfillment
    
    async def get_fulfillment_stats(self) -> OrderFulfillmentStats:
        """Get fulfillment statistics"""
        stats_dict = await self.fulfillment_repo.get_statistics()
        return OrderFulfillmentStats(
            pending=stats_dict.get("pending", 0),
            picking=stats_dict.get("picking", 0),
            packing=stats_dict.get("packing", 0),
            ready_to_ship=stats_dict.get("ready_to_ship", 0),
            shipped=stats_dict.get("shipped", 0),
            partially_fulfilled=stats_dict.get("partially_fulfilled", 0),
            fulfilled=stats_dict.get("fulfilled", 0),
            cancelled=stats_dict.get("cancelled", 0),
            total=stats_dict.get("total", 0)
        )
    
    # =========================================================================
    # Inventory Reservation Management
    # =========================================================================
    
    async def create_reservation(
        self,
        order_id: UUID,
        order_item_id: UUID,
        product_variant_id: UUID,
        quantity: int,
        stock_location_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None
    ) -> InventoryReservation:
        """Create an inventory reservation"""
        return await self._create_inventory_reservation(
            order_id=order_id,
            order_item_id=order_item_id,
            product_variant_id=product_variant_id,
            quantity=quantity,
            stock_location_id=stock_location_id,
            expires_at=expires_at
        )
    
    async def release_reservation(
        self,
        reservation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[InventoryReservation]:
        """Release a single inventory reservation"""
        reservation = await self.reservation_repo.release_reservation(reservation_id)
        
        if reservation:
            await self._create_history_entry(
                order_id=reservation.order_id,
                action=OrderHistoryAction.INVENTORY_RELEASED,
                description=f"Inventory reservation released for variant {reservation.product_variant_id}",
                performed_by_id=user_id,
                additional_data={
                    "product_variant_id": str(reservation.product_variant_id),
                    "quantity_released": reservation.quantity_reserved
                }
            )
            await self.db.commit()
        
        return reservation
    
    async def release_order_reservations(self, order_id: UUID) -> int:
        """Release all inventory reservations for an order"""
        count = await self.reservation_repo.release_order_reservations(order_id)
        
        if count > 0:
            await self._create_history_entry(
                order_id=order_id,
                action=OrderHistoryAction.INVENTORY_RELEASED,
                description=f"Released {count} inventory reservations",
                additional_data={"reservations_released": count}
            )
        
        return count
    
    async def fulfill_reservation(
        self,
        reservation_id: UUID,
        quantity_fulfilled: int,
        user_id: Optional[UUID] = None
    ) -> Optional[InventoryReservation]:
        """Mark reservation as fulfilled (partially or fully)"""
        reservation = await self.reservation_repo.fulfill_reservation(
            reservation_id=reservation_id,
            quantity_fulfilled=quantity_fulfilled
        )
        
        if reservation:
            await self.db.commit()
        
        return reservation
    
    async def get_order_reservations(
        self,
        order_id: UUID
    ) -> List[InventoryReservation]:
        """Get all reservations for an order"""
        return list(await self.reservation_repo.get_by_order(order_id))
    
    async def get_active_reservations(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[InventoryReservation]:
        """Get all active reservations"""
        return list(await self.reservation_repo.get_active_reservations(skip, limit))
    
    async def cleanup_expired_reservations(self) -> int:
        """Release expired reservations"""
        expired = await self.reservation_repo.get_expired_reservations()
        count = 0
        
        for reservation in expired:
            await self.reservation_repo.release_reservation(reservation.id)
            count += 1
        
        if count > 0:
            await self.db.commit()
            logger.info(f"Released {count} expired inventory reservations")
        
        return count
    
    # =========================================================================
    # Bulk Operations
    # =========================================================================
    
    async def bulk_update_status(
        self,
        update_data: BulkOrderStatusUpdate,
        user_id: Optional[UUID] = None
    ) -> BulkOperationResult:
        """Update status for multiple orders"""
        result = BulkOperationResult(
            success_count=0,
            failure_count=0,
            failed_ids=[],
            errors=[]
        )
        
        new_status = OrderStatus(update_data.new_status)
        
        for order_id in update_data.order_ids:
            try:
                await self.update_order_status(
                    order_id=order_id,
                    new_status=new_status,
                    user_id=user_id,
                    notes=update_data.notes
                )
                result.success_count += 1
            except Exception as e:
                result.failure_count += 1
                result.failed_ids.append(order_id)
                result.errors.append(f"Order {order_id}: {str(e)}")
        
        return result
    
    async def bulk_assign_orders(
        self,
        assignment_data: BulkOrderAssignment,
        user_id: Optional[UUID] = None
    ) -> BulkOperationResult:
        """Assign multiple orders to a sales rep or fulfillment staff"""
        result = BulkOperationResult(
            success_count=0,
            failure_count=0,
            failed_ids=[],
            errors=[]
        )
        
        for order_id in assignment_data.order_ids:
            try:
                order = await self.db.get(Order, order_id)
                if not order:
                    raise ValueError("Order not found")
                
                order.sales_rep_id = assignment_data.assigned_to_id
                
                await self._create_history_entry(
                    order_id=order_id,
                    action=OrderHistoryAction.ASSIGNED,
                    description=f"Order assigned to user {assignment_data.assigned_to_id}",
                    performed_by_id=user_id,
                    additional_data={"assigned_to_id": str(assignment_data.assigned_to_id)}
                )
                
                result.success_count += 1
            except Exception as e:
                result.failure_count += 1
                result.failed_ids.append(order_id)
                result.errors.append(f"Order {order_id}: {str(e)}")
        
        await self.db.commit()
        return result
    
    # =========================================================================
    # Dashboard and Analytics
    # =========================================================================
    
    async def get_dashboard(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> OrderManagementDashboard:
        """Get order management dashboard data"""
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=30)
        if not to_date:
            to_date = datetime.utcnow()
        
        # Get order counts by status
        status_query = (
            select(Order.status, func.count(Order.id))
            .where(and_(
                Order.created_at >= from_date,
                Order.created_at <= to_date
            ))
            .group_by(Order.status)
        )
        status_result = await self.db.execute(status_query)
        order_counts = [
            OrderStatusCount(status=row[0].value, count=row[1])
            for row in status_result
        ]
        
        # Get financial summary
        financial_query = (
            select(
                func.count(Order.id).label('total'),
                func.sum(Order.total_amount).label('total_revenue'),
                func.sum(
                    func.case(
                        (Order.payment_status == PaymentStatus.PENDING, Order.total_amount),
                        else_=0
                    )
                ).label('pending_amount'),
                func.sum(
                    func.case(
                        (Order.payment_status == PaymentStatus.PAID, Order.total_amount),
                        else_=0
                    )
                ).label('paid_amount')
            )
            .where(and_(
                Order.created_at >= from_date,
                Order.created_at <= to_date
            ))
        )
        financial_result = await self.db.execute(financial_query)
        financial_row = financial_result.first()
        
        # Get fulfillment stats
        fulfillment_stats = await self.get_fulfillment_stats()
        
        # Get recent orders count (last 24 hours)
        recent_query = (
            select(func.count(Order.id))
            .where(Order.created_at >= datetime.utcnow() - timedelta(hours=24))
        )
        recent_result = await self.db.execute(recent_query)
        recent_orders_count = recent_result.scalar() or 0
        
        # Get pending fulfillments count
        pending_fulfillments_query = (
            select(func.count(OrderFulfillment.id))
            .where(OrderFulfillment.status == FulfillmentStatus.PENDING)
        )
        pending_result = await self.db.execute(pending_fulfillments_query)
        pending_fulfillments_count = pending_result.scalar() or 0
        
        return OrderManagementDashboard(
            order_counts=order_counts,
            total_orders=financial_row.total if financial_row else 0,
            total_revenue=financial_row.total_revenue or Decimal("0") if financial_row else Decimal("0"),
            pending_amount=financial_row.pending_amount or Decimal("0") if financial_row else Decimal("0"),
            paid_amount=financial_row.paid_amount or Decimal("0") if financial_row else Decimal("0"),
            fulfillment_stats=fulfillment_stats,
            recent_orders_count=recent_orders_count,
            pending_fulfillments_count=pending_fulfillments_count,
            low_stock_alerts_count=0,  # Would need inventory service integration
            from_date=from_date,
            to_date=to_date
        )
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    async def _generate_order_number(self, channel: SalesChannel) -> str:
        """Generate unique order number based on channel"""
        today = datetime.utcnow()
        prefix_map = {
            SalesChannel.WHOLESALE: "WS",
            SalesChannel.RETAIL: "RT",
            SalesChannel.ECOMMERCE: "EC",
            SalesChannel.MARKETPLACE: "MP"
        }
        prefix = prefix_map.get(channel, "ORD")
        
        # Count today's orders
        count_query = (
            select(func.count(Order.id))
            .where(func.date(Order.created_at) == today.date())
        )
        result = await self.db.execute(count_query)
        count = result.scalar() or 0
        
        return f"{prefix}-{today.strftime('%Y%m%d')}-{count + 1:05d}"
    
    async def _get_order_with_details(self, order_id: UUID) -> Optional[Order]:
        """Get order with all related data loaded"""
        query = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.history),
                selectinload(Order.notes),
                selectinload(Order.fulfillments),
                selectinload(Order.inventory_reservations)
            )
            .where(Order.id == order_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    def _is_valid_status_transition(
        self,
        current_status: OrderStatus,
        new_status: OrderStatus
    ) -> bool:
        """Check if a status transition is valid"""
        valid_transitions = ORDER_STATUS_TRANSITIONS.get(current_status, [])
        return new_status in valid_transitions
    
    async def _create_history_entry(
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
        """Create an order history entry"""
        return await self.history_repo.create_history_entry(
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
    
    async def _create_inventory_reservation(
        self,
        order_id: UUID,
        order_item_id: UUID,
        product_variant_id: UUID,
        quantity: int,
        stock_location_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None
    ) -> InventoryReservation:
        """Create an inventory reservation"""
        if not expires_at:
            expires_at = datetime.utcnow() + timedelta(days=7)
        
        reservation = InventoryReservation(
            order_id=order_id,
            order_item_id=order_item_id,
            product_variant_id=product_variant_id,
            stock_location_id=stock_location_id,
            quantity_reserved=quantity,
            quantity_fulfilled=0,
            is_active=True,
            expires_at=expires_at
        )
        
        self.db.add(reservation)
        await self.db.flush()
        
        # Create history entry
        await self._create_history_entry(
            order_id=order_id,
            action=OrderHistoryAction.INVENTORY_RESERVED,
            description=f"Reserved {quantity} units of variant {product_variant_id}",
            additional_data={
                "product_variant_id": str(product_variant_id),
                "quantity_reserved": quantity,
                "expires_at": expires_at.isoformat()
            }
        )
        
        return reservation
    
    async def _check_order_fulfillment_complete(self, order_id: UUID) -> bool:
        """Check if all fulfillments for an order are complete"""
        fulfillments = await self.fulfillment_repo.get_by_order(order_id)
        
        if not fulfillments:
            return False
        
        all_fulfilled = all(
            f.status in [FulfillmentStatus.FULFILLED, FulfillmentStatus.SHIPPED]
            for f in fulfillments
        )
        
        if all_fulfilled:
            order = await self.db.get(Order, order_id)
            if order and order.status not in [OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
                order.status = OrderStatus.DELIVERED
                order.delivered_at = datetime.utcnow()
        
        return all_fulfilled


# Factory function for dependency injection
def get_order_management_service(db: AsyncSession) -> OrderManagementService:
    """Factory function to create OrderManagementService instance"""
    return OrderManagementService(db)


__all__ = [
    "OrderManagementService",
    "get_order_management_service",
    "ORDER_STATUS_TRANSITIONS"
]
