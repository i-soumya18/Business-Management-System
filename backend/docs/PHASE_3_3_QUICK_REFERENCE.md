# Phase 3.3 Quick Reference: Accounts Receivable

**Quick Start Guide for Accounts Receivable Module**

---

## 🚀 Quick Start

### 1. Run Database Migration
```bash
cd backend
alembic upgrade head
```

### 2. Verify Installation
```bash
pytest tests/test_accounts_receivable.py -v
```

### 3. Start Server
```bash
uvicorn app.main:app --reload
```

### 4. Access API Docs
- Swagger: http://localhost:8000/docs
- Navigate to "Accounts Receivable" tag

---

## 📋 Common Operations

### Create Invoice

```python
POST /api/ar/invoices

{
  "invoice_date": "2025-01-15",
  "due_date": "2025-02-14",
  "wholesale_customer_id": "customer-uuid",
  "customer_name": "ABC Company",
  "customer_email": "billing@abc.com",
  "billing_address_line1": "123 Business St",
  "billing_city": "New York",
  "billing_state": "NY",
  "billing_postal_code": "10001",
  "billing_country": "USA",
  "payment_terms": "Net 30",
  "tax_rate": 8.875,
  "items": [
    {
      "description": "Product A",
      "quantity": 10,
      "unit_price": 50.00,
      "line_total": 500.00,
      "tax_rate": 8.875
    }
  ]
}
```

### Send Invoice

```python
POST /api/ar/invoices/{invoice_id}/send
```

### Record Payment

```python
POST /api/ar/payments

{
  "invoice_id": "invoice-uuid",
  "amount": 500.00,
  "payment_date": "2025-01-20",
  "payment_gateway": "bank_transfer",
  "payment_method": "Bank Transfer",
  "reference_number": "REF-12345"
}
```

### Create Credit Note

```python
POST /api/ar/credit-notes

{
  "invoice_id": "invoice-uuid",
  "wholesale_customer_id": "customer-uuid",
  "amount": 100.00,
  "reason": "return",
  "description": "Product return"
}
```

### Apply Credit to Invoice

```python
POST /api/ar/credit-notes/apply

{
  "credit_note_id": "credit-uuid",
  "invoice_id": "invoice-uuid",
  "amount_to_apply": 50.00
}
```

---

## 📊 Analytics & Reports

### Get Aging Report
```python
GET /api/ar/analytics/aging-report

Response:
{
  "total_outstanding": "125,450.00",
  "current": {"amount": "85,000.00", "count": 45},
  "days_1_30": {"amount": "25,000.00", "count": 18},
  "days_31_60": {"amount": "10,000.00", "count": 8},
  "days_61_90": {"amount": "3,450.00", "count": 4},
  "over_90_days": {"amount": "2,000.00", "count": 3}
}
```

### Get AR Dashboard
```python
GET /api/ar/analytics/dashboard

Returns: Comprehensive dashboard with:
- Invoice summary (current month)
- Payment summary
- Aging report
- Overdue counts
- Collection effectiveness
```

### Get Customer Aging
```python
GET /api/ar/analytics/customer-aging?wholesale_customer_id={id}
```

---

## 🔍 Search & Filter

### Search Invoices
```python
GET /api/ar/invoices?status=sent&is_overdue=true&skip=0&limit=20
```

**Available Filters:**
- `status` - Invoice status (draft, sent, paid, etc.)
- `wholesale_customer_id` - Filter by B2B customer
- `retail_customer_id` - Filter by B2C customer
- `is_overdue` - Show only overdue invoices
- `invoice_date_from` / `invoice_date_to` - Date range
- `due_date_from` / `due_date_to` - Due date range
- `search` - Search invoice number, customer name, email

### Search Payments
```python
GET /api/ar/payments?status=completed&is_reconciled=false&skip=0&limit=20
```

**Available Filters:**
- `status` - Payment status
- `payment_method` - Filter by method
- `is_reconciled` - Reconciliation status
- `payment_date_from` / `payment_date_to` - Date range

