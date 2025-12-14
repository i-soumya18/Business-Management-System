"""
Pricing Engine Tests

Comprehensive test suite for the pricing engine including:
- Pricing rules CRUD operations
- Price calculation with various discount types
- Channel-specific pricing
- Volume discounts
- Promotional campaigns
- Customer tier pricing
- Price history tracking
- Competitor price monitoring
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from typing import AsyncGenerator

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pricing import (
    PricingRule,
    ChannelPrice,
    VolumeDiscount,
    Promotion,
    PriceHistory,
    CompetitorPrice,
    CustomerPricingTier,
    PricingRuleType,
    PricingRuleStatus,
    DiscountType,
    CustomerTier,
    PriceChangeReason
)
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.services.pricing import PricingService
from app.schemas.pricing import (
    PriceCalculationRequest,
    PricingRuleCreate,
    ChannelPriceCreate,
    VolumeDiscountCreate,
    PromotionCreate,
    PromotionValidationRequest,
    CustomerPricingTierCreate,
    CompetitorPriceCreate
)


# ==================== Fixtures ====================

@pytest_asyncio.fixture
async def pricing_service(db_session: AsyncSession) -> PricingService:
    """Create a pricing service instance"""
    return PricingService(db_session)


@pytest.fixture
def mock_product_id():
    """Mock product ID - for tests that don't need FK constraints"""
    return uuid4()


@pytest.fixture
def mock_variant_id():
    """Mock variant ID - for tests that don't need FK constraints"""
    return uuid4()


@pytest.fixture
def mock_category_id():
    """Mock category ID"""
    return uuid4()


@pytest.fixture
def mock_user_id():
    """Mock user ID"""
    return uuid4()


