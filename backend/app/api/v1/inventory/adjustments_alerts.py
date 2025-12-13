"""
Stock Adjustments and Alerts API Routes

Endpoints for managing stock adjustments and low stock alerts.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.inventory import (
    StockAdjustmentCreate,
    StockAdjustmentResponse,
    StockAdjustmentApproval,
    StockAdjustmentListResponse,
    LowStockAlertResponse,
    LowStockAlertResolve,
    LowStockAlertListResponse
)
from app.services.inventory import InventoryService
from app.repositories.inventory import StockAdjustmentRepository, LowStockAlertRepository
from app.api.dependencies import PaginationParams


router = APIRouter(prefix="/api/v1/inventory", tags=["Stock Adjustments & Alerts"])


# ============================================================================
# Stock Adjustments
# ============================================================================

@router.post("/adjustments", response_model=StockAdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_adjustment(
    adjustment_data: StockAdjustmentCreate,
    user_id: UUID = Query(..., description="User creating adjustment"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a stock adjustment
    
    Stock adjustments are used for physical counts, damaged goods, etc.
    They require approval before being applied to inventory.
    """
    service = InventoryService(db)
    
    result = await service.adjust_stock(
        location_id=adjustment_data.location_id,
        variant_id=adjustment_data.product_variant_id,
        expected_quantity=adjustment_data.expected_quantity,
        actual_quantity=adjustment_data.actual_quantity,
        reason=adjustment_data.reason,
        user_id=user_id,
        unit_cost=adjustment_data.unit_cost,
        notes=adjustment_data.notes
    )
    
    return result["adjustment"]


@router.get("/adjustments", response_model=StockAdjustmentListResponse)
async def list_stock_adjustments(
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List stock adjustments with optional filtering"""
    repo = StockAdjustmentRepository(db)
    
    filters = {}
    if location_id:
        filters["location_id"] = location_id
    if status_filter:
        filters["status"] = status_filter
    
    adjustments = await repo.get_all(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await repo.count(filters)
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return {
        "items": adjustments,
        "total": total,
        "page": pagination.skip // pagination.limit + 1,
        "page_size": pagination.limit,
        "pages": pages
    }


@router.get("/adjustments/pending", response_model=List[StockAdjustmentResponse])
async def list_pending_adjustments(
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    db: AsyncSession = Depends(get_db)
):
    """Get all pending stock adjustments awaiting approval"""
    repo = StockAdjustmentRepository(db)
    adjustments = await repo.get_pending_adjustments(location_id)
    return adjustments


@router.get("/adjustments/{adjustment_id}", response_model=StockAdjustmentResponse)
async def get_stock_adjustment(
    adjustment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a stock adjustment by ID"""
    repo = StockAdjustmentRepository(db)
    adjustment = await repo.get_by_id(adjustment_id)
    
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock adjustment not found"
        )
    
    return adjustment


@router.post("/adjustments/{adjustment_id}/approve")
async def approve_stock_adjustment(
    adjustment_id: UUID,
    approval_data: StockAdjustmentApproval,
    user_id: UUID = Query(..., description="User approving adjustment"),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve or reject a stock adjustment
    
    If approved, the adjustment is applied to inventory.
    If rejected, it's marked as rejected but not applied.
    """
    service = InventoryService(db)
    
    if approval_data.status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved' or 'rejected'"
        )
    
    if approval_data.status == "approved":
        result = await service.approve_adjustment(
            adjustment_id=adjustment_id,
            user_id=user_id,
            notes=approval_data.notes
        )
        return {
            "message": "Adjustment approved and applied",
            "adjustment": result["adjustment"],
            "inventory_level": result["inventory_level"]
        }
    else:
        repo = StockAdjustmentRepository(db)
        adjustment = await repo.reject_adjustment(
            adjustment_id=adjustment_id,
            approved_by_id=user_id,
            notes=approval_data.notes
        )
        return {
            "message": "Adjustment rejected",
            "adjustment": adjustment
        }


# ============================================================================
# Low Stock Alerts
# ============================================================================

@router.get("/alerts", response_model=LowStockAlertListResponse)
async def list_low_stock_alerts(
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List low stock alerts with optional filtering"""
    repo = LowStockAlertRepository(db)
    
    filters = {}
    if location_id:
        filters["location_id"] = location_id
    if status_filter:
        filters["status"] = status_filter
    
    alerts = await repo.get_all(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters,
        relationships=["product_variant", "location"]
    )
    total = await repo.count(filters)
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return {
        "items": alerts,
        "total": total,
        "page": pagination.skip // pagination.limit + 1,
        "page_size": pagination.limit,
        "pages": pages
    }


@router.get("/alerts/active", response_model=List[LowStockAlertResponse])
async def list_active_alerts(
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    db: AsyncSession = Depends(get_db)
):
    """Get all active low stock alerts"""
    repo = LowStockAlertRepository(db)
    alerts = await repo.get_active_alerts(location_id)
    return alerts


@router.get("/alerts/{alert_id}", response_model=LowStockAlertResponse)
async def get_low_stock_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a low stock alert by ID"""
    repo = LowStockAlertRepository(db)
    alert = await repo.get_by_id(alert_id, relationships=["product_variant", "location"])
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Low stock alert not found"
        )
    
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=LowStockAlertResponse)
async def resolve_low_stock_alert(
    alert_id: UUID,
    resolve_data: LowStockAlertResolve,
    user_id: UUID = Query(..., description="User resolving alert"),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve a low stock alert
    
    This marks the alert as resolved. Typically done after restocking.
    """
    repo = LowStockAlertRepository(db)
    
    alert = await repo.resolve_alert(
        alert_id=alert_id,
        resolved_by_id=user_id,
        resolution_notes=resolve_data.resolution_notes
    )
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Low stock alert not found"
        )
    
    return alert


@router.get("/alerts/variant/{variant_id}/location/{location_id}", response_model=LowStockAlertResponse)
async def get_alert_for_variant_location(
    variant_id: UUID,
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get active alert for a specific variant at a location"""
    repo = LowStockAlertRepository(db)
    alert = await repo.get_by_variant_and_location(variant_id, location_id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active alert found for this variant at this location"
        )
    
    return alert
