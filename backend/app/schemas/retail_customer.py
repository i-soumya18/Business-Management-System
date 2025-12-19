"""
Retail Customer Schemas - B2C CRM

Pydantic schemas for retail customer management including:
- Customer registration and profile management
- Loyalty program operations
- Customer preferences
- RFM analysis and CLV calculation
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, List, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.models.retail_customer import (
    CustomerTierLevel,
    CustomerPreferenceType
)


# ============================================================================
# RetailCustomer Schemas
# ============================================================================

class RetailCustomerBase(BaseModel):
    """Base schema for retail customer"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,20}$")
    alternate_phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,20}$")
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=100)
    
    # Marketing Preferences
    email_marketing_consent: bool = Field(default=True)
    sms_marketing_consent: bool = Field(default=True)
    push_notification_consent: bool = Field(default=True)
    
    # Shopping Preferences
    preferred_categories: Optional[Dict[str, Any]] = None
    preferred_brands: Optional[Dict[str, Any]] = None
    preferred_sizes: Optional[Dict[str, Any]] = None
    preferred_colors: Optional[Dict[str, Any]] = None
    preferred_payment_method: Optional[str] = Field(None, max_length=50)
    
    # Source
    acquisition_source: Optional[str] = Field(None, max_length=100)
    acquisition_campaign: Optional[str] = Field(None, max_length=100)
    referrer_customer_id: Optional[UUID] = None
    
    # Notes and Tags
    notes: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    
    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_genders = ["Male", "Female", "Other", "Prefer not to say"]
            if v not in valid_genders:
                raise ValueError(f"Gender must be one of: {', '.join(valid_genders)}")
        return v


class RetailCustomerCreate(RetailCustomerBase):
    """Schema for creating a retail customer"""
    user_id: Optional[UUID] = None  # Link to user account if registering online


class RetailCustomerUpdate(BaseModel):
    """Schema for updating a retail customer"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,20}$")
    alternate_phone: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,20}$")
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Marketing Preferences
    email_marketing_consent: Optional[bool] = None
    sms_marketing_consent: Optional[bool] = None
    push_notification_consent: Optional[bool] = None
    
    # Shopping Preferences
    preferred_categories: Optional[Dict[str, Any]] = None
    preferred_brands: Optional[Dict[str, Any]] = None
    preferred_sizes: Optional[Dict[str, Any]] = None
    preferred_colors: Optional[Dict[str, Any]] = None
    preferred_payment_method: Optional[str] = Field(None, max_length=50)
    
    # Notes and Tags
    notes: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(extra="forbid")


class RetailCustomerResponse(RetailCustomerBase):
    """Schema for retail customer response"""
    id: UUID
    customer_number: str
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    is_phone_verified: bool
    
    # Loyalty Program
    loyalty_points: int
    loyalty_points_lifetime: int
    loyalty_tier: CustomerTierLevel
    tier_start_date: Optional[date]
    tier_expiry_date: Optional[date]
    
    # Purchase Metrics
    total_orders: int
    total_spent: Decimal
    average_order_value: Decimal
    first_order_date: Optional[datetime]
    last_order_date: Optional[datetime]
    
    # RFM Metrics
    rfm_recency_score: Optional[int]
    rfm_frequency_score: Optional[int]
    rfm_monetary_score: Optional[int]
    rfm_segment: Optional[str]
    rfm_last_calculated: Optional[datetime]
    
    # CLV
    clv: Decimal
    clv_last_calculated: Optional[datetime]
    
    # Engagement
    email_open_rate: Optional[Decimal]
    email_click_rate: Optional[Decimal]
    last_email_sent: Optional[datetime]
    last_email_opened: Optional[datetime]
    
    # User Link
    user_id: Optional[UUID]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_activity_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class RetailCustomerListResponse(BaseModel):
    """Schema for retail customer list with summary"""
    id: UUID
    customer_number: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    city: Optional[str]
    is_active: bool
    loyalty_tier: CustomerTierLevel
    loyalty_points: int
    total_orders: int
    total_spent: Decimal
    last_order_date: Optional[datetime]
    rfm_segment: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RetailCustomerRegistration(BaseModel):
    """Schema for customer self-registration"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,20}$")
    password: str = Field(..., min_length=8, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    
    # Optional address
    address_line1: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=100)
    
    # Marketing consent
    email_marketing_consent: bool = Field(default=True)
    sms_marketing_consent: bool = Field(default=True)
    
    # Referral
    referral_code: Optional[str] = None


class RetailCustomerVerification(BaseModel):
    """Schema for customer verification"""
    verification_type: str = Field(..., pattern="^(email|phone)$")
    verification_code: str = Field(..., min_length=6, max_length=6)


# ============================================================================
# Loyalty Program Schemas
# ============================================================================

class LoyaltyTransactionBase(BaseModel):
    """Base schema for loyalty transaction"""
    transaction_type: str = Field(..., max_length=50)
    points: int = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    order_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class LoyaltyTransactionCreate(LoyaltyTransactionBase):
    """Schema for creating loyalty transaction"""
    customer_id: UUID


