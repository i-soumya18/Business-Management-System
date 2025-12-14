"""
E-Commerce Service Layer

Business logic for e-commerce operations including shopping cart, wishlist,
product reviews, and promotional codes.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.product import ProductVariant
from app.repositories.ecommerce import (
    ShoppingCartRepository,
    CartItemRepository,
    WishlistRepository,
    WishlistItemRepository,
    ProductReviewRepository,
    PromoCodeRepository,
    PromoCodeUsageRepository
)
from app.repositories.product import ProductRepository
from app.schemas.ecommerce import (
    AddToCartRequest,
    UpdateCartItemRequest,
    CartItemResponse,
    ShoppingCartResponse,
    ApplyPromoCodeRequest,
    PromoCodeValidation,
    WishlistItemCreate,
    ProductReviewCreate,
    ProductReviewUpdate,
    ProductReviewModeration,
    ReviewHelpfulnessVote
)


class ShoppingCartService:
    """Service for shopping cart operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cart_repo = ShoppingCartRepository(db)
        self.cart_item_repo = CartItemRepository(db)
        self.product_repo = ProductRepository(db)
    
    async def get_or_create_cart(
        self,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None
    ) -> ShoppingCart:
        """Get or create shopping cart for user or session"""
        if user_id:
            cart = await self.cart_repo.get_active_cart_by_user(user_id)
            if not cart:
                cart = ShoppingCart(user_id=user_id, status=CartStatus.ACTIVE)
                self.db.add(cart)
                await self.db.commit()
                await self.db.refresh(cart)
        elif session_id:
            cart = await self.cart_repo.get_cart_by_session(session_id)
            if not cart:
                cart = ShoppingCart(session_id=session_id, status=CartStatus.ACTIVE)
                self.db.add(cart)
                await self.db.commit()
                await self.db.refresh(cart)
        else:
            raise ValueError("Either user_id or session_id must be provided")
        
        return cart
    
    async def add_to_cart(
        self,
        request: AddToCartRequest,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None
    ) -> CartItem:
        """Add item to shopping cart"""
        # Get or create cart
        cart = await self.get_or_create_cart(user_id, session_id)
        
        # Verify product variant exists
        product_variant = await self.product_repo.get_variant_by_id(request.product_variant_id)
        if not product_variant:
            raise ValueError(f"Product variant {request.product_variant_id} not found")
        
        # Check if item already exists in cart
        existing_item = await self.cart_item_repo.get_by_cart_and_variant(
            cart.id, request.product_variant_id
        )
        
        if existing_item:
            # Update quantity
            existing_item.quantity += request.quantity
            await self.db.commit()
            await self.db.refresh(existing_item)
            cart_item = existing_item
        else:
            # Create new cart item
            cart_item = CartItem(
                cart_id=cart.id,
                product_variant_id=request.product_variant_id,
                quantity=request.quantity,
                unit_price=product_variant.sale_price or product_variant.price
            )
            self.db.add(cart_item)
        
        # Update cart last activity
        cart.last_activity_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(cart_item)
        
        return cart_item
    
    async def update_cart_item(
        self,
        cart_item_id: UUID,
        request: UpdateCartItemRequest
    ) -> CartItem:
        """Update cart item quantity"""
        cart_item = await self.cart_item_repo.get(cart_item_id)
        if not cart_item:
            raise ValueError(f"Cart item {cart_item_id} not found")
        
        cart_item.quantity = request.quantity
        
        # Update cart last activity
        cart = await self.cart_repo.get(cart_item.cart_id)
        cart.last_activity_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(cart_item)
        
        return cart_item
    
    async def remove_from_cart(self, cart_item_id: UUID) -> None:
        """Remove item from cart"""
        cart_item = await self.cart_item_repo.get(cart_item_id)
        if not cart_item:
            raise ValueError(f"Cart item {cart_item_id} not found")
        
        # Update cart last activity
        cart = await self.cart_repo.get(cart_item.cart_id)
        cart.last_activity_at = datetime.utcnow()
        
        await self.cart_item_repo.delete(cart_item_id)
    
    async def clear_cart(self, cart_id: UUID) -> None:
        """Clear all items from cart"""
        await self.cart_item_repo.clear_cart(cart_id)
    
    async def merge_carts(
        self,
        guest_cart_id: UUID,
        user_cart_id: UUID
    ) -> ShoppingCart:
        """Merge guest cart into user cart (on login)"""
        guest_cart = await self.cart_repo.get(guest_cart_id)
        user_cart = await self.cart_repo.get(user_cart_id)
        
        if not guest_cart or not user_cart:
            raise ValueError("Invalid cart IDs")
        
        # Transfer items from guest cart to user cart
        for item in guest_cart.items:
            existing_item = await self.cart_item_repo.get_by_cart_and_variant(
                user_cart.id, item.product_variant_id
            )
            
            if existing_item:
                existing_item.quantity += item.quantity
            else:
                new_item = CartItem(
                    cart_id=user_cart.id,
                    product_variant_id=item.product_variant_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )
                self.db.add(new_item)
        
        # Mark guest cart as merged
        guest_cart.status = CartStatus.MERGED
        user_cart.last_activity_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user_cart)
        
        return user_cart


