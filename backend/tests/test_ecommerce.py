"""
E-Commerce Module Tests

Comprehensive tests for e-commerce functionality including shopping cart,
wishlist, product reviews, and promotional codes.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.product import Product, ProductVariant
from app.models.category import Category
from app.models.ecommerce import (
    ShoppingCart,
    CartItem,
    Wishlist,
    WishlistItem,
    ProductReview,
    PromoCode,
    PromoCodeUsage,
    CartStatus,
    PromoCodeType,
    PromoCodeStatus,
    ReviewStatus
)
from app.services.ecommerce import (
    ShoppingCartService,
    PromoCodeService,
    WishlistService,
    ProductReviewService,
    AbandonedCartService
)
from app.schemas.ecommerce import (
    AddToCartRequest,
    UpdateCartItemRequest,
    WishlistItemCreate,
    ProductReviewCreate,
    ProductReviewUpdate
)


# ==================== Fixtures ====================

@pytest.fixture
async def test_category(db_session: AsyncSession):
    """Create test category"""
    category = Category(
        name="Test Category",
        slug="test-category"
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture
async def test_product(db_session: AsyncSession, test_category):
    """Create test product"""
    product = Product(
        name="Test Product",
        sku="TEST-PROD-001",
        category_id=test_category.id,
        description="Test product description"
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_product_variant(db_session: AsyncSession, test_product):
    """Create test product variant"""
    variant = ProductVariant(
        product_id=test_product.id,
        sku="TEST-VAR-001",
        size="M",
        color="Red",
        retail_price=Decimal("29.99"),
        sale_price=Decimal("24.99")
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)
    return variant


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ==================== Shopping Cart Tests ====================

class TestShoppingCart:
    """Test shopping cart functionality"""
    
    async def test_create_cart_for_user(self, db_session: AsyncSession, test_user):
        """Test creating cart for authenticated user"""
        service = ShoppingCartService(db_session)
        cart = await service.get_or_create_cart(user_id=test_user.id)
        
        assert cart is not None
        assert cart.user_id == test_user.id
        assert cart.status == CartStatus.ACTIVE
        assert cart.session_id is None
    
    async def test_create_cart_for_guest(self, db_session: AsyncSession):
        """Test creating cart for guest user"""
        service = ShoppingCartService(db_session)
        session_id = str(uuid4())
        cart = await service.get_or_create_cart(session_id=session_id)
        
        assert cart is not None
        assert cart.session_id == session_id
        assert cart.status == CartStatus.ACTIVE
        assert cart.user_id is None
    
    async def test_add_item_to_cart(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test adding item to cart"""
        service = ShoppingCartService(db_session)
        
        request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=2
        )
        
        cart_item = await service.add_to_cart(request, user_id=test_user.id)
        
        assert cart_item is not None
        assert cart_item.product_variant_id == test_product_variant.id
        assert cart_item.quantity == 2
        assert cart_item.unit_price == test_product_variant.sale_price
    
    async def test_update_cart_item_quantity(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test updating cart item quantity"""
        service = ShoppingCartService(db_session)
        
        # Add item
        add_request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=2
        )
        cart_item = await service.add_to_cart(add_request, user_id=test_user.id)
        
        # Update quantity
        update_request = UpdateCartItemRequest(quantity=5)
        updated_item = await service.update_cart_item(cart_item.id, update_request)
        
        assert updated_item.quantity == 5
    
    async def test_remove_item_from_cart(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test removing item from cart"""
        service = ShoppingCartService(db_session)
        
        # Add item
        request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=2
        )
        cart_item = await service.add_to_cart(request, user_id=test_user.id)
        
        # Remove item
        await service.remove_from_cart(cart_item.id)
        
        # Verify item is removed
        cart = await service.get_or_create_cart(user_id=test_user.id)
        assert len(cart.items) == 0
    
    async def test_cart_subtotal_calculation(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test cart subtotal calculation"""
        service = ShoppingCartService(db_session)
        
        # Add items
        request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=3
        )
        await service.add_to_cart(request, user_id=test_user.id)
        
        cart = await service.get_or_create_cart(user_id=test_user.id)
        
        expected_subtotal = test_product_variant.sale_price * 3
        assert cart.subtotal == expected_subtotal
    
    async def test_merge_guest_cart_into_user_cart(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test merging guest cart into user cart on login"""
        service = ShoppingCartService(db_session)
        
        # Create guest cart with items
        session_id = str(uuid4())
        guest_request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=2
        )
        await service.add_to_cart(guest_request, session_id=session_id)
        guest_cart = await service.get_or_create_cart(session_id=session_id)
        
        # Create user cart with items
        user_request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=3
        )
        await service.add_to_cart(user_request, user_id=test_user.id)
        user_cart = await service.get_or_create_cart(user_id=test_user.id)
        
        # Merge carts
        merged_cart = await service.merge_carts(guest_cart.id, user_cart.id)
        
        assert merged_cart.user_id == test_user.id
        assert len(merged_cart.items) == 1
        assert merged_cart.items[0].quantity == 5  # 2 + 3


