"""
Import/Export API Routes

Endpoints for bulk import/export of inventory data via CSV and file uploads.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.database.session import get_db
from app.services.csv_service import CSVImportExportService
from app.services.file_upload import FileUploadService
from app.repositories.product import ProductRepository, ProductVariantRepository


router = APIRouter(prefix="/api/v1/inventory/import-export", tags=["Import/Export"])
csv_service = CSVImportExportService()
file_service = FileUploadService()


# ============================================================================
# CSV Export Endpoints
# ============================================================================

@router.get("/export/products")
async def export_products(
    category_id: UUID | None = Query(None),
    brand_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Export products to CSV
    
    Returns a CSV file with all products or filtered by category/brand.
    """
    repo = ProductRepository(db)
    
    # Build filters
    filters = {}
    if category_id:
        filters["category_id"] = category_id
    if brand_id:
        filters["brand_id"] = brand_id
    
    # Get products
    products = await repo.get_all(limit=10000, filters=filters)
    
    # Convert to dictionaries
    product_dicts = [
        {
            "sku": p.sku,
            "name": p.name,
            "description": p.description,
            "category_id": str(p.category_id) if p.category_id else "",
            "brand_id": str(p.brand_id) if p.brand_id else "",
            "supplier_id": str(p.primary_supplier_id) if p.primary_supplier_id else "",
            "unit_cost": p.unit_cost or "",
            "wholesale_price": p.wholesale_price or "",
            "retail_price": p.retail_price or "",
            "fabric_type": p.fabric_type or "",
            "fabric_composition": p.fabric_composition or "",
            "care_instructions": p.care_instructions or "",
            "season": p.season or "",
            "collection": p.collection or "",
            "is_active": p.is_active
        }
        for p in products
    ]
    
    # Generate CSV
    csv_content = await csv_service.export_products_to_csv(product_dicts)
    
    # Return as downloadable file
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_export.csv"}
    )


@router.get("/export/variants")
async def export_variants(
    product_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Export product variants to CSV
    
    Returns CSV with all variants or filtered by product.
    """
    repo = ProductVariantRepository(db)
    
    # Get variants
    if product_id:
        variants = await repo.get_by_product(product_id, limit=10000)
    else:
        variants = await repo.get_all(limit=10000)
    
    # Convert to dictionaries
    variant_dicts = [
        {
            "sku": v.sku,
            "barcode": v.barcode or "",
            "product_id": str(v.product_id),
            "size": v.size or "",
            "color": v.color or "",
            "style": v.style or "",
            "unit_cost": v.unit_cost or "",
            "wholesale_price": v.wholesale_price or "",
            "retail_price": v.retail_price or "",
            "sale_price": v.sale_price or "",
            "weight": v.weight or "",
            "length": v.length or "",
            "width": v.width or "",
            "height": v.height or "",
            "is_active": v.is_active
        }
        for v in variants
    ]
    
    # Generate CSV
    csv_content = await csv_service.export_variants_to_csv(variant_dicts)
    
    # Return as downloadable file
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=variants_export.csv"}
    )


@router.get("/export/inventory")
async def export_inventory(
    location_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Export inventory levels to CSV
    
    Returns CSV with inventory levels, optionally filtered by location.
    """
    from app.repositories.inventory import InventoryLevelRepository
    
    repo = InventoryLevelRepository(db)
    
    # Get inventory levels
    if location_id:
        levels = await repo.get_by_location(location_id, limit=10000)
    else:
        levels = await repo.get_all(limit=10000)
    
    # Convert to dictionaries
    level_dicts = [
        {
            "variant_id": str(l.product_variant_id),
            "location_id": str(l.location_id),
            "quantity_on_hand": l.quantity_on_hand,
            "quantity_reserved": l.quantity_reserved,
            "quantity_available": l.quantity_available,
            "reorder_point": l.reorder_point or "",
            "reorder_quantity": l.reorder_quantity or "",
            "max_stock_level": l.max_stock_level or "",
            "last_counted_at": l.last_counted_at.isoformat() if l.last_counted_at else ""
        }
        for l in levels
    ]
    
    # Generate CSV
    csv_content = await csv_service.export_inventory_to_csv(level_dicts)
    
    # Return as downloadable file
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_export.csv"}
    )


# ============================================================================
# CSV Import Endpoints
# ============================================================================

@router.post("/import/products")
async def import_products(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Import products from CSV
    
    CSV should have columns: sku, name, description, category_id, brand_id, etc.
    """
    # Parse CSV
    products = await csv_service.parse_products_csv(file)
    
    repo = ProductRepository(db)
    
    # Import products
    created = 0
    updated = 0
    errors = []
    
    for product_data in products:
        try:
            # Check if product exists by SKU
            if product_data.get('sku'):
                existing = await repo.get_by_sku(product_data['sku'])
                
                if existing:
                    # Update existing product
                    await repo.update(existing.id, product_data)
                    updated += 1
                else:
                    # Create new product
                    await repo.create(product_data)
                    created += 1
        except Exception as e:
            errors.append({
                "sku": product_data.get('sku'),
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total_rows": len(products),
        "created": created,
        "updated": updated,
        "errors": errors
    }


@router.post("/import/variants")
async def import_variants(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Import product variants from CSV
    
    CSV should have columns: sku, barcode, product_id, size, color, etc.
    """
    # Parse CSV
    variants = await csv_service.parse_variants_csv(file)
    
    repo = ProductVariantRepository(db)
    
    # Import variants
    created = 0
    updated = 0
    errors = []
    
    for variant_data in variants:
        try:
            # Check if variant exists by SKU
            if variant_data.get('sku'):
                existing = await repo.get_by_sku(variant_data['sku'])
                
                if existing:
                    # Update existing variant
                    await repo.update(existing.id, variant_data)
                    updated += 1
                else:
                    # Create new variant
                    await repo.create(variant_data)
                    created += 1
        except Exception as e:
            errors.append({
                "sku": variant_data.get('sku'),
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total_rows": len(variants),
        "created": created,
        "updated": updated,
        "errors": errors
    }


# ============================================================================
# File Upload Endpoints
# ============================================================================

@router.post("/upload/product-image")
async def upload_product_image(
    file: UploadFile = File(...),
    product_id: str | None = Query(None)
):
    """
    Upload a product image
    
    Stores image locally (can be extended to S3/MinIO).
    """
    result = await file_service.upload_product_image(file, product_id)
    return result


@router.post("/upload/product-images")
async def upload_multiple_product_images(
    files: List[UploadFile] = File(...),
    product_id: str | None = Query(None)
):
    """Upload multiple product images"""
    results = await file_service.upload_multiple_images(files, product_id)
    return {
        "uploaded": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
        "results": results
    }


@router.post("/upload/brand-logo")
async def upload_brand_logo(
    file: UploadFile = File(...)
):
    """Upload a brand logo"""
    result = await file_service.upload_brand_logo(file)
    return result


@router.post("/upload/category-image")
async def upload_category_image(
    file: UploadFile = File(...)
):
    """Upload a category image"""
    result = await file_service.upload_category_image(file)
    return result


@router.delete("/file/{file_path:path}")
async def delete_file(
    file_path: str
):
    """Delete an uploaded file"""
    success = file_service.delete_file(file_path)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return {"message": "File deleted successfully"}


@router.get("/file/{file_path:path}/info")
async def get_file_info(
    file_path: str
):
    """Get information about an uploaded file"""
    info = file_service.get_file_info(file_path)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return info
