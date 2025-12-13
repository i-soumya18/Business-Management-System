"""
Tests for garment-specific repositories
"""
import pytest
from datetime import datetime
from app.repositories.garment import (
    SizeChartRepository,
    ColorRepository,
    FabricRepository,
    StyleRepository,
    CollectionRepository,
    MeasurementSpecRepository,
    GarmentImageRepository,
    ProductFabricRepository
)
from app.models.garment import (
    SizeChart, Color, Fabric, Style, Collection,
    MeasurementSpec, GarmentImage, ProductFabric,
    SizeCategory, Region, Season
)
from app.models.inventory import Product, ProductCategory


@pytest.mark.asyncio
class TestSizeChartRepository:
    """Tests for SizeChartRepository"""
    
    async def test_create_size_chart(self, db_session):
        """Test creating a size chart"""
        repo = SizeChartRepository(db_session)
        size_data = {
            "name": "Men's Shirts",
            "category": SizeCategory.TOPS,
            "region": Region.US,
            "sizes": {
                "S": {"chest": 36, "waist": 32},
                "M": {"chest": 40, "waist": 34},
                "L": {"chest": 44, "waist": 36}
            }
        }
        
        size_chart = await repo.create(size_data)
        assert size_chart.id is not None
        assert size_chart.name == "Men's Shirts"
        assert size_chart.category == SizeCategory.TOPS
        assert size_chart.region == Region.US
        assert "S" in size_chart.sizes
    
    async def test_get_by_category(self, db_session):
        """Test getting size charts by category"""
        repo = SizeChartRepository(db_session)
        
        # Create size charts
        await repo.create({
            "name": "Men's Shirts",
            "category": SizeCategory.TOPS,
            "region": Region.US,
            "sizes": {"S": {}, "M": {}, "L": {}}
        })
        await repo.create({
            "name": "Men's Pants",
            "category": SizeCategory.BOTTOMS,
            "region": Region.US,
            "sizes": {"30": {}, "32": {}, "34": {}}
        })
        
        tops = await repo.get_by_category(SizeCategory.TOPS)
        assert len(tops) == 1
        assert tops[0].name == "Men's Shirts"
        
        bottoms = await repo.get_by_category(SizeCategory.BOTTOMS, Region.US)
        assert len(bottoms) == 1
        assert bottoms[0].name == "Men's Pants"
    
    async def test_search_size_charts(self, db_session):
        """Test searching size charts"""
        repo = SizeChartRepository(db_session)
        
        await repo.create({
            "name": "Men's Premium Shirts",
            "category": SizeCategory.TOPS,
            "region": Region.US,
            "sizes": {"S": {}, "M": {}}
        })
        
        results = await repo.search("Premium")
        assert len(results) == 1
        assert "Premium" in results[0].name


@pytest.mark.asyncio
class TestColorRepository:
    """Tests for ColorRepository"""
    
    async def test_create_color(self, db_session):
        """Test creating a color"""
        repo = ColorRepository(db_session)
        color_data = {
            "code": "BLK",
            "name": "Black",
            "hex_code": "#000000",
            "pantone_code": "19-0303 TCX",
            "is_active": True
        }
        
        color = await repo.create(color_data)
        assert color.id is not None
        assert color.code == "BLK"
        assert color.hex_code == "#000000"
    
    async def test_get_by_code(self, db_session):
        """Test getting color by code"""
        repo = ColorRepository(db_session)
        
        await repo.create({
            "code": "RED",
            "name": "Red",
            "hex_code": "#FF0000"
        })
        
        color = await repo.get_by_code("RED")
        assert color is not None
        assert color.name == "Red"
    
    async def test_get_by_hex(self, db_session):
        """Test getting color by hex code"""
        repo = ColorRepository(db_session)
        
        await repo.create({
            "code": "BLU",
            "name": "Blue",
            "hex_code": "#0000FF"
        })
        
        color = await repo.get_by_hex("#0000FF")
        assert color is not None
        assert color.name == "Blue"
    
    async def test_get_active_colors(self, db_session):
        """Test getting active colors"""
        repo = ColorRepository(db_session)
        
        await repo.create({
            "code": "ACT",
            "name": "Active",
            "hex_code": "#111111",
            "is_active": True
        })
        await repo.create({
            "code": "INA",
            "name": "Inactive",
            "hex_code": "#222222",
            "is_active": False
        })
        
        colors = await repo.get_active_colors()
        assert len(colors) == 1
        assert colors[0].name == "Active"
    
    async def test_search_colors(self, db_session):
        """Test searching colors"""
        repo = ColorRepository(db_session)
        
        await repo.create({
            "code": "NGT",
            "name": "Midnight Blue",
            "hex_code": "#191970"
        })
        
        results = await repo.search("Midnight")
        assert len(results) == 1
        assert results[0].code == "NGT"


