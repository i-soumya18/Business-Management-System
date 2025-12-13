"""
API Router - Version 1
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, users
from app.api.v1.garment import garment_router
from app.api.v1 import reports

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["User Management"]
)

# Garment-specific features
api_router.include_router(
    garment_router,
    prefix="/garment",
    tags=["Garment Features"]
)

# Reports and Analytics
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports & Analytics"]
)

# Future routers will be added here:
# api_router.include_router(roles.router, prefix="/roles", tags=["Roles & Permissions"])
# api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
# api_router.include_router(sales.router, prefix="/sales", tags=["Sales"])
# api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
# api_router.include_router(customers.router, prefix="/customers", tags=["CRM"])
# api_router.include_router(finance.router, prefix="/finance", tags=["Finance"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
# api_router.include_router(ml.router, prefix="/ml", tags=["ML/AI"])
