"""
Pricing Engine Service

Core pricing engine service that handles:
- Dynamic price calculation with rule application
- Channel-specific pricing
- Volume-based discounts
- Promotional pricing with promo code validation
- Customer-specific pricing based on tiers
- Price history tracking
- Competitor price analysis
"""

from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import (
    PricingRule,
    PricingRuleProduct,
    PricingRuleCategory,
    PricingRuleCustomer,
    ChannelPrice,
    VolumeDiscount,
    Promotion,
    PromotionUsage,
    PriceHistory,
    CompetitorPrice,
    CustomerPricingTier,
    PricingRuleStatus,
    PricingRuleType,
    DiscountType,
    CustomerTier,
    PriceChangeReason
)
from app.repositories.pricing import (
    PricingRuleRepository,
    ChannelPriceRepository,
    VolumeDiscountRepository,
    PromotionRepository,
    PriceHistoryRepository,
    CompetitorPriceRepository,
    CustomerPricingTierRepository
)
from app.schemas.pricing import (
    PricingRuleCreate,
    PricingRuleUpdate,
    ChannelPriceCreate,
    ChannelPriceUpdate,
    VolumeDiscountCreate,
    VolumeDiscountUpdate,
    PromotionCreate,
    PromotionUpdate,
    PriceCalculationRequest,
    PriceCalculationResponse,
    AppliedDiscount,
    PromotionValidationRequest,
    PromotionValidationResponse,
    CompetitorPriceCreate,
    CompetitorPriceComparisonResponse,
    CustomerPricingTierCreate,
    PricingDashboard,
    PricingAnalytics
)


