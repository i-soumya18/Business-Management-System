"""
Inventory Operation Schemas

Pydantic schemas for inventory tracking, movements, adjustments, and alerts.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.inventory import MovementType


# ============================================================================
# StockLocation Schemas
# ============================================================================

class StockLocationBase(BaseModel):
    """Base stock location schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Location name")
    code: str = Field(..., min_length=1, max_length=50, description="Location code")
    location_type: str = Field(..., max_length=50, description="Location type (warehouse, store, dc)")
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=100)
    contact_person: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    is_default: bool = Field(default=False)
    priority: int = Field(default=0, description="Fulfillment priority")
    capacity: Optional[int] = Field(None, ge=0, description="Max capacity")
    is_active: bool = Field(default=True)


class StockLocationCreate(StockLocationBase):
    """Schema for creating a stock location"""
    pass


class StockLocationUpdate(BaseModel):
    """Schema for updating a stock location"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    location_type: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = None
    priority: Optional[int] = None
    capacity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class StockLocationResponse(StockLocationBase):
    """Schema for stock location response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    total_items: Optional[int] = Field(None, description="Total items stored")
    
    class Config:
        from_attributes = True


# ============================================================================
# InventoryLevel Schemas
# ============================================================================

class InventoryLevelBase(BaseModel):
    """Base inventory level schema"""
    product_variant_id: UUID
    location_id: UUID
    quantity_on_hand: int = Field(default=0, ge=0)
    quantity_reserved: int = Field(default=0, ge=0)
    quantity_available: int = Field(default=0, ge=0)
    reorder_point: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)


class InventoryLevelUpdate(BaseModel):
    """Schema for updating inventory level settings"""
    reorder_point: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)


class InventoryLevelResponse(InventoryLevelBase):
    """Schema for inventory level response"""
    id: UUID
    last_counted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool = Field(False, description="Is stock below reorder point")
    
    class Config:
        from_attributes = True


# ============================================================================
# InventoryMovement Schemas
# ============================================================================

class InventoryMovementBase(BaseModel):
    """Base inventory movement schema"""
    product_variant_id: UUID
    from_location_id: Optional[UUID] = None
    to_location_id: Optional[UUID] = None
    movement_type: MovementType
    quantity: int = Field(..., gt=0)
    unit_cost: Optional[float] = Field(None, ge=0)
    total_cost: Optional[float] = Field(None, ge=0)
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[UUID] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=200)


class InventoryMovementCreate(InventoryMovementBase):
    """Schema for creating an inventory movement"""
    pass


class InventoryMovementResponse(InventoryMovementBase):
    """Schema for inventory movement response"""
    id: UUID
    created_by_id: Optional[UUID]
    movement_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class InventoryMovementListResponse(BaseModel):
    """Paginated inventory movement list"""
    items: List[InventoryMovementResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Stock Reservation Schemas
# ============================================================================

class StockReservationRequest(BaseModel):
    """Request to reserve stock for an order"""
    product_variant_id: UUID
    location_id: UUID
    quantity: int = Field(..., gt=0)
    reference_type: str = Field(..., description="e.g., 'order'")
    reference_id: UUID
    notes: Optional[str] = None


class StockReservationResponse(BaseModel):
    """Stock reservation response"""
    success: bool
    message: str
    reserved_quantity: int
    available_quantity: int


class StockReleaseRequest(BaseModel):
    """Request to release reserved stock"""
    product_variant_id: UUID
    location_id: UUID
    quantity: int = Field(..., gt=0)
    reference_type: str
    reference_id: UUID


# ============================================================================
# StockAdjustment Schemas
# ============================================================================

class StockAdjustmentBase(BaseModel):
    """Base stock adjustment schema"""
    location_id: UUID
    product_variant_id: UUID
    reason: str = Field(..., max_length=200)
    expected_quantity: int = Field(..., ge=0)
    actual_quantity: int = Field(..., ge=0)
    unit_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class StockAdjustmentCreate(StockAdjustmentBase):
    """Schema for creating a stock adjustment"""
    pass


class StockAdjustmentResponse(StockAdjustmentBase):
    """Schema for stock adjustment response"""
    id: UUID
    adjustment_number: str
    adjustment_quantity: int
    total_cost_impact: Optional[float]
    adjusted_by_id: UUID
    approved_by_id: Optional[UUID]
    status: str
    adjustment_date: datetime
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StockAdjustmentApproval(BaseModel):
    """Schema for approving/rejecting adjustment"""
    status: str = Field(..., description="'approved' or 'rejected'")
    notes: Optional[str] = None


class StockAdjustmentListResponse(BaseModel):
    """Paginated stock adjustment list"""
    items: List[StockAdjustmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# LowStockAlert Schemas
# ============================================================================

class LowStockAlertResponse(BaseModel):
    """Schema for low stock alert response"""
    id: UUID
    product_variant_id: UUID
    location_id: UUID
    current_quantity: int
    reorder_point: int
    recommended_order_quantity: Optional[int]
    status: str
    resolved_at: Optional[datetime]
    resolved_by_id: Optional[UUID]
    resolution_notes: Optional[str]
    alert_date: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LowStockAlertResolve(BaseModel):
    """Schema for resolving a low stock alert"""
    resolution_notes: Optional[str] = None


class LowStockAlertListResponse(BaseModel):
    """Paginated low stock alert list"""
    items: List[LowStockAlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Bulk Operations
# ============================================================================

class BulkStockUpdate(BaseModel):
    """Bulk stock update request"""
    location_id: UUID
    updates: List[dict] = Field(..., description="List of {variant_id, quantity, cost}")
    reason: str
    notes: Optional[str] = None


class BulkStockUpdateResponse(BaseModel):
    """Bulk stock update response"""
    success: bool
    total_processed: int
    total_failed: int
    errors: List[dict] = Field(default_factory=list)
