"""
Category API Routes

Endpoints for managing hierarchical product categories.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithChildren,
    CategoryTree,
    CategoryListResponse
)
from app.repositories.category_brand_supplier import CategoryRepository
from app.api.dependencies import PaginationParams


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new category
    
    Slug must be unique across all categories.
    Can be a root category (no parent) or subcategory (with parent).
    """
    repo = CategoryRepository(db)
    
    # Check if slug already exists
    existing_slug = await repo.get_by_slug(category_data.slug)
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category_data.slug}' already exists"
        )
    
    # If parent specified, verify it exists
    if category_data.parent_id:
        parent = await repo.get_by_id(category_data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category {category_data.parent_id} not found"
            )
    
    # Create category
    category = await repo.create(category_data.model_dump())
    return category


@router.get("/", response_model=CategoryListResponse)
async def list_categories(
    pagination: PaginationParams = Depends(),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent category"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all categories with optional filtering
    
    Use parent_id=null to get only root categories.
    """
    repo = CategoryRepository(db)
    
    filters = {}
    if parent_id:
        filters["parent_id"] = parent_id
    
    categories = await repo.get_all(
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    total = await repo.count(filters)
    pages = (total + pagination.limit - 1) // pagination.limit
    
    return {
        "items": categories,
        "total": total,
        "page": pagination.skip // pagination.limit + 1,
        "page_size": pagination.limit,
        "pages": pages
    }


@router.get("/roots", response_model=List[CategoryResponse])
async def list_root_categories(
    db: AsyncSession = Depends(get_db)
):
    """Get all root categories (no parent)"""
    repo = CategoryRepository(db)
    categories = await repo.get_root_categories()
    return categories


@router.get("/tree", response_model=List[CategoryTree])
async def get_category_tree(
    parent_id: Optional[UUID] = Query(None, description="Root category (null for full tree)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete category tree with all descendants
    
    Returns hierarchical structure with full paths and levels.
    """
    repo = CategoryRepository(db)
    tree = await repo.get_tree(parent_id)
    return tree


@router.get("/{category_id}", response_model=CategoryWithChildren)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a category by ID with its direct children
    
    Use /tree endpoint for full hierarchy.
    """
    repo = CategoryRepository(db)
    category = await repo.get_with_children(category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a category by slug"""
    repo = CategoryRepository(db)
    category = await repo.get_by_slug(slug)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with slug '{slug}' not found"
        )
    
    return category


@router.get("/{category_id}/children", response_model=List[CategoryResponse])
async def get_category_children(
    category_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all direct children of a category"""
    repo = CategoryRepository(db)
    
    # Verify parent exists
    parent = await repo.get_by_id(category_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    children = await repo.get_children(category_id)
    return children


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a category
    
    Can change name, description, slug, parent, etc.
    Slug must remain unique if changed.
    """
    repo = CategoryRepository(db)
    
    # Check if category exists
    existing = await repo.get_by_id(category_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if slug is being changed and already exists
    if category_data.slug and category_data.slug != existing.slug:
        slug_exists = await repo.get_by_slug(category_data.slug)
        if slug_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{category_data.slug}' already exists"
            )
    
    # If parent is being changed, verify new parent exists
    if category_data.parent_id and category_data.parent_id != existing.parent_id:
        # Prevent circular reference
        if category_data.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )
        
        new_parent = await repo.get_by_id(category_data.parent_id)
        if not new_parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category {category_data.parent_id} not found"
            )
    
    # Update category
    updated_category = await repo.update(
        category_id,
        category_data.model_dump(exclude_unset=True)
    )
    
    return updated_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a category
    
    Note: Will also delete all child categories.
    Consider soft-delete by setting is_active=False instead.
    """
    repo = CategoryRepository(db)
    
    # Check if category exists
    exists = await repo.exists(category_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # TODO: Check if category has products before deleting
    # TODO: Handle child categories
    # For now, just delete
    await repo.delete(category_id)
    
    return None
