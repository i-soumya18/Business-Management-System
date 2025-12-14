"""
Unit Tests for Product Repository

Tests for ProductRepository and ProductVariantRepository operations.
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductVariant
from app.models.category import Category
from app.models.brand import Brand
from app.repositories.product import ProductRepository, ProductVariantRepository


pytestmark = pytest.mark.asyncio


class TestProductRepository:
    """Tests for ProductRepository"""
    
    async def test_create_product(self, db_session: AsyncSession):
        """Test creating a product"""
        repo = ProductRepository(db_session)
        
        product_data = {
            "sku": "TEST-001",
            "name": "Test Product",
            "slug": "test-product",
            "description": "A test product",
            "base_cost_price": 10.0,
            "base_wholesale_price": 15.0,
            "base_retail_price": 20.0,
            "is_active": True
        }
        
        product = await repo.create(product_data)
        
        assert product.id is not None
        assert product.sku == "TEST-001"
        assert product.name == "Test Product"
        assert product.base_retail_price == 20.0
    
    async def test_get_by_id(self, db_session: AsyncSession):
        """Test getting a product by ID"""
        repo = ProductRepository(db_session)
        
        # Create a product first
        product_data = {
            "sku": "TEST-002",
            "name": "Another Test Product",
            "slug": "another-test-product",
            "base_cost_price": 5.0,
            "base_retail_price": 10.0
        }
        created_product = await repo.create(product_data)
        
        # Retrieve it
        retrieved_product = await repo.get_by_id(created_product.id)
        
        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.sku == "TEST-002"
    
    async def test_get_by_sku(self, db_session: AsyncSession):
        """Test getting a product by SKU"""
        repo = ProductRepository(db_session)
        
        product_data = {
            "sku": "UNIQUE-SKU-001",
            "name": "SKU Test Product",
            "slug": "sku-test-product",
            "base_retail_price": 25.0
        }
        await repo.create(product_data)
        
        # Retrieve by SKU
        product = await repo.get_by_sku("UNIQUE-SKU-001")
        
        assert product is not None
        assert product.sku == "UNIQUE-SKU-001"
        assert product.name == "SKU Test Product"
    
    async def test_update_product(self, db_session: AsyncSession):
        """Test updating a product"""
        repo = ProductRepository(db_session)
        
        # Create product
        product_data = {
            "sku": "UPDATE-001",
            "name": "Original Name",
            "slug": "original-name",
            "base_retail_price": 30.0
        }
        product = await repo.create(product_data)
        
        # Update it
        updated_product = await repo.update(product.id, {
            "name": "Updated Name",
            "base_retail_price": 35.0
        })
        
        assert updated_product is not None
        assert updated_product.name == "Updated Name"
        assert updated_product.base_retail_price == 35.0
        assert updated_product.sku == "UPDATE-001"  # SKU unchanged
    
    async def test_delete_product(self, db_session: AsyncSession):
        """Test deleting a product"""
        repo = ProductRepository(db_session)
        
        # Create product
        product_data = {
            "sku": "DELETE-001",
            "name": "To Be Deleted",
            "slug": "to-be-deleted",
            "base_retail_price": 10.0
        }
        product = await repo.create(product_data)
        
        # Delete it
        deleted = await repo.delete(product.id)
        
        assert deleted is True
        
        # Verify it's gone
        retrieved = await repo.get_by_id(product.id)
        assert retrieved is None
    
    async def test_search_products(self, db_session: AsyncSession):
        """Test searching products"""
        repo = ProductRepository(db_session)
        
        # Create multiple products
        for i in range(5):
            await repo.create({
                "sku": f"SEARCH-{i:03d}",
                "name": f"Search Product {i}",
                "slug": f"search-product-{i}",
                "base_retail_price": 10.0 * (i + 1)
            })
        
        # Search by name
        results, total = await repo.search("Search Product", skip=0, limit=10)
        
        assert total >= 5
        assert len(results) >= 5


class TestProductVariantRepository:
    """Tests for ProductVariantRepository"""
    
    async def test_create_variant(self, db_session: AsyncSession, sample_product: Product):
        """Test creating a product variant"""
        repo = ProductVariantRepository(db_session)
        
        variant_data = {
            "product_id": sample_product.id,
            "sku": "VAR-001",
            "size": "M",
            "color": "Blue",
            "retail_price": 25.0,
            "is_active": True
        }
        
        variant = await repo.create(variant_data)
        
        assert variant.id is not None
        assert variant.sku == "VAR-001"
        assert variant.size == "M"
        assert variant.color == "Blue"
        assert variant.product_id == sample_product.id
    
    async def test_get_by_sku(self, db_session: AsyncSession, sample_product: Product):
        """Test getting variant by SKU"""
        repo = ProductVariantRepository(db_session)
        
        variant_data = {
            "product_id": sample_product.id,
            "sku": "VAR-SKU-001",
            "size": "L",
            "retail_price": 30.0
        }
        await repo.create(variant_data)
        
        # Retrieve by SKU
        variant = await repo.get_by_sku("VAR-SKU-001")
        
        assert variant is not None
        assert variant.sku == "VAR-SKU-001"
        assert variant.size == "L"
    
    async def test_get_by_barcode(self, db_session: AsyncSession, sample_product: Product):
        """Test getting variant by barcode"""
        repo = ProductVariantRepository(db_session)
        
        variant_data = {
            "product_id": sample_product.id,
            "sku": "VAR-002",
            "barcode": "1234567890123",
            "size": "XL",
            "retail_price": 35.0
        }
        await repo.create(variant_data)
        
        # Retrieve by barcode
        variant = await repo.get_by_barcode("1234567890123")
        
        assert variant is not None
        assert variant.barcode == "1234567890123"
        assert variant.size == "XL"
    
    async def test_get_by_product(self, db_session: AsyncSession, sample_product: Product):
        """Test getting all variants for a product"""
        repo = ProductVariantRepository(db_session)
        
        # Create multiple variants
        sizes = ["S", "M", "L", "XL"]
        for size in sizes:
            await repo.create({
                "product_id": sample_product.id,
                "sku": f"VAR-{size}",
                "size": size,
                "retail_price": 25.0
            })
        
        # Get all variants for product
        variants = await repo.get_by_product(sample_product.id, limit=10)
        
        assert len(variants) >= 4
        variant_sizes = [v.size for v in variants]
        for size in sizes:
            assert size in variant_sizes


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def sample_product(db_session: AsyncSession) -> Product:
    """Create a sample product for testing"""
    repo = ProductRepository(db_session)
    
    product_data = {
        "sku": "SAMPLE-PROD-001",
        "name": "Sample Product",
        "slug": "sample-product",
        "description": "A sample product for testing",
        "base_cost_price": 10.0,
        "base_wholesale_price": 15.0,
        "base_retail_price": 20.0,
        "is_active": True
    }
    
    product = await repo.create(product_data)
    return product


@pytest.fixture
async def sample_category(db_session: AsyncSession) -> Category:
    """Create a sample category for testing"""
    from app.repositories.category_brand_supplier import CategoryRepository
    
    repo = CategoryRepository(db_session)
    
    category_data = {
        "name": "Test Category",
        "slug": "test-category",
        "description": "A test category"
    }
    
    category = await repo.create(category_data)
    return category


@pytest.fixture
async def sample_brand(db_session: AsyncSession) -> Brand:
    """Create a sample brand for testing"""
    from app.repositories.category_brand_supplier import BrandRepository
    
    repo = BrandRepository(db_session)
    
    brand_data = {
        "name": "Test Brand",
        "code": "TST",
        "slug": "test-brand",
        "description": "A test brand"
    }
    
    brand = await repo.create(brand_data)
    return brand
