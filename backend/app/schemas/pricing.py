"""
Pricing Engine Schemas

Pydantic schemas for pricing rules, channel pricing, volume discounts,
promotions, price history, and competitor price monitoring.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.pricing import (
    PricingRuleType,
    DiscountType,
    PricingRuleStatus,
    CustomerTier,
    PriceChangeReason
)


# =============================================================================
# Base Schemas
# =============================================================================

class PricingBase(BaseModel):
    """Base schema for pricing models"""
    
    class Config:
        from_attributes = True


# =============================================================================
# Pricing Rule Schemas
# =============================================================================

class PricingRuleProductCreate(PricingBase):
    """Schema for creating a pricing rule product association"""
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    is_excluded: bool = False
    override_discount_value: Optional[Decimal] = None


class PricingRuleProductResponse(PricingBase):
    """Response schema for pricing rule product"""
    id: UUID
    pricing_rule_id: UUID
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    is_excluded: bool
    override_discount_value: Optional[Decimal] = None
    created_at: datetime


class PricingRuleCategoryCreate(PricingBase):
    """Schema for creating a pricing rule category association"""
    category_id: UUID
    include_subcategories: bool = True
    is_excluded: bool = False


class PricingRuleCategoryResponse(PricingBase):
    """Response schema for pricing rule category"""
    id: UUID
    pricing_rule_id: UUID
    category_id: UUID
    include_subcategories: bool
    is_excluded: bool
    created_at: datetime


class PricingRuleCustomerCreate(PricingBase):
    """Schema for creating a pricing rule customer association"""
    wholesale_customer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    override_discount_value: Optional[Decimal] = None


class PricingRuleCustomerResponse(PricingBase):
    """Response schema for pricing rule customer"""
    id: UUID
    pricing_rule_id: UUID
    wholesale_customer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    override_discount_value: Optional[Decimal] = None
    created_at: datetime


class PricingRuleCreate(PricingBase):
    """Schema for creating a pricing rule"""
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    rule_type: PricingRuleType
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    status: PricingRuleStatus = PricingRuleStatus.DRAFT
    max_discount_amount: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    applicable_channels: Optional[List[str]] = None
    applicable_customer_tiers: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    applicable_days: Optional[List[int]] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    min_order_value: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    get_discount_percentage: Optional[Decimal] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    is_stackable: bool = False
    is_exclusive: bool = False
    priority: int = 0
    conditions: Optional[dict] = None
    
    # Associated items - shortcut fields for simple associations
    product_ids: Optional[List[UUID]] = None
    variant_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    customer_ids: Optional[List[UUID]] = None
    
    # Associated items - complex associations with additional data
    products: Optional[List[PricingRuleProductCreate]] = None
    categories: Optional[List[PricingRuleCategoryCreate]] = None
    customers: Optional[List[PricingRuleCustomerCreate]] = None


class PricingRuleUpdate(PricingBase):
    """Schema for updating a pricing rule"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[PricingRuleStatus] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    applicable_channels: Optional[List[str]] = None
    applicable_customer_tiers: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    applicable_days: Optional[List[int]] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    min_order_value: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    get_discount_percentage: Optional[Decimal] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    is_stackable: Optional[bool] = None
    is_exclusive: Optional[bool] = None
    priority: Optional[int] = None
    conditions: Optional[dict] = None


class PricingRuleResponse(PricingBase):
    """Response schema for pricing rule"""
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    rule_type: PricingRuleType
    status: PricingRuleStatus
    priority: int
    discount_type: DiscountType
    discount_value: Decimal
    max_discount_amount: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    applicable_channels: Optional[List[str]] = None
    applicable_customer_tiers: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    applicable_days: Optional[List[int]] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    min_order_value: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    get_discount_percentage: Optional[Decimal] = None
    max_uses: Optional[int] = None
    current_uses: int
    max_uses_per_customer: Optional[int] = None
    is_stackable: bool
    is_exclusive: bool
    conditions: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class PricingRuleDetailResponse(PricingRuleResponse):
    """Detailed response with associations"""
    product_rules: List[PricingRuleProductResponse] = []
    category_rules: List[PricingRuleCategoryResponse] = []
    customer_rules: List[PricingRuleCustomerResponse] = []


# =============================================================================
# Channel Price Schemas
# =============================================================================

