"""
Stock Location API Routes

Endpoints for managing stock locations (warehouses, stores, distribution centers).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.inventory import (
    StockLocationCreate,
    StockLocationUpdate,
    StockLocationResponse
)
from app.repositories.inventory import StockLocationRepository
from app.api.dependencies import PaginationParams


router = APIRouter(prefix="/locations", tags=["Stock Locations"])


@router.post("/", response_model=StockLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_location(
    location_data: StockLocationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new stock location"""
    repo = StockLocationRepository(db)
    
    # Check if code already exists
    existing = await repo.get_by_code(location_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location with code '{location_data.code}' already exists"
        )
    
    # If this is set as default, unset other defaults
    if location_data.is_default:
        # TODO: Implement logic to unset other defaults
        pass
    
    location = await repo.create(location_data.model_dump())
    return location


@router.get("/", response_model=List[StockLocationResponse])
async def list_stock_locations(
    pagination: PaginationParams = Depends(),
    is_active: Optional[bool] = Query(None),
    location_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all stock locations with optional filtering"""
    repo = StockLocationRepository(db)
    
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if location_type:
        filters["location_type"] = location_type
    
    locations = await repo.get_all(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    return locations


@router.get("/active", response_model=List[StockLocationResponse])
async def list_active_locations(
    db: AsyncSession = Depends(get_db)
):
    """Get all active stock locations ordered by priority"""
    repo = StockLocationRepository(db)
    locations = await repo.get_active_locations()
    return locations


@router.get("/default", response_model=StockLocationResponse)
async def get_default_location(
    db: AsyncSession = Depends(get_db)
):
    """Get the default stock location"""
    repo = StockLocationRepository(db)
    location = await repo.get_default()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default location configured"
        )
    
    return location


@router.get("/{location_id}", response_model=StockLocationResponse)
async def get_stock_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a stock location by ID"""
    repo = StockLocationRepository(db)
    location = await repo.get_by_id(location_id)
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock location not found"
        )
    
    return location


@router.put("/{location_id}", response_model=StockLocationResponse)
async def update_stock_location(
    location_id: UUID,
    location_data: StockLocationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a stock location"""
    repo = StockLocationRepository(db)
    
    # Check if location exists
    existing = await repo.get_by_id(location_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock location not found"
        )
    
    # Check if code is being changed and already exists
    if location_data.code and location_data.code != existing.code:
        code_exists = await repo.get_by_code(location_data.code)
        if code_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location with code '{location_data.code}' already exists"
            )
    
    # Update location
    updated_location = await repo.update(
        location_id,
        location_data.model_dump(exclude_unset=True)
    )
    
    return updated_location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a stock location"""
    repo = StockLocationRepository(db)
    
    # Check if location exists
    exists = await repo.exists(location_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock location not found"
        )
    
    # TODO: Check if location has inventory before deleting
    # For now, just delete
    await repo.delete(location_id)
    
    return None


@router.get("/code/{code}", response_model=StockLocationResponse)
async def get_location_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a stock location by code"""
    repo = StockLocationRepository(db)
    location = await repo.get_by_code(code)
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock location with code '{code}' not found"
        )
    
    return location