class LoyaltyTransactionResponse(LoyaltyTransactionBase):
    """Schema for loyalty transaction response"""
    id: UUID
    customer_id: UUID
    balance_before: int
    balance_after: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LoyaltyPointsEarn(BaseModel):
    """Schema for earning loyalty points"""
    customer_id: UUID
    points: int = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    order_id: Optional[UUID] = None
    expiry_days: Optional[int] = Field(default=365, gt=0)


class LoyaltyPointsRedeem(BaseModel):
    """Schema for redeeming loyalty points"""
    customer_id: UUID
    points: int = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    order_id: Optional[UUID] = None


class LoyaltyPointsAdjust(BaseModel):
    """Schema for adjusting loyalty points (admin)"""
    customer_id: UUID
    points: int  # Can be positive or negative
    reason: str = Field(..., min_length=1, max_length=500)


class LoyaltyBalanceResponse(BaseModel):
    """Schema for loyalty balance response"""
    customer_id: UUID
    current_balance: int
    lifetime_points: int
    points_expiring_soon: int
    points_expiring_date: Optional[datetime]
    tier: CustomerTierLevel


class LoyaltyTierUpdate(BaseModel):
    """Schema for updating customer loyalty tier"""
    customer_id: UUID
    new_tier: CustomerTierLevel
    reason: str = Field(..., min_length=1, max_length=200)
    tier_expiry_date: Optional[date] = None


# ============================================================================
# Customer Preference Schemas
# ============================================================================

class CustomerPreferenceBase(BaseModel):
    """Base schema for customer preference"""
    preference_type: CustomerPreferenceType
    preference_key: str = Field(..., min_length=1, max_length=100)
    preference_value: str = Field(..., min_length=1)


class CustomerPreferenceCreate(CustomerPreferenceBase):
    """Schema for creating customer preference"""
    customer_id: UUID


class CustomerPreferenceUpdate(BaseModel):
    """Schema for updating customer preference"""
    preference_value: str = Field(..., min_length=1)


class CustomerPreferenceResponse(CustomerPreferenceBase):
    """Schema for customer preference response"""
    id: UUID
    customer_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CustomerPreferencesBulkUpdate(BaseModel):
    """Schema for bulk updating customer preferences"""
    customer_id: UUID
    preferences: List[Dict[str, Any]] = Field(
        ...,
        description="List of preferences with type, key, and value"
    )


# ============================================================================
# RFM Analysis Schemas
# ============================================================================

class RFMScoresResponse(BaseModel):
    """Schema for RFM scores response"""
    customer_id: UUID
    customer_number: str
    customer_name: str
    recency_score: int = Field(..., ge=1, le=5)
    frequency_score: int = Field(..., ge=1, le=5)
    monetary_score: int = Field(..., ge=1, le=5)
    rfm_segment: str
    total_orders: int
    total_spent: Decimal
    last_order_date: Optional[datetime]
    days_since_last_order: Optional[int]
    calculated_at: datetime


class RFMSegmentDistribution(BaseModel):
    """Schema for RFM segment distribution"""
    segment: str
    count: int
    percentage: Decimal
    total_revenue: Decimal
    average_order_value: Decimal


class RFMAnalysisRequest(BaseModel):
    """Schema for triggering RFM analysis"""
    customer_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Specific customers to analyze. If None, analyzes all active customers."
    )
    recalculate: bool = Field(
        default=False,
        description="Force recalculation even if recently calculated"
    )


class RFMAnalysisResponse(BaseModel):
    """Schema for RFM analysis response"""
    total_customers_analyzed: int
    segment_distribution: List[RFMSegmentDistribution]
    analysis_date: datetime
    
    # Segment definitions
    champion_count: int
    loyal_count: int
    potential_loyalist_count: int
    new_customers_count: int
    promising_count: int
    need_attention_count: int
    about_to_sleep_count: int
    at_risk_count: int
    cannot_lose_count: int
    hibernating_count: int
    lost_count: int


# ============================================================================
# CLV (Customer Lifetime Value) Schemas
# ============================================================================

class CLVCalculationRequest(BaseModel):
    """Schema for triggering CLV calculation"""
    customer_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Specific customers to calculate. If None, calculates for all."
    )
    prediction_months: int = Field(
        default=12,
        ge=1,
        le=60,
        description="Number of months to predict into the future"
    )
    recalculate: bool = Field(
        default=False,
        description="Force recalculation even if recently calculated"
    )


class CLVResponse(BaseModel):
    """Schema for CLV response"""
    customer_id: UUID
    customer_number: str
    customer_name: str
    clv: Decimal
    predicted_orders: int
    predicted_revenue: Decimal
    average_order_value: Decimal
    purchase_frequency: Decimal
    customer_lifespan_months: int
    calculated_at: datetime


class CLVDistribution(BaseModel):
    """Schema for CLV distribution"""
    range_label: str  # e.g., "0-1000", "1000-5000"
    min_value: Decimal
    max_value: Decimal
    count: int
    percentage: Decimal
    total_clv: Decimal


