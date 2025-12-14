"""
Order Management Schemas

Pydantic schemas for order management operations including:
- Order history tracking
- Order notes and comments
- Order fulfillment operations
- Inventory reservations
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.order_management import OrderHistoryAction, FulfillmentStatus


# ============================================================================
# Order History Schemas
# ============================================================================

class OrderHistoryBase(BaseModel):
    """Base schema for Order History"""
    action: OrderHistoryAction
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    description: str
    additional_data: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class OrderHistoryCreate(OrderHistoryBase):
    """Schema for creating Order History"""
    order_id: UUID
    performed_by_id: Optional[UUID] = None


class OrderHistoryUpdate(BaseModel):
    """Schema for updating Order History - Limited fields"""
    description: Optional[str] = None
    additional_data: Optional[dict] = None


class OrderHistoryResponse(OrderHistoryBase):
    """Schema for Order History response"""
    id: UUID
    order_id: UUID
    performed_by_id: Optional[UUID]
    created_at: datetime
    
    # Optional related data
    performed_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderHistoryList(BaseModel):
    """Schema for paginated Order History list"""
    items: List[OrderHistoryResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Order Note Schemas
# ============================================================================

class OrderNoteBase(BaseModel):
    """Base schema for Order Note"""
    note: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = True
    notify_customer: bool = False


class OrderNoteCreate(OrderNoteBase):
    """Schema for creating Order Note"""
    order_id: UUID
    created_by_id: Optional[UUID] = None


class OrderNoteUpdate(BaseModel):
    """Schema for updating Order Note"""
    note: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_internal: Optional[bool] = None


class OrderNoteResponse(OrderNoteBase):
    """Schema for Order Note response"""
    id: UUID
    order_id: UUID
    created_by_id: Optional[UUID]
    notified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Optional related data
    created_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderNoteList(BaseModel):
    """Schema for paginated Order Note list"""
    items: List[OrderNoteResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Order Fulfillment Schemas
# ============================================================================

class OrderFulfillmentBase(BaseModel):
    """Base schema for Order Fulfillment"""
    warehouse_location: Optional[str] = None
    items: dict  # {item_id: quantity}
    box_size: Optional[str] = None
    weight: Optional[float] = None
    packing_materials: Optional[dict] = None
    picking_notes: Optional[str] = None
    packing_notes: Optional[str] = None


class OrderFulfillmentCreate(OrderFulfillmentBase):
    """Schema for creating Order Fulfillment"""
    order_id: UUID
    assigned_to_id: Optional[UUID] = None
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if not v or not isinstance(v, dict):
            raise ValueError("Items must be a non-empty dictionary")
        return v


class OrderFulfillmentUpdate(BaseModel):
    """Schema for updating Order Fulfillment"""
    status: Optional[FulfillmentStatus] = None
    warehouse_location: Optional[str] = None
    assigned_to_id: Optional[UUID] = None
    box_size: Optional[str] = None
    weight: Optional[float] = None
    packing_materials: Optional[dict] = None
    picking_notes: Optional[str] = None
    packing_notes: Optional[str] = None


class OrderFulfillmentStatusUpdate(BaseModel):
    """Schema for updating Fulfillment Status"""
    status: FulfillmentStatus
    notes: Optional[str] = None


class OrderFulfillmentResponse(OrderFulfillmentBase):
    """Schema for Order Fulfillment response"""
    id: UUID
    order_id: UUID
    fulfillment_number: str
    status: FulfillmentStatus
    assigned_to_id: Optional[UUID]
    assigned_at: Optional[datetime]
    picking_started_at: Optional[datetime]
    picking_completed_at: Optional[datetime]
    packing_started_at: Optional[datetime]
    packing_completed_at: Optional[datetime]
    shipped_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Optional related data
    assigned_to_name: Optional[str] = None
    order_number: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderFulfillmentList(BaseModel):
    """Schema for paginated Order Fulfillment list"""
    items: List[OrderFulfillmentResponse]
    total: int
    page: int
    page_size: int


class OrderFulfillmentStats(BaseModel):
    """Schema for Fulfillment Statistics"""
    pending: int = 0
    picking: int = 0
    packing: int = 0
    ready_to_ship: int = 0
    shipped: int = 0
    partially_fulfilled: int = 0
    fulfilled: int = 0
    cancelled: int = 0
    total: int = 0


# ============================================================================
# Inventory Reservation Schemas
# ============================================================================

class InventoryReservationBase(BaseModel):
    """Base schema for Inventory Reservation"""
    quantity_reserved: int = Field(..., gt=0)
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None


class InventoryReservationCreate(InventoryReservationBase):
    """Schema for creating Inventory Reservation"""
    order_id: UUID
    order_item_id: UUID
    product_variant_id: UUID
    stock_location_id: Optional[UUID] = None


class InventoryReservationUpdate(BaseModel):
    """Schema for updating Inventory Reservation"""
    quantity_fulfilled: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    expires_at: Optional[datetime] = None


class InventoryReservationRelease(BaseModel):
    """Schema for releasing Inventory Reservation"""
    reason: Optional[str] = None


class InventoryReservationResponse(InventoryReservationBase):
    """Schema for Inventory Reservation response"""
    id: UUID
    order_id: UUID
    order_item_id: UUID
    product_variant_id: UUID
    stock_location_id: Optional[UUID]
    quantity_fulfilled: int
    is_active: bool
    reserved_at: datetime
    released_at: Optional[datetime]
    fulfilled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    quantity_remaining: int
    
    # Optional related data
    product_name: Optional[str] = None
    variant_name: Optional[str] = None
    location_name: Optional[str] = None
    order_number: Optional[str] = None
    
    class Config:
        from_attributes = True


class InventoryReservationList(BaseModel):
    """Schema for paginated Inventory Reservation list"""
    items: List[InventoryReservationResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Order Management Dashboard Schemas
# ============================================================================

class OrderStatusCount(BaseModel):
    """Schema for Order Status Counts"""
    status: str
    count: int


class OrderManagementDashboard(BaseModel):
    """Schema for Order Management Dashboard"""
    # Order Counts by Status
    order_counts: List[OrderStatusCount]
    total_orders: int
    
    # Financial Summary
    total_revenue: Decimal
    pending_amount: Decimal
    paid_amount: Decimal
    
    # Fulfillment Summary
    fulfillment_stats: OrderFulfillmentStats
    
    # Recent Activity
    recent_orders_count: int
    pending_fulfillments_count: int
    low_stock_alerts_count: int
    
    # Time period
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkOrderStatusUpdate(BaseModel):
    """Schema for bulk order status updates"""
    order_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    new_status: str
    notes: Optional[str] = None


class BulkOrderAssignment(BaseModel):
    """Schema for bulk order assignments"""
    order_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    assigned_to_id: UUID
    notes: Optional[str] = None


class BulkOperationResult(BaseModel):
    """Schema for bulk operation results"""
    success_count: int
    failure_count: int
    failed_ids: List[UUID]
    errors: List[str]


# ============================================================================
# Search and Filter Schemas
# ============================================================================

class OrderSearchFilters(BaseModel):
    """Schema for Order Search Filters"""
    # Text search
    search: Optional[str] = None
    
    # Status filters
    statuses: Optional[List[str]] = None
    payment_statuses: Optional[List[str]] = None
    
    # Channel filter
    channels: Optional[List[str]] = None
    
    # Date filters
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    # Customer filters
    customer_id: Optional[UUID] = None
    customer_email: Optional[str] = None
    
    # Amount filters
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    
    # Fulfillment filters
    has_fulfillment: Optional[bool] = None
    fulfillment_status: Optional[FulfillmentStatus] = None
    
    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    
    # Sorting
    sort_by: str = "created_at"
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class OrderManagementStats(BaseModel):
    """Schema for Order Management Statistics"""
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    orders_by_status: dict[str, int]
    orders_by_channel: dict[str, int]
    top_customers: List[dict[str, Any]]
    fulfillment_rate: float
    on_time_delivery_rate: float


__all__ = [
    # Order History
    "OrderHistoryBase",
    "OrderHistoryCreate",
    "OrderHistoryUpdate",
    "OrderHistoryResponse",
    "OrderHistoryList",
    # Order Notes
    "OrderNoteBase",
    "OrderNoteCreate",
    "OrderNoteUpdate",
    "OrderNoteResponse",
    "OrderNoteList",
    # Order Fulfillment
    "OrderFulfillmentBase",
    "OrderFulfillmentCreate",
    "OrderFulfillmentUpdate",
    "OrderFulfillmentStatusUpdate",
    "OrderFulfillmentResponse",
    "OrderFulfillmentList",
    "OrderFulfillmentStats",
    # Inventory Reservations
    "InventoryReservationBase",
    "InventoryReservationCreate",
    "InventoryReservationUpdate",
    "InventoryReservationRelease",
    "InventoryReservationResponse",
    "InventoryReservationList",
    # Dashboard
    "OrderManagementDashboard",
    "OrderStatusCount",
    # Bulk Operations
    "BulkOrderStatusUpdate",
    "BulkOrderAssignment",
    "BulkOperationResult",
    # Search & Stats
    "OrderSearchFilters",
    "OrderManagementStats",
]
