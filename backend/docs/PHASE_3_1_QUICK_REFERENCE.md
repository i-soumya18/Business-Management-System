# Phase 3.1: B2B CRM Quick Reference Guide

**Date:** December 15, 2025  
**Version:** 1.0  
**Status:** Production Ready

---

## 🚀 Quick Start

### API Base URL
```
http://localhost:8000/api/v1/crm
```

### Authentication
All endpoints require Bearer token authentication:
```bash
Authorization: Bearer <your_jwt_token>
```

---

## 📋 Lead Management

### Create Lead
```http
POST /crm/leads
```
```json
{
  "company_name": "Tech Solutions Ltd",
  "industry": "Technology",
  "company_size": "50-100",
  "website": "https://techsolutions.com",
  "contact_person": "John Doe",
  "title_position": "Purchasing Manager",
  "email": "john@techsolutions.com",
  "phone": "+911234567890",
  "city": "Mumbai",
  "state": "Maharashtra",
  "country": "India",
  "source": "website",
  "priority": "high",
  "estimated_deal_value": 50000.00,
  "requirements": "Looking for bulk garments for corporate uniforms"
}
```

**Response:** Lead with auto-generated `lead_number` (LEAD-YYYYMMDD-XXXX)

### List Leads (with filters)
```http
GET /crm/leads?page=1&page_size=50&status=new&search=Tech&assigned_to_id=<user_id>
```

**Filters Available:**
- `status`: new, contacted, qualified, converted, lost
- `source`: website, referral, phone, email, trade_show, etc.
- `priority`: low, medium, high, urgent
- `assigned_to_id`: Filter by assigned user
- `is_qualified`: true/false
- `search`: Search in company name, contact person, email, lead number

### Qualify Lead
```http
POST /crm/leads/{lead_id}/qualify
```
```json
{
  "qualification_score": 85,
  "is_qualified": true,
  "notes": "Strong prospect - budget confirmed"
}
```

### Convert Lead to Customer
```http
POST /crm/leads/{lead_id}/convert
```
```json
{
  "customer_id": "<wholesale_customer_id>",
  "notes": "First order placed - 500 units"
}
```

### Get Today's Follow-ups
```http
GET /crm/leads/follow-ups/today
```

### Get Lead Analytics
```http
GET /crm/leads/analytics/summary?start_date=2025-01-01&end_date=2025-12-31
```

---

## 💼 Opportunity Management

### Create Opportunity
```http
POST /crm/opportunities
```
```json
{
  "name": "Q4 Winter Collection Order",
  "description": "Bulk order for winter garments",
  "customer_id": "<customer_id>",
  "owner_id": "<user_id>",
  "lead_id": "<lead_id>",
  "estimated_value": 150000.00,
  "probability": 70,
  "expected_close_date": "2025-12-31T00:00:00Z",
  "stage": "proposal",
  "products_interested": {
    "categories": ["Jackets", "Sweaters"],
    "quantity": 500
  }
}
```

**Response:** Opportunity with auto-generated `opportunity_number` (OPP-YYYYMMDD-XXXX) and calculated `expected_revenue`

### Opportunity Stages
```
prospecting → qualification → needs_analysis → 
proposal → negotiation → closed_won / closed_lost
```

### Update Opportunity
```http
PUT /crm/opportunities/{opportunity_id}
```
```json
{
  "stage": "negotiation",
  "probability": 85,
  "next_step": "Send final proposal with pricing",
  "next_step_date": "2025-12-20T00:00:00Z"
}
```

### Close Opportunity (Won)
```http
POST /crm/opportunities/{opportunity_id}/close
```
```json
{
  "stage": "closed_won",
  "actual_close_date": "2025-12-15T10:30:00Z",
  "notes": "Deal closed - PO received"
}
```

### Close Opportunity (Lost)
```http
POST /crm/opportunities/{opportunity_id}/close
```
```json
{
  "stage": "closed_lost",
  "actual_close_date": "2025-12-15T10:30:00Z",
  "loss_reason": "Competitor had lower pricing",
  "notes": "Customer chose competitor"
}
```

### Get Pipeline Statistics
```http
GET /crm/opportunities/pipeline/stats?owner_id=<user_id>
```

**Returns:**
- Total opportunities count
- Total pipeline value
- Weighted pipeline value (sum of value × probability)
- Breakdown by stage

---

## 💬 Communication Management

### Log Communication
```http
POST /crm/communications
```
```json
{
  "customer_id": "<customer_id>",
  "our_representative_id": "<user_id>",
  "type": "phone",
  "direction": "outbound",
  "subject": "Follow-up on bulk order inquiry",
  "content": "Discussed winter collection requirements. Customer interested in 500 units. Needs detailed quotation.",
  "contact_person": "John Doe",
  "duration_minutes": 15,
  "requires_follow_up": true,
  "follow_up_date": "2025-12-20T10:00:00Z"
}
```

### Communication Types
- `phone` - Phone calls
- `email` - Email correspondence
- `meeting` - In-person meetings
- `video_call` - Video conferences
- `chat` - Chat messages
- `sms` - SMS messages
- `visit` - Site visits
- `other` - Other types

### Direction
- `inbound` - Customer initiated
- `outbound` - Sales team initiated

### Get Customer Communication History
```http
GET /crm/communications/customer/{customer_id}?page=1&page_size=50
```

### Get Lead Communication History
```http
GET /crm/communications/lead/{lead_id}?page=1&page_size=50
```

### Get Opportunity Communication History
```http
GET /crm/communications/opportunity/{opportunity_id}?page=1&page_size=50
```

### Get Pending Follow-ups
```http
GET /crm/communications/follow-ups/pending?representative_id=<user_id>
```

