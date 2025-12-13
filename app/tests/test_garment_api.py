"""
Tests for garment-specific API endpoints
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
class TestSizeChartAPI:
    """Tests for size chart API endpoints"""
    
    async def test_create_size_chart(self, client: AsyncClient):
        """Test creating a size chart"""
        data = {
            "name": "Men's Shirts",
            "category": "tops",
            "region": "us",
            "sizes": {
                "S": {"chest": 36, "waist": 32},
                "M": {"chest": 40, "waist": 34}
            }
        }
        
        response = await client.post("/api/v1/garment/size-charts/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "Men's Shirts"
        assert result["category"] == "tops"
    
    async def test_list_size_charts(self, client: AsyncClient, sample_size_chart):
        """Test listing size charts"""
        response = await client.get("/api/v1/garment/size-charts/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_size_chart_by_id(self, client: AsyncClient, sample_size_chart):
        """Test getting a size chart by ID"""
        response = await client.get(f"/api/v1/garment/size-charts/{sample_size_chart.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_size_chart.id
    
    async def test_update_size_chart(self, client: AsyncClient, sample_size_chart):
        """Test updating a size chart"""
        data = {"name": "Updated Name"}
        response = await client.put(
            f"/api/v1/garment/size-charts/{sample_size_chart.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Name"
    
    async def test_delete_size_chart(self, client: AsyncClient, sample_size_chart):
        """Test deleting a size chart"""
        response = await client.delete(f"/api/v1/garment/size-charts/{sample_size_chart.id}")
        assert response.status_code == 204
    
    async def test_get_by_category(self, client: AsyncClient, sample_size_chart):
        """Test getting size charts by category"""
        response = await client.get(
            "/api/v1/garment/size-charts/by-category/tops"
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
    
    async def test_search_size_charts(self, client: AsyncClient, sample_size_chart):
        """Test searching size charts"""
        response = await client.get(
            "/api/v1/garment/size-charts/search",
            params={"q": sample_size_chart.name}
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestColorAPI:
    """Tests for color API endpoints"""
    
    async def test_create_color(self, client: AsyncClient):
        """Test creating a color"""
        data = {
            "code": "RED",
            "name": "Red",
            "hex_code": "#FF0000",
            "is_active": True
        }
        
        response = await client.post("/api/v1/garment/colors/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["code"] == "RED"
        assert result["hex_code"] == "#FF0000"
    
    async def test_list_colors(self, client: AsyncClient, sample_color):
        """Test listing colors"""
        response = await client.get("/api/v1/garment/colors/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_color_by_id(self, client: AsyncClient, sample_color):
        """Test getting a color by ID"""
        response = await client.get(f"/api/v1/garment/colors/{sample_color.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_color.id
    
    async def test_get_color_by_code(self, client: AsyncClient, sample_color):
        """Test getting a color by code"""
        response = await client.get(f"/api/v1/garment/colors/by-code/{sample_color.code}")
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == sample_color.code
    
    async def test_update_color(self, client: AsyncClient, sample_color):
        """Test updating a color"""
        data = {"name": "Updated Color"}
        response = await client.put(
            f"/api/v1/garment/colors/{sample_color.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Color"
    
    async def test_delete_color(self, client: AsyncClient, sample_color):
        """Test deleting a color"""
        response = await client.delete(f"/api/v1/garment/colors/{sample_color.id}")
        assert response.status_code == 204
    
    async def test_search_colors(self, client: AsyncClient, sample_color):
        """Test searching colors"""
        response = await client.get(
            "/api/v1/garment/colors/search",
            params={"q": sample_color.name}
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestFabricAPI:
    """Tests for fabric API endpoints"""
    
    async def test_create_fabric(self, client: AsyncClient):
        """Test creating a fabric"""
        data = {
            "code": "COT100",
            "name": "100% Cotton",
            "composition": "100% Cotton",
            "weight_gsm": 180,
            "is_active": True
        }
        
        response = await client.post("/api/v1/garment/fabrics/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["code"] == "COT100"
        assert result["weight_gsm"] == 180
    
    async def test_list_fabrics(self, client: AsyncClient, sample_fabric):
        """Test listing fabrics"""
        response = await client.get("/api/v1/garment/fabrics/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_fabric_by_id(self, client: AsyncClient, sample_fabric):
        """Test getting a fabric by ID"""
        response = await client.get(f"/api/v1/garment/fabrics/{sample_fabric.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_fabric.id
    
    async def test_update_fabric(self, client: AsyncClient, sample_fabric):
        """Test updating a fabric"""
        data = {"name": "Updated Fabric"}
        response = await client.put(
            f"/api/v1/garment/fabrics/{sample_fabric.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Fabric"
    
    async def test_delete_fabric(self, client: AsyncClient, sample_fabric):
        """Test deleting a fabric"""
        response = await client.delete(f"/api/v1/garment/fabrics/{sample_fabric.id}")
        assert response.status_code == 204
    
    async def test_search_fabrics(self, client: AsyncClient, sample_fabric):
        """Test searching fabrics"""
        response = await client.get(
            "/api/v1/garment/fabrics/search",
            params={"q": sample_fabric.name}
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestStyleAPI:
    """Tests for style API endpoints"""
    
    async def test_create_style(self, client: AsyncClient):
        """Test creating a style"""
        data = {
            "code": "CAS",
            "name": "Casual",
            "description": "Casual wear",
            "is_active": True
        }
        
        response = await client.post("/api/v1/garment/styles/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["code"] == "CAS"
    
    async def test_list_styles(self, client: AsyncClient, sample_style):
        """Test listing styles"""
        response = await client.get("/api/v1/garment/styles/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_style_by_id(self, client: AsyncClient, sample_style):
        """Test getting a style by ID"""
        response = await client.get(f"/api/v1/garment/styles/{sample_style.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_style.id
    
    async def test_update_style(self, client: AsyncClient, sample_style):
        """Test updating a style"""
        data = {"name": "Updated Style"}
        response = await client.put(
            f"/api/v1/garment/styles/{sample_style.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Style"
    
    async def test_delete_style(self, client: AsyncClient, sample_style):
        """Test deleting a style"""
        response = await client.delete(f"/api/v1/garment/styles/{sample_style.id}")
        assert response.status_code == 204


@pytest.mark.asyncio
class TestCollectionAPI:
    """Tests for collection API endpoints"""
    
    async def test_create_collection(self, client: AsyncClient):
        """Test creating a collection"""
        data = {
            "code": "SS24",
            "name": "Spring Summer 2024",
            "season": "spring",
            "year": 2024,
            "is_active": True
        }
        
        response = await client.post("/api/v1/garment/collections/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["code"] == "SS24"
        assert result["season"] == "spring"
    
    async def test_list_collections(self, client: AsyncClient, sample_collection):
        """Test listing collections"""
        response = await client.get("/api/v1/garment/collections/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_collection_by_id(self, client: AsyncClient, sample_collection):
        """Test getting a collection by ID"""
        response = await client.get(f"/api/v1/garment/collections/{sample_collection.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_collection.id
    
    async def test_update_collection(self, client: AsyncClient, sample_collection):
        """Test updating a collection"""
        data = {"name": "Updated Collection"}
        response = await client.put(
            f"/api/v1/garment/collections/{sample_collection.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated Collection"
    
    async def test_delete_collection(self, client: AsyncClient, sample_collection):
        """Test deleting a collection"""
        response = await client.delete(f"/api/v1/garment/collections/{sample_collection.id}")
        assert response.status_code == 204
    
    async def test_get_by_season(self, client: AsyncClient, sample_collection):
        """Test getting collections by season"""
        response = await client.get(
            "/api/v1/garment/collections/by-season",
            params={"season": sample_collection.season.value}
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestMeasurementAPI:
    """Tests for measurement API endpoints"""
    
    async def test_create_measurement(self, client: AsyncClient, sample_product):
        """Test creating a measurement specification"""
        data = {
            "product_id": sample_product.id,
            "size": "M",
            "chest": 40.0,
            "waist": 34.0,
            "hips": 38.0,
            "length": 28.0
        }
        
        response = await client.post("/api/v1/garment/measurements/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["size"] == "M"
        assert result["chest"] == 40.0
    
    async def test_list_measurements(self, client: AsyncClient, sample_measurement):
        """Test listing measurements"""
        response = await client.get("/api/v1/garment/measurements/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_measurement_by_id(self, client: AsyncClient, sample_measurement):
        """Test getting a measurement by ID"""
        response = await client.get(f"/api/v1/garment/measurements/{sample_measurement.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_measurement.id
    
    async def test_update_measurement(self, client: AsyncClient, sample_measurement):
        """Test updating a measurement"""
        data = {"chest": 42.0}
        response = await client.put(
            f"/api/v1/garment/measurements/{sample_measurement.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["chest"] == 42.0
    
    async def test_delete_measurement(self, client: AsyncClient, sample_measurement):
        """Test deleting a measurement"""
        response = await client.delete(f"/api/v1/garment/measurements/{sample_measurement.id}")
        assert response.status_code == 204
    
    async def test_get_by_product(self, client: AsyncClient, sample_product, sample_measurement):
        """Test getting measurements by product"""
        response = await client.get(
            f"/api/v1/garment/measurements/by-product/{sample_product.id}"
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestGarmentImageAPI:
    """Tests for garment image API endpoints"""
    
    async def test_create_image(self, client: AsyncClient, sample_product):
        """Test creating a garment image"""
        data = {
            "product_id": sample_product.id,
            "image_url": "https://example.com/image.jpg",
            "alt_text": "Front view",
            "is_primary": True,
            "display_order": 1
        }
        
        response = await client.post("/api/v1/garment/images/", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["image_url"] == "https://example.com/image.jpg"
        assert result["is_primary"] is True
    
    async def test_list_images(self, client: AsyncClient, sample_image):
        """Test listing images"""
        response = await client.get("/api/v1/garment/images/")
        assert response.status_code == 200
        result = response.json()
        assert "items" in result
        assert len(result["items"]) > 0
    
    async def test_get_image_by_id(self, client: AsyncClient, sample_image):
        """Test getting an image by ID"""
        response = await client.get(f"/api/v1/garment/images/{sample_image.id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == sample_image.id
    
    async def test_update_image(self, client: AsyncClient, sample_image):
        """Test updating an image"""
        data = {"alt_text": "Updated alt text"}
        response = await client.put(
            f"/api/v1/garment/images/{sample_image.id}",
            json=data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["alt_text"] == "Updated alt text"
    
    async def test_delete_image(self, client: AsyncClient, sample_image):
        """Test deleting an image"""
        response = await client.delete(f"/api/v1/garment/images/{sample_image.id}")
        assert response.status_code == 204
    
    async def test_get_by_product(self, client: AsyncClient, sample_product, sample_image):
        """Test getting images by product"""
        response = await client.get(
            f"/api/v1/garment/images/by-product/{sample_product.id}"
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
    
    async def test_get_primary_image(self, client: AsyncClient, sample_product, sample_image):
        """Test getting primary image"""
        response = await client.get(
            f"/api/v1/garment/images/primary/{sample_product.id}"
        )
        assert response.status_code == 200
        result = response.json()
        assert result["is_primary"] is True
    
    async def test_set_primary_image(self, client: AsyncClient, sample_image):
        """Test setting primary image"""
        response = await client.patch(
            f"/api/v1/garment/images/{sample_image.id}/set-primary"
        )
        assert response.status_code == 200
        result = response.json()
        assert result["is_primary"] is True
    
    async def test_bulk_create_images(self, client: AsyncClient, sample_product):
        """Test bulk creating images"""
        data = {
            "product_id": sample_product.id,
            "images": [
                {
                    "image_url": "https://example.com/img1.jpg",
                    "alt_text": "Front",
                    "display_order": 1
                },
                {
                    "image_url": "https://example.com/img2.jpg",
                    "alt_text": "Back",
                    "display_order": 2
                }
            ]
        }
        
        response = await client.post("/api/v1/garment/images/bulk", json=data)
        assert response.status_code == 201
        result = response.json()
        assert len(result) == 2


# Fixtures

@pytest.fixture
async def sample_size_chart(db_session):
    """Create a sample size chart"""
    from app.repositories.garment import SizeChartRepository
    from app.models.garment import SizeCategory, Region
    
    repo = SizeChartRepository(db_session)
    return await repo.create({
        "name": "Test Size Chart",
        "category": SizeCategory.TOPS,
        "region": Region.US,
        "sizes": {"S": {}, "M": {}, "L": {}}
    })


@pytest.fixture
async def sample_color(db_session):
    """Create a sample color"""
    from app.repositories.garment import ColorRepository
    
    repo = ColorRepository(db_session)
    return await repo.create({
        "code": "TST",
        "name": "Test Color",
        "hex_code": "#123456"
    })


@pytest.fixture
async def sample_fabric(db_session):
    """Create a sample fabric"""
    from app.repositories.garment import FabricRepository
    
    repo = FabricRepository(db_session)
    return await repo.create({
        "code": "TST",
        "name": "Test Fabric",
        "composition": "Test"
    })


@pytest.fixture
async def sample_style(db_session):
    """Create a sample style"""
    from app.repositories.garment import StyleRepository
    
    repo = StyleRepository(db_session)
    return await repo.create({
        "code": "TST",
        "name": "Test Style"
    })


@pytest.fixture
async def sample_collection(db_session):
    """Create a sample collection"""
    from app.repositories.garment import CollectionRepository
    from app.models.garment import Season
    
    repo = CollectionRepository(db_session)
    return await repo.create({
        "code": "TST24",
        "name": "Test Collection",
        "season": Season.SPRING,
        "year": 2024
    })


@pytest.fixture
async def sample_product(db_session):
    """Create a sample product"""
    from app.repositories.inventory import ProductRepository, ProductCategoryRepository
    
    cat_repo = ProductCategoryRepository(db_session)
    category = await cat_repo.create({
        "name": "Test Category",
        "code": "TEST"
    })
    
    prod_repo = ProductRepository(db_session)
    return await prod_repo.create({
        "sku": "TEST-001",
        "name": "Test Product",
        "category_id": category.id,
        "cost_price": 10.0,
        "selling_price": 20.0
    })


@pytest.fixture
async def sample_measurement(db_session, sample_product):
    """Create a sample measurement"""
    from app.repositories.garment import MeasurementSpecRepository
    
    repo = MeasurementSpecRepository(db_session)
    return await repo.create({
        "product_id": sample_product.id,
        "size": "M",
        "chest": 40.0
    })


@pytest.fixture
async def sample_image(db_session, sample_product):
    """Create a sample image"""
    from app.repositories.garment import GarmentImageRepository
    
    repo = GarmentImageRepository(db_session)
    return await repo.create({
        "product_id": sample_product.id,
        "image_url": "https://example.com/test.jpg",
        "is_primary": True,
        "display_order": 1
    })
