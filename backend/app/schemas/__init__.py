"""
Schemas package initialization
"""

from app.schemas.order_management import (
    # Order History
    OrderHistoryCreate,
    OrderHistoryUpdate,
    OrderHistoryResponse,
    OrderHistoryList,
    # Order Notes
    OrderNoteCreate,
    OrderNoteUpdate,
    OrderNoteResponse,
    OrderNoteList,
    # Order Fulfillment
    OrderFulfillmentCreate,
    OrderFulfillmentUpdate,
    OrderFulfillmentStatusUpdate,
    OrderFulfillmentResponse,
    OrderFulfillmentList,
    OrderFulfillmentStats,
    # Inventory Reservations
    InventoryReservationCreate,
    InventoryReservationUpdate,
    InventoryReservationRelease,
    InventoryReservationResponse,
    InventoryReservationList,
    # Dashboard
    OrderManagementDashboard,
    OrderStatusCount,
    # Bulk Operations
    BulkOrderStatusUpdate,
    BulkOrderAssignment,
    BulkOperationResult,
    # Search & Stats
    OrderSearchFilters,
    OrderManagementStats,
)

__all__ = [
    # Order History
    "OrderHistoryCreate",
    "OrderHistoryUpdate",
    "OrderHistoryResponse",
    "OrderHistoryList",
    # Order Notes
    "OrderNoteCreate",
    "OrderNoteUpdate",
    "OrderNoteResponse",
    "OrderNoteList",
    # Order Fulfillment
    "OrderFulfillmentCreate",
    "OrderFulfillmentUpdate",
    "OrderFulfillmentStatusUpdate",
    "OrderFulfillmentResponse",
    "OrderFulfillmentList",
    "OrderFulfillmentStats",
    # Inventory Reservations
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
