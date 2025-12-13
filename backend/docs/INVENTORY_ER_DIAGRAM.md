# Inventory Module - Entity Relationship Diagram

## Schema Visualization

```
┌─────────────────────┐
│     Category        │
│─────────────────────│
│ id (PK, UUID)       │
│ name                │
│ slug (UNIQUE)       │
│ parent_id (FK) ──┐  │
│ description         │
│ display_order       │
│ is_active           │
└─────────────────────┘
         │
         └─────────────┐ (self-reference)
                       │
┌──────────────────────┴──────┐       ┌─────────────────────┐
│         Product             │       │       Brand         │
│─────────────────────────────│       │─────────────────────│
│ id (PK, UUID)               │       │ id (PK, UUID)       │
│ name                        │◄──────┤ name (UNIQUE)       │
│ slug (UNIQUE)               │       │ slug (UNIQUE)       │
│ sku (UNIQUE)                │       │ logo_url            │
│ category_id (FK)────────────┤       │ country_of_origin   │
│ brand_id (FK)               │       │ is_active           │
│ supplier_id (FK)────────────┤       └─────────────────────┘
│ garment_type                │
│ fabric_type                 │       ┌─────────────────────┐
│ fabric_composition          │       │      Supplier       │
│ care_instructions           │       │─────────────────────│
│ season                      │       │ id (PK, UUID)       │
│ collection                  │       │ name                │
│ base_cost_price             │       │ code (UNIQUE)       │
│ base_retail_price           │◄──────┤ contact_person      │
│ base_wholesale_price        │       │ email, phone        │
│ track_inventory             │       │ address fields      │
│ primary_image_url           │       │ payment_terms       │
│ is_active, is_featured      │       │ credit_limit        │
└────────────────┬────────────┘       │ rating              │
                 │                     │ lead_time_days      │
                 │                     └─────────────────────┘
                 │
                 │ 1:N
                 │
         ┌───────┴────────┐
         │                │
┌────────▼──────────────────────┐
│      ProductVariant           │
│───────────────────────────────│
│ id (PK, UUID)                 │
│ product_id (FK)               │
│ sku (UNIQUE)                  │
│ barcode (UNIQUE)              │
│ size                          │
│ color, color_code             │
│ style                         │
│ cost_price                    │
│ retail_price                  │
│ wholesale_price               │
│ sale_price                    │
│ weight, dimensions            │
│ is_active, is_default         │
└───────────┬───────────────────┘
            │
            │ 1:N
            │
    ┌───────┴────────┬────────────────────┐
    │                │                    │
┌───▼────────────────────────┐  ┌────────▼────────────────────┐
│    InventoryLevel          │  │   InventoryMovement         │
│────────────────────────────│  │─────────────────────────────│
│ id (PK, UUID)              │  │ id (PK, UUID)               │
│ product_variant_id (FK)    │  │ product_variant_id (FK)     │
│ location_id (FK)───────────┤  │ from_location_id (FK)────┐  │
│ quantity_on_hand           │  │ to_location_id (FK)──────┤  │
│ quantity_reserved          │  │ movement_type (ENUM)     │  │
│ quantity_available         │  │ quantity                 │  │
│ reorder_point              │  │ unit_cost, total_cost    │  │
│ reorder_quantity           │  │ reference_type, id       │  │
│ max_stock_level            │  │ created_by_id (FK)──┐    │  │
│ last_counted_at            │  │ movement_date        │    │  │
└────────────────────────────┘  └──────────────────────┴────┘  │
            │                                          │        │
            │ 1:1 per location                         │        │
            │                                          │        │
┌───────────▼──────────────┐                         │        │
│    StockLocation         │                         │        │
│──────────────────────────│                         │        │
│ id (PK, UUID)            │◄────────────────────────┘        │
│ name                     │◄─────────────────────────────────┘
│ code (UNIQUE)            │
│ location_type            │
│ address fields           │
│ contact_person           │
│ is_default               │
│ priority                 │
│ capacity                 │
│ is_active                │
└──────────┬───────────────┘
           │
           │ N:1
           │
┌──────────▼────────────────────┐       ┌─────────────────────┐
│    StockAdjustment            │       │    LowStockAlert    │
│───────────────────────────────│       │─────────────────────│
│ id (PK, UUID)                 │       │ id (PK, UUID)       │
│ location_id (FK)              │       │ variant_id (FK)─────┤
│ product_variant_id (FK)       │       │ location_id (FK)────┤
│ adjustment_number (UNIQUE)    │       │ current_quantity    │
│ reason                        │       │ reorder_point       │
│ expected_quantity             │       │ recommended_qty     │
│ actual_quantity               │       │ status              │
│ adjustment_quantity           │       │ resolved_at         │
│ unit_cost, total_cost_impact  │       │ resolved_by_id (FK)─┤
│ adjusted_by_id (FK)───────────┤       │ resolution_notes    │
│ approved_by_id (FK)───────────┤       └─────────────────────┘
│ status                        │
│ adjustment_date               │                 │
│ approved_at                   │                 │
└───────────────────────────────┘                 │
                                                  │
            ┌─────────────────────────────────────┘
            │
            │ References User table
            │ (from authentication module)
            │
┌───────────▼───────────┐
│        User           │
│───────────────────────│
│ id (PK, UUID)         │
│ email                 │
│ full_name             │
│ ...                   │
└───────────────────────┘
```

