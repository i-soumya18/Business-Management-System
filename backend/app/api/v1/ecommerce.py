"""
E-Commerce API Endpoints

REST API endpoints for e-commerce operations including shopping cart, wishlist,
product reviews, and promotional codes.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.ecommerce import ReviewStatus
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
    ShoppingCartResponse,
    CartItemResponse,
    ApplyPromoCodeRequest,
    PromoCodeValidation,
    WishlistCreate,
    WishlistUpdate,
    WishlistResponse,
    WishlistItemCreate,
    WishlistItemResponse,
    ProductReviewCreate,
    ProductReviewUpdate,
    ProductReviewResponse,
    ProductReviewModeration,
    ReviewHelpfulnessVote,
    ProductReviewStats,
    PromoCodeCreate,
    PromoCodeUpdate,
    PromoCodeResponse,
    AbandonedCartInfo
)

router = APIRouter()


# ==================== Shopping Cart Endpoints ====================

@router.get("/cart", response_model=ShoppingCartResponse, tags=["Shopping Cart"])
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's shopping cart"""
    service = ShoppingCartService(db)
    cart = await service.get_or_create_cart(user_id=current_user.id)
    
    return ShoppingCartResponse(
        id=cart.id,
        user_id=cart.user_id,
        session_id=cart.session_id,
        status=cart.status,
        items=[
            CartItemResponse(
                id=item.id,
                cart_id=item.cart_id,
                product_variant_id=item.product_variant_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                added_at=item.added_at
            )
            for item in cart.items
        ],
        subtotal=cart.subtotal,
        item_count=cart.item_count,
        promo_code_id=cart.promo_code_id,
        discount_amount=cart.discount_amount,
        total=cart.total,
        last_activity_at=cart.last_activity_at,
        created_at=cart.created_at
    )


