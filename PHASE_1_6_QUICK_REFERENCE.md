# Phase 1.6 Quick Reference - Reporting API

## 📊 Summary
- **Status:** ✅ Complete (100%)
- **Report Endpoints:** 5 comprehensive reports
- **Test Coverage:** 25+ tests
- **Lines of Code:** ~1,500 lines

## 🌐 API Endpoints

### Base URL: `/api/v1/reports`

---

### 1. Inventory Summary Report
```bash
GET /api/v1/reports/inventory-summary
```

**Query Parameters:**
- `category_id` (optional) - Filter by category
- `location_id` (optional) - Filter by location
- `include_inactive` (optional, default: false) - Include inactive products

**Response Overview:**
- Total products, variants, quantity, stock value
- Low stock and out-of-stock counts
- Category-wise breakdown
- Location-wise breakdown

**Example:**
```bash
GET /api/v1/reports/inventory-summary?category_id=10&location_id=5
```

---

### 2. Stock Valuation Report
```bash
GET /api/v1/reports/stock-valuation
```

**Query Parameters:**
- `category_id` (optional)
- `location_id` (optional)
- `include_inactive` (optional, default: false)
- `limit` (optional, default: 1000, max: 10000)

**Response Overview:**
- Total cost value, selling value, potential profit
- Average profit margin percentage
- Per-product breakdown with margins

**Example:**
```bash
GET /api/v1/reports/stock-valuation?category_id=10&limit=50
```

---

### 3. Low Stock Alert Report
```bash
GET /api/v1/reports/low-stock
```

**Query Parameters:**
- `category_id` (optional)
- `location_id` (optional)
- `status` (optional) - 'critical', 'low', 'out_of_stock'

**Response Overview:**
- Critical, low, and out-of-stock item counts
- Shortage quantities
- Days until stockout estimates
- Reorder recommendations

**Status Levels:**
- **critical:** Quantity < 50% of reorder point
- **low:** Quantity <= reorder point
- **out_of_stock:** Quantity = 0

**Example:**
```bash
GET /api/v1/reports/low-stock?status=critical
```

---

### 4. Stock Movement Report
```bash
GET /api/v1/reports/stock-movement
```

**Query Parameters:**
- `start_date` (optional, default: 30 days ago) - Format: YYYY-MM-DD
- `end_date` (optional, default: today) - Format: YYYY-MM-DD
- `movement_type` (optional) - purchase, sale, adjustment, transfer, return
- `product_id` (optional)
- `location_id` (optional)

**Response Overview:**
- Total movements count
- Quantity in vs out
- Net change
- Movement summary by type
- Top 100 products by movement count

**Example:**
```bash
GET /api/v1/reports/stock-movement?start_date=2024-11-01&end_date=2024-11-30&movement_type=sale
```

---

### 5. Inventory Aging Report
```bash
GET /api/v1/reports/inventory-aging
```

**Query Parameters:**
- `category_id` (optional)
- `location_id` (optional)
- `min_age_days` (optional)
- `max_age_days` (optional)

**Response Overview:**
- Aging buckets (0-30, 31-90, 91-180, 180+ days)
- Dead stock count and value
- Per-product age and last movement date
- Status classification (fresh, aging, stale, dead_stock)

**Aging Classification:**
- **Fresh:** 0-30 days
- **Aging:** 31-90 days
- **Stale:** 91-180 days
- **Dead Stock:** 180+ days

**Example:**
```bash
GET /api/v1/reports/inventory-aging?min_age_days=90
```

---

## 📦 Response Structures

### Inventory Summary
```json
{
  "generated_at": "2025-12-14T10:00:00Z",
  "total_products": 150,
  "total_variants": 450,
  "total_quantity": 15000,
  "total_stock_value": "150000.00",
  "low_stock_count": 12,
  "out_of_stock_count": 3,
  "categories": [
    {
      "category_id": 1,
      "category_name": "T-Shirts",
      "total_products": 50,
      "total_variants": 150,
      "total_quantity": 5000,
      "total_value": "50000.00",
      "low_stock_items": 3,
      "out_of_stock_items": 1
    }
  ],
  "locations": [
    {
      "location_id": 1,
      "location_name": "Main Warehouse",
      "location_type": "warehouse",
      "total_quantity": 10000,
      "total_value": "100000.00",
      "unique_products": 120
    }
  ]
}
```

### Stock Valuation
```json
{
  "generated_at": "2025-12-14T10:00:00Z",
  "total_cost_value": "100000.00",
  "total_selling_value": "200000.00",
  "total_potential_profit": "100000.00",
  "average_profit_margin": 50.0,
  "total_items": 150,
  "products": [
    {
      "product_id": 1,
      "sku": "TSH-001",
      "name": "Classic T-Shirt",
      "category_name": "T-Shirts",
      "total_quantity": 100,
      "cost_price": "10.00",
      "selling_price": "20.00",
      "total_cost_value": "1000.00",
      "total_selling_value": "2000.00",
      "potential_profit": "1000.00",
      "profit_margin_percentage": 50.0
    }
  ]
}
```

