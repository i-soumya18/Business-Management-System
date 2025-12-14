"""
Pricing Engine API Endpoints

Comprehensive API for:
- Dynamic pricing rules management
- Channel-specific pricing
- Volume-based discounts
- Promotional campaigns
- Price calculation
- Price history tracking
- Competitor price monitoring
- Customer tier management
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.pricing import (
    PricingRuleType,
    PricingRuleStatus,
    CustomerTier,
    PriceChangeReason
)
from app.schemas.pricing import (
    # Pricing Rules
    PricingRuleCreate,
    PricingRuleUpdate,
    PricingRuleResponse,
    PricingRuleListResponse,
    # Channel Pricing
    ChannelPriceCreate,
    ChannelPriceUpdate,
    ChannelPriceResponse,
    # Volume Discounts
    VolumeDiscountCreate,
    VolumeDiscountUpdate,
    VolumeDiscountResponse,
    VolumeDiscountListResponse,
    # Promotions
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
    PromotionListResponse,
    # Price Calculation
    PriceCalculationRequest,
    PriceCalculationResponse,
    # Promotion Validation
    PromotionValidationRequest,
    PromotionValidationResponse,
    # Price History
    PriceHistoryResponse,
    PriceHistoryListResponse,
    # Competitor Pricing
    CompetitorPriceCreate,
    CompetitorPriceResponse,
    CompetitorPriceComparisonResponse,
    # Customer Tiers
    CustomerPricingTierCreate,
    CustomerPricingTierResponse,
    # Dashboard
    PricingDashboard,
    PricingAnalytics
)
from app.services.pricing import PricingService

router = APIRouter(prefix="/pricing")


# ==================== Price Calculation ====================

@router.post(
    "/calculate",
    response_model=PriceCalculationResponse,
    summary="Calculate Final Price",
    description="""
    Calculate the final price for a product/variant with all applicable discounts.
    
    The calculation applies:
    1. Channel-specific base pricing
    2. Customer tier discounts
    3. Active pricing rules (by priority)
    4. Volume discounts
    5. Promotional discounts (code or auto-apply)
    
    Rules are applied in priority order, with stackable rules combining
    and non-stackable rules being mutually exclusive.
    """
)
async def calculate_price(
    request: PriceCalculationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Calculate final price with all applicable discounts"""
    service = PricingService(db)
    return await service.calculate_price(request)


# ==================== Pricing Rules ====================

@router.post(
    "/rules",
    response_model=PricingRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Pricing Rule",
    description="Create a new dynamic pricing rule"
)
async def create_pricing_rule(
    data: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new pricing rule"""
    service = PricingService(db)
    rule = await service.create_pricing_rule(data, created_by_id=current_user.id)
    await db.commit()
    return rule


@router.get(
    "/rules",
    response_model=PricingRuleListResponse,
    summary="List Pricing Rules",
    description="List pricing rules with filters and pagination"
)
async def list_pricing_rules(
    search: Optional[str] = Query(None, description="Search in name, code, description"),
    rule_types: Optional[List[PricingRuleType]] = Query(None, description="Filter by rule types"),
    statuses: Optional[List[PricingRuleStatus]] = Query(None, description="Filter by statuses"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("priority", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List pricing rules with filters"""
    service = PricingService(db)
    rules, total = await service.list_pricing_rules(
        search=search,
        rule_types=rule_types,
        statuses=statuses,
        channel=channel,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return PricingRuleListResponse(
        items=[PricingRuleResponse.model_validate(r) for r in rules],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/rules/{rule_id}",
    response_model=PricingRuleResponse,
    summary="Get Pricing Rule",
    description="Get a pricing rule by ID"
)
async def get_pricing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a pricing rule by ID"""
    service = PricingService(db)
    rule = await service.get_pricing_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found"
        )
    return rule


@router.put(
    "/rules/{rule_id}",
    response_model=PricingRuleResponse,
    summary="Update Pricing Rule",
    description="Update an existing pricing rule"
)
async def update_pricing_rule(
    rule_id: UUID,
    data: PricingRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a pricing rule"""
    service = PricingService(db)
    rule = await service.update_pricing_rule(rule_id, data)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found"
        )
    await db.commit()
    return rule


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Pricing Rule",
    description="Delete a pricing rule"
)
async def delete_pricing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a pricing rule"""
    service = PricingService(db)
    deleted = await service.delete_pricing_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found"
        )
    await db.commit()


@router.post(
    "/rules/{rule_id}/activate",
    response_model=PricingRuleResponse,
    summary="Activate Pricing Rule",
    description="Activate a paused or draft pricing rule"
)
async def activate_pricing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a pricing rule"""
    service = PricingService(db)
    rule = await service.activate_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found"
        )
    await db.commit()
    return rule


