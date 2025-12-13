"""
Size Chart API Routes

API endpoints for managing size charts for different garment categories.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.repositories.garment import SizeChartRepository
from app.schemas.garment import (
    SizeChartCreate,
    SizeChartUpdate,
    SizeChartResponse,
    SizeChartListResponse,
    SizeCategoryEnum,
    RegionEnum
)


router = APIRouter(prefix="/size-charts", tags=["size-charts"])


@router.post("/", response_model=SizeChartResponse, status_code=status.HTTP_201_CREATED)
async def create_size_chart(
    size_chart_data: SizeChartCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new size chart"""
    repo = SizeChartRepository(db)
    
    # Convert to dict
    data = size_chart_data.model_dump()
    
    # Convert sizes list to JSON-serializable format
    data["sizes"] = [size.model_dump() for size in size_chart_data.sizes]
    
    size_chart = await repo.create(data)
    return size_chart


@router.get("/", response_model=SizeChartListResponse)
async def list_size_charts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: SizeCategoryEnum = Query(None),
    region: RegionEnum = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """List all size charts with optional filters"""
    repo = SizeChartRepository(db)
    
    if category:
        items = await repo.get_by_category(
            category=category.value,
            region=region.value if region else None,
            active_only=active_only
        )
        total = len(items)
        items = items[skip:skip+limit]
    else:
        items, total = await repo.get_all(skip=skip, limit=limit)
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/search", response_model=SizeChartListResponse)
async def search_size_charts(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Search size charts by name"""
    repo = SizeChartRepository(db)
    items, total = await repo.search(q, skip=skip, limit=limit)
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{size_chart_id}", response_model=SizeChartResponse)
async def get_size_chart(
    size_chart_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific size chart by ID"""
    repo = SizeChartRepository(db)
    size_chart = await repo.get_by_id(size_chart_id)
    
    if not size_chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Size chart {size_chart_id} not found"
        )
    
    return size_chart


@router.put("/{size_chart_id}", response_model=SizeChartResponse)
async def update_size_chart(
    size_chart_id: int,
    size_chart_data: SizeChartUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a size chart"""
    repo = SizeChartRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(size_chart_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Size chart {size_chart_id} not found"
        )
    
    # Convert to dict and remove None values
    data = size_chart_data.model_dump(exclude_unset=True)
    
    # Convert sizes list if present
    if "sizes" in data and data["sizes"]:
        data["sizes"] = [size.model_dump() for size in size_chart_data.sizes]
    
    size_chart = await repo.update(size_chart_id, data)
    return size_chart


@router.delete("/{size_chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_size_chart(
    size_chart_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a size chart"""
    repo = SizeChartRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(size_chart_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Size chart {size_chart_id} not found"
        )
    
    await repo.delete(size_chart_id)
    return None


@router.get("/category/{category}", response_model=List[SizeChartResponse])
async def get_size_charts_by_category(
    category: SizeCategoryEnum,
    region: RegionEnum = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get size charts by category and optionally region"""
    repo = SizeChartRepository(db)
    
    size_charts = await repo.get_by_category(
        category=category.value,
        region=region.value if region else None,
        active_only=active_only
    )
    
    return size_charts
