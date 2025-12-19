"""
CRM Schemas - B2B Lead Management, Opportunities, and Communications

Pydantic schemas for:
- Lead management and qualification
- Sales opportunity tracking
- Customer communications
- Customer segmentation
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, validator

from app.models.crm import (
    LeadStatus,
    LeadSource,
    LeadPriority,
    OpportunityStage,
    CommunicationType,
    CommunicationDirection
)


# ===== Lead Schemas =====

class LeadBase(BaseModel):
    """Base Lead schema"""
    company_name: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    contact_person: str = Field(..., min_length=1, max_length=255)
    title_position: Optional[str] = Field(None, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=100)
    source: LeadSource
    priority: LeadPriority = LeadPriority.MEDIUM
    estimated_deal_value: Optional[Decimal] = Field(None, ge=0)
    estimated_close_date: Optional[datetime] = None
    requirements: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    assigned_to_id: Optional[UUID] = None


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, min_length=1, max_length=255)
    title_position: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    alternate_phone: Optional[str] = Field(None, max_length=20)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    status: Optional[LeadStatus] = None
    source: Optional[LeadSource] = None
    priority: Optional[LeadPriority] = None
    estimated_deal_value: Optional[Decimal] = Field(None, ge=0)
    estimated_close_date: Optional[datetime] = None
    requirements: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    assigned_to_id: Optional[UUID] = None
    next_follow_up_date: Optional[datetime] = None


class LeadQualify(BaseModel):
    """Schema for qualifying a lead"""
    qualification_score: int = Field(..., ge=0, le=100)
    is_qualified: bool = True
    notes: Optional[str] = None


class LeadConvert(BaseModel):
    """Schema for converting a lead to customer"""
    customer_id: UUID
    notes: Optional[str] = None


class LeadResponse(LeadBase):
    """Schema for lead response"""
    id: UUID
    lead_number: str
    status: LeadStatus
    is_qualified: bool
    qualification_score: Optional[int]
    assigned_to_id: Optional[UUID]
    converted_to_customer_id: Optional[UUID]
    converted_at: Optional[datetime]
    next_follow_up_date: Optional[datetime]
    last_contact_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list"""
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ===== Sales Opportunity Schemas =====

class OpportunityBase(BaseModel):
    """Base Opportunity schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    customer_id: UUID
    lead_id: Optional[UUID] = None
    estimated_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    probability: int = Field(default=50, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    competitors: Optional[str] = None
    risks: Optional[str] = None
    products_interested: Optional[Dict[str, Any]] = None
    next_step: Optional[str] = None
    next_step_date: Optional[datetime] = None
    tags: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class OpportunityCreate(OpportunityBase):
    """Schema for creating an opportunity"""
    owner_id: UUID
    stage: OpportunityStage = OpportunityStage.PROSPECTING


class OpportunityUpdate(BaseModel):
    """Schema for updating an opportunity"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    stage: Optional[OpportunityStage] = None
    estimated_value: Optional[Decimal] = Field(None, ge=0)
    probability: Optional[int] = Field(None, ge=0, le=100)
    expected_close_date: Optional[datetime] = None
    competitors: Optional[str] = None
    risks: Optional[str] = None
    products_interested: Optional[Dict[str, Any]] = None
    next_step: Optional[str] = None
    next_step_date: Optional[datetime] = None
    tags: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    owner_id: Optional[UUID] = None


class OpportunityClose(BaseModel):
    """Schema for closing an opportunity"""
    stage: OpportunityStage = Field(..., description="Must be closed_won or closed_lost")
    actual_close_date: datetime = Field(default_factory=datetime.utcnow)
    loss_reason: Optional[str] = Field(None, description="Required if closed_lost")
    notes: Optional[str] = None

    @validator('stage')
    def validate_close_stage(cls, v):
        if v not in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]:
            raise ValueError('Stage must be closed_won or closed_lost')
        return v

    @validator('loss_reason')
    def validate_loss_reason(cls, v, values):
        if 'stage' in values and values['stage'] == OpportunityStage.CLOSED_LOST and not v:
            raise ValueError('Loss reason is required when closing as lost')
        return v