@router.post(
    "/rules/{rule_id}/deactivate",
    response_model=PricingRuleResponse,
    summary="Deactivate Pricing Rule",
    description="Pause an active pricing rule"
)
async def deactivate_pricing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a pricing rule"""
    service = PricingService(db)
    rule = await service.deactivate_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing rule not found"
        )
    await db.commit()
    return rule


# ==================== Channel Pricing ====================

@router.post(
    "/channels",
    response_model=ChannelPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set Channel Price",
    description="Set or update channel-specific pricing for a product"
)
async def set_channel_price(
    data: ChannelPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set channel-specific pricing"""
    service = PricingService(db)
    return await service.set_channel_price(data, changed_by_id=current_user.id)


@router.get(
    "/channels/{channel}/product/{product_id}",
    response_model=ChannelPriceResponse,
    summary="Get Channel Price for Product",
    description="Get channel-specific price for a product"
)
async def get_channel_price_for_product(
    channel: str,
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get channel price for a product"""
    service = PricingService(db)
    price = await service.get_channel_price(product_id=product_id, channel=channel)
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel price not found"
        )
    return price


@router.get(
    "/channels/{channel}/variant/{variant_id}",
    response_model=ChannelPriceResponse,
    summary="Get Channel Price for Variant",
    description="Get channel-specific price for a product variant"
)
async def get_channel_price_for_variant(
    channel: str,
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get channel price for a variant"""
    service = PricingService(db)
    price = await service.get_channel_price(variant_id=variant_id, channel=channel)
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel price not found"
        )
    return price