# ==================== Wishlist Tests ====================

class TestWishlist:
    """Test wishlist functionality"""
    
    async def test_create_wishlist(self, db_session: AsyncSession, test_user):
        """Test creating wishlist"""
        wishlist = Wishlist(
            user_id=test_user.id,
            name="My Wishlist",
            is_public=False
        )
        db_session.add(wishlist)
        await db_session.commit()
        await db_session.refresh(wishlist)
        
        assert wishlist is not None
        assert wishlist.user_id == test_user.id
        assert wishlist.name == "My Wishlist"
    
    async def test_add_item_to_wishlist(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test adding item to wishlist"""
        service = WishlistService(db_session)
        
        request = WishlistItemCreate(
            product_variant_id=test_product_variant.id,
            priority=1,
            notes="Must have!"
        )
        
        wishlist_item = await service.add_to_wishlist(test_user.id, request)
        
        assert wishlist_item is not None
        assert wishlist_item.product_variant_id == test_product_variant.id
        assert wishlist_item.priority == 1
        assert wishlist_item.notes == "Must have!"
    
    async def test_remove_item_from_wishlist(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test removing item from wishlist"""
        service = WishlistService(db_session)
        
        # Add item
        request = WishlistItemCreate(
            product_variant_id=test_product_variant.id
        )
        wishlist_item = await service.add_to_wishlist(test_user.id, request)
        
        # Remove item
        await service.remove_from_wishlist(wishlist_item.id, test_user.id)
        
        # Verify item is removed
        wishlist = await service.wishlist_repo.get_default_wishlist(test_user.id)
        assert len(wishlist.items) == 0
    
    async def test_move_wishlist_item_to_cart(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test moving item from wishlist to cart"""
        wishlist_service = WishlistService(db_session)
        cart_service = ShoppingCartService(db_session)
        
        # Add item to wishlist
        request = WishlistItemCreate(
            product_variant_id=test_product_variant.id
        )
        wishlist_item = await wishlist_service.add_to_wishlist(test_user.id, request)
        
        # Move to cart
        cart_item = await wishlist_service.move_to_cart(
            wishlist_item.id,
            test_user.id,
            cart_service
        )
        
        assert cart_item is not None
        assert cart_item.product_variant_id == test_product_variant.id
        
        # Verify item is removed from wishlist
        wishlist = await wishlist_service.wishlist_repo.get_default_wishlist(test_user.id)
        assert len(wishlist.items) == 0


# ==================== Product Review Tests ====================

class TestProductReview:
    """Test product review functionality"""
    
    async def test_create_review(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test creating product review"""
        service = ProductReviewService(db_session)
        
        request = ProductReviewCreate(
            product_variant_id=test_product_variant.id,
            rating=5,
            title="Great product!",
            review_text="I absolutely love this product. Highly recommended!"
        )
        
        review = await service.create_review(test_user.id, request)
        
        assert review is not None
        assert review.user_id == test_user.id
        assert review.product_variant_id == test_product_variant.id
        assert review.rating == 5
        assert review.status == ReviewStatus.PENDING
    
    async def test_update_review(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test updating product review"""
        service = ProductReviewService(db_session)
        
        # Create review
        create_request = ProductReviewCreate(
            product_variant_id=test_product_variant.id,
            rating=4,
            title="Good product",
            review_text="Pretty good overall"
        )
        review = await service.create_review(test_user.id, create_request)
        
        # Update review
        update_request = ProductReviewUpdate(
            rating=5,
            title="Excellent product!",
            review_text="Changed my mind - this is amazing!"
        )
        updated_review = await service.update_review(review.id, test_user.id, update_request)
        
        assert updated_review.rating == 5
        assert updated_review.title == "Excellent product!"
    
    async def test_vote_review_helpfulness(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test voting on review helpfulness"""
        service = ProductReviewService(db_session)
        
        # Create review
        request = ProductReviewCreate(
            product_variant_id=test_product_variant.id,
            rating=5,
            title="Great!",
            review_text="Love it"
        )
        review = await service.create_review(test_user.id, request)
        
        # Vote helpful
        voted_review = await service.vote_helpfulness(review.id, True)
        assert voted_review.helpful_count == 1
        
        # Vote not helpful
        voted_review = await service.vote_helpfulness(review.id, False)
        assert voted_review.not_helpful_count == 1


# ==================== Promotional Code Tests ====================

class TestPromoCode:
    """Test promotional code functionality"""
    
    async def test_create_percentage_promo_code(self, db_session: AsyncSession):
        """Test creating percentage-based promo code"""
        promo_code = PromoCode(
            code="SAVE20",
            promo_type=PromoCodeType.PERCENTAGE,
            discount_percentage=Decimal("20.00"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(promo_code)
        await db_session.commit()
        await db_session.refresh(promo_code)
        
        assert promo_code is not None
        assert promo_code.code == "SAVE20"
        assert promo_code.discount_percentage == Decimal("20.00")
    
    async def test_validate_promo_code(self, db_session: AsyncSession, test_user):
        """Test validating promotional code"""
        # Create promo code
        promo_code = PromoCode(
            code="TEST10",
            promo_type=PromoCodeType.PERCENTAGE,
            discount_percentage=Decimal("10.00"),
            minimum_order_value=Decimal("50.00"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            status=PromoCodeStatus.ACTIVE
        )
        db_session.add(promo_code)
        await db_session.commit()
        
        service = PromoCodeService(db_session)
        
        # Test valid code with sufficient order value
        validation = await service.validate_promo_code(
            code="TEST10",
            user_id=test_user.id,
            subtotal=Decimal("100.00")
        )
        
        assert validation.is_valid is True
        assert validation.discount_amount == Decimal("10.00")  # 10% of 100
    
    async def test_promo_code_minimum_order_value(
        self,
        db_session: AsyncSession,
        test_user
    ):
        """Test promo code minimum order value requirement"""
        # Create promo code with minimum order value
        promo_code = PromoCode(
            code="MIN50",
            promo_type=PromoCodeType.PERCENTAGE,
            discount_percentage=Decimal("15.00"),
            minimum_order_value=Decimal("50.00"),
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            status=PromoCodeStatus.ACTIVE
        )
        db_session.add(promo_code)
        await db_session.commit()
        
        service = PromoCodeService(db_session)
        
        # Test with insufficient order value
        validation = await service.validate_promo_code(
            code="MIN50",
            user_id=test_user.id,
            subtotal=Decimal("30.00")
        )
        
        assert validation.is_valid is False
        assert "Minimum order value" in validation.message
    
    async def test_promo_code_usage_tracking(
        self,
        db_session: AsyncSession,
        test_user
    ):
        """Test promo code usage tracking"""
        # Create promo code
        promo_code = PromoCode(
            code="TRACK",
            promo_type=PromoCodeType.FIXED_AMOUNT,
            discount_amount=Decimal("10.00"),
            usage_limit=5,
            valid_from=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30),
            status=PromoCodeStatus.ACTIVE
        )
        db_session.add(promo_code)
        await db_session.commit()
        await db_session.refresh(promo_code)
        
        service = PromoCodeService(db_session)
        
        # Apply promo code
        order_id = uuid4()
        await service.apply_promo_code(
            promo_code.id,
            test_user.id,
            order_id,
            Decimal("10.00")
        )
        
        # Verify usage count increased
        await db_session.refresh(promo_code)
        assert promo_code.current_usage_count == 1


# ==================== Abandoned Cart Tests ====================

class TestAbandonedCart:
    """Test abandoned cart functionality"""
    
    async def test_get_abandoned_carts(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test retrieving abandoned carts"""
        # Create cart with old activity
        cart = ShoppingCart(
            user_id=test_user.id,
            status=CartStatus.ACTIVE,
            last_activity_at=datetime.utcnow() - timedelta(days=3)
        )
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)
        
        # Add item to cart
        cart_item = CartItem(
            cart_id=cart.id,
            product_variant_id=test_product_variant.id,
            quantity=1,
            unit_price=test_product_variant.sale_price
        )
        db_session.add(cart_item)
        await db_session.commit()
        
        # Get abandoned carts
        service = AbandonedCartService(db_session)
        abandoned_carts = await service.get_abandoned_carts(days_abandoned=2)
        
        assert len(abandoned_carts) > 0
        assert any(c.id == cart.id for c in abandoned_carts)


# ==================== Integration Tests ====================

class TestECommerceIntegration:
    """Integration tests for e-commerce workflows"""
    
    async def test_complete_shopping_flow(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test complete shopping flow from cart to checkout"""
        cart_service = ShoppingCartService(db_session)
        
        # Add item to cart
        request = AddToCartRequest(
            product_variant_id=test_product_variant.id,
            quantity=2
        )
        await cart_service.add_to_cart(request, user_id=test_user.id)
        
        # Get cart
        cart = await cart_service.get_or_create_cart(user_id=test_user.id)
        
        assert cart.item_count == 1
        assert len(cart.items) == 1
        assert cart.subtotal > 0
    
    async def test_wishlist_to_cart_to_checkout(
        self,
        db_session: AsyncSession,
        test_user,
        test_product_variant
    ):
        """Test flow from wishlist to cart to checkout"""
        wishlist_service = WishlistService(db_session)
        cart_service = ShoppingCartService(db_session)
        
        # Add to wishlist
        wishlist_request = WishlistItemCreate(
            product_variant_id=test_product_variant.id
        )
        wishlist_item = await wishlist_service.add_to_wishlist(
            test_user.id,
            wishlist_request
        )
        
        # Move to cart
        cart_item = await wishlist_service.move_to_cart(
            wishlist_item.id,
            test_user.id,
            cart_service
        )
        
        assert cart_item is not None
        
        # Get cart
        cart = await cart_service.get_or_create_cart(user_id=test_user.id)
        assert cart.item_count == 1