class PromoCodeService:
    """Service for promotional code operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.promo_repo = PromoCodeRepository(db)
        self.usage_repo = PromoCodeUsageRepository(db)
    
    async def validate_promo_code(
        self,
        code: str,
        user_id: Optional[UUID] = None,
        subtotal: Decimal = Decimal("0.00"),
        category_ids: Optional[List[UUID]] = None,
        product_variant_ids: Optional[List[UUID]] = None
    ) -> PromoCodeValidation:
        """Validate promotional code"""
        promo_code = await self.promo_repo.get_by_code(code)
        
        if not promo_code:
            return PromoCodeValidation(
                is_valid=False,
                message="Invalid promo code"
            )
        
        # Check if promo code is valid
        if not promo_code.is_valid():
            return PromoCodeValidation(
                is_valid=False,
                message="Promo code is not valid or has expired"
            )
        
        # Check minimum order value
        if promo_code.minimum_order_value and subtotal < promo_code.minimum_order_value:
            return PromoCodeValidation(
                is_valid=False,
                message=f"Minimum order value of ${promo_code.minimum_order_value} required"
            )
        
        # Check customer usage limit
        if user_id and promo_code.usage_per_customer:
            usage_count = await self.promo_repo.get_customer_usage_count(promo_code.id, user_id)
            if usage_count >= promo_code.usage_per_customer:
                return PromoCodeValidation(
                    is_valid=False,
                    message="You have reached the usage limit for this promo code"
                )
        
        # Check new customer restriction
        if promo_code.new_customers_only and user_id:
            # TODO: Check if customer has previous orders
            pass
        
        # Check category/product restrictions
        if promo_code.applicable_categories and category_ids:
            # Check if any cart items match applicable categories
            pass
        
        # Calculate discount
        discount_amount = Decimal("0.00")
        
        if promo_code.promo_type == PromoCodeType.PERCENTAGE:
            discount_amount = (subtotal * promo_code.discount_percentage / 100)
            if promo_code.maximum_discount_amount:
                discount_amount = min(discount_amount, promo_code.maximum_discount_amount)
        elif promo_code.promo_type == PromoCodeType.FIXED_AMOUNT:
            discount_amount = promo_code.discount_amount
        elif promo_code.promo_type == PromoCodeType.FREE_SHIPPING:
            # TODO: Get shipping cost
            discount_amount = Decimal("0.00")
        
        return PromoCodeValidation(
            is_valid=True,
            promo_code_id=promo_code.id,
            discount_amount=discount_amount,
            promo_code_type=promo_code.promo_type,
            message="Promo code applied successfully"
        )
    
    async def apply_promo_code(
        self,
        promo_code_id: UUID,
        user_id: UUID,
        order_id: UUID,
        discount_amount: Decimal
    ) -> PromoCodeUsage:
        """Apply promo code to order"""
        # Increment usage count
        await self.promo_repo.increment_usage(promo_code_id)
        
        # Create usage record
        usage = PromoCodeUsage(
            promo_code_id=promo_code_id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount
        )
        self.db.add(usage)
        await self.db.commit()
        await self.db.refresh(usage)
        
        return usage


class WishlistService:
    """Service for wishlist operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wishlist_repo = WishlistRepository(db)
        self.wishlist_item_repo = WishlistItemRepository(db)
        self.product_repo = ProductRepository(db)
    
    async def add_to_wishlist(
        self,
        user_id: UUID,
        request: WishlistItemCreate,
        wishlist_id: Optional[UUID] = None
    ) -> WishlistItem:
        """Add item to wishlist"""
        # Get or create default wishlist if no wishlist_id provided
        if not wishlist_id:
            wishlist = await self.wishlist_repo.get_default_wishlist(user_id)
        else:
            wishlist = await self.wishlist_repo.get(wishlist_id)
            if not wishlist or wishlist.user_id != user_id:
                raise ValueError("Invalid wishlist")
        
        # Verify product variant exists
        product_variant = await self.product_repo.get_variant_by_id(request.product_variant_id)
        if not product_variant:
            raise ValueError(f"Product variant {request.product_variant_id} not found")
        
        # Check if item already exists in wishlist
        existing_item = await self.wishlist_item_repo.get_by_wishlist_and_variant(
            wishlist.id, request.product_variant_id
        )
        
        if existing_item:
            raise ValueError("Item already in wishlist")
        
        # Create wishlist item
        wishlist_item = WishlistItem(
            wishlist_id=wishlist.id,
            product_variant_id=request.product_variant_id,
            priority=request.priority,
            notes=request.notes
        )
        self.db.add(wishlist_item)
        await self.db.commit()
        await self.db.refresh(wishlist_item)
        
        return wishlist_item
    
    async def remove_from_wishlist(self, wishlist_item_id: UUID, user_id: UUID) -> None:
        """Remove item from wishlist"""
        wishlist_item = await self.wishlist_item_repo.get(wishlist_item_id)
        if not wishlist_item:
            raise ValueError(f"Wishlist item {wishlist_item_id} not found")
        
        # Verify ownership
        wishlist = await self.wishlist_repo.get(wishlist_item.wishlist_id)
        if wishlist.user_id != user_id:
            raise ValueError("Unauthorized")
        
        await self.wishlist_item_repo.delete(wishlist_item_id)
    
    async def move_to_cart(
        self,
        wishlist_item_id: UUID,
        user_id: UUID,
        cart_service: ShoppingCartService
    ) -> CartItem:
        """Move item from wishlist to cart"""
        wishlist_item = await self.wishlist_item_repo.get(wishlist_item_id)
        if not wishlist_item:
            raise ValueError(f"Wishlist item {wishlist_item_id} not found")
        
        # Add to cart
        cart_item = await cart_service.add_to_cart(
            AddToCartRequest(
                product_variant_id=wishlist_item.product_variant_id,
                quantity=1
            ),
            user_id=user_id
        )
        
        # Remove from wishlist
        await self.wishlist_item_repo.delete(wishlist_item_id)
        
        return cart_item


