# Phase 1.5 Quick Reference

## 📊 Summary
- **Status:** ✅ Complete (100%)
- **API Endpoints:** 48 new endpoints
- **Database Models:** 8 new models
- **Test Coverage:** 80+ tests
- **Lines of Code:** ~2,745 lines

## 🌐 API Endpoints

### Base URL: `/api/v1/garment`

### Size Charts (`/size-charts`)
- `POST /` - Create size chart
- `GET /` - List (filter: category, region, active_only)
- `GET /search?q={query}` - Search
- `GET /{id}` - Get by ID
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete
- `GET /by-category/{category}` - Get by category

### Colors (`/colors`)
- `POST /` - Create color
- `GET /` - List (filter: active_only)
- `GET /search?q={query}` - Search
- `GET /{id}` - Get by ID
- `GET /by-code/{code}` - Get by code
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete
- `GET /active` - Get active colors only

### Fabrics (`/fabrics`)
- `POST /` - Create fabric
- `GET /` - List (filter: active_only)
- `GET /search?q={query}` - Search
- `GET /{id}` - Get by ID
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete
- `GET /active` - Get active fabrics only

### Styles (`/styles`)
- `POST /` - Create style
- `GET /` - List (filter: active_only)
- `GET /{id}` - Get by ID
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete

### Collections (`/collections`)
- `POST /` - Create collection
- `GET /` - List (filter: active_only)
- `GET /{id}` - Get by ID
- `GET /by-code/{code}` - Get by code
- `GET /by-season?season={season}&year={year}` - Get by season
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete

### Measurements (`/measurements`)
- `POST /` - Create measurement
- `GET /` - List
- `GET /{id}` - Get by ID
- `GET /by-product/{product_id}` - Get by product
- `GET /by-product/{product_id}/size/{size}` - Get by product and size
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete

### Images (`/images`)
- `POST /` - Create image
- `POST /bulk` - Bulk create images
- `GET /` - List
- `GET /{id}` - Get by ID
- `GET /by-product/{product_id}` - Get by product
- `GET /primary/{product_id}` - Get primary image
- `PATCH /{id}/set-primary` - Set as primary
- `PUT /{id}` - Update
- `DELETE /{id}` - Delete

## 📦 Models

### SizeChart
- Fields: name, category, region, sizes (JSON), description, is_active
- Enums: SizeCategory, Region

### Color
- Fields: code, name, hex_code, pantone_code, description, is_active
- Validation: Hex code pattern `^#[0-9A-Fa-f]{6}$`

### Fabric
- Fields: code, name, composition, weight_gsm, properties (JSON), care_instructions, is_active

### Style
- Fields: code, name, description, is_active

### Collection
- Fields: code, name, season, year, description, is_active
- Enum: Season

### MeasurementSpec
- Fields: product_id, size, chest, waist, hips, length, sleeve_length, shoulder_width, additional_measurements (JSON)

### GarmentImage
- Fields: product_id, color_id, image_url, alt_text, is_primary, display_order

### ProductFabric
- Fields: product_id, fabric_id, percentage

## 🔤 Enums

```python
SizeCategory = ["tops", "bottoms", "dresses", "outerwear", "underwear", "accessories"]
Region = ["us", "eu", "uk", "asia", "international"]
Season = ["spring", "summer", "fall", "winter", "all_season"]
```

## 🧪 Example Requests

### Create Color
```bash
POST /api/v1/garment/colors/
{
  "code": "NVY",
  "name": "Navy Blue",
  "hex_code": "#000080",
  "pantone_code": "19-4028 TCX",
  "is_active": true
}
```

### Create Size Chart
```bash
POST /api/v1/garment/size-charts/
{
  "name": "Men's Shirts",
  "category": "tops",
  "region": "us",
  "sizes": {
    "S": {"chest": 36, "waist": 32, "length": 27},
    "M": {"chest": 40, "waist": 34, "length": 28},
    "L": {"chest": 44, "waist": 36, "length": 29}
  }
}
```

### Bulk Create Images
```bash
POST /api/v1/garment/images/bulk
{
  "product_id": 123,
  "images": [
    {
      "image_url": "https://cdn.example.com/front.jpg",
      "alt_text": "Front view",
      "is_primary": true,
      "display_order": 1
    },
    {
      "image_url": "https://cdn.example.com/back.jpg",
      "alt_text": "Back view",
      "display_order": 2
    }
  ]
}
```

## 📁 File Locations

```
backend/
├── app/
│   ├── models/garment.py                   # 8 models
│   ├── schemas/garment.py                  # All schemas
│   ├── repositories/garment.py             # 7 repositories
│   └── api/v1/garment/
│       ├── __init__.py                     # Router aggregation
│       ├── size_charts.py                  # 7 endpoints
│       ├── attributes.py                   # 26 endpoints
│       └── measurements_images.py          # 15 endpoints
├── tests/
│   ├── test_garment_repository.py          # 30 tests
│   └── test_garment_api.py                 # 50 tests
└── alembic/versions/
    └── g12345678abc_add_garment_specific_models.py
```

## 🎯 Use Case: Complete Product Setup

```python
# 1. Create product (core inventory)
product = create_product(...)

# 2. Add fabric composition
add_fabric(product.id, fabric_id=cotton.id, percentage=60.0)
add_fabric(product.id, fabric_id=poly.id, percentage=40.0)

# 3. Add measurements per size
add_measurement(product.id, size="S", chest=36, length=27)
add_measurement(product.id, size="M", chest=40, length=28)
add_measurement(product.id, size="L", chest=44, length=29)

# 4. Add images
bulk_create_images(product.id, [
  {"url": "front.jpg", "is_primary": True},
  {"url": "back.jpg", "color_id": black.id}
])
```

## 🔍 Search & Filter Examples

```bash
# Search colors
GET /api/v1/garment/colors/search?q=blue

# Filter by category and region
GET /api/v1/garment/size-charts/?category=tops&region=us

# Get active fabrics only
GET /api/v1/garment/fabrics/?active_only=true

# Get collections by season
GET /api/v1/garment/collections/by-season?season=spring&year=2024

# Get all measurements for a product
GET /api/v1/garment/measurements/by-product/123
```

## 📄 Documentation
- **Full Report:** `PHASE_1_5_COMPLETION_REPORT.md`
- **API Docs:** `http://localhost:8000/docs`
- **Tasks:** `TASKS.md` (Phase 1.5 marked complete)