## Relationships Summary

### 1. Category (Self-Referential)
- **Type:** One-to-Many (recursive)
- **Relationship:** A category can have multiple subcategories
- **Foreign Key:** `parent_id` → `categories.id`
- **Delete Rule:** SET NULL

### 2. Product → Category
- **Type:** Many-to-One
- **Relationship:** Multiple products belong to one category
- **Foreign Key:** `product.category_id` → `categories.id`
- **Delete Rule:** SET NULL

### 3. Product → Brand
- **Type:** Many-to-One
- **Relationship:** Multiple products belong to one brand
- **Foreign Key:** `product.brand_id` → `brands.id`
- **Delete Rule:** SET NULL

### 4. Product → Supplier
- **Type:** Many-to-One
- **Relationship:** Multiple products sourced from one supplier
- **Foreign Key:** `product.supplier_id` → `suppliers.id`
- **Delete Rule:** SET NULL

### 5. Product → ProductVariant
- **Type:** One-to-Many
- **Relationship:** One product has multiple variants
- **Foreign Key:** `product_variant.product_id` → `products.id`
- **Delete Rule:** CASCADE (delete variants when product deleted)

### 6. ProductVariant → InventoryLevel
- **Type:** One-to-Many
- **Relationship:** One variant tracked at multiple locations
- **Foreign Key:** `inventory_level.product_variant_id` → `product_variants.id`
- **Delete Rule:** CASCADE
- **Constraint:** UNIQUE(product_variant_id, location_id)

### 7. StockLocation → InventoryLevel
- **Type:** One-to-Many
- **Relationship:** One location stores multiple variants
- **Foreign Key:** `inventory_level.location_id` → `stock_locations.id`
- **Delete Rule:** CASCADE

### 8. ProductVariant → InventoryMovement
- **Type:** One-to-Many
- **Relationship:** One variant has multiple movement records
- **Foreign Key:** `inventory_movement.product_variant_id` → `product_variants.id`
- **Delete Rule:** CASCADE

### 9. StockLocation → InventoryMovement (From/To)
- **Type:** One-to-Many (dual relationship)
- **Relationship:** Movements between locations
- **Foreign Keys:** 
  - `inventory_movement.from_location_id` → `stock_locations.id`
  - `inventory_movement.to_location_id` → `stock_locations.id`
- **Delete Rule:** SET NULL

### 10. User → InventoryMovement
- **Type:** One-to-Many
- **Relationship:** Track who created each movement
- **Foreign Key:** `inventory_movement.created_by_id` → `users.id`
- **Delete Rule:** SET NULL