### Low Stock Alert
```json
{
  "generated_at": "2025-12-14T10:00:00Z",
  "critical_items": 5,
  "low_stock_items": 12,
  "out_of_stock_items": 3,
  "total_shortage_value": "5000.00",
  "items": [
    {
      "product_id": 1,
      "sku": "TSH-001",
      "name": "Classic T-Shirt",
      "category_name": "T-Shirts",
      "location_name": "Main Warehouse",
      "current_quantity": 8,
      "reorder_point": 20,
      "reorder_quantity": 50,
      "shortage": 12,
      "days_until_stockout": 8,
      "status": "critical"
    }
  ]
}
```

### Stock Movement
```json
{
  "generated_at": "2025-12-14T10:00:00Z",
  "start_date": "2024-11-14",
  "end_date": "2024-12-14",
  "total_movements": 250,
  "total_quantity_in": 5000,
  "total_quantity_out": 3000,
  "net_change": 2000,
  "movement_summary": [
    {
      "movement_type": "purchase",
      "total_movements": 120,
      "total_quantity": 4000,
      "affected_products": 80
    },
    {
      "movement_type": "sale",
      "total_movements": 130,
      "total_quantity": 3000,
      "affected_products": 75
    }
  ],
  "product_details": [
    {
      "product_id": 1,
      "sku": "TSH-001",
      "name": "Classic T-Shirt",
      "total_in": 100,
      "total_out": 80,
      "net_change": 20,
      "movements_count": 15
    }
  ]
}
```

### Inventory Aging
```json
{
  "generated_at": "2025-12-14T10:00:00Z",
  "total_products": 120,
  "total_quantity": 10000,
  "total_value": "100000.00",
  "aging_buckets": [
    {
      "bucket_name": "0-30 days (Fresh)",
      "min_days": 0,
      "max_days": 30,
      "product_count": 50,
      "total_quantity": 5000,
      "total_value": "50000.00"
    },
    {
      "bucket_name": "180+ days (Dead Stock)",
      "min_days": 181,
      "max_days": null,
      "product_count": 10,
      "total_quantity": 500,
      "total_value": "5000.00"
    }
  ],
  "aged_products": [
    {
      "product_id": 1,
      "sku": "TSH-001",
      "name": "Classic T-Shirt",
      "category_name": "T-Shirts",
      "quantity": 50,
      "value": "500.00",
      "age_days": 200,
      "last_movement_date": "2024-05-28T10:00:00Z",
      "status": "dead_stock"
    }
  ],
  "dead_stock_count": 10,
  "dead_stock_value": "5000.00"
}
```

---

## 🎯 Common Use Cases

### Daily Operations Dashboard
```bash
# Get overall inventory health
GET /api/v1/reports/inventory-summary

# Check for items needing reorder
GET /api/v1/reports/low-stock?status=critical
```

### Financial Reporting
```bash
# Calculate inventory value for balance sheet
GET /api/v1/reports/stock-valuation

# Get stock value by category
GET /api/v1/reports/stock-valuation?category_id=10
```

### Purchase Planning
```bash
# Identify all low stock items
GET /api/v1/reports/low-stock

# Get low stock items by category for targeted purchasing
GET /api/v1/reports/low-stock?category_id=10
```

### Sales Analysis
```bash
# Get last 7 days movement
GET /api/v1/reports/stock-movement?start_date=2024-12-07&end_date=2024-12-14

# Analyze sales only
GET /api/v1/reports/stock-movement?movement_type=sale
```

### Inventory Optimization
```bash
# Identify dead stock for liquidation
GET /api/v1/reports/inventory-aging

# Get stale items (91-180 days) for promotions
GET /api/v1/reports/inventory-aging?min_age_days=91&max_age_days=180
```

---

## 📁 File Locations

```
backend/
├── app/
│   ├── schemas/reports.py          # 13 schemas (9 reports + 4 filters)
│   ├── repositories/reports.py     # ReportRepository with 5 methods
│   ├── api/v1/reports.py           # 5 REST endpoints
│   └── tests/test_reports_api.py   # 25+ tests with fixtures
```

---

## 🔍 Filter Combinations

### Multi-dimensional Filtering
```bash
# Category + Location
GET /api/v1/reports/inventory-summary?category_id=10&location_id=5

# Date Range + Movement Type + Product
GET /api/v1/reports/stock-movement?start_date=2024-12-01&end_date=2024-12-14&movement_type=sale&product_id=100

# Age Range + Category
GET /api/v1/reports/inventory-aging?min_age_days=30&max_age_days=90&category_id=10
```

---

## 📄 Documentation
- **Full Report:** `PHASE_1_6_COMPLETION_REPORT.md`
- **API Docs:** `http://localhost:8000/docs`
- **Tasks:** `TASKS.md` (Phase 1 marked 100% complete)

---

## 🎉 Phase 1 Complete!

**Total Phase 1 Deliverables:**
- 124+ REST API endpoints
- 6 major modules completed
- 10,000+ lines of production code
- Comprehensive test coverage
- Full documentation

**Next:** Phase 2 - Multi-Channel Sales System 🚀
