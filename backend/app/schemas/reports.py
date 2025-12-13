"""
Pydantic schemas for reporting module
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal


# Inventory Summary Report Schemas
class CategorySummary(BaseModel):
    """Category-level inventory summary"""
    category_id: int
    category_name: str
    total_products: int
    total_variants: int
    total_quantity: int
    total_value: Decimal
    low_stock_items: int
    out_of_stock_items: int


class LocationSummary(BaseModel):
    """Location-level inventory summary"""
    location_id: int
    location_name: str
    location_type: str
    total_quantity: int
    total_value: Decimal
    unique_products: int


class InventorySummaryReport(BaseModel):
    """Complete inventory summary report"""
    generated_at: datetime
    total_products: int
    total_variants: int
    total_quantity: int
    total_stock_value: Decimal
    low_stock_count: int
    out_of_stock_count: int
    categories: List[CategorySummary]
    locations: List[LocationSummary]
    
    class Config:
        from_attributes = True


# Stock Valuation Report Schemas
class ProductValuation(BaseModel):
    """Product-level valuation"""
    product_id: int
    sku: str
    name: str
    category_name: str
    total_quantity: int
    cost_price: Decimal
    selling_price: Decimal
    total_cost_value: Decimal
    total_selling_value: Decimal
    potential_profit: Decimal
    profit_margin_percentage: float


class StockValuationReport(BaseModel):
    """Stock valuation report"""
    generated_at: datetime
    total_cost_value: Decimal
    total_selling_value: Decimal
    total_potential_profit: Decimal
    average_profit_margin: float
    total_items: int
    products: List[ProductValuation]
    
    class Config:
        from_attributes = True


# Low Stock Report Schemas
class LowStockItem(BaseModel):
    """Low stock item details"""
    product_id: int
    sku: str
    name: str
    category_name: str
    location_name: str
    current_quantity: int
    reorder_point: int
    reorder_quantity: int
    shortage: int
    days_until_stockout: Optional[int]
    status: str  # 'low', 'critical', 'out_of_stock'


class LowStockReport(BaseModel):
    """Low stock alert report"""
    generated_at: datetime
    critical_items: int
    low_stock_items: int
    out_of_stock_items: int
    total_shortage_value: Decimal
    items: List[LowStockItem]
    
    class Config:
        from_attributes = True


# Stock Movement Report Schemas
class StockMovementSummary(BaseModel):
    """Stock movement summary by type"""
    movement_type: str
    total_movements: int
    total_quantity: int
    affected_products: int


class ProductMovementDetail(BaseModel):
    """Product-level movement details"""
    product_id: int
    sku: str
    name: str
    total_in: int
    total_out: int
    net_change: int
    movements_count: int


class StockMovementReport(BaseModel):
    """Stock movement report"""
    generated_at: datetime
    start_date: date
    end_date: date
    total_movements: int
    total_quantity_in: int
    total_quantity_out: int
    net_change: int
    movement_summary: List[StockMovementSummary]
    product_details: List[ProductMovementDetail]
    
    class Config:
        from_attributes = True


# Inventory Aging Report Schemas
class AgingBucket(BaseModel):
    """Aging bucket (time range)"""
    bucket_name: str
    min_days: int
    max_days: Optional[int]
    product_count: int
    total_quantity: int
    total_value: Decimal


class ProductAgingDetail(BaseModel):
    """Product aging details"""
    product_id: int
    sku: str
    name: str
    category_name: str
    quantity: int
    value: Decimal
    age_days: int
    last_movement_date: Optional[datetime]
    status: str  # 'fresh', 'aging', 'stale', 'dead_stock'


class InventoryAgingReport(BaseModel):
    """Inventory aging analysis report"""
    generated_at: datetime
    total_products: int
    total_quantity: int
    total_value: Decimal
    aging_buckets: List[AgingBucket]
    aged_products: List[ProductAgingDetail]
    dead_stock_count: int
    dead_stock_value: Decimal
    
    class Config:
        from_attributes = True


# Report Filters
class ReportDateFilter(BaseModel):
    """Date range filter for reports"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class InventoryReportFilters(BaseModel):
    """Common filters for inventory reports"""
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    brand_id: Optional[int] = None
    supplier_id: Optional[int] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    include_inactive: bool = False


class StockMovementFilters(ReportDateFilter):
    """Filters for stock movement report"""
    movement_type: Optional[str] = None
    product_id: Optional[int] = None
    location_id: Optional[int] = None


class AgingReportFilters(BaseModel):
    """Filters for aging report"""
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    min_age_days: Optional[int] = None
    max_age_days: Optional[int] = None
    status: Optional[str] = None  # 'fresh', 'aging', 'stale', 'dead_stock'
