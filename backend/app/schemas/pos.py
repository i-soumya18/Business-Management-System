"""
Point of Sale (POS) Schemas

Pydantic schemas for POS operations including cashier shifts, cash drawer management,
and return/exchange processing.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.pos import (
    ShiftStatus,
    CashDrawerStatus,
    POSTransactionType,
    ReturnReason
)


# ==================== Cashier Shift Schemas ====================

class CashierShiftBase(BaseModel):
    """Base schema for cashier shifts"""
    register_number: str = Field(..., max_length=50)
    opening_cash: Decimal = Field(default=Decimal("0.00"), ge=0)
    opening_notes: Optional[str] = None


class CashierShiftCreate(CashierShiftBase):
    """Schema for creating a new cashier shift"""
    pass


class CashierShiftClose(BaseModel):
    """Schema for closing a cashier shift"""
    closing_cash: Decimal = Field(..., ge=0)
    closing_notes: Optional[str] = None
    
    # Denomination breakdown (optional)
    denomination_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Cash denomination breakdown (e.g., {'100': 10, '50': 20})"
    )


class CashierShiftReconcile(BaseModel):
    """Schema for reconciling a cashier shift"""
    reconciliation_notes: Optional[str] = None
    additional_adjustments: Optional[Decimal] = Field(
        default=None,
        description="Any additional adjustments to apply"
    )


class CashierShiftResponse(CashierShiftBase):
    """Schema for cashier shift response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    shift_number: str
    cashier_id: UUID
    status: ShiftStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    # Cash Management
    closing_cash: Optional[Decimal] = None
    expected_cash: Decimal
    cash_variance: Decimal
    
    # Sales Summary
    total_transactions: int
    total_sales: Decimal
    total_returns: Decimal
    total_exchanges: Decimal
    
    # Payment Method Breakdown
    cash_sales: Decimal
    card_sales: Decimal
    upi_sales: Decimal
    other_sales: Decimal
    
    # Notes
    closing_notes: Optional[str] = None
    reconciliation_notes: Optional[str] = None
    
    # Additional Data
    additional_data: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


class CashierShiftSummary(BaseModel):
    """Summary schema for cashier shift"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    shift_number: str
    cashier_id: UUID
    register_number: str
    status: ShiftStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_transactions: int
    total_sales: Decimal
    cash_variance: Decimal


# ==================== Cash Drawer Schemas ====================

class CashDrawerBase(BaseModel):
    """Base schema for cash drawer"""
    denomination_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Cash denomination breakdown"
    )


class CashDrawerUpdate(CashDrawerBase):
    """Schema for updating cash drawer"""
    pass


class CashDrawerResponse(BaseModel):
    """Schema for cash drawer response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    shift_id: UUID
    status: CashDrawerStatus
    current_balance: Decimal
    denomination_breakdown: Optional[Dict[str, int]] = None
    last_transaction_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CashMovement(BaseModel):
    """Schema for cash movement (cash in/out)"""
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., max_length=500)
    notes: Optional[str] = None


# ==================== POS Transaction Schemas ====================

class POSTransactionBase(BaseModel):
    """Base schema for POS transactions"""
    transaction_type: POSTransactionType
    amount: Decimal
    payment_method: str = Field(..., max_length=50)
    
    # Customer Information (optional)
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=255)
    
    notes: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class POSTransactionCreate(POSTransactionBase):
    """Schema for creating a POS transaction"""
    order_id: Optional[UUID] = None
    original_order_id: Optional[UUID] = None  # For returns/exchanges


