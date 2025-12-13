"""
Garment API Router
"""
from fastapi import APIRouter

from app.api.v1.garment.size_charts import router as size_charts_router
from app.api.v1.garment.attributes import (
    color_router,
    fabric_router,
    style_router,
    collection_router
)
from app.api.v1.garment.measurements_images import (
    measurement_router,
    image_router
)

# Create main garment router
garment_router = APIRouter()

# Include all sub-routers
garment_router.include_router(
    size_charts_router,
    prefix="/size-charts",
    tags=["Size Charts"]
)

garment_router.include_router(
    color_router,
    prefix="/colors",
    tags=["Colors"]
)

garment_router.include_router(
    fabric_router,
    prefix="/fabrics",
    tags=["Fabrics"]
)

garment_router.include_router(
    style_router,
    prefix="/styles",
    tags=["Styles"]
)

garment_router.include_router(
    collection_router,
    prefix="/collections",
    tags=["Collections"]
)

garment_router.include_router(
    measurement_router,
    prefix="/measurements",
    tags=["Measurements"]
)

garment_router.include_router(
    image_router,
    prefix="/images",
    tags=["Garment Images"]
)