@pytest.fixture
def mock_wholesale_customer_id():
    """Mock wholesale customer ID"""
    return uuid4()


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession) -> Product:
    """Create a real test product in the database"""
    product = Product(
        id=uuid4(),
        name="Test Product",
        slug="test-product-" + str(uuid4())[:8],
        sku="TEST-PROD-" + str(uuid4())[:8],
        description="A test product for pricing tests",
        is_active=True,
        base_cost_price=Decimal("50.00"),
        base_retail_price=Decimal("100.00"),
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def test_variant(db_session: AsyncSession, test_product: Product) -> ProductVariant:
    """Create a real test product variant in the database"""
    variant = ProductVariant(
        id=uuid4(),
        product_id=test_product.id,
        sku="TEST-VAR-" + str(uuid4())[:8],
        size="M",
        color="Blue",
        retail_price=Decimal("100.00"),
        is_active=True,
    )
    db_session.add(variant)
    await db_session.flush()
    return variant


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a real test user in the database"""
    user = User(
        id=uuid4(),
        email=f"testuser-{uuid4()}@example.com",
        hashed_password="hashed_password_placeholder",
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ==================== Pricing Rule Tests ====================

class TestPricingRules:
    """Test pricing rule CRUD and application"""
    
    @pytest.mark.asyncio
    async def test_create_pricing_rule(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test creating a pricing rule"""
        rule_data = PricingRuleCreate(
            name="Summer Sale",
            code="SUMMER2024",
            rule_type=PricingRuleType.PROMOTIONAL,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("15.00"),
            status=PricingRuleStatus.ACTIVE,
            priority=10,
            description="15% off summer collection",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            applicable_channels=["retail", "ecommerce"]
        )
        
        rule = await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        assert rule is not None
        assert rule.name == "Summer Sale"
        assert rule.code == "SUMMER2024"
        assert rule.discount_type == DiscountType.PERCENTAGE
        assert rule.discount_value == Decimal("15.00")
        assert rule.status == PricingRuleStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_list_pricing_rules(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test listing pricing rules with filters"""
        # Create multiple rules
        for i in range(5):
            rule_data = PricingRuleCreate(
                name=f"Rule {i}",
                code=f"RULE{i}",
                rule_type=PricingRuleType.PROMOTIONAL,
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal(str(5 + i)),
                status=PricingRuleStatus.ACTIVE if i < 3 else PricingRuleStatus.PAUSED,
                priority=i
            )
            await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        # List all rules
        rules, total = await pricing_service.list_pricing_rules()
        assert total == 5
        
        # Filter by status
        active_rules, active_total = await pricing_service.list_pricing_rules(
            statuses=[PricingRuleStatus.ACTIVE]
        )
        assert active_total == 3
    
    @pytest.mark.asyncio
    async def test_activate_deactivate_rule(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test activating and deactivating rules"""
        rule_data = PricingRuleCreate(
            name="Test Rule",
            code="TESTRULE",
            rule_type=PricingRuleType.PROMOTIONAL,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("10.00"),
            status=PricingRuleStatus.DRAFT,
            priority=1
        )
        
        rule = await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        # Activate
        activated = await pricing_service.activate_rule(rule.id)
        await db_session.commit()
        assert activated.status == PricingRuleStatus.ACTIVE
        
        # Deactivate
        deactivated = await pricing_service.deactivate_rule(rule.id)
        await db_session.commit()
        assert deactivated.status == PricingRuleStatus.PAUSED


# ==================== Price Calculation Tests ====================

class TestPriceCalculation:
    """Test price calculation with various scenarios"""
    
    @pytest.mark.asyncio
    async def test_simple_percentage_discount(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        mock_product_id
    ):
        """Test simple percentage discount calculation"""
        # Create a global pricing rule (applies to all products)
        rule_data = PricingRuleCreate(
            name="10% Off",
            code="TENOFF",
            rule_type=PricingRuleType.PROMOTIONAL,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            status=PricingRuleStatus.ACTIVE,
            priority=10
            # No product_ids - this is a global rule
        )
        await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        # Calculate price
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("100.00"),
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.original_price == Decimal("100.00")
        assert result.final_price == Decimal("90.00")
        assert result.discount_amount == Decimal("10.00")
        assert result.discount_percentage == Decimal("10.00")
    
    @pytest.mark.asyncio
    async def test_fixed_amount_discount(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        mock_product_id
    ):
        """Test fixed amount discount calculation"""
        rule_data = PricingRuleCreate(
            name="$5 Off",
            code="FIVEOFF",
            rule_type=PricingRuleType.PROMOTIONAL,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("5.00"),
            status=PricingRuleStatus.ACTIVE,
            priority=10
            # No product_ids - this is a global rule
        )
        await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("50.00"),
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.original_price == Decimal("50.00")
        assert result.final_price == Decimal("45.00")
        assert result.discount_amount == Decimal("5.00")
    
    @pytest.mark.asyncio
    async def test_fixed_price_discount(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        mock_product_id
    ):
        """Test fixed price discount (sale price)"""
        rule_data = PricingRuleCreate(
            name="Special Price",
            code="SPECIAL",
            rule_type=PricingRuleType.CLEARANCE,
            discount_type=DiscountType.FIXED_PRICE,
            discount_value=Decimal("29.99"),
            status=PricingRuleStatus.ACTIVE,
            priority=10
            # No product_ids - this is a global rule
        )
        await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("49.99"),
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.original_price == Decimal("49.99")
        assert result.final_price == Decimal("29.99")
    
    @pytest.mark.asyncio
    async def test_no_discount_applied(
        self,
        pricing_service: PricingService,
        mock_product_id
    ):
        """Test price calculation with no applicable discounts"""
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("100.00"),
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.original_price == Decimal("100.00")
        assert result.final_price == Decimal("100.00")
        assert result.discount_amount == Decimal("0.00")
        assert len(result.applied_discounts) == 0
    
    @pytest.mark.asyncio
    async def test_quantity_multiplier(
        self,
        pricing_service: PricingService,
        mock_product_id
    ):
        """Test price calculation with quantity"""
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("25.00"),
            quantity=4,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.line_total == Decimal("100.00")
        assert result.original_line_total == Decimal("100.00")


# ==================== Channel Pricing Tests ====================

class TestChannelPricing:
    """Test channel-specific pricing"""
    
    @pytest.mark.asyncio
    async def test_set_channel_price(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_variant: ProductVariant
    ):
        """Test setting channel-specific price"""
        price_data = ChannelPriceCreate(
            product_variant_id=test_variant.id,
            channel="ecommerce",
            base_price=Decimal("49.99"),
            compare_at_price=Decimal("59.99"),
            cost_price=Decimal("25.00"),
            min_price=Decimal("39.99")
        )
        
        channel_price = await pricing_service.set_channel_price(price_data)
        
        assert channel_price.base_price == Decimal("49.99")
        assert channel_price.compare_at_price == Decimal("59.99")
        assert channel_price.channel == "ecommerce"
    
    @pytest.mark.asyncio
    async def test_channel_price_override_in_calculation(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_variant: ProductVariant
    ):
        """Test that channel price overrides base price"""
        # Set channel price
        price_data = ChannelPriceCreate(
            product_variant_id=test_variant.id,
            channel="wholesale",
            base_price=Decimal("35.00")
        )
        await pricing_service.set_channel_price(price_data)
        
        # Calculate price - channel price should be used
        request = PriceCalculationRequest(
            variant_id=test_variant.id,
            base_price=Decimal("50.00"),  # This should be overridden
            quantity=1,
            channel="wholesale"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.original_price == Decimal("35.00")


# ==================== Volume Discount Tests ====================

class TestVolumeDiscounts:
    """Test volume-based discounts"""
    
    @pytest.mark.asyncio
    async def test_create_volume_discount(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_product: Product
    ):
        """Test creating volume discount tiers"""
        # Create tiered discounts
        tiers = [
            (5, 10, 5),    # 5-10 items: 5% off
            (11, 25, 10),  # 11-25 items: 10% off
            (26, None, 15) # 26+ items: 15% off
        ]
        
        for i, (min_qty, max_qty, discount) in enumerate(tiers):
            discount_data = VolumeDiscountCreate(
                name=f"Volume Tier {i+1}",
                product_id=test_product.id,
                min_quantity=min_qty,
                max_quantity=max_qty,
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal(str(discount)),
                is_active=True
            )
            await pricing_service.create_volume_discount(discount_data)
        await db_session.commit()
        
        # Get discount tiers
        discounts = await pricing_service.get_volume_discount_tiers(
            product_id=test_product.id
        )
        
        assert len(discounts) == 3
    
    @pytest.mark.asyncio
    async def test_volume_discount_applied(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        mock_product_id
    ):
        """Test volume discount is applied correctly"""
        # Create global volume discount (no product FK required)
        discount_data = VolumeDiscountCreate(
            name="Global Volume Discount",
            min_quantity=10,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            is_active=True,
            is_global=True
        )
        await pricing_service.create_volume_discount(discount_data)
        await db_session.commit()
        
        # Calculate price with quantity meeting threshold
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("20.00"),
            quantity=15,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        # Should get 10% volume discount
        assert any(d.source == "volume_discount" for d in result.applied_discounts)


# ==================== Promotion Tests ====================

class TestPromotions:
    """Test promotional campaigns"""
    
    @pytest.mark.asyncio
    async def test_create_promotion(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test creating a promotion"""
        promo_data = PromotionCreate(
            name="Black Friday Sale",
            code="BLACKFRIDAY",
            description="25% off everything",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("25.00"),
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            status=PricingRuleStatus.ACTIVE,
            max_uses=1000,
            max_uses_per_customer=2,
            applicable_channels=["retail", "ecommerce"]
        )
        
        promo = await pricing_service.create_promotion(promo_data)
        await db_session.commit()
        
        assert promo.name == "Black Friday Sale"
        assert promo.code == "BLACKFRIDAY"
        assert promo.current_uses == 0
    
    @pytest.mark.asyncio
    async def test_validate_promotion_valid(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test validating a valid promotion code"""
        # Create promotion
        promo_data = PromotionCreate(
            name="Valid Promo",
            code="VALID20",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("20.00"),
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=30),
            status=PricingRuleStatus.ACTIVE,
            min_order_value=Decimal("50.00")
        )
        await pricing_service.create_promotion(promo_data)
        await db_session.commit()
        
        # Validate
        request = PromotionValidationRequest(
            code="VALID20",
            channel="retail",
            order_value=Decimal("100.00")
        )
        
        result = await pricing_service.validate_promotion(request)
        
        assert result.is_valid is True
        assert result.promotion_name == "Valid Promo"
        assert result.discount_value == Decimal("20.00")
    
    @pytest.mark.asyncio
    async def test_validate_promotion_expired(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test validating an expired promotion"""
        promo_data = PromotionCreate(
            name="Expired Promo",
            code="EXPIRED",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow() - timedelta(days=1),  # Already expired
            status=PricingRuleStatus.ACTIVE
        )
        await pricing_service.create_promotion(promo_data)
        await db_session.commit()
        
        request = PromotionValidationRequest(
            code="EXPIRED",
            channel="retail",
            order_value=Decimal("100.00")
        )
        
        result = await pricing_service.validate_promotion(request)
        
        assert result.is_valid is False
        assert "expired" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_validate_promotion_min_order(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test promotion minimum order value"""
        promo_data = PromotionCreate(
            name="Min Order Promo",
            code="MINORDER",
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("20.00"),
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=30),
            status=PricingRuleStatus.ACTIVE,
            min_order_value=Decimal("100.00")
        )
        await pricing_service.create_promotion(promo_data)
        await db_session.commit()
        
        # Try with order below minimum
        request = PromotionValidationRequest(
            code="MINORDER",
            channel="retail",
            order_value=Decimal("50.00")
        )
        
        result = await pricing_service.validate_promotion(request)
        
        assert result.is_valid is False
        assert "minimum" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_promotion_usage_limit(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test promotion usage limit"""
        promo_data = PromotionCreate(
            name="Limited Promo",
            code="LIMITED",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("15.00"),
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=30),
            status=PricingRuleStatus.ACTIVE,
            max_uses=0  # Already at limit
        )
        promo = await pricing_service.create_promotion(promo_data)
        await db_session.commit()
        
        request = PromotionValidationRequest(
            code="LIMITED",
            channel="retail",
            order_value=Decimal("100.00")
        )
        
        result = await pricing_service.validate_promotion(request)
        
        assert result.is_valid is False


# ==================== Customer Tier Tests ====================

class TestCustomerTiers:
    """Test customer pricing tiers"""
    
    @pytest.mark.asyncio
    async def test_assign_customer_tier(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test assigning a tier to a customer"""
        tier_data = CustomerPricingTierCreate(
            user_id=test_user.id,
            tier=CustomerTier.GOLD,
            discount_percentage=Decimal("10.00"),
            assignment_reason="High volume customer"
        )
        
        tier = await pricing_service.assign_customer_tier(tier_data)
        await db_session.commit()
        
        assert tier.tier == CustomerTier.GOLD
        assert tier.discount_percentage == Decimal("10.00")
    
    @pytest.mark.asyncio
    async def test_customer_tier_discount_applied(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_user: User,
        mock_product_id
    ):
        """Test customer tier discount is applied"""
        # Assign tier
        tier_data = CustomerPricingTierCreate(
            user_id=test_user.id,
            tier=CustomerTier.PLATINUM,
            discount_percentage=Decimal("15.00")
        )
        await pricing_service.assign_customer_tier(tier_data)
        await db_session.commit()
        
        # Calculate price
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("100.00"),
            quantity=1,
            channel="retail",
            user_id=test_user.id
        )
        
        result = await pricing_service.calculate_price(request)
        
        # Should have customer tier discount
        tier_discount = next(
            (d for d in result.applied_discounts if d.source == "customer_tier"),
            None
        )
        assert tier_discount is not None
        assert tier_discount.discount_value == Decimal("15.00")


# ==================== Price History Tests ====================

class TestPriceHistory:
    """Test price history tracking"""
    
    @pytest.mark.asyncio
    async def test_record_price_change(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_variant: ProductVariant,
        test_user: User
    ):
        """Test recording a price change"""
        history = await pricing_service.record_price_change(
            product_id=None,
            variant_id=test_variant.id,
            old_price=Decimal("49.99"),
            new_price=Decimal("39.99"),
            change_reason=PriceChangeReason.MANUAL_ADJUSTMENT,
            channel="retail",
            changed_by_id=test_user.id,
            notes="Competitive price adjustment"
        )
        await db_session.commit()
        
        assert history.old_price == Decimal("49.99")
        assert history.new_price == Decimal("39.99")
        assert history.change_reason == PriceChangeReason.MANUAL_ADJUSTMENT
    
    @pytest.mark.asyncio
    async def test_get_price_history(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_variant: ProductVariant
    ):
        """Test retrieving price history"""
        # Record multiple changes
        for i in range(5):
            await pricing_service.record_price_change(
                product_id=None,
                variant_id=test_variant.id,
                old_price=Decimal(str(50 - i)),
                new_price=Decimal(str(49 - i)),
                change_reason=PriceChangeReason.MANUAL_ADJUSTMENT
            )
        await db_session.commit()
        
        history, total = await pricing_service.get_price_history(
            variant_id=test_variant.id
        )
        
        assert total == 5
        assert len(history) == 5


# ==================== Competitor Pricing Tests ====================

class TestCompetitorPricing:
    """Test competitor price monitoring"""
    
    @pytest.mark.asyncio
    async def test_add_competitor_price(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_product: Product
    ):
        """Test adding competitor price observation"""
        competitor_data = CompetitorPriceCreate(
            product_id=test_product.id,
            competitor_name="Amazon",
            price=Decimal("42.99"),
            source="api_scraper",
            competitor_url="https://amazon.com/product/123",
            in_stock=True,
            match_confidence=0.95
        )
        
        price = await pricing_service.add_competitor_price(competitor_data)
        await db_session.commit()
        
        assert price.competitor_name == "Amazon"
        assert price.price == Decimal("42.99")
        assert price.is_latest is True
    
    @pytest.mark.asyncio
    async def test_get_competitor_comparison(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_variant: ProductVariant
    ):
        """Test competitor price comparison"""
        # Set our price
        await pricing_service.set_channel_price(
            ChannelPriceCreate(
                product_variant_id=test_variant.id,
                channel="retail",
                base_price=Decimal("49.99")
            )
        )
        
        # Add competitor prices
        competitors = [
            ("Amazon", Decimal("47.99")),
            ("Walmart", Decimal("51.99")),
            ("Target", Decimal("49.99"))
        ]
        
        for name, price in competitors:
            await pricing_service.add_competitor_price(
                CompetitorPriceCreate(
                    product_variant_id=test_variant.id,
                    competitor_name=name,
                    price=price,
                    source="manual"
                )
            )
        await db_session.commit()
        
        comparison = await pricing_service.get_price_comparison(
            variant_id=test_variant.id,
            channel="retail"
        )
        
        assert comparison.our_price == Decimal("49.99")
        assert len(comparison.competitor_prices) == 3


# ==================== Dashboard Tests ====================

class TestPricingDashboard:
    """Test pricing dashboard and analytics"""
    
    @pytest.mark.asyncio
    async def test_get_dashboard(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession
    ):
        """Test getting pricing dashboard data"""
        # Create some test data
        for i in range(3):
            await pricing_service.create_pricing_rule(
                PricingRuleCreate(
                    name=f"Rule {i}",
                    code=f"RULE{i}",
                    rule_type=PricingRuleType.PROMOTIONAL,
                    discount_type=DiscountType.PERCENTAGE,
                    discount_value=Decimal("5.00"),
                    status=PricingRuleStatus.ACTIVE,
                    priority=i
                )
            )
        
        for i in range(2):
            await pricing_service.create_promotion(
                PromotionCreate(
                    name=f"Promo {i}",
                    code=f"PROMO{i}",
                    discount_type=DiscountType.PERCENTAGE,
                    discount_value=Decimal("10.00"),
                    start_date=datetime.utcnow() - timedelta(days=1),
                    end_date=datetime.utcnow() + timedelta(days=30),
                    status=PricingRuleStatus.ACTIVE
                )
            )
        await db_session.commit()
        
        dashboard = await pricing_service.get_pricing_dashboard()
        
        assert dashboard.active_rules_count >= 3
        assert dashboard.active_promotions_count >= 2


# ==================== API Endpoint Tests ====================

class TestPricingAPI:
    """Test pricing API endpoints"""
    
    @pytest.mark.asyncio
    async def test_calculate_price_endpoint(self, client: AsyncClient):
        """Test price calculation endpoint"""
        request_data = {
            "product_id": str(uuid4()),
            "base_price": "100.00",
            "quantity": 1,
            "channel": "retail"
        }
        
        response = await client.post("/api/v1/pricing/calculate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "final_price" in data
        assert "original_price" in data
    
    @pytest.mark.asyncio
    async def test_create_rule_endpoint_unauthorized(self, client: AsyncClient):
        """Test creating rule without auth returns 401"""
        rule_data = {
            "name": "Test Rule",
            "code": "TEST",
            "rule_type": "standard",
            "discount_type": "percentage",
            "discount_value": "10.00",
            "status": "active",
            "priority": 1
        }
        
        response = await client.post("/api/v1/pricing/rules", json=rule_data)
        
        # Should require authentication
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_validate_promotion_endpoint(self, client: AsyncClient):
        """Test promotion validation endpoint"""
        request_data = {
            "code": "NONEXISTENT",
            "channel": "retail",
            "order_value": "100.00"
        }
        
        response = await client.post("/api/v1/pricing/promotions/validate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False


# ==================== Edge Case Tests ====================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_negative_price_prevented(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        mock_product_id
    ):
        """Test that final price cannot go negative"""
        # Create excessive discount
        rule_data = PricingRuleCreate(
            name="Big Discount",
            code="BIGDISCOUNT",
            rule_type=PricingRuleType.PROMOTIONAL,
            discount_type=DiscountType.FIXED_AMOUNT,
            discount_value=Decimal("200.00"),  # More than price
            status=PricingRuleStatus.ACTIVE,
            priority=10
            # No product_ids - global rule
        )
        await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("50.00"),
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        # Price should be 0, not negative
        assert result.final_price >= Decimal("0.00")
    
    @pytest.mark.asyncio
    async def test_min_price_enforced(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        test_variant: ProductVariant
    ):
        """Test that minimum price is enforced"""
        # Set channel price with minimum
        await pricing_service.set_channel_price(
            ChannelPriceCreate(
                product_variant_id=test_variant.id,
                channel="retail",
                base_price=Decimal("100.00"),
                min_price=Decimal("80.00")
            )
        )
        
        # Create discount that would go below min
        rule_data = PricingRuleCreate(
            name="Deep Discount",
            code="DEEP",
            rule_type=PricingRuleType.CLEARANCE,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("30.00"),  # Would be $70
            status=PricingRuleStatus.ACTIVE,
            priority=10
            # No variant_ids - global rule
        )
        await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        request = PriceCalculationRequest(
            variant_id=test_variant.id,
            base_price=Decimal("100.00"),
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        # Price should not go below minimum
        assert result.final_price >= Decimal("80.00")
    
    @pytest.mark.asyncio
    async def test_zero_quantity(self, pricing_service: PricingService, mock_product_id):
        """Test handling of zero quantity"""
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("100.00"),
            quantity=0,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        assert result.line_total == Decimal("0.00")
    
    @pytest.mark.asyncio
    async def test_max_discount_cap(
        self,
        pricing_service: PricingService,
        db_session: AsyncSession,
        mock_product_id
    ):
        """Test maximum discount cap is enforced"""
        rule_data = PricingRuleCreate(
            name="Capped Discount",
            code="CAPPED",
            rule_type=PricingRuleType.PROMOTIONAL,
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("50.00"),
            max_discount_amount=Decimal("20.00"),  # Cap at $20
            status=PricingRuleStatus.ACTIVE,
            priority=10
            # No product_ids - global rule
        )
        await pricing_service.create_pricing_rule(rule_data)
        await db_session.commit()
        
        request = PriceCalculationRequest(
            product_id=mock_product_id,
            base_price=Decimal("100.00"),  # 50% would be $50
            quantity=1,
            channel="retail"
        )
        
        result = await pricing_service.calculate_price(request)
        
        # Discount should be capped at $20
        assert result.discount_amount == Decimal("20.00")
        assert result.final_price == Decimal("80.00")
