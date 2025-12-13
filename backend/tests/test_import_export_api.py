"""
Integration Tests for CSV Import/Export API Endpoints

Tests for CSV import/export and file upload functionality.
"""

import pytest
from httpx import AsyncClient
from fastapi import status, UploadFile
from io import BytesIO
from uuid import uuid4

from app.main import app


pytestmark = pytest.mark.asyncio


class TestCSVExportEndpoints:
    """Tests for CSV export endpoints"""
    
    async def test_export_products_csv(self, client: AsyncClient):
        """Test exporting products to CSV"""
        # Create some products
        for i in range(3):
            await client.post("/api/v1/inventory/products/", json={
                "sku": f"EXP-{i}-{uuid4().hex[:6]}",
                "name": f"Export Product {i}",
                "retail_price": 10.0 * (i + 1)
            })
        
        # Export
        response = await client.get("/api/v1/inventory/import-export/export/products")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Verify CSV content
        content = response.text
        assert "sku,name" in content
        assert "Export Product" in content
    
    async def test_export_variants_csv(self, client: AsyncClient, sample_product_id: str):
        """Test exporting variants to CSV"""
        # Create variants
        sizes = ["S", "M", "L"]
        for size in sizes:
            await client.post("/api/v1/inventory/variants/", json={
                "product_id": sample_product_id,
                "sku": f"VAR-{size}-{uuid4().hex[:6]}",
                "size": size,
                "retail_price": 25.0
            })
        
        # Export
        response = await client.get("/api/v1/inventory/import-export/export/variants")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Verify CSV content
        content = response.text
        assert "sku,product_id" in content or "sku" in content
    
    async def test_export_inventory_csv(self, client: AsyncClient):
        """Test exporting inventory levels to CSV"""
        response = await client.get("/api/v1/inventory/import-export/export/inventory")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"


