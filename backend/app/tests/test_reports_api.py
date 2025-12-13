"""
Tests for reporting API endpoints
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from httpx import AsyncClient


@pytest.mark.asyncio
class TestInventorySummaryReport:
    """Tests for inventory summary report"""
    
    async def test_get_inventory_summary(
        self,
        client: AsyncClient,
        sample_products_with_inventory
    ):
        """Test getting inventory summary report"""
        response = await client.get("/api/v1/reports/inventory-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_at" in data
        assert "total_products" in data
        assert "total_variants" in data
        assert "total_quantity" in data
        assert "total_stock_value" in data
        assert "low_stock_count" in data
        assert "out_of_stock_count" in data
        assert "categories" in data
        assert "locations" in data
        
        assert isinstance(data["categories"], list)
        assert isinstance(data["locations"], list)
    
    async def test_inventory_summary_with_category_filter(
        self,
        client: AsyncClient,
        sample_category,
        sample_products_with_inventory
    ):
        """Test inventory summary filtered by category"""
        response = await client.get(
            f"/api/v1/reports/inventory-summary?category_id={sample_category.id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should only include products from the specified category
        if data["categories"]:
            assert all(cat["category_id"] == sample_category.id for cat in data["categories"])
    
    async def test_inventory_summary_with_location_filter(
        self,
        client: AsyncClient,
        sample_location,
        sample_products_with_inventory
    ):
        """Test inventory summary filtered by location"""
        response = await client.get(
            f"/api/v1/reports/inventory-summary?location_id={sample_location.id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should only include inventory from the specified location
        if data["locations"]:
            assert all(loc["location_id"] == sample_location.id for loc in data["locations"])
    
    async def test_inventory_summary_include_inactive(
        self,
        client: AsyncClient,
        sample_inactive_product
    ):
        """Test inventory summary with inactive products"""
        # Without include_inactive
        response1 = await client.get("/api/v1/reports/inventory-summary")
        assert response1.status_code == 200
        count1 = response1.json()["total_products"]
        
        # With include_inactive
        response2 = await client.get("/api/v1/reports/inventory-summary?include_inactive=true")
        assert response2.status_code == 200
        count2 = response2.json()["total_products"]
        
        # Should have more products when including inactive
        assert count2 >= count1


@pytest.mark.asyncio
class TestStockValuationReport:
    """Tests for stock valuation report"""
    
    async def test_get_stock_valuation(
        self,
        client: AsyncClient,
        sample_products_with_inventory
    ):
        """Test getting stock valuation report"""
        response = await client.get("/api/v1/reports/stock-valuation")
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_at" in data
        assert "total_cost_value" in data
        assert "total_selling_value" in data
        assert "total_potential_profit" in data
        assert "average_profit_margin" in data
        assert "total_items" in data
        assert "products" in data
        
        # Validate product valuation structure
        if data["products"]:
            product = data["products"][0]
            assert "product_id" in product
            assert "sku" in product
            assert "name" in product
            assert "total_quantity" in product
            assert "cost_price" in product
            assert "selling_price" in product
            assert "total_cost_value" in product
            assert "total_selling_value" in product
            assert "potential_profit" in product
            assert "profit_margin_percentage" in product
    
    async def test_stock_valuation_with_category_filter(
        self,
        client: AsyncClient,
        sample_category,
        sample_products_with_inventory
    ):
        """Test stock valuation filtered by category"""
        response = await client.get(
            f"/api/v1/reports/stock-valuation?category_id={sample_category.id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        # All products should be from the specified category
        if data["products"]:
            assert all(p["category_name"] == sample_category.name for p in data["products"])
    
    async def test_stock_valuation_with_limit(
        self,
        client: AsyncClient,
        sample_products_with_inventory
    ):
        """Test stock valuation with result limit"""
        response = await client.get("/api/v1/reports/stock-valuation?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["products"]) <= 5
    
    async def test_stock_valuation_profit_calculations(
        self,
        client: AsyncClient,
        sample_products_with_inventory
    ):
        """Test that profit calculations are correct"""
        response = await client.get("/api/v1/reports/stock-valuation")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify profit = selling_value - cost_value
        for product in data["products"]:
            expected_profit = float(product["total_selling_value"]) - float(product["total_cost_value"])
            actual_profit = float(product["potential_profit"])
            assert abs(expected_profit - actual_profit) < 0.01  # Allow for rounding


@pytest.mark.asyncio
class TestLowStockReport:
    """Tests for low stock report"""
    
    async def test_get_low_stock_report(
        self,
        client: AsyncClient,
        sample_low_stock_items
    ):
        """Test getting low stock report"""
        response = await client.get("/api/v1/reports/low-stock")
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_at" in data
        assert "critical_items" in data
        assert "low_stock_items" in data
        assert "out_of_stock_items" in data
        assert "total_shortage_value" in data
        assert "items" in data
        
        # Validate low stock item structure
        if data["items"]:
            item = data["items"][0]
            assert "product_id" in item
            assert "sku" in item
            assert "name" in item
            assert "current_quantity" in item
            assert "reorder_point" in item
            assert "reorder_quantity" in item
            assert "shortage" in item
            assert "status" in item
            assert item["status"] in ['critical', 'low', 'out_of_stock']
    
    async def test_low_stock_report_status_filter_critical(
        self,
        client: AsyncClient,
        sample_low_stock_items
    ):
        """Test low stock report filtered by critical status"""
        response = await client.get("/api/v1/reports/low-stock?status=critical")
        assert response.status_code == 200
        
        data = response.json()
        # All items should be critical
        if data["items"]:
            assert all(item["status"] == "critical" for item in data["items"])
    
    async def test_low_stock_report_status_filter_out_of_stock(
        self,
        client: AsyncClient,
        sample_out_of_stock_item
    ):
        """Test low stock report filtered by out of stock status"""
        response = await client.get("/api/v1/reports/low-stock?status=out_of_stock")
        assert response.status_code == 200
        
        data = response.json()
        # All items should be out of stock
        if data["items"]:
            assert all(item["status"] == "out_of_stock" for item in data["items"])
            assert all(item["current_quantity"] == 0 for item in data["items"])
    
    async def test_low_stock_report_with_filters(
        self,
        client: AsyncClient,
        sample_category,
        sample_location,
        sample_low_stock_items
    ):
        """Test low stock report with category and location filters"""
        response = await client.get(
            f"/api/v1/reports/low-stock?category_id={sample_category.id}&location_id={sample_location.id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data["items"], list)


@pytest.mark.asyncio
class TestStockMovementReport:
    """Tests for stock movement report"""
    
    async def test_get_stock_movement_report(
        self,
        client: AsyncClient,
        sample_inventory_movements
    ):
        """Test getting stock movement report"""
        response = await client.get("/api/v1/reports/stock-movement")
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_at" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "total_movements" in data
        assert "total_quantity_in" in data
        assert "total_quantity_out" in data
        assert "net_change" in data
        assert "movement_summary" in data
        assert "product_details" in data
    
    async def test_stock_movement_with_date_range(
        self,
        client: AsyncClient,
        sample_inventory_movements
    ):
        """Test stock movement report with custom date range"""
        start = (date.today() - timedelta(days=7)).isoformat()
        end = date.today().isoformat()
        
        response = await client.get(
            f"/api/v1/reports/stock-movement?start_date={start}&end_date={end}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["start_date"] == start
        assert data["end_date"] == end
    
    async def test_stock_movement_by_type(
        self,
        client: AsyncClient,
        sample_inventory_movements
    ):
        """Test stock movement report filtered by movement type"""
        response = await client.get("/api/v1/reports/stock-movement?movement_type=purchase")
        assert response.status_code == 200
        
        data = response.json()
        # Should only show purchase movements
        if data["movement_summary"]:
            assert all(m["movement_type"] == "purchase" for m in data["movement_summary"])
    
    async def test_stock_movement_by_product(
        self,
        client: AsyncClient,
        sample_product,
        sample_inventory_movements
    ):
        """Test stock movement report for specific product"""
        response = await client.get(
            f"/api/v1/reports/stock-movement?product_id={sample_product.id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_movements"] >= 0
    
    async def test_stock_movement_net_change_calculation(
        self,
        client: AsyncClient,
        sample_inventory_movements
    ):
        """Test that net change calculation is correct"""
        response = await client.get("/api/v1/reports/stock-movement")
        assert response.status_code == 200
        
        data = response.json()
        expected_net = data["total_quantity_in"] - data["total_quantity_out"]
        assert data["net_change"] == expected_net


@pytest.mark.asyncio
class TestInventoryAgingReport:
    """Tests for inventory aging report"""
    
    async def test_get_inventory_aging_report(
        self,
        client: AsyncClient,
        sample_aged_inventory
    ):
        """Test getting inventory aging report"""
        response = await client.get("/api/v1/reports/inventory-aging")
        assert response.status_code == 200
        
        data = response.json()
        assert "generated_at" in data
        assert "total_products" in data
        assert "total_quantity" in data
        assert "total_value" in data
        assert "aging_buckets" in data
        assert "aged_products" in data
        assert "dead_stock_count" in data
        assert "dead_stock_value" in data
        
        # Validate aging buckets
        assert len(data["aging_buckets"]) == 4  # 0-30, 31-90, 91-180, 180+
        for bucket in data["aging_buckets"]:
            assert "bucket_name" in bucket
            assert "min_days" in bucket
            assert "product_count" in bucket
            assert "total_quantity" in bucket
            assert "total_value" in bucket
    
    async def test_aging_report_with_category_filter(
        self,
        client: AsyncClient,
        sample_category,
        sample_aged_inventory
    ):
        """Test aging report filtered by category"""
        response = await client.get(
            f"/api/v1/reports/inventory-aging?category_id={sample_category.id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        # All products should be from the specified category
        if data["aged_products"]:
            assert all(p["category_name"] == sample_category.name for p in data["aged_products"])
    
    async def test_aging_report_with_age_filters(
        self,
        client: AsyncClient,
        sample_aged_inventory
    ):
        """Test aging report with min/max age filters"""
        response = await client.get(
            "/api/v1/reports/inventory-aging?min_age_days=30&max_age_days=90"
        )
        assert response.status_code == 200
        
        data = response.json()
        # All products should be within the age range
        if data["aged_products"]:
            assert all(30 <= p["age_days"] <= 90 for p in data["aged_products"])
    
    async def test_aging_report_dead_stock_identification(
        self,
        client: AsyncClient,
        sample_dead_stock
    ):
        """Test that dead stock (180+ days) is correctly identified"""
        response = await client.get("/api/v1/reports/inventory-aging")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check that dead stock items are marked
        dead_stock_items = [p for p in data["aged_products"] if p["status"] == "dead_stock"]
        assert all(item["age_days"] > 180 for item in dead_stock_items)
        
        # Verify dead stock count
        assert data["dead_stock_count"] == len(dead_stock_items)
    
    async def test_aging_report_status_classification(
        self,
        client: AsyncClient,
        sample_aged_inventory
    ):
        """Test that aging status is correctly classified"""
        response = await client.get("/api/v1/reports/inventory-aging")
        assert response.status_code == 200
        
        data = response.json()
        
        for product in data["aged_products"]:
            age = product["age_days"]
            status = product["status"]
            
            # Verify status matches age
            if age > 180:
                assert status == "dead_stock"
            elif age > 90:
                assert status == "stale"
            elif age > 30:
                assert status == "aging"
            else:
                assert status == "fresh"


# Test Fixtures

@pytest.fixture
async def sample_products_with_inventory(db_session, sample_category, sample_location):
    """Create sample products with inventory levels"""
    from app.repositories.inventory import ProductRepository, InventoryLevelRepository
    
    prod_repo = ProductRepository(db_session)
    inv_repo = InventoryLevelRepository(db_session)
    
    products = []
    for i in range(5):
        product = await prod_repo.create({
            "sku": f"TEST-{i:03d}",
            "name": f"Test Product {i}",
            "category_id": sample_category.id,
            "cost_price": 10.00 + i,
            "selling_price": 20.00 + i * 2
        })
        products.append(product)
        
        # Add inventory
        await inv_repo.create({
            "product_id": product.id,
            "location_id": sample_location.id,
            "quantity": 100 + i * 10,
            "reorder_point": 20,
            "reorder_quantity": 50
        })
    
    return products


@pytest.fixture
async def sample_low_stock_items(db_session, sample_category, sample_location):
    """Create sample products with low stock"""
    from app.repositories.inventory import ProductRepository, InventoryLevelRepository
    
    prod_repo = ProductRepository(db_session)
    inv_repo = InventoryLevelRepository(db_session)
    
    items = []
    for i, qty in enumerate([5, 10, 15]):  # All below reorder point of 20
        product = await prod_repo.create({
            "sku": f"LOW-{i:03d}",
            "name": f"Low Stock Item {i}",
            "category_id": sample_category.id,
            "cost_price": 10.00,
            "selling_price": 20.00
        })
        
        inv = await inv_repo.create({
            "product_id": product.id,
            "location_id": sample_location.id,
            "quantity": qty,
            "reorder_point": 20,
            "reorder_quantity": 50
        })
        items.append(inv)
    
    return items


@pytest.fixture
async def sample_out_of_stock_item(db_session, sample_category, sample_location):
    """Create a product that is out of stock"""
    from app.repositories.inventory import ProductRepository, InventoryLevelRepository
    
    prod_repo = ProductRepository(db_session)
    inv_repo = InventoryLevelRepository(db_session)
    
    product = await prod_repo.create({
        "sku": "OUT-001",
        "name": "Out of Stock Item",
        "category_id": sample_category.id,
        "cost_price": 10.00,
        "selling_price": 20.00
    })
    
    return await inv_repo.create({
        "product_id": product.id,
        "location_id": sample_location.id,
        "quantity": 0,
        "reorder_point": 20,
        "reorder_quantity": 50
    })


@pytest.fixture
async def sample_inventory_movements(db_session, sample_product, sample_location):
    """Create sample inventory movements"""
    from app.repositories.inventory import InventoryMovementRepository
    
    repo = InventoryMovementRepository(db_session)
    
    movements = []
    for i in range(10):
        movement = await repo.create({
            "product_id": sample_product.id,
            "location_id": sample_location.id,
            "movement_type": "purchase" if i % 2 == 0 else "sale",
            "quantity_change": 10 if i % 2 == 0 else -5,
            "reference_number": f"REF-{i:03d}",
            "notes": f"Test movement {i}"
        })
        movements.append(movement)
    
    return movements


@pytest.fixture
async def sample_aged_inventory(db_session, sample_category, sample_location):
    """Create sample products with varying ages"""
    from app.repositories.inventory import (
        ProductRepository,
        InventoryLevelRepository,
        InventoryMovementRepository
    )
    
    prod_repo = ProductRepository(db_session)
    inv_repo = InventoryLevelRepository(db_session)
    mov_repo = InventoryMovementRepository(db_session)
    
    ages = [10, 45, 120, 200]  # Fresh, aging, stale, dead stock
    products = []
    
    for i, age_days in enumerate(ages):
        product = await prod_repo.create({
            "sku": f"AGE-{i:03d}",
            "name": f"Aged Item {i}",
            "category_id": sample_category.id,
            "cost_price": 10.00,
            "selling_price": 20.00
        })
        
        await inv_repo.create({
            "product_id": product.id,
            "location_id": sample_location.id,
            "quantity": 50,
            "reorder_point": 20,
            "reorder_quantity": 50
        })
        
        # Create a movement with old date
        movement_date = datetime.utcnow() - timedelta(days=age_days)
        await mov_repo.create({
            "product_id": product.id,
            "location_id": sample_location.id,
            "movement_type": "purchase",
            "quantity_change": 50,
            "reference_number": f"OLD-{i:03d}",
            "movement_date": movement_date
        })
        
        products.append(product)
    
    return products


@pytest.fixture
async def sample_dead_stock(db_session, sample_category, sample_location):
    """Create a dead stock item (180+ days old)"""
    from app.repositories.inventory import (
        ProductRepository,
        InventoryLevelRepository,
        InventoryMovementRepository
    )
    
    prod_repo = ProductRepository(db_session)
    inv_repo = InventoryLevelRepository(db_session)
    mov_repo = InventoryMovementRepository(db_session)
    
    product = await prod_repo.create({
        "sku": "DEAD-001",
        "name": "Dead Stock Item",
        "category_id": sample_category.id,
        "cost_price": 10.00,
        "selling_price": 20.00
    })
    
    await inv_repo.create({
        "product_id": product.id,
        "location_id": sample_location.id,
        "quantity": 100,
        "reorder_point": 20,
        "reorder_quantity": 50
    })
    
    # Create old movement (200 days ago)
    old_date = datetime.utcnow() - timedelta(days=200)
    await mov_repo.create({
        "product_id": product.id,
        "location_id": sample_location.id,
        "movement_type": "purchase",
        "quantity_change": 100,
        "reference_number": "DEAD-REF",
        "movement_date": old_date
    })
    
    return product


@pytest.fixture
async def sample_inactive_product(db_session, sample_category):
    """Create an inactive product"""
    from app.repositories.inventory import ProductRepository
    
    repo = ProductRepository(db_session)
    return await repo.create({
        "sku": "INACTIVE-001",
        "name": "Inactive Product",
        "category_id": sample_category.id,
        "cost_price": 10.00,
        "selling_price": 20.00,
        "is_active": False
    })