class OpportunityResponse(OpportunityBase):
    """Schema for opportunity response"""
    id: UUID
    opportunity_number: str
    stage: OpportunityStage
    expected_revenue: Decimal
    actual_close_date: Optional[datetime]
    owner_id: UUID
    loss_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    """Schema for paginated opportunity list"""
    items: List[OpportunityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OpportunityStats(BaseModel):
    """Schema for opportunity statistics"""
    total_opportunities: int
    total_value: Decimal
    weighted_value: Decimal  # Sum of (value * probability)
    by_stage: Dict[str, int]
    win_rate: float  # Percentage


# ===== Customer Communication Schemas =====

class CommunicationBase(BaseModel):
    """Base Communication schema"""
    type: CommunicationType
    direction: CommunicationDirection
    subject: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    contact_person: Optional[str] = Field(None, max_length=255)
    communication_date: datetime = Field(default_factory=datetime.utcnow)
    duration_minutes: Optional[int] = Field(None, ge=0)
    requires_follow_up: bool = False
    follow_up_date: Optional[datetime] = None
    attachments: Optional[Dict[str, Any]] = None
    related_order_id: Optional[UUID] = None
    tags: Optional[Dict[str, Any]] = None


class CommunicationCreate(CommunicationBase):
    """Schema for creating a communication"""
    customer_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    our_representative_id: UUID

    @validator('customer_id', 'lead_id', 'opportunity_id')
    def validate_related_entity(cls, v, values):
        # At least one must be provided
        if not any([
            values.get('customer_id'),
            values.get('lead_id'),
            values.get('opportunity_id'),
            v
        ]):
            raise ValueError('At least one of customer_id, lead_id, or opportunity_id must be provided')
        return v


class CommunicationUpdate(BaseModel):
    """Schema for updating a communication"""
    type: Optional[CommunicationType] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    contact_person: Optional[str] = Field(None, max_length=255)
    duration_minutes: Optional[int] = Field(None, ge=0)
    requires_follow_up: Optional[bool] = None
    follow_up_date: Optional[datetime] = None
    follow_up_completed: Optional[bool] = None
    attachments: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None


class CommunicationResponse(CommunicationBase):
    """Schema for communication response"""
    id: UUID
    customer_id: Optional[UUID]
    lead_id: Optional[UUID]
    opportunity_id: Optional[UUID]
    our_representative_id: UUID
    follow_up_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommunicationListResponse(BaseModel):
    """Schema for paginated communication list"""
    items: List[CommunicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ===== Customer Segment Schemas =====

class SegmentBase(BaseModel):
    """Base Segment schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    code: str = Field(..., min_length=1, max_length=50)
    criteria: Optional[Dict[str, Any]] = None
    is_active: bool = True
    priority: int = Field(default=0, ge=0)
    benefits: Optional[Dict[str, Any]] = None


class SegmentCreate(SegmentBase):
    """Schema for creating a segment"""
    pass


class SegmentUpdate(BaseModel):
    """Schema for updating a segment"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)
    benefits: Optional[Dict[str, Any]] = None


class SegmentResponse(SegmentBase):
    """Schema for segment response"""
    id: UUID
    customer_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SegmentListResponse(BaseModel):
    """Schema for paginated segment list"""
    items: List[SegmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SegmentAssignment(BaseModel):
    """Schema for assigning customers to segments"""
    customer_ids: List[UUID] = Field(..., min_items=1)
    segment_id: UUID


class SegmentCustomerResponse(BaseModel):
    """Schema for segment-customer mapping"""
    customer_id: UUID
    segment_id: UUID
    assigned_at: datetime
    assigned_by_id: Optional[UUID]

    class Config:
        from_attributes = True


# ===== Analytics Schemas =====

class LeadAnalytics(BaseModel):
    """Schema for lead analytics"""
    total_leads: int
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    by_priority: Dict[str, int]
    conversion_rate: float
    average_time_to_convert_days: Optional[float]


class CustomerPerformanceMetrics(BaseModel):
    """Schema for customer performance metrics"""
    customer_id: UUID
    company_name: str
    total_orders: int
    total_spent: Decimal
    average_order_value: Decimal
    last_order_date: Optional[datetime]
    payment_behavior_score: Optional[int]  # 1-100
    engagement_score: Optional[int]  # 1-100


class SalesPipelineReport(BaseModel):
    """Schema for sales pipeline report"""
    total_opportunities: int
    total_pipeline_value: Decimal
    weighted_pipeline_value: Decimal
    by_stage: Dict[str, Dict[str, Any]]  # stage -> {count, value}
    expected_revenue_this_month: Decimal
    expected_revenue_this_quarter: Decimal
    win_rate: float
    average_deal_size: Decimal
    average_sales_cycle_days: Optional[float]
