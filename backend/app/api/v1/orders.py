"""
Order Management API Endpoints

Unified API for order management operations including:
- Order CRUD and status management
- Order history and notes
- Fulfillment workflow
- Inventory reservations
- Dashboard and analytics
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.models.order import OrderStatus, SalesChannel, PaymentMethod
from app.models.order_management import FulfillmentStatus, OrderHistoryAction
from app.services.order_management import OrderManagementService, get_order_management_service
from app.schemas.order_management import (
    OrderHistoryResponse,
    OrderHistoryList,
    OrderNoteCreate,
    OrderNoteUpdate,
    OrderNoteResponse,
    OrderNoteList,
    OrderFulfillmentCreate,
    OrderFulfillmentUpdate,
    OrderFulfillmentStatusUpdate,
    OrderFulfillmentResponse,
    OrderFulfillmentList,
    OrderFulfillmentStats,
    InventoryReservationResponse,
    InventoryReservationList,
    OrderManagementDashboard,
    OrderSearchFilters,
    BulkOrderStatusUpdate,
    BulkOrderAssignment,
    BulkOperationResult
)


router = APIRouter(prefix="/orders", tags=["Order Management"])


# =============================================================================
# Dependency
# =============================================================================

async def get_service(db: AsyncSession = Depends(get_db)) -> OrderManagementService:
    """Get order management service instance"""
    return get_order_management_service(db)


# =============================================================================
# Order Schemas (Local definitions for API)
# =============================================================================

from pydantic import BaseModel, Field
from typing import Any


class OrderItemCreate(BaseModel):
    """Schema for creating an order item"""
    product_variant_id: UUID
    quantity: int = Field(..., gt=0)
    unit_price: Optional[Decimal] = None
    discount_amount: Decimal = Decimal("0")


class OrderCreate(BaseModel):
    """Schema for creating an order"""
    channel: SalesChannel
    items: List[OrderItemCreate] = Field(..., min_length=1)
    customer_id: Optional[UUID] = None
    wholesale_customer_id: Optional[UUID] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    payment_terms: Optional[str] = None
    discount_amount: Decimal = Decimal("0")
    discount_code: Optional[str] = None
    tax_percentage: Optional[float] = None
    shipping_amount: Decimal = Decimal("0")
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    reference_number: Optional[str] = None
    source: Optional[str] = None
    reserve_inventory: bool = True


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: OrderStatus
    notes: Optional[str] = None


class OrderCancellation(BaseModel):
    """Schema for cancelling an order"""
    reason: str = Field(..., min_length=1, max_length=500)


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: UUID
    order_number: str
    channel: SalesChannel
    status: OrderStatus
    customer_id: Optional[UUID]
    wholesale_customer_id: Optional[UUID]
    customer_name: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    payment_status: str
    payment_method: Optional[str]
    order_date: datetime
    confirmed_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Counts for related data
    items_count: int = 0
    notes_count: int = 0
    fulfillments_count: int = 0
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Schema for paginated order list"""
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Order CRUD Endpoints
# =============================================================================

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    request: Request,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new order.
    
    Creates an order with the specified items, optionally reserving inventory.
    Supports all sales channels (wholesale, retail, e-commerce).
    """
    try:
        # Convert items to dict format
        items = [
            {
                "product_variant_id": item.product_variant_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_amount": item.discount_amount
            }
            for item in order_data.items
        ]
        
        order = await service.create_order(
            channel=order_data.channel,
            items=items,
            customer_id=order_data.customer_id,
            wholesale_customer_id=order_data.wholesale_customer_id,
            customer_name=order_data.customer_name,
            customer_email=order_data.customer_email,
            customer_phone=order_data.customer_phone,
            payment_method=order_data.payment_method,
            payment_terms=order_data.payment_terms,
            discount_amount=order_data.discount_amount,
            discount_code=order_data.discount_code,
            tax_percentage=order_data.tax_percentage,
            shipping_amount=order_data.shipping_amount,
            customer_notes=order_data.customer_notes,
            internal_notes=order_data.internal_notes,
            reference_number=order_data.reference_number,
            source=order_data.source,
            reserve_inventory=order_data.reserve_inventory,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return OrderResponse(
            **order.__dict__,
            items_count=len(order.items) if order.items else 0,
            notes_count=len(order.notes) if order.notes else 0,
            fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    search: Optional[str] = None,
    statuses: Optional[str] = Query(None, description="Comma-separated statuses"),
    channels: Optional[str] = Query(None, description="Comma-separated channels"),
    payment_statuses: Optional[str] = Query(None, description="Comma-separated payment statuses"),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    customer_id: Optional[UUID] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    List orders with filtering, sorting, and pagination.
    
    Supports filtering by:
    - Text search (order number, customer name, email)
    - Status, payment status, channel
    - Date range
    - Customer ID
    - Amount range
    """
    filters = OrderSearchFilters(
        search=search,
        statuses=statuses.split(",") if statuses else None,
        channels=channels.split(",") if channels else None,
        payment_statuses=payment_statuses.split(",") if payment_statuses else None,
        from_date=from_date,
        to_date=to_date,
        customer_id=customer_id,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    orders, total = await service.search_orders(filters)
    
    return OrderListResponse(
        items=[
            OrderResponse(
                **order.__dict__,
                items_count=len(order.items) if order.items else 0,
                notes_count=0,
                fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
            )
            for order in orders
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/dashboard", response_model=OrderManagementDashboard)
async def get_dashboard(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get order management dashboard with analytics.
    
    Returns:
    - Order counts by status
    - Financial summary (revenue, pending, paid)
    - Fulfillment statistics
    - Recent activity counts
    """
    return await service.get_dashboard(from_date=from_date, to_date=to_date)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get order details by ID"""
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    
    return OrderResponse(
        **order.__dict__,
        items_count=len(order.items) if order.items else 0,
        notes_count=len(order.notes) if order.notes else 0,
        fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
    )


@router.get("/number/{order_number}", response_model=OrderResponse)
async def get_order_by_number(
    order_number: str,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get order details by order number"""
    order = await service.get_order_by_number(order_number)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_number} not found"
        )
    
    return OrderResponse(
        **order.__dict__,
        items_count=len(order.items) if order.items else 0,
        notes_count=len(order.notes) if order.notes else 0,
        fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
    )


# =============================================================================
# Order Status Management
# =============================================================================

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    request: Request,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update order status.
    
    Validates status transitions and creates history entry.
    """
    try:
        order = await service.update_order_status(
            order_id=order_id,
            new_status=status_update.status,
            user_id=current_user.id,
            notes=status_update.notes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return OrderResponse(
            **order.__dict__,
            items_count=len(order.items) if order.items else 0,
            notes_count=len(order.notes) if order.notes else 0,
            fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/confirm", response_model=OrderResponse)
async def confirm_order(
    order_id: UUID,
    request: Request,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Confirm a draft or pending order"""
    try:
        order = await service.confirm_order(
            order_id=order_id,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return OrderResponse(
            **order.__dict__,
            items_count=len(order.items) if order.items else 0,
            notes_count=len(order.notes) if order.notes else 0,
            fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    cancellation: OrderCancellation,
    request: Request,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel an order.
    
    Releases inventory reservations and records cancellation reason.
    """
    try:
        order = await service.cancel_order(
            order_id=order_id,
            reason=cancellation.reason,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return OrderResponse(
            **order.__dict__,
            items_count=len(order.items) if order.items else 0,
            notes_count=len(order.notes) if order.notes else 0,
            fulfillments_count=len(order.fulfillments) if order.fulfillments else 0
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Order History
# =============================================================================

@router.get("/{order_id}/history", response_model=OrderHistoryList)
async def get_order_history(
    order_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get order history/audit trail"""
    skip = (page - 1) * page_size
    history = await service.get_order_history(order_id, skip=skip, limit=page_size)
    
    return OrderHistoryList(
        items=[OrderHistoryResponse.model_validate(h) for h in history],
        total=len(history),
        page=page,
        page_size=page_size
    )


# =============================================================================
# Order Notes
# =============================================================================

@router.get("/{order_id}/notes", response_model=OrderNoteList)
async def get_order_notes(
    order_id: UUID,
    include_internal: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get notes for an order"""
    notes = await service.get_order_notes(order_id, include_internal=include_internal)
    
    return OrderNoteList(
        items=[OrderNoteResponse.model_validate(n) for n in notes],
        total=len(notes),
        page=page,
        page_size=page_size
    )


@router.post("/{order_id}/notes", response_model=OrderNoteResponse, status_code=status.HTTP_201_CREATED)
async def add_order_note(
    order_id: UUID,
    note_data: OrderNoteCreate,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Add a note to an order"""
    try:
        note = await service.add_order_note(
            order_id=order_id,
            note=note_data.note,
            is_internal=note_data.is_internal,
            notify_customer=note_data.notify_customer,
            user_id=current_user.id
        )
        return OrderNoteResponse.model_validate(note)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/notes/{note_id}", response_model=OrderNoteResponse)
async def update_order_note(
    note_id: UUID,
    note_update: OrderNoteUpdate,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update an order note"""
    note = await service.update_order_note(note_id, note_update)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found"
        )
    return OrderNoteResponse.model_validate(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order_note(
    note_id: UUID,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an order note"""
    success = await service.delete_order_note(note_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found"
        )


# =============================================================================
# Order Fulfillment
# =============================================================================

@router.get("/fulfillments/pending", response_model=OrderFulfillmentList)
async def get_pending_fulfillments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all pending fulfillments"""
    skip = (page - 1) * page_size
    fulfillments = await service.get_pending_fulfillments(skip=skip, limit=page_size)
    
    return OrderFulfillmentList(
        items=[OrderFulfillmentResponse.model_validate(f) for f in fulfillments],
        total=len(fulfillments),
        page=page,
        page_size=page_size
    )


@router.get("/fulfillments/stats", response_model=OrderFulfillmentStats)
async def get_fulfillment_stats(
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get fulfillment statistics"""
    return await service.get_fulfillment_stats()


@router.get("/{order_id}/fulfillments", response_model=OrderFulfillmentList)
async def get_order_fulfillments(
    order_id: UUID,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get fulfillments for an order"""
    fulfillments = await service.get_order_fulfillments(order_id)
    
    return OrderFulfillmentList(
        items=[OrderFulfillmentResponse.model_validate(f) for f in fulfillments],
        total=len(fulfillments),
        page=1,
        page_size=len(fulfillments)
    )


class FulfillmentCreateRequest(BaseModel):
    """Request schema for creating fulfillment"""
    items: dict  # {order_item_id: quantity}
    warehouse_location: Optional[str] = None
    assigned_to_id: Optional[UUID] = None


@router.post("/{order_id}/fulfillments", response_model=OrderFulfillmentResponse, status_code=status.HTTP_201_CREATED)
async def create_fulfillment(
    order_id: UUID,
    fulfillment_data: FulfillmentCreateRequest,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a fulfillment for an order.
    
    Starts the warehouse fulfillment workflow (picking -> packing -> shipping).
    """
    try:
        fulfillment = await service.create_fulfillment(
            order_id=order_id,
            items=fulfillment_data.items,
            warehouse_location=fulfillment_data.warehouse_location,
            assigned_to_id=fulfillment_data.assigned_to_id,
            user_id=current_user.id
        )
        return OrderFulfillmentResponse.model_validate(fulfillment)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/fulfillments/{fulfillment_id}/status", response_model=OrderFulfillmentResponse)
async def update_fulfillment_status(
    fulfillment_id: UUID,
    status_update: OrderFulfillmentStatusUpdate,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update fulfillment status.
    
    Supports workflow: pending -> picking -> packing -> ready_to_ship -> shipped -> fulfilled
    """
    try:
        fulfillment = await service.update_fulfillment_status(
            fulfillment_id=fulfillment_id,
            new_status=status_update.status,
            notes=status_update.notes,
            user_id=current_user.id
        )
        
        if not fulfillment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment {fulfillment_id} not found"
            )
        
        return OrderFulfillmentResponse.model_validate(fulfillment)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


class FulfillmentAssignment(BaseModel):
    """Request schema for assigning fulfillment"""
    assigned_to_id: UUID


@router.put("/fulfillments/{fulfillment_id}/assign", response_model=OrderFulfillmentResponse)
async def assign_fulfillment(
    fulfillment_id: UUID,
    assignment: FulfillmentAssignment,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Assign a fulfillment to a warehouse staff member"""
    try:
        fulfillment = await service.assign_fulfillment(
            fulfillment_id=fulfillment_id,
            assigned_to_id=assignment.assigned_to_id,
            user_id=current_user.id
        )
        
        if not fulfillment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fulfillment {fulfillment_id} not found"
            )
        
        return OrderFulfillmentResponse.model_validate(fulfillment)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Inventory Reservations
# =============================================================================

@router.get("/{order_id}/reservations", response_model=InventoryReservationList)
async def get_order_reservations(
    order_id: UUID,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get inventory reservations for an order"""
    reservations = await service.get_order_reservations(order_id)
    
    return InventoryReservationList(
        items=[InventoryReservationResponse.model_validate(r) for r in reservations],
        total=len(reservations),
        page=1,
        page_size=len(reservations)
    )


@router.get("/reservations/active", response_model=InventoryReservationList)
async def get_active_reservations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all active inventory reservations"""
    skip = (page - 1) * page_size
    reservations = await service.get_active_reservations(skip=skip, limit=page_size)
    
    return InventoryReservationList(
        items=[InventoryReservationResponse.model_validate(r) for r in reservations],
        total=len(reservations),
        page=page,
        page_size=page_size
    )


@router.post("/reservations/{reservation_id}/release", response_model=InventoryReservationResponse)
async def release_reservation(
    reservation_id: UUID,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Release an inventory reservation"""
    reservation = await service.release_reservation(
        reservation_id=reservation_id,
        user_id=current_user.id
    )
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} not found"
        )
    
    return InventoryReservationResponse.model_validate(reservation)


@router.post("/reservations/cleanup-expired")
async def cleanup_expired_reservations(
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Clean up expired inventory reservations"""
    count = await service.cleanup_expired_reservations()
    return {"released_count": count, "message": f"Released {count} expired reservations"}


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/bulk/status", response_model=BulkOperationResult)
async def bulk_update_order_status(
    update_data: BulkOrderStatusUpdate,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update status for multiple orders.
    
    Processes each order individually and reports success/failure counts.
    """
    return await service.bulk_update_status(
        update_data=update_data,
        user_id=current_user.id
    )


@router.post("/bulk/assign", response_model=BulkOperationResult)
async def bulk_assign_orders(
    assignment_data: BulkOrderAssignment,
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign multiple orders to a user (sales rep or fulfillment staff).
    
    Processes each order individually and reports success/failure counts.
    """
    return await service.bulk_assign_orders(
        assignment_data=assignment_data,
        user_id=current_user.id
    )


# =============================================================================
# Customer-specific endpoints
# =============================================================================

@router.get("/customer/{customer_id}", response_model=OrderListResponse)
async def get_customer_orders(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all orders for a specific customer"""
    skip = (page - 1) * page_size
    orders = await service.get_orders_by_customer(customer_id, skip=skip, limit=page_size)
    
    return OrderListResponse(
        items=[
            OrderResponse(
                **order.__dict__,
                items_count=0,
                notes_count=0,
                fulfillments_count=0
            )
            for order in orders
        ],
        total=len(orders),
        page=page,
        page_size=page_size
    )


@router.get("/status/{status}", response_model=OrderListResponse)
async def get_orders_by_status(
    status: OrderStatus,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: OrderManagementService = Depends(get_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all orders with a specific status"""
    skip = (page - 1) * page_size
    orders = await service.get_orders_by_status(status, skip=skip, limit=page_size)
    
    return OrderListResponse(
        items=[
            OrderResponse(
                **order.__dict__,
                items_count=0,
                notes_count=0,
                fulfillments_count=0
            )
            for order in orders
        ],
        total=len(orders),
        page=page,
        page_size=page_size
    )


__all__ = ["router"]