### Search Credit Notes
```python
GET /api/ar/credit-notes?reason=return&is_expired=false&skip=0&limit=20
```

---

## 🔄 Invoice Status Workflow

```
DRAFT → SENT → PARTIALLY_PAID → PAID
             ↓
          OVERDUE → VOID/CANCELLED
```

### Status Transitions
- **DRAFT → SENT**: `POST /api/ar/invoices/{id}/send`
- **SENT → PARTIALLY_PAID**: Record partial payment
- **PARTIALLY_PAID → PAID**: Record final payment
- **Any → OVERDUE**: Automatic (due date passed)
- **Any → VOID**: `POST /api/ar/invoices/{id}/void`

---

## 📨 Payment Reminders

### Reminder Types & Timing

1. **FRIENDLY** - 3 days before due date
2. **FIRST** - 1-7 days overdue
3. **SECOND** - 8-30 days overdue
4. **FINAL** - 31-60 days overdue
5. **LEGAL** - 61+ days overdue

### Send Manual Reminder
```python
POST /api/ar/reminders

{
  "invoice_id": "invoice-uuid",
  "reminder_type": "first",
  "custom_message": "Your payment is overdue..."
}
```

### Process Automated Reminders
```python
POST /api/ar/reminders/process-automated

Returns: Count of reminders sent by type
```

### Get Reminders for Invoice
```python
GET /api/ar/reminders/invoice/{invoice_id}
```

---

## 💳 Payment Processing

### Record Payment
```python
POST /api/ar/payments

{
  "invoice_id": "invoice-uuid",
  "amount": 500.00,
  "payment_date": "2025-01-20",
  "payment_gateway": "bank_transfer",  # or "credit_card", "cash", "check", "online"
  "payment_method": "Bank Transfer",
  "transaction_id": "TXN-12345",
  "reference_number": "REF-12345",
  "notes": "Payment received"
}
```

### Reconcile Payment
```python
POST /api/ar/payments/{payment_id}/reconcile

{
  "notes": "Matched with bank statement line 45"
}
```

### Refund Payment
```python
POST /api/ar/payments/{payment_id}/refund

{
  "refund_amount": 500.00,
  "reason": "Customer request"
}

Returns: Payment + auto-created Credit Note
```

### Get Unreconciled Payments
```python
GET /api/ar/payments/unreconciled
```

### Bulk Reconcile
```python
POST /api/ar/payments/bulk/reconcile

{
  "payment_ids": ["uuid1", "uuid2", "uuid3"],
  "notes": "Bank reconciliation 2025-01"
}
```

---

## 💰 Credit Note Management

### Create Credit Note
```python
POST /api/ar/credit-notes

{
  "invoice_id": "invoice-uuid",
  "wholesale_customer_id": "customer-uuid",
  "amount": 100.00,
  "reason": "return",  # return, refund, discount, error, adjustment, goodwill, warranty, write_off
  "description": "Product return - damaged item",
  "expiry_date": "2026-01-15",  # Optional, defaults to 1 year
  "requires_approval": false
}
```

### Approve Credit Note
```python
POST /api/ar/credit-notes/{credit_note_id}/approve

{
  "approval_notes": "Approved by manager"
}
```

### Apply Credit Note
```python
POST /api/ar/credit-notes/apply

{
  "credit_note_id": "credit-uuid",
  "invoice_id": "invoice-uuid",
  "amount_to_apply": 50.00
}
```

### Get Available Credits for Customer
```python
GET /api/ar/credit-notes/customer/available?wholesale_customer_id={id}

Returns: All non-expired credits with remaining balance
```

---

## 🛠️ Bulk Operations

### Bulk Send Invoices
```python
POST /api/ar/invoices/bulk/send

{
  "invoice_ids": ["uuid1", "uuid2", "uuid3"]
}

Returns: {"success": [...], "failed": [...]}
```

### Bulk Update Invoice Status
```python
POST /api/ar/invoices/bulk/status

{
  "invoice_ids": ["uuid1", "uuid2"],
  "new_status": "cancelled"
}
```

