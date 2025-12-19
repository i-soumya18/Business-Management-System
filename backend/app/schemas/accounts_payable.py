"""
Accounts Payable Schemas

Pydantic schemas for bills, vendor payments, and expense management.
Includes comprehensive validation for accounts payable operations.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models.finance import (
    BillStatus,
    ExpenseCategory,
    PaymentRecordStatus
)


# ==================== Bill Schemas ====================

class BillBase(BaseModel):
    """Base schema for Bill"""
    supplier_bill_number: Optional[str] = Field(None, max_length=100, description="Supplier's invoice/bill number")
    description: str = Field(..., min_length=1, max_length=5000, description="Bill description")
    category: ExpenseCategory = Field(..., description="Expense category")
    
    # Financial Details
    subtotal: Decimal = Field(..., ge=0, description="Subtotal amount before tax")
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, description="Tax amount")
    total_amount: Decimal = Field(..., gt=0, description="Total bill amount")
    
    # Dates
    bill_date: date = Field(..., description="Bill issue date")
    due_date: date = Field(..., description="Payment due date")
    
    # Payment Terms
    payment_terms: str = Field(default="NET_30", max_length=50, description="Payment terms")
    
    # Notes
    notes: Optional[str] = Field(None, description="Additional notes")
    
    # Currency
    currency: str = Field(default="INR", min_length=3, max_length=3, description="Currency code")
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: date, info) -> date:
        """Validate due date is not before bill date"""
        if 'bill_date' in info.data and v < info.data['bill_date']:
            raise ValueError('Due date cannot be before bill date')
        return v
    
    @field_validator('total_amount')
    @classmethod
    def validate_total_amount(cls, v: Decimal, info) -> Decimal:
        """Validate total amount matches subtotal + tax"""
        data = info.data
        if 'subtotal' in data and 'tax_amount' in data:
            expected_total = data['subtotal'] + data['tax_amount']
            if abs(v - expected_total) > Decimal("0.01"):
                raise ValueError(f'Total amount {v} does not match subtotal + tax ({expected_total})')
        return v


class BillCreate(BillBase):
    """Schema for creating a Bill"""
    supplier_id: UUID = Field(..., description="Supplier/vendor ID")
    attachments: Optional[dict] = Field(None, description="Attached documents (PDFs, images)")


class BillUpdate(BaseModel):
    """Schema for updating a Bill"""
    supplier_bill_number: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    category: Optional[ExpenseCategory] = None
    
    subtotal: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, gt=0)
    
    bill_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_terms: Optional[str] = Field(None, max_length=50)
    
    notes: Optional[str] = None
    attachments: Optional[dict] = None


class BillStatusUpdate(BaseModel):
    """Schema for updating Bill status"""
    status: BillStatus = Field(..., description="New bill status")
    notes: Optional[str] = Field(None, description="Status change notes")


class BillApproval(BaseModel):
    """Schema for approving a Bill"""
    notes: Optional[str] = Field(None, max_length=1000, description="Approval notes")


class BillResponse(BillBase):
    """Schema for Bill response"""
    id: UUID
    bill_number: str
    supplier_id: UUID
    status: BillStatus
    
    # Calculated fields
    paid_amount: Decimal
    balance_due: Decimal
    
    # Approval
    approved_by_id: Optional[UUID]
    approved_at: Optional[datetime]
    
    # Attachments
    attachments: Optional[dict]
    
    # Audit
    created_by_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BillWithSupplier(BillResponse):
    """Bill response with supplier details"""
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_email: Optional[str] = None


class BillWithPayments(BillResponse):
    """Bill response with payment records"""
    payments: List["VendorPaymentResponse"] = []


# ==================== Vendor Payment Schemas ====================

class VendorPaymentBase(BaseModel):
    """Base schema for Vendor Payment"""
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., min_length=1, max_length=50, description="Payment method")
    payment_date: date = Field(..., description="Payment date")
    
    # Transaction Details
    transaction_reference: Optional[str] = Field(None, max_length=255, description="Transaction reference number")
    bank_account: Optional[str] = Field(None, max_length=100, description="Bank account used")
    check_number: Optional[str] = Field(None, max_length=50, description="Check number if applicable")
    
    # Notes
    notes: Optional[str] = Field(None, description="Payment notes")


class VendorPaymentCreate(VendorPaymentBase):
    """Schema for creating a Vendor Payment"""
    bill_id: UUID = Field(..., description="Bill ID to pay")


class VendorPaymentUpdate(BaseModel):
    """Schema for updating a Vendor Payment"""
    payment_method: Optional[str] = Field(None, max_length=50)
    transaction_reference: Optional[str] = Field(None, max_length=255)
    bank_account: Optional[str] = Field(None, max_length=100)
    check_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    status: Optional[PaymentRecordStatus] = None


class VendorPaymentResponse(VendorPaymentBase):
    """Schema for Vendor Payment response"""
    id: UUID
    payment_number: str
    bill_id: UUID
    status: PaymentRecordStatus
    
    # Audit
    created_by_id: Optional[UUID]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VendorPaymentWithBill(VendorPaymentResponse):
    """Vendor Payment response with bill details"""
    bill_number: Optional[str] = None
    supplier_name: Optional[str] = None
    bill_total: Optional[Decimal] = None


# ==================== Payment Scheduling Schemas ====================

class PaymentScheduleCreate(BaseModel):
    """Schema for creating a payment schedule"""
    bill_id: UUID = Field(..., description="Bill ID")
    scheduled_date: date = Field(..., description="Scheduled payment date")
    amount: Decimal = Field(..., gt=0, description="Scheduled payment amount")
    notes: Optional[str] = Field(None, description="Schedule notes")


class PaymentScheduleResponse(BaseModel):
    """Schema for payment schedule response"""
    id: UUID
    bill_id: UUID
    bill_number: str
    supplier_name: str
    scheduled_date: date
    amount: Decimal
    is_processed: bool
    processed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== Search and Filter Schemas ====================

class BillSearchParams(BaseModel):
    """Schema for bill search parameters"""
    status: Optional[BillStatus] = None
    supplier_id: Optional[UUID] = None
    category: Optional[ExpenseCategory] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    bill_date_from: Optional[date] = None
    bill_date_to: Optional[date] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None
    is_overdue: Optional[bool] = None
    search: Optional[str] = Field(None, max_length=255, description="Search in bill number, supplier name, description")
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class VendorPaymentSearchParams(BaseModel):
    """Schema for vendor payment search parameters"""
    bill_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    status: Optional[PaymentRecordStatus] = None
    payment_method: Optional[str] = None
    payment_date_from: Optional[date] = None
    payment_date_to: Optional[date] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    search: Optional[str] = Field(None, max_length=255)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


# ==================== Analytics and Reporting Schemas ====================

class AgingReportParams(BaseModel):
    """Parameters for aging report"""
    supplier_id: Optional[UUID] = None
    category: Optional[ExpenseCategory] = None
    as_of_date: Optional[date] = None


class AgingBucket(BaseModel):
    """Aging bucket data"""
    bucket: str = Field(..., description="Aging bucket (Current, 1-30, 31-60, 61-90, 90+)")
    count: int = Field(..., ge=0, description="Number of bills")
    total_amount: Decimal = Field(..., ge=0, description="Total amount in bucket")


class SupplierAgingReport(BaseModel):
    """Supplier aging report"""
    supplier_id: UUID
    supplier_name: str
    supplier_code: str
    
    # Totals
    total_outstanding: Decimal
    total_overdue: Decimal
    
    # Aging Buckets
    current: Decimal = Field(default=Decimal("0.00"), ge=0)
    days_1_30: Decimal = Field(default=Decimal("0.00"), ge=0)
    days_31_60: Decimal = Field(default=Decimal("0.00"), ge=0)
    days_61_90: Decimal = Field(default=Decimal("0.00"), ge=0)
    days_90_plus: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Bill counts
    total_bills: int = Field(default=0, ge=0)
    overdue_bills: int = Field(default=0, ge=0)


class AgingReportResponse(BaseModel):
    """Complete aging report response"""
    as_of_date: date
    total_outstanding: Decimal
    total_overdue: Decimal
    
    # Summary by bucket
    aging_buckets: List[AgingBucket]
    
    # By supplier
    by_supplier: List[SupplierAgingReport]


class ExpenseSummary(BaseModel):
    """Expense summary by category"""
    category: ExpenseCategory
    total_amount: Decimal
    bill_count: int
    paid_amount: Decimal
    outstanding_amount: Decimal


class ExpenseReportParams(BaseModel):
    """Parameters for expense report"""
    category: Optional[ExpenseCategory] = None
    supplier_id: Optional[UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ExpenseReportResponse(BaseModel):
    """Expense report response"""
    date_from: date
    date_to: date
    
    # Totals
    total_expenses: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    
    # By category
    by_category: List[ExpenseSummary]
    
    # Top suppliers
    top_suppliers: List[dict]


class PaymentSummary(BaseModel):
    """Payment summary"""
    total_payments: Decimal
    payment_count: int
    average_payment: Decimal
    
    # By method
    by_method: dict
    
    # By status
    by_status: dict


class VendorPerformance(BaseModel):
    """Vendor payment performance metrics"""
    supplier_id: UUID
    supplier_name: str
    
    # Payment metrics
    total_bills: int
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    
    # Timing metrics
    average_days_to_pay: Optional[float]
    on_time_payment_rate: Optional[float]  # Percentage
    
    # Status breakdown
    draft_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    paid_count: int = 0
    overdue_count: int = 0


class AccountsPayableDashboard(BaseModel):
    """Comprehensive AP dashboard data"""
    # Summary
    total_outstanding: Decimal
    total_overdue: Decimal
    bills_due_this_week: int
    bills_due_this_month: int
    
    # By status
    by_status: dict
    
    # By category
    by_category: List[ExpenseSummary]
    
    # Aging
    aging_summary: List[AgingBucket]
    
    # Recent activity
    recent_bills_count: int
    recent_payments_count: int


# ==================== Bulk Operations Schemas ====================

class BulkBillStatusUpdate(BaseModel):
    """Bulk status update for bills"""
    bill_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    status: BillStatus
    notes: Optional[str] = None


class BulkBillApproval(BaseModel):
    """Bulk approval for bills"""
    bill_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = None


class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    success_count: int
    failed_count: int
    failed_ids: List[UUID] = []
    errors: List[str] = []


# Forward references
BillWithPayments.model_rebuild()
