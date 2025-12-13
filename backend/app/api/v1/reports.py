"""
API endpoints for reporting module
"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.reports import ReportRepository
from app.schemas.reports import (
    InventorySummaryReport,
    StockValuationReport,
    LowStockReport,
    StockMovementReport,
    InventoryAgingReport
)

router = APIRouter()


@router.get("/inventory-summary", response_model=InventorySummaryReport)
async def get_inventory_summary(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    include_inactive: bool = Query(False, description="Include inactive products"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive inventory summary report
    
    Includes:
    - Total products, variants, quantity, and stock value
    - Low stock and out of stock counts
    - Category-wise breakdown
    - Location-wise breakdown
    """
    repo = ReportRepository(db)
    return await repo.get_inventory_summary(
        category_id=category_id,
        location_id=location_id,
        include_inactive=include_inactive
    )


@router.get("/stock-valuation", response_model=StockValuationReport)
async def get_stock_valuation(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    include_inactive: bool = Query(False, description="Include inactive products"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of products to include"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock valuation report
    
    Shows cost vs selling value analysis:
    - Total cost value (inventory at cost price)
    - Total selling value (inventory at selling price)
    - Potential profit (difference)
    - Average profit margin
    - Per-product breakdown with profit margins
    """
    repo = ReportRepository(db)
    return await repo.get_stock_valuation(
        category_id=category_id,
        location_id=location_id,
        include_inactive=include_inactive,
        limit=limit
    )


@router.get("/low-stock", response_model=LowStockReport)
async def get_low_stock_report(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    status: Optional[str] = Query(
        None,
        description="Filter by status: 'critical', 'low', 'out_of_stock'",
        regex="^(critical|low|out_of_stock)$"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Get low stock alert report
    
    Shows items that need reordering:
    - Critical items (< 50% of reorder point)
    - Low stock items (<= reorder point)
    - Out of stock items (0 quantity)
    - Shortage quantities
    - Estimated days until stockout
    """
    repo = ReportRepository(db)
    return await repo.get_low_stock_report(
        category_id=category_id,
        location_id=location_id,
        status=status
    )


@router.get("/stock-movement", response_model=StockMovementReport)
async def get_stock_movement_report(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type"),
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock movement report for a date range
    
    Analyzes inventory movements:
    - Total movements count
    - Quantity in vs quantity out
    - Net change
    - Breakdown by movement type
    - Per-product movement details (top 100)
    """
    repo = ReportRepository(db)
    return await repo.get_stock_movement_report(
        start_date=start_date,
        end_date=end_date,
        movement_type=movement_type,
        product_id=product_id,
        location_id=location_id
    )


@router.get("/inventory-aging", response_model=InventoryAgingReport)
async def get_inventory_aging_report(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    min_age_days: Optional[int] = Query(None, ge=0, description="Minimum age in days"),
    max_age_days: Optional[int] = Query(None, ge=0, description="Maximum age in days"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get inventory aging analysis report
    
    Shows how long items have been in stock:
    - Aging buckets (0-30, 31-90, 91-180, 180+ days)
    - Fresh vs aging vs stale vs dead stock classification
    - Dead stock count and value (180+ days)
    - Last movement date per product
    - Total inventory value by age
    """
    repo = ReportRepository(db)
    return await repo.get_inventory_aging_report(
        category_id=category_id,
        location_id=location_id,
        min_age_days=min_age_days,
        max_age_days=max_age_days
    )
