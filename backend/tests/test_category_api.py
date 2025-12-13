"""
Integration Tests for Category, Brand, and Supplier API Endpoints

Tests for hierarchical categories, brands, and supplier management via API.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4

from app.main import app


pytestmark = pytest.mark.asyncio


class TestCategoryEndpoints:
    """Tests for Category API endpoints"""
    
    async def test_create_category(self, client: AsyncClient):
        """Test creating a category"""
        category_data = {
            "name": "Electronics",
            "slug": f"electronics-{uuid4().hex[:6]}",
            "description": "Electronic products"
        }
        
        response = await client.post("/api/v1/inventory/categories/", json=category_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Electronics"
        assert data["slug"] == category_data["slug"]
    
    async def test_create_child_category(self, client: AsyncClient):
        """Test creating a child category"""
        # Create parent
        parent_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "Parent",
            "slug": f"parent-{uuid4().hex[:6]}"
        })
        parent_id = parent_response.json()["id"]
        
        # Create child
        child_data = {
            "name": "Child",
            "slug": f"child-{uuid4().hex[:6]}",
            "parent_id": parent_id
        }
        response = await client.post("/api/v1/inventory/categories/", json=child_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["parent_id"] == parent_id
    
    async def test_get_category_tree(self, client: AsyncClient):
        """Test getting full category tree"""
        # Create parent
        parent_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "Electronics",
            "slug": f"elec-{uuid4().hex[:6]}"
        })
        parent_id = parent_response.json()["id"]
        
        # Create children
        await client.post("/api/v1/inventory/categories/", json={
            "name": "Computers",
            "slug": f"comp-{uuid4().hex[:6]}",
            "parent_id": parent_id
        })
        await client.post("/api/v1/inventory/categories/", json={
            "name": "Phones",
            "slug": f"phone-{uuid4().hex[:6]}",
            "parent_id": parent_id
        })
        
        # Get tree for parent
        response = await client.get(f"/api/v1/inventory/categories/{parent_id}/tree")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Electronics"
        assert len(data["children"]) >= 2
    
    async def test_get_root_categories(self, client: AsyncClient):
        """Test getting root categories"""
        # Create root categories
        for i in range(3):
            await client.post("/api/v1/inventory/categories/", json={
                "name": f"Root {i}",
                "slug": f"root-{i}-{uuid4().hex[:6]}"
            })
        
        # Get roots
        response = await client.get("/api/v1/inventory/categories/tree")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
    
    async def test_get_category_children(self, client: AsyncClient):
        """Test getting child categories"""
        # Create parent
        parent_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "Parent Category",
            "slug": f"parent-cat-{uuid4().hex[:6]}"
        })
        parent_id = parent_response.json()["id"]
        
        # Create children
        for i in range(3):
            await client.post("/api/v1/inventory/categories/", json={
                "name": f"Child {i}",
                "slug": f"child-{i}-{uuid4().hex[:6]}",
                "parent_id": parent_id
            })
        
        # Get children
        response = await client.get(f"/api/v1/inventory/categories/{parent_id}/children")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
    
    async def test_update_category(self, client: AsyncClient):
        """Test updating a category"""
        # Create category
        create_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "Original",
            "slug": f"original-{uuid4().hex[:6]}"
        })
        category_id = create_response.json()["id"]
        
        # Update
        update_data = {
            "name": "Updated Name",
            "description": "Updated description"
        }
        response = await client.put(
            f"/api/v1/inventory/categories/{category_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
    
    async def test_delete_category(self, client: AsyncClient):
        """Test deleting a category"""
        # Create category
        create_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "To Delete",
            "slug": f"delete-{uuid4().hex[:6]}"
        })
        category_id = create_response.json()["id"]
        
        # Delete
        response = await client.delete(f"/api/v1/inventory/categories/{category_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestBrandEndpoints:
    """Tests for Brand API endpoints"""
    
    async def test_create_brand(self, client: AsyncClient):
        """Test creating a brand"""
        brand_data = {
            "name": "Nike",
            "code": f"NIKE-{uuid4().hex[:4]}",
            "slug": f"nike-{uuid4().hex[:6]}",
            "description": "Athletic wear"
        }
        
        response = await client.post("/api/v1/inventory/brands/", json=brand_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Nike"
        assert data["code"] == brand_data["code"]
    
    async def test_list_brands(self, client: AsyncClient):
        """Test listing brands"""
        # Create brands
        for i in range(3):
            await client.post("/api/v1/inventory/brands/", json={
                "name": f"Brand {i}",
                "code": f"BR{i}-{uuid4().hex[:4]}",
                "slug": f"brand-{i}-{uuid4().hex[:6]}"
            })
        
        # List
        response = await client.get("/api/v1/inventory/brands/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 3
    
    async def test_get_brand_by_slug(self, client: AsyncClient):
        """Test getting brand by slug"""
        slug = f"adidas-{uuid4().hex[:6]}"
        
        # Create brand
        await client.post("/api/v1/inventory/brands/", json={
            "name": "Adidas",
            "code": f"ADI-{uuid4().hex[:4]}",
            "slug": slug
        })
        
        # Get by slug
        response = await client.get(f"/api/v1/inventory/brands/slug/{slug}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == slug
    
    async def test_update_brand(self, client: AsyncClient):
        """Test updating a brand"""
        # Create brand
        create_response = await client.post("/api/v1/inventory/brands/", json={
            "name": "Original Brand",
            "code": f"ORIG-{uuid4().hex[:4]}",
            "slug": f"original-{uuid4().hex[:6]}"
        })
        brand_id = create_response.json()["id"]
        
        # Update
        update_data = {
            "name": "Updated Brand",
            "description": "Updated description"
        }
        response = await client.put(
            f"/api/v1/inventory/brands/{brand_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Brand"
    
    async def test_delete_brand(self, client: AsyncClient):
        """Test deleting a brand"""
        # Create brand
        create_response = await client.post("/api/v1/inventory/brands/", json={
            "name": "To Delete",
            "code": f"DEL-{uuid4().hex[:4]}",
            "slug": f"delete-{uuid4().hex[:6]}"
        })
        brand_id = create_response.json()["id"]
        
        # Delete
        response = await client.delete(f"/api/v1/inventory/brands/{brand_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestSupplierEndpoints:
    """Tests for Supplier API endpoints"""
    
    async def test_create_supplier(self, client: AsyncClient):
        """Test creating a supplier"""
        supplier_data = {
            "name": "ABC Supplies",
            "code": f"ABC-{uuid4().hex[:4]}",
            "email": f"abc-{uuid4().hex[:6]}@test.com",
            "phone": "123-456-7890",
            "is_active": True
        }
        
        response = await client.post("/api/v1/inventory/suppliers/", json=supplier_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "ABC Supplies"
        assert data["code"] == supplier_data["code"]
    
    async def test_list_suppliers(self, client: AsyncClient):
        """Test listing suppliers"""
        # Create suppliers
        for i in range(3):
            await client.post("/api/v1/inventory/suppliers/", json={
                "name": f"Supplier {i}",
                "code": f"SUP{i}-{uuid4().hex[:4]}",
                "email": f"sup{i}-{uuid4().hex[:6]}@test.com"
            })
        
        # List
        response = await client.get("/api/v1/inventory/suppliers/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 3
    
    async def test_get_supplier_by_code(self, client: AsyncClient):
        """Test getting supplier by code"""
        code = f"XYZ-{uuid4().hex[:4]}"
        
        # Create supplier
        await client.post("/api/v1/inventory/suppliers/", json={
            "name": "XYZ Corp",
            "code": code,
            "email": f"xyz-{uuid4().hex[:6]}@test.com"
        })
        
        # Get by code
        response = await client.get(f"/api/v1/inventory/suppliers/code/{code}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == code
    
    async def test_get_active_suppliers(self, client: AsyncClient):
        """Test getting only active suppliers"""
        # Create active suppliers
        for i in range(2):
            await client.post("/api/v1/inventory/suppliers/", json={
                "name": f"Active {i}",
                "code": f"ACT{i}-{uuid4().hex[:4]}",
                "email": f"act{i}-{uuid4().hex[:6]}@test.com",
                "is_active": True
            })
        
        # Create inactive supplier
        await client.post("/api/v1/inventory/suppliers/", json={
            "name": "Inactive",
            "code": f"INACT-{uuid4().hex[:4]}",
            "email": f"inact-{uuid4().hex[:6]}@test.com",
            "is_active": False
        })
        
        # Get active
        response = await client.get("/api/v1/inventory/suppliers/active")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert all(s["is_active"] for s in data)
    
    async def test_update_supplier(self, client: AsyncClient):
        """Test updating a supplier"""
        # Create supplier
        create_response = await client.post("/api/v1/inventory/suppliers/", json={
            "name": "Original Supplier",
            "code": f"ORIG-{uuid4().hex[:4]}",
            "email": f"original-{uuid4().hex[:6]}@test.com"
        })
        supplier_id = create_response.json()["id"]
        
        # Update
        update_data = {
            "name": "Updated Supplier",
            "phone": "999-888-7777"
        }
        response = await client.put(
            f"/api/v1/inventory/suppliers/{supplier_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Supplier"
        assert data["phone"] == "999-888-7777"
    
    async def test_delete_supplier(self, client: AsyncClient):
        """Test deleting a supplier"""
        # Create supplier
        create_response = await client.post("/api/v1/inventory/suppliers/", json={
            "name": "To Delete",
            "code": f"DEL-{uuid4().hex[:4]}",
            "email": f"delete-{uuid4().hex[:6]}@test.com"
        })
        supplier_id = create_response.json()["id"]
        
        # Delete
        response = await client.delete(f"/api/v1/inventory/suppliers/{supplier_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
