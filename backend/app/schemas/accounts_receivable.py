"""
Accounts Receivable Schemas

Pydantic schemas for invoices, payments, credit notes, and payment reminders.
Includes comprehensive validation for accounts receivable management.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.models.finance import (
    InvoiceStatus,
    ReminderType,
    CreditNoteReason,
    PaymentGateway,
    PaymentRecordStatus
)


# ==================== Invoice Schemas ====================

class InvoiceItemBase(BaseModel):
    """Base schema for Invoice Item"""
    item_description: str = Field(..., min_length=1, max_length=500)
    sku: Optional[str] = Field(None, max_length=100)
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_percentage: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    line_total: Decimal = Field(default=Decimal("0.00"), ge=0)


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating an Invoice Item"""
    pass


class InvoiceItemResponse(InvoiceItemBase):
    """Schema for Invoice Item response"""
    id: UUID
    invoice_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BillingAddress(BaseModel):
    """Schema for billing address"""
    billing_address_line1: str = Field(..., min_length=1, max_length=255)
    billing_address_line2: Optional[str] = Field(None, max_length=255)
    billing_city: str = Field(..., min_length=1, max_length=100)
    billing_state: str = Field(..., min_length=1, max_length=100)
    billing_postal_code: str = Field(..., min_length=1, max_length=20)
    billing_country: str = Field(default="India", max_length=100)


class InvoiceBase(BaseModel):
    """Base schema for Invoice"""
    # Customer Information
    customer_name: str = Field(..., min_length=2, max_length=255)
    customer_email: EmailStr
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_tax_id: Optional[str] = Field(None, max_length=100)
    
    # Financial Details
    subtotal: Decimal = Field(default=Decimal("0.00"), ge=0)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    shipping_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Payment Terms
    payment_terms: str = Field(default="Net 30", max_length=100)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    
    # Dates
    invoice_date: date
    due_date: date
    
    # Notes
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: date, info) -> date:
        """Validate due date is not before invoice date"""
        if 'invoice_date' in info.data and v < info.data['invoice_date']:
            raise ValueError('Due date cannot be before invoice date')
        return v


class InvoiceCreate(InvoiceBase, BillingAddress):
    """Schema for creating an Invoice"""
    order_id: UUID
    wholesale_customer_id: Optional[UUID] = None
    retail_customer_id: Optional[UUID] = None
    items: List[InvoiceItemCreate] = Field(..., min_length=1)
    
    @field_validator('wholesale_customer_id', 'retail_customer_id')
    @classmethod
    def validate_customer(cls, v, info) -> Optional[UUID]:
        """Ensure at least one customer ID is provided"""
        values = info.data
        wholesale_id = values.get('wholesale_customer_id')
        retail_id = values.get('retail_customer_id')
        
        if not wholesale_id and not retail_id:
            raise ValueError('Either wholesale_customer_id or retail_customer_id must be provided')
        
        return v