### 11. StockLocation → StockAdjustment
- **Type:** One-to-Many
- **Relationship:** Adjustments per location
- **Foreign Key:** `stock_adjustment.location_id` → `stock_locations.id`
- **Delete Rule:** CASCADE

### 12. ProductVariant → StockAdjustment
- **Type:** One-to-Many
- **Relationship:** Adjustment history per variant
- **Foreign Key:** `stock_adjustment.product_variant_id` → `product_variants.id`
- **Delete Rule:** CASCADE

### 13. User → StockAdjustment (Adjusted By / Approved By)
- **Type:** One-to-Many (dual relationship)
- **Relationship:** Track adjustment and approval users
- **Foreign Keys:**
  - `stock_adjustment.adjusted_by_id` → `users.id`
  - `stock_adjustment.approved_by_id` → `users.id`
- **Delete Rule:** SET NULL (keep record even if user deleted)

### 14. ProductVariant → LowStockAlert
- **Type:** One-to-Many
- **Relationship:** Alert history per variant
- **Foreign Key:** `low_stock_alert.product_variant_id` → `product_variants.id`
- **Delete Rule:** CASCADE

### 15. StockLocation → LowStockAlert
- **Type:** One-to-Many
- **Relationship:** Alerts per location
- **Foreign Key:** `low_stock_alert.location_id` → `stock_locations.id`
- **Delete Rule:** CASCADE

### 16. User → LowStockAlert
- **Type:** One-to-Many
- **Relationship:** Track who resolved alerts
- **Foreign Key:** `low_stock_alert.resolved_by_id` → `users.id`
- **Delete Rule:** SET NULL

## Cardinality

```
Category     1 ────── N  Product
Brand        1 ────── N  Product
Supplier     1 ────── N  Product
Product      1 ────── N  ProductVariant
ProductVariant  1 ─── N  InventoryLevel (one per location)
StockLocation   1 ─── N  InventoryLevel
ProductVariant  1 ─── N  InventoryMovement
StockLocation   1 ─── N  InventoryMovement (from)
StockLocation   1 ─── N  InventoryMovement (to)
User           1 ──── N  InventoryMovement
StockLocation  1 ──── N  StockAdjustment
ProductVariant 1 ──── N  StockAdjustment
User           1 ──── N  StockAdjustment (adjusted_by)
User           1 ──── N  StockAdjustment (approved_by)
ProductVariant 1 ──── N  LowStockAlert
StockLocation  1 ──── N  LowStockAlert
User           1 ──── N  LowStockAlert (resolved_by)
```

## Data Flow

### Product Creation Flow
1. Create Category (optional)
2. Create Brand (optional)
3. Create Supplier (optional)
4. Create Product → links to Category, Brand, Supplier
5. Create ProductVariant(s) → links to Product

### Inventory Tracking Flow
1. Create StockLocation(s)
2. Create InventoryLevel for each ProductVariant at each Location
3. Record InventoryMovement when stock changes
4. System automatically updates InventoryLevel.quantity_available
5. System generates LowStockAlert when below reorder point

### Stock Adjustment Flow
1. User performs physical count
2. Create StockAdjustment with expected vs actual quantities
3. Status: pending → awaiting approval
4. Approver reviews and approves/rejects
5. If approved: create InventoryMovement (type: adjustment)
6. Update InventoryLevel accordingly

## Index Strategy

### Query Patterns Optimized

1. **Find products by category**
   - Index: `ix_products_category_active`

2. **Find products by brand**
   - Index: `ix_products_brand_active`

3. **Search variants by size/color**
   - Index: `ix_variants_size_color`

4. **Check stock at location**
   - Unique index: `ix_inventory_variant_location`

5. **View movement history**
   - Index: `ix_movements_variant_date`
   - Index: `ix_movements_type_date`

6. **Find active alerts**
   - Index: `ix_alerts_status_date`

7. **Lookup by SKU**
   - Unique indexes on Product.sku and ProductVariant.sku

8. **Lookup by barcode**
   - Unique index on ProductVariant.barcode
