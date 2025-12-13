"""
Inventory Levels API Routes

Endpoints for querying and managing inventory levels across locations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.inventory import (
    InventoryLevelResponse,
    InventoryLevelUpdate
)
from app.repositories.inventory import InventoryLevelRepository
from app.api.dependencies import PaginationParams


router = APIRouter(prefix="/api/v1/inventory/levels", tags=["Inventory Levels"])


@router.get("/", response_model=List[InventoryLevelResponse])
async def list_inventory_levels(
    pagination: PaginationParams = Depends(),
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    variant_id: Optional[UUID] = Query(None, description="Filter by variant"),
    low_stock_only: bool = Query(False, description="Show only low stock items"),
    db: AsyncSession = Depends(get_db)
):
    """
    List inventory levels with optional filtering
    
    Can filter by location, variant, or show only low stock items.
    """
    repo = InventoryLevelRepository(db)
    
    if low_stock_only:
        levels = await repo.get_low_stock_items(location_id)
    elif location_id:
        levels = await repo.get_by_location(
            location_id,
            skip=pagination.skip,
            limit=pagination.limit
        )
    elif variant_id:
        levels = await repo.get_by_variant(variant_id)
    else:
        levels = await repo.get_all(
            skip=pagination.skip,
            limit=pagination.limit,
            relationships=["product_variant", "location"]
        )
    
    return levels


@router.get("/low-stock", response_model=List[InventoryLevelResponse])
async def list_low_stock_items(
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all items with stock below reorder point
    
    Items with no reorder point set are excluded.
    """
    repo = InventoryLevelRepository(db)
    levels = await repo.get_low_stock_items(location_id)
    return levels


@router.get("/{level_id}", response_model=InventoryLevelResponse)
async def get_inventory_level(
    level_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get an inventory level by ID"""
    repo = InventoryLevelRepository(db)
    level = await repo.get_by_id(
        level_id,
        relationships=["product_variant", "location"]
    )
    
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory level not found"
        )
    
    return level


@router.get("/variant/{variant_id}", response_model=List[InventoryLevelResponse])
async def get_levels_by_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get inventory levels for a variant across all locations
    
    Shows how much stock is available at each location.
    """
    repo = InventoryLevelRepository(db)
    levels = await repo.get_by_variant(variant_id)
    return levels


@router.get("/variant/{variant_id}/location/{location_id}", response_model=InventoryLevelResponse)
async def get_level_by_variant_and_location(
    variant_id: UUID,
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get inventory level for a specific variant at a specific location"""
    repo = InventoryLevelRepository(db)
    level = await repo.get_by_variant_and_location(variant_id, location_id)
    
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory level not found for this variant and location"
        )
    
    return level


@router.get("/variant/{variant_id}/total-stock", response_model=dict)
async def get_total_stock_for_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get total available stock for a variant across all locations
    
    Returns aggregate quantity available.
    """
    repo = InventoryLevelRepository(db)
    total = await repo.get_total_stock(variant_id)
    
    return {
        "variant_id": variant_id,
        "total_available": total
    }


@router.get("/location/{location_id}", response_model=List[InventoryLevelResponse])
async def get_levels_by_location(
    location_id: UUID,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all inventory levels at a specific location
    
    Shows all variants stored at this location.
    """
    repo = InventoryLevelRepository(db)
    levels = await repo.get_by_location(
        location_id,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return levels


@router.put("/{level_id}/settings", response_model=InventoryLevelResponse)
async def update_inventory_settings(
    level_id: UUID,
    settings: InventoryLevelUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update inventory level settings
    
    Updates reorder point, reorder quantity, and max stock level.
    Does not change actual stock quantities (use operations endpoints for that).
    """
    repo = InventoryLevelRepository(db)
    
    # Check if level exists
    existing = await repo.get_by_id(level_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory level not found"
        )
    
    # Update settings
    updated_level = await repo.update(
        level_id,
        settings.model_dump(exclude_unset=True)
    )
    
    return updated_level


@router.post("/variant/{variant_id}/location/{location_id}/count", response_model=InventoryLevelResponse)
async def update_last_count(
    variant_id: UUID,
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Update last counted timestamp for an inventory level
    
    Used to track when physical counts were performed.
    """
    from datetime import datetime
    
    repo = InventoryLevelRepository(db)
    
    level = await repo.get_by_variant_and_location(variant_id, location_id)
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory level not found"
        )
    
    updated_level = await repo.update(level.id, {
        "last_counted_at": datetime.utcnow()
    })
    
    return updated_level