class ProductReviewService:
    """Service for product review operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.review_repo = ProductReviewRepository(db)
        self.product_repo = ProductRepository(db)
    
    async def create_review(
        self,
        user_id: UUID,
        request: ProductReviewCreate
    ) -> ProductReview:
        """Create product review"""
        # Verify product variant exists
        product_variant = await self.product_repo.get_variant_by_id(request.product_variant_id)
        if not product_variant:
            raise ValueError(f"Product variant {request.product_variant_id} not found")
        
        # TODO: Check if user has purchased this product
        is_verified_purchase = False
        
        # Create review
        review = ProductReview(
            user_id=user_id,
            product_variant_id=request.product_variant_id,
            order_id=request.order_id,
            rating=request.rating,
            title=request.title,
            review_text=request.review_text,
            is_verified_purchase=is_verified_purchase,
            status=ReviewStatus.PENDING  # Requires moderation
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        
        return review
    
    async def update_review(
        self,
        review_id: UUID,
        user_id: UUID,
        request: ProductReviewUpdate
    ) -> ProductReview:
        """Update product review"""
        review = await self.review_repo.get(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        # Verify ownership
        if review.user_id != user_id:
            raise ValueError("Unauthorized")
        
        # Update fields
        if request.rating is not None:
            review.rating = request.rating
        if request.title is not None:
            review.title = request.title
        if request.review_text is not None:
            review.review_text = request.review_text
        
        # Reset to pending if content changed
        review.status = ReviewStatus.PENDING
        review.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(review)
        
        return review
    
    async def moderate_review(
        self,
        review_id: UUID,
        moderator_id: UUID,
        request: ProductReviewModeration
    ) -> ProductReview:
        """Moderate product review (admin only)"""
        review = await self.review_repo.get(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        review.status = request.status
        review.moderator_notes = request.moderator_notes
        review.moderated_by = moderator_id
        review.moderated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(review)
        
        return review
    
    async def vote_helpfulness(
        self,
        review_id: UUID,
        is_helpful: bool
    ) -> ProductReview:
        """Vote on review helpfulness"""
        return await self.review_repo.update_helpfulness(review_id, is_helpful)
    
    async def get_product_reviews(
        self,
        product_variant_id: UUID,
        status: Optional[ReviewStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[ProductReview]:
        """Get reviews for a product"""
        return await self.review_repo.get_by_product(
            product_variant_id,
            status=status or ReviewStatus.APPROVED,
            skip=skip,
            limit=limit
        )
    
    async def get_product_rating_stats(self, product_variant_id: UUID) -> dict:
        """Get rating statistics for a product"""
        return await self.review_repo.get_product_rating_stats(product_variant_id)


class AbandonedCartService:
    """Service for abandoned cart recovery"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cart_repo = ShoppingCartRepository(db)
    
    async def get_abandoned_carts(
        self,
        days_abandoned: int = 1,
        skip: int = 0,
        limit: int = 100
    ) -> List[ShoppingCart]:
        """Get abandoned carts for recovery campaigns"""
        return await self.cart_repo.get_abandoned_carts(
            days_abandoned=days_abandoned,
            skip=skip,
            limit=limit
        )
    
    async def mark_as_abandoned(self, cart_id: UUID) -> ShoppingCart:
        """Mark cart as abandoned"""
        cart = await self.cart_repo.get(cart_id)
        if not cart:
            raise ValueError(f"Cart {cart_id} not found")
        
        cart.status = CartStatus.ABANDONED
        await self.db.commit()
        await self.db.refresh(cart)
        
        return cart