@router.get(
    "/channels/variant/{variant_id}",
    response_model=List[ChannelPriceResponse],
    summary="Get All Channel Prices for Variant",
    description="Get all channel prices for a product variant"
)
async def get_all_channel_prices(
    variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all channel prices for a variant"""
    service = PricingService(db)
    return await service.get_all_channel_prices(variant_id)


# ==================== Volume Discounts ====================

@router.post(
    "/volume-discounts",
    response_model=VolumeDiscountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Volume Discount",
    description="Create a new volume discount tier"
)
async def create_volume_discount(
    data: VolumeDiscountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a volume discount"""
    service = PricingService(db)
    discount = await service.create_volume_discount(data, created_by_id=current_user.id)
    await db.commit()
    return discount


@router.get(
    "/volume-discounts",
    response_model=VolumeDiscountListResponse,
    summary="List Volume Discounts",
    description="List volume discount tiers with filters"
)
async def list_volume_discounts(
    product_id: Optional[UUID] = Query(None),
    variant_id: Optional[UUID] = Query(None),
    category_id: Optional[UUID] = Query(None),
    channel: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List volume discounts"""
    service = PricingService(db)
    discounts = await service.get_volume_discount_tiers(
        product_id=product_id,
        variant_id=variant_id,
        category_id=category_id,
        channel=channel
    )
    return VolumeDiscountListResponse(
        items=[VolumeDiscountResponse.model_validate(d) for d in discounts],
        total=len(discounts)
    )


@router.get(
    "/volume-discounts/{discount_id}",
    response_model=VolumeDiscountResponse,
    summary="Get Volume Discount",
    description="Get a volume discount by ID"
)
async def get_volume_discount(
    discount_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a volume discount"""
    service = PricingService(db)
    discount = await service.get_volume_discount(discount_id)
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume discount not found"
        )
    return discount


@router.put(
    "/volume-discounts/{discount_id}",
    response_model=VolumeDiscountResponse,
    summary="Update Volume Discount",
    description="Update a volume discount"
)
async def update_volume_discount(
    discount_id: UUID,
    data: VolumeDiscountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a volume discount"""
    service = PricingService(db)
    discount = await service.update_volume_discount(discount_id, data)
    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume discount not found"
        )
    await db.commit()
    return discount


@router.delete(
    "/volume-discounts/{discount_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Volume Discount",
    description="Delete a volume discount"
)
async def delete_volume_discount(
    discount_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a volume discount"""
    service = PricingService(db)
    deleted = await service.delete_volume_discount(discount_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume discount not found"
        )
    await db.commit()


# ==================== Promotions ====================

@router.post(
    "/promotions",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Promotion",
    description="Create a new promotional campaign"
)
async def create_promotion(
    data: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a promotion"""
    service = PricingService(db)
    
    # Check for duplicate code
    existing = await service.get_promotion_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Promotion code already exists"
        )
    
    promo = await service.create_promotion(data, created_by_id=current_user.id)
    await db.commit()
    return promo


@router.get(
    "/promotions",
    response_model=PromotionListResponse,
    summary="List Promotions",
    description="List promotions with filters and pagination"
)
async def list_promotions(
    search: Optional[str] = Query(None, description="Search in name, code, description"),
    statuses: Optional[List[PricingRuleStatus]] = Query(None, description="Filter by statuses"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    auto_apply: Optional[bool] = Query(None, description="Filter by auto-apply"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("start_date", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List promotions"""
    service = PricingService(db)
    promos, total = await service.list_promotions(
        search=search,
        statuses=statuses,
        channel=channel,
        auto_apply=auto_apply,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return PromotionListResponse(
        items=[PromotionResponse.model_validate(p) for p in promos],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/promotions/{promotion_id}",
    response_model=PromotionResponse,
    summary="Get Promotion",
    description="Get a promotion by ID"
)
async def get_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a promotion by ID"""
    service = PricingService(db)
    promo = await service.get_promotion(promotion_id)
    if not promo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    return promo


@router.put(
    "/promotions/{promotion_id}",
    response_model=PromotionResponse,
    summary="Update Promotion",
    description="Update a promotion"
)
async def update_promotion(
    promotion_id: UUID,
    data: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a promotion"""
    service = PricingService(db)
    promo = await service.update_promotion(promotion_id, data)
    if not promo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    await db.commit()
    return promo


@router.delete(
    "/promotions/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Promotion",
    description="Delete a promotion"
)
async def delete_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a promotion"""
    service = PricingService(db)
    deleted = await service.delete_promotion(promotion_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found"
        )
    await db.commit()


@router.post(
    "/promotions/validate",
    response_model=PromotionValidationResponse,
    summary="Validate Promotion Code",
    description="Validate a promotion code for an order"
)
async def validate_promotion_code(
    request: PromotionValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Validate a promotion code"""
    service = PricingService(db)
    return await service.validate_promotion(request)


# ==================== Price History ====================

@router.get(
    "/history",
    response_model=PriceHistoryListResponse,
    summary="Get Price History",
    description="Get price change history for a product"
)
async def get_price_history(
    product_id: Optional[UUID] = Query(None),
    variant_id: Optional[UUID] = Query(None),
    channel: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get price history"""
    if not product_id and not variant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either product_id or variant_id is required"
        )
    
    service = PricingService(db)
    history, total = await service.get_price_history(
        product_id=product_id,
        variant_id=variant_id,
        channel=channel,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return PriceHistoryListResponse(
        items=[PriceHistoryResponse.model_validate(h) for h in history],
        total=total,
        skip=skip,
        limit=limit
    )


# ==================== Competitor Pricing ====================

@router.post(
    "/competitors",
    response_model=CompetitorPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Competitor Price",
    description="Add a competitor price observation"
)
async def add_competitor_price(
    data: CompetitorPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add competitor price observation"""
    service = PricingService(db)
    price = await service.add_competitor_price(data)
    await db.commit()
    return price


@router.get(
    "/competitors",
    response_model=List[CompetitorPriceResponse],
    summary="Get Competitor Prices",
    description="Get latest competitor prices for a product"
)
async def get_competitor_prices(
    product_id: Optional[UUID] = Query(None),
    variant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get competitor prices"""
    if not product_id and not variant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either product_id or variant_id is required"
        )
    
    service = PricingService(db)
    return await service.get_competitor_prices(
        product_id=product_id,
        variant_id=variant_id
    )


@router.get(
    "/competitors/comparison",
    response_model=CompetitorPriceComparisonResponse,
    summary="Get Price Comparison",
    description="Get price comparison with competitors"
)
async def get_price_comparison(
    product_id: Optional[UUID] = Query(None),
    variant_id: Optional[UUID] = Query(None),
    channel: str = Query("retail"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get price comparison with competitors"""
    if not product_id and not variant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either product_id or variant_id is required"
        )
    
    service = PricingService(db)
    return await service.get_price_comparison(
        product_id=product_id,
        variant_id=variant_id,
        channel=channel
    )


@router.get(
    "/competitors/tracked",
    response_model=List[str],
    summary="Get Tracked Competitors",
    description="Get list of all tracked competitor names"
)
async def get_tracked_competitors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tracked competitors"""
    service = PricingService(db)
    return await service.get_tracked_competitors()


# ==================== Customer Tiers ====================

@router.post(
    "/customer-tiers",
    response_model=CustomerPricingTierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Customer Tier",
    description="Assign a pricing tier to a customer"
)
async def assign_customer_tier(
    data: CustomerPricingTierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign customer pricing tier"""
    if not data.user_id and not data.wholesale_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or wholesale_customer_id is required"
        )
    
    service = PricingService(db)
    tier = await service.assign_customer_tier(data, assigned_by_id=current_user.id)
    await db.commit()
    return tier


@router.get(
    "/customer-tiers/{user_id}",
    response_model=CustomerPricingTierResponse,
    summary="Get Customer Tier",
    description="Get customer's current pricing tier"
)
async def get_customer_tier(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer tier"""
    service = PricingService(db)
    tier = await service.get_customer_tier(user_id=user_id)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer tier not found"
        )
    return tier


@router.get(
    "/customer-tiers/wholesale/{customer_id}",
    response_model=CustomerPricingTierResponse,
    summary="Get Wholesale Customer Tier",
    description="Get wholesale customer's current pricing tier"
)
async def get_wholesale_customer_tier(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get wholesale customer tier"""
    service = PricingService(db)
    tier = await service.get_customer_tier(wholesale_customer_id=customer_id)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer tier not found"
        )
    return tier


@router.get(
    "/customer-tiers/by-tier/{tier}",
    response_model=List[CustomerPricingTierResponse],
    summary="Get Customers by Tier",
    description="Get all customers in a specific tier"
)
async def get_customers_by_tier(
    tier: CustomerTier,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customers by tier"""
    service = PricingService(db)
    tiers = await service.get_customers_by_tier(tier, skip=skip, limit=limit)
    return [CustomerPricingTierResponse.model_validate(t) for t in tiers]


# ==================== Dashboard & Analytics ====================

@router.get(
    "/dashboard",
    response_model=PricingDashboard,
    summary="Get Pricing Dashboard",
    description="Get pricing engine dashboard data"
)
async def get_pricing_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pricing dashboard"""
    service = PricingService(db)
    return await service.get_pricing_dashboard()


@router.get(
    "/analytics",
    response_model=PricingAnalytics,
    summary="Get Pricing Analytics",
    description="Get pricing analytics for a period"
)
async def get_pricing_analytics(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pricing analytics"""
    service = PricingService(db)
    return await service.get_pricing_analytics(start_date, end_date)