class ChannelPriceCreate(PricingBase):
    """Schema for creating channel-specific pricing"""
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    channel: str = Field(..., min_length=1, max_length=50)
    base_price: Decimal = Field(..., gt=0)
    compare_at_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    currency: str = "INR"
    min_price: Optional[Decimal] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class ChannelPriceUpdate(PricingBase):
    """Schema for updating channel-specific pricing"""
    base_price: Optional[Decimal] = None
    compare_at_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class ChannelPriceResponse(PricingBase):
    """Response schema for channel pricing"""
    id: UUID
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    channel: str
    base_price: Decimal
    compare_at_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    currency: str
    min_price: Optional[Decimal] = None
    is_active: bool
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BulkChannelPriceCreate(PricingBase):
    """Schema for bulk channel price creation"""
    prices: List[ChannelPriceCreate]


# =============================================================================
# Volume Discount Schemas
# =============================================================================

class VolumeDiscountCreate(PricingBase):
    """Schema for creating volume discount"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    is_global: bool = False
    min_quantity: int = Field(..., gt=0)
    max_quantity: Optional[int] = None
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    channel: Optional[str] = None
    customer_tier: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: int = 0


class VolumeDiscountUpdate(PricingBase):
    """Schema for updating volume discount"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    channel: Optional[str] = None
    customer_tier: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: Optional[int] = None


class VolumeDiscountResponse(PricingBase):
    """Response schema for volume discount"""
    id: UUID
    name: str
    description: Optional[str] = None
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    is_global: bool
    min_quantity: int
    max_quantity: Optional[int] = None
    discount_type: DiscountType
    discount_value: Decimal
    channel: Optional[str] = None
    customer_tier: Optional[str] = None
    is_active: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    priority: int
    created_at: datetime
    updated_at: datetime


class VolumeDiscountTierResponse(PricingBase):
    """Response for volume discount tiers"""
    min_quantity: int
    max_quantity: Optional[int] = None
    discount_type: DiscountType
    discount_value: Decimal
    unit_price: Optional[Decimal] = None
    total_savings: Optional[Decimal] = None


# =============================================================================
# Promotion Schemas
# =============================================================================

class PromotionCreate(PricingBase):
    """Schema for creating a promotion"""
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    status: PricingRuleStatus = PricingRuleStatus.DRAFT
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    max_discount_amount: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    get_discount_percentage: Optional[Decimal] = None
    applicable_channels: Optional[List[str]] = None
    applicable_customer_tiers: Optional[List[str]] = None
    first_order_only: bool = False
    applicable_product_ids: Optional[List[UUID]] = None
    applicable_category_ids: Optional[List[UUID]] = None
    excluded_product_ids: Optional[List[UUID]] = None
    start_date: datetime
    end_date: datetime
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    is_stackable: bool = False
    auto_apply: bool = False
    display_name: Optional[str] = None
    terms_conditions: Optional[str] = None
    banner_image_url: Optional[str] = None