@router.post("/cart/items", response_model=CartItemResponse, tags=["Shopping Cart"])
async def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add item to shopping cart"""
    service = ShoppingCartService(db)
    
    try:
        cart_item = await service.add_to_cart(request, user_id=current_user.id)
        
        return CartItemResponse(
            id=cart_item.id,
            cart_id=cart_item.cart_id,
            product_variant_id=cart_item.product_variant_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            subtotal=cart_item.subtotal,
            added_at=cart_item.added_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/cart/items/{item_id}", response_model=CartItemResponse, tags=["Shopping Cart"])
async def update_cart_item(
    item_id: UUID,
    request: UpdateCartItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update cart item quantity"""
    service = ShoppingCartService(db)
    
    try:
        cart_item = await service.update_cart_item(item_id, request)
        
        return CartItemResponse(
            id=cart_item.id,
            cart_id=cart_item.cart_id,
            product_variant_id=cart_item.product_variant_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            subtotal=cart_item.subtotal,
            added_at=cart_item.added_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/cart/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Shopping Cart"])
async def remove_from_cart(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove item from cart"""
    service = ShoppingCartService(db)
    
    try:
        await service.remove_from_cart(item_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT, tags=["Shopping Cart"])
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear all items from cart"""
    service = ShoppingCartService(db)
    cart = await service.get_or_create_cart(user_id=current_user.id)
    await service.clear_cart(cart.id)


@router.post("/cart/apply-promo", response_model=PromoCodeValidation, tags=["Shopping Cart"])
async def apply_promo_code(
    request: ApplyPromoCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply promotional code to cart"""
    cart_service = ShoppingCartService(db)
    promo_service = PromoCodeService(db)
    
    # Get cart
    cart = await cart_service.get_or_create_cart(user_id=current_user.id)
    
    # Validate promo code
    validation = await promo_service.validate_promo_code(
        code=request.code,
        user_id=current_user.id,
        subtotal=cart.subtotal
    )
    
    if validation.is_valid:
        # Update cart with promo code
        cart.promo_code_id = validation.promo_code_id
        cart.discount_amount = validation.discount_amount
        await db.commit()
    
    return validation


# ==================== Wishlist Endpoints ====================

@router.get("/wishlists", response_model=List[WishlistResponse], tags=["Wishlist"])
async def get_wishlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get user's wishlists"""
    service = WishlistService(db)
    wishlists = await service.wishlist_repo.get_by_user(current_user.id, skip, limit)
    
    return [
        WishlistResponse(
            id=wishlist.id,
            user_id=wishlist.user_id,
            name=wishlist.name,
            description=wishlist.description,
            is_public=wishlist.is_public,
            items=[
                WishlistItemResponse(
                    id=item.id,
                    wishlist_id=item.wishlist_id,
                    product_variant_id=item.product_variant_id,
                    priority=item.priority,
                    notes=item.notes,
                    added_at=item.added_at
                )
                for item in wishlist.items
            ],
            created_at=wishlist.created_at,
            updated_at=wishlist.updated_at
        )
        for wishlist in wishlists
    ]


@router.post("/wishlists", response_model=WishlistResponse, tags=["Wishlist"])
async def create_wishlist(
    request: WishlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new wishlist"""
    from app.models.ecommerce import Wishlist
    
    wishlist = Wishlist(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        is_public=request.is_public
    )
    db.add(wishlist)
    await db.commit()
    await db.refresh(wishlist)
    
    return WishlistResponse(
        id=wishlist.id,
        user_id=wishlist.user_id,
        name=wishlist.name,
        description=wishlist.description,
        is_public=wishlist.is_public,
        items=[],
        created_at=wishlist.created_at,
        updated_at=wishlist.updated_at
    )


@router.put("/wishlists/{wishlist_id}", response_model=WishlistResponse, tags=["Wishlist"])
async def update_wishlist(
    wishlist_id: UUID,
    request: WishlistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update wishlist"""
    service = WishlistService(db)
    wishlist = await service.wishlist_repo.get(wishlist_id)
    
    if not wishlist or wishlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")
    
    if request.name is not None:
        wishlist.name = request.name
    if request.description is not None:
        wishlist.description = request.description
    if request.is_public is not None:
        wishlist.is_public = request.is_public
    
    await db.commit()
    await db.refresh(wishlist)
    
    return WishlistResponse(
        id=wishlist.id,
        user_id=wishlist.user_id,
        name=wishlist.name,
        description=wishlist.description,
        is_public=wishlist.is_public,
        items=[
            WishlistItemResponse(
                id=item.id,
                wishlist_id=item.wishlist_id,
                product_variant_id=item.product_variant_id,
                priority=item.priority,
                notes=item.notes,
                added_at=item.added_at
            )
            for item in wishlist.items
        ],
        created_at=wishlist.created_at,
        updated_at=wishlist.updated_at
    )


@router.delete("/wishlists/{wishlist_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Wishlist"])
async def delete_wishlist(
    wishlist_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete wishlist"""
    service = WishlistService(db)
    wishlist = await service.wishlist_repo.get(wishlist_id)
    
    if not wishlist or wishlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")
    
    await service.wishlist_repo.delete(wishlist_id)


@router.post("/wishlists/items", response_model=WishlistItemResponse, tags=["Wishlist"])
async def add_to_wishlist(
    request: WishlistItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    wishlist_id: Optional[UUID] = Query(None)
):
    """Add item to wishlist"""
    service = WishlistService(db)
    
    try:
        wishlist_item = await service.add_to_wishlist(current_user.id, request, wishlist_id)
        
        return WishlistItemResponse(
            id=wishlist_item.id,
            wishlist_id=wishlist_item.wishlist_id,
            product_variant_id=wishlist_item.product_variant_id,
            priority=wishlist_item.priority,
            notes=wishlist_item.notes,
            added_at=wishlist_item.added_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/wishlists/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Wishlist"])
async def remove_from_wishlist(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove item from wishlist"""
    service = WishlistService(db)
    
    try:
        await service.remove_from_wishlist(item_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/wishlists/items/{item_id}/move-to-cart", response_model=CartItemResponse, tags=["Wishlist"])
async def move_to_cart(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Move item from wishlist to cart"""
    wishlist_service = WishlistService(db)
    cart_service = ShoppingCartService(db)
    
    try:
        cart_item = await wishlist_service.move_to_cart(item_id, current_user.id, cart_service)
        
        return CartItemResponse(
            id=cart_item.id,
            cart_id=cart_item.cart_id,
            product_variant_id=cart_item.product_variant_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            subtotal=cart_item.subtotal,
            added_at=cart_item.added_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Product Review Endpoints ====================

@router.get("/products/{product_variant_id}/reviews", response_model=List[ProductReviewResponse], tags=["Reviews"])
async def get_product_reviews(
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """Get reviews for a product"""
    service = ProductReviewService(db)
    reviews = await service.get_product_reviews(product_variant_id, skip=skip, limit=limit)
    
    return [
        ProductReviewResponse(
            id=review.id,
            user_id=review.user_id,
            product_variant_id=review.product_variant_id,
            order_id=review.order_id,
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            status=review.status,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
        for review in reviews
    ]


@router.get("/products/{product_variant_id}/reviews/stats", response_model=ProductReviewStats, tags=["Reviews"])
async def get_product_review_stats(
    product_variant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get review statistics for a product"""
    service = ProductReviewService(db)
    stats = await service.get_product_rating_stats(product_variant_id)
    
    return ProductReviewStats(
        total_reviews=stats["total_reviews"],
        average_rating=stats["average_rating"],
        rating_distribution=stats["rating_distribution"],
        verified_purchase_count=stats["verified_purchase_count"]
    )


@router.post("/reviews", response_model=ProductReviewResponse, tags=["Reviews"])
async def create_review(
    request: ProductReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create product review"""
    service = ProductReviewService(db)
    
    try:
        review = await service.create_review(current_user.id, request)
        
        return ProductReviewResponse(
            id=review.id,
            user_id=review.user_id,
            product_variant_id=review.product_variant_id,
            order_id=review.order_id,
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            status=review.status,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/reviews/{review_id}", response_model=ProductReviewResponse, tags=["Reviews"])
async def update_review(
    review_id: UUID,
    request: ProductReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update product review"""
    service = ProductReviewService(db)
    
    try:
        review = await service.update_review(review_id, current_user.id, request)
        
        return ProductReviewResponse(
            id=review.id,
            user_id=review.user_id,
            product_variant_id=review.product_variant_id,
            order_id=review.order_id,
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            status=review.status,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Reviews"])
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete product review"""
    service = ProductReviewService(db)
    review = await service.review_repo.get(review_id)
    
    if not review or review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    
    await service.review_repo.delete(review_id)


@router.post("/reviews/{review_id}/vote", response_model=ProductReviewResponse, tags=["Reviews"])
async def vote_review_helpfulness(
    review_id: UUID,
    request: ReviewHelpfulnessVote,
    db: AsyncSession = Depends(get_db)
):
    """Vote on review helpfulness"""
    service = ProductReviewService(db)
    
    try:
        review = await service.vote_helpfulness(review_id, request.is_helpful)
        
        return ProductReviewResponse(
            id=review.id,
            user_id=review.user_id,
            product_variant_id=review.product_variant_id,
            order_id=review.order_id,
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            status=review.status,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Admin: Review Moderation ====================

@router.get("/admin/reviews/pending", response_model=List[ProductReviewResponse], tags=["Admin - Reviews"])
async def get_pending_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get pending reviews for moderation (admin only)"""
    # TODO: Add admin permission check
    
    service = ProductReviewService(db)
    reviews = await service.review_repo.get_pending_reviews(skip, limit)
    
    return [
        ProductReviewResponse(
            id=review.id,
            user_id=review.user_id,
            product_variant_id=review.product_variant_id,
            order_id=review.order_id,
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            status=review.status,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
        for review in reviews
    ]


@router.post("/admin/reviews/{review_id}/moderate", response_model=ProductReviewResponse, tags=["Admin - Reviews"])
async def moderate_review(
    review_id: UUID,
    request: ProductReviewModeration,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Moderate product review (admin only)"""
    # TODO: Add admin permission check
    
    service = ProductReviewService(db)
    
    try:
        review = await service.moderate_review(review_id, current_user.id, request)
        
        return ProductReviewResponse(
            id=review.id,
            user_id=review.user_id,
            product_variant_id=review.product_variant_id,
            order_id=review.order_id,
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            status=review.status,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            moderator_notes=review.moderator_notes,
            moderated_by=review.moderated_by,
            moderated_at=review.moderated_at,
            created_at=review.created_at,
            updated_at=review.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Admin: Promotional Codes ====================

@router.get("/admin/promo-codes", response_model=List[PromoCodeResponse], tags=["Admin - Promo Codes"])
async def get_promo_codes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all promotional codes (admin only)"""
    # TODO: Add admin permission check
    
    service = PromoCodeService(db)
    promo_codes = await service.promo_repo.get_active_codes(skip, limit)
    
    return [
        PromoCodeResponse(
            id=code.id,
            code=code.code,
            promo_type=code.promo_type,
            discount_percentage=code.discount_percentage,
            discount_amount=code.discount_amount,
            minimum_order_value=code.minimum_order_value,
            maximum_discount_amount=code.maximum_discount_amount,
            usage_limit=code.usage_limit,
            usage_per_customer=code.usage_per_customer,
            current_usage_count=code.current_usage_count,
            valid_from=code.valid_from,
            valid_until=code.valid_until,
            status=code.status,
            is_active=code.is_active,
            new_customers_only=code.new_customers_only,
            created_at=code.created_at
        )
        for code in promo_codes
    ]


@router.post("/admin/promo-codes", response_model=PromoCodeResponse, tags=["Admin - Promo Codes"])
async def create_promo_code(
    request: PromoCodeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create promotional code (admin only)"""
    # TODO: Add admin permission check
    
    from app.models.ecommerce import PromoCode
    
    promo_code = PromoCode(
        code=request.code.upper(),
        promo_type=request.promo_type,
        discount_percentage=request.discount_percentage,
        discount_amount=request.discount_amount,
        minimum_order_value=request.minimum_order_value,
        maximum_discount_amount=request.maximum_discount_amount,
        usage_limit=request.usage_limit,
        usage_per_customer=request.usage_per_customer,
        valid_from=request.valid_from,
        valid_until=request.valid_until,
        applicable_categories=request.applicable_categories,
        applicable_products=request.applicable_products,
        excluded_products=request.excluded_products,
        customer_emails=request.customer_emails,
        is_active=request.is_active,
        new_customers_only=request.new_customers_only
    )
    db.add(promo_code)
    await db.commit()
    await db.refresh(promo_code)
    
    return PromoCodeResponse(
        id=promo_code.id,
        code=promo_code.code,
        promo_type=promo_code.promo_type,
        discount_percentage=promo_code.discount_percentage,
        discount_amount=promo_code.discount_amount,
        minimum_order_value=promo_code.minimum_order_value,
        maximum_discount_amount=promo_code.maximum_discount_amount,
        usage_limit=promo_code.usage_limit,
        usage_per_customer=promo_code.usage_per_customer,
        current_usage_count=promo_code.current_usage_count,
        valid_from=promo_code.valid_from,
        valid_until=promo_code.valid_until,
        status=promo_code.status,
        is_active=promo_code.is_active,
        new_customers_only=promo_code.new_customers_only,
        created_at=promo_code.created_at
    )


@router.put("/admin/promo-codes/{promo_code_id}", response_model=PromoCodeResponse, tags=["Admin - Promo Codes"])
async def update_promo_code(
    promo_code_id: UUID,
    request: PromoCodeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update promotional code (admin only)"""
    # TODO: Add admin permission check
    
    service = PromoCodeService(db)
    promo_code = await service.promo_repo.get(promo_code_id)
    
    if not promo_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    
    # Update fields
    if request.discount_percentage is not None:
        promo_code.discount_percentage = request.discount_percentage
    if request.discount_amount is not None:
        promo_code.discount_amount = request.discount_amount
    if request.usage_limit is not None:
        promo_code.usage_limit = request.usage_limit
    if request.usage_per_customer is not None:
        promo_code.usage_per_customer = request.usage_per_customer
    if request.valid_from is not None:
        promo_code.valid_from = request.valid_from
    if request.valid_until is not None:
        promo_code.valid_until = request.valid_until
    if request.is_active is not None:
        promo_code.is_active = request.is_active
    
    await db.commit()
    await db.refresh(promo_code)
    
    return PromoCodeResponse(
        id=promo_code.id,
        code=promo_code.code,
        promo_type=promo_code.promo_type,
        discount_percentage=promo_code.discount_percentage,
        discount_amount=promo_code.discount_amount,
        minimum_order_value=promo_code.minimum_order_value,
        maximum_discount_amount=promo_code.maximum_discount_amount,
        usage_limit=promo_code.usage_limit,
        usage_per_customer=promo_code.usage_per_customer,
        current_usage_count=promo_code.current_usage_count,
        valid_from=promo_code.valid_from,
        valid_until=promo_code.valid_until,
        status=promo_code.status,
        is_active=promo_code.is_active,
        new_customers_only=promo_code.new_customers_only,
        created_at=promo_code.created_at
    )


@router.delete("/admin/promo-codes/{promo_code_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin - Promo Codes"])
async def delete_promo_code(
    promo_code_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete promotional code (admin only)"""
    # TODO: Add admin permission check
    
    service = PromoCodeService(db)
    await service.promo_repo.delete(promo_code_id)


# ==================== Admin: Abandoned Carts ====================

@router.get("/admin/abandoned-carts", response_model=List[AbandonedCartInfo], tags=["Admin - Abandoned Carts"])
async def get_abandoned_carts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days_abandoned: int = Query(1, description="Days since last activity"),
    skip: int = 0,
    limit: int = 100
):
    """Get abandoned carts for recovery (admin only)"""
    # TODO: Add admin permission check
    
    service = AbandonedCartService(db)
    carts = await service.get_abandoned_carts(days_abandoned, skip, limit)
    
    from datetime import datetime
    
    return [
        AbandonedCartInfo(
            cart_id=cart.id,
            user_id=cart.user_id,
            session_id=cart.session_id,
            item_count=cart.item_count,
            subtotal=cart.subtotal,
            last_activity_at=cart.last_activity_at,
            days_abandoned=(datetime.utcnow() - cart.last_activity_at).days
        )
        for cart in carts
    ]
