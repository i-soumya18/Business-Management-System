"""
Product Variant API Routes

Endpoints for managing product variants (size, color, style combinations).
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.product import (
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantResponse,
    ProductVariantListResponse
)
from app.repositories.product import ProductVariantRepository, ProductRepository
from app.api.dependencies import SearchParams


router = APIRouter(prefix="/api/v1/inventory/variants", tags=["Product Variants"])


@router.post("/", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant(
    variant_data: ProductVariantCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product variant
    
    SKU and barcode must be unique across all variants.
    """
    variant_repo = ProductVariantRepository(db)
    product_repo = ProductRepository(db)
    
    # Check if product exists
    product = await product_repo.get_by_id(variant_data.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {variant_data.product_id} not found"
        )
    
    # Check if SKU already exists
    if variant_data.sku:
        existing_sku = await variant_repo.get_by_sku(variant_data.sku)
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant with SKU '{variant_data.sku}' already exists"
            )
    
    # Check if barcode already exists
    if variant_data.barcode:
        existing_barcode = await variant_repo.get_by_barcode(variant_data.barcode)
        if existing_barcode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant with barcode '{variant_data.barcode}' already exists"
            )
    
    # Create variant
    variant = await variant_repo.create(variant_data.model_dump())
    return variant


@router.get("/", response_model=ProductVariantListResponse)
async def list_variants(
    search: SearchParams = Depends(),
    product_id: Optional[UUID] = Query(None, description="Filter by product"),
    size: Optional[str] = Query(None, description="Filter by size"),
    color: Optional[str] = Query(None, description="Filter by color"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all product variants with optional filtering and search
    
    Supports:
    - Full-text search in SKU, barcode, size, color
    - Filter by product, size, color
    - Filter by active status
    - Pagination
    """
    repo = ProductVariantRepository(db)
    
    variants, total = await repo.search(
        query=search.q or "",
        product_id=product_id,
        size=size,
        color=color,
        is_active=is_active,
        skip=search.skip,
        limit=search.limit
    )
    
    pages = (total + search.limit - 1) // search.limit
    
    return {
        "items": variants,
        "total": total,
        "page": search.skip // search.limit + 1,
        "page_size": search.limit,
        "pages": pages
    }


@router.get("/product/{product_id}", response_model=List[ProductVariantResponse])
async def list_variants_by_product(
    product_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get all variants for a specific product"""
    repo = ProductVariantRepository(db)
    variants = await repo.get_by_product(
        product_id,
        skip=skip,
        limit=limit
    )
    return variants


@router.get("/{variant_id}", response_model=ProductVariantResponse)
async def get_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a variant by ID
    
    Includes product details and inventory levels.
    """
    repo = ProductVariantRepository(db)
    variant = await repo.get_with_inventory(variant_id)
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    return variant


@router.get("/sku/{sku}", response_model=ProductVariantResponse)
async def get_variant_by_sku(
    sku: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a variant by SKU"""
    repo = ProductVariantRepository(db)
    variant = await repo.get_by_sku(sku)
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant with SKU '{sku}' not found"
        )
    
    return variant


@router.get("/barcode/{barcode}", response_model=ProductVariantResponse)
async def get_variant_by_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a variant by barcode (for POS scanning)"""
    repo = ProductVariantRepository(db)
    variant = await repo.get_by_barcode(barcode)
    
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variant with barcode '{barcode}' not found"
        )
    
    return variant


@router.get("/{variant_id}/stock", response_model=dict)
async def get_variant_stock(
    variant_id: UUID,
    location_id: Optional[UUID] = Query(None, description="Specific location"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available stock for a variant
    
    Returns total stock or stock at a specific location.
    """
    repo = ProductVariantRepository(db)
    
    # Check if variant exists
    variant = await repo.get_by_id(variant_id)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    available_stock = await repo.get_available_stock(variant_id, location_id)
    
    return {
        "variant_id": variant_id,
        "location_id": location_id,
        "available_stock": available_stock,
        "sku": variant.sku
    }


@router.put("/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    variant_id: UUID,
    variant_data: ProductVariantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a product variant
    
    Can update any variant field except ID and product_id.
    SKU and barcode must remain unique if changed.
    """
    repo = ProductVariantRepository(db)
    
    # Check if variant exists
    existing = await repo.get_by_id(variant_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    # Check if SKU is being changed and already exists
    if variant_data.sku and variant_data.sku != existing.sku:
        sku_exists = await repo.get_by_sku(variant_data.sku)
        if sku_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant with SKU '{variant_data.sku}' already exists"
            )
    
    # Check if barcode is being changed and already exists
    if variant_data.barcode and variant_data.barcode != existing.barcode:
        barcode_exists = await repo.get_by_barcode(variant_data.barcode)
        if barcode_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant with barcode '{variant_data.barcode}' already exists"
            )
    
    # Update variant
    updated_variant = await repo.update(
        variant_id,
        variant_data.model_dump(exclude_unset=True)
    )
    
    return updated_variant


@router.delete("/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product variant
    
    Note: Consider soft-delete by setting is_active=False instead.
    """
    repo = ProductVariantRepository(db)
    
    # Check if variant exists
    exists = await repo.exists(variant_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    # TODO: Check if variant has inventory or orders before deleting
    # For now, just delete
    await repo.delete(variant_id)
    
    return None


@router.patch("/{variant_id}/activate", response_model=ProductVariantResponse)
async def activate_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Activate a product variant"""
    repo = ProductVariantRepository(db)
    
    variant = await repo.update(variant_id, {"is_active": True})
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    return variant


@router.patch("/{variant_id}/deactivate", response_model=ProductVariantResponse)
async def deactivate_variant(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a product variant (soft delete)"""
    repo = ProductVariantRepository(db)
    
    variant = await repo.update(variant_id, {"is_active": False})
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found"
        )
    
    return variant