### Bulk Reconcile Payments
```python
POST /api/ar/payments/bulk/reconcile

{
  "payment_ids": ["uuid1", "uuid2", "uuid3"],
  "notes": "Reconciliation batch 2025-01"
}
```

---

## 🔧 Maintenance Tasks

### Update Overdue Flags
```python
POST /api/ar/maintenance/update-overdue

Returns: {"updated_count": 15}
```

**Schedule:** Run daily via cron/scheduler

### Update Expired Credits
```python
POST /api/ar/maintenance/update-expired-credits

Returns: {"updated_count": 3}
```

**Schedule:** Run daily via cron/scheduler

---

## 📈 Key Metrics

### Invoice Summary
```python
GET /api/ar/analytics/invoice-summary?start_date=2025-01-01&end_date=2025-01-31

{
  "total_invoices": 150,
  "total_invoiced": "500,000.00",
  "total_paid": "400,000.00",
  "total_outstanding": "100,000.00",
  "overdue_count": 12,
  "overdue_amount": "25,000.00"
}
```

### Payment Summary
```python
GET /api/ar/analytics/payment-summary?start_date=2025-01-01&end_date=2025-01-31

{
  "total_payments": 120,
  "total_amount": "400,000.00",
  "total_fees": "5,000.00",
  "reconciled_count": 100,
  "pending_count": 20
}
```

### Collection Effectiveness
```
Collection Effectiveness = (Total Paid / Total Invoiced) * 100
```
Available in dashboard: `GET /api/ar/analytics/dashboard`

---

## 🔍 Common Queries

### Get All Overdue Invoices
```python
GET /api/ar/invoices?is_overdue=true&status=overdue
```

### Get Customer Invoice History
```python
GET /api/ar/invoices?wholesale_customer_id={id}&skip=0&limit=100
```

### Get Payments for Invoice
```python
GET /api/ar/payments/invoice/{invoice_id}
```

### Get Credit Notes for Invoice
```python
GET /api/ar/credit-notes/invoice/{invoice_id}
```

### Get Invoices for Order
```python
GET /api/ar/invoices/order/{order_id}
```

---

## 💡 Best Practices

### Invoice Creation
1. Always create invoices with `status=DRAFT`
2. Validate all calculations before sending
3. Send invoices only when finalized
4. Include clear payment terms and due dates

### Payment Processing
1. Record payments immediately upon receipt
2. Always include reference numbers
3. Reconcile payments within 24-48 hours
4. Track gateway fees for accurate accounting

### Credit Note Management
1. Use appropriate reason codes
2. Set expiry dates for time-limited credits
3. Apply credits in FIFO order
4. Require approval for credits > $1000

