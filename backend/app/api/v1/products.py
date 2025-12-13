"""
Product API Endpoints

Endpoints for managing products and their variants.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductWithVariants,
    ProductListResponse
)
from app.repositories.product import ProductRepository
from app.api.dependencies import PaginationParams, SearchParams

router = APIRouter()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product

    SKU must be unique across all products.
    """
    repo = ProductRepository(db)

    # Check if SKU already exists
    if product_data.sku:
        existing = await repo.get_by_sku(product_data.sku)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product_data.sku}' already exists"
            )

    # Create product
    product = await repo.create(product_data.model_dump())
    return product


@router.get("/", response_model=ProductListResponse)
async def list_products(
    search: SearchParams = Depends(),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    brand_id: Optional[UUID] = Query(None, description="Filter by brand"),
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all products with optional filtering and search

    Supports:
    - Full-text search in name, SKU, description
    - Filter by category, brand, supplier
    - Filter by active status
    - Pagination
    """
    repo = ProductRepository(db)

    products, total = await repo.search(
        query=search.q or "",
        category_id=category_id,
        brand_id=brand_id,
        supplier_id=supplier_id,
        is_active=is_active,
        skip=search.skip,
        limit=search.limit
    )

    pages = (total + search.limit - 1) // search.limit

    return {
        "items": products,
        "total": total,
        "page": search.skip // search.limit + 1,
        "page_size": search.limit,
        "pages": pages
    }


@router.get("/low-stock", response_model=List[ProductResponse])
async def list_low_stock_products(
    location_id: Optional[UUID] = Query(None, description="Filter by location"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get products with low stock levels

    Returns products where any variant is below reorder point.
    """
    repo = ProductRepository(db)
    products = await repo.get_low_stock_products(location_id)
    return products


@router.get("/{product_id}", response_model=ProductWithVariants)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a product by ID with all its variants

    Includes category, brand, supplier details and all variants.
    """
    repo = ProductRepository(db)
    product = await repo.get_with_variants(product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


@router.get("/sku/{sku}", response_model=ProductResponse)
async def get_product_by_sku(
    sku: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a product by SKU"""
    repo = ProductRepository(db)
    product = await repo.get_by_sku(sku)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with SKU '{sku}' not found"
        )

    return product


@router.get("/category/{category_id}", response_model=List[ProductResponse])
async def list_products_by_category(
    category_id: UUID,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get all products in a specific category"""
    repo = ProductRepository(db)
    products = await repo.get_by_category(
        category_id,
        skip=pagination.skip,
        limit=pagination.limit
    )
    return products


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a product

    Can update any product field except ID.
    SKU must remain unique if changed.
    """
    repo = ProductRepository(db)

    # Check if product exists
    existing = await repo.get_by_id(product_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Check if SKU is being changed and already exists
    if product_data.sku and product_data.sku != existing.sku:
        sku_exists = await repo.get_by_sku(product_data.sku)
        if sku_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product_data.sku}' already exists"
            )

    # Update product
    updated_product = await repo.update(
        product_id,
        product_data.model_dump(exclude_unset=True)
    )

    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product

    Note: This will also delete all associated variants.
    Consider soft-delete by setting is_active=False instead.
    """
    repo = ProductRepository(db)

    # Check if product exists
    exists = await repo.exists(product_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # TODO: Check if product has inventory before deleting
    # For now, just delete
    await repo.delete(product_id)

    return None


@router.patch("/{product_id}/activate", response_model=ProductResponse)
async def activate_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Activate a product"""
    repo = ProductRepository(db)

    product = await repo.update(product_id, {"is_active": True})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product


@router.patch("/{product_id}/deactivate", response_model=ProductResponse)
async def deactivate_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a product (soft delete)"""
    repo = ProductRepository(db)

    product = await repo.update(product_id, {"is_active": False})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product