@pytest.mark.asyncio
class TestFabricRepository:
    """Tests for FabricRepository"""
    
    async def test_create_fabric(self, db_session):
        """Test creating a fabric"""
        repo = FabricRepository(db_session)
        fabric_data = {
            "code": "COT100",
            "name": "100% Cotton",
            "composition": "100% Cotton",
            "weight_gsm": 180,
            "is_active": True
        }
        
        fabric = await repo.create(fabric_data)
        assert fabric.id is not None
        assert fabric.code == "COT100"
        assert fabric.weight_gsm == 180
    
    async def test_get_by_code(self, db_session):
        """Test getting fabric by code"""
        repo = FabricRepository(db_session)
        
        await repo.create({
            "code": "POLY",
            "name": "Polyester",
            "composition": "100% Polyester"
        })
        
        fabric = await repo.get_by_code("POLY")
        assert fabric is not None
        assert fabric.name == "Polyester"
    
    async def test_get_active_fabrics(self, db_session):
        """Test getting active fabrics"""
        repo = FabricRepository(db_session)
        
        await repo.create({
            "code": "ACT",
            "name": "Active Fabric",
            "composition": "Cotton",
            "is_active": True
        })
        await repo.create({
            "code": "INA",
            "name": "Inactive Fabric",
            "composition": "Polyester",
            "is_active": False
        })
        
        fabrics = await repo.get_active_fabrics()
        assert len(fabrics) == 1
        assert fabrics[0].name == "Active Fabric"
    
    async def test_search_fabrics(self, db_session):
        """Test searching fabrics"""
        repo = FabricRepository(db_session)
        
        await repo.create({
            "code": "DEN",
            "name": "Denim",
            "composition": "Cotton Denim"
        })
        
        results = await repo.search("Denim")
        assert len(results) == 1
        assert results[0].code == "DEN"


@pytest.mark.asyncio
class TestStyleRepository:
    """Tests for StyleRepository"""
    
    async def test_create_style(self, db_session):
        """Test creating a style"""
        repo = StyleRepository(db_session)
        style_data = {
            "code": "CAS",
            "name": "Casual",
            "description": "Casual wear",
            "is_active": True
        }
        
        style = await repo.create(style_data)
        assert style.id is not None
        assert style.code == "CAS"
    
    async def test_get_by_code(self, db_session):
        """Test getting style by code"""
        repo = StyleRepository(db_session)
        
        await repo.create({
            "code": "FOR",
            "name": "Formal",
            "description": "Formal wear"
        })
        
        style = await repo.get_by_code("FOR")
        assert style is not None
        assert style.name == "Formal"
    
    async def test_get_active_styles(self, db_session):
        """Test getting active styles"""
        repo = StyleRepository(db_session)
        
        await repo.create({
            "code": "ACT",
            "name": "Active Style",
            "is_active": True
        })
        await repo.create({
            "code": "INA",
            "name": "Inactive Style",
            "is_active": False
        })
        
        styles = await repo.get_active_styles()
        assert len(styles) == 1
        assert styles[0].name == "Active Style"


@pytest.mark.asyncio
class TestCollectionRepository:
    """Tests for CollectionRepository"""
    
    async def test_create_collection(self, db_session):
        """Test creating a collection"""
        repo = CollectionRepository(db_session)
        collection_data = {
            "code": "SS24",
            "name": "Spring Summer 2024",
            "season": Season.SPRING,
            "year": 2024,
            "is_active": True
        }
        
        collection = await repo.create(collection_data)
        assert collection.id is not None
        assert collection.code == "SS24"
        assert collection.season == Season.SPRING
    
    async def test_get_by_code(self, db_session):
        """Test getting collection by code"""
        repo = CollectionRepository(db_session)
        
        await repo.create({
            "code": "FW24",
            "name": "Fall Winter 2024",
            "season": Season.FALL,
            "year": 2024
        })
        
        collection = await repo.get_by_code("FW24")
        assert collection is not None
        assert collection.season == Season.FALL
    
    async def test_get_by_season(self, db_session):
        """Test getting collections by season"""
        repo = CollectionRepository(db_session)
        
        await repo.create({
            "code": "SS24",
            "name": "Spring 2024",
            "season": Season.SPRING,
            "year": 2024
        })
        await repo.create({
            "code": "SS25",
            "name": "Spring 2025",
            "season": Season.SPRING,
            "year": 2025
        })
        
        collections = await repo.get_by_season(Season.SPRING)
        assert len(collections) == 2
        
        collections_2024 = await repo.get_by_season(Season.SPRING, 2024)
        assert len(collections_2024) == 1
        assert collections_2024[0].year == 2024


@pytest.mark.asyncio
class TestMeasurementSpecRepository:
    """Tests for MeasurementSpecRepository"""
    
    async def test_create_measurement_spec(self, db_session, sample_product):
        """Test creating a measurement spec"""
        repo = MeasurementSpecRepository(db_session)
        spec_data = {
            "product_id": sample_product.id,
            "size": "M",
            "chest": 40.0,
            "waist": 34.0,
            "hips": 38.0,
            "length": 28.0
        }
        
        spec = await repo.create(spec_data)
        assert spec.id is not None
        assert spec.size == "M"
        assert spec.chest == 40.0
    
    async def test_get_by_product(self, db_session, sample_product):
        """Test getting measurements by product"""
        repo = MeasurementSpecRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "size": "S",
            "chest": 36.0
        })
        await repo.create({
            "product_id": sample_product.id,
            "size": "M",
            "chest": 40.0
        })
        
        specs = await repo.get_by_product(sample_product.id)
        assert len(specs) == 2
    
    async def test_get_by_product_and_size(self, db_session, sample_product):
        """Test getting measurement by product and size"""
        repo = MeasurementSpecRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "size": "L",
            "chest": 44.0
        })
        
        spec = await repo.get_by_product_and_size(sample_product.id, "L")
        assert spec is not None
        assert spec.chest == 44.0


