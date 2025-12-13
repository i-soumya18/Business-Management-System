"""
Color, Fabric, Style, and Collection API Routes

Comprehensive API endpoints for managing garment attributes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.garment import (
    ColorRepository,
    FabricRepository,
    StyleRepository,
    CollectionRepository
)
from app.schemas.garment import (
    ColorCreate, ColorUpdate, ColorResponse, ColorListResponse,
    FabricCreate, FabricUpdate, FabricResponse, FabricListResponse,
    StyleCreate, StyleUpdate, StyleResponse, StyleListResponse,
    CollectionCreate, CollectionUpdate, CollectionResponse, CollectionListResponse,
    SeasonEnum
)


# Color Router
color_router = APIRouter(prefix="/colors", tags=["colors"])


@color_router.post("/", response_model=ColorResponse, status_code=status.HTTP_201_CREATED)
async def create_color(
    color_data: ColorCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new color"""
    repo = ColorRepository(db)
    
    # Check for duplicate code
    existing = await repo.get_by_code(color_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Color with code {color_data.code} already exists"
        )
    
    color = await repo.create(color_data.model_dump())
    return color


@color_router.get("/", response_model=ColorListResponse)
async def list_colors(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List all colors"""
    repo = ColorRepository(db)
    
    if active_only:
        items = await repo.get_active_colors()
        total = len(items)
        items = items[skip:skip+limit]
    else:
        items, total = await repo.get_all(skip=skip, limit=limit)
    
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@color_router.get("/search", response_model=ColorListResponse)
async def search_colors(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Search colors by name or code"""
    repo = ColorRepository(db)
    items, total = await repo.search(q, skip=skip, limit=limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@color_router.get("/{color_id}", response_model=ColorResponse)
async def get_color(color_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific color by ID"""
    repo = ColorRepository(db)
    color = await repo.get_by_id(color_id)
    if not color:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Color not found")
    return color


@color_router.get("/code/{code}", response_model=ColorResponse)
async def get_color_by_code(code: str, db: AsyncSession = Depends(get_db)):
    """Get a color by code"""
    repo = ColorRepository(db)
    color = await repo.get_by_code(code)
    if not color:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Color not found")
    return color


@color_router.put("/{color_id}", response_model=ColorResponse)
async def update_color(
    color_id: int,
    color_data: ColorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a color"""
    repo = ColorRepository(db)
    existing = await repo.get_by_id(color_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Color not found")
    
    # Check code uniqueness if changing
    if color_data.code and color_data.code != existing.code:
        duplicate = await repo.get_by_code(color_data.code)
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Color with code {color_data.code} already exists"
            )
    
    color = await repo.update(color_id, color_data.model_dump(exclude_unset=True))
    return color


@color_router.delete("/{color_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_color(color_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a color"""
    repo = ColorRepository(db)
    existing = await repo.get_by_id(color_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Color not found")
    await repo.delete(color_id)
    return None


# Fabric Router
fabric_router = APIRouter(prefix="/fabrics", tags=["fabrics"])


@fabric_router.post("/", response_model=FabricResponse, status_code=status.HTTP_201_CREATED)
async def create_fabric(fabric_data: FabricCreate, db: AsyncSession = Depends(get_db)):
    """Create a new fabric"""
    repo = FabricRepository(db)
    existing = await repo.get_by_code(fabric_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fabric with code {fabric_data.code} already exists"
        )
    fabric = await repo.create(fabric_data.model_dump())
    return fabric


@fabric_router.get("/", response_model=FabricListResponse)
async def list_fabrics(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List all fabrics"""
    repo = FabricRepository(db)
    if active_only:
        items = await repo.get_active_fabrics()
        total = len(items)
        items = items[skip:skip+limit]
    else:
        items, total = await repo.get_all(skip=skip, limit=limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@fabric_router.get("/search", response_model=FabricListResponse)
async def search_fabrics(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Search fabrics by name or composition"""
    repo = FabricRepository(db)
    items, total = await repo.search(q, skip=skip, limit=limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@fabric_router.get("/{fabric_id}", response_model=FabricResponse)
async def get_fabric(fabric_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific fabric by ID"""
    repo = FabricRepository(db)
    fabric = await repo.get_by_id(fabric_id)
    if not fabric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fabric not found")
    return fabric


@fabric_router.put("/{fabric_id}", response_model=FabricResponse)
async def update_fabric(
    fabric_id: int,
    fabric_data: FabricUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a fabric"""
    repo = FabricRepository(db)
    existing = await repo.get_by_id(fabric_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fabric not found")
    fabric = await repo.update(fabric_id, fabric_data.model_dump(exclude_unset=True))
    return fabric


@fabric_router.delete("/{fabric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fabric(fabric_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a fabric"""
    repo = FabricRepository(db)
    existing = await repo.get_by_id(fabric_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fabric not found")
    await repo.delete(fabric_id)
    return None


# Style Router
style_router = APIRouter(prefix="/styles", tags=["styles"])


@style_router.post("/", response_model=StyleResponse, status_code=status.HTTP_201_CREATED)
async def create_style(style_data: StyleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new style"""
    repo = StyleRepository(db)
    existing = await repo.get_by_code(style_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Style with code {style_data.code} already exists"
        )
    style = await repo.create(style_data.model_dump())
    return style


@style_router.get("/", response_model=StyleListResponse)
async def list_styles(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List all styles"""
    repo = StyleRepository(db)
    if active_only:
        items = await repo.get_active_styles()
        total = len(items)
        items = items[skip:skip+limit]
    else:
        items, total = await repo.get_all(skip=skip, limit=limit)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@style_router.get("/{style_id}", response_model=StyleResponse)
async def get_style(style_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific style by ID"""
    repo = StyleRepository(db)
    style = await repo.get_by_id(style_id)
    if not style:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found")
    return style


@style_router.put("/{style_id}", response_model=StyleResponse)
async def update_style(
    style_id: int,
    style_data: StyleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a style"""
    repo = StyleRepository(db)
    existing = await repo.get_by_id(style_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found")
    style = await repo.update(style_id, style_data.model_dump(exclude_unset=True))
    return style


@style_router.delete("/{style_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style(style_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a style"""
    repo = StyleRepository(db)
    existing = await repo.get_by_id(style_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style not found")
    await repo.delete(style_id)
    return None


# Collection Router
collection_router = APIRouter(prefix="/collections", tags=["collections"])


@collection_router.post("/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(collection_data: CollectionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new collection"""
    repo = CollectionRepository(db)
    existing = await repo.get_by_code(collection_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collection with code {collection_data.code} already exists"
        )
    collection = await repo.create(collection_data.model_dump())
    return collection


@collection_router.get("/", response_model=CollectionListResponse)
async def list_collections(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    season: SeasonEnum = Query(None),
    year: int = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """List all collections with optional filters"""
    repo = CollectionRepository(db)
    
    if season:
        items = await repo.get_by_season(season=season.value, year=year)
        total = len(items)
        items = items[skip:skip+limit]
    elif active_only:
        items = await repo.get_active_collections()
        total = len(items)
        items = items[skip:skip+limit]
    else:
        items, total = await repo.get_all(skip=skip, limit=limit)
    
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@collection_router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific collection by ID"""
    repo = CollectionRepository(db)
    collection = await repo.get_by_id(collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection


@collection_router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    collection_data: CollectionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a collection"""
    repo = CollectionRepository(db)
    existing = await repo.get_by_id(collection_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    collection = await repo.update(collection_id, collection_data.model_dump(exclude_unset=True))
    return collection


@collection_router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a collection"""
    repo = CollectionRepository(db)
    existing = await repo.get_by_id(collection_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    await repo.delete(collection_id)
    return None
