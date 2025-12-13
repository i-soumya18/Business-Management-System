"""
Measurement Specifications and Garment Images API Routes

API endpoints for managing product measurements and image galleries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.repositories.garment import MeasurementSpecRepository, GarmentImageRepository
from app.schemas.garment import (
    MeasurementSpecCreate,
    MeasurementSpecUpdate,
    MeasurementSpecResponse,
    GarmentImageCreate,
    GarmentImageUpdate,
    GarmentImageResponse
)


# Measurement Spec Router
measurement_router = APIRouter(prefix="/measurements", tags=["measurements"])


@measurement_router.post("/", response_model=MeasurementSpecResponse, status_code=status.HTTP_201_CREATED)
async def create_measurement_spec(
    measurement_data: MeasurementSpecCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new measurement specification"""
    repo = MeasurementSpecRepository(db)
    
    # Check for duplicate
    existing = await repo.get_by_product_and_size(
        measurement_data.product_id,
        measurement_data.size
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Measurement spec for product {measurement_data.product_id} size {measurement_data.size} already exists"
        )
    
    measurement = await repo.create(measurement_data.model_dump())
    return measurement


@measurement_router.get("/product/{product_id}", response_model=List[MeasurementSpecResponse])
async def get_measurements_by_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all measurement specifications for a product"""
    repo = MeasurementSpecRepository(db)
    measurements = await repo.get_by_product(product_id)
    return measurements


@measurement_router.get("/product/{product_id}/size/{size}", response_model=MeasurementSpecResponse)
async def get_measurement_by_product_and_size(
    product_id: int,
    size: str,
    db: AsyncSession = Depends(get_db)
):
    """Get measurement specification for a specific product size"""
    repo = MeasurementSpecRepository(db)
    measurement = await repo.get_by_product_and_size(product_id, size)
    
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measurement spec for product {product_id} size {size} not found"
        )
    
    return measurement


@measurement_router.get("/{measurement_id}", response_model=MeasurementSpecResponse)
async def get_measurement_spec(
    measurement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific measurement specification by ID"""
    repo = MeasurementSpecRepository(db)
    measurement = await repo.get_by_id(measurement_id)
    
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement specification not found"
        )
    
    return measurement


@measurement_router.put("/{measurement_id}", response_model=MeasurementSpecResponse)
async def update_measurement_spec(
    measurement_id: int,
    measurement_data: MeasurementSpecUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a measurement specification"""
    repo = MeasurementSpecRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(measurement_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement specification not found"
        )
    
    measurement = await repo.update(measurement_id, measurement_data.model_dump(exclude_unset=True))
    return measurement


@measurement_router.delete("/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_measurement_spec(
    measurement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a measurement specification"""
    repo = MeasurementSpecRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(measurement_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement specification not found"
        )
    
    await repo.delete(measurement_id)
    return None


# Garment Image Router
image_router = APIRouter(prefix="/images", tags=["garment-images"])


@image_router.post("/", response_model=GarmentImageResponse, status_code=status.HTTP_201_CREATED)
async def create_garment_image(
    image_data: GarmentImageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new garment image"""
    repo = GarmentImageRepository(db)
    
    # If this is set as primary, unset other primary images for the product
    if image_data.is_primary:
        existing_images = await repo.get_by_product(image_data.product_id, active_only=False)
        for img in existing_images:
            if img.is_primary:
                await repo.update(img.id, {"is_primary": False})
    
    image = await repo.create(image_data.model_dump())
    return image


@image_router.get("/product/{product_id}", response_model=List[GarmentImageResponse])
async def get_images_by_product(
    product_id: int,
    active_only: bool = Query(True),
    color_id: int = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all images for a product, optionally filtered by color"""
    repo = GarmentImageRepository(db)
    
    if color_id:
        images = await repo.get_by_color(product_id, color_id)
    else:
        images = await repo.get_by_product(product_id, active_only=active_only)
    
    return images


@image_router.get("/product/{product_id}/primary", response_model=GarmentImageResponse)
async def get_primary_image(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get the primary image for a product"""
    repo = GarmentImageRepository(db)
    image = await repo.get_primary_image(product_id)
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No primary image found for product {product_id}"
        )
    
    return image


@image_router.get("/{image_id}", response_model=GarmentImageResponse)
async def get_garment_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific garment image by ID"""
    repo = GarmentImageRepository(db)
    image = await repo.get_by_id(image_id)
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garment image not found"
        )
    
    return image


@image_router.put("/{image_id}", response_model=GarmentImageResponse)
async def update_garment_image(
    image_id: int,
    image_data: GarmentImageUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a garment image"""
    repo = GarmentImageRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(image_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garment image not found"
        )
    
    # If setting as primary, unset other primary images for the product
    if image_data.is_primary:
        existing_images = await repo.get_by_product(existing.product_id, active_only=False)
        for img in existing_images:
            if img.is_primary and img.id != image_id:
                await repo.update(img.id, {"is_primary": False})
    
    image = await repo.update(image_id, image_data.model_dump(exclude_unset=True))
    return image


@image_router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_garment_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a garment image"""
    repo = GarmentImageRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(image_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garment image not found"
        )
    
    await repo.delete(image_id)
    return None


@image_router.patch("/{image_id}/set-primary", response_model=GarmentImageResponse)
async def set_primary_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Set an image as the primary image for its product"""
    repo = GarmentImageRepository(db)
    
    # Check if exists
    existing = await repo.get_by_id(image_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garment image not found"
        )
    
    # Unset other primary images for the product
    existing_images = await repo.get_by_product(existing.product_id, active_only=False)
    for img in existing_images:
        if img.is_primary:
            await repo.update(img.id, {"is_primary": False})
    
    # Set this image as primary
    image = await repo.update(image_id, {"is_primary": True})
    return image


@image_router.post("/bulk", response_model=List[GarmentImageResponse])
async def create_bulk_images(
    images_data: List[GarmentImageCreate],
    db: AsyncSession = Depends(get_db)
):
    """Create multiple garment images in bulk"""
    repo = GarmentImageRepository(db)
    
    created_images = []
    for image_data in images_data:
        image = await repo.create(image_data.model_dump())
        created_images.append(image)
    
    return created_images
