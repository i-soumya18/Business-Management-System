"""
Brand and Supplier API Routes

Endpoints for managing brands and suppliers.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.brand_supplier import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse
)
from app.repositories.category_brand_supplier import BrandRepository, SupplierRepository
from app.api.dependencies import PaginationParams, SearchParams


# ============================================================================
# Brand Routes
# ============================================================================

brand_router = APIRouter(prefix="/api/v1/inventory/brands", tags=["Brands"])


@brand_router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_data: BrandCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new brand
    
    Code and slug must be unique.
    """
    repo = BrandRepository(db)
    
    # Check if code already exists
    existing_code = await repo.get_by_code(brand_data.code)
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand with code '{brand_data.code}' already exists"
        )
    
    # Check if slug already exists
    existing_slug = await repo.get_by_slug(brand_data.slug)
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Brand with slug '{brand_data.slug}' already exists"
        )
    
    # Create brand
    brand = await repo.create(brand_data.model_dump())
    return brand


@brand_router.get("/", response_model=List[BrandResponse])
async def list_brands(
    search: SearchParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List all brands with optional search
    
    Searches in brand name and code.
    """
    repo = BrandRepository(db)
    
    if search.q:
        brands, total = await repo.search_brands(
            query=search.q,
            skip=search.skip,
            limit=search.limit
        )
    else:
        brands = await repo.get_all(
            skip=search.skip,
            limit=search.limit
        )
    
    return brands


@brand_router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a brand by ID"""
    repo = BrandRepository(db)
    brand = await repo.get_by_id(brand_id)
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return brand


@brand_router.get("/slug/{slug}", response_model=BrandResponse)
async def get_brand_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a brand by slug"""
    repo = BrandRepository(db)
    brand = await repo.get_by_slug(slug)
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with slug '{slug}' not found"
        )
    
    return brand


@brand_router.get("/code/{code}", response_model=BrandResponse)
async def get_brand_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a brand by code"""
    repo = BrandRepository(db)
    brand = await repo.get_by_code(code)
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with code '{code}' not found"
        )
    
    return brand


@brand_router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    brand_data: BrandUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a brand"""
    repo = BrandRepository(db)
    
    # Check if brand exists
    existing = await repo.get_by_id(brand_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Check uniqueness constraints
    if brand_data.code and brand_data.code != existing.code:
        code_exists = await repo.get_by_code(brand_data.code)
        if code_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand with code '{brand_data.code}' already exists"
            )
    
    if brand_data.slug and brand_data.slug != existing.slug:
        slug_exists = await repo.get_by_slug(brand_data.slug)
        if slug_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand with slug '{brand_data.slug}' already exists"
            )
    
    # Update brand
    updated_brand = await repo.update(
        brand_id,
        brand_data.model_dump(exclude_unset=True)
    )
    
    return updated_brand


@brand_router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a brand"""
    repo = BrandRepository(db)
    
    # Check if brand exists
    exists = await repo.exists(brand_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # TODO: Check if brand has products before deleting
    await repo.delete(brand_id)
    
    return None


# ============================================================================
# Supplier Routes
# ============================================================================

supplier_router = APIRouter(prefix="/api/v1/inventory/suppliers", tags=["Suppliers"])


@supplier_router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new supplier
    
    Code and email must be unique.
    """
    repo = SupplierRepository(db)
    
    # Check if code already exists
    existing_code = await repo.get_by_code(supplier_data.code)
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier with code '{supplier_data.code}' already exists"
        )
    
    # Check if email already exists
    if supplier_data.email:
        existing_email = await repo.get_by_email(supplier_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with email '{supplier_data.email}' already exists"
            )
    
    # Create supplier
    supplier = await repo.create(supplier_data.model_dump())
    return supplier


@supplier_router.get("/", response_model=List[SupplierResponse])
async def list_suppliers(
    search: SearchParams = Depends(),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all suppliers with optional search and filtering
    
    Searches in supplier name, code, and email.
    """
    repo = SupplierRepository(db)
    
    suppliers, total = await repo.search_suppliers(
        query=search.q or "",
        is_active=is_active,
        skip=search.skip,
        limit=search.limit
    )
    
    return suppliers


@supplier_router.get("/active", response_model=List[SupplierResponse])
async def list_active_suppliers(
    db: AsyncSession = Depends(get_db)
):
    """Get all active suppliers ordered by rating"""
    repo = SupplierRepository(db)
    suppliers = await repo.get_active_suppliers()
    return suppliers


@supplier_router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a supplier by ID"""
    repo = SupplierRepository(db)
    supplier = await repo.get_by_id(supplier_id)
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier


@supplier_router.get("/code/{code}", response_model=SupplierResponse)
async def get_supplier_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a supplier by code"""
    repo = SupplierRepository(db)
    supplier = await repo.get_by_code(code)
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with code '{code}' not found"
        )
    
    return supplier


@supplier_router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    supplier_data: SupplierUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a supplier"""
    repo = SupplierRepository(db)
    
    # Check if supplier exists
    existing = await repo.get_by_id(supplier_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    # Check uniqueness constraints
    if supplier_data.code and supplier_data.code != existing.code:
        code_exists = await repo.get_by_code(supplier_data.code)
        if code_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with code '{supplier_data.code}' already exists"
            )
    
    if supplier_data.email and supplier_data.email != existing.email:
        email_exists = await repo.get_by_email(supplier_data.email)
        if email_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with email '{supplier_data.email}' already exists"
            )
    
    # Update supplier
    updated_supplier = await repo.update(
        supplier_id,
        supplier_data.model_dump(exclude_unset=True)
    )
    
    return updated_supplier


@supplier_router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a supplier"""
    repo = SupplierRepository(db)
    
    # Check if supplier exists
    exists = await repo.exists(supplier_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    # TODO: Check if supplier has products before deleting
    await repo.delete(supplier_id)
    
    return None


@supplier_router.patch("/{supplier_id}/activate", response_model=SupplierResponse)
async def activate_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Activate a supplier"""
    repo = SupplierRepository(db)
    
    supplier = await repo.update(supplier_id, {"is_active": True})
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier


@supplier_router.patch("/{supplier_id}/deactivate", response_model=SupplierResponse)
async def deactivate_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a supplier"""
    repo = SupplierRepository(db)
    
    supplier = await repo.update(supplier_id, {"is_active": False})
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier
