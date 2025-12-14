"""
Wholesale Customer Schemas

Pydantic schemas for B2B wholesale customer management, credit limits,
payment terms, and contract pricing.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.models.wholesale import (
    CustomerType,
    CustomerStatus,
    PaymentTerms,
    CreditStatus
)


# ==================== Wholesale Customer Schemas ====================

class WholesaleCustomerBase(BaseModel):
    """Base schema for Wholesale Customer"""
    # Company Information
    company_name: str = Field(..., min_length=2, max_length=255)
    company_legal_name: Optional[str] = Field(None, max_length=255)
    business_registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=100)
    
    # Customer Type & Status
    customer_type: CustomerType = Field(default=CustomerType.RETAILER)
    
    # Contact Information
    primary_contact_name: str = Field(..., min_length=2, max_length=255)
    primary_email: EmailStr
    primary_phone: str = Field(..., min_length=10, max_length=20)
    secondary_contact_name: Optional[str] = Field(None, max_length=255)
    secondary_email: Optional[EmailStr] = None
    secondary_phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    
    # Business Address
    billing_address_line1: str = Field(..., min_length=5, max_length=255)
    billing_address_line2: Optional[str] = Field(None, max_length=255)
    billing_city: str = Field(..., min_length=2, max_length=100)
    billing_state: str = Field(..., min_length=2, max_length=100)
    billing_postal_code: str = Field(..., min_length=5, max_length=20)
    billing_country: str = Field(default="India", max_length=100)
    
    shipping_address_line1: Optional[str] = Field(None, max_length=255)
    shipping_address_line2: Optional[str] = Field(None, max_length=255)
    shipping_city: Optional[str] = Field(None, max_length=100)
    shipping_state: Optional[str] = Field(None, max_length=100)
    shipping_postal_code: Optional[str] = Field(None, max_length=20)
    shipping_country: Optional[str] = Field(None, max_length=100)
    
    # Credit Management
    credit_limit: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Payment Terms
    payment_terms: PaymentTerms = Field(default=PaymentTerms.NET_30)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    
    # Pricing & Discounts
    default_discount_percentage: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    has_contract_pricing: bool = Field(default=False)
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    
    # Minimum Order Requirements
    minimum_order_quantity: int = Field(default=0, ge=0)
    minimum_order_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    
    # Sales Representative Assignment
    sales_rep_id: Optional[UUID] = None
    
    # Business Details
    business_since: Optional[date] = None
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    number_of_employees: Optional[int] = Field(None, ge=1)
    number_of_stores: Optional[int] = Field(None, ge=1)
    
    # Preferences & Settings
    preferred_shipping_method: Optional[str] = Field(None, max_length=100)
    requires_approval: bool = Field(default=False)
    auto_approve_orders: bool = Field(default=False)
    send_invoices_via_email: bool = Field(default=True)
    
    # Communication & Notes
    notes: Optional[str] = None
    additional_data: Optional[dict] = None
    
    @field_validator("contract_end_date")
    @classmethod
    def validate_contract_dates(cls, v, info):
        """Validate that contract_end_date is after contract_start_date"""
        if v and info.data.get("contract_start_date"):
            if v < info.data["contract_start_date"]:
                raise ValueError("Contract end date must be after start date")
        return v


class WholesaleCustomerCreate(WholesaleCustomerBase):
    """Schema for creating a new Wholesale Customer"""
    pass


class WholesaleCustomerUpdate(BaseModel):
    """Schema for updating a Wholesale Customer (all fields optional)"""
    # Company Information
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    company_legal_name: Optional[str] = Field(None, max_length=255)
    business_registration_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=100)
    
    # Customer Type & Status
    customer_type: Optional[CustomerType] = None
    status: Optional[CustomerStatus] = None
    
    # Contact Information
    primary_contact_name: Optional[str] = Field(None, min_length=2, max_length=255)
    primary_email: Optional[EmailStr] = None
    primary_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    secondary_contact_name: Optional[str] = Field(None, max_length=255)
    secondary_email: Optional[EmailStr] = None
    secondary_phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    
    # Business Address
    billing_address_line1: Optional[str] = Field(None, min_length=5, max_length=255)
    billing_address_line2: Optional[str] = Field(None, max_length=255)
    billing_city: Optional[str] = Field(None, min_length=2, max_length=100)
    billing_state: Optional[str] = Field(None, min_length=2, max_length=100)
    billing_postal_code: Optional[str] = Field(None, min_length=5, max_length=20)
    billing_country: Optional[str] = Field(None, max_length=100)
    
    shipping_address_line1: Optional[str] = Field(None, max_length=255)
    shipping_address_line2: Optional[str] = Field(None, max_length=255)
    shipping_city: Optional[str] = Field(None, max_length=100)
    shipping_state: Optional[str] = Field(None, max_length=100)
    shipping_postal_code: Optional[str] = Field(None, max_length=20)
    shipping_country: Optional[str] = Field(None, max_length=100)
    
    # Credit Management
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    
    # Payment Terms
    payment_terms: Optional[PaymentTerms] = None
    payment_terms_days: Optional[int] = Field(None, ge=0, le=365)
    
    # Pricing & Discounts
    default_discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    has_contract_pricing: Optional[bool] = None
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    
    # Minimum Order Requirements
    minimum_order_quantity: Optional[int] = Field(None, ge=0)
    minimum_order_value: Optional[Decimal] = Field(None, ge=0)
    
    # Sales Representative Assignment
    sales_rep_id: Optional[UUID] = None
    
    # Business Details
    business_since: Optional[date] = None
    annual_revenue: Optional[Decimal] = Field(None, ge=0)
    number_of_employees: Optional[int] = Field(None, ge=1)
    number_of_stores: Optional[int] = Field(None, ge=1)
    
    # Preferences & Settings
    preferred_shipping_method: Optional[str] = Field(None, max_length=100)
    requires_approval: Optional[bool] = None
    auto_approve_orders: Optional[bool] = None
    send_invoices_via_email: Optional[bool] = None
    
    # Communication & Notes
    notes: Optional[str] = None
    additional_data: Optional[dict] = None


class WholesaleCustomerResponse(WholesaleCustomerBase):
    """Schema for Wholesale Customer response"""
    id: UUID
    status: CustomerStatus
    credit_used: Decimal
    credit_available: Decimal
    credit_status: CreditStatus
    total_orders: int
    total_spent: Decimal
    average_order_value: Decimal
    last_order_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    approved_by_id: Optional[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class WholesaleCustomerList(BaseModel):
    """Schema for paginated Wholesale Customer list"""
    items: List[WholesaleCustomerResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==================== Credit Management Schemas ====================

class CreditLimitUpdate(BaseModel):
    """Schema for updating customer credit limit"""
    credit_limit: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class CreditUsageUpdate(BaseModel):
    """Schema for updating credit usage (internal use)"""
    amount: Decimal = Field(...)
    operation: str = Field(..., pattern="^(increase|decrease)$")
    reference: str  # Order number or transaction reference


# ==================== Approval Schemas ====================

class CustomerApproval(BaseModel):
    """Schema for approving/rejecting customer"""
    approved: bool
    notes: Optional[str] = None


# ==================== Contract Pricing Schemas ====================

class ContractPricingBase(BaseModel):
    """Base schema for Contract Pricing"""
    product_variant_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    contract_price: Decimal = Field(..., ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    minimum_quantity: int = Field(default=1, ge=1)
    maximum_quantity: Optional[int] = Field(None, ge=1)
    valid_from: date
    valid_until: date
    is_active: bool = Field(default=True)
    notes: Optional[str] = None
    
    @field_validator("valid_until")
    @classmethod
    def validate_validity_period(cls, v, info):
        """Validate that valid_until is after valid_from"""
        if v and info.data.get("valid_from"):
            if v < info.data["valid_from"]:
                raise ValueError("Valid until date must be after valid from date")
        return v
    
    @field_validator("maximum_quantity")
    @classmethod
    def validate_quantity_range(cls, v, info):
        """Validate that maximum_quantity is >= minimum_quantity"""
        if v and info.data.get("minimum_quantity"):
            if v < info.data["minimum_quantity"]:
                raise ValueError("Maximum quantity must be >= minimum quantity")
        return v
    
    @field_validator("product_variant_id")
    @classmethod
    def validate_applicability(cls, v, info):
        """At least one of product_variant_id or category_id must be provided"""
        if not v and not info.data.get("category_id"):
            raise ValueError("Either product_variant_id or category_id must be provided")
        return v


class ContractPricingCreate(ContractPricingBase):
    """Schema for creating Contract Pricing"""
    customer_id: UUID


class ContractPricingUpdate(BaseModel):
    """Schema for updating Contract Pricing (all fields optional)"""
    contract_price: Optional[Decimal] = Field(None, ge=0)
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    minimum_quantity: Optional[int] = Field(None, ge=1)
    maximum_quantity: Optional[int] = Field(None, ge=1)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ContractPricingResponse(ContractPricingBase):
    """Schema for Contract Pricing response"""
    id: UUID
    customer_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    
    model_config = ConfigDict(from_attributes=True)


class ContractPricingList(BaseModel):
    """Schema for paginated Contract Pricing list"""
    items: List[ContractPricingResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ==================== Wholesale Order Schemas ====================

class WholesaleOrderCreate(BaseModel):
    """Schema for creating a wholesale order"""
    wholesale_customer_id: UUID
    sales_rep_id: Optional[UUID] = None
    items: List[dict]  # Will be detailed in order schemas
    discount_code: Optional[str] = None
    notes: Optional[str] = None
    requires_approval: bool = Field(default=False)


class WholesaleOrderValidation(BaseModel):
    """Schema for order validation response"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Validation details
    moq_passed: bool = True
    mov_passed: bool = True
    credit_check_passed: bool = True
    pricing_applied: bool = True
    
    # Order summary
    total_quantity: int = 0
    order_value: Decimal = Decimal("0.00")
    credit_required: Decimal = Decimal("0.00")
    credit_available: Decimal = Decimal("0.00")


# ==================== Bulk Pricing Schemas ====================

class BulkPricingCalculation(BaseModel):
    """Schema for bulk pricing calculation request"""
    customer_id: UUID
    items: List[dict]  # product_variant_id, quantity


class BulkPricingResponse(BaseModel):
    """Schema for bulk pricing calculation response"""
    items: List[dict]  # product_variant_id, quantity, unit_price, discount, total
    subtotal: Decimal
    total_discount: Decimal
    total: Decimal
    pricing_tiers_applied: List[str] = Field(default_factory=list)