class PricingService:
    """
    Core pricing engine service
    
    Handles all pricing calculations and rule applications
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_repo = PricingRuleRepository(db)
        self.channel_price_repo = ChannelPriceRepository(db)
        self.volume_repo = VolumeDiscountRepository(db)
        self.promo_repo = PromotionRepository(db)
        self.history_repo = PriceHistoryRepository(db)
        self.competitor_repo = CompetitorPriceRepository(db)
        self.tier_repo = CustomerPricingTierRepository(db)
    
    # ==================== Price Calculation ====================
    
    async def calculate_price(
        self,
        request: PriceCalculationRequest
    ) -> PriceCalculationResponse:
        """
        Calculate final price for a product/variant
        
        Applies pricing rules, volume discounts, customer tier discounts,
        and promotions in the correct order of priority.
        """
        applied_discounts: List[AppliedDiscount] = []
        
        # Step 1: Get base price (channel-specific or fallback)
        base_price = request.base_price
        channel_price = await self.channel_price_repo.get_price_for_product(
            product_id=request.product_id,
            variant_id=request.variant_id,
            channel=request.channel
        )
        
        if channel_price:
            base_price = channel_price.base_price
            compare_at_price = channel_price.compare_at_price
            min_price = channel_price.min_price
        else:
            compare_at_price = request.compare_at_price
            min_price = None
        
        original_price = base_price
        current_price = base_price
        
        # Step 2: Get customer tier discount
        customer_tier_name = None
        if request.user_id or request.wholesale_customer_id:
            tier = await self.tier_repo.get_customer_tier(
                user_id=request.user_id,
                wholesale_customer_id=request.wholesale_customer_id
            )
            if tier and tier.discount_percentage > 0:
                customer_tier_name = tier.tier.value
                tier_discount = current_price * (tier.discount_percentage / 100)
                tier_discount = tier_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                current_price -= tier_discount
                
                applied_discounts.append(AppliedDiscount(
                    discount_type=DiscountType.PERCENTAGE,
                    discount_value=tier.discount_percentage,
                    discount_amount=tier_discount,
                    source="customer_tier",
                    name=f"{tier.tier.value} Tier Discount"
                ))
        
        # Step 3: Apply pricing rules (sorted by priority)
        rules = await self.rule_repo.get_rules_for_product(
            product_id=request.product_id,
            variant_id=request.variant_id,
            category_id=request.category_id,
            channel=request.channel,
            customer_tier=customer_tier_name
        )
        
        non_stackable_applied = False
        for rule in rules:
            # Check if rule conditions are met
            if not self._check_rule_conditions(rule, request):
                continue
            
            # Check time restrictions
            if not self._check_time_restrictions(rule):
                continue
            
            # Check usage limits
            if rule.max_uses and rule.current_uses >= rule.max_uses:
                continue
            
            # Skip if non-stackable rule already applied
            if non_stackable_applied and not rule.is_stackable:
                continue
            
            # Calculate discount
            discount_amount = self._calculate_discount(
                rule.discount_type,
                rule.discount_value,
                current_price,
                request.quantity
            )
            
            if discount_amount > 0:
                # Apply max discount cap if set
                if rule.max_discount_amount:
                    discount_amount = min(discount_amount, rule.max_discount_amount)
                
                current_price -= discount_amount
                
                applied_discounts.append(AppliedDiscount(
                    discount_type=rule.discount_type,
                    discount_value=rule.discount_value,
                    discount_amount=discount_amount,
                    source="pricing_rule",
                    rule_id=rule.id,
                    name=rule.name
                ))
                
                if not rule.is_stackable:
                    non_stackable_applied = True
        
        # Step 4: Apply volume discounts
        volume_discounts = await self.volume_repo.get_applicable_discounts(
            product_id=request.product_id,
            variant_id=request.variant_id,
            category_id=request.category_id,
            quantity=request.quantity,
            channel=request.channel,
            customer_tier=customer_tier_name
        )
        
        # Get the best volume discount (highest discount amount)
        best_volume_discount = None
        best_volume_amount = Decimal("0")
        
        for vd in volume_discounts:
            amount = self._calculate_discount(
                vd.discount_type,
                vd.discount_value,
                current_price,
                request.quantity
            )
            if amount > best_volume_amount:
                best_volume_amount = amount
                best_volume_discount = vd
        
        if best_volume_discount:
            # Apply max discount if set
            if best_volume_discount.max_discount_amount:
                best_volume_amount = min(
                    best_volume_amount,
                    best_volume_discount.max_discount_amount
                )
            
            current_price -= best_volume_amount
            
            applied_discounts.append(AppliedDiscount(
                discount_type=best_volume_discount.discount_type,
                discount_value=best_volume_discount.discount_value,
                discount_amount=best_volume_amount,
                source="volume_discount",
                name=f"Volume Discount ({best_volume_discount.min_quantity}+ items)"
            ))
        
        # Step 5: Apply promotion code if provided
        promotion = None
        promo_discount = Decimal("0")
        
        if request.promotion_code:
            valid, promo, message = await self.promo_repo.validate_promotion(
                code=request.promotion_code,
                channel=request.channel,
                order_value=current_price * request.quantity,
                user_id=request.user_id,
                wholesale_customer_id=request.wholesale_customer_id
            )
            
            if valid and promo:
                promotion = promo
                promo_discount = self._calculate_discount(
                    promo.discount_type,
                    promo.discount_value,
                    current_price,
                    request.quantity
                )
                
                if promo.max_discount_amount:
                    promo_discount = min(promo_discount, promo.max_discount_amount)
                
                current_price -= promo_discount
                
                applied_discounts.append(AppliedDiscount(
                    discount_type=promo.discount_type,
                    discount_value=promo.discount_value,
                    discount_amount=promo_discount,
                    source="promotion",
                    promotion_id=promo.id,
                    name=promo.name
                ))
        
        # Step 6: Apply auto-apply promotions
        if not request.promotion_code:
            auto_promos = await self.promo_repo.get_active_promotions(
                channel=request.channel,
                auto_apply_only=True
            )
            
            for promo in auto_promos:
                # Check minimum order value
                if promo.min_order_value and (current_price * request.quantity) < promo.min_order_value:
                    continue
                
                auto_discount = self._calculate_discount(
                    promo.discount_type,
                    promo.discount_value,
                    current_price,
                    request.quantity
                )
                
                if auto_discount > 0:
                    if promo.max_discount_amount:
                        auto_discount = min(auto_discount, promo.max_discount_amount)
                    
                    current_price -= auto_discount
                    
                    applied_discounts.append(AppliedDiscount(
                        discount_type=promo.discount_type,
                        discount_value=promo.discount_value,
                        discount_amount=auto_discount,
                        source="promotion",
                        promotion_id=promo.id,
                        name=f"{promo.name} (Auto-applied)"
                    ))
                    break  # Only apply one auto-promotion
        
        # Ensure price doesn't go below minimum
        if min_price and current_price < min_price:
            current_price = min_price
        
        # Ensure price is not negative
        if current_price < 0:
            current_price = Decimal("0")
        
        # Calculate totals
        total_discount = original_price - current_price
        discount_percentage = (total_discount / original_price * 100) if original_price > 0 else Decimal("0")
        
        line_total = current_price * request.quantity
        original_line_total = original_price * request.quantity
        
        return PriceCalculationResponse(
            original_price=original_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            final_price=current_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            discount_amount=total_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            discount_percentage=discount_percentage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            applied_discounts=applied_discounts,
            quantity=request.quantity,
            line_total=line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            original_line_total=original_line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            compare_at_price=compare_at_price,
            currency=request.currency
        )
    
    def _check_rule_conditions(
        self,
        rule: PricingRule,
        request: PriceCalculationRequest
    ) -> bool:
        """Check if rule conditions are met"""
        if not rule.conditions:
            return True
        
        conditions = rule.conditions
        
        # Check minimum quantity
        if "min_quantity" in conditions:
            if request.quantity < conditions["min_quantity"]:
                return False
        
        # Check maximum quantity
        if "max_quantity" in conditions:
            if request.quantity > conditions["max_quantity"]:
                return False
        
        # Check minimum order value
        if "min_order_value" in conditions and request.order_total:
            if request.order_total < Decimal(str(conditions["min_order_value"])):
                return False
        
        return True
    
    def _check_time_restrictions(self, rule: PricingRule) -> bool:
        """Check if current time is within rule's time restrictions"""
        now = datetime.now()
        
        # Check day of week restrictions (0=Monday, 6=Sunday in the model)
        if rule.applicable_days:
            current_day = now.weekday()  # 0=Monday, 6=Sunday
            if current_day not in rule.applicable_days:
                return False
        
        # Check time of day restrictions
        if rule.start_time and rule.end_time:
            current_time = now.strftime("%H:%M")
            if not (rule.start_time <= current_time <= rule.end_time):
                return False
        
        return True
    
    def _calculate_discount(
        self,
        discount_type: DiscountType,
        discount_value: Decimal,
        price: Decimal,
        quantity: int
    ) -> Decimal:
        """Calculate discount amount based on type"""
        if discount_type == DiscountType.PERCENTAGE:
            return (price * discount_value / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif discount_type == DiscountType.FIXED_AMOUNT:
            return discount_value
        elif discount_type == DiscountType.FIXED_PRICE:
            if discount_value < price:
                return price - discount_value
            return Decimal("0")
        elif discount_type == DiscountType.BUY_X_GET_Y:
            # discount_value is in format: {"buy": X, "get": Y, "discount_percent": Z}
            # For simplicity, return 0 here - handle in cart level
            return Decimal("0")
        
        return Decimal("0")
    
    # ==================== Pricing Rules ====================
    
    async def create_pricing_rule(
        self,
        data: PricingRuleCreate,
        created_by_id: Optional[UUID] = None
    ) -> PricingRule:
        """Create a new pricing rule"""
        rule_data = data.model_dump(exclude={"product_ids", "variant_ids", "category_ids", "customer_ids", "products", "categories", "customers"})
        rule_data["created_by_id"] = created_by_id
        
        rule = await self.rule_repo.create(rule_data)
        
        # Add product associations
        if data.product_ids:
            for pid in data.product_ids:
                assoc = PricingRuleProduct(
                    pricing_rule_id=rule.id,
                    product_id=pid
                )
                self.db.add(assoc)
        
        if data.variant_ids:
            for vid in data.variant_ids:
                assoc = PricingRuleProduct(
                    pricing_rule_id=rule.id,
                    product_variant_id=vid
                )
                self.db.add(assoc)
        
        # Add category associations
        if data.category_ids:
            for cid in data.category_ids:
                assoc = PricingRuleCategory(
                    pricing_rule_id=rule.id,
                    category_id=cid
                )
                self.db.add(assoc)
        
        # Add customer associations
        if data.customer_ids:
            for cust_id in data.customer_ids:
                assoc = PricingRuleCustomer(
                    pricing_rule_id=rule.id,
                    wholesale_customer_id=cust_id
                )
                self.db.add(assoc)
        
        await self.db.flush()
        await self.db.refresh(rule)
        return rule
    
    async def update_pricing_rule(
        self,
        rule_id: UUID,
        data: PricingRuleUpdate
    ) -> Optional[PricingRule]:
        """Update a pricing rule"""
        update_data = data.model_dump(exclude_unset=True)
        return await self.rule_repo.update(rule_id, update_data)
    
    async def get_pricing_rule(self, rule_id: UUID) -> Optional[PricingRule]:
        """Get a pricing rule by ID"""
        return await self.rule_repo.get_by_id(rule_id)
    
    async def list_pricing_rules(
        self,
        search: Optional[str] = None,
        rule_types: Optional[List[PricingRuleType]] = None,
        statuses: Optional[List[PricingRuleStatus]] = None,
        channel: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "priority",
        sort_order: str = "desc"
    ) -> Tuple[List[PricingRule], int]:
        """List pricing rules with filters"""
        return await self.rule_repo.search_rules(
            search=search,
            rule_types=rule_types,
            statuses=statuses,
            channel=channel,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def delete_pricing_rule(self, rule_id: UUID) -> bool:
        """Delete a pricing rule"""
        return await self.rule_repo.delete(rule_id)
    
    async def activate_rule(self, rule_id: UUID) -> Optional[PricingRule]:
        """Activate a pricing rule"""
        return await self.rule_repo.activate_rule(rule_id)
    
    async def deactivate_rule(self, rule_id: UUID) -> Optional[PricingRule]:
        """Deactivate a pricing rule"""
        return await self.rule_repo.deactivate_rule(rule_id)
    
    # ==================== Channel Pricing ====================
    
    async def set_channel_price(
        self,
        data: ChannelPriceCreate,
        changed_by_id: Optional[UUID] = None
    ) -> ChannelPrice:
        """Set or update channel-specific pricing"""
        # Get existing price for history
        existing = await self.channel_price_repo.get_price_for_product(
            product_id=data.product_id,
            variant_id=data.product_variant_id,
            channel=data.channel
        )
        
        old_price = existing.base_price if existing else None
        
        # Upsert channel price
        channel_price = await self.channel_price_repo.upsert_channel_price(
            product_id=data.product_id,
            variant_id=data.product_variant_id,
            channel=data.channel,
            base_price=data.base_price,
            compare_at_price=data.compare_at_price,
            cost_price=data.cost_price,
            min_price=data.min_price
        )
        
        # Record price history
        await self.history_repo.record_price_change(
            product_id=data.product_id,
            variant_id=data.product_variant_id,
            old_price=old_price,
            new_price=data.base_price,
            change_reason=PriceChangeReason.CHANNEL_PRICE,
            channel=data.channel,
            old_cost=existing.cost_price if existing else None,
            new_cost=data.cost_price,
            changed_by_id=changed_by_id
        )
        
        await self.db.commit()
        return channel_price
    
    async def get_channel_price(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        channel: str = None
    ) -> Optional[ChannelPrice]:
        """Get channel price for a product"""
        return await self.channel_price_repo.get_price_for_product(
            product_id=product_id,
            variant_id=variant_id,
            channel=channel
        )
    
    async def get_all_channel_prices(
        self,
        variant_id: UUID
    ) -> List[ChannelPrice]:
        """Get all channel prices for a variant"""
        return list(await self.channel_price_repo.get_all_prices_for_variant(variant_id))
    
    # ==================== Volume Discounts ====================
    
    async def create_volume_discount(
        self,
        data: VolumeDiscountCreate,
        created_by_id: Optional[UUID] = None
    ) -> VolumeDiscount:
        """Create a volume discount tier"""
        discount_data = data.model_dump()
        discount_data["created_by_id"] = created_by_id
        return await self.volume_repo.create(discount_data)
    
    async def update_volume_discount(
        self,
        discount_id: UUID,
        data: VolumeDiscountUpdate
    ) -> Optional[VolumeDiscount]:
        """Update a volume discount"""
        update_data = data.model_dump(exclude_unset=True)
        return await self.volume_repo.update(discount_id, update_data)
    
    async def get_volume_discount(self, discount_id: UUID) -> Optional[VolumeDiscount]:
        """Get a volume discount by ID"""
        return await self.volume_repo.get_by_id(discount_id)
    
    async def get_volume_discount_tiers(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        channel: Optional[str] = None
    ) -> List[VolumeDiscount]:
        """Get volume discount tiers for display"""
        return list(await self.volume_repo.get_discount_tiers(
            product_id=product_id,
            variant_id=variant_id,
            category_id=category_id,
            channel=channel
        ))
    
    async def delete_volume_discount(self, discount_id: UUID) -> bool:
        """Delete a volume discount"""
        return await self.volume_repo.delete(discount_id)
    
    # ==================== Promotions ====================
    
    async def create_promotion(
        self,
        data: PromotionCreate,
        created_by_id: Optional[UUID] = None
    ) -> Promotion:
        """Create a new promotion"""
        promo_data = data.model_dump()
        promo_data["created_by_id"] = created_by_id
        return await self.promo_repo.create(promo_data)
    
    async def update_promotion(
        self,
        promotion_id: UUID,
        data: PromotionUpdate
    ) -> Optional[Promotion]:
        """Update a promotion"""
        update_data = data.model_dump(exclude_unset=True)
        return await self.promo_repo.update(promotion_id, update_data)
    
    async def get_promotion(self, promotion_id: UUID) -> Optional[Promotion]:
        """Get a promotion by ID"""
        return await self.promo_repo.get_by_id(promotion_id)
    
    async def get_promotion_by_code(self, code: str) -> Optional[Promotion]:
        """Get a promotion by code"""
        return await self.promo_repo.get_by_code(code)
    
    async def list_promotions(
        self,
        search: Optional[str] = None,
        statuses: Optional[List[PricingRuleStatus]] = None,
        channel: Optional[str] = None,
        auto_apply: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "start_date",
        sort_order: str = "desc"
    ) -> Tuple[List[Promotion], int]:
        """List promotions with filters"""
        return await self.promo_repo.search_promotions(
            search=search,
            statuses=statuses,
            channel=channel,
            auto_apply=auto_apply,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def validate_promotion(
        self,
        request: PromotionValidationRequest
    ) -> PromotionValidationResponse:
        """Validate a promotion code"""
        valid, promo, message = await self.promo_repo.validate_promotion(
            code=request.code,
            channel=request.channel,
            order_value=request.order_value,
            user_id=request.user_id,
            wholesale_customer_id=request.wholesale_customer_id
        )
        
        return PromotionValidationResponse(
            valid=valid,
            message=message,
            promotion_id=promo.id if promo else None,
            promotion_name=promo.name if promo else None,
            discount_type=promo.discount_type if promo else None,
            discount_value=promo.discount_value if promo else None,
            min_order_value=promo.min_order_value if promo else None,
            max_discount_amount=promo.max_discount_amount if promo else None
        )
    
    async def record_promotion_usage(
        self,
        promotion_id: UUID,
        order_id: UUID,
        discount_amount: Decimal,
        order_total_before: Decimal,
        order_total_after: Decimal,
        user_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None
    ) -> PromotionUsage:
        """Record promotion usage"""
        return await self.promo_repo.record_usage(
            promotion_id=promotion_id,
            order_id=order_id,
            discount_amount=discount_amount,
            order_total_before=order_total_before,
            order_total_after=order_total_after,
            user_id=user_id,
            wholesale_customer_id=wholesale_customer_id
        )
    
    async def delete_promotion(self, promotion_id: UUID) -> bool:
        """Delete a promotion"""
        return await self.promo_repo.delete(promotion_id)
    
    # ==================== Price History ====================
    
    async def get_price_history(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[PriceHistory], int]:
        """Get price history for a product"""
        return await self.history_repo.get_history_for_product(
            product_id=product_id,
            variant_id=variant_id,
            channel=channel,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    
    async def record_price_change(
        self,
        product_id: Optional[UUID],
        variant_id: Optional[UUID],
        old_price: Optional[Decimal],
        new_price: Decimal,
        change_reason: PriceChangeReason,
        channel: Optional[str] = None,
        old_cost: Optional[Decimal] = None,
        new_cost: Optional[Decimal] = None,
        changed_by_id: Optional[UUID] = None,
        pricing_rule_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> PriceHistory:
        """Manually record a price change"""
        return await self.history_repo.record_price_change(
            product_id=product_id,
            variant_id=variant_id,
            old_price=old_price,
            new_price=new_price,
            change_reason=change_reason,
            channel=channel,
            old_cost=old_cost,
            new_cost=new_cost,
            changed_by_id=changed_by_id,
            pricing_rule_id=pricing_rule_id,
            notes=notes,
            extra_data=extra_data
        )
    
    # ==================== Competitor Pricing ====================
    
    async def add_competitor_price(
        self,
        data: CompetitorPriceCreate
    ) -> CompetitorPrice:
        """Add a competitor price observation"""
        return await self.competitor_repo.add_competitor_price(
            product_id=data.product_id,
            variant_id=data.product_variant_id,
            competitor_name=data.competitor_name,
            price=data.price,
            source=data.source,
            competitor_url=data.competitor_url,
            competitor_product_name=data.competitor_product_name,
            competitor_sku=data.competitor_sku,
            sale_price=data.sale_price,
            in_stock=data.in_stock,
            match_confidence=data.match_confidence,
            extra_data=data.extra_data
        )
    
    async def get_competitor_prices(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None
    ) -> List[CompetitorPrice]:
        """Get latest competitor prices for a product"""
        return list(await self.competitor_repo.get_latest_prices(
            product_id=product_id,
            variant_id=variant_id
        ))
    
    async def get_price_comparison(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        channel: str = "retail"
    ) -> CompetitorPriceComparisonResponse:
        """Get price comparison with competitors"""
        # Get our price
        our_price = await self.channel_price_repo.get_price_for_product(
            product_id=product_id,
            variant_id=variant_id,
            channel=channel
        )
        
        # Get competitor prices
        competitor_prices = await self.competitor_repo.get_latest_prices(
            product_id=product_id,
            variant_id=variant_id
        )
        
        base_price = our_price.base_price if our_price else Decimal("0")
        
        comparisons = []
        for cp in competitor_prices:
            diff = cp.price - base_price
            diff_pct = (diff / base_price * 100) if base_price > 0 else Decimal("0")
            
            comparisons.append({
                "competitor_name": cp.competitor_name,
                "price": cp.price,
                "sale_price": cp.sale_price,
                "in_stock": cp.in_stock,
                "difference": diff.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "difference_percentage": diff_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "last_updated": cp.observed_at
            })
        
        # Calculate statistics
        comp_prices = [cp.price for cp in competitor_prices]
        avg_competitor = sum(comp_prices) / len(comp_prices) if comp_prices else Decimal("0")
        min_competitor = min(comp_prices) if comp_prices else Decimal("0")
        max_competitor = max(comp_prices) if comp_prices else Decimal("0")
        
        position = "lowest"
        if base_price > avg_competitor:
            position = "above_average"
        elif base_price < avg_competitor:
            position = "below_average"
        
        return CompetitorPriceComparisonResponse(
            product_id=product_id,
            variant_id=variant_id,
            our_price=base_price,
            competitor_prices=comparisons,
            average_competitor_price=avg_competitor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            lowest_competitor_price=min_competitor,
            highest_competitor_price=max_competitor,
            our_position=position,
            price_index=(base_price / avg_competitor * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if avg_competitor > 0 else Decimal("100")
        )
    
    async def get_tracked_competitors(self) -> List[str]:
        """Get list of all tracked competitors"""
        return await self.competitor_repo.get_tracked_competitors()
    
    # ==================== Customer Tiers ====================
    
    async def assign_customer_tier(
        self,
        data: CustomerPricingTierCreate,
        assigned_by_id: Optional[UUID] = None
    ) -> CustomerPricingTier:
        """Assign a pricing tier to a customer"""
        return await self.tier_repo.assign_tier(
            tier=data.tier,
            user_id=data.user_id,
            wholesale_customer_id=data.wholesale_customer_id,
            discount_percentage=data.discount_percentage,
            assignment_reason=data.assignment_reason,
            effective_from=data.effective_from,
            effective_until=data.effective_until,
            is_automatic=data.is_automatic
        )
    
    async def get_customer_tier(
        self,
        user_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None
    ) -> Optional[CustomerPricingTier]:
        """Get customer's current pricing tier"""
        return await self.tier_repo.get_customer_tier(
            user_id=user_id,
            wholesale_customer_id=wholesale_customer_id
        )
    
    async def get_customers_by_tier(
        self,
        tier: CustomerTier,
        skip: int = 0,
        limit: int = 100
    ) -> List[CustomerPricingTier]:
        """Get all customers in a tier"""
        return list(await self.tier_repo.get_customers_by_tier(tier, skip, limit))
    
    # ==================== Analytics & Dashboard ====================
    
    async def get_pricing_dashboard(self) -> PricingDashboard:
        """Get pricing dashboard data"""
        # Get rule counts
        _, active_rules_total = await self.rule_repo.search_rules(
            statuses=[PricingRuleStatus.ACTIVE],
            limit=1
        )
        all_rules, total_rules = await self.rule_repo.search_rules(limit=1)
        
        # Get promotion counts
        active_promos = await self.promo_repo.get_active_promotions()
        all_promos, total_promos = await self.promo_repo.search_promotions(limit=1)
        
        # Get volume discounts count
        volume_discounts = await self.volume_repo.get_all()
        
        # Get competitor tracking info
        tracked_competitors = await self.competitor_repo.get_tracked_competitors()
        
        return PricingDashboard(
            active_rules_count=active_rules_total,
            active_promotions_count=len(active_promos),
            volume_discounts_count=len(volume_discounts),
            total_promo_uses=sum(p.current_uses for p in active_promos),
            total_promo_savings=Decimal("0"),  # Would need additional query for actual savings
            recent_price_changes=0,  # Would need additional query
            products_tracked=0,  # Would need additional query
            competitors_tracked=len(tracked_competitors),
            top_promotions=[],
            recent_rules=[]
        )
    
    async def get_pricing_analytics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> PricingAnalytics:
        """Get pricing analytics for a period"""
        # This would include:
        # - Revenue impact of pricing rules
        # - Discount distribution
        # - Promotion performance
        # - Price elasticity analysis
        
        return PricingAnalytics(
            period_start=start_date,
            period_end=end_date,
            total_discounts_given=Decimal("0"),  # Would need order data
            average_discount_percentage=Decimal("0"),
            most_used_rules=[],
            most_used_promotions=[],
            revenue_impact=Decimal("0")
        )
