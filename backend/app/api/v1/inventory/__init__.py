"""
Inventory Module Router

Combines all inventory-related endpoints into a single router.
"""

from fastapi import APIRouter

from app.api.v1.inventory import products, variants, categories, brands_suppliers, locations, levels, operations, adjustments_alerts, import_export

router = APIRouter()

# Include all inventory endpoints
router.include_router(
    products.router,
    tags=["Inventory - Products"]
)

router.include_router(
    variants.router,
    tags=["Inventory - Variants"]
)

router.include_router(
    categories.router,
    tags=["Inventory - Categories"]
)

router.include_router(
    brands_suppliers.brand_router,
    tags=["Inventory - Brands"]
)

router.include_router(
    brands_suppliers.supplier_router,
    tags=["Inventory - Suppliers"]
)

router.include_router(
    locations.router,
    tags=["Inventory - Locations"]
)

router.include_router(
    levels.router,
    tags=["Inventory - Stock Levels"]
)

router.include_router(
    operations.router,
    tags=["Inventory - Operations"]
)

router.include_router(
    adjustments_alerts.router,
    tags=["Inventory - Adjustments & Alerts"]
)

router.include_router(
    import_export.router,
    tags=["Inventory - Import/Export"]
)