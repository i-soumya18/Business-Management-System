"""
Pricing Engine Repository

Repository layer for pricing rules, channel pricing, volume discounts,
promotions, price history, and competitor price monitoring.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Sequence
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_, desc, asc, cast, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import JSONB

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
    CustomerTier,
    PriceChangeReason
)
from app.repositories.base import BaseRepository


class PricingRuleRepository(BaseRepository[PricingRule]):
    """Repository for Pricing Rule operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PricingRule, db)
    
    async def get_by_code(self, code: str) -> Optional[PricingRule]:
        """Get pricing rule by code"""
        query = select(PricingRule).where(PricingRule.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_rules(
        self,
        rule_type: Optional[PricingRuleType] = None,
        channel: Optional[str] = None
    ) -> Sequence[PricingRule]:
        """Get active pricing rules"""
        now = datetime.utcnow()
        query = select(PricingRule).where(
            PricingRule.status == PricingRuleStatus.ACTIVE
        )
        
        # Check date validity
        query = query.where(
            or_(
                PricingRule.start_date.is_(None),
                PricingRule.start_date <= now
            )
        ).where(
            or_(
                PricingRule.end_date.is_(None),
                PricingRule.end_date >= now
            )
        )
        
        if rule_type:
            query = query.where(PricingRule.rule_type == rule_type)
        
        if channel:
            query = query.where(
                or_(
                    PricingRule.applicable_channels.is_(None),
                    cast(PricingRule.applicable_channels, JSONB) == cast(None, JSONB),  # JSON null
                    cast(PricingRule.applicable_channels, JSONB).contains(cast([channel], JSONB))
                )
            )
        
        query = query.order_by(desc(PricingRule.priority))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_rules_for_product(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        customer_tier: Optional[str] = None
    ) -> Sequence[PricingRule]:
        """Get applicable rules for a product/variant"""
        now = datetime.utcnow()
        
        # Start with active rules
        query = select(PricingRule).where(
            PricingRule.status == PricingRuleStatus.ACTIVE
        ).where(
            or_(
                PricingRule.start_date.is_(None),
                PricingRule.start_date <= now
            )
        ).where(
            or_(
                PricingRule.end_date.is_(None),
                PricingRule.end_date >= now
            )
        )
        
        # Channel filter - use raw SQL for JSON array containment
        # Note: JSON columns may store JSON null (not SQL NULL), so we check both
        if channel:
            # PostgreSQL @> operator for JSON array containment
            query = query.where(
                or_(
                    PricingRule.applicable_channels.is_(None),
                    cast(PricingRule.applicable_channels, JSONB) == cast(None, JSONB),  # JSON null
                    cast(PricingRule.applicable_channels, JSONB).contains(cast([channel], JSONB))
                )
            )
        
        # Customer tier filter - use raw SQL for JSON array containment
        # Note: JSON columns may store JSON null (not SQL NULL), so we check both
        if customer_tier:
            query = query.where(
                or_(
                    PricingRule.applicable_customer_tiers.is_(None),
                    cast(PricingRule.applicable_customer_tiers, JSONB) == cast(None, JSONB),  # JSON null
                    cast(PricingRule.applicable_customer_tiers, JSONB).contains(cast([customer_tier], JSONB))
                )
            )
        
        query = query.options(
            selectinload(PricingRule.product_rules),
            selectinload(PricingRule.category_rules)
        )
        
        query = query.order_by(desc(PricingRule.priority))
        result = await self.db.execute(query)
        rules = result.scalars().all()
        
        # Filter by product/variant/category associations
        applicable_rules = []
        for rule in rules:
            # Check product rules - only if there are actual product associations
            if rule.product_rules and len(rule.product_rules) > 0:
                product_match = False
                excluded = False
                for pr in rule.product_rules:
                    if pr.is_excluded:
                        if pr.product_id == product_id or pr.product_variant_id == variant_id:
                            excluded = True
                            break
                    else:
                        if pr.product_id == product_id or pr.product_variant_id == variant_id:
                            product_match = True
                
                if excluded:
                    continue
                if not product_match:
                    continue
            
            # Check category rules - only if there are actual category associations
            if rule.category_rules and len(rule.category_rules) > 0 and category_id:
                category_match = False
                for cr in rule.category_rules:
                    if not cr.is_excluded and cr.category_id == category_id:
                        category_match = True
                        break
                
                # Skip if no category match AND rule has no product rules
                if not category_match and (not rule.product_rules or len(rule.product_rules) == 0):
                    continue
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    async def search_rules(
        self,
        search: Optional[str] = None,
        rule_types: Optional[List[PricingRuleType]] = None,
        statuses: Optional[List[PricingRuleStatus]] = None,
        channel: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "priority",
        sort_order: str = "desc"
    ) -> tuple[Sequence[PricingRule], int]:
        """Search pricing rules with filters"""
        query = select(PricingRule)
        count_query = select(func.count()).select_from(PricingRule)
        
        # Apply filters
        if search:
            search_filter = or_(
                PricingRule.name.ilike(f"%{search}%"),
                PricingRule.code.ilike(f"%{search}%"),
                PricingRule.description.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if rule_types:
            query = query.where(PricingRule.rule_type.in_(rule_types))
            count_query = count_query.where(PricingRule.rule_type.in_(rule_types))
        
        if statuses:
            query = query.where(PricingRule.status.in_(statuses))
            count_query = count_query.where(PricingRule.status.in_(statuses))
        
        if channel:
            channel_filter = or_(
                PricingRule.applicable_channels.is_(None),
                cast(PricingRule.applicable_channels, JSONB) == cast(None, JSONB),  # JSON null
                cast(PricingRule.applicable_channels, JSONB).contains(cast([channel], JSONB))
            )
            query = query.where(channel_filter)
            count_query = count_query.where(channel_filter)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(PricingRule, sort_by, PricingRule.priority)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all(), total
    
    async def increment_usage(self, rule_id: UUID) -> None:
        """Increment usage count for a rule"""
        await self.db.execute(
            update(PricingRule)
            .where(PricingRule.id == rule_id)
            .values(current_uses=PricingRule.current_uses + 1)
        )
        await self.db.flush()
    
    async def activate_rule(self, rule_id: UUID) -> Optional[PricingRule]:
        """Activate a pricing rule"""
        rule = await self.get_by_id(rule_id)
        if rule:
            rule.status = PricingRuleStatus.ACTIVE
            await self.db.flush()
            await self.db.refresh(rule)
        return rule
    
    async def deactivate_rule(self, rule_id: UUID) -> Optional[PricingRule]:
        """Deactivate a pricing rule"""
        rule = await self.get_by_id(rule_id)
        if rule:
            rule.status = PricingRuleStatus.PAUSED
            await self.db.flush()
            await self.db.refresh(rule)
        return rule


class ChannelPriceRepository(BaseRepository[ChannelPrice]):
    """Repository for Channel Price operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(ChannelPrice, db)
    
    async def get_price_for_product(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        channel: str = None
    ) -> Optional[ChannelPrice]:
        """Get channel price for a product/variant"""
        query = select(ChannelPrice).where(
            ChannelPrice.channel == channel,
            ChannelPrice.is_active == True
        )
        
        if variant_id:
            query = query.where(ChannelPrice.product_variant_id == variant_id)
        elif product_id:
            query = query.where(ChannelPrice.product_id == product_id)
        else:
            return None
        
        now = datetime.utcnow()
        query = query.where(
            or_(
                ChannelPrice.effective_from.is_(None),
                ChannelPrice.effective_from <= now
            )
        ).where(
            or_(
                ChannelPrice.effective_until.is_(None),
                ChannelPrice.effective_until >= now
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_prices_for_channel(
        self,
        channel: str,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[ChannelPrice]:
        """Get all prices for a channel"""
        query = select(ChannelPrice).where(
            ChannelPrice.channel == channel,
            ChannelPrice.is_active == True
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_all_prices_for_variant(
        self,
        variant_id: UUID
    ) -> Sequence[ChannelPrice]:
        """Get all channel prices for a variant"""
        query = select(ChannelPrice).where(
            ChannelPrice.product_variant_id == variant_id,
            ChannelPrice.is_active == True
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def upsert_channel_price(
        self,
        product_id: Optional[UUID],
        variant_id: Optional[UUID],
        channel: str,
        base_price: Decimal,
        compare_at_price: Optional[Decimal] = None,
        cost_price: Optional[Decimal] = None,
        min_price: Optional[Decimal] = None
    ) -> ChannelPrice:
        """Create or update channel price"""
        existing = await self.get_price_for_product(
            product_id=product_id,
            variant_id=variant_id,
            channel=channel
        )
        
        if existing:
            existing.base_price = base_price
            existing.compare_at_price = compare_at_price
            existing.cost_price = cost_price
            existing.min_price = min_price
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            new_price = ChannelPrice(
                product_id=product_id,
                product_variant_id=variant_id,
                channel=channel,
                base_price=base_price,
                compare_at_price=compare_at_price,
                cost_price=cost_price,
                min_price=min_price
            )
            self.db.add(new_price)
            await self.db.flush()
            await self.db.refresh(new_price)
            return new_price


class VolumeDiscountRepository(BaseRepository[VolumeDiscount]):
    """Repository for Volume Discount operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(VolumeDiscount, db)
    
    async def get_applicable_discounts(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        quantity: int = 1,
        channel: Optional[str] = None,
        customer_tier: Optional[str] = None
    ) -> Sequence[VolumeDiscount]:
        """Get applicable volume discounts for a product"""
        now = datetime.utcnow()
        
        query = select(VolumeDiscount).where(
            VolumeDiscount.is_active == True,
            VolumeDiscount.min_quantity <= quantity
        )
        
        # Date validity
        query = query.where(
            or_(
                VolumeDiscount.start_date.is_(None),
                VolumeDiscount.start_date <= now
            )
        ).where(
            or_(
                VolumeDiscount.end_date.is_(None),
                VolumeDiscount.end_date >= now
            )
        )
        
        # Max quantity check
        query = query.where(
            or_(
                VolumeDiscount.max_quantity.is_(None),
                VolumeDiscount.max_quantity >= quantity
            )
        )
        
        # Channel filter
        if channel:
            query = query.where(
                or_(
                    VolumeDiscount.channel.is_(None),
                    VolumeDiscount.channel == channel
                )
            )
        
        # Customer tier filter
        if customer_tier:
            query = query.where(
                or_(
                    VolumeDiscount.customer_tier.is_(None),
                    VolumeDiscount.customer_tier == customer_tier
                )
            )
        
        # Product/category filter
        product_filters = [VolumeDiscount.is_global == True]
        if variant_id:
            product_filters.append(VolumeDiscount.product_variant_id == variant_id)
        if product_id:
            product_filters.append(VolumeDiscount.product_id == product_id)
        if category_id:
            product_filters.append(VolumeDiscount.category_id == category_id)
        
        query = query.where(or_(*product_filters))
        query = query.order_by(desc(VolumeDiscount.priority), desc(VolumeDiscount.min_quantity))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_discount_tiers(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        channel: Optional[str] = None
    ) -> Sequence[VolumeDiscount]:
        """Get all discount tiers for display"""
        query = select(VolumeDiscount).where(
            VolumeDiscount.is_active == True
        )
        
        # Product/category filter
        product_filters = [VolumeDiscount.is_global == True]
        if variant_id:
            product_filters.append(VolumeDiscount.product_variant_id == variant_id)
        if product_id:
            product_filters.append(VolumeDiscount.product_id == product_id)
        if category_id:
            product_filters.append(VolumeDiscount.category_id == category_id)
        
        query = query.where(or_(*product_filters))
        
        if channel:
            query = query.where(
                or_(
                    VolumeDiscount.channel.is_(None),
                    VolumeDiscount.channel == channel
                )
            )
        
        query = query.order_by(VolumeDiscount.min_quantity)
        
        result = await self.db.execute(query)
        return result.scalars().all()


class PromotionRepository(BaseRepository[Promotion]):
    """Repository for Promotion operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Promotion, db)
    
    async def get_by_code(self, code: str) -> Optional[Promotion]:
        """Get promotion by code"""
        query = select(Promotion).where(Promotion.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_promotions(
        self,
        channel: Optional[str] = None,
        auto_apply_only: bool = False
    ) -> Sequence[Promotion]:
        """Get currently active promotions"""
        now = datetime.utcnow()
        
        query = select(Promotion).where(
            Promotion.status == PricingRuleStatus.ACTIVE,
            Promotion.start_date <= now,
            Promotion.end_date >= now
        )
        
        # Check usage limits
        query = query.where(
            or_(
                Promotion.max_uses.is_(None),
                Promotion.current_uses < Promotion.max_uses
            )
        )
        
        if channel:
            query = query.where(
                or_(
                    Promotion.applicable_channels.is_(None),
                    cast(Promotion.applicable_channels, JSONB) == cast(None, JSONB),  # JSON null
                    cast(Promotion.applicable_channels, JSONB).contains(cast([channel], JSONB))
                )
            )
        
        if auto_apply_only:
            query = query.where(Promotion.auto_apply == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def validate_promotion(
        self,
        code: str,
        channel: str,
        order_value: Decimal,
        user_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None
    ) -> tuple[bool, Optional[Promotion], str]:
        """Validate a promotion code"""
        promo = await self.get_by_code(code)
        
        if not promo:
            return False, None, "Promotion code not found"
        
        now = datetime.utcnow()
        
        # Check status
        if promo.status != PricingRuleStatus.ACTIVE:
            return False, None, "Promotion is not active"
        
        # Check dates
        if promo.start_date > now:
            return False, None, "Promotion has not started yet"
        if promo.end_date < now:
            return False, None, "Promotion has expired"
        
        # Check usage limits
        if promo.max_uses is not None and promo.current_uses >= promo.max_uses:
            return False, None, "Promotion usage limit reached"
        
        # Check channel
        if promo.applicable_channels and channel not in promo.applicable_channels:
            return False, None, f"Promotion not valid for {channel} channel"
        
        # Check minimum order value
        if promo.min_order_value and order_value < promo.min_order_value:
            return False, None, f"Minimum order value is {promo.min_order_value}"
        
        # Check per-customer usage
        if promo.max_uses_per_customer and (user_id or wholesale_customer_id):
            usage_count = await self.get_customer_usage_count(
                promo.id, user_id, wholesale_customer_id
            )
            if usage_count >= promo.max_uses_per_customer:
                return False, None, "You have already used this promotion"
        
        return True, promo, "Promotion is valid"
    
    async def get_customer_usage_count(
        self,
        promotion_id: UUID,
        user_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None
    ) -> int:
        """Get promotion usage count for a customer"""
        query = select(func.count()).select_from(PromotionUsage).where(
            PromotionUsage.promotion_id == promotion_id
        )
        
        if user_id:
            query = query.where(PromotionUsage.user_id == user_id)
        elif wholesale_customer_id:
            query = query.where(PromotionUsage.wholesale_customer_id == wholesale_customer_id)
        else:
            return 0
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def record_usage(
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
        usage = PromotionUsage(
            promotion_id=promotion_id,
            order_id=order_id,
            user_id=user_id,
            wholesale_customer_id=wholesale_customer_id,
            discount_amount=discount_amount,
            order_total_before_discount=order_total_before,
            order_total_after_discount=order_total_after
        )
        self.db.add(usage)
        
        # Increment usage count
        await self.db.execute(
            update(Promotion)
            .where(Promotion.id == promotion_id)
            .values(current_uses=Promotion.current_uses + 1)
        )
        
        await self.db.flush()
        await self.db.refresh(usage)
        return usage
    
    async def search_promotions(
        self,
        search: Optional[str] = None,
        statuses: Optional[List[PricingRuleStatus]] = None,
        channel: Optional[str] = None,
        auto_apply: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "start_date",
        sort_order: str = "desc"
    ) -> tuple[Sequence[Promotion], int]:
        """Search promotions with filters"""
        query = select(Promotion)
        count_query = select(func.count()).select_from(Promotion)
        
        if search:
            search_filter = or_(
                Promotion.name.ilike(f"%{search}%"),
                Promotion.code.ilike(f"%{search}%"),
                Promotion.description.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if statuses:
            query = query.where(Promotion.status.in_(statuses))
            count_query = count_query.where(Promotion.status.in_(statuses))
        
        if channel:
            channel_filter = or_(
                Promotion.applicable_channels.is_(None),
                cast(Promotion.applicable_channels, JSONB) == cast(None, JSONB),  # JSON null
                cast(Promotion.applicable_channels, JSONB).contains(cast([channel], JSONB))
            )
            query = query.where(channel_filter)
            count_query = count_query.where(channel_filter)
        
        if auto_apply is not None:
            query = query.where(Promotion.auto_apply == auto_apply)
            count_query = count_query.where(Promotion.auto_apply == auto_apply)
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(Promotion, sort_by, Promotion.start_date)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all(), total


class PriceHistoryRepository(BaseRepository[PriceHistory]):
    """Repository for Price History operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PriceHistory, db)
    
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
        extra_data: Optional[dict] = None
    ) -> PriceHistory:
        """Record a price change"""
        history = PriceHistory(
            product_id=product_id,
            product_variant_id=variant_id,
            channel=channel,
            old_price=old_price,
            new_price=new_price,
            old_cost=old_cost,
            new_cost=new_cost,
            change_reason=change_reason,
            notes=notes,
            changed_by_id=changed_by_id,
            pricing_rule_id=pricing_rule_id,
            extra_data=extra_data
        )
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history
    
    async def get_history_for_product(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[Sequence[PriceHistory], int]:
        """Get price history for a product"""
        query = select(PriceHistory)
        count_query = select(func.count()).select_from(PriceHistory)
        
        if variant_id:
            query = query.where(PriceHistory.product_variant_id == variant_id)
            count_query = count_query.where(PriceHistory.product_variant_id == variant_id)
        elif product_id:
            query = query.where(PriceHistory.product_id == product_id)
            count_query = count_query.where(PriceHistory.product_id == product_id)
        
        if channel:
            query = query.where(PriceHistory.channel == channel)
            count_query = count_query.where(PriceHistory.channel == channel)
        
        if start_date:
            query = query.where(PriceHistory.effective_date >= start_date)
            count_query = count_query.where(PriceHistory.effective_date >= start_date)
        
        if end_date:
            query = query.where(PriceHistory.effective_date <= end_date)
            count_query = count_query.where(PriceHistory.effective_date <= end_date)
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        query = query.order_by(desc(PriceHistory.effective_date))
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all(), total
    
    async def get_latest_price(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None,
        channel: Optional[str] = None
    ) -> Optional[PriceHistory]:
        """Get the latest price record"""
        query = select(PriceHistory)
        
        if variant_id:
            query = query.where(PriceHistory.product_variant_id == variant_id)
        elif product_id:
            query = query.where(PriceHistory.product_id == product_id)
        else:
            return None
        
        if channel:
            query = query.where(PriceHistory.channel == channel)
        
        query = query.order_by(desc(PriceHistory.effective_date)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class CompetitorPriceRepository(BaseRepository[CompetitorPrice]):
    """Repository for Competitor Price operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CompetitorPrice, db)
    
    async def add_competitor_price(
        self,
        product_id: Optional[UUID],
        variant_id: Optional[UUID],
        competitor_name: str,
        price: Decimal,
        source: str,
        competitor_url: Optional[str] = None,
        competitor_product_name: Optional[str] = None,
        competitor_sku: Optional[str] = None,
        sale_price: Optional[Decimal] = None,
        in_stock: Optional[bool] = None,
        match_confidence: Optional[float] = None,
        extra_data: Optional[dict] = None
    ) -> CompetitorPrice:
        """Add a competitor price observation"""
        # Mark previous entries as not latest
        await self.db.execute(
            update(CompetitorPrice)
            .where(
                CompetitorPrice.competitor_name == competitor_name,
                CompetitorPrice.is_latest == True,
                or_(
                    CompetitorPrice.product_id == product_id,
                    CompetitorPrice.product_variant_id == variant_id
                )
            )
            .values(is_latest=False)
        )
        
        # Add new observation
        observation = CompetitorPrice(
            product_id=product_id,
            product_variant_id=variant_id,
            competitor_name=competitor_name,
            competitor_url=competitor_url,
            competitor_product_name=competitor_product_name,
            competitor_sku=competitor_sku,
            price=price,
            sale_price=sale_price,
            in_stock=in_stock,
            source=source,
            match_confidence=match_confidence,
            is_latest=True,
            extra_data=extra_data
        )
        self.db.add(observation)
        await self.db.flush()
        await self.db.refresh(observation)
        return observation
    
    async def get_latest_prices(
        self,
        product_id: Optional[UUID] = None,
        variant_id: Optional[UUID] = None
    ) -> Sequence[CompetitorPrice]:
        """Get latest competitor prices for a product"""
        query = select(CompetitorPrice).where(CompetitorPrice.is_latest == True)
        
        if variant_id:
            query = query.where(CompetitorPrice.product_variant_id == variant_id)
        elif product_id:
            query = query.where(CompetitorPrice.product_id == product_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_price_history_for_competitor(
        self,
        product_id: Optional[UUID],
        variant_id: Optional[UUID],
        competitor_name: str,
        limit: int = 30
    ) -> Sequence[CompetitorPrice]:
        """Get price history from a specific competitor"""
        query = select(CompetitorPrice).where(
            CompetitorPrice.competitor_name == competitor_name
        )
        
        if variant_id:
            query = query.where(CompetitorPrice.product_variant_id == variant_id)
        elif product_id:
            query = query.where(CompetitorPrice.product_id == product_id)
        
        query = query.order_by(desc(CompetitorPrice.observed_at)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_tracked_competitors(self) -> List[str]:
        """Get list of all tracked competitors"""
        query = select(CompetitorPrice.competitor_name).distinct()
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]


class CustomerPricingTierRepository(BaseRepository[CustomerPricingTier]):
    """Repository for Customer Pricing Tier operations"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(CustomerPricingTier, db)
    
    async def get_customer_tier(
        self,
        user_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None
    ) -> Optional[CustomerPricingTier]:
        """Get current tier for a customer"""
        now = datetime.utcnow()
        query = select(CustomerPricingTier).where(
            CustomerPricingTier.effective_from <= now
        ).where(
            or_(
                CustomerPricingTier.effective_until.is_(None),
                CustomerPricingTier.effective_until >= now
            )
        )
        
        if user_id:
            query = query.where(CustomerPricingTier.user_id == user_id)
        elif wholesale_customer_id:
            query = query.where(CustomerPricingTier.wholesale_customer_id == wholesale_customer_id)
        else:
            return None
        
        query = query.order_by(desc(CustomerPricingTier.effective_from)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def assign_tier(
        self,
        tier: CustomerTier,
        user_id: Optional[UUID] = None,
        wholesale_customer_id: Optional[UUID] = None,
        discount_percentage: Decimal = Decimal("0"),
        assignment_reason: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        effective_until: Optional[datetime] = None,
        is_automatic: bool = False
    ) -> CustomerPricingTier:
        """Assign a tier to a customer"""
        # End current tier if exists
        current = await self.get_customer_tier(user_id, wholesale_customer_id)
        if current:
            current.effective_until = datetime.utcnow()
            await self.db.flush()
        
        # Create new tier assignment
        tier_assignment = CustomerPricingTier(
            user_id=user_id,
            wholesale_customer_id=wholesale_customer_id,
            tier=tier,
            discount_percentage=discount_percentage,
            assignment_reason=assignment_reason,
            effective_from=effective_from or datetime.utcnow(),
            effective_until=effective_until,
            is_automatic=is_automatic
        )
        self.db.add(tier_assignment)
        await self.db.flush()
        await self.db.refresh(tier_assignment)
        return tier_assignment
    
    async def get_customers_by_tier(
        self,
        tier: CustomerTier,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[CustomerPricingTier]:
        """Get all customers in a specific tier"""
        now = datetime.utcnow()
        query = select(CustomerPricingTier).where(
            CustomerPricingTier.tier == tier,
            CustomerPricingTier.effective_from <= now
        ).where(
            or_(
                CustomerPricingTier.effective_until.is_(None),
                CustomerPricingTier.effective_until >= now
            )
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
