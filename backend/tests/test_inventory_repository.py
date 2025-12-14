"""
Unit Tests for Inventory Level Repository

Tests for InventoryLevelRepository operations including stock queries,
low stock identification, and inventory updates.
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.inventory import InventoryLevel, StockLocation
from app.models.product import Product, ProductVariant
from app.repositories.inventory import InventoryLevelRepository
from app.repositories.product import ProductRepository, ProductVariantRepository


pytestmark = pytest.mark.asyncio


class TestInventoryLevelRepository:
    """Tests for InventoryLevelRepository"""
    
    async def test_create_inventory_level(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        sample_warehouse: StockLocation
    ):
        """Test creating an inventory level"""
        repo = InventoryLevelRepository(db_session)
        
        inventory_data = {
            "product_variant_id": sample_variant.id,
            "warehouse_id": sample_warehouse.id,
            "quantity_on_hand": 100,
            "quantity_available": 95,
            "quantity_reserved": 5,
            "reorder_point": 20,
            "reorder_quantity": 50
        }
        
        inventory = await repo.create(inventory_data)
        
        assert inventory.id is not None
        assert inventory.quantity_on_hand == 100
        assert inventory.quantity_available == 95
        assert inventory.quantity_reserved == 5
    
    async def test_get_by_variant_and_location(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        sample_location: StockLocation
    ):
        """Test getting inventory by variant and location"""
        repo = InventoryLevelRepository(db_session)
        
        # Create inventory
        await repo.create({
            "product_variant_id": sample_variant.id,
            "warehouse_id": sample_location.id,
            "quantity_on_hand": 50
        })
        
        # Retrieve
        inventory = await repo.get_by_variant_and_warehouse(
            sample_variant.id,
            sample_location.id
        )
        
        assert inventory is not None
        assert inventory.product_variant_id == sample_variant.id
        assert inventory.warehouse_id == sample_location.id
        assert inventory.quantity_on_hand == 50
    
    async def test_get_total_stock_for_variant(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        multiple_warehouses
    ):
        """Test getting total stock across all warehouses for a variant"""
        repo = InventoryLevelRepository(db_session)
        
        # Create inventory in multiple warehouses
        quantities = [100, 50, 25]
        for warehouse, qty in zip(multiple_warehouses, quantities):
            await repo.create({
                "product_variant_id": sample_variant.id,
                "warehouse_id": warehouse.id,
                "quantity_on_hand": qty
            })
        
        # Get total stock
        total = await repo.get_total_stock_for_variant(sample_variant.id)
        
        assert total == sum(quantities)  # 100 + 50 + 25 = 175
    
    async def test_get_low_stock_items(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        sample_warehouse: Warehouse
    ):
        """Test getting items below reorder point"""
        repo = InventoryLevelRepository(db_session)
        
        # Create low stock item
        await repo.create({
            "product_variant_id": sample_variant.id,
            "warehouse_id": sample_warehouse.id,
            "quantity_on_hand": 10,
            "reorder_point": 20,
            "reorder_quantity": 50
        })
        
        # Get low stock items
        low_stock, total = await repo.get_low_stock_items(skip=0, limit=10)
        
        assert total >= 1
        assert any(
            item.product_variant_id == sample_variant.id
            for item in low_stock
        )
    
    async def test_update_stock_quantity(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        sample_warehouse: Warehouse
    ):
        """Test updating stock quantity"""
        repo = InventoryLevelRepository(db_session)
        
        # Create inventory
        inventory = await repo.create({
            "product_variant_id": sample_variant.id,
            "warehouse_id": sample_warehouse.id,
            "quantity_on_hand": 100,
            "quantity_available": 100
        })
        
        # Update quantity
        updated = await repo.update(inventory.id, {
            "quantity_on_hand": 150,
            "quantity_available": 140,
            "quantity_reserved": 10
        })
        
        assert updated.quantity_on_hand == 150
        assert updated.quantity_available == 140
        assert updated.quantity_reserved == 10
    
    async def test_update_reorder_settings(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        sample_warehouse: Warehouse
    ):
        """Test updating reorder point and quantity"""
        repo = InventoryLevelRepository(db_session)
        
        # Create inventory
        inventory = await repo.create({
            "product_variant_id": sample_variant.id,
            "warehouse_id": sample_warehouse.id,
            "quantity_on_hand": 50,
            "reorder_point": 20,
            "reorder_quantity": 50
        })
        
        # Update reorder settings
        updated = await repo.update(inventory.id, {
            "reorder_point": 30,
            "reorder_quantity": 100
        })
        
        assert updated.reorder_point == 30
        assert updated.reorder_quantity == 100
    
    async def test_get_by_warehouse(
        self,
        db_session: AsyncSession,
        sample_warehouse: Warehouse,
        multiple_variants
    ):
        """Test getting all inventory for a warehouse"""
        repo = InventoryLevelRepository(db_session)
        
        # Create inventory for multiple variants
        for variant in multiple_variants:
            await repo.create({
                "product_variant_id": variant.id,
                "warehouse_id": sample_warehouse.id,
                "quantity_on_hand": 50
            })
        
        # Get inventory for warehouse
        inventory_list = await repo.get_by_warehouse(
            sample_warehouse.id,
            limit=10
        )
        
        assert len(inventory_list) >= len(multiple_variants)
    
    async def test_search_inventory(
        self,
        db_session: AsyncSession,
        sample_variant: ProductVariant,
        sample_warehouse: Warehouse
    ):
        """Test searching inventory"""
        repo = InventoryLevelRepository(db_session)
        
        # Create inventory
        await repo.create({
            "product_variant_id": sample_variant.id,
            "warehouse_id": sample_warehouse.id,
            "quantity_on_hand": 75,
            "quantity_available": 70
        })
        
        # Search
        results, total = await repo.search(
            query=sample_variant.sku,
            skip=0,
            limit=10
        )
        
        assert total >= 1
        assert any(
            item.product_variant_id == sample_variant.id
            for item in results
        )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def sample_variant(
    db_session: AsyncSession,
    sample_product: Product
) -> ProductVariant:
    """Create a sample product variant for testing"""
    repo = ProductVariantRepository(db_session)
    
    variant_data = {
        "product_id": sample_product.id,
        "sku": f"VAR-{uuid4().hex[:8].upper()}",
        "size": "M",
        "color": "Blue",
        "retail_price": 25.0,
        "is_active": True
    }
    
    variant = await repo.create(variant_data)
    return variant


@pytest.fixture
async def sample_product(db_session: AsyncSession) -> Product:
    """Create a sample product for testing"""
    repo = ProductRepository(db_session)
    
    product_data = {
        "sku": f"PROD-{uuid4().hex[:8].upper()}",
        "name": "Sample Product",
        "description": "A sample product for testing",
        "unit_cost": 10.0,
        "wholesale_price": 15.0,
        "retail_price": 20.0,
        "is_active": True
    }
    
    product = await repo.create(product_data)
    return product


@pytest.fixture
async def sample_warehouse(db_session: AsyncSession) -> Warehouse:
    """Create a sample warehouse for testing"""
    from app.repositories.warehouse import WarehouseRepository
    
    repo = WarehouseRepository(db_session)
    
    warehouse_data = {
        "name": "Main Warehouse",
        "code": "MAIN",
        "address": "123 Main St",
        "city": "Test City",
        "state": "TS",
        "zip_code": "12345",
        "is_active": True
    }
    
    warehouse = await repo.create(warehouse_data)
    return warehouse


@pytest.fixture
async def multiple_warehouses(db_session: AsyncSession):
    """Create multiple warehouses for testing"""
    from app.repositories.warehouse import WarehouseRepository
    
    repo = WarehouseRepository(db_session)
    
    warehouses = []
    for i in range(3):
        warehouse = await repo.create({
            "name": f"Warehouse {i+1}",
            "code": f"WH{i+1}",
            "address": f"{i+1}00 Test St",
            "city": "Test City",
            "state": "TS",
            "zip_code": f"1234{i}",
            "is_active": True
        })
        warehouses.append(warehouse)
    
    return warehouses


@pytest.fixture
async def multiple_variants(
    db_session: AsyncSession,
    sample_product: Product
):
    """Create multiple product variants for testing"""
    repo = ProductVariantRepository(db_session)
    
    variants = []
    sizes = ["S", "M", "L"]
    for size in sizes:
        variant = await repo.create({
            "product_id": sample_product.id,
            "sku": f"VAR-{size}-{uuid4().hex[:6].upper()}",
            "size": size,
            "retail_price": 25.0,
            "is_active": True
        })
        variants.append(variant)
    
    return variants