@pytest.mark.asyncio
class TestGarmentImageRepository:
    """Tests for GarmentImageRepository"""
    
    async def test_create_garment_image(self, db_session, sample_product):
        """Test creating a garment image"""
        repo = GarmentImageRepository(db_session)
        image_data = {
            "product_id": sample_product.id,
            "image_url": "https://example.com/image1.jpg",
            "alt_text": "Front view",
            "is_primary": True,
            "display_order": 1
        }
        
        image = await repo.create(image_data)
        assert image.id is not None
        assert image.image_url == "https://example.com/image1.jpg"
        assert image.is_primary is True
    
    async def test_get_by_product(self, db_session, sample_product):
        """Test getting images by product"""
        repo = GarmentImageRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "image_url": "https://example.com/img1.jpg",
            "display_order": 1
        })
        await repo.create({
            "product_id": sample_product.id,
            "image_url": "https://example.com/img2.jpg",
            "display_order": 2
        })
        
        images = await repo.get_by_product(sample_product.id)
        assert len(images) == 2
    
    async def test_get_primary_image(self, db_session, sample_product):
        """Test getting primary image"""
        repo = GarmentImageRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "image_url": "https://example.com/primary.jpg",
            "is_primary": True,
            "display_order": 1
        })
        await repo.create({
            "product_id": sample_product.id,
            "image_url": "https://example.com/secondary.jpg",
            "is_primary": False,
            "display_order": 2
        })
        
        primary = await repo.get_primary_image(sample_product.id)
        assert primary is not None
        assert primary.is_primary is True
        assert "primary.jpg" in primary.image_url
    
    async def test_get_by_color(self, db_session, sample_product, sample_color):
        """Test getting images by color"""
        repo = GarmentImageRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "color_id": sample_color.id,
            "image_url": "https://example.com/black.jpg",
            "display_order": 1
        })
        
        images = await repo.get_by_color(sample_product.id, sample_color.id)
        assert len(images) == 1
        assert "black.jpg" in images[0].image_url


@pytest.mark.asyncio
class TestProductFabricRepository:
    """Tests for ProductFabricRepository"""
    
    async def test_create_product_fabric(self, db_session, sample_product, sample_fabric):
        """Test creating a product fabric association"""
        repo = ProductFabricRepository(db_session)
        pf_data = {
            "product_id": sample_product.id,
            "fabric_id": sample_fabric.id,
            "percentage": 60.0
        }
        
        pf = await repo.create(pf_data)
        assert pf.id is not None
        assert pf.percentage == 60.0
    
    async def test_get_by_product(self, db_session, sample_product, sample_fabric):
        """Test getting fabrics by product"""
        repo = ProductFabricRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "fabric_id": sample_fabric.id,
            "percentage": 100.0
        })
        
        fabrics = await repo.get_by_product(sample_product.id)
        assert len(fabrics) == 1
        assert fabrics[0].percentage == 100.0
    
    async def test_delete_by_product(self, db_session, sample_product, sample_fabric):
        """Test deleting product fabrics"""
        repo = ProductFabricRepository(db_session)
        
        await repo.create({
            "product_id": sample_product.id,
            "fabric_id": sample_fabric.id,
            "percentage": 100.0
        })
        
        count = await repo.delete_by_product(sample_product.id)
        assert count == 1
        
        fabrics = await repo.get_by_product(sample_product.id)
        assert len(fabrics) == 0


# Fixtures

@pytest.fixture
async def sample_product(db_session):
    """Create a sample product for testing"""
    from app.repositories.inventory import ProductRepository, ProductCategoryRepository
    
    cat_repo = ProductCategoryRepository(db_session)
    category = await cat_repo.create({
        "name": "Test Category",
        "code": "TEST"
    })
    
    prod_repo = ProductRepository(db_session)
    product = await prod_repo.create({
        "sku": "TEST-001",
        "name": "Test Product",
        "category_id": category.id,
        "cost_price": 10.0,
        "selling_price": 20.0
    })
    
    return product


@pytest.fixture
async def sample_color(db_session):
    """Create a sample color for testing"""
    repo = ColorRepository(db_session)
    color = await repo.create({
        "code": "BLK",
        "name": "Black",
        "hex_code": "#000000"
    })
    return color


@pytest.fixture
async def sample_fabric(db_session):
    """Create a sample fabric for testing"""
    repo = FabricRepository(db_session)
    fabric = await repo.create({
        "code": "COT",
        "name": "Cotton",
        "composition": "100% Cotton"
    })
    return fabric
