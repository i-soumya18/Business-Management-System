"""
Integration Tests for Product API Endpoints

Tests for Product and ProductVariant CRUD operations via the API.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4

from app.main import app


pytestmark = pytest.mark.asyncio


class TestProductEndpoints:
    """Tests for Product API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_product(self, client: AsyncClient):
        """Test creating a product via API"""
        product_data = {
            "sku": f"TEST-{uuid4().hex[:8].upper()}",
            "name": "Test Product",
            "slug": f"test-product-{uuid4().hex[:8]}",
            "description": "A test product",
            "base_cost_price": 10.0,
            "base_wholesale_price": 15.0,
            "base_retail_price": 20.0,
            "is_active": True
        }
        
        response = await client.post("/api/v1/inventory/products/", json=product_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["sku"] == product_data["sku"]
        assert data["name"] == product_data["name"]
        assert data["base_retail_price"] == product_data["base_retail_price"]
    
    async def test_create_product_duplicate_sku(self, client: AsyncClient):
        """Test creating a product with duplicate SKU fails"""
        sku = f"DUP-{uuid4().hex[:8].upper()}"
        product_data = {
            "sku": sku,
            "name": "Product 1",
            "slug": f"product-1-{uuid4().hex[:8]}",
            "base_retail_price": 20.0
        }
        
        # Create first product
        response1 = await client.post("/api/v1/inventory/products/", json=product_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        product_data["name"] = "Product 2"
        response2 = await client.post("/api/v1/inventory/products/", json=product_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_list_products(self, client: AsyncClient):
        """Test listing products"""
        # Create a few products
        for i in range(3):
            await client.post("/api/v1/inventory/products/", json={
                "sku": f"LIST-{i}-{uuid4().hex[:6].upper()}",
                "name": f"List Product {i}",
                "retail_price": 10.0 * (i + 1)
            })
        
        # List products
        response = await client.get("/api/v1/inventory/products/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 3
    
    async def test_get_product_by_id(self, client: AsyncClient):
        """Test getting a product by ID"""
        # Create product
        create_response = await client.post("/api/v1/inventory/products/", json={
            "sku": f"GET-{uuid4().hex[:8].upper()}",
            "name": "Get Product",
            "retail_price": 25.0
        })
        product_id = create_response.json()["id"]
        
        # Get product
        response = await client.get(f"/api/v1/inventory/products/{product_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == product_id
        assert data["name"] == "Get Product"
    
    async def test_get_product_by_sku(self, client: AsyncClient):
        """Test getting a product by SKU"""
        sku = f"SKU-{uuid4().hex[:8].upper()}"
        
        # Create product
        await client.post("/api/v1/inventory/products/", json={
            "sku": sku,
            "name": "SKU Product",
            "retail_price": 30.0
        })
        
        # Get by SKU
        response = await client.get(f"/api/v1/inventory/products/sku/{sku}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sku"] == sku
        assert data["name"] == "SKU Product"
    
    async def test_update_product(self, client: AsyncClient):
        """Test updating a product"""
        # Create product
        create_response = await client.post("/api/v1/inventory/products/", json={
            "sku": f"UPD-{uuid4().hex[:8].upper()}",
            "name": "Original Name",
            "retail_price": 20.0
        })
        product_id = create_response.json()["id"]
        
        # Update product
        update_data = {
            "name": "Updated Name",
            "retail_price": 25.0
        }
        response = await client.put(
            f"/api/v1/inventory/products/{product_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["retail_price"] == 25.0
    
    async def test_delete_product(self, client: AsyncClient):
        """Test deleting a product"""
        # Create product
        create_response = await client.post("/api/v1/inventory/products/", json={
            "sku": f"DEL-{uuid4().hex[:8].upper()}",
            "name": "To Delete",
            "retail_price": 15.0
        })
        product_id = create_response.json()["id"]
        
        # Delete product
        response = await client.delete(f"/api/v1/inventory/products/{product_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        get_response = await client.get(f"/api/v1/inventory/products/{product_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_activate_product(self, client: AsyncClient):
        """Test activating a product"""
        # Create inactive product
        create_response = await client.post("/api/v1/inventory/products/", json={
            "sku": f"ACT-{uuid4().hex[:8].upper()}",
            "name": "Inactive Product",
            "retail_price": 20.0,
            "is_active": False
        })
        product_id = create_response.json()["id"]
        
        # Activate
        response = await client.patch(f"/api/v1/inventory/products/{product_id}/activate")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is True
    
    async def test_deactivate_product(self, client: AsyncClient):
        """Test deactivating a product"""
        # Create active product
        create_response = await client.post("/api/v1/inventory/products/", json={
            "sku": f"DEACT-{uuid4().hex[:8].upper()}",
            "name": "Active Product",
            "retail_price": 20.0,
            "is_active": True
        })
        product_id = create_response.json()["id"]
        
        # Deactivate
        response = await client.patch(f"/api/v1/inventory/products/{product_id}/deactivate")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False


class TestProductVariantEndpoints:
    """Tests for ProductVariant API endpoints"""
    
    async def test_create_variant(self, client: AsyncClient, sample_product_id: str):
        """Test creating a product variant"""
        variant_data = {
            "product_id": sample_product_id,
            "sku": f"VAR-{uuid4().hex[:8].upper()}",
            "size": "M",
            "color": "Blue",
            "retail_price": 25.0,
            "is_active": True
        }
        
        response = await client.post("/api/v1/inventory/variants/", json=variant_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["sku"] == variant_data["sku"]
        assert data["size"] == "M"
        assert data["color"] == "Blue"
    
    async def test_create_variant_duplicate_sku(
        self,
        client: AsyncClient,
        sample_product_id: str
    ):
        """Test creating a variant with duplicate SKU fails"""
        sku = f"VAR-DUP-{uuid4().hex[:8].upper()}"
        variant_data = {
            "product_id": sample_product_id,
            "sku": sku,
            "size": "S",
            "retail_price": 20.0
        }
        
        # Create first variant
        response1 = await client.post("/api/v1/inventory/variants/", json=variant_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        variant_data["size"] = "M"
        response2 = await client.post("/api/v1/inventory/variants/", json=variant_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_list_variants(self, client: AsyncClient, sample_product_id: str):
        """Test listing variants"""
        # Create variants
        sizes = ["S", "M", "L"]
        for size in sizes:
            await client.post("/api/v1/inventory/variants/", json={
                "product_id": sample_product_id,
                "sku": f"VAR-{size}-{uuid4().hex[:6].upper()}",
                "size": size,
                "retail_price": 25.0
            })
        
        # List variants
        response = await client.get("/api/v1/inventory/variants/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 3
    
    async def test_get_variant_by_id(self, client: AsyncClient, sample_product_id: str):
        """Test getting a variant by ID"""
        # Create variant
        create_response = await client.post("/api/v1/inventory/variants/", json={
            "product_id": sample_product_id,
            "sku": f"VAR-GET-{uuid4().hex[:8].upper()}",
            "size": "L",
            "retail_price": 30.0
        })
        variant_id = create_response.json()["id"]
        
        # Get variant
        response = await client.get(f"/api/v1/inventory/variants/{variant_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == variant_id
        assert data["size"] == "L"
    
    async def test_get_variant_by_barcode(
        self,
        client: AsyncClient,
        sample_product_id: str
    ):
        """Test getting a variant by barcode"""
        barcode = f"123{uuid4().hex[:10]}"
        
        # Create variant with barcode
        await client.post("/api/v1/inventory/variants/", json={
            "product_id": sample_product_id,
            "sku": f"VAR-{uuid4().hex[:8].upper()}",
            "barcode": barcode,
            "size": "XL",
            "retail_price": 35.0
        })
        
        # Get by barcode
        response = await client.get(f"/api/v1/inventory/variants/barcode/{barcode}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["barcode"] == barcode
        assert data["size"] == "XL"
    
    async def test_update_variant(self, client: AsyncClient, sample_product_id: str):
        """Test updating a variant"""
        # Create variant
        create_response = await client.post("/api/v1/inventory/variants/", json={
            "product_id": sample_product_id,
            "sku": f"VAR-UPD-{uuid4().hex[:8].upper()}",
            "size": "M",
            "retail_price": 25.0
        })
        variant_id = create_response.json()["id"]
        
        # Update variant
        update_data = {
            "size": "L",
            "retail_price": 30.0
        }
        response = await client.put(
            f"/api/v1/inventory/variants/{variant_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["size"] == "L"
        assert data["retail_price"] == 30.0
    
    async def test_delete_variant(self, client: AsyncClient, sample_product_id: str):
        """Test deleting a variant"""
        # Create variant
        create_response = await client.post("/api/v1/inventory/variants/", json={
            "product_id": sample_product_id,
            "sku": f"VAR-DEL-{uuid4().hex[:8].upper()}",
            "size": "S",
            "retail_price": 20.0
        })
        variant_id = create_response.json()["id"]
        
        # Delete variant
        response = await client.delete(f"/api/v1/inventory/variants/{variant_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        get_response = await client.get(f"/api/v1/inventory/variants/{variant_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Fixtures
# ============================================================================




@pytest.fixture
async def sample_product_id(client: AsyncClient) -> str:
    """Create a sample product and return its ID"""
    response = await client.post("/api/v1/inventory/products/", json={
        "sku": f"SAMPLE-{uuid4().hex[:8].upper()}",
        "name": "Sample Product for Variants",
        "slug": f"sample-product-{uuid4().hex[:8]}",
        "description": "A sample product",
        "base_retail_price": 20.0,
        "is_active": True
    })
    return response.json()["id"]