class CLVAnalysisResponse(BaseModel):
    """Schema for CLV analysis response"""
    total_customers_analyzed: int
    total_clv: Decimal
    average_clv: Decimal
    median_clv: Decimal
    distribution: List[CLVDistribution]
    top_customers: List[CLVResponse]
    analysis_date: datetime


# ============================================================================
# Purchase History Schemas
# ============================================================================

class PurchaseHistorySummary(BaseModel):
    """Schema for purchase history summary"""
    customer_id: UUID
    total_orders: int
    total_spent: Decimal
    average_order_value: Decimal
    first_order_date: Optional[datetime]
    last_order_date: Optional[datetime]
    favorite_category: Optional[str]
    favorite_brand: Optional[str]
    most_purchased_product: Optional[str]
    purchase_frequency_days: Optional[int]


class CustomerAnalytics(BaseModel):
    """Schema for comprehensive customer analytics"""
    customer_id: UUID
    customer_number: str
    customer_name: str
    email: EmailStr
    
    # Purchase metrics
    purchase_summary: PurchaseHistorySummary
    
    # Loyalty
    loyalty_tier: CustomerTierLevel
    loyalty_points: int
    
    # RFM
    rfm_recency_score: Optional[int]
    rfm_frequency_score: Optional[int]
    rfm_monetary_score: Optional[int]
    rfm_segment: Optional[str]
    
    # CLV
    clv: Decimal
    
    # Engagement
    email_open_rate: Optional[Decimal]
    email_click_rate: Optional[Decimal]
    last_activity_at: Optional[datetime]


# ============================================================================
# Search and Filter Schemas
# ============================================================================

class RetailCustomerSearchFilters(BaseModel):
    """Schema for customer search filters"""
    search: Optional[str] = Field(
        default=None,
        description="Search by name, email, phone, or customer number"
    )
    is_active: Optional[bool] = None
    loyalty_tier: Optional[CustomerTierLevel] = None
    rfm_segment: Optional[str] = None
    city: Optional[str] = None
    min_total_spent: Optional[Decimal] = None
    max_total_spent: Optional[Decimal] = None
    min_orders: Optional[int] = None
    max_orders: Optional[int] = None
    registered_after: Optional[datetime] = None
    registered_before: Optional[datetime] = None
    last_order_after: Optional[datetime] = None
    last_order_before: Optional[datetime] = None
    has_email_consent: Optional[bool] = None
    has_sms_consent: Optional[bool] = None


# ============================================================================
# Bulk Operations Schemas
# ============================================================================

class BulkCustomerStatusUpdate(BaseModel):
    """Schema for bulk customer status update"""
    customer_ids: List[UUID] = Field(..., min_length=1)
    is_active: bool
    reason: str = Field(..., min_length=1, max_length=200)


class BulkLoyaltyTierUpdate(BaseModel):
    """Schema for bulk loyalty tier update"""
    customer_ids: List[UUID] = Field(..., min_length=1)
    new_tier: CustomerTierLevel
    tier_expiry_date: Optional[date] = None


class BulkTagUpdate(BaseModel):
    """Schema for bulk tag update"""
    customer_ids: List[UUID] = Field(..., min_length=1)
    tags: Dict[str, Any]
    merge: bool = Field(
        default=True,
        description="If True, merge with existing tags. If False, replace."
    )


# ============================================================================
# Analytics Schemas
# ============================================================================

class CustomerAcquisitionMetrics(BaseModel):
    """Schema for customer acquisition metrics"""
    period: str  # daily, weekly, monthly
    start_date: date
    end_date: date
    new_customers: int
    total_customers: int
    growth_rate: Decimal
    acquisition_by_source: Dict[str, int]
    acquisition_by_campaign: Dict[str, int]


class CustomerRetentionMetrics(BaseModel):
    """Schema for customer retention metrics"""
    period: str
    cohort_date: date
    total_customers: int
    active_customers: int
    retention_rate: Decimal
    churn_rate: Decimal
    repeat_purchase_rate: Decimal


class LoyaltyProgramMetrics(BaseModel):
    """Schema for loyalty program metrics"""
    total_members: int
    active_members: int
    bronze_members: int
    silver_members: int
    gold_members: int
    platinum_members: int
    total_points_issued: int
    total_points_redeemed: int
    total_points_expired: int
    current_outstanding_points: int
    redemption_rate: Decimal


# ============================================================================
# Communication Schemas
# ============================================================================

class CustomerCommunicationPreferences(BaseModel):
    """Schema for communication preferences"""
    customer_id: UUID
    email_marketing: bool
    sms_marketing: bool
    push_notifications: bool
    preferred_contact_method: str = Field(..., pattern="^(email|sms|phone)$")
    preferred_contact_time: Optional[str] = None


class MarketingCampaignTarget(BaseModel):
    """Schema for targeting customers for marketing campaign"""
    segment: Optional[str] = None
    loyalty_tier: Optional[CustomerTierLevel] = None
    min_clv: Optional[Decimal] = None
    rfm_segments: Optional[List[str]] = None
    city: Optional[str] = None
    has_email_consent: bool = True
    has_sms_consent: Optional[bool] = None