### Collections
1. Send friendly reminders before due date
2. Process automated reminders daily
3. Escalate consistently (don't skip tiers)
4. Track acknowledgments and responses

### Reporting
1. Review aging report weekly
2. Monitor collection effectiveness monthly
3. Update overdue flags daily
4. Expire old credits monthly

---

## 🐛 Troubleshooting

### "Cannot send invoice" Error
- Check invoice status is DRAFT
- Verify all required fields populated

### "Payment amount exceeds amount due" Error
- Check invoice.amount_due
- Verify no duplicate payments

### "Cannot apply credit note" Error
- Check credit note is approved
- Verify not expired
- Check sufficient remaining balance

### "Cannot void paid invoice" Error
- Paid invoices cannot be voided
- Use refund process instead

---

## 📞 Integration Examples

### Create Invoice from Order
```python
# In Order Management module
async def create_invoice_from_order(order_id):
    service = AccountsReceivableService(db)
    # Logic to create invoice from order items
    return await service.create_invoice_from_order(order_id, user.id)
```

### Update Order Status on Payment
```python
# In Payment processing
async def on_payment_complete(payment, invoice):
    if invoice.status == InvoiceStatus.PAID:
        # Update order status
        order = await order_repo.get(invoice.order_id)
        order.payment_status = "PAID"
        await order_repo.update(order)
```

---

## 📚 Model Relationships

```
Invoice
  ├─ order_id → Order
  ├─ wholesale_customer_id → WholesaleCustomer
  ├─ retail_customer_id → RetailCustomer
  ├─ created_by_id → User
  ├─ items → List[InvoiceItem]
  ├─ payments → List[PaymentRecord]
  ├─ credit_notes → List[CreditNote]
  └─ reminders → List[PaymentReminder]

PaymentRecord
  ├─ invoice_id → Invoice
  ├─ wholesale_customer_id → WholesaleCustomer
  ├─ retail_customer_id → RetailCustomer
  ├─ created_by_id → User
  └─ reconciled_by_id → User

CreditNote
  ├─ invoice_id → Invoice
  ├─ wholesale_customer_id → WholesaleCustomer
  ├─ retail_customer_id → RetailCustomer
  ├─ created_by_id → User
  ├─ approved_by_id → User
  └─ applied_to_invoice_id → Invoice
```

---

## 🔑 Enum Values

### InvoiceStatus
- `draft` - Invoice being prepared
- `sent` - Invoice sent to customer
- `partially_paid` - Some payment received
- `paid` - Fully paid
- `overdue` - Past due date
- `cancelled` - Cancelled by user
- `void` - Voided (with reason)

### PaymentGateway
- `bank_transfer`
- `credit_card`
- `cash`
- `check`
- `online`

### PaymentRecordStatus
- `pending` - Payment initiated
- `completed` - Payment successful
- `failed` - Payment failed
- `refunded` - Payment refunded

### CreditNoteReason
- `return` - Product return
- `refund` - Payment refund
- `discount` - Discount applied
- `error` - Invoice error correction
- `adjustment` - Price adjustment
- `goodwill` - Customer goodwill
- `warranty` - Warranty claim
- `write_off` - Debt write-off

### ReminderType
- `friendly` - Pre-due courtesy
- `first` - 1-7 days overdue
- `second` - 8-30 days overdue
- `final` - 31-60 days overdue
- `legal` - 61+ days (collections)

---

## ⚡ Performance Tips

1. **Use Pagination**: Always use `skip` and `limit` for lists
2. **Filter Early**: Apply filters to reduce dataset size
3. **Batch Operations**: Use bulk endpoints for multiple records
4. **Index Usage**: Queries on indexed fields are faster
5. **Eager Loading**: Use detail endpoints (with items loaded)

---

## 📅 Scheduled Tasks

### Daily Tasks
```bash
# Update overdue flags (8:00 AM)
POST /api/ar/maintenance/update-overdue

# Process automated reminders (9:00 AM)
POST /api/ar/reminders/process-automated

# Update expired credits (11:00 PM)
POST /api/ar/maintenance/update-expired-credits
```

### Weekly Tasks
```bash
# Review aging report (Monday 9:00 AM)
GET /api/ar/analytics/aging-report

# Reconcile unreconciled payments (Friday 5:00 PM)
GET /api/ar/payments/unreconciled
```

### Monthly Tasks
```bash
# Generate monthly summary (1st of month)
GET /api/ar/analytics/invoice-summary?start_date=...&end_date=...
GET /api/ar/analytics/payment-summary?start_date=...&end_date=...

# Review collection effectiveness
GET /api/ar/analytics/dashboard
```

---

## 🎯 Quick Wins

### Improve Cash Flow
1. Enable automated reminders
2. Send invoices immediately after order fulfillment
3. Offer early payment discounts (via discount_amount)
4. Set up online payment options

### Reduce DSO (Days Sales Outstanding)
1. Send friendly reminders before due date
2. Make payment process easy
3. Follow up consistently on overdue invoices
4. Offer payment plans for large amounts

### Increase Collection Rate
1. Review aging report weekly
2. Prioritize oldest overdue invoices
3. Escalate reminders appropriately
4. Track customer payment patterns

---

**For detailed documentation, see:** `PHASE_3_3_COMPLETION_REPORT.md`

**API Documentation:** http://localhost:8000/docs

**Support:** Check test files for usage examples