### Mark Follow-up Complete
```http
POST /crm/communications/{communication_id}/complete-follow-up
```

---

## 👥 Customer Segmentation

### Create Segment
```http
POST /crm/segments
```
```json
{
  "name": "High Value Customers",
  "description": "Customers with annual spend > 500K",
  "code": "HVC",
  "criteria": {
    "min_annual_spend": 500000,
    "order_frequency": "monthly",
    "credit_rating": "excellent"
  },
  "is_active": true,
  "priority": 1,
  "benefits": {
    "discount_tier": "Platinum",
    "payment_terms": "Net 60",
    "dedicated_account_manager": true
  }
}
```

### List Segments
```http
GET /crm/segments?page=1&page_size=50&is_active=true&search=High
```

### Assign Customers to Segment (Bulk)
```http
POST /crm/segments/{segment_id}/assign-customers
```
```json
{
  "customer_ids": [
    "<customer_id_1>",
    "<customer_id_2>",
    "<customer_id_3>"
  ],
  "segment_id": "<segment_id>"
}
```

### Remove Customers from Segment (Bulk)
```http
POST /crm/segments/{segment_id}/remove-customers
```
```json
[
  "<customer_id_1>",
  "<customer_id_2>"
]
```

---

## 📊 Common Workflows

### 1. Lead to Customer Journey
```
1. Create Lead (POST /crm/leads)
2. Log initial communication (POST /crm/communications)
3. Qualify lead (POST /crm/leads/{id}/qualify)
4. Create opportunity (POST /crm/opportunities)
5. Log follow-up communications
6. Update opportunity stage as it progresses
7. Close opportunity as won (POST /crm/opportunities/{id}/close)
8. Convert lead to customer (POST /crm/leads/{id}/convert)
```

### 2. Sales Pipeline Management
```
1. Create opportunities for qualified leads
2. Update probability as negotiations progress
3. Track next steps and follow-up dates
4. Log all customer communications
5. Monitor pipeline stats (GET /crm/opportunities/pipeline/stats)
6. Close opportunities (won/lost) with proper documentation
```

### 3. Customer Relationship Tracking
```
1. Log every customer interaction (calls, emails, meetings)
2. Set follow-up reminders
3. Track follow-up completion
4. Review communication history
5. Analyze customer engagement patterns
```

### 4. Customer Segmentation Strategy
```
1. Define segment criteria (spend, frequency, etc.)
2. Create segments (POST /crm/segments)
3. Bulk assign customers based on criteria
4. Target segments with specific campaigns
5. Monitor segment performance
6. Adjust segment criteria as needed
```

---

## 🔍 Search & Filtering

### Lead Search
```http
GET /crm/leads?search=tech&status=qualified&priority=high&page=1&page_size=20
```

### Opportunity Search
```http
GET /crm/opportunities?search=winter&stage=negotiation&min_value=50000&max_value=200000
```

### Segment Search
```http
GET /crm/segments?search=premium&is_active=true
```

---

## 📈 Analytics Endpoints

### Lead Analytics
```http
GET /crm/leads/analytics/summary
```
Returns:
- Total leads count
- Breakdown by status
- Breakdown by source
- Conversion rate
- Average time to convert

### Pipeline Statistics
```http
GET /crm/opportunities/pipeline/stats
```
Returns:
- Total opportunities
- Total pipeline value
- Weighted pipeline value
- Breakdown by stage
- Win rate

---

## 🔢 Auto-Generated Numbers

### Lead Numbers
- Format: `LEAD-YYYYMMDD-XXXX`
- Example: `LEAD-20251215-0001`
- Sequential per day

### Opportunity Numbers
- Format: `OPP-YYYYMMDD-XXXX`
- Example: `OPP-20251215-0001`
- Sequential per day

---

## ⚠️ Important Notes

### Lead Management
- Email must be unique across all leads
- Lead status automatically changes on conversion
- Follow-up dates trigger reminder lists
- Qualification score is 0-100

### Opportunity Management
- Expected revenue = estimated_value × (probability / 100)
- Expected revenue recalculates on value/probability changes
- Closed opportunities cannot be updated
- Loss reason required when closing as lost
- Probability must be 0-100

### Communications
- At least one entity (customer, lead, or opportunity) required
- Follow-up date triggers pending follow-up list
- Duration in minutes (optional)
- Attachments stored as JSON

### Segments
- Segment code must be unique
- Criteria stored as flexible JSON
- Customer count automatically maintained
- Bulk operations for efficiency

---

## 🛠️ Data Models

### Lead
```
- Auto-generated lead_number
- Company & contact information
- Status workflow tracking
- Qualification scoring
- Assignment to sales rep
- Follow-up management
- Conversion tracking
```

### Sales Opportunity
```
- Auto-generated opportunity_number
- Linked to customer (required)
- Linked to lead (optional)
- Value & probability tracking
- Expected revenue calculation
- Pipeline stage management
- Next step planning
- Win/loss tracking
```

### Customer Communication
```
- Multi-entity linking (customer/lead/opportunity)
- Type & direction tracking
- Duration tracking
- Follow-up management
- Representative assignment
- Flexible attachments
```

### Customer Segment
```
- Flexible criteria (JSON)
- Active/inactive status
- Priority ordering
- Benefits definition
- Customer count tracking
- Many-to-many customer relationships
```

---

## 🔐 Security

- All endpoints require authentication
- Bearer token in Authorization header
- User context available via current_user
- Access control ready for implementation

---

## 📞 Support & Documentation

- **Full Documentation:** PHASE_3_1_COMPLETION_REPORT.md
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Test Suite:** `/backend/tests/test_crm.py` (40+ test cases)

---

**Last Updated:** December 15, 2025  
**Version:** 1.0  
**Status:** ✅ Production Ready
