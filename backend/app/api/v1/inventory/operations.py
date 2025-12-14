"""
Inventory Operations API Routes

Endpoints for inventory movements, reservations, and stock operations.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.inventory import (
    InventoryMovementCreate,
    InventoryMovementResponse,
    InventoryMovementListResponse,
    StockReservationRequest,
    StockReservationResponse,
    StockReleaseRequest,
    BulkStockUpdate,
    BulkStockUpdateResponse
)
from app.services.inventory import InventoryService
from app.api.dependencies import PaginationParams


router = APIRouter(prefix="/operations", tags=["Inventory Operations"])


@router.post("/receive", status_code=status.HTTP_201_CREATED)
async def receive_stock(
    variant_id: UUID = Query(..., description="Product variant ID"),
    location_id: UUID = Query(..., description="Stock location ID"),
    quantity: int = Query(..., gt=0, description="Quantity to receive"),
    unit_cost: Optional[float] = Query(None, ge=0, description="Cost per unit"),
    reference_type: Optional[str] = Query(None, description="Reference type"),
    reference_id: Optional[UUID] = Query(None, description="Reference ID"),
    reference_number: Optional[str] = Query(None, description="Reference number"),
    notes: Optional[str] = Query(None, description="Additional notes"),
    db: AsyncSession = Depends(get_db)
):
    """
    Receive stock into inventory
    
    This creates an inventory movement and updates stock levels.
    """
    service = InventoryService(db)
    
    result = await service.receive_stock(
        variant_id=variant_id,
        location_id=location_id,
        quantity=quantity,
        unit_cost=unit_cost,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        notes=notes
    )
    
    return result


@router.post("/ship", status_code=status.HTTP_200_OK)
async def ship_stock(
    variant_id: UUID = Query(..., description="Product variant ID"),
    location_id: UUID = Query(..., description="Stock location ID"),
    quantity: int = Query(..., gt=0, description="Quantity to ship"),
    reference_type: Optional[str] = Query(None, description="Reference type"),
    reference_id: Optional[UUID] = Query(None, description="Reference ID"),
    reference_number: Optional[str] = Query(None, description="Reference number"),
    notes: Optional[str] = Query(None, description="Additional notes"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ship stock out of inventory
    
    Reduces inventory. Stock must be reserved first.
    """
    service = InventoryService(db)
    
    result = await service.ship_stock(
        variant_id=variant_id,
        location_id=location_id,
        quantity=quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_number=reference_number,
        notes=notes
    )
    
    return result


@router.post("/transfer", status_code=status.HTTP_200_OK)
async def transfer_stock(
    variant_id: UUID = Query(..., description="Product variant ID"),
    from_location_id: UUID = Query(..., description="Source location ID"),
    to_location_id: UUID = Query(..., description="Destination location ID"),
    quantity: int = Query(..., gt=0, description="Quantity to transfer"),
    notes: Optional[str] = Query(None, description="Additional notes"),
    db: AsyncSession = Depends(get_db)
):
    """
    Transfer stock between locations
    """
    service = InventoryService(db)
    
    if from_location_id == to_location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination locations must be different"
        )
    
    result = await service.transfer_stock(
        variant_id=variant_id,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        quantity=quantity,
        notes=notes
    )
    
    return result


@router.post("/reserve", response_model=StockReservationResponse)
async def reserve_stock(
    request: StockReservationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reserve stock for an order or allocation
    
    Reserved stock is not available for other orders but still counts as on-hand.
    """
    service = InventoryService(db)
    
    result = await service.reserve_stock(
        variant_id=request.product_variant_id,
        location_id=request.location_id,
        quantity=request.quantity,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        notes=request.notes
    )
    
    return {
        "success": True,
        "message": f"Reserved {result['reserved_quantity']} units",
        "reserved_quantity": result["reserved_quantity"],
        "available_quantity": result["available_quantity"]
    }


@router.post("/release", response_model=StockReservationResponse)
async def release_reservation(
    request: StockReleaseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Release a stock reservation
    
    Unreserved stock becomes available again.
    """
    service = InventoryService(db)
    
    result = await service.release_reservation(
        variant_id=request.product_variant_id,
        location_id=request.location_id,
        quantity=request.quantity,
        reference_type=request.reference_type,
        reference_id=request.reference_id
    )
    
    return {
        "success": True,
        "message": f"Released {result['released_quantity']} units",
        "reserved_quantity": result["released_quantity"],
        "available_quantity": result["inventory_level"].quantity_available
    }


@router.get("/movements", response_model=InventoryMovementListResponse)
async def list_movements(
    variant_id: Optional[UUID] = Query(None, description="Filter by variant"),
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List inventory movements with optional filtering
    """
    from app.repositories.inventory import InventoryMovementRepository
    
    repo = InventoryMovementRepository(db)
    
    if variant_id:
        movements, total = await repo.get_by_variant(
            variant_id,
            skip=pagination.skip,
            limit=pagination.limit
        )
    elif location_id:
        movements, total = await repo.get_by_location(
            location_id,
            skip=pagination.skip,
            limit=pagination.limit
        )
    else:
        movements = await repo.get_all(
            skip=pagination.skip,
            limit=pagination.limit
        )
        total = await repo.count()
    
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return {
        "items": movements,
        "total": total,
        "page": pagination.skip // pagination.limit + 1,
        "page_size": pagination.limit,
        "pages": pages
    }


@router.post("/bulk-update", response_model=BulkStockUpdateResponse)
async def bulk_stock_update(
    bulk_request: BulkStockUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk update stock levels
    
    Useful for importing stock counts or reconciling inventory.
    """
    service = InventoryService(db)
    
    total_processed = 0
    total_failed = 0
    errors = []
    
    for update in bulk_request.updates:
        try:
            await service.receive_stock(
                variant_id=update.get("variant_id"),
                location_id=bulk_request.location_id,
                quantity=update.get("quantity", 0),
                unit_cost=update.get("cost"),
                reference_type="bulk_update",
                notes=bulk_request.notes
            )
            total_processed += 1
        except Exception as e:
            total_failed += 1
            errors.append({
                "variant_id": str(update.get("variant_id")),
                "error": str(e)
            })
    
    return {
        "success": total_failed == 0,
        "total_processed": total_processed,
        "total_failed": total_failed,
        "errors": errors
    }
