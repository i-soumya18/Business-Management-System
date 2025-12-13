"""
Repository for reporting queries and analytics
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy import select, func, case, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.product import Product, ProductVariant
from app.models.category import Category as ProductCategory
from app.models.brand import Brand
from app.models.supplier import Supplier
from app.models.inventory import (
    InventoryLevel, InventoryMovement, StockLocation
)
from app.schemas.reports import (
    InventorySummaryReport, CategorySummary, LocationSummary,
    StockValuationReport, ProductValuation,
    LowStockReport, LowStockItem,
    StockMovementReport, StockMovementSummary, ProductMovementDetail,
    InventoryAgingReport, AgingBucket, ProductAgingDetail
)


class ReportRepository:
    """Repository for generating various inventory reports"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_inventory_summary(
        self,
        category_id: Optional[int] = None,
        location_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> InventorySummaryReport:
        """
        Generate comprehensive inventory summary report
        """
        # Base filter
        filters = []
        if not include_inactive:
            filters.append(Product.is_active == True)
        if category_id:
            filters.append(Product.category_id == category_id)
        
        # Total products and variants
        product_query = select(func.count(Product.id)).where(and_(*filters) if filters else True)
        total_products = (await self.session.execute(product_query)).scalar() or 0
        
        variant_query = select(func.count(ProductVariant.id)).join(Product).where(
            and_(*filters) if filters else True
        )
        total_variants = (await self.session.execute(variant_query)).scalar() or 0
        
        # Total quantity and value
        inventory_filters = list(filters)
        if location_id:
            inventory_filters.append(InventoryLevel.location_id == location_id)
        
        stock_query = select(
            func.coalesce(func.sum(InventoryLevel.quantity), 0).label('total_quantity'),
            func.coalesce(func.sum(InventoryLevel.quantity * Product.cost_price), Decimal('0')).label('total_value')
        ).select_from(InventoryLevel).join(Product).where(
            and_(*inventory_filters) if inventory_filters else True
        )
        stock_result = (await self.session.execute(stock_query)).first()
        total_quantity = int(stock_result.total_quantity or 0)
        total_value = Decimal(str(stock_result.total_value or 0))
        
        # Low stock and out of stock counts
        low_stock_query = select(func.count(InventoryLevel.id)).join(Product).where(
            and_(
                InventoryLevel.quantity <= InventoryLevel.reorder_point,
                InventoryLevel.quantity > 0,
                *inventory_filters
            )
        )
        low_stock_count = (await self.session.execute(low_stock_query)).scalar() or 0
        
        out_of_stock_query = select(func.count(InventoryLevel.id)).join(Product).where(
            and_(
                InventoryLevel.quantity == 0,
                *inventory_filters
            )
        )
        out_of_stock_count = (await self.session.execute(out_of_stock_query)).scalar() or 0
        
        # Category summaries
        categories = await self._get_category_summaries(filters, location_id)
        
        # Location summaries
        locations = await self._get_location_summaries(filters, category_id)
        
        return InventorySummaryReport(
            generated_at=datetime.utcnow(),
            total_products=total_products,
            total_variants=total_variants,
            total_quantity=total_quantity,
            total_stock_value=total_value,
            low_stock_count=low_stock_count,
            out_of_stock_count=out_of_stock_count,
            categories=categories,
            locations=locations
        )
    
    async def _get_category_summaries(
        self,
        product_filters: List,
        location_id: Optional[int]
    ) -> List[CategorySummary]:
        """Get inventory summary by category"""
        inventory_filters = [*product_filters]
        if location_id:
            inventory_filters.append(InventoryLevel.location_id == location_id)
        
        query = select(
            ProductCategory.id.label('category_id'),
            ProductCategory.name.label('category_name'),
            func.count(func.distinct(Product.id)).label('total_products'),
            func.count(func.distinct(ProductVariant.id)).label('total_variants'),
            func.coalesce(func.sum(InventoryLevel.quantity), 0).label('total_quantity'),
            func.coalesce(func.sum(InventoryLevel.quantity * Product.cost_price), Decimal('0')).label('total_value'),
            func.sum(
                case((and_(InventoryLevel.quantity <= InventoryLevel.reorder_point, InventoryLevel.quantity > 0), 1), else_=0)
            ).label('low_stock_items'),
            func.sum(
                case((InventoryLevel.quantity == 0, 1), else_=0)
            ).label('out_of_stock_items')
        ).select_from(ProductCategory).join(
            Product, Product.category_id == ProductCategory.id
        ).outerjoin(
            ProductVariant, ProductVariant.product_id == Product.id
        ).outerjoin(
            InventoryLevel, InventoryLevel.product_id == Product.id
        ).where(
            and_(*inventory_filters) if inventory_filters else True
        ).group_by(ProductCategory.id, ProductCategory.name)
        
        result = await self.session.execute(query)
        return [
            CategorySummary(
                category_id=row.category_id,
                category_name=row.category_name,
                total_products=row.total_products or 0,
                total_variants=row.total_variants or 0,
                total_quantity=int(row.total_quantity or 0),
                total_value=Decimal(str(row.total_value or 0)),
                low_stock_items=row.low_stock_items or 0,
                out_of_stock_items=row.out_of_stock_items or 0
            )
            for row in result.all()
        ]
    
    async def _get_location_summaries(
        self,
        product_filters: List,
        category_id: Optional[int]
    ) -> List[LocationSummary]:
        """Get inventory summary by location"""
        inventory_filters = [*product_filters]
        
        query = select(
            StockLocation.id.label('location_id'),
            StockLocation.name.label('location_name'),
            StockLocation.location_type.label('location_type'),
            func.coalesce(func.sum(InventoryLevel.quantity), 0).label('total_quantity'),
            func.coalesce(func.sum(InventoryLevel.quantity * Product.cost_price), Decimal('0')).label('total_value'),
            func.count(func.distinct(Product.id)).label('unique_products')
        ).select_from(StockLocation).join(
            InventoryLevel, InventoryLevel.location_id == StockLocation.id
        ).join(
            Product, InventoryLevel.product_id == Product.id
        ).where(
            and_(*inventory_filters) if inventory_filters else True
        ).group_by(StockLocation.id, StockLocation.name, StockLocation.location_type)
        
        result = await self.session.execute(query)
        return [
            LocationSummary(
                location_id=row.location_id,
                location_name=row.location_name,
                location_type=row.location_type,
                total_quantity=int(row.total_quantity or 0),
                total_value=Decimal(str(row.total_value or 0)),
                unique_products=row.unique_products or 0
            )
            for row in result.all()
        ]
    
    async def get_stock_valuation(
        self,
        category_id: Optional[int] = None,
        location_id: Optional[int] = None,
        include_inactive: bool = False,
        limit: int = 1000
    ) -> StockValuationReport:
        """
        Generate stock valuation report showing cost vs selling value
        """
        filters = []
        if not include_inactive:
            filters.append(Product.is_active == True)
        if category_id:
            filters.append(Product.category_id == category_id)
        if location_id:
            filters.append(InventoryLevel.location_id == location_id)
        
        # Query for product valuations
        query = select(
            Product.id.label('product_id'),
            Product.sku,
            Product.name,
            ProductCategory.name.label('category_name'),
            func.coalesce(func.sum(InventoryLevel.quantity), 0).label('total_quantity'),
            Product.cost_price,
            Product.selling_price,
            (func.coalesce(func.sum(InventoryLevel.quantity), 0) * Product.cost_price).label('total_cost_value'),
            (func.coalesce(func.sum(InventoryLevel.quantity), 0) * Product.selling_price).label('total_selling_value'),
            ((func.coalesce(func.sum(InventoryLevel.quantity), 0) * Product.selling_price) - 
             (func.coalesce(func.sum(InventoryLevel.quantity), 0) * Product.cost_price)).label('potential_profit')
        ).select_from(Product).join(
            ProductCategory, Product.category_id == ProductCategory.id
        ).outerjoin(
            InventoryLevel, InventoryLevel.product_id == Product.id
        ).where(
            and_(*filters) if filters else True
        ).group_by(
            Product.id, Product.sku, Product.name, ProductCategory.name,
            Product.cost_price, Product.selling_price
        ).order_by(desc('total_cost_value')).limit(limit)
        
        result = await self.session.execute(query)
        products = []
        total_cost = Decimal('0')
        total_selling = Decimal('0')
        total_profit = Decimal('0')
        
        for row in result.all():
            cost_val = Decimal(str(row.total_cost_value or 0))
            selling_val = Decimal(str(row.total_selling_value or 0))
            profit = Decimal(str(row.potential_profit or 0))
            
            # Calculate profit margin
            profit_margin = 0.0
            if selling_val > 0:
                profit_margin = float((profit / selling_val) * 100)
            
            products.append(ProductValuation(
                product_id=row.product_id,
                sku=row.sku,
                name=row.name,
                category_name=row.category_name,
                total_quantity=int(row.total_quantity or 0),
                cost_price=Decimal(str(row.cost_price)),
                selling_price=Decimal(str(row.selling_price)),
                total_cost_value=cost_val,
                total_selling_value=selling_val,
                potential_profit=profit,
                profit_margin_percentage=profit_margin
            ))
            
            total_cost += cost_val
            total_selling += selling_val
            total_profit += profit
        
        # Calculate average profit margin
        avg_profit_margin = 0.0
        if total_selling > 0:
            avg_profit_margin = float((total_profit / total_selling) * 100)
        
        return StockValuationReport(
            generated_at=datetime.utcnow(),
            total_cost_value=total_cost,
            total_selling_value=total_selling,
            total_potential_profit=total_profit,
            average_profit_margin=avg_profit_margin,
            total_items=len(products),
            products=products
        )
    
    async def get_low_stock_report(
        self,
        category_id: Optional[int] = None,
        location_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> LowStockReport:
        """
        Generate low stock alert report
        """
        filters = [Product.is_active == True]
        if category_id:
            filters.append(Product.category_id == category_id)
        if location_id:
            filters.append(InventoryLevel.location_id == location_id)
        
        # Status filter
        if status == 'critical':
            filters.append(InventoryLevel.quantity < (InventoryLevel.reorder_point * 0.5))
        elif status == 'low':
            filters.append(and_(
                InventoryLevel.quantity <= InventoryLevel.reorder_point,
                InventoryLevel.quantity > 0
            ))
        elif status == 'out_of_stock':
            filters.append(InventoryLevel.quantity == 0)
        else:
            # All low stock items
            filters.append(InventoryLevel.quantity <= InventoryLevel.reorder_point)
        
        query = select(
            Product.id.label('product_id'),
            Product.sku,
            Product.name,
            ProductCategory.name.label('category_name'),
            StockLocation.name.label('location_name'),
            InventoryLevel.quantity.label('current_quantity'),
            InventoryLevel.reorder_point,
            InventoryLevel.reorder_quantity,
            (InventoryLevel.reorder_point - InventoryLevel.quantity).label('shortage')
        ).select_from(InventoryLevel).join(
            Product, InventoryLevel.product_id == Product.id
        ).join(
            ProductCategory, Product.category_id == ProductCategory.id
        ).join(
            StockLocation, InventoryLevel.location_id == StockLocation.id
        ).where(and_(*filters)).order_by(InventoryLevel.quantity)
        
        result = await self.session.execute(query)
        items = []
        critical_count = 0
        low_stock_count = 0
        out_of_stock_count = 0
        total_shortage_value = Decimal('0')
        
        for row in result.all():
            qty = row.current_quantity
            reorder_pt = row.reorder_point
            
            # Determine status
            if qty == 0:
                item_status = 'out_of_stock'
                out_of_stock_count += 1
            elif qty < (reorder_pt * 0.5):
                item_status = 'critical'
                critical_count += 1
            else:
                item_status = 'low'
                low_stock_count += 1
            
            # Estimate days until stockout (simplified - would need sales data for accuracy)
            days_until_stockout = None
            if qty > 0:
                # Placeholder logic - in reality would calculate based on average daily sales
                days_until_stockout = qty  # Simplified assumption
            
            shortage = max(0, row.shortage or 0)
            
            items.append(LowStockItem(
                product_id=row.product_id,
                sku=row.sku,
                name=row.name,
                category_name=row.category_name,
                location_name=row.location_name,
                current_quantity=qty,
                reorder_point=reorder_pt,
                reorder_quantity=row.reorder_quantity,
                shortage=shortage,
                days_until_stockout=days_until_stockout,
                status=item_status
            ))
        
        return LowStockReport(
            generated_at=datetime.utcnow(),
            critical_items=critical_count,
            low_stock_items=low_stock_count,
            out_of_stock_items=out_of_stock_count,
            total_shortage_value=total_shortage_value,
            items=items
        )
    
    async def get_stock_movement_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        movement_type: Optional[str] = None,
        product_id: Optional[int] = None,
        location_id: Optional[int] = None
    ) -> StockMovementReport:
        """
        Generate stock movement report for a date range
        """
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        filters = [
            InventoryMovement.movement_date >= datetime.combine(start_date, datetime.min.time()),
            InventoryMovement.movement_date <= datetime.combine(end_date, datetime.max.time())
        ]
        
        if movement_type:
            filters.append(InventoryMovement.movement_type == movement_type)
        if product_id:
            filters.append(InventoryMovement.product_id == product_id)
        if location_id:
            filters.append(InventoryMovement.location_id == location_id)
        
        # Total movements count
        total_query = select(func.count(InventoryMovement.id)).where(and_(*filters))
        total_movements = (await self.session.execute(total_query)).scalar() or 0
        
        # Quantity in and out
        quantity_query = select(
            func.sum(case((InventoryMovement.quantity_change > 0, InventoryMovement.quantity_change), else_=0)).label('total_in'),
            func.sum(case((InventoryMovement.quantity_change < 0, -InventoryMovement.quantity_change), else_=0)).label('total_out')
        ).where(and_(*filters))
        qty_result = (await self.session.execute(quantity_query)).first()
        total_in = int(qty_result.total_in or 0)
        total_out = int(qty_result.total_out or 0)
        net_change = total_in - total_out
        
        # Movement summary by type
        summary_query = select(
            InventoryMovement.movement_type,
            func.count(InventoryMovement.id).label('total_movements'),
            func.sum(func.abs(InventoryMovement.quantity_change)).label('total_quantity'),
            func.count(func.distinct(InventoryMovement.product_id)).label('affected_products')
        ).where(and_(*filters)).group_by(InventoryMovement.movement_type)
        
        summary_result = await self.session.execute(summary_query)
        movement_summary = [
            StockMovementSummary(
                movement_type=row.movement_type,
                total_movements=row.total_movements,
                total_quantity=int(row.total_quantity or 0),
                affected_products=row.affected_products
            )
            for row in summary_result.all()
        ]
        
        # Product-level details
        if not product_id:  # Only show product details if not filtered by specific product
            product_query = select(
                Product.id.label('product_id'),
                Product.sku,
                Product.name,
                func.sum(case((InventoryMovement.quantity_change > 0, InventoryMovement.quantity_change), else_=0)).label('total_in'),
                func.sum(case((InventoryMovement.quantity_change < 0, -InventoryMovement.quantity_change), else_=0)).label('total_out'),
                func.count(InventoryMovement.id).label('movements_count')
            ).select_from(InventoryMovement).join(
                Product, InventoryMovement.product_id == Product.id
            ).where(and_(*filters)).group_by(
                Product.id, Product.sku, Product.name
            ).order_by(desc('movements_count')).limit(100)
            
            product_result = await self.session.execute(product_query)
            product_details = [
                ProductMovementDetail(
                    product_id=row.product_id,
                    sku=row.sku,
                    name=row.name,
                    total_in=int(row.total_in or 0),
                    total_out=int(row.total_out or 0),
                    net_change=int(row.total_in or 0) - int(row.total_out or 0),
                    movements_count=row.movements_count
                )
                for row in product_result.all()
            ]
        else:
            product_details = []
        
        return StockMovementReport(
            generated_at=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            total_movements=total_movements,
            total_quantity_in=total_in,
            total_quantity_out=total_out,
            net_change=net_change,
            movement_summary=movement_summary,
            product_details=product_details
        )
    
    async def get_inventory_aging_report(
        self,
        category_id: Optional[int] = None,
        location_id: Optional[int] = None,
        min_age_days: Optional[int] = None,
        max_age_days: Optional[int] = None
    ) -> InventoryAgingReport:
        """
        Generate inventory aging report showing how long items have been in stock
        """
        filters = [Product.is_active == True]
        if category_id:
            filters.append(Product.category_id == category_id)
        if location_id:
            filters.append(InventoryLevel.location_id == location_id)
        
        # Get products with their last movement date
        query = select(
            Product.id.label('product_id'),
            Product.sku,
            Product.name,
            ProductCategory.name.label('category_name'),
            func.coalesce(func.sum(InventoryLevel.quantity), 0).label('quantity'),
            (func.coalesce(func.sum(InventoryLevel.quantity), 0) * Product.cost_price).label('value'),
            func.max(InventoryMovement.movement_date).label('last_movement_date')
        ).select_from(Product).join(
            ProductCategory, Product.category_id == ProductCategory.id
        ).outerjoin(
            InventoryLevel, InventoryLevel.product_id == Product.id
        ).outerjoin(
            InventoryMovement, InventoryMovement.product_id == Product.id
        ).where(
            and_(*filters)
        ).group_by(
            Product.id, Product.sku, Product.name, ProductCategory.name, Product.cost_price
        ).having(
            func.coalesce(func.sum(InventoryLevel.quantity), 0) > 0
        )
        
        result = await self.session.execute(query)
        
        aged_products = []
        total_quantity = 0
        total_value = Decimal('0')
        dead_stock_count = 0
        dead_stock_value = Decimal('0')
        
        for row in result.all():
            # Calculate age
            last_movement = row.last_movement_date
            if last_movement:
                age_days = (datetime.utcnow() - last_movement).days
            else:
                age_days = 365  # Assume very old if no movement history
            
            # Apply age filters
            if min_age_days and age_days < min_age_days:
                continue
            if max_age_days and age_days > max_age_days:
                continue
            
            # Determine status
            if age_days > 180:
                status = 'dead_stock'
                dead_stock_count += 1
                dead_stock_value += Decimal(str(row.value or 0))
            elif age_days > 90:
                status = 'stale'
            elif age_days > 30:
                status = 'aging'
            else:
                status = 'fresh'
            
            qty = int(row.quantity or 0)
            val = Decimal(str(row.value or 0))
            
            aged_products.append(ProductAgingDetail(
                product_id=row.product_id,
                sku=row.sku,
                name=row.name,
                category_name=row.category_name,
                quantity=qty,
                value=val,
                age_days=age_days,
                last_movement_date=last_movement,
                status=status
            ))
            
            total_quantity += qty
            total_value += val
        
        # Create aging buckets
        aging_buckets = [
            AgingBucket(bucket_name="0-30 days (Fresh)", min_days=0, max_days=30, 
                       product_count=0, total_quantity=0, total_value=Decimal('0')),
            AgingBucket(bucket_name="31-90 days (Aging)", min_days=31, max_days=90,
                       product_count=0, total_quantity=0, total_value=Decimal('0')),
            AgingBucket(bucket_name="91-180 days (Stale)", min_days=91, max_days=180,
                       product_count=0, total_quantity=0, total_value=Decimal('0')),
            AgingBucket(bucket_name="180+ days (Dead Stock)", min_days=181, max_days=None,
                       product_count=0, total_quantity=0, total_value=Decimal('0'))
        ]
        
        # Populate buckets
        for product in aged_products:
            age = product.age_days
            if age <= 30:
                bucket = aging_buckets[0]
            elif age <= 90:
                bucket = aging_buckets[1]
            elif age <= 180:
                bucket = aging_buckets[2]
            else:
                bucket = aging_buckets[3]
            
            bucket.product_count += 1
            bucket.total_quantity += product.quantity
            bucket.total_value += product.value
        
        return InventoryAgingReport(
            generated_at=datetime.utcnow(),
            total_products=len(aged_products),
            total_quantity=total_quantity,
            total_value=total_value,
            aging_buckets=aging_buckets,
            aged_products=sorted(aged_products, key=lambda x: x.age_days, reverse=True),
            dead_stock_count=dead_stock_count,
            dead_stock_value=dead_stock_value
        )