class PromotionUpdate(PricingBase):
    """Schema for updating a promotion"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[PricingRuleStatus] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    get_discount_percentage: Optional[Decimal] = None
    applicable_channels: Optional[List[str]] = None
    applicable_customer_tiers: Optional[List[str]] = None
    first_order_only: Optional[bool] = None
    applicable_product_ids: Optional[List[UUID]] = None
    applicable_category_ids: Optional[List[UUID]] = None
    excluded_product_ids: Optional[List[UUID]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    is_stackable: Optional[bool] = None
    auto_apply: Optional[bool] = None
    display_name: Optional[str] = None
    terms_conditions: Optional[str] = None
    banner_image_url: Optional[str] = None


class PromotionResponse(PricingBase):
    """Response schema for promotion"""
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    status: PricingRuleStatus
    discount_type: DiscountType
    discount_value: Decimal
    max_discount_amount: Optional[Decimal] = None
    min_order_value: Optional[Decimal] = None
    min_quantity: Optional[int] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    get_discount_percentage: Optional[Decimal] = None
    applicable_channels: Optional[List[str]] = None
    applicable_customer_tiers: Optional[List[str]] = None
    first_order_only: bool
    start_date: datetime
    end_date: datetime
    max_uses: Optional[int] = None
    current_uses: int
    max_uses_per_customer: Optional[int] = None
    is_stackable: bool
    auto_apply: bool
    display_name: Optional[str] = None
    terms_conditions: Optional[str] = None
    banner_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PromotionValidationRequest(PricingBase):
    """Request schema for promotion validation"""
    code: str
    channel: str
    order_value: Decimal
    product_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    quantity: Optional[int] = None
    customer_tier: Optional[str] = None
    user_id: Optional[UUID] = None
    wholesale_customer_id: Optional[UUID] = None
    is_first_order: bool = False


class PromotionValidationResponse(PricingBase):
    """Response schema for promotion validation"""
    is_valid: bool = Field(alias="valid")
    promotion_id: Optional[UUID] = None
    promotion_name: Optional[str] = None
    code: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    discount_amount: Decimal = Decimal("0")
    min_order_value: Optional[Decimal] = None
    max_discount_amount: Optional[Decimal] = None
    message: str
    errors: List[str] = []
    
    model_config = ConfigDict(populate_by_name=True)


class PromotionUsageResponse(PricingBase):
    """Response schema for promotion usage"""
    id: UUID
    promotion_id: UUID
    order_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    wholesale_customer_id: Optional[UUID] = None
    discount_amount: Decimal
    order_total_before_discount: Decimal
    order_total_after_discount: Decimal
    used_at: datetime


# =============================================================================
# Price History Schemas
# =============================================================================

class PriceHistoryCreate(PricingBase):
    """Schema for creating price history entry"""
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    channel: Optional[str] = None
    old_price: Optional[Decimal] = None
    new_price: Decimal
    old_cost: Optional[Decimal] = None
    new_cost: Optional[Decimal] = None
    currency: str = "INR"
    change_reason: PriceChangeReason
    notes: Optional[str] = None
    pricing_rule_id: Optional[UUID] = None
    effective_date: Optional[datetime] = None
    extra_data: Optional[dict] = None


class PriceHistoryResponse(PricingBase):
    """Response schema for price history"""
    id: UUID
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    channel: Optional[str] = None
    old_price: Optional[Decimal] = None
    new_price: Decimal
    old_cost: Optional[Decimal] = None
    new_cost: Optional[Decimal] = None
    currency: str
    change_reason: PriceChangeReason
    notes: Optional[str] = None
    changed_by_id: Optional[UUID] = None
    pricing_rule_id: Optional[UUID] = None
    effective_date: datetime
    extra_data: Optional[dict] = None
    created_at: datetime
    
    # Calculated fields
    price_change: Optional[Decimal] = None
    price_change_percentage: Optional[float] = None


class PriceHistoryFilter(PricingBase):
    """Filter schema for price history queries"""
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    channel: Optional[str] = None
    change_reason: Optional[PriceChangeReason] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


# =============================================================================
# Competitor Price Schemas
# =============================================================================

class CompetitorPriceCreate(PricingBase):
    """Schema for creating competitor price entry"""
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    competitor_name: str = Field(..., min_length=1, max_length=200)
    competitor_url: Optional[str] = None
    competitor_product_name: Optional[str] = None
    competitor_sku: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    sale_price: Optional[Decimal] = None
    currency: str = "INR"
    in_stock: Optional[bool] = None
    source: str = Field(..., min_length=1, max_length=50)
    match_confidence: Optional[float] = None
    extra_data: Optional[dict] = None


class CompetitorPriceUpdate(PricingBase):
    """Schema for updating competitor price entry"""
    price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    match_confidence: Optional[float] = None
    extra_data: Optional[dict] = None


class CompetitorPriceResponse(PricingBase):
    """Response schema for competitor price"""
    id: UUID
    product_id: Optional[UUID] = None
    product_variant_id: Optional[UUID] = None
    competitor_name: str
    competitor_url: Optional[str] = None
    competitor_product_name: Optional[str] = None
    competitor_sku: Optional[str] = None
    price: Decimal
    sale_price: Optional[Decimal] = None
    currency: str
    in_stock: Optional[bool] = None
    source: str
    match_confidence: Optional[float] = None
    observed_at: datetime
    is_latest: bool
    extra_data: Optional[dict] = None
    created_at: datetime


class CompetitorPriceComparisonItem(PricingBase):
    """Individual competitor price comparison item"""
    competitor_name: str
    price: Decimal
    sale_price: Optional[Decimal] = None
    in_stock: Optional[bool] = None
    difference: Decimal
    difference_percentage: Decimal
    last_updated: datetime


class CompetitorPriceComparisonResponse(PricingBase):
    """Response schema for competitor price comparison"""
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    product_name: Optional[str] = None
    our_price: Decimal
    competitor_prices: List[CompetitorPriceComparisonItem]
    lowest_competitor_price: Optional[Decimal] = None
    highest_competitor_price: Optional[Decimal] = None
    average_competitor_price: Optional[Decimal] = None
    our_position: Optional[str] = None  # "lowest", "above_average", "below_average"
    price_index: Optional[Decimal] = None


# =============================================================================
# Customer Pricing Tier Schemas
# =============================================================================

class CustomerPricingTierCreate(PricingBase):
    """Schema for creating customer pricing tier"""
    user_id: Optional[UUID] = None
    wholesale_customer_id: Optional[UUID] = None
    tier: CustomerTier
    discount_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    assignment_reason: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    is_automatic: bool = False


class CustomerPricingTierUpdate(PricingBase):
    """Schema for updating customer pricing tier"""
    tier: Optional[CustomerTier] = None
    discount_percentage: Optional[Decimal] = None
    assignment_reason: Optional[str] = None
    effective_until: Optional[datetime] = None


class CustomerPricingTierResponse(PricingBase):
    """Response schema for customer pricing tier"""
    id: UUID
    user_id: Optional[UUID] = None
    wholesale_customer_id: Optional[UUID] = None
    tier: CustomerTier
    discount_percentage: Decimal
    assignment_reason: Optional[str] = None
    effective_from: datetime
    effective_until: Optional[datetime] = None
    is_automatic: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Price Calculation Schemas
# =============================================================================

class AppliedDiscount(PricingBase):
    """Details of an applied discount"""
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal
    source: str  # "pricing_rule", "promotion", "volume_discount", "customer_tier"
    rule_id: Optional[UUID] = None
    promotion_id: Optional[UUID] = None
    name: Optional[str] = None


class PriceCalculationRequest(PricingBase):
    """Request schema for price calculation"""
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    base_price: Decimal
    compare_at_price: Optional[Decimal] = None
    category_id: Optional[UUID] = None
    quantity: int = 1
    channel: str = "retail"
    user_id: Optional[UUID] = None
    wholesale_customer_id: Optional[UUID] = None
    promotion_code: Optional[str] = None
    order_total: Optional[Decimal] = None
    currency: str = "INR"


class PriceBreakdownItem(PricingBase):
    """Price breakdown item"""
    description: str
    rule_code: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = None
    amount: Decimal


class PriceCalculationResponse(PricingBase):
    """Response schema for price calculation"""
    original_price: Decimal
    final_price: Decimal
    discount_amount: Decimal
    discount_percentage: Decimal
    applied_discounts: List[AppliedDiscount] = []
    quantity: int
    line_total: Decimal
    original_line_total: Decimal
    compare_at_price: Optional[Decimal] = None
    currency: str = "INR"


class BulkPriceCalculationRequest(PricingBase):
    """Request schema for bulk price calculation"""
    items: List[PriceCalculationRequest]


class BulkPriceCalculationResponse(PricingBase):
    """Response schema for bulk price calculation"""
    items: List[PriceCalculationResponse]
    subtotal: Decimal
    total_discount: Decimal
    total: Decimal


# =============================================================================
# Search and List Schemas
# =============================================================================

class PricingRuleSearchFilters(PricingBase):
    """Filters for pricing rule search"""
    search: Optional[str] = None
    rule_types: Optional[List[PricingRuleType]] = None
    statuses: Optional[List[PricingRuleStatus]] = None
    channel: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "priority"
    sort_order: str = "desc"


class PromotionSearchFilters(PricingBase):
    """Filters for promotion search"""
    search: Optional[str] = None
    statuses: Optional[List[PricingRuleStatus]] = None
    channel: Optional[str] = None
    is_active: Optional[bool] = None
    auto_apply: Optional[bool] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "start_date"
    sort_order: str = "desc"


class PricingRuleListResponse(PricingBase):
    """Response schema for pricing rule list"""
    items: List[PricingRuleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PromotionListResponse(PricingBase):
    """Response schema for promotion list"""
    items: List[PromotionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VolumeDiscountListResponse(PricingBase):
    """Response schema for volume discount list"""
    items: List[VolumeDiscountResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PriceHistoryListResponse(PricingBase):
    """Response schema for price history list"""
    items: List[PriceHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Dashboard and Analytics Schemas
# =============================================================================

class PricingDashboard(PricingBase):
    """Dashboard data for pricing engine"""
    active_rules_count: int
    active_promotions_count: int
    volume_discounts_count: int
    
    # Promotion stats
    total_promo_uses: int
    total_promo_savings: Decimal
    
    # Price changes
    recent_price_changes: int
    
    # Competitor analysis
    products_tracked: int
    competitors_tracked: int
    
    # Top performers
    top_promotions: List[dict] = []
    recent_rules: List[PricingRuleResponse] = []


class PricingAnalytics(PricingBase):
    """Analytics data for pricing"""
    period_start: datetime
    period_end: datetime
    
    # Discount stats
    total_orders_with_discounts: int
    total_discount_amount: Decimal
    average_discount_percentage: float
    
    # Promotion performance
    promotion_usage_count: int
    promotion_revenue_impact: Decimal
    
    # Price change impact
    price_changes_count: int
    average_price_change: Decimal
    
    # By channel
    discount_by_channel: dict = {}
    
    # By rule type
    discount_by_rule_type: dict = {}
