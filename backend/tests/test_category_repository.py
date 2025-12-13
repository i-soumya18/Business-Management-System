"""
Unit Tests for Category, Brand, and Supplier Repositories

Tests for CategoryRepository, BrandRepository, and SupplierRepository operations.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.brand import Brand
from app.models.supplier import Supplier
from app.repositories.category_brand_supplier import (
    CategoryRepository,
    BrandRepository,
    SupplierRepository
)


pytestmark = pytest.mark.asyncio


class TestCategoryRepository:
    """Tests for CategoryRepository"""
    
    async def test_create_category(self, db_session: AsyncSession):
        """Test creating a category"""
        repo = CategoryRepository(db_session)
        
        category_data = {
            "name": "Electronics",
            "slug": "electronics",
            "description": "Electronic products"
        }
        
        category = await repo.create(category_data)
        
        assert category.id is not None
        assert category.name == "Electronics"
        assert category.slug == "electronics"
    
    async def test_get_by_slug(self, db_session: AsyncSession):
        """Test getting a category by slug"""
        repo = CategoryRepository(db_session)
        
        await repo.create({
            "name": "Clothing",
            "slug": "clothing",
            "description": "Clothing items"
        })
        
        category = await repo.get_by_slug("clothing")
        
        assert category is not None
        assert category.slug == "clothing"
        assert category.name == "Clothing"
    
    async def test_get_root_categories(self, db_session: AsyncSession):
        """Test getting root categories (no parent)"""
        repo = CategoryRepository(db_session)
        
        # Create root categories
        await repo.create({
            "name": "Root 1",
            "slug": "root-1"
        })
        await repo.create({
            "name": "Root 2",
            "slug": "root-2"
        })
        
        # Create child category
        parent = await repo.create({
            "name": "Parent",
            "slug": "parent"
        })
        await repo.create({
            "name": "Child",
            "slug": "child",
            "parent_id": parent.id
        })
        
        # Get root categories
        roots = await repo.get_root_categories()
        
        assert len(roots) >= 2
        root_names = [r.name for r in roots]
        assert "Root 1" in root_names
        assert "Root 2" in root_names
        assert "Child" not in root_names
    
    async def test_get_children(self, db_session: AsyncSession):
        """Test getting child categories"""
        repo = CategoryRepository(db_session)
        
        # Create parent
        parent = await repo.create({
            "name": "Parent Category",
            "slug": "parent-cat"
        })
        
        # Create children
        for i in range(3):
            await repo.create({
                "name": f"Child {i}",
                "slug": f"child-{i}",
                "parent_id": parent.id
            })
        
        # Get children
        children = await repo.get_children(parent.id)
        
        assert len(children) == 3
        child_names = [c.name for c in children]
        for i in range(3):
            assert f"Child {i}" in child_names
    
    async def test_get_tree(self, db_session: AsyncSession):
        """Test getting category tree with children"""
        repo = CategoryRepository(db_session)
        
        # Create parent
        parent = await repo.create({
            "name": "Electronics",
            "slug": "electronics"
        })
        
        # Create children
        computers = await repo.create({
            "name": "Computers",
            "slug": "computers",
            "parent_id": parent.id
        })
        phones = await repo.create({
            "name": "Phones",
            "slug": "phones",
            "parent_id": parent.id
        })
        
        # Create grandchildren
        await repo.create({
            "name": "Laptops",
            "slug": "laptops",
            "parent_id": computers.id
        })
        await repo.create({
            "name": "Desktops",
            "slug": "desktops",
            "parent_id": computers.id
        })
        
        # Get tree
        tree = await repo.get_tree(parent.id)
        
        assert tree is not None
        assert tree.name == "Electronics"
        assert len(tree.children) == 2
        
        # Find computers child
        computers_child = next((c for c in tree.children if c.name == "Computers"), None)
        assert computers_child is not None
        assert len(computers_child.children) == 2


class TestBrandRepository:
    """Tests for BrandRepository"""
    
    async def test_create_brand(self, db_session: AsyncSession):
        """Test creating a brand"""
        repo = BrandRepository(db_session)
        
        brand_data = {
            "name": "Nike",
            "code": "NIKE",
            "slug": "nike",
            "description": "Athletic wear"
        }
        
        brand = await repo.create(brand_data)
        
        assert brand.id is not None
        assert brand.name == "Nike"
        assert brand.code == "NIKE"
        assert brand.slug == "nike"
    
    async def test_get_by_slug(self, db_session: AsyncSession):
        """Test getting a brand by slug"""
        repo = BrandRepository(db_session)
        
        await repo.create({
            "name": "Adidas",
            "code": "ADI",
            "slug": "adidas"
        })
        
        brand = await repo.get_by_slug("adidas")
        
        assert brand is not None
        assert brand.slug == "adidas"
        assert brand.name == "Adidas"
    
    async def test_get_by_code(self, db_session: AsyncSession):
        """Test getting a brand by code"""
        repo = BrandRepository(db_session)
        
        await repo.create({
            "name": "Puma",
            "code": "PUMA",
            "slug": "puma"
        })
        
        brand = await repo.get_by_code("PUMA")
        
        assert brand is not None
        assert brand.code == "PUMA"
        assert brand.name == "Puma"
    
    async def test_search_brands(self, db_session: AsyncSession):
        """Test searching brands"""
        repo = BrandRepository(db_session)
        
        # Create brands
        brands = ["Nike", "Adidas", "Puma", "Under Armour", "New Balance"]
        for name in brands:
            await repo.create({
                "name": name,
                "code": name.upper().replace(" ", ""),
                "slug": name.lower().replace(" ", "-")
            })
        
        # Search
        results, total = await repo.search_brands("Arm", skip=0, limit=10)
        
        assert total >= 1
        assert any("Armour" in r.name for r in results)


class TestSupplierRepository:
    """Tests for SupplierRepository"""
    
    async def test_create_supplier(self, db_session: AsyncSession):
        """Test creating a supplier"""
        repo = SupplierRepository(db_session)
        
        supplier_data = {
            "name": "ABC Supplies",
            "code": "ABC",
            "email": "contact@abc.com",
            "phone": "123-456-7890",
            "is_active": True
        }
        
        supplier = await repo.create(supplier_data)
        
        assert supplier.id is not None
        assert supplier.name == "ABC Supplies"
        assert supplier.code == "ABC"
        assert supplier.email == "contact@abc.com"
    
    async def test_get_by_code(self, db_session: AsyncSession):
        """Test getting a supplier by code"""
        repo = SupplierRepository(db_session)
        
        await repo.create({
            "name": "XYZ Corp",
            "code": "XYZ",
            "email": "info@xyz.com"
        })
        
        supplier = await repo.get_by_code("XYZ")
        
        assert supplier is not None
        assert supplier.code == "XYZ"
        assert supplier.name == "XYZ Corp"
    
    async def test_get_by_email(self, db_session: AsyncSession):
        """Test getting a supplier by email"""
        repo = SupplierRepository(db_session)
        
        await repo.create({
            "name": "DEF Company",
            "code": "DEF",
            "email": "contact@def.com"
        })
        
        supplier = await repo.get_by_email("contact@def.com")
        
        assert supplier is not None
        assert supplier.email == "contact@def.com"
        assert supplier.name == "DEF Company"
    
    async def test_get_active_suppliers(self, db_session: AsyncSession):
        """Test getting only active suppliers"""
        repo = SupplierRepository(db_session)
        
        # Create active suppliers
        await repo.create({
            "name": "Active 1",
            "code": "ACT1",
            "email": "act1@test.com",
            "is_active": True
        })
        await repo.create({
            "name": "Active 2",
            "code": "ACT2",
            "email": "act2@test.com",
            "is_active": True
        })
        
        # Create inactive supplier
        await repo.create({
            "name": "Inactive",
            "code": "INACT",
            "email": "inact@test.com",
            "is_active": False
        })
        
        # Get active suppliers
        active = await repo.get_active_suppliers()
        
        assert len(active) >= 2
        assert all(s.is_active for s in active)
        active_names = [s.name for s in active]
        assert "Inactive" not in active_names
    
    async def test_search_suppliers(self, db_session: AsyncSession):
        """Test searching suppliers"""
        repo = SupplierRepository(db_session)
        
        # Create suppliers
        suppliers = ["Global Supplies", "Local Vendor", "International Trade Co"]
        for name in suppliers:
            code = "".join(word[0] for word in name.split())
            await repo.create({
                "name": name,
                "code": code,
                "email": f"{code.lower()}@test.com"
            })
        
        # Search
        results, total = await repo.search_suppliers("Global", skip=0, limit=10)
        
        assert total >= 1
        assert any("Global" in r.name for r in results)