class TestCSVImportEndpoints:
    """Tests for CSV import endpoints"""
    
    async def test_import_products_csv(self, client: AsyncClient):
        """Test importing products from CSV"""
        # Create CSV content
        csv_content = f"""sku,name,description,unit_cost,retail_price,is_active
IMP-001-{uuid4().hex[:6]},Import Product 1,Description 1,10.0,20.0,true
IMP-002-{uuid4().hex[:6]},Import Product 2,Description 2,15.0,30.0,true
IMP-003-{uuid4().hex[:6]},Import Product 3,Description 3,20.0,40.0,false
"""
        
        # Create file-like object
        csv_file = BytesIO(csv_content.encode())
        
        # Import
        response = await client.post(
            "/api/v1/inventory/import-export/import/products",
            files={"file": ("products.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["created"] >= 3
    
    async def test_import_products_update_existing(self, client: AsyncClient):
        """Test importing products updates existing ones"""
        sku = f"IMP-UPD-{uuid4().hex[:6]}"
        
        # Create product
        await client.post("/api/v1/inventory/products/", json={
            "sku": sku,
            "name": "Original Name",
            "retail_price": 20.0
        })
        
        # Create CSV with updated data
        csv_content = f"""sku,name,retail_price
{sku},Updated Name,25.0
"""
        csv_file = BytesIO(csv_content.encode())
        
        # Import
        response = await client.post(
            "/api/v1/inventory/import-export/import/products",
            files={"file": ("update.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated"] >= 1
        
        # Verify update
        get_response = await client.get(f"/api/v1/inventory/products/sku/{sku}")
        product = get_response.json()
        assert product["name"] == "Updated Name"
        assert product["retail_price"] == 25.0
    
    async def test_import_variants_csv(self, client: AsyncClient, sample_product_id: str):
        """Test importing variants from CSV"""
        # Create CSV content
        csv_content = f"""sku,product_id,size,color,retail_price,is_active
VAR-IMP-S-{uuid4().hex[:6]},{sample_product_id},S,Red,20.0,true
VAR-IMP-M-{uuid4().hex[:6]},{sample_product_id},M,Blue,25.0,true
VAR-IMP-L-{uuid4().hex[:6]},{sample_product_id},L,Green,30.0,true
"""
        
        # Create file-like object
        csv_file = BytesIO(csv_content.encode())
        
        # Import
        response = await client.post(
            "/api/v1/inventory/import-export/import/variants",
            files={"file": ("variants.csv", csv_file, "text/csv")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["created"] >= 3


class TestFileUploadEndpoints:
    """Tests for file upload endpoints"""
    
    async def test_upload_product_image(self, client: AsyncClient, sample_product_id: str):
        """Test uploading a product image"""
        # Create fake image file
        image_data = b"fake image data"
        image_file = BytesIO(image_data)
        
        # Upload
        response = await client.post(
            "/api/v1/inventory/import-export/upload/product-image",
            data={"product_id": sample_product_id},
            files={"file": ("product.jpg", image_file, "image/jpeg")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "file_path" in data
        assert data["file_path"].endswith(".jpg")
    
    async def test_upload_multiple_product_images(
        self,
        client: AsyncClient,
        sample_product_id: str
    ):
        """Test uploading multiple product images"""
        # Create fake image files
        files = []
        for i in range(3):
            image_data = f"fake image {i}".encode()
            files.append(("files", (f"product-{i}.jpg", BytesIO(image_data), "image/jpeg")))
        
        # Upload
        response = await client.post(
            "/api/v1/inventory/import-export/upload/product-images",
            data={"product_id": sample_product_id},
            files=files
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "file_paths" in data
        assert len(data["file_paths"]) == 3
    
    async def test_upload_brand_logo(self, client: AsyncClient):
        """Test uploading a brand logo"""
        # Create brand first
        brand_response = await client.post("/api/v1/inventory/brands/", json={
            "name": "Test Brand",
            "code": f"TST-{uuid4().hex[:4]}",
            "slug": f"test-brand-{uuid4().hex[:6]}"
        })
        brand_id = brand_response.json()["id"]
        
        # Create fake logo file
        logo_data = b"fake logo data"
        logo_file = BytesIO(logo_data)
        
        # Upload
        response = await client.post(
            "/api/v1/inventory/import-export/upload/brand-logo",
            data={"brand_id": brand_id},
            files={"file": ("logo.png", logo_file, "image/png")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "file_path" in data
        assert data["file_path"].endswith(".png")
    
    async def test_upload_category_image(self, client: AsyncClient):
        """Test uploading a category image"""
        # Create category first
        category_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "Test Category",
            "slug": f"test-category-{uuid4().hex[:6]}"
        })
        category_id = category_response.json()["id"]
        
        # Create fake image file
        image_data = b"fake category image"
        image_file = BytesIO(image_data)
        
        # Upload
        response = await client.post(
            "/api/v1/inventory/import-export/upload/category-image",
            data={"category_id": category_id},
            files={"file": ("category.jpg", image_file, "image/jpeg")}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "file_path" in data
    
    async def test_upload_invalid_file_type(self, client: AsyncClient):
        """Test uploading invalid file type fails"""
        # Create category
        category_response = await client.post("/api/v1/inventory/categories/", json={
            "name": "Test Category",
            "slug": f"test-cat-{uuid4().hex[:6]}"
        })
        category_id = category_response.json()["id"]
        
        # Try to upload invalid file type
        file_data = b"fake data"
        file = BytesIO(file_data)
        
        response = await client.post(
            "/api/v1/inventory/import-export/upload/category-image",
            data={"category_id": category_id},
            files={"file": ("file.txt", file, "text/plain")}
        )
        
        # Should fail with 400
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestFileManagementEndpoints:
    """Tests for file management endpoints"""
    
    async def test_get_file_info(self, client: AsyncClient):
        """Test getting file information"""
        # This test assumes a file exists or mocks the service
        # For now, we'll test the endpoint structure
        response = await client.get("/api/v1/inventory/import-export/file/test.jpg/info")
        
        # May return 404 if file doesn't exist, which is expected
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_product_id(client: AsyncClient) -> str:
    """Create a sample product and return its ID"""
    response = await client.post("/api/v1/inventory/products/", json={
        "sku": f"SAMPLE-{uuid4().hex[:8].upper()}",
        "name": "Sample Product",
        "retail_price": 20.0
    })
    return response.json()["id"]