class InvoiceUpdate(BaseModel):
    """Schema for updating an Invoice"""
    status: Optional[InvoiceStatus] = None
    customer_name: Optional[str] = Field(None, min_length=2, max_length=255)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = Field(None, max_length=20)
    
    billing_address_line1: Optional[str] = Field(None, max_length=255)
    billing_address_line2: Optional[str] = Field(None, max_length=255)
    billing_city: Optional[str] = Field(None, max_length=100)
    billing_state: Optional[str] = Field(None, max_length=100)
    billing_postal_code: Optional[str] = Field(None, max_length=20)
    billing_country: Optional[str] = Field(None, max_length=100)
    
    payment_terms: Optional[str] = Field(None, max_length=100)
    payment_terms_days: Optional[int] = Field(None, ge=0, le=365)
    due_date: Optional[date] = None
    
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class InvoiceResponse(InvoiceBase, BillingAddress):
    """Schema for Invoice response"""
    id: UUID
    invoice_number: str
    order_id: UUID
    wholesale_customer_id: Optional[UUID]
    retail_customer_id: Optional[UUID]
    
    status: InvoiceStatus
    amount_paid: Decimal
    amount_due: Decimal
    credit_applied: Decimal
    
    is_sent: bool
    sent_at: Optional[datetime]
    is_overdue_flag: bool
    reminders_sent: int
    last_reminder_sent_at: Optional[datetime]
    
    paid_date: Optional[datetime]
    
    created_by_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    is_fully_paid: bool = False
    days_overdue: int = 0
    aging_bucket: str = "Current"
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceDetail(InvoiceResponse):
    """Schema for detailed Invoice response with items"""
    items: List[InvoiceItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class InvoiceList(BaseModel):
    """Schema for paginated Invoice list"""
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==================== Payment Schemas ====================

class PaymentRecordBase(BaseModel):
    """Base schema for Payment Record"""
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentGateway
    payment_date: date
    
    # Transaction Details
    transaction_reference: Optional[str] = Field(None, max_length=255)
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_account_last4: Optional[str] = Field(None, max_length=4)
    cheque_number: Optional[str] = Field(None, max_length=50)
    
    notes: Optional[str] = None
    reference_number: Optional[str] = Field(None, max_length=100)


class PaymentRecordCreate(PaymentRecordBase):
    """Schema for creating a Payment Record"""
    invoice_id: UUID
    wholesale_customer_id: Optional[UUID] = None
    retail_customer_id: Optional[UUID] = None


class PaymentRecordUpdate(BaseModel):
    """Schema for updating a Payment Record"""
    status: Optional[PaymentRecordStatus] = None
    notes: Optional[str] = None
    is_reconciled: Optional[bool] = None


class PaymentRecordResponse(PaymentRecordBase):
    """Schema for Payment Record response"""
    id: UUID
    payment_number: str
    invoice_id: UUID
    wholesale_customer_id: Optional[UUID]
    retail_customer_id: Optional[UUID]
    
    payment_gateway: PaymentGateway
    status: PaymentRecordStatus
    currency: str
    
    # Gateway Details
    gateway_transaction_id: Optional[str]
    gateway_fee: Decimal
    
    # Reconciliation
    is_reconciled: bool
    reconciled_at: Optional[datetime]
    reconciled_by_id: Optional[UUID]
    
    # Refund
    refund_amount: Decimal
    refunded_at: Optional[datetime]
    
    created_by_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaymentRecordList(BaseModel):
    """Schema for paginated Payment Record list"""
    items: List[PaymentRecordResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ReconcilePayment(BaseModel):
    """Schema for reconciling a payment"""
    is_reconciled: bool = True
    notes: Optional[str] = None


# ==================== Credit Note Schemas ====================

class CreditNoteBase(BaseModel):
    """Base schema for Credit Note"""
    total_amount: Decimal = Field(..., gt=0)
    reason: CreditNoteReason
    notes: Optional[str] = None
    expiry_date: Optional[date] = None


class CreditNoteCreate(CreditNoteBase):
    """Schema for creating a Credit Note"""
    invoice_id: UUID
    wholesale_customer_id: Optional[UUID] = None
    retail_customer_id: Optional[UUID] = None
    internal_notes: Optional[str] = None


class CreditNoteUpdate(BaseModel):
    """Schema for updating a Credit Note"""
    amount_used: Optional[Decimal] = Field(None, ge=0)
    is_applied: Optional[bool] = None
    is_expired: Optional[bool] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class CreditNoteResponse(CreditNoteBase):
    """Schema for Credit Note response"""
    id: UUID
    credit_note_number: str
    invoice_id: UUID
    wholesale_customer_id: Optional[UUID]
    retail_customer_id: Optional[UUID]
    
    issue_date: date
    amount_used: Decimal
    amount_remaining: Decimal
    
    is_applied: bool
    is_expired: bool
    
    created_by_id: Optional[UUID]
    approved_by_id: Optional[UUID]
    approved_at: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime
    
    # Computed property
    is_fully_used: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class CreditNoteList(BaseModel):
    """Schema for paginated Credit Note list"""
    items: List[CreditNoteResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ApplyCreditNote(BaseModel):
    """Schema for applying a credit note to an invoice"""
    credit_note_id: UUID
    amount: Decimal = Field(..., gt=0)


class ApproveCreditNote(BaseModel):
    """Schema for approving a credit note"""
    approved: bool = True
    internal_notes: Optional[str] = None


# ==================== Payment Reminder Schemas ====================

class PaymentReminderBase(BaseModel):
    """Base schema for Payment Reminder"""
    reminder_type: ReminderType
    days_overdue: int = Field(..., ge=0)
    
    sent_to_email: Optional[EmailStr] = None
    sent_to_phone: Optional[str] = Field(None, max_length=20)
    
    subject: Optional[str] = Field(None, max_length=500)
    message: Optional[str] = None


class PaymentReminderCreate(PaymentReminderBase):
    """Schema for creating a Payment Reminder"""
    invoice_id: UUID


class PaymentReminderResponse(PaymentReminderBase):
    """Schema for Payment Reminder response"""
    id: UUID
    invoice_id: UUID
    
    sent_at: datetime
    email_sent: bool
    sms_sent: bool
    
    is_acknowledged: bool
    acknowledged_at: Optional[datetime]
    customer_response: Optional[str]
    
    created_by_id: Optional[UUID]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaymentReminderList(BaseModel):
    """Schema for paginated Payment Reminder list"""
    items: List[PaymentReminderResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AcknowledgeReminder(BaseModel):
    """Schema for acknowledging a payment reminder"""
    is_acknowledged: bool = True
    customer_response: Optional[str] = None


# ==================== Analytics & Reports ====================

class AgingBucket(BaseModel):
    """Schema for aging report bucket"""
    bucket: str  # Current, 1-30, 31-60, 61-90, 90+
    count: int
    total_amount: Decimal


class AgingReport(BaseModel):
    """Schema for Accounts Receivable aging report"""
    as_of_date: date
    total_outstanding: Decimal
    buckets: List[AgingBucket]


class CustomerAgingSummary(BaseModel):
    """Schema for customer aging summary"""
    customer_id: UUID
    customer_name: str
    customer_type: str  # wholesale or retail
    total_outstanding: Decimal
    current: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_90_plus: Decimal
    oldest_invoice_days: int


class AgingReportDetail(BaseModel):
    """Schema for detailed aging report"""
    as_of_date: date
    total_outstanding: Decimal
    total_customers: int
    customers: List[CustomerAgingSummary]


class InvoiceSummary(BaseModel):
    """Schema for invoice summary statistics"""
    total_invoices: int
    total_amount: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    overdue_count: int
    overdue_amount: Decimal


class PaymentSummary(BaseModel):
    """Schema for payment summary statistics"""
    total_payments: int
    total_amount: Decimal
    total_fees: Decimal
    reconciled_count: int
    pending_count: int
    failed_count: int


class ARDashboard(BaseModel):
    """Schema for AR dashboard summary"""
    invoice_summary: InvoiceSummary
    payment_summary: PaymentSummary
    aging_summary: AgingReport
    recent_invoices: List[InvoiceResponse]
    recent_payments: List[PaymentRecordResponse]
    overdue_invoices: List[InvoiceResponse]


# ==================== Bulk Operations ====================

class BulkInvoiceStatusUpdate(BaseModel):
    """Schema for bulk invoice status update"""
    invoice_ids: List[UUID] = Field(..., min_length=1)
    status: InvoiceStatus


class BulkSendInvoices(BaseModel):
    """Schema for bulk sending invoices"""
    invoice_ids: List[UUID] = Field(..., min_length=1)
    send_email: bool = True
    send_sms: bool = False


class BulkPaymentReconciliation(BaseModel):
    """Schema for bulk payment reconciliation"""
    payment_ids: List[UUID] = Field(..., min_length=1)
    is_reconciled: bool = True


# ==================== Search & Filter ====================

class InvoiceFilter(BaseModel):
    """Schema for filtering invoices"""
    status: Optional[InvoiceStatus] = None
    wholesale_customer_id: Optional[UUID] = None
    retail_customer_id: Optional[UUID] = None
    is_overdue: Optional[bool] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    invoice_date_from: Optional[date] = None
    invoice_date_to: Optional[date] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None
    search: Optional[str] = None  # Search in invoice_number, customer_name


class PaymentFilter(BaseModel):
    """Schema for filtering payments"""
    status: Optional[PaymentRecordStatus] = None
    payment_method: Optional[PaymentGateway] = None
    is_reconciled: Optional[bool] = None
    wholesale_customer_id: Optional[UUID] = None
    retail_customer_id: Optional[UUID] = None
    payment_date_from: Optional[date] = None
    payment_date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None


class CreditNoteFilter(BaseModel):
    """Schema for filtering credit notes"""
    reason: Optional[CreditNoteReason] = None
    is_applied: Optional[bool] = None
    is_expired: Optional[bool] = None
    wholesale_customer_id: Optional[UUID] = None
    retail_customer_id: Optional[UUID] = None
    issue_date_from: Optional[date] = None
    issue_date_to: Optional[date] = None
