# Phase 3.2 Quick Reference: B2C CRM API

**Module:** Retail Customer Management (B2C CRM)  
**Base URL:** `/api/v1/retail-customers`  
**Authentication:** Required (JWT Bearer token)

---

## 📋 Table of Contents

1. [Customer Management](#customer-management)
2. [Loyalty Program](#loyalty-program)
3. [Customer Preferences](#customer-preferences)
4. [RFM Analysis](#rfm-analysis)
5. [CLV Calculation](#clv-calculation)
6. [Bulk Operations](#bulk-operations)
7. [Analytics](#analytics)

---

## Customer Management

### Register Customer (Public)
```http
POST /api/v1/retail-customers/register
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+919876543210",
  "password": "SecurePass123",
  "date_of_birth": "1990-01-15",
  "gender": "Male",
  "city": "Mumbai",
  "state": "Maharashtra",
  "country": "India",
  "email_marketing_consent": true,
  "sms_marketing_consent": true
}
```

### Create Customer (Admin)
```http
POST /api/v1/retail-customers/
Authorization: Bearer {token}
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@example.com",
  "phone": "+918765432109",
  "city": "Delhi",
  "user_id": "uuid-optional"
}
```

### Get Customer
```http
# By ID
GET /api/v1/retail-customers/{customer_id}
Authorization: Bearer {token}

# By Customer Number
GET /api/v1/retail-customers/number/CUST-20251217-0001
Authorization: Bearer {token}

# By Email
GET /api/v1/retail-customers/email/john@example.com
Authorization: Bearer {token}
```

### List Customers
```http
GET /api/v1/retail-customers/?skip=0&limit=100&is_active=true&loyalty_tier=silver
Authorization: Bearer {token}
```

### Advanced Search
```http
POST /api/v1/retail-customers/search?skip=0&limit=100
Authorization: Bearer {token}
Content-Type: application/json

{
  "search": "john",
  "is_active": true,
  "loyalty_tier": "silver",
  "rfm_segment": "Loyal",
  "city": "Mumbai",
  "min_total_spent": 10000,
  "min_orders": 5,
  "registered_after": "2025-01-01T00:00:00Z",
  "has_email_consent": true
}
```

### Update Customer
```http
PUT /api/v1/retail-customers/{customer_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe Updated",
  "email": "john.new@example.com",
  "phone": "+919876543210",
  "address_line1": "123 Main St",
  "city": "Mumbai",
  "state": "Maharashtra",
  "postal_code": "400001",
  "email_marketing_consent": false
}
```

### Verify Email/Phone
```http
POST /api/v1/retail-customers/{customer_id}/verify-email
Content-Type: application/json

{
  "verification_type": "email",
  "verification_code": "123456"
}

POST /api/v1/retail-customers/{customer_id}/verify-phone
Content-Type: application/json

{
  "verification_type": "phone",
  "verification_code": "654321"
}
```

### Deactivate/Reactivate
```http
POST /api/v1/retail-customers/{customer_id}/deactivate?reason=Customer%20request
Authorization: Bearer {token}

POST /api/v1/retail-customers/{customer_id}/reactivate
Authorization: Bearer {token}
```

---

## Loyalty Program

### Get Loyalty Balance
```http
GET /api/v1/retail-customers/{customer_id}/loyalty/balance
Authorization: Bearer {token}

Response:
{
  "customer_id": "uuid",
  "current_balance": 1500,
  "lifetime_points": 3500,
  "points_expiring_soon": 200,
  "points_expiring_date": "2025-12-31T23:59:59Z",
  "tier": "silver"
}
```

### Get Transaction History
```http
GET /api/v1/retail-customers/{customer_id}/loyalty/transactions?transaction_type=EARNED&skip=0&limit=50
Authorization: Bearer {token}
```

### Earn Points
```http
POST /api/v1/retail-customers/loyalty/earn
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_id": "uuid",
  "points": 200,
  "description": "Purchase reward - Order #12345",
  "order_id": "order-uuid",
  "expiry_days": 365
}
```

### Redeem Points
```http
POST /api/v1/retail-customers/loyalty/redeem
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_id": "uuid",
  "points": 500,
  "description": "Discount redemption",
  "order_id": "order-uuid"
}
```

### Adjust Points (Admin)
```http
POST /api/v1/retail-customers/loyalty/adjust
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_id": "uuid",
  "points": 100,  # Positive or negative
  "reason": "Compensation for delayed delivery"
}
```

### Expire Old Points
```http
POST /api/v1/retail-customers/loyalty/expire-points?customer_id=uuid
Authorization: Bearer {token}

# Omit customer_id to expire for all customers
POST /api/v1/retail-customers/loyalty/expire-points
Authorization: Bearer {token}
```

### Update Loyalty Tier
```http
# Manual tier update (admin)
PUT /api/v1/retail-customers/loyalty/tier
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_id": "uuid",
  "new_tier": "gold",
  "reason": "Promotional upgrade",
  "tier_expiry_date": "2026-12-31"
}

# Auto-calculate tier based on points
POST /api/v1/retail-customers/{customer_id}/loyalty/auto-tier
Authorization: Bearer {token}
```

---

## Customer Preferences

### Get Preferences
```http
# All preferences
GET /api/v1/retail-customers/{customer_id}/preferences
Authorization: Bearer {token}

# By type
GET /api/v1/retail-customers/{customer_id}/preferences?preference_type=communication
Authorization: Bearer {token}
```

### Create/Update Preference
```http
POST /api/v1/retail-customers/{customer_id}/preferences
Authorization: Bearer {token}
Content-Type: application/json

{
  "preference_type": "communication",
  "preference_key": "email_frequency",
  "preference_value": "weekly"
}

PUT /api/v1/retail-customers/{customer_id}/preferences/{preference_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "preference_value": "daily"
}
```

### Bulk Update Preferences
```http
POST /api/v1/retail-customers/{customer_id}/preferences/bulk
Authorization: Bearer {token}
Content-Type: application/json

{
  "preferences": [
    {
      "preference_type": "communication",
      "preference_key": "email_frequency",
      "preference_value": "weekly"
    },
    {
      "preference_type": "shopping",
      "preference_key": "favorite_category",
      "preference_value": "shirts"
    },
    {
      "preference_type": "payment",
      "preference_key": "preferred_method",
      "preference_value": "card"
    }
  ]
}
```

### Delete Preference
```http
DELETE /api/v1/retail-customers/{customer_id}/preferences/{preference_id}
Authorization: Bearer {token}
```

---

## RFM Analysis

### Calculate RFM Scores
```http
POST /api/v1/retail-customers/analytics/rfm/calculate
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_ids": null,  # All customers
  "recalculate": false   # Skip recently calculated
}

# Or for specific customers
{
  "customer_ids": ["uuid1", "uuid2", "uuid3"],
  "recalculate": true
}

Response:
{
  "message": "RFM scores calculated for 150 customers",
  "customers_updated": 150
}
```

### Get Customer RFM
```http
GET /api/v1/retail-customers/{customer_id}/analytics/rfm
Authorization: Bearer {token}

Response:
{
  "customer_id": "uuid",
  "customer_number": "CUST-20251217-0001",
  "customer_name": "John Doe",
  "recency_score": 5,
  "frequency_score": 4,
  "monetary_score": 4,
  "rfm_segment": "Loyal",
  "total_orders": 15,
  "total_spent": 45000,
  "last_order_date": "2025-12-15T10:30:00Z",
  "days_since_last_order": 2,
  "calculated_at": "2025-12-17T08:00:00Z"
}
```

### Get Segment Distribution
```http
GET /api/v1/retail-customers/analytics/rfm/distribution
Authorization: Bearer {token}

Response:
{
  "total_customers_analyzed": 500,
  "segment_distribution": [
    {
      "segment": "Champion",
      "count": 25,
      "percentage": 5.0,
      "total_revenue": 500000,
      "average_order_value": 4000
    },
    {
      "segment": "Loyal",
      "count": 75,
      "percentage": 15.0,
      "total_revenue": 900000,
      "average_order_value": 2400
    }
    // ... more segments
  ],
  "champion_count": 25,
  "loyal_count": 75,
  "potential_loyalist_count": 50,
  "new_customers_count": 40,
  "promising_count": 60,
  "need_attention_count": 45,
  "about_to_sleep_count": 35,
  "at_risk_count": 30,
  "cannot_lose_count": 15,
  "hibernating_count": 80,
  "lost_count": 45,
  "analysis_date": "2025-12-17T08:00:00Z"
}
```

**RFM Segments Explained:**
- **Champion** (R=5, F=5, M=5): Best customers, buy frequently, spend a lot
- **Loyal** (R=4-5, F=4-5, M=3-5): Consistent buyers
- **Potential Loyalist** (R=4-5, F=3, M=3-4): Promising, engage more
- **New Customer** (R=5, F=1-2, M=1-2): Just joined, nurture
- **Promising** (R=4-5, F=2-3, M=2-3): Recent buyers with potential
- **Need Attention** (R=3, F=3-4, M=3-4): Declining engagement
- **About to Sleep** (R=2-3, F=2-3, M=2-3): Becoming inactive
- **At Risk** (R=1-2, F=3-4, M=3-5): Losing valuable customers
- **Can't Lose Them** (R=1-2, F=5, M=5): High-value but inactive
- **Hibernating** (R=1-2, F=2-3, M=1-2): Long-time inactive
- **Lost** (R=1, F=1, M=1-2): Churned customers

---

## CLV Calculation

### Calculate CLV
```http
POST /api/v1/retail-customers/analytics/clv/calculate
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_ids": null,      # All customers
  "prediction_months": 12,   # 12-month prediction
  "recalculate": false
}

Response:
{
  "message": "CLV calculated for 200 customers",
  "customers_updated": 200,
  "prediction_months": 12
}
```

### Get Customer CLV
```http
GET /api/v1/retail-customers/{customer_id}/analytics/clv
Authorization: Bearer {token}

Response:
{
  "customer_id": "uuid",
  "customer_number": "CUST-20251217-0001",
  "customer_name": "John Doe",
  "clv": 48000.00,
  "predicted_orders": 12,
  "predicted_revenue": 48000.00,
  "average_order_value": 4000.00,
  "purchase_frequency": 1.2,  # orders per month
  "customer_lifespan_months": 12,
  "calculated_at": "2025-12-17T08:00:00Z"
}
```

### Get CLV Analysis
```http
GET /api/v1/retail-customers/analytics/clv/analysis?limit=100
Authorization: Bearer {token}

Response:
{
  "total_customers_analyzed": 500,
  "total_clv": 15000000.00,
  "average_clv": 30000.00,
  "median_clv": 22000.00,
  "distribution": [
    {
      "range_label": "0-1000",
      "min_value": 0,
      "max_value": 1000,
      "count": 50,
      "percentage": 10.0,
      "total_clv": 35000.00
    },
    {
      "range_label": "1000-5000",
      "min_value": 1000,
      "max_value": 5000,
      "count": 150,
      "percentage": 30.0,
      "total_clv": 450000.00
    }
    // ... more ranges
  ],
  "top_customers": [
    {
      "customer_id": "uuid",
      "customer_number": "CUST-20251217-0001",
      "customer_name": "Top Customer",
      "clv": 150000.00,
      // ... more fields
    }
    // ... top 10 customers
  ],
  "analysis_date": "2025-12-17T08:00:00Z"
}
```

---

## Bulk Operations

### Bulk Status Update
```http
POST /api/v1/retail-customers/bulk/status
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_ids": ["uuid1", "uuid2", "uuid3"],
  "is_active": false,
  "reason": "Bulk deactivation for maintenance"
}

Response:
{
  "message": "Updated status for 3 customers",
  "customers_updated": 3
}
```

### Bulk Tier Update
```http
POST /api/v1/retail-customers/bulk/tier
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_ids": ["uuid1", "uuid2", "uuid3"],
  "new_tier": "gold",
  "tier_expiry_date": "2026-12-31"
}

Response:
{
  "message": "Updated tier for 3 customers",
  "customers_updated": 3
}
```

---

## Analytics

### Loyalty Program Metrics
```http
GET /api/v1/retail-customers/analytics/loyalty/metrics
Authorization: Bearer {token}

Response:
{
  "total_members": 5000,
  "active_members": 4500,
  "bronze_members": 3000,
  "silver_members": 1200,
  "gold_members": 250,
  "platinum_members": 50,
  "total_points_issued": 5000000,
  "total_points_redeemed": 1500000,
  "total_points_expired": 200000,
  "current_outstanding_points": 3300000,
  "redemption_rate": 30.0
}
```

### Customer Analytics Summary
```http
GET /api/v1/retail-customers/{customer_id}/analytics/summary
Authorization: Bearer {token}

Response:
{
  "customer_id": "uuid",
  "customer_number": "CUST-20251217-0001",
  "customer_name": "John Doe",
  "email": "john@example.com",
  "purchase_summary": {
    "customer_id": "uuid",
    "total_orders": 15,
    "total_spent": 60000.00,
    "average_order_value": 4000.00,
    "first_order_date": "2024-01-15T10:00:00Z",
    "last_order_date": "2025-12-15T14:30:00Z",
    "favorite_category": "Shirts",
    "favorite_brand": "Brand A",
    "most_purchased_product": "Blue Oxford Shirt",
    "purchase_frequency_days": 30
  },
  "loyalty_tier": "silver",
  "loyalty_points": 1500,
  "rfm_recency_score": 5,
  "rfm_frequency_score": 4,
  "rfm_monetary_score": 4,
  "rfm_segment": "Loyal",
  "clv": 48000.00,
  "email_open_rate": 45.5,
  "email_click_rate": 12.3,
  "last_activity_at": "2025-12-15T14:30:00Z"
}
```

---

## Common Filters & Parameters

### Search Filters
- `search`: Text search (name, email, phone, customer number)
- `is_active`: Boolean (active/inactive)
- `loyalty_tier`: bronze, silver, gold, platinum
- `rfm_segment`: Champion, Loyal, At Risk, etc.
- `city`, `state`, `country`: Location filters
- `min_total_spent`, `max_total_spent`: Spending range
- `min_orders`, `max_orders`: Order count range
- `registered_after`, `registered_before`: Date range
- `last_order_after`, `last_order_before`: Last order date
- `has_email_consent`, `has_sms_consent`: Marketing consent

### Pagination
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)

---

## Error Responses

```json
{
  "detail": "Customer not found"
}

{
  "detail": "Email already registered"
}

{
  "detail": "Insufficient loyalty points"
}

{
  "detail": "RFM scores not calculated for this customer"
}
```

---

## Status Codes

- `200 OK`: Successful GET/PUT request
- `201 Created`: Successful POST (creation)
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error

---

## Tips & Best Practices

### Loyalty Points
1. Always set expiry for earned points (default: 365 days)
2. Check balance before redemption
3. Regularly run point expiration (automated job recommended)
4. Monitor expiring points for customer retention campaigns

### RFM Analysis
1. Calculate monthly for all customers
2. Use segments for targeted marketing:
   - Champions/Loyal: VIP programs, early access
   - At Risk/Can't Lose: Win-back campaigns
   - New Customers: Onboarding sequences
3. Track segment migration over time

### CLV
1. Calculate quarterly or when purchase patterns change
2. Use for customer acquisition cost (CAC) analysis
3. Focus marketing on high-CLV segments
4. Predict revenue for business planning

### Performance
1. Use pagination for large lists
2. Bulk operations for multiple updates
3. Filter by city/segment to reduce dataset size
4. Cache analytics results client-side

---

**Reference Version:** 1.0  
**Last Updated:** December 17, 2025  
**Module:** Phase 3.2 - B2C CRM