class POSTransactionResponse(POSTransactionBase):
    """Schema for POS transaction response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    transaction_number: str
    shift_id: UUID
    order_id: Optional[UUID] = None
    original_order_id: Optional[UUID] = None
    receipt_number: Optional[str] = None
    receipt_generated: bool
    transaction_at: datetime


# ==================== Return/Exchange Schemas ====================

class ReturnItemDetail(BaseModel):
    """Schema for individual returned item"""
    product_variant_id: UUID
    quantity: int = Field(..., gt=0)
    reason: ReturnReason
    condition: str = Field(..., description="Product condition (e.g., 'New', 'Used', 'Damaged')")
    restock: bool = Field(default=True, description="Whether item should be restocked")


class ReturnExchangeBase(BaseModel):
    """Base schema for return/exchange"""
    is_exchange: bool = False
    reason: ReturnReason
    reason_description: Optional[str] = None
    restocking_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: Optional[str] = None


class ReturnExchangeCreate(ReturnExchangeBase):
    """Schema for creating a return/exchange"""
    original_order_id: UUID
    returned_items: List[ReturnItemDetail] = Field(..., min_length=1)
    
    # For exchanges
    new_order_id: Optional[UUID] = Field(
        default=None,
        description="Required for exchanges - the new order with replacement items"
    )
    
    @field_validator('new_order_id')
    @classmethod
    def validate_exchange_order(cls, v, info):
        """Validate that exchange has new order"""
        if info.data.get('is_exchange') and not v:
            raise ValueError("Exchange requires new_order_id")
        return v


class ReturnExchangeResponse(ReturnExchangeBase):
    """Schema for return/exchange response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    return_number: str
    original_order_id: UUID
    new_order_id: Optional[UUID] = None
    pos_transaction_id: Optional[UUID] = None
    refund_amount: Decimal
    processed_by_id: UUID
    restocked: bool
    returned_items: Dict[str, Any]
    returned_at: datetime
    created_at: datetime


# ==================== POS Sale Schemas ====================

class POSSaleItem(BaseModel):
    """Schema for POS sale item"""
    product_variant_id: UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)


class POSSaleCreate(BaseModel):
    """Schema for creating a POS sale"""
    items: List[POSSaleItem] = Field(..., min_length=1)
    payment_method: str = Field(..., max_length=50)
    
    # Customer Information (optional)
    customer_name: Optional[str] = Field(None, max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=255)
    
    # Discounts
    subtotal_discount: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Payment Details
    amount_tendered: Optional[Decimal] = Field(
        None,
        description="Amount given by customer (for cash payments)"
    )
    
    notes: Optional[str] = None


class POSSaleResponse(BaseModel):
    """Schema for POS sale response"""
    order_id: UUID
    transaction_id: UUID
    transaction_number: str
    receipt_number: str
    
    subtotal: Decimal
    total_discount: Decimal
    total_tax: Decimal
    total_amount: Decimal
    
    payment_method: str
    amount_tendered: Optional[Decimal] = None
    change_due: Optional[Decimal] = None
    
    transaction_at: datetime


# ==================== Receipt Schemas ====================

class ReceiptRequest(BaseModel):
    """Schema for generating receipt"""
    transaction_id: UUID
    format: str = Field(default="pdf", pattern="^(pdf|html|thermal)$")


class ReceiptResponse(BaseModel):
    """Schema for receipt response"""
    receipt_number: str
    receipt_url: Optional[str] = None
    receipt_data: Optional[str] = None  # Base64 encoded if format is pdf


# ==================== Analytics Schemas ====================

class ShiftAnalytics(BaseModel):
    """Schema for shift analytics"""
    shift_id: UUID
    shift_number: str
    duration_minutes: Optional[int]
    
    # Transaction Counts
    total_transactions: int
    sales_count: int
    returns_count: int
    exchanges_count: int
    
    # Financial Summary
    gross_sales: Decimal
    net_sales: Decimal
    total_returns: Decimal
    total_exchanges: Decimal
    
    # Payment Method Breakdown
    cash_transactions: int
    card_transactions: int
    upi_transactions: int
    
    cash_amount: Decimal
    card_amount: Decimal
    upi_amount: Decimal
    
    # Average Metrics
    average_transaction_value: Decimal
    average_items_per_transaction: Decimal
    
    # Cash Management
    opening_cash: Decimal
    expected_cash: Decimal
    closing_cash: Optional[Decimal]
    cash_variance: Optional[Decimal]


class DailyPOSSummary(BaseModel):
    """Schema for daily POS summary"""
    date: datetime
    total_shifts: int
    total_transactions: int
    
    gross_sales: Decimal
    net_sales: Decimal
    total_returns: Decimal
    
    cash_sales: Decimal
    card_sales: Decimal
    upi_sales: Decimal
    
    average_transaction_value: Decimal
    top_selling_products: List[Dict[str, Any]]


# ==================== Search and Filter Schemas ====================

class ShiftSearchFilters(BaseModel):
    """Schema for shift search filters"""
    cashier_id: Optional[UUID] = None
    register_number: Optional[str] = None
    status: Optional[ShiftStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_variance: Optional[Decimal] = None
    max_variance: Optional[Decimal] = None


class TransactionSearchFilters(BaseModel):
    """Schema for transaction search filters"""
    shift_id: Optional[UUID] = None
    transaction_type: Optional[POSTransactionType] = None
    payment_method: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
